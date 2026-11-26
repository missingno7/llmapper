"""E3M1 street walls at 16 units a pixel, axis-aligned: is x panning 0, in phase with the world 1,024 grid, or both (self-contained redo of consolidation_audit_mid_facade_phase.py)."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[4]))
import math
import sys
from collections import Counter
from bloodmap.format import read_map
from bloodmap.corpus import corpus_map_path
from bloodmap.model import record_fields
from bloodmap.texture_align import wall_art_sizes

sizes = wall_art_sizes()
name = sys.argv[1] if len(sys.argv) > 1 else "E3M1"
d = read_map(corpus_map_path(name))
S = [record_fields(s) for s in d.sectors]
W = [record_fields(w) for w in d.walls]
owner = {}
for i, s in enumerate(S):
    for w in range(s["wall_ptr"], s["wall_ptr"] + s["wall_count"]):
        owner[w] = i
c = Counter()
for w, x in enumerate(W):
    if not S[owner[w]]["ceiling_stat"] & 1:
        continue
    if x["next_sector"] >= 0 and S[x["next_sector"]]["ceiling_stat"] & 1:
        continue
    b = W[x["point2"]]
    L = math.hypot(b["x"] - x["x"], b["y"] - x["y"])
    tw = sizes.get(x["picnum"], (0, 0))[0]
    if not tw or not x["x_repeat"]:
        continue
    if abs(L / (x["x_repeat"] * 8) - 16) > 0.5:
        continue
    if x["x"] != b["x"] and x["y"] != b["y"]:
        c["diagonal"] += 1
        continue
    along = (b["x"] - x["x"]) if x["y"] == b["y"] else (b["y"] - x["y"])
    start = x["x"] if x["y"] == b["y"] else x["y"]
    sign = 1 if along > 0 else -1
    world = (sign * start // 16) % tw
    pan = x["x_panning"] % tw
    c["n"] += 1
    c["world"] += pan == world
    c["zero"] += pan == 0
    c["both"] += pan == world and pan == 0
print(name, dict(c))
