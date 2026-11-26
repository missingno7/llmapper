"""Every sender on the exit channel 4 in the 43 campaign maps: its kind, type, tile and trigger, and which maps have one wearing tile 318."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[4]))
import os
import sys

from bloodmap.corpus import campaign_maps
from bloodmap.format import read_map
from bloodmap.model import record_extra, record_fields

with_318 = []
for path in campaign_maps():
    disk = read_map(path)
    senders = []
    for kind, records in (("sector", disk.sectors), ("wall", disk.walls), ("sprite", disk.sprites)):
        for index, record in enumerate(records):
            extra = record_extra(record)
            if not extra or int(extra.get("tx_id", 0)) != 4:
                continue
            f = record_fields(record)
            how = [k for k in ("trigger_push", "trigger_enter", "trigger_on", "trigger_off", "trigger_vector", "trigger_touch") if extra.get(k)]
            senders.append((kind, index, f.get("type"), f.get("picnum"), int(extra.get("rx_id", 0)), how))
    if any(s[0] == "sprite" and s[3] == 318 for s in senders):
        with_318.append(path.stem.upper())
    else:
        print(path.stem.upper(), senders)
print(len(with_318), "of", len(campaign_maps()), "maps have a channel-4 sender wearing 318")
