"""Conditional traversability: which ways open, and what opens them.

`reachability.py` answers whether geometry is part of the level, and says so
plainly in its own limitations: *gating is ignored, a closed door is still a
portal*. That is the right answer to its question and the wrong answer to
this one. This module is the derived view that puts the gates back — a
reading over `reachability.py`'s graph and `effects.py`'s embedding, not a
second graph of its own.

Three kinds of edge come out of it:

* **at rest** — passable without anyone doing anything.
* **conditional** — passable in exactly one of the mechanism's two states,
  carrying the state that enables it and the chain that reaches that state.
* **never** — passable in neither, which is a finding rather than an edge.

The chain is the point. An edge is not annotated "this is a door"; it is
annotated with the trigger that fires, the channel it fires on, the
mechanism that listens, and what that does to the opening — every step of it
a field in the map.

**Scope.** Only Z-motion is read, because only Z-motion has a spatial-effect
reading: `effects.embedding` asks both its questions about a vertical
opening. The rotate and slide families -- 659 campaign sectors -- have no
swept-area test yet and are **excluded**, not silently answered.
"""

from __future__ import annotations

from collections import defaultdict, deque
from dataclasses import dataclass, field
from typing import Any, Iterable, Sequence

from .doors import (
    KEY_NAMES, KEY_TYPES, MOTION_TYPES, PLAYER_HEIGHT, SWITCH_TYPES,
    Z_MOTION_TYPES, _wall_owners, observe_motion_sector,
)
from .effects import STEP_UP, design_object, embedding, physical_effects
from .fragment import SYSTEM_CHANNELS
from .reachability import analyze_reachability

SCHEMA = "llmapper.conditional-traversability"
SCHEMA_VERSION = 1

#: A wall crack. Shot open, it transmits once and does not come back --
#: the campaign's only common irreversible topology change. 108 in the
#: campaign, 107 of which transmit. DNE3L6 supplies the vocabulary:
#: type-408 cracks TX-ing type-459 exploders (`docs/corpus.md`).
CRACK_TYPE = 408
EXPLODER_TYPE = 459
#: Things that are destroyed rather than operated. Firing at one is an action
#: that cannot be taken back, so an edge it opens never closes.
DESTRUCTIBLE_TYPES = frozenset({CRACK_TYPE, 406, 411, 412, 417})

#: How an action reaches a mechanism.
BY_SWITCH = "switch"
BY_SHOT = "shot"
BY_TOUCH = "touch"
BY_PUSH = "push"
BY_KEY = "key"
BY_START = "level_start"
BY_UNKNOWN = "unknown"


class ConditionalError(ValueError):
    pass


def _extra(item: Any) -> dict[str, Any]:
    payload = getattr(item, "extra", None)
    if payload is None or not hasattr(payload, "fields"):
        return {}
    return payload.fields


def channel_name(channel: int) -> str | None:
    """The engine's own name for a channel, where it has one."""
    return SYSTEM_CHANNELS.get(int(channel))


# ---------------------------------------------------------------------------
# Who talks to whom
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class Source:
    """One thing that transmits on a channel."""

    kind: str                 # sprite | wall | sector
    index: int
    type_id: int
    channel: int
    trigger: str
    key: int = 0
    irreversible: bool = False
    once: bool = False

    def to_dict(self) -> dict[str, Any]:
        out = {
            "kind": self.kind, "index": self.index, "type_id": self.type_id,
            "channel": self.channel, "channel_name": channel_name(self.channel),
            "trigger": self.trigger, "irreversible": self.irreversible,
            "once": self.once,
        }
        if self.key:
            out["key"] = self.key
            out["key_name"] = KEY_NAMES.get(self.key)
        return out


def _sprite_trigger(type_id: int, extra: dict[str, Any]) -> str:
    if type_id in SWITCH_TYPES:
        return BY_SWITCH
    if type_id in DESTRUCTIBLE_TYPES:
        return BY_SHOT
    if extra.get("trigger_vector"):
        return BY_SHOT
    if extra.get("trigger_push"):
        return BY_PUSH
    if extra.get("trigger_touch") or extra.get("trigger_proximity"):
        return BY_TOUCH
    return BY_UNKNOWN


def transmitters(disk: Any) -> dict[int, list[Source]]:
    """Every sprite, wall and sector that transmits, indexed by channel.

    Sectors transmit too, and leaving them out is how a `trigger_enter` room
    that opens a door elsewhere looks like an unwired mechanism.
    """
    out: dict[int, list[Source]] = defaultdict(list)
    for index, sprite in enumerate(disk.sprites):
        extra = _extra(sprite)
        channel = int(extra.get("tx_id") or 0)
        if not channel:
            continue
        type_id = int(sprite.fields["type"])
        out[channel].append(Source(
            kind="sprite", index=index, type_id=type_id, channel=channel,
            trigger=_sprite_trigger(type_id, extra),
            key=int(extra.get("key") or 0),
            irreversible=type_id in DESTRUCTIBLE_TYPES,
            once=bool(extra.get("trigger_once")),
        ))
    for index, wall in enumerate(disk.walls):
        extra = _extra(wall)
        channel = int(extra.get("tx_id") or 0)
        if not channel:
            continue
        out[channel].append(Source(
            kind="wall", index=index, type_id=int(wall.fields["type"]),
            channel=channel,
            trigger=BY_PUSH if extra.get("trigger_push") else (
                BY_SHOT if extra.get("trigger_vector") else BY_UNKNOWN),
            key=int(extra.get("key") or 0),
            once=bool(extra.get("trigger_once")),
        ))
    for index, sector in enumerate(disk.sectors):
        extra = _extra(sector)
        channel = int(extra.get("tx_id") or 0)
        if not channel:
            continue
        out[channel].append(Source(
            kind="sector", index=index, type_id=int(sector.fields["type"]),
            channel=channel,
            trigger=BY_TOUCH if (extra.get("trigger_enter")
                                 or extra.get("trigger_proximity")) else (
                BY_PUSH if extra.get("trigger_push") else BY_UNKNOWN),
            key=int(extra.get("key") or 0),
            once=bool(extra.get("trigger_once")),
        ))
    return dict(out)


def key_sprites(disk: Any) -> dict[int, list[int]]:
    """Where each key lies, by the key number an XSECTOR would name."""
    out: dict[int, list[int]] = defaultdict(list)
    for index, sprite in enumerate(disk.sprites):
        key = KEY_TYPES.get(int(sprite.fields["type"]))
        if key:
            out[key].append(index)
    return dict(out)


# ---------------------------------------------------------------------------
# Which side of a mechanism a body can be on
# ---------------------------------------------------------------------------

def rest_state(record: dict[str, Any]) -> str:
    """Which of the two endpoint states the sector is built sitting in.

    XSECTOR `state` says so directly. Where it does not, the sector's own
    stored floor and ceiling do: they are the pose the map ships in.
    """
    if int(record["state"]):
        return "on"
    if (int(record["floor_z"]) == int(record["on_floor_z"])
            and int(record["ceiling_z"]) == int(record["on_ceiling_z"])
            and (int(record["off_floor_z"]) != int(record["on_floor_z"])
                 or int(record["off_ceiling_z"]) != int(record["on_ceiling_z"]))):
        return "on"
    return "off"


def passable(record: dict[str, Any], state: str, neighbour_floor_z: int,
             *, leaving: bool) -> bool:
    """Can a body cross between this mechanism and that neighbour, in `state`?

    Two conditions, and both are needed. The gap has to admit a standing body
    -- which is what a door changes -- and the floors have to be close enough
    to walk between -- which is what a lift changes. Asking only the first
    calls every lift unconditional; asking only the second calls every door
    unconditional.

    **Climbing is limited and falling is not**, so the crossing is directed.
    A body steps up at most `STEP_UP` and drops as far as the map allows, and
    a lift is exactly the mechanism that exploits the difference: ride it up,
    or step off the top and fall back down. Treating the two directions alike
    called 21 of E1M2's crossings impassable when a body can simply jump down
    them.
    """
    floor = int(record[f"{state}_floor_z"])
    ceiling = int(record[f"{state}_ceiling_z"])
    if (floor - ceiling) < PLAYER_HEIGHT:
        return False
    #: Blood's z grows downward, so a smaller number is higher up.
    here, there = (floor, int(neighbour_floor_z)) if leaving else (
        int(neighbour_floor_z), floor)
    return there >= here - STEP_UP


@dataclass
class ConditionalEdge:
    """One crossing that is not simply there."""

    sectors: tuple[int, int]
    mechanism: int
    enabling_state: str
    verdict: str                       # conditional | never
    delta: dict[str, Any] = field(default_factory=dict)
    causes: list[Source] = field(default_factory=list)
    requires_key: int = 0
    irreversible: bool = False
    #: How many walls carry this one crossing.
    walls: int = 1

    def to_dict(self) -> dict[str, Any]:
        out = {
            "from": self.sectors[0], "to": self.sectors[1],
            "sectors": list(self.sectors), "mechanism": self.mechanism,
            "walls": self.walls,
            "enabling_state": self.enabling_state, "verdict": self.verdict,
            "topology_delta": dict(self.delta),
            "causes": [item.to_dict() for item in self.causes],
            "irreversible": self.irreversible,
        }
        if self.requires_key:
            out["requires_key"] = self.requires_key
            out["requires_key_name"] = KEY_NAMES.get(self.requires_key)
        return out


def _causes_for(record: dict[str, Any], wires: dict[int, list[Source]]) -> list[Source]:
    """Every way the mechanism's state gets changed, as sources.

    A mechanism worked by its own wall or by walking into it has no
    transmitter anywhere: it *is* the trigger, and reading only the channel
    graph loses it.
    """
    found: list[Source] = []
    listens = int(record["rx_id"] or 0)
    if listens:
        found.extend(wires.get(listens, ()))
    interaction = record["interaction"]
    direct = interaction.split("+")[0]
    if direct in ("wall_push", "sector_push"):
        found.append(Source(kind="sector", index=record["sector_id"],
                            type_id=record["type_id"], channel=0,
                            trigger=BY_PUSH, key=int(record["key"] or 0),
                            once=bool("trigger_once" in record["triggers"])))
    elif direct == "touch":
        found.append(Source(kind="sector", index=record["sector_id"],
                            type_id=record["type_id"], channel=0,
                            trigger=BY_TOUCH, key=int(record["key"] or 0),
                            once=bool("trigger_once" in record["triggers"])))
    return found


def conditional_edges(disk: Any, *, owners: Sequence[int] | None = None
                      ) -> tuple[list[ConditionalEdge], dict[str, Any]]:
    """Every crossing a Z-motion mechanism gates, with what opens it."""
    owners = list(owners) if owners is not None else _wall_owners(disk)
    wires = transmitters(disk)
    edges: list[ConditionalEdge] = []
    scoped_out = 0
    considered = 0
    inert = 0
    for sector_id in range(len(disk.sectors)):
        record = observe_motion_sector(disk, sector_id, owners=owners)
        if record is None:
            continue
        effects = physical_effects(record)
        if not any(item["effect"].startswith("move_") for item in effects):
            #: Slide and rotate. No swept-area reading exists, so no claim is
            #: made about what they gate -- excluded, not answered.
            if record["type_id"] in MOTION_TYPES:
                scoped_out += 1
            continue
        considered += 1
        rest = rest_state(record)
        other = "off" if rest == "on" else "on"
        #: The embedding is a property of the mechanism, so it is asked once
        #: with *every* neighbour's floor. Asking it per crossing, with one
        #: floor, makes `levels_served >= 2` unsatisfiable by construction --
        #: which meant `reads_as` could never say "carries a body between
        #: levels" and every lift in the campaign read as a door.
        spatial = embedding(record, (
            int(disk.sectors[int(portal["next_sector"])].fields["floor_z"])
            for portal in record["portals"]))
        reads_as = design_object(spatial)
        causes = _causes_for(record, wires)
        if not causes:
            #: Nothing can change this sector's state -- no channel reaches
            #: it, no wall of it is pushable, walking in does nothing. Its
            #: crossings are whatever they are at rest and for ever, so it
            #: gates nothing and contributes no conditional edge.
            #:
            #: Almost all of these are type 0 carrying XSECTOR z endpoints:
            #: `doors._is_motion` accepts them on the endpoints alone, which
            #: is right for "does this sector describe a motion" and wrong
            #: for "can this motion ever happen". E1M3 has eight, and before
            #: this they produced 60 conditional edges opened by nobody.
            inert += 1
            continue
        needs_key = int(record["key"] or 0) or next(
            (item.key for item in causes if item.key), 0)
        #: Irreversible only when *every* way to it is. A door a crack opens
        #: and a switch also opens is not a one-way change.
        irreversible = all(item.irreversible for item in causes)
        by_neighbour: dict[int, list[dict[str, Any]]] = defaultdict(list)
        for portal in record["portals"]:
            by_neighbour[int(portal["next_sector"])].append(portal)
        for neighbour, portals in sorted(by_neighbour.items()):
            floor = int(disk.sectors[neighbour].fields["floor_z"])
            #: Two walls between the same pair of sectors are one crossing.
            #: Emitting one edge per wall double-counted every mechanism that
            #: shares more than one wall with its neighbour.
            for leaving in (True, False):
                at_rest = passable(record, rest, floor, leaving=leaving)
                when_moved = passable(record, other, floor, leaving=leaving)
                if at_rest and when_moved:
                    continue                 # simply a way; nothing to say
                pair = ((sector_id, neighbour) if leaving
                        else (neighbour, sector_id))
                if not at_rest and not when_moved:
                    edges.append(ConditionalEdge(
                        sectors=pair, mechanism=sector_id,
                        enabling_state="none", verdict="never",
                        delta=_delta(record, rest, other, floor, leaving, reads_as),
                        causes=causes, requires_key=needs_key,
                        irreversible=irreversible, walls=len(portals)))
                    continue
                edges.append(ConditionalEdge(
                    sectors=pair, mechanism=sector_id,
                    enabling_state=other if when_moved else rest,
                    verdict="conditional",
                    delta=_delta(record, rest, other, floor, leaving, reads_as),
                    causes=causes, requires_key=needs_key,
                    irreversible=irreversible, walls=len(portals)))
    summary = {
        "z_motion_mechanisms": considered,
        "wired": considered - inert,
        "inert_no_cause": inert,
        "scoped_out_rotate_slide": scoped_out,
        "conditional": sum(1 for e in edges if e.verdict == "conditional"),
        "never": sum(1 for e in edges if e.verdict == "never"),
        "irreversible": sum(1 for e in edges if e.irreversible),
        "keyed": sum(1 for e in edges if e.requires_key),
    }
    return edges, summary


def _delta(record: dict[str, Any], rest: str, other: str,
           neighbour_floor_z: int, leaving: bool, reads_as: str) -> dict[str, Any]:
    """What the motion does to this crossing, in the map's own numbers."""
    return {
        "direction": "out of the mechanism" if leaving else "into it",
        "rest_state": rest,
        "opening_at_rest": int(record[f"{rest}_floor_z"])
                           - int(record[f"{rest}_ceiling_z"]),
        "opening_when_moved": int(record[f"{other}_floor_z"])
                              - int(record[f"{other}_ceiling_z"]),
        "floor_at_rest": int(record[f"{rest}_floor_z"]),
        "floor_when_moved": int(record[f"{other}_floor_z"]),
        "neighbour_floor": int(neighbour_floor_z),
        "standing_height": PLAYER_HEIGHT,
        "step_up": STEP_UP,
        "reads_as": reads_as,
        "note": "climbing is capped at step_up; falling is not, so the two "
                "directions of one crossing can differ",
    }


def route_edges(edges: Sequence["ConditionalEdge"]) -> list[dict[str, Any]]:
    """Collapse a mechanism's crossings into the route it gates.

    A door is one sector with a portal on each side, so it gates two
    crossings and four directed edges. What a reader means by "the door" is
    the single connection between the rooms either side of it, and that is
    what this returns: one route per mechanism, naming the rooms it joins
    and carrying the same cause chain.
    """
    by_mechanism: dict[int, list[ConditionalEdge]] = defaultdict(list)
    for edge in edges:
        if edge.verdict == "conditional":
            by_mechanism[edge.mechanism].append(edge)
    routes = []
    for mechanism, group in sorted(by_mechanism.items()):
        joins = sorted({sector for edge in group for sector in edge.sectors
                        if sector != mechanism})
        first = group[0]
        routes.append({
            "mechanism": mechanism,
            "joins": joins,
            "crossings": len(group),
            "enabling_states": sorted({edge.enabling_state for edge in group}),
            "requires_key": first.requires_key or None,
            "requires_key_name": KEY_NAMES.get(first.requires_key),
            "irreversible": all(edge.irreversible for edge in group),
            "reads_as": first.delta.get("reads_as"),
            "causes": [item.to_dict() for item in first.causes],
        })
    return routes


# ---------------------------------------------------------------------------
# What becomes reachable after an action
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class Action:
    """One thing a player can do that changes the topology.

    Deliberately only three kinds, and each is a thing the map itself
    contains: a switch sprite to work, a destructible to shoot, a key to
    pick up.
    """

    kind: str                 # use_switch | destroy | obtain_key | operate
    index: int = -1           # the sprite, wall or sector acted on
    key: int = 0
    channel: int = 0
    where: int = -1           # the sector the action is performed from

    def to_dict(self) -> dict[str, Any]:
        out = {"kind": self.kind}
        if self.index >= 0:
            out["index"] = self.index
        if self.key:
            out["key"] = self.key
            out["key_name"] = KEY_NAMES.get(self.key)
        if self.channel:
            out["channel"] = self.channel
            out["channel_name"] = channel_name(self.channel)
        if self.where >= 0:
            out["performed_from_sector"] = self.where
        return out

    def describes(self) -> str:
        if self.kind == "obtain_key":
            return f"pick up the {KEY_NAMES.get(self.key, self.key)} key"
        if self.kind == "destroy":
            return f"destroy sprite {self.index} (channel {self.channel})"
        if self.kind == "use_switch":
            return f"use switch sprite {self.index} (channel {self.channel})"
        return f"operate mechanism sector {self.index}"


@dataclass
class Held:
    """What has been done so far."""

    channels: frozenset[int] = frozenset()
    keys: frozenset[int] = frozenset()
    operated: frozenset[int] = frozenset()

    def with_action(self, action: "Action") -> "Held":
        channels, keys, operated = set(self.channels), set(self.keys), set(self.operated)
        if action.channel:
            channels.add(action.channel)
        if action.key:
            keys.add(action.key)
        if action.kind == "operate":
            operated.add(action.index)
        return Held(frozenset(channels), frozenset(keys), frozenset(operated))


def _edge_enabled(edge: "ConditionalEdge", held: Held) -> bool:
    """Is this crossing open, given what has been done?

    The key clause is a real gate and not decoration: a door whose XSECTOR
    names a key does not move for a body that has not got it, however many
    times the channel is fired.
    """
    if edge.verdict != "conditional":
        return False
    if edge.requires_key and edge.requires_key not in held.keys:
        return False
    for cause in edge.causes:
        if cause.channel and cause.channel in held.channels:
            return True
        if not cause.channel and edge.mechanism in held.operated:
            return True
    return False


def walkable_at_rest(disk: Any) -> set[tuple[int, int]]:
    """`spatial.py`'s stricter opinion about which portals a body can use.

    `reachability.portal_graph` ignores gating on purpose -- a closed door is
    still a portal -- which is right for "is this geometry part of the level"
    and too permissive here. `analyze_spatial` additionally refuses a wall
    carrying the blocking cstat, a portal narrower than 512, and an opening
    under 4096.

    Neither base is right on its own, and the difference is not small: on
    E1M1 the permissive one calls 125 of 155 sectors reachable at rest and
    the strict one calls 2, because the player start's two wide portals both
    carry the blocking flag. See `reports/blood-conditional-topology.md`.
    """
    from .spatial import analyze_spatial

    view = analyze_spatial(disk.to_build_ir())["views"]["traversability"]
    out: set[tuple[int, int]] = set()
    for edge in view["walkable_at_rest"]:
        left, right = (int(item.split(":")[1]) for item in edge["sectors"])
        out.add((left, right))
        out.add((right, left))
    return out


def _directed_base(disk: Any, gated: set[tuple[int, int]], *, strict: bool
                   ) -> tuple[dict[int, set[int]], Any]:
    """The base graph, directed, with the gated crossings removed.

    The base is taken whole rather than rebuilt: this view's job is to put
    gates back on somebody else's answer, not to have a second opinion about
    what a portal is. Links and teleports come along with it.
    """
    reach = analyze_reachability(disk)
    allowed = walkable_at_rest(disk) if strict else None
    out: dict[int, set[int]] = defaultdict(set)
    for sector, neighbours in reach.graph.items():
        for neighbour in neighbours:
            if (sector, neighbour) in gated:
                continue
            if allowed is not None and (sector, neighbour) not in allowed:
                #: Links and teleports have no portal, so `analyze_spatial`
                #: never saw them; they are kept whatever the base.
                if not any((sector, neighbour) == tuple(record["sectors"])
                           or (neighbour, sector) == tuple(record["sectors"])
                           for group in (reach.links, reach.teleports)
                           for record in group):
                    continue
            out[sector].add(neighbour)
    return out, reach


def _flood(graph: dict[int, set[int]], origin: int) -> set[int]:
    seen, pending = {origin}, deque([origin])
    while pending:
        current = pending.popleft()
        for neighbour in graph.get(current, ()):
            if neighbour not in seen:
                seen.add(neighbour)
                pending.append(neighbour)
    return seen


@dataclass
class ConditionalGraph:
    """The whole reading of one map, ready to be asked questions."""

    disk: Any
    edges: list[ConditionalEdge]
    summary: dict[str, Any]
    start: int
    base: dict[int, set[int]] = field(default_factory=dict)
    gated: set[tuple[int, int]] = field(default_factory=set)
    reach: Any = None

    def reachable(self, held: Held) -> set[int]:
        graph = {sector: set(neighbours) for sector, neighbours in self.base.items()}
        for edge in self.edges:
            if _edge_enabled(edge, held):
                graph.setdefault(edge.sectors[0], set()).add(edge.sectors[1])
        return _flood(graph, self.start)

    def available_actions(self, held: Held, reached: set[int]) -> list[Action]:
        """Everything a body standing in `reached` could do next.

        An action a player cannot walk to is not available, which is the
        whole reason this is computed against the reached set rather than
        against the map.
        """
        found: dict[tuple[str, int], Action] = {}
        for index, sprite in enumerate(self.disk.sprites):
            sector = int(sprite.fields["sector"])
            if sector not in reached:
                continue
            type_id = int(sprite.fields["type"])
            extra = _extra(sprite)
            channel = int(extra.get("tx_id") or 0)
            key = KEY_TYPES.get(type_id)
            if key and key not in held.keys:
                found[("obtain_key", index)] = Action(
                    kind="obtain_key", index=index, key=key, where=sector)
            elif type_id in DESTRUCTIBLE_TYPES and channel and channel not in held.channels:
                found[("destroy", index)] = Action(
                    kind="destroy", index=index, channel=channel, where=sector)
            elif type_id in SWITCH_TYPES and channel and channel not in held.channels:
                found[("use_switch", index)] = Action(
                    kind="use_switch", index=index, channel=channel, where=sector)
        for edge in self.edges:
            if edge.verdict != "conditional" or edge.mechanism in held.operated:
                continue
            if any(cause.channel for cause in edge.causes):
                continue
            #: A door with no channel is worked by hand, so a body has to be
            #: able to stand beside it.
            if edge.sectors[0] in reached or edge.sectors[1] in reached:
                found[("operate", edge.mechanism)] = Action(
                    kind="operate", index=edge.mechanism,
                    where=edge.sectors[0] if edge.sectors[0] in reached
                    else edge.sectors[1])
        return sorted(found.values(), key=lambda item: (item.kind, item.index))

    def explain(self, action: Action, opened: Sequence["ConditionalEdge"]
                ) -> list[dict[str, Any]]:
        """The chain, one link at a time, every link a field in the map."""
        chains = []
        for edge in opened:
            cause = next(
                (item for item in edge.causes
                 if item.channel == action.channel and action.channel), None)
            chains.append({
                "trigger": (cause.to_dict() if cause is not None
                            else {"kind": "direct", "index": edge.mechanism,
                                  "trigger": "push or touch, no channel"}),
                "channel": ({"id": action.channel,
                             "name": channel_name(action.channel)}
                            if action.channel else None),
                "mechanism": {"sector": edge.mechanism,
                              "enabling_state": edge.enabling_state},
                "topology_delta": dict(edge.delta),
                "crossing": {"from": edge.sectors[0], "to": edge.sectors[1]},
                "irreversible": edge.irreversible,
                "requires_key": edge.requires_key or None,
            })
        return chains


def build_graph(disk: Any, *, owners: Sequence[int] | None = None,
                strict: bool = False) -> ConditionalGraph:
    """Read one map into a conditional-traversability graph.

    `strict` swaps the permissive base for `spatial.py`'s walkable-at-rest
    one. The two disagree enormously and neither is right, which is a finding
    rather than a setting -- see `walkable_at_rest`.
    """
    edges, summary = conditional_edges(disk, owners=owners)
    gated = {edge.sectors for edge in edges}
    base, reach = _directed_base(disk, gated, strict=strict)
    summary = {**summary, "base": "walkable_at_rest" if strict else "portal_graph"}
    start = int(reach.start["sector"])
    return ConditionalGraph(disk=disk, edges=edges, summary=summary,
                            start=start, base=base, gated=gated, reach=reach)


def what_becomes_reachable(disk: Any, action: Action, *,
                           already: Held | None = None,
                           graph: ConditionalGraph | None = None) -> dict[str, Any]:
    """The phase's question, answered mechanically and with its provenance."""
    graph = graph or build_graph(disk)
    before_held = already or Held()
    before = graph.reachable(before_held)
    after_held = before_held.with_action(action)
    after = graph.reachable(after_held)
    opened = [edge for edge in graph.edges
              if _edge_enabled(edge, after_held)
              and not _edge_enabled(edge, before_held)]
    return {
        "$schema": SCHEMA,
        "schema_version": SCHEMA_VERSION,
        "action": action.to_dict(),
        "action_reads_as": action.describes(),
        "reachable_before": len(before),
        "reachable_after": len(after),
        "newly_reachable": sorted(after - before),
        "crossings_opened": [edge.to_dict() for edge in opened],
        "why": graph.explain(action, opened),
        "limitations": list(LIMITATIONS),
    }


def frontier(disk: Any, *, graph: ConditionalGraph | None = None,
             rounds: int = 32) -> dict[str, Any]:
    """Spawn, then what each obtainable action unlocks, in order.

    Each round asks what a body could do from where it can already stand,
    scores every one of those actions on its own, then takes all of them and
    goes round again. The order within a round is not a claim about play
    order -- only the rounds are ordered.
    """
    graph = graph or build_graph(disk)
    held = Held()
    reached = graph.reachable(held)
    steps = [{"round": 0, "action": None, "reached": len(reached),
              "newly_reachable": sorted(reached)}]
    for index in range(1, rounds + 1):
        actions = graph.available_actions(held, reached)
        fresh = [item for item in actions
                 if not (item.kind == "obtain_key" and item.key in held.keys)]
        if not fresh:
            break
        scored = []
        for action in fresh:
            after = graph.reachable(held.with_action(action))
            scored.append((action, sorted(after - reached)))
        nxt = held
        for action in fresh:
            nxt = nxt.with_action(action)
        after_all = graph.reachable(nxt)
        if after_all == reached and nxt == held:
            break
        steps.append({
            "round": index,
            "actions": [{"action": action.to_dict(),
                         "reads_as": action.describes(),
                         "unlocks": len(gained), "newly_reachable": gained[:24]}
                        for action, gained in scored],
            "reached": len(after_all),
            "newly_reachable": sorted(after_all - reached)[:64],
        })
        if after_all == reached and nxt != held:
            held, reached = nxt, after_all
            continue
        held, reached = nxt, after_all
    return {
        "$schema": SCHEMA, "schema_version": SCHEMA_VERSION,
        "start_sector": graph.start,
        "sector_count": len(disk.sectors),
        "at_rest_reachable": steps[0]["reached"],
        "finally_reachable": steps[-1]["reached"],
        "gated_by_action": steps[-1]["reached"] - steps[0]["reached"],
        "rounds": steps,
        "summary": dict(graph.summary),
        "limitations": list(LIMITATIONS),
    }


LIMITATIONS = (
    "Only Z-motion is gated. The rotate and slide families have no "
    "swept-area spatial-effect reading, so their crossings are left in the "
    "base graph as `reachability.py` had them -- excluded, not answered.",
    "The base graph is `reachability.py`'s, so a static height difference "
    "between two ordinary sectors is not gated. Only a mechanism's own "
    "crossings are.",
    "Climbing is capped at the engine's step-up and falling is not, so a "
    "crossing is directed. A lift a body can ride up and step off is two "
    "different edges.",
    "A mechanism nothing can reach -- no channel, no pushable wall, no "
    "trigger on entry -- gates nothing, because its state never changes. "
    "Those are counted as inert rather than read as permanent walls.",
    "Firing a channel is modelled as making every listener's enabling state "
    "available. A channel that toggles listeners into different states, or "
    "a `command` that turns one off, is not distinguished.",
    "Whether a body can *survive* a crossing is not asked. A long fall is a "
    "way down.",
)
