"""Campaign link markers (types 6/7, 9/10, 11/12, 13/14): count by type, statnum, tile and cstat."""
import sys; sys.path.insert(0, ".")
from collections import Counter
from bloodmap.corpus import campaign_maps
from bloodmap.format import read_map
from bloodmap.model import record_fields as F
by_type, status, tile, cstat = Counter(), Counter(), Counter(), Counter()
for path in campaign_maps():
    for s in read_map(path).sprites:
        f = F(s)
        if f["type"] in (6, 7, 9, 10, 11, 12, 13, 14):
            by_type[f["type"]] += 1; status[f["status"]] += 1; tile[f["picnum"]] += 1; cstat[f["cstat"]] += 1
print("total", sum(by_type.values()), "by type", dict(sorted(by_type.items())))
print("statnum", dict(status), "tile", dict(tile), "cstat", dict(cstat.most_common()))
