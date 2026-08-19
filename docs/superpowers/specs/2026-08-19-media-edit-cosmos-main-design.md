# COSMOS Media Edit + COSMOS Main Model Design

## Goal
Add end-to-end prompt-driven editing for user-uploaded images and videos while making `COSMOS Main` the default switchable model identity across app, API, CLI, and JSONL integration.

## Truth boundary
`phera-ra/QC67_cosmo` is published as a text-generation model. It is therefore used as the default COSMOS controller/planner identity, not falsely described as a native pixel/video diffusion model. Actual visual transformation is performed by a swappable edit renderer. The built-in native renderer provides deterministic, offline image/video transformations for guaranteed local operation; an HTTP edit renderer can be selected for semantic generative edits when a capable image/video model is attached.

## Architecture
The feature is split into four isolated units:

1. **Model registry/controller** (`models.py`) defines `cosmos-main`, `native-edit`, and `http-edit`, persists the user's default model, and reports runtime availability. `cosmos-main` points to `phera-ra/QC67_cosmo` as the controller identity and defaults to the native renderer when no external edit endpoint is configured.
2. **Asset/edit service** (`editing.py`) validates common image/video types, stores uploads under the COSMOS home directory, creates edit jobs/receipts, advances CST state for continuity, and routes edits through the selected model/renderer.
3. **Renderers** (`edit_providers.py`) implement a local Pillow image editor and FFmpeg video editor plus an optional HTTP edit bridge. Native edits are prompt-conditioned and deterministic; video edits preserve audio unless disabled. The HTTP bridge is the extension point for semantic object/background/inpainting/video-diffusion systems.
4. **Surfaces** update FastAPI, CLI, JSONL bridge, and the shared PWA/mobile UI. The UI adds Edit Media, upload preview, model selection, strength, preserve-subject/audio switches, and downloadable output.

## Supported uploads
Images: `.png`, `.jpg`, `.jpeg`, `.webp`.
Videos: `.mp4`, `.mov`, `.webm`, `.m4v`.
Maximum upload size is configurable through `COSMOS_MAX_UPLOAD_MB` and defaults to 256 MB.

## Model routing
- Default model ID: `cosmos-main`.
- `cosmos-main`: controller identity `phera-ra/QC67_cosmo`; renderer uses `COSMOS_EDIT_RENDERER`, default `native`.
- `native-edit`: bypasses the controller identity and forces the offline native renderer.
- `http-edit`: sends the source asset + prompt/settings to `COSMOS_EDIT_ENDPOINT`.
- The chosen model and actual renderer runtime are always written to receipts/status so the system never implies QC67 directly generated pixels when it did not.

## Image editing
Native image editing uses Pillow and prompt-derived transform selection (tone, saturation, contrast, sharpen/soften, monochrome, warm/cool/neon/cinematic treatment) blended against the original by `strength`. It preserves dimensions and source content. Semantic changes such as replacing objects/backgrounds require a capable HTTP edit renderer.

## Video editing
Native video editing invokes FFmpeg with prompt-derived color/effect filters. It preserves the original audio stream by default, maps it when present, and encodes H.264/AAC-compatible MP4 output. The edit job advances COSMOS state once per job and records continuity metadata. External renderers may implement frame/chunk diffusion while retaining the same request/receipt contract.

## API
- `POST /v1/uploads` multipart upload; returns asset metadata.
- `GET /v1/assets/{asset_id}` metadata.
- `GET /v1/models` list models/default.
- `POST /v1/models/default` set persisted default model.
- `POST /v1/edit/image` edit an uploaded image.
- `POST /v1/edit/video` edit an uploaded video.
- `GET /v1/edit/jobs/{job_id}` job metadata.
- Existing `/out` static serving remains the output delivery path.

## CLI
- `cosmos-media edit-image --input ... --prompt ... --out ... [--model ...] [--strength ...]`
- `cosmos-media edit-video --input ... --prompt ... --out ... [--model ...] [--strength ...] [--no-preserve-audio]`
- `cosmos-media models list`
- `cosmos-media models default`
- `cosmos-media models set-default MODEL`

## JSONL bridge
Add operations `models`, `set_default_model`, `edit_image`, and `edit_video`. File paths are local to the COSMOS host.

## UI
The shared PWA/mobile interface gains `Edit Image` and `Edit Video` modes. Selecting an edit mode reveals file upload, model selector, strength, preserve-subject, and preserve-audio controls. The app uploads the file first, then sends the edit request, then previews/shares the `/out` result.

## Error handling
- Reject unsupported extensions, empty files, oversized files, wrong edit/media kind, unknown models, missing endpoints, invalid strength, and missing FFmpeg/Pillow with actionable errors.
- Upload filenames are never trusted; stored files use UUID asset IDs and validated suffixes.
- Job metadata transitions through `queued`, `processing`, `completed`, or `failed` and captures the error message on failure.

## Testing and acceptance
Tests must prove:
- `cosmos-main` is the default and exposes the QC67 controller identity.
- upload validation/storage works.
- native image edit produces a changed valid image.
- native video filter planning is deterministic and audio preservation is requested by default.
- model switching persists.
- CLI/API/JSONL contracts expose the new feature.
- old generation tests remain green.
- CI performs an actual native image edit and short native video edit and uploads those outputs as proof artifacts.
