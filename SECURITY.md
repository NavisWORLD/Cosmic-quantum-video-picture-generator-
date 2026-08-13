# Security Policy

## Supported release

The current `0.1.x` engineering release is the supported public development line.

## Secrets

Never commit:

- IBM Quantum API keys;
- provider API tokens;
- private model credentials;
- private source images or biometric datasets;
- `.env` files containing secrets.

Use `.env` only on trusted local machines or use your deployment platform's secret manager. `.env` is ignored by Git.

## Network exposure

The reference server defaults to `127.0.0.1`. It is designed for local use and trusted development networks.

Before exposing it to an untrusted network, add at minimum:

- authentication and authorization;
- TLS termination;
- request-size limits;
- rate limits / job quotas;
- provider-specific content controls;
- output-path restrictions;
- a queue for long-running generation;
- audit logging that excludes secrets;
- sandboxing appropriate to any third-party renderer.

## File serving

The reference FastAPI app serves generated files only from the explicit `out/` directory. Do not replace that with an arbitrary filesystem route.

External HTTP providers may return shared paths or URLs. Treat those providers as trusted infrastructure; a production bridge should validate allowed shared roots and download origins.

## Generated media

Media providers can have their own safety, privacy, copyright, retention, and acceptable-use rules. Operators are responsible for configuring those providers appropriately for their deployment.

Do not use private images, sensitive biometric information, or third-party datasets without appropriate permission and a lawful basis.

## Dependency and model supply chain

This repository intentionally does not bundle large model weights. Verify the source, checksum, license, and model-card terms of any model or workflow you attach.

For reproducible deployments, pin dependency versions and record provider/model identifiers in generation manifests.

## Reporting a vulnerability

Please use GitHub's private vulnerability reporting feature for this repository when available rather than posting secrets or exploit details in a public issue.

Include:

- affected commit/version;
- reproduction steps;
- expected and actual behavior;
- impact;
- minimal proof of concept if safe to share;
- suggested mitigation if known.

## Scientific claims are not security guarantees

CST state, quantum-derived entropy, receipts, and hashes are engineering/research features. They are not substitutes for cryptographic authentication, access control, encryption, or secure key management unless a component explicitly implements those properties using established cryptographic primitives.