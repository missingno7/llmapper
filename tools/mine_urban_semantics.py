"""Per-sector urban semantics: what each piece of a city map actually is.

The street classifier answers one question -- where is the street network --
and everything it cannot name gets lumped as "interior".  That lump is where
its known misreadings live: TEDE1M2's covered lanes counted as interiors,
E3M1's saloon and hotel merged into one 113-sector blob through their shared
upstairs, doorways on frontage buildings attributed to no building at all.

This pass labels every sector and groups interiors into *buildings*:

  street            the sky network (from mine_city_norms, with its rules)
  arcade            covered passage at street grade: non-sky, standing-height,
                    touching the street at 2+ separated mouths, shallow
  courtyard         sky pocket off the network (reachable, not street)
  roof              sky, standing above grade, off the network
  interior_ground   non-sky, within one standing of street grade
  interior_upper    non-sky, more than one standing above grade
  underground       non-sky, more than one standing below grade
  scene             unreachable in the optimistic model (backdrops et al.)

Buildings: connected non-street plan area (a raster over the full map)
adjacent to the street; every interior sector is assigned to the building
whose footprint contains it, so enterability can finally be counted PER
BUILDING -- doorways on edge-frontage buildings included, which the
walk-around block census structurally missed.

    python -m tools.mine_urban_semantics TEDE1M2 E3M2 E3M1 E1M4 DWE3M10 \\
        -o projects/blood-city/references/urban-semantics.json --plots DIR

Derived labels; thresholds echoed in the output.
"""

from __future__ import annotations

import argparse
import json
import pathlib
import statistics
from collections import Counter, defaultdict, deque
from typing import Any

import numpy as np

from tools.mine_city_norms import (
    CELL, MapGeom, StreetRaster, _full_walk_adjacency, doorways,
    indoor_components, load_source, street_component,
)

SCHEMA = "llmapper.urban-semantics"
SCHEMA_VERSION = 1

#: A storey: within this of street grade is ground floor (z units).
STOREY_Z = None  # set per game from the profile

#: An arcade mouth pair must be at least this far apart for the passage to
#: count as a through-route rather than a porch.
ARCADE_MOUTH_SPAN = 2048

#: Arcade sectors sit within this many walkable hops of the street.
ARCADE_DEPTH = 3


def full_map_buildings(geom: MapGeom, street: set[int], raster: StreetRaster):
    """Connected non-street plan areas: the buildings (and terrain masses).

    Unlike the loop census, border-touching areas count -- an edge-frontage
    building is still a building.  Returns a label grid aligned with the
    street raster plus per-label info.
    """
    mask = raster.mask
    labels = np.zeros(mask.shape, dtype=np.int32)
    info: dict[int, dict[str, Any]] = {}
    current = 0
    for r in range(raster.ny):
        for c in range(raster.nx):
            if mask[r, c] or labels[r, c]:
                continue
            current += 1
            cells = []
            touches_street = False
            queue = deque([(r, c)])
            labels[r, c] = current
            while queue:
                cr, cc = queue.popleft()
                cells.append((cr, cc))
                for dr, dc in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                    nr, nc = cr + dr, cc + dc
                    if not (0 <= nr < raster.ny and 0 <= nc < raster.nx):
                        continue
                    if mask[nr, nc]:
                        touches_street = True
                        continue
                    if not labels[nr, nc]:
                        labels[nr, nc] = current
                        queue.append((nr, nc))
            info[current] = {
                "cells": len(cells),
                "area": len(cells) * CELL * CELL,
                "touches_street": touches_street,
            }
    return labels, info


def classify(geom: MapGeom) -> dict[str, Any]:
    standing = geom.profile.standing_height
    street = street_component(geom)
    raster = StreetRaster(geom, street)
    walk = _full_walk_adjacency(geom)

    # Reachability: optimistic and directed, the same rules the street
    # classifier screens with (drops pass downward, mechanisms open).
    header = geom.disk.header
    hf = header.fields if hasattr(header, "fields") else header
    start = int(hf.get("start_sector", -1))
    pass_gap = geom.profile.crouch_height or int(geom.profile.standing_height * 0.75)
    directed: dict[int, set[int]] = defaultdict(set)
    for s in range(len(geom.sectors)):
        for w in geom.sector_walls[s]:
            o = int(geom.walls[w].fields["next_sector"])
            if o < 0:
                continue
            doored = geom.is_door_sector(o) or geom.is_door_sector(s)
            if geom.gap(s, o) >= pass_gap or doored:
                if doored or geom.rise(s, o) <= geom.profile.max_step:
                    directed[s].add(o)
                if doored or geom.rise(o, s) <= geom.profile.max_step:
                    directed[o].add(s)
    if geom.game == "blood":
        from tools.mine_stacks import observe as observe_stacks
        for row in observe_stacks(geom.name, geom.disk):
            upper, lower = row.get("upper_sector"), row.get("lower_sector")
            if row.get("paired") and upper is not None and lower is not None:
                directed[upper].add(lower)
                directed[lower].add(upper)
    reachable: set[int] = set()
    if 0 <= start < len(geom.sectors):
        reachable = {start}
        queue = deque([start])
        while queue:
            cur = queue.popleft()
            for o in directed[cur]:
                if o not in reachable:
                    reachable.add(o)
                    queue.append(o)

    grade = statistics.median([geom.floor_z[s] for s in street]) if street else 0

    # Walkable hop depth from the street network, and each sector's LOCAL
    # grade: the floor of the street it is reached from.  A hilltop town's
    # interiors are ground-floor relative to their own street, not to the
    # city median (E3M2 read as one giant upper storey before this).
    depth = {s: 0 for s in street}
    local_grade = {s: geom.floor_z[s] for s in street}
    queue = deque(street)
    while queue:
        cur = queue.popleft()
        for o in walk[cur]:
            if o not in depth:
                depth[o] = depth[cur] + 1
                local_grade[o] = local_grade[cur]
                queue.append(o)

    # Buildings.
    labels_grid, buildings = full_map_buildings(geom, street, raster)

    def building_of(sector_id: int) -> int:
        points = [geom.wall_xy(w) for w in geom.sector_walls[sector_id]]
        cx = sum(p[0] for p in points) / len(points)
        cy = sum(p[1] for p in points) / len(points)
        r, c = raster.cell(cx, cy)
        if 0 <= r < raster.ny and 0 <= c < raster.nx:
            return int(labels_grid[r, c])
        return 0

    # Arcade candidates: at-grade non-sky components with 2+ separated
    # street mouths, all sectors shallow and standing-height.
    def min_side(sector_id):
        pts = [geom.wall_xy(w) for w in geom.sector_walls[sector_id]]
        xs = [p[0] for p in pts]
        ys = [p[1] for p in pts]
        return min(max(xs) - min(xs), max(ys) - min(ys))

    candidate = {
        s for s in range(len(geom.sectors))
        if s not in street and not geom.parallax[s]
        and abs(geom.floor_z[s] - grade) <= geom.profile.max_step * 2
        and depth.get(s, 99) <= ARCADE_DEPTH
        and (geom.floor_z[s] - geom.ceiling_z[s]) >= standing
        # Corridor-narrow per sector: a roofed shed with doors on two sides
        # is a building, not a passage (E3M2's halls read as arcades until
        # this test).
        and min_side(s) <= 2560
    }
    arcades: set[int] = set()
    seen: set[int] = set()
    for s in candidate:
        if s in seen:
            continue
        comp = {s}
        seen.add(s)
        queue = deque([s])
        while queue:
            cur = queue.popleft()
            for o in walk[cur]:
                if o in candidate and o not in seen:
                    seen.add(o)
                    comp.add(o)
                    queue.append(o)
        mouths = []
        for member in comp:
            for w in geom.sector_walls[member]:
                o = int(geom.walls[w].fields["next_sector"])
                if o in street and o in walk[member]:
                    (x1, y1), (x2, y2) = geom.wall_segment(w)
                    mouths.append(((x1 + x2) / 2, (y1 + y2) / 2))
        span = 0.0
        for i in range(len(mouths)):
            for j in range(i + 1, len(mouths)):
                dx = mouths[i][0] - mouths[j][0]
                dy = mouths[i][1] - mouths[j][1]
                span = max(span, (dx * dx + dy * dy) ** 0.5)
        # Keep only sectors ON a mouth-to-mouth path: a vestibule dangling
        # off the passage is a building's entry hall, not the passage
        # (E3M2's ground floors are vestibules and were being absorbed).
        mouth_sectors = {m for m in comp
                         if any(o in street for o in walk[m])}
        on_path: set = set()
        if len(mouth_sectors) >= 2:
            dist_from: dict = {}
            for mouth in mouth_sectors:
                dist = {mouth: 0}
                queue2 = deque([mouth])
                while queue2:
                    cur2 = queue2.popleft()
                    for o in walk[cur2]:
                        if o in comp and o not in dist:
                            dist[o] = dist[cur2] + 1
                            queue2.append(o)
                dist_from[mouth] = dist
            mouth_list = sorted(mouth_sectors)
            for i, a in enumerate(mouth_list):
                for b in mouth_list[i + 1:]:
                    da, db = dist_from[a], dist_from[b]
                    if b not in da:
                        continue
                    d_ab = da[b]
                    for member in comp:
                        if member in da and member in db                                 and da[member] + db[member] == d_ab:
                            on_path.add(member)
        comp = on_path
        total_area = sum(geom.area[m] for m in comp)
        # A passage is longer than it is wide: mean width (area over mouth
        # span) at alley scale.  Without this, a shop with two street doors
        # reads as an arcade and vanishes from the building census.
        if (len(mouths) >= 2 and comp and span >= ARCADE_MOUTH_SPAN
                and total_area / span <= 2048):
            arcades |= comp

    # Scene applies to sky components only (the E2M1 rule).  Interiors are
    # labeled by geometry regardless of reachability: the optimistic model
    # still under-reaches through unmodeled gating, and calling a locked
    # ward a "scene" would repeat the bot mistake in static form.
    scene_sky = set()
    for comp in getattr(geom, "scene_components", []):
        scene_sky |= comp
    label = {}
    for s in range(len(geom.sectors)):
        if s in street:
            label[s] = "street"
        elif s in arcades:
            label[s] = "arcade"
        elif geom.parallax[s]:
            if s in scene_sky:
                label[s] = "scene"
            else:
                rise = grade - geom.floor_z[s]
                label[s] = "roof" if rise > standing else "courtyard"
        else:
            reference = local_grade.get(s, grade)
            delta = geom.floor_z[s] - reference
            if delta > standing:
                label[s] = "underground"
            elif delta < -standing:
                label[s] = "interior_upper"
            else:
                label[s] = "interior_ground"

    # Buildings: a building is a GROUND-FLOOR walkable interior component.
    # Party walls stop being mergers (rowhouses split) and shared upstairs
    # stop being mergers (E3M1 saloon/hotel connect only above; the ground
    # components separate them).  Upper storeys attach to the building they
    # walk down into.
    ground = {s for s in range(len(geom.sectors)) if label[s] == "interior_ground"}
    building_id: dict[int, int] = {}
    ground_components: list = []
    for s in sorted(ground):
        if s in building_id:
            continue
        comp = {s}
        building_id[s] = len(ground_components)
        queue = deque([s])
        while queue:
            cur = queue.popleft()
            for o in walk[cur]:
                if o in ground and o not in building_id:
                    building_id[o] = building_id[s]
                    comp.add(o)
                    queue.append(o)
        ground_components.append(comp)
    upper = {s for s in range(len(geom.sectors)) if label[s] == "interior_upper"}
    upper_attach: dict[int, int] = {}
    for s in sorted(upper):
        if s in upper_attach:
            continue
        comp = {s}
        queue = deque([s])
        touched: set = set()
        seen_u = {s}
        while queue:
            cur = queue.popleft()
            for o in walk[cur]:
                if o in upper and o not in seen_u:
                    seen_u.add(o)
                    comp.add(o)
                    queue.append(o)
                elif o in building_id:
                    touched.add(building_id[o])
        target = min(touched) if touched else -1
        for member in comp:
            upper_attach[member] = target

    # The true circulation network is street plus arcades (E3M2's town
    # runs on covered inner streets; TEDE1M2's lanes are roofed).  Doorways
    # count from both.
    public = street | arcades
    comps, membership = indoor_components(geom, public)
    doors = doorways(geom, public, membership)
    per_building: dict[int, dict[str, Any]] = defaultdict(
        lambda: {"interior_sectors": 0, "ground": 0, "upper": 0,
                 "doorways": 0, "area": 0})
    for s, b in building_id.items():
        row = per_building[b]
        row["interior_sectors"] += 1
        row["ground"] += 1
        row["area"] += round(geom.area[s])
    for s, b in upper_attach.items():
        if b >= 0:
            per_building[b]["interior_sectors"] += 1
            per_building[b]["upper"] += 1
            per_building[b]["area"] += round(geom.area[s])
    for door in doors:
        into = door["into_sector"]
        b = building_id.get(into, upper_attach.get(into, -1))
        if b is not None and b >= 0:
            per_building[b]["doorways"] += 1

    # Solid masses fronting the street with no interior still count in the
    # denominator: a building you cannot enter.
    interior_mass_labels = {building_of(s) for s in ground}
    solid_masses = sum(
        1 for b, i in buildings.items()
        if i["touches_street"] and 1024 * 1024 <= i["area"] <= 400e6
        and b not in interior_mass_labels
    )
    substantial = [b for b, row in per_building.items()
                   if row["area"] >= 1024 * 1024]
    entered = [b for b in substantial if per_building[b]["doorways"] > 0]

    counts = Counter(label.values())
    network_doorways = len(doors)
    result_stub = None  # keep diff small
    counts_dict = dict(counts.most_common())
    ret = {
        "map": geom.name,
        "labels": label,
        "label_counts": counts_dict,
        "grade_z": grade,
        "arcade_sectors": sorted(arcades),
        "network_with_arcades": {
            "sectors": len(street) + len(arcades),
            "doorways_from_network": None,  # filled below
        },
        "buildings": {
            "ground_components_substantial": len(substantial),
            "solid_fronting_masses": solid_masses,
            "entered_from_street": len(entered),
            "enterable_share_per_building": round(
                len(entered) / (len(substantial) + solid_masses), 3)
            if (substantial or solid_masses) else None,
            "storey_mix": {
                "single_storey": sum(1 for b in substantial
                                     if per_building[b]["upper"] == 0),
                "multi_storey": sum(1 for b in substantial
                                    if per_building[b]["upper"] > 0),
            },
            "detail": [
                {"building": b, **per_building[b]}
                for b in sorted(substantial,
                                key=lambda b: -per_building[b]["interior_sectors"])
                [:20]
            ],
        },
        "thresholds": {
            "storey_split_z": standing,
            "arcade_mouth_span": ARCADE_MOUTH_SPAN,
            "arcade_depth_hops": ARCADE_DEPTH,
        },
    }
    ret["network_with_arcades"]["doorways_from_network"] = network_doorways
    return ret


LABEL_COLORS = {
    "street": "#aecde8", "arcade": "#4f9edd", "courtyard": "#b8d8b8",
    "roof": "#8a6ea8", "interior_ground": "#f5b880", "interior_upper": "#d98a4a",
    "underground": "#7a5c44", "scene": "#d8d8d8",
}


def plot(geom: MapGeom, record: dict[str, Any], out: pathlib.Path) -> None:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    fig, ax = plt.subplots(figsize=(14, 14))
    label = record["labels"]

    def loops_of(sector_id):
        walls = geom.sector_walls[sector_id]
        remaining = set(walls)
        loops = []
        while remaining:
            start_w = min(remaining)
            loop = []
            w = start_w
            while True:
                loop.append(geom.wall_xy(w))
                remaining.discard(w)
                w = int(geom.walls[w].fields["point2"])
                if w == start_w:
                    break
            loops.append(loop)
        return loops

    def loop_area(loop):
        total = 0
        for i, (x1, y1) in enumerate(loop):
            x2, y2 = loop[(i + 1) % len(loop)]
            total += x1 * y2 - x2 * y1
        return abs(total) / 2

    for s in range(len(geom.sectors)):
        color = LABEL_COLORS.get(label[s], "0.9")
        loops = sorted(loops_of(s), key=loop_area, reverse=True)
        if not loops:
            continue
        ax.add_patch(plt.Polygon(loops[0], closed=True, facecolor=color,
                                 edgecolor="0.5", linewidth=0.2, zorder=1))
        for hole in loops[1:]:
            # A hole is either another sector (drawn in its own color at a
            # higher zorder) or solid mass: paint mass first, sectors cover.
            ax.add_patch(plt.Polygon(hole, closed=True, facecolor="#c9bfae",
                                     edgecolor="0.5", linewidth=0.2, zorder=2))
    # Redraw every sector's outer loop above the mass fills so island
    # sectors inside holes stay visible.
    for s in range(len(geom.sectors)):
        color = LABEL_COLORS.get(label[s], "0.9")
        loops = sorted(loops_of(s), key=loop_area, reverse=True)
        if loops and loop_area(loops[0]) < 40e6:
            ax.add_patch(plt.Polygon(loops[0], closed=True, facecolor=color,
                                     edgecolor="0.4", linewidth=0.3, zorder=3))
    for w in range(len(geom.walls)):
        if int(geom.walls[w].fields["next_sector"]) < 0:
            (x1, y1), (x2, y2) = geom.wall_segment(w)
            ax.plot([x1, x2], [y1, y2], color="0.25", linewidth=0.4, zorder=2)
    handles = [plt.Line2D([0], [0], marker="s", linestyle="", markersize=10,
                          markerfacecolor=c, label=name)
               for name, c in LABEL_COLORS.items()]
    ax.legend(handles=handles, loc="upper right", fontsize=9)
    counts = record["label_counts"]
    ax.set_title(f"{record['map']} urban semantics  " +
                 " ".join(f"{k}:{v}" for k, v in counts.items()))
    ax.set_aspect("equal")
    ax.invert_yaxis()
    fig.tight_layout()
    fig.savefig(out, dpi=110)
    plt.close(fig)


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("maps", nargs="+")
    parser.add_argument("-o", "--output",
                        default="projects/blood-city/references/urban-semantics.json")
    parser.add_argument("--plots", default=None)
    parser.add_argument("--game", default="blood")
    args = parser.parse_args(argv)
    records = []
    for name in args.maps:
        path = (f"maps/blood/{name}.MAP" if args.game == "blood"
                else f"maps/duke3d/{name}.map")
        geom = load_source(name, args.game, path)
        record = classify(geom)
        if args.plots:
            out_dir = pathlib.Path(args.plots)
            out_dir.mkdir(parents=True, exist_ok=True)
            plot(geom, record, out_dir / f"{name.lower()}-semantics.png")
        record.pop("labels")
        records.append(record)
        print(name, record["label_counts"],
              "| buildings", record["buildings"]["ground_components_substantial"],
              "+solid", record["buildings"]["solid_fronting_masses"],
              "entered", record["buildings"]["entered_from_street"],
              "share", record["buildings"]["enterable_share_per_building"],
              "storeys", record["buildings"]["storey_mix"])
    payload = {"$schema": SCHEMA, "schema_version": SCHEMA_VERSION,
               "per_map": records}
    out = pathlib.Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(f"wrote {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
