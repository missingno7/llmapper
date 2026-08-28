"""Wall sprites as rectangles on a 2D surface, and where ours collide.

Owner: "when you are putting wall sprites they should not occupy same
physical space... some sprites are wider, taller, etc, so this should be
handled.  When placed on wall it should treat that wall as basically
vertical 2D surface that can have wall sprites on it in different places."

That is exactly right and it is not what this project does.  `props.py`
carries `MIN_WALL_PROP_SPACING = 384` and reserves a fixed run of the
*supporting line* around every existing anchor -- one dimension, one
constant, no knowledge of how wide or tall the thing being hung actually
is.  A 128-wide decal and a 1,024-wide window reserve the same 384, and two
sprites at the same point but different heights are treated as a conflict
while two overlapping wide ones 400 apart are treated as fine.

A wall sprite is a rectangle on a plane.  Build draws it:

* **along the wall**, from ``-(w/2 + xofs) * xrepeat / 4`` to
  ``+(w - w/2 - xofs) * xrepeat / 4`` about its own x/y, where `w` is the
  tile width and `xofs` its ART x offset (`bloodmap.placement.sprite_width`
  is the same scale factor);
* **up and down**, by `bloodmap.placement.sprite_extent`, which already
  knows the ``y_repeat << 2`` scale and the y offset.

So the audit is: group every wall-aligned sprite by the plane it lies on
(parallel angle, same supporting line), project each onto that plane as
``(along0, along1) x (ztop, zbottom)``, and intersect.

Derived: every rectangle, every overlap, every campaign rate below.
Interpreted: nothing.

    python tools/mine_wall_sprites.py projects/blood-city/level/city-skeleton.MAP
    python tools/mine_wall_sprites.py --corpus
"""

from __future__ import annotations

import argparse
import collections
import json
import math
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

from bloodmap.art import read_art_directory
from bloodmap.format import read_map
from bloodmap.placement import sprite_extent

#: cstat bits 4-5: 00 face, 01 wall, 10 floor.
ALIGN_MASK = 0x30
ALIGN_WALL = 0x10
#: cstat bit 3 mirrors the tile about its own centre line.
XFLIP = 0x04

#: How far apart two supporting lines may be and still count as one wall.
#: Wall props are mounted a tenth of a body width off the surface, so two
#: props on the same wall can differ by a unit or two of rounding; a genuine
#: second wall is hundreds of units away.
PLANE_TOLERANCE = 24.0

#: The share of a rectangle that may be covered before it counts as hidden.
#: Any overlap at all is a coplanar-sprite defect, but a few units of
#: touching edge is not what the owner is seeing.
OVERLAP_FLOOR = 0.02


def _art(reference="reference/blood"):
    tiles = read_art_directory(reference)
    return {tile: (art.width, art.height,
                   art.animation["xofs"], art.animation["yofs"])
            for tile, art in tiles.items()}


def rectangle(sprite, art) -> dict | None:
    """This wall sprite's footprint on its own plane, in map units.

    `along` is measured from the sprite's own x/y in the direction the wall
    runs (the sprite's angle turned a quarter); `z` is Build's, downward.
    """
    size = art.get(int(sprite.picnum))
    if size is None:
        return None
    width, height, xofs, yofs = size
    if width <= 0 or height <= 0:
        return None
    centre_x = width // 2 + int(xofs)
    if int(sprite.cstat) & XFLIP:
        centre_x = width - centre_x
    scale = int(sprite.x_repeat)
    left = (scale * centre_x) // 4
    right = (scale * (width - centre_x)) // 4
    above, below = sprite_extent(height, int(sprite.y_repeat),
                                 int(sprite.cstat), y_offset=int(yofs))
    return {"left": left, "right": right, "above": above, "below": below,
            "drawn_width": left + right, "drawn_height": above + below}


def plane_of(sprite):
    """(unit vector along the wall, signed distance of the supporting line).

    Two sprites share a plane when their angles are parallel -- the same or
    opposite, since a back-to-back pair is still coplanar and still fights
    for the same pixels -- and their lines coincide.
    """
    angle = int(sprite.angle) & 2047
    radians = (angle + 512) * math.pi / 1024.0
    ux, uy = math.cos(radians), math.sin(radians)
    if (ux, uy) < (0.0, 0.0):            # canonical direction for the pair
        ux, uy = -ux, -uy
    # The supporting line's perpendicular offset from the origin.
    offset = -sprite.x * uy + sprite.y * ux
    return (ux, uy), offset


def _overlap(a, b) -> float:
    """Area shared by two (along0, along1, z0, z1) rectangles."""
    wide = min(a[1], b[1]) - max(a[0], b[0])
    tall = min(a[3], b[3]) - max(a[2], b[2])
    if wide <= 0 or tall <= 0:
        return 0.0
    return float(wide) * float(tall)


def survey(path, art) -> dict:
    # Either a path or an already-read map: the build has the map in hand and
    # writing it out to read it back would let the two drift.
    m = read_map(path) if isinstance(path, (str, pathlib.Path)) else path
    planes = collections.defaultdict(list)
    counted = 0
    for index, sprite in enumerate(m.sprites):
        if int(sprite.cstat) & ALIGN_MASK != ALIGN_WALL:
            continue
        box = rectangle(sprite, art)
        if box is None or box["drawn_width"] <= 0 or box["drawn_height"] <= 0:
            continue
        counted += 1
        (ux, uy), offset = plane_of(sprite)
        along = sprite.x * ux + sprite.y * uy
        key = (round(ux, 3), round(uy, 3),
               round(offset / PLANE_TOLERANCE))
        planes[key].append({
            "sprite": index, "picnum": int(sprite.picnum),
            "sector": int(sprite.sector),
            "rect": (along - box["left"], along + box["right"],
                     sprite.z - box["above"], sprite.z + box["below"]),
            "area": float(box["drawn_width"]) * float(box["drawn_height"]),
        })

    clashes = []
    for key, items in planes.items():
        for i in range(len(items)):
            for j in range(i + 1, len(items)):
                a, b = items[i], items[j]
                shared = _overlap(a["rect"], b["rect"])
                if shared <= 0:
                    continue
                share = shared / min(a["area"], b["area"])
                if share < OVERLAP_FLOOR:
                    continue
                clashes.append({
                    "a": a["sprite"], "b": b["sprite"],
                    "tiles": [a["picnum"], b["picnum"]],
                    "sectors": [a["sector"], b["sector"]],
                    "covered_share": round(share, 3),
                    "overlap_units2": int(shared),
                })
    clashes.sort(key=lambda row: -row["covered_share"])
    return {
        "map": pathlib.Path(path).stem if isinstance(path, (str, pathlib.Path))
               else "<in memory>",
        "sprites": len(m.sprites),
        "wall_sprites": counted,
        "planes": len(planes),
        "clashing_pairs": len(clashes),
        "sprites_involved": len({s for row in clashes for s in (row["a"], row["b"])}),
        "clash_rate_per_100_wall_sprites": round(
            100.0 * len(clashes) / max(1, counted), 2),
        "fully_hidden": sum(1 for row in clashes if row["covered_share"] >= 0.95),
        "worst": clashes[:12],
    }


CORPUS = ("E1M1", "E2M1", "E3M1", "E3M2", "E4M9", "E6M1", "DWE3M1", "DWE3M10")

FIRST_LETTER, LAST_LETTER = 3808, 3833


def vertical_text(paths) -> dict:
    """How the campaign stacks letters downward, where it does.

    Text does not have to run across a wall.  Grouping every letter sprite
    by the point it hangs at -- same x, same y, same angle -- finds the
    columns, and the gaps between them give the pitch as a multiple of a
    letter's own drawn height.  `lettering.PITCH` is the sideways number
    (1.45) and had no counterpart, so writing downward was not expressible.
    """
    import statistics
    columns = collections.Counter()
    pitches = []
    sizes = collections.Counter()
    for path in paths:
        try:
            m = read_map(path)
        except Exception:
            continue
        stacks = collections.defaultdict(list)
        for sprite in m.sprites:
            if FIRST_LETTER <= sprite.picnum <= LAST_LETTER:
                stacks[(sprite.x, sprite.y, sprite.angle)].append(sprite)
        for group in stacks.values():
            if len(group) < 2:
                continue
            columns[pathlib.Path(path).stem] += 1
            drawn = (int(group[0].y_repeat) << 2) * 11
            sizes[int(group[0].y_repeat)] += 1
            heights = sorted(sprite.z for sprite in group)
            for lower, upper in zip(heights, heights[1:]):
                if upper > lower and drawn:
                    pitches.append((upper - lower) / drawn)
    pitches.sort()
    if not pitches:
        return {"columns": 0}
    return {
        "maps_with_columns": dict(columns),
        "columns": sum(columns.values()),
        "gaps": len(pitches),
        "pitch_drawn_heights": {
            "median": round(statistics.median(pitches), 3),
            "q1": round(pitches[len(pitches) // 4], 3),
            "q3": round(pitches[3 * len(pitches) // 4], 3),
            "min": round(pitches[0], 3), "max": round(pitches[-1], 3),
        },
        "sizes": sizes.most_common(8),
    }


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("maps", nargs="*")
    parser.add_argument("--corpus", action="store_true",
                        help="survey the campaign, for the rate to beat")
    parser.add_argument("-o", "--output")
    parser.add_argument("--reference", default="reference/blood")
    args = parser.parse_args(argv)

    art = _art(args.reference)
    targets = list(args.maps)
    if args.corpus:
        targets += [f"maps/blood/{name}.MAP" for name in CORPUS]
    rows = [survey(path, art) for path in targets]
    columns = (vertical_text(sorted(pathlib.Path("maps/blood").glob("*.MAP")))
               if args.corpus else {})
    for row in rows:
        print(f"{row['map']:12s} wall sprites {row['wall_sprites']:4d}  "
              f"clashing pairs {row['clashing_pairs']:4d}  "
              f"({row['clash_rate_per_100_wall_sprites']:5.2f} per 100)  "
              f"fully hidden {row['fully_hidden']:3d}")
    if args.output:
        pathlib.Path(args.output).write_text(
            json.dumps({"$schema": "llmapper.wall-sprite-overlap",
                        "schema_version": 1,
                        "note": ("Derived: every rectangle, overlap and pitch. "
                                 "A wall sprite is a rectangle on a plane, and "
                                 "two collide when their spans intersect in "
                                 "BOTH axes -- so stacking is legal."),
                        "maps": rows,
                        "vertical_text": columns}, indent=1),
            encoding="utf-8")
        print(f"wrote {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
