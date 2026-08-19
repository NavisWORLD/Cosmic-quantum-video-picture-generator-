# COSMOS Media Editing

COSMOS Media v0.3.0 can transform an existing image or video from a prompt through the same engine used for generation, continuity, receipts, desktop/mobile UI, CLI, REST API, and JSONL integration.

## Model architecture

The default edit model ID is **`cosmos-main`**.

`cosmos-main` is intentionally a composite model identity:

- **Controller identity:** `phera-ra/QC67_cosmo`
- **Synaptic continuity:** COSMOS `cosmos.synaptic.v1` state
- **Visual renderer:** selected by `COSMOS_EDIT_RENDERER`

`QC67_cosmo` is published as a text-generation model. COSMOS therefore does **not** claim that QC67 directly renders pixels. Its identity belongs to the controller/planning side of the stack, while the renderer that actually transforms an image/video is recorded separately in every edit result and receipt.

Available model IDs:

| ID | Role | Renderer |
|---|---|---|
| `cosmos-main` | default COSMOS composite model | configured `native` or `http` |
| `native-edit` | guaranteed offline fallback | Pillow + FFmpeg |
| `http-edit` | attach a semantic generative editor | configured HTTP service |

## What the built-in editor does

The native path is deliberately dependency-light and usable offline:

- images: prompt-conditioned contrast, brightness, saturation, sharpness/softness, monochrome, warm/cool/neon/cinematic treatment and deterministic prompt tinting;
- videos: prompt-conditioned FFmpeg color/tone filters, H.264 output, optional original-audio preservation;
- both: COSMOS Synaptic continuity update, asset/job metadata, SHA-256 source/output hashes and edit receipt.

It is a real editor, but it is **not** a hidden diffusion model. Requests that require semantic reconstruction such as “remove this person,” “replace the car with a dragon,” inpainting, identity-conditioned wardrobe changes, or generative background replacement require a capable semantic renderer attached through `http-edit` or by configuring COSMOS Main with `COSMOS_EDIT_RENDERER=http`.

## Supported uploads

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

Maximum upload size defaults to 256 MB and can be changed with `COSMOS_MAX_UPLOAD_MB`.

## App workflow

1. Start COSMOS Media or open the packaged desktop app.
2. Choose **Edit Uploaded Image** or **Edit Uploaded Video**.
3. Choose a file.
4. Leave **COSMOS Main** selected or choose another available model.
5. Enter the requested edit.
6. Set edit strength and preservation options.
7. Press **EDIT // REWRITE THIS MEDIA**.
8. Preview/share the output. The result JSON shows the model, controller identity, actual renderer, job ID, receipt and state hash.

The same interface is used by the browser/PWA and Capacitor Android/iOS shells.

## CLI

```bash
cosmos-media edit-image \
  --input ./photo.png \
  --prompt "warm cinematic neon moonlight" \
  --model cosmos-main \
  --strength 0.7 \
  --out ./edited.png
```

```bash
cosmos-media edit-video \
  --input ./clip.mp4 \
  --prompt "cool cinematic electric night" \
  --model cosmos-main \
  --strength 0.55 \
  --out ./edited.mp4
```

Disable original audio preservation with `--no-preserve-audio`.

Model management:

```bash
cosmos-media models list
cosmos-media models default
cosmos-media models set-default native-edit
cosmos-media models set-default cosmos-main
```

## REST API

Upload media first:

```bash
curl -F "file=@photo.png" http://127.0.0.1:8788/v1/uploads
```

Then use the returned `asset_id`:

```json
POST /v1/edit/image
{
  "asset_id": "...",
  "prompt": "warm cinematic neon moonlight",
  "model": "cosmos-main",
  "strength": 0.7,
  "preserve_subject": true
}
```

Video:

```json
POST /v1/edit/video
{
  "asset_id": "...",
  "prompt": "cool cinematic electric night",
  "model": "cosmos-main",
  "strength": 0.55,
  "preserve_subject": true,
  "preserve_audio": true
}
```

Other endpoints:

- `GET /v1/models`
- `POST /v1/models/default`
- `GET /v1/assets/{asset_id}`
- `GET /v1/edit/jobs/{job_id}`

## JSONL bridge

A host process can call COSMOS without an HTTP client:

```json
{"id":"models","op":"models"}
{"id":"edit","op":"edit_image","input":"./photo.png","prompt":"warm cinematic","output":"out/result.png","model":"cosmos-main"}
```

Operations added in v0.3.0:

- `models`
- `set_default_model`
- `edit_image`
- `edit_video`

## External semantic renderer contract

Set:

```env
COSMOS_EDIT_RENDERER=http
COSMOS_EDIT_ENDPOINT=http://127.0.0.1:9000
```

For direct selection use model ID `http-edit`.

COSMOS sends multipart requests to:

- `POST {COSMOS_EDIT_ENDPOINT}/edit/image`
- `POST {COSMOS_EDIT_ENDPOINT}/edit/video`

Form fields include prompt, negative prompt, strength, preserve-subject, and for video preserve-audio. The source media is sent as `file`.

The renderer may return:

1. raw media bytes;
2. JSON with `data_base64`;
3. JSON with a locally reachable `output_path`; or
4. JSON with a downloadable `url`.

This keeps COSMOS provider-neutral while preserving one stable app/CLI/API/receipt contract.

## Receipts and continuity

Each edit advances a dedicated persisted Synaptic state and emits a `cosmos-media-edit/1` receipt containing:

- asset ID;
- source SHA-256;
- prompt hash;
- Synaptic state hash;
- selected model;
- controller identity, when applicable;
- actual renderer;
- output SHA-256;
- edit parameters;
- receipt hash.

The distinction between **model identity** and **actual renderer** is deliberate and is the provenance boundary used throughout COSMOS Media.
