from __future__ import annotations

from dataclasses import dataclass, field
import os
from pathlib import Path


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
    provider: str = field(default_factory=lambda: os.getenv("COSMOS_MEDIA_PROVIDER", "procedural").strip().lower())
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

    def ensure_dirs(self) -> None:
        for name in ("runs", "cache", "state", "receipts"):
            (self.home / name).mkdir(parents=True, exist_ok=True)

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
        }
