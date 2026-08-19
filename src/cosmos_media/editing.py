from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import shutil
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


class EditingService:
    """Upload + prompt-edit service shared by CLI, API, UI and JSONL bridge."""

    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or Settings()
        self.settings.ensure_dirs()
        self.registry = ModelRegistry(
            self.settings.home,
            configured_default=self.settings.default_model,
            edit_renderer=self.settings.edit_renderer,
            edit_endpoint=self.settings.edit_endpoint,
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

    def _asset_meta_path(self, asset_id: str) -> Path:
        return self._assets_dir / f"{asset_id}.json"

    def _record_asset(self, *, asset_id: str, kind: str, original_name: str, path: Path) -> dict[str, Any]:
        payload = {
            "asset_id": asset_id,
            "kind": kind,
            "original_name": original_name,
            "path": str(path),
            "size": path.stat().st_size,
            "sha256": _sha256_file(path),
            "created_at": _utc_now(),
        }
        _write_json(self._asset_meta_path(asset_id), payload)
        return payload

    def import_file(self, source: str | Path) -> dict[str, Any]:
        path = Path(source)
        if not path.is_file():
            raise ValueError(f"input media does not exist: {path}")
        suffix = path.suffix.lower()
        kind = self._classify_suffix(suffix)
        self._validate_size(path.stat().st_size)
        asset_id = uuid.uuid4().hex
        destination = self._assets_dir / f"{asset_id}{suffix}"
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(path, destination)
        return self._record_asset(
            asset_id=asset_id,
            kind=kind,
            original_name=path.name,
            path=destination,
        )

    def store_upload(self, filename: str, data: bytes) -> dict[str, Any]:
        suffix = Path(filename or "upload").suffix.lower()
        kind = self._classify_suffix(suffix)
        self._validate_size(len(data))
        asset_id = uuid.uuid4().hex
        destination = self._assets_dir / f"{asset_id}{suffix}"
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(data)
        return self._record_asset(
            asset_id=asset_id,
            kind=kind,
            original_name=Path(filename).name or f"upload{suffix}",
            path=destination,
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
        return {
            "default_model": selected.id,
            "model": selected.to_dict(),
            "renderer": self.registry.renderer_for(selected),
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
        renderer = self.registry.renderer_for(spec)
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
    ) -> dict[str, Any]:
        asset = self.asset(asset_id)
        job, spec, renderer, destination = self._begin_job(
            kind="image",
            asset=asset,
            prompt=prompt,
            model_id=model,
            strength=strength,
            output=output,
        )
        job["status"] = "processing"
        self._write_job(job)
        try:
            state = self._pulse("image", asset, prompt, spec.id)
            provider = make_edit_provider(self.settings, renderer)
            rendered = provider.edit_image(
                EditImageJob(
                    source=Path(asset["path"]),
                    output=destination,
                    prompt=prompt,
                    negative_prompt=negative_prompt,
                    strength=float(strength),
                    preserve_subject=bool(preserve_subject),
                    state=list(state["values"]),
                )
            )
            receipt = self._receipt(
                job=job,
                asset=asset,
                prompt=prompt,
                state=state,
                output=rendered,
                parameters={
                    "strength": float(strength),
                    "preserve_subject": bool(preserve_subject),
                    "negative_prompt_hash": sha256_text(negative_prompt),
                },
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
    ) -> dict[str, Any]:
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
                )
            )
            receipt = self._receipt(
                job=job,
                asset=asset,
                prompt=prompt,
                state=state,
                output=rendered,
                parameters={
                    "strength": float(strength),
                    "preserve_subject": bool(preserve_subject),
                    "preserve_audio": bool(preserve_audio),
                    "negative_prompt_hash": sha256_text(negative_prompt),
                },
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
                "state": {"step_index": state["step_index"], "state_hash": state["state_hash"]},
            }
        except Exception as exc:
            job.update({"status": "failed", "error": str(exc)})
            self._write_job(job)
            raise
