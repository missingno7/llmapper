"""Detail one precedent selection: geometry, player scale, ART usage, neighbors."""

from __future__ import annotations

import json
import sys
from pathlib import Path

from bloodmap.format import read_map
from bloodmap.player_space import inspect_space, player_profile
from bloodmap.spatial import analyze_spatial

PROFILE = player_profile("blood")


def detail(path: Path, sector_ids: list[int]) -> dict:
    disk = read_map(path)
    level = disk.to_level_ir()
    build = disk.to_build_ir()
    spatial = analyze_spatial(build)
    geo = {int(item["ref"].split(":", 1)[1]): item for item in spatial["views"]["geometry"]["sectors"]}
    rows = []
    for sid in sector_ids:
        fields = level.sectors[sid]["fields"]
        walls = [
            level.walls[w]["fields"]
            for w in range(int(fields["wall_ptr"]), int(fields["wall_ptr"]) + int(fields["wall_count"]))
        ]
        wall_tiles: dict[int, int] = {}
        for wall in walls:
            wall_tiles[int(wall["picnum"])] = wall_tiles.get(int(wall["picnum"]), 0) + 1
        sprites = [
            {"index": i, "type": int(s["fields"]["type"]), "picnum": int(s["fields"]["picnum"]),
             "cstat": int(s["fields"]["cstat"]), "shade": int(s["fields"]["shade"]),
             "x_repeat": int(s["fields"]["x_repeat"])}
            for i, s in enumerate(level.sprites) if int(s["fields"]["sector"]) == sid
        ]
        types: dict[int, int] = {}
        pics: dict[int, int] = {}
        for s in sprites:
            types[s["type"]] = types.get(s["type"], 0) + 1
            pics[s["picnum"]] = pics.get(s["picnum"], 0) + 1
        rows.append({
            "sector": f"sector:{sid}",
            "player_areas": round(geo[sid]["area"] / PROFILE.body_width ** 2, 1),
            "clear_player_heights": round(geo[sid]["clear_height"] / PROFILE.standing_height, 2),
            "floor_z": geo[sid]["floor_z"], "ceiling_z": geo[sid]["ceiling_z"],
            "wall_loop_count": geo[sid]["wall_loop_count"],
            "wall_count": len(walls),
            "floor_tile": int(fields["floor_picnum"]), "ceiling_tile": int(fields["ceiling_picnum"]),
            "floor_shade": int(fields["floor_shade"]), "ceiling_shade": int(fields["ceiling_shade"]),
            "ceiling_parallax": bool(int(fields["ceiling_stat"]) & 1),
            "wall_tiles": dict(sorted(wall_tiles.items(), key=lambda kv: -kv[1])[:6]),
            "sprite_count": len(sprites),
            "sprite_types": dict(sorted(types.items(), key=lambda kv: -kv[1])[:8]),
            "sprite_picnums": dict(sorted(pics.items(), key=lambda kv: -kv[1])[:8]),
            "neighbors": sorted({
                int(v.split(":", 1)[1])
                for p in spatial["views"]["geometry"]["portals"]
                for v in p["sectors"] if sid in [int(x.split(":", 1)[1]) for x in p["sectors"]]
            } - {sid}),
        })
    return {"map": path.name, "sectors": rows}


if __name__ == "__main__":
    print(json.dumps(
        detail(Path(sys.argv[1]), [int(v) for v in sys.argv[2].split(",")]),
        indent=2, sort_keys=True,
    ))
