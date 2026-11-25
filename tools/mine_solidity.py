"""Which sprites stop a body and which a bullet, tile by tile and by how they stand, over the campaign and Death Wish; and what of a map does not.

The owner, 2026-11-25, on roofs one fell through: "Check if there are no other sprites that
supposed to be blocking and are not, like lamps and other stuff". Blood is of one mind about
most tiles: every barrel blocks and nearly every bottle, and hardly a candle.

    python -m tools.mine_solidity                 mine, and write knowledge/blood/design/solidity-v1.json
    python -m tools.mine_solidity --check MAP     what of a map passes through where Blood's does not
"""

from __future__ import annotations

import argparse
from collections import defaultdict
import json
from pathlib import Path

from bloodmap.corpus import campaign_maps, corpus_map_path, named_maps
from bloodmap.format import read_map
from bloodmap.model import record_fields

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "knowledge" / "blood" / "design" / "solidity-v1.json"
#: what is a thing and no actor, item, marker or sound
KINDS = (0, 20, 21, 22, 30, 32, 416, 417)
STANDS = {0: "face", 1: "wall", 2: "flat"}
#: how many there must be, and what share of them, for a map to be held to it
LEAST, SHARE = 8, 0.8


def thing(f) -> bool:
    """A drawn thing: what may be walked into or shot at."""
    return not int(f["cstat"]) & 32768 and int(f["type"]) in KINDS and int(f["picnum"]) > 0 and int(f["status"]) in (0, 4)


def key(f) -> str:
    return f"{int(f['picnum'])}:{STANDS.get(int(f['cstat']) >> 4 & 3, 'odd')}"


def mine(paths) -> dict[str, list[int]]:
    """tile:stand -> [seen, that block, that stop a bullet]."""
    out: dict[str, list[int]] = defaultdict(lambda: [0, 0, 0])
    for path in paths:
        for sprite in read_map(path).sprites:
            f = record_fields(sprite)
            if thing(f):
                row = out[key(f)]
                row[0] += 1
                row[1] += int(f["cstat"]) & 1
                row[2] += bool(int(f["cstat"]) & 256)
    return {k: out[k] for k in sorted(out, key=lambda k: (int(k.split(":")[0]), k))}


def faults(disk, table) -> list[dict]:
    """The things of a map that let through what Blood's of the same tile and stand do not."""
    out = []
    for i, sprite in enumerate(disk.sprites):
        f = record_fields(sprite)
        if not thing(f) or key(f).endswith("flat"):
            continue
        seen, block, hit = table.get(key(f), (0, 0, 0))
        if seen < LEAST:
            continue
        lacks = [name for name, count, bit in (("body", block, 1), ("bullet", hit, 256)) if count / seen >= SHARE and not int(f["cstat"]) & bit]
        if lacks:
            out.append({"sprite": i, "tile": int(f["picnum"]), "lacks": lacks, "of": seen})
    return out


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--check", metavar="MAP")
    args = parser.parse_args()
    if args.check:
        path = Path(args.check) if Path(args.check).exists() else corpus_map_path(args.check)
        rows = faults(read_map(path), json.loads(DATA.read_text("utf-8"))["tiles"])
        for row in rows:
            print(row)
        print(len(rows), "let through what Blood's do not")
        return
    paths = sorted({*campaign_maps(), *(p for p in named_maps() if p.stem.upper().startswith("DWE"))}, key=lambda p: p.stem)
    tiles = mine(paths)
    DATA.write_text(json.dumps({"schema": "llmapper.solidity-v1", "maps": len(paths), "tiles": tiles}, separators=(",", ":")) + "\n", "utf-8",
                    newline="\n")
    print(len(tiles), "tiles as they stand, of", len(paths), "maps ->", DATA)


if __name__ == "__main__":
    main()
