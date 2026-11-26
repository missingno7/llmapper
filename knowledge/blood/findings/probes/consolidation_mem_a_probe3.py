"""Count campaign link markers by statnum and tile."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[4]))
from collections import Counter
from bloodmap.corpus import campaign_maps
from bloodmap.format import read_map
from bloodmap.model import record_fields
c = Counter()
for p in campaign_maps():
    m = read_map(p)
    for s in m.sprites:
        f = record_fields(s)
        t = f.get("type")
        if t in (6, 7, 9, 10, 11, 12, 13, 14):
            c[("all", f.get("statnum"), f.get("picnum"))] += 1
            if t in (11, 12): c[("stack", t)] += 1
print(sorted(c.items(), key=lambda kv: -kv[1])[:12])
