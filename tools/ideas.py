"""An idea catalogue: tour a map nobody asked about, and file what is seen.

The owner, 2026-11-18: "You can even study random levels for inspiration
to get you new ideas that can be catalogised."

`tools/study.py` answers a question already asked ("how did Blood build a
crypt?"). This is the other half of learning: looking at maps with no
question in mind, so there are ideas on file BEFORE the question comes.

.. code-block:: bash

    python -m tools.ideas pick --n 2                 # maps not toured yet
    python -m tools.ideas tour E2M4                  # frames of its places
    python -m tools.ideas add --map E2M4 --sector 613 --kind set-piece \\
        --title "..." --what "..." --recipe "..." --use "..."
    python -m tools.ideas list --kind mechanism --grep lift
    python -m tools.ideas use E2M4-613-... --where "St Gallow's crypt"

**A tour** picks the places of a map most worth standing in -- the ones
with the most detail layers, the ones with moving sectors, the tallest
and the biggest -- renders each as the game shows it from its corners,
draws its plan, and prints what it is made of. Looking at the frames is
the mapper's job; the tool only puts them in front of it.

**A card** is one idea, small enough to reuse: what it is, where it was
seen (map and sector, so it can be looked at again), a recipe in sizes
and tiles, and where it might go. Cards are one file each under
``knowledge/blood/ideas/cards/`` so two tours can file at once.

Kinds: ``set-piece`` (a thing a room is for), ``mechanism`` (something
that moves or is triggered), ``composition`` (how spaces are arranged or
seen from one another), ``detail`` (a small touch of tile or sprite),
``lighting``, ``encounter`` (how enemies are met), ``secret``,
``transition`` (how one place leads into another).
"""

from __future__ import annotations

import argparse
import datetime
import json
import pathlib
import random
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "projects" / "blood-city" / "level"))

IDEAS = ROOT / "knowledge" / "blood" / "ideas"
CARDS = IDEAS / "cards"
TOURS = IDEAS / "tours"
KINDS = ("set-piece", "mechanism", "composition", "detail", "lighting",
         "encounter", "secret", "transition")
POPULATIONS = ("blood-campaign", "community-curated")


def _maps() -> dict[str, pathlib.Path]:
    from bloodmap.corpus import list_corpus_maps

    out = {}
    for population in POPULATIONS:
        for item in list_corpus_maps(population=population):
            out[item.path.stem.upper()] = item.path
    return out


def toured() -> set[str]:
    return {p.name.upper() for p in TOURS.iterdir()} if TOURS.exists() else set()


def cards() -> list[dict]:
    out = []
    if CARDS.exists():
        for path in sorted(CARDS.glob("*.json")):
            card = json.loads(path.read_text("utf-8"))
            card["id"] = path.stem
            out.append(card)
    return out


def tour(name: str, count: int = 8) -> list[dict]:
    """Render the places of one map most worth standing in."""
    from bloodmap.blood_types import SPRITE_TYPES
    from bloodmap.format import read_map
    from tools import place_character as pc
    from tools import study

    path = _maps()[name.upper()]
    geom = pc.Geometry(read_map(path))
    rows = []
    for place in pc.places(geom):
        profile = pc.profile(geom, place)
        if profile["solid_wall"] < 4096:
            continue
        rows.append((place, profile))
    #: the most layered, the ones that move most, the tallest, the biggest
    chosen: list = []
    for key in (lambda r: -r[1]["layer_count"],
                lambda r: -r[1]["moving_sectors"],
                lambda r: -r[1]["clear_bodies"],
                lambda r: -r[1]["machines"],
                lambda r: -r[1]["area_M"]):
        for row in sorted(rows, key=key):
            if all(row[1]["host"] != c[1]["host"] for c in chosen):
                chosen.append(row)
                break
    for row in sorted(rows, key=lambda r: -r[1]["layer_count"]):
        if len(chosen) >= count:
            break
        if all(row[1]["host"] != c[1]["host"] for c in chosen):
            chosen.append(row)
    folder = TOURS / name.upper()
    folder.mkdir(parents=True, exist_ok=True)
    names = pc.names()
    report = []
    for place, profile in chosen:
        host = profile["host"]
        out = folder / f"place_{host}"
        out.mkdir(parents=True, exist_ok=True)
        study._plan(geom, place, out / "plan.png")
        try:
            frames = study._frames(path, geom, place, host, out)
        except Exception as error:                          # noqa: BLE001
            frames = [f"(no frames: {error})"]
        movers = sorted({int(geom.sectors[s]["type"]) for s in place
                         if int(geom.sectors[s]["type"])})
        report.append({
            "host": host, "sky": profile["sky"], "metres": profile["metres"],
            "layers": [k for k, v in profile["layers"].items() if v],
            "sector_types": movers,
            "walls": [[t, s, names.get(t, "")]
                      for t, s in profile["wall_tiles"][:5]],
            "things": len(study._things(geom, place, host)),
            "sprites": study._sprites_of(geom, place, SPRITE_TYPES)[:10],
            "plan": str(out / "plan.png"), "frames": frames})
    (folder / "tour.json").write_text(json.dumps(
        {"map": name.upper(), "date": datetime.date.today().isoformat(),
         "places": report}, indent=1), "utf-8")
    return report


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    sub = parser.add_subparsers(dest="command", required=True)
    pick = sub.add_parser("pick")
    pick.add_argument("--n", type=int, default=1)
    pick.add_argument("--seed", type=int)
    tour_ = sub.add_parser("tour")
    tour_.add_argument("map")
    tour_.add_argument("--places", type=int, default=8)
    add = sub.add_parser("add")
    for flag in ("--map", "--kind", "--title", "--what", "--recipe", "--use"):
        add.add_argument(flag, required=True)
    add.add_argument("--sector", type=int, required=True)
    add.add_argument("--frame", default="")
    lst = sub.add_parser("list")
    lst.add_argument("--kind")
    lst.add_argument("--grep")
    lst.add_argument("--unused", action="store_true")
    use = sub.add_parser("use")
    use.add_argument("id")
    use.add_argument("--where", required=True)
    args = parser.parse_args(argv)

    if args.command == "pick":
        left = sorted(set(_maps()) - toured())
        random.Random(args.seed).shuffle(left)
        print(" ".join(left[:args.n]) or "(every map has been toured)")
        return 0
    if args.command == "tour":
        for row in tour(args.map, args.places):
            print(f"s{row['host']:<5} {'outdoor' if row['sky'] else 'indoor':<8}"
                  f"{row['metres'][0]} x {row['metres'][1]} m, "
                  f"{row['metres'][2]} m high; layers {','.join(row['layers'])}; "
                  f"moves {row['sector_types']}; {row['things']} things")
            print(f"       walls {[(t, n) for t, _s, n in row['walls'][:3]]}")
            print(f"       frames {row['frames']}")
        return 0
    if args.command == "add":
        if args.kind not in KINDS:
            parser.error(f"kind must be one of {', '.join(KINDS)}")
        slug = re.sub(r"[^a-z0-9]+", "-", args.title.lower()).strip("-")[:40]
        CARDS.mkdir(parents=True, exist_ok=True)
        path = CARDS / f"{args.map.upper()}-{args.sector}-{slug}.json"
        path.write_text(json.dumps({
            "map": args.map.upper(), "sector": args.sector, "kind": args.kind,
            "title": args.title, "what": args.what, "recipe": args.recipe,
            "use": args.use, "frame": args.frame,
            "date": datetime.date.today().isoformat(), "used_in": []},
            indent=1), "utf-8")
        print(path)
        return 0
    if args.command == "list":
        for card in cards():
            if args.kind and card["kind"] != args.kind:
                continue
            text = " ".join(str(card[k]) for k in ("title", "what", "recipe",
                                                   "use"))
            if args.grep and args.grep.lower() not in text.lower():
                continue
            if args.unused and card["used_in"]:
                continue
            print(f"{card['id']}\n   [{card['kind']}] {card['title']} "
                  f"({card['map']} s{card['sector']})"
                  f"{'  USED: ' + '; '.join(card['used_in']) if card['used_in'] else ''}"
                  f"\n   {card['what']}\n   recipe: {card['recipe']}"
                  f"\n   could go: {card['use']}")
        return 0
    if args.command == "use":
        path = CARDS / f"{args.id}.json"
        card = json.loads(path.read_text("utf-8"))
        card["used_in"].append(args.where)
        path.write_text(json.dumps(card, indent=1), "utf-8")
        print("marked")
        return 0
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
