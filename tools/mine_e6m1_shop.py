"""Mine Blood E6M1's shop as a concrete prefab language.

The generic fixture survey deliberately treats every small raised sector as
one family.  That loses the information that matters when reproducing this
particular shop: a shelf is wall texture 2026/202/2635, a cash register is
the raised top of counter sector 32, and the clothes, mannequins and wall
utilities are sprites with their own alignment, palette and height.

This report keeps those roles separate.  It records every occurrence of the
owner-identified asset, the complete sectors that carry the counter, retail
floor and display clusters, and a one-hop sector neighbourhood around them.
It is evidence for a prefab; it does not infer that an arbitrary use of a
tile elsewhere in the map is also a shop.

    python -m tools.mine_e6m1_shop -o projects/blood-city/references/e6m1-shop.json
"""

from __future__ import annotations

import argparse
import collections
import json
import pathlib
from typing import Any

from bloodmap.format import read_map


ASSETS = {
    "shelf_wall": (2026, 202, 2635),
    "crate_surface": (95, 452),
    "hanging_clothes": (73,),
    "mannequin": (2377,),
    "cash_register_surface": (2476,),
    "drawer_surface": (35, 36),
    "wood_casework": (34,),
    "outlet": (1050,),
    "chair": (758,),
    "wall_clock": (1165,),
    "shaft_metal": (1097,),
}

# These are not guessed from proximity: they are the sectors identified while
# reading the original E6M1 shop.  The report also lists their neighbours,
# so a later pass can disagree with this seed from evidence rather than losing
# the original measurement.
FOCUS_SECTORS = (32, 34, 45, 50, 61, 63, 79)
SPRITE_FIELDS = ("x", "y", "z", "cstat", "picnum", "shade", "pal",
                 "x_repeat", "y_repeat", "x_offset", "y_offset",
                 "sector", "status", "angle", "type")


def _fields(item) -> dict[str, Any]:
    return item.fields


def _wall_owner(disk) -> dict[int, int]:
    return {
        wall_index: sector_index
        for sector_index, sector in enumerate(disk.sectors)
        for wall_index in range(int(_fields(sector)["wall_ptr"]),
                                int(_fields(sector)["wall_ptr"])
                                + int(_fields(sector)["wall_count"]))
    }


def _bounds(disk, sector_id: int) -> list[int]:
    sector = _fields(disk.sectors[sector_id])
    points = [
        (_fields(disk.walls[wall_id])["x"], _fields(disk.walls[wall_id])["y"])
        for wall_id in range(int(sector["wall_ptr"]),
                             int(sector["wall_ptr"]) + int(sector["wall_count"]))
    ]
    return [min(x for x, _y in points), min(y for _x, y in points),
            max(x for x, _y in points), max(y for _x, y in points)]


def _area(disk, sector_id: int) -> int:
    sector = _fields(disk.sectors[sector_id])
    points = [
        (_fields(disk.walls[wall_id])["x"], _fields(disk.walls[wall_id])["y"])
        for wall_id in range(int(sector["wall_ptr"]),
                             int(sector["wall_ptr"]) + int(sector["wall_count"]))
    ]
    twice = sum(x0 * y1 - x1 * y0
                for (x0, y0), (x1, y1) in zip(points, points[1:] + points[:1]))
    return abs(twice) // 2


def _sector_snapshot(disk, sector_id: int) -> dict[str, Any]:
    sector = _fields(disk.sectors[sector_id])
    wall_ids = range(int(sector["wall_ptr"]),
                     int(sector["wall_ptr"]) + int(sector["wall_count"]))
    return {
        "sector": sector_id,
        "bounds": _bounds(disk, sector_id),
        "area": _area(disk, sector_id),
        "ceiling_z": int(sector["ceiling_z"]),
        "floor_z": int(sector["floor_z"]),
        "ceiling_picnum": int(sector["ceiling_picnum"]),
        "floor_picnum": int(sector["floor_picnum"]),
        "ceiling_shade": int(sector["ceiling_shade"]),
        "floor_shade": int(sector["floor_shade"]),
        "walls": [{
            "wall": wall_id,
            "x": int(_fields(disk.walls[wall_id])["x"]),
            "y": int(_fields(disk.walls[wall_id])["y"]),
            "next_sector": int(_fields(disk.walls[wall_id])["next_sector"]),
            "picnum": int(_fields(disk.walls[wall_id])["picnum"]),
            "over_picnum": int(_fields(disk.walls[wall_id])["over_picnum"]),
            "cstat": int(_fields(disk.walls[wall_id])["cstat"]),
        } for wall_id in wall_ids],
        "sprites": [{name: int(_fields(sprite)[name]) for name in SPRITE_FIELDS}
                    | {"sprite": sprite_id}
                    for sprite_id, sprite in enumerate(disk.sprites)
                    if int(_fields(sprite)["sector"]) == sector_id],
    }


def _neighbours(disk, seeds: set[int]) -> list[int]:
    found = set(seeds)
    for sector_id in seeds:
        sector = _fields(disk.sectors[sector_id])
        for wall_id in range(int(sector["wall_ptr"]),
                             int(sector["wall_ptr"]) + int(sector["wall_count"])):
            other = int(_fields(disk.walls[wall_id])["next_sector"])
            if other >= 0:
                found.add(other)
    return sorted(found)


def _asset_occurrences(disk, wall_owner: dict[int, int], picnums: tuple[int, ...]) -> dict[str, list[dict[str, int]]]:
    wanted = set(picnums)
    sprites = [
        {name: int(_fields(sprite)[name]) for name in SPRITE_FIELDS}
        | {"sprite": sprite_id}
        for sprite_id, sprite in enumerate(disk.sprites)
        if int(_fields(sprite)["picnum"]) in wanted
    ]
    walls = []
    for wall_id, wall in enumerate(disk.walls):
        fields = _fields(wall)
        for field in ("picnum", "over_picnum"):
            if int(fields[field]) in wanted:
                walls.append({"wall": wall_id, "sector": wall_owner[wall_id],
                              "field": field, "picnum": int(fields[field]),
                              "x": int(fields["x"]), "y": int(fields["y"]),
                              "next_sector": int(fields["next_sector"]),
                              "cstat": int(fields["cstat"])})
    surfaces = []
    for sector_id, sector in enumerate(disk.sectors):
        fields = _fields(sector)
        for field in ("floor_picnum", "ceiling_picnum"):
            if int(fields[field]) in wanted:
                surfaces.append({"sector": sector_id, "field": field,
                                 "picnum": int(fields[field]),
                                 "z": int(fields["floor_z"] if field == "floor_picnum"
                                          else fields["ceiling_z"])})
    return {"sprites": sprites, "walls": walls, "surfaces": surfaces}


def mine(path: pathlib.Path) -> dict[str, Any]:
    disk = read_map(path)
    wall_owner = _wall_owner(disk)
    focus = set(FOCUS_SECTORS)
    report = {
        "$schema": "llmapper.e6m1-shop",
        "schema_version": 1,
        "source": str(path).replace("\\", "/"),
        "note": ("Derived occurrences and sector geometry for the E6M1 shop. "
                 "Role names are owner-supplied and deliberately kept separate "
                 "from the measurements."),
        "role_assets": {name: list(picnums) for name, picnums in ASSETS.items()},
        "asset_occurrences": {
            name: _asset_occurrences(disk, wall_owner, picnums)
            for name, picnums in ASSETS.items()
        },
        "focus_sectors": [_sector_snapshot(disk, sector_id)
                          for sector_id in FOCUS_SECTORS],
        "focus_neighbourhood": [_sector_snapshot(disk, sector_id)
                                for sector_id in _neighbours(disk, focus)],
        "asset_counts": {
            name: {
                "sprites": len(rows["sprites"]), "walls": len(rows["walls"]),
                "surfaces": len(rows["surfaces"]),
            }
            for name, rows in {
                name: _asset_occurrences(disk, wall_owner, picnums)
                for name, picnums in ASSETS.items()
            }.items()
        },
    }
    return report


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--map", default="maps/blood/campaign/E6M1.MAP")
    parser.add_argument("-o", "--output", required=True)
    args = parser.parse_args(argv)
    report = mine(pathlib.Path(args.map))
    output = pathlib.Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2), encoding="utf-8", newline="\n")
    print(f"wrote {output}")
    for name, counts in report["asset_counts"].items():
        print(f"  {name:22s} sprites={counts['sprites']:3d} walls={counts['walls']:3d} "
              f"surfaces={counts['surfaces']:3d}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
