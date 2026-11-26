"""E3M1: share of wall length per tile on walls bounding sky sectors (one-sided, or two-sided onto a roofed neighbour)."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[4]))
import collections, math
from bloodmap.format import read_map
from bloodmap.corpus import corpus_map_path
from bloodmap.model import record_fields

m = read_map(corpus_map_path("E3M1"))
W = [record_fields(w) for w in m.walls]
S = [record_fields(s) for s in m.sectors]
print(list(W[0].keys()))
by = {k: collections.Counter() for k in ("one_sided", "onto_roofed", "both", "both_tall")}
for si, s in enumerate(S):
    if not s["ceiling_stat"] & 1:
        continue
    for wi in range(s["wall_ptr"], s["wall_ptr"] + s["wall_count"]):
        w = W[wi]; p2 = W[w["point2"]]
        L = math.hypot(p2["x"] - w["x"], p2["y"] - w["y"])
        ns = w["next_sector"]
        kind = None
        if ns < 0:
            kind = "one_sided"
        elif not S[ns]["ceiling_stat"] & 1:
            kind = "onto_roofed"
        if kind:
            by[kind][w["picnum"]] += L
            by["both"][w["picnum"]] += L
            h = (s["floor_z"] - s["ceiling_z"]) if ns < 0 else (S[ns]["ceiling_z"] - s["ceiling_z"])
            if abs(h) >= 16960 * 2:
                by["both_tall"][w["picnum"]] += L
for k, c in by.items():
    tot = sum(c.values())
    print(k, int(tot), [(t, round(100 * v / tot, 1)) for t, v in c.most_common(8)], "distinct", len(c))
