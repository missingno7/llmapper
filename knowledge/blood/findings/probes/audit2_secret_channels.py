"""Per campaign map: the secret totals declared on channel 1 (command 64+n) and the senders on channel 2, by kind (sector, wall, sprite)."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[4]))
import os
import sys
from collections import Counter

from bloodmap.corpus import campaign_maps
from bloodmap.format import read_map
from bloodmap.model import record_extra

declares, credits, kinds, totals, multi = 0, 0, Counter(), {}, {}
for path in campaign_maps():
    disk = read_map(path)
    name = path.stem.upper()
    seen_total, seen_credit = [], False
    for kind, records in (("sector", disk.sectors), ("wall", disk.walls), ("sprite", disk.sprites)):
        for record in records:
            x = record_extra(record) or {}
            tx, cmd = int(x.get("tx_id", 0) or 0), int(x.get("command", 0) or 0)
            if tx == 1 and cmd >= 64:
                seen_total.append(cmd - 64)
            if tx == 2:
                seen_credit = True
                kinds[kind] += 1
    if seen_total:
        declares += 1
        totals[name] = seen_total
        if len(set(seen_total)) > 1:
            multi[name] = seen_total
    credits += seen_credit
print("maps declaring a total", declares, "of", len(campaign_maps()), "crediting on 2", credits)
print("channel-2 senders by kind", dict(kinds))
flat = {m: max(v) for m, v in totals.items()}
print("lowest five", sorted(flat.items(), key=lambda kv: kv[1])[:5])
print("lowest", min(flat.items(), key=lambda kv: kv[1]), "highest", max(flat.items(), key=lambda kv: kv[1]))
print("maps with differing declared totals", multi)
