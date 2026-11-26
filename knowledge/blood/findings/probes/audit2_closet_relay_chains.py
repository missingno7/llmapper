"""Counts the campaign's wiring chains (bloodmap.wiring.chains) and those passing through a relay where no player goes, by the relay's type."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[4]))
from collections import Counter
from bloodmap.corpus import campaign_maps
from bloodmap.format import read_map
from bloodmap.reachability import sector_kinds
from bloodmap import wiring

total = through = 0
relay_types = Counter()
for p in campaign_maps():
    d = read_map(p)
    reach = sector_kinds(d)
    nodes = {n["id"]: n for n in wiring.nodes(d)}
    for c in wiring.chains(d, reach=reach):
        total += 1
        if c["closet_relays"]:
            through += 1
            for r in c["closet_relays"]:
                n = nodes[r]
                relay_types[(n["kind"], n["type"], n["type_name"])] += 1
print("chains", total, "through a closet relay", through)
switch = sum(v for (k, t, _), v in relay_types.items() if t in (20, 21, 22))
print("relay occurrences", sum(relay_types.values()), "of which switches 20-22", switch)
for key, v in relay_types.most_common(12):
    print(key, v)
