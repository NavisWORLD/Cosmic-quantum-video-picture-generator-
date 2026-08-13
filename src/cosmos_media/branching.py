from __future__ import annotations

from dataclasses import asdict, dataclass
import math
from typing import Callable

from .provenance import mix_seed
from .state import CSTState


@dataclass(slots=True)
class BranchCandidate:
    index: int
    prompt: str
    seed: int
    seed_hash: str
    state: CSTState
    score: float
    rationale: dict[str, float]

    def to_dict(self) -> dict[str, object]:
        payload = asdict(self)
        payload["state"] = self.state.to_dict()
        return payload


_STYLE_AXES = (
    "cinematic continuity",
    "documentary physicality",
    "dreamlike geometry",
    "intimate character focus",
    "large-scale environmental motion",
    "subtle natural lighting",
    "high temporal coherence",
    "restrained camera language",
)


def _continuity_score(parent: CSTState, child: CSTState) -> float:
    distance = math.sqrt(sum((a - b) ** 2 for a, b in zip(parent.values, child.values)))
    max_distance = math.sqrt(len(parent.values) * 4.0)
    return 1.0 - min(1.0, distance / max_distance)


def search_branches(
    prompt: str,
    parent_state: CSTState,
    *,
    namespace: str,
    count: int = 4,
    scorer: Callable[[str, CSTState], float] | None = None,
) -> list[BranchCandidate]:
    """Generate parallel computational creative branches and rank them.

    “Multiverse” in the public project vocabulary maps to these parallel
    candidate trajectories. This function does not assert physical multiverse
    access or cross-universe communication.
    """
    count = max(1, int(count))
    candidates: list[BranchCandidate] = []
    for index in range(count):
        axis = _STYLE_AXES[index % len(_STYLE_AXES)]
        branch_prompt = f"{prompt}. Branch emphasis: {axis}."
        seed, seed_hash = mix_seed(namespace, prompt, parent_state.hash(), index, axis)
        child = parent_state.step(f"{branch_prompt}|{seed}")
        continuity = _continuity_score(parent_state, child)
        diversity = abs(child.values[index % len(child.values)])
        external = scorer(branch_prompt, child) if scorer else 0.5
        score = 0.50 * continuity + 0.25 * diversity + 0.25 * float(external)
        candidates.append(
            BranchCandidate(
                index=index,
                prompt=branch_prompt,
                seed=seed,
                seed_hash=seed_hash,
                state=child,
                score=round(score, 9),
                rationale={
                    "continuity": round(continuity, 9),
                    "diversity": round(diversity, 9),
                    "external": round(float(external), 9),
                },
            )
        )
    return sorted(candidates, key=lambda item: item.score, reverse=True)
