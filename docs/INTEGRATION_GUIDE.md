# Integration Guide

## Goal

COSMOS Quantum Media is designed to be attached to another generator, render farm, game engine, local AI stack, or engineering environment without importing the whole Python implementation.

There are three integration levels:

1. **REST API client** — easiest and language-neutral.
2. **HTTP media-provider adapter** — let COSMOS orchestrate your renderer.
3. **Native core embedding** — use the Rust or C++ timeline/state primitives inside your own process.

## 1. Run the COSMOS API

```bash
pip install -e ".[server,media]"
cosmos-media serve
```

Default base URL:

```text
http://127.0.0.1:8788
```

Health:

```bash
curl http://127.0.0.1:8788/v1/health
```

## 2. Generate an image through REST

```bash
curl -X POST http://127.0.0.1:8788/v1/image \
  -H "content-type: application/json" \
  -d '{
    "prompt": "a glass observatory above a violet ocean",
    "context": "the same explorer from the previous scene returns at dawn",
    "output": "out/example.png"
  }'
```

Response shape:

```json
{
  "output": "out/example.png",
  "receipt": ".cosmos-media/runs/image-.../receipt.json",
  "run_id": "image-...",
  "state": {
    "values": [0.0, 0.0],
    "step_index": 1,
    "hash": "..."
  }
}
```

The actual state array contains 12 values.

## 3. Generate long-form video

```bash
curl -X POST http://127.0.0.1:8788/v1/video \
  -H "content-type: application/json" \
  -d '{
    "prompt": "continuous expedition across an impossible ocean world",
    "context": "keep the same vessel, weather system, crew, and camera grammar",
    "duration": 3600,
    "chunk_seconds": 8,
    "output": "out/one-hour.mp4"
  }'
```

COSMOS will create the chunk plan first and then render each chunk. The provider receives continuity metadata including the previous output path and narrative progress.

## 4. Resume an interrupted video

The video response contains a `run_id`. Reuse it:

```json
{
  "prompt": "same prompt as the original run",
  "duration": 3600,
  "resume_run": "video-20260812T...",
  "output": "out/one-hour.mp4"
}
```

Existing non-empty chunk files are skipped. Keep prompt/settings stable when resuming if reproducibility matters.

## 5. Storybook endpoint

```bash
curl -X POST http://127.0.0.1:8788/v1/storybook \
  -H "content-type: application/json" \
  -d '{
    "title": "The Lantern Orchard",
    "context": "A student finds a tiny glowing seed behind the school. The class plants it together. By winter it has grown into a tree that lights the playground.",
    "pages": 8,
    "output_dir": "out/lantern-orchard"
  }'
```

Outputs:

```text
out/lantern-orchard/
  BOOK.md
  storybook.json
  page-001.png
  page-002.png
  ...
```

## 6. Computational branch search

```bash
curl -X POST http://127.0.0.1:8788/v1/branch-search \
  -H "content-type: application/json" \
  -d '{"prompt":"a silent city waking at sunrise","count":6}'
```

The result is ordered best-first by the built-in continuity/diversity/reward heuristic. A production system can replace or extend this with a learned scorer.

## 7. Attach your own media renderer

Set:

```bash
COSMOS_MEDIA_PROVIDER=http
COSMOS_MEDIA_ENDPOINT=http://127.0.0.1:9000
```

Your service must implement:

```text
POST /generate/image
POST /generate/video
```

### Image request

```json
{
  "prompt": "...",
  "context": "...",
  "seed": 123456789,
  "width": 1024,
  "height": 576,
  "state": [0.12, -0.07, 0.31, 0.0, 0.21, -0.18, 0.09, 0.4, -0.11, 0.08, 0.03, 0.15]
}
```

### Video request

```json
{
  "prompt": "...",
  "context": "...",
  "seed": 123456789,
  "width": 1024,
  "height": 576,
  "fps": 24,
  "duration": 8.0,
  "state": [0.12, -0.07, 0.31, 0.0, 0.21, -0.18, 0.09, 0.4, -0.11, 0.08, 0.03, 0.15],
  "continuity": {
    "index": 7,
    "start": 56.0,
    "narrative_progress": 0.42,
    "overlap_before": 0.5,
    "overlap_after": 0.5,
    "previous_output": ".cosmos-media/runs/.../chunk-00006.mp4",
    "state_hash": "..."
  }
}
```

### Provider response formats

Return exactly one of these patterns.

#### Raw media bytes

Use a media content type such as `image/png`, `image/jpeg`, `video/mp4`, or `application/octet-stream`.

#### Base64 JSON

```json
{"data_base64":"iVBORw0KGgo..."}
```

#### Shared filesystem path

```json
{"path":"/shared/render-123.png"}
```

The COSMOS process must be able to read that path.

#### Downloadable URL

```json
{"url":"https://your-render-service.example/output/123.mp4"}
```

COSMOS downloads it into the run output path.

## 8. Mapping COSMOS state into a model

The provider is free to interpret the 12 state values. Useful mappings include:

- camera energy;
- motion magnitude;
- color temperature;
- depth-of-field preference;
- shot scale;
- environmental volatility;
- character intimacy;
- texture complexity;
- lighting contrast;
- surrealism strength;
- continuity weight;
- novelty pressure.

Do not assume those semantic names are intrinsic to the vector. If you use a learned mapping, document and version it.

## 9. ComfyUI-style bridge pattern

A practical adapter can translate each COSMOS request into a stored workflow template:

```text
COSMOS JSON
  -> replace positive prompt
  -> replace seed
  -> replace width/height/frames
  -> map CST state to selected node parameters
  -> submit workflow
  -> poll completion
  -> return image/video bytes or path
```

Keep the ComfyUI-specific logic in the adapter service. That prevents COSMOS core from being tied to one workflow schema.

## 10. Node / browser client

```js
const response = await fetch('http://127.0.0.1:8788/v1/image', {
  method: 'POST',
  headers: {'content-type':'application/json'},
  body: JSON.stringify({
    prompt: 'moonlit greenhouse',
    output: 'out/node-image.png'
  })
});
console.log(await response.json());
```

## 11. Rust client

Use any HTTP client against the REST API, or embed `native/rust` when you only need planning/state primitives.

```rust
use cosmos_quantum_media_core::{plan_timeline, CstState};

let state = CstState::from_context("scene context");
let chunks = plan_timeline(3600.0, 8.0, 0.5).unwrap();
println!("{} {:?}", chunks.len(), state.values);
```

## 12. C++ client

```cpp
#include "cosmos_media.hpp"

using namespace cosmos_media;
auto state = CstState::from_context("scene context");
auto chunks = plan_timeline(3600.0, 8.0, 0.5);
```

The C++ seed helper is a stable 64-bit native seed mixer designed to avoid external crypto dependencies. Python and Rust use SHA-256 receipts. If bit-for-bit cross-language seed identity is required, use the REST API as the canonical seed authority or replace the C++ seed helper with your organization’s SHA-256 implementation.

## 13. IBM Quantum credentials

Install:

```bash
pip install -e ".[quantum]"
```

Then configure your own IBM Quantum Platform values:

```bash
COSMOS_QUANTUM_MODE=ibm
IBM_QUANTUM_API_KEY=...
IBM_QUANTUM_INSTANCE=...
IBM_QUANTUM_BACKEND=
IBM_QUANTUM_SHOTS=256
```

The adapter never includes the API key in receipts or provider payloads.

## 14. Production hardening checklist

Before putting the API on a network outside localhost:

- add authentication;
- add TLS at a reverse proxy;
- restrict output paths;
- enforce request/body limits;
- rate-limit expensive jobs;
- put long jobs onto a queue;
- isolate provider credentials;
- version your provider/model/workflow in receipts;
- log request IDs, not secrets;
- define content and privacy policy appropriate to your use case;
- use object storage rather than local disk for distributed workers.

COSMOS is intentionally modular so those deployment concerns can be added around the same core contract.