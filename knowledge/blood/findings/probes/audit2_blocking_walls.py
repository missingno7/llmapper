"""Over the 43 campaign maps: two-sided walls with the blocking bit (cstat 1), counted as records and as pairs, how many are kWallGib (type 511), and of the gib walls how many start in state 0 and have an rx channel."""
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
    walls = [record_fields(w) for w in m.walls]
    pairs = set()
    for i, w in enumerate(walls):
        if w["next_wall"] < 0:
            continue
        other = walls[w["next_wall"]]
        if w["cstat"] & 1:
            c["records"] += 1
            if w["type"] == 511:
                c["records 511"] += 1
        if (w["cstat"] | other["cstat"]) & 1:
            pairs.add(frozenset((i, w["next_wall"])))
    for pair in pairs:
        c["pairs"] += 1
        a, b = tuple(pair) if len(pair) == 2 else (next(iter(pair)),) * 2
        if 511 in (walls[a]["type"], walls[b]["type"]):
            c["pairs 511"] += 1
    for i, w in enumerate(walls):
        if w["type"] == 511:
            x = record_extra(m.walls[i]) or {}
            c["gib walls"] += 1
            c["gib two-sided"] += w["next_wall"] >= 0
            c["gib blocking"] += bool(w["cstat"] & 1)
            c["gib state 0"] += x.get("state", 0) == 0
            c["gib with rx"] += x.get("rx_id", 0) > 0
for k, v in sorted(c.items()):
    print(k, v)
