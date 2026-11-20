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
MECHANISMS = DESIGN / "mechanism-examples-v1.json"
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


def tile_name(tile: int) -> tuple[str, str]:
    """What a tile is, and whose word that is: ("owner", ...) outranks ("looks", ...)."""
    owner = owner_names().get(int(tile))
    if owner:
        return "owner", owner
    row = tile_looks().get(int(tile), {})
    return "looks", str(row.get("depicts") or row.get("looks") or "")


def tile_is(tile: int, *words: str) -> bool:
    """Whether the tile's name says it is one of `words` (the owner's name
    when there is one, the library's reading otherwise).

    The guard against choosing a tile by what it was called in code: the
    city stocked a grocer's window with tile 2937 as "a roast" (the owner's
    "dead cultist"), and shelved its market hall with 202 (the owner's
    "worn wall/facade texture").
    """
    _source, name = tile_name(tile)
    name = name.lower()
    return any(word.lower() in name for word in words)


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
    from bloodmap import examples
    from bloodmap.blood_types import SPRITE_TYPES
    from bloodmap.format import read_map
    from bloodmap.lettering import read_sign
    from bloodmap.corpus import list_corpus_maps
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
            first = len(rows)
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
                    "layers": profile["layer_count"],
                    #: which sectors the place is, so any shelf can ask
                    #: "which room is this sector in" without the geometry
                    "members": sorted(place)})
            #: what each place holds, under the mechanisms shelf's own keys
            #: (`sector:614`, `effect:conveyor`, `sprite:20`, `channel:4`)
            held = examples.by_place(
                examples.observe(item.path.stem.upper(), disk),
                {sector: row["id"] for row in rows[first:]
                 for sector in row["members"]})
            for row in rows[first:]:
                row["mechanisms"] = held.get(row["id"], {})
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


def sector_places(data: dict | None = None) -> dict[str, dict[int, str]]:
    """Map name to sector to the id of the catalogued place that sector is in."""
    if data is None:
        data = json.loads(PLACES.read_text("utf-8"))
    out: dict[str, dict[int, str]] = {}
    for row in data["places"]:
        where = out.setdefault(row["map"], {})
        for sector in row["members"]:
            where[sector] = row["id"]
    return out


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
    through any receiver that sends in turn. The reading is
    `bloodmap.wiring.chains`; this finds the map.
    """
    from bloodmap import wiring
    from bloodmap.format import read_map
    from bloodmap.corpus import corpus_map_path
    from bloodmap.reachability import sector_kinds

    path = (pathlib.Path(name) if name.upper().endswith(".MAP")
            else corpus_map_path(name))
    disk = read_map(path)
    return wiring.chains(disk, only, reach=sector_kinds(disk))


def find_places(words: list[str], tile: int | None = None,
                limit: int = 25) -> list[tuple[float, dict, list[str]]]:
    data = json.loads(PLACES.read_text("utf-8"))
    looks, names, labels = tile_looks(), owner_names(), place_labels()
    rarity = {int(t): n for t, n in data["tile_places"].items()}
    #: a word that names a mechanism finds the rooms holding one
    index = mechanism_index() if words else None
    holds: dict[str, list[tuple[str, dict]]] = {}
    if index is not None:
        from bloodmap import examples

        for word in words:
            answers = [(key, entry) for key, entry in index["entries"].items()
                       if entry["kind"] != "lesson"
                       and examples.search({"entries": {key: entry}}, [word])]
            holds[word.lower()] = answers
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
            held = row.get("mechanisms", {})
            for key, entry in holds.get(w, ()):
                if key in held:
                    #: a mechanism few rooms hold says more than a common one
                    score += (4.0 / math.sqrt(entry.get("place_count") or 1)
                              + math.log2(1 + held[key]))
                    if len(why) < 6:
                        why.append(f"holds {key} x{held[key]}")
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


def build_mechanisms() -> dict:
    """Every type, sector effect, reserved channel and lesson, with examples.

    The shelf an agent asks "which levels have one of these". The reading is
    `bloodmap.examples`; this is its run over the campaign, joined to the
    mechanism curriculum and to the library code that cites each lesson.
    """
    from bloodmap import examples
    from bloodmap.corpus import campaign_maps, corpus_root, list_corpus_maps
    from bloodmap.curriculum import mine_course
    from bloodmap.format import read_map

    seen = [examples.observe(path.stem.upper(), read_map(path))
            for path in campaign_maps(required=True)]
    document = examples.build(
        seen, curriculum={"maps": mine_course(corpus_root() / "mechanism")},
        cited=examples.cited_lessons(ROOT / "bloodmap"),
        #: after `build-places`: without it no example knows its room
        places=sector_places() if PLACES.exists() else None)
    files = {item.path.stem.upper(): item.relative
             for item in list_corpus_maps(population="mechanism-tutorial",
                                          attach_tiers=False)}
    for entry in document["entries"].values():
        if entry["kind"] == "lesson":
            entry["file"] = files.get(entry["name"].upper())
    MECHANISMS.write_text(json.dumps(document, indent=1) + "\n",
                          encoding="utf-8", newline="\n")
    return document


def mechanism_index() -> dict | None:
    if not MECHANISMS.exists():
        return None
    return json.loads(MECHANISMS.read_text("utf-8"))


def _example(entry: dict, item: dict) -> str:
    kind = entry["kind"].split()[0]
    if kind in ("sprite", "wall"):
        return f"{item['map']} {kind} {item['id']} (sector {item['sector']})"
    if kind == "channel" and item["id"] != item["sector"]:
        return f"{item['map']}:{item['sector']} (object {item['id']})"
    return f"{item['map']}:{item['sector']}"


def show_mechanism(key: str, entry: dict) -> str:
    """One mechanism entry as a dozen lines, ending in what to run next."""
    _kind, _colon, ident = key.partition(":")
    lines = []
    if entry["kind"] == "lesson":
        size = entry["size"]
        lines.append(f"LESSON {entry['name']}  tutorial tier {entry['tier']}, "
                     f"{size['sectors']} sectors, {size['sprites']} sprites")
        lines.append(f"  shows: {entry['says']}")
        if entry["types"]:
            lines.append("  uses: " + ", ".join(entry["types"]))
        if entry["slots"]:
            lines.append("  sector resources spent: " + ", ".join(entry["slots"]))
        if entry["cited_by"]:
            lines.append("  cited by: " + ", ".join(entry["cited_by"]))
        if entry.get("file"):
            where = f"maps/blood/{entry['file']}"
            if entry.get("sectors"):
                lines.append(f"  its parts are sectors {entry['sectors']}: "
                             f"python -m tools.catalog record {where} sector "
                             f"{entry['sectors'][0]}")
            lines.append(f"  its wiring: python -m tools.catalog mechanisms {where}")
        else:
            lines.append("  file: not in the local corpus")
        return "\n".join(lines)
    head = {"effect": f"EFFECT {entry['name']}",
            "channel": f"CHANNEL {ident}  {entry['name']}"}.get(
                entry["kind"],
                f"{entry['kind'].upper()} {ident}  {entry['name']}"
                + (f"  [{entry['category']}]" if entry.get("category") else ""))
    lines.append(head)
    if entry.get("says"):
        lines.append(f"  is: {entry['says']}")
    if entry.get("fields"):
        lines.append("  defined by XSECTOR: " + "; ".join(
            f"{rule} of {', '.join(names)}" for rule, names in entry["fields"].items()))
    lines.append(f"  in the campaign: {entry['count']} in {entry['maps']} maps")
    if entry.get("read_as"):
        lines.append("  read as: " + ", ".join(
            f"{name} x{n}" for name, n in entry["read_as"].items()))
        lines.append("  worked by: " + ", ".join(
            f"{name} x{n}" for name, n in entry["worked_by"].items()))
    if entry["kind"] != "effect":
        if entry.get("set_off_by"):
            lines.append("  on a wire, set off by: " + ", ".join(
                f"{who} x{n}" for who, n in entry["set_off_by"].items()))
        if entry.get("starts"):
            lines.append(f"  starts {entry['starts']} chains, answered by: " + ", ".join(
                f"{what} x{n}" for what, n in entry["drives"].items()))
        if not entry.get("set_off_by") and not entry.get("starts"):
            lines.append("  on a wire: never, in the campaign")
        lines.append("  a part is not a mechanism: what this one becomes is "
                     "decided by what is wired to it")
    if entry["examples"]:
        lines.append(f"  {entry.get('examples_are', 'examples')}: " + ", ".join(
            _example(entry, item) for item in entry["examples"]))
        first = entry["examples"][0]
        what = entry["kind"].split()[0]
        if what in ("effect", "channel"):
            what = "sector" if first["id"] == first["sector"] else None
        if what:
            lines.append(f"  its fields: python -m tools.catalog record "
                         f"{first['map']} {what} {first['id']}")
        lines.append(f"  its wiring: python -m tools.catalog mechanisms "
                     f"{first['map']} --place {first['map']}:{first['sector']}")
        lines.append(f"  look at it: python -m tools.study <slug> --seed "
                     f"{first['map']}:{first['sector']}!")
    if entry.get("places"):
        labels = place_labels()
        top = entry["places"][0]["id"]
        lines.append(f"  rooms with the most ({entry['place_count']} hold one): "
                     + ", ".join(
                         f"{room['id']} x{room['count']}"
                         + (f" [{labels[room['id']]['kind']}]"
                            if room["id"] in labels else "")
                         for room in entry["places"]))
        lines.append(f"  that room: python -m tools.catalog show {top}")
    if entry.get("lessons"):
        lines.append("  taught by: " + ", ".join(entry["lessons"])
                     + f"  (python -m tools.catalog show lesson:{entry['lessons'][0]})")
    return "\n".join(lines)


def find_mechanisms(words: list[str], limit: int = 10) -> list[str]:
    from bloodmap import examples

    index = mechanism_index()
    if index is None:
        return ["  (not built: python -m tools.catalog build-mechanisms)"]
    out = []
    for key, entry in examples.search(index, words)[:limit]:
        if entry["kind"] == "lesson":
            said = f"tutorial: {entry['says'][:70]}"
        else:
            said = (f"{entry['name']}: {entry['count']} in {entry['maps']} maps"
                    + (f", e.g. {_example(entry, entry['examples'][0])}"
                       if entry["examples"] else "")
                    + (f"; most in room {entry['places'][0]['id']} "
                       f"x{entry['places'][0]['count']}"
                       if entry.get("places") else ""))
        out.append(f"  {key:<28}{said}")
    return out


def _wire(row: dict) -> str:
    """One shape of chain as a line: the act, who it is done to, what answers."""
    first = row["examples"][0]
    return (f"{row['cause']} on {row['sender']} -> "
            f"{'; '.join(row['answers']) or 'nothing listens'}: "
            f"{row['count']} in {row['maps']} maps"
            + (f", {row['keyed']} keyed" if row["keyed"] else "")
            + (f", {row['silent']} never fire" if row.get("silent") else "")
            + (f", {row['through_closet']} relayed out of reach"
               if row.get("through_closet") else "")
            + f", e.g. {first['map']} {first['root']}"
            + (f" in room {first['place']}" if first.get("place") else ""))


def find_wiring(words: list[str], limit: int = 8) -> list[str]:
    """The shapes of chain answering to the words, and how to read one in full."""
    from bloodmap import examples

    index = mechanism_index()
    if index is None or "wiring" not in index:
        return ["  (not built: python -m tools.catalog build-mechanisms)"]
    found = examples.search_wiring(index, words)
    out = [f"  {_wire(row)}" for row in found[:limit]]
    if len(found) > limit:
        out.append(f"  ... {len(found) - limit} more shapes: "
                   f"python -m tools.catalog wiring {' '.join(words)}")
    if found:
        first = found[0]["examples"][0]
        out.append(f"  one in full: python -m tools.catalog mechanisms {first['map']} "
                   f"--place {first['map']}:{first['sector']}")
    return out


def find_written(words: list[str], limit: int = 5) -> list[str]:
    """Reports and measured families that mention the words, from the knowledge index."""
    try:
        from bloodmap.knowledge_index import lookup

        found = lookup(" ".join(words))
    except Exception as error:               # the index reads many files
        return [f"  (knowledge index unavailable: {type(error).__name__}: {error})"]
    out = []
    for entry in found.get("entries", []):
        if entry.get("subject_kind") == "tile":
            continue                         # tiles are answered above
        out.append(f"  {entry['source']}: {entry['says'][:80]}")
        if len(out) >= limit:
            break
    return out


def record(map_name: str, kind: str, index: int) -> str:
    """One sector, wall or sprite as the fields that are set on it.

    What an agent copies a mechanism from: the type by name, the fields that
    are not zero, and the extension's fields that are not zero. Everything at
    its default is left out, which turns a seventy-field record into a few
    lines.
    """
    from bloodmap.blood_types import classify
    from bloodmap.corpus import corpus_map_path
    from bloodmap.format import read_map
    from bloodmap.model import record_extra, record_fields

    path = (pathlib.Path(map_name) if map_name.upper().endswith(".MAP")
            else corpus_map_path(map_name))
    disk = read_map(path)
    group = {"sector": disk.sectors, "wall": disk.walls,
             "sprite": disk.sprites}[kind]
    if not 0 <= index < len(group):
        return f"{path.stem} has {len(group)} {kind}s; there is no {kind} {index}"
    item = group[index]
    fields = record_fields(item)
    named = classify(kind, int(fields.get("type", 0)))

    def set_fields(values, skip=()):
        return ", ".join(f"{name}={value}" for name, value in values.items()
                         if value not in (0, -1, False) and name not in skip)

    lines = [f"{path.stem.upper()} {kind} {index}: type {fields.get('type', 0)} "
             f"{named.get('name') or ''}".rstrip()]
    lines.append("  fields: " + (set_fields(fields, skip=("type", "extra")) or "(all default)"))
    extra = record_extra(item)
    if extra:
        lines.append("  extension: " + (set_fields(extra, skip=("reference",))
                                        or "(present, all default)"))
    else:
        lines.append("  extension: none")
    if PLACES.exists():
        from bloodmap.sector_geom import wall_owners

        sector = (index if kind == "sector"
                  else int(fields["sector"]) if kind == "sprite"
                  else wall_owners(disk).get(index, -1))
        room = sector_places().get(path.stem.upper(), {}).get(sector)
        if room:
            label = place_labels().get(room)
            lines.append(f"  in room: {room}"
                         + (f" [{label['kind']}]" if label else "")
                         + f"  (python -m tools.catalog show {room})")
        else:
            lines.append(f"  in room: none catalogued for sector {sector}")
    return "\n".join(lines)


def show(what: str) -> str:
    """One entry, with everything the library links to it."""
    lines = []
    if not what.isdigit():
        from bloodmap import examples

        index = mechanism_index()
        key = examples.resolve(index, what) if index else None
        if key is not None:
            return show_mechanism(key, index["entries"][key])
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
            return (f"no place, type, effect, channel or lesson called {what} "
                    f"in the catalogue; try: python -m tools.catalog find {what}")
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
        lines.extend(_place_holds(row))
        lines.append(f"  look at it: python -m tools.study <slug> --seed {row['map']}:{row['host']}!")
    return "\n".join(lines)


#: Sprite categories that are a room's contents and not its workings.
STANDS_IN = ("dude", "weapon", "ammo", "health", "armor", "powerup", "start")


def _place_holds(row: dict) -> list[str]:
    """What a catalogued room does and what stands in it, by the mechanisms shelf's keys."""
    from bloodmap.blood_types import classify

    held = row.get("mechanisms")
    if held is None:
        return [f"  sprite types: {row['types']}",
                f"  moving sector types: {row['moves']}",
                "  mechanisms: not joined (python -m tools.catalog build-places)"]
    index = mechanism_index() or {"entries": {}}
    works, stands = [], {}
    for key, count in sorted(held.items(), key=lambda item: (-item[1], item[0])):
        kind, _colon, ident = key.partition(":")
        entry = index["entries"].get(key)
        if entry is not None:
            name, category = entry["name"], entry.get("category")
        elif kind in ("sector", "wall", "sprite", "channel"):
            named = classify(kind, int(ident))
            name, category = named.get("name") or f"type {ident}", named.get("category")
        else:
            name, category = ident, None
        if kind == "sprite" and category in STANDS_IN:
            stands.setdefault(category, []).append(f"{name} x{count}")
        else:
            works.append((key, f"{key} {name} x{count}" if kind != "effect"
                          else f"{key} x{count}"))
    lines = ["  works by: " + (", ".join(said for _key, said in works[:14])
                              + (f" (+{len(works) - 14} more)" if len(works) > 14 else "")
                              if works else "nothing typed, no sector effect")]
    if stands:
        lines.append("  stands in it: " + "; ".join(
            f"{category}: {', '.join(stands[category][:5])}"
            for category in STANDS_IN if category in stands))
    if works:
        lines.append(f"  one of those: python -m tools.catalog show {works[0][0]}")
        lines.append(f"  its wiring: python -m tools.catalog mechanisms {row['map']} "
                     f"--place {row['id']}")
    return lines


def map_reading(name: str, rooms: int = 12, shapes: int = 10) -> str:
    """One whole map as our readers read it: rooms, how it ends, wiring, materials.

    Everything here is a reading, and the last section says how far the
    readers got: a campaign map is known to be finishable, so where the
    reading stops short the reader is at fault, not the map. Each line that
    names a room or an object can be followed with the command beside it.
    """
    from collections import Counter

    from bloodmap import completion, examples
    from bloodmap.corpus import corpus_map_path
    from bloodmap.format import read_map
    from bloodmap.model import record_fields

    path = (pathlib.Path(name) if name.upper().endswith(".MAP")
            else corpus_map_path(name))
    key = path.stem.upper()
    disk = read_map(path)
    data = json.loads(PLACES.read_text("utf-8")) if PLACES.exists() else {"places": []}
    mine = [row for row in data["places"] if row["map"] == key]
    where = {sector: row["id"] for row in mine for sector in row["members"]}
    labels, names, looks = place_labels(), owner_names(), tile_looks()

    def room(sector: int) -> str:
        ident = where.get(sector)
        if ident is None:
            return f"sector {sector} (no catalogued room)"
        label = labels.get(ident)
        return ident + (f" [{label['kind']}]" if label else "")

    def tile(number: int) -> str:
        said = names.get(number) or looks.get(number, {}).get("looks") or "unnamed"
        return f"{number} {said[:34]}"

    mark = completion.read(disk, key)
    lines = [f"MAP {key}  {len(disk.sectors)} sectors, {len(disk.walls)} walls, "
             f"{len(disk.sprites)} sprites; {len(mine)} rooms catalogued; the "
             f"player starts in {room(mark['start_sector'])}"]

    #: what the map calls itself: every tile in it that is a sign
    worn = {int(record_fields(wall)[field]) for wall in disk.walls
            for field in ("picnum", "over_picnum")}
    worn |= {int(record_fields(sprite)["picnum"]) for sprite in disk.sprites}
    signs = sorted(number for number in worn
                   if looks.get(number, {}).get("class") == "sign")
    lettered = sorted({word for row in mine for word in row["signs"]})
    lines.append("SAYS OF ITSELF  (tiles that are signs, and lettering spelt in sprites)")
    lines.append("  " + ("; ".join(tile(number) for number in signs[:14])
                         or "no sign tile")
                 + (f"; lettered {lettered}" if lettered else ""))
    lines.append(f"ROOMS  (the {min(rooms, len(mine))} largest of {len(mine)}; "
                 f"python -m tools.catalog show <room>)")
    for row in sorted(mine, key=lambda r: -r["metres"][0] * r["metres"][1])[:rooms]:
        label = labels.get(row["id"])
        held = row.get("mechanisms", {})
        dudes = sum(n for k, n in held.items() if k.startswith("sprite:")
                    and (mechanism_index() or {"entries": {}})["entries"].get(k, {})
                    .get("category") == "dude")
        lines.append(
            f"  {row['id']:<10}{('[' + label['kind'] + '] ') if label else ''}"
            f"{'outdoor' if row['sky'] else 'indoor'} "
            f"{row['metres'][0]}x{row['metres'][1]} m, {row['sectors']} sectors"
            + (f", lettered {row['signs']}" if row["signs"] else "")
            + (f", {dudes} dudes" if dudes else "")
            + f"; wears " + ", ".join(tile(t) for t in row["distinctive"][:2]))

    lines.append("HOW IT IS FINISHED")
    for row in mark["exits"]:
        lines.append(f"  exit: {row['cause']} on {row['root']} in {room(row['sector'])} "
                     f"-> {row['to']}"
                     + ("" if row["reached"] else "  (our traversal never gets here)"))
    if not mark["exits"]:
        lines.append("  exit: NONE. No chain ends at the level's exit")
    for row in mark["keys"]:
        lines.append(f"  key: {row['name']} (sprite {row['sprite']}) in {room(row['sector'])}"
                     + ("" if row["reached"] else "  (our traversal never gets here)"))
    for row in mark["locked"]:
        lines.append(
            f"  wants the {row['key_name'] or row['key']} key"
            f"{' (pushed by hand)' if row.get('by_hand') else ''}: "
            f"{len(row['senders'])} face(s)/object(s) in {room(row['sector'])} "
            f"({row['senders'][0]}) -> {', '.join(row['answers'][:6]) or 'nothing'}"
            + (f" (+{len(row['answers']) - 6})" if len(row["answers"]) > 6 else ""))
    secrets = mark["secrets"]
    lines.append(f"  secrets: the level declares {secrets['declared']}; "
                 f"{secrets['credited_normal']} senders credit a normal one and "
                 f"{secrets['credited_super']} a super secret")

    lines.append("HOW IT IS PLAYED  (gated areas: what each act opens; the "
                 "engine decides where one ends)")
    for area in mark["gated_areas"][:14]:
        lines.append(f"  round {area['round']}: {area['sectors']:>3} sectors around "
                     f"{room(area['first_sector'])} -- {'; '.join(area['opened_by'])}")
    if len(mark["gated_areas"]) > 14:
        lines.append(f"  ... {len(mark['gated_areas']) - 14} more areas")
    seen = examples.observe(key, disk)
    index = examples.build([seen], places={key: where})
    lines.append(f"WIRING  ({len(seen['wires'])} chains; "
                 f"python -m tools.catalog mechanisms {key} --place <room>)")
    lines.append("  in phrases: " + ", ".join(
        f"{phrase['name']} {phrase['chains']}"
        for phrase in examples.idioms(index) if phrase["chains"]))
    # Each shape beside how often Blood wires the same thing. A shape the
    # campaign never has is not wrong, but it is the first place to look:
    # an author's intent the campaign expresses some other way.
    known = {(row["cause"], row["sender"], tuple(row["answers"])): row
             for row in (mechanism_index() or {}).get("wiring", ())}
    in_campaign = key in set((mechanism_index() or {}).get("maps", ()))
    unattested = []
    for row in index["wiring"]:
        there = known.get((row["cause"], row["sender"], tuple(row["answers"])))
        if there is None:
            unattested.append(row)
    for row in index["wiring"][:shapes]:
        there = known.get((row["cause"], row["sender"], tuple(row["answers"])))
        said = f"  {_wire(row)}".replace(f": {row['count']} in 1 maps",
                                         f": x{row['count']}")
        if not in_campaign:
            said += ("  [the campaign: never]" if there is None else
                     f"  [the campaign: {there['count']} in {there['maps']} maps]")
        lines.append(said)
    if len(index["wiring"]) > shapes:
        lines.append(f"  ... {len(index['wiring']) - shapes} more shapes")
    if not in_campaign:
        lines.append(f"  {len(index['wiring']) - len(unattested)} of "
                     f"{len(index['wiring'])} shapes are ones the campaign has; "
                     f"{len(unattested)} it never has"
                     + (": " + "; ".join(
                         f"{row['cause']} on {row['sender']} -> "
                         f"{', '.join(row['answers']) or 'nothing'}"
                         for row in unattested[:6]) if unattested else ""))

    lines.append("MATERIALS  (python -m tools.catalog show <tile>)")
    walls = Counter(int(record_fields(wall)["picnum"]) for wall in disk.walls
                    if int(record_fields(wall)["next_sector"]) < 0)
    floors = Counter(int(record_fields(sector)["floor_picnum"]) for sector in disk.sectors)
    ceilings = Counter(int(record_fields(sector)["ceiling_picnum"]) for sector in disk.sectors)
    for said, counted in (("walls", walls), ("floors", floors), ("ceilings", ceilings)):
        lines.append(f"  {said}: " + "; ".join(
            f"{tile(t)} x{n}" for t, n in counted.most_common(5))
            + f"  ({len(counted)} tiles in all)")

    lines.append("HOW FAR OUR READERS GET  (a shipped map can be finished: a "
                 "shortfall here is the reader's)")
    lines.append(f"  stood in {mark['reached']} of {mark['space']} player-space "
                 f"sectors; the older progression reader ends at "
                 f"{mark['older_reader']['final_reachable']}")
    if mark["unreached"]:
        by_room = Counter(where.get(sector) for sector in mark["unreached"])
        lines.append("  never reached: " + ", ".join(
            f"{(ident or 'uncatalogued')}"
            + (f" [{labels[ident]['kind']}]" if ident in labels else "")
            + f" x{count}" for ident, count in by_room.most_common(8)))
    for said in completion.missed(mark):
        lines.append(f"  missed: {said}")
    lines.append(f"  in full: python -m tools.reading_check {key}")
    return "\n".join(lines)


def find_all(words: list[str]) -> str:
    """Everything the library holds that answers to the words.

    One question, every shelf: what the engine does (types, effects,
    channels, lessons), what a mapper sees (tiles, places), and what has been
    written down (studies, ideas, measured reports).
    """
    out = ["PARTS  (a type, a sector effect, an engine channel, a lesson: "
           "python -m tools.catalog show <key>)"]
    out.extend(find_mechanisms(words))
    out.append("WIRING  (a mechanism: an act, the object it is done to, what answers)")
    out.extend(find_wiring(words))
    out.append("TILES")
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
    out.append("WRITTEN")
    out.extend(find_written(words))
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
    sub.add_parser("build-mechanisms")
    sub.add_parser("idioms", help="the phrases the campaign's wiring is written in")
    whole = sub.add_parser("map", help="one whole map as our readers read it")
    whole.add_argument("name")
    wires = sub.add_parser("wiring", help="shapes of chain: an act, a sender, what answers")
    wires.add_argument("words", nargs="+")
    wires.add_argument("--limit", type=int, default=40)
    rec = sub.add_parser("record")
    rec.add_argument("map")
    rec.add_argument("kind", choices=("sector", "wall", "sprite"))
    rec.add_argument("index", type=int)
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
            from bloodmap.corpus import corpus_map_path
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
                  f"hop(s) -> {chain['receivers']}"
                  + ("  NEVER FIRES: reports neither its ON nor its OFF change"
                     if chain["silent"] else "")
                  + (f"  stops at {', '.join(chain['dead_relays'])}: a relay "
                     f"that reports no change" if chain["dead_relays"] else "")
                  + (f"  relayed out of reach by {', '.join(chain['closet_relays'])}"
                     if chain["closet_relays"] else ""))
            for step in chain["steps"][:10]:
                print(f"     {step['from']} --ch {step['channel']} cmd "
                      f"{step['command']}--> {step['to']} ({step['to_type']})"
                      f"{' after ' + str(step['wait']) if step['wait'] else ''}")
    elif args.command == "record":
        print(record(args.map, args.kind, args.index))
    elif args.command == "map":
        print(map_reading(args.name))
    elif args.command == "idioms":
        from bloodmap import examples

        for phrase in examples.idioms(mechanism_index() or {}):
            print(f"{phrase['name']:<14}{phrase['chains']:>5} chains in "
                  f"{phrase['shapes']} shapes  {phrase['says']}")
            if phrase["commonest"]:
                print(f"{'':14}commonest: {_wire(phrase['commonest'])}")
                print(f"{'':14}all of them: python -m tools.catalog wiring {phrase['name']}")
    elif args.command == "wiring":
        print("\n".join(find_wiring(args.words, args.limit)) or "  no chain of that shape")
    elif args.command == "build-mechanisms":
        document = build_mechanisms()
        kinds = Counter(entry["kind"] for entry in document["entries"].values())
        print(f"{len(document['entries'])} entries from {len(document['maps'])} "
              f"maps -> {MECHANISMS.relative_to(ROOT).as_posix()}")
        for kind, count in kinds.most_common():
            print(f"  {kind:<14}{count}")
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
        index = mechanism_index()
        if index is None:
            print("mechanisms: not built (python -m tools.catalog build-mechanisms)")
        else:
            kinds = Counter(entry["kind"] for entry in index["entries"].values())
            print("mechanisms: " + "; ".join(
                f"{count} {kind}s" for kind, count in kinds.most_common()))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
