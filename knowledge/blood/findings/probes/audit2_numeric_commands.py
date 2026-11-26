"""Count the objects in the 43 campaign maps whose command is 64 or more (kCmdNumberic), by the channel they send on."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[4]))
import os
import sys
from collections import Counter

from bloodmap.corpus import campaign_maps
from bloodmap.format import read_map
from bloodmap.model import record_extra

by_channel = Counter()
maps = set()
total = 0
for path in campaign_maps():
    disk = read_map(path)
    for kind, records in (("sector", disk.sectors), ("wall", disk.walls), ("sprite", disk.sprites)):
        for record in records:
            extra = record_extra(record)
            if not extra or int(extra.get("command", 0)) < 64:
                continue
            total += 1
            maps.add(path.stem.upper())
            by_channel[int(extra.get("tx_id", 0))] += 1
print("objects", total, "maps", len(maps), "of", len(campaign_maps()))
print("by tx channel", by_channel.most_common())
