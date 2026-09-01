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


def _inside(polygon, x: float, y: float) -> bool:
    """Ray casting against the room's ACTUAL outline, notches and all."""
    hit = False
    count = len(polygon)
    for index in range(count):
        ax, ay = polygon[index]
        bx, by = polygon[(index + 1) % count]
        if (ay > y) != (by > y):
            cross = ax + (y - ay) * (bx - ax) / (by - ay)
            if x < cross:
                hit = not hit
    return hit


def _clearance(polygon, x: float, y: float) -> float:
    """Distance from a point to the nearest edge of the outline."""
    best = float("inf")
    count = len(polygon)
    for index in range(count):
        ax, ay = polygon[index]
        bx, by = polygon[(index + 1) % count]
        dx, dy = bx - ax, by - ay
        span = dx * dx + dy * dy
        t = 0.0 if not span else max(0.0, min(1.0, ((x - ax) * dx +
                                                    (y - ay) * dy) / span))
        px, py = ax + t * dx, ay + t * dy
        best = min(best, ((x - px) ** 2 + (y - py) ** 2) ** 0.5)
    return best


def _slots(count: int, box, *, margin: int, outline=None):
    """`count` positions that are actually ON the ground, as world (x, y).

    The first version laid a lattice over the BOUNDING BOX and let the caller
    filter afterwards, which dropped eleven of twenty plants in the cemetery:
    a green with a church and two mausolea standing in it is not a rectangle,
    and most of its bounding box is masonry.

    So the lattice is oversampled and then filtered against the room's own
    NOTCHED outline -- inside it, and `margin` clear of every edge, so a tree
    does not grow through a wall it is standing against. Positions stay
    deterministic: the same green always grows the same way, which is what
    makes a rebuild diffable.
    """
    x0, y0, x1, y1 = box
    if x1 <= x0 or y1 <= y0 or count <= 0:
        return []
    if outline is None:
        inner = (x0 + margin, y0 + margin, x1 - margin, y1 - margin)
        if inner[2] <= inner[0] or inner[3] <= inner[1]:
            return []
        columns = max(1, int(round(count ** 0.5)))
        rows = max(1, (count + columns - 1) // columns)
        return [(int(inner[0] + (inner[2] - inner[0]) * (i % columns + 0.5)
                     / columns),
                 int(inner[1] + (inner[3] - inner[1]) * (i // columns + 0.5)
                     / rows))
                for i in range(count)]
    #: Oversample, keep what lands on the ground, then thin evenly so the
    #: survivors are spread rather than clustered in whichever corner the
    #: lattice happened to favour.
    side = max(3, int((count * 6) ** 0.5) + 1)
    candidates = []
    for row in range(side):
        for column in range(side):
            x = x0 + (x1 - x0) * (column + 0.5) / side
            y = y0 + (y1 - y0) * (row + 0.5) / side
            if _inside(outline, x, y) and _clearance(outline, x, y) >= margin:
                candidates.append((int(x), int(y)))
    if not candidates:
        return []
    if len(candidates) <= count:
        return candidates
    step = len(candidates) / float(count)
    return [candidates[int(index * step)] for index in range(count)]


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
              "solids": [tuple(int(v) for v in solid) for solid in solids],
              #: the ground's ACTUAL shape, notches and all -- what the slot
              #: lattice has to respect
              "outline": [(int(p[0]), int(p[1])) for p in outline]}

    #: A path down the middle, gate side to far side. Its own room at the
    #: ground's level: a different surface underfoot, not a stripe painted on
    #: the same one. It must match the hole exactly, which is the compiler's
    #: rule for anything standing in a carved opening.
    if paths and min(width, depth) > 4 * PATH_WIDTH:
        #: A path down the MIDDLE of the bounding box walks through the
        #: church. So candidate strips are scanned outwards from the middle
        #: and the first one that is clear of everything standing on the
        #: green wins -- a path goes where there is room for it, which is how
        #: a path comes to be in the first place.
        gx0, gy0 = box[0], box[1]
        blocked_boxes = [tuple(solid) for solid in solids]
        path_box = None
        centre = box[0] + (width - PATH_WIDTH) // 2
        span = (width - PATH_WIDTH) // 2
        for offset in range(0, span + 1, PATH_WIDTH // 2):
            for sign in ((0,) if offset == 0 else (-1, 1)):
                px0 = centre + sign * offset
                trial = (px0, box[1] + PATH_WIDTH, px0 + PATH_WIDTH,
                         box[3] - PATH_WIDTH)
                if any(_overlaps(trial, b) for b in blocked_boxes):
                    continue
                #: and it has to lie wholly ON the ground. The ground's
                #: outline is NOTCHED around the church and the mausolea, so
                #: "clear of the solids" is not the same as "inside the
                #: room" -- a strip running past the end of the turf carves a
                #: hole through nothing and the compiler sees a malformed
                #: region.
                #: Sampled down the CENTRELINE with real clearance, not at
                #: the corners. A corner probe one unit inside the boundary
                #: passes while the strip's edge lies flush against a
                #: mausoleum, and a carve that shares an edge with a notch is
                #: a degenerate polygon -- which showed up, bizarrely, as the
                #: cemetery overlapping a street two districts away.
                need = PATH_WIDTH // 2 + 256
                mid = (trial[0] + trial[2]) // 2
                steps = max(2, (trial[3] - trial[1]) // 512)
                ok = True
                for step in range(steps + 1):
                    py = trial[1] + (trial[3] - trial[1]) * step / steps
                    if not _inside(outline, mid, py) or                             _clearance(outline, mid, py) < need:
                        ok = False
                        break
                if not ok:
                    continue
                path_box = trial
                break
            if path_box:
                break
        if path_box is None:
            report["refused"].append(
                "path: no strip across the green is clear of the things "
                "standing on it")
            return report, box, area
        try:
            #: In the GROUND's own coordinates. It was built with no frame
            #: of its own -- the district's frame lives on its street -- so
            #: its local space is world space, and subtracting the bounding
            #: box origin (which the roadways correctly do, because a street
            #: room IS framed) put the hole a district away from the path
            #: standing in it.
            layout_ground.carve([
                (path_box[0], path_box[1]), (path_box[2], path_box[1]),
                (path_box[2], path_box[3]), (path_box[0], path_box[3])])
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
            #: Nothing stands ON the path. It joins the list of things the
            #: planting yields to, which is the whole point of a path.
            report["solids"].append(tuple(int(v) for v in path_box))
        except Exception as exc:                       # pragma: no cover
            report["refused"].append(f"path: {exc}")

    return report, box, area


def plant(layout, ground_region: str, box, area, *, art_sizes=None,
          prefix: str = "green", solids=(), clearance: int = 256,
          outline=None):
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
    #: Margins are the clear space a thing needs from the ground's own edge,
    #: and they were first written for an open lawn. This green is a walled
    #: yard with a church, two mausolea and now a path in it, and the turf
    #: left over is in strips: a 2048 margin put a tree nowhere. A tree wants
    #: a body's room, a headstone less, a bush almost none -- which is also
    #: how they sit in E1M1's cemetery.
    plans = (("tree", TREES, TREE_PER, 1024),
             ("stone", STONES, STONE_PER, 640),
             ("bush", ("bush",), BUSH_PER, 384))
    for kind, names, per, margin in plans:
        count = max(1, int(area // per))
        for index, (x, y) in enumerate(_slots(count, box, margin=margin,
                                              outline=outline)):
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
        on_ground = (_inside(outline, x, y)
                     and _clearance(outline, x, y) >= 256) if outline             else _free(x, y)
        if not on_ground:
            dropped += 1
            continue
        layout.place_on_floor(f"{prefix}:straw:{index}", ground_region,
                              local=(fx, fy),
                              **furnish("straw", art_sizes))
        planted["straw"] = planted.get("straw", 0) + 1
    if dropped:
        planted["_dropped_into_masonry"] = dropped
    return planted
