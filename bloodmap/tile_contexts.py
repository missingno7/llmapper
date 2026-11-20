"""What a tile is used as, where, and on whose evidence: a catalogue that grows.

The owner, 2026-11-20, of the one-line `dual_role` note on an anchor: "There
can be a lot of different contexts for stuff", and then: "I would like to
make the whole system the way it can learn by itself, so agents should be
able to discover things, catalogise them and easily browse them".

A CONTEXT is a tile in a slot in a kind of place: 2476 on a floor in a shop
(a register top) and on a wall in a works (machinery); 364 on a one-sided
wall and on a step's face. Each context carries its EVIDENCE, and the
evidence says whose it is. In order of authority:

``owner``              the owner's tile sheet (`owner-anchors-v1.json`): his
                       name for the tile and his `dual_role` notes, as said
``blood-campaign``     the 43 maps, counted
``owner-map``          the owner's own maps (`owner-maps.json` lists them)
``community-curated``  the curated community maps, counted
``blood-bloodbath``    the multiplayer maps, counted
``community``          the 1,500 community maps, counted
``agent``              what an agent read and recorded (`record`), with what
                       it looked at; never outranks a count or the owner

The counts are MINED (`mine`, by `tools/tile_contexts.py mine`) into one file
per population; the readings are appended to `readings.jsonl`. Nothing here
decides what a tile may be; it says where it has been seen and who says so,
and `attestation` answers "has anyone used this tile here, and who".

A slot is the engine's: a floor or ceiling (``_parallax`` when open to the
sky), a wall by the band the renderer draws (`bloodmap.render_slots`:
``one_sided_middle``, ``two_sided_upper``, ``two_sided_lower``,
``masked_middle``, ``oneway_middle``), or a sprite by alignment
(``sprite_face``, ``sprite_wall``, ``sprite_floor``). A place is the kind the
catalog labels the room with where it is labelled, else ``outdoors`` or
``indoors``.
"""

from __future__ import annotations

import datetime
import json
from pathlib import Path
from typing import Any, Iterable, Iterator

ROOT = Path(__file__).resolve().parent.parent
HOME = ROOT / "knowledge" / "blood" / "tile-contexts"
READINGS = HOME / "readings.jsonl"
OWNER_MAPS = HOME / "owner-maps.json"

#: whose evidence, most authoritative first
AUTHORITY = ("owner", "blood-campaign", "owner-map", "community-curated",
             "blood-bloodbath", "community", "agent")
#: populations that are counted from maps
MINED = AUTHORITY[1:-1]
ANY = "any"
EXAMPLES = 3

SPRITE_SLOT = {0: "sprite_face", 16: "sprite_wall", 32: "sprite_floor"}


class TileContextError(ValueError):
    """A context that cannot be recorded as asked."""


def place_kind(sector_fields: dict, labelled: str | None = None) -> str:
    """A room's kind where it is labelled, else whether it is under the sky."""
    if labelled:
        return str(labelled)
    return "outdoors" if int(sector_fields["ceiling_stat"]) & 1 else "indoors"


def uses(disk: Any, labels: dict[int, str] | None = None) -> Iterator[tuple]:
    """Every (tile, slot, place, reference) this map draws or stands.

    Walls are taken by the band the renderer draws, so a tile stored on a
    wall it never shows on is not counted as used there.
    """
    from .render_slots import render_slots
    from .usage_kinds import surface_slot

    labels = labels or {}
    sectors = [s.fields for s in disk.sectors]
    kinds = [place_kind(f, labels.get(i)) for i, f in enumerate(sectors)]
    for index, f in enumerate(sectors):
        for role in ("floor", "ceiling"):
            tile = int(f[f"{role}_picnum"])
            yield tile, surface_slot(role, int(f[f"{role}_stat"])), kinds[index], ("sector", index)
    for draw in render_slots(disk):
        place = kinds[draw.sector] if 0 <= draw.sector < len(kinds) else "indoors"
        for band in draw.bands:
            yield int(band.tile), band.band, place, ("wall", draw.wall)
    for index, sprite in enumerate(disk.sprites):
        f = sprite.fields
        sector = int(f["sector"])
        if int(f["cstat"]) & 0x8000 or int(f["picnum"]) <= 0 or not 0 <= sector < len(kinds):
            continue
        slot = SPRITE_SLOT.get(int(f["cstat"]) & 48)
        if slot:
            yield int(f["picnum"]), slot, kinds[sector], ("sprite", index)


def mine(maps: Iterable[tuple[str, Any, dict[int, str] | None]]) -> dict:
    """Count every (tile, slot, place) over maps given as (name, disk, labels)."""
    tiles: dict[str, dict[str, dict]] = {}
    count = 0
    failed: list[str] = []
    for name, disk, labels in maps:
        # a community map may be malformed (a wall's point2 past the end):
        # it is skipped and named, never repaired
        try:
            found = list(uses(disk, labels))
        except (IndexError, KeyError, ValueError) as exc:
            failed.append(f"{name}: {type(exc).__name__}")
            continue
        count += 1
        seen: set[tuple] = set()
        for tile, slot, place, ref in found:
            key = f"{slot}|{place}"
            row = tiles.setdefault(str(tile), {}).setdefault(
                key, {"count": 0, "maps": 0, "examples": []})
            row["count"] += 1
            if (tile, key) not in seen:
                seen.add((tile, key))
                row["maps"] += 1
                if len(row["examples"]) < EXAMPLES:
                    row["examples"].append([name, ref[0], ref[1]])
    return {"maps": count, "tiles": tiles, "failed": failed}


def mined_path(population: str) -> Path:
    return HOME / f"mined-{population}.json"


def save_mined(population: str, table: dict, *, maps: list[str]) -> Path:
    HOME.mkdir(parents=True, exist_ok=True)
    path = mined_path(population)
    document = {"population": population, "maps": table["maps"],
                "map_names": sorted(maps), "failed": table.get("failed", []),
                "mined": datetime.date.today().isoformat(),
                "tiles": table["tiles"]}
    path.write_text(json.dumps(document, sort_keys=True), encoding="utf-8")
    return path


_CACHE: dict[str, Any] = {}


def _mined(population: str) -> dict:
    if population not in _CACHE:
        path = mined_path(population)
        _CACHE[population] = (json.loads(path.read_text("utf-8"))
                              if path.exists() else {"tiles": {}, "maps": 0})
    return _CACHE[population]


def clear_cache() -> None:
    _CACHE.clear()


def readings() -> list[dict]:
    """Every context an agent recorded, oldest first."""
    if "readings" not in _CACHE:
        _CACHE["readings"] = ([json.loads(line) for line in
                               READINGS.read_text("utf-8").splitlines() if line.strip()]
                              if READINGS.exists() else [])
    return _CACHE["readings"]


def record(tile: int, *, slot: str = ANY, place: str = ANY, is_: str,
           evidence: str, by: str = "agent", fits: bool = True) -> dict:
    """Catalogue what a tile is in a context, and what that was read from.

    An agent's reading is the weakest evidence there is and never replaces a
    count or the owner's word: it fills a gap ("what IS 364 on a step") and
    says what it looked at, so the next agent can check it.

    `fits` False records a MISFIT: what goes wrong when the tile is used
    there ("reads as eyes at street distance"). A misfit attests nothing,
    and `novel` and `show` say it out loud: a warning is never permission.
    """
    if not is_.strip() or not evidence.strip():
        raise TileContextError("a reading says what the tile is and what that was read from")
    row = {"tile": int(tile), "slot": slot, "place": place, "is": is_.strip(),
           "evidence": evidence.strip(), "by": by, "fits": bool(fits),
           "date": datetime.date.today().isoformat()}
    HOME.mkdir(parents=True, exist_ok=True)
    with READINGS.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(row, sort_keys=True) + "\n")
    _CACHE.pop("readings", None)
    return row


def _owner_rows(tile: int) -> list[dict]:
    from .owner_anchors import load_owner_anchors

    if "owner" not in _CACHE:
        try:
            _CACHE["owner"] = load_owner_anchors()
        except Exception:                                        # noqa: BLE001
            _CACHE["owner"] = None
    anchors = _CACHE["owner"]
    anchor = anchors.get(int(tile)) if anchors is not None else None
    if anchor is None:
        return []
    rows = [{"source": "owner", "slot": ANY, "place": ANY, "is": anchor.label_en,
             "evidence": "owner tile sheet"}]
    if anchor.dual_role:
        rows.append({"source": "owner", "slot": ANY, "place": ANY,
                     "is": anchor.dual_role, "evidence": "owner tile sheet: dual_role"})
    return rows


def contexts(tile: int) -> list[dict]:
    """Everything known of a tile, context by context, most authoritative first."""
    tile = int(tile)
    out = list(_owner_rows(tile))
    for population in MINED:
        for key, row in _mined(population).get("tiles", {}).get(str(tile), {}).items():
            slot, place = key.split("|", 1)
            out.append({"source": population, "slot": slot, "place": place,
                        "count": row["count"], "maps": row["maps"],
                        "examples": row["examples"]})
    for row in readings():
        if int(row["tile"]) == tile:
            out.append({"source": "agent", "by": row.get("by", "agent"),
                        "fits": row.get("fits", True),
                        "slot": row["slot"], "place": row["place"], "is": row["is"],
                        "evidence": row["evidence"], "date": row.get("date")})
    rank = {name: index for index, name in enumerate(AUTHORITY)}
    out.sort(key=lambda r: (rank.get(r["source"], 99), -int(r.get("count", 0))))
    return out


def attestation(tile: int, slot: str, place: str | None = None) -> dict | None:
    """The most authoritative evidence that this tile has been used here.

    `place` None asks about the slot in any place. The owner's own words
    attest a tile only where he said them about a context; his name for a
    tile attests nothing about where it goes.
    """
    for row in contexts(tile):
        if row["source"] == "owner" or row.get("fits") is False:
            continue
        if row["slot"] not in (slot, ANY):
            continue
        if place is not None and row["place"] not in (place, ANY):
            continue
        return row
    return None


def suggest(slot: str, place: str | None = None, *, at_least: str = "community",
            limit: int = 20) -> list[dict]:
    """Tiles used in this slot (and kind of place), most used first, with whose count."""
    allowed = AUTHORITY[: AUTHORITY.index(at_least) + 1]
    score: dict[int, dict] = {}
    for population in MINED:
        if population not in allowed:
            continue
        for tile, rows in _mined(population).get("tiles", {}).items():
            for key, row in rows.items():
                s, p = key.split("|", 1)
                if s != slot or (place is not None and p != place):
                    continue
                entry = score.setdefault(int(tile), {"tile": int(tile), "count": 0,
                                                     "maps": 0, "sources": {}})
                entry["count"] += row["count"]
                entry["maps"] += row["maps"]
                entry["sources"][population] = row["maps"]
    ranked = sorted(score.values(), key=lambda e: (-len(e["sources"]), -e["maps"], -e["count"]))
    return ranked[:limit]


def novel(disk: Any, labels: dict[int, str] | None = None, *,
          trusted: tuple[str, ...] = ("blood-campaign", "owner-map")) -> list[dict]:
    """What this map does that the trusted evidence has never shown: the
    discoveries to catalogue (or the mistakes to fix). One row per (tile,
    slot, place), with where it happens and what evidence there is at all."""
    found: dict[tuple, dict] = {}
    for tile, slot, place, ref in uses(disk, labels):
        key = (tile, slot, place)
        if key in found:
            found[key]["count"] += 1
            continue
        best = attestation(tile, slot, place)
        warned = [r for r in contexts(tile) if r.get("fits") is False
                  and r["slot"] in (slot, ANY) and r["place"] in (place, ANY)]
        if best is not None and best["source"] in trusted and not warned:
            continue
        found[key] = {"tile": tile, "slot": slot, "place": place, "count": 1,
                      "first": list(ref),
                      "misfit": [r["is"] for r in warned],
                      "evidence": None if best is None else
                      {k: best[k] for k in ("source", "slot", "place", "maps", "is", "examples")
                       if k in best}}
    return sorted(found.values(), key=lambda r: (r["evidence"] is not None, -r["count"]))
