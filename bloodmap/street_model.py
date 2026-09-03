"""Reading a street built on the ground-plane model, and gating it.

The model (street-model-decisions sections 7, 10, 11): the street is the
ground plane, a pavement is an island standing 2048 on it, and **the kerb is
not a thing anyone draws** -- it is the island's edge showing above the road,
so the band that draws is the one facing the ROAD.

Gravesend gave that band the house tiles, and the explanation is structural
rather than careless: its streets were the residue left when district regions
had holes cut in them, so the band was a hole's EDGE and inherited the
building's material. Nothing was choosing it.

The gate here is exact because the kerb is now a **declared record**. P14's
first run could not calibrate a geometric one -- guessing from the map which
two-sided steps are kerbs picks up harbour walls, ledges and rooftops, the
campaign's outdoor kerb tiles are diverse (2490, 67, 110, 2499, 6... top eight
sharing 43% of 1046 records), and the narrower clause "never the material
above it" scored the campaign at 16% against the city's 0%, so the city was
already better by it. With `overlay.HeightIsland` declaring which records are
kerbs there is a population to check instead of a population to infer, which
is what closes owner-queue item 18.

The absolute check that goes with it (owner-queue item 17): the rise is 2048,
E3M1's without exception on all eleven of its kerbs, and it is asserted as a
number rather than as "the same as its neighbours".
"""

from __future__ import annotations

import math
import statistics
from typing import Any, Iterable, Sequence

#: E3M1's, and Gravesend's choice. Not a campaign law -- see the module note.
KERB_TILE = 6
#: E3M1's kerb step, on 11 of 11 road-side records. An absolute.
KERB_RISE = 2048


class StreetModelError(ValueError):
    """A street that does not read as one."""


def _fields(item: Any) -> Any:
    return item["fields"] if isinstance(item, dict) else item.fields


def kerb_faults(disk: Any, declared: Sequence[dict], *,
                owners: Sequence[int] | None = None) -> list[str]:
    """Check every record an island declared as its kerb.

    `declared` is what the build emitted -- `{road_piece, island, edge,
    picnum, rise}` per record -- so this asks a question about records the
    model claims rather than about steps that look like kerbs.

    Three clauses, and the middle one is the owner's:

    * the band wears the declared kerb tile;
    * it **never wears the material of the surface standing above it** -- a
      kerb that wears the pavement's tile is the pavement folded down, and one
      that wears the building's is what Gravesend had;
    * the step is `KERB_RISE`, absolutely, not merely consistent.
    """
    from .texture_frame import sector_index

    owners = list(owners) if owners is not None else sector_index(disk)
    index = _edge_index(disk, owners)
    out = []
    for record in declared:
        edge = tuple(tuple(point) for point in record["edge"])
        #: A boundary has TWO records and only one of them is the kerb: the
        #: one on the ROAD's side. Picking by edge orientation gets whichever
        #: happens to be indexed first, which is how the first run of this
        #: reader reported the island's own facade tile as a kerb fault. The
        #: road is the side whose floor is LOWER -- numerically larger, since
        #: Blood's z grows downward -- which is true by the definition of an
        #: island and needs no names carried in from the build.
        candidates = [found for found in
                      (index.get(edge), index.get((edge[1], edge[0])))
                      if found is not None]
        if not candidates:
            out.append(f"kerb {record['island']}: no record at {edge}")
            continue
        found = max(candidates,
                    key=lambda row: int(_fields(disk.sectors[row[1]])["floor_z"]))
        wall_id, here, there = found
        face = _fields(disk.walls[wall_id])
        picnum = int(face["picnum"])
        want = int(record.get("picnum", KERB_TILE))
        if picnum != want:
            out.append(
                f"wall[{wall_id}] is a declared kerb wearing {picnum}, not "
                f"the island's kerb tile {want}")
        if there >= 0:
            above = int(_fields(disk.sectors[there])["floor_picnum"])
            if picnum == above:
                out.append(
                    f"wall[{wall_id}] wears {picnum}, the material of the "
                    f"surface standing above it -- a kerb is not the pavement "
                    f"folded down")
            rise = (int(_fields(disk.sectors[here])["floor_z"])
                    - int(_fields(disk.sectors[there])["floor_z"]))
            if rise != int(record.get("rise", KERB_RISE)):
                out.append(
                    f"wall[{wall_id}] steps {rise}, not the declared "
                    f"{record.get('rise', KERB_RISE)} (E3M1: 2048 on 11 of 11)")
    return out


def _edge_index(disk: Any, owners: Sequence[int]) -> dict:
    out = {}
    for wall_id, wall in enumerate(disk.walls):
        face = _fields(wall)
        nxt = _fields(disk.walls[int(face["point2"])])
        key = ((int(face["x"]), int(face["y"])), (int(nxt["x"]), int(nxt["y"])))
        out[key] = (wall_id, owners[wall_id], int(face["next_sector"]))
    return out


def shadow_edge_faults(disk: Any, edges: Iterable[tuple], bearing_degrees: float,
                       tolerance: float) -> list[str]:
    """Every declared shadow edge runs at the level's one sun."""
    from .overlay import Cut

    out = []
    for edge in edges:
        (ax, ay), (bx, by) = edge
        found = Cut((int(ax), int(ay)), (int(bx), int(by))).bearing
        gap = min(abs(found - bearing_degrees),
                  180.0 - abs(found - bearing_degrees))
        if gap > tolerance:
            out.append(f"shadow edge {edge} runs at {found:.1f} deg, "
                       f"{gap:.1f} off the sun's {bearing_degrees:.1f}")
    return out


def sees_the_kerb(disk: Any, road_sector: int,
                  owners: Sequence[int] | None = None) -> dict[str, Any]:
    """What a body standing on the road sees at the edge of it.

    The owner's acceptance test in one reading: from the road, the first thing
    up is the kerb face, not the house. A road whose boundary records wear the
    building's material has no kerb, whatever its heights say.
    """
    from .texture_frame import sector_index

    owners = list(owners) if owners is not None else sector_index(disk)
    fields = _fields(disk.sectors[road_sector])
    start = int(fields["wall_ptr"])
    count = int(fields["wall_count"])
    seen = []
    for wall_id in range(start, start + count):
        face = _fields(disk.walls[wall_id])
        nxt = int(face["next_sector"])
        if nxt < 0:
            continue
        rise = (int(fields["floor_z"])
                - int(_fields(disk.sectors[nxt])["floor_z"]))
        if rise <= 0:
            continue                        # the neighbour is not standing up
        seen.append({"wall": wall_id, "picnum": int(face["picnum"]),
                     "rise": rise,
                     "above": int(_fields(disk.sectors[nxt])["floor_picnum"])})
    return {"road": road_sector, "faces": seen,
            "kerb_tiles": sorted({row["picnum"] for row in seen}),
            "materials_above": sorted({row["above"] for row in seen})}


# ---------------------------------------------------------------------------
# the reader side: recover from a built map what the emitter declared
# ---------------------------------------------------------------------------

def read_city(disk: Any, *, road_tile: int = 352, pavement_tile: int = 4,
              owners: Sequence[int] | None = None) -> dict:
    """What a reader can recover from a built city, and what it cannot.

    The symmetry rule: every writer has a reader, and the reader's census is
    the writer's evidence. This is the reader for the ground model -- planes,
    islands, the shade levels and the sun's bearing -- and it is deliberately
    written to report what it CANNOT recover as well, because a value that
    only the emitter knows is a claim nobody can check.

    The bearing comes out of the geometry rather than out of a declaration:
    every two-sided record between two same-z outdoor sectors of DIFFERENT
    shade is an iso-line of the field, and an oblique one lies along the sun.
    """
    from .texture_frame import sector_index

    owners = list(owners) if owners is not None else sector_index(disk)
    outdoor = [i for i, sec in enumerate(disk.sectors)
               if int(_fields(sec)["ceiling_stat"]) & 1]
    road = {i for i in outdoor
            if int(_fields(disk.sectors[i])["floor_picnum"]) == road_tile}
    pavement = {i for i in outdoor
                if int(_fields(disk.sectors[i])["floor_picnum"])
                == pavement_tile}

    graph: dict[int, set] = {}
    boundaries = []
    for wall_id, wall in enumerate(disk.walls):
        face = _fields(wall)
        there = int(face["next_sector"])
        if there < 0:
            continue
        here = owners[wall_id]
        a, b = disk.sectors[here], disk.sectors[there]
        if int(_fields(a)["floor_z"]) == int(_fields(b)["floor_z"]):
            graph.setdefault(here, set()).add(there)
            if (here in outdoor and there in outdoor
                    and int(_fields(a)["floor_shade"])
                    != int(_fields(b)["floor_shade"])):
                boundaries.append(wall_id)

    def components(members):
        seen = set()
        count = 0
        for start in sorted(members):
            if start in seen:
                continue
            count += 1
            stack = [start]
            seen.add(start)
            while stack:
                node = stack.pop()
                for nxt in graph.get(node, ()):
                    if nxt in members and nxt not in seen:
                        seen.add(nxt)
                        stack.append(nxt)
        return count

    bearings = []
    for wall_id in boundaries:
        face = _fields(disk.walls[wall_id])
        nxt = _fields(disk.walls[int(face["point2"])])
        dx = int(nxt["x"]) - int(face["x"])
        dy = int(nxt["y"]) - int(face["y"])
        if dx == 0 or dy == 0:
            continue
        bearings.append(math.degrees(math.atan2(abs(dy), abs(dx))))

    shades = sorted({int(_fields(disk.sectors[i])["floor_shade"])
                     for i in road | pavement})
    return {
        "planes": components(road),
        "islands": components(pavement),
        "road_sectors": len(road),
        "pavement_sectors": len(pavement),
        "shade_levels": shades,
        "iso_lines": len(boundaries),
        "oblique_iso_lines": len(bearings),
        "sun_bearing_degrees": (statistics.median(bearings)
                                if bearings else None),
        #: What this reader CANNOT recover, by name. Each is a real asymmetry
        #: between what the emitter said and what the map records, not a
        #: failure of the build.
        "symmetry_gaps": [
            "surface identity: two islands joined by a pavement-only path are "
            "one connected component, so the reader counts networks and not "
            "the surfaces the emitter declared",
            "field depth: the map records a shade, and base + k*step is only "
            "recoverable as a set of levels once the base and the step are "
            "assumed -- the depth k itself is not written anywhere",
            "lamp authorship: a lamp's delta has been summed into floor_shade "
            "by the time it is on disk, so the reader sees the total and not "
            "the contributions the ledger arbitrated",
        ],
    }


# ---------------------------------------------------------------------------
# the owner's four findings, as readers that run on any map
# ---------------------------------------------------------------------------

#: The campaign's whole sky family. `usage_kinds.sky_family` derives the same
#: set from the corpus; this is here so a reader can name one without an
#: index.
SKY_FAMILY = frozenset({2500, 3491, 3678})

#: What a light must be to stand outdoors. Blood mounts its lights on walls:
#: of the campaign's wall-aligned bright sprites the commonest are 795, 510
#: and 511, all indoor, and OUTDOORS the campaign mounts two in 43 maps. So a
#: lamp on a street is a choice either way -- but a lamp hanging from nothing
#: is not a choice, it is a mistake, and this is the bit that says so.
SPRITE_WALL_ALIGNED = 16


def kerb_tile_faults(disk: Any, *, kerb_tile: int = KERB_TILE,
                     road_tile: int = 352, pavement_tile: int = 4,
                     owners: Sequence[int] | None = None) -> list[str]:
    """A kerb exists only where ROAD meets PAVEMENT (owner, W1).

    E3M1 says it twice over: its eleven tile-6 records are all road-side and
    all step 2048 to a pavement, and its road|road records wear the district's
    facade family (401, 400, 380, 393) instead. So the kerb tile is never a
    surface's default material -- the moment it is, every shadow cut and every
    map edge reads as a kerb, and so does the face of an end wall.
    """
    from .texture_frame import sector_index

    owners = list(owners) if owners is not None else sector_index(disk)
    out = []
    for wall_id, wall in enumerate(disk.walls):
        face = _fields(wall)
        if int(face["picnum"]) != int(kerb_tile):
            continue
        here = owners[wall_id]
        there = int(face["next_sector"])
        pair = {int(_fields(disk.sectors[here])["floor_picnum"]),
                int(_fields(disk.sectors[there])["floor_picnum"])
                if there >= 0 else -1}
        if pair != {int(road_tile), int(pavement_tile)}:
            out.append(f"wall {wall_id} wears the kerb tile {kerb_tile} but "
                       f"separates {sorted(pair)}, not road|pavement")
    return out


def step_shade_faults(disk: Any, *, offset: int = 6, kerb_tile: int = KERB_TILE,
                      owners: Sequence[int] | None = None) -> list[str]:
    """A step's face follows the field its floor is in (owner, W2).

    Measured on E3M1's eleven kerb records: the six standing on road at floor
    shade 32 read a median 38, the five standing on road at 8 read 8, and the
    median delta over all eleven is +6. A face that keeps the base while the
    surfaces around it darken is the one thing in an outdoor scene that does
    not obey the sun.
    """
    from .texture_frame import sector_index

    owners = list(owners) if owners is not None else sector_index(disk)
    out = []
    for wall_id, wall in enumerate(disk.walls):
        face = _fields(wall)
        if int(face["picnum"]) != int(kerb_tile):
            continue
        here = owners[wall_id]
        want = int(_fields(disk.sectors[here])["floor_shade"]) + int(offset)
        got = int(face["shade"])
        if got != want:
            out.append(f"wall {wall_id} is a step out of a floor at shade "
                       f"{int(_fields(disk.sectors[here])['floor_shade'])} "
                       f"and reads {got}, not {want}")
    return out


def lamp_faults(disk: Any, *, tiles: Iterable[int] = (),
                max_shade: int = -64,
                owners: Sequence[int] | None = None) -> list[str]:
    """A lamp hangs from something or stands on something (owner, W3).

    Under an open sky there is nothing overhead to hang from, so a ceiling
    lantern out there hangs from nothing. Either the sprite is wall-aligned
    and sits on a wall of its own sector, or it is under a real ceiling.
    """
    from .texture_frame import sector_index

    owners = list(owners) if owners is not None else sector_index(disk)
    wanted = {int(tile) for tile in tiles}
    out = []
    for index, sprite in enumerate(disk.sprites):
        fields = _fields(sprite)
        cstat = int(fields["cstat"])
        if cstat & 32768:
            continue
        if wanted:
            if int(fields["picnum"]) not in wanted:
                continue
        elif int(fields["shade"]) > int(max_shade):
            continue
        sector_id = int(fields["sector"])
        if not int(_fields(disk.sectors[sector_id])["ceiling_stat"]) & 1:
            continue
        if not cstat & SPRITE_WALL_ALIGNED:
            out.append(f"sprite {index} (tile {fields['picnum']}) hangs under "
                       f"an open sky with nothing over it")
            continue
        if not _touches_a_wall(disk, sector_id, (int(fields["x"]),
                                                 int(fields["y"]))):
            out.append(f"sprite {index} (tile {fields['picnum']}) is "
                       f"wall-aligned but stands on no wall of sector "
                       f"{sector_id}")
    return out


def _touches_a_wall(disk: Any, sector_id: int, point, slack: int = 64) -> bool:
    fields = _fields(disk.sectors[sector_id])
    start = int(fields["wall_ptr"])
    for wall_id in range(start, start + int(fields["wall_count"])):
        here = _fields(disk.walls[wall_id])
        nxt = _fields(disk.walls[int(here["point2"])])
        ax, ay = int(here["x"]), int(here["y"])
        bx, by = int(nxt["x"]), int(nxt["y"])
        dx, dy = bx - ax, by - ay
        span = dx * dx + dy * dy
        if not span:
            continue
        t = ((point[0] - ax) * dx + (point[1] - ay) * dy) / span
        t = max(0.0, min(1.0, t))
        near = (ax + dx * t, ay + dy * t)
        if math.hypot(point[0] - near[0], point[1] - near[1]) <= slack:
            return True
    return False


def sky_faults(disk: Any, *, owners: Sequence[int] | None = None) -> list[str]:
    """One connected outdoor space wears ONE sky (owner, W4).

    Measured, and it is a law rather than a tendency: across the 43 campaign
    maps, **271 of 271 connected outdoor regions carry exactly one sky
    picnum**, with no exception at any size. A seam between two skies reads as
    a crack in the sky, which is what the owner saw where DWE3M10's 3678 met
    E3M1's 3491.

    The horizon counts: its parallaxed FLOOR is a sky surface like any other.
    This is also the reader side -- run on an original, a non-empty answer is
    a finding about that map.
    """
    from .texture_frame import sector_index

    owners = list(owners) if owners is not None else sector_index(disk)
    outdoor = [i for i, sec in enumerate(disk.sectors)
               if int(_fields(sec)["ceiling_stat"]) & 1]
    graph: dict[int, set] = {}
    for wall_id, wall in enumerate(disk.walls):
        there = int(_fields(wall)["next_sector"])
        if there < 0:
            continue
        here = owners[wall_id]
        if here in outdoor and there in outdoor:
            graph.setdefault(here, set()).add(there)
            graph.setdefault(there, set()).add(here)
    seen: set = set()
    out = []
    for start in outdoor:
        if start in seen:
            continue
        component = [start]
        seen.add(start)
        stack = [start]
        while stack:
            node = stack.pop()
            for nxt in graph.get(node, ()):
                if nxt not in seen:
                    seen.add(nxt)
                    stack.append(nxt)
                    component.append(nxt)
        skies: dict[int, int] = {}
        for member in component:
            fields = _fields(disk.sectors[member])
            skies[int(fields["ceiling_picnum"])] = \
                skies.get(int(fields["ceiling_picnum"]), 0) + 1
            if int(fields["floor_stat"]) & 1:
                skies[int(fields["floor_picnum"])] = \
                    skies.get(int(fields["floor_picnum"]), 0) + 1
        if len(skies) > 1:
            out.append(f"one outdoor space of {len(component)} sectors wears "
                       f"{len(skies)} skies: "
                       f"{sorted(skies.items(), key=lambda kv: -kv[1])} -- "
                       f"271 of 271 campaign regions wear exactly one")
    return out


def circuit_faults(disk: Any, circuit: Iterable[dict], surfaces: dict, *,
                   start_sector: int | None = None,
                   reachable: Iterable[int] | None = None) -> list[str]:
    """Every built leg of a circuit is reachable, in order, from the start.

    A leg is a sequence of SURFACE IDS -- "the avenue between Theatre Row and
    Market Street" -- because a coordinate does not survive a re-solve and a
    surface does. `surfaces` maps a surface id to the sectors that realise it;
    `reachable` is the set the conditional graph floods at rest.

    Three questions, and each fails differently. A leg naming a surface the
    level does not have is a leg with nothing to stand on. A leg whose
    surfaces are not in the reachable set is a leg a body cannot get to. And
    two consecutive legs with no reachable surface between them are a circuit
    that is not one.
    """
    reached = set(reachable) if reachable is not None else None
    out = []
    previous = None
    for index, leg in enumerate(circuit):
        if not leg.get("built", True):
            continue
        named = list(leg.get("surfaces", ()))
        if not named:
            out.append(f"leg {index} ({leg['leg']!r}) names no surface")
            continue
        missing = [name for name in named if not surfaces.get(name)]
        if missing:
            out.append(f"leg {index} ({leg['leg']!r}) names {missing}, which "
                       f"this level does not have")
            continue
        if reached is not None:
            unreached = [name for name in named
                         if not (set(surfaces[name]) & reached)]
            if unreached:
                out.append(f"leg {index} ({leg['leg']!r}): {unreached} is "
                           f"built and not reachable at rest")
                continue
        previous = index
    if previous is None and any(leg.get("built", True) for leg in circuit):
        out.append("no leg of the circuit is standing")
    return out


# ---------------------------------------------------------------------------
# the owner's second walk (2026-09-03): eight findings, as readers
# ---------------------------------------------------------------------------

#: THE CAMPAIGN'S Z-MOTION DOOR, measured over 1231 type-600 sectors in 43
#: maps: the long side runs 768 to 2048 across the middle half with a median
#: of 1024, and the short side is 256 on 339 of them, the commonest by a
#: distance. E3M1's own six (s52, s54, s58, s59, s60, s114) are 256 to 1024
#: long, 256 thick except s114's 128, CLOSED at rest -- ceiling on floor, all
#: six -- and carry NO masked record between them.
DOOR_WIDTH_ENVELOPE = (768, 2048)
DOOR_THICKNESS = 256
#: What one opens to. E3M1's four that move travel 16384, 17408, 18432 and
#: 22528; the campaign's median is 16384. A door opens to its LINTEL and never
#: to the roof.
DOOR_TRAVEL_ENVELOPE = (16384, 30720)

#: A ONE-SIDED OUTDOOR RECORD TAKES ITS PIECE'S FIELD, and by the same offset
#: the kerb does. Over the campaign's 5320 such records the median delta from
#: the floor shade of the piece they stand on is **+6**, quartiles -3 to +15.75
#: -- the same +6 the kerb census gave. E3M1's own 122 read a median 0, with
#: 32% of them exactly 0, and it is the outlier here as it is on the shade
#: step.
FACADE_SHADE_OFFSET = 6
FACADE_SHADE_QUARTILES = (-3, 16)

#: `triggers.cpp:102-104`: a sprite sends only if the state it is entering has
#: its bit set. Neither bit, no message, whatever the tx says.
TRIGGER_ON, TRIGGER_OFF = "trigger_on", "trigger_off"
#: How far a standing body can reach to press something.
USE_RANGE = 1024 + 512


def door_envelope_faults(disk: Any, *, door_type: int = 600,
                         owners: Sequence[int] | None = None) -> list[str]:
    """A door is a door-sized sector, shut at rest, that opens to its lintel.

    The owner's W5. Nine of them were 4096 x 1024 sectors standing OPEN at
    rest with 33920 of clear -- the whole facade lifting, not a door -- where
    every one of E3M1's six is closed with its ceiling on its floor, 256 to
    1024 long and 256 thick.
    """
    from .texture_frame import sector_index

    owners = list(owners) if owners is not None else sector_index(disk)
    low, high = DOOR_WIDTH_ENVELOPE
    out = []
    for index, sector in enumerate(disk.sectors):
        fields = _fields(sector)
        if int(fields["type"]) != int(door_type):
            continue
        start = int(fields["wall_ptr"])
        count = int(fields["wall_count"])
        points = [(int(_fields(disk.walls[w])["x"]),
                   int(_fields(disk.walls[w])["y"]))
                  for w in range(start, start + count)]
        span_x = max(p[0] for p in points) - min(p[0] for p in points)
        span_y = max(p[1] for p in points) - min(p[1] for p in points)
        long_side, short_side = max(span_x, span_y), min(span_x, span_y)
        if not low <= long_side <= high:
            out.append(f"sector {index}: a door {long_side} across is outside "
                       f"the campaign's {low}-{high}")
        if short_side > DOOR_THICKNESS * 2:
            out.append(f"sector {index}: a door {short_side} thick; the "
                       f"campaign's commonest is {DOOR_THICKNESS}")
        if int(fields["ceiling_z"]) != int(fields["floor_z"]):
            out.append(f"sector {index}: a door standing open at rest, "
                       f"{int(fields['floor_z']) - int(fields['ceiling_z'])} "
                       f"of clear; all six of E3M1's are shut")
        holder = getattr(sector, "extra", None)
        if holder is None:
            out.append(f"sector {index}: a door with no XSECTOR opens nowhere")
            continue
        travel = abs(int(holder.fields.get("off_ceiling_z", 0))
                     - int(holder.fields.get("on_ceiling_z", 0)))
        if travel and not (DOOR_TRAVEL_ENVELOPE[0] <= travel
                           <= DOOR_TRAVEL_ENVELOPE[1]):
            out.append(f"sector {index}: it opens {travel}, outside the "
                       f"campaign's {DOOR_TRAVEL_ENVELOPE}")
    return out


def facade_motion_faults(disk: Any, *, facade_tiles: Iterable[int] = (),
                         owners: Sequence[int] | None = None) -> list[str]:
    """A facade never moves. The aperture grammar's own rule, as a reading.

    The band above and beside a mouth belongs to the facade, and a facade
    record carrying a drag flag is the whole building lifting with the door.
    """
    from .motion import flagged_walls
    from .texture_frame import sector_index

    owners = list(owners) if owners is not None else sector_index(disk)
    wanted = {int(tile) for tile in facade_tiles}
    out = []
    for index, sector in enumerate(disk.sectors):
        fields = _fields(sector)
        start = int(fields["wall_ptr"])
        count = int(fields["wall_count"])
        records = range(start, start + count)
        if wanted and not any(int(_fields(disk.walls[w])["picnum"]) in wanted
                              for w in records):
            continue
        moving = sorted(flagged_walls(disk, index))
        if moving:
            out.append(f"sector {index}: {len(moving)} facade record(s) carry "
                       f"a drag flag; a facade does not move")
    return out


def switch_faults(disk: Any, *, use_range: int = USE_RANGE,
                  owners: Sequence[int] | None = None) -> list[str]:
    """A switch that cannot send, or that nobody can reach (W6).

    `triggers.cpp:102-104` gates every message on the send-when bit of the
    state being entered: without `trigger_on` (or `trigger_off` for the way
    back) a tx is a number nobody ever transmits. And a switch out of a
    standing body's reach of a walkable floor is a switch nobody presses --
    the nine in this city sat 5120 above the SHELL's roof.
    """
    from .texture_frame import sector_index

    owners = list(owners) if owners is not None else sector_index(disk)
    out = []
    for index, sprite in enumerate(disk.sprites):
        holder = getattr(sprite, "extra", None)
        if holder is None:
            continue
        tx = int(holder.fields.get("tx_id", 0))
        if not tx:
            continue
        if not (int(holder.fields.get(TRIGGER_ON, 0))
                or int(holder.fields.get(TRIGGER_OFF, 0))):
            out.append(f"sprite {index}: carries tx {tx} and neither "
                       f"{TRIGGER_ON} nor {TRIGGER_OFF}, so by "
                       f"triggers.cpp:102-104 it can never send")
        fields = _fields(sprite)
        sector = int(fields["sector"])
        floor = int(_fields(disk.sectors[sector])["floor_z"])
        above = floor - int(fields["z"])
        if not 0 <= above <= use_range * 8:
            out.append(f"sprite {index}: stands {above} above its sector's "
                       f"floor, which no body reaches")
    return out


def sprite_home_faults(disk: Any) -> list[str]:
    """Every sprite is in the sector its xy is in, at that sector's floor (W8).

    `updatesector` is the engine's own answer to "which sector is this point
    in", and a sprite whose `sector` field disagrees with it is somewhere else
    from where it is drawn to stand.
    """
    out = []
    for index, sprite in enumerate(disk.sprites):
        fields = _fields(sprite)
        point = (int(fields["x"]), int(fields["y"]))
        named = int(fields["sector"])
        found = _sector_at(disk, point)
        if found is None:
            out.append(f"sprite {index} at {point} is in no sector at all")
            continue
        if found != named:
            out.append(f"sprite {index} at {point} says sector {named} and "
                       f"updatesector says {found}")
    return out


def _sector_at(disk: Any, point) -> int | None:
    """`updatesector`, as a reading: which sector contains this point."""
    for index in range(len(disk.sectors)):
        if _point_in_sector(disk, index, point):
            return index
    return None


def _point_in_sector(disk: Any, index: int, point) -> bool:
    fields = _fields(disk.sectors[index])
    start = int(fields["wall_ptr"])
    count = int(fields["wall_count"])
    inside = False
    walk = start
    while walk < start + count:
        loop = []
        first = walk
        while True:
            face = _fields(disk.walls[walk])
            loop.append((int(face["x"]), int(face["y"])))
            walk = int(face["point2"])
            if walk == first:
                walk = first + len(loop)
                break
        if _crosses(loop, point):
            inside = not inside
    return inside


def _crosses(loop, point) -> bool:
    x, y = point
    inside = False
    for index, (ax, ay) in enumerate(loop):
        bx, by = loop[(index + 1) % len(loop)]
        if (ay > y) != (by > y):
            span = (by - ay)
            if span and x < ax + (y - ay) * (bx - ax) / span:
                inside = not inside
    return inside


#: WHICH ANCHOR KINDS A USE ADMITS. `owner_anchors` names 224 tiles and its
#: `kind` IS the role -- 121 wall, 60 sprite, 37 surface, 6 maskwall -- so a
#: gate asks the anchors and never a census. A census says what the campaign
#: happens to do with a tile; an anchor says what the tile IS.
ANCHOR_KIND_FOR_USE = {
    "floor": {"surface"},
    "ceiling": {"surface"},
    "wall": {"wall", "maskwall"},
    "maskwall": {"maskwall", "wall"},
    "sprite": {"sprite"},
}


def tile_uses(disk: Any) -> dict:
    """Every (use, tile) the map needs, with how many records need it."""
    from collections import Counter

    out: Counter = Counter()
    for sector in disk.sectors:
        fields = _fields(sector)
        for role in ("floor", "ceiling"):
            out[(role, int(fields[f"{role}_picnum"]))] += 1
    for wall in disk.walls:
        face = _fields(wall)
        out[("wall", int(face["picnum"]))] += 1
        if int(face["cstat"]) & 16 and int(face["over_picnum"]):
            out[("maskwall", int(face["over_picnum"]))] += 1
    for sprite in disk.sprites:
        out[("sprite", int(_fields(sprite)["picnum"]))] += 1
    return dict(out)


def anchor_role_faults(disk: Any, *, anchors: Any = None,
                       acknowledged: Iterable[tuple] = ()) -> dict:
    """Every tile the map uses, against the role its OWNER ANCHOR gives it.

    Three outcomes, and they are three different things:

    * **matches** -- the anchor's kind admits the use, and nothing is owed.
    * **a fault** -- the anchor gives the tile a kind this use does not admit
      and nobody has recorded why. 379 is a `wall` and E3M1 puts it on top of
      an end wall; that is a real disagreement between the owner's word for a
      tile and the campaign's use of it, and it is a question, not a licence.
    * **unanchored** -- 224 tiles are named and this is not one of them. It
      goes on the NEXT SHEET, never into a guess: a gate that invents a role
      for an unnamed tile is a census wearing an anchor's clothes.

    `acknowledged` is the project's list of conflicts it has taken to the
    owner, as `(use, picnum)` pairs. An acknowledged conflict is reported and
    is not a fault; an unacknowledged one is.
    """
    from .owner_anchors import load_owner_anchors

    anchors = anchors if anchors is not None else load_owner_anchors()
    known = {(str(use), int(tile)) for use, tile in acknowledged}
    faults, unanchored, noted = [], [], []
    for (use, tile), count in sorted(tile_uses(disk).items()):
        anchor = anchors.get(tile)
        if anchor is None:
            unanchored.append({"use": use, "picnum": tile, "records": count})
            continue
        admits = ANCHOR_KIND_FOR_USE.get(use, set())
        if anchor.kind in admits:
            continue
        row = {"use": use, "picnum": tile, "records": count,
               "anchor_kind": anchor.kind, "label": anchor.label_en,
               "binding": anchor.binding or "untested"}
        if (use, tile) in known:
            noted.append(row)
            continue
        faults.append(f"{count} record(s) use {tile} as a {use}; the owner "
                      f"names it a {anchor.kind} -- {anchor.label_en!r} "
                      f"({row['binding']} binding)")
    return {"faults": faults, "unanchored": unanchored, "acknowledged": noted}


def horizontal_tile_faults(disk: Any, *, anchors: Any = None,
                           acknowledged: Iterable[tuple] = ()) -> list[str]:
    """A tile on a floor or a ceiling whose anchor is not a surface (W9).

    The role comes from `owner_anchors`, never from a list of wall tiles
    somebody typed: the first version of this gate carried its own set and
    passed 379 on three roofs and 2490 on twenty-three sea floors, because
    neither was in it.
    """
    found = anchor_role_faults(disk, anchors=anchors,
                               acknowledged=acknowledged)
    return [row for row in found["faults"]
            if " as a floor;" in row or " as a ceiling;" in row]


def mask_partner_faults(disk: Any, *, owners: Sequence[int] | None = None
                        ) -> list[str]:
    """A mask is on BOTH records of a join, or the sentence says one-way (W10).

    A masked record whose partner is not masked is a wall you can see through
    from one side and not the other, and no construct in this project declares
    that.
    """
    from .texture_frame import sector_index

    owners = list(owners) if owners is not None else sector_index(disk)
    out = []
    for wall_id, wall in enumerate(disk.walls):
        face = _fields(wall)
        if not int(face["cstat"]) & 16:
            continue
        partner = int(face.get("next_wall", -1))
        if partner < 0:
            out.append(f"wall {wall_id} is masked and one-sided; a mask needs "
                       f"a partner to be seen through")
            continue
        other = _fields(disk.walls[partner])
        if not int(other["cstat"]) & 16:
            out.append(f"wall {wall_id} is masked and its partner "
                       f"{partner} is not")
        elif int(other["over_picnum"]) != int(face["over_picnum"]):
            out.append(f"wall {wall_id} shows {face['over_picnum']} and its "
                       f"partner {partner} shows {other['over_picnum']}")
    return out


def facade_shade_faults(disk: Any, *, offset: int = FACADE_SHADE_OFFSET,
                        facade_tiles: Iterable[int] = (),
                        owners: Sequence[int] | None = None) -> list[str]:
    """A one-sided outdoor record takes its piece's field (W11).

    Measured over the campaign's 5320 such records: the median delta from the
    floor shade of the piece they stand on is +6, quartiles -3 to +15.75 --
    the same +6 the kerb census gave, which makes it one law and not two.
    E3M1's own 122 read a median 0 and it is the outlier here as it is on the
    shade step.
    """
    from .texture_frame import sector_index

    owners = list(owners) if owners is not None else sector_index(disk)
    wanted = {int(tile) for tile in facade_tiles}
    out = []
    for wall_id, wall in enumerate(disk.walls):
        face = _fields(wall)
        if int(face["next_sector"]) >= 0:
            continue
        if wanted and int(face["picnum"]) not in wanted:
            continue
        here = owners[wall_id]
        sector = _fields(disk.sectors[here])
        if not int(sector["ceiling_stat"]) & 1:
            continue
        want = int(sector["floor_shade"]) + int(offset)
        if int(face["shade"]) != want:
            out.append(f"wall {wall_id} stands on a piece at shade "
                       f"{int(sector['floor_shade'])} and reads "
                       f"{int(face['shade'])}, not {want}")
    return out


def sky_clip_faults(disk: Any, *, lintel_height: int | None = None,
                    owners: Sequence[int] | None = None) -> list[str]:
    """A real ceiling beside the sky clips everything above it (W12).

    `engine.cpp:4688`: the upper wall between two sectors raises `umost` to
    the far ceiling line only when at least ONE of the two ceilings is not
    parallaxed. Sky against sky never clips, whatever the step -- E3M1 has 13
    differing sky|sky pairs and no visible cut. So what an outdoor opening may
    have is a LINTEL over a door-width mouth, and what it may not have is a
    roof-height slab across a facade's width.
    """
    from .texture_frame import sector_index

    owners = list(owners) if owners is not None else sector_index(disk)
    out = []
    for wall_id, wall in enumerate(disk.walls):
        face = _fields(wall)
        there = int(face["next_sector"])
        if there < 0:
            continue
        here = owners[wall_id]
        a, b = _fields(disk.sectors[here]), _fields(disk.sectors[there])
        if not int(b["ceiling_stat"]) & 1:
            continue
        if int(a["ceiling_stat"]) & 1:
            continue
        clear = int(a["floor_z"]) - int(a["ceiling_z"])
        if lintel_height is not None and clear <= int(lintel_height):
            continue
        out.append(f"wall {wall_id}: sector {here} has a real ceiling "
                   f"{clear} above its floor and faces the sky in {there}, "
                   f"so it clips everything above its line behind it")
    return out


def prop_role_faults(disk: Any, *, anchors: Any = None,
                     acknowledged: Iterable[tuple] = (),
                     owners: Sequence[int] | None = None) -> list[str]:
    """A prop's tile is a sprite, and it is placed on something (W7).

    Two questions, each with its own source. THE ROLE comes from
    `owner_anchors`: tile 510 was chosen for being drawn bright and the owner
    names it a `wall` -- "metal plate" -- so it was never a prop at all. THE
    PLACEMENT comes from the sprite itself: a wall-aligned sprite belongs on a
    ONE-SIDED record and never on a red wall between two street pieces, and a
    sprite that hangs belongs under a real ceiling.
    """
    from .texture_frame import sector_index

    owners = list(owners) if owners is not None else sector_index(disk)
    found = anchor_role_faults(disk, anchors=anchors,
                               acknowledged=acknowledged)
    out = [row for row in found["faults"] if " as a sprite;" in row]
    for index, sprite in enumerate(disk.sprites):
        fields = _fields(sprite)
        sector = _fields(disk.sectors[int(fields["sector"])])
        cstat = int(fields["cstat"])
        if cstat & 16 and not _touches_a_solid(
                disk, int(fields["sector"]),
                (int(fields["x"]), int(fields["y"]))):
            out.append(f"sprite {index}: tile {fields['picnum']} is "
                       f"wall-aligned and the record it stands on is a "
                       f"portal, not a wall")
        if (not cstat & 16 and int(fields["z"]) < int(sector["floor_z"])
                and int(sector["ceiling_stat"]) & 1):
            out.append(f"sprite {index}: tile {fields['picnum']} hangs above "
                       f"its floor and the sector's ceiling is the sky")
    return out


def _touches_a_solid(disk: Any, sector_id: int, point, slack: int = 64) -> bool:
    """Is the nearest record of this sector a one-sided one?"""
    fields = _fields(disk.sectors[sector_id])
    start = int(fields["wall_ptr"])
    best = None
    for wall_id in range(start, start + int(fields["wall_count"])):
        here = _fields(disk.walls[wall_id])
        nxt = _fields(disk.walls[int(here["point2"])])
        ax, ay = int(here["x"]), int(here["y"])
        dx, dy = int(nxt["x"]) - ax, int(nxt["y"]) - ay
        span = dx * dx + dy * dy
        if not span:
            continue
        share = max(0.0, min(1.0, ((point[0] - ax) * dx
                                   + (point[1] - ay) * dy) / span))
        near = (ax + dx * share, ay + dy * share)
        distance = math.hypot(point[0] - near[0], point[1] - near[1])
        if best is None or distance < best[0]:
            best = (distance, int(here["next_sector"]) < 0)
    return bool(best and best[0] <= slack and best[1])


def shadow_fits_faults(disk: Any, masses: Iterable[Any]) -> list[str]:
    """The shadow's near edge shares vertices with the building it falls from.

    W11's second half. A shadow is cast from a mass's footprint, and if that
    footprint is not the building's own outline the shadow starts somewhere
    the building is not. Gated by VERTEX IDENTITY, exactly: every corner the
    mass casts from must be a vertex of the built map.
    """
    built = {(int(_fields(wall)["x"]), int(_fields(wall)["y"]))
             for wall in disk.walls}
    out = []
    for mass in masses:
        for point in getattr(mass, "outline", ()):
            spot = (int(point[0]), int(point[1]))
            if spot not in built:
                out.append(f"{getattr(mass, 'mass_id', mass)}: casts from "
                           f"{spot}, which is not a vertex of the map -- the "
                           f"shadow does not start at the building")
    return out
