"""Count the XSPRITE launch_skill (lSkill) masks over the 43 campaign maps: sprites per non-zero mask."""
import collections
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[4]))
from bloodmap.corpus import campaign_maps  # noqa: E402
from bloodmap.format import read_map  # noqa: E402
from bloodmap.model import record_extra  # noqa: E402

masks = collections.Counter()
for path in campaign_maps():
    for s in read_map(path).sprites:
        x = record_extra(s) or {}
        if x.get("launch_skill"):
            masks[x["launch_skill"]] += 1
print("masked sprites", sum(masks.values()), "masks", len(masks))
for mask, n in masks.most_common():
    print(f"{mask:2d} {mask:05b} {n}")
