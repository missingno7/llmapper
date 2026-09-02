"""The reader half of `light_field`: the sun and its field, off the shadows.

The writer takes a bearing and some masses and cuts a plane into levels. This
recovers all three from a finished map: the sun's bearing from the shade
boundaries, the field's levels from the shades themselves, and which mass
casts which shadow from where the boundaries start.

How the bearing is recovered, and why it takes two measurements
===============================================================

A directional sun sweeps each mass along one vector, so a shadow is a mass
plus that translation. Its SIDE edges are therefore parallel to the throw and
its FAR end is perpendicular to it. Two facts follow, and the reader uses both
because either alone is ambiguous:

1. the oblique shade boundaries all share one bearing, modulo 180 -- that
   fixes the sun's AXIS but not which way along it the shadows fall;
2. a shade boundary perpendicular to that axis is a shadow's far end, and the
   SHADOW is on the up-sun side of it -- that fixes the sign.

`light_field.sun_vector` is the writer's convention and it is the throw: the
direction shadows are cast, in Build units (2048 to the turn). What comes back
here is in the same units so the two can be compared without a conversion
anybody has to remember.

What the residue is
===================

* **shade edges not at the bearing** -- an oblique boundary whose bearing is
  not the sun's. One directional source cannot have made it.
* **sector shades that fit no level** -- a floor shade that is not
  `base + k * step` for any k the field reaches. Lighter than its depth
  predicts is a source (a lamp); darker is a shadow nothing in the model
  casts. They are counted apart because they are different failures.
"""

from __future__ import annotations

import math
from collections import Counter, defaultdict
from typing import Any, Sequence

from .light_field import LEVEL_FLOOR, MAX_LEVELS, STEP, STEP_ENVELOPE
from .read_joins import adjacency, street_network
from .texture_frame import sector_index

#: Within this many degrees of an axis, a boundary is an axis-aligned cut
#: rather than an oblique one. E3M1's obliques sit 3.6-6.4 degrees off the
#: y axis, so the window has to be small; 2 degrees keeps them all.
AXIS_DEGREES = 2.0
#: How far from the recovered axis a boundary may sit and still be counted as
#: the same source. The obliques span 82.87-86.42, so a source is a cluster,
#: not a number, and the width is part of the answer.
CLUSTER_DEGREES = 8.0
#: Build's turn.
UNITS_PER_TURN = 2048


def _face(item: Any) -> Any:
    return item["fields"] if isinstance(item, dict) else item.fields


def _bearing(p: tuple[int, int], q: tuple[int, int]) -> float:
    return math.degrees(math.atan2(q[1] - p[1], q[0] - p[0])) % 360.0


def _axis(bearing: float) -> float:
    return bearing % 180.0


def _to_units(degrees: float) -> int:
    return int(round((degrees % 360.0) * UNITS_PER_TURN / 360.0))


def _extra(item: Any) -> dict[str, Any] | None:
    extra = item["blood"] if isinstance(item, dict) else getattr(item, "extra", None)
    if extra is None:
        return None
    return extra["fields"] if isinstance(extra, dict) else extra.fields


def has_a_light_wave(sector: Any) -> bool:
    """Does this sector's shade come from a WAVE rather than from the sun?

    An XSECTOR with `amplitude` or `shade_always` drives its own shade at run
    time, so its `floor_shade` is a phase of that wave and not a sample of the
    sun's field. Such a sector is not evidence about the sun and is excluded
    from the shade-boundary population before anything is measured -- E3M1 has
    61 of them (45 with `shade_always`), and reading their boundaries as
    shadow edges would put a mechanism's flicker into the sun's bearing.
    """
    extra = _extra(sector) or {}
    return bool(int(extra.get("amplitude", 0)) or int(extra.get("shade_always", 0)))


def shade_edges(level: Any, network: set[int], owners: Sequence[int], *,
                exclude_waves: bool = True) -> list[dict[str, Any]]:
    """Every record inside the network whose two sides are at one z and differ
    in floor shade. Both records of a pair appear: a boundary has two sides."""
    waved = {index for index in network
             if has_a_light_wave(level.sectors[index])} if exclude_waves else set()
    out = []
    for wall_id, wall in enumerate(level.walls):
        face = _face(wall)
        other = int(face["next_sector"])
        here = owners[wall_id]
        if other < 0 or here not in network or other not in network:
            continue
        if here in waved or other in waved:
            continue
        a, b = _face(level.sectors[here]), _face(level.sectors[other])
        if int(a["floor_z"]) != int(b["floor_z"]):
            continue
        if int(a["floor_shade"]) == int(b["floor_shade"]):
            continue
        start = (int(face["x"]), int(face["y"]))
        nxt = _face(level.walls[int(face["point2"])])
        end = (int(nxt["x"]), int(nxt["y"]))
        out.append({
            "wall": wall_id, "here": here, "there": other,
            "shade_here": int(a["floor_shade"]), "shade_there": int(b["floor_shade"]),
            "start": start, "end": end,
            "bearing": round(_bearing(start, end), 2),
            "axis": round(_axis(_bearing(start, end)), 2),
            "length": round(math.dist(start, end), 1),
        })
    return out


def sun_axis(edges: Sequence[dict[str, Any]]) -> dict[str, Any]:
    """The one bearing the oblique boundaries share, modulo 180.

    Weighted by LENGTH: a 9472-unit boundary is more evidence about where the
    sun is than a 1028-unit one, and an unweighted median lets a short edge
    at the wrong angle move the answer.
    """
    oblique = [row for row in edges
               if min(row["axis"], abs(row["axis"] - 90.0),
                      180.0 - row["axis"]) > AXIS_DEGREES]
    if not oblique:
        return {"oblique_edges": 0, "axis_degrees": None}
    ordered = sorted(oblique, key=lambda row: row["axis"])
    total = sum(row["length"] for row in ordered)
    running, median = 0.0, ordered[-1]["axis"]
    for row in ordered:
        running += row["length"]
        if running >= total / 2:
            median = row["axis"]
            break
    within = [row for row in oblique
              if abs(row["axis"] - median) <= CLUSTER_DEGREES]
    outside = [row for row in oblique
               if abs(row["axis"] - median) > CLUSTER_DEGREES]
    axes = [row["axis"] for row in within]
    return {
        "oblique_edges": len(oblique),
        "axis_degrees": round(median, 2),
        "axis_units_mod_half_turn": _to_units(median),
        "cluster_records": len(within),
        "cluster_spread_degrees": [round(min(axes), 2), round(max(axes), 2)],
        "axis_aligned_edges": len(edges) - len(oblique),
        "residue_edges_off_the_bearing": [row["wall"] for row in outside],
        "residue_axes": sorted({row["axis"] for row in outside}),
    }


def sun_sign(edges: Sequence[dict[str, Any]], axis_degrees: float
             ) -> dict[str, Any]:
    """Which way along the axis the shadows fall.

    A boundary perpendicular to the axis is a shadow's FAR end, so the darker
    side of it lies up-sun and the throw points from dark to light across it.
    Each such boundary votes; the vote is reported with its count so a tie is
    visible rather than silently broken.
    """
    throw = math.radians(axis_degrees)
    vector = (math.cos(throw), math.sin(throw))
    votes: Counter = Counter()
    used = []
    for row in edges:
        offset = abs(((row["axis"] - axis_degrees) % 180.0) - 90.0)
        if offset > 15.0:                      # not a far end
            continue
        #: from the darker side toward the lighter one, across the boundary
        dark_is_here = row["shade_here"] > row["shade_there"]
        (sx, sy), (ex, ey) = row["start"], row["end"]
        normal = (ey - sy, -(ex - sx))         # right of the record's direction
        length = math.hypot(*normal) or 1.0
        normal = (normal[0] / length, normal[1] / length)
        #: Build winds a sector's walls so that its own side is to the LEFT of
        #: the record's direction, so `normal` points into `there`.
        toward_light = normal if dark_is_here else (-normal[0], -normal[1])
        dot = toward_light[0] * vector[0] + toward_light[1] * vector[1]
        if abs(dot) < 0.2:
            continue
        votes["+" if dot > 0 else "-"] += 1
        used.append({"wall": row["wall"], "vote": "+" if dot > 0 else "-",
                     "dot": round(dot, 3)})
    plus, minus = votes.get("+", 0), votes.get("-", 0)
    sign = 1 if plus >= minus else -1
    bearing = (axis_degrees if sign > 0 else axis_degrees + 180.0) % 360.0
    return {
        "far_end_boundaries": len(used),
        "votes": {"along the axis": plus, "against it": minus},
        "decided": plus != minus,
        "throw_bearing_degrees": round(bearing, 2),
        "throw_bearing_units": _to_units(bearing),
        "ballots": used,
    }


def field_levels(level: Any, network: set[int],
                 exclude: set[int] | None = None) -> dict[str, Any]:
    """The field's levels, area-weighted, and how many of them `base + k*step`
    reaches.

    `exclude` drops the sectors that drive their own shade: their `floor_shade`
    is a phase of a wave, not a sample of the sun.
    """
    from .viewplan import sector_area

    exclude = set(exclude or ())
    by_shade: dict[int, float] = defaultdict(float)
    sectors: dict[int, list[int]] = defaultdict(list)
    for index in sorted(set(network) - exclude):
        shade = int(_face(level.sectors[index])["floor_shade"])
        by_shade[shade] += float(sector_area(level, index))
        sectors[shade].append(index)
    total = sum(by_shade.values()) or 1.0
    significant = sorted(shade for shade, area in by_shade.items()
                         if area / total >= LEVEL_FLOOR)
    base = min(significant) if significant else min(by_shade, default=0)
    fitted: dict[int, int] = {}
    misfit: dict[int, int] = {}
    for shade in sorted(by_shade):
        for depth in range(MAX_LEVELS):
            if base + depth * STEP == shade:
                fitted[shade] = depth
                break
        else:
            misfit[shade] = shade - base
    return {
        "levels": {int(shade): {"area_share": round(area / total, 4),
                                "sectors": sectors[shade]}
                   for shade, area in sorted(by_shade.items())},
        "significant_levels": significant,
        "significant_count": len(significant),
        "lit_base": int(base),
        "step_assumed": STEP,
        "step_envelope": list(STEP_ENVELOPE),
        "shades_that_fit_base_plus_k_step": {int(k): int(v) for k, v in fitted.items()},
        "shades_that_fit_no_level": {int(k): int(v) for k, v in misfit.items()},
        "sectors_that_fit": sorted(index for shade in fitted
                                   for index in sectors[shade]),
        "sectors_that_fit_no_level": sorted(index for shade in misfit
                                            for index in sectors[shade]),
        "lighter_than_the_base": sorted(index for shade in misfit
                                        if shade < base for index in sectors[shade]),
    }


def observed_step(edges: Sequence[dict[str, Any]]) -> dict[str, Any]:
    """The shade delta across the boundaries, as the map states it."""
    deltas = Counter(abs(row["shade_here"] - row["shade_there"]) for row in edges)
    values = sorted(deltas.elements())
    low, high = STEP_ENVELOPE
    return {
        "deltas": {int(k): int(v) for k, v in sorted(deltas.items())},
        "median": int(values[len(values) // 2]) if values else None,
        "inside_the_campaign_envelope": sum(
            count for delta, count in deltas.items() if low <= delta <= high),
        "outside_it": sum(count for delta, count in deltas.items()
                          if not low <= delta <= high),
    }


def casters(level: Any, edges: Sequence[dict[str, Any]], throw_degrees: float,
            kinds: dict[int, str]) -> dict[str, Any]:
    """Which corner threw each shadow.

    A shadow's side edge is the ray from a caster's corner along the throw, so
    the edge's UP-SUN endpoint should be a vertex of a mass and its down-sun
    endpoint should not. Counting both is the test: if the up-sun end is a
    mass corner much more often, the sign is confirmed by geometry that had no
    part in choosing it.
    """
    masses = {index for index, kind in kinds.items()
              if kind in ("solid", "end_wall")}
    corners: dict[tuple[int, int], set[int]] = defaultdict(set)
    for wall_id, wall in enumerate(level.walls):
        face = _face(wall)
        point = (int(face["x"]), int(face["y"]))
        owner = None
        for index in masses:
            fields = _face(level.sectors[index])
            start = int(fields["wall_ptr"])
            if start <= wall_id < start + int(fields["wall_count"]):
                owner = index
                break
        if owner is not None:
            corners[point].add(owner)
        if int(face["next_sector"]) < 0:
            corners[point].add(-1)            # a one-sided wall: a building

    vector = (math.cos(math.radians(throw_degrees)),
              math.sin(math.radians(throw_degrees)))
    up_sun = down_sun = neither = 0
    rows = []
    for row in edges:
        (sx, sy), (ex, ey) = row["start"], row["end"]
        along = (ex - sx) * vector[0] + (ey - sy) * vector[1]
        head, tail = ((sx, sy), (ex, ey)) if along > 0 else ((ex, ey), (sx, sy))
        at_head, at_tail = corners.get(head), corners.get(tail)
        if at_head:
            up_sun += 1
        if at_tail:
            down_sun += 1
        if not at_head and not at_tail:
            neither += 1
        rows.append({"wall": row["wall"], "up_sun_corner": head,
                     "casts_from": sorted(at_head) if at_head else [],
                     "down_sun_corner": tail,
                     "also_at_the_far_end": sorted(at_tail) if at_tail else []})
    return {
        "edges": len(edges),
        "up_sun_end_is_a_mass_corner": up_sun,
        "down_sun_end_is_a_mass_corner": down_sun,
        "neither_end_is": neither,
        "per_edge": rows,
    }


def lamps(level: Any, network: set[int], fit: dict[str, Any], *,
          fullbright: int = -128) -> dict[str, Any]:
    """Sources: sprites the engine draws at full brightness, and the sectors
    that are lighter than the field's own base."""
    bright: dict[int, Counter] = defaultdict(Counter)
    for sprite in level.sprites:
        fields = _face(sprite)
        sector = int(fields["sector"])
        if sector in network and int(fields["shade"]) <= fullbright:
            bright[sector][int(fields["picnum"])] += 1
    return {
        "fullbright_sprites": sum(sum(row.values()) for row in bright.values()),
        "fullbright_by_sector": {int(k): dict(v) for k, v in sorted(bright.items())},
        "tiles": dict(sorted(Counter(
            tile for row in bright.values() for tile, count in row.items()
            for _ in range(count)).items())),
        "sectors_lighter_than_the_base": fit["lighter_than_the_base"],
        "sectors_with_a_source_and_no_extra_light": sorted(
            set(bright) - set(fit["lighter_than_the_base"])),
    }


def read_light(level: Any, kinds: dict[int, str] | None = None, *,
               owners: Sequence[int] | None = None) -> dict[str, Any]:
    owners = list(owners) if owners is not None else sector_index(level)
    graph = adjacency(level, owners)
    network, _ = street_network(level, graph)
    if kinds is None:
        from .read_joins import surface_kinds

        kinds = surface_kinds(level, owners=owners)["kinds"]
    waved = sorted(index for index in network
                   if has_a_light_wave(level.sectors[index]))
    edges = shade_edges(level, network, owners, exclude_waves=True)
    with_waves = shade_edges(level, network, owners, exclude_waves=False)
    axis = sun_axis(edges)
    sign = (sun_sign(edges, axis["axis_degrees"])
            if axis["axis_degrees"] is not None else {})
    fit = field_levels(level, network, exclude=set(waved))
    throw = sign.get("throw_bearing_degrees")
    return {
        "network": sorted(network),
        "sectors_driving_their_own_shade": waved,
        "sectors_driving_their_own_shade_in_the_whole_map": sorted(
            index for index in range(len(level.sectors))
            if has_a_light_wave(level.sectors[index])),
        "shade_edge_records_before_excluding_waves": len(with_waves),
        "shade_edge_records_the_wave_exclusion_removes": len(with_waves) - len(edges),
        "shade_edge_records": len(edges),
        "shade_edges": edges,
        "axis": axis,
        "sign": sign,
        "step": observed_step(edges),
        "field": fit,
        "casters": (casters(level, [row for row in edges
                                    if min(row["axis"], abs(row["axis"] - 90.0),
                                           180.0 - row["axis"]) > AXIS_DEGREES],
                            throw, kinds) if throw is not None else {}),
        "lamps": lamps(level, network, fit),
    }


def summary(result: dict[str, Any]) -> dict[str, Any]:
    axis, fit = result["axis"], result["field"]
    off = len(axis.get("residue_edges_off_the_bearing", []))
    misfit = len(fit["sectors_that_fit_no_level"])
    return {
        "shade_edge_records": int(result["shade_edge_records"]),
        "shade_edge_records_the_wave_exclusion_removes":
            int(result["shade_edge_records_the_wave_exclusion_removes"]),
        "sectors_driving_their_own_shade": len(result["sectors_driving_their_own_shade"]),
        "oblique_edges": int(axis.get("oblique_edges", 0)),
        "sun_axis_degrees": axis.get("axis_degrees"),
        "throw_bearing_units": result["sign"].get("throw_bearing_units"),
        "sun_decided": result["sign"].get("decided"),
        "edges_off_the_bearing": off,
        "lit_base": fit["lit_base"],
        "significant_levels": fit["significant_count"],
        "sectors_that_fit_base_plus_k_step": len(fit["sectors_that_fit"]),
        "sectors_that_fit_no_level": misfit,
        "observed_deltas": result["step"]["deltas"],
        "fullbright_sprites": result["lamps"]["fullbright_sprites"],
    }
