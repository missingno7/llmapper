"""Over the 43 campaign maps: rotating sectors (types 613/615/617) started by rx 7 with both waves retriggering, with their busy times and the sprites they carry."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[4]))
from collections import Counter
from bloodmap.format import read_map
from bloodmap.corpus import campaign_maps
from bloodmap.model import record_fields, record_extra

found = []
for p in campaign_maps():
    m = read_map(p)
    by_sector = {}
    for i, sp in enumerate(m.sprites):
        by_sector.setdefault(record_fields(sp)["sector"], []).append(record_fields(sp)["picnum"])
    for i, s in enumerate(m.sectors):
        f = record_fields(s)
        if f["type"] not in (613, 615, 617):
            continue
        x = record_extra(s) or {}
        if x.get("rx_id") == 7 and x.get("retrigger_a") and x.get("retrigger_b"):
            found.append((p.stem, i, f["type"], x["busy_time_a"], x["busy_time_b"], x.get("key"), x.get("trigger_push"), x.get("trigger_wall_push"), x.get("marker_0"), sorted(by_sector.get(i, []))))
for row in found:
    print(row)
print(len(found), "in", len({r[0] for r in found}), "maps", Counter(r[2] for r in found))
