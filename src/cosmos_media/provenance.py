from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
from typing import Any, Iterable


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_text(text: str) -> str:
    return sha256_bytes(text.encode("utf-8"))


def canonical_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def mix_seed(namespace: str, *parts: str | bytes | int | float) -> tuple[int, str]:
    h = hashlib.sha256()
    h.update(namespace.encode("utf-8"))
    h.update(b"\0")
    for part in parts:
        if isinstance(part, bytes):
            payload = part
        else:
            payload = str(part).encode("utf-8")
        h.update(len(payload).to_bytes(8, "big"))
        h.update(payload)
    digest = h.digest()
    return int.from_bytes(digest[:8], "big") & 0x7FFF_FFFF_FFFF_FFFF, digest.hex()


@dataclass(slots=True)
class QuantumReceipt:
    mode: str
    source: str
    backend: str | None = None
    job_id: str | None = None
    raw_hash: str | None = None
    result_hash: str | None = None
    fallback_reason: str | None = None


@dataclass(slots=True)
class GenerationReceipt:
    run_id: str
    kind: str
    prompt_hash: str
    context_hash: str
    state_hash: str
    seed: int
    seed_hash: str
    provider: str
    parameters: dict[str, Any]
    outputs: list[str] = field(default_factory=list)
    quantum: QuantumReceipt | None = None
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    engine: str = "cosmos-quantum-media/0.1.0"

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["receipt_hash"] = sha256_text(canonical_json(payload))
        return payload

    def write(self, path: str | Path) -> Path:
        destination = Path(path)
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text(json.dumps(self.to_dict(), indent=2, ensure_ascii=False), encoding="utf-8")
        return destination


def hash_files(paths: Iterable[str | Path]) -> dict[str, str]:
    result: dict[str, str] = {}
    for item in paths:
        path = Path(item)
        with path.open("rb") as handle:
            result[str(path)] = sha256_bytes(handle.read())
    return result
