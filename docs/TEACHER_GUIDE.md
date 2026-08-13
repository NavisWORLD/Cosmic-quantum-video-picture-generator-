# Teacher Guide — COSMOS Quantum Media

## Purpose

This guide turns the repository into a classroom/lab tool for teaching generative media, state, randomness, reproducibility, long-form planning, and scientific skepticism without requiring students to accept the project’s research vocabulary as established physics.

The built-in procedural provider is especially useful in schools because it can demonstrate the complete pipeline without downloading large model weights.

## Learning goals

Students should be able to:

- explain the difference between a prompt and persistent state;
- describe deterministic seeds and why reproducibility matters;
- explain what a generation receipt records;
- distinguish a computational branch search from a claim about physical parallel universes;
- explain how a long video can be built from short clips;
- compare classical randomness with a hardware-linked quantum measurement source;
- design a fair controlled experiment;
- identify which claims are directly verified by code and which remain hypotheses;
- reason about privacy, provenance, licensing, and responsible media generation.

## Recommended age bands

### Middle school / introductory

Focus on:

- seeds;
- continuity;
- storyboards;
- “same input, different random choices”;
- how software remembers a small state.

Use the procedural provider only.

### High school

Add:

- state vectors;
- deterministic hashing;
- simple Hebbian learning;
- long-form chunking;
- controlled comparisons;
- API concepts.

### College / engineering lab

Add:

- provider adapters;
- Rust/C++ implementations;
- distributed render architecture;
- Qiskit Runtime;
- ablation studies;
- statistical evaluation;
- reproducibility packages.

## Safe classroom setup

1. Clone the repository onto a teacher-controlled machine.
2. Create a Python virtual environment.
3. Install:

```bash
pip install -e ".[server,media,test]"
```

4. Install FFmpeg if video will be used.
5. Keep `COSMOS_QUANTUM_MODE=local` unless the instructor explicitly wants an IBM Quantum exercise.
6. Run:

```bash
cosmos-media doctor
cosmos-media serve
```

7. Open:

```text
http://127.0.0.1:8788/app/
```

Do not expose the reference server directly to the public internet without authentication and deployment hardening.

## Lesson 1 — What is a seed?

### Question

If two students use the same prompt, why can they receive different images?

### Activity

Generate twice without an explicit seed. Then generate twice with the same explicit seed.

```bash
cosmos-media image --prompt "a tiny observatory in a sunflower" --seed 42 --out out/a.png
cosmos-media image --prompt "a tiny observatory in a sunflower" --seed 42 --out out/b.png
```

With the procedural provider, the outputs should be deterministic for the same effective seed/settings.

### Discussion

A seed does not contain the final picture. It selects a reproducible path through a stochastic process.

## Lesson 2 — Memory without storing everything

### Question

How can a system remember creative continuity without keeping every previous frame in active memory?

### Activity

Inspect:

```bash
cosmos-media status
```

Find the 12 state values and `step_index`. Generate an image, then inspect again.

### Concept

The state is a compressed continuity signal. It cannot contain every detail from the past. Students should discuss what is lost when rich history is compressed into 12 numbers.

## Lesson 3 — Hebbian associations

Introduce the rough idea:

> When two patterns repeatedly occur together, a simple system can strengthen their association.

Show the update concept:

```text
W <- decay * W + learning_rate * outer(before, after)
```

Avoid presenting this small matrix as a full model of biological learning.

## Lesson 4 — “Multiverse” as search

### Activity

```bash
cosmos-media branch-search --prompt "a city wakes beneath two moons" --count 6
```

Ask students to identify:

- parent prompt;
- candidate branch prompt;
- candidate state;
- candidate score;
- best-ranked branch.

### Key distinction

The software creates alternate **computational possibilities**. That is enough to teach planning and search. It is not evidence that the program accessed physical alternate universes.

## Lesson 5 — Building a one-minute film from short pieces

Plan a 60-second video at eight-second chunks.

Expected chunk count:

```text
ceil(60 / 8) = 8
```

Then compare with a one-hour plan:

```text
ceil(3600 / 8) = 450
```

Discuss why resumable chunks are useful:

- failures are local;
- memory use stays bounded;
- workers can be distributed;
- providers with short clip limits can still participate;
- continuity becomes an explicit engineering problem.

## Lesson 6 — Storybook from source context

Give every student the same source paragraph and generate an eight-page storybook.

Ask:

- what facts came directly from the source?
- what visual choices were added by the scene planner?
- where might a real image model hallucinate details?
- how could the prompt be changed to reduce unsupported invention?

This is a useful media-literacy exercise.

## Lesson 7 — Quantum measurement vs. quantum claim

Start with the local mode.

Explain that ordinary cryptographic randomness can produce excellent seed material.

Then, if the class has access to IBM Quantum credentials, show the IBM path:

```text
circuit -> measurement shots -> returned bytes -> hash -> seed mixer -> media renderer
```

Ask students to label which machine performs each step.

The QPU does not directly draw the image in this architecture.

## Lesson 8 — Design a fair experiment

Question:

> Do IBM-derived seeds improve a predefined property of generated media?

Students must define:

- a fixed provider/model;
- prompts;
- classical control groups;
- IBM group;
- sample count;
- primary metric;
- blind evaluation procedure;
- exclusion criteria.

Require students to write the experiment before seeing results.

## Lesson 9 — Provenance and receipts

Open a receipt from `.cosmos-media/runs/.../receipt.json`.

Students identify:

- prompt hash;
- context hash;
- state hash;
- seed hash;
- provider;
- output;
- quantum source;
- backend/job ID when applicable.

Discuss why hashes are useful and why a hash is not the same as the original content.

## Lesson 10 — Build a provider

Advanced students implement a tiny HTTP service with:

```text
POST /generate/image
POST /generate/video
```

The provider can return a generated file, a shared path, base64, or a URL.

The objective is to learn interface design, not to build a foundation model from scratch.

## Assessment ideas

### Short answer

1. Why is a one-hour video broken into chunks?
2. What information does a generation receipt preserve?
3. What is the difference between local entropy and IBM-derived measurement data?
4. What does “12D” mean in this repository?
5. Why can a valid IBM job ID fail to prove a broader physical interpretation?

### Engineering assessment

Ask students to add one of:

- a new branch scoring metric;
- a new provider adapter;
- a continuity visualization;
- a receipt comparison tool;
- a timeline scheduler;
- a test proving a claimed invariant.

### Research assessment

Ask students to design and preregister a classical-vs-IBM seed experiment, then critique their own design for confounders.

## Accessibility and inclusion

For learners who struggle with long prompts or written composition:

- allow short prompts plus visual reference descriptions;
- use storybook mode to break a task into pages;
- show one concept at a time: seed, state, branch, timeline, receipt;
- let students inspect JSON visually rather than requiring code first;
- pair the PWA with screen-reader/browser accessibility tools;
- avoid grading artistic output quality as a proxy for technical understanding.

## Teacher answer key — central distinctions

- **Seed:** starting variable for a reproducible stochastic path.
- **State:** compact continuity memory updated across generations.
- **Hebbian association:** correlation-based local weight update.
- **Branch search:** multiple computational candidate futures.
- **Quantum provenance:** hardware/service-linked measurement/job metadata.
- **Quantum advantage:** a measured comparative result, not a branding term.
- **Provider:** the component that actually creates the image/video.
- **COSMOS:** the orchestration/state/provenance/timeline layer around providers.

## Final classroom message

Students should leave understanding that ambitious ideas become stronger when they are translated into mechanisms that can be inspected, tested, reproduced, criticized, and improved.