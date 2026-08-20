from __future__ import annotations

"""Language-neutral stdio bridge for embedding COSMOS in another application.

Any process that can spawn a subprocess and exchange JSON lines can use COSMOS
as a state/branch/render/edit helper without linking Python directly.
"""

import json
from pathlib import Path
from typing import Any, TextIO

from .editing import EditingService
from .engine import CosmosMediaEngine


CAPABILITIES = {
    "protocol": "cosmos-media-jsonl/1",
    "modes": ["standalone", "helper", "bridge"],
    "operations": [
        "capabilities",
        "status",
        "state",
        "reset_state",
        "branch",
        "plan",
        "image",
        "video",
        "storybook",
        "models",
        "set_default_model",
        "edit_image",
        "edit_video",
    ],
    "editing": {
        "uploads": ["png", "jpg", "jpeg", "webp", "mp4", "mov", "webm", "m4v"],
        "image": ["prompt", "negative_prompt", "model", "strength", "preserve_subject", "mask"],
        "video": [
            "prompt",
            "negative_prompt",
            "model",
            "strength",
            "preserve_subject",
            "preserve_audio",
            "chunk_seconds",
            "style_lock",
            "temporal_blend",
        ],
        "renderers": ["native", "diffusers", "http"],
        "default_model": "cosmos-main",
    },
}


def _editing_for(engine: CosmosMediaEngine, editing: EditingService | None) -> EditingService:
    return editing if editing is not None else EditingService(engine.settings)


def handle_request(
    engine: CosmosMediaEngine,
    request: dict[str, Any],
    editing: EditingService | None = None,
) -> dict[str, Any]:
    op = str(request.get("op", "")).strip().lower()
    request_id = request.get("id")

    def ok(result: Any) -> dict[str, Any]:
        return {"ok": True, "id": request_id, "op": op, "result": result}

    if op == "capabilities":
        return ok(CAPABILITIES)
    if op == "status":
        status = engine.status()
        status["editing"] = _editing_for(engine, editing).models()
        return ok(status)
    if op == "models":
        return ok(_editing_for(engine, editing).models())
    if op == "set_default_model":
        model = str(request.get("model", "")).strip()
        if not model:
            raise ValueError("set_default_model requires model")
        return ok(_editing_for(engine, editing).set_default_model(model))
    if op == "edit_image":
        prompt = str(request.get("prompt", "")).strip()
        source = str(request.get("input", "")).strip()
        if not source or not prompt:
            raise ValueError("edit_image requires input and prompt")
        service = _editing_for(engine, editing)
        asset = service.import_file(source)
        mask_asset_id = None
        mask_source = str(request.get("mask", "")).strip()
        if mask_source:
            mask_asset_id = service.import_file(mask_source)["asset_id"]
        return ok(
            service.edit_image(
                asset["asset_id"],
                prompt,
                request.get("output", "out/bridge-edited-image.png"),
                model=request.get("model"),
                negative_prompt=str(request.get("negative_prompt", "")),
                strength=float(request.get("strength", 0.5)),
                preserve_subject=bool(request.get("preserve_subject", True)),
                mask_asset_id=mask_asset_id,
            )
        )
    if op == "edit_video":
        prompt = str(request.get("prompt", "")).strip()
        source = str(request.get("input", "")).strip()
        if not source or not prompt:
            raise ValueError("edit_video requires input and prompt")
        service = _editing_for(engine, editing)
        asset = service.import_file(source)
        return ok(
            service.edit_video(
                asset["asset_id"],
                prompt,
                request.get("output", "out/bridge-edited-video.mp4"),
                model=request.get("model"),
                negative_prompt=str(request.get("negative_prompt", "")),
                strength=float(request.get("strength", 0.45)),
                preserve_subject=bool(request.get("preserve_subject", True)),
                preserve_audio=bool(request.get("preserve_audio", True)),
                chunk_seconds=float(request.get("chunk_seconds", 6.0)),
                style_lock=bool(request.get("style_lock", True)),
                temporal_blend=float(request.get("temporal_blend", 0.12)),
            )
        )
    if op == "state":
        return ok(engine.state.to_dict())
    if op == "reset_state":
        return ok(engine.reset_state(str(request.get("context", ""))))
    if op in {"branch", "plan"}:
        prompt = str(request.get("prompt", "")).strip()
        if not prompt:
            raise ValueError("branch/plan requires prompt")
        branches = engine.branch_search(prompt, request.get("count"))
        if op == "plan":
            return ok({"selected": branches[0], "candidates": branches})
        return ok(branches)
    if op == "image":
        prompt = str(request.get("prompt", "")).strip()
        if not prompt:
            raise ValueError("image requires prompt")
        output = Path(str(request.get("output", "out/bridge-image.png")))
        return ok(
            engine.generate_image(
                prompt,
                output,
                context=str(request.get("context", "")),
                seed=request.get("seed"),
                width=request.get("width"),
                height=request.get("height"),
            )
        )
    if op == "video":
        prompt = str(request.get("prompt", "")).strip()
        if not prompt:
            raise ValueError("video requires prompt")
        if "duration" not in request:
            raise ValueError("video requires duration")
        output = Path(str(request.get("output", "out/bridge-video.mp4")))
        return ok(
            engine.generate_video(
                prompt,
                output,
                duration=float(request["duration"]),
                context=str(request.get("context", "")),
                seed=request.get("seed"),
                width=request.get("width"),
                height=request.get("height"),
                fps=request.get("fps"),
                chunk_seconds=request.get("chunk_seconds"),
                overlap_seconds=float(request.get("overlap_seconds", 0.5)),
                resume_run=request.get("resume_run"),
            )
        )
    if op == "storybook":
        context = str(request.get("context", "")).strip()
        if not context:
            raise ValueError("storybook requires context")
        output = Path(str(request.get("output", "out/bridge-storybook")))
        return ok(
            engine.generate_storybook(
                context,
                output,
                pages=int(request.get("pages", 8)),
                title=str(request.get("title", "COSMOS Storybook")),
                style=str(request.get("style", "cinematic storybook realism")),
                seed=request.get("seed"),
            )
        )
    raise ValueError(f"unknown bridge operation: {op!r}")


def process_json_line(
    engine: CosmosMediaEngine,
    line: str,
    editing: EditingService | None = None,
) -> dict[str, Any]:
    request: dict[str, Any] | None = None
    try:
        request = json.loads(line)
        if not isinstance(request, dict):
            raise ValueError("request must be a JSON object")
        return handle_request(engine, request, editing)
    except Exception as exc:
        return {
            "ok": False,
            "id": request.get("id") if isinstance(request, dict) else None,
            "error": {"type": type(exc).__name__, "message": str(exc)},
        }


def run_stdio(
    engine: CosmosMediaEngine,
    source: TextIO,
    sink: TextIO,
    editing: EditingService | None = None,
) -> int:
    service = editing or EditingService(engine.settings)
    for raw_line in source:
        line = raw_line.strip()
        if not line:
            continue
        response = process_json_line(engine, line, service)
        sink.write(json.dumps(response, separators=(",", ":"), ensure_ascii=False) + "\n")
        sink.flush()
    return 0
