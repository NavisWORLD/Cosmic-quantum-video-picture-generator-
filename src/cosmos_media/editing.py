from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import uuid
from typing import Any

from .config import Settings
from .edit_providers import EditImageJob, EditVideoJob, make_edit_provider
from .models import ModelRegistry
from .provenance import canonical_json, sha256_text
from .synaptic import SynapticCore


IMAGE_SUFFIXES = {".png", ".jpg", ".jpeg", ".webp"}
VIDEO_SUFFIXES = {".mp4", ".mov", ".webm", ".m4v"}


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(path.suffix + ".tmp")
    temp.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    temp.replace(path)


def _parse_rate(value: str | None) -> float | None:
    text = str(value or "").strip()
    if not text:
        return None
    try:
        if "/" in text:
            numerator, denominator = text.split("/", 1)
            denominator_v = float(denominator)
            return float(numerator) / denominator_v if denominator_v else None
        return float(text)
    except (TypeError, ValueError, ZeroDivisionError):
        return None


class EditingService:
    """Upload + prompt-edit service shared by CLI, API, UI and JSONL bridge."""

    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or Settings()
        self.settings.ensure_dirs()
        self.registry = ModelRegistry(
            self.settings.home,
            configured_default=self.settings.default_model,
            edit_renderer=self.settings.edit_renderer,
            image_edit_renderer=self.settings.image_edit_renderer,
            video_edit_renderer=self.settings.video_edit_renderer,
            edit_endpoint=self.settings.edit_endpoint,
            semantic_image_model=self.settings.semantic_image_model,
        )
        self._synaptic_path = self.settings.home / "state" / "editing-synaptic.json"
        self.synaptic = self._load_synaptic()

    @property
    def _assets_dir(self) -> Path:
        return self.settings.home / "assets"

    @property
    def _jobs_dir(self) -> Path:
        return self.settings.home / "edit_jobs"

    @property
    def _receipts_dir(self) -> Path:
        return self.settings.home / "receipts"

    def _load_synaptic(self) -> SynapticCore:
        try:
            payload = json.loads(self._synaptic_path.read_text(encoding="utf-8"))
            return SynapticCore.from_snapshot(payload)
        except (FileNotFoundError, json.JSONDecodeError, ValueError, TypeError, OSError):
            return SynapticCore.from_context("cosmos media editing continuity")

    def _save_synaptic(self) -> None:
        _write_json(self._synaptic_path, self.synaptic.snapshot())

    def _classify_suffix(self, suffix: str) -> str:
        normalized = suffix.lower()
        if normalized in IMAGE_SUFFIXES:
            return "image"
        if normalized in VIDEO_SUFFIXES:
            return "video"
        allowed = ", ".join(sorted(IMAGE_SUFFIXES | VIDEO_SUFFIXES))
        raise ValueError(f"unsupported media type {normalized or '<none>'}; allowed: {allowed}")

    def _validate_size(self, size: int) -> None:
        if size <= 0:
            raise ValueError("uploaded media must not be empty")
        limit = int(self.settings.max_upload_mb) * 1024 * 1024
        if size > limit:
            raise ValueError(
                f"upload is {size / (1024 * 1024):.1f} MB; maximum is {self.settings.max_upload_mb} MB"
            )

    def _inspect_image(self, path: Path) -> dict[str, Any]:
        try:
            from PIL import Image, UnidentifiedImageError
        except ImportError as exc:
            raise RuntimeError("Pillow is required to validate image uploads") from exc
        try:
            with Image.open(path) as opened:
                opened.verify()
            with Image.open(path) as opened:
                return {
                    "width": int(opened.width),
                    "height": int(opened.height),
                    "format": str(opened.format or path.suffix.lstrip(".")).upper(),
                    "mode": str(opened.mode),
                }
        except (UnidentifiedImageError, OSError, ValueError) as exc:
            raise ValueError(f"invalid image upload: {path.name}") from exc

    def _inspect_video(self, path: Path) -> dict[str, Any]:
        ffprobe = shutil.which("ffprobe")
        if not ffprobe:
            return {}
        command = [
            ffprobe,
            "-v",
            "error",
            "-select_streams",
            "v:0",
            "-show_entries",
            "stream=width,height,avg_frame_rate,codec_name:format=duration,format_name",
            "-of",
            "json",
            str(path),
        ]
        try:
            result = subprocess.run(command, check=True, capture_output=True, text=True)
            payload = json.loads(result.stdout or "{}")
        except (subprocess.CalledProcessError, json.JSONDecodeError, OSError) as exc:
            raise ValueError(f"invalid video upload: {path.name}") from exc
        streams = payload.get("streams") or []
        if not streams:
            raise ValueError(f"invalid video upload: {path.name}")
        stream = streams[0]
        format_data = payload.get("format") or {}
        metadata: dict[str, Any] = {
            "width": int(stream.get("width") or 0),
            "height": int(stream.get("height") or 0),
            "codec": str(stream.get("codec_name") or ""),
            "format": str(format_data.get("format_name") or path.suffix.lstrip(".")),
        }
        fps = _parse_rate(stream.get("avg_frame_rate"))
        if fps is not None:
            metadata["fps"] = fps
        try:
            duration = float(format_data.get("duration") or 0.0)
            if duration > 0:
                metadata["duration"] = duration
        except (TypeError, ValueError):
            pass
        return metadata

    def _inspect_media(self, path: Path, kind: str) -> dict[str, Any]:
        return self._inspect_image(path) if kind == "image" else self._inspect_video(path)

    def _asset_meta_path(self, asset_id: str) -> Path:
        return self._assets_dir / f"{asset_id}.json"

    def _record_asset(
        self,
        *,
        asset_id: str,
        kind: str,
        original_name: str,
        path: Path,
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "asset_id": asset_id,
            "kind": kind,
            "original_name": original_name,
            "path": str(path),
            "size": path.stat().st_size,
            "sha256": _sha256_file(path),
            "created_at": _utc_now(),
        }
        payload.update(metadata or {})
        _write_json(self._asset_meta_path(asset_id), payload)
        return payload

    def import_file(self, source: str | Path) -> dict[str, Any]:
        path = Path(source)
        if not path.is_file():
            raise ValueError(f"input media does not exist: {path}")
        suffix = path.suffix.lower()
        kind = self._classify_suffix(suffix)
        self._validate_size(path.stat().st_size)
        metadata = self._inspect_media(path, kind)
        asset_id = uuid.uuid4().hex
        destination = self._assets_dir / f"{asset_id}{suffix}"
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(path, destination)
        return self._record_asset(
            asset_id=asset_id,
            kind=kind,
            original_name=path.name,
            path=destination,
            metadata=metadata,
        )

    def store_upload(self, filename: str, data: bytes) -> dict[str, Any]:
        suffix = Path(filename or "upload").suffix.lower()
        kind = self._classify_suffix(suffix)
        self._validate_size(len(data))
        asset_id = uuid.uuid4().hex
        destination = self._assets_dir / f"{asset_id}{suffix}"
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(data)
        try:
            metadata = self._inspect_media(destination, kind)
        except Exception:
            destination.unlink(missing_ok=True)
            raise
        return self._record_asset(
            asset_id=asset_id,
            kind=kind,
            original_name=Path(filename).name or f"upload{suffix}",
            path=destination,
            metadata=metadata,
        )

    def asset(self, asset_id: str) -> dict[str, Any]:
        safe_id = str(asset_id).strip()
        if not safe_id or any(ch not in "0123456789abcdef" for ch in safe_id.lower()):
            raise ValueError("invalid asset id")
        path = self._asset_meta_path(safe_id)
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except FileNotFoundError as exc:
            raise ValueError(f"unknown asset: {safe_id}") from exc
        media_path = Path(str(payload.get("path", "")))
        if not media_path.is_file():
            raise ValueError(f"asset data is missing: {safe_id}")
        return payload

    def _job_path(self, job_id: str) -> Path:
        return self._jobs_dir / f"{job_id}.json"

    def _write_job(self, payload: dict[str, Any]) -> None:
        payload["updated_at"] = _utc_now()
        _write_json(self._job_path(str(payload["job_id"])), payload)

    def job(self, job_id: str) -> dict[str, Any]:
        try:
            return json.loads(self._job_path(job_id).read_text(encoding="utf-8"))
        except FileNotFoundError as exc:
            raise ValueError(f"unknown edit job: {job_id}") from exc

    def models(self) -> dict[str, Any]:
        return self.registry.status()

    def set_default_model(self, model_id: str) -> dict[str, Any]:
        selected = self.registry.set_default(model_id)
        image_renderer = (
            self.registry.renderer_for(selected, "image_edit")
            if "image_edit" in selected.capabilities
            else None
        )
        video_renderer = (
            self.registry.renderer_for(selected, "video_edit")
            if "video_edit" in selected.capabilities
            else None
        )
        return {
            "default_model": selected.id,
            "model": selected.to_dict(),
            "renderer": image_renderer if image_renderer == video_renderer else "mixed",
            "renderers": {"image_edit": image_renderer, "video_edit": video_renderer},
        }

    def _begin_job(
        self,
        *,
        kind: str,
        asset: dict[str, Any],
        prompt: str,
        model_id: str | None,
        strength: float,
        output: str | Path | None,
    ) -> tuple[dict[str, Any], Any, str, Path]:
        if not prompt.strip():
            raise ValueError("edit prompt must not be empty")
        strength_v = float(strength)
        if not 0.0 <= strength_v <= 1.0:
            raise ValueError("edit strength must be between 0 and 1")
        if asset["kind"] != kind:
            raise ValueError(f"asset {asset['asset_id']} is {asset['kind']}, not {kind}")

        capability = f"{kind}_edit"
        spec = self.registry.resolve(model_id, capability)
        renderer = self.registry.renderer_for(spec, capability)
        job_id = f"edit-{kind}-{uuid.uuid4().hex[:16]}"
        if output is None:
            suffix = ".png" if kind == "image" else ".mp4"
            destination = Path("out") / "edits" / f"{job_id}{suffix}"
        else:
            destination = Path(output)
        destination.parent.mkdir(parents=True, exist_ok=True)
        job = {
            "job_id": job_id,
            "kind": kind,
            "status": "queued",
            "asset_id": asset["asset_id"],
            "source": asset["path"],
            "prompt_hash": sha256_text(prompt),
            "model": spec.id,
            "controller_repo": spec.controller_repo,
            "renderer": renderer,
            "strength": strength_v,
            "output": str(destination),
            "created_at": _utc_now(),
            "error": None,
        }
        self._write_job(job)
        return job, spec, renderer, destination

    def _pulse(self, kind: str, asset: dict[str, Any], prompt: str, model_id: str) -> dict[str, Any]:
        snapshot = self.synaptic.pulse(
            f"media-edit|{kind}|{model_id}|{asset['sha256']}|{prompt}",
            learn=True,
        )
        self._save_synaptic()
        return snapshot

    def _apply_mask(self, source: Path, edited: Path, mask: Path) -> Path:
        try:
            from PIL import Image
        except ImportError as exc:
            raise RuntimeError("Pillow is required for masked image editing") from exc
        with Image.open(source) as source_opened:
            source_has_alpha = "A" in source_opened.getbands()
            source_image = source_opened.convert("RGBA" if source_has_alpha else "RGB")
        with Image.open(edited) as edited_opened:
            edited_image = edited_opened.convert(source_image.mode).resize(source_image.size)
        with Image.open(mask) as mask_opened:
            mask_image = mask_opened.convert("L").resize(source_image.size)
        result = Image.composite(edited_image, source_image, mask_image)
        if edited.suffix.lower() in {".jpg", ".jpeg"}:
            result = result.convert("RGB")
        result.save(edited)
        return edited

    def _receipt(
        self,
        *,
        job: dict[str, Any],
        asset: dict[str, Any],
        prompt: str,
        state: dict[str, Any],
        output: Path,
        parameters: dict[str, Any],
    ) -> Path:
        payload: dict[str, Any] = {
            "protocol": "cosmos-media-edit/1",
            "job_id": job["job_id"],
            "kind": job["kind"],
            "asset_id": asset["asset_id"],
            "source_sha256": asset["sha256"],
            "prompt_hash": sha256_text(prompt),
            "state_hash": state["state_hash"],
            "model": job["model"],
            "controller_repo": job["controller_repo"],
            "renderer": job["renderer"],
            "parameters": parameters,
            "output": str(output),
            "output_sha256": _sha256_file(output),
            "created_at": _utc_now(),
        }
        payload["receipt_hash"] = sha256_text(canonical_json(payload))
        path = self._receipts_dir / f"{job['job_id']}.json"
        _write_json(path, payload)
        return path

    def edit_image(
        self,
        asset_id: str,
        prompt: str,
        output: str | Path | None = None,
        *,
        model: str | None = None,
        negative_prompt: str = "",
        strength: float = 0.5,
        preserve_subject: bool = True,
        mask_asset_id: str | None = None,
    ) -> dict[str, Any]:
        asset = self.asset(asset_id)
        mask_asset = self.asset(mask_asset_id) if mask_asset_id else None
        if mask_asset and mask_asset["kind"] != "image":
            raise ValueError("image edit mask must be an image asset")
        job, spec, renderer, destination = self._begin_job(
            kind="image",
            asset=asset,
            prompt=prompt,
            model_id=model,
            strength=strength,
            output=output,
        )
        job["status"] = "processing"
        if mask_asset:
            job["mask_asset_id"] = mask_asset["asset_id"]
        self._write_job(job)
        parameters = {
            "strength": float(strength),
            "preserve_subject": bool(preserve_subject),
            "negative_prompt_hash": sha256_text(negative_prompt),
            "mask_asset_id": mask_asset["asset_id"] if mask_asset else None,
            "mask_sha256": mask_asset["sha256"] if mask_asset else None,
        }
        try:
            state = self._pulse("image", asset, prompt, spec.id)
            provider = make_edit_provider(self.settings, renderer)
            mask_path = Path(mask_asset["path"]) if mask_asset else None
            rendered = provider.edit_image(
                EditImageJob(
                    source=Path(asset["path"]),
                    output=destination,
                    prompt=prompt,
                    negative_prompt=negative_prompt,
                    strength=float(strength),
                    preserve_subject=bool(preserve_subject),
                    state=list(state["values"]),
                    mask=mask_path,
                )
            )
            if mask_path:
                rendered = self._apply_mask(Path(asset["path"]), rendered, mask_path)
            receipt = self._receipt(
                job=job,
                asset=asset,
                prompt=prompt,
                state=state,
                output=rendered,
                parameters=parameters,
            )
            job.update({"status": "completed", "output": str(rendered), "receipt": str(receipt)})
            self._write_job(job)
            return {
                "output": str(rendered),
                "receipt": str(receipt),
                "job_id": job["job_id"],
                "model": spec.id,
                "controller_repo": spec.controller_repo,
                "renderer": renderer,
                "mask_asset_id": mask_asset["asset_id"] if mask_asset else None,
                "parameters": parameters,
                "state": {"step_index": state["step_index"], "state_hash": state["state_hash"]},
            }
        except Exception as exc:
            job.update({"status": "failed", "error": str(exc)})
            self._write_job(job)
            raise

    def edit_video(
        self,
        asset_id: str,
        prompt: str,
        output: str | Path | None = None,
        *,
        model: str | None = None,
        negative_prompt: str = "",
        strength: float = 0.45,
        preserve_subject: bool = True,
        preserve_audio: bool = True,
        chunk_seconds: float = 6.0,
        style_lock: bool = True,
        temporal_blend: float = 0.12,
    ) -> dict[str, Any]:
        if float(chunk_seconds) <= 0:
            raise ValueError("chunk_seconds must be positive")
        if not 0.0 <= float(temporal_blend) <= 1.0:
            raise ValueError("temporal_blend must be between 0 and 1")
        asset = self.asset(asset_id)
        job, spec, renderer, destination = self._begin_job(
            kind="video",
            asset=asset,
            prompt=prompt,
            model_id=model,
            strength=strength,
            output=output,
        )
        job["status"] = "processing"
        self._write_job(job)
        parameters = {
            "strength": float(strength),
            "preserve_subject": bool(preserve_subject),
            "preserve_audio": bool(preserve_audio),
            "chunk_seconds": float(chunk_seconds),
            "style_lock": bool(style_lock),
            "temporal_blend": float(temporal_blend),
            "negative_prompt_hash": sha256_text(negative_prompt),
        }
        try:
            state = self._pulse("video", asset, prompt, spec.id)
            provider = make_edit_provider(self.settings, renderer)
            rendered = provider.edit_video(
                EditVideoJob(
                    source=Path(asset["path"]),
                    output=destination,
                    prompt=prompt,
                    negative_prompt=negative_prompt,
                    strength=float(strength),
                    preserve_subject=bool(preserve_subject),
                    preserve_audio=bool(preserve_audio),
                    state=list(state["values"]),
                    chunk_seconds=float(chunk_seconds),
                    style_lock=bool(style_lock),
                    temporal_blend=float(temporal_blend),
                )
            )
            receipt = self._receipt(
                job=job,
                asset=asset,
                prompt=prompt,
                state=state,
                output=rendered,
                parameters=parameters,
            )
            job.update({"status": "completed", "output": str(rendered), "receipt": str(receipt)})
            self._write_job(job)
            return {
                "output": str(rendered),
                "receipt": str(receipt),
                "job_id": job["job_id"],
                "model": spec.id,
                "controller_repo": spec.controller_repo,
                "renderer": renderer,
                "parameters": parameters,
                "state": {"step_index": state["step_index"], "state_hash": state["state_hash"]},
            }
        except Exception as exc:
            job.update({"status": "failed", "error": str(exc)})
            self._write_job(job)
            raise
