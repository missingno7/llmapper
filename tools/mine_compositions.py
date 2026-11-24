"""Mine and search geometric compositions across the Blood map corpus."""

from __future__ import annotations

import argparse
from collections import Counter
from concurrent.futures import ProcessPoolExecutor
from dataclasses import dataclass
import json
import os
from pathlib import Path
import re
import sys
from tempfile import NamedTemporaryFile
from time import perf_counter
from typing import Iterable

from bloodmap import compositions, corpus
from bloodmap.art import ArtError, read_art_directory
from bloodmap.format import BloodMapError, read_map
from tools import catalog

NAMED = catalog.DESIGN / "compositions-v1.json"
COMMUNITY = catalog.DESIGN / "compositions-community-v1.json"
CONVERSIONS = catalog.DESIGN.parent / "duke-conversions.json"
ART = catalog.ROOT / "reference" / "blood"
KINDS = ("ring", "square", "pillars", "nest", "round", "focus", "group")
SOURCES = ("campaign", "curated", "community")
COMMUNITY_LIMIT = 3_000_000
WORD = re.compile(r"\w+")


@dataclass(frozen=True)
class _Job:
    path: Path
    source: str
    provenance: str
    relative: str


def _named_jobs() -> list[_Job]:
    campaign = set(corpus.campaign_maps(required=True))
    jobs = []
    for path in sorted(campaign | set(corpus.named_maps()), key=lambda p: (p.stem.upper(), p)):
        try:
            item = corpus.resolve_corpus_map(path)
            provenance, relative = item.population, item.relative
        except corpus.CorpusError:  # a supported flat corpus
            provenance, relative = corpus.classify_map_population(path), path.name
        jobs.append(_Job(path, "campaign" if path in campaign else "curated", provenance, relative))
    return jobs


def _community_jobs() -> list[_Job]:
    excluded = set()
    if CONVERSIONS.exists():
        excluded = {row["map"].casefold()
                    for row in json.loads(CONVERSIONS.read_text("utf-8"))["conversions"]}
    items = corpus.list_corpus_maps(population="community", attach_tiers=False)
    jobs = [_Job(item.path, "community", item.population, item.relative) for item in items
            if item.relative.casefold() not in excluded and not corpus.is_editor_autosave(item.path)]
    print(f"Community registry has {len(jobs)} eligible maps, {len(items) - len(jobs)} excluded")
    return jobs


def _directional_art() -> frozenset[int]:
    try:
        tiles = read_art_directory(ART)
    except (ArtError, OSError) as error:
        print(f"ART unavailable, using native dude and wall-sprite angles ({error})", file=sys.stderr)
        return frozenset()
    # NBlood viewProcessSprites selects five mirrored or eight full views
    # from the low three bits of picanm.extra (ART bits 28..30).
    return frozenset(tile for tile, art in tiles.items() if ((art.picanm >> 28) & 7) in (1, 2))


_DIRECTIONAL_TILES: frozenset[int] = frozenset()


def _worker_init(directional: frozenset[int]) -> None:
    global _DIRECTIONAL_TILES
    _DIRECTIONAL_TILES = directional


def _scan(job: _Job) -> tuple[list[dict], str | None]:
    try:
        disk = read_map(job.path, verify_crc=job.source != "community")
    except (BloodMapError, OSError) as error:
        return [], str(error)
    try:
        rows = compositions.observe_compositions(disk, directional_tiles=_DIRECTIONAL_TILES)
    except (ArithmeticError, LookupError, ValueError) as error:
        if job.source != "community":                      # a shipped map the reader cannot read is the reader's fault
            raise
        return [], f"{type(error).__name__}: {error}"
    for row in rows:
        row.update(map=job.path.stem.upper(), source=job.source, provenance=job.provenance)
        if job.source == "community":
            row["path"] = job.relative
    return rows, None


def _scan_jobs(jobs: list[_Job], serial: bool, directional: frozenset[int]) -> tuple[list[dict], int]:
    rows, failed = [], 0

    def collect(results: Iterable[tuple[list[dict], str | None]]) -> None:
        nonlocal failed
        for job, (found, error) in zip(jobs, results):
            if error is not None:
                failed += 1
                print(f"{job.relative}: {error}", file=sys.stderr)
            else:
                rows.extend(found)

    if serial:
        _worker_init(directional)
        collect(map(_scan, jobs))
    else:
        with ProcessPoolExecutor(max_workers=min(8, os.cpu_count() or 1),
                                 initializer=_worker_init, initargs=(directional,)) as pool:
            collect(pool.map(_scan, jobs, chunksize=4))
    return rows, failed


def _join_places(rows: list[dict]) -> None:
    where = catalog.sector_places() if catalog.PLACES.exists() else {}
    labels = catalog.place_labels()
    for row in rows:
        places = where.get(row["map"], {})
        room = places.get(row["host_sector"]) or places.get(row["centre_sector"])
        row["place"] = room
        row["room_kind"] = labels.get(room, {}).get("kind")


def _compact(row: dict) -> dict:
    slim = {k: v for k, v in row.items() if k not in ("members", "id")}
    slim["centre_contents"] = [{"picnum": picnum, "type": kind}
                              for picnum, kind in sorted({(s["picnum"], s["type"])
                                                          for s in row["centre_contents"]})]
    slim["wiring"] = [{"tx_id": tx, "rx_id": rx}
                      for tx, rx in sorted({(w["tx_id"], w["rx_id"]) for w in row["wiring"]})]
    if row["kind"] == "group":
        slim["layers"] = [{k: v for k, v in layer.items() if k not in ("id", "radius")}
                          for layer in row["layers"]]
    return slim


def _dump(value: dict) -> str:
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"))


def _rank(row: dict) -> tuple:
    return (-row["score"], -row["count"], row["map"], row.get("path", ""),
            row["host_sector"], row["kind"], row["centre"])


def _write(path: Path, rows: list[dict], maps: int, failed: int, *, community: bool) -> int:
    header = {"$schema": "llmapper.compositions", "schema_version": 1,
              "maps": maps, "unreadable": failed}
    footer = "\n]}\n"
    omitted = 0
    if community:
        # Rank before applying the byte budget. Source names are UTF-8, so
        # characters are not necessarily bytes.
        selected = [r for r in rows if ((r["kind"] == "group" and r["count"] >= 2)
                                       or (r["kind"] == "ring" and r["count"] >= 5))]
        kept = []
        budget = COMMUNITY_LIMIT - len(_dump(header).encode("utf-8")) - 128
        for row in sorted(selected, key=_rank):
            line = _dump(_compact(row))
            budget -= len(line.encode("utf-8")) + 2
            if budget < 0:
                break
            kept.append((row, line))
        omitted = len(selected) - len(kept)
        header["omitted_for_size"] = omitted
    else:
        kept = [(row, _dump(row)) for row in rows]
    kept.sort(key=lambda pair: (pair[0]["map"], pair[0].get("path", ""), pair[0]["id"]))
    path.parent.mkdir(parents=True, exist_ok=True)
    with NamedTemporaryFile(mode="w", encoding="utf-8", newline="\n", dir=path.parent,
                            prefix=path.stem + "-", suffix=".tmp", delete=False) as out:
        temp = Path(out.name)
        out.write(_dump(header)[:-1] + ',"records":[\n')
        out.write(",\n".join(line for _row, line in kept))
        out.write(footer)
    try:
        temp.replace(path)
    finally:
        temp.unlink(missing_ok=True)
    if omitted:
        print(f"Omitted {omitted} lower-scoring community records at the 3 MB budget")
    return len(kept)


def mine(*, community: bool = False, serial: bool = False) -> int:
    start = perf_counter()
    jobs = _named_jobs()
    directional = _directional_art()
    rows, failed = _scan_jobs(jobs, serial, directional)
    if failed:
        print("Named shelf left intact because a named map could not be read", file=sys.stderr)
        return 1
    _join_places(rows)
    total = _write(NAMED, rows, len(jobs), failed, community=False)
    print(f"{len(jobs)} named maps, {total} compositions in {perf_counter() - start:.2f}s")
    for source in SOURCES[:2]:
        counts = Counter(r["kind"] for r in rows if r["source"] == source)
        print(f"  {source} ({sum(job.source == source for job in jobs)} maps) "
              + ", ".join(f"{kind} {counts[kind]}" for kind in KINDS))
    print(f"  {NAMED.relative_to(catalog.ROOT)}")
    if community:
        start = perf_counter()
        jobs = _community_jobs()
        if not jobs:
            print("No eligible community maps. Community shelf left intact.", file=sys.stderr)
            return 1
        rows, failed = _scan_jobs(jobs, serial, directional)
        if failed == len(jobs):
            print("No readable community maps. Community shelf left intact.", file=sys.stderr)
            return 1
        total = _write(COMMUNITY, rows, len(jobs), failed, community=True)
        print(f"{len(jobs) - failed}/{len(jobs)} community maps, {total} retained in "
              f"{perf_counter() - start:.2f}s, {COMMUNITY.stat().st_size:,} bytes")
        print(f"  {COMMUNITY.relative_to(catalog.ROOT)}")
    return 0


def _rows(source: str | None) -> Iterable[dict]:
    shelves = ((COMMUNITY,) if source == "community" else
               (NAMED,) if source else (NAMED, COMMUNITY))
    for path in shelves:
        if path.exists():
            for row in json.loads(path.read_text("utf-8"))["records"]:
                if source is None or row["source"] == source:
                    yield row


def _tiles(row: dict) -> set[int]:
    floor = row["centre_floor"]
    return (set(row["family"]["picnums"]) | {s["picnum"] for s in row["centre_contents"]}
            | ({floor["floor_tile"]} if floor else set()))


def _words(text: str) -> list[str]:
    return WORD.findall(text.casefold())


def find(words: Iterable[str], *, kind: str | None = None,
         min_count: int = 0, source: str | None = None) -> list[dict]:
    """Find rows by kind, room and the catalogue vocabulary for their tiles."""
    wanted = [token for word in words for token in _words(word)]
    names, looks, labels = catalog.owner_names(), catalog.tile_looks(), catalog.place_labels()
    tile_text = {}
    for tile in set(names) | set(looks):
        reading = looks.get(tile, {})
        tile_text[tile] = _words(" ".join([names.get(tile, ""), reading.get("depicts", ""),
                                         reading.get("looks", ""), *reading.get("tags", [])]))
    matches = []
    for row in _rows(source):
        if (kind is not None and row["kind"] != kind) or row["count"] < min_count:
            continue
        tiles = _tiles(row)
        words_here = _words(" ".join((row["map"], row.get("place") or "", row.get("path", ""),
                                     row["kind"], row.get("form", ""),
                                     labels.get(row.get("place"), {}).get("kind")
                                     or row.get("room_kind") or "",
                                     "centre object" if row["centre_contents"] else "")))
        for layer in row.get("layers", ()):
            words_here.extend(_words(layer["kind"] + " " + layer.get("form", "")))
        # Exact picnum search and prefix matching for words such as candle /
        # candleholder. Fold regular plurals so "rings" also finds a ring.
        digits = {str(t) for t in tiles} | {w for w in words_here if w.isdecimal()}
        for tile in tiles:
            words_here.extend(tile_text.get(tile, ()))
        if all(token in digits if token.isdecimal() else
               any(here.startswith(token.rstrip("s")) for here in words_here) for token in wanted):
            matches.append(row)
    return sorted(matches, key=_rank)


def at_place(ref: str, *, shelf_rooms_only: bool = False) -> list[dict]:
    name, sep, sector_text = ref.rpartition(":")
    if not sep or not name or not sector_text.isdecimal():
        raise ValueError("expected MAP:sector")
    name, sector = name.casefold(), int(sector_text)
    found = []
    for row in _rows(None):
        if shelf_rooms_only and row["source"] == "community":
            continue
        if name not in (row["map"].casefold(), row.get("path", "").casefold()):
            continue
        if ((row.get("place") or "").casefold() == f"{name}:{sector}"
                or sector in (row["host_sector"], row["centre_sector"])
                or any(m["kind"] == "sector" and m["id"] == sector for m in row.get("members", ()))):
            found.append(row)
    return sorted(found, key=_rank)


def _tile_names(tiles: Iterable[int], names: dict[int, str]) -> str:
    for tile in tiles:
        if tile not in names:
            _source, names[tile] = catalog.tile_name(tile)
    return ", ".join(f"{tile} {names[tile]}" if names[tile] else str(tile) for tile in tiles)


def describe(row: dict, names: dict[int, str]) -> str:
    ref = f"{row.get('path', row['map'])}:{row['host_sector']}"
    shape = row.get("form", row["kind"])
    if row["kind"] == "group":
        shape += " (" + " + ".join(layer.get("form", layer["kind"]) for layer in row["layers"]) + ")"
    tiles = _tile_names(row["family"]["picnums"][:4], names)
    centre_tiles = list(dict.fromkeys(s["picnum"] for s in row["centre_contents"]))
    centre = _tile_names(centre_tiles[:4], names)
    missing = f", {row['missing']} missing" if row.get("missing") else ""
    place = f", room {row['place']}" if row.get("place") and row["place"] != ref else ""
    return (f"  {ref}  {shape}, {row['count']}{missing}, radius {row['radius_m']} m"
            + (f" | {tiles}" if tiles else "") + (f" | centre {centre}" if centre else "") + place)


def _detail(row: dict, names: dict[int, str]) -> Iterable[str]:
    yield describe(row, names)
    yield (f"    centre {row['centre']} z {row['z']}, sector {row['centre_sector']}, "
           f"regularity {row['regularity']}, score {row['score']}, {row['provenance']}")
    floor = row["centre_floor"]
    if floor:
        yield (f"    centre floor {_tile_names([floor['floor_tile']], names)}, "
               f"step {floor['floor_step']:+}, shade contrast {row['light_contrast']:+}, "
               f"type {floor['type']}" + (", sloped" if floor["sloped"] else ""))
    for level in row.get("levels", ()):
        yield (f"    level {level['sectors']}, {level['sides']} sides, radius {level['radius']}, "
               f"step {level['floor_step']:+}, floor {_tile_names([level['floor_tile']], names)}, "
               f"shade {level['floor_shade']}, type {level['type']}")
    if row.get("members"):
        yield "    members " + ", ".join(f"{m['kind']} {m['id']}" for m in row["members"])
    if row["wired"]:
        yield "    wiring " + ", ".join(f"{w.get('kind', '')} {w.get('id', '')} "
                                        f"TX {w['tx_id']} RX {w['rx_id']}" for w in row["wiring"])


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    mining = sub.add_parser("mine")
    mining.add_argument("--community", action="store_true")
    mining.add_argument("--serial", action="store_true")
    search = sub.add_parser("find")
    search.add_argument("words", nargs="*")
    search.add_argument("--kind", choices=KINDS)
    search.add_argument("--min-count", type=int, default=0)
    search.add_argument("--source", choices=SOURCES)
    search.add_argument("--limit", type=int)
    show = sub.add_parser("show")
    show.add_argument("place")
    args = parser.parse_args(argv)
    if args.command == "mine":
        try:
            return mine(community=args.community, serial=args.serial)
        except corpus.CorpusError as error:
            parser.exit(1, f"{error}\n")
    names: dict[int, str] = {}
    if args.command == "find":
        if args.source == "community" and not COMMUNITY.exists():
            parser.exit(1, "Community shelf is absent. Run python -m tools.mine_compositions mine --community\n")
        rows = find(args.words, kind=args.kind, min_count=args.min_count, source=args.source)
        for row in rows[:args.limit]:
            print(describe(row, names))
    else:
        try:
            rows = at_place(args.place)
        except ValueError as error:
            parser.error(str(error))
        for row in rows:
            print("\n".join(_detail(row, names)))
    if not rows:
        print("No compositions found")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
