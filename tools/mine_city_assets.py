"""What Blood's own town maps are dressed with, and how each thing is set down.

The owner, looking at Gravesend on 2026-11-18: "try using more variety of
assets, check other blood city maps like DWE3M1, E3M1, etc. what they are
using for decorations. Looks like you have quite limited set now."

Counted, that is exact: Gravesend used 38 distinct decoration tiles; E3M1
uses 61, E1M2 109, E1M4 104, DWE3M1 142.

`tools/mine_prop_catalogue.py` already catalogues the whole campaign, with a
frequency floor, which is why a bottle that stands on forty bars is in it
and a "Cask of Amontillado Pub & Grille" sign that hangs on two is not. This
asks a narrower question of a named handful of TOWN maps and keeps
everything: for each decoration tile, which of the maps use it, whether
indoors or out, how it is aligned, and the fields the mappers gave it
(repeats, cstat, shade, palette, type, status, and how far over the floor
its anchor sits) -- so a tile can be set down here the way it is set down
there, by copying a measured placement and not by guessing one.

What it does not know is what a tile IS. The contact sheet is for that: a
person, or a model looking at the picture, names it. Tiles the owner has
anchored are starred.

.. code-block:: bash

    python -m tools.mine_city_assets                    # the default town maps
    python -m tools.mine_city_assets --sheet out.png --json out.json
"""

from __future__ import annotations

import argparse
import collections
import json
import pathlib
import statistics
import sys
from typing import Any
from bloodmap.player_space import PLAYER_PROFILES

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

#: Blood's town maps: the campaign's city street and its neighbours, E1M4's
#: fairground town, E6M1's shopfront, and Death Wish's two.
TOWN_MAPS = ("E3M1", "E3M2", "E1M2", "E1M4", "E6M1", "DWE3M1", "DWE3M10")


def map_path(text: str) -> pathlib.Path:
    """A corpus map by its name (`E3M1`), or a map file by its path; one that is not there is an error, not a skip."""
    from bloodmap.corpus import corpus_map_path

    path = pathlib.Path(text)
    if path.suffix.upper() != ".MAP":
        path = corpus_map_path(text)
    if not path.is_absolute():
        path = ROOT / path
    if not path.exists():
        raise SystemExit(f"no map {text} (a corpus name, or a path to a MAP)")
    return path
ALPHABET = frozenset(range(3808, 3834))
BODY = PLAYER_PROFILES["blood"].standing_height


def is_decoration(fields: Any) -> bool:
    """A sprite that is there to be looked at.

    Untyped sprites, the breakable "thing" types (400 to 433) and the two
    torch types (30, 32). Not actors, pickups, switches or markers, which
    the engine knows by type; not the alphabet, which is a text primitive.
    """
    if int(fields["cstat"]) & 0x8000:
        return False
    kind = int(fields.get("type", 0))
    if not (kind == 0 or 400 <= kind <= 433 or kind in (30, 32)):
        return False
    tile = int(fields["picnum"])
    return tile > 0 and tile not in ALPHABET


def _mode(values):
    return collections.Counter(values).most_common(1)[0][0]


def census(paths) -> dict[int, dict[str, Any]]:
    from bloodmap.format import read_map

    rows: dict[int, dict[str, list]] = {}
    for text in paths:
        path = map_path(str(text))
        disk = read_map(path)
        sectors = [s.fields for s in disk.sectors]
        for sprite in disk.sprites:
            f = sprite.fields
            if not is_decoration(f):
                continue
            sector = (sectors[int(f["sector"])]
                      if 0 <= int(f["sector"]) < len(sectors) else None)
            row = rows.setdefault(int(f["picnum"]), collections.defaultdict(list))
            row["map"].append(path.stem)
            row["where"].append("out" if sector is not None
                                and int(sector["ceiling_stat"]) & 1 else "in")
            row["align"].append({0: "face", 16: "wall", 32: "floor"}.get(
                int(f["cstat"]) & 48, "other"))
            row["repeats"].append((int(f["x_repeat"]), int(f["y_repeat"])))
            row["cstat"].append(int(f["cstat"]))
            row["shade"].append(int(f["shade"]))
            #: A sprite wearing its SECTOR's palette wears the place, not
            #: itself: DWE3M1 is fogged, and 970 of its sprites are palette 1
            #: in a palette-1 sector, none in a clear one. The owner found
            #: fog-blue chairs and bottles in Gravesend's clear rooms. The
            #: thing's own palette is what is left when the place's is taken.
            own = int(f.get("pal", 0))
            if sector is not None and own and own == int(
                    sector.get("floor_pal", 0)):
                own = 0
            row["pal"].append(own)
            row["type"].append(int(f.get("type", 0)))
            row["status"].append(int(f.get("statnum", f.get("status", 0))))
            if sector is not None:
                row["over_floor"].append(
                    (int(sector["floor_z"]) - int(f["z"])) / BODY)
    out = {}
    for tile, row in rows.items():
        maps = collections.Counter(row["map"])
        out[tile] = {
            "count": len(row["map"]),
            "maps": dict(maps),
            "where": dict(collections.Counter(row["where"])),
            "align": _mode(row["align"]),
            "x_repeat": _mode(row["repeats"])[0],
            "y_repeat": _mode(row["repeats"])[1],
            "cstat": _mode(row["cstat"]),
            "shade": int(statistics.median(row["shade"])),
            "pal": _mode(row["pal"]),
            "type": _mode(row["type"]),
            "status": _mode(row["status"]),
            "over_floor_bodies": (round(statistics.median(row["over_floor"]), 3)
                                  if row["over_floor"] else None),
        }
    return out


def variety(path: pathlib.Path) -> dict[str, int]:
    """How many different things one map is dressed and built with."""
    from bloodmap.format import read_map

    disk = read_map(path)
    decor = collections.Counter(int(s.fields["picnum"]) for s in disk.sprites
                                if is_decoration(s.fields))
    sectors = [s.fields for s in disk.sectors]
    return {
        "decoration_sprites": sum(decor.values()),
        "decoration_tiles": len(decor),
        "decoration_tiles_used_3_times": sum(1 for v in decor.values() if v >= 3),
        "wall_tiles": len({int(w.fields["picnum"]) for w in disk.walls}),
        "floor_tiles": len({int(s["floor_picnum"]) for s in sectors}),
        "ceiling_tiles": len({int(s["ceiling_picnum"]) for s in sectors
                              if not int(s["ceiling_stat"]) & 1}),
        "sectors": len(sectors),
    }


def contact_sheet(found: dict[int, dict], tiles: list[int], out: pathlib.Path,
                  *, columns: int = 10, cell: int = 132) -> None:
    from PIL import Image, ImageDraw

    from bloodmap import art

    art_tiles = art.read_art_directory(str(ROOT / "reference" / "blood"))
    palette = art.read_palette(ROOT / "reference" / "blood" / "xmapedit"
                               / "palettes" / "import" / "BLOOD.PAL")
    anchors = json.loads((ROOT / "knowledge" / "blood" / "design"
                          / "owner-anchors-v1.json").read_text("utf-8"))
    named = {a["picnum"] for a in anchors["anchors"] if "picnum" in a}
    rows = (len(tiles) + columns - 1) // columns
    sheet = Image.new("RGB", (columns * cell, rows * (cell + 26)), (60, 0, 60))
    draw = ImageDraw.Draw(sheet)
    for index, tile in enumerate(tiles):
        x, y = (index % columns) * cell, (index // columns) * (cell + 26)
        picture = art_tiles.get(tile)
        if picture is not None and picture.width and picture.height:
            image = Image.frombytes("RGB", (picture.width, picture.height),
                                    art.tile_to_rgb(picture, palette))
            scale = min(cell / image.width, cell / image.height, 3.0)
            image = image.resize((max(1, int(image.width * scale)),
                                  max(1, int(image.height * scale))),
                                 Image.NEAREST)
            sheet.paste(image, (x + (cell - image.width) // 2,
                                y + 26 + (cell - image.height) // 2))
        row = found[tile]
        where = max(row["where"], key=row["where"].get)
        draw.text((x + 2, y + 1),
                  f"{tile} n{row['count']} m{len(row['maps'])}", fill="white")
        draw.text((x + 2, y + 12),
                  f"{where}/{row['align']}" + (" *" if tile in named else ""),
                  fill=(255, 255, 0))
    sheet.save(out)


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("maps", nargs="*", default=list(TOWN_MAPS))
    parser.add_argument("--json", default=str(
        ROOT / "knowledge" / "blood" / "references" / "city-assets.json"))
    parser.add_argument("--sheet", default=str(
        ROOT / "knowledge" / "blood" / "references" / "city-assets.png"))
    parser.add_argument("--against", default="",
                        help="a built map (a project's): the tiles it already uses are left off the sheet")
    args = parser.parse_args(argv)
    found = census(args.maps)
    pathlib.Path(args.json).write_text(json.dumps(
        {"maps": list(args.maps), "tiles": {str(k): v for k, v in sorted(found.items())}},
        indent=1), "utf-8")
    ours = set()
    against = pathlib.Path(args.against or "no-map")
    if args.against and against.exists():
        from bloodmap.format import read_map

        ours = {int(s.fields["picnum"]) for s in read_map(against).sprites
                if is_decoration(s.fields)}
        print("variety:", against.stem, variety(against))
    for text in args.maps:
        path = ROOT / text
        if path.exists():
            print("variety:", path.stem, variety(path))
    unused = [t for t in sorted(found, key=lambda t: (-len(found[t]["maps"]),
                                                      -found[t]["count"]))
              if t not in ours and len(found[t]["maps"]) >= 2]
    contact_sheet(found, unused[:150], pathlib.Path(args.sheet))
    print(f"{len(found)} decoration tiles in {len(args.maps)} town maps; "
          f"{len(unused)} in two or more that {against.stem} does not use")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
