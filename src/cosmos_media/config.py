from __future__ import annotations

from dataclasses import dataclass, field
import os
from pathlib import Path
import shutil


def _bool(name: str, default: bool = False) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def load_env_file(path: str | Path = ".env", *, override: bool = False) -> None:
    """Load a minimal KEY=VALUE file without adding a dotenv dependency."""
    source = Path(path)
    if not source.exists():
        return
    for raw_line in source.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key and (override or key not in os.environ):
            os.environ[key] = value


@dataclass(slots=True)
class Settings:
    home: Path = field(default_factory=lambda: Path(os.getenv("COSMOS_HOME", ".cosmos-media")))
    provider: str = field(default_factory=lambda: os.getenv("COSMOS_MEDIA_PROVIDER", "native").strip().lower())
    media_endpoint: str = field(default_factory=lambda: os.getenv("COSMOS_MEDIA_ENDPOINT", "http://127.0.0.1:9000").rstrip("/"))
    media_timeout: float = field(default_factory=lambda: float(os.getenv("COSMOS_MEDIA_TIMEOUT", "600")))
    ffmpeg: str = field(default_factory=lambda: os.getenv("COSMOS_FFMPEG", "ffmpeg"))
    api_host: str = field(default_factory=lambda: os.getenv("COSMOS_API_HOST", "127.0.0.1"))
    api_port: int = field(default_factory=lambda: int(os.getenv("COSMOS_API_PORT", "8788")))
    quantum_mode: str = field(default_factory=lambda: os.getenv("COSMOS_QUANTUM_MODE", "local").strip().lower())
    quantum_strict: bool = field(default_factory=lambda: _bool("COSMOS_QUANTUM_STRICT", False))
    ibm_api_key: str = field(default_factory=lambda: os.getenv("IBM_QUANTUM_API_KEY", ""))
    ibm_instance: str = field(default_factory=lambda: os.getenv("IBM_QUANTUM_INSTANCE", ""))
    ibm_backend: str = field(default_factory=lambda: os.getenv("IBM_QUANTUM_BACKEND", ""))
    ibm_shots: int = field(default_factory=lambda: int(os.getenv("IBM_QUANTUM_SHOTS", "256")))
    width: int = field(default_factory=lambda: int(os.getenv("COSMOS_WIDTH", "1024")))
    height: int = field(default_factory=lambda: int(os.getenv("COSMOS_HEIGHT", "576")))
    fps: int = field(default_factory=lambda: int(os.getenv("COSMOS_FPS", "24")))
    chunk_seconds: float = field(default_factory=lambda: float(os.getenv("COSMOS_CHUNK_SECONDS", "8")))
    branches: int = field(default_factory=lambda: int(os.getenv("COSMOS_BRANCHES", "4")))
    seed_namespace: str = field(default_factory=lambda: os.getenv("COSMOS_SEED_NAMESPACE", "cosmos-media-v1"))

    # Editing/model configuration. COSMOS Main is a controller identity while
    # edit_renderer names the implementation that actually changes pixels.
    default_model: str = field(default_factory=lambda: os.getenv("COSMOS_DEFAULT_MODEL", "cosmos-main").strip().lower())
    edit_renderer: str = field(default_factory=lambda: os.getenv("COSMOS_EDIT_RENDERER", "native").strip().lower())
    edit_endpoint: str = field(default_factory=lambda: os.getenv("COSMOS_EDIT_ENDPOINT", "").rstrip("/"))
    max_upload_mb: int = field(default_factory=lambda: int(os.getenv("COSMOS_MAX_UPLOAD_MB", "256")))

    def __post_init__(self) -> None:
        # A packaged desktop build includes imageio-ffmpeg. Resolve it during
        # settings construction so existing render/stitch/edit code receives a
        # real executable path on clean Windows/macOS installations.
        self.ffmpeg = self.resolved_ffmpeg()
        if self.max_upload_mb <= 0:
            raise ValueError("COSMOS_MAX_UPLOAD_MB must be positive")
        if self.edit_renderer not in {"native", "http"}:
            raise ValueError("COSMOS_EDIT_RENDERER must be 'native' or 'http'")

    def ensure_dirs(self) -> None:
        for name in ("runs", "cache", "state", "receipts", "assets", "edit_jobs"):
            (self.home / name).mkdir(parents=True, exist_ok=True)

    def resolved_ffmpeg(self) -> str:
        explicit = self.ffmpeg.strip()
        if explicit and explicit != "ffmpeg":
            return explicit
        found = shutil.which(explicit or "ffmpeg")
        if found:
            return found
        try:
            import imageio_ffmpeg

            return imageio_ffmpeg.get_ffmpeg_exe()
        except Exception:
            return explicit or "ffmpeg"

    def public_dict(self) -> dict[str, object]:
        return {
            "home": str(self.home),
            "provider": self.provider,
            "media_endpoint": self.media_endpoint,
            "media_timeout": self.media_timeout,
            "ffmpeg": self.ffmpeg,
            "api_host": self.api_host,
            "api_port": self.api_port,
            "quantum_mode": self.quantum_mode,
            "quantum_strict": self.quantum_strict,
            "ibm_configured": bool(self.ibm_api_key),
            "ibm_instance_configured": bool(self.ibm_instance),
            "ibm_backend": self.ibm_backend or None,
            "ibm_shots": self.ibm_shots,
            "width": self.width,
            "height": self.height,
            "fps": self.fps,
            "chunk_seconds": self.chunk_seconds,
            "branches": self.branches,
            "seed_namespace": self.seed_namespace,
            "default_model": self.default_model,
            "edit_renderer": self.edit_renderer,
            "edit_endpoint_configured": bool(self.edit_endpoint),
            "max_upload_mb": self.max_upload_mb,
        }
