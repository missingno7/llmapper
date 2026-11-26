"""Over the 43 campaign maps: room-over-room link pairs per map, counted as upper link markers (types 6, 9, 11, 13) and lower ones (7, 10, 12, 14), with the histogram of pairs per map."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[4]))
from collections import Counter
from bloodmap.format import read_map
from bloodmap.corpus import campaign_maps
from bloodmap.model import record_fields

UP, LOW = {6, 9, 11, 13}, {7, 10, 12, 14}
per = {}
for p in campaign_maps():
    m = read_map(p)
    types = Counter(record_fields(s)["type"] for s in m.sprites)
    up, low = sum(types[t] for t in UP), sum(types[t] for t in LOW)
    per[p.stem] = (up, low)
print("maps with none:", sorted(k for k, v in per.items() if v[0] == 0 and v[1] == 0))
print("histogram of upper markers per map:", sorted(Counter(v[0] for v in per.values()).items()))
print({k: v for k, v in per.items() if v[0] != v[1]})
