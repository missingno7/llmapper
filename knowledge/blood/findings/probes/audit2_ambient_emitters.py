"""Over the 43 campaign maps: type 710 ambient emitters, their statnum, owner, cstat, shade, state, data_4 and radius order."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[4]))
from collections import Counter
from bloodmap.format import read_map
from bloodmap.corpus import campaign_maps
from bloodmap.model import record_fields, record_extra

c = Counter()
for p in campaign_maps():
    m = read_map(p)
    for s in m.sprites:
        f = record_fields(s)
        if f["type"] != 710:
            continue
        x = record_extra(s) or {}
        c["n"] += 1
        c[f"status {f['status']}"] += 1
        c[f"owner {f['owner']}"] += 1
        c[f"cstat {f['cstat']}"] += 1
        c[f"shade {f['shade']}"] += 1
        c[f"state {x.get('state')}"] += 1
        c[f"data_4 {x.get('data_4')}"] += 1
        c["data_1 < data_2" if x.get("data_1", 0) < x.get("data_2", 0) else "data_1 >= data_2"] += 1
        if f["status"] == 12 and x.get("state") == 1 and x.get("data_1", 0) < x.get("data_2", 0):
            c["active (stat 12, state 1, d1<d2)"] += 1
for k, v in c.most_common(25):
    print(v, k)
