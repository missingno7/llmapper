"""Three censuses the writer's table needs before it changes anything.

Decisions section 30 assigns them, each from a question E3M1 raised alone and
one map cannot answer:

* **28b, end-wall tiles by join pair.** `TILE_CLASSES["facade stone"]` is 400
  and E3M1's three road|end_wall records all wear 414. One map is one level's
  choice; 43 maps are the class.
* **28d, u-continuity by BEND CLASS.** E3M1 continues a material on 88% of
  collinear solid-solid joins and 15-51% of bends, so a surface there is a
  flat face rather than a run. `RUN_BREAK_DEGREES` is 100, which carries a run
  through every bend. Whether that is E3M1 or Blood is a census question.
* **28e, interior|interior pairs.** 1122 of E3M1's 1386 two-sided records are
  interior meeting interior and the join table has no row for any of them.
  Classing them by what the two floors and the two ceilings DO says how many
  rows an indoor grammar would need. **Rows are proposed here and never
  added**: `joins.ROWS` is the writer's.

Every function takes a decompiled level and returns facts about that level;
the corpus-wide aggregates are sums over those, so a census is reproducible
one map at a time and no map's numbers depend on the order they were read in.

Section 22a is binding on what comes out: a norm is conditioned on a context
(join pair, bend class, floor/ceiling kind), never a global average, and each
row carries the cases where Blood did NOT do the thing.
"""

from __future__ import annotations

from collections import Counter, defaultdict
from typing import Any, Iterable, Sequence

from .joins import TILE_CLASSES
from .read_joins import INTERIOR, adjacency, surface_kinds
from .texture_frame import (
    _fields, join_class, join_continues, sector_index, wall_visible,
)

#: The join pairs 28b is about: a street meeting a termination.
END_WALL_PAIRS = ("road|end_wall", "pavement|end_wall")


def _face(item: Any) -> Any:
    return item["fields"] if isinstance(item, dict) else item.fields


def _extra(item: Any) -> dict[str, Any] | None:
    extra = item["blood"] if isinstance(item, dict) else getattr(item, "extra", None)
    if extra is None:
        return None
    return dict(extra["fields"] if isinstance(extra, dict) else extra.fields)


def _spread(values: Sequence[float]) -> dict[str, Any]:
    if not values:
        return {"n": 0}
    ordered = sorted(values)
    def at(fraction: float) -> float:
        return ordered[min(len(ordered) - 1, int(fraction * len(ordered)))]
    return {"n": len(ordered), "min": ordered[0], "q1": at(0.25),
            "median": at(0.5), "q3": at(0.75), "max": ordered[-1]}


# ---------------------------------------------------------------------------
# 28b: what an end wall wears, by join pair
# ---------------------------------------------------------------------------

def end_wall_tiles(level: Any, kinds: dict[int, str] | None = None, *,
                   owners: Sequence[int] | None = None) -> dict[str, Any]:
    """For every record where ground meets a termination, what the band wears.

    The band is on the GROUND's record -- the side a body sees from the street
    -- which is the correction the whole street model was built on, so that is
    the record read. Blocking is reported beside the tile because the row
    claims both.
    """
    owners = list(owners) if owners is not None else sector_index(level)
    if kinds is None:
        kinds = surface_kinds(level, owners=owners)["kinds"]
    tiles: dict[str, Counter] = defaultdict(Counter)
    blocking: dict[str, Counter] = defaultdict(Counter)
    records: dict[str, list[int]] = defaultdict(list)
    #: How far the termination stands above the ground, split by whether the
    #: record blocks. Section 22a: a norm is conditioned, and "does an end
    #: wall block" is conditioned on how high it is -- a mass six player
    #: heights up needs no blocking bit, because gravity is the gate.
    steps: dict[str, dict[int, list[int]]] = defaultdict(
        lambda: {0: [], 1: []})
    for wall_id, wall in enumerate(level.walls):
        face = _face(wall)
        other = int(face["next_sector"])
        if other < 0:
            continue
        here = owners[wall_id]
        a, b = kinds.get(here), kinds.get(other)
        if b != "end_wall" or a not in ("road", "pavement"):
            continue
        #: The band only exists where the far side stands ABOVE this one;
        #: Blood's z grows downward.
        if int(_face(level.sectors[other])["floor_z"]) >= int(
                _face(level.sectors[here])["floor_z"]):
            continue
        key = f"{a}|end_wall"
        blocks = int(face["cstat"]) & 1
        tiles[key][int(face["picnum"])] += 1
        blocking[key][blocks] += 1
        records[key].append(wall_id)
        steps[key][blocks].append(
            int(_face(level.sectors[here])["floor_z"])
            - int(_face(level.sectors[other])["floor_z"]))
    return {
        "tiles": {key: dict(sorted(value.items()))
                  for key, value in sorted(tiles.items())},
        "blocking": {key: dict(sorted(value.items()))
                     for key, value in sorted(blocking.items())},
        "records": {key: sorted(value) for key, value in sorted(records.items())},
        "step_by_blocking": {
            key: {"blocking": _spread(value[1]),
                  "not blocking": _spread(value[0])}
            for key, value in sorted(steps.items())},
        #: The raw steps, so a corpus aggregate is the real distribution
        #: rather than a distribution of medians.
        "step_values": {key: {"blocking": list(value[1]),
                              "not blocking": list(value[0])}
                        for key, value in sorted(steps.items())},
        "total": sum(sum(value.values()) for value in tiles.values()),
    }


# ---------------------------------------------------------------------------
# 28d: where a material stops, by bend class
# ---------------------------------------------------------------------------

def u_continuity(level: Any, art_sizes: dict[int, tuple[int, int]], *,
                 owners: Sequence[int] | None = None) -> dict[str, Any]:
    """Same-tile joins by bend class, and whether u continues across each.

    `texture_frame.continuity_rows` measures this already and its classes are
    `"<collinear|bend|reflex> <solid-solid|solid-portal|portal-portal>"`. What
    is added here is the ANGLE beside the class, so the census can say where
    the campaign actually stops rather than only that it stopped -- a bend of
    12 degrees and one of 89 are the same class and not the same decision.
    """
    owners = list(owners) if owners is not None else sector_index(level)
    rows: dict[str, dict[str, Any]] = {}
    angles: dict[str, list[float]] = defaultdict(list)
    broke_at: list[float] = []
    kept_at: list[float] = []
    from .texture_frame import join_turn

    for sector in level.sectors:
        fields = _face(sector)
        start = int(fields["wall_ptr"])
        count = int(fields["wall_count"])
        for index in range(start, start + count):
            here = _fields(level.walls[index])
            nxt = int(here["point2"])
            if not (start <= nxt < start + count) or nxt == index:
                continue
            tile = int(here["picnum"])
            if tile != int(_fields(level.walls[nxt])["picnum"]):
                continue
            size = art_sizes.get(tile)
            if not size or not size[0] or not size[1]:
                continue
            name = join_class(level, index, nxt)
            turn = round(join_turn(level, index, nxt), 1)
            x_ok, _ = join_continues(level, index, nxt, size, owners)
            row = rows.setdefault(name, {"n": 0, "u_continues": 0})
            row["n"] += 1
            row["u_continues"] += int(x_ok)
            angles[name].append(turn)
            (kept_at if x_ok else broke_at).append(turn)
    for name, row in rows.items():
        row["percent"] = round(100.0 * row["u_continues"] / row["n"], 1)
        row["turn_degrees"] = _spread(angles[name])
    return {
        "by_class": dict(sorted(rows.items())),
        "turn_where_u_continues": _spread(kept_at),
        "turn_where_it_breaks": _spread(broke_at),
        "joins": sum(row["n"] for row in rows.values()),
        "continues": sum(row["u_continues"] for row in rows.values()),
    }


# ---------------------------------------------------------------------------
# 28e: what an interior meeting an interior actually is
# ---------------------------------------------------------------------------

#: How a floor or a ceiling relates across a shared record. These are the
#: axes an indoor join row would be keyed on, and they are read from what a
#: body and the renderer see, never from a tile.
def _relation(here: int, there: int, step: int) -> str:
    delta = there - here
    if delta == 0:
        return "level"
    if abs(delta) <= step:
        return "a step up" if delta < 0 else "a step down"
    return "far above" if delta < 0 else "far below"


AUTOSTEP = 4096


def interior_pairs(level: Any, kinds: dict[int, str] | None = None, *,
                   owners: Sequence[int] | None = None) -> dict[str, Any]:
    """Every interior|interior shared record, classed by what the two
    surfaces do -- floor relation, ceiling relation, and whether the record
    draws at all.

    The classes are the row keys an indoor grammar would need. **Nothing is
    added to `joins.ROWS`**: the census proposes and the writer decides, which
    is the rule the outdoor table was built under and the reason it can be
    trusted.
    """
    owners = list(owners) if owners is not None else sector_index(level)
    if kinds is None:
        kinds = surface_kinds(level, owners=owners)["kinds"]
    classes: Counter = Counter()
    drawn: dict[str, Counter] = defaultdict(Counter)
    tiles: dict[str, Counter] = defaultdict(Counter)
    typed: dict[str, Counter] = defaultdict(Counter)
    for wall_id, wall in enumerate(level.walls):
        face = _face(wall)
        other = int(face["next_sector"])
        if other < 0:
            continue
        here = owners[wall_id]
        if kinds.get(here) != INTERIOR or kinds.get(other) != INTERIOR:
            continue
        a, b = _face(level.sectors[here]), _face(level.sectors[other])
        floor = _relation(int(a["floor_z"]), int(b["floor_z"]), AUTOSTEP)
        ceiling = _relation(int(a["ceiling_z"]), int(b["ceiling_z"]), AUTOSTEP)
        key = f"floor {floor} | ceiling {ceiling}"
        classes[key] += 1
        visible = wall_visible(level, wall_id, owners)
        drawn[key]["draws" if visible else "draws nothing"] += 1
        if visible:
            tiles[key][int(face["picnum"])] += 1
        #: A mechanism on either side is why a pair exists at all, often
        #: enough that it belongs in the class rather than under it.
        moves = bool(int(a["type"]) or int(b["type"]))
        typed[key]["a mechanism on one side" if moves else "both at rest"] += 1
    return {
        "classes": dict(classes.most_common()),
        "draws": {key: dict(value) for key, value in sorted(drawn.items())},
        "top_tiles": {key: dict(value.most_common(4))
                      for key, value in sorted(tiles.items())},
        "mechanisms": {key: dict(value) for key, value in sorted(typed.items())},
        "records": sum(classes.values()),
    }


# ---------------------------------------------------------------------------
# the corpus-wide aggregates
# ---------------------------------------------------------------------------

def _merge_counter(into: dict[str, Counter], rows: dict[str, dict]) -> None:
    for key, value in rows.items():
        into[key].update({int(k) if str(k).lstrip("-").isdigit() else k: v
                          for k, v in value.items()})


def census(levels: Iterable[Any], *, names: Sequence[str] = (),
           art_sizes: dict[int, tuple[int, int]] | None = None
           ) -> dict[str, Any]:
    """All three censuses over a population, per map and summed.

    Per map as well as summed on purpose: a class that only one map has is a
    different fact from one every map has, and a total hides which.
    """
    if art_sizes is None:
        from .texture_align import wall_art_sizes

        art_sizes = wall_art_sizes()
    end_tiles: dict[str, Counter] = defaultdict(Counter)
    end_block: dict[str, Counter] = defaultdict(Counter)
    end_step: dict[str, dict[str, list[int]]] = defaultdict(
        lambda: {"blocking": [], "not blocking": []})
    end_maps: dict[str, set] = defaultdict(set)
    bend: dict[str, dict[str, int]] = {}
    bend_maps: dict[str, set] = defaultdict(set)
    inside: Counter = Counter()
    inside_draws: dict[str, Counter] = defaultdict(Counter)
    inside_maps: dict[str, set] = defaultdict(set)
    per_map: dict[str, Any] = {}

    for index, level in enumerate(levels):
        name = names[index] if index < len(names) else f"map:{index}"
        owners = sector_index(level)
        kinds = surface_kinds(level, owners=owners)["kinds"]
        walls = end_wall_tiles(level, kinds, owners=owners)
        bends = u_continuity(level, art_sizes, owners=owners)
        pairs = interior_pairs(level, kinds, owners=owners)
        per_map[name] = {"end_wall": walls, "u_continuity": bends,
                         "interior_pairs": pairs}
        _merge_counter(end_tiles, walls["tiles"])
        _merge_counter(end_block, walls["blocking"])
        for key in walls["tiles"]:
            end_maps[key].add(name)
        for key, value in walls["step_values"].items():
            for state, numbers in value.items():
                end_step[key][state].extend(numbers)
        for key, row in bends["by_class"].items():
            into = bend.setdefault(key, {"n": 0, "u_continues": 0})
            into["n"] += row["n"]
            into["u_continues"] += row["u_continues"]
            bend_maps[key].add(name)
        for key, count in pairs["classes"].items():
            inside[key] += count
            inside_maps[key].add(name)
        for key, row in pairs["draws"].items():
            inside_draws[key].update(row)

    for key, row in bend.items():
        row["percent"] = round(100.0 * row["u_continues"] / row["n"], 1) if row["n"] else 0.0
        row["maps"] = len(bend_maps[key])
    return {
        "maps": len(per_map),
        "end_wall_tiles": {
            "tiles": {key: dict(sorted(value.items(), key=lambda r: -r[1]))
                      for key, value in sorted(end_tiles.items())},
            "blocking": {key: dict(sorted(value.items()))
                         for key, value in sorted(end_block.items())},
            "maps_with_the_pair": {key: len(value)
                                   for key, value in sorted(end_maps.items())},
            "step_by_blocking": {
                key: {state: _spread(values)
                      for state, values in sorted(value.items())}
                for key, value in sorted(end_step.items())},
            "the_writers_class": {"facade stone": TILE_CLASSES["facade stone"]},
        },
        "u_continuity": dict(sorted(bend.items())),
        "interior_pairs": {
            "classes": dict(inside.most_common()),
            "maps_with_the_class": {key: len(value)
                                    for key, value in sorted(inside_maps.items())},
            "draws": {key: dict(value) for key, value in sorted(inside_draws.items())},
        },
        "per_map": per_map,
    }


def proposed_indoor_rows(summary: dict[str, Any], *,
                         floor_share: float = 0.02) -> list[dict[str, Any]]:
    """The rows an indoor grammar would need, PROPOSED and never added.

    A class earns a proposal when it holds at least `floor_share` of the
    interior records AND appears in more than one map: one map's habit is not
    a row, and neither is a class that exists twice in the corpus.
    """
    classes = summary["interior_pairs"]["classes"]
    maps = summary["interior_pairs"]["maps_with_the_class"]
    draws = summary["interior_pairs"]["draws"]
    total = sum(classes.values()) or 1
    out = []
    for key, count in classes.items():
        share = count / total
        if share < floor_share or maps.get(key, 0) < 2:
            continue
        shown = draws.get(key, {})
        out.append({
            "proposed_row": key,
            "records": count,
            "share": round(share, 4),
            "maps": maps.get(key, 0),
            "draws": shown,
            "note": ("a row nobody has described; proposed only. "
                     f"{shown.get('draws nothing', 0)} of {count} of its "
                     f"records draw no band, which is what a 'nothing' row "
                     f"would say"),
        })
    return out
