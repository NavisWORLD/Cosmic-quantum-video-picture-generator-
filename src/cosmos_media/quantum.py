from __future__ import annotations

from dataclasses import dataclass
import json
import math
import secrets
from typing import Any

from .config import Settings
from .provenance import QuantumReceipt, sha256_bytes, sha256_text


@dataclass(slots=True)
class EntropySample:
    payload: bytes
    receipt: QuantumReceipt


class QuantumUnavailable(RuntimeError):
    pass


def local_entropy(size: int = 32, *, reason: str | None = None) -> EntropySample:
    payload = secrets.token_bytes(max(1, int(size)))
    return EntropySample(
        payload=payload,
        receipt=QuantumReceipt(
            mode="local",
            source="python.secrets",
            raw_hash=sha256_bytes(payload),
            result_hash=sha256_bytes(payload),
            fallback_reason=reason,
        ),
    )


class IBMQuantumEntropy:
    """IBM Quantum Runtime adapter.

    The adapter samples a small Hadamard-measure circuit and uses the returned
    shot bytes as seed material. It records backend/job/result hashes while
    never persisting the API key. This is provenance/entropy input, not a
    claim that the QPU renders media or guarantees a quality advantage.
    """

    def __init__(self, settings: Settings):
        self.settings = settings

    def _service(self):
        try:
            from qiskit_ibm_runtime import QiskitRuntimeService
        except ImportError as exc:
            raise QuantumUnavailable("qiskit-ibm-runtime is not installed") from exc
        kwargs: dict[str, Any] = {"channel": "ibm_quantum_platform"}
        if self.settings.ibm_api_key:
            kwargs["token"] = self.settings.ibm_api_key
        if self.settings.ibm_instance:
            kwargs["instance"] = self.settings.ibm_instance
        try:
            return QiskitRuntimeService(**kwargs)
        except Exception as exc:  # SDK/network/auth errors vary by release
            raise QuantumUnavailable(f"IBM Quantum service unavailable: {exc}") from exc

    def _backend(self, service):
        try:
            if self.settings.ibm_backend:
                return service.backend(name=self.settings.ibm_backend)
            return service.least_busy(operational=True, simulator=False, min_num_qubits=8)
        except Exception as exc:
            raise QuantumUnavailable(f"No usable IBM Quantum backend: {exc}") from exc

    def status(self) -> dict[str, Any]:
        try:
            service = self._service()
            backend = self._backend(service)
            return {
                "available": True,
                "mode": "ibm",
                "channel": "ibm_quantum_platform",
                "backend": getattr(backend, "name", None),
                "instance_configured": bool(self.settings.ibm_instance),
            }
        except QuantumUnavailable as exc:
            return {
                "available": False,
                "mode": "ibm",
                "channel": "ibm_quantum_platform",
                "reason": str(exc),
                "instance_configured": bool(self.settings.ibm_instance),
            }

    def sample(self, size: int = 32) -> EntropySample:
        try:
            from qiskit import QuantumCircuit
            from qiskit.transpiler import generate_preset_pass_manager
            from qiskit_ibm_runtime import SamplerV2 as Sampler
        except ImportError as exc:
            raise QuantumUnavailable("Qiskit runtime dependencies are not installed") from exc

        service = self._service()
        backend = self._backend(service)
        qubits = 8
        circuit = QuantumCircuit(qubits)
        circuit.h(range(qubits))
        circuit.measure_all()
        try:
            pass_manager = generate_preset_pass_manager(optimization_level=1, backend=backend)
            isa_circuit = pass_manager.run(circuit)
            sampler = Sampler(mode=backend)
            shots = max(self.settings.ibm_shots, int(math.ceil(size)))
            job = sampler.run([isa_circuit], shots=shots)
            result = job.result()
            data = result[0].data.meas
            raw = bytes(data.array.tobytes())
            if not raw:
                raise QuantumUnavailable("IBM Sampler returned an empty measurement array")
            counts = data.get_counts()
            job_id = job.job_id() if callable(getattr(job, "job_id", None)) else str(getattr(job, "job_id", ""))
            receipt = QuantumReceipt(
                mode="ibm",
                source="qiskit-runtime-sampler-v2",
                backend=getattr(backend, "name", None),
                job_id=job_id or None,
                raw_hash=sha256_bytes(raw),
                result_hash=sha256_text(json.dumps(counts, sort_keys=True)),
            )
            # Mix/truncate deterministically downstream; retain enough raw shot bytes here.
            return EntropySample(raw[: max(size, 32)], receipt)
        except QuantumUnavailable:
            raise
        except Exception as exc:
            raise QuantumUnavailable(f"IBM quantum sampling failed: {exc}") from exc


def get_entropy(settings: Settings, size: int = 32) -> EntropySample:
    mode = settings.quantum_mode
    if mode in {"off", "none", "disabled"}:
        payload = b"cosmos-quantum-disabled"
        return EntropySample(
            payload=payload,
            receipt=QuantumReceipt(
                mode="off",
                source="constant-disabled-marker",
                raw_hash=sha256_bytes(payload),
                result_hash=sha256_bytes(payload),
            ),
        )
    if mode == "ibm":
        try:
            return IBMQuantumEntropy(settings).sample(size=size)
        except QuantumUnavailable as exc:
            if settings.quantum_strict:
                raise
            return local_entropy(size=size, reason=str(exc))
    return local_entropy(size=size)


def quantum_status(settings: Settings) -> dict[str, Any]:
    if settings.quantum_mode == "ibm":
        return IBMQuantumEntropy(settings).status()
    return {
        "available": True,
        "mode": settings.quantum_mode,
        "source": "python.secrets" if settings.quantum_mode == "local" else "disabled",
    }
