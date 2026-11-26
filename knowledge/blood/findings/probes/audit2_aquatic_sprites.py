"""Counts sprites of the wet-only tiles (664, 660, 546 and the rest of furniture.wet_only) over the 43 campaign maps by whether their sector is under water."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[4]))
from collections import defaultdict
from bloodmap.format import read_map
from bloodmap.corpus import campaign_maps
from bloodmap.model import record_fields, record_extra
from bloodmap.furniture import wet_only

wet = sorted(wet_only())
print("wet_only", wet)
n = defaultdict(int)
sectors = defaultdict(set)
dry = defaultdict(list)
shallow = defaultdict(int)
invisible = defaultdict(int)
for p in campaign_maps():
    m = read_map(p)
    name = p.stem.upper()
    for i, s in enumerate(m.sprites):
        f = record_fields(s)
        t = f["picnum"]
        if t not in wet:
            continue
        if f["cstat"] & 0x8000:
            invisible[t] += 1
            continue
        n[t] += 1
        sectors[t].add((name, f["sector"]))
        x = record_extra(m.sectors[f["sector"]]) or {}
        if not x.get("underwater"):
            dry[t].append(f"{name} sprite {i}")
            if x.get("depth"):
                shallow[t] += 1
for t in wet:
    print(t, "sprites", n[t], "sectors", len(sectors[t]), "not under water", len(dry[t]), "in depth water", shallow[t], "invisible skipped", invisible[t], dry[t][:8])
