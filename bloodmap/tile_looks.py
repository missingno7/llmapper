"""What a tile shows and whose word that is: the library's readings and the owner's names, for code that must ask.

The readings are `knowledge/blood/design/tile-looks/part-*.json` (written by
`python -m tools.catalog look`), the names `owner-anchors-v1.json` (the owner's
tile sheet). The owner's name outranks a reading wherever both exist. A pass
that must know which tiles are words, or which are paper, asks here instead of
keeping a list of numbers.
"""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DESIGN = ROOT / "knowledge" / "blood" / "design"
LOOKS = DESIGN / "tile-looks"
USAGE = DESIGN / "tile-usage-v1.json"


def tile_looks() -> dict[int, dict]:
    """Every tile the library has read: its class, layout, what it depicts, its themes and tags."""
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


@lru_cache(maxsize=1)
def word_tiles() -> frozenset[int]:
    """Every tile the library reads as words: signs, boards, letters, and any bill tagged as carrying text.

    What a blind reader must not be shown when asked to name a place from its
    shapes (`tools.critique`, `tools.showcase`).
    """
    return frozenset(tile for tile, row in tile_looks().items()
                     if row.get("class") in ("sign", "letter") or "text" in row.get("tags", ()))


@lru_cache(maxsize=1)
def hung_tiles() -> frozenset[int]:
    """Tiles that are a picture of something HUNG: paper, boards, signs.

    The owner, 2026-11-19: "not all wall sprites will be on the wall and
    it doesn't mean it is wrong ... Two sided wall sprite can be used for
    balcony railing for example." A railing, a gate, a curtain, a cobweb,
    a flag stand free by nature. A poster, a notice, a newspaper page or a
    name board does not: with air behind it, it is a mistake. The library
    says which is which: its `sign` class, and anything tagged `paper`.
    """
    return frozenset(tile for tile, row in tile_looks().items()
                     if row.get("class") == "sign" or "paper" in row.get("tags", ()))


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
