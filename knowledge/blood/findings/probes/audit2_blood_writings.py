"""Count the blood-writing sprites 826, 1105 and 2345 over the 43 campaign maps: where, at what repeat and shade, how high their middle stands, and whether their sector is open to the sky."""
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[4]))
from bloodmap.corpus import campaign_maps
from bloodmap.format import read_map
from bloodmap.model import record_fields

BODY = 16960
TILES = (826, 1105, 2345)
per, maps = Counter(), {t: set() for t in TILES}
for path in campaign_maps():
    disk = read_map(path)
    for sprite in disk.sprites:
        f = record_fields(sprite)
        if f["picnum"] not in TILES or f["sector"] < 0:
            continue
        sec = record_fields(disk.sectors[f["sector"]])
        sky = bool(sec["ceiling_stat"] & 1)
        up = (sec["floor_z"] - f["z"]) / BODY        # cstat 128 centres the art on z; otherwise z is the bottom
        per[f["picnum"]] += 1
        maps[f["picnum"]].add(Path(path).stem)
        print(Path(path).stem, f["picnum"], "repeat", f["x_repeat"], f["y_repeat"], "shade", f["shade"], "cstat", f["cstat"],
              "z above floor (bodies)", round(up, 2), "sky" if sky else "indoors")
print({t: (per[t], len(maps[t])) for t in TILES})
