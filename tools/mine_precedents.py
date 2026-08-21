"""Bounded precedent mining for one authoring pilot.

Answers five concrete authoring questions against original Blood maps and keeps
exact source references.  This is deliberately not a corpus-wide semantic atlas.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

from bloodmap.decompiler import decompile_level
from bloodmap.format import read_map
from bloodmap.player_space import player_profile
from bloodmap.spatial import analyze_spatial

PROFILE = player_profile("blood")


def _sid(ref):
    return int(str(ref).split(":", 1)[1])


def scan(path: Path) -> dict:
    disk = read_map(path)
    level = disk.to_level_ir()
    build = disk.to_build_ir()
    spatial = analyze_spatial(build)
    geo = {_sid(item["ref"]): item for item in spatial["views"]["geometry"]["sectors"]}
    portals = spatial["views"]["geometry"]["portals"]
    sprites_per_sector = {}
    for sprite in level.sprites:
        sector = int(sprite["fields"]["sector"])
        sprites_per_sector[sector] = sprites_per_sector.get(sector, 0) + 1

    parallax = {
        sector_id for sector_id, sector in enumerate(level.sectors)
        if int(sector["fields"]["ceiling_stat"]) & 1
    }

    out = {"map": path.name, "sectors": len(level.sectors)}

    # 1. large parallax (open-sky) parent spaces, ranked by footprint
    open_spaces = sorted(
        (
            {
                "sector": f"sector:{sid}",
                "player_areas": round(geo[sid]["area"] / PROFILE.body_width ** 2, 1),
                "loops": geo[sid]["wall_loop_count"],
                "clear_player_heights": round(geo[sid]["clear_height"] / PROFILE.standing_height, 2),
                "sprites": sprites_per_sector.get(sid, 0),
            }
            for sid in parallax if sid in geo
        ),
        key=lambda item: -item["player_areas"],
    )[:3]
    out["open_parent_spaces"] = open_spaces

    # 2. multi-loop sectors: an outer space that literally contains a mass
    out["container_sectors"] = sorted(
        (
            {
                "sector": f"sector:{sid}", "loops": item["wall_loop_count"],
                "player_areas": round(item["area"] / PROFILE.body_width ** 2, 1),
                "parallax_ceiling": sid in parallax,
            }
            for sid, item in geo.items() if item["wall_loop_count"] >= 2
        ),
        key=lambda item: (-item["loops"], -item["player_areas"]),
    )[:3]

    # 3. stair runs: chains of sectors whose floors step monotonically
    adjacency = {}
    for portal in portals:
        a, b = (_sid(v) for v in portal["sectors"])
        adjacency.setdefault(a, set()).add(b)
        adjacency.setdefault(b, set()).add(a)
    runs = []
    for sid in sorted(geo):
        chain, current, seen = [sid], sid, {sid}
        while True:
            step = [
                n for n in sorted(adjacency.get(current, ()))
                if n not in seen and n in geo
                and 0 < geo[current]["floor_z"] - geo[n]["floor_z"] <= 4096
                and geo[n]["area"] < 6_000_000
            ]
            if not step:
                break
            current = step[0]
            seen.add(current)
            chain.append(current)
        if len(chain) >= 4:
            runs.append({
                "sectors": [f"sector:{v}" for v in chain],
                "steps": len(chain) - 1,
                "rise_player_heights": round(
                    (geo[chain[0]]["floor_z"] - geo[chain[-1]]["floor_z"]) / PROFILE.standing_height, 2,
                ),
            })
    out["stair_runs"] = sorted(runs, key=lambda item: -item["steps"])[:2]

    # 4. release openings: a narrow portal onto a much larger space
    releases = []
    for portal in portals:
        a, b = (_sid(v) for v in portal["sectors"])
        if a not in geo or b not in geo or portal["width"] <= 0:
            continue
        for small, big in ((a, b), (b, a)):
            if geo[small]["area"] <= 0:
                continue
            ratio = geo[big]["area"] / geo[small]["area"]
            if ratio >= 8 and portal["width"] <= 2048 and geo[big]["area"] > 4_000_000:
                releases.append({
                    "portal": portal["id"],
                    "from": f"sector:{small}", "to": f"sector:{big}",
                    "area_ratio": round(ratio, 1),
                    "opening_player_widths": round(portal["width"] / PROFILE.body_width, 2),
                    "height_gain_player_heights": round(
                        (geo[big]["clear_height"] - geo[small]["clear_height"]) / PROFILE.standing_height, 2,
                    ),
                })
    out["release_openings"] = sorted(releases, key=lambda item: -item["area_ratio"])[:3]

    # 5. decorated large rooms
    out["decorated_rooms"] = sorted(
        (
            {
                "sector": f"sector:{sid}",
                "player_areas": round(geo[sid]["area"] / PROFILE.body_width ** 2, 1),
                "sprites": count,
                "sprites_per_100_player_areas": round(
                    count / max(1.0, geo[sid]["area"] / PROFILE.body_width ** 2) * 100, 2,
                ),
            }
            for sid, count in sprites_per_sector.items()
            if sid in geo and count >= 8 and geo[sid]["area"] > 3_000_000
        ),
        key=lambda item: -item["sprites"],
    )[:3]

    # 6. dark low interiors (crypt candidates)
    crypts = []
    for sid, item in geo.items():
        fields = level.sectors[sid]["fields"]
        shade = (int(fields["floor_shade"]) + int(fields["ceiling_shade"])) / 2
        heights = item["clear_height"] / PROFILE.standing_height
        areas = item["area"] / PROFILE.body_width ** 2
        if shade >= 24 and 1.2 <= heights <= 3.0 and 20 <= areas <= 400 and sid not in parallax:
            crypts.append({
                "sector": f"sector:{sid}", "shade": shade,
                "clear_player_heights": round(heights, 2), "player_areas": round(areas, 1),
                "floor_tile": int(fields["floor_picnum"]), "ceiling_tile": int(fields["ceiling_picnum"]),
            })
    out["dark_low_interiors"] = sorted(crypts, key=lambda item: -item["shade"])[:3]
    return out


def main(argv):
    directory = Path(argv[1]) if len(argv) > 1 else Path("maps/blood")
    names = argv[2].split(",") if len(argv) > 2 else None
    results = []
    for path in sorted(directory.glob("*.MAP")):
        if names and path.stem not in names:
            continue
        try:
            results.append(scan(path))
        except Exception as exc:  # noqa: BLE001 - a survey must not stop on one bad map
            results.append({"map": path.name, "error": f"{type(exc).__name__}: {exc}"})
    print(json.dumps(results, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
