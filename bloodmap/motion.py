"""The four primitives every Blood motion mechanism is composed from.

Factored this way because the owner's grammar is factored this way, and
because the point of a grammar is to build and read combinations nobody has
named yet. A planar door and a curtain differ in how they SPLIT a footprint
and in which walls they flag; underneath they are the same four things.

    1. MARKED-WALL MOTION   which walls move, and what that drags with them
    2. MOTION MARKERS       the from/to pair that parameterizes the travel
    3. CONTROL WIRING       what makes it go, and whether the verb fits
    4. ROR STACK            the link pair, and whether you can see through it

Each is separately readable and separately buildable, each has its own
fixture, and `mechanism.planar_door` and `mechanism.curtain` add nothing but
composition facts on top.

The reading half and the authoring half live side by side on purpose. Every
defect this project has shipped came from one of them knowing something the
other did not.
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field
from typing import Any, Iterable

# ---------------------------------------------------------------------------
# 1. MARKED-WALL MOTION
# ---------------------------------------------------------------------------

#: `TranslateSector`'s payload flags, on walls. The editor colours them:
#: 16384 is BLUE and travels the marker vector, 32768 is GREEN and travels
#: exactly opposite. One sector with two opposite-flagged leaves is a double
#: door.
MOVES_WITH = 16384
MOVES_AGAINST = 32768
CARRY = MOVES_WITH | MOVES_AGAINST

#: The unmarked slide and rotate types move every wall regardless of flags;
#: `bAllWalls` in `triggers.cpp:879` is set for exactly these.
MOVES_EVERY_WALL = (616, 617)
MOVING_TYPES = (613, 614, 615, 616, 617)

#: The payload shapes the campaign builds, measured over 659 swept sectors.
SHAPE_BOUNDARY = "boundary re-partition"
SHAPE_RESIZE = "the sector resizes itself"
SHAPE_WHOLE = "the whole sector travels"
SHAPE_PARTIAL = "part of the sector travels"
SHAPE_NONE = "nothing moves"


def sector_walls(disk: Any, sector_id: int) -> range:
    fields = disk.sectors[sector_id].fields
    start = int(fields["wall_ptr"])
    return range(start, start + int(fields["wall_count"]))


def wall_owners(disk: Any) -> dict[int, int]:
    """Which sector owns each wall."""
    owners: dict[int, int] = {}
    for sector_id in range(len(disk.sectors)):
        for wall_id in sector_walls(disk, sector_id):
            owners[wall_id] = sector_id
    return owners


def flagged_walls(disk: Any, sector_id: int) -> dict[int, int]:
    """The moving sector's own flagged walls, wall id -> direction sign."""
    type_id = int(disk.sectors[sector_id].fields["type"])
    every = type_id in MOVES_EVERY_WALL
    out: dict[int, int] = {}
    for wall_id in sector_walls(disk, sector_id):
        cstat = int(disk.walls[wall_id].fields["cstat"])
        if every:
            out[wall_id] = 1
        elif cstat & MOVES_WITH:
            out[wall_id] = 1
        elif cstat & MOVES_AGAINST:
            out[wall_id] = -1
    return out


def moved_points(disk: Any, sector_id: int) -> dict[tuple[int, int], int]:
    """Every VERTEX the motion displaces, with the sign it moves under.

    The engine moves points, not walls. `TranslateSector` drags a flagged
    wall's own vertex and then its `point2`'s as well, unless that next wall
    carries a flag of its own -- in which case it travels under its own sign,
    which is exactly what lets a curtain's two caps close toward each other:

        triggers.cpp:897  if (wall[nWall].cstat&16384) {
                              DragPoint(nWall, ...);
                              if ((wall[v10].cstat&49152) == 0)
                                  DragPoint(v10, ...);

    So a flag on one wall moves a whole EDGE, and the set of moved points --
    not the set of flags -- is what the motion actually is.
    """
    flags = flagged_walls(disk, sector_id)
    every = int(disk.sectors[sector_id].fields["type"]) in MOVES_EVERY_WALL
    out: dict[tuple[int, int], int] = {}
    for wall_id, sign in flags.items():
        fields = disk.walls[wall_id].fields
        out[(int(fields["x"]), int(fields["y"]))] = sign
        end_id = int(fields["point2"])
        end = disk.walls[end_id].fields
        if every or not int(end["cstat"]) & CARRY:
            out.setdefault((int(end["x"]), int(end["y"])), sign)
    return out


def motion_set(disk: Any, sector_id: int,
               owners: dict[int, int] | None = None) -> dict[str, Any]:
    """Every wall the motion deforms, in EVERY sector, and why.

    The owner's deepest payload rule, and the one no gate here could see:
    `dragpoint` (engine.cpp:13071) walks the whole fan of walls around a
    vertex and sets each one's x,y. So moving a point moves it for every wall
    incident on it, in any sector that shares it -- one end travels and the
    other stays, and that wall is deformed whether its author meant it or not.

    The consequence is that a mechanism needs MOTION APERTURES: deliberate
    wall splits that bound the deformation, exactly as a doorway's jamb
    isolates a door's texture. E1M1's curtain has them -- its motion reaches
    only itself and the alcove it hangs in -- and the pattern zoo's did not,
    so pushing the fabric deformed the corners of the room.
    """
    points = moved_points(disk, sector_id)
    owners = owners if owners is not None else wall_owners(disk)
    walls: dict[int, set[int]] = defaultdict(set)
    for wall_id, wall in enumerate(disk.walls):
        key = (int(wall.fields["x"]), int(wall.fields["y"]))
        if key in points:
            walls[owners.get(wall_id, -1)].add(wall_id)
    return {
        "sector": sector_id,
        "points": sorted(points),
        "signs": {f"{x},{y}": sign for (x, y), sign in sorted(points.items())},
        "sectors": sorted(walls),
        "walls": {sector: sorted(found) for sector, found in sorted(walls.items())},
        "basis": "engine.cpp:13071 dragpoint walks every wall around a "
                 "vertex; triggers.cpp:897 drags a flagged wall's point2 too",
    }


def payload_shape(disk: Any, sector_id: int) -> dict[str, Any]:
    """What the ARRANGEMENT of flagged walls means.

    Three named shapes, all measured on the campaign: one flagged wall that
    is a portal RE-PARTITIONS the boundary between two sectors (E1M1's
    casket, 44 of them); two flagged walls with OPPOSITE signs make the
    sector RESIZE itself (E1M1's curtain, 104); everything else moves part
    or all of the sector rigidly.
    """
    flags = flagged_walls(disk, sector_id)
    if not flags:
        return {"shape": SHAPE_NONE, "flagged": 0}
    with_walls = sorted(w for w, s in flags.items() if s > 0)
    against = sorted(w for w, s in flags.items() if s < 0)
    every = int(disk.sectors[sector_id].fields["type"]) in MOVES_EVERY_WALL
    portals = [w for w in flags
               if int(disk.walls[w].fields["next_sector"]) >= 0]
    if not every and len(flags) == 1 and portals:
        return {
            "shape": SHAPE_BOUNDARY, "flagged": 1,
            "boundary_wall": portals[0],
            "re_partitions_with": int(
                disk.walls[portals[0]].fields["next_sector"]),
            "basis": "one flagged wall, and it is the portal to a neighbour: "
                     "its travel moves the line between the two sectors",
        }
    if with_walls and against:
        return {
            "shape": SHAPE_RESIZE, "flagged": len(flags),
            "advancing": with_walls, "retreating": against,
            "basis": "flagged walls carry OPPOSITE flags, so the sector's "
                     "own extent changes and the texture between them "
                     "deforms",
        }
    count = len(sector_walls(disk, sector_id))
    return {
        "shape": SHAPE_WHOLE if len(flags) >= count else SHAPE_PARTIAL,
        "flagged": len(flags), "of": count,
    }


@dataclass
class MotionSetFinding:
    """The actual motion set against what the construct declared."""

    sector: int
    actual: list[int] = field(default_factory=list)
    declared: list[int] = field(default_factory=list)
    undeclared: list[dict[str, Any]] = field(default_factory=list)

    @property
    def clean(self) -> bool:
        return not self.undeclared


def drag_closure(disk: Any, sector_id: int) -> dict[str, Any]:
    """Which walls `DragPoint` actually moves, walked the way the engine does.

    `motion_set` finds the moved walls by COORDINATE coincidence, which is a
    good approximation and not what the engine does. `DragPoint`
    (triggers.cpp:817-854) walks the `nextwall` ring from the dragged wall:

        vb = nWall
        do { if (wall[vb].nextwall >= 0) { vb = wall[wall[vb].nextwall].point2;
             ... } } while (vb != nWall)

    -- it follows the red-wall links, so it moves every wall that SHARES THE
    VERTEX THROUGH THE LINK GRAPH. Two walls can sit on the same coordinate
    without being linked (a T-junction, or two rooms that merely touch), and
    linked walls always share a coordinate. So the coordinate reading can
    over-report and never under-reports, and where the two disagree the
    nextwall walk is the truth.

    The walk itself lives in `motion_sim.drag_closure`, which is the one
    implementation: the sweep needs the per-driver SIGN and the loops the
    chains land in, and a second transcription that only needed the wall set
    drifted from it in exactly the way that matters -- it walked the ring
    forward only, and `DragPoint`'s forward walk STOPS at a one-sided wall
    and then goes round the other way through `lastwall` (triggers.cpp:836-848,
    engine.cpp:13227). A fin beside a void slot is precisely that case, so the
    short version under-reported the closure of the mechanism this project
    builds most.
    """
    from .motion_sim import drag_closure as _closure

    full = _closure(disk, sector_id)
    return {"walls": full["walls"], "sectors": full["sectors"],
            "flagged": sorted(flagged_walls(disk, sector_id)),
            "loops": full["loops"],
            "disagreements": full["disagreements"],
            "basis": full["basis"]}


def closure_disagreement(disk: Any, sector_id: int) -> dict[str, Any]:
    """Where the coordinate reading and the nextwall walk differ."""
    by_link = drag_closure(disk, sector_id)
    try:
        by_coord = motion_set(disk, sector_id)
    except Exception as exc:
        return {"error": str(exc)}
    link, coord = set(by_link["sectors"]), set(by_coord["sectors"])
    return {
        "by_nextwall": sorted(link), "by_coordinate": sorted(coord),
        "coordinate_only": sorted(coord - link),
        "nextwall_only": sorted(link - coord),
        "agree": link == coord,
    }


def check_motion_set(disk: Any, sector_id: int, declared: Iterable[int],
                     owners: dict[int, int] | None = None) -> MotionSetFinding:
    """Diff the actual motion set against the sentence's declared payload.

    The detection law from the owner's grammar: any member of the actual set
    the construct did not declare is an integration defect **even when the
    geometry is valid at every step of the travel**, because the deformation
    is reaching something nobody meant it to reach. The report names the wall
    and the vertex it drags through, so the fix -- a seam -- is obvious.
    """
    owners = owners if owners is not None else wall_owners(disk)
    found = motion_set(disk, sector_id, owners)
    allowed = set(declared) | {sector_id}
    out = MotionSetFinding(sector=sector_id, actual=list(found["sectors"]),
                           declared=sorted(allowed))
    points = dict(moved_points(disk, sector_id))
    for sector, walls in found["walls"].items():
        if sector in allowed:
            continue
        for wall_id in walls:
            fields = disk.walls[wall_id].fields
            out.undeclared.append({
                "sector": sector, "wall": wall_id,
                "vertex": [int(fields["x"]), int(fields["y"])],
                "why": f"wall {wall_id} of sector {sector} shares the moved "
                       f"vertex ({int(fields['x'])}, {int(fields['y'])}), so "
                       f"the motion drags one of its ends",
            })
    return out


# ---------------------------------------------------------------------------
# 2. MOTION MARKERS
# ---------------------------------------------------------------------------

#: kMarkerOff and kMarkerOn. Statnum 10 is the engine-instruction list, which
#: `dbLoadMap` culls from the world -- a marker built anywhere else is a
#: marker the level does not have.
MARKER_OFF, MARKER_ON = 3, 4
MARKER_STATNUM = 10
MARKER_PICNUM = 3997
MARKER_CSTAT = 32896


def marker_pair(disk: Any, sector_id: int) -> dict[str, Any] | None:
    """The from/to pair a Marked motion reads its travel out of.

    `marker_0` is the OFF pose and `marker_1` the ON pose, and `trInit`
    treats the geometry as SAVED at busy 1 -- so a sector whose `state` is 0
    displaces itself by the whole marker separation the instant the level
    loads. That is not a bug in the engine; it is how a gate is authored in
    its open pose and rests shut. It IS a bug when nobody meant it.
    """
    extra = _extra(disk.sectors[sector_id])
    if not extra:
        return None
    off, on = int(extra.get("marker_0", -1)), int(extra.get("marker_1", -1))
    if off < 0 or on < 0:
        return None
    a, b = disk.sprites[off].fields, disk.sprites[on].fields
    return {
        "off": {"sprite": off, "x": int(a["x"]), "y": int(a["y"]),
                "angle": int(a["angle"])},
        "on": {"sprite": on, "x": int(b["x"]), "y": int(b["y"]),
               "angle": int(b["angle"])},
        "travel": (int(b["x"]) - int(a["x"]), int(b["y"]) - int(a["y"])),
        "turn": int(b["angle"]) - int(a["angle"]),
        #: Not "where it rests on its way somewhere" -- which STATE it is
        #: in. The two marker positions ARE the two states.
        "state": 1 if int(extra.get("state", 0)) else 0,
        "at": "on" if int(extra.get("state", 0)) else "off",
    }


MARKER_AXIS = 5
#: Build's full circle. `RotatePoint` masks the angle with 2047, so a marker
#: angle that is a multiple of this turns all the way round and comes back.
FULL_CIRCLE = 2048


def rotate_marker(disk: Any, sector_id: int) -> dict[str, Any] | None:
    """The single marker a ROTATE reads, which is nothing like a slide's pair.

    A slide consumes only the DIFFERENCE between two markers and ignores
    where they sit. A rotate has one marker and consumes it the other way
    round: its x/y are the PIVOT that `RotatePoint` turns the sector about --
    absolute position mattering -- and its `ang` is the turn, interpolated
    from 0 (triggers.cpp:2230, the single-marker `TranslateSector` call
    passing a8=0 and a11=pMark1->ang).

    And `ang` is a TOTAL TURN, not a final heading. `RotatePoint` masks with
    2047, so a marker angle that is a whole number of full circles rotates
    the sector all the way round and returns it to where it was drawn: a
    gear, not a door. Thirteen of the curriculum's fifteen rotator markers
    are exact multiples of 2048.
    """
    extra = _extra(disk.sectors[sector_id])
    index = extra.get("marker_0")
    #: -1 is "no marker", and it was guarded at the top end only. Python
    #: indexes -1 from the END, so a sector with NO marker read the map's
    #: last sprite and, if that sprite happened to be a kMarkerAxis, reported
    #: a pivot and a turn for a mechanism that has neither. In a map with no
    #: sprites at all it raised instead. Found by `readback.state_pair`
    #: measuring a lift, which is a z motion and carries no marker.
    if index is None or not (0 <= int(index) < len(disk.sprites)):
        return None
    sprite = disk.sprites[int(index)]
    if int(sprite.fields["type"]) != MARKER_AXIS:
        return None
    turn = int(sprite.fields["angle"])
    return {
        "pivot": (int(sprite.fields["x"]), int(sprite.fields["y"])),
        "turn": turn,
        "turns_full_circles": turn % FULL_CIRCLE == 0 and turn != 0,
        "net_heading": turn % FULL_CIRCLE,
        "sprite": int(index),
    }


def place_markers(layout: Any, name: str, *, driven_region: str,
                  off_at: tuple[int, int], on_at: tuple[int, int],
                  off_region: str | None = None,
                  on_region: str | None = None,
                  z: int = 0, off_z: int | None = None,
                  on_z: int | None = None, turn: int = 0) -> list[str]:
    """The pair that anchors a motion's two STATES.

    **Markers are state-anchored, not journey-anchored.** Settled against
    `maps/blood/mechanism/Vanilla/DOOR-CURTAINS.map`, three exemplars to the
    coordinate: type 3 is the position FOR STATE OFF and type 4 the position
    FOR STATE ON. There is no "from" and no "to" and no rest marker -- rest
    is whatever `state` says.

    The mapper DRAWS the geometry at the ON pose. Every tutorial curtain's
    fabric hem is saved exactly at its type-4 marker: s3's fin tip sits at
    y -1152 and its marker 337 sits at y -1152, while marker 336 (OFF) is
    away at -2048 where the fabric will be when it is drawn across. `state`
    then decides which of the two the sector snaps to at load, and a state-0
    sector displaces itself by the whole separation the instant the level
    starts -- which is not a bug, it is how a curtain drawn open comes up
    closed.

    Modelling this as a journey with a rest end was wrong in both directions
    and is why the pattern zoo's curtains ran backwards.

    `owner` is still the sector CONTROLLED rather than the one a marker
    stands in, and `dbLoadMap` deletes any marker whose owner names no
    XSECTOR.
    """
    out = []
    for tag, kind, at, where, at_z in (
            ("off", MARKER_OFF, off_at, off_region or driven_region,
             z if off_z is None else off_z),
            ("on", MARKER_ON, on_at, on_region or driven_region,
             z if on_z is None else on_z)):
        out.append(layout.add_sprite(
            f"{name}_marker_{tag}", where,
            x=int(at[0]), y=int(at[1]), z=int(at_z),
            type=kind, picnum=MARKER_PICNUM, status=MARKER_STATNUM,
            cstat=MARKER_CSTAT, x_repeat=64, y_repeat=64,
            angle=int(turn) if tag == "on" else 0,
            marker_owner=driven_region))
    return out


def off_pose(disk: Any, sector_id: int) -> list[tuple[int, int]] | None:
    """The sector's outline at state OFF: busy 0, from the engine's own rule.

    `trInit` translates a moving sector by -65536 of the marker delta,
    records THAT as the base with `setBaseWallSect`, and only then applies
    the sector's own busy (triggers.cpp:2224-2245). So the outline saved in
    the map is the pose at busy 65536 -- state ON -- and this is the other
    one.

    It delegates to `blood_poses`, which transcribes `TranslateSector` and
    knows that a sweep starts at the sector's REST pose -- so a mechanism
    authored to start open does not get its two states swapped. An earlier
    version of this function subtracted the delta from every point in the sector, which
    is right only when the whole sector travels and wrong for every mechanism
    that deforms -- a curtain's fin moved bodily instead of stretching, so
    its closed span measured the same as its drawn one and the fabric could
    never be calibrated.
    """
    from .motion_sim import blood_poses

    if not marker_pair(disk, sector_id):
        return None
    off, _on = blood_poses(disk, sector_id)
    return [(int(round(x)), int(round(y))) for x, y in off]


def marker_convention(disk: Any, sector_id: int) -> str | None:
    """Whether the author parked the marker pair AT the two poses.

    This used to be called `drawn_pose` and was read as measuring which pose
    a map is saved in. It cannot: for a SLIDE the engine consumes only the
    difference between the markers (`x + vc - a4` in TranslateSector), so the
    pair's absolute position on the grid is free, and a pair parked in the
    middle of the sector drives it identically to one placed at the poses.

    Both conventions are in the curriculum -- 196 mechanisms place the pair at
    the two poses, 52 park it elsewhere -- so this reports which one is in
    use, and nothing more. `"at the poses"` means the reading of the markers
    as places is meaningful for this sector; `"parked"` means it is not.
    """
    pair = marker_pair(disk, sector_id)
    if not pair:
        return None
    from .motion_sim import blood_sector_walls

    walls = blood_sector_walls(disk, sector_id)
    flags = flagged_walls(disk, sector_id)
    if not flags or not walls:
        return None
    start = int(disk.sectors[sector_id].fields["wall_ptr"])
    tip = walls[sorted(flags)[0] - start]
    to_off = abs(tip[0] - pair["off"]["x"]) + abs(tip[1] - pair["off"]["y"])
    to_on = abs(tip[0] - pair["on"]["x"]) + abs(tip[1] - pair["on"]["y"])
    travel = max(abs(pair["travel"][0]), abs(pair["travel"][1])) or 1
    return "at the poses" if min(to_off, to_on) <= travel // 2 else "parked"


def drawn_pose(disk: Any, sector_id: int) -> str | None:
    """Deprecated: the geometry is ALWAYS the ON pose. See `off_pose`.

    Kept so existing readings do not break, and it now answers what the
    engine answers rather than what a coordinate comparison suggested.
    """
    return "on" if marker_pair(disk, sector_id) else None


# ---------------------------------------------------------------------------
# 3. CONTROL WIRING
# ---------------------------------------------------------------------------

#: Blood's command verbs, from the XSPRITE/XSECTOR `command` field.
CMD_OFF, CMD_ON, CMD_STATE, CMD_TOGGLE, CMD_NOT_STATE = 0, 1, 2, 3, 4
#: kCmdLink: couples state continuously and is sent outside the edge
#: guards, which is how a combination switch transmits with no edge flag.
CMD_LINK = 5

#: The routes a mechanism can be worked through, all orthogonal to each other
#: and to everything else in the grammar.
ROUTES = ("push", "wall_push", "wall_button", "remote", "level_start")

#: kChannelLevelStart fires before the player moves.
CHANNEL_LEVEL_START = 7


class WiringError(ValueError):
    """A control wiring that cannot work as written."""


def verb_fits_state(command: int, state: int) -> bool:
    """Whether a command can change a receiver in this state.

    The owner's state+verb rule, and the reason the zoo's casket "did not
    work": it was saved at state 1 and its switch sent command 1. ON to a
    thing already on is a no-op, and no amount of pushing changes that.

    TOGGLE and NOT_STATE always change something. ON changes only a thing
    that is off, OFF only a thing that is on.
    """
    command, state = int(command), 1 if int(state) else 0
    if command in (CMD_TOGGLE, CMD_NOT_STATE, CMD_STATE):
        return True
    if command == CMD_ON:
        return state == 0
    if command == CMD_OFF:
        return state == 1
    return False


def wiring(*, route: str = "remote", channel: int | None = None,
           command: int = CMD_TOGGLE, key: int | None = None,
           receiver_state: int = 0, locked: bool = False) -> dict[str, int]:
    """XSECTOR fields for one control route, with the verb checked.

    Refuses at CONSTRUCTION time a command that cannot change the receiver,
    because that defect is invisible in every static reading of the finished
    map -- the fields are all individually valid and the mechanism simply
    never moves.
    """
    if route not in ROUTES:
        raise WiringError(f"unknown route {route!r}; one of {ROUTES}")
    if not verb_fits_state(command, receiver_state):
        raise WiringError(
            f"command {command} cannot change a receiver saved at state "
            f"{receiver_state}: it is a no-op. Wire TOGGLE (3) unless the "
            f"intent needs a directed verb")
    fields: dict[str, int] = {}
    if route == "push":
        fields.update({"trigger_push": 1})
    elif route == "wall_push":
        fields.update({"trigger_push": 1, "trigger_wall_push": 1})
    elif route in ("remote", "wall_button", "level_start"):
        fields.update({"trigger_push": 0, "trigger_wall_push": 0})
        listens = CHANNEL_LEVEL_START if route == "level_start" else channel
        if not listens:
            raise WiringError(f"a {route} wiring needs a channel")
        fields["rx_id"] = int(listens)
    if key is not None:
        fields["key"] = int(key)
    if locked:
        fields["locked"] = 1
    return fields


#: `eventq.h`: the two system channels a secret uses, and the command range
#: that carries a NUMBER rather than a verb.
CHANNEL_SET_TOTAL_SECRETS = 1
CHANNEL_SECRET_FOUND = 2
#: `kCmdNumberic = 64`: command 64 means 0, 65 means 1, and so on.
CMD_NUMERIC_BASE = 64


def secret_credit(index: int = 0) -> dict[str, int]:
    """XSECTOR for a space that counts as a secret when you walk into it.

    `OTHERSECTORSFX-SECRETS.map` s2 and s3, to the field: transmit on channel
    2 (`kChannelSecretFound`) with the NUMERIC command that carries the
    secret's index -- 64 is 0, 65 is 1 -- on entering, once, with
    `dude_lockout` so a wandering monster cannot claim it for you.

    The command is the part that is easy to get wrong, and the zoo did: it
    sent command 1, which is kCmdOn. The counter wants a number.
    """
    return {"tx_id": CHANNEL_SECRET_FOUND,
            "command": CMD_NUMERIC_BASE + int(index),
            "trigger_on": 1, "trigger_once": 1, "trigger_enter": 1,
            "dude_lockout": 1}


def secret_total(count: int) -> dict[str, int]:
    """XSPRITE that tells the level how many secrets it has.

    Without it the tally has nothing to count against. The tutorial's sprite
    0 does it and so does every one of the campaign maps checked: listen on
    channel 7 (level start) and transmit the count on channel 1
    (`kChannelSetTotalSecrets`) as a numeric command.
    """
    return {"rx_id": CHANNEL_LEVEL_START,
            "tx_id": CHANNEL_SET_TOTAL_SECRETS,
            "command": CMD_NUMERIC_BASE + int(count), "trigger_on": 1}


def secret_faults(disk: Any) -> list[str]:
    """Secrets wired so the counter never hears them."""
    out = []
    total = 0
    credits = 0
    for kind, items in (("sector", disk.sectors), ("sprite", disk.sprites),
                        ("wall", disk.walls)):
        for index, item in enumerate(items):
            extra = _extra(item)
            channel = int(extra.get("tx_id", 0) or 0)
            command = int(extra.get("command", 0) or 0)
            if channel == CHANNEL_SET_TOTAL_SECRETS:
                total += 1
            if channel != CHANNEL_SECRET_FOUND:
                continue
            credits += 1
            if command < CMD_NUMERIC_BASE:
                out.append(
                    f"{kind} {index} credits a secret with command "
                    f"{command}, which is a verb; channel "
                    f"{CHANNEL_SECRET_FOUND} counts a NUMBER, so it wants "
                    f"{CMD_NUMERIC_BASE} or above")
    if credits and not total:
        out.append(
            f"{credits} secret(s) are credited but nothing sets the level "
            f"total on channel {CHANNEL_SET_TOTAL_SECRETS}, so the tally has "
            f"nothing to count against")
    return out


#: The canonical switch, from `#TYPE600.MAP` and `#MSGBUT.MAP`: type 21 on
#: picnum 1046, and it springs back after `wait_time` tenths.
SWITCH_TYPE, SWITCH_PICNUM = 21, 1046
SWITCH_WAIT = 30


def transmitter(*, channel: int, command: int = CMD_TOGGLE,
                receiver_state: int = 0, push: bool = True,
                on: bool = True, off: bool = False,
                wait_time: int | None = SWITCH_WAIT,
                shootable: bool = False, relay: bool = False
                ) -> dict[str, int]:
    """XSPRITE/XWALL fields for the thing that sends the command.

    **`trigger_on` is not optional, and this is why nothing worked.** A
    transmitter does not send because it has a `tx_id` and a `command`; it
    sends because its state CHANGED in a direction it was told to report:

        triggers.cpp:100  if (pXSprite->txID) {
                              if (command != kCmdLink && pXSprite->triggerOn
                                  && pXSprite->state)  evSend(...);
                              if (command != kCmdLink && pXSprite->triggerOff
                                  && !pXSprite->state) evSend(...);

    With neither flag set, pushing a switch flips its own state and sends
    NOTHING. The pattern zoo's casket and curtain switches were wired exactly
    that way -- valid `tx_id`, valid `command`, valid `trigger_push` -- and
    both did nothing at all when the owner pushed them.

    `wait_time` is the other half of the canonical switch: every switch in
    `#TYPE600.MAP` waits 30 tenths and then returns to its rest state, so a
    momentary button fires once per push instead of latching.
    """
    if not (on or off) and int(command) != CMD_LINK and not relay:
        raise WiringError(
            "a toggle, one-way or padlock switch that reports neither its ON "
            "nor its OFF edge can never send: triggers.cpp:100 gates evSend "
            "on triggerOn/triggerOff. Pass relay=True for a kGenTrigger, "
            "which sends from its own path, or use command 5 (Link), which "
            "kSwitchCombo sends outside those guards")
    if not verb_fits_state(command, receiver_state):
        raise WiringError(
            f"a transmitter sending command {command} to a receiver saved at "
            f"state {receiver_state} is a no-op")
    fields = {"tx_id": int(channel), "command": int(command)}
    if on:
        fields["trigger_on"] = 1
    if off:
        fields["trigger_off"] = 1
    if push:
        fields["trigger_push"] = 1
    if shootable:
        fields["trigger_vector"] = 1
    if wait_time:
        fields["wait_time"] = int(wait_time)
    return fields


def wall_button(layout: Any, region_id: str, edge: tuple, *, channel: int,
                command: int = CMD_TOGGLE, receiver_state: int = 0,
                shootable: bool = False) -> dict[str, int]:
    """Make one wall face the button for a mechanism on `channel`.

    The tutorials' way of wiring a shove, and it is not the sector flag we
    had been using. `xmapedit.pdf` p.239 gives the recipe for the curtain:
    press F6 on a curtain face, leave it type 0 Decoration, set TX ID 100,
    command Toggle, Send When Going ON and Going OFF, Trigger On Push -- and
    the SECTOR gets only RX 100. DOOR-CURTAINS s3 is exactly that: walls 38,
    39 and 40 each carry the XWALL, and the whole of s3's XSECTOR is rx 100,
    two busy times and the marker pair.

    Worth preferring for two reasons beyond fidelity. The button is the
    surface you actually touch, so a shove on the fabric works and a shove on
    the door frame does not; and the mechanism's own `tx` slot stays free,
    which is the difference between a door that can drive a light and one
    that cannot.
    """
    fields = transmitter(channel=channel, command=command,
                         receiver_state=receiver_state, push=True,
                         on=True, off=True, wait_time=None,
                         shootable=shootable)
    layout.wire_wall(region_id, edge[0], edge[1], **fields)
    return fields


# ---------------------------------------------------------------------------
# 3b. THINGS THAT BREAK, AND THE BLAST THAT SELLS IT
# ---------------------------------------------------------------------------

#: `kStatThing`. A thing is not a switch: it transmits when it DIES, so it
#: must live on the thing statnum or the engine never runs its damage path.
THING_STATNUM = 4
#: `kThingWallCrack`, and the tile the tutorials use for it.
CRACK_TYPE, CRACK_PICNUM = 408, 1127
#: `#SPR408.MAP` spr0: wall-aligned, one-sided, centred, translucent.
#: ENVIRONMENT-EXPLODEWALL uses 464 instead -- hitscan-blocking and opaque --
#: so the two oracles disagree here and the canonical single is preferred.
CRACK_CSTAT = 722
#: `kThingObjectExplode`: the puff that makes a breach read as a breach.
EXPLODER_TYPE, EXPLODER_PICNUM = 459, 908
#: `kStatDude`... no: the tutorials put exploders on 11 and nothing else.
EXPLODER_STATNUM = 11
EXPLODER_CSTAT = 128
#: #SPR408 staggers three of them by 2, 1, 1 tenths.
EXPLODER_WAITS = (2, 1, 1)


def thing_transmitter(*, channel: int, command: int = CMD_ON,
                      once: bool = True) -> dict[str, int]:
    """XSPRITE for a THING that fires when it is destroyed.

    Not `transmitter`, and the difference is why the zoo's crack did nothing.
    A switch reports a state edge from `SetSpriteState`; a thing reports its
    own death, and the trigger that carries that is `trigger_impact` --
    damage landing on it -- not `trigger_vector`, which is a hitscan
    crossing. `#SPR408.MAP` spr0 is the record, to the field: tx, command 1,
    Going ON, Going OFF, Once, Impact.
    """
    fields = {"tx_id": int(channel), "command": int(command),
              "trigger_on": 1, "trigger_off": 1, "trigger_impact": 1}
    if once:
        fields["trigger_once"] = 1
    return fields


def crack_thing(**overrides: int) -> dict[str, int]:
    """The full native record for a breakable wall crack.

    Constructors set `status` and `cstat` themselves. Leaving either to a
    default is how the zoo shipped a type-408 sitting on the default statnum,
    where the engine's damage path never reaches it: it looked right in every
    static reading and did nothing at all when shot.
    """
    record = {"type": CRACK_TYPE, "picnum": CRACK_PICNUM,
              "cstat": CRACK_CSTAT, "status": THING_STATNUM,
              "x_repeat": 64, "y_repeat": 64, "shade": -8}
    record.update(overrides)
    return record


def exploder(*, channel: int, wait: int = 1, **overrides: int) -> dict[str, int]:
    """One puff of the cascade that makes a crack BLOW rather than vanish.

    `#SPR408.MAP` places three, all on the crack's own channel, staggered by
    a tenth or two so the breach comes apart in sequence instead of all at
    once. Omitting them -- which the zoo did -- leaves a wall that silently
    disappears, and that is what the owner saw.
    """
    record = {"type": EXPLODER_TYPE, "picnum": EXPLODER_PICNUM,
              "cstat": EXPLODER_CSTAT, "status": EXPLODER_STATNUM,
              "x_repeat": 4, "y_repeat": 64, "shade": -8,
              "behavior": {"rx_id": int(channel), "trigger_on": 1,
                           "wait_time": int(wait)}}
    record.update(overrides)
    return record


def thing_faults(disk: Any) -> list[str]:
    """Things wired so they can never fire. A constructor-level error.

    Two ways to build a dead crack, both invisible to every other reading
    because each field is individually legal:

    * it is not on the THING statnum, so the engine's damage path never
      reaches it;
    * it reports `trigger_vector` (a hitscan crossing) instead of
      `trigger_impact` (damage landing), or reports no trigger at all.
    """
    out = []
    for index, sprite in enumerate(disk.sprites):
        if int(sprite.fields["type"]) != CRACK_TYPE:
            continue
        extra = _extra(sprite)
        if int(sprite.fields["status"]) != THING_STATNUM:
            out.append(
                f"sprite {index} is a type-{CRACK_TYPE} thing on statnum "
                f"{int(sprite.fields['status'])}, not {THING_STATNUM}: the "
                f"engine's damage path never reaches it, so it cannot break")
        if not extra.get("trigger_impact"):
            out.append(
                f"sprite {index} is a type-{CRACK_TYPE} thing without "
                f"trigger_impact"
                + (" (it has trigger_vector, which is a hitscan crossing, "
                   "not damage landing)" if extra.get("trigger_vector")
                   else "")
                + ": nothing will fire when it is destroyed")
        if extra.get("tx_id") and not (extra.get("trigger_on")
                                       or extra.get("trigger_off")):
            out.append(
                f"sprite {index} transmits on {int(extra['tx_id'])} but "
                f"reports no edge")
    return out


def silent_transmitters(disk: Any) -> list[str]:
    """Senders that can never send, because no edge is reported.

    The check that would have caught both of the zoo's dead switches without
    anyone walking the map.
    """
    out = []
    for index, sprite in enumerate(disk.sprites):
        extra = _extra(sprite)
        channel = int(extra.get("tx_id") or 0)
        if not channel or "command" not in extra:
            continue
        if int(extra["command"]) == 5:
            continue                      # kCmdLink never evSends
        if int(extra.get("trigger_on", 0)) or int(extra.get("trigger_off", 0)):
            continue
        out.append(
            f"sprite {index} carries tx_id {channel} and command "
            f"{int(extra['command'])} but reports neither its ON nor its OFF "
            f"edge, so triggers.cpp never calls evSend for it: pushing it "
            f"does nothing")
    return out


# ---------------------------------------------------------------------------
# 4. ROR STACK
# ---------------------------------------------------------------------------

#: kMarkerUpStack / kMarkerLowStack, paired on their XSPRITE `data_1`.
STACK_UPPER, STACK_LOWER = 11, 12

#: A stack is SEEN through only when its floor says so: picnum 504, or the
#: floor stat carrying 0x180. `mirrors.cpp` IsRorSector. The warp and the
#: view are separate properties, and a link without this is a hole you fall
#: through looking at a solid floor.
ROR_FLOOR_PICNUM = 504
ROR_FLOOR_STAT = 0x180


def is_see_through(disk: Any, sector_id: int, *,
                   surface: str = "floor") -> bool:
    """Whether you can look through this sector's floor -- or its ceiling.

    An upper stack sector is seen down through its FLOOR and a lower one up
    through its CEILING, and `#STACK.MAP` marks both.
    """
    fields = disk.sectors[sector_id].fields
    return (int(fields[f"{surface}_picnum"]) == ROR_FLOOR_PICNUM
            or bool(int(fields[f"{surface}_stat"]) & ROR_FLOOR_STAT))


def stack_pairs(disk: Any) -> list[dict[str, Any]]:
    """Every room-over-room link, with whether it can be seen through."""
    upper: dict[int, list[tuple[int, int]]] = defaultdict(list)
    lower: dict[int, list[tuple[int, int]]] = defaultdict(list)
    for index, sprite in enumerate(disk.sprites):
        extra = _extra(sprite)
        if not extra or "data_1" not in extra:
            continue
        kind = int(sprite.fields["type"])
        record = (int(sprite.fields["sector"]), index)
        if kind == STACK_UPPER:
            upper[int(extra["data_1"])].append(record)
        elif kind == STACK_LOWER:
            lower[int(extra["data_1"])].append(record)
    out = []
    for key in sorted(set(upper) & set(lower)):
        for up_sector, up_sprite in upper[key]:
            for low_sector, low_sprite in lower[key]:
                out.append({
                    "link_id": key,
                    "upper": up_sector, "lower": low_sector,
                    "sprites": [up_sprite, low_sprite],
                    "see_through": (is_see_through(disk, up_sector)
                                    and is_see_through(disk, low_sector,
                                                       surface="ceiling")),
                    "offset": (
                        int(disk.sprites[low_sprite].fields["x"])
                        - int(disk.sprites[up_sprite].fields["x"]),
                        int(disk.sprites[low_sprite].fields["y"])
                        - int(disk.sprites[up_sprite].fields["y"])),
                })
    return out


def build_stack_link(layout: Any, link_id: int, *, upper_region: str,
                     lower_region: str, upper_at: tuple[int, int],
                     lower_at: tuple[int, int], upper_z: int, lower_z: int,
                     see_through: bool = True) -> list[str]:
    """A room-over-room link, and the see-through floor that reveals it.

    A stack link is a TRANSLATION AT A PLANE: the marker pair carries the
    offset applied when a body crosses, so the two halves need not overlap in
    plan -- the oracle's are five thousand units apart in y.

    `see_through` sets the upper sector's floor to picnum 504, which is the
    half the pattern zoo forgot: the link worked and the floor looked solid.
    """
    #: BOTH halves, and that is not symmetry for its own sake: `#STACK.MAP`
    #: puts 504 on the upper sector's FLOOR (you look down through it) and on
    #: the lower sector's CEILING (you look up through it), and the oracle
    #: casket does the same on s3 and s6. Setting only the upper leaves the
    #: view from below looking at a solid ceiling.
    if see_through:
        layout.regions[upper_region].floor_picnum = ROR_FLOOR_PICNUM
        layout.regions[lower_region].ceiling_picnum = ROR_FLOOR_PICNUM
    made = []
    for tag, region, kind, at, z in (
            ("upper", upper_region, STACK_UPPER, upper_at, upper_z),
            ("lower", lower_region, STACK_LOWER, lower_at, lower_z)):
        made.append(layout.add_sprite(
            f"link:{link_id}:{tag}", region,
            x=int(at[0]), y=int(at[1]), z=int(z),
            type=int(kind), picnum=0, status=0, cstat=128,
            x_repeat=64, y_repeat=64, angle=0,
            behavior={"data_1": int(link_id)}))
    return made


def _extra(item: Any) -> dict[str, Any]:
    payload = getattr(item, "extra", None)
    if payload is None:
        return {}
    return payload.fields if hasattr(payload, "fields") else {}


def no_op_wirings(disk: Any) -> list[str]:
    """Transmitters whose command cannot change the receiver they address.

    The owner's state+verb rule as a whole-map check. Every field involved is
    individually valid, so nothing else in this project could see it: the
    pattern zoo shipped a casket saved at state 1 with a switch sending
    command 1, and it simply could not be operated.
    """
    receivers: dict[int, list[tuple[int, int]]] = defaultdict(list)
    for sector_id, sector in enumerate(disk.sectors):
        extra = _extra(sector)
        channel = int(extra.get("rx_id") or 0)
        if channel:
            receivers[channel].append((sector_id, int(extra.get("state", 0))))
    out = []
    for index, sprite in enumerate(disk.sprites):
        extra = _extra(sprite)
        channel = int(extra.get("tx_id") or 0)
        if not channel or "command" not in extra:
            continue
        command = int(extra["command"])
        for sector_id, state in receivers.get(channel, ()):
            if not verb_fits_state(command, state):
                out.append(
                    f"sprite {index} sends command {command} on channel "
                    f"{channel} to sector {sector_id}, which is saved at "
                    f"state {state}: a no-op")
    return out
