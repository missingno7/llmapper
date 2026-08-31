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
from bloodmap.patterns import corpus_map_path, list_corpus_maps
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


def _along(sprite, unit):
    return sprite.x * unit[0] + sprite.y * unit[1]


def _unit(angle):
    radians = (int(angle) - 512) * math.pi / 1024.0
    return (math.cos(radians), math.sin(radians))


def stacks(m):
    """Letters sharing one point on a wall, split by what they actually are.

    Two different things put letters above each other and they were counted
    as one: a word written DOWNWARD, and a sign of several LINES whose
    letters happen to share an x.  The first version of this measured 132
    "columns" of which only 11 were columns; the rest were the second and
    third lines of ordinary horizontal signs.

    The discriminator is whether each letter has a horizontal neighbour
    within two drawn widths at its own z.  If every letter does, the stack
    is a set of lines; if none does, it is a column.
    """
    letters = [sp for sp in m.sprites
               if FIRST_LETTER <= sp.picnum <= LAST_LETTER]
    points = collections.defaultdict(list)
    for sprite in letters:
        points[(sprite.x, sprite.y, sprite.angle)].append(sprite)
    columns, lines = [], []
    for (x, y, angle), group in points.items():
        if len(group) < 2:
            continue
        group.sort(key=lambda sp: sp.z)
        unit = _unit(angle)
        here = x * unit[0] + y * unit[1]
        neighbourly = 0
        for sprite in group:
            reach = 2.0 * sprite.x_repeat * 8 / 4.0
            if any(other.angle == angle and other.z == sprite.z
                   and 0 < abs(_along(other, unit) - here) <= reach
                   for other in letters):
                neighbourly += 1
        if neighbourly == len(group):
            lines.append(group)
        elif neighbourly == 0:
            columns.append(group)
    return columns, lines


def _pitches(groups):
    out = []
    for group in groups:
        drawn = (int(group[0].y_repeat) << 2) * 11
        if not drawn:
            continue
        heights = sorted(sprite.z for sprite in group)
        out += [(b - a) / drawn for a, b in zip(heights, heights[1:]) if b > a]
    return sorted(out)


def _spread(values) -> dict:
    if not values:
        return {"n": 0}
    import statistics
    return {"n": len(values),
            "median": round(statistics.median(values), 3),
            "q1": round(values[len(values) // 4], 3),
            "q3": round(values[3 * len(values) // 4], 3),
            "min": round(values[0], 3), "max": round(values[-1], 3)}


def text_geometry(paths) -> dict:
    """How far apart letters go downward, for the two reasons they do.

    Both numbers are spacing as a multiple of a letter's own drawn height,
    and `lettering.PITCH` (1.45) is the sideways one that had no counterpart.
    """
    column_maps, line_maps = collections.Counter(), collections.Counter()
    column_pitch, line_pitch = [], []
    examples = []
    for path in paths:
        try:
            m = read_map(path)
        except Exception:
            continue
        columns, lines = stacks(m)
        if columns:
            column_maps[pathlib.Path(path).stem] += len(columns)
            from bloodmap.lettering import letter_from
            for group in columns:
                word = "".join(letter_from(sp.picnum) or "" for sp in group)
                if len(word) > 2:
                    examples.append(f"{pathlib.Path(path).stem}:{word}")
        if lines:
            line_maps[pathlib.Path(path).stem] += len(lines)
        column_pitch += _pitches(columns)
        line_pitch += _pitches(lines)
    return {
        "columns": {"count": sum(column_maps.values()),
                    "maps": dict(column_maps),
                    "examples": examples[:8],
                    "letter_pitch_drawn_heights": _spread(sorted(column_pitch))},
        "lines": {"stacks": sum(line_maps.values()),
                  "maps": dict(line_maps),
                  "line_pitch_drawn_heights": _spread(sorted(line_pitch))},
    }


FIRST_LETTER, LAST_LETTER = 3808, 3833


def _words(m):
    """Every word written in letters, and how it is drawn.

    A column is one word.  Everything else groups by (sector, z, angle),
    which is `read_sign`'s rule and is right once the columns are taken
    out: a sign of several lines is several words at several heights, not
    one garbled one.
    """
    from bloodmap.lettering import letter_from
    columns, _lines = stacks(m)
    claimed = {id(sprite) for group in columns for sprite in group}
    rows = collections.defaultdict(list)
    for sprite in m.sprites:
        if not (FIRST_LETTER <= sprite.picnum <= LAST_LETTER):
            continue
        if id(sprite) in claimed:
            continue
        # NOT keyed on the sector.  A long sign painted along a wall crosses
        # whatever sector boundaries the wall crosses, and `read_sign` keys
        # on the sector -- which is why it returns LIQUO, LOERS and WTID for
        # DWE3M10 instead of the words that are actually written there
        # (grammar request #12).  The plane and the height are what a line
        # of text shares.
        unit = _unit(sprite.angle)
        offset = -sprite.x * unit[1] + sprite.y * unit[0]
        rows[(round(unit[0], 3), round(unit[1], 3), round(offset / 24.0),
              sprite.z)].append(sprite)

    groups = [("down", group) for group in columns]
    for key, group in rows.items():
        unit = (key[0], key[1])
        group.sort(key=lambda sprite: _along(sprite, unit))
        # Two words on one line are two words: split where the gap between
        # neighbours exceeds a couple of letter widths.
        run = [group[0]]
        for previous, sprite in zip(group, group[1:]):
            reach = 2.2 * previous.x_repeat * 8 / 4.0
            if _along(sprite, unit) - _along(previous, unit) > reach:
                groups.append(("across", run))
                run = []
            run.append(sprite)
        if run:
            groups.append(("across", run))

    out = []
    for direction, group in groups:
        out.append({
            "word": "".join(letter_from(sp.picnum) or "" for sp in group),
            "direction": direction,
            "letters": len(group),
            "sizes": sorted({int(sp.y_repeat) for sp in group}),
            "palettes": sorted({int(sp.pal) for sp in group}),
            "shades": sorted({int(sp.shade) for sp in group}),
            "square": all(sp.x_repeat == sp.y_repeat for sp in group),
        })
    return out


#: How far apart two letters may sit and still be one sign, in drawn widths.
#: Six, because E1M4 tracks ROTTEN CANDY at 2.0 and the campaign's ordinary
#: pitch is 1.45 -- a threshold near the pitch splits a wide-tracked sign
#: into its letters, which is what made the first version of this report
#: eleven one-letter words where there is a carnival attraction.
SIGN_GAP_WIDTHS = 6.0

#: How far apart in z, as a multiple of a letter's drawn height, two letters
#: have to be before they are on different LINES.  One: below the campaign's
#: 1.455 line pitch and above E1M4's 0.73 of carnival jitter.
LINE_SPLIT = 1.0


def sign_runs(m, gap_widths: float = SIGN_GAP_WIDTHS):
    """Letters clustered into signs by the plane they share and their spacing.

    Deliberately NOT keyed on z: E1M4's carnival signs jitter their letters
    up and down by most of a letter's height, and a grouping that wants one
    z reads ROTTEN CANDY as eleven separate letters.
    """
    letters = [sp for sp in m.sprites
               if FIRST_LETTER <= sp.picnum <= LAST_LETTER]
    planes = collections.defaultdict(list)
    for sprite in letters:
        unit = _unit(sprite.angle)
        offset = -sprite.x * unit[1] + sprite.y * unit[0]
        planes[(round(unit[0], 3), round(unit[1], 3),
                round(offset / 24.0))].append((sprite, unit))
    out = []
    for items in planes.values():
        unit = items[0][1]
        # Lines first.  A run clustered along the wall alone interleaves two
        # stacked lines whose x ranges overlap -- DWE1M7's FINANCE and
        # GRUDGE come back as FGIRNUADNGCEE, and their two uniform palettes
        # come back as an alternating "mixed" sign that is nothing of the
        # kind.  Letters more than LINE_SPLIT of their own height apart in z
        # are different lines; E1M4's carnival jitter is 0.73 across a whole
        # sign and the campaign's line pitch is 1.455, so the two separate
        # cleanly.
        # Single linkage on z, not bucketing: a bucket boundary cuts through
        # a jittered sign wherever it happens to fall, which took two
        # letters out of ROTTEN CANDY and one out of SPOOKY.
        ordered = sorted((sprite for sprite, _u in items), key=lambda s: s.z)
        lines, line = [], [ordered[0]]
        for previous, sprite in zip(ordered, ordered[1:]):
            drawn = (int(previous.y_repeat) << 2) * 11 or 1
            if sprite.z - previous.z > LINE_SPLIT * drawn:
                lines.append(line)
                line = []
            line.append(sprite)
        lines.append(line)
        for line in lines:
            line.sort(key=lambda sprite: _along(sprite, unit))
            run = [line[0]]
            for previous, sprite in zip(line, line[1:]):
                width = previous.x_repeat * 8 / 4.0
                if (_along(sprite, unit) - _along(previous, unit)
                        > gap_widths * width):
                    out.append((run, unit))
                    run = []
                run.append(sprite)
            out.append((run, unit))
    return [(run, unit) for run, unit in out if run]


def _cycle_length(values) -> int:
    """The shortest period this sequence repeats at, or 0 if it does not."""
    n = len(values)
    for period in range(1, n // 2 + 1):
        if n % period:
            continue
        if all(values[i] == values[i % period] for i in range(n)):
            return period
    return 0


def sign_composition(paths) -> dict:
    """Uniform against mixed, and what the mixing is doing.

    Three questions the owner asked of the per-letter palettes: is the cycle
    regular, does it alternate, and how often is a sign uniform at all.
    """
    from bloodmap.lettering import letter_from
    import itertools
    uniform = mixed = per_word = 0
    by_map = collections.Counter()
    cycles = collections.Counter()
    palette_counts = collections.Counter()
    tracking = collections.defaultdict(list)
    jitter = collections.defaultdict(list)
    examples = {"cycled": [], "irregular": []}
    for path in paths:
        try:
            m = read_map(path)
        except Exception:
            continue
        name = pathlib.Path(path).stem
        for run, unit in sign_runs(m):
            if len(run) < 3:
                continue
            word = "".join(letter_from(sp.picnum) or "" for sp in run)
            palettes = [int(sp.pal) for sp in run]
            width = run[0].x_repeat * 8 / 4.0
            drawn_h = (int(run[0].y_repeat) << 2) * 11
            alongs = [_along(sp, unit) for sp in run]
            gaps = [(b - a) / width for a, b in zip(alongs, alongs[1:])
                    if b > a]
            spread = ((max(sp.z for sp in run) - min(sp.z for sp in run))
                      / drawn_h) if drawn_h else 0.0
            distinct = len(set(palettes))
            kind = "uniform" if distinct == 1 else "mixed"
            if distinct == 1:
                uniform += 1
            else:
                mixed += 1
                period = _cycle_length(palettes)
                cycles[period] += 1
                palette_counts[distinct] += 1
                by_map[name] += 1
                # Colour can mark a WORD rather than a letter: DWE2M2 paints
                # ACTIVE, REMOVED and OPEN in three palettes with each word
                # uniform.  A run of equal palettes as long as a word is that
                # idiom, not a per-letter one.
                blocks = [len(list(g)) for _k, g in itertools.groupby(palettes)]
                if len(blocks) > 1 and min(blocks) >= 3:
                    per_word += 1
                row = f"{name}:{word} {palettes}"
                if period:
                    examples["cycled"].append(f"{row} period {period}")
                else:
                    examples["irregular"].append(row)
            if gaps:
                tracking[kind].append(sum(gaps) / len(gaps))
            jitter[kind].append(spread)
    return {
        "signs": uniform + mixed,
        "uniform": uniform,
        "mixed": mixed,
        "mixed_share": round(mixed / max(1, uniform + mixed), 3),
        "mixed_by_map": dict(by_map),
        "mixed_marking_whole_words": per_word,
        "cycle_period": {("none" if k == 0 else k): v
                         for k, v in sorted(cycles.items())},
        "distinct_palettes_when_mixed": dict(sorted(palette_counts.items())),
        "tracking_drawn_widths": {k: _spread(sorted(v))
                                  for k, v in tracking.items()},
        "z_jitter_letter_heights": {k: _spread(sorted(v))
                                    for k, v in jitter.items()},
        "examples": {k: v[:8] for k, v in examples.items()},
    }


def text_styles(paths) -> dict:
    """The (size, palette, shade) combinations the campaign actually writes.

    A text style is a parametric prefab exactly as a fixture family is: the
    look is pinned and the words are free.  So the question is which looks
    recur, and the answer is a joint distribution rather than the marginal
    palette table `lettering.PALETTES` already carries.
    """
    combos = collections.Counter()
    examples = collections.defaultdict(list)
    directions = collections.Counter()
    mixed_size = mixed_palette = 0
    lengths = []
    total = 0
    for path in paths:
        try:
            m = read_map(path)
        except Exception:
            continue
        for row in _words(m):
            if not row["word"]:
                continue
            total += 1
            directions[row["direction"]] += 1
            lengths.append(row["letters"])
            if len(row["sizes"]) > 1:
                mixed_size += 1
            if len(row["palettes"]) > 1:
                mixed_palette += 1
            key = (row["sizes"][0], row["palettes"][0], row["shades"][0],
                   row["direction"])
            combos[key] += 1
            if len(examples[key]) < 4 and len(row["word"]) > 2:
                examples[key].append(row["word"])
    lengths.sort()
    return {
        "words": total,
        "directions": dict(directions),
        "words_with_more_than_one_size": mixed_size,
        "words_with_more_than_one_palette": mixed_palette,
        "letters_per_word": {
            "median": lengths[len(lengths) // 2] if lengths else 0,
            "q1": lengths[len(lengths) // 4] if lengths else 0,
            "q3": lengths[3 * len(lengths) // 4] if lengths else 0,
            "max": lengths[-1] if lengths else 0,
        },
        "styles": [
            {"size": size, "palette": palette, "shade": shade,
             "direction": direction, "words": count,
             "examples": examples[(size, palette, shade, direction)]}
            for (size, palette, shade, direction), count in combos.most_common(24)
        ],
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
        targets += [corpus_map_path(name) for name in CORPUS]
    rows = [survey(path, art) for path in targets]
    # Both of these ask what "the campaign" writes. They used to glob a
    # flat maps/blood, which swept curated and converted maps in beside
    # the campaign and, after the corpus was reorganized, matched
    # nothing at all. Name the population instead.
    campaign = sorted(item.path for item in
                      list_corpus_maps(population="blood-campaign"))
    geometry = text_geometry(campaign) if args.corpus else {}
    styles = text_styles(campaign) if args.corpus else {}
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
                        "text_geometry": geometry,
                        "text_styles": styles}, indent=1),
            encoding="utf-8")
        print(f"wrote {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
