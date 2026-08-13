from __future__ import annotations

"""Language-neutral stdio bridge for embedding COSMOS in another application.

Any process that can spawn a subprocess and exchange JSON lines can use COSMOS
as a state/branch/render helper without linking Python directly.
"""

import json
from pathlib import Path
from typing import Any, TextIO

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
    ],
}


def handle_request(engine: CosmosMediaEngine, request: dict[str, Any]) -> dict[str, Any]:
    op = str(request.get("op", "")).strip().lower()
    request_id = request.get("id")

    def ok(result: Any) -> dict[str, Any]:
        return {"ok": True, "id": request_id, "op": op, "result": result}

    if op == "capabilities":
        return ok(CAPABILITIES)
    if op == "status":
        return ok(engine.status())
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


def process_json_line(engine: CosmosMediaEngine, line: str) -> dict[str, Any]:
    request: dict[str, Any] | None = None
    try:
        request = json.loads(line)
        if not isinstance(request, dict):
            raise ValueError("request must be a JSON object")
        return handle_request(engine, request)
    except Exception as exc:
        return {
            "ok": False,
            "id": request.get("id") if isinstance(request, dict) else None,
            "error": {"type": type(exc).__name__, "message": str(exc)},
        }


def run_stdio(engine: CosmosMediaEngine, source: TextIO, sink: TextIO) -> int:
    for raw_line in source:
        line = raw_line.strip()
        if not line:
            continue
        response = process_json_line(engine, line)
        sink.write(json.dumps(response, separators=(",", ":"), ensure_ascii=False) + "\n")
        sink.flush()
    return 0
