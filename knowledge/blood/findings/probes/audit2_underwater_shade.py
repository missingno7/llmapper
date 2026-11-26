"""Floor and ceiling shades of the campaign's underwater sectors (XSECTOR underwater flag): quartiles, and how many carry a shade wave."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[4]))
import os
import statistics
import sys

from bloodmap.corpus import campaign_maps
from bloodmap.format import read_map
from bloodmap.model import record_extra, record_fields

floors, ceilings, waved, n = [], [], 0, 0
for path in campaign_maps():
    disk = read_map(path)
    for s in disk.sectors:
        x = record_extra(s) or {}
        if not int(x.get("underwater", 0) or 0):
            continue
        f = record_fields(s)
        n += 1
        floors.append(int(f["floor_shade"]))
        ceilings.append(int(f["ceiling_shade"]))
        waved += bool(int(x.get("shade_wave", 0) or 0) and int(x.get("amplitude", 0) or 0))
q = lambda v: [statistics.quantiles(v, n=4)[0], statistics.median(v), statistics.quantiles(v, n=4)[2]]
print("underwater sectors", n, "floor q1/median/q3", q(floors), "ceiling", q(ceilings), "with a shade wave", waved)
