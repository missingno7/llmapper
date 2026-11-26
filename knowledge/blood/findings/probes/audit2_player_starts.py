"""Player start markers in the 43 campaign maps: type-1 and type-2 counts, their pictures, whether the header start matches type 1 number 0, and where the first type-1 marker by index is not number 0."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[4]))
import os
import sys
from collections import Counter

from bloodmap.corpus import campaign_maps
from bloodmap.format import read_map
from bloodmap.model import record_extra, record_fields

ones, twos, pics, disagree, first_wrong, missing = Counter(), Counter(), Counter(), [], [], []
for path in campaign_maps():
    disk = read_map(path)
    name = path.stem.upper()
    sp = []
    for index, s in enumerate(disk.sprites):
        f = record_fields(s)
        t = int(f["type"])
        if t in (1, 2):
            x = record_extra(s) or {}
            sp.append((index, t, int(x.get("data_1", 0) or 0), int(f["x"]), int(f["y"]), int(f["picnum"])))
            if t == 2:
                pics[int(f["picnum"])] += 1
    ones[sum(1 for r in sp if r[1] == 1)] += 1
    twos[sum(1 for r in sp if r[1] == 2)] += 1
    zero = [r for r in sp if r[1] == 1 and r[2] == 0]
    if not zero:
        missing.append(name)
        continue
    hx, hy = int(disk.header["start_x"]), int(disk.header["start_y"])
    if (hx, hy) != (zero[0][3], zero[0][4]):
        disagree.append(name)
    first = min((r for r in sp if r[1] == 1), key=lambda r: r[0])
    if first[2] != 0:
        first_wrong.append(name)
print("type-1 markers per map", sorted(ones.items()), "type-2 per map", sorted(twos.items()))
print("type-2 pictures", sorted(pics.items()))
print("no type-1 number 0", missing)
print("header start differs from type 1 number 0:", len(disagree))
print("first type-1 marker by index is not number 0:", first_wrong)
