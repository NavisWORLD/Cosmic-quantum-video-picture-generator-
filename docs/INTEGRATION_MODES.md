# COSMOS Integration Modes

COSMOS can own the whole media job or become a component inside another creative system. The same state, branch, receipt and timeline machinery is used in every mode.

## Mode A — Standalone renderer

Use the built-in first-party renderer:

```bash
COSMOS_MEDIA_PROVIDER=native cosmos-media image \
  --prompt "a luminous observatory above an alien ocean" \
  --out out/native.png
```

The pixels are produced by `src/cosmos_media/native_renderer.py`. Prompt/context, seed and CST state determine the scene grammar, palette, celestial/environmental structures, recursive geometry, glow layers, particles, reflections and animation phase.

For video, COSMOS synthesizes native frames inside each bounded timeline chunk and encodes them with FFmpeg. Long runs remain resumable through per-run CST/Hebbian checkpoints.

## Mode B — Helper / planner

Keep another application's renderer but use COSMOS for continuity and planning.

Useful calls:

```bash
cosmos-media status
cosmos-media branch-search --prompt "continue the scene" --count 8
cosmos-media bridge --request '{"op":"plan","prompt":"continue the scene"}'
```

A host application can use the selected branch prompt, seed/state metadata, or receipts without asking COSMOS to render the final pixels.

## Mode C — Persistent JSONL bridge

Start:

```bash
cosmos-media bridge --stdio
```

Then exchange one JSON object per line.

Request:

```json
{"id":"42","op":"plan","prompt":"a city inside a ringed planet"}
```

Response:

```json
{"ok":true,"id":"42","op":"plan","result":{"selected":{},"candidates":[]}}
```

Supported operations:

- `capabilities`
- `status`
- `state`
- `reset_state`
- `branch`
- `plan`
- `image`
- `video`
- `storybook`

This mode is intentionally suitable for Electron applications, Node tools, agent frameworks, shell pipelines, desktop generators, C++/Rust host applications, game engines and other local creative stacks. See `examples/node_bridge_client.mjs`.

## Mode D — HTTP engine API

Start:

```bash
cosmos-media serve
```

Then call the `/v1` endpoints from any language. This is useful when the host and COSMOS run as separate services or containers.

## Mode E — COSMOS orchestrating an external renderer

Set:

```bash
COSMOS_MEDIA_PROVIDER=http
COSMOS_MEDIA_ENDPOINT=http://127.0.0.1:9000
```

COSMOS continues to own state, branching, long-form timeline, checkpoints and receipts, but sends each bounded image/video render request to the attached provider.

That external renderer may be a local model server, ComfyUI workflow gateway, render farm, custom diffusion/video stack or another media engine.

## Architecture rule

The host should be able to choose independently:

```text
WHO OWNS CONTINUITY?   COSMOS or host
WHO OWNS PLANNING?     COSMOS or host
WHO OWNS PIXELS?       COSMOS native or external renderer
WHO OWNS UI?           COSMOS PWA or host application
HOW DO THEY TALK?      CLI, JSONL, REST, or native Rust/C++ core
```

That separation is deliberate. COSMOS is useful as a solo application **and** as an attachable subsystem.