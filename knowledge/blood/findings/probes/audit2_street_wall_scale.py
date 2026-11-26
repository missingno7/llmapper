"""Street walls (a wall of a sky-ceilinged sector that does not open onto another sky sector) by world units per tile pixel, in E3M1 and TEDE1M2, and E3M1's street openings by width."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[4]))
import math
from collections import Counter
from bloodmap.format import read_map
from bloodmap.corpus import corpus_map_path
from bloodmap.model import record_fields
from bloodmap.texture_align import wall_art_sizes

sizes = wall_art_sizes()
for name in ("E3M1", "TEDE1M2"):
    d = read_map(corpus_map_path(name))
    S = [record_fields(s) for s in d.sectors]
    W = [record_fields(w) for w in d.walls]
    owner = {}
    for i, s in enumerate(S):
        for w in range(s["wall_ptr"], s["wall_ptr"] + s["wall_count"]):
            owner[w] = i
    c = Counter()
    openings = Counter()
    for w, x in enumerate(W):
        s = S[owner[w]]
        if not s["ceiling_stat"] & 1:
            continue
        b = W[x["point2"]]
        L = math.hypot(b["x"] - x["x"], b["y"] - x["y"])
        n = x["next_sector"]
        if n >= 0 and S[n]["ceiling_stat"] & 1:
            continue
        if n >= 0:
            openings[round(L)] += 1
        tw = sizes.get(x["picnum"], (0, 0))[0]
        if not tw or not x["x_repeat"]:
            c["no size"] += 1
            continue
        c["n"] += 1
        upp = L / (x["x_repeat"] * 8)
        if abs(upp - 16) <= 0.5:
            c["16"] += 1
    print(name, dict(c))
    if name == "E3M1":
        print("  roofed openings off the street, by length:", openings.most_common(6))
