from __future__ import annotations

from dataclasses import dataclass, asdict
import math


@dataclass(frozen=True, slots=True)
class ChunkPlan:
    index: int
    start: float
    duration: float
    overlap_before: float
    overlap_after: float
    narrative_progress: float

    def to_dict(self) -> dict[str, float | int]:
        return asdict(self)


def plan_timeline(
    duration: float,
    *,
    chunk_seconds: float = 8.0,
    overlap_seconds: float = 0.5,
) -> list[ChunkPlan]:
    """Split any finite duration into bounded resumable render chunks.

    A 3600-second request with 8-second chunks produces 450 chunks. The
    overlap fields are continuity metadata for providers that support temporal
    conditioning; FFmpeg stitching itself defaults to hard concatenation.
    """
    duration = float(duration)
    chunk_seconds = float(chunk_seconds)
    overlap_seconds = max(0.0, float(overlap_seconds))
    if not math.isfinite(duration) or duration <= 0:
        raise ValueError("duration must be a positive finite number")
    if not math.isfinite(chunk_seconds) or chunk_seconds <= 0:
        raise ValueError("chunk_seconds must be a positive finite number")
    if overlap_seconds >= chunk_seconds:
        raise ValueError("overlap_seconds must be smaller than chunk_seconds")

    count = int(math.ceil(duration / chunk_seconds))
    plans: list[ChunkPlan] = []
    for index in range(count):
        start = index * chunk_seconds
        remaining = duration - start
        length = min(chunk_seconds, remaining)
        plans.append(
            ChunkPlan(
                index=index,
                start=round(start, 6),
                duration=round(length, 6),
                overlap_before=0.0 if index == 0 else min(overlap_seconds, length / 2.0),
                overlap_after=0.0 if index == count - 1 else min(overlap_seconds, length / 2.0),
                narrative_progress=round((start + length / 2.0) / duration, 9),
            )
        )
    return plans
