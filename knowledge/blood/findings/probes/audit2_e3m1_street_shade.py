"""E3M1's open-sky ground by floor tile (352 road, 4 pavement): area share per floor shade, area-weighted mean; and the open-sky sectors' walls below shade 0 by tile."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[4]))
import os
import sys
from collections import Counter, defaultdict

from bloodmap.corpus import corpus_map_path
from bloodmap.format import read_map
from bloodmap.model import record_fields
from bloodmap.sector_geom import outline_and_holes


def area(points):
    return abs(sum(a[0] * b[1] - b[0] * a[1] for a, b in zip(points, points[1:] + points[:1]))) / 2


disk = read_map(corpus_map_path("E3M1"))
by_tile = defaultdict(Counter)
walls = Counter()
for index, sector in enumerate(disk.sectors):
    f = record_fields(sector)
    if not int(f["ceiling_stat"]) & 1:
        continue
    tile = int(f["floor_picnum"])
    if tile in (352, 4):
        outline, holes = outline_and_holes(disk, index)
        by_tile[tile][(int(f["floor_shade"]), index if tile == 352 else None)] += area(outline) - sum(area(h) for h in holes)
    for w in range(int(f["wall_ptr"]), int(f["wall_ptr"]) + int(f["wall_count"])):
        wf = record_fields(disk.walls[w])
        if int(wf["shade"]) < 0:
            walls[(int(wf["shade"]), int(wf["picnum"]))] += 1
for tile, shares in by_tile.items():
    total = sum(shares.values())
    by_shade = Counter()
    for (shade, _i), a in shares.items():
        by_shade[shade] += a
    print("tile", tile, "area", round(total), "mean", round(sum(s * a for s, a in by_shade.items()) / total, 1),
          {s: f"{100 * a / total:.1f}%" for s, a in sorted(by_shade.items())})
    if tile == 352:
        print("  largest road sectors", sorted(((round(100 * a / total, 1), i, s) for (s, i), a in shares.items()), reverse=True)[:4])
print("open-sky walls below shade 0:", sum(walls.values()), sorted(walls.items(), key=lambda kv: -kv[1]))
