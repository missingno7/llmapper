"""E3M1's street headers taken as walls of a sky sector whose next sector is roofed with a lower ceiling (an upper step over an opening), and how many carry wall cstat 4."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[4]))
from bloodmap.format import read_map
from bloodmap.corpus import corpus_map_path
from bloodmap.model import record_fields

m = read_map(corpus_map_path("E3M1"))
secs = [record_fields(s) for s in m.sectors]
n = with4 = 0
for i, f in enumerate(secs):
    if not f["ceiling_stat"] & 1:
        continue
    for w in range(f["wall_ptr"], f["wall_ptr"] + f["wall_count"]):
        wf = record_fields(m.walls[w])
        o = wf["next_sector"]
        if o < 0 or secs[o]["ceiling_stat"] & 1:
            continue
        if secs[o]["ceiling_z"] > f["ceiling_z"]:
            n += 1
            with4 += bool(wf["cstat"] & 4)
print("headers", n, "with cstat 4", with4)
