"""What Blood makes destructible: for every tile a thing can wear, how many of its sprites break, and the record they break by.

    python -m tools.mine_breakables            writes knowledge/blood/design/breakables-v1.json
    python -m tools.mine_breakables show 925   one tile

A tile's `record` is the commonest whole record (type, data, whether a bullet
reaches it) among its breakable sprites. `shot` counts the other way a thing is
broken: a switch that answers a bullet and shows its next picture (`bloodmap.breakables`).
"""

from __future__ import annotations

import json
import sys
from collections import Counter, defaultdict

from bloodmap.breakables import DATA, KINDS, RECORD, SHOT_KINDS
from bloodmap.corpus import named_maps
from bloodmap.format import read_map
from bloodmap.model import record_extra, record_fields


def mine() -> dict:
    seen: Counter = Counter()
    records: dict[int, Counter] = defaultdict(Counter)
    shot: Counter = Counter()
    example: dict[int, str] = {}
    maps = named_maps()
    for path in maps:
        for index, sprite in enumerate(read_map(path).sprites):
            f, x = record_fields(sprite), record_extra(sprite) or {}
            if int(f["cstat"]) & 32768:
                continue
            tile = int(f["picnum"])
            seen[tile] += 1
            if int(f["type"]) in KINDS:
                records[tile][(int(f["type"]), bool(int(f["cstat"]) & 256)) + tuple(int(x.get(k, 0)) for k in RECORD)] += 1
            elif int(f["type"]) in SHOT_KINDS and x.get("trigger_vector") and not x.get("trigger_push"):
                shot[tile] += 1
            else:
                continue
            example.setdefault(tile, f"{path.stem} sprite {index}")
    tiles = {}
    for tile in sorted(example):
        row = {"seen": seen[tile], "breaks": sum(records[tile].values()), "shot": shot[tile], "example": example[tile]}
        if records[tile]:
            best = max(sorted(records[tile]), key=records[tile].get)
            row["record"] = {"type": best[0], "hitscan": best[1], **{k: v for k, v in zip(RECORD, best[2:]) if v}}
        tiles[str(tile)] = row
    return {"maps": len(maps), "tiles": tiles}


def main() -> int:
    if sys.argv[1:2] == ["show"]:
        print(json.dumps(json.loads(DATA.read_text("utf-8"))["tiles"].get(sys.argv[2]), indent=1))
        return 0
    found = mine()
    DATA.write_text(json.dumps(found, indent=1) + "\n", encoding="utf-8", newline="\n")
    print(f"{len(found['tiles'])} tiles break in {found['maps']} maps: {DATA}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
