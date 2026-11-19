"""The mapper's catalogues: what every tile looks like, what every place is.

The owner, 2026-11-18: "How could we improve search efficiency? ... you can
just look at pages with picnums and mark what looks interesting, then
search in which maps it is used, look how it looks and in which contexts
it is used, identify each of the context types, if it is hospital,
graveyard, sewers"; and: "every time you are searching for things you can
be catalogising everything, you can even run fleet of agents all around to
improve our catalogs".

Finding a thing was the slow part of every study: a "meat plant" that was
lettering on a wall, a "theatre" that was a carnival booth. Nothing said
what a tile shows or what a place is. Two catalogues do, and both are
filled by LOOKING -- by the mapper or by a fleet of agents -- and kept:

**Tiles** (``knowledge/blood/design/tile-looks/part-*.json``): what each
tile depicts, in a line, with tags. This is the mapper's reading of the
picture and is kept apart from the owner's names
(`owner-anchors-v1.json`), which outrank it. ``sheets`` draws the tiles in
pages for looking at; ``look`` records a reading; ``tiles TEXT`` searches
readings, tags and owner names.

**Places** (``knowledge/blood/design/places-v1.json`` and
``place-labels/*.json``): every room of the campaign and curated maps,
with the words its lettering sprites spell, its distinctive tiles (the
ones few other places have), what stands in it, and its size. ``places
TEXT`` searches the signs, the tiles' readings and the labels; ``label``
records what a place IS once somebody has looked at it.

**A library, not a pile of notes.** The owner again: "that catalog needs
to be coherent and usable ... rather than tons of texts, it needs to be a
real library you can use". So an entry is a few FIXED fields, every word
in them comes from `catalog-vocabulary.json` (a tile's class, layout and
themes; a place's kind), and `look` and `label` REFUSE a word that is not
there. One thing has one name; a search for "rail" finds every rail.
`knowledge/blood/LIBRARY.md` is the one page on how to use it.

.. code-block:: bash

    python -m tools.catalog find rail                 # everything about rails
    python -m tools.catalog show 1129                 # one tile, cross-linked
    python -m tools.catalog show E1M2:271             # one place
    python -m tools.catalog sheets                    # pages of tiles to read
    python -m tools.catalog look 1129 --class material --layout band \
        --depicts "railway track with sleepers" --themes rail,floor --part mine
    python -m tools.catalog label E1M2:271 --kind station --note "waiting hall" --part mine
    python -m tools.catalog build-places
    python -m tools.catalog status
"""

from __future__ import annotations

import argparse
import json
import math
import pathlib
import re
import sys
from collections import Counter

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

DESIGN = ROOT / "knowledge" / "blood" / "design"
LOOKS = DESIGN / "tile-looks"
LABELS = DESIGN / "place-labels"
PLACES = DESIGN / "places-v1.json"
USAGE = DESIGN / "tile-usage-v1.json"
SHEETS = ROOT / "reports" / "tiles" / "sheets"
PER_PAGE, COLUMNS, CELL = 40, 8, 136


def tile_looks() -> dict[int, dict]:
    out: dict[int, dict] = {}
    if LOOKS.exists():
        for path in sorted(LOOKS.glob("part-*.json")):
            for key, row in json.loads(path.read_text("utf-8")).items():
                out[int(key)] = row
    return out


def owner_names() -> dict[int, str]:
    data = json.loads((DESIGN / "owner-anchors-v1.json").read_text("utf-8"))
    return {int(a["picnum"]): a.get("label_en", "") for a in data["anchors"]}


def used_tiles() -> list[int]:
    return sorted(int(k) for k in json.loads(USAGE.read_text("utf-8"))["tiles"])


def sheets() -> list[pathlib.Path]:
    """Every tile Blood's maps use, forty to a page, numbered."""
    from PIL import Image, ImageDraw
    from bloodmap.art import read_art_directory, read_palette, tile_to_rgb
    from tools.tile_usage import ART_DIR, PALETTE

    tiles = read_art_directory(ART_DIR)
    palette = read_palette(PALETTE)
    wanted = [t for t in used_tiles() if t in tiles and tiles[t].width
              and tiles[t].height]
    SHEETS.mkdir(parents=True, exist_ok=True)
    pages = []
    for page, start in enumerate(range(0, len(wanted), PER_PAGE)):
        rows = math.ceil(PER_PAGE / COLUMNS)
        sheet = Image.new("RGB", (COLUMNS * CELL, rows * (CELL + 18)),
                          (40, 40, 40))
        draw = ImageDraw.Draw(sheet)
        for index, tile in enumerate(wanted[start:start + PER_PAGE]):
            art = tiles[tile]
            rgb = bytearray(tile_to_rgb(art, palette))
            for x in range(art.width):
                for y in range(art.height):
                    if art.pixels[x * art.height + y] == 255:
                        k = (y * art.width + x) * 3
                        rgb[k:k + 3] = bytes((255, 0, 255))
            picture = Image.frombytes("RGB", (art.width, art.height),
                                      bytes(rgb))
            scale = min((CELL - 8) / art.width, (CELL - 8) / art.height)
            size = (max(1, int(art.width * scale)),
                    max(1, int(art.height * scale)))
            picture = picture.resize(size, Image.Resampling.NEAREST)
            cx = (index % COLUMNS) * CELL
            cy = (index // COLUMNS) * (CELL + 18)
            sheet.paste(picture, (cx + 4, cy + 4))
            draw.text((cx + 4, cy + CELL), f"{tile}  {art.width}x{art.height}",
                      fill=(255, 255, 0))
        path = SHEETS / f"page-{page:02d}.png"
        sheet.save(path)
        pages.append(path)
    (SHEETS / "index.json").write_text(json.dumps(
        {f"page-{p:02d}": wanted[s:s + PER_PAGE]
         for p, s in enumerate(range(0, len(wanted), PER_PAGE))}), "utf-8")
    return pages


class CatalogError(ValueError):
    """An entry the library refuses, naming the word it does not know."""


def vocabulary() -> dict:
    return json.loads((DESIGN / "catalog-vocabulary.json").read_text("utf-8"))


def record_look(tile: int, klass: str, layout: str, depicts: str,
                themes: list[str], part: str, runs: str = "") -> None:
    """One reading of one tile, in the library's own words.

    `runs` is for a tile with a DIRECTION -- rails, planks, a conveyor's
    slats: the tile axis ("x" or "y") its lines continue along. The
    owner, 2026-11-18: "rails are going 90 degrees from train than they
    should really go". `directional_floor_faults` holds a floor to it.
    """
    vocab = vocabulary()
    if runs not in ("", "x", "y"):
        raise CatalogError("runs is x or y: the tile axis its lines follow")
    if klass not in vocab["tile_class"]:
        raise CatalogError(f"class {klass!r} is not one of "
                           f"{', '.join(vocab['tile_class'])}")
    if layout not in vocab["tile_layout"]:
        raise CatalogError(f"layout {layout!r} is not one of "
                           f"{', '.join(vocab['tile_layout'])}")
    unknown = [t for t in themes if t not in vocab["themes"]]
    if unknown:
        raise CatalogError(f"themes {unknown} are not in the vocabulary")
    if len(depicts.split()) > 10:
        raise CatalogError("`depicts` is a name, ten words at most")
    LOOKS.mkdir(parents=True, exist_ok=True)
    path = LOOKS / f"part-{part}.json"
    data = json.loads(path.read_text("utf-8")) if path.exists() else {}
    data[str(tile)] = {"class": klass, "layout": layout, "looks": depicts,
                       "tags": sorted(set(themes)), "by": part}
    if runs:
        data[str(tile)]["runs"] = runs
    path.write_text(json.dumps(data, indent=1), "utf-8")


def find_tiles(words: list[str]) -> list[tuple[int, str]]:
    looks, names = tile_looks(), owner_names()
    out = []
    for tile in sorted(set(looks) | set(names)):
        row = looks.get(tile, {})
        text = " ".join([names.get(tile, ""), row.get("looks", ""),
                         row.get("class", ""),
                         " ".join(row.get("tags", []))]).lower()
        if all(word.lower() in text for word in words):
            said = (f"owner: {names[tile]}" if tile in names else "") + (
                f"  looks: {row['looks']}" if row else "")
            out.append((tile, said.strip()))
    return out


# ---------------------------------------------------------------------------
# places
# ---------------------------------------------------------------------------
def build_places() -> dict:
    from bloodmap.blood_types import SPRITE_TYPES
    from bloodmap.format import read_map
    from bloodmap.lettering import read_sign
    from bloodmap.patterns import list_corpus_maps
    from tools import place_character as pc

    rows = []
    for population in ("blood-campaign", "community-curated"):
        for item in list_corpus_maps(population=population):
            try:
                disk = read_map(item.path)
            except Exception:                               # noqa: BLE001
                continue
            geom = pc.Geometry(disk)
            try:
                signs = read_sign(disk)
            except Exception:                               # noqa: BLE001
                signs = []
            words_in: dict[int, list[str]] = {}
            for word, ids in signs:
                if len(word) >= 3 and ids:
                    sector = int(disk.sprites[ids[0]].fields["sector"])
                    words_in.setdefault(sector, []).append(word)
            for place in pc.places(geom):
                profile = pc.profile(geom, place)
                if profile["solid_wall"] < 4096:
                    continue
                tiles = ({t for t, _s in profile["wall_tiles"]}
                         | {profile["floor_tile"], profile["ceiling_tile"]})
                things = Counter()
                kinds = Counter()
                for sector in place:
                    s = geom.sectors[sector]
                    if sector != profile["host"]:
                        tiles.add(int(s["floor_picnum"]))
                    for sprite in geom.by_sector.get(sector, ()):
                        if int(sprite["cstat"]) & 32768:
                            continue
                        things[int(sprite["picnum"])] += 1
                        kind = int(sprite.get("type", 0))
                        if kind:
                            kinds[(SPRITE_TYPES.get(kind) or {}).get(
                                "name", str(kind))] += 1
                rows.append({
                    "id": f"{item.path.stem.upper()}:{profile['host']}",
                    "map": item.path.stem.upper(),
                    "host": profile["host"], "sky": profile["sky"],
                    "metres": profile["metres"],
                    "sectors": profile["sectors"],
                    "signs": sorted({w for s in place
                                     for w in words_in.get(s, ())}),
                    "tiles": sorted(tiles),
                    "sprites": dict(things.most_common(24)),
                    "types": dict(kinds.most_common(10)),
                    "moves": sorted({int(geom.sectors[s]["type"])
                                     for s in place
                                     if int(geom.sectors[s]["type"])}),
                    "layers": profile["layer_count"]})
    #: a tile is distinctive of a place when few places have it
    seen = Counter()
    for row in rows:
        for tile in set(row["tiles"]) | {int(t) for t in row["sprites"]}:
            seen[tile] += 1
    for row in rows:
        every = set(row["tiles"]) | {int(t) for t in row["sprites"]}
        row["distinctive"] = sorted(every, key=lambda t: seen[t])[:10]
    data = {"$schema": "llmapper.places", "places": rows,
            "tile_places": {str(t): n for t, n in seen.items()}}
    PLACES.write_text(json.dumps(data), "utf-8")
    return data


def place_labels() -> dict[str, dict]:
    out: dict[str, dict] = {}
    if LABELS.exists():
        for path in sorted(LABELS.glob("part-*.json")):
            out.update(json.loads(path.read_text("utf-8")))
    return out


def record_label(place_id: str, kind: str, note: str, part: str,
                 scale: str = "place", confidence: str = "seen") -> None:
    """What something IS, at one of four scales.

    The owner, 2026-11-18: "annotations for the maps like these are
    hospitals, these are hospital beds and graveyard, parts of graveyard,
    like in different scales of magnitude". A map, a venue in it, a room,
    a thing in the room: each gets a kind from the vocabulary, and each
    says how it is known -- seen, inferred, or only guessed.
    """
    vocab = vocabulary()
    if scale not in vocab["scale"]:
        raise CatalogError(f"scale {scale!r} is not one of {list(vocab['scale'])}")
    if confidence not in vocab["confidence"]:
        raise CatalogError(f"confidence {confidence!r} is not one of "
                           f"{list(vocab['confidence'])}")
    kinds = vocab["thing_kind"] if scale == "thing" else vocab["place_kind"]
    if kind not in kinds:
        raise CatalogError(f"kind {kind!r} is not in the vocabulary for a "
                           f"{scale}")
    if len(note.split()) > 14:
        raise CatalogError("a label's note is fourteen words at most")
    LABELS.mkdir(parents=True, exist_ok=True)
    path = LABELS / f"part-{part}.json"
    data = json.loads(path.read_text("utf-8")) if path.exists() else {}
    key = place_id.upper() if scale != "thing" else f"{place_id.upper()}#thing"
    data[key] = {"kind": kind, "note": note, "by": part, "scale": scale,
                 "confidence": confidence}
    path.write_text(json.dumps(data, indent=1), "utf-8")


def directional_floor_faults(disk) -> list[dict]:
    """Floors whose tile has a direction that runs ACROSS a long sector.

    A floor texture's x lies along the world's x unless `floor_stat` bit 4
    swaps them. For a tile the library says `runs` along one of its axes,
    a sector at least twice as long as wide should run the same way.
    """
    looks = tile_looks()
    out = []
    for index, sector in enumerate(disk.sectors):
        s = sector.fields
        runs = looks.get(int(s["floor_picnum"]), {}).get("runs")
        if not runs or int(s["floor_stat"]) & 64:      # relative: skip
            continue
        xs, ys = [], []
        for w in range(int(s["wall_ptr"]),
                       int(s["wall_ptr"]) + int(s["wall_count"])):
            xs.append(int(disk.walls[w].fields["x"]))
            ys.append(int(disk.walls[w].fields["y"]))
        span_x, span_y = max(xs) - min(xs), max(ys) - min(ys)
        #: a clear long axis, and wide enough to be the thing itself: a
        #: track cut into slivers across its width (E1M2 s265) or a short
        #: piece of one (4,096 of an 8,192-wide bed) says nothing
        if (max(span_x, span_y) < 2.5 * min(span_x, span_y)
                or min(span_x, span_y) < 2048):
            continue
        long_axis = "x" if span_x > span_y else "y"
        world = runs if not int(s["floor_stat"]) & 4 else (
            "y" if runs == "x" else "x")
        if world != long_axis:
            out.append({"sector": index, "tile": int(s["floor_picnum"]),
                        "runs_along": world, "sector_runs": long_axis,
                        "size": [span_x, span_y]})
    return out


#: a theme a place's rare tiles carry -> the kind of place it suggests
THEME_KIND = {
    "medical": "hospital", "morgue": "morgue", "rail": "station",
    "church": "church", "crypt": "crypt", "graveyard": "graveyard",
    "funeral": "morgue", "bar": "bar", "kitchen": "kitchen", "shop": "shop",
    "bank": "bank", "theatre": "theatre", "carnival": "carnival",
    "school": "school", "library": "library", "prison": "prison",
    "sewer": "sewer", "nautical": "harbour", "industrial": "factory",
    "mine": "mine", "cave": "cave", "snow": "snowfield", "hotel": "hotel-lobby",
    "office": "office", "meat": "factory", "forest": "forest",
    "garden": "garden"}


def guess_places() -> dict:
    """The catalogue's own hypotheses: what each place might be.

    From the themes of the tiles a place wears, weighted so that a tile
    few places have counts for more, plus any lettering. A guess is filed
    as `guessed` and names its evidence; it is a place to LOOK, not a fact.
    It never replaces a label somebody recorded by looking.
    """
    data = json.loads(PLACES.read_text("utf-8"))
    looks = tile_looks()
    rarity = {int(t): n for t, n in data["tile_places"].items()}
    kinds = set(vocabulary()["place_kind"])
    out = {}
    for row in data["places"]:
        votes: Counter = Counter()
        evidence: dict[str, list[int]] = {}
        for tile in set(row["tiles"]) | {int(t) for t in row["sprites"]}:
            for theme in looks.get(tile, {}).get("tags", ()):
                kind = THEME_KIND.get(theme)
                if kind:
                    votes[kind] += 1.0 / math.sqrt(rarity.get(tile, 1))
                    evidence.setdefault(kind, []).append(tile)
        for sign in row["signs"]:
            word = sign.lower()
            for kind in kinds:
                if kind.replace("-", " ") in word:
                    votes[kind] += 3
        if not votes:
            continue
        (kind, score), *rest = votes.most_common(2)
        if score < 0.5 or (rest and rest[0][1] > 0.7 * score):
            continue                      # too weak, or two kinds tie
        tiles = sorted(set(evidence.get(kind, [])),
                       key=lambda t: rarity.get(t, 1))[:4]
        out[row["id"]] = {"kind": kind, "by": "guess", "scale": "place",
                          "confidence": "guessed",
                          "note": "tiles " + " ".join(str(t) for t in tiles)}
    LABELS.mkdir(parents=True, exist_ok=True)
    #: part-0guess sorts first, so any label recorded by a reader overrides
    (LABELS / "part-0guess.json").write_text(json.dumps(out, indent=1), "utf-8")
    return out


def mechanisms(name: str, only: set[int] | None = None) -> list[dict]:
    """Every wired chain of one map: who sends, on what, to whom.

    The owner: "We also should be understanding mechanisms, some levels
    have pretty complex chains of them." A chain starts at a thing a
    player can cause (pushed, shot, entered, picked up, killed, or the
    level starting) and follows each channel to its receivers, and on
    through any receiver that sends in turn.
    """
    from bloodmap.blood_types import (RESERVED_CHANNELS, SECTOR_TYPES,
                                      SPRITE_TYPES, WALL_TYPES)
    from bloodmap.format import read_map
    from bloodmap.patterns import corpus_map_path

    path = (pathlib.Path(name) if name.upper().endswith(".MAP")
            else corpus_map_path(name))
    disk = read_map(path)
    nodes = []
    for kind, group, table in (("sprite", disk.sprites, SPRITE_TYPES),
                               ("sector", disk.sectors, SECTOR_TYPES),
                               ("wall", disk.walls, WALL_TYPES)):
        for index, item in enumerate(group):
            x = getattr(getattr(item, "extra", None), "fields", None) or {}
            tx, rx = int(x.get("tx_id", 0) or 0), int(x.get("rx_id", 0) or 0)
            if not tx and not rx:
                continue
            f = item.fields
            what = int(f.get("type", 0))
            causes = [c for c in ("push", "vector", "impact", "pickup",
                                  "touch", "sight", "proximity", "enter",
                                  "exit", "wall_push")
                      if int(x.get(f"trigger_{c}", 0) or 0)]
            sector = int(f["sector"]) if kind == "sprite" else (
                index if kind == "sector" else -1)
            nodes.append({
                "id": f"{kind} {index}", "kind": kind, "index": index,
                "type": what,
                "type_name": (table.get(what) or {}).get("name", str(what)),
                "tile": int(f.get("picnum", f.get("floor_picnum", 0))),
                "tx": tx, "rx": rx, "command": int(x.get("command", 0) or 0),
                "causes": causes, "sector": sector,
                "once": bool(int(x.get("trigger_once", 0) or 0)),
                "wait": int(x.get("wait_time", x.get("wait_time_a", 0)) or 0),
                "key": int(x.get("key", 0) or 0)})
    listeners: dict[int, list[dict]] = {}
    for node in nodes:
        if node["rx"]:
            listeners.setdefault(node["rx"], []).append(node)
    reserved = {int(k): v for k, v in RESERVED_CHANNELS.items()} \
        if isinstance(RESERVED_CHANNELS, dict) else {}
    chains = []
    for node in nodes:
        #: a root: it sends, and something a player does (or a reserved
        #: channel such as the level's start) sets it off
        starts = node["causes"] or (node["rx"] in reserved)
        if not node["tx"] or not starts:
            continue
        if only is not None and node["sector"] not in only:
            continue
        steps, seen, frontier, depth = [], {node["id"]}, [node], 0
        while frontier and depth < 8:
            nxt = []
            for sender in frontier:
                for receiver in listeners.get(sender["tx"], ()):
                    steps.append({"from": sender["id"], "channel": sender["tx"],
                                  "command": sender["command"],
                                  "to": receiver["id"],
                                  "to_type": receiver["type_name"],
                                  "wait": receiver["wait"]})
                    if receiver["id"] not in seen and receiver["tx"]:
                        seen.add(receiver["id"])
                        nxt.append(receiver)
            frontier, depth = nxt, depth + 1
        chains.append({
            "root": node["id"], "root_type": node["type_name"],
            "tile": node["tile"], "sector": node["sector"],
            "cause": node["causes"] or [f"channel {node['rx']} "
                                        f"({reserved.get(node['rx'], '')})"],
            "key": node["key"], "once": node["once"],
            "steps": steps, "depth": depth,
            "receivers": dict(Counter(s["to_type"] for s in steps))})
    chains.sort(key=lambda c: (-c["depth"], -len(c["steps"])))
    return chains


def find_places(words: list[str], tile: int | None = None,
                limit: int = 25) -> list[tuple[float, dict, list[str]]]:
    data = json.loads(PLACES.read_text("utf-8"))
    looks, names, labels = tile_looks(), owner_names(), place_labels()
    rarity = {int(t): n for t, n in data["tile_places"].items()}
    hits = []
    for row in data["places"]:
        every = set(row["tiles"]) | {int(t) for t in row["sprites"]}
        if tile is not None and tile not in every:
            continue
        why, score = [], 0.0
        label = labels.get(row["id"], {})
        for word in words:
            w = word.lower()
            found = False
            if any(w in sign.lower() for sign in row["signs"]):
                why.append(f"sign {[s for s in row['signs'] if w in s.lower()]}")
                score += 5
                found = True
            if w in (label.get("kind", "") + " " + label.get("note", "")).lower():
                why.append(f"labelled {label['kind']!r}")
                score += 6
                found = True
            for t in every:
                text = (names.get(t, "") + " " + looks.get(t, {}).get(
                    "looks", "") + " " + " ".join(
                        looks.get(t, {}).get("tags", []))).lower()
                if re.search(rf"\b{re.escape(w)}", text):
                    #: a rare tile says more about a place than a common one
                    score += 2.0 / math.sqrt(rarity.get(t, 1))
                    if len(why) < 6:
                        why.append(f"tile {t} ({(names.get(t) or looks.get(t, {}).get('looks', ''))[:30]})")
                    found = True
            if not found:
                score = -1
                break
        if (score > 0 and why) or (tile is not None and not words):
            hits.append((score, row, why))
    hits.sort(key=lambda h: -h[0])
    return hits[:limit]


def show(what: str) -> str:
    """One entry, with everything the library links to it."""
    lines = []
    if what.isdigit():
        tile = int(what)
        looks, names = tile_looks().get(tile), owner_names().get(tile)
        usage = json.loads(USAGE.read_text("utf-8"))["tiles"].get(str(tile))
        lines.append(f"TILE {tile}")
        lines.append(f"  owner: {names or '(not named)'}")
        if looks:
            lines.append(f"  reading: {looks.get('class', '?')} / "
                         f"{looks.get('layout', '?')}: {looks['looks']} "
                         f"{looks['tags']} (by {looks['by']})")
        else:
            lines.append("  reading: (nobody has looked yet)")
        if usage:
            lines.append("  used as: " + ", ".join(
                f"{role} x{row['count']} in {row['maps']} maps"
                for role, row in usage["roles"].items()))
        lines.append(f"  picture: python -m tools.tile_usage {tile}")
        if PLACES.exists():
            hits = find_places([], tile, 8)
            labels = place_labels()
            lines.append("  in places: " + ", ".join(
                row["id"] + (f" [{labels[row['id']]['kind']}]"
                             if row["id"] in labels else "")
                for _s, row, _w in hits))
    else:
        data = json.loads(PLACES.read_text("utf-8"))
        row = next((r for r in data["places"] if r["id"] == what.upper()), None)
        if row is None:
            return f"no place {what} in the catalogue"
        label = place_labels().get(row["id"])
        looks, names = tile_looks(), owner_names()
        lines.append(f"PLACE {row['id']}  {'outdoor' if row['sky'] else 'indoor'}  "
                     f"{row['metres'][0]} x {row['metres'][1]} m, "
                     f"{row['metres'][2]} m high, {row['sectors']} sectors")
        lines.append(f"  kind: {label['kind'] + ' -- ' + label['note'] if label else '(not labelled)'}")
        lines.append(f"  signs: {row['signs'] or '-'}")
        lines.append("  distinctive tiles: " + "; ".join(
            f"{t} {(names.get(t) or looks.get(t, {}).get('looks') or '?')[:28]}"
            for t in row["distinctive"]))
        lines.append(f"  sprite types: {row['types']}")
        lines.append(f"  moving sector types: {row['moves']}")
        lines.append(f"  look at it: python -m tools.study <slug> --seed {row['map']}:{row['host']}!")
    return "\n".join(lines)


def find_all(words: list[str]) -> str:
    """Tiles, places, studies and idea cards that answer to the words."""
    out = ["TILES"]
    for tile, said in find_tiles(words)[:20]:
        out.append(f"  {tile:>5}  {said}")
    out.append("PLACES")
    if PLACES.exists():
        labels = place_labels()
        for _score, row, why in find_places(words, None, 12):
            label = labels.get(row["id"], {})
            out.append(f"  {row['id']:<14}"
                       f"{('[' + label['kind'] + '] ') if label else ''}"
                       f"{row['metres'][0]}x{row['metres'][1]} m  "
                       + "; ".join(why[:3]))
    studies = ROOT / "knowledge" / "blood" / "studies"
    out.append("STUDIES")
    for notes in sorted(studies.glob("*/notes.md")):
        text = notes.read_text("utf-8").lower()
        if all(re.search(rf"\b{re.escape(w.lower())}\b", text) for w in words):
            out.append(f"  {notes.parent.name}  ({notes})")
    out.append("IDEAS")
    cards = ROOT / "knowledge" / "blood" / "ideas" / "cards"
    for path in sorted(cards.glob("*.json")):
        card = json.loads(path.read_text("utf-8"))
        text = " ".join(str(card[k]) for k in ("title", "what", "recipe",
                                               "use")).lower()
        if all(re.search(rf"\b{re.escape(w.lower())}\b", text) for w in words):
            out.append(f"  {path.stem}: [{card['kind']}] {card['title']}")
    return "\n".join(out)


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("sheets")
    look = sub.add_parser("look")
    look.add_argument("tile", type=int)
    look.add_argument("--class", dest="klass", required=True)
    look.add_argument("--layout", required=True)
    look.add_argument("--depicts", required=True)
    look.add_argument("--themes", default="")
    look.add_argument("--part", required=True)
    look.add_argument("--runs", default="")
    batch = sub.add_parser("look-batch")
    batch.add_argument("file")
    batch.add_argument("--part", required=True)
    find = sub.add_parser("find")
    find.add_argument("words", nargs="+")
    show_ = sub.add_parser("show")
    show_.add_argument("what")
    vocab = sub.add_parser("vocab")
    vocab.add_argument("action", choices=("list", "add"))
    vocab.add_argument("--list", dest="which",
                       choices=("themes", "place_kind"))
    vocab.add_argument("--word")
    tiles = sub.add_parser("tiles")
    tiles.add_argument("words", nargs="+")
    sub.add_parser("build-places")
    places = sub.add_parser("places")
    places.add_argument("words", nargs="*")
    places.add_argument("--tile", type=int)
    places.add_argument("--limit", type=int, default=25)
    label = sub.add_parser("label")
    label.add_argument("place")
    label.add_argument("--kind", required=True)
    label.add_argument("--note", default="")
    label.add_argument("--part", required=True)
    label.add_argument("--scale", default="place")
    label.add_argument("--confidence", default="seen")
    sub.add_parser("guess")
    mech = sub.add_parser("mechanisms")
    mech.add_argument("map")
    mech.add_argument("--place", help="MAP:sector, to keep to one place")
    mech.add_argument("--limit", type=int, default=12)
    sub.add_parser("status")
    args = parser.parse_args(argv)
    if args.command == "sheets":
        pages = sheets()
        print(f"{len(pages)} pages -> {SHEETS}")
    elif args.command == "look":
        try:
            record_look(args.tile, args.klass, args.layout, args.depicts,
                        [t for t in re.split(r"[,\s]+", args.themes) if t],
                        args.part, args.runs)
        except CatalogError as error:
            print(f"refused: {error}")
            return 2
    elif args.command == "look-batch":
        #: a JSON list of {"tile", "class", "layout", "depicts", "themes"}
        rows = json.loads(pathlib.Path(args.file).read_text("utf-8"))
        done, refused = 0, []
        for row in rows:
            try:
                record_look(int(row["tile"]), row["class"], row["layout"],
                            row["depicts"], list(row.get("themes", [])),
                            args.part)
                done += 1
            except (CatalogError, KeyError) as error:
                refused.append(f"tile {row.get('tile')}: {error}")
        print(f"recorded {done}, refused {len(refused)}")
        for line in refused:
            print("  " + line)
        return 2 if refused else 0
    elif args.command == "find":
        print(find_all(args.words))
    elif args.command == "show":
        print(show(args.what))
    elif args.command == "vocab":
        path = DESIGN / "catalog-vocabulary.json"
        data = vocabulary()
        if args.action == "list":
            for key in ("tile_class", "tile_layout", "themes", "place_kind"):
                print(key + ": " + ", ".join(data[key]))
        else:
            if args.word not in data[args.which]:
                data[args.which].append(args.word)
                path.write_text(json.dumps(data, indent=1), "utf-8")
            print(f"{args.which}: {args.word}")
    elif args.command == "tiles":
        for tile, said in find_tiles(args.words):
            print(f"{tile:>5}  {said}")
    elif args.command == "build-places":
        data = build_places()
        print(f"{len(data['places'])} places -> {PLACES}")
    elif args.command == "places":
        labels = place_labels()
        for score, row, why in find_places(args.words, args.tile, args.limit):
            label = labels.get(row["id"], {})
            print(f"{row['id']:<14} {'outdoor' if row['sky'] else 'indoor':<8}"
                  f"{row['metres'][0]}x{row['metres'][1]} m  "
                  f"{('[' + label['kind'] + '] ') if label else ''}"
                  f"signs {row['signs'][:5]}\n      {'; '.join(why)}")
    elif args.command == "label":
        try:
            record_label(args.place, args.kind, args.note, args.part,
                         args.scale, args.confidence)
        except CatalogError as error:
            print(f"refused: {error}")
            return 2
    elif args.command == "guess":
        made = guess_places()
        print(f"{len(made)} places guessed -> {LABELS / 'part-0guess.json'}")
        for kind, n in Counter(r["kind"] for r in made.values()).most_common():
            print(f"  {kind:<14}{n}")
    elif args.command == "mechanisms":
        only = None
        if args.place:
            from bloodmap.format import read_map
            from bloodmap.patterns import corpus_map_path
            from tools import place_character as pc
            geom = pc.Geometry(read_map(corpus_map_path(args.map)))
            only = pc.place_of(geom, int(args.place.split(":")[1]))
        chains = mechanisms(args.map, only)
        print(f"{len(chains)} chains a player can set off")
        for chain in chains[:args.limit]:
            print(f"{chain['root']} ({chain['root_type']}, tile "
                  f"{chain['tile']}, sector {chain['sector']}) by "
                  f"{'/'.join(chain['cause'])}"
                  f"{' key ' + str(chain['key']) if chain['key'] else ''}"
                  f"{' once' if chain['once'] else ''}: {chain['depth']} "
                  f"hop(s) -> {chain['receivers']}")
            for step in chain["steps"][:10]:
                print(f"     {step['from']} --ch {step['channel']} cmd "
                      f"{step['command']}--> {step['to']} ({step['to_type']})"
                      f"{' after ' + str(step['wait']) if step['wait'] else ''}")
    elif args.command == "status":
        used, looks = used_tiles(), tile_looks()
        names = owner_names()
        print(f"tiles in use: {len(used)}; owner-named {sum(1 for t in used if t in names)}; "
              f"read by the mapper {sum(1 for t in used if t in looks)}; "
              f"neither {sum(1 for t in used if t not in names and t not in looks)}")
        if PLACES.exists():
            data = json.loads(PLACES.read_text("utf-8"))
            labels = place_labels()
            signed = sum(1 for r in data["places"] if r["signs"])
            by = Counter(labels[r["id"]].get("confidence", "seen")
                         for r in data["places"] if r["id"] in labels)
            print(f"places: {len(data['places'])}; with lettering {signed}; "
                  f"labelled {dict(by)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
