"""Authored values the campaign never uses for that type.

The fault class this exists for is the one no structural check can see: a map
that is perfectly valid, loads without complaint, and carries a field value Blood
never wrote. `(state 1, busy 0)` on a slide sector was exactly that -- legal,
loadable, and a door that could not be opened, because the campaign's 659 slide
and rotate sectors only ever rest at `(0, 0)` or `(1, 65536)`.

Run it over a built map::

    python -m tools.unattested_values projects/.../candidate-v5.MAP

The comparison is per (kind, type, field), so a switch is judged against
switches. Two kinds of field are excluded, because comparing their values across
maps means nothing:

* **index fields** name another object -- `marker_0` is a sprite number, so
  "the campaign never uses 0 here" only says sprite 0 is rarely a marker;
* **runtime fields** are scratch the engine owns and overwrites -- the campaign
  ships `target` and `burn_source` at 0 and the project writes -1, and both are
  safe, since `actOwnerIdToSpriteId` returns -1 unchanged and the AI paths guard
  on `!= -1`.

Without those exclusions the report is 99 lines of which 92 are noise. With them
it is seven, and all seven are real.
"""

from __future__ import annotations

import argparse
import glob
import pathlib
import re
from collections import Counter, defaultdict
from typing import Any

from bloodmap.format import read_map

CAMPAIGN = re.compile(r"^E[1-46]M[1-9]$")

#: Fields holding the index of another object. Their values are addresses, not
#: intent, and are only meaningful within the map that wrote them.
INDEX_FIELDS = frozenset({"reference", "marker_0", "marker_1", "target", "burn_source"})

#: Fields the engine writes during play. An authored value is a starting point
#: the first tick may overwrite, so a difference from the campaign is not a
#: statement about the level's design.
RUNTIME_FIELDS = frozenset({
    "busy", "target_x", "target_y", "target_z", "burn_time", "health",
    "move_state", "sys_data_1", "sys_data_2", "sys_data_3", "sys_data_4",
})

#: `busy` is runtime state everywhere except on a moving sector, where it is
#: half of the authored resting pose and the whole reason a door works.
POSE_TYPES = frozenset({600, 601, 602, 613, 614, 615, 616, 617, 618})


def campaign_distribution(directory: str) -> dict[tuple[str, int, str], Counter]:
    dist: dict[tuple[str, int, str], Counter] = defaultdict(Counter)
    for path in sorted(glob.glob(str(pathlib.Path(directory) / "*.MAP"))):
        if not CAMPAIGN.match(pathlib.Path(path).stem.upper()):
            continue
        try:
            disk = read_map(path)
        except Exception:
            continue
        for kind, items in (("sector", disk.sectors), ("wall", disk.walls),
                            ("sprite", disk.sprites)):
            for item in items:
                type_id = int(item.fields["type"])
                if not type_id or item.extra is None:
                    continue
                for name, value in item.extra.fields.items():
                    dist[(kind, type_id, name)][int(value)] += 1
    return dist


def _skip(kind: str, type_id: int, field: str) -> bool:
    if field in INDEX_FIELDS:
        return True
    if field == "busy":
        return not (kind == "sector" and type_id in POSE_TYPES)
    return field in RUNTIME_FIELDS


def unattested(disk: Any, dist: dict[tuple[str, int, str], Counter],
               *, rare_share: float = 0.0) -> list[dict[str, Any]]:
    """Every authored value the campaign uses at or below `rare_share` of the time.

    At the default of zero this reports only values the campaign never uses at
    all, which is the question worth asking first.
    """
    out: list[dict[str, Any]] = []
    for kind, items in (("sector", disk.sectors), ("wall", disk.walls),
                        ("sprite", disk.sprites)):
        for index, item in enumerate(items):
            type_id = int(item.fields["type"])
            if not type_id or item.extra is None:
                continue
            for name, raw in item.extra.fields.items():
                if _skip(kind, type_id, name):
                    continue
                value = int(raw)
                seen = dist.get((kind, type_id, name))
                if not seen:
                    continue
                total = sum(seen.values())
                share = seen.get(value, 0) / total
                if share <= rare_share:
                    out.append({
                        "kind": kind, "index": index, "type": type_id,
                        "field": name, "value": value,
                        "campaign_share": round(share, 4),
                        "campaign_n": total,
                        "campaign_common": seen.most_common(3),
                    })
    return out


def statnum_distribution(directory: str) -> dict[int, Counter]:
    """type -> how the campaign distributes that type across statnums."""
    dist: dict[int, Counter] = defaultdict(Counter)
    for path in sorted(glob.glob(str(pathlib.Path(directory) / "*.MAP"))):
        if not CAMPAIGN.match(pathlib.Path(path).stem.upper()):
            continue
        try:
            disk = read_map(path)
        except Exception:
            continue
        for sprite in disk.sprites:
            type_id = int(sprite.fields["type"])
            if type_id:
                dist[type_id][int(sprite.fields["status"])] += 1
    return dist


def misfiled_sprites(disk: Any, dist: dict[int, Counter]) -> list[dict[str, Any]]:
    """Sprites on a statnum the campaign never uses for their type.

    Blood dispatches almost everything by statnum, not by type: `actInit` walks
    one list per statnum and `actDamageSprite` switches on it before it looks at
    anything else. A sprite filed on the wrong list keeps its type and its
    picture and quietly stops being that kind of object.

    The wall crack is the worked example. All 108 campaign cracks sit on statnum
    4, kStatThing; this level's sat on 0. `actDamageSprite` runs the
    health-and-trigger path under `case kStatThing` only, and `actInit` hands out
    `startHealth` on the same list -- so off it the crack could not be hurt,
    never reached zero health, never called `trTriggerSprite`, and the charges
    behind it never fired.
    """
    out: list[dict[str, Any]] = []
    for index, sprite in enumerate(disk.sprites):
        type_id = int(sprite.fields["type"])
        if not type_id:
            continue
        seen = dist.get(type_id)
        if not seen:
            continue
        status = int(sprite.fields["status"])
        if seen.get(status, 0):
            continue
        out.append({
            "sprite": index, "type": type_id, "status": status,
            "campaign": dict(seen),
        })
    return out


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("map")
    parser.add_argument("--corpus", default="maps/blood")
    parser.add_argument("--rare-share", type=float, default=0.0,
                        help="also report values this rare or rarer (0 = never used)")
    args = parser.parse_args(argv)

    dist = campaign_distribution(args.corpus)
    if not dist:
        print("no campaign maps found; nothing to compare against")
        return 1
    disk = read_map(args.map)

    misfiled = misfiled_sprites(disk, statnum_distribution(args.corpus))
    for row in misfiled:
        print("sprite %-5d type %-5d is on statnum %d; the campaign files that type on %s"
              % (row["sprite"], row["type"], row["status"], row["campaign"]))
    if misfiled:
        print()

    findings = unattested(disk, dist, rare_share=args.rare_share)
    if not findings:
        if not misfiled:
            print("every authored value is one the campaign uses")
        return 1 if misfiled else 0
    print("%-7s %-6s %-5s %-18s %8s  %s" %
          ("kind", "index", "type", "field", "value", "campaign"))
    for row in findings:
        common = ", ".join("%d x%d" % pair for pair in row["campaign_common"])
        print("%-7s %-6d %-5d %-18s %8d  %.1f%% of %d (%s)" % (
            row["kind"], row["index"], row["type"], row["field"], row["value"],
            100 * row["campaign_share"], row["campaign_n"], common))
    print("\n%d authored value(s) the campaign does not support" % len(findings))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
