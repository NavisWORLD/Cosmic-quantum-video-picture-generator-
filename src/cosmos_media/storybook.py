from __future__ import annotations

from dataclasses import asdict, dataclass
import re
from typing import Iterable


@dataclass(slots=True)
class StoryScene:
    page: int
    title: str
    narration: str
    image_prompt: str
    continuity_note: str

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


def _sentences(text: str) -> list[str]:
    cleaned = re.sub(r"\s+", " ", text.strip())
    if not cleaned:
        return []
    parts = re.split(r"(?<=[.!?])\s+", cleaned)
    return [part.strip() for part in parts if part.strip()]


def plan_storybook(context: str, *, pages: int = 8, style: str = "cinematic storybook realism") -> list[StoryScene]:
    """Convert user-provided context into deterministic scene prompts.

    This planner intentionally does not invent biographical facts beyond the
    supplied context. If the context is short, it expands visual framing and
    pacing while keeping the factual narration anchored to the source text.
    """
    pages = max(1, min(64, int(pages)))
    source = _sentences(context)
    if not source:
        source = ["A new story begins with the context the user chooses to provide."]

    scenes: list[StoryScene] = []
    for page in range(1, pages + 1):
        sentence = source[(page - 1) % len(source)]
        progress = (page - 1) / max(1, pages - 1)
        if progress < 0.25:
            pacing = "opening image, establish place, identity, and emotional weather"
        elif progress < 0.6:
            pacing = "develop the central action with clear spatial continuity"
        elif progress < 0.85:
            pacing = "raise visual scale and emotional consequence without changing the source facts"
        else:
            pacing = "resolve into a memorable final image that echoes the opening"
        title = f"Page {page}: {sentence[:42].rstrip(' ,.;:')}"
        prompt = (
            f"{style}; {pacing}. Visualize only what can be reasonably grounded in this source context: "
            f"{sentence} Maintain recurring characters, clothing, architecture, light direction, palette, "
            f"camera grammar, and object placement from previous pages. No text in the image."
        )
        scenes.append(
            StoryScene(
                page=page,
                title=title,
                narration=sentence,
                image_prompt=prompt,
                continuity_note=f"story progress {progress:.3f}; preserve recurring visual identity",
            )
        )
    return scenes


def story_markdown(title: str, scenes: Iterable[StoryScene]) -> str:
    lines = [f"# {title}", ""]
    for scene in scenes:
        lines.extend(
            [
                f"## {scene.title}",
                "",
                scene.narration,
                "",
                f"![Page {scene.page}](page-{scene.page:03d}.png)",
                "",
            ]
        )
    return "\n".join(lines)
