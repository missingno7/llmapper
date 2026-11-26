"""Foes met on each of the five difficulties over the 43 campaign maps (types 201-250 and 18, as difficulty._foe), against the middle one: pooled and by a map's median."""
import statistics
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[4]))
from bloodmap.corpus import campaign_maps  # noqa: E402
from bloodmap.format import read_map  # noqa: E402
from bloodmap.model import record_extra, record_fields  # noqa: E402

total = [0] * 5
per_map = []
for path in campaign_maps():
    counts = [0] * 5
    for s in read_map(path).sprites:
        f = record_fields(s)
        if not (201 <= f["type"] <= 250 or f["type"] == 18):
            continue
        mask = int((record_extra(s) or {}).get("launch_skill") or 0)
        for k in range(5):
            if not mask >> k & 1:
                counts[k] += 1
    total = [a + b for a, b in zip(total, counts)]
    if counts[2]:
        per_map.append([c / counts[2] for c in counts])
print("foes per difficulty", total)
print("pooled against the middle", [round(t / total[2], 2) for t in total])
print("median of maps", [round(statistics.median(r[k] for r in per_map), 2) for k in range(5)], "maps", len(per_map))
