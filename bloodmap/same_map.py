"""Whether two maps are the same level whatever order their records are in.

Reorganising a level's program renames its regions and changes the order they
are walked in, so the compiled map carries the same level with its sectors,
walls and sprites in another order. A byte comparison cannot tell that from a
change of design; a comparison of what is there, without where in the file it
is, can. Each sector is reduced to its surfaces and its outline (walked from
its least corner), each wall to its two ends and what it wears, each sprite to
where it stands and what it is.

    python -m bloodmap.same_map before.MAP after.MAP

The answer for a refactor that must not change a level at all is still the
bytes (`sha256sum`); this is for the one that may reorder it. Written for
Gravesend's tree restructure (2026-11), where a build that reshuffled every
sprite could not be told from one that had only moved rooms between parents.
"""

from __future__ import annotations

import sys
from collections import Counter
from typing import Any

from .model import record_fields
from .sector_geom import sector_walls

SECTOR = ("floor_z", "ceiling_z", "floor_picnum", "ceiling_picnum", "floor_shade", "ceiling_shade", "floor_stat",
          "ceiling_stat", "floor_heinum", "ceiling_heinum", "type")
WALL = ("picnum", "over_picnum", "cstat", "shade", "x_repeat", "y_repeat", "x_panning", "y_panning", "type")
SPRITE = ("x", "y", "z", "picnum", "type", "cstat", "status", "shade", "x_repeat", "y_repeat", "angle", "pal")


def canonical(disk: Any) -> dict[str, Counter]:
    """A map as three bags: its sectors, its walls and its sprites, each without its number."""
    walls = [record_fields(w) for w in disk.walls]
    sectors = Counter()
    for index, sector in enumerate(disk.sectors):
        fields = record_fields(sector)
        loop = [(int(walls[w]["x"]), int(walls[w]["y"])) for w in sector_walls(disk, index)]
        if loop:
            at = loop.index(min(loop))
            loop = loop[at:] + loop[:at]
        sectors[tuple(int(fields[k]) for k in SECTOR) + (tuple(loop),)] += 1
    wall_bag = Counter()
    for wall in walls:
        end = walls[int(wall["point2"])]
        wall_bag[(int(wall["x"]), int(wall["y"]), int(end["x"]), int(end["y"]), int(wall["next_sector"]) >= 0)
                 + tuple(int(wall[k]) for k in WALL)] += 1
    sprites = Counter(tuple(int(record_fields(s)[k]) for k in SPRITE) for s in disk.sprites)
    return {"sectors": sectors, "walls": wall_bag, "sprites": sprites}


def difference(before: Any, after: Any) -> dict[str, dict[str, int]]:
    """What one map has that the other has not, counted by kind: all zeros is the same level."""
    a, b = canonical(before), canonical(after)
    return {kind: {"only_before": sum((a[kind] - b[kind]).values()), "only_after": sum((b[kind] - a[kind]).values())}
            for kind in a}


def same(before: Any, after: Any) -> bool:
    return all(not row["only_before"] and not row["only_after"] for row in difference(before, after).values())


def main(argv: list[str] | None = None) -> int:
    from .format import read_map

    args = list(sys.argv[1:] if argv is None else argv)
    if len(args) != 2:
        print(__doc__)
        return 2
    found = difference(read_map(args[0]), read_map(args[1]))
    for kind, row in found.items():
        print(f"{kind:8s} only in the first: {row['only_before']:5d}   only in the second: {row['only_after']:5d}")
    alike = all(not r["only_before"] and not r["only_after"] for r in found.values())
    print("the same level" if alike else "NOT the same level")
    return 0 if alike else 1


if __name__ == "__main__":
    raise SystemExit(main())
