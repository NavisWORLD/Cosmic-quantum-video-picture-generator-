from __future__ import annotations

from dataclasses import asdict, dataclass, replace
import importlib.util
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


def _detect_semantic_runtime() -> bool:
    return bool(importlib.util.find_spec("torch") and importlib.util.find_spec("diffusers"))


class ModelRegistry:
    """Persisted registry for COSMOS edit model selection.

    `cosmos-main` is a composite identity: QC67 is the controller/planner
    identity while a visual renderer performs the actual pixel/video transform.
    The distinction is surfaced in every status/result so COSMOS never claims a
    text-generation controller directly rendered media.
    """

    def __init__(
        self,
        home: str | Path,
        *,
        configured_default: str = COSMOS_MAIN_MODEL_ID,
        edit_renderer: str = "native",
        image_edit_renderer: str | None = None,
        video_edit_renderer: str | None = None,
        edit_endpoint: str = "",
        semantic_available: bool | None = None,
        semantic_image_model: str = "Qwen/Qwen-Image-Edit-2511",
    ) -> None:
        self.home = Path(home)
        self.edit_renderer = (edit_renderer or "native").strip().lower()
        self.image_edit_renderer = (image_edit_renderer or self.edit_renderer).strip().lower()
        self.video_edit_renderer = (video_edit_renderer or self.edit_renderer).strip().lower()
        self.edit_endpoint = edit_endpoint.strip()
        self.semantic_image_model = semantic_image_model.strip()
        self.semantic_available = _detect_semantic_runtime() if semantic_available is None else bool(semantic_available)
        self._state_path = self.home / "state" / "model.json"
        self._specs: dict[str, ModelSpec] = {
            COSMOS_MAIN_MODEL_ID: ModelSpec(
                id=COSMOS_MAIN_MODEL_ID,
                label="COSMOS Main",
                controller_repo=COSMOS_MAIN_CONTROLLER_REPO,
                renderer="configured",
                capabilities=("image_edit", "video_edit", "continuity", "planning"),
                description=(
                    "Default first-party COSMOS composite profile: QC67 controller/planning identity "
                    "plus the configured visual renderer."
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
            "diffusers-edit": ModelSpec(
                id="diffusers-edit",
                label="COSMOS Local Semantic Edit",
                controller_repo=None,
                renderer="diffusers",
                capabilities=(
                    "image_edit",
                    "video_edit",
                    "semantic_edit",
                    "framewise_video_edit",
                    "mask_composite",
                ),
                description=(
                    "Optional local semantic editor using a Diffusers image-edit pipeline; "
                    f"configured model: {self.semantic_image_model or '<unset>'}."
                ),
                available=self.semantic_available and bool(self.semantic_image_model),
            ),
            "http-edit": ModelSpec(
                id="http-edit",
                label="External HTTP Edit Model",
                controller_repo=None,
                renderer="http",
                capabilities=("image_edit", "video_edit", "semantic_edit", "mask_input"),
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

    def _validate_renderer(self, renderer: str) -> str:
        chosen = renderer.strip().lower()
        if chosen not in {"native", "http", "diffusers"}:
            raise ValueError(f"unsupported edit renderer: {chosen!r}")
        if chosen == "http" and not self.edit_endpoint:
            raise RuntimeError("HTTP editing requires COSMOS_EDIT_ENDPOINT")
        if chosen == "diffusers" and not self.semantic_available:
            raise RuntimeError(
                "local semantic editing requires the optional semantic stack: "
                "pip install -e '.[semantic]'"
            )
        if chosen == "diffusers" and not self.semantic_image_model:
            raise RuntimeError("local semantic editing requires COSMOS_SEMANTIC_IMAGE_MODEL")
        return chosen

    def renderer_for(self, spec: ModelSpec, capability: str | None = None) -> str:
        if spec.renderer == "configured":
            if capability == "image_edit":
                renderer = self.image_edit_renderer
            elif capability == "video_edit":
                renderer = self.video_edit_renderer
            else:
                renderer = self.edit_renderer
            return renderer.strip().lower()
        return spec.renderer

    def resolve(self, model_id: str | None, capability: str) -> ModelSpec:
        spec = self.get(model_id)
        if capability not in spec.capabilities:
            raise ValueError(f"model {spec.id!r} does not support {capability}")
        renderer = self.renderer_for(spec, capability)
        self._validate_renderer(renderer)
        if spec.id != COSMOS_MAIN_MODEL_ID and not spec.available:
            if spec.renderer == "http":
                raise RuntimeError("http-edit requires COSMOS_EDIT_ENDPOINT")
            if spec.renderer == "diffusers":
                raise RuntimeError(
                    "diffusers-edit is unavailable; install with: pip install -e '.[semantic]'"
                )
            raise RuntimeError(f"model {spec.id!r} is unavailable")
        return spec

    def set_default(self, model_id: str) -> ModelSpec:
        spec = self.get(model_id)
        self.default_id = spec.id
        self._write_persisted_default()
        return self.get(spec.id)

    def list(self) -> list[dict[str, Any]]:
        result: list[dict[str, Any]] = []
        for model_id in self._specs:
            spec = self.get(model_id)
            payload = spec.to_dict()
            if spec.id == COSMOS_MAIN_MODEL_ID:
                image_renderer = self.renderer_for(spec, "image_edit")
                video_renderer = self.renderer_for(spec, "video_edit")
                payload["active_renderer"] = image_renderer if image_renderer == video_renderer else "mixed"
                payload["active_renderers"] = {
                    "image_edit": image_renderer,
                    "video_edit": video_renderer,
                }
                payload["available"] = all(
                    (
                        renderer == "native"
                        or (renderer == "http" and bool(self.edit_endpoint))
                        or (renderer == "diffusers" and self.semantic_available and bool(self.semantic_image_model))
                    )
                    for renderer in (image_renderer, video_renderer)
                )
            else:
                payload["active_renderer"] = spec.renderer
            result.append(payload)
        return result

    def status(self) -> dict[str, Any]:
        default = self.get()
        image_renderer = self.renderer_for(default, "image_edit") if "image_edit" in default.capabilities else None
        video_renderer = self.renderer_for(default, "video_edit") if "video_edit" in default.capabilities else None
        return {
            "default_model": self.default_id,
            "default_label": default.label,
            "controller_repo": default.controller_repo,
            "renderer": image_renderer if image_renderer == video_renderer else "mixed",
            "renderers": {
                "image_edit": image_renderer,
                "video_edit": video_renderer,
            },
            "semantic_runtime": self.semantic_available,
            "semantic_image_model": self.semantic_image_model,
            "models": self.list(),
        }
