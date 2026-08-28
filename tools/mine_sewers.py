"""What a DukCity sewer actually is, before Blood City digs one.

Phase 0 counted below-grade sectors (75-125 per DukCity map); this pass
measures their anatomy: how many surface entries per unit of street, what
form an entry takes (walk-down, drop, water dive), whether the network loops
like the street grid above it or runs its own line, how deep it sits, how wet
it is, and what role it plays in the route (keycard evidence for required
passage, entry count for shortcut loops, Duke secret tags for secrets).

    python -m tools.mine_sewers -o projects/blood-city/references/sewer-mining.json

Structure only -- dressing for Blood City's sewer comes from the Blood-side
water and underground norms already in knowledge/blood/design/.
"""

from __future__ import annotations

import argparse
import json
import pathlib
import statistics
from collections import defaultdict, deque
from typing import Any

from bloodmap.duke_semantics import classify_se7_groups
from tools.mine_city_norms import (
    StreetRaster, load_source, street_component, boundary_walls, Z_PER_XY,
)

SCHEMA = "llmapper.sewer-anatomy"
SCHEMA_VERSION = 1

SOURCES = [
    ("DukCity1", "duke3d", "maps/duke3d/DukCity1.map"),
    ("DukCity2", "duke3d", "maps/duke3d/DukCity2.map"),
    ("DukCity3", "duke3d", "maps/duke3d/DukCity3.map"),
    ("DukCity4", "duke3d", "maps/duke3d/DukCity4.map"),
]

#: Duke3D ACCESSCARD tile.
KEYCARD_PICNUM = 60

#: Duke secret sectors are lotag 32767; the disk field is masked to 14 bits.
SECRET_LOTAG = 32767 & 0x3FFF

MIN_SEWER_SECTORS = 3

WATER_LOTAGS = {1, 2}


def walkable_adjacency(geom, se7_edges) -> dict[int, set[int]]:
    """Red-wall adjacency the player fits through, plus SE7 teleport pairs."""
    pass_gap = int(geom.profile.standing_height * 0.75)
    adjacency: dict[int, set[int]] = defaultdict(set)
    for sector_id in range(len(geom.sectors)):
        for w in geom.sector_walls[sector_id]:
            other = int(geom.walls[w].fields["next_sector"])
            if other < 0:
                continue
            if geom.gap(sector_id, other) >= pass_gap or geom.is_door_sector(other) \
                    or geom.is_door_sector(sector_id):
                adjacency[sector_id].add(other)
                adjacency[other].add(sector_id)
    for a, b in se7_edges:
        adjacency[a].add(b)
        adjacency[b].add(a)
    return adjacency


def components_of(members: set[int], adjacency: dict[int, set[int]]) -> list[set[int]]:
    seen: set[int] = set()
    out = []
    for start in members:
        if start in seen:
            continue
        component = {start}
        seen.add(start)
        queue = deque([start])
        while queue:
            current = queue.popleft()
            for other in adjacency[current]:
                if other in members and other not in seen:
                    seen.add(other)
                    component.add(other)
                    queue.append(other)
        out.append(component)
    return out


def analyze(name: str, game: str, path: str) -> dict[str, Any]:
    geom = load_source(name, game, path)
    street = street_component(geom)
    raster = StreetRaster(geom, street)
    grade = statistics.median([geom.floor_z[s] for s in street])
    standing = geom.profile.standing_height

    se7 = classify_se7_groups(geom.disk)
    se7_edges = []
    water_dive_pairs = set()
    for record in se7.values():
        endpoints = record.get("endpoints", [])
        sectors = [e["source_sector"] for e in endpoints]
        for i, a in enumerate(sectors):
            for b in sectors[i + 1:]:
                se7_edges.append((a, b))
                if record.get("kind") == "water_link":
                    water_dive_pairs.add(frozenset((a, b)))
    # SE17 elevator shafts: stacked sectors elsewhere in map space, grouped
    # by hitag, traversed by riding -- an edge the geometry does not draw.
    elevator_pairs = set()
    lifts: dict[int, list[int]] = defaultdict(list)
    for sprite in geom.sprites:
        if int(sprite.fields["picnum"]) == 1 and int(sprite.fields["lotag"]) == 17:
            lifts[int(sprite.fields["hitag"])].append(int(sprite.fields["sector"]))
    for group in lifts.values():
        for i, a in enumerate(group):
            for b in group[i + 1:]:
                se7_edges.append((a, b))
                elevator_pairs.add(frozenset((a, b)))

    adjacency = walkable_adjacency(geom, se7_edges)

    below = {
        i for i in range(len(geom.sectors))
        if i not in street and geom.floor_z[i] - grade > standing
    }
    networks = [c for c in components_of(below, adjacency)
                if len(c) >= MIN_SEWER_SECTORS]
    networks.sort(key=lambda c: -sum(geom.area[s] for s in c))

    # Reachability from the street without passing through any below-grade
    # network, so an entry is a first contact rather than a tunnel-internal hop.
    surface_reach: set[int] = set(street)
    queue = deque(street)
    while queue:
        current = queue.popleft()
        for other in adjacency[current]:
            if other not in surface_reach and other not in below:
                surface_reach.add(other)
                queue.append(other)

    frontage = sum(geom.wall_length(w) for w in boundary_walls(geom, street))

    records = []
    for component in networks:
        area = sum(geom.area[s] for s in component)
        depths = [(geom.floor_z[s] - grade) / standing for s in component]
        wet_area = sum(
            geom.area[s] for s in component
            if (int(geom.sectors[s].fields["lotag"]) & 0x3FFF) in WATER_LOTAGS)
        # Under-street share: area whose centroid raster cell is street above.
        under = 0.0
        for s in component:
            points = [geom.wall_xy(w) for w in geom.sector_walls[s]]
            cx = sum(p[0] for p in points) / len(points)
            cy = sum(p[1] for p in points) / len(points)
            if raster.is_street(cx, cy):
                under += geom.area[s]

        entries = []
        for s in component:
            for other in adjacency[s]:
                if other in component or other not in surface_reach:
                    continue
                if frozenset((s, other)) in water_dive_pairs:
                    form = "water_dive"
                elif frozenset((s, other)) in elevator_pairs:
                    form = "elevator"
                else:
                    drop = geom.floor_z[s] - geom.floor_z[other]
                    form = "drop" if drop > geom.profile.max_step else "walk"
                entries.append({"from_sector": other, "into_sector": s, "form": form,
                                "descent_z": geom.floor_z[s] - geom.floor_z[other]})
        # One vestibule can touch the network at several sectors; merge entries
        # whose surface side is the same connected pocket of surface_reach.
        vestibules: dict[int, int] = {}
        for entry in entries:
            root = entry["from_sector"]
            if root not in vestibules:
                pocket = {root}
                queue = deque([root])
                while queue:
                    current = queue.popleft()
                    for other in adjacency[current]:
                        if other in surface_reach and other not in street \
                                and other not in pocket and other not in component:
                            pocket.add(other)
                            queue.append(other)
                index = len(set(vestibules.values()))
                for member in pocket:
                    vestibules.setdefault(member, index)
            entry["vestibule"] = vestibules[entry["from_sector"]]
        distinct = {}
        for entry in entries:
            distinct.setdefault(entry["vestibule"], entry)

        edges = sum(len(adjacency[s] & component) for s in component) // 2
        secrets = sum(1 for s in component
                      if (int(geom.sectors[s].fields["lotag"]) & 0x3FFF) == SECRET_LOTAG)
        # A subway is ridden into, not climbed into: SE6 (engine) / SE14 (car)
        # inside the component marks a transit ring rather than a sewer.
        transit = sum(1 for spr in geom.sprites
                      if int(spr.fields["picnum"]) == 1
                      and int(spr.fields["lotag"]) in (6, 14)
                      and int(spr.fields["sector"]) in component)
        keycards = [i for i, spr in enumerate(geom.sprites)
                    if int(spr.fields["picnum"]) == KEYCARD_PICNUM
                    and int(spr.fields["sector"]) in component]

        records.append({
            "sectors": len(component),
            "sector_ids": sorted(component)[:16],
            "area": round(area),
            "depth_standing_heights": {
                "median": round(statistics.median(depths), 2),
                "min": round(min(depths), 2),
                "max": round(max(depths), 2),
            },
            "wet_area_share": round(wet_area / area, 2) if area else 0,
            "under_street_area_share": round(under / area, 2) if area else 0,
            "loops_cycle_rank": edges - len(component) + 1,
            "entries": sorted(distinct.values(), key=lambda e: e["into_sector"]),
            "entry_count": len(distinct),
            "entry_forms": sorted(e["form"] for e in distinct.values()),
            "secret_sectors": secrets,
            "keycards_inside": keycards,
            "transit_effectors": transit,
            "role_reading": (
                "transit_ring" if transit else
                "required_passage" if keycards else
                "secret" if secrets and len(distinct) <= 1 else
                "shortcut_loop" if len(distinct) >= 2 else "dead_end_pocket"),
        })

    return {
        "map": name,
        "street_grade_z": grade,
        "street_frontage_units": round(frontage),
        "below_grade_sectors_total": len(below),
        "networks": records,
        "entries_per_10240_frontage": round(
            sum(r["entry_count"] for r in records) / max(1.0, frontage) * 10240, 2),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("-o", "--output",
                        default="projects/blood-city/references/sewer-mining.json")
    args = parser.parse_args(argv)
    payload = {
        "$schema": SCHEMA,
        "schema_version": SCHEMA_VERSION,
        "scope": {"sources": [n for n, _g, _p in SOURCES], "method": __doc__,
                  "thresholds": {"min_sewer_sectors": MIN_SEWER_SECTORS,
                                 "below_grade": "floor deeper than one standing height",
                                 "z_per_xy": Z_PER_XY}},
        "per_map": [analyze(*source) for source in SOURCES],
    }
    out = pathlib.Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    for record in payload["per_map"]:
        print(record["map"], "networks:", len(record["networks"]),
              "entries/10240:", record["entries_per_10240_frontage"])
    print(f"wrote {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
