"""E3M1's street: its road sectors (floor 352 under sky) and their width, the pavements beside them, and every wall wearing kerb tile 6."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[4]))
import sys
from bloodmap.corpus import corpus_map_path
from bloodmap.format import read_map
from bloodmap.model import record_fields as F
m = read_map(corpus_map_path("E3M1"))
def box(i):
    s = F(m.sectors[i]); ws = [F(m.walls[w]) for w in range(s["wall_ptr"], s["wall_ptr"] + s["wall_count"])]
    xs = [w["x"] for w in ws]; ys = [w["y"] for w in ws]
    return max(xs) - min(xs), max(ys) - min(ys)
def owner(w):
    for i, s in enumerate(m.sectors):
        f = F(s)
        if f["wall_ptr"] <= w < f["wall_ptr"] + f["wall_count"]:
            return i
for i, s in enumerate(m.sectors):
    f = F(s)
    if f["floor_picnum"] == 352 and f["ceiling_stat"] & 1:
        print("road", i, "box", box(i), "narrow", min(box(i)))
    if f["floor_picnum"] == 4 and f["ceiling_stat"] & 1:
        print("  pavement", i, "box", box(i), "narrow", min(box(i)))
for i in (10, 11):
    f = F(m.sectors[i]); print("s%d" % i, "floor tile", f["floor_picnum"], "box", box(i))
for w, wall in enumerate(m.walls):
    f = F(wall)
    if f["picnum"] == 6 or f["over_picnum"] == 6:
        a, b = owner(w), f["next_sector"]
        fa = F(m.sectors[a]); fb = F(m.sectors[b]) if b >= 0 else None
        print("kerb wall", w, "in s%d" % a, "floor", fa["floor_picnum"], "faces s%d" % b, "floor", fb and fb["floor_picnum"],
              "step", fb and fa["floor_z"] - fb["floor_z"])
