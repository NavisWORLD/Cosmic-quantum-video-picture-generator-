# COSMOS Media Edit + Model Stack Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Finalize prompt-driven image/video editing with COSMOS Main as the default composite model, switchable native/diffusers/http renderers, masked image editing, chunked semantic-video orchestration, full UI/CLI/API/bridge coverage, and regression-safe packaging.

**Architecture:** Extend the existing `EditingService`, `ModelRegistry`, provider layer and shared PWA instead of creating a parallel subsystem. Keep native editing as the zero-dependency testable fallback; add a lazily loaded optional Diffusers renderer for semantic image edits and framewise semantic video orchestration; preserve HTTP as the remote/specialized backend. Every result reports model/controller/renderer and writes a Synaptic continuity receipt.

**Tech Stack:** Python 3.10+, Pillow, FFmpeg/FFprobe, FastAPI, Pydantic, optional PyTorch + Diffusers + Transformers + Accelerate, existing HTML/JS PWA, pytest, GitHub Actions.

**Spec:** `docs/superpowers/specs/2026-08-20-media-edit-model-stack-design.md`

## Global Constraints

- `cosmos-main` remains the default model ID.
- `phera-ra/QC67_cosmo` is identified as the controller/planning model, never as the pixel renderer.
- Native edit works offline on clean packaged installs.
- Semantic local dependencies/model weights are optional and are not bundled into desktop installers.
- Image uploads: PNG/JPEG/WEBP. Video uploads: MP4/MOV/WEBM/M4V.
- Existing Synaptic v1 state and receipts remain backward compatible.
- Existing generator, storybook, SDK, packaging and bridge behavior must remain green.

---

### Task 1: Test the missing media-edit behaviors

**Files:**
- Modify: `tests/test_editing.py`
- Modify: `tests/test_models.py`
- Create: `tests/test_edit_integrator.py`

**Interfaces:**
- Consumes: existing `EditingService`, `ModelRegistry`, provider helpers.
- Produces: failing tests for mask composition, media validation, diffusers availability, video edit parameters and JSONL bridge propagation.

- [ ] Add a test that creates a two-tone source image and half-frame mask, runs native image edit, and asserts pixels outside the mask stay byte/pixel-identical while masked pixels change.
- [ ] Add a test that stores invalid bytes with a valid `.png` suffix and asserts upload/import validation rejects it.
- [ ] Add a test that `diffusers-edit` exists in model registry, reports semantic image capability, and is unavailable when the optional dependency/model configuration is absent.
- [ ] Add a bridge test proving `mask`, `chunk_seconds`, `style_lock`, and `temporal_blend` are accepted and forwarded.
- [ ] Run the targeted tests and confirm they fail specifically because the behaviors are not yet implemented.

### Task 2: Add validated upload metadata and mask support

**Files:**
- Modify: `src/cosmos_media/editing.py`
- Modify: `src/cosmos_media/edit_providers.py`

**Interfaces:**
- Produces: validated image/video assets; optional mask passed as `EditImageJob.mask`; receipt `mask_sha256`.

- [ ] Decode image uploads with Pillow during asset validation and store width/height/format metadata.
- [ ] Probe videos with `ffprobe` when available and record duration/width/height/fps; reject files that cannot be probed when FFprobe is available.
- [ ] Extend `EditImageJob` with `mask: Path | None`.
- [ ] Extend `EditingService.edit_image(..., mask_asset_id: str | None = None)` and validate mask kind=image.
- [ ] Composite provider output over original using the grayscale mask after rendering, guaranteeing unmasked pixels are preserved.
- [ ] Record mask hash in receipts.
- [ ] Run targeted tests until green.

### Task 3: Add the optional local semantic Diffusers renderer

**Files:**
- Modify: `pyproject.toml`
- Modify: `.env.example`
- Modify: `src/cosmos_media/config.py`
- Modify: `src/cosmos_media/models.py`
- Modify: `src/cosmos_media/edit_providers.py`
- Test: `tests/test_models.py`
- Test: `tests/test_editing.py`

**Interfaces:**
- Produces: renderer name `diffusers`, model ID `diffusers-edit`, settings `semantic_image_model`, `semantic_device`, `semantic_steps`.

- [ ] Add optional dependency extra `semantic = [torch, diffusers, transformers, accelerate, safetensors]` without adding it to default desktop/media extras.
- [ ] Add environment settings with default semantic image model `Qwen/Qwen-Image-Edit-2511`, `COSMOS_SEMANTIC_DEVICE=auto`, and bounded inference steps.
- [ ] Register `diffusers-edit` with `image_edit`, `semantic_edit`, and framewise-video capability; mark availability based on importability/config, not on the model being pre-downloaded.
- [ ] Implement lazy `DiffusersEditProvider` loading via `DiffusionPipeline.from_pretrained`, device selection (`cuda`, `mps`, `cpu`) and cached pipeline reuse.
- [ ] Run semantic image edit with source image, prompt, negative prompt when supported, and deterministic generator/seed derived from job state.
- [ ] Apply optional mask composition after generation.
- [ ] Missing packages/model load errors must produce actionable runtime errors instead of silent fallback.
- [ ] Run tests with the provider uninstalled and confirm registry/error behavior is green without downloading weights.

### Task 4: Build chunked semantic video editing

**Files:**
- Modify: `src/cosmos_media/edit_providers.py`
- Modify: `src/cosmos_media/editing.py`
- Test: `tests/test_editing.py`

**Interfaces:**
- Extend `EditVideoJob` with `chunk_seconds: float`, `style_lock: bool`, `temporal_blend: float`.
- Renderer behavior: native remains FFmpeg filter; diffusers performs bounded frame extraction/edit/reassembly; HTTP forwards the parameters.

- [ ] Add validation for chunk seconds > 0 and temporal blend in [0,1].
- [ ] Implement FFmpeg frame extraction into bounded temporary chunks for semantic framewise mode.
- [ ] Edit each frame through the semantic image provider using a stable per-job seed and continuity suffix (`chunk=N frame=M`).
- [ ] When `style_lock` is true, keep the same prompt/seed family across the whole job.
- [ ] Blend each edited frame with the previous edited frame by `temporal_blend` before writing it, reducing flicker without overwriting motion.
- [ ] Reassemble frames at source fps and reattach source audio when `preserve_audio` is true.
- [ ] Clean temporary working directories in `finally` blocks.
- [ ] Unit-test orchestration with an injected tiny fake semantic frame editor, not a heavyweight model download.
- [ ] Run native real-FFmpeg video smoke test.

### Task 5: Expose the completed controls through API, CLI and JSONL bridge

**Files:**
- Modify: `src/cosmos_media/api.py`
- Modify: `src/cosmos_media/cli.py`
- Modify: `src/cosmos_media/integrator.py`
- Test: `tests/test_edit_integrator.py`

**Interfaces:**
- Image: `mask_asset_id` / CLI `--mask`.
- Video: `chunk_seconds`, `style_lock`, `temporal_blend`.

- [ ] Extend Pydantic image/video edit request models with the new fields and bounds.
- [ ] Add CLI `--mask`, `--chunk-seconds`, `--no-style-lock`, `--temporal-blend`.
- [ ] Extend JSONL bridge propagation for the same settings.
- [ ] Add capabilities metadata for mask and semantic renderer support.
- [ ] Run API import, CLI parser and bridge tests.

### Task 6: Finish the shared desktop/web/mobile Edit Media UI

**Files:**
- Modify: `apps/pwa/index.html`
- Modify: `apps/pwa/app.js`

**Interfaces:**
- Uses existing `/v1/uploads`, `/v1/models`, `/v1/edit/image`, `/v1/edit/video`.

- [ ] Add optional image-mask upload/preview visible only in image-edit mode.
- [ ] Add video chunk seconds, style lock and temporal smoothing controls visible only in video-edit mode.
- [ ] Upload the mask as a second asset and send `mask_asset_id`.
- [ ] Show controller/renderer distinction in model notes and results.
- [ ] Keep existing mobile engine URL and sharing behavior.
- [ ] Add lightweight JS/static checks to CI so missing element IDs or syntax errors fail before packaging.

### Task 7: Documentation, configuration and packaging regression

**Files:**
- Modify: `README.md`
- Modify: `docs/MEDIA_EDITING.md` or create it if missing
- Modify: `.env.example`
- Modify: `.github/workflows/ci.yml`
- Modify: `.github/workflows/package-ci.yml` only if needed for UI/static checks

**Interfaces:**
- Documents exact model/controller/renderer boundary and install commands.

- [ ] Document native versus semantic editing honestly.
- [ ] Document `pip install -e '.[semantic]'` and the heavyweight model/storage expectation.
- [ ] Document Qwen Image Edit as the optional default semantic image model and HTTP as the preferred specialized video backend when available.
- [ ] Add CI smoke for native image edit, masked image edit and native video edit.
- [ ] Run the complete Python suite, Rust tests, C++ tests, SDK CI-compatible commands and package CI.

### Task 8: Final verification, PR, merge and release-state check

**Files:**
- No production changes unless verification finds a defect.

**Interfaces:**
- Produces merged `main` with all checks green.

- [ ] Open a PR from `agent/media-edit-model-stack` to `main`.
- [ ] Wait for all triggered checks and inspect failures rather than merging around them.
- [ ] Fix failures test-first and rerun until green.
- [ ] Merge only when engine, editing, SDK and packaging checks are green.
- [ ] Verify `main` head matches the merge commit and post-merge CI passes.
- [ ] Verify current release metadata accurately reflects whether the new edit stack is included; do not claim a public binary contains code it predates.
