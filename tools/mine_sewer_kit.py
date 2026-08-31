"""Mine Blood's sewer machinery and finish kit across the original maps.

The report separates *where* a tile occurs (wall/surface/sprite) from a
design reading.  For each supplied role it chooses the densest original map
and records the affected sectors plus their one-hop neighbours, so a later
prefab reads the complete technical setting instead of borrowing a tile in
isolation.

    python -m tools.mine_sewer_kit -o projects/blood-city/references/sewer-kit.json
"""

from __future__ import annotations

import argparse
import collections
import json
from pathlib import Path

from bloodmap.format import read_map


ASSETS = {
    "machinery": (2462, 2463, 2476, 2477),
    # 498 per owner correction 2026-08-31; 468 is the unlit ceiling light,
    # see knowledge/blood/design/owner-anchors-v1.json
    "pipe_walls": (496, 497, 498, 499),
    "sewer_door": (500,),
    "sewer_light": (501,),
    "sewer_grate": (502,),
}


def owner_index(disk):
    return {
        wall_id: sector_id
        for sector_id, sector in enumerate(disk.sectors)
        for wall_id in range(int(sector.fields["wall_ptr"]),
                             int(sector.fields["wall_ptr"])
                             + int(sector.fields["wall_count"]))
    }


def sectors_for(disk, tiles):
    wanted = set(tiles)
    owners = owner_index(disk)
    sectors = set()
    uses = []
    for wall_id, wall in enumerate(disk.walls):
        for field in ("picnum", "over_picnum"):
            tile = int(wall.fields[field])
            if tile in wanted:
                sector = owners[wall_id]
                sectors.add(sector)
                uses.append({"kind": "wall", "sector": sector,
                             "wall": wall_id, "field": field, "picnum": tile})
    for sector_id, sector in enumerate(disk.sectors):
        for field in ("floor_picnum", "ceiling_picnum"):
            tile = int(sector.fields[field])
            if tile in wanted:
                sectors.add(sector_id)
                uses.append({"kind": "surface", "sector": sector_id,
                             "field": field, "picnum": tile})
    for sprite_id, sprite in enumerate(disk.sprites):
        if int(sprite.fields["picnum"]) in wanted:
            sector = int(sprite.fields["sector"])
            sectors.add(sector)
            uses.append({"kind": "sprite", "sector": sector,
                         "sprite": sprite_id, "picnum": int(sprite.fields["picnum"]),
                         "type": int(sprite.fields["type"]),
                         "cstat": int(sprite.fields["cstat"])})
    return sectors, uses


def snapshot(disk, sector_id):
    sector = disk.sectors[sector_id].fields
    walls = range(int(sector["wall_ptr"]), int(sector["wall_ptr"]) + int(sector["wall_count"]))
    neighbours = sorted({int(disk.walls[i].fields["next_sector"])
                         for i in walls if int(disk.walls[i].fields["next_sector"]) >= 0})
    return {
        "sector": sector_id,
        "floor_z": int(sector["floor_z"]), "ceiling_z": int(sector["ceiling_z"]),
        "floor_picnum": int(sector["floor_picnum"]),
        "ceiling_picnum": int(sector["ceiling_picnum"]),
        "wall_picnums": dict(collections.Counter(int(disk.walls[i].fields["picnum"])
                                                   for i in walls)),
        "neighbours": neighbours,
    }


def mine(roots: list[Path]):
    maps = []
    for root in roots:
        for path in sorted(root.glob("*.[Mm][Aa][Pp]")):
            try:
                disk = read_map(path)
            except Exception:
                continue
            maps.append((path, disk))
    report = {"$schema": "llmapper.sewer-kit", "schema_version": 1,
              "role_assets": {name: list(tiles) for name, tiles in ASSETS.items()},
              "roles": {}}
    for role, tiles in ASSETS.items():
        hits = []
        for path, disk in maps:
            sectors, uses = sectors_for(disk, tiles)
            if uses:
                hits.append((len(uses), path, disk, sectors, uses))
        hits.sort(key=lambda item: (-item[0], item[1].name))
        examples = []
        for count, path, disk, sectors, uses in hits[:5]:
            context = set(sectors)
            for sector_id in sectors:
                context.update(snapshot(disk, sector_id)["neighbours"])
            examples.append({
                "map": path.name, "uses": count,
                "affected_sectors": sorted(sectors),
                "uses_by_kind": dict(collections.Counter(item["kind"] for item in uses)),
                "tile_counts": dict(collections.Counter(item["picnum"] for item in uses)),
                "context": [snapshot(disk, sector_id) for sector_id in sorted(context)],
            })
        report["roles"][role] = {"maps_with_use": len(hits), "examples": examples}
    return report


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    # The reference corpus: original campaign plus the owner's curated picks
    # and conversions, matching the pre-reorganization flat maps/blood.
    parser.add_argument("--maps", nargs="*", default=[
        "maps/blood/campaign", "maps/blood/campaign/multiplayer",
        "maps/blood/curated", "maps/blood/curated/multiplayer",
        "maps/blood/conversions",
    ])
    parser.add_argument("-o", "--output", required=True)
    args = parser.parse_args(argv)
    report = mine([Path(root) for root in args.maps])
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    for role, record in report["roles"].items():
        shown = ", ".join(f"{item['map']} ({item['uses']})" for item in record["examples"][:3])
        print(f"{role}: {record['maps_with_use']} map(s); {shown}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
