"""Mine the mechanism tutorials in `maps/blood/mechanism/`.

The owner supplied a curriculum: one folder of single-purpose maps, each
teaching one mechanism, authored by someone who knew the engine. This project
had built its mechanism subsystem from the campaign and from guesses, and the
tutorials disagreed with it in several places -- that disagreement is the
point. Reading them is cheaper than re-deriving Blood from the source, and
more reliable than inferring intent from a shipped level where a mechanism is
tangled with a fight.

The module mines FACTS -- what is in the map -- and leaves LAWS to the
detectors in `curriculum_laws`, so a law can never be asserted without the
citation that produced it. Every construct reduces to a SENTENCE, the Phase 8
grammar made textual, and the sentences are what the report shows.

`Modern/` is a separate dialect (NBlood extensions) and is deliberately out of
scope; `mine_folder` refuses it rather than reading it as vanilla.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from . import motion

#: `common_game.h`, the SPRITE TYPES enum. Named from the engine rather than
#: from what the tile looks like, because the field that MOVES is the type.
SPRITE_ROLES = {
    1: "single-player start", 2: "multiplayer start",
    3: "marker: position for state OFF", 4: "marker: position for state ON",
    5: "marker: rotation axis",
    6: "marker: link low", 7: "marker: link up", 8: "marker: warp destination",
    9: "marker: water up", 10: "marker: water low",
    11: "marker: stack upper", 12: "marker: stack lower",
    13: "marker: goo up", 14: "marker: goo low",
    15: "marker: path node", 18: "dude spawn", 19: "earthquake",
    20: "switch: toggle", 21: "switch: one-way", 22: "switch: combination",
    23: "switch: padlock",
    700: "generator: trigger (a relay)", 701: "generator: dripping water",
    702: "generator: dripping blood", 703: "generator: fireball",
    704: "generator: ecto skull", 705: "generator: dart",
    706: "generator: bubble", 707: "generator: bubbles",
    708: "generator: sound", 709: "sector sound", 710: "ambient sound",
}

#: Sector types that carry a marker pair and physically move in plan.
SWEPT = motion.MOVING_TYPES

#: The tutorials the mechanism subsystem is built on: mined AND fixtured.
#: Named here rather than in the script that runs the mine, because the
#: fixtures assert against this list and a test may not depend on a scratch
#: file.
TIER1 = (
    "DOOR-CEILING.map", "DOOR-CLOSET.map", "DOOR-COMBIDOORS.map",
    "DOOR-CURTAINS.map", "DOOR-CURTAINSD.map", "DOOR-PATHDOOR.map",
    "DOOR-PORTCULLIS.map", "DOOR-ROTATEGATE.map", "DOOR-ROTATING.map",
    "DOOR-SLIDING.map", "DOOR-SLIDINGD.map", "DOOR-SLIDINGGATE.map",
    "DOOR-SLIDINGGATED.map", "DOOR-SWINGING.map", "DOOR-SWINGINGD.map",
    "DOOR-SWINGINGGATE.map", "DOOR-SWINGINGGATED.map", "DOOR-3DSLIDEDOOR.map",
    "MACHINERY-LIFT.map", "MACHINERY-SLIFT.map", "MACHINERY-STEPSLIFT.map",
    "MACHINERY-CONVEYOR.map", "MACHINERY-ESCALATOR.map", "MACHINERY-GEAR.map",
    "MACHINERY-PISTON.map", "MACHINERY-2SLIDES.map", "MACHINERY-LEVER.map",
    "MACHINERY-SLEVER.map", "MACHINERY-3DBUTTON.map", "MACHINERY-TELEPORT.map",
    "STACKS3DSPACES.map", "STACKS3DSPACES-ROR1.map", "STACKS3DSPACES-ROR2.map",
    "STACKS3DSPACES-BADROR.map",
)

#: Mined into knowledge; fixtured only where the rework touches them.
TIER2_PREFIXES = ("ENVIRONMENT-", "WALL-", "WALLS-", "SPRITE-", "LIGHTING-",
                  "TRAP-", "MODELLING-", "OTHERSECTORSFX-")


def tier(name: str) -> str:
    """Which tier a tutorial belongs to."""
    if name in TIER1:
        return "1"
    if name.startswith(TIER2_PREFIXES):
        return "2"
    return "3"

#: The XSECTOR fields that are SINGLE-SLOT: one of each per sector, and so the
#: thing compositions collide over. `state`/`busy` are the state machine.
SLOTS = {
    "rx": ("rx_id",), "tx": ("tx_id", "command"),
    "state": ("state", "busy"),
    "shade wave": ("amplitude", "wave", "shade_floor", "shade_ceiling",
                   "shade_walls", "phase", "freq"),
    "wind": ("wind_vel", "wind_ang", "wind_always"),
    "panning": ("pan_vel", "pan_angle", "pan_always", "pan_floor",
                "pan_ceiling"),
    "bob": ("bob_speed", "bob_z_range", "bob_always", "bob_floor",
            "bob_ceiling"),
    "z pair": ("off_floor_z", "on_floor_z", "off_ceiling_z", "on_ceiling_z"),
    "damage": ("damage_type", "underwater"),
    "key": ("key", "locked"),
}

#: What answers a mechanism, as XSECTOR flags.
ROUTE_FIELDS = {
    "trigger_push": "push", "trigger_wall_push": "a shove",
    "trigger_enter": "entering", "trigger_exit": "leaving",
    "trigger_proximity": "proximity", "trigger_impact": "impact",
    "trigger_explode": "an explosion", "trigger_wall_gib": "the wall breaking",
}


def _extra(item: Any) -> dict[str, Any]:
    payload = getattr(item, "extra", None)
    if payload is None:
        return {}
    fields = payload.fields if hasattr(payload, "fields") else {}
    return {k: v for k, v in fields.items()
            if v not in (0, -1, False) and k != "reference"}


@dataclass
class Construct:
    """One mechanism in one tutorial map, as facts."""

    sector: int
    type_id: int
    extra: dict[str, Any] = field(default_factory=dict)
    markers: dict[str, Any] | None = None
    drawn_at: str | None = None
    shape: str = ""
    motion_sectors: list[int] = field(default_factory=list)
    flagged: int = 0
    z_pair: dict[str, int] = field(default_factory=dict)
    slots: list[str] = field(default_factory=list)
    drives: list[int] = field(default_factory=list)
    driven_by: list[str] = field(default_factory=list)
    buttons: list[int] = field(default_factory=list)
    carried_sprites: list[int] = field(default_factory=list)
    sentence: str = ""

    def as_json(self) -> dict[str, Any]:
        out: dict[str, Any] = {
            "sector": self.sector, "type": self.type_id, "shape": self.shape,
            "slots": self.slots, "sentence": self.sentence}
        for name in ("drawn_at", "z_pair", "drives", "driven_by",
                     "motion_sectors", "flagged", "buttons",
                     "carried_sprites"):
            value = getattr(self, name)
            if value:
                out[name] = value
        if self.markers:
            out["markers"] = {"travel": list(self.markers["travel"]),
                              "state": self.markers["state"],
                              "at": self.markers["at"]}
        return out


@dataclass
class Reading:
    """One tutorial map, mined."""

    name: str
    sectors: int = 0
    walls: int = 0
    sprites: int = 0
    constructs: list[Construct] = field(default_factory=list)
    wiring: dict[str, Any] = field(default_factory=dict)
    sprite_roles: dict[str, int] = field(default_factory=dict)
    stacks: list[dict[str, Any]] = field(default_factory=list)
    wall_buttons: dict[str, list[int]] = field(default_factory=dict)
    notes: list[str] = field(default_factory=list)

    def as_json(self) -> dict[str, Any]:
        return {"map": self.name, "sectors": self.sectors,
                "walls": self.walls, "sprites": self.sprites,
                "constructs": [c.as_json() for c in self.constructs],
                "wiring": self.wiring, "sprite_roles": self.sprite_roles,
                "stacks": self.stacks, "wall_buttons": self.wall_buttons,
                "notes": self.notes}


def slots_used(extra: dict[str, Any]) -> list[str]:
    """Which single-slot XSECTOR resources this sector has spent."""
    return [name for name, keys in SLOTS.items()
            if any(key in extra for key in keys)]


def z_pair(extra: dict[str, Any]) -> dict[str, int]:
    """The state-anchored z quartet, if this sector has one.

    The exact analogue of the marker pair in the vertical: `off_floor_z` is
    where the floor sits for state OFF and `on_floor_z` for state ON, and the
    ceiling has its own pair. A lift is the pair with the floor moving; a
    ceiling door is the pair with the ceiling moving.
    """
    keys = ("off_floor_z", "on_floor_z", "off_ceiling_z", "on_ceiling_z")
    if not any(key in extra for key in keys):
        return {}
    return {key: int(extra.get(key, 0)) for key in keys}


def wiring_graph(disk: Any) -> dict[str, Any]:
    """Every transmitter and receiver in the map, by channel.

    Sectors, walls and sprites all carry rx/tx, so the control bus is one
    graph over all three -- which is why a construct's effect network can
    leave its own storage entirely.
    """
    tx: dict[int, list[dict[str, Any]]] = {}
    rx: dict[int, list[dict[str, Any]]] = {}
    for kind, items in (("sector", disk.sectors), ("wall", disk.walls),
                        ("sprite", disk.sprites)):
        for index, item in enumerate(items):
            extra = _extra(item)
            if not extra:
                continue
            node: dict[str, Any] = {"kind": kind, "id": index}
            if kind == "sprite":
                type_id = int(item.fields["type"])
                node["role"] = SPRITE_ROLES.get(type_id, f"type {type_id}")
            if "tx_id" in extra:
                tx.setdefault(int(extra["tx_id"]), []).append(
                    dict(node, command=int(extra.get("command", 0)),
                         edges=[name for name in ("trigger_on", "trigger_off")
                                if extra.get(name)]))
            if "rx_id" in extra:
                rx.setdefault(int(extra["rx_id"]), []).append(node)
    channels = sorted(set(tx) | set(rx))
    return {"channels": {str(c): {"tx": tx.get(c, []), "rx": rx.get(c, [])}
                         for c in channels},
            "dangling_tx": sorted(c for c in tx if c not in rx and c > 7),
            "dangling_rx": sorted(c for c in rx if c not in tx and c > 7)}


def sentence(construct: Construct) -> str:
    """The Phase 8 grammar for one construct, as a line of English."""
    parts = [f"s{construct.sector} type {construct.type_id}"]
    if construct.shape:
        parts.append(construct.shape)
    if construct.markers:
        travel = construct.markers["travel"]
        axis = "x" if abs(travel[0]) >= abs(travel[1]) else "y"
        parts.append(
            f"markers {max(abs(travel[0]), abs(travel[1]))} apart along "
            f"{axis}, pair {construct.drawn_at or 'unplaceable'}, rests at "
            f"{construct.markers['at'].upper()}")
    if construct.z_pair:
        pair = construct.z_pair
        moves = []
        if pair["off_floor_z"] != pair["on_floor_z"]:
            moves.append(
                f"floor {pair['off_floor_z']} -> {pair['on_floor_z']}")
        if pair["off_ceiling_z"] != pair["on_ceiling_z"]:
            moves.append(
                f"ceiling {pair['off_ceiling_z']} -> {pair['on_ceiling_z']}")
        parts.append("; ".join(moves) if moves
                     else "a z pair that does not travel")
    if construct.driven_by:
        parts.append("answered by " + ", ".join(construct.driven_by))
    if construct.buttons:
        parts.append(f"shoved through {len(construct.buttons)} wall "
                     f"button(s)")
    if construct.carried_sprites:
        parts.append(f"carries {len(construct.carried_sprites)} sprite(s)")
    if construct.drives:
        parts.append("drives " + ", ".join(f"s{s}" for s in construct.drives))
    if len(construct.motion_sectors) > 1:
        parts.append(f"deforms {len(construct.motion_sectors)} sectors")
    return ", ".join(parts)


def _bbox(disk: Any, sector_id: int) -> tuple[int, int, int, int]:
    walls = list(motion.sector_walls(disk, sector_id))
    xs = [int(disk.walls[w].fields["x"]) for w in walls]
    ys = [int(disk.walls[w].fields["y"]) for w in walls]
    return min(xs), min(ys), max(xs), max(ys)


def outer_loop(disk: Any, sector_id: int) -> list[tuple[int, int]]:
    """The sector's OUTER wall loop, in order.

    A Build sector is one outer loop plus zero or more inner loops (the holes
    that hold sectors drawn inside it). `wall_ptr` starts the outer one.
    """
    start = int(disk.sectors[sector_id].fields["wall_ptr"])
    points, current = [], start
    while True:
        fields = disk.walls[current].fields
        points.append((int(fields["x"]), int(fields["y"])))
        current = int(fields["point2"])
        if current == start or len(points) > 512:
            return points


def is_convex(points: list[tuple[int, int]]) -> bool:
    signs = set()
    count = len(points)
    for index in range(count):
        ax, ay = points[index]
        bx, by = points[(index + 1) % count]
        cx, cy = points[(index + 2) % count]
        cross = (bx - ax) * (cy - by) - (by - ay) * (cx - bx)
        if cross:
            signs.add(cross > 0)
    return len(signs) <= 1


def stack_faults(disk: Any, pair: dict[str, Any]) -> list[str]:
    """Check one ROR link against the rules the manual states.

    `maps/blood/mechanism/xmapedit.pdf` p.364-365 lists them, and
    STACKS3DSPACES-BADROR is shipped as the NEGATIVE example -- the manual
    points at it to show what goes wrong -- so a reader that calls it fine is
    wrong. Its link sectors are the only CONCAVE ones in the whole curriculum:
    ten-wall outer loops with the side alcoves cut into the boundary, where
    every working link sector in ROR1 and ROR2 keeps a four- or six-wall
    convex outer loop and puts its complexity in inner loops instead. That is
    the manual's "do not over-complicate the shape of the sectors", measured.
    """
    faults = []
    upper, lower = pair["upper"], pair["lower"]
    ub, lb = _bbox(disk, upper), _bbox(disk, lower)
    if (ub[2] - ub[0], ub[3] - ub[1]) != (lb[2] - lb[0], lb[3] - lb[1]):
        faults.append(
            f"the halves are not the same size ({ub[2] - ub[0]}x"
            f"{ub[3] - ub[1]} over {lb[2] - lb[0]}x{lb[3] - lb[1]}); the pair "
            f"is a portal and must be congruent")
    for link_sector in (upper, lower):
        loop = outer_loop(disk, link_sector)
        if not is_convex(loop):
            faults.append(
                f"s{link_sector} is a link sector whose outer loop is "
                f"concave ({len(loop)} walls); a link is a portal silhouette "
                f"and re-entrant corners in it are what HOMs")
    for marker_sprite in pair["sprites"]:
        sprite = disk.sprites[marker_sprite]
        role = int(sprite.fields["type"])
        sector_id = upper if role == motion.STACK_UPPER else lower
        plane = "floor_z" if role == motion.STACK_UPPER else "ceiling_z"
        want = int(disk.sectors[sector_id].fields[plane])
        if int(sprite.fields["z"]) != want:
            faults.append(
                f"the {plane.split('_')[0]} marker floats: sprite "
                f"{marker_sprite} sits at z {int(sprite.fields['z'])} and the "
                f"plane it links is at {want}")
    return faults


def wall_transmitters(disk: Any) -> dict[int, list[int]]:
    """Walls that TRANSMIT, grouped by the channel they send on.

    The tutorials wire a shove this way rather than with the sector's own
    `trigger_wall_push`: the curtain's three fabric faces each carry an XWALL
    with tx 100 and Push, and the sector merely receives 100 (manual p.239).
    It buys two things -- the button is exactly the surface you touch, and the
    sector's single tx slot stays free for the mechanism's own effects.
    """
    out: dict[int, list[int]] = {}
    for index, wall in enumerate(disk.walls):
        extra = _extra(wall)
        if "tx_id" in extra and extra.get("trigger_push"):
            out.setdefault(int(extra["tx_id"]), []).append(index)
    return out


def mine_map(path: str | Path) -> Reading:
    """One tutorial map, read into constructs and a wiring graph."""
    from .format import read_map

    path = Path(path)
    disk = read_map(path)
    reading = Reading(name=path.name, sectors=len(disk.sectors),
                      walls=len(disk.walls), sprites=len(disk.sprites))
    reading.wiring = wiring_graph(disk)
    roles: dict[str, int] = {}
    for sprite in disk.sprites:
        type_id = int(sprite.fields["type"])
        if not type_id:
            continue
        name = SPRITE_ROLES.get(type_id, f"type {type_id}")
        roles[name] = roles.get(name, 0) + 1
    reading.sprite_roles = dict(sorted(roles.items()))
    try:
        reading.stacks = motion.stack_pairs(disk)
        for pair in reading.stacks:
            pair["faults"] = stack_faults(disk, pair)
    except Exception as exc:                        # pragma: no cover
        reading.notes.append(f"stack pairs unreadable: {exc}")
    buttons = wall_transmitters(disk)
    reading.wall_buttons = {str(k): v for k, v in sorted(buttons.items())}

    channels = reading.wiring["channels"]
    for index, sector in enumerate(disk.sectors):
        type_id = int(sector.fields["type"])
        extra = _extra(sector)
        if not type_id and not extra:
            continue
        construct = Construct(sector=index, type_id=type_id, extra=extra)
        construct.slots = slots_used(extra)
        construct.z_pair = z_pair(extra)
        if type_id in SWEPT:
            try:
                pair = motion.marker_pair(disk, index)
                construct.markers = pair
                construct.drawn_at = motion.marker_convention(disk, index)
                construct.motion_sectors = motion.motion_set(disk,
                                                             index)["sectors"]
                construct.flagged = len(motion.flagged_walls(disk, index))
                construct.shape = motion.payload_shape(disk, index)["shape"]
            except Exception as exc:
                reading.notes.append(f"s{index}: not swept -- {exc}")
        construct.driven_by = [label for key, label in ROUTE_FIELDS.items()
                               if extra.get(key)]
        if "rx_id" in extra:
            construct.driven_by.append(f"channel {int(extra['rx_id'])}")
        if "tx_id" in extra:
            listeners = channels.get(str(int(extra["tx_id"])), {}).get("rx", [])
            construct.drives = [node["id"] for node in listeners
                                if node["kind"] == "sector"
                                and node["id"] != index]
        if "rx_id" in extra:
            construct.buttons = buttons.get(int(extra["rx_id"]), [])
        if construct.markers:
            carried = []
            for sprite_id, sprite in enumerate(disk.sprites):
                if int(sprite.fields["sector"]) != index:
                    continue
                if int(sprite.fields["cstat"]) & motion.CARRY:
                    carried.append(sprite_id)
            construct.carried_sprites = carried
        construct.sentence = sentence(construct)
        reading.constructs.append(construct)
    return reading


def mine_folder(folder: str | Path, *,
                names: list[str] | None = None) -> list[Reading]:
    """Mine a folder of tutorials. `Modern/` is a different dialect."""
    folder = Path(folder)
    if folder.name.lower() == "modern":
        raise ValueError(
            "Modern/ is the NBlood-extension dialect, not vanilla Blood; "
            "mining it as vanilla would attribute extension semantics to the "
            "base engine")
    picked = sorted(path for path in folder.glob("*.[mM][aA][pP]")
                    if names is None or path.name in names)
    out = []
    for path in picked:
        try:
            out.append(mine_map(path))
        except Exception as exc:
            failed = Reading(name=path.name)
            failed.notes.append(f"unreadable: {exc}")
            out.append(failed)
    return out
