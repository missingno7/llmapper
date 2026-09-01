"""Where the campaign is attested to use each tile, and the laws that follow.

The representation taxonomy as a *measurement*. For every picnum this says
which slots the campaign has been seen to use it in and how often -- wall
picnum on a one- or two-sided wall, the masked overlay of a two-sided wall,
floor, ceiling, either of those parallaxed, and sprite by alignment.

It says where a tile HAS been seen, never where it MAY go. That distinction
is the whole reason the usage-kind check is a warning rather than an error,
and why an owner anchor's `dual_role` note overrides it in both directions.

Three engine laws are enforced from here, each measured before it was given a
severity:

**The mask law.** A tile carrying the mask colour -- palette index 255, the
ART transparency colour, which is not the translucency cstat bit -- never
appears on a floor, a ceiling, or a one-sided wall's picnum. Measured: 0 of
26383 non-parallax surface slots and 0 of 52422 one-sided wall slots, over 43
campaign maps. Two tiles break it on *two-sided* walls across 23 of 60839
slots, which is too few to name a family, so the rule leaves those alone.

**The parallax law, both directions.** A parallaxed surface wears a tile from
the sky family; a sky-family tile on a surface carries the parallax bit. The
family is derived, not assumed: every tile the campaign ever parallaxes, which
is exactly three -- 2500, 3491, 3678. They are backdrops rather than skies as
such (3678 is a dark rock face used as a cavern roof 363 times), and all three
are 64x400.

**Why the aspect law exempts them.** 64x400 is not a power of two on either
side, and `bloodmap.rules_blood`'s `flat-tile-power-of-two` would reject all
three on a normal ceiling. It does not have to: a parallax surface is not
sampled through `picsiz` at all. The two laws interlock -- you cannot legally
put a sky tile on an ordinary ceiling, because the aspect law forbids it and
the parallax law tells you which bit to set instead.
"""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any

KNOWLEDGE = (Path(__file__).resolve().parent.parent / "knowledge" / "blood"
             / "design" / "usage-kinds-v1.json")

#: The slots a tile can occupy, as the mine counts them.
SURFACE_SLOTS = ("floor", "ceiling")
WALL_SLOTS = ("wall_one_sided", "wall_two_sided")
SPRITE_SLOTS = ("sprite_face", "sprite_wall", "sprite_floor")

#: Blood's own bits, named so a reader does not have to remember them.
STAT_PARALLAX = 1
CSTAT_MASKED = 16


class UsageError(ValueError):
    """A question about tile usage the table cannot stand behind."""


@lru_cache(maxsize=1)
def load(path: str | Path | None = None) -> dict[str, Any]:
    """The compiled usage-kind table, or an empty one when it is absent."""
    target = Path(path) if path is not None else KNOWLEDGE
    try:
        return json.loads(target.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {"usage": {}, "sky_family": {"tiles": []}, "tile_sizes": {}}


def slots_for(picnum: int, table: dict[str, Any] | None = None) -> dict[str, int]:
    """Which slots the campaign uses this tile in, with counts."""
    data = table if table is not None else load()
    return dict(data.get("usage", {}).get(str(int(picnum)), {}))


def attested(picnum: int, slot: str, table: dict[str, Any] | None = None) -> bool:
    """Whether the campaign has ever used this tile in this slot."""
    return slots_for(picnum, table).get(slot, 0) > 0


def sky_family(table: dict[str, Any] | None = None) -> set[int]:
    """Every tile the campaign puts on a parallaxed surface."""
    data = table if table is not None else load()
    return {int(t) for t in data.get("sky_family", {}).get("tiles", [])}


def tile_size(picnum: int,
              table: dict[str, Any] | None = None) -> tuple[int, int] | None:
    data = table if table is not None else load()
    size = data.get("tile_sizes", {}).get(str(int(picnum)))
    return (int(size[0]), int(size[1])) if size else None


@lru_cache(maxsize=1)
def masked_tiles(directory: str = "reference/blood",
                 threshold: float = 0.05) -> frozenset[int]:
    """Tiles carrying enough mask colour to be see-through, from the ART.

    The threshold is the owner's: above five percent transparent pixels the
    tile is a cut-out rather than a texture with a stray index in it.
    """
    try:
        from .art import read_art_directory, transparency_stats
    except Exception:
        return frozenset()
    out = set()
    try:
        tiles = read_art_directory(directory)
    except Exception:
        return frozenset()
    for picnum, tile in tiles.items():
        try:
            stats = transparency_stats(tile)
        except Exception:
            continue
        if stats.get("has_mask") and float(stats["transparent_ratio"]) > threshold:
            out.add(int(picnum))
    return frozenset(out)


def wall_slot(next_sector: int) -> str:
    return "wall_two_sided" if int(next_sector) >= 0 else "wall_one_sided"


def surface_slot(role: str, stat: int) -> str:
    return f"{role}_parallax" if int(stat) & STAT_PARALLAX else role


def unattested_uses(disk: Any, *, table: dict[str, Any] | None = None,
                    allow: set[int] | None = None) -> list[dict[str, Any]]:
    """Every place the map puts a tile in a slot the campaign never attests.

    A warning, not an error: the corpus is 43 maps and an authored map is
    allowed to be the first to do something. What it is not allowed to do is
    do it *by accident*, which is what this catches -- shelf goods laid on a
    floor, a facade backdrop used as bulk fill, a sprite tile painted on a
    wall.
    """
    data = table if table is not None else load()
    if not data.get("usage"):
        return []
    permitted = allow or set()
    out = []
    for index, sector in enumerate(disk.sectors):
        fields = sector.fields
        for role in SURFACE_SLOTS:
            picnum = int(fields[f"{role}_picnum"])
            if picnum in permitted:
                continue
            slot = surface_slot(role, int(fields[f"{role}_stat"]))
            if not slots_for(picnum, data):
                continue                  # tile the campaign never uses at all
            if not attested(picnum, slot, data):
                out.append({"where": f"sector[{index}].{role}",
                            "picnum": picnum, "slot": slot,
                            "attested": sorted(slots_for(picnum, data))})
    for index, wall in enumerate(disk.walls):
        fields = wall.fields
        picnum = int(fields["picnum"])
        if picnum in permitted:
            continue
        slot = wall_slot(int(fields["next_sector"]))
        if not slots_for(picnum, data):
            continue
        if not attested(picnum, slot, data):
            out.append({"where": f"wall[{index}]", "picnum": picnum,
                        "slot": slot,
                        "attested": sorted(slots_for(picnum, data))})
    return out


def overused(disk: Any, *, table: dict[str, Any] | None = None,
             factor: float = 20.0, floor_count: int = 20) -> list[dict[str, Any]]:
    """Tiles the map leans on far harder than the campaign ever does.

    Slot-correctness is not the whole of usage. Tile 400 is a multi-storey
    facade backdrop that the campaign puts on 48 wall slots in 43 maps; the
    pattern zoo made it the default gallery wall and used it 162 times in one
    level. Every one of those uses is in an attested slot, so the usage-kind
    check passes them all, and the level still looks nothing like Blood.

    This compares each tile's share of the authored map's wall slots against
    its share of the campaign's, and reports the ones that are `factor` times
    out. It is the crudest possible instrument and it found the real problem.
    """
    data = table if table is not None else load()
    usage = data.get("usage", {})
    if not usage:
        return []
    campaign_total = sum(counts.get(slot, 0)
                         for counts in usage.values() for slot in WALL_SLOTS)
    if not campaign_total:
        return []
    from collections import Counter

    mine = Counter(int(w.fields["picnum"]) for w in disk.walls)
    total = sum(mine.values()) or 1
    out = []
    for picnum, count in mine.most_common():
        if count < floor_count:
            continue
        campaign = sum(usage.get(str(picnum), {}).get(slot, 0)
                       for slot in WALL_SLOTS)
        share = count / total
        campaign_share = campaign / campaign_total
        if campaign_share <= 0:
            continue
        ratio = share / campaign_share
        if ratio >= factor:
            out.append({"picnum": picnum, "used": count,
                        "share": round(share, 4),
                        "campaign_slots": campaign,
                        "campaign_share": round(campaign_share, 6),
                        "times_the_campaign_rate": round(ratio, 1)})
    return out
