"""Discover, catalogue and browse what tiles are used as, where, and on whose evidence.

The front of `bloodmap.tile_contexts`, for agents building a level:

``mine``      count every (tile, slot, kind of place) over a population of
              maps -- the campaign, the owner's own maps, the curated and the
              community ones -- into `knowledge/blood/tile-contexts/`
``show``      everything known of one tile, context by context, with whose
              evidence: the owner's word, then counts, then agents' readings
``where``     what Blood puts in a slot (and a kind of place): "what do
              step faces in a church wear?", most used first, with names
``discover``  what a map does that the campaign and the owner's maps never
              show: discoveries to catalogue, or mistakes to fix
``record``    catalogue a reading: what a tile IS in a context, and what it
              was read from (the picture, a frame, a map)

.. code-block:: bash

    python -m tools.tile_contexts mine --population blood-campaign
    python -m tools.tile_contexts show 364
    python -m tools.tile_contexts where two_sided_lower --place church
    python -m tools.tile_contexts discover projects/blood-city/level/blood-city-current.MAP
    python -m tools.tile_contexts record 364 --slot two_sided_lower \\
        --is "ogee lattice stone, a drum's face" --evidence "RABIDN09 sector 190"

Mining the 1,500 community maps takes a while; run it in the background.
"""

from __future__ import annotations

import argparse
import json
import pathlib
import sys
import time

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from bloodmap import tile_contexts as tc  # noqa: E402


def _labels() -> dict[str, dict[int, str]]:
    """Map name -> sector -> the kind of place the catalog labels it."""
    from tools import catalog

    places = catalog.sector_places()
    kinds = {pid: row.get("kind") for pid, row in catalog.place_labels().items()}
    out: dict[str, dict[int, str]] = {}
    for map_name, sectors in places.items():
        out[map_name] = {s: kinds[p] for s, p in sectors.items() if kinds.get(p)}
    return out


def _population_maps(population: str) -> list[tuple[str, pathlib.Path]]:
    if population == "owner-map":
        if not tc.OWNER_MAPS.exists():
            return []
        rows = json.loads(tc.OWNER_MAPS.read_text("utf-8"))["maps"]
        return [(r["name"], pathlib.Path(r["path"])) for r in rows
                if pathlib.Path(r["path"]).exists()]
    from bloodmap.corpus import list_corpus_maps

    return [(item.path.stem.upper(), item.path)
            for item in list_corpus_maps(population=population)]


def mine(population: str) -> dict:
    from bloodmap.format import read_map

    labels = _labels()
    maps = _population_maps(population)
    started = time.time()
    names, failed = [], []

    def disks():
        for name, path in maps:
            try:
                disk = read_map(path)
            except Exception as exc:                            # noqa: BLE001
                failed.append(f"{name}: {exc}"[:120])
                continue
            names.append(name)
            yield name, disk, labels.get(name)

    table = tc.mine(disks())
    path = tc.save_mined(population, table, maps=names)
    failed += table.get("failed", [])
    return {"population": population, "maps": table["maps"], "failed": failed[:5],
            "failed_count": len(failed), "tiles": len(table["tiles"]),
            "seconds": round(time.time() - started), "path": str(path)}


def _name(tile: int) -> str:
    from tools import catalog

    source, name = catalog.tile_name(tile)
    return f"{name} ({source})" if name else "(nobody has named or read it)"


def show(tile: int) -> str:
    rows = tc.contexts(tile)
    lines = [f"TILE {tile}: {_name(tile)}"]
    if not rows:
        lines.append("  no context known: mine the populations, or record a reading")
    for row in rows:
        where = f"{row['slot']} in {row['place']}"
        if "count" in row:
            ex = ", ".join(f"{m} {k} {i}" for m, k, i in row["examples"])
            lines.append(f"  {row['source']:17s} {where:40s} {row['count']:5d} x in "
                         f"{row['maps']:3d} maps  e.g. {ex}")
        else:
            tag = "MISFIT" if row.get("fits") is False else "is"
            lines.append(f"  {row['source']:17s} {where:40s} {tag}: {row['is']}  "
                         f"[{row['evidence']}{', ' + row['date'] if row.get('date') else ''}]")
    return "\n".join(lines)


def where(slot: str, place: str | None, at_least: str, limit: int) -> str:
    rows = tc.suggest(slot, place, at_least=at_least, limit=limit)
    lines = [f"{slot} in {place or 'any place'} (evidence up to {at_least}):"]
    for row in rows:
        sources = ", ".join(f"{k} {v}" for k, v in row["sources"].items())
        lines.append(f"  {row['tile']:5d}  {row['maps']:4d} maps  {_name(row['tile'])[:60]:60s} [{sources}]")
    return "\n".join(lines)


def discover(map_path: str, limit: int) -> str:
    from bloodmap.format import read_map

    disk = read_map(map_path)
    rows = tc.novel(disk)
    unseen = [r for r in rows if r["evidence"] is None]
    elsewhere = [r for r in rows if r["evidence"] is not None]
    lines = [f"{pathlib.Path(map_path).name}: {len(unseen)} uses nobody has shown, "
             f"{len(elsewhere)} shown only outside the campaign and the owner's maps"]
    for row in unseen[:limit]:
        lines.append(f"  NEW   {row['tile']:5d} {row['slot']:18s} {row['place']:12s} x{row['count']:<3d} "
                     f"{row['first'][0]} {row['first'][1]}  {_name(row['tile'])[:50]}")
    for row in elsewhere[:limit]:
        ev = row["evidence"]
        lines.append(f"  SEEN  {row['tile']:5d} {row['slot']:18s} {row['place']:12s} x{row['count']:<3d} "
                     f"by {ev['source']} ({ev.get('maps', '?')} maps)  {_name(row['tile'])[:40]}")
    for row in rows:
        for said in row.get("misfit") or []:
            lines.append(f"  MISFIT {row['tile']:5d} {row['slot']:18s} {row['place']:12s} "
                         f"x{row['count']:<3d} {said[:70]}")
    lines.append("  catalogue what a NEW use is with `record` (or `record --misfit` "
                 "what goes wrong), or fix it in the map")
    return "\n".join(lines)


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    sub = parser.add_subparsers(dest="command", required=True)
    m = sub.add_parser("mine")
    m.add_argument("--population", action="append",
                   help=f"one of {', '.join(tc.MINED)}; repeat, or omit for all but community")
    s = sub.add_parser("show")
    s.add_argument("tile", type=int)
    w = sub.add_parser("where")
    w.add_argument("slot")
    w.add_argument("--place", default=None)
    w.add_argument("--at-least", default="community", choices=tc.AUTHORITY[1:])
    w.add_argument("--limit", type=int, default=20)
    d = sub.add_parser("discover")
    d.add_argument("map")
    d.add_argument("--limit", type=int, default=25)
    r = sub.add_parser("record")
    r.add_argument("tile", type=int)
    r.add_argument("--slot", default=tc.ANY)
    r.add_argument("--place", default=tc.ANY)
    r.add_argument("--is", dest="is_", required=True)
    r.add_argument("--evidence", required=True)
    r.add_argument("--by", default="agent")
    r.add_argument("--misfit", action="store_true",
                   help="what goes WRONG with the tile there: a warning, never permission")
    args = parser.parse_args(argv)
    if args.command == "mine":
        for population in args.population or [p for p in tc.MINED if p != "community"]:
            print(json.dumps(mine(population)))
    elif args.command == "show":
        print(show(args.tile))
    elif args.command == "where":
        print(where(args.slot, args.place, args.at_least, args.limit))
    elif args.command == "discover":
        print(discover(args.map, args.limit))
    elif args.command == "record":
        print(json.dumps(tc.record(args.tile, slot=args.slot, place=args.place,
                                   is_=args.is_, evidence=args.evidence, by=args.by,
                                   fits=not args.misfit)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
