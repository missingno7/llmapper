"""E2M1's reachable sectors split by sky ceiling: mean floor shade outdoors and indoors, and sky sectors that share a wall with a roofed one."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[4]))
import statistics as st
from bloodmap.format import read_map
from bloodmap.corpus import corpus_map_path
from bloodmap.model import record_fields
from bloodmap.reachability import sector_kinds

d = read_map(corpus_map_path("E2M1"))
kinds = sector_kinds(d)
reach = [i for i in range(len(d.sectors)) if kinds.get(i) == "reachable"]
sky = {i for i in reach if record_fields(d.sectors[i])["ceiling_stat"] & 1}
roofed = set(reach) - sky
shade = {i: record_fields(d.sectors[i])["floor_shade"] for i in reach}
print("sky", len(sky), round(st.mean(shade[i] for i in sky), 1), "roofed", len(roofed), round(st.mean(shade[i] for i in roofed), 1))
steps = []
for i in sorted(sky):
    f = record_fields(d.sectors[i])
    for w in range(f["wall_ptr"], f["wall_ptr"] + f["wall_count"]):
        n = record_fields(d.walls[w])["next_sector"]
        if n in roofed:
            steps.append((i, n, shade[n] - shade[i]))
print("sky|roofed thresholds", len(steps), "mean step", round(st.mean(s for _, _, s in steps), 1))
print(steps[:12])
