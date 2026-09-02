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
