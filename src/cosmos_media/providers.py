from __future__ import annotations

from dataclasses import dataclass
import base64
import json
import math
from pathlib import Path
import random
import shutil
import subprocess
import tempfile
from typing import Any, Protocol

from .config import Settings
from .native_renderer import render_native_image


@dataclass(slots=True)
class ImageJob:
    prompt: str
    seed: int
    width: int
    height: int
    state: list[float]
    output: Path
    context: str = ""


@dataclass(slots=True)
class VideoJob:
    prompt: str
    seed: int
    width: int
    height: int
    fps: int
    duration: float
    state: list[float]
    output: Path
    context: str = ""
    continuity: dict[str, Any] | None = None


class MediaProvider(Protocol):
    name: str

    def generate_image(self, job: ImageJob) -> Path: ...

    def generate_video(self, job: VideoJob) -> Path: ...


class NativeProvider:
    """First-party COSMOS renderer.

    Images and animation frames are synthesized entirely by code in this
    repository from prompt/context, seed and CST state. No remote media model,
    ComfyUI server, Diffusers pipeline or hosted image API is required.
    """

    name = "native"

    def __init__(self, settings: Settings):
        self.settings = settings

    def generate_image(self, job: ImageJob) -> Path:
        job.output.parent.mkdir(parents=True, exist_ok=True)
        image = render_native_image(
            job.prompt,
            job.context,
            job.seed,
            job.state,
            job.width,
            job.height,
            phase=0.0,
        )
        image.save(job.output)
        return job.output

    def generate_video(self, job: VideoJob) -> Path:
        job.output.parent.mkdir(parents=True, exist_ok=True)
        ffmpeg = shutil.which(self.settings.ffmpeg) or self.settings.ffmpeg
        # Bound internal synthesis cadence while preserving requested output FPS.
        # This keeps long timelines practical without retaining frames in RAM.
        synth_fps = max(2, min(job.fps, 8))
        frame_count = max(1, int(math.ceil(job.duration * synth_fps)))
        continuity = job.continuity or {}
        global_start = float(continuity.get("start", 0.0))

        with tempfile.TemporaryDirectory(prefix="cosmos-native-") as temp_dir:
            frames = Path(temp_dir)
            for index in range(frame_count):
                local_t = index / synth_fps
                phase = global_start + local_t
                image = render_native_image(
                    job.prompt,
                    job.context,
                    job.seed,
                    job.state,
                    job.width,
                    job.height,
                    phase=phase,
                )
                image.save(frames / f"frame-{index:06d}.png")

            command = [
                ffmpeg,
                "-y",
                "-framerate",
                str(synth_fps),
                "-i",
                str(frames / "frame-%06d.png"),
                "-t",
                f"{job.duration:.6f}",
                "-r",
                str(job.fps),
                "-vf",
                "format=yuv420p",
                "-c:v",
                "libx264",
                "-preset",
                "veryfast",
                "-movflags",
                "+faststart",
                str(job.output),
            ]
            try:
                subprocess.run(command, check=True, capture_output=True)
            except FileNotFoundError as exc:
                raise RuntimeError(
                    "FFmpeg was not found. Install ffmpeg or set COSMOS_FFMPEG."
                ) from exc
            except subprocess.CalledProcessError as exc:
                stderr = exc.stderr.decode("utf-8", errors="replace")[-2500:]
                raise RuntimeError(f"COSMOS native FFmpeg encode failed: {stderr}") from exc
        return job.output


class ProceduralProvider:
    """Tiny deterministic diagnostic renderer used for plumbing tests."""

    name = "procedural"

    def __init__(self, settings: Settings):
        self.settings = settings

    def _image(self, job: ImageJob):
        try:
            from PIL import Image, ImageDraw, ImageFont
        except ImportError as exc:
            raise RuntimeError(
                "Pillow is required for procedural media: pip install -e '.[media]'"
            ) from exc

        rng = random.Random(job.seed)
        image = Image.new(
            "RGB",
            (job.width, job.height),
            (rng.randrange(8, 45), rng.randrange(8, 45), rng.randrange(20, 70)),
        )
        draw = ImageDraw.Draw(image, "RGBA")
        count = max(18, min(80, int((job.width * job.height) / 25000)))
        for index in range(count):
            x = rng.randrange(0, max(1, job.width))
            y = rng.randrange(0, max(1, job.height))
            radius = rng.randrange(max(5, job.width // 80), max(8, job.width // 12))
            state_value = job.state[index % len(job.state)] if job.state else 0.0
            alpha = int(45 + abs(state_value) * 130)
            color = (
                rng.randrange(30, 256),
                rng.randrange(30, 256),
                rng.randrange(30, 256),
                alpha,
            )
            draw.ellipse(
                (x - radius, y - radius, x + radius, y + radius), fill=color
            )

        panel_h = min(job.height // 3, 230)
        draw.rectangle(
            (0, job.height - panel_h, job.width, job.height), fill=(0, 0, 0, 160)
        )
        font = ImageFont.load_default()
        wrapped = _wrap_text(job.prompt, max_chars=max(24, job.width // 12))
        state_text = "CST " + " ".join(f"{v:+.2f}" for v in job.state[:6])
        draw.multiline_text(
            (24, job.height - panel_h + 20),
            wrapped,
            font=font,
            fill=(255, 255, 255, 240),
            spacing=5,
        )
        draw.text(
            (24, job.height - 28),
            state_text,
            font=font,
            fill=(190, 220, 255, 220),
        )
        return image

    def generate_image(self, job: ImageJob) -> Path:
        job.output.parent.mkdir(parents=True, exist_ok=True)
        image = self._image(job)
        image.save(job.output)
        return job.output

    def generate_video(self, job: VideoJob) -> Path:
        job.output.parent.mkdir(parents=True, exist_ok=True)
        ffmpeg = shutil.which(self.settings.ffmpeg) or self.settings.ffmpeg
        still = job.output.with_suffix(".source.png")
        image_job = ImageJob(
            prompt=job.prompt,
            seed=job.seed,
            width=job.width,
            height=job.height,
            state=job.state,
            output=still,
            context=job.context,
        )
        self.generate_image(image_job)
        command = [
            ffmpeg,
            "-y",
            "-loop",
            "1",
            "-i",
            str(still),
            "-t",
            f"{job.duration:.6f}",
            "-r",
            str(job.fps),
            "-vf",
            "format=yuv420p",
            "-c:v",
            "libx264",
            "-preset",
            "veryfast",
            "-movflags",
            "+faststart",
            str(job.output),
        ]
        try:
            subprocess.run(command, check=True, capture_output=True)
        except FileNotFoundError as exc:
            raise RuntimeError(
                "FFmpeg was not found. Install ffmpeg or set COSMOS_FFMPEG."
            ) from exc
        except subprocess.CalledProcessError as exc:
            stderr = exc.stderr.decode("utf-8", errors="replace")[-2000:]
            raise RuntimeError(f"FFmpeg failed: {stderr}") from exc
        finally:
            still.unlink(missing_ok=True)
        return job.output


class HTTPProvider:
    """Language-neutral provider bridge for attaching any external renderer."""

    name = "http"

    def __init__(self, settings: Settings):
        self.settings = settings

    def _post(self, route: str, payload: dict[str, Any], destination: Path) -> Path:
        try:
            import httpx
        except ImportError as exc:
            raise RuntimeError(
                "httpx is required for HTTP providers: pip install -e '.[media]'"
            ) from exc
        destination.parent.mkdir(parents=True, exist_ok=True)
        with httpx.Client(timeout=self.settings.media_timeout) as client:
            response = client.post(f"{self.settings.media_endpoint}{route}", json=payload)
            response.raise_for_status()
            ctype = response.headers.get("content-type", "")
            if (
                ctype.startswith("image/")
                or ctype.startswith("video/")
                or ctype == "application/octet-stream"
            ):
                destination.write_bytes(response.content)
                return destination
            data = response.json()
            if data.get("data_base64"):
                destination.write_bytes(base64.b64decode(data["data_base64"]))
                return destination
            if data.get("path"):
                source = Path(data["path"])
                if not source.exists():
                    raise RuntimeError(
                        f"Provider returned missing shared path: {source}"
                    )
                shutil.copy2(source, destination)
                return destination
            if data.get("url"):
                downloaded = client.get(data["url"])
                downloaded.raise_for_status()
                destination.write_bytes(downloaded.content)
                return destination
            raise RuntimeError(
                f"Provider returned no supported output field: {json.dumps(data)[:500]}"
            )

    def generate_image(self, job: ImageJob) -> Path:
        return self._post(
            "/generate/image",
            {
                "prompt": job.prompt,
                "context": job.context,
                "seed": job.seed,
                "width": job.width,
                "height": job.height,
                "state": job.state,
            },
            job.output,
        )

    def generate_video(self, job: VideoJob) -> Path:
        return self._post(
            "/generate/video",
            {
                "prompt": job.prompt,
                "context": job.context,
                "seed": job.seed,
                "width": job.width,
                "height": job.height,
                "fps": job.fps,
                "duration": job.duration,
                "state": job.state,
                "continuity": job.continuity or {},
            },
            job.output,
        )


def make_provider(settings: Settings) -> MediaProvider:
    if settings.provider == "native":
        return NativeProvider(settings)
    if settings.provider == "procedural":
        return ProceduralProvider(settings)
    if settings.provider == "http":
        return HTTPProvider(settings)
    raise ValueError(
        f"Unknown COSMOS_MEDIA_PROVIDER={settings.provider!r}. "
        "Supported built-ins: native, procedural, http"
    )


def _wrap_text(text: str, max_chars: int) -> str:
    words = text.split()
    lines: list[str] = []
    line: list[str] = []
    current = 0
    for word in words:
        extra = len(word) + (1 if line else 0)
        if line and current + extra > max_chars:
            lines.append(" ".join(line))
            line = [word]
            current = len(word)
        else:
            line.append(word)
            current += extra
    if line:
        lines.append(" ".join(line))
    return "\n".join(lines[:8])
