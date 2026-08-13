"""COSMOS quantum media orchestration engine."""

from .config import Settings
from .state import CSTState, HebbianAssociator
from .synaptic import PROTOCOL as SYNAPTIC_PROTOCOL, SynapticCore, pulse_snapshot
from .timeline import ChunkPlan, plan_timeline

__all__ = [
    "Settings",
    "CSTState",
    "HebbianAssociator",
    "SynapticCore",
    "SYNAPTIC_PROTOCOL",
    "pulse_snapshot",
    "ChunkPlan",
    "plan_timeline",
]
__version__ = "0.3.0"
