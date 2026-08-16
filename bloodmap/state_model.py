"""Explicit state layers for Design Probes.

These are lightweight, serializable models separate from the static BuildIR.
They capture only what a probe needs to answer a bounded design question.

Separation rationale:
  - PlayerState: where the player is, what they carry
  - WorldState: which mechanisms are active, which routes are enabled
  - PlayerKnowledge: what the player has seen, known landmarks, known routes

Same geometry + different knowledge = different player experience.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


class StateError(ValueError):
    """A state model constraint was violated."""


# ---------------------------------------------------------------------------
# PlayerState
# ---------------------------------------------------------------------------

@dataclass
class PlayerState:
    """Player position, sector, angle, and inventory relevant to traversal.

    Inventory is intentionally minimal: keys and any profile-relevant items.
    Weapons/combat are not modeled yet.
    """

    sector: int = 0
    x: int = 0
    y: int = 0
    z: int = 0
    angle: int = 0
    keys: frozenset[str] = field(default_factory=frozenset)

    def to_dict(self) -> dict[str, Any]:
        return {
            "sector": int(self.sector),
            "x": int(self.x),
            "y": int(self.y),
            "z": int(self.z),
            "angle": int(self.angle),
            "keys": sorted(self.keys),
        }

    @classmethod
    def from_dict(cls, value: dict[str, Any]) -> "PlayerState":
        return cls(
            sector=int(value.get("sector", 0)),
            x=int(value.get("x", 0)),
            y=int(value.get("y", 0)),
            z=int(value.get("z", 0)),
            angle=int(value.get("angle", 0)),
            keys=frozenset(str(k) for k in value.get("keys", [])),
        )

    def with_keys(self, keys: frozenset[str]) -> "PlayerState":
        return PlayerState(
            sector=self.sector, x=self.x, y=self.y, z=self.z,
            angle=self.angle, keys=keys,
        )


# ---------------------------------------------------------------------------
# WorldState
# ---------------------------------------------------------------------------

@dataclass
class WorldState:
    """Semantic mechanism state: doors open/closed, lifts position, switches,
    destructible barriers, water/teleport links, enabled/disabled routes.

    This does not duplicate arbitrary engine runtime internals.
    It models only the aspects needed to answer bounded design questions.
    """

    opened_portals: frozenset[str] = field(default_factory=frozenset)
    activated_mechanisms: frozenset[str] = field(default_factory=frozenset)
    destroyed_barriers: frozenset[str] = field(default_factory=frozenset)
    enabled_routes: frozenset[str] = field(default_factory=frozenset)
    notes: str = ""

    def to_dict(self) -> dict[str, Any]:
        result: dict[str, Any] = {
            "opened_portals": sorted(self.opened_portals),
            "activated_mechanisms": sorted(self.activated_mechanisms),
            "destroyed_barriers": sorted(self.destroyed_barriers),
            "enabled_routes": sorted(self.enabled_routes),
        }
        if self.notes:
            result["notes"] = self.notes
        return result

    @classmethod
    def from_dict(cls, value: dict[str, Any] | None) -> "WorldState":
        value = value or {}
        unknown = sorted(set(value) - {
            "opened_portals", "activated_mechanisms", "destroyed_barriers",
            "enabled_routes", "notes",
        })
        if unknown:
            raise StateError(f"unsupported WorldState fields: {unknown}")
        return cls(
            opened_portals=frozenset(str(p) for p in value.get("opened_portals", [])),
            activated_mechanisms=frozenset(str(m) for m in value.get("activated_mechanisms", [])),
            destroyed_barriers=frozenset(str(b) for b in value.get("destroyed_barriers", [])),
            enabled_routes=frozenset(str(r) for r in value.get("enabled_routes", [])),
            notes=str(value.get("notes", "")),
        )

    @classmethod
    def initial(cls) -> "WorldState":
        """The default initial world state: no mechanisms activated."""
        return cls()

    def with_opened_portal(self, portal_id: str) -> "WorldState":
        return WorldState(
            opened_portals=self.opened_portals | {portal_id},
            activated_mechanisms=self.activated_mechanisms,
            destroyed_barriers=self.destroyed_barriers,
            enabled_routes=self.enabled_routes,
            notes=self.notes,
        )

    def with_activated_mechanism(self, mechanism_id: str) -> "WorldState":
        return WorldState(
            opened_portals=self.opened_portals,
            activated_mechanisms=self.activated_mechanisms | {mechanism_id},
            destroyed_barriers=self.destroyed_barriers,
            enabled_routes=self.enabled_routes,
            notes=self.notes,
        )


# ---------------------------------------------------------------------------
# PlayerKnowledge
# ---------------------------------------------------------------------------

@dataclass
class PlayerKnowledge:
    """What the player has seen and knows: seen sectors, known landmarks,
    known locked routes, visited areas, known objectives.

    Kept separate from physical world state because:
      same geometry + different knowledge = different player experience
    """

    seen_sectors: frozenset[int] = field(default_factory=frozenset)
    known_landmarks: frozenset[str] = field(default_factory=frozenset)
    known_locked_routes: frozenset[str] = field(default_factory=frozenset)
    visited_areas: frozenset[str] = field(default_factory=frozenset)
    known_objectives: frozenset[str] = field(default_factory=frozenset)
    notes: str = ""

    def to_dict(self) -> dict[str, Any]:
        result: dict[str, Any] = {
            "seen_sectors": sorted(self.seen_sectors),
            "known_landmarks": sorted(self.known_landmarks),
            "known_locked_routes": sorted(self.known_locked_routes),
            "visited_areas": sorted(self.visited_areas),
            "known_objectives": sorted(self.known_objectives),
        }
        if self.notes:
            result["notes"] = self.notes
        return result

    @classmethod
    def from_dict(cls, value: dict[str, Any] | None) -> "PlayerKnowledge":
        value = value or {}
        allowed = {
            "seen_sectors", "known_landmarks", "known_locked_routes",
            "visited_areas", "known_objectives", "notes",
        }
        unknown = sorted(set(value) - allowed)
        if unknown:
            raise StateError(f"unsupported PlayerKnowledge fields: {unknown}")
        return cls(
            seen_sectors=frozenset(int(s) for s in value.get("seen_sectors", [])),
            known_landmarks=frozenset(str(l) for l in value.get("known_landmarks", [])),
            known_locked_routes=frozenset(str(r) for r in value.get("known_locked_routes", [])),
            visited_areas=frozenset(str(a) for a in value.get("visited_areas", [])),
            known_objectives=frozenset(str(o) for o in value.get("known_objectives", [])),
            notes=str(value.get("notes", "")),
        )

    @classmethod
    def empty(cls) -> "PlayerKnowledge":
        return cls()

    def with_seen_sectors(self, sectors: frozenset[int]) -> "PlayerKnowledge":
        return PlayerKnowledge(
            seen_sectors=self.seen_sectors | sectors,
            known_landmarks=self.known_landmarks,
            known_locked_routes=self.known_locked_routes,
            visited_areas=self.visited_areas,
            known_objectives=self.known_objectives,
            notes=self.notes,
        )
