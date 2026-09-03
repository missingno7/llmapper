"""The reader half of the join grammar: what kind of join is every shared wall?

`joins.py` is the writer -- a table keyed by (surface kind A, surface kind B,
height relation) that says what each side's record shows. This is the inverse
half the symmetry rule asks for (decisions section 20): read an original map's
surface kinds off its geometry, classify every two-sided record, and count the
table against it. **No row is added here.** A pair with no row is reported,
with its records, which is the whole point of the census.

Reading a surface's kind
========================

`joins.py` says it plainly: "surface kind is not readable from a tile". So
none of the rules below look at one. They look at what a body can do and at
what the engine draws:

* **solid** -- `floor_z == ceiling_z`. A sector with no clear height is a
  MASS: `wallVisible` (`xmpmaped.cpp:1500-1525`) draws nothing inside it and
  no body stands in it. E3M1 has 21, and two of them (s10, s11) are the
  sectors the writer's table cites as a "pavement-only path".
* **horizon** -- floor AND ceiling parallax (`joins.HORIZON_TILE`'s law, read
  as the stat bits rather than as tile 3678).
* **sea** -- `joins.is_water`: a floor palette in `WATER_PALETTES` or any
  panning or drag. Water is a palette and a behaviour, never a tile.
* the **street network** -- the largest-area connected component of outdoor
  walkable sectors (parallax ceiling, non-zero clear height). Inside it:
  * **road** -- the base plane: the level the islands step up from;
  * **pavement** -- a sector standing exactly the modal step above a road
    neighbour. The step is MEASURED off the map, not assumed to be 2048;
  * **end_wall** -- an outdoor sector standing more than Blood's 4096
    autostep above every neighbour it has. Nobody can step onto it, so its
    floor is a wall top rather than ground. This is the criterion, and it
    needs no tile: E3M1's 379 falls out of it rather than into it.
* **interior** -- walkable with a ceiling that is not parallax.

`interior`, `solid` and `outdoor_ground` are READER kinds. They are not rows
in the writer's table and are not proposed as any: they exist so that a pair
involving them can be named in the residue instead of vanishing from the
denominator.
"""

from __future__ import annotations

from collections import Counter, defaultdict, deque
from typing import Any, Iterable, Sequence

from . import joins
from .joins import (
    B_ABOVE, END_WALL, EQUAL, HORIZON, JoinError, PAVEMENT, ROAD, SEA, SHORE,
    TILE_CLASSES, height_relation, rule,
)
from .texture_frame import sector_index

#: Reader-only kinds. The writer's table has no rows for these and none are
#: proposed: they name what a pair is so the residue can be read.
SOLID = "solid"
INTERIOR = "interior"
OUTDOOR_GROUND = "outdoor_ground"
WATER = "water"
#: A raised outdoor mass that carries a SECTOR TYPE is not a termination: it
#: is a mechanism, and what the reader sees is its rest state (decisions
#: section 30, item 28c). Naming it apart is what lets the end-wall row keep
#: its blocking clause on the records that stay put -- E3M1's four
#: non-blocking pavement|end_wall records all face sectors 172 and 174, which
#: carry type 600 and move.
MECHANISM_AT_REST = "mechanism_at_rest"
#: A raised outdoor mass that HOLDS ROOMS is a building, not a termination
#: (decisions section 31, item 32c). `end_wall` is defined as "an outdoor mass
#: no body can step onto", and the city's 126 `end_wall|interior` records were
#: that definition meeting a room behind it -- a contradiction the grammar had
#: no word for. Two clauses decide it, and the roof one is RELATIONAL rather
#: than a tile constant: the mass's top must wear a tile that one of the rooms
#: it opens onto wears as its CEILING. That is what a roof IS -- the same
#: surface seen from above and from below -- and it is why Gravesend's nine
#: buildings read as facades while E1M2's raised mass, whose top is 49 and
#: whose three rooms are ceilinged 68, stays a termination.
FACADE = "facade"
#: The threshold between the street and a room: a sector at the PAVEMENT'S OWN
#: z with a pavement on one side and a room on the other. It is neither -- it
#: is roofed like the room and level with the street -- and calling it an
#: interior put 36 of the city's records into `pavement|interior` and
#: `interior|interior`, which say nothing about a way in.
OPENING = "opening"

#: `Blood`'s step-up limit. A body climbs 4096 without jumping, so an outdoor
#: floor more than that above every neighbour is not ground -- it is a top.
AUTOSTEP = 4096


class KindReadError(ValueError):
    """The map's surface kinds cannot be read with the evidence available."""


def _face(item: Any) -> Any:
    return item["fields"] if isinstance(item, dict) else item.fields


def _extra(item: Any) -> dict[str, Any] | None:
    """The Blood extra of a sector, wall or sprite, however it is carried.

    `assembly._x`'s accessor, repeated here because `joins.is_water` does not
    have it: it reads `getattr(sector, "extra", None)`, which is `None` for
    every `LevelIR` sector (they carry the extra under the key `"blood"`), so
    its panning clause never runs on a decompiled level and only its palette
    clause does. On DWE3M10 -- the map the shore and sea rows were mined from
    -- that loses 4 of its 22 panning sectors (393-396, palette 0). Reported,
    not patched: `joins.py` is the writer.
    """
    extra = item["blood"] if isinstance(item, dict) else getattr(item, "extra", None)
    if extra is None:
        return None
    return extra["fields"] if isinstance(extra, dict) else extra.fields


def reads_as_water(sector: Any) -> bool:
    """`joins.is_water`'s own two clauses, with an accessor that can see both."""
    fields = _face(sector)
    extra = _extra(sector) or {}
    panning = any(int(extra.get(name, 0)) for name in
                  ("pan_floor", "pan_always", "pan_velocity", "drag"))
    return panning or int(fields.get("floor_pal", 0)) in joins.WATER_PALETTES


def _area(level: Any, sector_id: int) -> float:
    from .viewplan import sector_area

    return float(sector_area(level, sector_id))


def adjacency(level: Any, owners: Sequence[int] | None = None
              ) -> dict[int, set[int]]:
    owners = list(owners) if owners is not None else sector_index(level)
    out: dict[int, set[int]] = defaultdict(set)
    for wall_id, wall in enumerate(level.walls):
        other = int(_face(wall)["next_sector"])
        if other >= 0:
            out[owners[wall_id]].add(other)
            out[other].add(owners[wall_id])
    return out


def _component(seeds: Iterable[int], members: set[int],
               graph: dict[int, set[int]]) -> set[int]:
    seen = {seed for seed in seeds if seed in members}
    queue = deque(seen)
    while queue:
        current = queue.popleft()
        for other in graph.get(current, ()):
            if other in members and other not in seen:
                seen.add(other)
                queue.append(other)
    return seen


def street_network(level: Any, graph: dict[int, set[int]]) -> tuple[set[int], list[dict]]:
    """The largest-area connected run of outdoor walkable ground.

    Largest by AREA rather than by sector count: E3M1's roofs are several
    small sky sectors each, and counting sectors would elect a roof.
    """
    outdoor = {index for index, sector in enumerate(level.sectors)
               if int(_face(sector)["ceiling_stat"]) & 1
               and int(_face(sector)["floor_z"]) != int(_face(sector)["ceiling_z"])}
    components: list[set[int]] = []
    left = set(outdoor)
    while left:
        seed = min(left)
        found = _component([seed], outdoor, graph)
        components.append(found)
        left -= found
    scored = [{"sectors": sorted(item),
               "area": round(sum(_area(level, index) for index in item), 1)}
              for item in components]
    scored.sort(key=lambda row: -row["area"])
    return (set(scored[0]["sectors"]) if scored else set()), scored


def measured_rise(level: Any, network: set[int], graph: dict[int, set[int]]
                  ) -> tuple[int, dict[int, int]]:
    """The step the network's islands stand on, counted off the map.

    Every floor step inside the network is tallied; the modal one is the rise.
    `HeightIsland.rise` defaults to 2048 because E3M1 does; this reads it back
    rather than agreeing with itself.
    """
    steps = Counter()
    for here in sorted(network):
        for there in sorted(graph.get(here, ())):
            if there <= here or there not in network:
                continue
            delta = abs(int(_face(level.sectors[here])["floor_z"])
                        - int(_face(level.sectors[there])["floor_z"]))
            if delta:
                steps[delta] += 1
    if not steps:
        return 0, {}
    walkable = {delta: count for delta, count in steps.items()
                if delta <= AUTOSTEP}
    source = walkable or dict(steps)
    rise = max(source, key=lambda key: (source[key], -key))
    return int(rise), {int(k): int(v) for k, v in sorted(steps.items())}


def surface_kinds(level: Any, *, owners: Sequence[int] | None = None
                  ) -> dict[str, Any]:
    """Every sector's surface kind, with the measurement that decided it."""
    owners = list(owners) if owners is not None else sector_index(level)
    graph = adjacency(level, owners)
    kinds: dict[int, str] = {}
    why: dict[int, str] = {}

    def name(sector_id: int, kind: str, reason: str) -> None:
        kinds[sector_id] = kind
        why[sector_id] = reason

    for index, sector in enumerate(level.sectors):
        fields = _face(sector)
        if int(fields["floor_z"]) == int(fields["ceiling_z"]):
            name(index, SOLID, "floor_z == ceiling_z: no clear height, so "
                               "nothing draws inside and no body stands in it")
        elif int(fields["floor_stat"]) & 1 and int(fields["ceiling_stat"]) & 1:
            name(index, HORIZON, "floor and ceiling both parallax")
        elif reads_as_water(sector):
            name(index, WATER, "joins.is_water's own test -- a water palette, "
                               "or panning or drag on the floor -- with an "
                               "accessor that can see a LevelIR's extra")

    network, components = street_network(level, graph)
    rise, steps = measured_rise(level, network, graph)

    #: The base plane is the LOWEST ground -- Blood's z grows downward, so the
    #: base has the GREATEST floor_z -- among the levels that carry real area.
    #: The area floor is what stops a one-sector pit from electing itself.
    #: WATER, A HORIZON AND A SOLID ARE ALREADY NAMED, and they do not vote.
    #: A city with a sea on its south edge has more water than street -- 41
    #: sectors and 1.2 billion square units of it in Gravesend -- so a base
    #: plane elected by area put the SEA at the bottom of the street network,
    #: called it the road, and left every pavement and every carriageway
    #: unnamed. Both the naming below and the election have to respect what
    #: the first pass already decided.
    by_level: dict[int, float] = defaultdict(float)
    for index in sorted(network):
        if index in kinds:
            continue
        by_level[int(_face(level.sectors[index])["floor_z"])] += _area(level, index)
    total_area = sum(by_level.values())
    significant = [z for z, area in by_level.items()
                   if total_area and area >= 0.05 * total_area]
    base_z = max(significant) if significant else (
        max(by_level) if by_level else None)

    raised: list[int] = []
    for index in sorted(network):
        if index in kinds:
            continue
        here = int(_face(level.sectors[index])["floor_z"])
        if base_z is not None and here == base_z:
            name(index, ROAD, f"outdoor ground at the network's base plane "
                              f"z={base_z}, the level its islands stand on")
        elif base_z is not None and rise and here == base_z - rise:
            name(index, PAVEMENT,
                 f"outdoor ground exactly the measured rise ({rise}) above "
                 f"the base plane")
        else:
            raised.append(index)

    #: END WALLS ARE MASSES, NOT SECTORS. E3M1's wall tops are cut into
    #: several sectors that abut one another at the SAME z, so a per-sector
    #: test ("higher than every neighbour") passes on the ends of a mass and
    #: fails in its middle: applied sector by sector it finds 3 of E3M1's 8.
    #: The test belongs to the connected GROUP: nobody can step onto any part
    #: of it from outside it.
    pending = set(raised)
    while pending:
        group = _component([min(pending)], pending, graph)
        pending -= group
        edges = [(member, other) for member in sorted(group)
                 for other in sorted(graph.get(member, ()))
                 if other not in group and kinds.get(other) != SOLID
                 and other in network]
        climbable = [(member, other) for member, other in edges
                     if int(_face(level.sectors[other])["floor_z"])
                     - int(_face(level.sectors[member])["floor_z"]) <= AUTOSTEP]
        #: A mass MOVES if any of its sectors carries a type. It is then a
        #: mechanism at rest, whole, rather than a mass some of whose sectors
        #: happen to be typed: a door leaf and the frame it is cut from are
        #: one thing, and splitting them by which sector holds the type would
        #: put half a door in each kind.
        moves = sorted(member for member in group
                       if int(_face(level.sectors[member])["type"]))
        for member in sorted(group):
            here = int(_face(level.sectors[member])["floor_z"])
            if edges and not climbable and moves:
                types = sorted({int(_face(level.sectors[index])["type"])
                                for index in moves})
                name(member, MECHANISM_AT_REST,
                     f"outdoor, in a mass of {len(group)} sector(s) no body "
                     f"can step onto, but sector(s) {moves} carry type "
                     f"{types}: this is its REST state, and layer 5 owns what "
                     f"it does. Not a termination")
            elif edges and not climbable:
                name(member, END_WALL,
                     f"outdoor, in a mass of {len(group)} sector(s) that no "
                     f"body can step onto: every one of its {len(edges)} "
                     f"edges to the network rises more than the {AUTOSTEP} "
                     f"autostep")
            else:
                name(member, OUTDOOR_GROUND,
                     f"outdoor ground at z={here}, neither the base plane nor "
                     f"one measured rise ({rise}) above it, and reachable")

    #: A shore is ground that meets water at its own level.
    for index in sorted(network):
        if kinds.get(index) not in (ROAD, PAVEMENT, OUTDOOR_GROUND):
            continue
        for other in graph.get(index, ()):
            if kinds.get(other) == WATER and (
                    int(_face(level.sectors[index])["floor_z"])
                    == int(_face(level.sectors[other])["floor_z"])):
                name(index, SHORE, "ground meeting water at its own z")
                break

    for index in range(len(level.sectors)):
        if index not in kinds:
            name(index, INTERIOR,
                 "walkable with a ceiling that is not parallax")

    #: OPENINGS BEFORE FACADES, because the mouth a facade needs is usually
    #: the opening. A facade whose only room has just been renamed would
    #: otherwise stop being a facade, which is the wrong way round: the
    #: opening is the evidence FOR the building, not against it.
    for index in sorted(kinds):
        if kinds[index] != INTERIOR:
            continue
        here = int(_face(level.sectors[index])["floor_z"])
        level_pavements = [other for other in sorted(graph.get(index, ()))
                           if kinds.get(other) == PAVEMENT
                           and int(_face(level.sectors[other])["floor_z"])
                           == here]
        rooms = [other for other in sorted(graph.get(index, ()))
                 if kinds.get(other) == INTERIOR and other != index]
        if level_pavements and rooms:
            name(index, OPENING,
                 f"a room at the pavement's own z={here}, with pavement "
                 f"{level_pavements} on one side and room {rooms} on the "
                 f"other: a way in rather than either")

    #: A mass is re-read as a building where it holds a room and roofs it.
    #: Done as a second pass over the masses the first one named, so the test
    #: can be written and argued with on its own, and so a mass that MOVES
    #: keeps the mechanism reading it already earned.
    pending = {index for index, kind in kinds.items() if kind == END_WALL}
    while pending:
        group = _component([min(pending)], pending, graph)
        pending -= group
        mouths = [other for member in sorted(group)
                  for other in sorted(graph.get(member, ()))
                  if other not in group
                  and kinds.get(other) in (INTERIOR, OPENING)]
        if not mouths:
            continue
        tops = {int(_face(level.sectors[member])["floor_picnum"])
                for member in group}
        roofs = {int(_face(level.sectors[other])["ceiling_picnum"])
                 for other in mouths}
        shared = sorted(tops & roofs)
        if not shared:
            continue
        for member in sorted(group):
            name(member, FACADE,
                 f"a raised mass of {len(group)} sector(s) holding "
                 f"{len(set(mouths))} room(s), whose top wears tile "
                 f"{shared[0]} -- the tile room {sorted(set(mouths))[0]} "
                 f"wears as its ceiling. The mass is the room's roof, so it "
                 f"is a building rather than a termination")

    return {
        "kinds": kinds,
        "why": why,
        "street_network": sorted(network),
        "outdoor_components": components,
        "measured_rise": rise,
        "steps_in_the_network": steps,
        "base_plane_z": base_z,
        "counts": dict(Counter(kinds.values())),
    }


def _kerb_tile() -> int:
    return int(TILE_CLASSES["kerb class"])


def join_census(level: Any, kinds: dict[int, str], *,
                owners: Sequence[int] | None = None) -> dict[str, Any]:
    """Every two-sided record, looked up in the writer's table.

    Both records of a pair are counted, once each: a join is one thing seen
    from two records and each side's rule is about its own record.
    """
    owners = list(owners) if owners is not None else sector_index(level)
    described: Counter = Counter()
    undescribed: Counter = Counter()
    described_records: dict[str, list[int]] = defaultdict(list)
    undescribed_records: dict[str, list[int]] = defaultdict(list)
    #: What the records of each row actually WEAR, as rates. Section 13's
    #: addendum asks for exactly this and calls it the table's evidence.
    band_tiles: dict[str, Counter] = defaultdict(Counter)
    band_blocking: dict[str, Counter] = defaultdict(Counter)
    class_hits: dict[str, list[int]] = defaultdict(lambda: [0, 0])
    disagreements: list[dict[str, Any]] = []

    for wall_id, wall in enumerate(level.walls):
        face = _face(wall)
        other = int(face["next_sector"])
        if other < 0:
            continue
        here = owners[wall_id]
        a_kind, b_kind = kinds.get(here), kinds.get(other)
        height = height_relation(
            int(_face(level.sectors[here])["floor_z"]),
            int(_face(level.sectors[other])["floor_z"]))
        key = f"{a_kind}|{b_kind}|{height}"
        try:
            found = rule(a_kind, b_kind, height)
        except JoinError:
            undescribed[key] += 1
            undescribed_records[key].append(wall_id)
            continue
        described[key] += 1
        described_records[key].append(wall_id)
        if found.a_shows == joins.NOTHING:
            continue
        wanted = next((value for cls, value in TILE_CLASSES.items()
                       if cls in found.a_shows), None)
        got = int(face["picnum"])
        band_tiles[key][got] += 1
        band_blocking[key][int(face["cstat"]) & 1] += 1
        row = class_hits[key]
        row[1] += 1
        if wanted is not None and wanted == got:
            row[0] += 1
        if found.cstat & 1 and not int(face["cstat"]) & 1:
            disagreements.append({
                "wall": wall_id, "sector": here, "faces_sector": other,
                "join": key,
                "the_table_says": "blocking (cstat 1)",
                "the_map_says": f"cstat {int(face['cstat'])}, not blocking",
                #: The reason is usually here: a raised outdoor mass that
                #: carries a sector type is a MECHANISM at rest, and the
                #: end-wall row is about a wall that stays put.
                "faced_sector_type": int(_face(level.sectors[other])["type"]),
                "faced_sector_moves": bool(int(_face(level.sectors[other])["type"]))})

    total = sum(described.values()) + sum(undescribed.values())
    return {
        "two_sided_records": total,
        "described": dict(described),
        "undescribed": dict(undescribed),
        "described_records": {key: sorted(value)
                              for key, value in sorted(described_records.items())},
        "undescribed_records": {key: sorted(value)
                                for key, value in sorted(undescribed_records.items())},
        "records_described": sum(described.values()),
        "records_undescribed": sum(undescribed.values()),
        #: `row -> {tile: records}`: what the class is made of in THIS map.
        "band_tiles": {key: dict(sorted(value.items()))
                       for key, value in sorted(band_tiles.items())},
        "band_blocking": {key: dict(sorted(value.items()))
                          for key, value in sorted(band_blocking.items())},
        #: `row -> [records wearing the table's nominated tile, records]`.
        #: A row is a CLASS ("kerb class"), and which member a level uses is
        #: the level's choice, so a miss here is not a defect: it says how
        #: many members the class has.
        "table_tile_matches": {key: list(value)
                               for key, value in sorted(class_hits.items())},
        "cstat_disagreements": disagreements,
    }


def read_joins(level: Any) -> dict[str, Any]:
    """Surface kinds, then the census of the writer's table against them."""
    owners = sector_index(level)
    kinds = surface_kinds(level, owners=owners)
    census = join_census(level, kinds["kinds"], owners=owners)
    return {"kinds": kinds, "census": census}


def summary(result: dict[str, Any]) -> dict[str, Any]:
    census = result["census"]
    total = int(census["two_sided_records"])
    residue = int(census["records_undescribed"])
    return {
        "two_sided_records": total,
        "records_described": int(census["records_described"]),
        "records_undescribed": residue,
        "residue_percent": round(100.0 * residue / total, 2) if total else 0.0,
        "rows_used": len(census["described"]),
        "pairs_with_no_row": len(census["undescribed"]),
        "cstat_disagreements": len(census["cstat_disagreements"]),
        "kinds": result["kinds"]["counts"],
        "measured_rise": result["kinds"]["measured_rise"],
    }
