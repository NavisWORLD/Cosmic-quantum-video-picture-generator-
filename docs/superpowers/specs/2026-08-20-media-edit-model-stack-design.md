# COSMOS Media Edit + Model Stack Design

Date: 2026-08-20

## Goal

Turn COSMOS Media into a prompt-driven editor as well as a generator. A user can upload a supported image or video, describe the requested change, keep **COSMOS Main** as the default first-party model profile, switch model/render backends when desired, and receive a downloadable edited result with Synaptic continuity and provenance receipts.

## Truth boundary

`phera-ra/QC67_cosmo` is a text-generation/controller model, not a diffusion or video-render checkpoint. COSMOS therefore treats **COSMOS Main** as a composite first-party model profile: QC67 is the controller/planning identity, COSMOS owns routing, continuity, job state and receipts, and the selected visual renderer performs the pixel/video transform. Results always report both the controller and the renderer.

The built-in `native` renderer must remain fully offline and testable, but it provides deterministic prompt-conditioned visual transforms rather than unrestricted semantic object synthesis. Semantic edits such as adding/removing objects are enabled through a capable visual backend. The first local semantic backend is a Diffusers adapter, with `Qwen/Qwen-Image-Edit-2511` as the documented image-edit default when the optional heavyweight dependencies/model are installed. HTTP remains the generic bridge for remote or specialized image/video models.

## Architecture

### Model profiles

- `cosmos-main` — default. Controller: `phera-ra/QC67_cosmo`. Renderer: configured per media type.
- `native-edit` — offline Pillow/FFmpeg edit backend.
- `diffusers-edit` — optional local semantic image editor; can also drive chunked framewise video editing through the COSMOS continuity pipeline.
- `http-edit` — external semantic image/video endpoint.

The model registry exposes capabilities and availability. `cosmos-main` resolves to the configured image/video renderer while staying the visible default model identity.

### Upload + validation

Supported images: PNG, JPEG, WEBP.
Supported videos: MP4, MOV, WEBM, M4V.

Uploads are stored under opaque asset IDs. Image uploads are decoded with Pillow before acceptance. Video uploads are probed with FFprobe when available. Extension-only acceptance is not sufficient. Size limits are enforced before storage.

### Image editing

`EditingService.edit_image` accepts source asset, prompt, optional negative prompt, optional mask asset, model, strength and subject-preservation settings. A mask is a grayscale image resized to the source dimensions. The renderer produces an edited image, then COSMOS composites the edited result over the original using the mask so changes are confined to the selected area.

Native image editing remains deterministic and offline. Diffusers loads the configured image edit pipeline lazily and caches it for the process. HTTP sends source plus optional mask to the configured endpoint.

### Video editing

Video editing is chunk-aware. The request accepts `chunk_seconds`, `style_lock` and `temporal_blend`. Native mode applies deterministic FFmpeg filters while preserving optional audio. Semantic framewise mode extracts frames for bounded chunks, edits frames through the image semantic backend with a stable seed/continuity context, blends adjacent edited frames conservatively for temporal smoothing, reassembles the chunks, then restores source audio when requested.

A specialized HTTP video backend may replace framewise semantic editing when configured. The job/receipt records which path was used.

### Synaptic continuity

Every edit advances the existing `cosmos.synaptic.v1` state. Video chunk/frame prompts include source hash, model ID, prompt and chunk/frame index. The same state is carried across chunks. Receipts include state hash, source/output hashes, controller, renderer, model, mask hash when present and edit parameters.

### API / CLI / bridge

REST:
- `POST /v1/uploads`
- `GET /v1/assets/{asset_id}`
- `GET /v1/models`
- `POST /v1/models/default`
- `POST /v1/edit/image`
- `POST /v1/edit/video`
- `GET /v1/edit/jobs/{job_id}`

CLI:
- `cosmos-media edit-image --input ... --prompt ... --out ...`
- `cosmos-media edit-video --input ... --prompt ... --out ...`
- optional `--mask` for image edits
- model selection and model default commands
- chunk/style/temporal controls for video edits

JSONL bridge mirrors image/video edit settings and model selection.

### UI

The shared PWA/mobile/desktop interface keeps one Create/Edit surface. Edit mode includes source upload, optional mask for images, model selector, strength, negative prompt, subject/audio preservation, chunk duration, style lock and temporal smoothing. Source and result previews remain local/engine-backed.

### Packaging

Version remains the current 0.3 line while this feature is finalized. Packaging must include only lightweight runtime dependencies by default. Diffusers/torch/transformers/accelerate are an optional `semantic` extra because the model is tens of gigabytes and unsuitable for bundling in one-click desktop installers. Clean installs still work through native edit; semantic local users opt in, while remote semantic backends use HTTP.

## Security / privacy

- No uploaded file is executed.
- Output paths are created by the engine or explicit CLI arguments.
- Asset IDs are opaque and validated.
- Uploaded bytes never leave the device unless the user selects a remote HTTP renderer.
- Remote-render status is visible in model metadata/receipts.
- Model credentials/tokens remain environment variables and are never written to receipts.

## Acceptance criteria

1. Native image upload + prompt edit works and changes pixels.
2. Masked edits modify only masked regions.
3. Native video upload + prompt edit produces a valid MP4 and can preserve audio.
4. Chunked semantic-video orchestration is implemented and testable without downloading huge models by using an injected/fake image editor in unit tests.
5. `cosmos-main` remains the default and reports QC67 controller plus actual renderer.
6. `diffusers-edit` appears only as available when dependencies/config allow it; missing dependencies fail with an actionable message.
7. HTTP semantic editing remains switchable.
8. API, CLI and JSONL bridge expose the edit controls.
9. Shared PWA/mobile UI exposes upload/edit/model controls.
10. Full Python, Rust, C++, SDK, packaging and media smoke CI remain green.
11. README/manual explain which components are first-party orchestration versus which backend actually renders pixels.
