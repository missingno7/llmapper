"""Count the scene components (sky networks unreachable from the start) of at least 20M area in 6 sectors or fewer over the 43 campaign maps, by tools/mine_city_norms.street_component."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[4]))
from bloodmap.corpus import campaign_maps
from tools.mine_city_norms import load_source, street_component

total, big = 0, []
for path in campaign_maps():
    name = Path(path).stem.upper()
    geom = load_source(name, "blood", str(path))
    try:
        street_component(geom)
    except Exception as exc:                      # a map the street reader cannot take
        print(name, "unreadable:", exc)
        continue
    for comp in getattr(geom, "scene_components", []):
        area = sum(geom.area[s] for s in comp)
        walls = sum(len(geom.sector_walls[s]) for s in comp)
        total += 1
        if area >= 20_000_000 and len(comp) <= 6:
            big.append((name, len(comp), walls, round(area / 1e6), sorted(comp)[:3]))
print("scene components:", total, "of >=20M in <=6 sectors:", len(big))
for row in sorted(big, key=lambda r: -r[3])[:8]:
    print(row)
for row in big:
    if row[0] in ("E2M1", "E4M1", "E2M6"):
        print(row)
