"""Mine the per-tile usage-kind table by RENDERED slot.

.. code-block:: bash

    python -m tools.mine_usage_kinds                 # campaign -> report + v2 knowledge
    python -m tools.mine_usage_kinds --art reference/blood --no-knowledge

The first table (`knowledge/blood/design/usage-kinds-v1.json`, mined by the
now-retired `work/_usage_mine.py`) counted where each tile is STORED: wall
picnum on a one- or two-sided wall, over_picnum, floor, ceiling, sprite by
alignment. The engine does not draw storage slots; it draws bands, and
`bloodmap.render_slots` says which band shows which tile. This mine counts
the bands. A tile stored on a two-sided wall lands in `two_sided_upper`,
`two_sided_lower`, both, or -- when neither sector steps and the wall is not
masked -- in `wall_undrawn`, which is not a slot at all but the count of
walls whose authored picnum is on screen nowhere from either side.

Population: the 43 campaign maps, through the corpus registry. Generated maps
are never mined.
"""

from __future__ import annotations

import argparse
import json
import pathlib
import sys
from collections import Counter, defaultdict

ROOT = pathlib.Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from bloodmap.format import read_map                            # noqa: E402
from bloodmap.patterns import list_corpus_maps                  # noqa: E402
from bloodmap.render_slots import (                             # noqa: E402
    MASKED_MIDDLE, ONE_SIDED_MIDDLE, ONEWAY_MIDDLE, RENDERED_WALL_SLOTS,
    TWO_SIDED_LOWER, TWO_SIDED_UPPER, bands_showing_picnum, render_slots,
)

SPRITE_ALIGNMENT = 0x30
STAT_PARALLAX = 1

#: The bands whose tile is opaque -- a mask-coloured tile here shows the
#: frame buffer through its holes. The masked and one-way middles are where
#: a see-through tile belongs (one-way is opaque too, but it is the overlay
#: field and the campaign uses it for mirrors and fake walls).
OPAQUE_BANDS = (ONE_SIDED_MIDDLE, TWO_SIDED_UPPER, TWO_SIDED_LOWER)

REPORT = ROOT / "reports" / "blood-usage-kinds-rendered.json"
KNOWLEDGE = ROOT / "knowledge" / "blood" / "design" / "usage-kinds-v2.json"
PREVIOUS = ROOT / "knowledge" / "blood" / "design" / "usage-kinds-v1.json"


def art_tables(directory: str) -> tuple[dict[int, tuple[int, int]], set[int]]:
    """(tile sizes, mask-carrying tiles) from the ART, or empty when absent."""
    try:
        from bloodmap.art import read_art_directory, transparency_stats
        art = read_art_directory(directory)
    except Exception:
        return {}, set()
    sizes = {}
    masked = set()
    for picnum, tile in art.items():
        sizes[int(picnum)] = (int(tile.width), int(tile.height))
        try:
            stats = transparency_stats(tile)
        except Exception:
            continue
        if stats.get("has_mask") and float(stats["transparent_ratio"]) > 0.05:
            masked.add(int(picnum))
    return sizes, masked


def mine_map(disk, usage, band_totals, undrawn_examples, name):
    draws = render_slots(disk)
    for sector in disk.sectors:
        f = sector.fields
        for role in ("floor", "ceiling"):
            picnum = int(f[f"{role}_picnum"])
            slot = (f"{role}_parallax" if int(f[f"{role}_stat"]) & STAT_PARALLAX
                    else role)
            usage[picnum][slot] += 1
            band_totals[slot] += 1
    for draw in draws:
        for band in draw.bands:
            usage[band.tile][band.band] += 1
            band_totals[band.band] += 1
        if draw.next_sector >= 0:
            band_totals["two_sided_walls"] += 1
        else:
            band_totals["one_sided_walls"] += 1
        if not bands_showing_picnum(draws, draw.wall):
            usage[draw.picnum]["wall_undrawn"] += 1
            band_totals["wall_undrawn"] += 1
            if len(undrawn_examples[draw.picnum]) < 3:
                undrawn_examples[draw.picnum].append(
                    f"{name} wall {draw.wall} (sector {draw.sector})")
        if (draw.next_sector >= 0 and draw.over_picnum
                and not draw.draws_over_picnum):
            usage[draw.over_picnum]["over_unread"] += 1
            band_totals["over_unread"] += 1
    for sprite in disk.sprites:
        f = sprite.fields
        align = int(f["cstat"]) & SPRITE_ALIGNMENT
        slot = {0: "sprite_face", 16: "sprite_wall",
                32: "sprite_floor"}.get(align, "sprite_other")
        usage[int(f["picnum"])][slot] += 1
        band_totals[slot] += 1


def diff_against_previous(usage: dict, previous: dict) -> dict:
    """How storage slots redistribute into rendered ones, for the report."""
    out = {}
    for picnum, counts in previous.get("usage", {}).items():
        mine = usage.get(int(picnum), {})
        stored_walls = counts.get("wall_one_sided", 0) + counts.get("wall_two_sided", 0)
        drawn_walls = sum(mine.get(s, 0) for s in RENDERED_WALL_SLOTS)
        if stored_walls or drawn_walls:
            out[picnum] = {
                "stored": {k: v for k, v in counts.items()
                           if k.startswith(("wall_", "over_"))},
                "rendered": {k: v for k, v in mine.items()
                             if k in RENDERED_WALL_SLOTS
                             or k in ("wall_undrawn", "over_unread")},
            }
    return out


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--art", default=str(ROOT / "reference" / "blood"))
    parser.add_argument("--population", default="blood-campaign")
    parser.add_argument("--no-knowledge", action="store_true",
                        help="write the report only")
    args = parser.parse_args(argv)

    sizes, masked = art_tables(args.art)
    previous = {}
    if PREVIOUS.exists():
        previous = json.loads(PREVIOUS.read_text(encoding="utf-8"))
    if not sizes and previous.get("tile_sizes"):
        sizes = {int(k): tuple(v) for k, v in previous["tile_sizes"].items()}

    usage: dict[int, Counter] = defaultdict(Counter)
    band_totals: Counter = Counter()
    undrawn_examples: dict[int, list[str]] = defaultdict(list)
    maps = 0
    for entry in list_corpus_maps(population=args.population):
        disk = read_map(entry.path)
        maps += 1
        mine_map(disk, usage, band_totals, undrawn_examples, entry.path.stem)
    if not maps:
        print("no maps in population", args.population)
        return 1

    masked_on_opaque = {
        str(p): {b: usage[p][b] for b in OPAQUE_BANDS if usage[p][b]}
        for p in sorted(masked) if any(usage[p][b] for b in OPAQUE_BANDS)}
    masked_in_middles = {
        str(p): {b: usage[p][b] for b in (MASKED_MIDDLE, ONEWAY_MIDDLE)
                 if usage[p][b]}
        for p in sorted(masked)
        if usage[p][MASKED_MIDDLE] or usage[p][ONEWAY_MIDDLE]}

    undrawn_ranked = sorted(
        ((p, c["wall_undrawn"]) for p, c in usage.items() if c["wall_undrawn"]),
        key=lambda kv: -kv[1])

    report = {
        "$schema": "llmapper.blood-usage-kinds-rendered", "schema_version": 2,
        "population": args.population, "maps": maps,
        "tiles_seen": len(usage),
        "slots": list(RENDERED_WALL_SLOTS) + [
            "floor", "ceiling", "floor_parallax", "ceiling_parallax",
            "sprite_face", "sprite_wall", "sprite_floor"],
        "not_slots": {
            "wall_undrawn": "walls whose authored picnum is drawn on no band "
                            "from either side (render_slots.undrawn_walls)",
            "over_unread": "two-sided walls carrying an over_picnum the "
                           "engine never reads (neither masked nor one-way)",
        },
        "band_totals": dict(sorted(band_totals.items())),
        "mask_law_rendered": {
            "statement": "a mask-coloured tile is never drawn on an opaque "
                         "band: one_sided_middle, two_sided_upper, "
                         "two_sided_lower",
            "opaque_band_slots": sum(band_totals[b] for b in OPAQUE_BANDS),
            "masked_tiles_on_opaque_bands": masked_on_opaque,
            "masked_tiles_in_middles": masked_in_middles,
            "art_read": bool(masked),
        },
        "undrawn_by_tile": [{"picnum": p, "walls": c,
                             "examples": undrawn_examples[p]}
                            for p, c in undrawn_ranked[:40]],
        "usage": {str(p): dict(sorted(c.items()))
                  for p, c in sorted(usage.items())},
        "tile_sizes": {str(p): list(s) for p, s in sorted(sizes.items())
                       if p in usage},
        "diff_against_v1": diff_against_previous(usage, previous),
    }
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    REPORT.write_text(json.dumps(report, indent=1) + "\n", encoding="utf-8",
                      newline="\n")
    print("maps", maps, "tiles", len(usage))
    print("band totals:", dict(sorted(band_totals.items())))
    print("masked tiles on opaque bands:", masked_on_opaque)
    print("undrawn walls, top tiles:", undrawn_ranked[:12])
    print("wrote", REPORT)

    if args.no_knowledge:
        return 0
    knowledge = {
        "$schema": "llmapper.blood-usage-kinds",
        "schema_version": 2,
        "grade": "DERIVED",
        "population": args.population,
        "maps": maps,
        "about": (
            "For every picnum, which RENDERED slots the campaign is attested "
            "to show it in and how often. A slot is a band the engine draws: "
            "one_sided_middle (picnum of a white wall), two_sided_upper and "
            "two_sided_lower (picnum on the ceiling / floor step of a red "
            "wall, the lower one swapped to the partner's picnum under "
            "cstat&2), masked_middle (over_picnum of a cstat&16 wall), "
            "oneway_middle (over_picnum of a cstat&32 wall), floor, ceiling, "
            "floor_parallax, ceiling_parallax, sprite_face, sprite_wall, "
            "sprite_floor. Two counts beside them are NOT slots: wall_undrawn "
            "(the authored picnum is on screen nowhere from either side) and "
            "over_unread (an over_picnum the engine never reads). v1 counted "
            "where a tile is STORED; this counts where it is SEEN, so a tile "
            "the campaign only ever stores on invisible walls has no rendered "
            "wall slot at all."),
        "how": (
            "bloodmap.render_slots over the campaign through the corpus "
            "registry, plus the ART for tile sizes and mask ratios. "
            "tools/mine_usage_kinds.py; reports/blood-usage-kinds-rendered.json "
            "carries the full mine and the diff against v1."),
        "engine": (
            "NBlood/source/build/src/engine.cpp:4686 (masked deferral), "
            ":4688-4724 (upper step), :4799-4836 (lower step and the cstat&2 "
            "swap), :4938-4940 (white and one-way walls), :7217-7231 (masked "
            "middle); mirrors.cpp:37,466-469 (the mirror tile bypass)"),
        "sky_family": previous.get("sky_family", {"tiles": [2500, 3491, 3678]}),
        "mask_law_rendered": report["mask_law_rendered"],
        "band_totals": report["band_totals"],
        "usage": report["usage"],
        "tile_sizes": report["tile_sizes"],
    }
    KNOWLEDGE.write_text(json.dumps(knowledge, indent=1) + "\n",
                         encoding="utf-8", newline="\n")
    print("wrote", KNOWLEDGE, f"({KNOWLEDGE.stat().st_size // 1024} KB)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
