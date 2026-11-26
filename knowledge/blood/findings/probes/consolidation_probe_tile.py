"""Where a tile stands in the campaign: alignment, height over floor and under ceiling, sky or roof."""
import sys, collections, statistics as st
from bloodmap.format import read_map
from bloodmap.corpus import campaign_maps
from bloodmap.model import record_fields, record_extra

tile = int(sys.argv[1]); show = int(sys.argv[2]) if len(sys.argv) > 2 else 8
rows = []
for p in campaign_maps():
    m = read_map(p)
    for i, s in enumerate(m.sprites):
        f = record_fields(s)
        if f["picnum"] != tile or f["sector"] < 0:
            continue
        sf = record_fields(m.sectors[f["sector"]])
        rows.append(dict(map=p.stem.upper(), i=i, align=(f["cstat"] >> 4) & 3, cstat=f["cstat"], type=f["type"], stat=f["status"],
                         over_floor=sf["floor_z"] - f["z"], under_ceil=f["z"] - sf["ceiling_z"], sky=sf["ceiling_stat"] & 1,
                         rep=(f["x_repeat"], f["y_repeat"]), shade=f["shade"]))
print("n", len(rows), "maps", len({r["map"] for r in rows}))
print("align", collections.Counter(r["align"] for r in rows), "type", collections.Counter(r["type"] for r in rows).most_common(5),
      "sky", sum(r["sky"] for r in rows))
print("over floor median", st.median(r["over_floor"] for r in rows), "under ceiling median", st.median(r["under_ceil"] for r in rows))
print("under ceiling quartiles", sorted(r["under_ceil"] for r in rows)[len(rows)//4], sorted(r["under_ceil"] for r in rows)[3*len(rows)//4])
for r in rows[:show]:
    print(r)
