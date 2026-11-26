"""Over the 43 campaign maps: sectors with a non-zero XSECTOR amplitude (animated shade) per map, the floor-shade median of those sectors, and user channels (100 and up, counted as tools/mine_mechanisms.py does) per map with their median."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[4]))
import statistics
from bloodmap.format import read_map
from bloodmap.corpus import campaign_maps
from bloodmap.model import record_fields, record_extra

rows = []
for p in campaign_maps():
    m = read_map(p)
    anim, shades = 0, []
    for s in m.sectors:
        x = record_extra(s)
        if x and x.get("amplitude", 0):
            anim += 1
            shades.append(record_fields(s)["floor_shade"])
    chans = set()
    for items in (m.sprites, m.sectors, m.walls):
        for it in items:
            x = record_extra(it)
            if not x:
                continue
            for key in ("tx_id", "rx_id"):
                if x.get(key, 0) >= 100:
                    chans.add(x[key])
    rows.append((p.stem, anim, len(m.sectors), statistics.median(shades) if shades else None, len(chans)))
for name, a, n, med, ch in sorted(rows, key=lambda r: -r[1] / r[2]):
    print(f"{name}: animated {a}/{n} ({100*a/n:.1f}%), floor-shade median of animated {med}, user channels {ch}")
print("campaign median user channels:", statistics.median(r[4] for r in rows), "max:", max(rows, key=lambda r: r[4]))
