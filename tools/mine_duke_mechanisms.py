"""What a Duke map DOES: its sector tags, effectors and control sprites.

Blood puts its behaviour in XSECTOR/XSPRITE/XWALL structures.  Duke has no
such thing.  A Duke map's mechanisms are:

* a **sector lotag** naming what kind of sector it is (20 = ceiling door,
  21 = floor door, 25 = sliding door, 15 = warp elevator, 1 = above water);
* a **SECTOREFFECTOR** sprite (tile 1) sitting in that sector, whose own
  lotag selects the effect (SE 6 subway, SE 11 swinging door, SE 17 warp
  elevator, SE 24 conveyor, SE 31 floor rise/fall);
* **control sprites** -- ACTIVATOR, TOUCHPLATE, MASTERSWITCH, CYCLER,
  MUSICANDSFX, RESPAWN, LOCATORS, GPSPEED -- wired together by `hitag`
  channel numbers.

`knowledge/duke3d/semantics-v1.json` supplies the names, transcribed from
Duke's own DEFS.CON and EDuke32's `game.h`; this counts what each map
actually uses so the vocabulary can be read rather than guessed at.

    python tools/mine_duke_mechanisms.py DukCity1 DukCity2 DukCity3 DukCity4
"""

from __future__ import annotations

import argparse
import collections
import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from bloodmap.duke import read_duke_map

SEMANTICS = ROOT / "knowledge" / "duke3d" / "semantics-v1.json"


def load_semantics() -> dict:
    with SEMANTICS.open(encoding="utf-8") as handle:
        return json.load(handle)


def name_of(sem, picnum: int) -> str:
    names = sem["tiles_by_number"].get(str(picnum))
    return names[0] if names else f"tile{picnum}"


def survey(path: pathlib.Path, sem: dict) -> dict:
    m = read_duke_map(path)
    control = {v: k for k, v in sem["control_sprites"].items()}
    tags = sem["sector_tags"]
    effects = sem["sector_effectors"]

    sector_tags = collections.Counter()
    for s in m.sectors:
        if s.lotag:
            sector_tags[s.lotag] += 1
    effectors = collections.Counter()
    controls = collections.Counter()
    channels = collections.Counter()
    for sp in m.sprites:
        role = control.get(sp.picnum)
        if role is None:
            continue
        controls[role] += 1
        if sp.hitag:
            channels[sp.hitag] += 1
        if role == "SECTOREFFECTOR":
            effectors[sp.lotag] += 1

    # Anything that is neither control nor an actor: the scenery vocabulary.
    scenery = collections.Counter()
    for sp in m.sprites:
        if sp.picnum in control:
            continue
        scenery[sp.picnum] += 1

    return {
        "map": path.stem,
        "sectors": len(m.sectors),
        "walls": len(m.walls),
        "sprites": len(m.sprites),
        "sector_tags": {tags.get(str(k), f"lotag {k}"): n
                        for k, n in sector_tags.most_common()},
        "sector_effectors": {effects.get(str(k), f"SE {k}"): n
                             for k, n in effectors.most_common()},
        "control_sprites": dict(controls.most_common()),
        "distinct_channels": len(channels),
        "scenery_top": {name_of(sem, k): n for k, n in scenery.most_common(20)},
    }


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("maps", nargs="*")
    ap.add_argument("--dir", default="maps/duke3d")
    ap.add_argument("-o", "--output",
                    default="knowledge/duke3d/mechanisms-v1.json")
    args = ap.parse_args(argv)

    sem = load_semantics()
    directory = ROOT / args.dir
    names = args.maps or sorted(p.stem for p in directory.glob("*.map"))
    rows = []
    for name in names:
        path = directory / f"{name}.map"
        try:
            rows.append(survey(path, sem))
        except Exception as exc:
            print(f"!! {name}: {exc}")
    # What the corpus uses overall, so a rare effect is visibly rare.
    totals = collections.Counter()
    effect_maps = collections.Counter()
    for row in rows:
        for effect, n in row["sector_effectors"].items():
            totals[effect] += n
            effect_maps[effect] += 1
    out = {
        "$schema": "llmapper.duke-mechanisms",
        "schema_version": 1,
        "maps_examined": len(rows),
        "effector_totals": dict(totals.most_common()),
        "effector_map_counts": dict(effect_maps.most_common()),
        "maps": rows,
    }
    path = ROOT / args.output
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(out, indent=1), encoding="utf-8")
    for row in rows:
        print(f"\n== {row['map']}: {row['sectors']} sectors, "
              f"{row['sprites']} sprites, {row['distinct_channels']} channels")
        print(f"   sector tags: {row['sector_tags']}")
        print(f"   effectors:   {row['sector_effectors']}")
        print(f"   controls:    {row['control_sprites']}")
    print(f"\nwrote {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
