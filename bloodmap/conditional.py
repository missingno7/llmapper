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
from .effects import (
    OPENS_A_WAY, PAYLOAD_NOTHING, PAYLOAD_SPRITES, STEP_UP, design_object,
    embedding, leaf_blocks, physical_effects, portal_midpoint, swept_motion,
    swept_opening,
)
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
DESTRUCTIBLE_TYPES = frozenset({CRACK_TYPE, 400, 406, 411, 412,
                                416, 417})

#: Build wall cstat bits. Bit 0 stops a body; bit 4 makes the mid-texture
#: solid-looking; bit 6 stops a hitscan. Only bit 0 decides whether a body
#: gets through, masked or not.
WALL_BLOCK, WALL_MASKED, WALL_HITSCAN = 1, 16, 64

#: kWallGib (NBlood `common_game.h:459`). **The only wall a mechanism can
#: reopen.** `triggers.cpp:SetupGibWallState` clears `cstat & 65` and the
#: masked bit on both sides when the XWALL's `state` is 1, and sets them
#: again when it is 0. Nothing else in the engine changes a wall's blocking
#: bit -- a Z-motion sector moves floors and ceilings, never cstat -- so a
#: blocking wall that is not a gib wall is shut for ever.
KWALLGIB = 511

#: The three base graphs, and what each assumes. One is the default; all
#: three stay callable, because they disagree by a lot and the disagreement
#: is a finding rather than a setting.
BASE_OPTIMISTIC = "optimistic"
BASE_BLOCKING_AWARE = "blocking_aware"
BASE_STRICT = "strict"
BASES = {
    BASE_OPTIMISTIC: "reachability.portal_graph: every two-sided wall is a "
                     "way, gating ignored. Reaches behind shut doors.",
    BASE_BLOCKING_AWARE: "portal_graph, minus crossings whose wall carries "
                         "the blocking cstat, plus those blocking walls a "
                         "kWallGib mechanism reopens. The default.",
    BASE_STRICT: "spatial.walkable_at_rest: blocking flag, portal width "
                 "below 512 and opening below 4096 are all hard stops, and "
                 "nothing reopens any of them.",
}

#: How an action reaches a mechanism.
BY_SWITCH = "switch"
BY_SHOT = "shot"
BY_TOUCH = "touch"
BY_PUSH = "push"
BY_PICKUP = "pickup"
BY_GENERATOR = "generator"
#: Not a player action at all: the thing listens on one channel and
#: retransmits on another. Three quarters of what this classifier first
#: called `unknown` is this -- a link in a chain rather than its head.
BY_RELAY = "relay"
#: A body leaving the sector rather than entering it -- Blood's `trigger_exit`.
BY_LEAVE = "leave"
#: Something dying. A dude that transmits does it on death.
BY_KILL = "kill"
BY_KEY = "key"
BY_START = "level_start"
BY_UNKNOWN = "unknown"

#: kGenTrigger and its family: things that fire a channel on their own
#: schedule (NBlood `kGenTrigger` 700 upward).
GENERATOR_TYPES = frozenset(range(700, 712))
#: Sprite categories a player takes rather than works. A key that transmits
#: when collected is a cause, and calling it unknown loses the commonest
#: progression step in the game.
PICKUP_CATEGORIES = frozenset({"key", "health", "ammo", "weapon", "armor",
                               "powerup", "item"})


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


def _category(kind: str, type_id: int) -> str:
    from .blood_types import classify

    try:
        return classify(kind, type_id).get("category") or ""
    except Exception:
        return ""


def _trigger_for(kind: str, type_id: int, extra: dict[str, Any]) -> str:
    """How this thing gets fired, in the order the evidence is strongest.

    Player-facing flags first, then what the thing *is*, and only then the
    fallback that it listens to somebody else. Reaching the fallback is the
    common case: a Z-motion sector that transmits when it moves is a relay,
    not an unexplained trigger, and 154 of the campaign's 204 formerly
    `unknown` causes are exactly that.
    """
    if extra.get("trigger_vector"):
        return BY_SHOT
    if extra.get("trigger_push") or extra.get("trigger_wall_push"):
        return BY_PUSH
    if extra.get("trigger_touch") or extra.get("trigger_proximity") \
            or extra.get("trigger_enter"):
        return BY_TOUCH
    if extra.get("trigger_exit"):
        return BY_LEAVE
    if kind == "sprite":
        if type_id in SWITCH_TYPES:
            return BY_SWITCH
        if type_id in DESTRUCTIBLE_TYPES:
            return BY_SHOT
        if type_id in GENERATOR_TYPES:
            return BY_GENERATOR
        if type_id in KEY_TYPES or _category("sprite", type_id) in PICKUP_CATEGORIES:
            return BY_PICKUP
        if _category("sprite", type_id) == "dude":
            return BY_KILL
    if int(extra.get("rx_id") or 0):
        return BY_RELAY
    return BY_UNKNOWN


def _sprite_trigger(type_id: int, extra: dict[str, Any]) -> str:
    return _trigger_for("sprite", type_id, extra)


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
            trigger=_trigger_for("wall", int(wall.fields["type"]), extra),
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
            trigger=_trigger_for("sector", int(sector.fields["type"]), extra),
            key=int(extra.get("key") or 0),
            once=bool(extra.get("trigger_once")),
        ))
    return dict(out)


#: Channels the engine fires by itself when the level loads
#: (`eventq.h`: kChannelLevelStart and the ports' own variants). Anything
#: listening on one of these has already happened before the player does
#: anything at all.
LEVEL_START_CHANNELS = frozenset({7, 17, 18})


def level_start_closure(disk: Any,
                        wires: dict[int, list[Source]] | None = None) -> frozenset[int]:
    """Every channel that has fired before the player moves.

    The level-start broadcast is not a player action and a reading that
    treats it as one gets a level badly wrong. E1M1 is the case: its player
    start is inside a closed casket, and the switch that opens it sits in
    another sector entirely, listening on **rx 7** with a six-tick wait. No
    body can reach that switch, so a frontier that waits for a player to
    work it reports the whole level unreachable -- 2 sectors of 155.

    The closure is transitive, because a start-fired thing may transmit to
    something else that transmits again.
    """
    wires = transmitters(disk) if wires is None else wires
    listeners: dict[int, list[int]] = defaultdict(list)
    for kind, items in (("sprite", disk.sprites), ("wall", disk.walls),
                        ("sector", disk.sectors)):
        for item in items:
            extra = _extra(item)
            listens = int(extra.get("rx_id") or 0)
            sends = int(extra.get("tx_id") or 0)
            if listens and sends:
                listeners[listens].append(sends)
    fired = set(LEVEL_START_CHANNELS)
    pending = list(fired)
    while pending:
        channel = pending.pop()
        for onward in listeners.get(channel, ()):
            if onward not in fired:
                fired.add(onward)
                pending.append(onward)
    return frozenset(fired)


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
    #: A crossing is gated by a moving *sector* or by a breakable *wall*.
    mechanism_kind: str = "sector"
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
            "mechanism_kind": self.mechanism_kind, "walls": self.walls,
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
    swept = 0
    ungated = 0
    for sector_id in range(len(disk.sectors)):
        record = observe_motion_sector(disk, sector_id, owners=owners)
        if record is None:
            continue
        effects = physical_effects(record)
        motion = swept_motion(disk, sector_id, record)
        if motion is not None:
            #: Slide and rotate, no longer parked. A leaf is a solid wall
            #: *inside* the mechanism's sector -- E1M1's s4, s63 and s125
            #: all move walls that are not portals at all -- so what the
            #: motion gates is the sector's own crossings: while the leaf is
            #: in the way there is no getting from one side to the other.
            sweeps = swept_opening(disk, sector_id, motion)
            load = motion["payload"]["carries"]
            causes = _causes_for(record, wires)
            if not causes or load == PAYLOAD_NOTHING:
                inert += 1
                continue
            swept += 1
            neighbours = sorted({int(portal["next_sector"])
                                 for portal in record["portals"]})
            rest = rest_state(record)
            other = "off" if rest == "on" else "on"
            #: Which state actually blocks, measured rather than assumed.
            #: The line between two portals' midpoints is the way across; if
            #: a leaf segment crosses it, that way is shut. Assuming instead
            #: that the rest state is the shut one cut E1M2 from 231
            #: reachable sectors to 26.
            shut_at_rest = None
            if len(neighbours) == 2:
                a = portal_midpoint(disk, sector_id, neighbours[0])
                b = portal_midpoint(disk, sector_id, neighbours[1])
                if a is not None and b is not None:
                    at_rest = leaf_blocks(disk, sector_id, motion, a, b,
                                          moved=(rest != "off"))
                    when_moved = leaf_blocks(disk, sector_id, motion, a, b,
                                             moved=(rest == "off"))
                    if at_rest is not None and at_rest != when_moved:
                        shut_at_rest = at_rest
            if (load == PAYLOAD_SPRITES or not sweeps["admits_a_body"]
                    or shut_at_rest is None):
                #: Three reasons to record the route and gate nothing.
                #:
                #: The payload is sprites, so the gate stands somewhere
                #: inside the sector and locating it needs the polygon sweep
                #: this does not have. Or the leaf never vacates a body's
                #: width. Or -- the one the campaign forced -- no leaf
                #: segment separates the sector's two portals in one state
                #: and not the other, so which state is shut is not
                #: measurable here. That covers a sector with more than two
                #: portal neighbours (a room carrying scenery, like E1M2's
                #: seven-neighbour sector 34) and a sector all of whose
                #: walls are portals (no leaf at all).
                ungated += 1
                continue
            reads_as = design_object({}, sweeps=sweeps)
            for neighbour in sorted(neighbours):
                for pair in ((sector_id, neighbour), (neighbour, sector_id)):
                    edges.append(ConditionalEdge(
                        sectors=pair, mechanism=sector_id,
                        enabling_state=(other if shut_at_rest else rest),
                        verdict="conditional",
                        delta={"kind": "swept", "rest_state": rest,
                               "effect": motion["effect"],
                               "travel": motion.get("travel"),
                               "turn": motion.get("turn"),
                               "payload": load,
                               "shut_at_rest": shut_at_rest,
                               "leaf_length": sweeps["leaf_length"],
                               "opening": sweeps["opening"],
                               "body_width": sweeps["body_width"],
                               "basis": sweeps["basis"],
                               "reads_as": reads_as},
                        causes=causes,
                        requires_key=int(record["key"] or 0),
                        irreversible=all(item.irreversible for item in causes)))
            continue
        if not any(item["effect"].startswith("move_") for item in effects):
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
        "swept_mechanisms": swept,
        "swept_recorded_but_not_gated": ungated,
        "scoped_out_no_reading": scoped_out,
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


def blocking_crossings(disk: Any) -> dict[tuple[int, int], list[int]]:
    """Sector pairs a body cannot cross, because every wall between blocks.

    Two levels, and conflating them is wrong in both directions.

    A **wall pair** -- a wall and its `nextwall` partner -- is shut when
    either side carries the blocking bit, because Blood's own gib-wall setup
    sets it on one side and clears it on the other
    (`triggers.cpp:679-684`). Asking only the near side misses half of them.

    A **sector pair** is shut only when *every* wall pair between the two
    blocks. Two rooms often share a blocked wall and an open doorway, and
    refusing the crossing on the strength of the blocked one made this base
    stricter than the strict base -- E1M1 fell to 28 sectors against the
    strict base's 34, which is how the mistake surfaced.
    """
    owners = _wall_owners(disk)
    total: dict[tuple[int, int], int] = defaultdict(int)
    blocked: dict[tuple[int, int], list[int]] = defaultdict(list)
    seen: set[int] = set()
    for index, wall in enumerate(disk.walls):
        other = int(wall.fields["next_sector"])
        if other < 0 or index >= len(owners) or owners[index] < 0:
            continue
        if index in seen:
            continue
        partner = int(wall.fields["next_wall"])
        seen.add(index)
        if 0 <= partner < len(disk.walls):
            seen.add(partner)
        here = owners[index]
        pair = (here, other)
        stops = bool(int(wall.fields["cstat"]) & WALL_BLOCK)
        if 0 <= partner < len(disk.walls):
            stops = stops or bool(int(disk.walls[partner].fields["cstat"]) & WALL_BLOCK)
        for key in (pair, (other, here)):
            total[key] += 1
            if stops:
                blocked[key].append(index)
    return {pair: walls for pair, walls in blocked.items()
            if len(walls) == total[pair]}


def gib_wall_edges(disk: Any, wires: dict[int, list[Source]]
                   ) -> list[ConditionalEdge]:
    """Breakable walls, as conditional crossings.

    kWallGib is the one mechanism in the engine that reopens a blocked wall.
    Every one of the campaign's 205 is built in state 0 -- shut -- and every
    one of them is wired, by a channel or by being shootable. There are no
    exceptions to reopen by hand.
    """
    owners = _wall_owners(disk)
    edges: list[ConditionalEdge] = []
    seen: set[int] = set()
    for index, wall in enumerate(disk.walls):
        other = int(wall.fields["next_sector"])
        if other < 0 or index >= len(owners) or owners[index] < 0:
            continue
        if int(wall.fields["type"]) != KWALLGIB or index in seen:
            continue
        #: 210 of the campaign's 218 gib walls carry type 511 on *both*
        #: sides of the pair, because the engine sets both up together.
        #: Reading each side as its own mechanism doubles every breakable
        #: wall in the map.
        seen.add(index)
        partner = int(wall.fields["next_wall"])
        if 0 <= partner < len(disk.walls)                 and int(disk.walls[partner].fields["type"]) == KWALLGIB:
            seen.add(partner)
        extra = _extra(wall)
        if not extra:
            continue
        here = owners[index]
        listens = int(extra.get("rx_id") or 0)
        causes: list[Source] = list(wires.get(listens, ())) if listens else []
        if extra.get("trigger_vector"):
            causes.append(Source(
                kind="wall", index=index, type_id=KWALLGIB, channel=0,
                trigger=BY_SHOT, key=int(extra.get("key") or 0),
                irreversible=True, once=bool(extra.get("trigger_once"))))
        if not causes:
            continue
        shut = not int(extra.get("state") or 0)
        delta = {
            "kind": "wall_blocking_cstat",
            "wall": index,
            "cstat": int(wall.fields["cstat"]),
            "blocking_at_rest": shut,
            "state_at_rest": "off" if shut else "on",
            "engine": "NBlood triggers.cpp SetupGibWallState: state 1 clears "
                      "cstat & 65 and the masked bit on both sides; state 0 "
                      "sets them",
            "reads_as": "changes what fits through",
        }
        for pair in ((here, other), (other, here)):
            edges.append(ConditionalEdge(
                sectors=pair, mechanism=index, mechanism_kind="wall",
                enabling_state="on" if shut else "off",
                verdict="conditional", delta=delta, causes=causes,
                requires_key=int(extra.get("key") or 0),
                irreversible=all(item.irreversible for item in causes)))
    return edges


def route_edges(edges: Sequence["ConditionalEdge"]) -> list[dict[str, Any]]:
    """Collapse a mechanism's crossings into the route it gates.

    A door is one sector with a portal on each side, so it gates two
    crossings and four directed edges. What a reader means by "the door" is
    the single connection between the rooms either side of it, and that is
    what this returns: one route per mechanism, naming the rooms it joins
    and carrying the same cause chain.
    """
    by_mechanism: dict[tuple[str, int], list[ConditionalEdge]] = defaultdict(list)
    for edge in edges:
        if edge.verdict == "conditional":
            by_mechanism[(edge.mechanism_kind, edge.mechanism)].append(edge)
    routes = []
    for (kind, mechanism), group in sorted(by_mechanism.items()):
        #: A wall gates the two sectors it separates and is not one of them;
        #: a sector gates its neighbours and is not one of them either.
        joins = sorted({sector for edge in group for sector in edge.sectors
                        if kind == "wall" or sector != mechanism})
        first = group[0]
        routes.append({
            "mechanism": mechanism,
            "mechanism_kind": kind,
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


def _non_portal_pairs(reach: Any) -> set[tuple[int, int]]:
    """Stack links and teleports, which are not portals and never blocked.

    Leaving these out is not a small error. E1M1's player start is a closed
    box of four sectors whose only two portals carry the blocking cstat;
    the way out is a **paired stack link** to sector 28. `analyze_spatial`
    records it under `known_non_portal_transitions` and
    `analyze_progression` never reads that list, which is why it reaches 2
    of 146 design sectors on a map players finish.
    """
    out: set[tuple[int, int]] = set()
    for group in (reach.links, reach.teleports):
        for record in group:
            left, right = record["sectors"]
            out.add((int(left), int(right)))
            out.add((int(right), int(left)))
    return out


def _directed_base(disk: Any, gated: set[tuple[int, int]], *, base: str
                   ) -> tuple[dict[int, set[int]], Any]:
    """The base graph, directed, with the gated crossings removed.

    The base is taken whole rather than rebuilt: this view's job is to put
    gates back on somebody else's answer, not to have a second opinion about
    what a portal is.
    """
    if base not in BASES:
        raise ConditionalError(
            f"unknown base {base!r}; choose one of {sorted(BASES)}")
    reach = analyze_reachability(disk)
    keep_anyway = _non_portal_pairs(reach)
    refused: set[tuple[int, int]] = set()
    if base == BASE_BLOCKING_AWARE:
        refused = set(blocking_crossings(disk))
    elif base == BASE_STRICT:
        allowed = walkable_at_rest(disk)
        refused = {(a, b) for a, group in reach.graph.items() for b in group
                   if (a, b) not in allowed}
    out: dict[int, set[int]] = defaultdict(set)
    for sector, neighbours in reach.graph.items():
        for neighbour in neighbours:
            pair = (sector, neighbour)
            if pair in gated:
                continue
            if pair in refused and pair not in keep_anyway:
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
    #: Fired before the player does anything -- see `level_start_closure`.
    fired_at_start: frozenset[int] = frozenset()

    def at_rest(self) -> Held:
        """What has already happened when the level loads."""
        return Held(channels=self.fired_at_start)

    def reachable(self, held: Held,
                  without: set[tuple[str, int]] | None = None) -> set[int]:
        """Where a body can get, optionally with one mechanism struck out.

        `without` is how every question below is asked: run the map with
        everything worked, then again with this one mechanism removed, and
        the difference is what that mechanism is *for*.
        """
        graph = {sector: set(neighbours) for sector, neighbours in self.base.items()}
        struck = without or set()
        held = Held(frozenset(held.channels | self.fired_at_start),
                    held.keys, held.operated)
        for edge in self.edges:
            if (edge.mechanism_kind, edge.mechanism) in struck:
                continue
            if _edge_enabled(edge, held):
                graph.setdefault(edge.sectors[0], set()).add(edge.sectors[1])
        return _flood(graph, self.start)

    def everything_worked(self) -> Held:
        """Every channel fired, every key held, every hand-worked thing worked.

        Not a claim that a player can do all of it -- it is the upper bound
        the counterfactuals are measured against.
        """
        channels = {cause.channel for edge in self.edges
                    for cause in edge.causes if cause.channel}
        keys = {edge.requires_key for edge in self.edges if edge.requires_key}
        operated = {edge.mechanism for edge in self.edges
                    if edge.mechanism_kind == "sector"
                    and not any(cause.channel for cause in edge.causes)}
        return Held(frozenset(channels), frozenset(keys), frozenset(operated))

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


#: What a mechanism is *for*, as far as where it sits can say.
#:
#: These five are assigned from one counterfactual -- run the map with the
#: mechanism, run it without, read the difference -- plus two facts about
#: the sector itself. They are deliberately fewer than the eight names an
#: author would use, because **the embedding does not determine all eight**.
#: See `reports/blood-swept-mechanisms.md`: E1M1's rat trap and its curtain
#: have identical topological signatures and different dramatic jobs, and
#: its plain sliding door is more load-bearing than the double rotating door
#: the author built as the way on. Naming those apart is a reading of intent,
#: not of space, and inventing a spatial rule that happens to split eleven
#: hand-labelled cases would be fitting noise.
#:
#: What the reading *can* separate is recorded here; what it cannot is
#: recorded beside it as content, for a human or a later phase to read.
ROLE_NARRATIVE = "narrative"
ROLE_ROR_CARRIER = "technical workaround"
ROLE_FIXTURE = "fixture"
ROLE_REQUIRED = "required passage"
ROLE_SIDE = "side passage"
#: The mechanism is described -- primitive, payload, the gap it vacates --
#: but which of its states blocks was not measurable, so it gates nothing
#: and nothing is claimed about what it is for. Saying that is the point.
ROLE_UNPLACED = "recorded, not placed"
ROLE_SECRET = "secret"
ROLE_SECRET_ENTRANCE = "secret entrance"
ROLE_AMBUSH = "ambush"

#: The four planes a name can come from, in the order that decides ties.
#:
#: A mechanism the player starts inside is narrative whatever else is true,
#: so **position** outranks everything. A distinctively dressed one is what
#: its dressing says -- but only where the owner called that tile strongly
#: binding, which is the rule that keeps a name off wallpaper. What waits
#: beyond beats how much is lost, because "rats come out" is a stronger
#: claim than "one sector fewer".
PLANES = ("position", "dressing", "contents", "topology")

#: kChannelSecretFound. A sector that transmits on it *is* a secret: entering
#: it is what scores one, so a secret within reach of what a mechanism opens
#: is the measurable form of "this revealed a secret".
SECRET_CHANNEL = 2
#: How far beyond a mechanism a secret still counts as the thing it revealed.
SECRET_REACH = 1

#: How many portal neighbours a swept mechanism may have and still be read
#: as a leaf between two sides rather than a room carrying scenery.
LEAF_NEIGHBOURS = 2


def secret_sectors(disk: Any) -> set[int]:
    return {index for index, sector in enumerate(disk.sectors)
            if int(_extra(sector).get("tx_id") or 0) == SECRET_CHANNEL}


def dude_sectors(disk: Any) -> set[int]:
    from .blood_types import classify

    out = set()
    for sprite in disk.sprites:
        try:
            category = classify("sprite", int(sprite.fields["type"])).get("category")
        except Exception:
            continue
        if category == "dude":
            out.add(int(sprite.fields["sector"]))
    return out


def ror_sectors(reach: Any) -> set[int]:
    """Sectors that are half of a stack link.

    Room-over-room is not only a way through: it is a **budget**. Two ROR
    volumes must not be in view at once or the renderer shows both, so a
    level gets very few of them and authors reuse the ones they have. E1M1
    reuses its one big ROR volume (sector 65) as the carrier for a sliding
    gate rather than building a second sector for the gate -- an engine
    visibility constraint reshaping the authoring, visible in the map as one
    sector doing two unrelated jobs.
    """
    out = set()
    for record in reach.links:
        left, right = record["sectors"]
        out.add(int(left))
        out.add(int(right))
    return out


def _position_plane(graph: "ConditionalGraph", mechanism: int, kind: str
                    ) -> tuple[str, dict[str, Any]] | None:
    """Where it sits: at the spawn, or inside a room-over-room pair."""
    if kind == "sector" and mechanism == graph.start:
        return ROLE_NARRATIVE, {"reason": "the player starts inside it"}
    if kind == "sector" and mechanism in ror_sectors(graph.reach):
        return ROLE_ROR_CARRIER, {
            "reason": "half of a stack link and a mechanism at once; the "
                      "visibility budget on ROR volumes is why one sector "
                      "does two jobs"}
    return None


def _dressing_plane(graph: "ConditionalGraph", mechanism: int, kind: str
                    ) -> tuple[str, dict[str, Any]] | None:
    """What the moving faces are wearing, where the owner vouched for it.

    Only a **strong**-binding owner tile may name. That is the owner's rule
    and it bites: on E1M1's thirteen attested cases this plane returns
    nothing at all, because none of their moved faces wears a tile the owner
    graded strong. The curtain of sector 125 wears tile 146, which the
    anchors do not grade -- so the plane that would have called it a
    furnishing is silent, and says so rather than guessing from a tile it
    was told not to trust.
    """
    if kind != "sector":
        return None
    from .doors import observe_motion_sector
    from .owner_anchors import OwnerAnchorError, load_owner_anchors

    record = observe_motion_sector(graph.disk, mechanism)
    motion = swept_motion(graph.disk, mechanism, record) if record else None
    if motion is None:
        return None
    load = motion["payload"]
    try:
        anchors = load_owner_anchors()
    except OwnerAnchorError:
        return None
    picnums = []
    walls = load["walls_with"] + load["walls_against"]
    if load["moves_every_wall"]:
        start = int(graph.disk.sectors[mechanism].fields["wall_ptr"])
        count = int(graph.disk.sectors[mechanism].fields["wall_count"])
        walls = list(range(start, start + count))
    for wall_id in walls:
        if 0 <= wall_id < len(graph.disk.walls):
            picnums.append(int(graph.disk.walls[wall_id].fields["picnum"]))
    for index in load["sprites_with"] + load["sprites_against"]:
        if 0 <= index < len(graph.disk.sprites):
            picnums.append(int(graph.disk.sprites[index].fields["picnum"]))
    evidence = anchors.naming_evidence(picnums, used_for="dressing")
    if not evidence:
        return None
    #: The name is the owner's own label. Nothing is invented from a tile.
    return f"dressed: {evidence[0]['label']}", {
        "reason": "a strong-binding owner tile on the moving faces",
        "owner_evidence": evidence}


def _contents_plane(graph: "ConditionalGraph", joins: list[int],
                    secrets: set[int], dudes: set[int]
                    ) -> tuple[str, dict[str, Any]] | None:
    """What waits on the far side."""
    from collections import deque

    nearby: set[int] = set()
    for origin in joins:
        seen, pending = {origin}, deque([(origin, 0)])
        while pending:
            current, depth = pending.popleft()
            if current in secrets:
                nearby.add(current)
            if depth >= SECRET_REACH:
                continue
            for neighbour in graph.reach.graph.get(current, ()):
                if neighbour not in seen:
                    seen.add(neighbour)
                    pending.append((neighbour, depth + 1))
    waiting = [item for item in joins if item in dudes]
    if nearby:
        role = (ROLE_SECRET_ENTRANCE if set(nearby) & set(joins)
                else ROLE_SECRET)
        return role, {"reason": "a secret sector within reach of what it opens",
                      "secrets": sorted(nearby)}
    if waiting:
        return ROLE_AMBUSH, {"reason": "dudes in the sector immediately beyond",
                             "sectors": waiting}
    return None


def design_role(graph: "ConditionalGraph", mechanism: int, *,
                kind: str = "sector") -> dict[str, Any]:
    """What this mechanism is for, read across four planes.

    Version 2. The first read topology alone and could name five things; the
    evidence said naming is cross-view, so each plane now proposes
    independently and the report says **which one decided**.

    * **position** -- the player starts inside it, or it is half of a stack
      link. Outranks everything, because neither fact is about reachability.
    * **dressing** -- a strong-binding owner tile on the moving faces. The
      name is the owner's own label. Weak and untested tiles never reach
      here.
    * **contents** -- a secret within reach of what it opens, or dudes in the
      sector immediately beyond.
    * **topology** -- one counterfactual: work everything, then everything
      but this, and read the difference.

    `contested` lists the planes that proposed something else. Two planes
    disagreeing is not an error; it is two readings of one object, and
    hiding it would be the error.
    """
    disk = graph.disk
    held = graph.everything_worked()
    full = graph.reachable(held)
    without = graph.reachable(held, without={(kind, mechanism)})
    lost = sorted(full - without)
    edges = [edge for edge in graph.edges
             if edge.mechanism == mechanism and edge.mechanism_kind == kind]
    joins = sorted({sector for edge in edges for sector in edge.sectors
                    if kind == "wall" or sector != mechanism})
    if not joins and kind == "sector":
        #: A mechanism this view declines to gate still *joins* the sectors
        #: it has portals to, and the contents plane has every right to look
        #: at them. Reading joins off the edges alone left the plane blind
        #: on exactly the mechanisms topology could not place.
        joins = sorted(graph.reach.graph.get(mechanism, set()))
    opening = next((edge.delta.get("opening") for edge in edges
                    if edge.delta.get("opening") is not None), None)
    admits = any(edge.delta.get("reads_as") == OPENS_A_WAY for edge in edges)
    if opening is None and kind == "sector":
        from .doors import observe_motion_sector

        record = observe_motion_sector(disk, mechanism)
        motion = swept_motion(disk, mechanism, record) if record else None
        if motion is not None:
            measured = swept_opening(disk, mechanism, motion)
            opening = measured["opening"]
            admits = admits or measured["admits_a_body"]

    secrets, dudes = secret_sectors(disk), dude_sectors(disk)
    proposals: dict[str, tuple[str, dict[str, Any]]] = {}
    found = _position_plane(graph, mechanism, kind)
    if found:
        proposals["position"] = found
    found = _dressing_plane(graph, mechanism, kind)
    if found:
        proposals["dressing"] = found
    found = _contents_plane(graph, joins, secrets, dudes)
    if found:
        proposals["contents"] = found
    if not admits and (opening or 0) < 384:
        proposals["topology"] = (ROLE_FIXTURE, {
            "reason": "never opens a body's width"})
    elif not edges:
        proposals["topology"] = (ROLE_UNPLACED, {
            "reason": "which of its states blocks was not measurable, so it "
                      "gates nothing and nothing is claimed"})
    elif len(lost) > 1:
        proposals["topology"] = (ROLE_REQUIRED, {
            "reason": f"{len(lost)} sectors are lost without it"})
    else:
        proposals["topology"] = (ROLE_SIDE, {
            "reason": "removing it costs only its own sector"})

    decided_by = next((plane for plane in PLANES if plane in proposals), None)
    role, why = proposals[decided_by] if decided_by else (ROLE_UNPLACED, {})
    contested = sorted(plane for plane, (name, _) in proposals.items()
                       if plane != decided_by and name != role)
    return {
        "mechanism": mechanism, "mechanism_kind": kind, "role": role,
        "decided_by": decided_by, "why": why,
        "proposals": {plane: {"role": name, **detail}
                      for plane, (name, detail) in proposals.items()},
        "contested": contested,
        "joins": joins,
        "sectors_lost_without_it": len(lost),
        "lost_without_it": lost[:24],
        "swept_opening": opening,
        "basis": "four planes -- position, dressing, contents, topology -- "
                 "each proposing on its own evidence; ties go in that order",
    }


def design_roles(graph: "ConditionalGraph") -> list[dict[str, Any]]:
    """Every gating mechanism in the map, named from its embedding."""
    seen = {(edge.mechanism_kind, edge.mechanism) for edge in graph.edges
            if edge.verdict == "conditional"}
    return [design_role(graph, mechanism, kind=kind)
            for kind, mechanism in sorted(seen, key=lambda item: (item[0], item[1]))]


def build_graph(disk: Any, *, owners: Sequence[int] | None = None,
                base: str = BASE_BLOCKING_AWARE) -> ConditionalGraph:
    """Read one map into a conditional-traversability graph.

    Three bases, one default, each saying what it assumes -- see `BASES`.
    They disagree by a lot, and the disagreement is a finding rather than a
    setting, so all three stay callable.
    """
    edges, summary = conditional_edges(disk, owners=owners)
    if base == BASE_BLOCKING_AWARE:
        #: A blocked wall a mechanism reopens is a conditional crossing, not
        #: a wall. Added before the base is built so the base refuses it as
        #: a portal and the edge puts it back with its cause chain.
        edges = edges + gib_wall_edges(disk, transmitters(disk))
    gated = {edge.sectors for edge in edges}
    graph, reach = _directed_base(disk, gated, base=base)
    blocked = blocking_crossings(disk)
    reopened = {edge.sectors for edge in edges if edge.mechanism_kind == "wall"}
    summary = {
        **summary, "base": base, "base_assumes": BASES[base],
        "blocking_crossings": len(blocked),
        "blocking_reopened_by_a_gib_wall": len(reopened),
        "blocking_shut_for_ever": len(set(blocked) - reopened),
        "conditional": sum(1 for e in edges if e.verdict == "conditional"),
    }
    start = int(reach.start["sector"])
    fired = level_start_closure(disk)
    summary["channels_fired_at_level_start"] = len(fired)
    return ConditionalGraph(disk=disk, edges=edges, summary=summary,
                            start=start, base=graph, gated=gated, reach=reach,
                            fired_at_start=fired)


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
