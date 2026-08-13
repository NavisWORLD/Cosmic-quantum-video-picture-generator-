# COSMOS Quantum Media — Engineering Manual

## 1. Purpose

COSMOS Quantum Media is a local-first orchestration layer for image, video, and illustrated-story generation. Its job is not to replace a diffusion/video model. Its job is to make a media model behave like one component inside a persistent creative system.

The engine adds four things that ordinary one-shot generation endpoints commonly lack:

1. **continuity state** across scenes;
2. **candidate-branch search** before committing to a trajectory;
3. **provenance and deterministic receipts**;
4. **long-form planning** that can continue far beyond a single model call.

An optional IBM Quantum adapter can contribute measurement-derived seed material and hardware/job provenance. This is deliberately isolated from the renderer so the system remains useful when quantum hardware is unavailable.

## 2. Architecture at a glance

```text
User / App / External Engineer
            |
            v
      FastAPI / CLI
            |
            v
+------------------------------+
|      CosmosMediaEngine       |
|                              |
| Context -> 12D CST State     |
|       -> Hebbian Bias        |
|       -> Branch Search       |
|       -> Seed / Provenance   |
|       -> Timeline Planner    |
+------------------------------+
       |                |
       |                +------> IBM Quantum Runtime (optional)
       |
       +------> MediaProvider
                   |
             +-----+-----+
             |           |
       procedural      HTTP bridge
                         |
                   any renderer
```

The Python engine is the reference orchestration implementation. Rust and C++ implement the high-frequency deterministic planning primitives so other systems can embed the CST state and timeline logic without starting a Python interpreter.

## 3. The COSMOS loop

The engine follows the project lineage:

**perceive → compress → expand → validate → express → store**

### Perceive

Inputs can include:

- a generation prompt;
- user-supplied source context;
- prior persistent CST state;
- optional external metadata supplied by an integration;
- optional quantum measurement material.

The public engine does not automatically scrape private accounts or ingest hidden personal data. Context is explicit input.

### Compress

The engine reduces the request to compact, reproducible structures:

- SHA-256 prompt hash;
- SHA-256 context hash;
- 12-value CST state;
- state hash;
- base seed and seed hash;
- timeline chunk plan.

### Expand

The engine can produce multiple candidate trajectories. `branch-search` perturbs prompt emphasis and CST state, calculates candidate seeds, and ranks the branches using continuity, diversity, and an optional external score.

### Validate

Validation happens before expensive rendering:

- prompt must be non-empty;
- durations must be positive finite numbers;
- overlap must be smaller than a chunk;
- page counts are bounded in the storybook planner;
- provider names must resolve;
- IBM failures either raise in strict mode or fail soft to local entropy.

### Express

The selected provider receives the generation request. The built-in procedural provider is a deterministic integration test backend. It proves that orchestration, files, FFmpeg, state, receipts, and the UI work. It is not a photorealistic foundation model.

A real generation stack should normally attach through the HTTP provider protocol.

### Store

COSMOS stores technical continuity rather than pretending every prior frame can stay inside a model context window. State checkpoints, manifests, receipts, branch information, and output paths are persisted under `.cosmos-media/` by default.

## 4. The 12D CST media state

`CSTState` contains exactly 12 floating-point values in `[-1, 1]` plus a step counter.

In this repository, “12D” means a **12-dimensional computational state vector**. The software does not assert that these twelve values are literal extra physical dimensions.

A deterministic stimulus vector `s` is derived from the incoming prompt/context. Each new state blends:

- damped previous state;
- stimulus drive;
- a phase-coupled recurrent neighboring term;
- a Hebbian association bias.

Conceptually:

```text
x(t+1) = tanh(
    damping * x(t)
  + gate * stimulus
  + recurrent_phase_coupling
  + association_bias
)
```

The bounded nonlinear update avoids uncontrolled divergence and does not use a hard zero gate that can silently kill the state.

## 5. Hebbian continuity

`HebbianAssociator` maintains a 12×12 matrix. After a transition from `x_before` to `x_after`, the matrix updates approximately as:

```text
W <- decay * W + learning_rate * outer(x_before, x_after)
```

Weights are bounded to `[-1, 1]`. A projection of the current state through `W` becomes a small bias on the next state step.

This is intentionally lightweight. It is not a replacement for neural-network training. It is a continuity memory that can run cheaply between generation calls.

## 6. Computational “multiverse” branch search

The branch engine is the operational definition of multiverse probing in this public build.

Given a parent state and prompt, it creates multiple candidate trajectories:

```text
parent
  |-- branch 0: cinematic continuity
  |-- branch 1: documentary physicality
  |-- branch 2: dreamlike geometry
  |-- branch 3: intimate character focus
  ...
```

Each branch receives:

- a deterministic prompt variation;
- a deterministic branch seed;
- a child CST state;
- a continuity score;
- a diversity score;
- an optional external reward score.

The best-scoring branch can be selected for continuation.

This is analogous to search, planning, beam expansion, or model-based candidate evaluation. It does not establish physical access to alternate universes.

## 7. Quantum layer

### Modes

`COSMOS_QUANTUM_MODE` accepts:

- `off` — deterministic disabled marker;
- `local` — cryptographic entropy from `python.secrets`;
- `ibm` — IBM Quantum Runtime sampling with fail-soft local fallback unless strict mode is enabled.

### IBM path

The adapter:

1. initializes `QiskitRuntimeService` for the IBM Quantum Platform;
2. selects an explicit backend or the least-busy operational non-simulator backend with at least eight qubits;
3. creates an 8-qubit Hadamard measurement circuit;
4. transpiles it for the backend;
5. submits it through Sampler V2;
6. obtains measurement bytes/counts;
7. hashes the raw bytes and count result;
8. mixes the bytes into the generation seed path;
9. records backend and job ID when available.

API keys are never written to receipts.

### Why use it?

The defensible use today is experimental entropy/provenance and comparative research. Researchers can run matched trials:

```text
same model + same prompt + same compute + classical seed source
vs.
same model + same prompt + same compute + IBM-derived seed source
```

Then compare measurable outputs. The repository does not pre-declare the result.

## 8. Long-form and “infinite” video

Most video models generate bounded clips. COSMOS treats a long video as a timeline of clips.

For a duration `D` and chunk size `C`:

```text
chunk_count = ceil(D / C)
```

A one-hour video at eight seconds per chunk produces 450 chunks.

Every chunk receives:

- index;
- start time;
- duration;
- narrative progress in `[0,1]`;
- overlap metadata;
- derived seed;
- evolved CST state;
- previous-output path for providers that support reference conditioning.

After every chunk, the manifest and state are written to disk. Therefore an interrupted run can resume from already-rendered chunks.

The built-in stitcher first attempts FFmpeg stream-copy concatenation. If codec/container consistency prevents that, it falls back to H.264 transcoding.

“Infinite” in the product language means **continuable and not artificially capped by the orchestration layer**. Physical compute, storage, provider limits, model context, cost, and wall-clock time remain finite.

## 9. Storybook engine

The storybook planner consumes user-supplied source context and turns it into up to 64 scene records. It tries not to invent biographical facts beyond the source. Each page receives:

- title;
- narration anchored to a source sentence;
- image prompt;
- continuity note;
- page seed;
- state hash;
- generated image.

Outputs include:

- `BOOK.md`;
- `storybook.json`;
- page images;
- generation receipt.

A higher-level LLM can replace the deterministic scene planner through an integration, but the built-in planner remains usable without one.

## 10. Provider model

The engine deliberately separates orchestration from visual-model choice.

### Procedural provider

Use it for:

- installation verification;
- CI/smoke tests;
- API integration tests;
- seed/state debugging;
- demonstrations where a large model is unavailable.

### HTTP provider

Use it for real media generation. Any language or stack can implement two endpoints:

```text
POST /generate/image
POST /generate/video
```

The service can be a ComfyUI adapter, a custom Diffusers server, a render farm, a hosted API bridge, a game-engine renderer, or another generator.

The HTTP response can contain raw media bytes, a base64 payload, a shared filesystem path, or a downloadable URL.

## 11. Receipts and reproducibility

A receipt contains technical metadata such as:

- run ID;
- generation kind;
- prompt/context/state hashes;
- seed and seed hash;
- provider;
- generation parameters;
- output paths;
- quantum mode/source/backend/job/result hashes;
- timestamp;
- receipt hash.

The purpose is not blockchain theater. It is to make ablation studies and debugging possible.

A good experiment can archive:

```text
prompt
provider/model identifier
provider version
settings
seed receipt
quantum receipt
output hash
human/automated evaluation
```

## 12. API integration

The FastAPI service exposes plain JSON over HTTP so a Rust engine, Unity/Unreal tool, Node service, browser, automation platform, or local application can call the same interface.

The PWA is only one client. It is not privileged.

## 13. Deployment patterns

### Local artist workstation

```text
PWA -> local COSMOS API -> local HTTP model provider -> local GPU
```

### Render farm

```text
client -> COSMOS planner -> HTTP provider gateway -> worker pool -> object storage
```

### Research station

```text
experiment runner -> COSMOS -> IBM entropy + fixed media provider -> receipts -> evaluator
```

### School/lab demonstration

```text
browser/PWA -> procedural provider
```

This last mode needs no model weights and is useful for teaching state, seed, provenance, and timeline concepts.

## 14. Failure behavior

The engine is designed to fail soft where that protects usability and fail hard where silent corruption would be dangerous.

Fail-soft examples:

- missing/corrupt persistent CST state -> start with a clean state;
- IBM unavailable and strict mode disabled -> local entropy with fallback reason recorded.

Fail-hard examples:

- invalid duration;
- invalid chunk overlap;
- unknown provider;
- provider returns no usable output;
- FFmpeg missing for video;
- storybook context is empty.

## 15. Security and privacy

Do not put API keys in source files. Use `.env` or a secret manager.

Do not expose the API directly to an untrusted network without adding authentication, rate limits, path policies, and provider-specific safety controls.

The reference server serves only the explicit `out/` directory as generated public output. It does not provide an arbitrary filesystem download route.

## 16. Extending the engine

Recommended extension points:

- new `MediaProvider` implementations;
- learned branch scorers;
- optical-flow or embedding continuity metrics;
- reference-image conditioning;
- audio timeline and soundtrack generation;
- distributed queue workers;
- object-storage manifests;
- user-defined CST state adapters;
- benchmark harnesses comparing classical and IBM-derived seed paths;
- native bindings from Rust/C++ into other runtimes.

Keep the architectural rule: **provider quality and COSMOS orchestration are separate variables**. That makes experiments interpretable and the system replaceable rather than locked to one model.

## 17. What makes this build different

The distinctive engineering combination is not “quantum pixels.” It is the coupling of:

- persistent low-dimensional creative state;
- Hebbian continuity bias;
- candidate trajectory search;
- optional hardware-derived quantum provenance;
- deterministic receipts;
- resumable long-duration chunk planning;
- provider-neutral media generation;
- Python orchestration with Rust/C++ native planning cores;
- one API shared by CLI, PWA, native clients, and external renderers.

That is the testable system delivered by this repository.