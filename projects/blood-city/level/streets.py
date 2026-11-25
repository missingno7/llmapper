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
    KERB_RISE, MIN_CARRIAGEWAY, ROADWAY_TILE, SIDEWALK_NARROW, Run,
    carriageway, kerb_junction, lamp_slots, runs_from_plan, sidewalk_for,
)

#: The same face map the rest of the skeleton uses: name -> outline
#: edge index, for a rectangular room.
COMPASS = dict(zip(RECT_FACES, range(4)))

#: How far from the kerb's edge a lamp stands. DWE3M1's 26 outdoor lamps
#: (tile 640): median 512, the nearer half 128 to 256. Half the pavement,
#: which is what this used, put a lamp 1,024 in on a wide pavement: in the
#: middle of the walk, in front of a shop window (owner, 2026-11-18: "lamps
#: are also placed a little bit weirdly around the town").
LAMP_KERB = 512


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


#: What a carriageway keeps between itself and a district seam it runs
#: ALONG, and the least it may be and still be a lane: a body is 600 across.
CENTRE_STRIP = 256
HALF_LANE = 1280
#: The paved band left where a carriageway meets a seam END-ON, or another
#: run's carriageway: a crossing, a pavement's width, not a line.  The first
#: build left `CENTRE_STRIP` there too and a blind reviewer read every one as
#: "stray strips ... a mistake rather than a design".
CROSSING = 1024
#: The owner's kerb tile (owner-anchors, picnum 6).
KERB_TILE = 6


def _clip_seams(rect, bounds, city_bounds, *, seam: int, edge: int,
                end: int | None = None, along: int | None = None):
    """Clip a carriageway into one district.

    A side of the district that is the city's own edge keeps a pavement
    (`edge`) between the road and the wall.  A side that is a seam with
    another district keeps `seam`; on the axis the run travels (`along`, 0
    for x and 1 for y) it keeps `end` instead, which is half a crossing.
    """
    out = []
    for index, (low, high) in enumerate(((rect[0], rect[2]),
                                         (rect[1], rect[3]))):
        b0, b1 = bounds[index], bounds[index + 2]
        c0, c1 = city_bounds[index], city_bounds[index + 2]
        gap = end if (end is not None and index == along) else seam
        lo = max(low, b0 + (edge if b0 <= c0 else gap))
        hi = min(high, b1 - (edge if b1 >= c1 else gap))
        out.append((lo, hi))
    (x0, x1), (y0, y1) = out
    if x1 - x0 < 1024 or y1 - y0 < 1024:
        return None
    return (int(x0), int(y0), int(x1), int(y1))


def _clear_rects(rect, obstacles, *, along: int, min_across: int,
                 min_along: int):
    """Every maximal clear rectangle of `rect`, longest along the run first.

    `_subtract` tiles what is left with a guillotine cut, and a tiling is not
    the same as the clear space: an obstacle poking into one side of a street
    leaves a full-width stretch beyond it that no tile of the guillotine
    covers.  A road wants that stretch.  So: every band across the street
    bounded by the street's own edges or an obstacle's, and along each band
    every stretch no obstacle enters.
    """
    across = 1 - along
    lo, hi = rect[across], rect[across + 2]
    start, stop = rect[along], rect[along + 2]
    hits = [o for o in obstacles if _overlaps(rect, o)]
    lows = sorted({lo} | {min(hi, max(lo, o[across + 2])) for o in hits})
    highs = sorted({hi} | {min(hi, max(lo, o[across])) for o in hits})
    out = set()
    for a in lows:
        for b in highs:
            if b - a < min_across:
                continue
            blocked = sorted((max(start, o[along]), min(stop, o[along + 2]))
                             for o in hits
                             if o[across] < b and o[across + 2] > a)
            cursor = start
            for s, e in blocked + [(stop, stop)]:
                if s - cursor >= min_along:
                    piece = [0, 0, 0, 0]
                    piece[along], piece[along + 2] = cursor, s
                    piece[across], piece[across + 2] = a, b
                    out.add(tuple(int(v) for v in piece))
                cursor = max(cursor, e)
    return sorted(out, key=lambda r: (-(r[along + 2] - r[along]),
                                      -(r[across + 2] - r[across]),
                                      r[0], r[1]))


def _intersection(a, b):
    x0, y0 = max(a[0], b[0]), max(a[1], b[1])
    x1, y1 = min(a[2], b[2]), min(a[3], b[3])
    if x1 <= x0 or y1 <= y0:
        return None
    return (int(x0), int(y0), int(x1), int(y1))


def _area2(points) -> int:
    return sum(points[i][0] * points[(i + 1) % len(points)][1]
               - points[(i + 1) % len(points)][0] * points[i][1]
               for i in range(len(points)))


#: How far past its end nodes a run's carriageway reaches: a junction's
#: half-depth, so whichever road is laid first owns the junction's square.
JUNCTION = 2048

#: A part of a carriageway thinner than this on one side of a seam is not a
#: sector worth having; the road gives it up and stops at the seam.
SLIVER = 512


def _trim_slivers(rect, district_bounds):
    """Pull a road's edge back to a seam it only just crosses."""
    x0, y0, x1, y1 = rect
    for bounds in district_bounds.values():
        for line in (bounds[0], bounds[2]):
            if x0 < line < x1:
                if line - x0 < SLIVER:
                    x0 = line
                elif x1 - line < SLIVER:
                    x1 = line
        for line in (bounds[1], bounds[3]):
            if y0 < line < y1:
                if line - y0 < SLIVER:
                    y0 = line
                elif y1 - line < SLIVER:
                    y1 = line
    return (int(x0), int(y0), int(x1), int(y1))


def _merge_collinear(segments):
    """Join end-to-end axis-aligned segments into the longest stretches."""
    out = []
    for first, second in sorted(tuple(sorted(pair)) for pair in segments):
        if out:
            a, b = out[-1]
            same_line = ((a[0] == b[0] == first[0] == second[0])
                         or (a[1] == b[1] == first[1] == second[1]))
            if same_line and b == first:
                out[-1] = (a, second)
                continue
        out.append((first, second))
    return out


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
        rise: int = KERB_RISE, seam_gates: list | None = None):
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

    #: Carriageway pieces already committed, kept apart from `taken`: an
    #: obstacle keeps a pavement's width of clearance, another run's road a
    #: crossing's.
    roads: list[tuple[int, int, int, int]] = []
    #: What each district's street gives up at its own EDGE, in world
    #: coordinates: see `_notch`.
    notches: dict[str, list[tuple[int, int, int, int]]] = {}
    #: Every part laid, for joining across the seams afterwards.
    parts: list[tuple[str, object, tuple[int, int, int, int]]] = []
    #: Parts that are holes inside one street: joined on all four edges.
    interior: set[tuple[int, int, int, int]] = set()

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
        sidewalk = sidewalk_for(run.width)
        along = 0 if run.horizontal else 1
        across = 1 - along
        #: THE ROAD IS GEOMETRY; THE SEAM IS BOOKKEEPING.  Gravesend's district
        #: seams run down its main streets' centrelines, a carriageway was a
        #: hole in one district's street, and a hole may not touch its
        #: street's outline -- so for months no road could cross a seam.
        #: Eight runs were refused; then (2026-11-17, morning) each got two
        #: half-roads either side of a raised strip, which a blind reviewer
        #: read as a mistake; then one road on one side of the seam, which
        #: was not the street the plan drew.
        #:
        #: Now the road is laid where the plan puts it, down the middle, and
        #: where it lies on or across a seam each district gives up its part
        #: as a NOTCH in its street's outline rather than a hole inside it.
        #: The parts are rooms of their own districts, joined to each other
        #: across the seam, and the streets are joined along what is left of
        #: it.  Only the city's own edge keeps a pavement in front of it.
        #: A run ends at a node, which is the CENTRE of a junction, so two
        #: roads that stop at their nodes leave the junction's square to
        #: nobody.  Each run reaches a junction's depth past its ends; the
        #: first road laid takes the square and the others arrive at its
        #: edge.  (The first build kept a paved crossing between any two
        #: roads instead, and a blind reviewer read every junction as "an
        #: error: carts would hit a kerb".)
        reach = list(road)
        reach[along] -= JUNCTION
        reach[along + 2] += JUNCTION
        clipped = _clip_seams(tuple(reach), city_bounds, city_bounds,
                              seam=0, edge=sidewalk)
        if clipped is None:
            refused.append({"run": run.name,
                            "why": "nothing is left inside the city's edge"})
            continue
        #: A carriageway must not run through a building. The plan puts runs
        #: between blocks, so an overlap means the plan and the massing
        #: disagree -- worth reporting, never worth silently trimming.
        hit = sorted({block["id"]
                      for blocks in blocks_by_district.values()
                      for block in blocks
                      if _overlaps(clipped, tuple(int(v * unit)
                                                  for v in block["rect"]))})
        if hit:
            refused.append({"run": run.name,
                            "why": f"would run through {', '.join(hit)}"})
            continue

        #: Inflated, so the road keeps a strip of PAVEMENT between itself
        #: and everything else rather than sharing an edge with it.  The
        #: clearance is the narrow pavement whatever the run affords: a wide
        #: street that passes something standing in it (the church tower
        #: stands in the avenue) narrows its road there rather than losing it.
        def _free(rect):
            return _clear_rects(
                rect,
                [(box[0] - SIDEWALK_NARROW, box[1] - SIDEWALK_NARROW,
                  box[2] + SIDEWALK_NARROW, box[3] + SIDEWALK_NARROW)
                 for box in taken]
                + list(roads),
                along=along, min_across=MIN_CARRIAGEWAY,
                min_along=2 * MIN_CARRIAGEWAY)

        #: One piece at a time, each yielding to the ones already committed.
        #: The LONGEST clear stretch first, not the largest: a road is
        #: continuous before it is wide.
        pieces = []
        for _ in range(6):
            free = _free(clipped)
            if not free:
                break
            piece = free[0]
            piece = _trim_slivers(piece, district_bounds)
            pieces.append(piece)
            roads.append(piece)
        if not pieces:
            refused.append({"run": run.name,
                            "why": "wholly inside carriageways already laid, "
                                   "or what was left was not a road"})
            continue

        for index, piece in enumerate(pieces):
            suffix = "" if len(pieces) == 1 else f"_{index}"
            owners = [(name, _intersection(piece, bounds))
                      for name, bounds in district_bounds.items()
                      if streets.get(name) is not None]
            owners = [(name, part) for name, part in owners if part is not None]
            for name, (x0, y0, x1, y1) in owners:
                bounds = district_bounds[name]
                sx0, sy0 = bounds[0], bounds[1]
                #: whether this part is a notch or a hole is decided at the
                #: end, when every road that might touch it has been laid
                notches.setdefault(name, []).append((x0, y0, x1, y1))
                tag = f"_{name}" if len(owners) > 1 else ""
                road_room = district_of[name].room(
                    f"roadway_{run.name}{tag}{suffix}",
                    [(0, 0), (x1 - x0, 0), (x1 - x0, y1 - y0), (0, y1 - y0)],
                    role="exterior", faces=dict(COMPASS),
                    frame=Frame(int(x0), int(y0)),
                    note=(f"{run.name}: the carriageway, {rise} below the "
                          f"pavement -- E3M1's kerb, measured on 22 of 22 "
                          f"shared walls"),
                    intent={"kind": "roadway", "run": run.name,
                            "district": name},
                )
                #: The kerb's face is drawn from the LOWER side's record,
                #: which is the road's: the owner's kerb tile (6), as E3M1
                #: wears it on the road side of all 13 of its kerb walls.
                road_room.surfaces(floor_picnum=ROADWAY_TILE,
                                   wall_picnum=KERB_TILE,
                                   floor_z=grade + rise,
                                   clear_height=street_sky - rise)
                parts.append((name, road_room, (x0, y0, x1, y1)))
                laid.append({"run": run.name, "district": name,
                             "rect": (x0, y0, x1, y1), "width": run.width,
                             "sidewalk": sidewalk,
                             "carriageway": piece[across + 2] - piece[across],
                             "piece": index, "of": len(pieces),
                             "half": len(owners) > 1})
        kerbs.append(kerb_junction(run))
        slots.extend(slot.as_json()
                     for slot in lamp_slots(
                         run, sidewalk=sidewalk, stagger=True,
                         inset=min(LAMP_KERB, sidewalk // 2)))

    #: ---- the outlines, then every join, from the finished shapes ----------
    from shapely.geometry import box as _box
    from shapely.ops import unary_union
    from bloodmap.levelprog import _compass_edges

    shapes = {}
    for name, street in streets.items():
        bounds = district_bounds.get(name)
        if bounds is None:
            continue
        shape = _box(*bounds)
        #: A part is a NOTCH if it reaches the district's edge, or touches a
        #: part that does; anything else is a hole inside the street.  Two
        #: roads that meet at a junction are one shape, so the question is
        #: asked of each connected group, not of each rectangle.
        cut = []
        pending = list(notches.get(name, ()))
        grown = True
        while grown:
            grown = False
            for rect in list(pending):
                touches_edge = (rect[0] <= bounds[0] or rect[1] <= bounds[1]
                                or rect[2] >= bounds[2] or rect[3] >= bounds[3])
                if touches_edge or any(_box(*rect).touches(_box(*other))
                                       or _box(*rect).intersects(_box(*other))
                                       for other in cut):
                    cut.append(rect)
                    pending.remove(rect)
                    grown = True
        for index, rect in enumerate(pending):
            if any(_box(*rect).intersects(_box(*other))
                   for other in pending[index + 1:]):
                raise ValueError(
                    f"{name}: two carriageways meet inside the street and "
                    f"neither reaches its edge; a street's holes may not "
                    f"share an edge")
            x0, y0, x1, y1 = rect
            sx0, sy0 = bounds[0], bounds[1]
            street.carve([(x0 - sx0, y0 - sy0), (x1 - sx0, y0 - sy0),
                          (x1 - sx0, y1 - sy0), (x0 - sx0, y1 - sy0)])
            interior.add(rect)
        if cut:
            shape = shape.difference(unary_union([_box(*r) for r in cut]))
            if shape.geom_type != "Polygon" or shape.interiors:
                raise ValueError(
                    f"{name}: its carriageways cut the street in two, or "
                    f"left an island; a road may not sever a district")
            ring = [(int(round(x)) - int(bounds[0]),
                     int(round(y)) - int(bounds[1]))
                    for x, y in list(shape.exterior.coords)[:-1]]
            if _area2(ring) < 0:
                ring.reverse()
            street.outline = ring
            #: the compass names follow the new outline; a hole's faces are
            #: resolved through `_hole_faces` and keep their entries
            street.faces = {**{k: v for k, v in street.faces.items()
                               if k in street._hole_faces},
                            **_compass_edges(ring)}
        shapes[name] = shape

    def _segments(a, b):
        both = a.boundary.intersection(b.boundary)
        out = []
        for geom in getattr(both, "geoms", [both]):
            if geom.geom_type != "LineString":
                continue
            points = [(int(round(x)), int(round(y))) for x, y in geom.coords]
            for first, second in zip(points, points[1:]):
                if first != second:
                    out.append((first, second))
        return _merge_collinear(out)

    #: street to street, along what is left of each seam
    if seam_gates is not None:
        names = sorted(shapes)
        for i, left in enumerate(names):
            for right in names[i + 1:]:
                for k, (a, b) in enumerate(_segments(shapes[left],
                                                     shapes[right])):
                    seam_gates.append((
                        f"connection:seam_{left}_{right}_{k}",
                        streets[left].region_id, streets[right].region_id,
                        a, b, 0))
        #: a carriageway part to its own street, and to the part across a seam
        for i, (name, room, rect) in enumerate(parts):
            if rect in interior:
                x0, y0, x1, y1 = rect
                for k, (a, b) in enumerate((((x0, y0), (x1, y0)),
                                            ((x1, y0), (x1, y1)),
                                            ((x1, y1), (x0, y1)),
                                            ((x0, y1), (x0, y0)))):
                    seam_gates.append((
                        f"connection:{room.node_id}_kerb_{k}",
                        room.region_id, streets[name].region_id, a, b, 0))
                continue
            for k, (a, b) in enumerate(_segments(_box(*rect), shapes[name])):
                seam_gates.append((
                    f"connection:{room.node_id}_kerb_{k}",
                    room.region_id, streets[name].region_id, a, b, 0))
            for other_name, other, other_rect in parts[i + 1:]:
                for k, (a, b) in enumerate(_segments(_box(*rect),
                                                     _box(*other_rect))):
                    seam_gates.append((
                        f"connection:{room.node_id}_to_{other.node_id}_{k}",
                        room.region_id, other.region_id, a, b, 0))
            #: ...and across a seam to the neighbouring district's PAVEMENT,
            #: where a part's end lies on the seam with no road beyond it
            for other_name, shape in shapes.items():
                if other_name == name:
                    continue
                for k, (a, b) in enumerate(_segments(_box(*rect), shape)):
                    seam_gates.append((
                        f"connection:{room.node_id}_kerb_{other_name}_{k}",
                        room.region_id, streets[other_name].region_id,
                        a, b, 0))

    return {"runs": len(runs), "laid": laid, "pavement": pavement,
            "refused": refused, "kerbs": kerbs, "lamp_slots": slots}


def _with_vertices(outline, points):
    """`outline` with every point that lies on one of its edges made a vertex."""
    out = []
    count = len(outline)
    for index in range(count):
        a, b = outline[index], outline[(index + 1) % count]
        out.append(a)
        on = []
        for q in set(points):
            if q in (a, b):
                continue
            cross = (b[0] - a[0]) * (q[1] - a[1]) - (b[1] - a[1]) * (q[0] - a[0])
            if cross:
                continue
            dot = (q[0] - a[0]) * (b[0] - a[0]) + (q[1] - a[1]) * (b[1] - a[1])
            if 0 < dot < (b[0] - a[0]) ** 2 + (b[1] - a[1]) ** 2:
                on.append((dot, q))
        out.extend(q for _d, q in sorted(on))
    return out
