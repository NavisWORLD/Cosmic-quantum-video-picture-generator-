from __future__ import annotations

import argparse
import json
from pathlib import Path
import shutil
import sys

from .config import Settings, load_env_file
from .engine import CosmosMediaEngine


def _json(value) -> None:
    print(json.dumps(value, indent=2, ensure_ascii=False))


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="cosmos-media",
        description="COSMOS/CST stateful image, video and storybook generation orchestrator",
    )
    parser.add_argument("--env", default=".env", help="optional KEY=VALUE environment file")
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("status", help="show engine/provider/quantum/state status")
    sub.add_parser("doctor", help="check local runtime dependencies")

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

    serve = sub.add_parser("serve", help="run the FastAPI integration server")
    serve.add_argument("--host")
    serve.add_argument("--port", type=int)

    return parser


def doctor(settings: Settings) -> dict[str, object]:
    checks: dict[str, object] = {
        "python": sys.version.split()[0],
        "provider": settings.provider,
        "ffmpeg": shutil.which(settings.ffmpeg),
        "home": str(settings.home),
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
    checks["ready_for_procedural_image"] = bool(checks["pillow"])
    checks["ready_for_procedural_video"] = bool(checks["pillow"] and checks["ffmpeg"])
    return checks


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    load_env_file(Path(args.env))
    settings = Settings()

    if args.command == "doctor":
        _json(doctor(settings))
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
    if args.command == "status":
        _json(engine.status())
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
