from __future__ import annotations

from dataclasses import asdict, dataclass, replace
import json
from pathlib import Path
from typing import Any


COSMOS_MAIN_MODEL_ID = "cosmos-main"
COSMOS_MAIN_CONTROLLER_REPO = "phera-ra/QC67_cosmo"


@dataclass(frozen=True, slots=True)
class ModelSpec:
    id: str
    label: str
    controller_repo: str | None
    renderer: str
    capabilities: tuple[str, ...]
    description: str
    default: bool = False
    available: bool = True

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["capabilities"] = list(self.capabilities)
        return payload


class ModelRegistry:
    """Small persisted registry for COSMOS edit model selection.

    `cosmos-main` is a composite identity: QC67 is the controller/planner
    identity while an edit renderer performs the actual pixel/video transform.
    This distinction is surfaced in metadata so the system never claims the
    text-generation controller directly rendered media.
    """

    def __init__(
        self,
        home: str | Path,
        *,
        configured_default: str = COSMOS_MAIN_MODEL_ID,
        edit_renderer: str = "native",
        edit_endpoint: str = "",
    ) -> None:
        self.home = Path(home)
        self.edit_renderer = (edit_renderer or "native").strip().lower()
        self.edit_endpoint = edit_endpoint.strip()
        self._state_path = self.home / "state" / "model.json"
        self._specs: dict[str, ModelSpec] = {
            COSMOS_MAIN_MODEL_ID: ModelSpec(
                id=COSMOS_MAIN_MODEL_ID,
                label="COSMOS Main",
                controller_repo=COSMOS_MAIN_CONTROLLER_REPO,
                renderer="configured",
                capabilities=("image_edit", "video_edit", "continuity", "planning"),
                description=(
                    "Default COSMOS composite model: QC67 controller identity with "
                    "the configured visual edit renderer."
                ),
            ),
            "native-edit": ModelSpec(
                id="native-edit",
                label="COSMOS Native Edit",
                controller_repo=None,
                renderer="native",
                capabilities=("image_edit", "video_edit", "offline"),
                description="Offline Pillow/FFmpeg prompt-conditioned media editor.",
            ),
            "http-edit": ModelSpec(
                id="http-edit",
                label="External HTTP Edit Model",
                controller_repo=None,
                renderer="http",
                capabilities=("image_edit", "video_edit", "semantic_edit"),
                description="Bridge to a configured semantic image/video editing endpoint.",
                available=bool(self.edit_endpoint),
            ),
        }
        persisted = self._read_persisted_default()
        candidate = persisted or configured_default or COSMOS_MAIN_MODEL_ID
        self.default_id = candidate if candidate in self._specs else COSMOS_MAIN_MODEL_ID

    def _read_persisted_default(self) -> str | None:
        try:
            data = json.loads(self._state_path.read_text(encoding="utf-8"))
            value = str(data.get("default_model", "")).strip()
            return value or None
        except (FileNotFoundError, json.JSONDecodeError, OSError, TypeError, ValueError):
            return None

    def _write_persisted_default(self) -> None:
        self._state_path.parent.mkdir(parents=True, exist_ok=True)
        temp = self._state_path.with_suffix(".tmp")
        temp.write_text(
            json.dumps({"default_model": self.default_id}, indent=2),
            encoding="utf-8",
        )
        temp.replace(self._state_path)

    def get(self, model_id: str | None = None) -> ModelSpec:
        chosen = (model_id or self.default_id).strip().lower()
        spec = self._specs.get(chosen)
        if spec is None:
            raise ValueError(f"unknown model: {chosen!r}")
        return replace(spec, default=chosen == self.default_id)

    def resolve(self, model_id: str | None, capability: str) -> ModelSpec:
        spec = self.get(model_id)
        if capability not in spec.capabilities:
            raise ValueError(f"model {spec.id!r} does not support {capability}")
        if spec.renderer == "http" and not self.edit_endpoint:
            raise RuntimeError(
                "http-edit requires COSMOS_EDIT_ENDPOINT to point at a compatible edit service"
            )
        return spec

    def set_default(self, model_id: str) -> ModelSpec:
        spec = self.get(model_id)
        self.default_id = spec.id
        self._write_persisted_default()
        return self.get(spec.id)

    def renderer_for(self, spec: ModelSpec) -> str:
        if spec.renderer == "configured":
            renderer = self.edit_renderer or "native"
            if renderer not in {"native", "http"}:
                raise ValueError(f"unsupported COSMOS_EDIT_RENDERER: {renderer!r}")
            if renderer == "http" and not self.edit_endpoint:
                raise RuntimeError(
                    "COSMOS Main is configured for the HTTP renderer but COSMOS_EDIT_ENDPOINT is empty"
                )
            return renderer
        return spec.renderer

    def list(self) -> list[dict[str, Any]]:
        result: list[dict[str, Any]] = []
        for model_id in self._specs:
            spec = self.get(model_id)
            payload = spec.to_dict()
            payload["active_renderer"] = self.renderer_for(spec) if spec.available or spec.id == COSMOS_MAIN_MODEL_ID else spec.renderer
            result.append(payload)
        return result

    def status(self) -> dict[str, Any]:
        default = self.get()
        return {
            "default_model": self.default_id,
            "default_label": default.label,
            "controller_repo": default.controller_repo,
            "renderer": self.renderer_for(default),
            "models": self.list(),
        }
