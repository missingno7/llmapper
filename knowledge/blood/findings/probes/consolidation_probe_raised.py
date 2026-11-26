"""Raised blocks: roofed sectors whose floor stands above every neighbour, rise = min neighbour floor - own floor, per map or over the campaign."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[4]))
import sys, math, statistics as st
from bloodmap.format import read_map
from bloodmap.corpus import campaign_maps, corpus_map_path
from bloodmap.model import record_fields

ISLAND = "--island" in sys.argv
names = [a for a in sys.argv[1:] if not a.startswith("--")]
paths = [corpus_map_path(n) for n in names] if names else campaign_maps()
rises = []
for p in paths:
    m = read_map(p)
    W = [record_fields(w) for w in m.walls]; S = [record_fields(s) for s in m.sectors]
    for si, s in enumerate(S):
        if s["ceiling_stat"] & 1 or s["floor_heinum"]:
            continue
        ws = range(s["wall_ptr"], s["wall_ptr"] + s["wall_count"])
        nbs = {W[w]["next_sector"] for w in ws} - {-1}
        if not nbs or (ISLAND and any(W[w]["next_sector"] < 0 for w in ws)):
            continue  # an island block: every side opens on a neighbour
        r = min(S[n]["floor_z"] for n in nbs) - s["floor_z"]
        if max(S[n]["floor_z"] for n in nbs) - s["floor_z"] < 512: continue
        xs = [W[w]["x"] for w in ws]; ys = [W[w]["y"] for w in ws]
        span = max(max(xs) - min(xs), max(ys) - min(ys))
        if 512 <= r <= 16960 and span <= 4096 and s["floor_z"] - s["ceiling_z"] > 8192:
            rises.append((r, p.stem.upper(), si))
v = sorted(r for r, *_ in rises)
print(len(v), "median", st.median(v) if v else None, "q1", v[len(v)//4] if v else None, "q3", v[3*len(v)//4] if v else None)
import collections; print(collections.Counter(v).most_common(8))
if names: print(rises[:40])
