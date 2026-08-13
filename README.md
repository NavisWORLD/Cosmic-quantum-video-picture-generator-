# COSMOS // Cosmic Quantum Video & Picture Generator

**A local-first standalone media engine, creative helper, and universal integration bridge with CST state, deterministic provenance, long-form chunking, computational branch search, first-party rendering, and optional IBM Quantum entropy/provenance.**

> Status: **research + engineering release**. COSMOS now ships with its own first-party image/video synthesizer, a pluggable external-provider protocol, long-form timeline rendering, storybook generation, CST-inspired state evolution, Rust/C++ reference cores, an installable PWA, CLI/JSONL integration bridge, tests, CI, and IBM Quantum integration hooks. External model weights are optional and intentionally not bundled.

## What this actually is

COSMOS Media is a complete generation **engine and integration layer**, not merely a wrapper around somebody else's renderer. It can operate alone or sit behind another creative application.

It coordinates:

1. user context and creative intent;
2. a persistent 12-dimensional CST-inspired state vector;
3. deterministic seed/provenance mixing;
4. optional IBM Quantum measurement-derived entropy;
5. computational “multiverse” branch search (multiple candidate prompt/state branches scored by a reward function);
6. a built-in prompt/CST-conditioned native visual synthesizer;
7. optional external image/video provider adapters;
8. long-form video chunk planning, checkpoints, resume, and stitching;
9. storybook scene extraction and illustration;
10. a language-neutral HTTP API and JSONL stdio bridge for Python, Rust, C++, JavaScript, Go, shell tools, desktop apps, mobile/PWA clients, agents, and other generators.

The term **multiverse** in this repository refers to parallel computational candidate branches unless a document explicitly says otherwise. The project does **not** claim to prove physical multiverse access, cross-universe injection, consciousness, or quantum advantage. Those ideas can be investigated experimentally, but claims require controlled evidence.

## Three operating modes

### 1. Standalone / solo grinder

COSMOS makes its own images, animated video chunks, long-form stitched videos, and storybooks using `COSMOS_MEDIA_PROVIDER=native` (the default).

```bash
cosmos-media image --prompt "a luminous world tree above an alien ocean" --out out/world.png
cosmos-media video --prompt "fly through the floating islands" --duration 20 --out out/flight.mp4
```

No ComfyUI, Diffusers server, hosted image API, or external media generator is required for the native path.

### 2. Helper / co-engine

Another app can use COSMOS only for state, branch planning, continuity, seeds, receipts, story/world memory, or long-timeline management while keeping its own renderer/UI.

```bash
cosmos-media branch-search --prompt "continue this scene without breaking continuity" --count 8
cosmos-media status
```

### 3. Bridge / integrator

Any application that can spawn a process can keep COSMOS alive as a JSONL subprocess:

```bash
cosmos-media bridge --stdio
```

Then send one JSON request per line:

```json
{"id":"1","op":"capabilities"}
{"id":"2","op":"plan","prompt":"a neon cathedral drifting through Saturn's rings"}
{"id":"3","op":"image","prompt":"continue the chosen branch","output":"out/bridge.png"}
```

Every line produces one machine-readable JSON response. This is intended for agent frameworks, desktop tools, render farms, local AI stacks, game engines, automation scripts, or another generator that wants COSMOS as its media/continuity engine.

## Why it is different

Most media generators are stateless request/response systems. COSMOS Media adds a continuity layer and also owns a renderer:

- **First-party rendering:** `native_renderer.py` produces pixels and animation frames directly from prompt/context, seed, CST state, scene grammar, recursive geometry, layered light/noise, particles, reflections, celestial/environmental structures, and animation phase.
- **Stateful creation:** each scene can inherit a compact 12D state from prior scenes.
- **Hebbian-style adaptation:** repeated semantic/state pairings can strengthen a small association matrix used to bias later state transitions.
- **Branch search:** create N candidate creative trajectories, score them, then continue the best branch.
- **Quantum provenance:** optionally mix IBM measurement results into the seed trail and preserve backend/job/result hashes.
- **Reproducible receipts:** every generation can emit a JSON receipt containing context hash, state hash, seed hash, provider, parameters, and outputs.
- **Long-form rendering:** a 60-minute request becomes a resumable sequence of bounded clips with per-run state checkpoints and continuity metadata, then gets stitched with FFmpeg.
- **Provider optionality:** COSMOS can render itself or hand the same state/timeline to a different renderer through the HTTP provider contract.

## Quick start

### Python 3.10+

```bash
python -m venv .venv
# Windows: .venv\Scripts\activate
# macOS/Linux: source .venv/bin/activate
pip install -e ".[server,media,test]"
cp .env.example .env   # Windows: copy .env.example .env
cosmos-media doctor
cosmos-media image --prompt "a bioluminescent library orbiting Saturn" --out out/library.png
cosmos-media video --prompt "slow flight through the library" --duration 30 --out out/library.mp4
cosmos-media storybook --context-file examples/story_context.txt --out out/storybook
cosmos-media capabilities
cosmos-media serve
```

The default `native` provider is the first-party COSMOS renderer. `procedural` remains a tiny diagnostic backend, and `http` lets COSMOS drive a different renderer when desired.

### One-hour video

```bash
cosmos-media video \
  --prompt "a continuous cinematic expedition through an impossible ocean planet" \
  --duration 3600 \
  --chunk-seconds 8 \
  --out out/ocean-hour.mp4
```

COSMOS plans the hour as resumable chunks, preserves continuity metadata, writes per-run CST/Hebbian checkpoints, renders each chunk, and stitches the result. At eight-second chunks, one hour is 450 independently recoverable segments. Rendering time, storage, and visual quality still depend on resolution, hardware, provider, and settings. “Infinite” therefore means **continuable/resumable with no engine-level narrative duration cap**, not infinite physical compute.

## IBM Quantum mode

Install the optional dependency:

```bash
pip install -e ".[quantum]"
```

Set your own credentials:

```bash
COSMOS_QUANTUM_MODE=ibm
IBM_QUANTUM_API_KEY=...
IBM_QUANTUM_INSTANCE=...   # recommended CRN / instance
IBM_QUANTUM_BACKEND=       # optional preferred backend
```

The adapter uses `qiskit_ibm_runtime.QiskitRuntimeService`. If credentials, a backend, network access, or queue capacity are unavailable, the engine fails soft to a local cryptographic entropy source unless strict mode is enabled.

Quantum receipts can include backend name, job identifier when available, raw-bit hash, result hash, and the final mixed seed hash. Secrets are never written to receipts.

## Repository map

```text
src/cosmos_media/          Python engine, native renderer, API, CLI, JSONL bridge
native/rust/               Rust CST/seed/timeline reference core
native/cpp/                C++17 CST/seed/timeline reference core
apps/pwa/                  installable mobile/desktop web app
docs/                      manuals, research disclosure, integration guides
examples/                  sample context + provider examples
scripts/                   install/run/build helpers
tests/                     Python engine/native/integration tests
.github/workflows/          cross-language CI and release builds
```

## Core loop

The media engine follows the COSMOS lineage:

**perceive → compress → expand → validate → express → store**

For media generation that becomes:

1. **Perceive** user context, references, prompt and optional sensor/metadata input.
2. **Compress** into hashes, scene descriptors and a 12D creative state.
3. **Expand** into candidate branches, prompts, seeds and shot plans.
4. **Validate** length, resource limits, provider capability and continuity constraints.
5. **Express** through the native renderer or an attached provider.
6. **Store** receipts, state checkpoints, branch scores and output manifests.

## API

Run:

```bash
cosmos-media serve --host 127.0.0.1 --port 8788
```

Key endpoints:

- `GET /v1/health`
- `GET /v1/state`
- `POST /v1/image`
- `POST /v1/video`
- `POST /v1/storybook`
- `POST /v1/branch-search`
- `GET /v1/quantum/status`

The API schemas are intentionally plain JSON so external engines can integrate without importing Python.

## JSONL stdio bridge

For tools that prefer subprocess integration instead of HTTP:

```bash
cosmos-media bridge --stdio
```

Supported operations include:

```text
capabilities
status
state
reset_state
branch
plan
image
video
storybook
```

One-shot mode is also available:

```bash
cosmos-media bridge --request '{"op":"plan","prompt":"continue the world"}'
```

## Optional external provider protocol

Set:

```bash
COSMOS_MEDIA_PROVIDER=http
COSMOS_MEDIA_ENDPOINT=http://127.0.0.1:9000
```

COSMOS will call:

```text
POST /generate/image
POST /generate/video
```

The external provider receives prompt, seed, CST state, duration/resolution, and continuity metadata. See `docs/INTEGRATION_GUIDE.md` for the complete contract.

## Rust

```bash
cd native/rust
cargo test
cargo run --example demo
```

The Rust crate implements deterministic seed mixing, 12D state stepping and long-form chunk planning so high-throughput integrations can share the same planning semantics without Python.

## C++

```bash
cmake -S native/cpp -B native/cpp/build
cmake --build native/cpp/build
ctest --test-dir native/cpp/build
```

The C++17 library mirrors the core deterministic planning primitives and exposes a small header-friendly API suitable for game engines, render farms and native tools.

## Installable app

`apps/pwa/` is a Progressive Web App. Serve the repository API and the PWA together, then install it from a desktop browser or add it to the home screen on iOS/Android. The UI talks to the same `/v1` API used by engineering integrations, and clean installs use the native renderer by default.

For distributable desktop builds, `scripts/build_desktop.py` uses PyInstaller when installed. Native mobile shells can wrap the same PWA/API contract without changing the engine.

## Reproducibility and receipts

Each generation directory can contain:

```text
manifest.json
receipt.json
state.json
checkpoints/
chunks/
outputs/
```

A receipt records enough metadata to compare native, external, classical, and IBM-assisted paths without exposing API keys. This is designed for ablation testing: same prompt/settings, different entropy source or renderer, repeated trials, measured outcome metrics.

## Research disclosure

The repository separates **implemented engineering** from **research hypotheses**. In particular:

- IBM Quantum can supply measurement results, runtime/job provenance and entropy-like input.
- This repo does not assert that quantum-derived seeds make a model more accurate, creative or realistic.
- “12D,” “CST,” “Hebbian,” “multiverse,” and “entanglement” terminology may name project-specific computational structures; they should not be read as established physical conclusions without independent evidence.
- Claims of quantum advantage should be tested against classical baselines with matched compute, renderer/model, prompt, seed budget and evaluation metrics.

See `docs/RESEARCH_DISCLOSURE.md`.

## Lineage and provenance

This public build preserves the COSMOS / Cosmic Synapse Theory project lineage and its local-first adaptive-system architecture. Project provenance includes the timestamped research record and Zenodo DOI **10.5281/zenodo.17574447**. See `NOTICE.md` for attribution/provenance notes.

## License

Apache License 2.0. See `LICENSE` and `NOTICE.md`. Third-party models, providers, datasets and SDKs retain their own licenses and terms. No external model weights are sublicensed by this repository.

## Safety and privacy

- Keep API keys in environment variables or a local secret manager.
- Do not commit private source images, biometric data, or third-party copyrighted datasets without permission.
- An optional external media provider may impose its own content rules and data-retention policy.
- Receipts intentionally store hashes and technical metadata, not raw secrets.

## Definition of “done” for this release

The repository is considered engine-complete when:

- Python package installs and CLI starts;
- first-party native image/video paths work end-to-end without an external media generator;
- JSONL CLI bridge works as a persistent helper/integrator;
- long-form timeline planning supports 60 minutes and resumes by chunk/checkpoint;
- storybook generation produces scene metadata + native illustrations;
- IBM adapter connects when user credentials/dependencies are available and fails soft otherwise;
- HTTP adapter can optionally hand work to another image/video backend;
- Rust and C++ cores compile/test;
- PWA installs and calls the same engine API;
- CI verifies native Python rendering plus Rust/C++ on every push;
- documentation distinguishes implemented behavior from experimental claims.

That is the scope of this public engineering release.