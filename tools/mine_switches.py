"""How high a switch hangs, and which tile says what it is.

Three questions, all answerable from the corpus:

1. **How high?** A switch the player has to touch must be within reach. Blood's
   use is a hitscan from the eye (``ActionScan``, range 64), so a switch above
   the player's aim is not a hard switch, it is an unreachable one.
2. **Which tile?** Blood distinguishes what a control *is* by its art. A switch
   you press, a switch you shoot and a lever are different tiles, and using one
   for another lies to the player about how to work it.
3. **The exit.** ``kChannelLevelExitNormal = 4`` (eventq.h:30) ends the level,
   and a switch that ends the level is conventionally not the same tile as one
   that opens a door.

What is measured
----------------

Every sprite of type 20-23 (``kSwitchToggle``, ``kSwitchOneWay``,
``kSwitchCombo``, ``kSwitchPadlock``), with its height above its sector floor in
standing humans, its tile, and how it is triggered. The last matters most: a
switch with ``trigger_push`` is worked by hand and must be in reach; one with
``trigger_impact`` or ``trigger_vector`` is shot, and may be anywhere the player
can aim.

.. code-block:: bash

    python -m tools.mine_switches -o knowledge/blood/design/switches-v1.json
"""

from __future__ import annotations

import argparse
import glob
import json
import pathlib
import re
import statistics
from collections import Counter, defaultdict
from typing import Any

from bloodmap.format import read_map
from bloodmap.player_space import PLAYER_PROFILES

SCHEMA = "llmapper.blood-switches"
SCHEMA_VERSION = 1

CAMPAIGN = re.compile(r"^E[1-46]M[1-9]$")
PLAYER_HEIGHT = PLAYER_PROFILES["blood"].standing_height
EYE_HEIGHT = PLAYER_PROFILES["blood"].eye_height

#: common_game.h:231-236
SWITCH_TYPES = {20: "toggle", 21: "one_way", 22: "combo", 23: "padlock"}

#: eventq.h:30-32
CHANNEL_EXIT = 4
CHANNEL_SECRET_EXIT = 5
CHANNEL_NAMES = {4: "level exit", 5: "secret exit", 6: "custom end"}


def extra_of(item: Any) -> dict:
    extra = getattr(item, "extra", None)
    if extra is None or not hasattr(extra, "fields"):
        return {}
    return extra.fields


def observe(name: str, disk: Any) -> list[dict[str, Any]]:
    out = []
    for index, sprite in enumerate(disk.sprites):
        fields = sprite.fields
        kind = int(fields["type"])
        if kind not in SWITCH_TYPES:
            continue
        extra = extra_of(sprite)
        sector = int(fields["sector"])
        floor = (int(disk.sectors[sector].fields["floor_z"])
                 if 0 <= sector < len(disk.sectors) else 0)
        shot = bool(int(extra.get("trigger_impact", 0) or 0)
                    or int(extra.get("trigger_vector", 0) or 0))
        pushed = bool(int(extra.get("trigger_push", 0) or 0)
                      or int(extra.get("trigger_wall_push", 0) or 0))
        out.append({
            "map": name, "index": index,
            "picnum": int(fields["picnum"]),
            "type": kind, "kind": SWITCH_TYPES[kind],
            "above_floor": floor - int(fields["z"]),
            "above_floor_humans": round((floor - int(fields["z"])) / PLAYER_HEIGHT, 3),
            "cstat": int(fields["cstat"]),
            "x_repeat": int(fields["x_repeat"]),
            "y_repeat": int(fields["y_repeat"]),
            "tx_id": int(extra.get("tx_id", 0) or 0),
            "command": int(extra.get("command", 0) or 0),
            "shot": shot,
            "pushed": pushed,
            "how": "shot" if (shot and not pushed) else
                   ("pushed" if pushed and not shot else
                    ("either" if shot and pushed else "unknown")),
        })
    return out


def band(values: list[float], digits: int = 2) -> dict[str, float]:
    ordered = sorted(values)
    if not ordered:
        return {}

    def at(f: float) -> float:
        return ordered[min(len(ordered) - 1, int(f * (len(ordered) - 1)))]

    return {"min": round(ordered[0], digits), "q1": round(at(0.25), digits),
            "median": round(statistics.median(ordered), digits),
            "q3": round(at(0.75), digits), "p95": round(at(0.95), digits),
            "max": round(ordered[-1], digits)}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--maps", default="maps/blood")
    parser.add_argument("-o", "--output")
    args = parser.parse_args(argv)

    rows: list[dict[str, Any]] = []
    seen = 0
    for path in sorted(glob.glob(str(pathlib.Path(args.maps) / "*.MAP"))):
        name = pathlib.Path(path).stem.upper()
        if not CAMPAIGN.match(name):
            continue
        try:
            rows.extend(observe(name, read_map(path)))
        except Exception as error:
            print(f"skipped {name}: {type(error).__name__}: {error}")
            continue
        seen += 1

    by_how: dict[str, list] = defaultdict(list)
    for row in rows:
        by_how[row["how"]].append(row)

    tiles = Counter(r["picnum"] for r in rows)
    exit_rows = [r for r in rows if r["tx_id"] == CHANNEL_EXIT]
    secret_rows = [r for r in rows if r["tx_id"] == CHANNEL_SECRET_EXIT]
    exit_tiles = Counter(r["picnum"] for r in exit_rows)
    other_tiles = Counter(r["picnum"] for r in rows if r["tx_id"] != CHANNEL_EXIT)

    print("%d maps, %d switches" % (seen, len(rows)))
    print()
    print("how they are worked:")
    for how in sorted(by_how):
        heights = [r["above_floor_humans"] for r in by_how[how]]
        print("  %-8s %4d   height above floor: %s"
              % (how, len(by_how[how]), band(heights)))
    print()
    print("the eye is at %.2f humans; anything much above that cannot be pressed"
          % (EYE_HEIGHT / PLAYER_HEIGHT))
    print()
    print("commonest switch tiles overall:")
    for picnum, count in tiles.most_common(12):
        print("    %5d  %4d" % (picnum, count))
    print()
    print("switches on channel %d (level exit): %d" % (CHANNEL_EXIT, len(exit_rows)))
    for picnum, count in exit_tiles.most_common(8):
        share_elsewhere = other_tiles.get(picnum, 0)
        print("    tile %5d used %3d times as an exit, %3d times for anything else"
              % (picnum, count, share_elsewhere))
    if exit_rows:
        print("    exit switch height: %s"
              % band([r["above_floor_humans"] for r in exit_rows]))
    print("switches on channel %d (secret exit): %d"
          % (CHANNEL_SECRET_EXIT, len(secret_rows)))
    for picnum, count in Counter(r["picnum"] for r in secret_rows).most_common(4):
        print("    tile %5d x%d" % (picnum, count))

    if args.output:
        out = pathlib.Path(args.output)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps({
            "$schema": SCHEMA, "schema_version": SCHEMA_VERSION,
            "maps": seen, "switches": len(rows),
            "unit": "standing humans (%d z)" % PLAYER_HEIGHT,
            "eye_height_humans": round(EYE_HEIGHT / PLAYER_HEIGHT, 3),
            "engine": {
                "types": {str(k): v for k, v in SWITCH_TYPES.items()},
                "types_source": "NBlood common_game.h:231-236",
                "exit_channel": CHANNEL_EXIT,
                "exit_channel_source": "NBlood eventq.h:30 kChannelLevelExitNormal",
            },
            "by_how": {how: {
                "count": len(items),
                "height_humans": band([r["above_floor_humans"] for r in items]),
                "tiles": dict(Counter(r["picnum"] for r in items).most_common(10)),
            } for how, items in by_how.items()},
            "tiles": dict(tiles.most_common()),
            "exit": {
                "count": len(exit_rows),
                "tiles": dict(exit_tiles),
                "tiles_elsewhere": {str(p): other_tiles.get(p, 0) for p in exit_tiles},
                "height_humans": band([r["above_floor_humans"] for r in exit_rows]),
            },
            "secret_exit": {
                "count": len(secret_rows),
                "tiles": dict(Counter(r["picnum"] for r in secret_rows)),
            },
            "rows": rows,
        }, indent=1) + "\n", encoding="utf-8")
        print("wrote", args.output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
