from __future__ import annotations

import os
from pathlib import Path
import sys
from threading import Lock
from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from . import __version__
from .config import Settings, load_env_file
from .engine import CosmosMediaEngine
from .integrator import CAPABILITIES

load_env_file(".env")
_settings = Settings()
_engine = CosmosMediaEngine(_settings)
_lock = Lock()

Path("out").mkdir(parents=True, exist_ok=True)


def _resolve_pwa_dir() -> Path:
    configured = os.getenv("COSMOS_PWA_DIR")
    if configured:
        return Path(configured)
    local = Path("apps/pwa")
    if local.exists():
        return local
    bundle_root = getattr(sys, "_MEIPASS", None)
    if bundle_root:
        bundled = Path(bundle_root) / "apps" / "pwa"
        if bundled.exists():
            return bundled
    return local


def _cors_origins() -> list[str]:
    configured = os.getenv("COSMOS_CORS_ORIGINS", "").strip()
    if configured:
        return [value.strip() for value in configured.split(",") if value.strip()]
    # Capacitor uses local WebView origins. Browser/PWA same-origin calls do not
    # require CORS, while these defaults let packaged mobile clients reach a
    # COSMOS engine on the user's LAN or trusted deployment.
    return [
        "capacitor://localhost",
        "ionic://localhost",
        "http://localhost",
        "https://localhost",
    ]


app = FastAPI(
    title="COSMOS Quantum Media API",
    version=__version__,
    description="Standalone/helper/bridge media engine with CST continuity and optional IBM Quantum provenance",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins(),
    allow_credentials=False,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Content-Type", "Accept"],
)


class ImageRequest(BaseModel):
    prompt: str = Field(min_length=1)
    output: str = "out/api-image.png"
    context: str = ""
    seed: int | None = None
    width: int | None = None
    height: int | None = None


class VideoRequest(BaseModel):
    prompt: str = Field(min_length=1)
    output: str = "out/api-video.mp4"
    duration: float = Field(gt=0)
    context: str = ""
    seed: int | None = None
    width: int | None = None
    height: int | None = None
    fps: int | None = None
    chunk_seconds: float | None = Field(default=None, gt=0)
    overlap_seconds: float = Field(default=0.5, ge=0)
    resume_run: str | None = None


class StorybookRequest(BaseModel):
    context: str = Field(min_length=1)
    output_dir: str = "out/storybook"
    pages: int = Field(default=8, ge=1, le=64)
    title: str = "COSMOS Storybook"
    style: str = "cinematic storybook realism"
    seed: int | None = None


class BranchRequest(BaseModel):
    prompt: str = Field(min_length=1)
    count: int | None = Field(default=None, ge=1, le=64)


class ResetRequest(BaseModel):
    context: str = ""


def _run(fn, *args, **kwargs):
    try:
        with _lock:
            return fn(*args, **kwargs)
    except (ValueError, RuntimeError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.get("/v1/health")
def health() -> dict[str, Any]:
    return {"ok": True, "engine": f"cosmos-quantum-media/{__version__}", "provider": _engine.provider.name}


@app.get("/v1/capabilities")
def capabilities() -> dict[str, Any]:
    return {**CAPABILITIES, "provider": _engine.provider.name, "version": __version__}


@app.get("/v1/state")
def state() -> dict[str, Any]:
    return _engine.state.to_dict()


@app.post("/v1/state/reset")
def reset(request: ResetRequest) -> dict[str, Any]:
    return _run(_engine.reset_state, request.context)


@app.get("/v1/quantum/status")
def quantum() -> dict[str, Any]:
    return _engine.status()["quantum"]


@app.get("/v1/status")
def status() -> dict[str, Any]:
    return _engine.status()


@app.post("/v1/plan")
def plan(request: BranchRequest) -> dict[str, Any]:
    branches = _run(_engine.branch_search, request.prompt, request.count)
    return {"selected": branches[0], "candidates": branches}


@app.post("/v1/image")
def image(request: ImageRequest) -> dict[str, Any]:
    return _run(
        _engine.generate_image,
        request.prompt,
        Path(request.output),
        context=request.context,
        seed=request.seed,
        width=request.width,
        height=request.height,
    )


@app.post("/v1/video")
def video(request: VideoRequest) -> dict[str, Any]:
    return _run(
        _engine.generate_video,
        request.prompt,
        Path(request.output),
        duration=request.duration,
        context=request.context,
        seed=request.seed,
        width=request.width,
        height=request.height,
        fps=request.fps,
        chunk_seconds=request.chunk_seconds,
        overlap_seconds=request.overlap_seconds,
        resume_run=request.resume_run,
    )


@app.post("/v1/storybook")
def storybook(request: StorybookRequest) -> dict[str, Any]:
    return _run(
        _engine.generate_storybook,
        request.context,
        Path(request.output_dir),
        pages=request.pages,
        title=request.title,
        style=request.style,
        seed=request.seed,
    )


@app.post("/v1/branch-search")
def branches(request: BranchRequest) -> list[dict[str, Any]]:
    return _run(_engine.branch_search, request.prompt, request.count)


app.mount("/out", StaticFiles(directory="out", check_dir=False), name="outputs")
app.mount("/app", StaticFiles(directory=str(_resolve_pwa_dir()), html=True, check_dir=False), name="pwa")
