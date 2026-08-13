# Research Disclosure

## Scope

COSMOS Quantum Media combines ordinary software engineering, project-specific adaptive-state methods, and optional quantum-hardware inputs. This document separates what the repository **implements** from what would require independent scientific validation.

## Implemented and directly inspectable

The repository implements:

- a 12-value bounded computational state vector;
- recurrent state evolution driven by deterministic prompt/context features;
- a small Hebbian-style association matrix;
- computational candidate-branch search;
- deterministic seed hashing and generation receipts;
- long-duration chunk planning and resumable rendering;
- image, video and storybook provider orchestration;
- an IBM Quantum Runtime adapter that can submit a measured circuit and incorporate returned measurement bytes into a seed path;
- backend/job/result provenance when available;
- local cryptographic fallback when IBM is unavailable and strict mode is disabled;
- Python, Rust and C++ implementations of core planning concepts;
- a REST API and PWA client.

These claims can be verified by reading and executing the code.

## Experimental project vocabulary

Several COSMOS/CST terms are intentionally retained because they are part of the project lineage. Their software meaning in this repository is:

### “12D”

A 12-dimensional numerical state vector used for adaptive continuity.

### “Hebbian”

A local correlation update on a 12×12 association matrix inspired by the general principle that correlated activations can strengthen associations. It is not presented as a biological brain simulation.

### “Multiverse probing”

Parallel computational candidate trajectories generated from one parent prompt/state and ranked before continuation.

### “Injection”

Feeding a selected candidate state/seed/prompt trajectory into the next generation stage.

### “Quantum entanglement”

If an experiment deliberately runs an entangled circuit, the term describes the circuit/state used by the quantum backend. It does not mean the generated media is physically entangled with another universe or viewer.

### “Quantum media”

Media orchestration in which quantum measurement results may participate in provenance or seed construction. The actual pixels/frames are produced by a media renderer/provider.

## Claims this repository does not establish

The software does not, by itself, prove:

- physical access to parallel universes;
- communication across universes;
- literal multidimensional reality injection;
- consciousness or sentience;
- that a QPU makes images more beautiful, realistic or meaningful;
- that quantum-derived random seeds are inherently better than high-quality classical random seeds;
- quantum advantage for image/video generation;
- a new law of physics.

A future experiment may investigate any testable hypothesis, but the result must be measured rather than assumed.

## Why preserve the quantum path at all?

There are legitimate engineering and research reasons to preserve it:

1. **provenance:** a generation can be associated with a specific remote hardware job and result hash;
2. **entropy-source experiments:** one can compare classical and quantum-derived seed paths;
3. **hybrid-system research:** the project can test whether hardware measurements become useful conditioning variables in a larger adaptive system;
4. **reproducible negative results:** proving that no quality difference exists is still useful evidence;
5. **future replaceability:** the provider architecture lets researchers change the quantum experiment without rewriting the media renderer.

## Current IBM Runtime assumptions

The Python adapter targets the IBM Quantum Platform through `qiskit_ibm_runtime.QiskitRuntimeService` using the `ibm_quantum_platform` channel and Sampler V2.

Because SDKs and cloud services evolve, pin versions for a formal experiment and record them in the experiment manifest.

## Recommended ablation experiment

To test whether IBM-derived seed material changes any measurable outcome:

### Fixed variables

Keep constant:

- media provider and model/checkpoint;
- model version;
- workflow graph;
- prompt/context;
- resolution;
- frame count/duration;
- sampling/scheduler settings;
- guidance values;
- post-processing;
- hardware class for media rendering;
- evaluation method.

### Experimental groups

Use at least:

1. deterministic fixed classical seeds;
2. cryptographically random local seeds;
3. IBM-derived seed material.

If the project claims a special entanglement circuit is meaningful, add it as a separate IBM group rather than combining it with all quantum samples.

### Repeat trials

A single striking image proves almost nothing. Run enough repeated trials to estimate variability.

### Metrics

Possible metrics include:

- temporal consistency score;
- optical-flow discontinuity;
- identity consistency for recurring subjects;
- image/text alignment;
- perceptual similarity between adjacent scenes;
- diversity across independent runs;
- human pairwise preference under blinded conditions;
- generation latency;
- QPU queue/runtime;
- total media compute;
- total cost.

Do not select metrics only after seeing which one makes a preferred group look best.

### Statistical analysis

Predefine:

- primary metric;
- sample size target;
- exclusion criteria;
- confidence interval or hypothesis test;
- treatment of multiple comparisons.

Publish null results.

## Quantum advantage standard

A claim of “quantum advantage” should specify **advantage at what task** and against **which classical baseline**.

For this project, a meaningful claim might be:

> Under a matched media-rendering budget and predefined evaluation metric, conditioning strategy Q using quantum-hardware measurements achieves outcome M compared with classical strategy C.

That would still require evidence that the improvement is due to a specifically quantum resource rather than ordinary stochastic variation, API differences, selection effects or extra compute.

## Provenance is not proof

A valid IBM job ID can demonstrate that a hardware-linked computation occurred. It does not establish the interpretation placed on the result.

Similarly, a DOI or timestamp establishes provenance/public record; it does not automatically validate scientific conclusions.

## Reproducible publication checklist

For serious results, publish:

- exact commit SHA;
- Python/Rust/C++ versions as applicable;
- Qiskit and qiskit-ibm-runtime versions;
- IBM backend name and relevant calibration metadata if available;
- job IDs where sharing is permitted;
- circuit source;
- transpilation settings;
- shot count;
- prompt/context hashes;
- seed receipts;
- media provider/model identifiers;
- all material generation settings;
- evaluation code;
- raw aggregate results;
- limitations and failed runs.

## Responsible language

Strong creative language is welcome in project branding, but scientific documentation should distinguish:

- **metaphor**;
- **software mechanism**;
- **hypothesis**;
- **measured result**;
- **established external science**.

That distinction makes the project easier to evaluate, integrate and improve.