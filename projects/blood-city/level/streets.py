"""Give every street run its anatomy: pavement, carriageway, kerb.

The district street is one open region at one level wearing one tile, which
is a large part of why the city reads as empty even where it is dense -- the
eye has nothing to follow along it. `bloodmap.street` carries the measured
grammar (E3M1: tile 4 over tile 352, a 2048 kerb, a 2048 pavement band) and
this module applies it to Gravesend's own circulation graph.

Two decisions worth stating, because both could have gone the other way.

**The pavement keeps the district's tile; only the roadway is retiled.** The
measured law is about the SPLIT -- that a carriageway differs from the
pavement and sits below it -- not about tile 4 specifically. Each district's
ground tile is its own register, set from its facade material, and flattening
all four to E3M1's would trade a real difference for a borrowed one.

**The roadway drops; the pavement does not rise.** Buildings, plazas,
forecourts and yards all stand at grade. Raising the pavement to make the
kerb would put a step down into every shop door in the city; lowering the
carriageway leaves all of that alone and is what a street actually looks
like.

A run whose carriageway would be narrower than a road stays pavement end to
end -- the five 3072 lanes -- which is the correct reading of a lane, not a
failure to build one.
"""

from __future__ import annotations

import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[3]))
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

from bloodmap.levelprog import RECT_FACES, Frame
from bloodmap.street import (
    KERB_RISE, MIN_CARRIAGEWAY, ROADWAY_TILE, Run, carriageway, kerb_junction,
    lamp_slots, runs_from_plan, sidewalk_for,
)

#: The same face map the rest of the skeleton uses: name -> outline
#: edge index, for a rectangular room.
COMPASS = dict(zip(RECT_FACES, range(4)))


def _overlaps(a, b) -> bool:
    return not (a[2] <= b[0] or b[2] <= a[0] or a[3] <= b[1] or b[3] <= a[1])


def _clip(rect, bounds, *, margin: int):
    """Clip a carriageway into its district, keeping pavement all round.

    The district seams run down street centrelines, so a run along one has
    half its width in the neighbour. Clipping to the bounds exactly would put
    the road's edge ON the street's outer wall, and two coincident
    same-direction segments are not a portal -- the compiler says so. A
    margin keeps a strip of pavement between the carriageway and every
    boundary, which is what a kerb needs anyway: something to stand on.
    """
    x0 = max(rect[0], bounds[0] + margin)
    y0 = max(rect[1], bounds[1] + margin)
    x1 = min(rect[2], bounds[2] - margin)
    y1 = min(rect[3], bounds[3] - margin)
    if x1 - x0 < 1024 or y1 - y0 < 1024:
        return None
    return (x0, y0, x1, y1)


def _rooms_under(node) -> list:
    """Every room in this subtree, however deeply nested."""
    from bloodmap.levelprog import Room

    out = []
    stack = list(getattr(node, "children", ()))
    while stack:
        item = stack.pop()
        if isinstance(item, Room):
            out.append(item)
        stack.extend(getattr(item, "children", ()))
    return out


def _world_box(room):
    """A room's bounding box in world units.

    `Room.world_outline` already composes the frame chain, which is the only
    correct way to ask where a nested room actually is -- a district's frame
    lives on its street, so a room's own outline says nothing on its own.
    """
    try:
        outline = room.world_outline()
    except Exception:
        return None
    if not outline:
        return None
    xs = [int(point[0]) for point in outline]
    ys = [int(point[1]) for point in outline]
    return (min(xs), min(ys), max(xs), max(ys))


def _subtract(rect, taken, *, least: int = 1024):
    """`rect` minus every rectangle already laid, as axis-aligned pieces.

    Two carriageways CROSS at a junction, which is right for a street and
    illegal for geometry: the compiler refuses two independent regions that
    overlap. So the crossing belongs to whichever road was laid first and the
    second road arrives at it in two pieces, which is exactly what a side
    street does.

    A guillotine split is enough here because every rectangle is axis
    aligned: cut the survivor into the strips left of, right of, below and
    above the obstacle, and recurse on each.
    """
    pieces = [rect]
    for other in taken:
        out = []
        for piece in pieces:
            if not _overlaps(piece, other):
                out.append(piece)
                continue
            x0, y0, x1, y1 = piece
            ox0, oy0, ox1, oy1 = other
            for candidate in ((x0, y0, min(x1, ox0), y1),
                              (max(x0, ox1), y0, x1, y1),
                              (max(x0, ox0), y0, min(x1, ox1), min(y1, oy0)),
                              (max(x0, ox0), max(y0, oy1), min(x1, ox1), y1)):
                if (candidate[2] - candidate[0] >= least
                        and candidate[3] - candidate[1] >= least):
                    out.append(candidate)
        pieces = out
    return pieces


def plan_runs(data, widths, *, unit: int = 1024) -> list[Run]:
    return runs_from_plan(data["nodes"], data["edges"], widths, unit=unit)


def lay(city, data, widths, district_bounds, streets, district_of, *,
        grade: int, street_sky: int, blocks_by_district, unit: int = 1024,
        rise: int = KERB_RISE):
    """Carve a carriageway out of each street run and drop it by a kerb.

    Returns a report: what was laid, what was left as pavement, and every
    run that was refused with the reason, so a run silently missing its road
    is impossible.
    """
    runs = plan_runs(data, widths, unit=unit)
    city_bounds = (min(b[0] for b in district_bounds.values()),
                   min(b[1] for b in district_bounds.values()),
                   max(b[2] for b in district_bounds.values()),
                   max(b[3] for b in district_bounds.values()))
    laid, pavement, refused, kerbs, slots = [], [], [], [], []
    #: Every carriageway rectangle already committed, so a later run can be
    #: cut around the junctions it crosses -- SEEDED with everything the
    #: street has already given away. A district street is carved for its
    #: blocks, its light pools, the grate kerb, market furniture and every
    #: venue threshold, and each of those is a claim the road must yield to.
    #: The pavement was there first.
    taken: list[tuple[int, int, int, int]] = []
    for name, assembly in district_of.items():
        street_room = streets.get(name)
        for room in _rooms_under(assembly):
            if room is street_room:
                continue
            box = _world_box(room)
            if box is not None:
                taken.append(box)
        bounds = district_bounds.get(name)
        if bounds is None or street_room is None:
            continue
        for hole in getattr(street_room, "holes", ()):
            xs = [point[0] + bounds[0] for point in hole]
            ys = [point[1] + bounds[1] for point in hole]
            taken.append((min(xs), min(ys), max(xs), max(ys)))

    for run in runs:
        road = carriageway(run)
        if road is None:
            pavement.append({"run": run.name, "width": run.width,
                             "why": "narrower than a carriageway; a lane"})
            continue
        if run.district not in district_bounds:
            refused.append({"run": run.name,
                            "why": f"district {run.district!r} has no bounds"})
            continue
        #: NOT clipped to the run's own district. Gravesend's district seams
        #: are drawn down street CENTRELINES, so a main street belongs half
        #: to each side of it -- clipping to one district leaves half a
        #: carriageway, and taking a pavement off that leaves nothing, which
        #: is why eight of thirteen runs came back unroaded on the first
        #: attempt. The seam is bookkeeping; the road is geometry. A piece is
        #: carved out of EVERY district street it crosses and the room is
        #: parented to the district the plan says owns the run.
        clipped = _clip(road, district_bounds[run.district],
                        margin=sidewalk_for(run.width))
        seam = ("straddles a district seam: Gravesend draws its seams down "
                "street CENTRELINES, so half this run belongs to each side "
                "and neither half is wide enough for a carriageway plus its "
                "pavements. Needs paired half-roads joined across the seam")
        if clipped is None:
            refused.append({"run": run.name, "why": seam})
            continue
        #: The minimum applies to what SURVIVES the clip, not to what the run
        #: asked for. A 7168 avenue clipped to 1280 is not a narrow road, it
        #: is the sliver left over from a seam, and laying it would put a
        #: kerb round a strip too thin to drive a cart down.
        if min(clipped[2] - clipped[0], clipped[3] - clipped[1]) < MIN_CARRIAGEWAY:
            refused.append({"run": run.name, "why": seam})
            continue
        #: A carriageway must not run through a building. The plan puts runs
        #: between blocks, so an overlap means the plan and the massing
        #: disagree -- worth reporting, never worth silently trimming.
        hit = [block["id"]
               for blocks in blocks_by_district.values() for block in blocks
               if _overlaps(clipped, tuple(int(v * unit) for v in block["rect"]))]
        if hit:
            refused.append({"run": run.name,
                            "why": f"would run through {', '.join(hit)}"})
            continue

        #: Inflated, so the road keeps a strip of PAVEMENT between itself
        #: and everything else rather than sharing an edge with it. Two
        #: rooms that share a boundary must be a portal or be apart; a road
        #: running flush against a boardwalk is neither, and a one-unit gap
        #: would only trade the error for a sliver. A kerb needs something to
        #: stand on anyway.
        margin = sidewalk_for(run.width)

        def _free(rect):
            return _subtract(rect, [(box[0] - margin, box[1] - margin,
                                     box[2] + margin, box[3] + margin)
                                    for box in taken])

        #: One piece at a time, each yielding to the ones already committed
        #: -- including the earlier pieces of this same run. `_subtract`
        #: returns a tiling of the remainder, and a tiling's pieces share
        #: edges with each other, which is the same coincidence problem in
        #: miniature.
        pieces = []
        for _ in range(4):
            free = _free(clipped)
            if not free:
                break
            piece = max(free, key=lambda r: (r[2] - r[0]) * (r[3] - r[1]))
            #: and it has to still BE a road after everything it yielded to.
            if min(piece[2] - piece[0],
                   piece[3] - piece[1]) < MIN_CARRIAGEWAY:
                break
            pieces.append(piece)
            taken.append(piece)
        if not pieces:
            refused.append({"run": run.name,
                            "why": "wholly inside carriageways already laid"})
            continue

        for index, piece in enumerate(pieces):
            #: A room placed in a street's hole must match that hole exactly
            #: -- the compiler exempts a region whose outline IS one of
            #: another's holes, and nothing weaker. A seam-spanning
            #: carriageway cannot satisfy that for two streets at once, so it
            #: is split AT the seam into one room per district and the two
            #: halves are joined to each other across it. The road is
            #: continuous; only its bookkeeping has a join in it.
            halves = [(run.district, piece)] if streets.get(run.district) else []
            if not halves:
                refused.append({"run": run.name,
                                "why": "crosses no district street"})
                continue
            suffix = "" if len(pieces) == 1 else f"_{index}"
            built = []
            for half, (name, (x0, y0, x1, y1)) in enumerate(halves):
                street_bounds = district_bounds[name]
                sx0, sy0 = street_bounds[0], street_bounds[1]
                streets[name].carve([(x0 - sx0, y0 - sy0), (x1 - sx0, y0 - sy0),
                                     (x1 - sx0, y1 - sy0), (x0 - sx0, y1 - sy0)])
                tail = suffix if len(halves) == 1 else f"{suffix}_{name}"
                road_room = district_of[name].room(
                    f"roadway_{run.name}{tail}",
                    [(0, 0), (x1 - x0, 0), (x1 - x0, y1 - y0), (0, y1 - y0)],
                    role="exterior", faces=dict(COMPASS),
                    frame=Frame(int(x0), int(y0)),
                    note=(f"{run.name}: the carriageway, {rise} below the "
                          f"pavement -- E3M1's kerb, measured on 22 of 22 "
                          f"shared walls"),
                    intent={"kind": "roadway", "run": run.name,
                            "district": name},
                )
                road_room.surfaces(floor_picnum=ROADWAY_TILE,
                                   floor_z=grade + rise,
                                   clear_height=street_sky - rise)
                for face in COMPASS:
                    city.connect(
                        road_room.face(face), streets[name].face("north"),
                        connection_id=(f"connection:{run.name}{tail}"
                                       f"_kerb_{face}"))
                built.append((name, road_room, (x0, y0, x1, y1)))
                laid.append({"run": run.name, "district": name,
                             "rect": (x0, y0, x1, y1), "width": run.width,
                             "sidewalk": sidewalk_for(run.width),
                             "carriageway": min(x1 - x0, y1 - y0),
                             "piece": index, "of": len(pieces)})
            #: and the halves to each other, so the carriageway is one
            #: walkable surface across the seam.
            for (name_a, room_a, box_a), (name_b, room_b, box_b) in zip(
                    built, built[1:]):
                vertical = abs(box_a[1] - box_b[1]) >= abs(box_a[0] - box_b[0])
                if vertical:
                    lower, upper = ((room_a, room_b) if box_a[1] < box_b[1]
                                    else (room_b, room_a))
                    city.connect(lower.face("south"), upper.face("north"),
                                 connection_id=(f"connection:{run.name}"
                                                f"{suffix}_seam"))
                else:
                    left, right = ((room_a, room_b) if box_a[0] < box_b[0]
                                   else (room_b, room_a))
                    city.connect(left.face("east"), right.face("west"),
                                 connection_id=(f"connection:{run.name}"
                                                f"{suffix}_seam"))
        kerbs.append(kerb_junction(run))
        slots.extend(slot.as_json() for slot in lamp_slots(run))

    return {"runs": len(runs), "laid": laid, "pavement": pavement,
            "refused": refused, "kerbs": kerbs, "lamp_slots": slots}
