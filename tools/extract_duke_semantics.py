"""Duke's own names for its tiles, sector tags and sector effectors.

Every Duke census this project has run printed bare numbers -- "tile 2621",
"sector lotag 21" -- because nothing here knew what Duke calls things.  Duke
does know, in two places we already have:

* `reference/duke3d/DEFS.CON` -- 1,190 `define NAME VALUE` lines naming
  every tile the game has an identity for, from SECTOREFFECTOR 1 to the
  last decoration.  This is the game's own dictionary, shipped with it.
* `reference/eduke32/source/duke3d/src/game.h` -- the `ST_*` sector-tag and
  `SE_*` sector-effector enumerations, which is where the *mechanisms*
  live.  A Duke map's behaviour is almost entirely sector lotags plus
  SECTOREFFECTOR sprites whose lotag selects an effect.

Read from source, not inferred: the same discipline this project applies to
NBlood.  The output is `knowledge/duke3d/semantics-v1.json`.

    python tools/extract_duke_semantics.py
"""

from __future__ import annotations

import argparse
import json
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
DEFS = ROOT / "reference" / "duke3d" / "DEFS.CON"
GAME_H = ROOT / "reference" / "eduke32" / "source" / "duke3d" / "src" / "game.h"

DEFINE = re.compile(r"^\s*define\s+([A-Za-z_][A-Za-z0-9_]*)\s+(-?\d+)\s*$",
                    re.IGNORECASE)
ENUM = re.compile(r"^\s*(S[ET]_[A-Z0-9_]+)\s*=\s*(\d+)\s*,")


#: DEFS.CON is sectioned by comment, and only the first section is tiles.
#: After "Defines weapon..." it is weapon ids, actor motion values, player
#: actions and sound ids -- all of which collide numerically with tiles.
#: Reading the whole file as a tile dictionary makes tile 4 come back as
#: ACTIVATORLOCKED *and* RPG_WEAPON *and* getv *and* EJECT_CLIP, which is
#: how this was noticed.
TILE_SECTION_ENDS = "Defines weapon"


def read_defines(path: pathlib.Path) -> tuple[dict[str, int], dict[str, int]]:
    """(tile names, everything else), split at the file's own section break."""
    tiles: dict[str, int] = {}
    other: dict[str, int] = {}
    in_tiles = True
    for line in path.read_text(errors="replace").splitlines():
        if TILE_SECTION_ENDS in line:
            in_tiles = False
        match = DEFINE.match(line)
        if match:
            (tiles if in_tiles else other)[match.group(1)] = int(match.group(2))
    return tiles, other


def read_enums(path: pathlib.Path) -> tuple[dict[int, str], dict[int, str]]:
    """The ST_* and SE_* tables, keyed by their numeric tag."""
    sector_tags: dict[int, str] = {}
    effectors: dict[int, str] = {}
    for line in path.read_text(errors="replace").splitlines():
        match = ENUM.match(line)
        if not match:
            continue
        name, value = match.group(1), int(match.group(2))
        target = sector_tags if name.startswith("ST_") else effectors
        # Strip the numeric prefix Duke bakes into the name: ST_21_FLOOR_DOOR
        # is the tag 21, and repeating it in the label helps nobody.
        label = re.sub(r"^S[ET]_\d+_?", "", name) or name
        target[value] = label.lower().replace("_", " ") or name.lower()
    return sector_tags, effectors


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("-o", "--output",
                    default="knowledge/duke3d/semantics-v1.json")
    args = ap.parse_args(argv)

    if not DEFS.exists():
        print(f"!! {DEFS} not found", file=sys.stderr)
        return 1
    tiles, other = read_defines(DEFS)
    sector_tags, effectors = ({}, {})
    if GAME_H.exists():
        sector_tags, effectors = read_enums(GAME_H)

    # A tile can have several names (aliases); keep them all, and index the
    # other way for lookups.
    by_number: dict[int, list[str]] = {}
    for name, value in tiles.items():
        by_number.setdefault(value, []).append(name)

    #: The sprites that carry a Duke map's logic rather than its scenery.
    control = {name: tiles[name] for name in (
        "SECTOREFFECTOR", "ACTIVATOR", "TOUCHPLATE", "ACTIVATORLOCKED",
        "MUSICANDSFX", "LOCATORS", "CYCLER", "MASTERSWITCH", "RESPAWN",
        "GPSPEED") if name in tiles}

    # Cross-check against the shipped ART: a name whose number has no tile
    # is a name for something else that happens to share the number.
    real = set()
    try:
        from bloodmap.art import read_art_directory
        art = read_art_directory(ROOT / "reference" / "duke3d")
        real = {t for t, tile in art.items() if tile.width and tile.height}
    except Exception:
        pass
    drawn = {k: v for k, v in by_number.items() if not real or k in real}

    out = {
        "$schema": "llmapper.duke-semantics",
        "schema_version": 1,
        "sources": {
            "tiles": "reference/duke3d/DEFS.CON (shipped with the game)",
            "tags": "reference/eduke32/source/duke3d/src/game.h (ST_*, SE_*)",
        },
        "note": ("Everything here is transcribed from Duke's own files. "
                 "Nothing is inferred from map statistics."),
        "tile_count": len(tiles),
        "tiles_with_art": len(drawn),
        "tiles_by_name": tiles,
        "tiles_by_number": {str(k): v for k, v in sorted(drawn.items())},
        "named_but_no_art": {str(k): v for k, v in sorted(by_number.items())
                             if real and k not in real},
        "non_tile_constants": other,
        "control_sprites": control,
        "sector_tags": {str(k): v for k, v in sorted(sector_tags.items())},
        "sector_effectors": {str(k): v for k, v in sorted(effectors.items())},
    }
    path = ROOT / args.output
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(out, indent=1, sort_keys=False),
                    encoding="utf-8")
    print(f"wrote {args.output}: {len(tiles)} tile names "
          f"({len(drawn)} with art), {len(other)} non-tile constants, "
          f"{len(sector_tags)} sector tags, {len(effectors)} sector effectors")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
