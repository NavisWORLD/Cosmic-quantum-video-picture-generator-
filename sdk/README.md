# COSMOS SDKs

Cross-language libraries for the COSMOS state and association engine.

## Native SDKs

- Python — `cosmos_media.SynapticCore`
- Rust — `sdk/rust`
- C++ — `sdk/cpp/cosmos_synaptic.hpp`
- Go — `sdk/go`
- JavaScript / TypeScript — `sdk/typescript`
- Java — `sdk/java/CosmosSynaptic.java`
- C# — `sdk/csharp`
- Kotlin/JVM — `sdk/kotlin/CosmosSynaptic.kt`
- Swift — `sdk/swift`

All implementations use the same 12-value recurrent update and 12x12 association matrix defaults as the Python engine.

## Universal ABI

`native/c_abi` builds a shared library named `cosmos_synaptic` with a small C ABI:

- `cosmos_synaptic_create`
- `cosmos_synaptic_destroy`
- `cosmos_synaptic_advance`
- `cosmos_synaptic_project`
- `cosmos_synaptic_step_index`
- `cosmos_synaptic_values`

That ABI is the compatibility path for languages with FFI support, including Zig, Nim, Julia, LuaJIT, Swift, Rust, C, Fortran, and others.

## Protocol

The portable snapshot protocol identifier is `cosmos.synaptic.v1`. A snapshot carries the 12 state values, step index, and the complete association matrix so it can be moved between applications or languages without losing continuity.

## Verification

`.github/workflows/sdk-ci.yml` compiles the available SDKs on GitHub-hosted runners. Python, Rust, C++, C ABI, Go, JavaScript, Java, C#, and Swift are build-gated. Kotlin is source-compatible with the JVM implementation and can also call the C ABI.

The word “synaptic” here names a software association mechanism; it does not claim the code is a biological nervous system.
