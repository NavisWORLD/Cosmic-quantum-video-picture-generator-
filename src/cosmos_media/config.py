from __future__ import annotations

from dataclasses import dataclass
import os
from pathlib import Path


def _bool(name: str, default: bool = False) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


@dataclass(slots=True)
class Settings:
    home: Path = Path(os.getenv("COSMOS_HOME", ".cosmos-media"))
    provider: str = os.getenv("COSMOS_MEDIA_PROVIDER", "procedural").strip().lower()
    media_endpoint: str = os.getenv("COSMOS_MEDIA_ENDPOINT", "http://127.0.0.1:9000").rstrip("/")
    media_timeout: float = float(os.getenv("COSMOS_MEDIA_TIMEOUT", "600"))
    ffmpeg: str = os.getenv("COSMOS_FFMPEG", "ffmpeg")
    api_host: str = os.getenv("COSMOS_API_HOST", "127.0.0.1")
    api_port: int = int(os.getenv("COSMOS_API_PORT", "8788"))
    quantum_mode: str = os.getenv("COSMOS_QUANTUM_MODE", "local").strip().lower()
    quantum_strict: bool = _bool("COSMOS_QUANTUM_STRICT", False)
    ibm_api_key: str = os.getenv("IBM_QUANTUM_API_KEY", "")
    ibm_instance: str = os.getenv("IBM_QUANTUM_INSTANCE", "")
    ibm_backend: str = os.getenv("IBM_QUANTUM_BACKEND", "")
    ibm_shots: int = int(os.getenv("IBM_QUANTUM_SHOTS", "256"))
    width: int = int(os.getenv("COSMOS_WIDTH", "1024"))
    height: int = int(os.getenv("COSMOS_HEIGHT", "576"))
    fps: int = int(os.getenv("COSMOS_FPS", "24"))
    chunk_seconds: float = float(os.getenv("COSMOS_CHUNK_SECONDS", "8"))
    branches: int = int(os.getenv("COSMOS_BRANCHES", "4"))
    seed_namespace: str = os.getenv("COSMOS_SEED_NAMESPACE", "cosmos-media-v1")

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
