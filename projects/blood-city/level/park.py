"""The first greenery: the cemetery ground becomes an enclosed green.

Gravesend already had the right SHAPE for this and none of the substance. The
cemetery is a walled, gated ground off Old Crossing -- the E1M1 grammar, an
enclosed green you enter through a lychgate -- and it was a flat empty floor
wearing tile 352, which is the ROADWAY tile. A yard of tarmac behind a
lychgate.

So this is a dressing pass, not a construction one. The room, its wall and
its gate are all built already; what was missing is everything that makes a
green read as one:

* **grass** (361, owner-anchored "grass/turf with dirt patches", binding
  strong) as the ground, in place of the roadway tile;
* **dirt paths** (270) from the gate to the mausolea, as their own rooms at
  the same level -- a path is a different surface, not a painted stripe;
* **trees and bushes** from `bloodmap.furniture`, which already carries oak,
  elm, pine, deadwood and bush with their campaign cstats and shades;
* **headstones** -- the RIP, cross and flame stones, and the tomb -- which
  the campaign puts in exactly this place and which need no invention here;
* **straw** (515) at the foot of the wall, where a green goes untended.

Nothing is placed by hand. Every position comes from a SLOT derived from the
ground's own footprint, the same principle the street lamps use: how many
trees a green wants is a function of how big it is, and a green whose
contents are written out one by one is a green that stops being edited.
"""

from __future__ import annotations

import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[3]))
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

from bloodmap.furniture import furnish
from bloodmap.levelprog import RECT_FACES, Frame

COMPASS = dict(zip(RECT_FACES, range(4)))

#: Owner anchors. 361 is graded strong; 270 and 515 carry the owner's own
#: label and no binding grade, so they are used as MATERIAL and never named.
GRASS = 361
DIRT = 270
STRAW = 515

#: A path two bodies wide: you meet someone on it and neither steps onto the
#: grass. 384 is a player width, so 1024 is comfortably that.
PATH_WIDTH = 1024

#: One tree per this much ground, so a bigger green is a fuller one. Trees
#: are the slowest thing to read at distance, so they are the sparsest.
TREE_PER = 6 * 1024 * 6 * 1024
BUSH_PER = 4 * 1024 * 4 * 1024
STONE_PER = 5 * 1024 * 5 * 1024

#: What stands in a cemetery green, in the order the slots are filled. The
#: campaign's own set: three headstone kinds and a tomb.
STONES = ("headstone_rip", "headstone_cross", "headstone_flame", "tomb")
TREES = ("oak", "elm", "pine", "deadwood")


def _slots(count: int, box, *, margin: int):
    """`count` positions spread over a box, as (x, y) in world units.

    A lattice rather than a line, and inset from the wall so nothing stands
    in the masonry. Positions are deterministic: the same green always grows
    the same way, which is what makes a rebuild diffable.
    """
    x0, y0, x1, y1 = box
    x0, y0, x1, y1 = x0 + margin, y0 + margin, x1 - margin, y1 - margin
    if x1 <= x0 or y1 <= y0 or count <= 0:
        return []
    columns = max(1, int(round(count ** 0.5)))
    rows = max(1, (count + columns - 1) // columns)
    out = []
    for index in range(count):
        column, row = index % columns, index // columns
        out.append((int(x0 + (x1 - x0) * (column + 0.5) / columns),
                    int(y0 + (y1 - y0) * (row + 0.5) / rows)))
    return out


def _local(box, x, y):
    """A world point as the (0..1, 0..1) local a placement wants."""
    x0, y0, x1, y1 = box
    return ((x - x0) / max(1, x1 - x0), (y - y0) / max(1, y1 - y0))


def _overlaps(a, b) -> bool:
    return not (a[2] <= b[0] or b[2] <= a[0] or a[3] <= b[1] or b[3] <= a[1])


def green(city, layout_ground, *, district, grade: int, art_sizes=None,
          paths: bool = True, solids=()):
    """Turn a bare walled ground into a green. Returns what it planted."""
    outline = layout_ground.world_outline()
    xs = [int(p[0]) for p in outline]
    ys = [int(p[1]) for p in outline]
    box = (min(xs), min(ys), max(xs), max(ys))
    width, depth = box[2] - box[0], box[3] - box[1]
    area = width * depth

    layout_ground.surfaces(floor_picnum=GRASS)

    report = {"ground": layout_ground.region_id, "tile": GRASS,
              "area": area, "paths": [], "planted": {}, "refused": [],
              "solids": [tuple(int(v) for v in solid) for solid in solids]}

    #: A path down the middle, gate side to far side. Its own room at the
    #: ground's level: a different surface underfoot, not a stripe painted on
    #: the same one. It must match the hole exactly, which is the compiler's
    #: rule for anything standing in a carved opening.
    if paths and min(width, depth) > 4 * PATH_WIDTH:
        px0 = box[0] + (width - PATH_WIDTH) // 2
        path_box = (px0, box[1] + PATH_WIDTH, px0 + PATH_WIDTH,
                    box[3] - PATH_WIDTH)
        gx0, gy0 = box[0], box[1]
        #: A green with a church and two mausolea standing in it is not a
        #: rectangle, and a path laid straight down the middle of the
        #: bounding box walks through the church. Anything already standing
        #: on the ground refuses the path rather than being cut through.
        blocked = [tuple(solid) for solid in solids
                   if _overlaps(path_box, tuple(solid))]
        if blocked:
            report["refused"].append(
                f"path: would run through {len(blocked)} thing(s) standing "
                f"on the green")
            return report, box, area
        try:
            layout_ground.carve([
                (path_box[0] - gx0, path_box[1] - gy0),
                (path_box[2] - gx0, path_box[1] - gy0),
                (path_box[2] - gx0, path_box[3] - gy0),
                (path_box[0] - gx0, path_box[3] - gy0)])
            path = district.room(
                "green_path",
                [(0, 0), (path_box[2] - path_box[0], 0),
                 (path_box[2] - path_box[0], path_box[3] - path_box[1]),
                 (0, path_box[3] - path_box[1])],
                role="exterior", faces=dict(COMPASS),
                frame=Frame(path_box[0], path_box[1]),
                note="the trodden path across the green: dirt, not turf",
                intent={"kind": "path", "surface": "dirt"},
            )
            path.surfaces(floor_picnum=DIRT)
            for face in COMPASS:
                city.connect(path.face(face), layout_ground.face("north"),
                             connection_id=f"connection:green_path_{face}")
            report["paths"].append(path_box)
        except Exception as exc:                       # pragma: no cover
            report["refused"].append(f"path: {exc}")

    return report, box, area


def plant(layout, ground_region: str, box, area, *, art_sizes=None,
          prefix: str = "green", solids=(), clearance: int = 512):
    """Fill a green's slots with what a green holds. Deterministic.

    A green with a church and two mausolea in it is not a rectangle, and the
    slot lattice is laid over the bounding box -- so every slot is checked
    against what already stands there and the ones that land in masonry are
    dropped rather than planted inside it. `clearance` keeps a tree from
    growing flush against a wall it would clip through.
    """
    blocked = [(int(s[0]) - clearance, int(s[1]) - clearance,
                int(s[2]) + clearance, int(s[3]) + clearance)
               for s in solids]

    def _free(x, y):
        return not any(bx0 <= x <= bx1 and by0 <= y <= by1
                       for bx0, by0, bx1, by1 in blocked)

    planted = {}
    dropped = 0
    plans = (("tree", TREES, TREE_PER, 2048),
             ("stone", STONES, STONE_PER, 1536),
             ("bush", ("bush",), BUSH_PER, 1024))
    for kind, names, per, margin in plans:
        count = max(1, int(area // per))
        for index, (x, y) in enumerate(_slots(count, box, margin=margin)):
            if not _free(x, y):
                dropped += 1
                continue
            name = names[index % len(names)]
            layout.place_on_floor(
                f"{prefix}:{kind}:{index}", ground_region,
                local=_local(box, x, y),
                **furnish(name, art_sizes))
            planted[name] = planted.get(name, 0) + 1
    #: Straw at the foot of the wall, where a green goes untended. One
    #: tangle per corner, inside the planting margin so it reads as neglect
    #: rather than as litter dropped in the middle of the lawn.
    for index, (fx, fy) in enumerate(((0.08, 0.08), (0.92, 0.08),
                                      (0.08, 0.92), (0.92, 0.92))):
        x = box[0] + (box[2] - box[0]) * fx
        y = box[1] + (box[3] - box[1]) * fy
        if not _free(x, y):
            dropped += 1
            continue
        layout.place_on_floor(f"{prefix}:straw:{index}", ground_region,
                              local=(fx, fy),
                              **furnish("straw", art_sizes))
        planted["straw"] = planted.get("straw", 0) + 1
    if dropped:
        planted["_dropped_into_masonry"] = dropped
    return planted
