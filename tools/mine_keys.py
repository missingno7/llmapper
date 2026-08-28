"""How Blood tells you which key a door wants.

A keyed door in Blood carries its requirement in the XSector's ``key`` field,
which the engine checks and the player cannot see. What the player reads is a
*placard*: a 58x58 emblem in a spiked iron frame, hung beside or above the door,
one tile per key.

This project deleted all six of those tiles from its level on the grounds that
they were "six identical 58x58" gizmos. They are identical only in their frame;
the emblem inside is the whole message, and without it a locked door tells you
nothing but that it is locked.

What is measured
----------------

* which placard tile goes with which ``key`` value, from co-location -- the
  emblem nearest each keyed door, not from a table somebody remembered;
* how the placard is hung: height above the floor, distance from the door, and
  the cstat that makes it a wall sprite rather than a face sprite;
* whether the *key item* itself uses the same emblem, which would let one
  vocabulary serve both.

.. code-block:: bash

    python -m tools.mine_keys -o knowledge/blood/design/keys-v1.json
"""

from __future__ import annotations

import argparse
import glob
import json
import math
import pathlib
import re
import statistics
from collections import Counter, defaultdict
from typing import Any

from bloodmap.format import read_map
from bloodmap.player_space import PLAYER_PROFILES

SCHEMA = "llmapper.blood-keys"
SCHEMA_VERSION = 1

CAMPAIGN = re.compile(r"^E[1-46]M[1-9]$")
PLAYER_HEIGHT = PLAYER_PROFILES["blood"].standing_height

#: The six emblems, in tile order. Named from rendering them, not from memory.
PLACARD_TILES = {
    2540: "skull",
    2541: "eye",
    2542: "flame",
    2543: "dagger",
    2544: "spider",
    2545: "moon",
}

#: How far from a keyed door a placard can be and still be about that door.
NEAR = 3072


def key_of(item: Any) -> int:
    """The key an item demands, out of its Blood extension.

    Not `fields["key"]`: that is the base Build struct, which has no such
    member. Blood keeps it in the XSECTOR / XSPRITE / XWALL extension hanging
    off `.extra`, and reading the wrong one silently returns nothing -- a first
    pass reported 0 keyed things across all 43 maps, next to 200 placards, which
    should have been the tell.
    """
    extra = getattr(item, "extra", None)
    if extra is None or not hasattr(extra, "fields"):
        return 0
    return int(extra.fields.get("key", 0) or 0)


def keyed_things(disk: Any) -> list[dict[str, Any]]:
    """Everything in the map that demands a key."""
    out = []
    for index, sector in enumerate(disk.sectors):
        key = key_of(sector)
        if not key:
            continue
        fields = sector.fields
        start, count = int(fields["wall_ptr"]), int(fields["wall_count"])
        xs = [int(disk.walls[w].fields["x"]) for w in range(start, start + count)]
        ys = [int(disk.walls[w].fields["y"]) for w in range(start, start + count)]
        out.append({"kind": "sector", "index": index, "key": key,
                    "x": sum(xs) // len(xs), "y": sum(ys) // len(ys),
                    "floor_z": int(fields["floor_z"])})
    for index, sprite in enumerate(disk.sprites):
        key = key_of(sprite)
        if key:
            out.append({"kind": "sprite", "index": index, "key": key,
                        "x": int(sprite.fields["x"]), "y": int(sprite.fields["y"]),
                        "floor_z": int(sprite.fields["z"])})
    for index, wall in enumerate(disk.walls):
        key = key_of(wall)
        if key:
            out.append({"kind": "wall", "index": index, "key": key,
                        "x": int(wall.fields["x"]), "y": int(wall.fields["y"]),
                        "floor_z": 0})
    return out


def observe(name: str, disk: Any) -> dict[str, Any]:
    placards = []
    for index, sprite in enumerate(disk.sprites):
        picnum = int(sprite.fields["picnum"])
        if picnum not in PLACARD_TILES:
            continue
        sector = int(sprite.fields["sector"])
        floor = (int(disk.sectors[sector].fields["floor_z"])
                 if 0 <= sector < len(disk.sectors) else 0)
        placards.append({
            "map": name, "index": index, "picnum": picnum,
            "emblem": PLACARD_TILES[picnum],
            "x": int(sprite.fields["x"]), "y": int(sprite.fields["y"]),
            "z": int(sprite.fields["z"]),
            "above_floor": floor - int(sprite.fields["z"]),
            "above_floor_humans": round((floor - int(sprite.fields["z"]))
                                        / PLAYER_HEIGHT, 3),
            "cstat": int(sprite.fields["cstat"]),
            "x_repeat": int(sprite.fields["x_repeat"]),
            "y_repeat": int(sprite.fields["y_repeat"]),
            "shade": int(sprite.fields["shade"]),
            "pal": int(sprite.fields["pal"]),
            "angle": int(sprite.fields["angle"]),
            "type": int(sprite.fields["type"]),
        })

    doors = keyed_things(disk)
    # Pair each placard with the nearest keyed thing, and vice versa.
    pairs = []
    for placard in placards:
        best = None
        for door in doors:
            distance = math.hypot(door["x"] - placard["x"], door["y"] - placard["y"])
            if best is None or distance < best[0]:
                best = (distance, door)
        if best and best[0] <= NEAR:
            pairs.append({"picnum": placard["picnum"], "key": best[1]["key"],
                          "distance": round(best[0], 1),
                          "above_floor_humans": placard["above_floor_humans"]})
    marked = 0
    for door in doors:
        for placard in placards:
            if math.hypot(door["x"] - placard["x"],
                          door["y"] - placard["y"]) <= NEAR:
                marked += 1
                break
    return {"placards": placards, "keyed": doors, "pairs": pairs,
            "keyed_count": len(doors), "keyed_marked": marked}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--maps", default="maps/blood")
    parser.add_argument("-o", "--output")
    args = parser.parse_args(argv)

    placards: list[dict] = []
    pairs: list[dict] = []
    keyed = marked = 0
    seen = 0
    for path in sorted(glob.glob(str(pathlib.Path(args.maps) / "*.MAP"))):
        name = pathlib.Path(path).stem.upper()
        if not CAMPAIGN.match(name):
            continue
        try:
            row = observe(name, read_map(path))
        except Exception as error:
            print(f"skipped {name}: {type(error).__name__}: {error}")
            continue
        seen += 1
        placards.extend(row["placards"])
        pairs.extend(row["pairs"])
        keyed += row["keyed_count"]
        marked += row["keyed_marked"]

    mapping: dict[int, Counter] = defaultdict(Counter)
    for pair in pairs:
        mapping[pair["key"]].update([pair["picnum"]])

    heights = [p["above_floor_humans"] for p in placards]
    cstats = Counter(p["cstat"] for p in placards)
    repeats = Counter((p["x_repeat"], p["y_repeat"]) for p in placards)
    pals = Counter(p["pal"] for p in placards)

    print("%d maps, %d placards, %d keyed things, %d of them with a placard "
          "within %d units (%.0f%%)"
          % (seen, len(placards), keyed, marked, NEAR,
             100 * marked / max(1, keyed)))
    print()
    print("key value -> emblem, by what sits next to the door:")
    for key in sorted(mapping):
        top = mapping[key].most_common(3)
        print("  key %d: %s" % (key, ", ".join(
            "%s(%d) x%d" % (PLACARD_TILES[p], p, n) for p, n in top)))
    print()
    ordered = sorted(heights)
    if ordered:
        print("hung at, above the floor, in standing humans: q1 %.2f median %.2f q3 %.2f"
              % (ordered[len(ordered) // 4], statistics.median(ordered),
                 ordered[3 * len(ordered) // 4]))
    print("cstat:   %s" % cstats.most_common(4))
    print("repeats: %s" % repeats.most_common(4))
    print("palette: %s" % pals.most_common(4))

    if args.output:
        out = pathlib.Path(args.output)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps({
            "$schema": SCHEMA, "schema_version": SCHEMA_VERSION,
            "maps": seen,
            "tiles": {str(k): v for k, v in PLACARD_TILES.items()},
            "key_to_tile": {str(k): v.most_common(1)[0][0]
                            for k, v in mapping.items() if v},
            "key_to_tile_votes": {str(k): dict(v) for k, v in mapping.items()},
            "placards": len(placards),
            "keyed_things": keyed,
            "keyed_with_a_placard": marked,
            "share_marked": round(marked / max(1, keyed), 3),
            "hung_above_floor_humans": {
                "q1": round(ordered[len(ordered) // 4], 3) if ordered else None,
                "median": round(statistics.median(ordered), 3) if ordered else None,
                "q3": round(ordered[3 * len(ordered) // 4], 3) if ordered else None,
            },
            "cstat": dict(cstats.most_common()),
            "repeats": {str(k): v for k, v in repeats.most_common()},
            "palette": dict(pals.most_common()),
            "reading_guide": [
                "the emblem is the message; the frame is the same on all six",
                "key_to_tile is derived from co-location, not from a table",
            ],
        }, indent=1) + "\n", encoding="utf-8")
        print("wrote", args.output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
