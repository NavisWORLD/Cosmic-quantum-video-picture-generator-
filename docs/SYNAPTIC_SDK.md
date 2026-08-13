# COSMOS Synaptic SDK Manual

## Contract

`cosmos.synaptic.v1` is a portable software-state contract shared across the SDKs. The canonical implementation is `cosmos_media.SynapticCore`.

Each core carries:

- 12 bounded state values
- a monotonically increasing step index
- a 12x12 association matrix
- learning rate `0.04`
- association decay `0.995`
- recurrent defaults `omega=0.37`, `damping=0.82`, `gate=0.33`

An update derives a deterministic 12-value input vector from SHA-256, projects the current association matrix into a bias vector, advances the recurrent state, and then updates the matrix from the before/after pair.

## Python

```python
from cosmos_media import SynapticCore

core = SynapticCore.from_context("character continuity")
state = core.pulse("camera moves into the next scene")
print(state["values"])
```

## Rust

Use the crate in `sdk/rust`. It wraps the existing tested `native/rust` primitives instead of duplicating them.

## C++

Include `sdk/cpp/cosmos_synaptic.hpp`. The wrapper composes `CstState` with `HebbianAssociator` from the existing C++ core.

## C ABI

Build:

```bash
cmake -S native/c_abi -B build/cabi
cmake --build build/cabi --config Release
```

The resulting shared library exposes create/destroy, advance, projection, state-values, and step-index functions. Languages with a C FFI can call this ABI directly.

## Go, JavaScript/TypeScript, Java, C#, Kotlin, Swift

Each implementation lives under `sdk/<language>` and mirrors the same constants and update order. These are deliberately dependency-light so they can be embedded in games, media tools, services, mobile apps, plugins, and local applications.

## Other languages

For Zig, Nim, Julia, Fortran, LuaJIT, Ruby extensions, PHP FFI, R native extensions, and other runtimes, bind `native/c_abi/include/cosmos_synaptic.h`. This is the maintained compatibility boundary rather than pretending every language needs a separate copy of the algorithm.

## Interchange rule

When moving continuity between languages, serialize:

- protocol: `cosmos.synaptic.v1`
- dimensions: `12`
- step index
- 12 state values
- 12x12 matrix

Keep values as IEEE-754 double precision. Allow small floating-point tolerance across standard-library `sin`/`tanh` implementations.

## Scope

The term “synaptic” describes a software association/update mechanism inspired by neural-learning ideas. It does not establish biological equivalence, consciousness, or a physical nervous-system claim.
