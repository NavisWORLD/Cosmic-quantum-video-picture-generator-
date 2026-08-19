# COSMOS Media Edit + COSMOS Main Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add prompt-driven image/video editing with `COSMOS Main` as the default switchable model identity across CLI, API, JSONL bridge, and shared desktop/mobile UI.

**Architecture:** Keep editing isolated from the existing generation engine. A model registry chooses `cosmos-main`, `native-edit`, or `http-edit`; an edit service owns uploads/jobs/state/receipts; edit providers own Pillow/FFmpeg/HTTP transformation; existing surfaces call the service. `phera-ra/QC67_cosmo` is the default controller identity while actual pixels are produced by the selected edit renderer.

**Tech Stack:** Python 3.10+, Pillow, FFmpeg, httpx, FastAPI + python-multipart, existing CST state/receipts, vanilla JS PWA/Capacitor wrapper, pytest, GitHub Actions.

**Spec:** `docs/superpowers/specs/2026-08-19-media-edit-cosmos-main-design.md`

## Global Constraints
- Existing generation/image/video/storybook behavior must remain backward compatible.
- Default model ID is exactly `cosmos-main`.
- COSMOS Main controller repo ID is exactly `phera-ra/QC67_cosmo`.
- Native editing must work offline with Pillow + FFmpeg.
- Semantic generative editing is an optional HTTP renderer capability; do not claim QC67 directly renders pixels.
- Supported images: png, jpg, jpeg, webp. Supported videos: mp4, mov, webm, m4v.
- Maximum upload size defaults to 256 MB and is configurable.
- Every edit result records chosen model, actual renderer, prompt hash, source hash, state hash, and output path.

---

### Task 1: Write acceptance tests first

**Files:**
- Create: `tests/test_editing.py`
- Create: `tests/test_models.py`

**Interfaces:**
- Consumes: `Settings`, future `ModelRegistry`, future `EditingService`.
- Produces: executable behavior specification for model defaults, uploads, native image edits, prompt filter planning, and persisted model switching.

- [ ] **Step 1: Add failing model registry tests**

```python
from cosmos_media.models import ModelRegistry

def test_cosmos_main_is_default(tmp_path):
    registry = ModelRegistry(tmp_path)
    assert registry.default_id == "cosmos-main"
    model = registry.get("cosmos-main")
    assert model.controller_repo == "phera-ra/QC67_cosmo"
    assert model.default is True
```

- [ ] **Step 2: Add failing editing tests**

```python
from PIL import Image
from cosmos_media.editing import EditingService


def test_upload_and_native_image_edit(tmp_path, settings):
    source = tmp_path / "source.png"
    Image.new("RGB", (64, 48), (40, 60, 80)).save(source)
    service = EditingService(settings)
    asset = service.import_file(source)
    result = service.edit_image(asset["asset_id"], "warm cinematic neon", tmp_path / "edited.png", model="native-edit", strength=0.8)
    assert (tmp_path / "edited.png").exists()
    assert result["model"] == "native-edit"
    assert result["renderer"] == "native"
```

- [ ] **Step 3: Push the test-only commit and confirm CI fails because modules do not exist.**

### Task 2: Model registry + COSMOS Main controller identity

**Files:**
- Create: `src/cosmos_media/models.py`
- Modify: `src/cosmos_media/config.py`
- Modify: `.env.example`

**Interfaces:**
- Produces: `ModelSpec`, `ModelRegistry`, `Settings.default_model`, `Settings.edit_renderer`, `Settings.edit_endpoint`, `Settings.max_upload_mb`.

- [ ] **Step 1:** Implement model specs for `cosmos-main`, `native-edit`, and `http-edit`.
- [ ] **Step 2:** Persist default model to `<COSMOS_HOME>/state/model.json`.
- [ ] **Step 3:** Add configuration/environment variables and public status fields.
- [ ] **Step 4:** Run `pytest tests/test_models.py` until green.

### Task 3: Native + HTTP edit providers

**Files:**
- Create: `src/cosmos_media/edit_providers.py`

**Interfaces:**
- Produces: `EditImageJob`, `EditVideoJob`, `NativeEditProvider`, `HttpEditProvider`, `make_edit_provider`, `prompt_video_filter`.

- [ ] **Step 1:** Implement deterministic prompt classification and Pillow transformations.
- [ ] **Step 2:** Implement FFmpeg prompt filter planning and audio-preserving video command.
- [ ] **Step 3:** Implement HTTP multipart bridge for external semantic editors.
- [ ] **Step 4:** Run provider-focused tests.

### Task 4: Upload, edit job, CST continuity, receipts

**Files:**
- Create: `src/cosmos_media/editing.py`

**Interfaces:**
- Produces: `EditingService.import_file`, `store_upload`, `asset`, `edit_image`, `edit_video`, `job`, `models`, `set_default_model`.

- [ ] **Step 1:** Validate suffix/size and store UUID-named assets.
- [ ] **Step 2:** Load/save edit CST/Hebbian state under COSMOS home.
- [ ] **Step 3:** Route via model registry and edit providers.
- [ ] **Step 4:** Write job JSON and receipt JSON with source/output hashes and actual renderer.
- [ ] **Step 5:** Run `pytest tests/test_editing.py` until green.

### Task 5: API surface

**Files:**
- Modify: `src/cosmos_media/api.py`
- Modify: `pyproject.toml`

**Interfaces:**
- Produces endpoints `/v1/uploads`, `/v1/assets/{id}`, `/v1/models`, `/v1/models/default`, `/v1/edit/image`, `/v1/edit/video`, `/v1/edit/jobs/{id}`.

- [ ] **Step 1:** Add `python-multipart` to server/all extras.
- [ ] **Step 2:** Add request models and upload route.
- [ ] **Step 3:** Add model and edit routes.
- [ ] **Step 4:** Add API tests or compile/runtime smoke.

### Task 6: CLI + JSONL integration

**Files:**
- Modify: `src/cosmos_media/cli.py`
- Modify: `src/cosmos_media/integrator.py`

**Interfaces:**
- Produces CLI commands `edit-image`, `edit-video`, `models ...`; bridge ops `models`, `set_default_model`, `edit_image`, `edit_video`.

- [ ] **Step 1:** Add CLI parsers/options and command handlers.
- [ ] **Step 2:** Add JSONL capabilities and operation handlers.
- [ ] **Step 3:** Smoke both paths against real local files.

### Task 7: Shared desktop/PWA/mobile UI

**Files:**
- Modify: `apps/pwa/index.html`
- Modify: `apps/pwa/app.js`

**Interfaces:**
- Adds Edit Image/Edit Video modes, upload file control, model selector, edit strength, preserve subject/audio controls, upload + edit flow, output preview/share.

- [ ] **Step 1:** Add edit controls without breaking existing generation modes.
- [ ] **Step 2:** Load model list from `/v1/models` and default to COSMOS Main.
- [ ] **Step 3:** Upload via multipart to `/v1/uploads`, then submit JSON edit request.
- [ ] **Step 4:** Preview returned image/video through existing `/out` URL logic.

### Task 8: CI proof + docs

**Files:**
- Modify: `.github/workflows/ci.yml`
- Modify: `README.md`
- Create: `docs/MEDIA_EDITING.md`

**Interfaces:**
- CI generates a source fixture, edits an actual image, edits an actual short video, verifies outputs, verifies `cosmos-main` default, and uploads proof artifacts.

- [ ] **Step 1:** Add native edit smoke steps to CI.
- [ ] **Step 2:** Document model truth boundary and switchability.
- [ ] **Step 3:** Document CLI/API/app usage and external semantic renderer contract.

### Task 9: Final verification and merge

- [ ] **Step 1:** Run/observe full Python, Rust, C++, SDK, C ABI, and packaging workflows for the PR head.
- [ ] **Step 2:** Inspect CI proof artifacts and verify non-empty edited image/video.
- [ ] **Step 3:** Review PR diff for unrelated changes and secrets.
- [ ] **Step 4:** Merge only if required checks are green; report any credential-dependent boundaries separately.
