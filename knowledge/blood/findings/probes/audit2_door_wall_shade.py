"""Walls facing a type-600 (Z-motion) sector in E3M1, E3M2, E1M1, E6M1 and E4M9: their shade minus the median wall shade of the sector they belong to."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[4]))
import os
import statistics
import sys

from bloodmap.corpus import corpus_map_path
from bloodmap.format import read_map
from bloodmap.model import record_fields

deltas = []
for name in ("E3M1", "E3M2", "E1M1", "E6M1", "E4M9"):
    disk = read_map(corpus_map_path(name))
    sectors = [record_fields(s) for s in disk.sectors]
    walls = [record_fields(w) for w in disk.walls]
    for index, s in enumerate(sectors):
        if int(s["type"]) == 600:
            continue
        own = walls[s["wall_ptr"]:s["wall_ptr"] + s["wall_count"]]
        median = statistics.median(int(w["shade"]) for w in own)
        for w in own:
            n = int(w["next_sector"])
            if n >= 0 and int(sectors[n]["type"]) == 600:
                deltas.append(int(w["shade"]) - median)
q = statistics.quantiles(deltas, n=10)
print("walls", len(deltas), "median", statistics.median(deltas), "p10", q[0], "p90", q[-1])
