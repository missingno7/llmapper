"""Count type-710 ambient sound sprites in each of the 43 campaign maps: total, median, mean, range, per hundred sectors, and the maps with none or the most."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[4]))
import os
import statistics
import sys

from bloodmap.corpus import campaign_maps
from bloodmap.format import read_map
from bloodmap.model import record_fields

rows = []
for path in campaign_maps():
    disk = read_map(path)
    n = sum(1 for s in disk.sprites if int(record_fields(s)["type"]) == 710)
    rows.append((path.stem.upper(), n, 100 * n / len(disk.sectors)))
counts = [r[1] for r in rows]
print("maps", len(rows), "total", sum(counts), "median", statistics.median(counts),
      "mean", round(statistics.mean(counts), 1), "range", min(counts), max(counts))
print("median per 100 sectors", round(statistics.median(r[2] for r in rows), 1))
print("none", [r[0] for r in rows if r[1] == 0])
print("most", sorted(rows, key=lambda r: -r[1])[:3])
