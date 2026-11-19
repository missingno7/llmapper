"""Wiring: what a player's act sets off, followed from sender to listener across sectors, walls and sprites.

There is no such thing in Blood as a door or a lift. There are sectors, walls
and sprites, and laid over them a second layer: this one sends on a channel
when something is done to it, those listen on that channel and do what their
own fields say. A "door" is a sector that changes what fits through it, plus
whatever was wired to set it off, and the same sector type on the end of a
different wire is a crusher, a secret or a trap. So a mechanism is not a
record. It is a CHAIN: a cause, the object it happens to, the channel that
object sends on, everything that listens, and on through any listener that
sends in turn.

`chains` reads that layer off a map. A chain starts where the engine itself
starts one:

* a trigger flag on the object (pushed, shot, entered, picked up, ...);
* a dude that is killed or a thing that is destroyed, which fire their own
  trigger with no flag at all (`actKillDude`, actor.cpp:3029; the thing
  branch of `actDamageSprite`, actor.cpp:3513);
* one of the engine's channels the object listens on (the level starting).

and it ends at its listeners, or at one of the engine's own channels (a
secret found, the level's exit), which is a listener no record holds.

Having a channel is not sending. An object sends when its own state changes
in a direction it was told to report: `SetSpriteState`, `SetWallState` and
`SetSectorState` (triggers.cpp:100, :121, :136) each call `evSend` only
under `triggerOn` or `triggerOff`. 2,757 of the campaign's 2,775 chains start
at a sender that reports one or both. One that reports neither is SILENT: it
flips and nothing hears, and a relay like that is where a cascade stops. A
Link command (5) is the exception; it drives its listeners by another path.

`shape` reduces a chain to what a mapper asks for -- "a pushed switch that
moves a floor" -- so the same wiring can be counted and found across a
campaign. `bloodmap.examples` indexes the shapes; `tools/catalog.py
mechanisms MAP` prints one map's chains. The per-channel bus views
(`analysis.channel_graph`, `curriculum.wiring_graph`) answer a different
question, who is on a channel; this answers what happens.

The second half of the module is the same layer from the author's side. A
`Circuit` holds a layout's wires: each `Wire` says in a sentence what it is
for, names what sends and on what cause, and names what answers. The circuit
numbers the channels, refuses what the engine cannot do, writes the fields,
and after the build reads the finished map back with `chains` and says where
it and the declaration differ -- including every channel on the map that no
wire owns.
"""

from __future__ import annotations

from collections import Counter
from typing import Any, Iterable, Mapping

from .blood_types import RESERVED_CHANNELS, SECTOR_TYPES, SPRITE_TYPES, WALL_TYPES
from .model import record_extra, record_fields
from .sector_geom import wall_owners

#: A trigger flag, and what a player (or anything else) does to raise it.
CAUSES: tuple[str, ...] = ("push", "vector", "impact", "pickup", "touch", "sight",
                           "proximity", "enter", "exit", "wall_push")

#: Channels from here up are a level's own; below are the engine's, and zero
#: is no channel at all (`if (pXSprite->txID)`, triggers.cpp).
USER_CHANNELS_FROM = 100

#: How far a chain is followed through listeners that send in turn.
MAX_DEPTH = 8

#: `kCmdLink`: the listener follows the sender's travel; no `evSend` is made.
CMD_LINK = 5

#: `bloodmap.effects`' reading of a moving sector, as the clause a shape says.
#: Its other readings ("neither", "not decidable from z alone") say nothing a
#: mapper can use, so a sector read that way keeps its type's name alone.
DOES = {
    "changes what fits through": "changes what fits through",
    "carries a body between levels": "carries a body between levels",
    "both": "changes what fits through and carries a body between levels",
}


def _engine_channel(channel: int) -> str | None:
    """The engine's name for a channel it owns, or None for a level's own or none."""
    if 0 < channel < USER_CHANNELS_FROM and channel in RESERVED_CHANNELS:
        return str(RESERVED_CHANNELS[channel]["name"])
    return None


def nodes(disk: Any) -> list[dict[str, Any]]:
    """Every sector, wall and sprite that sends or listens, with why it would fire."""
    owners = wall_owners(disk)
    out = []
    for kind, group, table in (("sprite", disk.sprites, SPRITE_TYPES),
                               ("sector", disk.sectors, SECTOR_TYPES),
                               ("wall", disk.walls, WALL_TYPES)):
        for index, item in enumerate(group):
            extra = record_extra(item) or {}
            tx, rx = int(extra.get("tx_id", 0) or 0), int(extra.get("rx_id", 0) or 0)
            if not tx and not rx:
                continue
            fields = record_fields(item)
            type_id = int(fields.get("type", 0))
            named = table.get(type_id) or {}
            causes = [cause for cause in CAUSES
                      if int(extra.get(f"trigger_{cause}", 0) or 0)]
            if not causes and tx and kind == "sprite":
                # No flag, and it still fires: the engine triggers a dude on
                # its death and a thing on its destruction.
                if named.get("category") == "dude":
                    causes = ["killed"]
                elif named.get("category") == "thing":
                    causes = ["destroyed"]
            sector = (int(fields["sector"]) if kind == "sprite"
                      else index if kind == "sector" else owners.get(index, -1))
            command = int(extra.get("command", 0) or 0)
            out.append({
                "id": f"{kind} {index}", "kind": kind, "index": index,
                "type": type_id, "type_name": named.get("name", str(type_id)),
                "tile": int(fields.get("picnum", fields.get("floor_picnum", 0))),
                "tx": tx, "rx": rx, "command": command,
                #: which change of its own state it reports, and so sends on
                "reports": [edge for edge in ("on", "off")
                            if int(extra.get(f"trigger_{edge}", 0) or 0)],
                "link": command == CMD_LINK,
                "causes": causes, "sector": sector,
                "once": bool(int(extra.get("trigger_once", 0) or 0)),
                "wait": int(extra.get("wait_time", extra.get("wait_time_a", 0)) or 0),
                "key": int(extra.get("key", 0) or 0)})
    return out


def can_send(node: Mapping[str, Any]) -> bool:
    """Whether a change of this object's state reaches anything at all."""
    return bool(node["tx"]) and (bool(node["reports"]) or bool(node["link"]))


def silent_senders(disk: Any) -> list[dict[str, Any]]:
    """Every object with a channel to send on that can never send on it."""
    return [node for node in nodes(disk) if node["tx"] and not can_send(node)]


def chains(disk: Any, only: Iterable[int] | None = None, *,
           reach: Mapping[int, str] | None = None) -> list[dict[str, Any]]:
    """Every chain of one map, deepest first: a cause, a sender, and all that answers.

    `reach` is sector to what kind of place it is
    (`bloodmap.reachability.sector_kinds`). With it a chain lists its
    `closet_relays`: listeners that send on and sit where no player goes.
    Blood's mappers keep a cascade's switches in a sealed room and wire them
    by channel, and 607 of the campaign's 2,775 chains pass through one.

    `only` keeps the chains whose first object is in one of those sectors. A
    step whose `to` is ``engine`` ends on a channel the engine owns; its
    `to_type` is that channel's name. A chain is `silent` when its sender
    reports no change of state: it is wired and it never fires. A listener
    that would relay and cannot is in `dead_relays`, and the chain stops there.
    """
    every = nodes(disk)
    keep = None if only is None else set(only)
    listeners: dict[int, list[dict[str, Any]]] = {}
    for node in every:
        if node["rx"]:
            listeners.setdefault(node["rx"], []).append(node)
    found = []
    for node in every:
        if not node["tx"]:
            continue
        started_by = _engine_channel(node["rx"])
        if node["causes"]:
            cause = list(node["causes"])
        elif started_by:
            cause = [f"channel {node['rx']} {started_by}"]
        elif not node["rx"]:
            # It sends, nothing is flagged and it listens to nothing: what
            # fires it is its own type's business (a generator's timer).
            cause = ["itself"]
        else:
            continue                      # a relay: it is some other chain's step
        if keep is not None and node["sector"] not in keep:
            continue
        steps, seen, depth = [], {node["id"]}, 0
        dead: list[str] = []
        closet: list[str] = []
        frontier = [node]
        while frontier and depth < MAX_DEPTH:
            following = []
            for sender in frontier:
                engine = _engine_channel(sender["tx"])
                if engine:
                    steps.append({"from": sender["id"], "channel": sender["tx"],
                                  "command": sender["command"], "to": "engine",
                                  "to_kind": "engine", "to_type_id": sender["tx"],
                                  "to_type": engine, "wait": 0})
                for receiver in listeners.get(sender["tx"], ()):
                    steps.append({"from": sender["id"], "channel": sender["tx"],
                                  "command": sender["command"],
                                  "to": receiver["id"], "to_kind": receiver["kind"],
                                  "to_type_id": receiver["type"],
                                  "to_type": receiver["type_name"],
                                  "wait": receiver["wait"]})
                    if receiver["id"] not in seen and receiver["tx"]:
                        seen.add(receiver["id"])
                        if can_send(receiver):
                            following.append(receiver)
                            if reach is not None and reach.get(
                                    receiver["sector"]) != "reachable":
                                closet.append(receiver["id"])
                        else:
                            dead.append(receiver["id"])
            frontier, depth = following, depth + 1
        found.append({
            "root": node["id"], "root_kind": node["kind"], "root_type_id": node["type"],
            "root_type": node["type_name"], "tile": node["tile"],
            "sector": node["sector"], "cause": cause,
            "key": node["key"], "once": node["once"],
            "silent": not can_send(node), "dead_relays": dead,
            "closet_relays": closet,
            "steps": steps, "depth": depth,
            "receivers": dict(Counter(step["to_type"] for step in steps))})
    found.sort(key=lambda chain: (-chain["depth"], -len(chain["steps"])))
    return found


def _part(kind: str, type_id: int, type_name: str) -> str:
    """A part in a mapper's words: its type's name, or what it plainly is."""
    if kind == "engine":
        return f"the engine ({type_name})"
    if not type_id:
        return f"a plain {kind}"
    return type_name


def shape(chain: Mapping[str, Any],
          readings: Mapping[int, Mapping[str, Any]] | None = None) -> dict[str, Any]:
    """What a chain is, with its numbers taken out: cause, sender, what answers.

    Two chains of one shape are the same wiring in two places. `readings` is
    sector to `bloodmap.effects`' reading of it; with it a moving sector on
    the end of the wire is named by what it does to the space around it
    ("changes what fits through"), which is the only honest sense in which a
    sector is a door.
    """
    answers = set()
    for step in chain["steps"]:
        said = _part(step["to_kind"], step["to_type_id"], step["to_type"])
        if step["to_kind"] == "sector" and readings is not None:
            reading = readings.get(int(step["to"].split()[1]))
            if reading and reading["is"] in DOES:
                said += f" that {DOES[reading['is']]}"
        answers.add(said)
    return {"cause": "/".join(chain["cause"]),
            "sender": _part(chain["root_kind"], chain["root_type_id"], chain["root_type"]),
            "answers": sorted(answers)}


# ---------------------------------------------------------------------------
# The authoring half: a wire is declared, compiled, and read back
# ---------------------------------------------------------------------------
#
# The reading half above takes a finished map and says what its wiring is.
# This half lets a level SAY what its wiring is before it is built, in the
# same terms, so the two can be compared.
#
# The owner's description of the layer is the specification: "these mechanics
# things are like a programming language of the level, same things are used
# for different purposes according to what the author wants." A one-way
# switch that reacts to a bullet is a destroyable clock, because a switch
# shows a second picture; a z-moving sector is a door or a lift by where it
# sits and what is wired to it; a switch no player can reach relays a cascade.
# So nothing here is called a door. A `Wire` is one statement of that
# language: when THIS is done to these objects, THOSE answer, and it says in
# a sentence what the author wants of it.

#: Engine channels the engine listens on: a level object may only send there.
ENGINE_HEARS = (1, 2, 3, 4, 5)
#: Engine channels the engine sends on: a level object may only listen there.
ENGINE_SENDS = (7, 8, 9, 10)
#: A cause that is the engine speaking, and the channel it speaks on.
LEVEL_START = "level start"
LEVEL_START_CHANNEL = 7
#: Causes the engine raises with no flag on the object (see `nodes`).
UNFLAGGED_CAUSES = ("killed", "destroyed")
#: Not a cause a player raises: the sender answers another wire and passes
#: it on, as a curtain that draws passes its travel to the stage's light.
RELAY = "relay"
#: `kCmdToggle`, the verb the campaign wires most; `bloodmap.motion.wiring`
#: explains when a directed verb is a no-op.
CMD_TOGGLE = 3
#: The last channel a level may use (`kChannelUserMax`).
USER_CHANNELS_TO = 1023


class WireError(ValueError):
    """A wire that cannot be built as it was declared."""


def region(region_id: str) -> tuple:
    """A sector, named by the region that becomes it."""
    return ("region", str(region_id))


def placement(placement_id: str) -> tuple:
    """A sprite, named by its placement."""
    return ("placement", str(placement_id))


def face(region_id: str, a1: tuple[int, int], a2: tuple[int, int]) -> tuple:
    """A wall surface, named by its region and the segment it lies on."""
    return ("face", str(region_id), (int(a1[0]), int(a1[1])), (int(a2[0]), int(a2[1])))


def _said(ref: tuple) -> str:
    if ref[0] == "face":
        return f"the face of {ref[1]} from {ref[2]} to {ref[3]}"
    return f"{ref[0]} {ref[1]}"


class Wire:
    """One channel's worth of intent: these objects send, those answer.

    `when` and `then` return the wire, so a statement reads in one line.
    Nothing is written to the layout until `Circuit.apply`.
    """

    def __init__(self, name: str, says: str, *, channel: int | None = None,
                 engine: str | None = None) -> None:
        self.name, self.says = str(name), str(says)
        self.channel, self.engine = channel, engine
        self.senders: list[dict[str, Any]] = []
        self.answers: list[dict[str, Any]] = []

    def when(self, ref: tuple, cause: str, *, command: int = CMD_TOGGLE,
             on: bool = True, off: bool = False, once: bool = False,
             key: int | None = None, **fields: int) -> "Wire":
        """This object sends on the wire when `cause` is done to it.

        `cause` is a trigger flag's name (`push`, `vector`, `enter`, ...),
        `killed` or `destroyed` for a dude or a thing, or `level start`.
        `on`/`off` are which change of the sender's own state is reported:
        with neither, nothing is ever sent (triggers.cpp:100).
        """
        if cause not in CAUSES + UNFLAGGED_CAUSES + (LEVEL_START, RELAY):
            raise WireError(
                f"wire {self.name!r}: {cause!r} is not something that can be done "
                f"to an object; one of {', '.join(CAUSES + UNFLAGGED_CAUSES)}, "
                f"{LEVEL_START!r} or {RELAY!r}")
        if cause in UNFLAGGED_CAUSES and ref[0] != "placement":
            raise WireError(f"wire {self.name!r}: only a sprite can be {cause}")
        if not (on or off) and int(command) != CMD_LINK:
            raise WireError(
                f"wire {self.name!r}: a sender that reports neither its ON nor "
                f"its OFF change sends nothing (triggers.cpp:100, :121, :136)")
        written = {"command": int(command)}
        if on:
            written["trigger_on"] = 1
        if off:
            written["trigger_off"] = 1
        if cause in CAUSES:
            written[f"trigger_{cause}"] = 1
        if cause == LEVEL_START:
            written["rx_id"] = LEVEL_START_CHANNEL
        if once:
            written["trigger_once"] = 1
        if key is not None:
            written["key"] = int(key)
        written.update({name: int(value) for name, value in fields.items()})
        self.senders.append({"ref": ref, "cause": cause, "fields": written})
        return self

    def then(self, ref: tuple, **fields: int) -> "Wire":
        """This object answers the wire; what it does is its own fields' business."""
        self.answers.append({"ref": ref,
                             "fields": {name: int(value) for name, value in fields.items()}})
        return self


class Circuit:
    """Every wire of one layout: declared here, numbered here, read back here.

    Channels were constants chosen by hand in each module that needed one,
    which is how the city came to lay a wire on channel 30, the engine's
    `kChannelPlayer0`. A circuit numbers its own wires from 100 upwards,
    around any channel the layout already uses, and refuses the three things
    the engine cannot do: an object sending on two channels, an object
    listening on two, and a level wire on a channel the engine owns.
    """

    def __init__(self, layout: Any = None, *,
                 first_channel: int = USER_CHANNELS_FROM) -> None:
        #: None until `bind`: a wire's ends are names, so they can be
        #: declared while the level is still a program and has no layout
        self.layout = layout
        self.first_channel = int(first_channel)
        self.wires: list[Wire] = []
        self.applied = False

    def bind(self, layout: Any) -> "Circuit":
        """Give the circuit the layout its names are names in."""
        self.layout = layout
        return self

    # ---- declaring -----------------------------------------------------------

    def wire(self, name: str, says: str, *, channel: int | None = None,
             engine: str | None = None) -> Wire:
        """Declare a wire. `says` is what the author wants of it, in a sentence.

        `engine` names an engine channel (`kChannelSecretFound`,
        `kChannelLevelExitNormal`) when one end of the wire is the engine;
        `channel` pins a level's own number, for a wire whose number is
        already written somewhere a build must not change.
        """
        if any(wire.name == name for wire in self.wires):
            raise WireError(f"there is already a wire called {name!r}")
        if not str(says).strip():
            raise WireError(f"wire {name!r} does not say what it is for")
        if engine is not None and channel is not None:
            raise WireError(f"wire {name!r}: the engine's channel has its own number")
        made = Wire(name, says, channel=channel, engine=engine)
        self.wires.append(made)
        return made

    # ---- the layout's three stores ------------------------------------------

    def _store(self, ref: tuple) -> dict[str, int]:
        """The fields a reference's object will be built with, as they stand."""
        if ref[0] == "region":
            if ref[1] not in self.layout.regions:
                raise WireError(f"there is no region {ref[1]!r}")
            return self.layout.regions[ref[1]].sector_behavior
        if ref[0] == "placement":
            for spec in self.layout.placements:
                if spec.placement_id == ref[1]:
                    return spec.behavior
            raise WireError(f"there is no placement {ref[1]!r}")
        if ref[0] == "face":
            return self._faces.setdefault(ref, {})
        raise WireError(f"{ref!r} is not a region, a placement or a face")

    def _hand_numbered(self) -> set[int]:
        used: set[int] = set()
        stores = [spec.sector_behavior for spec in self.layout.regions.values()]
        stores += [spec.behavior for spec in self.layout.placements]
        stores += list(getattr(self.layout, "wired_walls", {}).values())
        for store in stores:
            for key in ("tx_id", "rx_id"):
                if int(store.get(key, 0) or 0):
                    used.add(int(store[key]))
        return used

    def _engine_channel(self, wire: Wire) -> int:
        named = {str(row["name"]): int(number)
                 for number, row in RESERVED_CHANNELS.items()}
        if wire.engine not in named:
            raise WireError(f"wire {wire.name!r}: the engine has no channel "
                            f"called {wire.engine!r}")
        channel = named[wire.engine]
        if channel in ENGINE_HEARS:
            if wire.answers:
                raise WireError(
                    f"wire {wire.name!r}: the engine listens on {wire.engine}; "
                    f"nothing in the level may answer it")
        elif channel in ENGINE_SENDS:
            if wire.senders:
                raise WireError(
                    f"wire {wire.name!r}: the engine sends on {wire.engine}; "
                    f"nothing in the level may send on it")
        else:
            raise WireError(
                f"wire {wire.name!r}: which end of {wire.engine} is the engine's "
                f"is not written down here; add it to ENGINE_HEARS or "
                f"ENGINE_SENDS with its source line")
        return channel

    # ---- compiling -----------------------------------------------------------

    def apply(self) -> list[dict[str, Any]]:
        """Number every wire and write it into the layout. Once, before compile."""
        if self.applied:
            raise WireError("this circuit has already been applied")
        if self.layout is None:
            raise WireError("the circuit has no layout: `bind` one before `apply`")
        self._faces: dict[tuple, dict[str, int]] = {}
        taken = self._hand_numbered()
        owner: dict[int, str] = {}
        for wire in self.wires:
            if wire.engine is not None:
                wire.channel = self._engine_channel(wire)
                continue
            if wire.channel is None:
                continue
            if not USER_CHANNELS_FROM <= wire.channel <= USER_CHANNELS_TO:
                raise WireError(
                    f"wire {wire.name!r}: channel {wire.channel} is not a level's "
                    f"own ({USER_CHANNELS_FROM}..{USER_CHANNELS_TO}); below "
                    f"{USER_CHANNELS_FROM} is the engine's")
            if wire.channel in owner:
                raise WireError(f"wires {owner[wire.channel]!r} and {wire.name!r} "
                                f"are both pinned to channel {wire.channel}")
            owner[wire.channel] = wire.name
        free = (number for number in range(self.first_channel, USER_CHANNELS_TO + 1)
                if number not in taken and number not in owner)
        for wire in self.wires:
            if wire.channel is None:
                wire.channel = next(free, None)
                if wire.channel is None:
                    raise WireError("no free channel is left for a level wire")
                owner[wire.channel] = wire.name
        slots: dict[tuple, str] = {}
        for wire in self.wires:
            if wire.engine is None and not wire.senders:
                raise WireError(f"wire {wire.name!r} has nothing that sends")
            if wire.engine is None and not wire.answers:
                raise WireError(f"wire {wire.name!r} has nothing that answers")
            for end, slot, rows in (("sends", "tx_id", wire.senders),
                                    ("listens", "rx_id", wire.answers)):
                for row in rows:
                    held = slots.get((row["ref"], slot))
                    if held is not None and held != wire.name:
                        raise WireError(
                            f"{_said(row['ref'])} already {end} on wire {held!r} and "
                            f"cannot also on {wire.name!r}: an object has one "
                            f"{slot}. Put both on one wire, or relay through "
                            f"an object that listens on one and sends on the other")
                    slots[(row["ref"], slot)] = wire.name
                    self._write(wire, row, {slot: wire.channel, **row["fields"]})
        for ref, fields in self._faces.items():
            self.layout.wire_wall(ref[1], ref[2], ref[3], **fields)
        self.applied = True
        return self.listing()

    def _write(self, wire: Wire, row: dict[str, Any], fields: dict[str, int]) -> None:
        store = self._store(row["ref"])
        for name, value in fields.items():
            already = int(store.get(name, 0) or 0)
            if already and already != int(value):
                raise WireError(
                    f"wire {wire.name!r} wants {name}={value} on {_said(row['ref'])}, "
                    f"which already has {name}={already}"
                    + (": an object has one of these" if name in ("tx_id", "rx_id") else ""))
            store[name] = int(value)

    def listing(self) -> list[dict[str, Any]]:
        """The level's wiring as it was declared: its program, one line a wire."""
        return [{"name": wire.name, "says": wire.says, "channel": wire.channel,
                 "engine": wire.engine,
                 "when": [f"{row['cause']} on {_said(row['ref'])}" for row in wire.senders],
                 "then": [_said(row["ref"]) for row in wire.answers]}
                for wire in self.wires]

    # ---- reading back --------------------------------------------------------

    def read_back(self, compiled: Any, disk: Any) -> dict[str, Any]:
        """Compare the finished map's wiring with what was declared.

        Read with `nodes` and `chains`, the same reader that reads the
        campaign, so a wire that agrees here is one the index would describe
        the way its author did. `undeclared` is every level channel on the
        map that no wire owns: the wiring nobody said the purpose of.
        """
        every = nodes(disk)
        by_id = {node["id"]: node for node in every}
        roots = {chain["root"]: chain for chain in chains(disk)}

        def resolve(ref: tuple, channel: int, slot: str) -> list[str]:
            if ref[0] == "region":
                allocation = compiled.allocations.get(ref[1])
                return [] if allocation is None else [f"sector {allocation.sector_id}"]
            if ref[0] == "placement":
                index = compiled.placement_sprites.get(ref[1])
                return [] if index is None else [f"sprite {index}"]
            allocation = compiled.allocations.get(ref[1])
            return [] if allocation is None else sorted(
                node["id"] for node in every
                if node["kind"] == "wall" and node["sector"] == allocation.sector_id
                and node[slot] == channel)

        owned, report = set(), []
        for wire in self.wires:
            owned.add(wire.channel)
            faults: list[str] = []
            sending = {node["id"] for node in every if node["tx"] == wire.channel}
            hearing = {node["id"] for node in every if node["rx"] == wire.channel}
            senders, answers = [], []
            for row in wire.senders:
                found = resolve(row["ref"], wire.channel, "tx")
                senders += found
                if not found or not set(found) <= sending:
                    faults.append(f"{_said(row['ref'])} does not send on channel "
                                  f"{wire.channel} in the map")
                    continue
                for ident in found:
                    if row["cause"] == LEVEL_START:
                        fires = by_id[ident]["rx"] == LEVEL_START_CHANNEL
                    elif row["cause"] == RELAY:
                        fires = bool(by_id[ident]["rx"])
                    else:
                        fires = row["cause"] in by_id[ident]["causes"]
                    if not fires:
                        faults.append(f"{ident} is not set off by {row['cause']}")
                    if row["cause"] == RELAY:
                        continue          # some other wire's chain passes here
                    chain = roots.get(ident)
                    if chain is None:
                        faults.append(f"{ident} starts no chain")
                    elif wire.engine and not any(
                            step["to"] == "engine" and step["channel"] == wire.channel
                            for step in chain["steps"]):
                        faults.append(f"{ident} does not reach {wire.engine}")
            for row in wire.answers:
                found = resolve(row["ref"], wire.channel, "rx")
                answers += found
                if not found or not set(found) <= hearing:
                    faults.append(f"{_said(row['ref'])} does not listen on channel "
                                  f"{wire.channel} in the map")
            for ident in sorted(sending - set(senders)):
                faults.append(f"{ident} sends on the wire and was not declared")
            for ident in sorted(hearing - set(answers)):
                faults.append(f"{ident} answers the wire and was not declared")
            for ident in senders:
                if ident not in roots:
                    continue              # a relay, or already reported above
                reached = {step["to"] for step in roots[ident]["steps"]
                           if step["channel"] == wire.channel}
                for missed in sorted(set(answers) - reached):
                    faults.append(f"the chain from {ident} does not reach {missed}")
            report.append({"name": wire.name, "says": wire.says, "channel": wire.channel,
                           "engine": wire.engine, "senders": sorted(set(senders)),
                           "answers": sorted(set(answers)), "faults": faults})
        undeclared = []
        for channel in sorted({node["tx"] for node in every} | {node["rx"] for node in every}):
            if not channel or channel in owned:
                continue
            sending = [node["id"] for node in every if node["tx"] == channel]
            hearing = [node["id"] for node in every if node["rx"] == channel]
            if channel < USER_CHANNELS_FROM and not (sending and hearing):
                continue                  # one end is the engine: not a level wire
            undeclared.append({"channel": channel, "senders": sending, "listeners": hearing})
        return {"wires": report, "undeclared": undeclared,
                #: wired and unable to send, declared or not
                "silent": [{"id": node["id"], "channel": node["tx"],
                            "type": node["type_name"], "sector": node["sector"]}
                           for node in every if node["tx"] and not can_send(node)],
                "agrees": not any(row["faults"] for row in report)}
