"""Count the campaign's lever sprites (tile 1070): how many, wall-aligned, with a tx, by command, and their trigger flags."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[4]))
import os
import sys
from collections import Counter

from bloodmap.corpus import campaign_maps
from bloodmap.format import read_map
from bloodmap.model import record_extra, record_fields

total = wall = with_tx = push = on = off = 0
commands = Counter()
types = Counter()
for path in campaign_maps():
    disk = read_map(path)
    for record in disk.sprites:
        f = record_fields(record)
        if int(f["picnum"]) != 1070:
            continue
        total += 1
        if int(f["cstat"]) & 0x30 == 0x10:
            wall += 1
        types[int(f["type"])] += 1
        x = record_extra(record) or {}
        if int(x.get("tx_id", 0) or 0):
            with_tx += 1
        commands[int(x.get("command", 0) or 0)] += 1
        push += bool(x.get("trigger_push"))
        on += bool(x.get("trigger_on"))
        off += bool(x.get("trigger_off"))
print("sprites", total, "wall-aligned", wall, "with tx", with_tx)
print("commands", commands.most_common())
print("types", types.most_common())
print("trigger_push", push, "trigger_on", on, "trigger_off", off)
