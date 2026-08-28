"""How tall Blood draws each of its sprite tiles.

`mine_decoration` already catalogues decoration, and it is the reason a sconce
in this project is the size a sconce is. It did not stop a garden being planted
with trees a third of their proper height, because it catalogues what the corpus
*files* as decoration and the corpus files its trees elsewhere -- so
`DECORATION` had no entry for 540, 541, 542, 543, 547 or 599, `height_range`
returned ``None`` for every one of them, and the invented number went through
untouched. The trees were authored at 2.8 to 3.4 player heights on the reasoning
that a tree is about three times a person. Blood draws them at 7.2 to 8.5.

The gap was not in the number, it was in the coverage: a tile the table does not
know is a tile with no size discipline at all. So this mines *every* picnum the
campaign ever draws as a sprite, without asking what kind of thing it is.

.. code-block:: bash

    python -m tools.mine_sprite_heights -o knowledge/blood/design/sprite-heights-v1.json
    python -m tools.mine_sprite_heights --against projects/.../candidate-v5.MAP

Height is ``y_repeat * 4 * tile_height`` in z units -- the arithmetic in
`GetSpriteExtents`, where the drawn half-extent is ``(yrepeat<<2) * centre`` --
divided by a player height so the numbers mean something. Invisible sprites are
skipped: a sprite Blood never draws has no drawn size, and markers are a large
share of the corpus.
"""

from __future__ import annotations

import argparse
import glob
import json
import pathlib
import re
import statistics
from collections import defaultdict
from typing import Any

from bloodmap.art import read_art_directory
from bloodmap.format import read_map
from bloodmap.player_space import PLAYER_PROFILES

SCHEMA = "llmapper.blood-sprite-heights"
SCHEMA_VERSION = 1

CAMPAIGN = re.compile(r"^E[1-46]M[1-9]$")

#: A sprite is measured against a *body*, not against the camera. This read
#: `eye_height` back when both fields held 0x1600 and the difference did not
#: show; they are 16960 and 14112 now and it does.
PLAYER_HEIGHT = PLAYER_PROFILES["blood"].standing_height

#: cstat bit 15. The engine skips the sprite entirely, so it has no drawn size.
CSTAT_INVISIBLE = 0x8000

#: Below this a tile's range is one or two authors' choices rather than a
#: convention, and holding a level to it would be superstition.
MIN_OBSERVATIONS = 4

#: How far outside the campaign's own range for a tile counts as wrong. Loose on
#: purpose: the question is whether a sprite is the *kind* of size Blood draws
#: it, not whether it matches to the repeat. A quarter under the smallest the
#: campaign ever drew, or a third over the largest, is a different object.
UNDER = 0.75
OVER = 1.33


def drawn_height(fields: Any, tile: Any) -> float:
    """Drawn height in player heights."""
    return int(fields["y_repeat"]) * 4 * tile.height / float(PLAYER_HEIGHT)


def observe(path: str, art: dict[int, Any], into: dict[int, list[float]]) -> None:
    for sprite in read_map(path).sprites:
        fields = sprite.fields
        if int(fields["cstat"]) & CSTAT_INVISIBLE:
            continue
        tile = art.get(int(fields["picnum"]))
        if tile is None or tile.height <= 0:
            continue
        into[int(fields["picnum"])].append(drawn_height(fields, tile))


def build(seen: dict[int, list[float]]) -> dict[str, Any]:
    tiles: dict[str, Any] = {}
    for picnum, values in sorted(seen.items()):
        if len(values) < MIN_OBSERVATIONS:
            continue
        ordered = sorted(values)
        tiles[str(picnum)] = {
            "n": len(ordered),
            "min": round(ordered[0], 2),
            "median": round(statistics.median(ordered), 2),
            "max": round(ordered[-1], 2),
        }
    return {
        "$schema": SCHEMA,
        "schema_version": SCHEMA_VERSION,
        "unit": "standing humans (%d z)" % PLAYER_HEIGHT,
        "min_observations": MIN_OBSERVATIONS,
        "tiles": tiles,
        "reading_guide": [
            "height is y_repeat * 4 * tile_height, which is the arithmetic in "
            "GetSpriteExtents and not the same as the sprite's width formula",
            "invisible sprites (cstat 0x8000) are not counted: Blood never draws "
            "them, so they have no drawn size",
            "a range is what the campaign did, never what a level must do -- but "
            "a level three times outside one is not making a choice, it is "
            "guessing at a tile it has not looked at",
        ],
    }


def offenders(disk: Any, art: dict[int, Any], tiles: dict[str, Any]) -> list[dict[str, Any]]:
    """Sprites drawn at a size the campaign never draws that tile."""
    out = []
    for index, sprite in enumerate(disk.sprites):
        fields = sprite.fields
        if int(fields["cstat"]) & CSTAT_INVISIBLE:
            continue
        picnum = int(fields["picnum"])
        tile = art.get(picnum)
        band = tiles.get(str(picnum))
        if tile is None or band is None:
            continue
        height = drawn_height(fields, tile)
        if height < band["min"] * UNDER or height > band["max"] * OVER:
            out.append({
                "sprite": index, "picnum": picnum,
                "drawn": round(height, 2),
                "campaign_min": band["min"], "campaign_max": band["max"],
                "observations": band["n"],
            })
    return out


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--maps", default="maps/blood")
    parser.add_argument("--art", default="reference/blood")
    parser.add_argument("--against")
    parser.add_argument("-o", "--output")
    args = parser.parse_args(argv)

    art = read_art_directory(args.art)
    if not art:
        print("no Blood ART")
        return 1

    seen: dict[int, list[float]] = defaultdict(list)
    maps = 0
    for path in sorted(glob.glob(str(pathlib.Path(args.maps) / "*.MAP"))):
        if not CAMPAIGN.match(pathlib.Path(path).stem.upper()):
            continue
        observe(path, art, seen)
        maps += 1
    document = build(seen)
    print("%d maps, %d picnums drawn, %d with %d+ observations" % (
        maps, len(seen), len(document["tiles"]), MIN_OBSERVATIONS))

    if args.output:
        out = pathlib.Path(args.output)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(document, indent=1, sort_keys=True) + "\n",
                       encoding="utf-8")
        print("wrote", args.output)

    if args.against:
        rows = offenders(read_map(args.against), art, document["tiles"])
        print()
        print("%d sprites outside the campaign range for their own tile" % len(rows))
        for row in rows:
            print("   sprite %-4d tile %-5d drawn %5.2f PH   campaign %.2f..%.2f (n=%d)" % (
                row["sprite"], row["picnum"], row["drawn"],
                row["campaign_min"], row["campaign_max"], row["observations"]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
