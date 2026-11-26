"""E3M1's street surface taken as the sky sectors with their floor at grade or the road below it (floor_z 8192 or lower down): their floor shades, and the walls between two of them of different shade, axis-aligned or oblique with the angle in degrees folded to 0-90."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[4]))
import math
import statistics
from collections import Counter
from bloodmap.format import read_map
from bloodmap.corpus import corpus_map_path
from bloodmap.model import record_fields

m = read_map(corpus_map_path("E3M1"))
secs = [record_fields(s) for s in m.sectors]
walls = [record_fields(w) for w in m.walls]
street = {i for i, f in enumerate(secs) if f["ceiling_stat"] & 1 and f["floor_z"] >= 8192}
print("street sectors", len(street), "shades", sorted(Counter(secs[i]["floor_shade"] for i in street).items()))
owner = {}
for i, f in enumerate(secs):
    for w in range(f["wall_ptr"], f["wall_ptr"] + f["wall_count"]):
        owner[w] = i
axis, oblique, bounds = 0, [], 0
for w, f in enumerate(walls):
    a, b = owner[w], f["next_sector"]
    if b < 0 or a not in street or b not in street or a > b:
        continue
    if secs[a]["floor_shade"] == secs[b]["floor_shade"]:
        continue
    bounds += 1
    n = walls[f["point2"]]
    dx, dy = n["x"] - f["x"], n["y"] - f["y"]
    if dx == 0 or dy == 0:
        axis += 1
    else:
        ang = math.degrees(math.atan2(abs(dy), abs(dx)))
        oblique.append(round(ang, 1))
print("shade boundaries", bounds, "axis-aligned", axis, "oblique", len(oblique), sorted(oblique))
if oblique:
    print("oblique median", statistics.median(oblique))
