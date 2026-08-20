from __future__ import annotations

from contextlib import ExitStack
from dataclasses import dataclass
import base64
import hashlib
import inspect
import json
from pathlib import Path
import shutil
import subprocess
import tempfile
from typing import Any, Protocol

from .config import Settings


@dataclass(slots=True)
class EditImageJob:
    source: Path
    output: Path
    prompt: str
    negative_prompt: str = ""
    strength: float = 0.5
    preserve_subject: bool = True
    state: list[float] | None = None
    mask: Path | None = None
    seed: int | None = None


@dataclass(slots=True)
class EditVideoJob:
    source: Path
    output: Path
    prompt: str
    negative_prompt: str = ""
    strength: float = 0.45
    preserve_subject: bool = True
    preserve_audio: bool = True
    state: list[float] | None = None
    chunk_seconds: float = 6.0
    style_lock: bool = True
    temporal_blend: float = 0.12
    seed: int | None = None


class EditProvider(Protocol):
    name: str

    def edit_image(self, job: EditImageJob) -> Path: ...

    def edit_video(self, job: EditVideoJob) -> Path: ...


def _clamp_strength(value: float) -> float:
    number = float(value)
    if not 0.0 <= number <= 1.0:
        raise ValueError("edit strength must be between 0 and 1")
    return number


def _clamp_temporal(value: float) -> float:
    number = float(value)
    if not 0.0 <= number <= 1.0:
        raise ValueError("temporal_blend must be between 0 and 1")
    return number


def _seed_from_job(prompt: str, state: list[float] | None, explicit: int | None = None) -> int:
    if explicit is not None:
        return int(explicit) & 0x7FFFFFFF
    payload = prompt + "|" + ",".join(f"{value:.8f}" for value in (state or []))
    return int.from_bytes(hashlib.sha256(payload.encode("utf-8")).digest()[:4], "big") & 0x7FFFFFFF


def _prompt_tint(prompt: str) -> tuple[int, int, int]:
    digest = hashlib.sha256(prompt.strip().lower().encode("utf-8")).digest()
    return (64 + digest[0] % 160, 64 + digest[1] % 160, 64 + digest[2] % 160)


def prompt_video_filter(prompt: str, strength: float = 0.5) -> str:
    """Return a deterministic, broadly-supported FFmpeg filter chain."""
    strength = _clamp_strength(strength)
    text = prompt.strip().lower()
    filters: list[str] = []

    contrast = 1.0 + 0.18 * strength
    saturation = 1.0 + 0.32 * strength
    brightness = 0.015 * strength

    if any(word in text for word in ("cinematic", "movie", "film")):
        contrast += 0.08 * strength
        saturation -= 0.04 * strength
    if any(word in text for word in ("neon", "cyberpunk", "vivid", "electric")):
        saturation += 0.35 * strength
        contrast += 0.06 * strength
    if any(word in text for word in ("soft", "dream", "ethereal", "pastel")):
        contrast -= 0.10 * strength
        saturation -= 0.12 * strength
    if any(word in text for word in ("black and white", "monochrome", "grayscale")):
        filters.append("hue=s=0")
    if any(word in text for word in ("warm", "golden", "sunset", "amber")):
        filters.append(f"colorbalance=rs={0.12 * strength:.4f}:gs={0.035 * strength:.4f}:bs={-0.10 * strength:.4f}")
    if any(word in text for word in ("cool", "moonlit", "blue", "icy")):
        filters.append(f"colorbalance=rs={-0.08 * strength:.4f}:gs={0.015 * strength:.4f}:bs={0.12 * strength:.4f}")

    filters.append(
        f"eq=contrast={max(0.5, contrast):.4f}:saturation={max(0.0, saturation):.4f}:brightness={brightness:.4f}"
    )
    digest = hashlib.sha256(text.encode("utf-8")).digest()
    hue = ((digest[0] / 255.0) - 0.5) * 10.0 * strength
    filters.append(f"hue=h={hue:.4f}")
    return ",".join(filters)


def _parse_rate(value: str | None, fallback: float = 24.0) -> float:
    text = str(value or "").strip()
    if not text:
        return fallback
    if "/" in text:
        left, right = text.split("/", 1)
        try:
            denominator = float(right)
            return float(left) / denominator if denominator else fallback
        except ValueError:
            return fallback
    try:
        return float(text)
    except ValueError:
        return fallback


def _probe_video(source: Path) -> dict[str, Any]:
    ffprobe = shutil.which("ffprobe")
    if not ffprobe:
        raise RuntimeError("semantic video editing requires ffprobe on PATH")
    command = [
        ffprobe,
        "-v",
        "error",
        "-select_streams",
        "v:0",
        "-show_entries",
        "stream=width,height,avg_frame_rate:format=duration",
        "-of",
        "json",
        str(source),
    ]
    try:
        result = subprocess.run(command, check=True, capture_output=True, text=True)
        payload = json.loads(result.stdout or "{}")
    except (subprocess.CalledProcessError, json.JSONDecodeError) as exc:
        raise RuntimeError(f"could not probe video for semantic editing: {source}") from exc
    streams = payload.get("streams") or []
    if not streams:
        raise RuntimeError(f"video has no readable video stream: {source}")
    stream = streams[0]
    duration = float((payload.get("format") or {}).get("duration") or 0.0)
    if duration <= 0:
        raise RuntimeError("semantic video editing requires a measurable video duration")
    return {
        "duration": duration,
        "fps": max(1.0, _parse_rate(stream.get("avg_frame_rate"), 24.0)),
        "width": int(stream.get("width") or 0),
        "height": int(stream.get("height") or 0),
    }


class NativeEditProvider:
    name = "native"

    def __init__(self, settings: Settings):
        self.settings = settings

    def edit_image(self, job: EditImageJob) -> Path:
        strength = _clamp_strength(job.strength)
        try:
            from PIL import Image, ImageEnhance, ImageFilter, ImageOps
        except ImportError as exc:
            raise RuntimeError(
                "Pillow is required for native image editing: pip install -e '.[media]'"
            ) from exc

        job.output.parent.mkdir(parents=True, exist_ok=True)
        with Image.open(job.source) as opened:
            source_mode = "RGBA" if "A" in opened.getbands() else "RGB"
            original = opened.convert(source_mode)
            alpha = original.getchannel("A") if source_mode == "RGBA" else None
            rgb = original.convert("RGB")
            text = job.prompt.lower()

            contrast = 1.0 + 0.30 * strength
            color = 1.0 + 0.35 * strength
            brightness = 1.0 + 0.05 * strength
            sharpness = 1.0 + 0.45 * strength

            if any(word in text for word in ("cinematic", "movie", "film")):
                contrast += 0.18 * strength
                color -= 0.08 * strength
            if any(word in text for word in ("neon", "cyberpunk", "vivid", "electric")):
                color += 0.55 * strength
                contrast += 0.12 * strength
            if any(word in text for word in ("soft", "dream", "ethereal", "pastel")):
                sharpness = max(0.4, 1.0 - 0.45 * strength)
                contrast = max(0.6, contrast - 0.25 * strength)
                rgb = rgb.filter(ImageFilter.GaussianBlur(radius=1.5 * strength))
            if any(word in text for word in ("sharp", "crisp", "detailed", "clarity")):
                sharpness += 0.65 * strength
            if any(word in text for word in ("dark", "night", "noir")):
                brightness = max(0.45, brightness - 0.28 * strength)
            if any(word in text for word in ("bright", "daylight", "glowing", "luminous")):
                brightness += 0.16 * strength

            rgb = ImageEnhance.Contrast(rgb).enhance(max(0.1, contrast))
            rgb = ImageEnhance.Color(rgb).enhance(max(0.0, color))
            rgb = ImageEnhance.Brightness(rgb).enhance(max(0.1, brightness))
            rgb = ImageEnhance.Sharpness(rgb).enhance(max(0.0, sharpness))

            if any(word in text for word in ("black and white", "monochrome", "grayscale")):
                gray = ImageOps.grayscale(rgb)
                rgb = Image.merge("RGB", (gray, gray, gray))

            tint = _prompt_tint(job.prompt)
            if any(word in text for word in ("warm", "golden", "sunset", "amber")):
                tint = (238, 146, 72)
            elif any(word in text for word in ("cool", "moonlit", "blue", "icy")):
                tint = (72, 128, 238)
            elif any(word in text for word in ("neon", "cyberpunk", "electric")):
                tint = (178, 62, 238)

            overlay = Image.new("RGB", rgb.size, tint)
            tint_strength = min(0.32, 0.06 + strength * 0.20)
            rgb = Image.blend(rgb, overlay, tint_strength)
            preserve_factor = strength * (0.72 if job.preserve_subject else 0.92)
            rgb = Image.blend(original.convert("RGB"), rgb, preserve_factor)

            if alpha is not None:
                final = rgb.convert("RGBA")
                final.putalpha(alpha)
            else:
                final = rgb

            suffix = job.output.suffix.lower()
            if suffix in {".jpg", ".jpeg"} and final.mode == "RGBA":
                final = final.convert("RGB")
            final.save(job.output)
        return job.output

    def edit_video(self, job: EditVideoJob) -> Path:
        _clamp_strength(job.strength)
        _clamp_temporal(job.temporal_blend)
        if float(job.chunk_seconds) <= 0:
            raise ValueError("chunk_seconds must be positive")
        job.output.parent.mkdir(parents=True, exist_ok=True)
        ffmpeg = shutil.which(self.settings.ffmpeg) or self.settings.ffmpeg
        video_filter = prompt_video_filter(job.prompt, job.strength)
        command = [ffmpeg, "-y", "-i", str(job.source), "-map", "0:v:0"]
        if job.preserve_audio:
            command += ["-map", "0:a?"]
        command += [
            "-vf",
            video_filter,
            "-c:v",
            "libx264",
            "-preset",
            "veryfast",
            "-crf",
            "20",
            "-pix_fmt",
            "yuv420p",
        ]
        if job.preserve_audio:
            command += ["-c:a", "aac", "-b:a", "192k"]
        else:
            command += ["-an"]
        command += ["-movflags", "+faststart", str(job.output)]
        try:
            subprocess.run(command, check=True, capture_output=True)
        except FileNotFoundError as exc:
            raise RuntimeError("FFmpeg was not found. Install ffmpeg or set COSMOS_FFMPEG.") from exc
        except subprocess.CalledProcessError as exc:
            stderr = exc.stderr.decode("utf-8", errors="replace")[-3000:]
            raise RuntimeError(f"COSMOS native video edit failed: {stderr}") from exc
        return job.output


_DIFFUSERS_PIPELINES: dict[tuple[str, str], Any] = {}


class DiffusersEditProvider:
    """Optional local semantic renderer.

    It intentionally loads dependencies and model weights lazily so the default
    desktop/mobile packages stay small and work without a GPU or model download.
    """

    name = "diffusers"

    def __init__(self, settings: Settings):
        self.settings = settings

    def _runtime(self):
        try:
            import torch
            from diffusers import DiffusionPipeline
        except ImportError as exc:
            raise RuntimeError(
                "local semantic editing requires optional dependencies: "
                "pip install -e '.[semantic]'"
            ) from exc
        return torch, DiffusionPipeline

    def _device(self, torch) -> str:
        configured = self.settings.semantic_device
        if configured != "auto":
            return configured
        if torch.cuda.is_available():
            return "cuda"
        if getattr(torch.backends, "mps", None) and torch.backends.mps.is_available():
            return "mps"
        return "cpu"

    def _pipeline(self):
        torch, DiffusionPipeline = self._runtime()
        model_id = self.settings.semantic_image_model.strip()
        if not model_id:
            raise RuntimeError("COSMOS_SEMANTIC_IMAGE_MODEL is empty")
        device = self._device(torch)
        key = (model_id, device)
        cached = _DIFFUSERS_PIPELINES.get(key)
        if cached is not None:
            return torch, cached, device

        dtype = torch.float32
        if device == "cuda":
            dtype = torch.bfloat16 if torch.cuda.is_bf16_supported() else torch.float16
        elif device == "mps":
            dtype = torch.float16
        try:
            pipe = DiffusionPipeline.from_pretrained(model_id, torch_dtype=dtype)
            pipe.to(device)
        except Exception as exc:
            raise RuntimeError(
                f"could not load semantic image model {model_id!r}; ensure the model is accessible "
                "and enough RAM/VRAM/disk space is available"
            ) from exc
        _DIFFUSERS_PIPELINES[key] = pipe
        return torch, pipe, device

    def edit_image(self, job: EditImageJob) -> Path:
        _clamp_strength(job.strength)
        try:
            from PIL import Image
        except ImportError as exc:
            raise RuntimeError("Pillow is required for semantic image editing") from exc

        torch, pipe, _device = self._pipeline()
        job.output.parent.mkdir(parents=True, exist_ok=True)
        with Image.open(job.source) as opened:
            image = opened.convert("RGB")
        signature = inspect.signature(pipe.__call__)
        parameters = signature.parameters
        kwargs: dict[str, Any] = {"prompt": job.prompt}
        if "image" in parameters:
            kwargs["image"] = image
        else:
            raise RuntimeError("configured Diffusers pipeline does not accept an input image")
        if job.negative_prompt and "negative_prompt" in parameters:
            kwargs["negative_prompt"] = job.negative_prompt
        if "strength" in parameters:
            kwargs["strength"] = float(job.strength)
        if "num_inference_steps" in parameters:
            kwargs["num_inference_steps"] = int(self.settings.semantic_steps)
        seed = _seed_from_job(job.prompt, job.state, job.seed)
        if "generator" in parameters:
            kwargs["generator"] = torch.Generator(device="cpu").manual_seed(seed)
        if job.mask and "mask_image" in parameters:
            with Image.open(job.mask) as mask_opened:
                kwargs["mask_image"] = mask_opened.convert("L")
        try:
            response = pipe(**kwargs)
            images = getattr(response, "images", None)
            if not images:
                raise RuntimeError("semantic pipeline returned no images")
            result = images[0]
            if not hasattr(result, "save"):
                raise RuntimeError("semantic pipeline returned a non-image result")
            if job.output.suffix.lower() in {".jpg", ".jpeg"}:
                result = result.convert("RGB")
            result.save(job.output)
        except RuntimeError:
            raise
        except Exception as exc:
            raise RuntimeError(f"semantic image edit failed: {exc}") from exc
        return job.output

    def _encode_chunk(self, ffmpeg: str, frame_dir: Path, fps: float, output: Path) -> None:
        command = [
            ffmpeg,
            "-y",
            "-framerate",
            f"{fps:.6f}",
            "-i",
            str(frame_dir / "edited-%08d.png"),
            "-c:v",
            "libx264",
            "-preset",
            "veryfast",
            "-crf",
            "19",
            "-pix_fmt",
            "yuv420p",
            str(output),
        ]
        subprocess.run(command, check=True, capture_output=True)

    def edit_video(self, job: EditVideoJob) -> Path:
        _clamp_strength(job.strength)
        blend = _clamp_temporal(job.temporal_blend)
        chunk_seconds = float(job.chunk_seconds)
        if chunk_seconds <= 0:
            raise ValueError("chunk_seconds must be positive")
        try:
            from PIL import Image
        except ImportError as exc:
            raise RuntimeError("Pillow is required for semantic video editing") from exc

        metadata = _probe_video(job.source)
        ffmpeg = shutil.which(self.settings.ffmpeg) or self.settings.ffmpeg
        fps = float(metadata["fps"])
        duration = float(metadata["duration"])
        base_seed = _seed_from_job(job.prompt, job.state, job.seed)
        job.output.parent.mkdir(parents=True, exist_ok=True)

        with tempfile.TemporaryDirectory(prefix="cosmos-edit-video-") as temp_name:
            root = Path(temp_name)
            chunks: list[Path] = []
            previous_frame = None
            global_frame = 0
            start = 0.0
            chunk_index = 0
            while start < duration - 1e-6:
                current_duration = min(chunk_seconds, duration - start)
                chunk_dir = root / f"chunk-{chunk_index:05d}"
                input_dir = chunk_dir / "input"
                output_dir = chunk_dir / "output"
                input_dir.mkdir(parents=True)
                output_dir.mkdir(parents=True)
                extract = [
                    ffmpeg,
                    "-y",
                    "-ss",
                    f"{start:.6f}",
                    "-t",
                    f"{current_duration:.6f}",
                    "-i",
                    str(job.source),
                    "-map",
                    "0:v:0",
                    "-vsync",
                    "0",
                    str(input_dir / "frame-%08d.png"),
                ]
                try:
                    subprocess.run(extract, check=True, capture_output=True)
                except subprocess.CalledProcessError as exc:
                    stderr = exc.stderr.decode("utf-8", errors="replace")[-3000:]
                    raise RuntimeError(f"semantic video frame extraction failed: {stderr}") from exc

                frames = sorted(input_dir.glob("frame-*.png"))
                if not frames:
                    break
                for local_index, frame in enumerate(frames, start=1):
                    edited_path = output_dir / f"edited-{local_index:08d}.png"
                    frame_seed = base_seed if job.style_lock else (base_seed + global_frame) & 0x7FFFFFFF
                    frame_prompt = job.prompt
                    if not job.style_lock:
                        frame_prompt = f"{job.prompt}\nContinuity frame {global_frame}."
                    self.edit_image(
                        EditImageJob(
                            source=frame,
                            output=edited_path,
                            prompt=frame_prompt,
                            negative_prompt=job.negative_prompt,
                            strength=job.strength,
                            preserve_subject=job.preserve_subject,
                            state=job.state,
                            seed=frame_seed,
                        )
                    )
                    if previous_frame is not None and blend > 0:
                        with Image.open(edited_path) as current:
                            current_rgb = current.convert("RGB")
                        previous_rgb = previous_frame.resize(current_rgb.size).convert("RGB")
                        smoothed = Image.blend(current_rgb, previous_rgb, blend)
                        smoothed.save(edited_path)
                        previous_frame = smoothed.copy()
                    else:
                        with Image.open(edited_path) as current:
                            previous_frame = current.convert("RGB").copy()
                    global_frame += 1

                chunk_video = root / f"edited-chunk-{chunk_index:05d}.mp4"
                try:
                    self._encode_chunk(ffmpeg, output_dir, fps, chunk_video)
                except subprocess.CalledProcessError as exc:
                    stderr = exc.stderr.decode("utf-8", errors="replace")[-3000:]
                    raise RuntimeError(f"semantic video chunk encoding failed: {stderr}") from exc
                chunks.append(chunk_video)
                start += current_duration
                chunk_index += 1

            if not chunks:
                raise RuntimeError("semantic video editor produced no chunks")
            concat_list = root / "chunks.txt"
            concat_list.write_text(
                "".join(f"file '{path.as_posix()}'\n" for path in chunks),
                encoding="utf-8",
            )
            video_only = root / "video-only.mp4"
            concat = [
                ffmpeg,
                "-y",
                "-f",
                "concat",
                "-safe",
                "0",
                "-i",
                str(concat_list),
                "-c",
                "copy",
                str(video_only),
            ]
            try:
                subprocess.run(concat, check=True, capture_output=True)
            except subprocess.CalledProcessError:
                concat = [
                    ffmpeg,
                    "-y",
                    "-f",
                    "concat",
                    "-safe",
                    "0",
                    "-i",
                    str(concat_list),
                    "-c:v",
                    "libx264",
                    "-pix_fmt",
                    "yuv420p",
                    str(video_only),
                ]
                subprocess.run(concat, check=True, capture_output=True)

            if job.preserve_audio:
                mux = [
                    ffmpeg,
                    "-y",
                    "-i",
                    str(video_only),
                    "-i",
                    str(job.source),
                    "-map",
                    "0:v:0",
                    "-map",
                    "1:a?",
                    "-c:v",
                    "copy",
                    "-c:a",
                    "aac",
                    "-b:a",
                    "192k",
                    "-shortest",
                    "-movflags",
                    "+faststart",
                    str(job.output),
                ]
                subprocess.run(mux, check=True, capture_output=True)
            else:
                shutil.copy2(video_only, job.output)
        return job.output


class HttpEditProvider:
    name = "http"

    def __init__(self, settings: Settings):
        self.settings = settings
        self.endpoint = settings.edit_endpoint.rstrip("/")
        if not self.endpoint:
            raise RuntimeError("HTTP edit provider requires COSMOS_EDIT_ENDPOINT")

    def _edit(self, kind: str, job: EditImageJob | EditVideoJob) -> Path:
        try:
            import httpx
        except ImportError as exc:
            raise RuntimeError("HTTP editing requires httpx: pip install -e '.[media]'") from exc

        job.output.parent.mkdir(parents=True, exist_ok=True)
        fields = {
            "prompt": job.prompt,
            "negative_prompt": job.negative_prompt,
            "strength": str(job.strength),
            "preserve_subject": "true" if job.preserve_subject else "false",
            "state": json.dumps(job.state or []),
        }
        if isinstance(job, EditVideoJob):
            fields.update(
                {
                    "preserve_audio": "true" if job.preserve_audio else "false",
                    "chunk_seconds": str(job.chunk_seconds),
                    "style_lock": "true" if job.style_lock else "false",
                    "temporal_blend": str(job.temporal_blend),
                }
            )
        with ExitStack() as stack:
            source_handle = stack.enter_context(job.source.open("rb"))
            files: dict[str, Any] = {
                "file": (job.source.name, source_handle, "application/octet-stream")
            }
            if isinstance(job, EditImageJob) and job.mask:
                mask_handle = stack.enter_context(job.mask.open("rb"))
                files["mask"] = (job.mask.name, mask_handle, "application/octet-stream")
            response = httpx.post(
                f"{self.endpoint}/edit/{kind}",
                data=fields,
                files=files,
                timeout=self.settings.media_timeout,
            )
        response.raise_for_status()
        content_type = response.headers.get("content-type", "")
        if "application/json" not in content_type:
            job.output.write_bytes(response.content)
            return job.output

        payload: dict[str, Any] = response.json()
        if payload.get("data_base64"):
            job.output.write_bytes(base64.b64decode(str(payload["data_base64"])))
            return job.output
        if payload.get("output_path"):
            source = Path(str(payload["output_path"]))
            if not source.exists():
                raise RuntimeError(f"HTTP editor returned missing output_path: {source}")
            shutil.copy2(source, job.output)
            return job.output
        if payload.get("url"):
            downloaded = httpx.get(str(payload["url"]), timeout=self.settings.media_timeout)
            downloaded.raise_for_status()
            job.output.write_bytes(downloaded.content)
            return job.output
        raise RuntimeError("HTTP editor JSON must contain data_base64, output_path, or url")

    def edit_image(self, job: EditImageJob) -> Path:
        return self._edit("image", job)

    def edit_video(self, job: EditVideoJob) -> Path:
        return self._edit("video", job)


def make_edit_provider(settings: Settings, renderer: str) -> EditProvider:
    chosen = renderer.strip().lower()
    if chosen == "native":
        return NativeEditProvider(settings)
    if chosen == "http":
        return HttpEditProvider(settings)
    if chosen == "diffusers":
        return DiffusersEditProvider(settings)
    raise ValueError(f"unknown edit renderer: {chosen!r}")
