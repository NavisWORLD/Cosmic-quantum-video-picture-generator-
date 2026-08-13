from cosmos_media.branching import search_branches
from cosmos_media.provenance import mix_seed
from cosmos_media.state import CSTState, HebbianAssociator
from cosmos_media.storybook import plan_storybook
from cosmos_media.timeline import plan_timeline


def test_hour_timeline_is_450_chunks():
    chunks = plan_timeline(3600, chunk_seconds=8, overlap_seconds=0.5)
    assert len(chunks) == 450
    assert chunks[0].start == 0
    assert chunks[-1].start == 3592
    assert sum(item.duration for item in chunks) == 3600


def test_state_is_12d_and_bounded():
    state = CSTState.from_context("hello cosmos")
    assert len(state.values) == 12
    for _ in range(100):
        state = state.step("continued scene")
    assert all(-1.0 <= value <= 1.0 for value in state.values)


def test_hebbian_projection_shape():
    before = CSTState.from_context("before")
    after = before.step("after")
    h = HebbianAssociator()
    h.update(before, after)
    projected = h.project(after)
    assert len(projected) == 12
    assert all(-1.0 <= value <= 1.0 for value in projected)


def test_seed_mixing_is_deterministic():
    first = mix_seed("namespace", "a", 2, b"three")
    second = mix_seed("namespace", "a", 2, b"three")
    changed = mix_seed("namespace", "a", 3, b"three")
    assert first == second
    assert first != changed


def test_branch_search_ranks_candidates():
    candidates = search_branches("a quiet city", CSTState(), namespace="test", count=5)
    assert len(candidates) == 5
    assert candidates == sorted(candidates, key=lambda item: item.score, reverse=True)


def test_storybook_planner_honors_page_count():
    scenes = plan_storybook("A child finds a glowing seed. They plant it beside the school.", pages=6)
    assert len(scenes) == 6
    assert all("No text in the image" in scene.image_prompt for scene in scenes)
