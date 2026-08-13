from __future__ import annotations

from dataclasses import dataclass, field
import hashlib
import json
import math
from typing import Iterable

DIMENSIONS = 12


def _clamp(value: float, lo: float = -1.0, hi: float = 1.0) -> float:
    return max(lo, min(hi, value))


def _stable_unit_values(text: str, count: int = DIMENSIONS) -> list[float]:
    """Map arbitrary text deterministically into [-1, 1] values."""
    out: list[float] = []
    counter = 0
    while len(out) < count:
        digest = hashlib.sha256(f"{counter}:{text}".encode("utf-8")).digest()
        for i in range(0, len(digest), 2):
            if len(out) >= count:
                break
            raw = int.from_bytes(digest[i : i + 2], "big")
            out.append((raw / 65535.0) * 2.0 - 1.0)
        counter += 1
    return out


@dataclass(slots=True)
class CSTState:
    """Compact CST-inspired state used for media continuity.

    This is a project-specific computational state vector. It is not a claim
    that these twelve values are literal physical dimensions.
    """

    values: list[float] = field(default_factory=lambda: [0.0] * DIMENSIONS)
    step_index: int = 0

    def __post_init__(self) -> None:
        if len(self.values) != DIMENSIONS:
            raise ValueError(f"CSTState requires exactly {DIMENSIONS} values")
        self.values = [_clamp(float(v)) for v in self.values]

    @classmethod
    def from_context(cls, context: str) -> "CSTState":
        return cls(_stable_unit_values(context, DIMENSIONS), 0)

    def copy(self) -> "CSTState":
        return CSTState(self.values.copy(), self.step_index)

    def hash(self) -> str:
        payload = json.dumps(
            {"values": [round(v, 9) for v in self.values], "step": self.step_index},
            sort_keys=True,
            separators=(",", ":"),
        )
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()

    def to_dict(self) -> dict[str, object]:
        return {"values": self.values, "step_index": self.step_index, "hash": self.hash()}

    def step(
        self,
        stimulus: str,
        *,
        omega: float = 0.37,
        damping: float = 0.82,
        gate: float = 0.33,
        association_bias: Iterable[float] | None = None,
    ) -> "CSTState":
        """Advance a non-saturating recurrent state update.

        The update blends the previous state, a deterministic stimulus vector,
        a phase-coupled recurrent term, and an optional learned association bias.
        tanh keeps the vector bounded while avoiding hard clamping as the primary gate.
        """
        stim = _stable_unit_values(stimulus, DIMENSIONS)
        bias = list(association_bias or [0.0] * DIMENSIONS)
        if len(bias) != DIMENSIONS:
            raise ValueError("association_bias must have 12 values")
        next_values: list[float] = []
        phase = (self.step_index + 1) * omega
        for i, previous in enumerate(self.values):
            coupled = self.values[(i - 1) % DIMENSIONS] - self.values[(i + 1) % DIMENSIONS]
            recurrent = math.sin(phase + i * (math.pi / 6.0)) * coupled * 0.18
            drive = stim[i] * gate + bias[i] * 0.25
            raw = damping * previous + drive + recurrent
            next_values.append(math.tanh(raw))
        return CSTState(next_values, self.step_index + 1)


@dataclass(slots=True)
class HebbianAssociator:
    """Small Hebbian-style association matrix for continuity bias.

    It learns correlations between consecutive 12D states. The matrix is kept
    bounded and can be serialized in generation receipts/checkpoints.
    """

    learning_rate: float = 0.04
    decay: float = 0.995
    weights: list[list[float]] = field(
        default_factory=lambda: [[0.0 for _ in range(DIMENSIONS)] for _ in range(DIMENSIONS)]
    )

    def update(self, before: CSTState, after: CSTState) -> None:
        for i in range(DIMENSIONS):
            for j in range(DIMENSIONS):
                w = self.weights[i][j] * self.decay
                w += self.learning_rate * before.values[i] * after.values[j]
                self.weights[i][j] = _clamp(w)

    def project(self, state: CSTState) -> list[float]:
        projected: list[float] = []
        for j in range(DIMENSIONS):
            value = sum(state.values[i] * self.weights[i][j] for i in range(DIMENSIONS))
            projected.append(math.tanh(value / max(1, DIMENSIONS)))
        return projected

    def to_dict(self) -> dict[str, object]:
        return {
            "learning_rate": self.learning_rate,
            "decay": self.decay,
            "weights": self.weights,
        }
