from __future__ import annotations

import argparse
import json
from pathlib import Path
import shutil
import sys

from .config import Settings, load_env_file
from .editing import EditingService
from .engine import CosmosMediaEngine
from .integrator import CAPABILITIES, handle_request, run_stdio


def _json(value) -> None:
    print(json.dumps(value, indent=2, ensure_ascii=False))


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="cosmos-media",
        description="COSMOS/CST standalone media engine, editor, helper, and integration bridge",
    )
    parser.add_argument("--env", default=".env", help="optional KEY=VALUE environment file")
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("status", help="show engine/provider/quantum/edit/model status")
    sub.add_parser("doctor", help="check local runtime dependencies")
    sub.add_parser("capabilities", help="print machine-readable integration capabilities")

    reset = sub.add_parser("reset-state", help="reset persistent CST state")
    reset.add_argument("--context", default="")

    image = sub.add_parser("image", help="generate an image")
    image.add_argument("--prompt", required=True)
    image.add_argument("--context", default="")
    image.add_argument("--seed", type=int)
    image.add_argument("--width", type=int)
    image.add_argument("--height", type=int)
    image.add_argument("--out", required=True)

    video = sub.add_parser("video", help="generate and stitch a long-form video")
    video.add_argument("--prompt", required=True)
    video.add_argument("--context", default="")
    video.add_argument("--seed", type=int)
    video.add_argument("--duration", type=float, required=True)
    video.add_argument("--chunk-seconds", type=float)
    video.add_argument("--overlap-seconds", type=float, default=0.5)
    video.add_argument("--fps", type=int)
    video.add_argument("--width", type=int)
    video.add_argument("--height", type=int)
    video.add_argument("--resume-run")
    video.add_argument("--out", required=True)

    edit_image = sub.add_parser("edit-image", help="edit an existing image from a prompt")
    edit_image.add_argument("--input", required=True)
    edit_image.add_argument("--mask", help="optional image mask; white pixels are editable")
    edit_image.add_argument("--prompt", required=True)
    edit_image.add_argument("--negative-prompt", default="")
    edit_image.add_argument("--model")
    edit_image.add_argument("--strength", type=float, default=0.5)
    edit_image.add_argument("--no-preserve-subject", action="store_false", dest="preserve_subject")
    edit_image.add_argument("--out", required=True)

    edit_video = sub.add_parser("edit-video", help="edit an existing video from a prompt")
    edit_video.add_argument("--input", required=True)
    edit_video.add_argument("--prompt", required=True)
    edit_video.add_argument("--negative-prompt", default="")
    edit_video.add_argument("--model")
    edit_video.add_argument("--strength", type=float, default=0.45)
    edit_video.add_argument("--no-preserve-subject", action="store_false", dest="preserve_subject")
    edit_video.add_argument("--no-preserve-audio", action="store_false", dest="preserve_audio")
    edit_video.add_argument("--chunk-seconds", type=float, default=6.0)
    edit_video.add_argument("--no-style-lock", action="store_false", dest="style_lock")
    edit_video.add_argument("--temporal-blend", type=float, default=0.12)
    edit_video.add_argument("--out", required=True)

    models = sub.add_parser("models", help="list or change edit models")
    model_sub = models.add_subparsers(dest="model_command", required=True)
    model_sub.add_parser("list", help="list available edit models")
    model_sub.add_parser("default", help="show current default edit model")
    model_set = model_sub.add_parser("set-default", help="persist a new default edit model")
    model_set.add_argument("model")

    story = sub.add_parser("storybook", help="generate a context-grounded illustrated storybook")
    story.add_argument("--context", help="literal context text")
    story.add_argument("--context-file", help="UTF-8 file containing source context")
    story.add_argument("--pages", type=int, default=8)
    story.add_argument("--title", default="COSMOS Storybook")
    story.add_argument("--style", default="cinematic storybook realism")
    story.add_argument("--seed", type=int)
    story.add_argument("--out", required=True)

    branch = sub.add_parser("branch-search", help="plan computational multiverse candidate branches")
    branch.add_argument("--prompt", required=True)
    branch.add_argument("--count", type=int)

    bridge = sub.add_parser(
        "bridge",
        help="JSON integration bridge for external apps, agents, renderers, and CLIs",
    )
    bridge.add_argument(
        "--stdio",
        action="store_true",
        help="persistent JSONL stdin/stdout mode; one request and response per line",
    )
    bridge.add_argument(
        "--request",
        help="one-shot JSON request; if omitted and --stdio is not set, read one JSON object from stdin",
    )

    serve = sub.add_parser("serve", help="run the FastAPI integration server")
    serve.add_argument("--host")
    serve.add_argument("--port", type=int)

    return parser


def doctor(settings: Settings) -> dict[str, object]:
    checks: dict[str, object] = {
        "python": sys.version.split()[0],
        "provider": settings.provider,
        "ffmpeg": shutil.which(settings.ffmpeg) or settings.ffmpeg,
        "ffprobe": shutil.which("ffprobe"),
        "home": str(settings.home),
        "modes": ["standalone", "helper", "bridge"],
        "default_model": settings.default_model,
        "edit_renderer": settings.edit_renderer,
        "image_edit_renderer": settings.image_edit_renderer,
        "video_edit_renderer": settings.video_edit_renderer,
        "semantic_image_model": settings.semantic_image_model,
    }
    try:
        import PIL  # noqa: F401
        checks["pillow"] = True
    except ImportError:
        checks["pillow"] = False
    try:
        import httpx  # noqa: F401
        checks["httpx"] = True
    except ImportError:
        checks["httpx"] = False
    try:
        import fastapi  # noqa: F401
        checks["fastapi"] = True
    except ImportError:
        checks["fastapi"] = False
    try:
        import qiskit_ibm_runtime  # noqa: F401
        checks["qiskit_ibm_runtime"] = True
    except ImportError:
        checks["qiskit_ibm_runtime"] = False
    try:
        import torch  # noqa: F401
        import diffusers  # noqa: F401
        checks["semantic_runtime"] = True
    except ImportError:
        checks["semantic_runtime"] = False
    checks["ready_for_native_image"] = bool(checks["pillow"])
    checks["ready_for_native_video"] = bool(checks["pillow"] and checks["ffmpeg"])
    checks["ready_for_native_edit_image"] = bool(checks["pillow"])
    checks["ready_for_native_edit_video"] = bool(checks["ffmpeg"])
    checks["ready_for_http_bridge"] = bool(checks["httpx"])
    checks["http_edit_configured"] = bool(settings.edit_endpoint)
    checks["ready_for_local_semantic_edit"] = bool(checks["pillow"] and checks["semantic_runtime"])
    return checks


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    load_env_file(Path(args.env))
    settings = Settings()

    if args.command == "doctor":
        _json(doctor(settings))
        return 0
    if args.command == "capabilities":
        _json(CAPABILITIES)
        return 0
    if args.command == "serve":
        try:
            import uvicorn
        except ImportError:
            parser.error("serve requires: pip install -e '.[server]' ")
        host = args.host or settings.api_host
        port = args.port or settings.api_port
        uvicorn.run("cosmos_media.api:app", host=host, port=port, reload=False)
        return 0

    engine = CosmosMediaEngine(settings)
    editing = EditingService(settings)

    if args.command == "bridge":
        if args.stdio:
            return run_stdio(engine, sys.stdin, sys.stdout, editing)
        raw = args.request if args.request is not None else sys.stdin.read()
        try:
            request = json.loads(raw)
            if not isinstance(request, dict):
                raise ValueError("bridge request must be a JSON object")
            _json(handle_request(engine, request, editing))
            return 0
        except Exception as exc:
            _json({"ok": False, "error": {"type": type(exc).__name__, "message": str(exc)}})
            return 2

    if args.command == "status":
        status = engine.status()
        status["editing"] = editing.models()
        _json(status)
    elif args.command == "models":
        if args.model_command == "list":
            _json(editing.models())
        elif args.model_command == "default":
            _json({"default_model": editing.registry.default_id, "model": editing.registry.get().to_dict()})
        elif args.model_command == "set-default":
            _json(editing.set_default_model(args.model))
        else:
            parser.error(f"unknown models command: {args.model_command}")
    elif args.command == "edit-image":
        asset = editing.import_file(args.input)
        mask_asset_id = None
        if args.mask:
            mask_asset_id = editing.import_file(args.mask)["asset_id"]
        _json(
            editing.edit_image(
                asset["asset_id"],
                args.prompt,
                args.out,
                model=args.model,
                negative_prompt=args.negative_prompt,
                strength=args.strength,
                preserve_subject=args.preserve_subject,
                mask_asset_id=mask_asset_id,
            )
        )
    elif args.command == "edit-video":
        asset = editing.import_file(args.input)
        _json(
            editing.edit_video(
                asset["asset_id"],
                args.prompt,
                args.out,
                model=args.model,
                negative_prompt=args.negative_prompt,
                strength=args.strength,
                preserve_subject=args.preserve_subject,
                preserve_audio=args.preserve_audio,
                chunk_seconds=args.chunk_seconds,
                style_lock=args.style_lock,
                temporal_blend=args.temporal_blend,
            )
        )
    elif args.command == "reset-state":
        _json(engine.reset_state(args.context))
    elif args.command == "image":
        _json(
            engine.generate_image(
                args.prompt,
                args.out,
                context=args.context,
                seed=args.seed,
                width=args.width,
                height=args.height,
            )
        )
    elif args.command == "video":
        _json(
            engine.generate_video(
                args.prompt,
                args.out,
                duration=args.duration,
                context=args.context,
                seed=args.seed,
                width=args.width,
                height=args.height,
                fps=args.fps,
                chunk_seconds=args.chunk_seconds,
                overlap_seconds=args.overlap_seconds,
                resume_run=args.resume_run,
            )
        )
    elif args.command == "storybook":
        if args.context_file:
            context = Path(args.context_file).read_text(encoding="utf-8")
        else:
            context = args.context or ""
        if not context.strip():
            parser.error("storybook requires --context or --context-file")
        _json(
            engine.generate_storybook(
                context,
                args.out,
                pages=args.pages,
                title=args.title,
                style=args.style,
                seed=args.seed,
            )
        )
    elif args.command == "branch-search":
        _json(engine.branch_search(args.prompt, args.count))
    else:
        parser.error(f"unknown command: {args.command}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
