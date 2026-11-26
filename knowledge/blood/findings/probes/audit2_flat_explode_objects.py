"""Counts floor-aligned explode (417) and gib (416) objects over the 43 campaign maps, and how many block."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[4]))
from bloodmap.format import read_map
from bloodmap.corpus import campaign_maps, corpus_map_path
from bloodmap.model import record_fields, record_extra

counts = {417: [0, 0], 416: [0, 0]}
maps = 0
for p in campaign_maps():
    maps += 1
    m = read_map(p)
    for s in m.sprites:
        f = record_fields(s)
        if f["type"] in counts and (f["cstat"] & 0x30) == 0x20:
            counts[f["type"]][0] += 1
            if f["cstat"] & 1:
                counts[f["type"]][1] += 1
print("maps", maps)
for t, (n, b) in counts.items():
    print(f"type {t}: floor-aligned {n}, blocking {b}")
for name, i in (("E1M4", 277), ("E4M9", 290)):
    m = read_map(corpus_map_path(name))
    f = record_fields(m.sprites[i])
    x = record_extra(m.sprites[i]) or {}
    print(name, i, "type", f["type"], "picnum", f["picnum"], "cstat", f["cstat"], "data1", x.get("data_1"))
