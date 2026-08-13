from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Iterable, Mapping

from .state import CSTState, DIMENSIONS, HebbianAssociator

PROTOCOL = "cosmos.synaptic.v1"


@dataclass(slots=True)
class SynapticCore:
    """Canonical COSMOS Synaptic v1 kernel.

    The kernel composes the existing 12D recurrent CST state with the existing
    Hebbian associator. It is intentionally small enough to reproduce in other
    languages and stable enough to serialize between processes.
    """

    state: CSTState
    associator: HebbianAssociator
    omega: float = 0.37
    damping: float = 0.82
    gate: float = 0.33

    @classmethod
    def from_context(
        cls,
        context: str,
        *,
        learning_rate: float = 0.04,
        decay: float = 0.995,
        omega: float = 0.37,
        damping: float = 0.82,
        gate: float = 0.33,
    ) -> "SynapticCore":
        return cls(
            state=CSTState.from_context(context),
            associator=HebbianAssociator(learning_rate=learning_rate, decay=decay),
            omega=float(omega),
            damping=float(damping),
            gate=float(gate),
        )

    @classmethod
    def from_snapshot(cls, snapshot: Mapping[str, Any]) -> "SynapticCore":
        protocol = snapshot.get("protocol", PROTOCOL)
        if protocol != PROTOCOL:
            raise ValueError(f"unsupported synaptic protocol: {protocol!r}")

        values = snapshot.get("values")
        if not isinstance(values, list) or len(values) != DIMENSIONS:
            raise ValueError(f"snapshot values must contain exactly {DIMENSIONS} numbers")

        weights = snapshot.get("weights")
        if weights is None:
            weights = [[0.0 for _ in range(DIMENSIONS)] for _ in range(DIMENSIONS)]
        if (
            not isinstance(weights, list)
            or len(weights) != DIMENSIONS
            or any(not isinstance(row, list) or len(row) != DIMENSIONS for row in weights)
        ):
            raise ValueError(f"snapshot weights must be a {DIMENSIONS}x{DIMENSIONS} matrix")

        associator = HebbianAssociator(
            learning_rate=float(snapshot.get("learning_rate", 0.04)),
            decay=float(snapshot.get("decay", 0.995)),
            weights=[[float(value) for value in row] for row in weights],
        )
        return cls(
            state=CSTState([float(value) for value in values], int(snapshot.get("step_index", 0))),
            associator=associator,
            omega=float(snapshot.get("omega", 0.37)),
            damping=float(snapshot.get("damping", 0.82)),
            gate=float(snapshot.get("gate", 0.33)),
        )

    def pulse(self, stimulus: str, *, learn: bool = True) -> dict[str, Any]:
        """Advance one synaptic pulse and optionally update Hebbian weights."""
        if not stimulus:
            raise ValueError("stimulus must not be empty")
        before = self.state.copy()
        bias = self.associator.project(before)
        after = before.step(
            stimulus,
            omega=self.omega,
            damping=self.damping,
            gate=self.gate,
            association_bias=bias,
        )
        if learn:
            self.associator.update(before, after)
        self.state = after
        return self.snapshot()

    def project(self, values: Iterable[float] | None = None) -> list[float]:
        """Project the current or supplied 12D state through learned associations."""
        state = self.state if values is None else CSTState(list(values), self.state.step_index)
        return self.associator.project(state)

    def snapshot(self) -> dict[str, Any]:
        """Return the portable protocol snapshot shared by all SDKs."""
        return {
            "protocol": PROTOCOL,
            "dimensions": DIMENSIONS,
            "step_index": self.state.step_index,
            "values": self.state.values.copy(),
            "weights": [row.copy() for row in self.associator.weights],
            "learning_rate": self.associator.learning_rate,
            "decay": self.associator.decay,
            "omega": self.omega,
            "damping": self.damping,
            "gate": self.gate,
            "state_hash": self.state.hash(),
        }


def pulse_snapshot(snapshot: Mapping[str, Any], stimulus: str, *, learn: bool = True) -> dict[str, Any]:
    """Stateless helper used by REST/JSON bridges."""
    core = SynapticCore.from_snapshot(snapshot)
    return core.pulse(stimulus, learn=learn)
