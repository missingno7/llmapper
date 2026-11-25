"""The map that is played: the city as it is built, with everything that lies under it moved out from under it.

    python projects/blood-city/level/release.py        # from blood-city-current.MAP; the build does it last

The engine hears through floors (`references/sewers-outside.md`), so 62 of the city's 97
ambiences, the sewers' own, were heard on its streets; and the automap drew both on one
another. The owner, 2026-11-25, when both links had been walked: "Both stacks work, go
ahead with the shift."

What is under the city is joined to it by nothing but links: it is one component of the
portals, and a link is a translation. So the component is moved and nothing in it is
changed -- `blood-city-current.MAP` stays in the plan's own coordinates, where every tool
and test reads it, and this writes `gravesend.MAP`, which is the same sectors, walls and
sprites in the same order with two numbers added to some of them.

The shift is a whole number of every floor tile's period (a floor's pattern lies on the
map's own grid: 16,384 units is 4 of the longest, 256 texels at 16), and of 1,024, the
grid the plan is drawn on.
"""

from __future__ import annotations

import copy
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
LEVEL = Path(__file__).resolve().parent
PLAN, RELEASE = LEVEL / "blood-city-current.MAP", LEVEL / "gravesend.MAP"

PU = 1024
#: west, clear of the drowned places (x -45..-14), and north, clear of the sea (y 63 on); inside Build's +-131,072
SHIFT = (-128 * PU, -16 * PU)
PERIOD, EXTENT = 16384, 131072


def _f(item):
    from bloodmap.model import record_fields
    return record_fields(item)


def under(disk) -> set[int]:
    """The sectors that lie under the city: what the portals join to the slab's lower half (`l3_church.SLAB_LINK`)."""
    from bloodmap.reachability import link_pairs
    import l3_church
    start = next(row["sectors"][1] for row in link_pairs(disk) if row["link_id"] == l3_church.SLAB_LINK)
    beyond = defaultdict(set)
    for i, sector in enumerate(disk.sectors):
        s = _f(sector)
        for w in range(int(s["wall_ptr"]), int(s["wall_ptr"]) + int(s["wall_count"])):
            n = int(_f(disk.walls[w])["next_sector"])
            if n >= 0:
                beyond[i].add(n)
    found, edge = {start}, [start]
    while edge:
        for n in beyond[edge.pop()]:
            if n not in found:
                found.add(n)
                edge.append(n)
    if int(disk.header["start_sector"]) in found:
        raise SystemExit("the city and what is under it are joined by a portal: nothing can be moved")
    return found


def shift(disk, by=SHIFT):
    """A copy of the map with what is under the city moved."""
    dx, dy = by
    if dx % PERIOD or dy % PERIOD:
        raise ValueError(f"a floor's pattern lies on the map's grid: {by} is not a whole number of {PERIOD}")
    out = copy.deepcopy(disk)
    moved = under(out)
    for i in moved:
        s = _f(out.sectors[i])
        for w in range(int(s["wall_ptr"]), int(s["wall_ptr"]) + int(s["wall_count"])):
            f = _f(out.walls[w])
            f["x"], f["y"] = int(f["x"]) + dx, int(f["y"]) + dy
            if max(abs(f["x"]), abs(f["y"])) >= EXTENT:
                raise ValueError(f"wall {w} would stand at {f['x']}, {f['y']}, off Build's map")
    for sprite in out.sprites:
        f = _f(sprite)
        if int(f["sector"]) in moved:
            f["x"], f["y"] = int(f["x"]) + dx, int(f["y"]) + dy
    return out


def build() -> dict:
    """Write the released map from the plan's."""
    from bloodmap.format import read_map, write_map
    disk = read_map(PLAN)
    write_map(shift(disk), RELEASE)
    return {"sectors": len(under(disk)), "of": len(disk.sectors), "by": [v // PU for v in SHIFT]}


if __name__ == "__main__":
    print("released:", build())
