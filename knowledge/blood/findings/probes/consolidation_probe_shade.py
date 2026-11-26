"""Floor shade of sky sectors vs roofed sectors per map: mean, area-weighted mean, median."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[4]))
import sys, statistics as st
from bloodmap.format import read_map
from bloodmap.corpus import corpus_map_path
from bloodmap.model import record_fields

for name in sys.argv[1:]:
    m = read_map(corpus_map_path(name))
    W = [record_fields(w) for w in m.walls]
    out = {True: [], False: []}
    for s in map(record_fields, m.sectors):
        a = 0
        for wi in range(s["wall_ptr"], s["wall_ptr"] + s["wall_count"]):
            w = W[wi]; p = W[w["point2"]]
            a += w["x"] * p["y"] - p["x"] * w["y"]
        out[bool(s["ceiling_stat"] & 1)].append((s["floor_shade"], abs(a) / 2))
    for sky, rows in out.items():
        tot = sum(a for _, a in rows) or 1
        print(name, "sky" if sky else "roofed", len(rows), "median", st.median(r for r, _ in rows), "area-mean", round(sum(r * a for r, a in rows) / tot, 1))
