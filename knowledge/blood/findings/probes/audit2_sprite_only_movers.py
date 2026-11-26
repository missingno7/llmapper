"""Marked slide/rotate sectors (614/615) in the 43 campaign maps that flag no wall to move but flag sprites to ride, and how many set the XSECTOR drag bit."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[4]))
import os
import sys

from bloodmap.corpus import campaign_maps
from bloodmap.format import read_map
from bloodmap.model import record_extra, record_fields

only_sprites = []
marked = 0
for path in campaign_maps():
    disk = read_map(path)
    by_sector = {}
    for index, sprite in enumerate(disk.sprites):
        f = record_fields(sprite)
        if int(f["cstat"]) & (8192 | 16384):
            by_sector.setdefault(int(f["sector"]), []).append(index)
    for sid, sector in enumerate(disk.sectors):
        s = record_fields(sector)
        if s["type"] not in (614, 615):
            continue
        marked += 1
        walls = range(s["wall_ptr"], s["wall_ptr"] + s["wall_count"])
        flagged = [w for w in walls if int(record_fields(disk.walls[w])["cstat"]) & (16384 | 32768)]
        riders = by_sector.get(sid, [])
        if not flagged and riders:
            extra = record_extra(sector) or {}
            only_sprites.append((path.stem.upper(), sid, s["type"], len(riders), int(extra.get("drag", 0) or 0)))
print("marked 614/615 sectors", marked, "moving sprites only", len(only_sprites))
for row in only_sprites:
    print(row)
