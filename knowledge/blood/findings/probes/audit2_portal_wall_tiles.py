"""Campaign sectors with more than one wall tile and both two-sided and solid walls: how many put on a two-sided wall a tile none of their solid walls wears (two readings)."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[4]))
import os
import sys
from collections import Counter

from bloodmap.corpus import campaign_maps
from bloodmap.format import read_map
from bloodmap.model import record_fields

rooms = any_other = modal_differs = with_both = 0
for path in campaign_maps():
    disk = read_map(path)
    walls = [record_fields(w) for w in disk.walls]
    for s in map(record_fields, disk.sectors):
        own = walls[s["wall_ptr"]:s["wall_ptr"] + s["wall_count"]]
        if len({int(w["picnum"]) for w in own}) < 2:
            continue
        rooms += 1
        two = Counter(int(w["picnum"]) for w in own if int(w["next_sector"]) >= 0)
        solid = Counter(int(w["picnum"]) for w in own if int(w["next_sector"]) < 0)
        if not two or not solid:
            continue
        with_both += 1
        any_other += bool(set(two) - set(solid))
        modal_differs += two.most_common(1)[0][0] != solid.most_common(1)[0][0]
print("sectors with more than one wall tile", rooms, "with both kinds of wall", with_both)
print("a two-sided tile no solid wall wears", any_other, f"{any_other / rooms:.0%} of all, {any_other / with_both:.0%} of both")
print("modal two-sided tile differs from modal solid", modal_differs, f"{modal_differs / rooms:.0%} of all, {modal_differs / with_both:.0%} of both")
