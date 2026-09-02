"""The solver's inverse: a city's plan recovered from a finished map.

Decisions section 20 calls this the acid test -- "recover a city's street
graph, islands, blocks and envelopes from an original" -- and marks it
missing. This is it, in the language of `projects/blood-city/level/city_plan.py`:
a graph of nodes and edges whose edges carry a WIDTH CLASS, islands with
bands, blocks with envelopes. **No picnums, no z, no Build units** leave this
module; every extent is in plan units, and `PLAN_UNIT` states the one
conversion, which is the plotting convention the plan file already uses.

What the reader can and cannot recover
======================================

It recovers the graph, the widths and the envelopes. It does NOT recover
districts, roles, venues or names: those are interpretation, they belong to
layer 8, and inventing them here would be putting our vocabulary into the
map's mouth.

The width class is reported twice on purpose. A street has a CARRIAGEWAY (the
road) and a FULL WIDTH (the road plus the islands that flank it), and the two
land in different classes -- E3M1's north-south street is 7.28 pu of
carriageway and 10.78 with its pavements. The plan's classes were written from
one of those and it does not say which, so the reader gives both and the
residual from the nearest class, and says nothing about which is meant.

The residue
===========

* ground on no street, island or area;
* and the number that says what a rectangular schematic costs: every plan
  element is a RECT, and a sector is not. The reader reports each element's
  fill -- the sector area over its own bounding rectangle -- so "the plan
  covers the ground" cannot be claimed by a box drawn round a concave place.
"""

from __future__ import annotations

from collections import defaultdict
from typing import Any, Sequence

from .read_islands import read_islands
from .read_joins import adjacency, street_network, surface_kinds
from .texture_frame import sector_index

#: The plotting convention `city_plan.py` states: 1 plan unit renders at 1024
#: Build units. It is the ONLY conversion in this module, and it is here so
#: that everything else can be a plan unit.
PLAN_UNIT = 1024

#: `city_plan.py`'s width classes, in plan units. Reported as the NEAREST
#: class with its residual, never as the answer: these are Gravesend's
#: vocabulary and E3M1 had no part in choosing them.
WIDTH_CLASSES = {"alley": 2, "lane": 3, "street": 5, "row": 6, "avenue": 7}

#: A rect is a corridor rather than a place when it is this much longer than
#: it is wide. Below it, it is a junction or an open area.
CORRIDOR_RATIO = 2.0
#: Where the call could go either way. A piece in this band is emitted as a
#: `candidate` both ways and left to the selection pass, which is Manifold's
#: rule: do not commit to an interpretation inside a reader.
AMBIGUOUS_LOW, AMBIGUOUS_HIGH = 1.2, 2.5


def _face(item: Any) -> Any:
    return item["fields"] if isinstance(item, dict) else item.fields


def _pu(value: float) -> float:
    return round(float(value) / PLAN_UNIT, 2)


def bbox(level: Any, sector_id: int) -> tuple[int, int, int, int]:
    fields = _face(level.sectors[sector_id])
    start = int(fields["wall_ptr"])
    walls = range(start, start + int(fields["wall_count"]))
    xs = [int(_face(level.walls[w])["x"]) for w in walls]
    ys = [int(_face(level.walls[w])["y"]) for w in walls]
    return min(xs), min(ys), max(xs), max(ys)


def nearest_class(width_pu: float) -> dict[str, Any]:
    name = min(WIDTH_CLASSES, key=lambda key: abs(WIDTH_CLASSES[key] - width_pu))
    return {"nearest": name, "class_pu": WIDTH_CLASSES[name],
            "residual_pu": round(width_pu - WIDTH_CLASSES[name], 2)}


def shape_of(level: Any, sector_id: int) -> dict[str, Any]:
    """One ground sector as a plan rectangle: extent, axis, fill."""
    from .viewplan import sector_area

    x0, y0, x1, y1 = bbox(level, sector_id)
    width, depth = x1 - x0, y1 - y0
    long_side, short_side = max(width, depth), min(width, depth)
    axis = ("x" if width > depth else "y") if long_side else "x"
    rect_area = float(width) * float(depth)
    area = float(sector_area(level, sector_id))
    return {
        "sector": sector_id,
        "rect_pu": [_pu(x0), _pu(y0), _pu(x1), _pu(y1)],
        "extent_pu": [_pu(width), _pu(depth)],
        "axis": axis if long_side >= CORRIDOR_RATIO * short_side else "square",
        "width_pu": _pu(short_side),
        "length_pu": _pu(long_side),
        "fill": round(area / rect_area, 3) if rect_area else 0.0,
    }


def corridors(level: Any, roads: Sequence[int], graph: dict[int, set[int]]
              ) -> list[dict[str, Any]]:
    """Road sectors merged into runs of one axis and one width.

    A street is not a sector. E3M1 cuts its carriageways at shadow boundaries,
    so a corridor is the set of road pieces that share an edge, run the same
    way and are the same width -- which is the thing the plan calls an edge.
    """
    shapes = {index: shape_of(level, index) for index in roads}
    left = set(roads)
    out: list[dict[str, Any]] = []
    while left:
        seed = min(left)
        group, queue = {seed}, [seed]
        while queue:
            current = queue.pop()
            for other in sorted(graph.get(current, ())):
                if other not in left or other in group:
                    continue
                if shapes[other]["axis"] != shapes[current]["axis"]:
                    continue
                if shapes[other]["width_pu"] != shapes[current]["width_pu"]:
                    continue
                group.add(other)
                queue.append(other)
        left -= group
        rects = [bbox(level, index) for index in group]
        x0 = min(r[0] for r in rects); y0 = min(r[1] for r in rects)
        x1 = max(r[2] for r in rects); y1 = max(r[3] for r in rects)
        width, depth = x1 - x0, y1 - y0
        short_side, long_side = min(width, depth), max(width, depth)
        axis = shapes[seed]["axis"]
        ratio = round(long_side / short_side, 2) if short_side else 0.0
        out.append({
            "corridor_id": f"corridor:{len(out):02d}",
            "sectors": sorted(group),
            "axis": axis,
            #: A square piece of road is a JUNCTION -- a place on the plan --
            #: and a long one is an EDGE. The threshold is `CORRIDOR_RATIO`
            #: and it is a judgement: E3M1's west arm is 1.79 long by wide and
            #: could be read either way, so it is emitted as a candidate for
            #: the selection pass rather than decided here.
            "role": "junction" if axis == "square" else "edge",
            "ratio": ratio,
            "ambiguous": bool(AMBIGUOUS_LOW <= ratio <= AMBIGUOUS_HIGH),
            "rect_pu": [_pu(x0), _pu(y0), _pu(x1), _pu(y1)],
            "carriageway_pu": _pu(short_side),
            "length_pu": _pu(long_side),
            "carriageway_class": nearest_class(_pu(short_side)),
        })
    out.sort(key=lambda row: -row["length_pu"])
    for number, row in enumerate(out):
        row["corridor_id"] = f"corridor:{number:02d}"
    return out


#: A flanking island is a BAND only if it runs along a real share of the
#: corridor. Below this it is an open place the street happens to touch --
#: E3M1's s175 is 17 plan units wide and touches three corridors, and
#: counting it as a pavement band made every street in the map an avenue.
BAND_RUN = 0.25


def _flanks(level: Any, corridor: dict[str, Any], islands: Sequence[dict],
            graph: dict[int, set[int]]) -> dict[str, Any]:
    """The islands that run ALONG this corridor, and the band on each side.

    Along, and on a side: the band is the flanking sector's extent
    PERPENDICULAR to the corridor, and it counts only if the sector runs at
    least `BAND_RUN` of the corridor's length. A place the street merely
    touches is reported apart, because it is not a width.
    """
    members = set(corridor["sectors"])
    if corridor["role"] == "junction":
        #: A junction has no width to flank. Everything it touches is a place.
        return {"bands": {"low": [], "high": []},
                "band_low_pu": 0.0, "band_high_pu": 0.0,
                "touched_but_not_a_band": [
                    {"island": island["island_id"], "sector": index,
                     "why": "this piece of road is a junction, not an edge, "
                            "so it has no width for a band to flank"}
                    for island in islands for index in island["sectors"]
                    if graph.get(index, set()) & members]}
    x0, y0, x1, y1 = [value * PLAN_UNIT for value in corridor["rect_pu"]]
    across = 0 if corridor["axis"] == "y" else 1
    along = 1 - across
    lo = (x0, y0)[along]
    hi = (x1, y1)[along]
    span = max(1.0, hi - lo)
    sides: dict[str, list[dict[str, Any]]] = {"low": [], "high": []}
    touched: list[dict[str, Any]] = []
    for island in islands:
        for index in island["sectors"]:
            if not graph.get(index, set()) & members:
                continue
            rect = bbox(level, index)
            run = (min(rect[along + 2], hi) - max(rect[along], lo)) / span
            band = _pu(rect[across + 2] - rect[across])
            shape = shape_of(level, index)
            row = {"island": island["island_id"], "sector": index,
                   "band_pu": band, "runs_along": round(run, 2),
                   "shape": shape["axis"]}
            if run < BAND_RUN:
                touched.append({**row, "why": "runs along less than "
                                              f"{BAND_RUN} of the corridor"})
                continue
            #: A BAND IS A STRIP, and its long side is the corridor's. E3M1's
            #: s175 is 18 by 17 plan units and runs the whole length of two
            #: corridors; counted as a band it made both of them 23 pu wide.
            #: A place a street runs along is still a place.
            if shape["axis"] != corridor["axis"]:
                touched.append({**row, "why": (
                    "not a strip along this corridor: its own shape is "
                    f"{shape['axis']!r}, so it is a place the street runs "
                    f"along rather than a width of it")})
                continue
            middle = (rect[across] + rect[across + 2]) / 2.0
            centre = ((x0, y0)[across] + (x1, y1)[across]) / 2.0
            sides["low" if middle < centre else "high"].append(row)
    return {
        "bands": sides,
        "band_low_pu": max((row["band_pu"] for row in sides["low"]), default=0.0),
        "band_high_pu": max((row["band_pu"] for row in sides["high"]), default=0.0),
        "touched_but_not_a_band": touched,
    }


#: What counts as ground for a frontage: the surfaces a building fronts ONTO.
FRONTAGE_KINDS = frozenset({"road", "pavement", "outdoor_ground", "shore"})


def frontages(level: Any, group: set[int], kinds: dict[int, str],
              owners: Sequence[int], places: dict[int, str]) -> dict[str, set[int]]:
    """Which street each of a mass's sectors fronts onto, by place.

    `places` maps a ground sector to the plan element it belongs to (a
    corridor, an island). A frontage is therefore named after a STREET rather
    than after the sector on the other side of one door, which is what makes
    the cut stable when the shadow cuts a carriageway into four.
    """
    out: dict[str, set[int]] = defaultdict(set)
    for index in sorted(group):
        fields = _face(level.sectors[index])
        start = int(fields["wall_ptr"])
        for wall_id in range(start, start + int(fields["wall_count"])):
            other = int(_face(level.walls[wall_id])["next_sector"])
            if other < 0 or kinds.get(other) not in FRONTAGE_KINDS:
                continue
            out[places.get(other, f"unnamed_ground:{other}")].add(index)
    return dict(out)


def blocks(level: Any, kinds: dict[int, str], graph: dict[int, set[int]],
           places: dict[int, str] | None = None) -> tuple[list, list]:
    """The masses between the streets, cut at their street frontages.

    A connected run of interiors and solid masses is a MASS, and E3M1's
    largest is 123 sectors -- a whole side of the city, because its buildings
    run together through their interiors. `city_plan`'s block is one buildable
    rectangle, so the mass is cut: every sector goes to the frontage it is
    nearest to THROUGH THE MASS ITSELF (a multi-source breadth-first walk from
    the sectors that touch each street), and a block is the part of the mass
    one street serves.

    A sector the walk reaches from two frontages at the same distance is not
    assigned by tie-break -- it is emitted as a `candidate` for the selection
    pass, because which building a shared back room belongs to is exactly the
    kind of question a reader may not decide quietly.

    Returns `(blocks, candidates)`.
    """
    places = dict(places or {})
    inside = {index for index, kind in kinds.items()
              if kind in ("interior", "solid")}
    left = set(inside)
    out: list[dict[str, Any]] = []
    unsure: list[dict[str, Any]] = []
    owners = sector_index(level)
    while left:
        seed = min(left)
        group, queue = {seed}, [seed]
        while queue:
            current = queue.pop()
            for other in sorted(graph.get(current, ())):
                if other in left and other not in group:
                    group.add(other)
                    queue.append(other)
        left -= group

        fronts = frontages(level, group, kinds, owners, places)
        if len(fronts) < 2:
            parts = {(sorted(fronts)[0] if fronts else "no frontage"):
                     sorted(group)}
            ties: dict[int, list[str]] = {}
        else:
            parts, ties = _cut_at_frontages(group, fronts, graph)
        for name, members in sorted(parts.items()):
            if not members:
                continue
            rects = [bbox(level, index) for index in members]
            x0 = min(r[0] for r in rects); y0 = min(r[1] for r in rects)
            x1 = max(r[2] for r in rects); y1 = max(r[3] for r in rects)
            out.append({
                "block_id": f"block:{len(out):02d}",
                "sectors": sorted(members),
                "fronts": name,
                "mass_sectors": len(group),
                "frontages_of_the_mass": sorted(fronts),
                "envelope_pu": [_pu(x1 - x0), _pu(y1 - y0)],
                "rect_pu": [_pu(x0), _pu(y0), _pu(x1), _pu(y1)],
            })
        for index, names in sorted(ties.items()):
            unsure.append({
                "about": f"sector:{index}",
                "readings": sorted(names),
                "why": (f"equally far through the mass from "
                        f"{len(names)} frontages, so which block it belongs "
                        f"to is not decided by the walk"),
            })
    out.sort(key=lambda row: -(row["envelope_pu"][0] * row["envelope_pu"][1]))
    for number, row in enumerate(out):
        row["block_id"] = f"block:{number:02d}"
    return out, unsure


def _cut_at_frontages(group: set[int], fronts: dict[str, set[int]],
                      graph: dict[int, set[int]]):
    """Multi-source breadth-first from each frontage, at once.

    All sources advance a step together, so a sector is claimed by whichever
    frontage reaches it first and a sector reached in the same step by two is
    a tie rather than a race the iteration order wins.
    """
    owner: dict[int, str] = {}
    ties: dict[int, list[str]] = {}
    frontier: dict[str, set[int]] = {name: set(members)
                                     for name, members in fronts.items()}
    for name, members in frontier.items():
        for index in members:
            owner.setdefault(index, name)
    #: A sector on two frontages at once belongs to both from step zero.
    for index in list(owner):
        holders = sorted(name for name, members in fronts.items()
                         if index in members)
        if len(holders) > 1:
            ties[index] = holders
    seen = set(owner)
    while any(frontier.values()):
        reached: dict[int, list[str]] = defaultdict(list)
        for name, members in frontier.items():
            for index in members:
                for other in sorted(graph.get(index, ())):
                    if other in group and other not in seen:
                        reached[other].append(name)
        nxt: dict[str, set[int]] = {name: set() for name in fronts}
        for index, names in sorted(reached.items()):
            unique = sorted(set(names))
            owner[index] = unique[0]
            if len(unique) > 1:
                ties[index] = unique
            seen.add(index)
            for name in unique:
                nxt[name].add(index)
        frontier = nxt
    parts: dict[str, list[int]] = defaultdict(list)
    for index in sorted(group):
        parts[owner.get(index, "no frontage")].append(index)
    return dict(parts), ties


def read_plan(level: Any, kinds: dict[int, str] | None = None, *,
              owners: Sequence[int] | None = None) -> dict[str, Any]:
    owners = list(owners) if owners is not None else sector_index(level)
    graph = adjacency(level, owners)
    network, _ = street_network(level, graph)
    if kinds is None:
        kinds = surface_kinds(level, owners=owners)["kinds"]
    roads = sorted(index for index in network if kinds.get(index) == "road")
    islands = read_islands(level, kinds, owners=owners)["islands"]

    runs = corridors(level, roads, graph)
    for run in runs:
        flanks = _flanks(level, run, islands, graph)
        run["flanks"] = flanks
        full = round(run["carriageway_pu"] + flanks["band_low_pu"]
                     + flanks["band_high_pu"], 2)
        run["full_width_pu"] = full
        run["full_width_class"] = nearest_class(full)

    #: Nodes: a square road piece is a junction; a corridor end that meets
    #: nothing is a terminus. Both are places on the plan, in plan units.
    nodes: dict[str, Any] = {}
    for run in runs:
        x0, y0, x1, y1 = run["rect_pu"]
        for name, point in (("a", (x0, y0)), ("b", (x1, y1))):
            nodes[f"{run['corridor_id']}:{name}"] = list(point)

    edges = [{"corridor": run["corridor_id"],
              "from": f"{run['corridor_id']}:a",
              "to": f"{run['corridor_id']}:b",
              "width_class": run["carriageway_class"]["nearest"],
              "carriageway_pu": run["carriageway_pu"],
              "full_width_pu": run["full_width_pu"],
              "length_pu": run["length_pu"]}
             for run in runs if run["role"] == "edge"]
    junctions = [run for run in runs if run["role"] == "junction"]
    #: Manifold's rule, applied: a piece whose ratio is in the ambiguous band
    #: is kept BOTH ways and resolved by a named pass, not by this reader.
    candidates = [{"about": run["corridor_id"], "sectors": run["sectors"],
                   "ratio": run["ratio"],
                   "readings": ["edge", "junction"],
                   "why": (f"long/short is {run['ratio']}, inside the "
                           f"ambiguous band "
                           f"[{AMBIGUOUS_LOW}, {AMBIGUOUS_HIGH}]")}
                  for run in runs if run["ambiguous"]]

    #: Which plan element each ground sector belongs to, so a frontage is
    #: named after a STREET and not after the sector behind one door.
    places: dict[int, str] = {}
    for run in runs:
        for index in run["sectors"]:
            places[index] = run["corridor_id"]
    for island in islands:
        for index in island["sectors"]:
            places.setdefault(index, island["island_id"])
    built, unsure = blocks(level, kinds, graph, places)
    #: A sector the frontage walk reaches from two streets at once is a
    #: candidate, not a tie-break: which building a shared back room belongs
    #: to is not a reader's to decide quietly.
    candidates += unsure

    claimed = {index for run in runs for index in run["sectors"]}
    claimed |= {index for island in islands for index in island["sectors"]}
    ground = sorted(index for index in network
                    if kinds.get(index) in ("road", "pavement",
                                            "outdoor_ground", "shore"))
    residue = [index for index in ground if index not in claimed]

    shapes = {index: shape_of(level, index) for index in ground}
    fills = sorted(row["fill"] for row in shapes.values())
    return {
        "plan_unit_build": PLAN_UNIT,
        "nodes": nodes,
        "edges": edges,
        "junctions": junctions,
        "candidates": candidates,
        "corridors": runs,
        "islands": [{"island": island["island_id"],
                     "sectors": island["sectors"],
                     "band_pu": sorted({shape_of(level, index)["width_pu"]
                                        for index in island["sectors"]})}
                    for island in islands],
        "blocks": built,
        "ground_sectors": ground,
        "ground_shapes": shapes,
        "rectangular_fill": {
            "median": fills[len(fills) // 2] if fills else 0.0,
            "worst": fills[0] if fills else 0.0,
            "best": fills[-1] if fills else 0.0},
        "residue_sectors": residue,
    }


def summary(result: dict[str, Any]) -> dict[str, Any]:
    ground = len(result["ground_sectors"])
    residue = len(result["residue_sectors"])
    return {
        "corridors": len(result["corridors"]),
        "edges": len(result["edges"]),
        "islands": len(result["islands"]),
        "blocks": len(result["blocks"]),
        "ground_sectors": ground,
        "residue_sectors": residue,
        "residue_percent": round(100.0 * residue / ground, 2) if ground else 0.0,
        "rectangular_fill": result["rectangular_fill"],
    }
