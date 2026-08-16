"""Design Probe: a replayable question about a level.

A Design Probe is the level-design analogue of a unit test:
  - It has a starting state (player, world, knowledge)
  - It has a question / hypothesis
  - It runs a bounded deterministic procedure
  - It returns a structured result with evidence

Every probe is serializable so the same probe can be run:
  before edit / after edit / Blood source / Duke source / converted candidate

Fidelity levels:
  L0 — graph/state reasoning (cheap, deterministic)
  L1 — spatial traversal (actual Build geometry, player dimensions)
  L2 — perceptual traversal (visibility, landmarks, view depth)
  L3 — abstract gameplay reasoning (combat, resources, enemy exposure)

This iteration implements L0-L2 probes. L3 remains architectural.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable

from .state_model import PlayerKnowledge, PlayerState, WorldState


class ProbeError(ValueError):
    """A design probe could not be formed or executed safely."""


# ---------------------------------------------------------------------------
# Evidence classification
# ---------------------------------------------------------------------------

EVIDENCE_STATIC_EXACT = "static_exact"
EVIDENCE_STATIC_APPROXIMATE = "static_approximate"
EVIDENCE_SEMANTIC_SIMULATION = "semantic_simulation"
EVIDENCE_REAL_ENGINE = "real_engine"

EVIDENCE_LEVELS = {
    EVIDENCE_STATIC_EXACT: "Derived from exact map structure (geometry, topology, references)",
    EVIDENCE_STATIC_APPROXIMATE: "Derived from approximate static analysis (heuristics, bounds)",
    EVIDENCE_SEMANTIC_SIMULATION: "Derived from semantic mechanism model (doors, lifts, switches)",
    EVIDENCE_REAL_ENGINE: "Derived from real engine runtime (NBlood/EDuke32 oracle)",
}


@dataclass
class Evidence:
    """A single piece of evidence with its source classification."""

    claim: str
    source: str = EVIDENCE_STATIC_EXACT
    confidence: str = "high"  # high, medium, low, uncertain
    details: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        result: dict[str, Any] = {
            "claim": self.claim,
            "source": self.source,
            "confidence": self.confidence,
        }
        if self.details:
            result["details"] = self.details
        return result


# ---------------------------------------------------------------------------
# Probe schema
# ---------------------------------------------------------------------------

@dataclass
class DesignProbe:
    """A replayable, serializable design probe.

    Schema: llmapper.design-probe
    Version: 1
    """

    probe_type: str  # "access", "route", "progression", "transition", "visibility", "revisit", "escape"
    question: str = ""
    player_state: PlayerState = field(default_factory=PlayerState)
    world_state: WorldState = field(default_factory=WorldState)
    player_knowledge: PlayerKnowledge = field(default_factory=PlayerKnowledge)
    parameters: dict[str, Any] = field(default_factory=dict)
    schema: str = "llmapper.design-probe"
    schema_version: int = 1

    def to_dict(self) -> dict[str, Any]:
        return {
            "$schema": self.schema,
            "schema_version": self.schema_version,
            "probe_type": self.probe_type,
            "question": self.question,
            "player_state": self.player_state.to_dict(),
            "world_state": self.world_state.to_dict(),
            "player_knowledge": self.player_knowledge.to_dict(),
            "parameters": self.parameters,
        }

    @classmethod
    def from_dict(cls, value: dict[str, Any]) -> "DesignProbe":
        if value.get("$schema") != "llmapper.design-probe":
            raise ProbeError(f"not a design probe: {value.get('$schema')}")
        return cls(
            probe_type=str(value["probe_type"]),
            question=str(value.get("question", "")),
            player_state=PlayerState.from_dict(value.get("player_state", {})),
            world_state=WorldState.from_dict(value.get("world_state", {})),
            player_knowledge=PlayerKnowledge.from_dict(value.get("player_knowledge", {})),
            parameters=dict(value.get("parameters", {})),
        )


# ---------------------------------------------------------------------------
# Probe result
# ---------------------------------------------------------------------------

@dataclass
class ProbeResult:
    """Structured result of running a design probe.

    Schema: llmapper.probe-result
    Version: 1
    """

    probe_type: str
    status: str  # "pass", "fail", "inconclusive", "error"
    question: str = ""
    answer: str = ""
    evidence: list[Evidence] = field(default_factory=list)
    measurements: dict[str, Any] = field(default_factory=dict)
    route: list[int] = field(default_factory=list)  # compressed sector path
    blocking_reasons: list[str] = field(default_factory=list)
    required_keys: list[str] = field(default_factory=list)
    required_mechanisms: list[str] = field(default_factory=list)
    state_changes: list[dict[str, Any]] = field(default_factory=list)
    limitations: list[str] = field(default_factory=list)
    fidelity_level: str = "L0"  # L0, L1, L2, L3
    schema: str = "llmapper.probe-result"
    schema_version: int = 1

    def to_dict(self) -> dict[str, Any]:
        result: dict[str, Any] = {
            "$schema": self.schema,
            "schema_version": self.schema_version,
            "probe_type": self.probe_type,
            "status": self.status,
            "fidelity_level": self.fidelity_level,
        }
        if self.question:
            result["question"] = self.question
        if self.answer:
            result["answer"] = self.answer
        if self.evidence:
            result["evidence"] = [e.to_dict() for e in self.evidence]
        if self.measurements:
            result["measurements"] = self.measurements
        if self.route:
            result["route"] = [f"sector:{s}" for s in self.route]
        if self.blocking_reasons:
            result["blocking_reasons"] = self.blocking_reasons
        if self.required_keys:
            result["required_keys"] = self.required_keys
        if self.required_mechanisms:
            result["required_mechanisms"] = self.required_mechanisms
        if self.state_changes:
            result["state_changes"] = self.state_changes
        if self.limitations:
            result["limitations"] = self.limitations
        return result


# ---------------------------------------------------------------------------
# Probe registry
# ---------------------------------------------------------------------------

_PROBE_REGISTRY: dict[str, Callable[..., ProbeResult]] = {}


def register_probe(probe_type: str):
    """Decorator to register a probe implementation."""
    def decorator(func: Callable[..., ProbeResult]) -> Callable[..., ProbeResult]:
        _PROBE_REGISTRY[probe_type] = func
        return func
    return decorator


def get_probe(probe_type: str) -> Callable[..., ProbeResult]:
    """Get a registered probe implementation by type name."""
    if probe_type not in _PROBE_REGISTRY:
        raise ProbeError(f"unknown probe type: {probe_type}")
    return _PROBE_REGISTRY[probe_type]


def list_probes() -> list[str]:
    """List all registered probe types."""
    return sorted(_PROBE_REGISTRY.keys())


def run_probe(probe: DesignProbe, build_ir) -> ProbeResult:
    """Run a design probe against a BuildIR instance.

    The probe is executed by the registered implementation for its type.
    """
    from .build_ir import BuildIR
    if not isinstance(build_ir, BuildIR):
        raise ProbeError("probe requires a BuildIR instance")

    probe_type = probe.probe_type
    if probe_type not in _PROBE_REGISTRY:
        raise ProbeError(f"unknown probe type: {probe_type}")

    return _PROBE_REGISTRY[probe_type](probe, build_ir)
