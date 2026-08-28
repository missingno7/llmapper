"""What a Blood level measures like, so an authored one can be compared to it.

The authoring loop can already tell whether a level is structurally valid and
whether it loads.  Neither answers the question that actually matters once the
geometry compiles: *does this read as a level somebody built, or as a set of
rooms that happen to connect?*

That question has measurable parts.  This module computes them for any Blood
map, and `tools/design_norms` turns the 43-map campaign into the range each one
actually occupies.  A candidate outside that range is not automatically wrong --
Blood levels differ enormously from each other -- but a candidate outside the
range on the *same axis every campaign map agrees on* is worth looking at.

Everything here is derived.  Nothing is a score: the profile is a vector of
independent measurements, and collapsing it into one number would throw away the
only thing that makes it actionable.

Off-map geometry is excluded throughout, via
:func:`bloodmap.reachability.design_sectors` -- a level's switch closet and its
author's signature are not rooms and should not move any statistic.
"""

from __future__ import annotations

import math
import statistics
from collections import Counter
from typing import Any

from .doors import KEY_TYPES
from .reachability import analyze_reachability, design_sectors, portal_graph

#: Blood sector types that move geometry.
MOVING_SECTOR_RANGE = range(600, 620)

#: XSPRITE command values at or above this carry a number rather than an order;
#: on channel 2 that number identifies a secret (see the mechanics document).
NUMERIC_COMMAND_BASE = 64
SECRET_FOUND_CHANNEL = 2
TOTAL_SECRETS_CHANNEL = 1

PLAYER_WIDTH = 384

DUDE_RANGE = range(200, 261)
WEAPON_AMMO_RANGE = range(40, 80)
ITEM_RANGE = range(100, 150)


def _sector_area(disk: Any, sector_id: int) -> float:
    fields = disk.sectors[sector_id].fields
    start = int(fields["wall_ptr"])
    count = int(fields["wall_count"])
    total = 0.0
    for index in range(start, start + count):
        wall = disk.walls[index].fields
        nxt = disk.walls[int(wall["point2"])].fields
        total += int(wall["x"]) * int(nxt["y"]) - int(nxt["x"]) * int(wall["y"])
    return abs(total) / 2.0


def _topology(disk: Any, playable: set[int]) -> dict[str, Any]:
    """Loops, dead ends and branching in the graph the player actually walks.

    This is the part of a level plan that a room list cannot express. A Blood
    level is a network the player can come back around; a level built by adding
    rooms to whatever was most recently placed is a tree, and a tree is a
    corridor crawl however good its individual rooms are.

    Walls are not the only way through. Water links, stack links and teleporters
    join sectors that share no wall at all, and a level whose shortcut is a dive
    has that loop in play whether or not it has it in geometry -- so the graph
    here is the one :func:`analyze_reachability` walks, not the wall graph. 24 of
    the 43 campaign maps carry water links, so leaving them out is not a corner
    case.

    The cyclomatic number ``E - N + components`` counts independent loops, and
    dividing by sector count makes levels of different sizes comparable.
    """
    walked = analyze_reachability(disk).graph
    graph = {
        sector: {other for other in neighbours if other in playable}
        for sector, neighbours in walked.items()
        if sector in playable
    }
    for sector in playable:
        graph.setdefault(sector, set())
    nodes = len(graph)
    edges = sum(len(v) for v in graph.values()) // 2
    degrees = [len(v) for v in graph.values()]

    seen: set[int] = set()
    components = 0
    for start in graph:
        if start in seen:
            continue
        components += 1
        stack = [start]
        seen.add(start)
        while stack:
            current = stack.pop()
            for neighbour in graph[current]:
                if neighbour not in seen:
                    seen.add(neighbour)
                    stack.append(neighbour)

    cyclomatic = edges - nodes + components
    return {
        "sectors": nodes,
        "portals": edges,
        "components": components,
        "independent_loops": cyclomatic,
        "loops_per_100_sectors": round(100.0 * cyclomatic / nodes, 1) if nodes else 0.0,
        "dead_end_fraction": round(sum(1 for d in degrees if d <= 1) / nodes, 3) if nodes else 0.0,
        "mean_degree": round(statistics.mean(degrees), 2) if degrees else 0.0,
        "max_degree": max(degrees) if degrees else 0,
    }


#: How far two water links may disagree, in world units, before the flooded space
#: stops describing the same geography as the dry one. Four player widths; the
#: campaign's four walkable disagreements miss by 4 to 18.
WORMHOLE_TOLERANCE = 4 * 384


def water_wormholes(disk: Any) -> list[dict[str, Any]]:
    """Pools that dive into one place by different translations.

    A dive is only a shortcut if the flooded space is the dry level's geography
    carried whole. When two mouths share an underwater region *and the player can
    also walk between them*, the translation from each mouth to its shaft has to
    be the same one -- otherwise a short swim comes out somewhere a long walk
    would have reached, and the water reads as a wormhole.

    The campaign is emphatic about this once the condition is stated properly.
    Of the pool pairs sharing an underwater region:

    * both mouths reachable on foot -- **630 agree, 4 disagree**;
    * not both reachable on foot -- 8 agree, 100 disagree.

    So it is not a loose convention that a third of maps happen to follow. It is
    a rule that applies exactly when the player can compare the two routes, and
    the earlier reading of "32% of regions are consistent" was measuring both
    cases together and learning nothing from either.

    Returns one record per offending pair; empty when the level is honest.
    """
    from .reachability import portal_graph as _portal_graph

    links: dict[int, dict[str, Any]] = {}
    for sprite in disk.sprites:
        if sprite.extra is None:
            continue
        kind = int(sprite.fields["type"])
        if kind not in (9, 10):
            continue
        record = links.setdefault(int(sprite.extra.fields.get("data_1", 0)), {})
        record["upper" if kind == 9 else "lower"] = sprite.fields
    joined = {k: v for k, v in links.items() if "upper" in v and "lower" in v}
    if len(joined) < 2:
        return []

    graph = _portal_graph(disk)
    underwater = {
        index for index, sector in enumerate(disk.sectors)
        if sector.extra and int(sector.extra.fields.get("underwater", 0))
    }

    def component(start: int) -> set[int]:
        seen = {start}
        stack = [start]
        while stack:
            for neighbour in graph.get(stack.pop(), ()):
                if neighbour not in seen:
                    seen.add(neighbour)
                    stack.append(neighbour)
        return seen

    def walkable(a: int, b: int) -> bool:
        if a in underwater or b in underwater:
            return False
        seen = {a}
        stack = [a]
        while stack:
            current = stack.pop()
            if current == b:
                return True
            for neighbour in graph.get(current, ()):
                if neighbour in underwater or neighbour in seen:
                    continue
                seen.add(neighbour)
                stack.append(neighbour)
        return False

    def translation(record: dict[str, Any]) -> tuple[int, int]:
        upper, lower = record["upper"], record["lower"]
        return (int(lower["x"]) - int(upper["x"]), int(lower["y"]) - int(upper["y"]))

    keys = sorted(joined)
    found: list[dict[str, Any]] = []
    for index, key_a in enumerate(keys):
        for key_b in keys[index + 1:]:
            lower_a = int(joined[key_a]["lower"]["sector"])
            lower_b = int(joined[key_b]["lower"]["sector"])
            if lower_b not in component(lower_a):
                continue                      # separate flooded places; free
            upper_a = int(joined[key_a]["upper"]["sector"])
            upper_b = int(joined[key_b]["upper"]["sector"])
            if not walkable(upper_a, upper_b):
                continue                      # cannot compare the two routes
            ta, tb = translation(joined[key_a]), translation(joined[key_b])
            drift = math.hypot(ta[0] - tb[0], ta[1] - tb[1])
            if drift > WORMHOLE_TOLERANCE:
                found.append({
                    "links": [key_a, key_b],
                    "pools": [upper_a, upper_b],
                    "translations": [ta, tb],
                    "drift_player_widths": round(drift / PLAYER_WIDTH, 1),
                })
    return found


def water_route_ratios(disk: Any) -> list[float]:
    """For each pair of pools, the swim between them over the surface gap.

    A dive is a shortcut through a space the player cannot see, and the one way
    to get it wrong without the engine objecting is to make that space too small:
    the player goes under in one place and steps out somewhere the swim could not
    have carried them.

    The campaign does not do that. Across its 732 pool-to-pool routes the
    underwater path runs a median **1.19** times the straight-line distance
    between the two pools and is almost never shorter -- p10 is 0.95. Anything
    well under 1 is a hole in the map's geography rather than in its geometry.

    Returns one ratio per traversable pair, empty when the level has no water.
    """
    from .reachability import link_pairs

    def centre(sector_id: int) -> tuple[float, float]:
        fields = disk.sectors[sector_id].fields
        start = int(fields["wall_ptr"])
        count = int(fields["wall_count"])
        xs = [int(disk.walls[w].fields["x"]) for w in range(start, start + count)]
        ys = [int(disk.walls[w].fields["y"]) for w in range(start, start + count)]
        return sum(xs) / count, sum(ys) / count

    pools: dict[int, tuple[int, int]] = {}
    for sprite in disk.sprites:
        if sprite.extra is None:
            continue
        kind = int(sprite.fields["type"])
        if kind not in (9, 10):
            continue
        link = int(sprite.extra.fields.get("data_1", 0))
        upper, lower = pools.get(link, (-1, -1))
        if kind == 9:
            upper = int(sprite.fields["sector"])
        else:
            lower = int(sprite.fields["sector"])
        pools[link] = (upper, lower)
    joined = [(u, l) for u, l in pools.values() if u >= 0 and l >= 0]
    if len(joined) < 2:
        return []

    graph = portal_graph(disk)
    ratios: list[float] = []
    for index, (upper_a, lower_a) in enumerate(joined):
        # Sector-centre to sector-centre along the walls, which is the swim.
        distance = {lower_a: 0.0}
        queue = [lower_a]
        while queue:
            current = queue.pop(0)
            for neighbour in graph.get(current, ()):
                if neighbour in distance:
                    continue
                here, there = centre(current), centre(neighbour)
                distance[neighbour] = distance[current] + math.hypot(
                    here[0] - there[0], here[1] - there[1])
                queue.append(neighbour)
        for upper_b, lower_b in joined[index + 1:]:
            if lower_b not in distance:
                continue
            ca, cb = centre(upper_a), centre(upper_b)
            surface = math.hypot(ca[0] - cb[0], ca[1] - cb[1])
            if surface > PLAYER_WIDTH:
                ratios.append(distance[lower_b] / surface)
    return ratios


def _progression(disk: Any) -> dict[str, Any]:
    """Keys, locks and secrets -- the level's gating, not its geometry."""
    keys_placed = Counter()
    declared_secrets = 0
    secret_marks = 0
    for sprite in disk.sprites:
        type_id = int(sprite.fields["type"])
        if type_id in KEY_TYPES:
            keys_placed[KEY_TYPES[type_id]] += 1
        if sprite.extra is None:
            continue
        extra = sprite.extra.fields
        channel = int(extra.get("tx_id", 0))
        command = int(extra.get("command", 0))
        if command >= NUMERIC_COMMAND_BASE:
            if channel == TOTAL_SECRETS_CHANNEL:
                declared_secrets = max(declared_secrets, command - NUMERIC_COMMAND_BASE)
            elif channel == SECRET_FOUND_CHANNEL:
                secret_marks += 1

    locked = 0
    for group in (disk.sectors, disk.walls, disk.sprites):
        for item in group:
            if item.extra is not None and int(item.extra.fields.get("key", 0)):
                locked += 1
    for sector in disk.sectors:
        if sector.extra is not None and int(sector.extra.fields.get("tx_id", 0)) == SECRET_FOUND_CHANNEL:
            secret_marks += 1

    return {
        "keys_placed": sum(keys_placed.values()),
        "distinct_keys": len(keys_placed),
        "locked_objects": locked,
        "declared_secrets": declared_secrets,
        "secret_marks": secret_marks,
    }


def _population(disk: Any, playable: set[int]) -> dict[str, Any]:
    """Who and what is in the level, and how thickly it is spread.

    Absolute counts scale with the level, so a small level fails them for being
    small rather than for being empty. The densities are what a level of any
    size can be held to: the campaign puts a dude in 11% of its playable
    sectors and roughly one pickup on each.
    """
    types = Counter(int(sprite.fields["type"]) for sprite in disk.sprites)
    dudes = sum(count for t, count in types.items() if t in DUDE_RANGE)
    ammo = sum(count for t, count in types.items() if t in WEAPON_AMMO_RANGE)
    items = sum(count for t, count in types.items() if t in ITEM_RANGE)
    occupied = {
        int(sprite.fields["sector"]) for sprite in disk.sprites
        if int(sprite.fields["type"]) in DUDE_RANGE
        and int(sprite.fields["sector"]) in playable
    }
    count = len(playable) or 1
    return {
        "dudes": dudes,
        "distinct_dude_types": len({t for t in types if t in DUDE_RANGE}),
        "weapons_and_ammo": ammo,
        "items": items,
        "pickups": ammo + items,
        "pickups_per_dude": round((ammo + items) / dudes, 2) if dudes else 0.0,
        "dudes_per_100_sectors": round(100.0 * dudes / count, 1),
        "pickups_per_100_sectors": round(100.0 * (ammo + items) / count, 1),
        # The rate, not the count: `weapons_and_ammo` is a size-dependent total
        # and cannot be compared between levels of different scale.
        "weapons_per_100_sectors": round(100.0 * ammo / count, 1),
        "occupied_sector_fraction": round(len(occupied) / count, 3),
    }


def _patch_share(disk: Any, playable: set[int], graph: dict[int, set[int]],
                 value: dict[int, int]) -> float:
    """Share of sectors sitting in a run of three or more that share a finish.

    Blood paints regions, not rooms. The median same-tile patch is a single
    sector -- doors, trim and one-off spaces -- but 65 to 78% of a level's
    sectors sit in a patch of three or more, so most of the level is a few large
    painted areas with a scattering of exceptions.

    That is what hierarchical style inheritance produces, and what choosing a
    finish per room does not: a level whose rooms each name their own tiles
    scores near zero here however plausible each individual choice was.
    """
    seen: set[int] = set()
    grouped = 0
    for start in playable:
        if start in seen:
            continue
        stack = [start]
        seen.add(start)
        members = 0
        while stack:
            current = stack.pop()
            members += 1
            for neighbour in graph.get(current, ()):
                if neighbour in seen or neighbour not in playable:
                    continue
                if value.get(neighbour) == value.get(current):
                    seen.add(neighbour)
                    stack.append(neighbour)
        if members >= 3:
            grouped += members
    return round(grouped / len(playable), 3) if playable else 0.0


def coincident_solid_pairs(disk: Any) -> list[tuple[int, int]]:
    """Walls from two different sectors that occupy the same line and both block.

    Two sectors that share a line either share a *portal* -- one wall each,
    wound opposite, pointing at each other -- or they do not touch. A pair that
    is coincident and solid on both sides is a wall with no thickness and no
    inside, and the Blood campaign contains **none**: zero across 113,261 walls
    in 43 maps.

    It is the shape an authoring model produces when it declares a boundary
    between two regions and then declines to join them, and it is worth naming
    because the engine will not complain: the map validates, loads and renders,
    and the only sign is that the two rooms never became neighbours.

    Blood's own way to stop a player at a boundary it can see across is a joined
    wall with the blocking bit, which 2,272 two-sided walls in the campaign use.
    """
    owner: dict[int, int] = {}
    for index, sector in enumerate(disk.sectors):
        start = int(sector.fields["wall_ptr"])
        for wall in range(start, start + int(sector.fields["wall_count"])):
            owner[wall] = index

    by_line: dict[frozenset, list[int]] = {}
    for index, wall in enumerate(disk.walls):
        fields = wall.fields
        end = disk.walls[int(fields["point2"])].fields
        a = (int(fields["x"]), int(fields["y"]))
        b = (int(end["x"]), int(end["y"]))
        if a == b:
            continue
        by_line.setdefault(frozenset((a, b)), []).append(index)

    found: list[tuple[int, int]] = []
    for group in by_line.values():
        for left in group:
            for right in group:
                if left >= right or owner.get(left) == owner.get(right):
                    continue
                if (int(disk.walls[left].fields["next_sector"]) < 0
                        and int(disk.walls[right].fields["next_sector"]) < 0):
                    found.append((left, right))
    return found


def _materials(disk: Any, playable: set[int]) -> dict[str, Any]:
    walls = Counter()
    for index, wall in enumerate(disk.walls):
        walls[int(wall.fields["picnum"])] += 1
    floors = Counter()
    ceilings = Counter()
    for index in playable:
        fields = disk.sectors[index].fields
        floors[int(fields["floor_picnum"])] += 1
        ceilings[int(fields["ceiling_picnum"])] += 1

    def concentration(counter: Counter) -> float:
        """Share held by the single most-used tile.

        A level that paints almost everything with one tile reads as untextured
        even when its tile *count* looks respectable.
        """
        total = sum(counter.values())
        return round(counter.most_common(1)[0][1] / total, 3) if total else 0.0

    graph = {
        sector: {other for other in neighbours if other in playable}
        for sector, neighbours in portal_graph(disk).items()
        if sector in playable
    }
    floor_of = {i: int(disk.sectors[i].fields["floor_picnum"]) for i in playable}
    ceiling_of = {i: int(disk.sectors[i].fields["ceiling_picnum"]) for i in playable}
    return {
        "wall_tiles": len(walls),
        "floor_tiles": len(floors),
        "ceiling_tiles": len(ceilings),
        "dominant_wall_share": concentration(walls),
        "dominant_floor_share": concentration(floors),
        "floor_patch_share": _patch_share(disk, playable, graph, floor_of),
        "ceiling_patch_share": _patch_share(disk, playable, graph, ceiling_of),
    }


def _shape(disk: Any, playable: set[int]) -> dict[str, Any]:
    areas = [_sector_area(disk, index) for index in playable]
    heights = [
        abs(int(disk.sectors[i].fields["floor_z"]) - int(disk.sectors[i].fields["ceiling_z"]))
        for i in playable
    ]
    floors = sorted({int(disk.sectors[i].fields["floor_z"]) for i in playable})
    sky = sum(1 for i in playable if int(disk.sectors[i].fields["ceiling_stat"]) & 1)
    walls = sum(int(disk.sectors[i].fields["wall_count"]) for i in playable)

    def spread(values: list[float]) -> float:
        """Interquartile ratio: how unlike each other the rooms are.

        A level whose rooms are all the same size reads as modular. The ratio is
        scale-free, so it compares across levels of any size.
        """
        if len(values) < 4:
            return 1.0
        ordered = sorted(values)
        low = ordered[len(ordered) // 4]
        high = ordered[3 * len(ordered) // 4]
        return round(high / low, 2) if low else 0.0

    return {
        "walls_per_sector": round(walls / len(playable), 1) if playable else 0.0,
        "median_area": int(statistics.median(areas)) if areas else 0,
        "area_iqr_ratio": spread(areas),
        "median_height": int(statistics.median(heights)) if heights else 0,
        "height_iqr_ratio": spread([float(h) for h in heights]),
        "distinct_floor_levels": len(floors),
        "sky_fraction": round(sky / len(playable), 3) if playable else 0.0,
    }


def _water(disk: Any, playable: set[int]) -> dict[str, Any]:
    ratios = water_route_ratios(disk)
    underwater = [
        index for index in playable
        if disk.sectors[index].extra
        and int(disk.sectors[index].extra.fields.get("underwater", 0))
    ]
    record: dict[str, Any] = {
        "underwater_sectors": len(underwater),
        "pool_pairs": sum(1 for s in disk.sprites if int(s.fields["type"]) == 9),
    }
    if ratios:
        record["route_over_surface_gap"] = round(statistics.median(ratios), 2)
        record["shortest_route_ratio"] = round(min(ratios), 2)
    record["wormholes"] = len(water_wormholes(disk))
    return record


def _mechanisms(disk: Any) -> dict[str, Any]:
    types = Counter(int(sector.fields["type"]) for sector in disk.sectors)
    moving = {t: n for t, n in types.items() if t in MOVING_SECTOR_RANGE}
    return {
        "moving_sectors": sum(moving.values()),
        "distinct_moving_types": len(moving),
        "by_type": {str(t): n for t, n in sorted(moving.items())},
    }


def _mechanism_density(disk: Any, playable: set[int]) -> float:
    types = Counter(int(sector.fields["type"]) for sector in disk.sectors)
    moving = sum(n for t, n in types.items() if t in MOVING_SECTOR_RANGE)
    return round(100.0 * moving / (len(playable) or 1), 1)


def level_profile(disk: Any, *, name: str = "") -> dict[str, Any]:
    """A vector of design measurements for one Blood map.

    Deliberately not a score. Each group answers a different question and they
    disagree with each other on purpose: a small level with strong topology is a
    different thing from a sprawling one with none, and one number could not
    tell them apart.
    """
    playable = set(design_sectors(disk))
    reach = analyze_reachability(disk)
    profile = {
        "$schema": "llmapper.blood-level-profile",
        "schema_version": 1,
        "name": name,
        "scale": {
            "sectors": len(disk.sectors),
            "playable_sectors": len(playable),
            "walls": len(disk.walls),
            "sprites": len(disk.sprites),
            "off_map_fraction": round(reach.offmap_fraction, 3),
        },
        "shape": _shape(disk, playable),
        "geometry": {
            "coincident_solid_pairs": len(coincident_solid_pairs(disk)),
            "blocking_two_sided_walls": sum(
                1 for wall in disk.walls
                if int(wall.fields["next_sector"]) >= 0 and int(wall.fields["cstat"]) & 1
            ),
        },
        "topology": _topology(disk, playable),
        "materials": _materials(disk, playable),
        "progression": _progression(disk),
        "population": _population(disk, playable),
        "water": _water(disk, playable),
        "mechanisms": dict(_mechanisms(disk),
                           moving_per_100_sectors=_mechanism_density(disk, playable)),
    }
    return profile


def flatten(profile: dict[str, Any]) -> dict[str, float]:
    """The comparable scalars, as ``group.metric`` -> value."""
    flat: dict[str, float] = {}
    for group, values in profile.items():
        if not isinstance(values, dict) or group.startswith("$"):
            continue
        for key, value in values.items():
            if isinstance(value, (int, float)) and not isinstance(value, bool):
                flat[f"{group}.{key}"] = float(value)
    return flat
