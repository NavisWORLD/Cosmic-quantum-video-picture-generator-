from __future__ import annotations

import json
from pathlib import Path

from cosmos_media.config import Settings
from cosmos_media.engine import CosmosMediaEngine


class FakeProvider:
    name = "fake"

    def generate_image(self, job):
        job.output.parent.mkdir(parents=True, exist_ok=True)
        job.output.write_bytes(f"image:{job.seed}".encode())
        return job.output

    def generate_video(self, job):
        job.output.parent.mkdir(parents=True, exist_ok=True)
        job.output.write_bytes(f"video:{job.seed}:{job.duration}".encode())
        return job.output


def make_engine(tmp_path: Path) -> CosmosMediaEngine:
    settings = Settings(
        home=tmp_path / ".cosmos",
        provider="procedural",
        quantum_mode="off",
        width=96,
        height=64,
        fps=12,
        chunk_seconds=1.0,
    )
    engine = CosmosMediaEngine(settings)
    engine.provider = FakeProvider()
    return engine


def fake_stitch(chunks: list[Path], destination: Path, run_dir: Path) -> None:
    del run_dir
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_bytes(b"|".join(path.read_bytes() for path in chunks))


def test_image_and_storybook_engine_paths(tmp_path):
    engine = make_engine(tmp_path)
    image = tmp_path / "out" / "one.bin"
    result = engine.generate_image("a remembered garden", image, seed=7)
    assert image.exists()
    assert Path(result["receipt"]).exists()

    book_dir = tmp_path / "book"
    book = engine.generate_storybook(
        "A child finds a glowing seed. The class plants it together.",
        book_dir,
        pages=2,
        seed=9,
    )
    assert book["pages"] == 2
    assert (book_dir / "BOOK.md").exists()
    assert (book_dir / "page-001.png").exists()
    assert (book_dir / "page-002.png").exists()


def test_video_resume_reuses_seed_and_run_checkpoint(tmp_path):
    engine = make_engine(tmp_path)
    engine._stitch = fake_stitch
    output = tmp_path / "out" / "video.bin"

    first = engine.generate_video(
        "a continuous impossible ocean",
        output,
        duration=3.0,
        chunk_seconds=1.0,
        seed=42,
    )
    run_dir = engine.settings.home / "runs" / first["run_id"]
    manifest_path = run_dir / "manifest.json"
    before = json.loads(manifest_path.read_text(encoding="utf-8"))
    before_seed = before["base_seed"]
    before_hashes = [item["seed_hash"] for item in before["chunks"]]

    # Simulate a crash/recovery point after chunk 1 by removing chunk 2 and its
    # checkpoint. Then mutate global engine state to prove resume restores the
    # video-run checkpoint rather than trusting unrelated later state.
    (run_dir / "chunks" / "chunk-00002.mp4").unlink()
    (run_dir / "checkpoints" / "chunk-00002.json").unlink()
    engine.reset_state("unrelated work after interruption")

    resumed = engine.generate_video(
        "a continuous impossible ocean",
        output,
        duration=3.0,
        chunk_seconds=1.0,
        resume_run=first["run_id"],
    )
    after = json.loads(manifest_path.read_text(encoding="utf-8"))

    assert resumed["run_id"] == first["run_id"]
    assert after["base_seed"] == before_seed
    assert [item["seed_hash"] for item in after["chunks"]] == before_hashes
    assert [item["resumed"] for item in after["chunks"]] == [True, True, False]
    assert output.exists()
