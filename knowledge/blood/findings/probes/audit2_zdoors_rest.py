"""Over the 43 campaign maps: type 600 sectors whose ceiling moves and floor stays, split by whether they are shut in the OFF pose (off_ceiling_z == off_floor_z) or in the ON pose."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[4]))
from collections import Counter
from bloodmap.format import read_map
from bloodmap.corpus import campaign_maps
from bloodmap.model import record_fields, record_extra

c = Counter()
for p in campaign_maps():
    for s in read_map(p).sectors:
        if record_fields(s)["type"] != 600:
            continue
        x = record_extra(s)
        if not x:
            continue
        if x["on_ceiling_z"] != x["off_ceiling_z"] and x["on_floor_z"] == x["off_floor_z"]:
            c["ceiling moves, floor fixed"] += 1
            c["shut when OFF"] += x["off_ceiling_z"] == x["off_floor_z"]
            c["shut when ON"] += x["on_ceiling_z"] == x["on_floor_z"]
            # the pose it starts in is its state's (trInit, triggers.cpp:2248-2250)
            pose = "on" if int(x.get("state", 0)) else "off"
            c["shut at rest"] += x[f"{pose}_ceiling_z"] == x[f"{pose}_floor_z"]
            c["shut when ON and starting ON"] += pose == "on" and x["on_ceiling_z"] == x["on_floor_z"]
            c["shut when OFF and starting ON"] += pose == "on" and x["off_ceiling_z"] == x["off_floor_z"]
print(dict(c))
