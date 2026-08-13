from __future__ import annotations

from datetime import datetime, timezone
import json
from pathlib import Path
import shutil
import subprocess
import uuid
from typing import Any

from .branching import search_branches
from .config import Settings
from .provenance import GenerationReceipt, QuantumReceipt, mix_seed, sha256_text
from .providers import ImageJob, VideoJob, make_provider
from .quantum import get_entropy, quantum_status
from .state import CSTState, HebbianAssociator
from .storybook import plan_storybook, story_markdown
from .timeline import plan_timeline


class CosmosMediaEngine:
    def __init__(self, settings: Settings | None = None):
        self.settings = settings or Settings()
        self.settings.ensure_dirs()
        self.provider = make_provider(self.settings)
        self.state, self.associator = self._load_state()

    @property
    def _state_path(self) -> Path:
        return self.settings.home / "state" / "current.json"

    def _load_state(self) -> tuple[CSTState, HebbianAssociator]:
        path = self._state_path
        if not path.exists():
            return CSTState(), HebbianAssociator()
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            state_data = data.get("state", {})
            state = CSTState(
                list(state_data.get("values", [0.0] * 12)),
                int(state_data.get("step_index", 0)),
            )
            hebbian_data = data.get("hebbian", {})
            associator = HebbianAssociator(
                learning_rate=float(hebbian_data.get("learning_rate", 0.04)),
                decay=float(hebbian_data.get("decay", 0.995)),
            )
            weights = hebbian_data.get("weights")
            if (
                isinstance(weights, list)
                and len(weights) == 12
                and all(isinstance(row, list) and len(row) == 12 for row in weights)
            ):
                associator.weights = [[float(v) for v in row] for row in weights]
            return state, associator
        except Exception:
            # Corrupt state should not make the media engine unbootable.
            return CSTState(), HebbianAssociator()

    def _save_state(self) -> None:
        payload = {
            "state": self.state.to_dict(),
            "hebbian": self.associator.to_dict(),
            "saved_at": datetime.now(timezone.utc).isoformat(),
        }
        self._state_path.parent.mkdir(parents=True, exist_ok=True)
        temp = self._state_path.with_suffix(".tmp")
        temp.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        temp.replace(self._state_path)

    def reset_state(self, context: str = "") -> dict[str, Any]:
        self.state = CSTState.from_context(context) if context else CSTState()
        self.associator = HebbianAssociator()
        self._save_state()
        return self.state.to_dict()

    def _advance(self, stimulus: str) -> CSTState:
        before = self.state
        bias = self.associator.project(before)
        after = before.step(stimulus, association_bias=bias)
        self.associator.update(before, after)
        self.state = after
        return after

    def _new_run(self, kind: str) -> tuple[str, Path]:
        stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        run_id = f"{kind}-{stamp}-{uuid.uuid4().hex[:8]}"
        directory = self.settings.home / "runs" / run_id
        directory.mkdir(parents=True, exist_ok=False)
        return run_id, directory

    def _base_seed(
        self,
        *,
        prompt: str,
        context: str,
        explicit_seed: int | None,
    ) -> tuple[int, str, QuantumReceipt | None]:
        if explicit_seed is not None:
            seed, digest = mix_seed(
                self.settings.seed_namespace,
                "explicit",
                int(explicit_seed),
                prompt,
                context,
                self.state.hash(),
            )
            return seed, digest, QuantumReceipt(mode="explicit", source="user-seed")
        entropy = get_entropy(self.settings, size=64)
        seed, digest = mix_seed(
            self.settings.seed_namespace,
            prompt,
            context,
            self.state.hash(),
            entropy.payload,
        )
        return seed, digest, entropy.receipt

    def generate_image(
        self,
        prompt: str,
        output: str | Path,
        *,
        context: str = "",
        seed: int | None = None,
        width: int | None = None,
        height: int | None = None,
    ) -> dict[str, Any]:
        if not prompt.strip():
            raise ValueError("prompt must not be empty")
        run_id, run_dir = self._new_run("image")
        destination = Path(output)
        destination.parent.mkdir(parents=True, exist_ok=True)
        base_seed, seed_hash, quantum_receipt = self._base_seed(
            prompt=prompt,
            context=context,
            explicit_seed=seed,
        )
        state = self._advance(f"image|{prompt}|{context}|{base_seed}")
        job = ImageJob(
            prompt=prompt,
            context=context,
            seed=base_seed,
            width=int(width or self.settings.width),
            height=int(height or self.settings.height),
            state=state.values.copy(),
            output=destination,
        )
        rendered = self.provider.generate_image(job)
        receipt = GenerationReceipt(
            run_id=run_id,
            kind="image",
            prompt_hash=sha256_text(prompt),
            context_hash=sha256_text(context),
            state_hash=state.hash(),
            seed=base_seed,
            seed_hash=seed_hash,
            provider=self.provider.name,
            parameters={"width": job.width, "height": job.height},
            outputs=[str(rendered)],
            quantum=quantum_receipt,
        )
        receipt_path = receipt.write(run_dir / "receipt.json")
        (run_dir / "state.json").write_text(
            json.dumps(state.to_dict(), indent=2), encoding="utf-8"
        )
        self._save_state()
        return {
            "output": str(rendered),
            "receipt": str(receipt_path),
            "run_id": run_id,
            "state": state.to_dict(),
        }

    def generate_video(
        self,
        prompt: str,
        output: str | Path,
        *,
        duration: float,
        context: str = "",
        seed: int | None = None,
        width: int | None = None,
        height: int | None = None,
        fps: int | None = None,
        chunk_seconds: float | None = None,
        overlap_seconds: float = 0.5,
        resume_run: str | None = None,
    ) -> dict[str, Any]:
        if not prompt.strip():
            raise ValueError("prompt must not be empty")

        chunk_seconds_v = float(chunk_seconds or self.settings.chunk_seconds)
        chunks = plan_timeline(
            duration,
            chunk_seconds=chunk_seconds_v,
            overlap_seconds=overlap_seconds,
        )
        prompt_hash = sha256_text(prompt)
        context_hash = sha256_text(context)

        if resume_run:
            run_id = resume_run
            run_dir = self.settings.home / "runs" / run_id
            if not run_dir.exists():
                raise ValueError(f"resume run does not exist: {run_id}")
        else:
            run_id, run_dir = self._new_run("video")

        chunk_dir = run_dir / "chunks"
        chunk_dir.mkdir(parents=True, exist_ok=True)
        destination = Path(output)
        destination.parent.mkdir(parents=True, exist_ok=True)
        manifest_path = run_dir / "manifest.json"

        width_v = int(width or self.settings.width)
        height_v = int(height or self.settings.height)
        fps_v = int(fps or self.settings.fps)

        if resume_run:
            if not manifest_path.exists():
                raise ValueError(
                    f"resume run {run_id!r} has no manifest.json; refusing to sample a new base seed"
                )
            prior_manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            checks = {
                "prompt_hash": prompt_hash,
                "context_hash": context_hash,
                "duration": float(duration),
                "chunk_seconds": chunk_seconds_v,
                "fps": fps_v,
                "width": width_v,
                "height": height_v,
                "provider": self.provider.name,
            }
            for key, expected in checks.items():
                actual = prior_manifest.get(key)
                if actual != expected:
                    raise ValueError(
                        f"resume mismatch for {key}: original={actual!r}, requested={expected!r}"
                    )
            if "base_seed" not in prior_manifest or "base_seed_hash" not in prior_manifest:
                raise ValueError(
                    "resume manifest predates deterministic-resume support; rerun with an explicit --seed"
                )
            base_seed = int(prior_manifest["base_seed"])
            seed_hash = str(prior_manifest["base_seed_hash"])
            quantum_receipt = QuantumReceipt(
                mode="resume",
                source="manifest-base-seed",
                result_hash=seed_hash,
            )
        else:
            base_seed, seed_hash, quantum_receipt = self._base_seed(
                prompt=prompt,
                context=context,
                explicit_seed=seed,
            )

        manifest: dict[str, Any] = {
            "run_id": run_id,
            "prompt_hash": prompt_hash,
            "context_hash": context_hash,
            "duration": float(duration),
            "chunk_seconds": chunk_seconds_v,
            "fps": fps_v,
            "width": width_v,
            "height": height_v,
            "provider": self.provider.name,
            "base_seed": base_seed,
            "base_seed_hash": seed_hash,
            "chunks": [],
        }
        # Persist the base seed before expensive work so an interruption after
        # chunk zero can resume the exact same trajectory.
        manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")

        previous_output: str | None = None
        rendered_paths: list[Path] = []
        for plan in chunks:
            chunk_seed, chunk_seed_hash = mix_seed(
                self.settings.seed_namespace,
                base_seed,
                prompt,
                plan.index,
                plan.start,
                plan.duration,
            )
            chunk_path = chunk_dir / f"chunk-{plan.index:05d}.mp4"
            skipped = chunk_path.exists() and chunk_path.stat().st_size > 0

            if skipped:
                # The persisted global state was advanced after every completed
                # chunk in the original run. Do not advance it twice on resume.
                state = self.state
            else:
                state = self._advance(
                    f"video|{prompt}|chunk={plan.index}|"
                    f"progress={plan.narrative_progress:.9f}|seed={chunk_seed}"
                )
                continuity = {
                    "index": plan.index,
                    "start": plan.start,
                    "narrative_progress": plan.narrative_progress,
                    "overlap_before": plan.overlap_before,
                    "overlap_after": plan.overlap_after,
                    "previous_output": previous_output,
                    "state_hash": state.hash(),
                }
                self.provider.generate_video(
                    VideoJob(
                        prompt=prompt,
                        context=context,
                        seed=chunk_seed,
                        width=width_v,
                        height=height_v,
                        fps=fps_v,
                        duration=plan.duration,
                        state=state.values.copy(),
                        output=chunk_path,
                        continuity=continuity,
                    )
                )
                self._save_state()

            rendered_paths.append(chunk_path)
            previous_output = str(chunk_path)
            manifest["chunks"].append(
                {
                    **plan.to_dict(),
                    "path": str(chunk_path),
                    "seed_hash": chunk_seed_hash,
                    "state_hash": state.hash(),
                    "resumed": skipped,
                }
            )
            # Persist progress after each chunk so interruption loses at most one clip.
            manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")

        self._stitch(rendered_paths, destination, run_dir)
        receipt = GenerationReceipt(
            run_id=run_id,
            kind="video",
            prompt_hash=prompt_hash,
            context_hash=context_hash,
            state_hash=self.state.hash(),
            seed=base_seed,
            seed_hash=seed_hash,
            provider=self.provider.name,
            parameters={
                "duration": float(duration),
                "chunks": len(chunks),
                "chunk_seconds": chunk_seconds_v,
                "overlap_seconds": overlap_seconds,
                "width": width_v,
                "height": height_v,
                "fps": fps_v,
            },
            outputs=[str(destination)],
            quantum=quantum_receipt,
        )
        receipt_path = receipt.write(run_dir / "receipt.json")
        return {
            "output": str(destination),
            "receipt": str(receipt_path),
            "manifest": str(manifest_path),
            "run_id": run_id,
            "chunks": len(chunks),
            "state": self.state.to_dict(),
        }

    def _stitch(self, chunks: list[Path], destination: Path, run_dir: Path) -> None:
        if not chunks:
            raise RuntimeError("no video chunks were rendered")
        if len(chunks) == 1:
            shutil.copy2(chunks[0], destination)
            return

        concat_file = run_dir / "concat.txt"
        lines: list[str] = []
        for path in chunks:
            escaped = path.resolve().as_posix().replace("'", "'\\''")
            lines.append(f"file '{escaped}'")
        concat_file.write_text("\n".join(lines) + "\n", encoding="utf-8")

        base = [
            self.settings.ffmpeg,
            "-y",
            "-f",
            "concat",
            "-safe",
            "0",
            "-i",
            str(concat_file),
        ]
        copy_cmd = base + ["-c", "copy", "-movflags", "+faststart", str(destination)]
        try:
            subprocess.run(copy_cmd, check=True, capture_output=True)
            return
        except (FileNotFoundError, subprocess.CalledProcessError):
            pass

        transcode_cmd = base + [
            "-c:v",
            "libx264",
            "-preset",
            "veryfast",
            "-pix_fmt",
            "yuv420p",
            "-movflags",
            "+faststart",
            str(destination),
        ]
        try:
            subprocess.run(transcode_cmd, check=True, capture_output=True)
        except FileNotFoundError as exc:
            raise RuntimeError(
                "FFmpeg was not found. Install ffmpeg or set COSMOS_FFMPEG."
            ) from exc
        except subprocess.CalledProcessError as exc:
            stderr = exc.stderr.decode("utf-8", errors="replace")[-2500:]
            raise RuntimeError(f"FFmpeg could not stitch chunks: {stderr}") from exc

    def generate_storybook(
        self,
        context: str,
        output_dir: str | Path,
        *,
        pages: int = 8,
        title: str = "COSMOS Storybook",
        style: str = "cinematic storybook realism",
        seed: int | None = None,
    ) -> dict[str, Any]:
        if not context.strip():
            raise ValueError("context must not be empty")
        run_id, run_dir = self._new_run("storybook")
        destination = Path(output_dir)
        destination.mkdir(parents=True, exist_ok=True)
        scenes = plan_storybook(context, pages=pages, style=style)
        base_seed, seed_hash, quantum_receipt = self._base_seed(
            prompt=title,
            context=context,
            explicit_seed=seed,
        )
        outputs: list[str] = []
        scene_records: list[dict[str, Any]] = []
        for scene in scenes:
            page_seed, page_seed_hash = mix_seed(
                self.settings.seed_namespace,
                base_seed,
                scene.page,
                scene.image_prompt,
            )
            state = self._advance(
                f"storybook|page={scene.page}|{scene.image_prompt}|{page_seed}"
            )
            page_path = destination / f"page-{scene.page:03d}.png"
            self.provider.generate_image(
                ImageJob(
                    prompt=scene.image_prompt,
                    context=context,
                    seed=page_seed,
                    width=self.settings.width,
                    height=self.settings.height,
                    state=state.values.copy(),
                    output=page_path,
                )
            )
            outputs.append(str(page_path))
            record = scene.to_dict()
            record.update(
                {
                    "image": str(page_path),
                    "seed_hash": page_seed_hash,
                    "state_hash": state.hash(),
                }
            )
            scene_records.append(record)
            self._save_state()

        (destination / "storybook.json").write_text(
            json.dumps(
                {"title": title, "scenes": scene_records}, indent=2, ensure_ascii=False
            ),
            encoding="utf-8",
        )
        (destination / "BOOK.md").write_text(
            story_markdown(title, scenes), encoding="utf-8"
        )
        receipt = GenerationReceipt(
            run_id=run_id,
            kind="storybook",
            prompt_hash=sha256_text(title),
            context_hash=sha256_text(context),
            state_hash=self.state.hash(),
            seed=base_seed,
            seed_hash=seed_hash,
            provider=self.provider.name,
            parameters={"pages": len(scenes), "style": style, "title": title},
            outputs=outputs,
            quantum=quantum_receipt,
        )
        receipt_path = receipt.write(run_dir / "receipt.json")
        return {
            "output_dir": str(destination),
            "book": str(destination / "BOOK.md"),
            "manifest": str(destination / "storybook.json"),
            "receipt": str(receipt_path),
            "run_id": run_id,
            "pages": len(scenes),
        }

    def branch_search(
        self, prompt: str, count: int | None = None
    ) -> list[dict[str, Any]]:
        return [
            candidate.to_dict()
            for candidate in search_branches(
                prompt,
                self.state,
                namespace=self.settings.seed_namespace,
                count=count or self.settings.branches,
            )
        ]

    def status(self) -> dict[str, Any]:
        return {
            "engine": "cosmos-quantum-media/0.1.0",
            "provider": self.provider.name,
            "settings": self.settings.public_dict(),
            "state": self.state.to_dict(),
            "quantum": quantum_status(self.settings),
        }
