"""Game-neutral semantic mechanisms and representability.

Blood and Duke share Build, so BuildIR cannot prove engine-independence.
This layer sits *above* native encodings:

    Doom native ─┐
    Blood native ─┼→ SemanticLevel / SemanticMechanism → target lowering
    Duke native ──┘

It is intentionally small. A concept exists here only when Doom and Blood
(or Duke) both supply evidence, and native object references are retained.
BuildIR remains a Build-engine contract and is not a universal map IR.
"""

from __future__ import annotations

from collections import defaultdict, deque
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Iterable


class MechanismError(ValueError):
    pass


class Representability(str, Enum):
    """Asymmetric conversion fidelity. Reverse direction is often worse."""

    EXACT = "exact"
    SEMANTIC = "semantic"
    APPROXIMATE = "approximate"
    REQUIRES_REDESIGN = "requires_redesign"
    UNSUPPORTED = "unsupported"


# Justified by Doom linedef specials (GZDoom xlat/base.txt) plus Blood XSECTOR
# motion / TX-RX / keys already used in this repository.
MECHANISM_KINDS = (
    "door",
    "lift",
    "switch",
    "key_gate",
    "teleport",
    "exit",
    "secret",
    "damage_area",
    "stair",
    "light",
    "floor_move",
    "ceiling_move",
)


@dataclass
class SemanticMechanism:
    """A gameplay mechanism with native evidence still attached."""

    id: str
    kind: str
    source_game: str
    native_refs: list[str]
    activation: str
    repeatable: bool
    state: str
    parameters: dict[str, Any] = field(default_factory=dict)
    required_keys: list[str] = field(default_factory=list)
    targets: list[str] = field(default_factory=list)
    fidelity: str = Representability.SEMANTIC.value
    confidence: str = "high"
    notes: str = ""

    def to_dict(self) -> dict[str, Any]:
        result = {
            "id": self.id,
            "kind": self.kind,
            "source_game": self.source_game,
            "native_refs": list(self.native_refs),
            "activation": self.activation,
            "repeatable": self.repeatable,
            "state": self.state,
            "parameters": dict(self.parameters),
            "required_keys": list(self.required_keys),
            "targets": list(self.targets),
            "fidelity": self.fidelity,
            "confidence": self.confidence,
        }
        if self.notes:
            result["notes"] = self.notes
        return result


@dataclass
class SemanticRegion:
    id: str
    native_refs: list[str]
    items: list[str] = field(default_factory=list)
    tags: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id, "native_refs": list(self.native_refs),
            "items": list(self.items), "tags": list(self.tags),
        }


@dataclass
class SemanticConnection:
    id: str
    kind: str
    source: str
    target: str
    mechanism_id: str | None = None
    required_keys: list[str] = field(default_factory=list)
    initial: str = "open"

    def to_dict(self) -> dict[str, Any]:
        result = {
            "id": self.id, "kind": self.kind, "source": self.source, "target": self.target,
            "initial": self.initial, "required_keys": list(self.required_keys),
        }
        if self.mechanism_id:
            result["mechanism_id"] = self.mechanism_id
        return result


@dataclass
class SemanticLevel:
    """Engine-neutral progression graph. Native encodings are references only."""

    source_game: str
    regions: list[SemanticRegion]
    connections: list[SemanticConnection]
    mechanisms: list[SemanticMechanism]
    start_region: str
    exit_regions: list[str] = field(default_factory=list)
    notes: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "$schema": "llmapper.semantic-level",
            "schema_version": 1,
            "source_game": self.source_game,
            "start_region": self.start_region,
            "exit_regions": list(self.exit_regions),
            "regions": [item.to_dict() for item in self.regions],
            "connections": [item.to_dict() for item in self.connections],
            "mechanisms": [item.to_dict() for item in self.mechanisms],
            "notes": self.notes,
        }


def representability_matrix() -> list[dict[str, str]]:
    """Documented asymmetry: Doom→Blood is usually a lowering into a richer target."""
    return [
        {
            "source": "doom", "target": "blood", "concept": "normal door",
            "representability": Representability.SEMANTIC.value,
            "notes": "Doom linedef special + tag → Blood type-600 Z-motion; activation modes differ",
        },
        {
            "source": "doom", "target": "blood", "concept": "keyed door",
            "representability": Representability.SEMANTIC.value,
            "notes": "Doom card/skull colors → Blood key 100/101/102; card vs skull collapsed",
        },
        {
            "source": "doom", "target": "blood", "concept": "switch-activated door",
            "representability": Representability.SEMANTIC.value,
            "notes": "Doom USE linedef → Blood switch sprite TX / XSECTOR RX",
        },
        {
            "source": "doom", "target": "blood", "concept": "walkover-triggered door",
            "representability": Representability.APPROXIMATE.value,
            "notes": "Doom WALK linedef → Blood XSECTOR trigger_enter; no linedef walk trigger",
        },
        {
            "source": "doom", "target": "blood", "concept": "lift",
            "representability": Representability.SEMANTIC.value,
            "notes": "Doom plat down-wait-up → Blood type-600 floor motion",
        },
        {
            "source": "doom", "target": "blood", "concept": "teleport",
            "representability": Representability.SEMANTIC.value,
            "notes": "Doom special 39/97 + teleport dest → Blood type 604 + warp marker",
        },
        {
            "source": "doom", "target": "blood", "concept": "exit",
            "representability": Representability.SEMANTIC.value,
            "notes": "Doom special 11/52 → Blood channel-4 exit switch",
        },
        {
            "source": "doom", "target": "blood", "concept": "secret sector",
            "representability": Representability.APPROXIMATE.value,
            "notes": "Doom sector special 9 counted; Blood has no identical secret tally",
        },
        {
            "source": "doom", "target": "blood", "concept": "damage floor",
            "representability": Representability.SEMANTIC.value,
            "notes": "Doom nukage/hellslime specials → Blood XSECTOR damage_type",
        },
        {
            "source": "blood", "target": "doom", "concept": "rotating sector",
            "representability": Representability.REQUIRES_REDESIGN.value,
            "notes": "Classic Doom has no rotating sector primitive",
        },
        {
            "source": "blood", "target": "doom", "concept": "sliding door",
            "representability": Representability.REQUIRES_REDESIGN.value,
            "notes": "Classic Doom doors are vertical sector motion, not wall translation",
        },
        {
            "source": "build", "target": "doom", "concept": "stacked/overlapping sectors",
            "representability": Representability.UNSUPPORTED.value,
            "notes": "Classic Doom sectors partition the XY plane; Build stacking has no native home",
        },
    ]


def solve_progression(
    level: SemanticLevel,
    *,
    initial_keys: Iterable[str] = (),
    max_steps: int = 256,
) -> dict[str, Any]:
    """Reachability over semantic connections. Native encodings are not consulted."""
    regions = {item.id: item for item in level.regions}
    if level.start_region not in regions:
        raise MechanismError(f"start region {level.start_region!r} is missing")
    by_id = {item.id: item for item in level.mechanisms}
    keys = set(initial_keys)
    reached = {level.start_region}
    opened: set[str] = set()
    events: list[dict[str, Any]] = []

    def collect_items() -> None:
        for region_id in list(reached):
            for item in regions[region_id].items:
                if item.startswith("key:") and item not in keys:
                    keys.add(item)
                    events.append({"kind": "take-key", "region": region_id, "item": item})

    def usable(connection: SemanticConnection) -> bool:
        if connection.source not in reached:
            return False
        if connection.kind == "teleport":
            mechanism = by_id.get(connection.mechanism_id or "")
            if mechanism and mechanism.activation == "walk" and connection.source in reached:
                return True
            return connection.source in reached
        needed = {f"key:{name}" if not str(name).startswith("key:") else str(name) for name in connection.required_keys}
        if needed and not needed <= keys:
            return False
        if connection.initial == "open":
            return True
        if connection.id in opened:
            return True
        if connection.kind in {"door", "locked_door", "key_gate", "lift"}:
            mechanism = by_id.get(connection.mechanism_id or "")
            if mechanism is None:
                return needed <= keys
            if mechanism.activation in {"use", "walk", "switch", "enter"}:
                return True
        return False

    collect_items()
    for _step in range(int(max_steps)):
        progressed = False
        for connection in level.connections:
            if connection.target in reached and connection.kind != "teleport":
                continue
            if not usable(connection):
                continue
            if connection.initial != "open":
                opened.add(connection.id)
                if connection.mechanism_id:
                    for other in level.connections:
                        if other.mechanism_id == connection.mechanism_id:
                            opened.add(other.id)
                events.append({
                    "kind": "open", "connection": connection.id, "mechanism": connection.mechanism_id,
                    "from": connection.source, "to": connection.target,
                })
            if connection.target not in reached:
                reached.add(connection.target)
                events.append({"kind": "reach", "region": connection.target, "via": connection.id})
                progressed = True
        collect_items()
        if not progressed:
            # Retry after keys collected in newly reached rooms.
            second = False
            for connection in level.connections:
                if connection.target in reached:
                    continue
                if usable(connection) and connection.target not in reached:
                    if connection.initial != "open":
                        opened.add(connection.id)
                    reached.add(connection.target)
                    events.append({"kind": "reach", "region": connection.target, "via": connection.id})
                    second = True
            collect_items()
            if not second:
                break
            progressed = True
        if not progressed:
            break

    exits_reached = [item for item in level.exit_regions if item in reached]
    return {
        "$schema": "llmapper.progression-solution",
        "schema_version": 1,
        "start_region": level.start_region,
        "reached_regions": sorted(reached),
        "keys": sorted(keys),
        "opened_connections": sorted(opened),
        "exits_reached": exits_reached,
        "exit_reachable": bool(exits_reached) if level.exit_regions else False,
        "events": events,
        "limitations": [
            "graph reasoning over declared semantic connections",
            "does not simulate combat, timing, or renderer occlusion",
        ],
    }


def compare_progression(left: dict[str, Any], right: dict[str, Any]) -> dict[str, Any]:
    """Compare two engine implementations of the same semantic scenario."""
    fields = ("reached_regions", "keys", "exits_reached", "exit_reachable")
    matches = {name: left.get(name) == right.get(name) for name in fields}
    return {
        "same_exit_reachability": matches["exit_reachable"] and matches["exits_reached"],
        "same_keys": matches["keys"],
        "same_reached_set": matches["reached_regions"],
        "matches": matches,
    }
