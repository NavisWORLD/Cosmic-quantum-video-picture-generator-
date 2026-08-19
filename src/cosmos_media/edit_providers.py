from __future__ import annotations

from dataclasses import dataclass
import base64
import hashlib
from pathlib import Path
import shutil
import subprocess
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


class EditProvider(Protocol):
    name: str

    def edit_image(self, job: EditImageJob) -> Path: ...

    def edit_video(self, job: EditVideoJob) -> Path: ...


def _clamp_strength(value: float) -> float:
    number = float(value)
    if not 0.0 <= number <= 1.0:
        raise ValueError("edit strength must be between 0 and 1")
    return number


def _prompt_tint(prompt: str) -> tuple[int, int, int]:
    digest = hashlib.sha256(prompt.strip().lower().encode("utf-8")).digest()
    # Keep the tint in a visible but not crushing range.
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
    # A tiny prompt-hash hue rotation means generic prompts still create a
    # deterministic visible edit rather than silently copying the source.
    digest = hashlib.sha256(text.encode("utf-8")).digest()
    hue = ((digest[0] / 255.0) - 0.5) * 10.0 * strength
    filters.append(f"hue=h={hue:.4f}")
    return ",".join(filters)


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
            # Blend the styled result with the source so strength has a clear,
            # intuitive meaning and preserve-subject remains conservative.
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
        job.output.parent.mkdir(parents=True, exist_ok=True)
        ffmpeg = shutil.which(self.settings.ffmpeg) or self.settings.ffmpeg
        video_filter = prompt_video_filter(job.prompt, job.strength)
        command = [
            ffmpeg,
            "-y",
            "-i",
            str(job.source),
            "-map",
            "0:v:0",
        ]
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
            raise RuntimeError(
                "FFmpeg was not found. Install ffmpeg or set COSMOS_FFMPEG."
            ) from exc
        except subprocess.CalledProcessError as exc:
            stderr = exc.stderr.decode("utf-8", errors="replace")[-3000:]
            raise RuntimeError(f"COSMOS native video edit failed: {stderr}") from exc
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
            raise RuntimeError(
                "HTTP editing requires httpx: pip install -e '.[media]'"
            ) from exc

        job.output.parent.mkdir(parents=True, exist_ok=True)
        fields = {
            "prompt": job.prompt,
            "negative_prompt": job.negative_prompt,
            "strength": str(job.strength),
            "preserve_subject": "true" if job.preserve_subject else "false",
        }
        if isinstance(job, EditVideoJob):
            fields["preserve_audio"] = "true" if job.preserve_audio else "false"
        with job.source.open("rb") as handle:
            response = httpx.post(
                f"{self.endpoint}/edit/{kind}",
                data=fields,
                files={"file": (job.source.name, handle, "application/octet-stream")},
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
    raise ValueError(f"unknown edit renderer: {chosen!r}")
