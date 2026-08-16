"""Visual style vocabulary extracted from a Blood map.

A style reference is not a geometry oracle.  DWE2M3 and E2L1 share a space-station
mood but not sector shapes; unique correspondences are zero.  Conversion therefore
keeps Duke topology and borrows Blood-native surface, palette, shade, visibility,
and sky evidence from the reference map.
"""

from __future__ import annotations

from collections import Counter, defaultdict
from statistics import mean, median
from typing import Any

from .format import read_map
from .model import DiskMap


def _modal(counts: Counter[int]) -> tuple[int, int] | None:
    if not counts:
        return None
    value, amount = counts.most_common(1)[0]
    return int(value), int(amount)


def _shade_summary(values: list[int]) -> dict[str, float | int]:
    ordinary = [value for value in values if value > -100]
    if not ordinary:
        ordinary = list(values)
    return {
        "min": min(ordinary),
        "max": max(ordinary),
        "mean": round(mean(ordinary), 3),
        "median": int(median(ordinary)),
        "samples": len(ordinary),
    }


def extract_visual_style(disk: DiskMap, *, source: str | None = None) -> dict[str, Any]:
    """Measure the Blood-native look of one map, split by surface role.

    Palettes and shades are recorded per tile so conversion can reuse the same
    tile+pal+shade bundles the reference actually authored, not just tile IDs.
    """
    surfaces: dict[str, dict[int, dict[str, Counter[int]]]] = {
        "ceiling": defaultdict(lambda: {"pal": Counter(), "shade": Counter()}),
        "floor": defaultdict(lambda: {"pal": Counter(), "shade": Counter()}),
        "wall": defaultdict(lambda: {"pal": Counter(), "shade": Counter()}),
        "sky": defaultdict(lambda: {"pal": Counter(), "shade": Counter()}),
    }
    counts: dict[str, Counter[int]] = {role: Counter() for role in surfaces}

    for sector in disk.sectors:
        sky = bool(sector.ceiling_stat & 1)
        ceiling_role = "sky" if sky else "ceiling"
        counts[ceiling_role][sector.ceiling_picnum] += 1
        surfaces[ceiling_role][sector.ceiling_picnum]["pal"][sector.ceiling_pal] += 1
        surfaces[ceiling_role][sector.ceiling_picnum]["shade"][sector.ceiling_shade] += 1
        counts["floor"][sector.floor_picnum] += 1
        surfaces["floor"][sector.floor_picnum]["pal"][sector.floor_pal] += 1
        surfaces["floor"][sector.floor_picnum]["shade"][sector.floor_shade] += 1

    for wall in disk.walls:
        counts["wall"][wall.picnum] += 1
        surfaces["wall"][wall.picnum]["pal"][wall.pal] += 1
        surfaces["wall"][wall.picnum]["shade"][wall.shade] += 1
        if wall.over_picnum:
            counts["wall"][wall.over_picnum] += 1
            surfaces["wall"][wall.over_picnum]["pal"][wall.pal] += 1
            surfaces["wall"][wall.over_picnum]["shade"][wall.shade] += 1

    usage: dict[str, dict[str, dict[str, int]]] = {}
    for role, tiles in surfaces.items():
        usage[role] = {}
        for tile, channels in tiles.items():
            pal = _modal(channels["pal"])
            shade = _modal(channels["shade"])
            if pal is None or shade is None:
                continue
            usage[role][str(tile)] = {
                "count": int(counts[role][tile]),
                "pal": pal[0],
                "pal_support": pal[1],
                "shade": shade[0],
                "shade_support": shade[1],
            }

    header = disk.header
    return {
        "$schema": "llmapper.visual-style",
        "schema_version": 1,
        "source": source,
        "classification": "style-reference-vocabulary",
        "header": {
            "visibility": int(header["visibility"]),
            "sky_bits": int(header["sky_bits"]),
            "sky_type": int(header["sky_type"]),
            "sky_offsets": [int(value) for value in disk.sky_offsets],
        },
        "candidates": {
            role: {tile: count for tile, count in role_counts.items() if 0 < tile < 4096}
            for role, role_counts in counts.items()
        },
        "surface": usage,
        "shades": {
            "ceiling": _shade_summary([sector.ceiling_shade for sector in disk.sectors if not (sector.ceiling_stat & 1)]),
            "floor": _shade_summary([sector.floor_shade for sector in disk.sectors]),
            "wall": _shade_summary([wall.shade for wall in disk.walls]),
        },
        "parallax_ceilings": int(sum(1 for sector in disk.sectors if sector.ceiling_stat & 1)),
    }


def load_visual_style(path: str) -> dict[str, Any]:
    return extract_visual_style(read_map(path), source=str(path))


def style_candidate_tiles(style: dict[str, Any], role: str) -> set[int]:
    return {int(tile) for tile in style["candidates"].get(role, {})}


def style_tile_usage(style: dict[str, Any], role: str, tile: int) -> dict[str, int] | None:
    return style.get("surface", {}).get(role, {}).get(str(int(tile)))


def corpus_parallax_tiles(blood_maps) -> dict[int, int]:
    """Tiles Blood authors actually used as parallax ceilings, with frequencies."""
    counts: Counter[int] = Counter()
    paths = sorted({path.resolve() for path in blood_maps.glob("*.MAP")} | {path.resolve() for path in blood_maps.glob("*.map")})
    for path in paths:
        disk = read_map(path)
        for sector in disk.sectors:
            if sector.ceiling_stat & 1 and 0 < sector.ceiling_picnum < 4096:
                counts[sector.ceiling_picnum] += 1
    return dict(counts)
