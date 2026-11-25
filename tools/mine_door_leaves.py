"""Which way each door tile's leaf moves, over the campaign: goes up, slides or swings (the owner's rules for leaves, counted).

The owner, 2026-11-25: "in door with knob (picnum 30) I would avoid doing them as Z
motion ... Door picnum 22 are good for Z door. but 23 is sliding door recommended only
for example. 24,25,26,27 can be any door type ... These nuances should be obvious from
existing maps, these are some sort of unwritten rules." They are: 30 slides in all four
places it moves in and never goes up. A leaf's motion is its sector's type; a Z door's
leaf is what its neighbours show over it, a slide's or a swing's the walls it carries.

    python -m tools.mine_door_leaves            every leaf tile from 20 to 34, with examples
    python -m tools.mine_door_leaves 30 23      those
    python -m tools.mine_door_leaves --check MAP   the leaves of one map against the owner's rules
"""

from __future__ import annotations

import argparse
from collections import Counter, defaultdict

from bloodmap.corpus import campaign_maps, corpus_map_path
from bloodmap.format import read_map
from bloodmap.model import record_fields

MOTION = {600: "z", 602: "z", 614: "slide", 616: "slide", 613: "swing", 615: "swing", 617: "swing"}
LEAVES = range(20, 35)
#: the owner's rules: what each leaf may do
RULES = {22: {"z", "slide", "swing"}, 23: {"slide"}, 24: {"z", "slide", "swing"}, 25: {"z", "slide", "swing"},
         26: {"z", "slide", "swing"}, 27: {"z", "slide", "swing"}, 30: {"slide", "swing"}}


def leaves(disk) -> list[tuple[int, int, str]]:
    """(sector, tile, motion) of every leaf in a map."""
    out = []
    for i, sector in enumerate(disk.sectors):
        s = record_fields(sector)
        kind = MOTION.get(int(s["type"]))
        if kind is None:
            continue
        tiles = set()
        for w in range(int(s["wall_ptr"]), int(s["wall_ptr"]) + int(s["wall_count"])):
            f = record_fields(disk.walls[w])
            if kind == "z" and int(f["next_wall"]) >= 0:
                tiles.add(int(record_fields(disk.walls[int(f["next_wall"])])["picnum"]))
            elif kind != "z" and (int(f["cstat"]) & 0xC000 or int(s["type"]) in (613, 616, 617)):
                tiles.add(int(f["picnum"]))
                if int(f["next_wall"]) >= 0:
                    tiles.add(int(record_fields(disk.walls[int(f["next_wall"])])["picnum"]))
        out += [(i, t, kind) for t in sorted(tiles)]
    return out


def broken_rules(disk) -> list[tuple[int, int, str]]:
    """Leaves that move as the owner says their tile does not."""
    return [(i, t, kind) for i, t, kind in leaves(disk) if t in RULES and kind not in RULES[t]]


def mine(tiles=None) -> dict:
    use: dict = defaultdict(Counter)
    where: dict = defaultdict(list)
    for m in campaign_maps():
        path = m if hasattr(m, "exists") else corpus_map_path(m)
        for i, t, kind in leaves(read_map(path)):
            if t in (tiles or LEAVES):
                use[t][kind] += 1
                where[t, kind].append(f"{path.stem}:{i}")
    return {t: {kind: (n, where[t, kind][:5]) for kind, n in use[t].items()} for t in sorted(use)}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("tiles", nargs="*", type=int)
    parser.add_argument("--check", metavar="MAP")
    args = parser.parse_args()
    if args.check:
        for i, t, kind in broken_rules(read_map(args.check)):
            print(f"sector {i}: a leaf of tile {t} moves as a {kind} door; the owner's rule: {sorted(RULES[t])}")
        return
    for tile, kinds in mine(args.tiles or None).items():
        print(tile, "  ".join(f"{kind} {n} ({', '.join(ex)})" for kind, (n, ex) in sorted(kinds.items(), key=lambda k: -k[1][0])))


if __name__ == "__main__":
    main()
