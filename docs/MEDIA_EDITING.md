# COSMOS Media Editing

COSMOS Media v0.3.0 can transform an existing image or video from a prompt through the same engine used for generation, Synaptic continuity, receipts, desktop/mobile UI, CLI, REST API, and JSONL integration.

## Model architecture

The default edit model ID is **`cosmos-main`**.

`cosmos-main` is intentionally a composite first-party profile:

- **Controller / planning identity:** `phera-ra/QC67_cosmo`
- **Synaptic continuity:** COSMOS `cosmos.synaptic.v1` state
- **Visual renderer:** selected independently for image/video editing

`QC67_cosmo` is a text-generation model. COSMOS therefore does **not** claim that QC67 directly renders pixels. The controller/model identity and the renderer that actually transforms media are recorded separately in edit results and receipts.

Available model IDs:

| ID | Role | Renderer |
|---|---|---|
| `cosmos-main` | default COSMOS composite profile | configured per media type |
| `native-edit` | guaranteed offline fallback | Pillow + FFmpeg |
| `diffusers-edit` | optional local semantic editing | Diffusers image-edit pipeline |
| `http-edit` | external semantic/specialized editor | configured HTTP service |

Configuration:

```env
COSMOS_DEFAULT_MODEL=cosmos-main
COSMOS_EDIT_RENDERER=native
COSMOS_IMAGE_EDIT_RENDERER=
COSMOS_VIDEO_EDIT_RENDERER=
```

Blank per-media values inherit `COSMOS_EDIT_RENDERER`. A useful mixed setup is:

```env
COSMOS_IMAGE_EDIT_RENDERER=diffusers
COSMOS_VIDEO_EDIT_RENDERER=http
COSMOS_EDIT_ENDPOINT=http://127.0.0.1:9000
```

COSMOS Main remains the visible/default first-party profile while the result reports the actual image/video renderer.

## Native editing

The dependency-light offline path supports:

- images: prompt-conditioned contrast, brightness, saturation, sharpness/softness, monochrome, warm/cool/neon/cinematic treatments and deterministic prompt tinting;
- masked images: white mask regions may change while black mask regions are composited back from the exact original image;
- videos: prompt-conditioned FFmpeg color/tone transforms, H.264 output and optional original-audio preservation;
- every edit: validated asset metadata, job record, Synaptic state update, SHA-256 source/output hashes and edit receipt.

Native edit is a real deterministic editor, but it is **not** a hidden diffusion model. Semantic reconstruction such as replacing an object, changing clothing, adding a creature, removing a person, or generating a new background requires `diffusers-edit` or `http-edit`.

## Optional local semantic editing

Install the heavyweight optional stack separately:

```bash
pip install -e '.[semantic]'
```

Default semantic model:

```env
COSMOS_SEMANTIC_IMAGE_MODEL=Qwen/Qwen-Image-Edit-2511
COSMOS_SEMANTIC_DEVICE=auto
COSMOS_SEMANTIC_STEPS=24
COSMOS_IMAGE_EDIT_RENDERER=diffusers
```

`Qwen/Qwen-Image-Edit-2511` is an image-to-image Diffusers model and its repository is roughly 58 GB. COSMOS deliberately does not bundle those weights into its one-click desktop/mobile packages. The model is loaded lazily only when the Diffusers renderer is selected.

Device selection supports `auto`, `cuda`, `mps`, and `cpu`. `auto` prefers CUDA, then Apple MPS, then CPU. Realistic performance and memory requirements depend on the selected semantic model and hardware.

### Semantic video editing

`diffusers-edit` can also process video through COSMOS framewise orchestration:

1. probe source duration/fps;
2. divide the timeline into bounded chunks;
3. extract source frames;
4. edit frames through the semantic image renderer;
5. carry one COSMOS/Synaptic continuity state across chunks;
6. optionally lock the seed/style family across the entire job;
7. apply conservative temporal blending between adjacent edited frames;
8. encode chunk videos;
9. concatenate them;
10. restore source audio when requested.

For dedicated high-end video-to-video models, `http-edit` is usually the better renderer because COSMOS can delegate the actual video transform while retaining its model identity, continuity, job system and receipts.

## Supported uploads and validation

Images:

- `.png`
- `.jpg`
- `.jpeg`
- `.webp`

Videos:

- `.mp4`
- `.mov`
- `.webm`
- `.m4v`

Images are decoded/verified with Pillow instead of trusting the filename extension. Videos are probed with FFprobe when available. Upload size defaults to 256 MB and is controlled by `COSMOS_MAX_UPLOAD_MB`.

## App workflow

1. Start COSMOS Media or the packaged desktop app.
2. Choose **Edit Uploaded Image** or **Edit Uploaded Video**.
3. Choose source media.
4. For images, optionally add a mask.
5. Leave **COSMOS Main** selected or choose another available model.
6. Describe the requested change and optionally describe what to avoid.
7. Set edit strength and preservation controls.
8. For semantic video, choose chunk size, style lock and temporal smoothing.
9. Press **EDIT // REWRITE THIS MEDIA**.
10. Preview/share the output. Result JSON reports model, controller identity, actual renderer, parameters, job ID, receipt and state hash.

The same UI is used by browser/PWA, desktop packaging, and Capacitor Android/iOS shells.

## CLI

Image edit:

```bash
cosmos-media edit-image \
  --input ./photo.png \
  --prompt "replace the background with a moonlit futuristic city" \
  --model cosmos-main \
  --strength 0.7 \
  --out ./edited.png
```

Masked image edit:

```bash
cosmos-media edit-image \
  --input ./photo.png \
  --mask ./mask.png \
  --prompt "replace only the masked sky with an aurora" \
  --out ./masked-edit.png
```

Video edit:

```bash
cosmos-media edit-video \
  --input ./clip.mp4 \
  --prompt "cinematic neon science-fiction night" \
  --model cosmos-main \
  --strength 0.55 \
  --chunk-seconds 6 \
  --temporal-blend 0.12 \
  --out ./edited.mp4
```

Use `--no-style-lock`, `--no-preserve-audio`, or `--no-preserve-subject` when desired.

Model management:

```bash
cosmos-media models list
cosmos-media models default
cosmos-media models set-default native-edit
cosmos-media models set-default diffusers-edit
cosmos-media models set-default cosmos-main
```

## REST API

Upload media first:

```bash
curl -F "file=@photo.png" http://127.0.0.1:8788/v1/uploads
```

Masked image edit (upload the mask separately and use both returned IDs):

```json
POST /v1/edit/image
{
  "asset_id": "source_asset_id",
  "mask_asset_id": "mask_asset_id",
  "prompt": "replace only the masked sky",
  "model": "cosmos-main",
  "strength": 0.7,
  "preserve_subject": true
}
```

Video:

```json
POST /v1/edit/video
{
  "asset_id": "video_asset_id",
  "prompt": "cinematic electric night",
  "model": "cosmos-main",
  "strength": 0.55,
  "preserve_subject": true,
  "preserve_audio": true,
  "chunk_seconds": 6.0,
  "style_lock": true,
  "temporal_blend": 0.12
}
```

Other endpoints:

- `GET /v1/models`
- `POST /v1/models/default`
- `GET /v1/assets/{asset_id}`
- `GET /v1/edit/jobs/{job_id}`
- `GET /v1/capabilities`

## JSONL bridge

A host process can call COSMOS without an HTTP client:

```json
{"id":"models","op":"models"}
{"id":"edit","op":"edit_image","input":"./photo.png","mask":"./mask.png","prompt":"change only the sky","output":"out/result.png","model":"cosmos-main"}
{"id":"video","op":"edit_video","input":"./clip.mp4","prompt":"neon cinematic","chunk_seconds":6,"style_lock":true,"temporal_blend":0.12}
```

The bridge imports file paths into the same opaque-asset system before editing.

## External semantic renderer contract

Set:

```env
COSMOS_IMAGE_EDIT_RENDERER=http
COSMOS_VIDEO_EDIT_RENDERER=http
COSMOS_EDIT_ENDPOINT=http://127.0.0.1:9000
```

COSMOS sends multipart requests to:

- `POST {COSMOS_EDIT_ENDPOINT}/edit/image`
- `POST {COSMOS_EDIT_ENDPOINT}/edit/video`

Image requests can include `file` and `mask`. Video form fields include `preserve_audio`, `chunk_seconds`, `style_lock`, and `temporal_blend` in addition to prompt/model state parameters.

The external renderer may return:

1. raw media bytes;
2. JSON with `data_base64`;
3. JSON with a locally reachable `output_path`; or
4. JSON with a downloadable `url`.

Remote-rendered source media leaves the local device by definition; COSMOS does not send uploads remotely when the selected renderer is `native` or `diffusers`.

## Receipts and continuity

Each edit advances a dedicated persisted Synaptic state and emits a `cosmos-media-edit/1` receipt containing:

- asset ID and source SHA-256;
- prompt hash;
- Synaptic state hash;
- selected COSMOS model profile;
- controller identity, when applicable;
- actual renderer;
- mask asset/hash when used;
- video continuity parameters when used;
- output SHA-256;
- receipt hash.

The distinction between **COSMOS model/controller identity** and **actual renderer** is a deliberate provenance boundary, not marketing shorthand.
