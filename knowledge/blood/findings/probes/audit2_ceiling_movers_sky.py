"""Over the 43 campaign maps: Z-motion sectors (type 600/602 with an XSECTOR) that move their ceiling or floor, and how many of each have a parallax (sky) ceiling."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[4]))
from collections import Counter
from bloodmap.format import read_map
from bloodmap.corpus import campaign_maps
from bloodmap.model import record_fields, record_extra

ceil_n = ceil_sky = floor_n = floor_sky = 0
where = Counter()
for p in campaign_maps():
    m = read_map(p)
    for s in m.sectors:
        f = record_fields(s)
        if f["type"] not in (600, 602):
            continue
        x = record_extra(s)
        if not x or "on_ceiling_z" not in x:
            continue
        sky = bool(f["ceiling_stat"] & 1)
        if x["on_ceiling_z"] != x["off_ceiling_z"]:
            ceil_n += 1
            if sky:
                ceil_sky += 1
                where[p.stem] += 1
        if x["on_floor_z"] != x["off_floor_z"]:
            floor_n += 1
            floor_sky += sky
print(f"ceiling moves: {ceil_sky}/{ceil_n} open to the sky ({100*ceil_sky/ceil_n:.1f}%) in {dict(where)}")
print(f"floor moves: {floor_sky}/{floor_n} open to the sky ({100*floor_sky/floor_n:.1f}%)")
