"""Campaign sectors whose visibility byte is 240-255 (less distance fog), by map and value."""
import sys; sys.path.insert(0, ".")
from collections import Counter
from bloodmap.corpus import campaign_maps
from bloodmap.format import read_map
from bloodmap.model import record_fields as F
per_map, values, other = Counter(), Counter(), Counter()
for path in campaign_maps():
    for s in read_map(path).sectors:
        v = F(s)["visibility"]
        if v >= 240:
            per_map[path.stem] += 1; values[v] += 1
        elif v:
            other[v] += 1
print("sectors at 240-255:", sum(per_map.values()), dict(per_map), "values", dict(sorted(values.items())))
print("sectors at 1-239:", sum(other.values()))
