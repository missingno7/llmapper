"""Object-scale relations: what is next to what, said without naming it.

At *space* scale `decompiler.py` already emits relations between perceptual
spaces and structures (`connects`, `part_of`, `overlaps`, `embedded_in`,
`overlook`, `pit`). At *object* scale -- the sprite, the wall segment, the
two-player-widths sector -- nothing emits relations at all.
`placement.observe_sprite_attachment` measures one sprite against its nearest
wall, but that is a per-sprite record, not a relation, and nothing relates two
sprites or two small sectors to each other.

This module fills exactly that gap and stops. It answers, for a local
neighborhood, "what is around this primitive", in a form two occurrences in
different maps can be compared in. It does not name anything: there is no
`shelf` here and no `drawer`, only `against_wall`, `rests_on`, `repeats_along`.

**Frame independence is the point.** Every measure is either a count, a ratio,
a normalized distance (player widths / player heights), or an angle *relative
to a referenced wall's inward normal*. No world coordinate, no world bearing,
no absolute z reaches a relation. The claim is exact under translation and
quarter-turn rotation -- the transform Build integer geometry admits losslessly
(`BuildIR.rotate_quarter_turns`) -- and `tests/test_relations.py` pins it by
re-extracting from a transformed copy and requiring an identical document.

Deliberate non-goals: naming objects, mechanism wiring (`assembly.py` owns
that), space-scale grouping (`decompiler.py` owns that), stair runs and
recesses (`structures.py` owns those), and any relation no current consumer
reads.
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field
from fractions import Fraction
from math import hypot
from pathlib import Path
from statistics import mean, pstdev
from typing import Any, Iterable, Sequence

from .build_ir import BuildIR
from .design import _polygon_loops, _signed_area
from .placement import build_angle, inward_normal, point_segment_distance
from .planar_geom import point_in_loop
from .player_space import player_profile
from .spatial import analyze_spatial


SCHEMA = "llmapper.object-relations"
SCHEMA_VERSION = 1

#: Every relation kind, and the consumer that justifies it. A kind with no
#: consumer does not belong here (`10_AGENT_EXECUTION_PROTOCOL.md`: do not add
#: relations no consumer needs yet).
RELATION_KINDS: dict[str, str] = {
    "in_sector": "anchor: which space carries the object (03: contains)",
    "against_wall": "03 discriminator against_wall; shelf vs crate pile",
    "faces_wall": "03 discriminator privileged_front / open_front",
    "rests_on": "03 supports/supported_by; what holds the object up",
    "repeats_along": "03 repeats_along + stackable_identical_units",
    "adjacent_to": "03 open_to/accessible_from at object scale",
    "above": "03 above/below; overlooks, lofts, stacked volumes",
    "inside": "03 inside/contains; a volume cut into another",
    "shares_plane": "03 coplanar_with/shares_height_with; a run of surfaces",
    "shares_material": "03 shares_style_with, the cheapest style relation",
}

#: Measures may never carry a world frame. Pinned by a test, not by hope.
FORBIDDEN_MEASURE_KEYS = frozenset({
    "x", "y", "z", "cx", "cy", "bounds", "angle", "world_angle",
    "floor_z", "ceiling_z", "centroid",
})

#: Two sprites count as one repeating run when their spacings agree this
#: closely (coefficient of variation) and they stay this near a straight line.
REPEAT_SPACING_CV = 0.12
REPEAT_COLLINEAR_PLAYER_WIDTHS = 0.35
REPEAT_MIN_MEMBERS = 3

#: A sprite is "against" a wall inside this distance, and "resting" on a
#: surface inside this clearance. Both are the bands `placement.py` already
#: measured across the campaign, restated here as thresholds.
AGAINST_WALL_PLAYER_WIDTHS = 0.75
RESTS_ON_PLAYER_HEIGHTS = 0.15

#: Facing tolerance: a quarter of a right angle either side of the wall normal.
FACES_BUILD_UNITS = 256


class RelationError(ValueError):
    pass


@dataclass(frozen=True)
class Relation:
    """One observed relation, with the evidence that produced it.

    `subject` and `object` are primitive references (`sprite:12`, `wall:44`,
    `sector:32`); `members` carries the group for a group relation. `measures`
    is frame-independent by construction (see `FORBIDDEN_MEASURE_KEYS`).
    """

    kind: str
    subject: str | None = None
    object: str | None = None
    members: tuple[str, ...] = ()
    measures: dict[str, Any] = field(default_factory=dict)
    basis: str = ""

    def to_dict(self) -> dict[str, Any]:
        item: dict[str, Any] = {"kind": self.kind}
        if self.subject is not None:
            item["subject"] = self.subject
        if self.object is not None:
            item["object"] = self.object
        if self.members:
            item["members"] = list(self.members)
        item["measures"] = dict(self.measures)
        item["basis"] = self.basis
        return item

    def sort_key(self) -> tuple:
        return (self.kind, self.subject or "", self.object or "", self.members)


def _ref(kind: str, identifier: int) -> str:
    return f"{kind}:{identifier}"


def _id(ref: str) -> int:
    return int(str(ref).split(":", 1)[1])


def _owners(build: BuildIR) -> list[int]:
    owners = [-1] * len(build.walls)
    for sector_id, sector in enumerate(build.sectors):
        first = int(sector["fields"]["wall_ptr"])
        count = int(sector["fields"]["wall_count"])
        for wall_id in range(first, first + count):
            if 0 <= wall_id < len(owners):
                owners[wall_id] = sector_id
    return owners


def _bounds(points: Sequence[tuple[int, int]]) -> tuple[int, int, int, int]:
    xs = [int(p[0]) for p in points]
    ys = [int(p[1]) for p in points]
    return min(xs), min(ys), max(xs), max(ys)


def _bbox_overlap_fraction(a: tuple[int, int, int, int], b: tuple[int, int, int, int]) -> float:
    """Overlap of two plan bounding boxes, over the smaller box.

    Bounding boxes, not true polygon area: cheap, and exact under the
    quarter-turn rotations Build geometry admits. The name says `bbox` so no
    consumer mistakes it for a polygon intersection.
    """
    width = min(a[2], b[2]) - max(a[0], b[0])
    height = min(a[3], b[3]) - max(a[1], b[1])
    if width <= 0 or height <= 0:
        return 0.0
    smaller = min((a[2] - a[0]) * (a[3] - a[1]), (b[2] - b[0]) * (b[3] - b[1]))
    return 0.0 if smaller <= 0 else (width * height) / smaller


def _centroid(loop: Sequence[tuple[int, int]]) -> tuple[Fraction, Fraction]:
    """Exact rational vertex centroid.

    Rational, not float: `planar_geom.point_in_loop` is an exact even-odd test
    and a float centroid would make containment depend on rounding -- which is
    precisely the frame dependence this module exists to avoid.
    """
    if not loop:
        return Fraction(0), Fraction(0)
    count = len(loop)
    return (Fraction(sum(int(p[0]) for p in loop), count),
            Fraction(sum(int(p[1]) for p in loop), count))


@dataclass(frozen=True)
class Neighborhood:
    """The primitives a relation dump is taken over."""

    seeds: tuple[int, ...]
    sectors: tuple[int, ...]
    walls: tuple[int, ...]
    sprites: tuple[int, ...]
    hops: int

    def to_dict(self) -> dict[str, Any]:
        return {
            "seed_sectors": list(self.seeds),
            "hops": self.hops,
            "sectors": list(self.sectors),
            "wall_count": len(self.walls),
            "sprite_count": len(self.sprites),
        }


def neighborhood(
    build: BuildIR,
    *,
    sectors: Iterable[int] | None = None,
    sprites: Iterable[int] | None = None,
    hops: int = 1,
) -> Neighborhood:
    """Grow a local neighborhood from seed sectors and/or seed sprites.

    Expansion is by portal adjacency, `hops` steps. This is scale 1-2 of the
    multi-scale ladder in `03_...md`; scales 3+ (room, architectural context)
    are `decompiler.py`'s perceptual spaces and are not recomputed here.
    """
    if hops < 0:
        raise RelationError("hops must not be negative")
    seeds: set[int] = {int(value) for value in (sectors or ())}
    for sprite_id in (int(value) for value in (sprites or ())):
        if not 0 <= sprite_id < len(build.sprites):
            raise RelationError(f"sprite:{sprite_id} is out of range")
        seeds.add(int(build.sprites[sprite_id]["fields"]["sector"]))
    if not seeds:
        raise RelationError("a neighborhood needs at least one seed sector or sprite")
    invalid = sorted(value for value in seeds if not 0 <= value < len(build.sectors))
    if invalid:
        raise RelationError(f"seed sectors out of range: {invalid}")

    owners = _owners(build)
    adjacency: dict[int, set[int]] = defaultdict(set)
    for wall_id, wall in enumerate(build.walls):
        left, right = owners[wall_id], int(wall["fields"]["next_sector"])
        if left >= 0 and right >= 0:
            adjacency[left].add(right)
            adjacency[right].add(left)

    reached = set(seeds)
    frontier = set(seeds)
    for _step in range(hops):
        frontier = {other for value in frontier for other in adjacency[value]} - reached
        if not frontier:
            break
        reached |= frontier

    selected = tuple(sorted(reached))
    walls = tuple(
        wall_id for wall_id in range(len(build.walls)) if owners[wall_id] in reached
    )
    sprite_ids = tuple(
        sprite_id for sprite_id, sprite in enumerate(build.sprites)
        if int(sprite["fields"]["sector"]) in reached
    )
    return Neighborhood(
        seeds=tuple(sorted(seeds)), sectors=selected, walls=walls,
        sprites=sprite_ids, hops=hops,
    )


def _sector_geometry(build: BuildIR, sector_ids: Iterable[int]) -> dict[int, dict[str, Any]]:
    geometry: dict[int, dict[str, Any]] = {}
    for sector_id in sector_ids:
        loops = _polygon_loops(build, sector_id)
        if not loops:
            continue
        fields = build.sectors[sector_id]["fields"]
        points = [point for loop in loops for point in loop]
        geometry[sector_id] = {
            "loops": loops,
            "outer": max(loops, key=lambda loop: abs(_signed_area(loop))),
            "bounds": _bounds(points),
            "area": abs(sum(_signed_area(loop) for loop in loops)),
            "floor_z": int(fields["floor_z"]),
            "ceiling_z": int(fields["ceiling_z"]),
            "floor_picnum": int(fields["floor_picnum"]),
            "ceiling_picnum": int(fields["ceiling_picnum"]),
        }
    return geometry


def _wall_segment(build: BuildIR, wall_id: int) -> tuple[tuple[int, int], tuple[int, int]]:
    fields = build.walls[wall_id]["fields"]
    point2 = int(fields["point2"])
    if not 0 <= point2 < len(build.walls):
        raise RelationError(f"wall:{wall_id} has invalid point2 {point2}")
    end = build.walls[point2]["fields"]
    return (int(fields["x"]), int(fields["y"])), (int(end["x"]), int(end["y"]))


def _sprite_relations(
    build: BuildIR, hood: Neighborhood, geometry: dict[int, dict[str, Any]],
    width: int, height: int,
) -> list[Relation]:
    """in_sector, against_wall, faces_wall, rests_on.

    The measurements are `placement.observe_sprite_attachment`'s, recomputed on
    BuildIR so Duke3D neighborhoods work too, and emitted as relations with the
    wall they are relative to instead of as a per-sprite record.
    """
    out: list[Relation] = []
    for sprite_id in hood.sprites:
        fields = build.sprites[sprite_id]["fields"]
        sector_id = int(fields["sector"])
        sector = geometry.get(sector_id)
        if sector is None:
            continue
        sprite_ref = _ref("sprite", sprite_id)
        x, y, z = int(fields["x"]), int(fields["y"]), int(fields["z"])
        out.append(Relation(
            kind="in_sector", subject=sprite_ref, object=_ref("sector", sector_id),
            measures={"picnum": int(fields["picnum"])},
            basis="native sprite.sector",
        ))

        best: tuple[float, float, int] | None = None
        first = int(build.sectors[sector_id]["fields"]["wall_ptr"])
        count = int(build.sectors[sector_id]["fields"]["wall_count"])
        for wall_id in range(first, first + count):
            if not 0 <= wall_id < len(build.walls):
                continue
            (ax, ay), (bx, by) = _wall_segment(build, wall_id)
            distance, t = point_segment_distance(x, y, ax, ay, bx, by)
            if best is None or distance < best[0]:
                best = (distance, t, wall_id)
        if best is not None and best[0] <= AGAINST_WALL_PLAYER_WIDTHS * width:
            distance, t, wall_id = best
            (ax, ay), (bx, by) = _wall_segment(build, wall_id)
            wall_ref = _ref("wall", wall_id)
            wall_fields = build.walls[wall_id]["fields"]
            out.append(Relation(
                kind="against_wall", subject=sprite_ref, object=wall_ref,
                measures={
                    "distance_player_widths": round(distance / width, 4),
                    "along_wall": round(t, 4),
                    "wall_picnum": int(wall_fields["picnum"]),
                    "wall_is_portal": int(wall_fields["next_sector"]) >= 0,
                },
                basis="perpendicular distance to the owning sector's nearest wall segment",
            ))
            nx, ny = inward_normal(ax, ay, bx, by)
            delta = (int(fields["angle"]) - build_angle(nx, ny)) & 2047
            if delta > 1024:
                delta -= 2048
            if abs(delta) <= FACES_BUILD_UNITS:
                out.append(Relation(
                    kind="faces_wall", subject=sprite_ref, object=wall_ref,
                    measures={"angle_from_inward_normal": int(delta)},
                    basis="sprite angle relative to that wall's inward normal, not to world north",
                ))

        floor_clear = sector["floor_z"] - z
        ceiling_clear = z - sector["ceiling_z"]
        if 0 <= floor_clear <= RESTS_ON_PLAYER_HEIGHTS * height:
            out.append(Relation(
                kind="rests_on", subject=sprite_ref, object=_ref("sector", sector_id),
                measures={"surface": "floor",
                          "clearance_player_heights": round(floor_clear / height, 4)},
                basis="sprite z within one clearance band of the sector floor plane",
            ))
        elif 0 <= ceiling_clear <= RESTS_ON_PLAYER_HEIGHTS * height:
            out.append(Relation(
                kind="rests_on", subject=sprite_ref, object=_ref("sector", sector_id),
                measures={"surface": "ceiling",
                          "clearance_player_heights": round(ceiling_clear / height, 4)},
                basis="sprite z within one clearance band of the sector ceiling plane",
            ))
    return out


def _line_deviation(points: Sequence[tuple[float, float]]) -> float:
    """Largest perpendicular distance from the line through the end points."""
    if len(points) < 3:
        return 0.0
    (ax, ay), (bx, by) = points[0], points[-1]
    length = hypot(bx - ax, by - ay)
    if length == 0:
        return max(hypot(px - ax, py - ay) for px, py in points)
    return max(
        abs((bx - ax) * (ay - py) - (ax - px) * (by - ay)) / length
        for px, py in points
    )


def _repeat_relations(
    build: BuildIR, hood: Neighborhood, width: int, height: int,
) -> list[Relation]:
    """Runs of identical sprites, evenly spaced in plan or in z.

    Sectors are deliberately excluded: a run of repeating sectors is a stair or
    a landing, and `structures.py` already recovers those with a richer
    parameter set. Duplicating it here would produce two names for one fact.
    """
    out: list[Relation] = []
    by_picnum: dict[int, list[int]] = defaultdict(list)
    for sprite_id in hood.sprites:
        by_picnum[int(build.sprites[sprite_id]["fields"]["picnum"])].append(sprite_id)

    for picnum, members in sorted(by_picnum.items()):
        if len(members) < REPEAT_MIN_MEMBERS:
            continue
        points = {
            sprite_id: (
                int(build.sprites[sprite_id]["fields"]["x"]),
                int(build.sprites[sprite_id]["fields"]["y"]),
                int(build.sprites[sprite_id]["fields"]["z"]),
            )
            for sprite_id in members
        }
        # Plan run: collinear in XY, evenly spaced.
        plan = sorted(members, key=lambda s: (points[s][0], points[s][1]))
        plan_xy = [(points[s][0], points[s][1]) for s in plan]
        if _line_deviation(plan_xy) <= REPEAT_COLLINEAR_PLAYER_WIDTHS * width:
            gaps = [
                hypot(b[0] - a[0], b[1] - a[1])
                for a, b in zip(plan_xy, plan_xy[1:])
            ]
            relation = _even_run(
                "plan", picnum, _canonical_order(plan), gaps,
                unit=width, unit_name="player_widths")
            if relation is not None:
                out.append(relation)
        # Vertical run: same plan position, evenly spaced in z. Blood z grows
        # downward, so sorting by z runs top-down; the spacing is what matters.
        column = sorted(members, key=lambda s: points[s][2])
        column_xy = [(points[s][0], points[s][1]) for s in column]
        if _line_deviation(column_xy) <= REPEAT_COLLINEAR_PLAYER_WIDTHS * width and all(
            hypot(b[0] - a[0], b[1] - a[1]) <= REPEAT_COLLINEAR_PLAYER_WIDTHS * width
            for a, b in zip(column_xy, column_xy[1:])
        ):
            gaps = [abs(points[b][2] - points[a][2]) for a, b in zip(column, column[1:])]
            relation = _even_run(
                "vertical", picnum, column, gaps, unit=height, unit_name="player_heights")
            if relation is not None:
                out.append(relation)
    return out


def _canonical_order(members: Sequence[int]) -> list[int]:
    """Orient a plan run without reference to the world frame.

    A run of identical sprites has no inherent direction, but sorting the
    members by position gives it one -- and a 180-degree rotation reverses it,
    which made the very first invariance run disagree with itself. Rotation
    preserves the sequence up to reversal, so pick whichever end makes the id
    sequence smaller and the choice becomes a property of the run, not of north.
    """
    forward = list(members)
    return min(forward, forward[::-1])


def _even_run(
    axis: str, picnum: int, members: Sequence[int], gaps: Sequence[float],
    *, unit: int, unit_name: str,
) -> Relation | None:
    if len(gaps) < REPEAT_MIN_MEMBERS - 1 or min(gaps) <= 0:
        return None
    spacing = mean(gaps)
    cv = pstdev(gaps) / spacing if spacing else 1.0
    if cv > REPEAT_SPACING_CV:
        return None
    return Relation(
        kind="repeats_along",
        members=tuple(_ref("sprite", sprite_id) for sprite_id in members),
        measures={
            "axis": axis,
            "count": len(members),
            "picnum": picnum,
            f"spacing_{unit_name}": round(spacing / unit, 4),
            "spacing_variation": round(cv, 4),
        },
        basis=f"identical picnum, collinear centres, even {axis} spacing "
              f"(cv <= {REPEAT_SPACING_CV})",
    )


def _sector_relations(
    build: BuildIR, hood: Neighborhood, geometry: dict[int, dict[str, Any]],
    spatial: dict[str, Any], width: int, height: int,
) -> list[Relation]:
    """adjacent_to, above, inside, shares_plane, shares_material."""
    out: list[Relation] = []
    selected = set(hood.sectors)

    for edge in spatial["views"]["geometry"]["portals"]:
        left, right = (_id(ref) for ref in edge["sectors"])
        if left not in selected or right not in selected:
            continue
        low, high = (left, right) if left < right else (right, left)
        out.append(Relation(
            kind="adjacent_to", subject=_ref("sector", low), object=_ref("sector", high),
            measures={
                "width_player_widths": round(edge["width"] / width, 4),
                "opening_player_heights": round(edge["at_rest_opening"] / height, 4),
                "step_player_heights": round(edge["floor_delta"] / height, 4),
                "blocking_flag": bool(edge["blocking_flag"]),
            },
            basis=f"spatial.analyze_spatial {edge['id']}",
        ))

    ordered = sorted(geometry)
    for index, upper in enumerate(ordered):
        for lower in ordered[index + 1:]:
            for a, b in ((upper, lower), (lower, upper)):
                top, bottom = geometry[a], geometry[b]
                overlap = _bbox_overlap_fraction(top["bounds"], bottom["bounds"])
                if overlap <= 0 or top["floor_z"] > bottom["ceiling_z"]:
                    continue
                out.append(Relation(
                    kind="above", subject=_ref("sector", a), object=_ref("sector", b),
                    measures={
                        "plan_bbox_overlap_fraction": round(overlap, 4),
                        "gap_player_heights": round(
                            (bottom["ceiling_z"] - top["floor_z"]) / height, 4),
                    },
                    basis="plan bounding-box overlap with the subject's floor at or "
                          "above the object's ceiling (Blood z grows downward)",
                ))

    for outer in ordered:
        for inner in ordered:
            if inner == outer or geometry[inner]["area"] >= geometry[outer]["area"]:
                continue
            ob, ib = geometry[outer]["bounds"], geometry[inner]["bounds"]
            if not (ob[0] <= ib[0] and ob[1] <= ib[1] and ob[2] >= ib[2] and ob[3] >= ib[3]):
                continue
            if point_in_loop(_centroid(geometry[inner]["outer"]),
                             geometry[outer]["outer"]) != 1:
                continue
            out.append(Relation(
                kind="inside", subject=_ref("sector", inner), object=_ref("sector", outer),
                measures={"area_fraction": round(
                    geometry[inner]["area"] / max(1.0, geometry[outer]["area"]), 4)},
                basis="plan bounds contained and inner centroid inside the outer loop",
            ))

    for surface in ("floor", "ceiling"):
        planes: dict[int, list[int]] = defaultdict(list)
        for sector_id in ordered:
            planes[geometry[sector_id][f"{surface}_z"]].append(sector_id)
        for _z, members in sorted(planes.items()):
            if len(members) < 2:
                continue
            out.append(Relation(
                kind="shares_plane",
                members=tuple(_ref("sector", value) for value in sorted(members)),
                measures={"surface": surface, "count": len(members)},
                basis=f"identical native {surface}_z",
            ))
        materials: dict[int, list[int]] = defaultdict(list)
        for sector_id in ordered:
            materials[geometry[sector_id][f"{surface}_picnum"]].append(sector_id)
        for picnum, members in sorted(materials.items()):
            if len(members) < 2:
                continue
            out.append(Relation(
                kind="shares_material",
                members=tuple(_ref("sector", value) for value in sorted(members)),
                measures={"surface": surface, "picnum": picnum, "count": len(members)},
                basis=f"identical native {surface}_picnum",
            ))
    return out


def extract_relations(
    build: BuildIR,
    *,
    sectors: Iterable[int] | None = None,
    sprites: Iterable[int] | None = None,
    hops: int = 1,
    game: str = "blood",
    source: str | None = None,
    population: str | None = None,
) -> dict[str, Any]:
    """Dump every object-scale relation in one local neighborhood.

    The document is deterministic and frame-independent: the same neighborhood
    of a translated or quarter-turn-rotated map produces an identical
    `relations` list.
    """
    hood = neighborhood(build, sectors=sectors, sprites=sprites, hops=hops)
    profile = player_profile(game)
    width, height = profile.body_width, profile.standing_height
    geometry = _sector_geometry(build, hood.sectors)
    spatial = analyze_spatial(build, hood.sectors)

    relations = [
        *_sprite_relations(build, hood, geometry, width, height),
        *_repeat_relations(build, hood, width, height),
        *_sector_relations(build, hood, geometry, spatial, width, height),
    ]
    leaked = sorted({
        key for relation in relations for key in relation.measures
        if key in FORBIDDEN_MEASURE_KEYS
    })
    if leaked:
        raise RelationError(f"relation measures leaked a world frame: {leaked}")
    relations.sort(key=Relation.sort_key)

    counts: dict[str, int] = defaultdict(int)
    for relation in relations:
        counts[relation.kind] += 1
    return {
        "$schema": SCHEMA,
        "schema_version": SCHEMA_VERSION,
        "source": source,
        "population": population,
        "game": game,
        "player_profile": {"body_width": width, "standing_height": height},
        "neighborhood": hood.to_dict(),
        "relation_kinds": dict(RELATION_KINDS),
        "counts": {kind: counts[kind] for kind in sorted(counts)},
        "relations": [relation.to_dict() for relation in relations],
        "limitations": [
            "Frame independence is claimed for translation and quarter-turn "
            "rotation only -- the exact-integer transform Build geometry admits. "
            "Mirroring reverses wall winding and is not claimed.",
            "plan_bbox_overlap_fraction is a bounding-box overlap, not a polygon "
            "intersection.",
            "repeats_along covers sprites only; repeating sectors are stairs and "
            "landings, which structures.py already recovers.",
            "rests_on states that a sprite sits within a clearance band of a "
            "surface. It does not read tile heights, so it is not contact.",
            "No relation here names an object. Interpretation is a later pass.",
        ],
    }


# ---------------------------------------------------------------------------
# Context signatures: one neighborhood reduced to a comparable key
# ---------------------------------------------------------------------------
#
# A relation document is inspectable but not comparable: two neighborhoods
# with the same structure have different primitive ids. A signature is the
# discrete reduction that makes them group. It lives here rather than in a
# consumer because both the anchor query and the unsigned pattern pipeline
# need exactly this key, and two copies would drift.

def _fraction_band(part: int, whole: int) -> str:
    if whole == 0:
        return "none"
    if part == 0:
        return "none"
    return "all" if part == whole else "some"


def _count_band(value: int) -> str:
    if value <= 0:
        return "0"
    if value == 1:
        return "1"
    return "2" if value == 2 else "3+"


#: What a sector holds. Meaningful with the sector alone -- scale 1.
OBJECT_FACETS = ("objects", "seated", "wallbound", "run")
#: How a sector sits among its neighbours. Needs the neighbours -- scale 2.
CONTEXT_FACETS = ("portals", "enclosed", "stacked", "coplanar")


def context_signature(
    document: dict[str, Any], sector_id: int, *, facets: Sequence[str] | None = None,
) -> str:
    """Reduce one carrying sector's relation neighborhood to a discrete key.

    Every facet is read from Phase 1 relations, so the signature inherits their
    frame independence: the same place in a translated or rotated map keys the
    same. It describes the sector's *role* in its neighborhood, not its shape,
    which is what makes two occurrences in different maps comparable.

    `facets` restricts the key. A hops=0 neighborhood is one sector, so every
    `CONTEXT_FACETS` relation is absent *by construction* there -- a scale-1
    signature that reported `portals:0` for a sector with four portals would be
    stating an artefact of the selection as a fact about the map.
    """
    ref = f"sector:{sector_id}"
    relations = document["relations"]
    portals = sum(
        1 for item in relations
        if item["kind"] == "adjacent_to" and ref in (item["subject"], item["object"])
    )
    enclosed = any(
        item["kind"] == "inside" and item["subject"] == ref for item in relations
    )
    over = any(item["kind"] == "above" and item["subject"] == ref for item in relations)
    under = any(item["kind"] == "above" and item["object"] == ref for item in relations)
    coplanar = any(
        item["kind"] == "shares_plane" and ref in item.get("members", [])
        for item in relations
    )
    own = {
        item["subject"] for item in relations
        if item["kind"] == "in_sector" and item["object"] == ref
    }
    seated = sum(
        1 for item in relations
        if item["kind"] == "rests_on" and item["subject"] in own
    )
    wallbound = sum(
        1 for item in relations
        if item["kind"] == "against_wall" and item["subject"] in own
    )
    in_run = any(
        item["kind"] == "repeats_along" and own & set(item.get("members", []))
        for item in relations
    )
    stacked = "both" if over and under else "over" if over else "under" if under else "none"
    values = {
        "portals": _count_band(portals),
        "enclosed": "yes" if enclosed else "no",
        "stacked": stacked,
        "coplanar": "yes" if coplanar else "no",
        "objects": _count_band(len(own)),
        "seated": _fraction_band(seated, len(own)),
        "wallbound": _fraction_band(wallbound, len(own)),
        "run": "yes" if in_run else "no",
    }
    wanted = tuple(facets) if facets is not None else CONTEXT_FACETS + OBJECT_FACETS
    unknown = [name for name in wanted if name not in values]
    if unknown:
        raise RelationError(f"unknown signature facets: {unknown}")
    return "|".join(f"{name}:{values[name]}" for name in wanted)


def signature_facets(signature: str) -> dict[str, str]:
    return dict(part.split(":", 1) for part in signature.split("|") if ":" in part)



# ---------------------------------------------------------------------------
# Pilot mining: the same extractor, run over a population
# ---------------------------------------------------------------------------


def sprite_dense_seeds(build: BuildIR, *, limit: int) -> list[int]:
    """The sectors carrying the most sprites, as neighborhood seeds.

    Object-scale relations only exist where objects are. Seeding on sprite
    density picks the neighborhoods with something to say without hand-picking
    them per map, which would smuggle the answer into the sample.
    """
    counts: dict[int, int] = defaultdict(int)
    for sprite in build.sprites:
        counts[int(sprite["fields"]["sector"])] += 1
    ranked = sorted(counts.items(), key=lambda item: (-item[1], item[0]))
    return [sector_id for sector_id, _count in ranked[:limit]
            if 0 <= sector_id < len(build.sectors)]


def _bin(value: float, edges: Sequence[float], labels: Sequence[str]) -> str:
    for edge, label in zip(edges, labels):
        if value < edge:
            return label
    return labels[-1]


#: Binned distributions worth aggregating. Binning, not raw values: a
#: distribution over 40k measurements is evidence, a list of them is a dump.
_DISTRIBUTIONS = {
    ("against_wall", "distance_player_widths"):
        ((0.1, 0.3, 0.5), ("flush", "near", "offset", "loose")),
    ("rests_on", "clearance_player_heights"):
        ((0.001, 0.05, 0.1), ("exact", "sub_step", "step", "band")),
    ("adjacent_to", "width_player_widths"):
        ((1.0, 2.0, 4.0), ("under_one_body", "one_to_two", "two_to_four", "wide")),
    ("above", "gap_player_heights"):
        ((0.001, 0.5, 1.0, 2.0), ("flush", "under_half", "half_to_one",
                                  "one_to_two", "over_two")),
    ("repeats_along", "spacing_player_widths"):
        ((1.0, 2.0, 4.0), ("tight", "one_to_two", "two_to_four", "wide")),
}


def mine_relations(
    directory: str | Path | None = None,
    *,
    population: str = "blood-campaign",
    maps: int = 5,
    seeds_per_map: int = 3,
    hops: int = 1,
    game: str = "blood",
) -> dict[str, Any]:
    """Run the extractor over a population and report what recurs.

    A pilot, and labelled one: it samples the sprite-densest neighborhoods of
    the first `maps` maps, and says so. It proves the extractor runs on real
    maps and produces comparable output; it is not a corpus-wide statistic.
    """
    from .format import read_map
    from .patterns import list_corpus_maps

    selected = list_corpus_maps(directory, population=population)[:maps]
    if not selected:
        raise RelationError(f"no maps for population {population!r}")

    kind_counts: dict[str, int] = defaultdict(int)
    per_map: list[dict[str, Any]] = []
    distributions: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))
    faces_exact = 0
    faces_total = 0
    runs: list[dict[str, Any]] = []
    errors: list[dict[str, str]] = []

    for item in selected:
        try:
            build = read_map(item.path).to_build_ir()
            seeds = sprite_dense_seeds(build, limit=seeds_per_map)
            if not seeds:
                errors.append({"map": item.name, "error": "no sprites to seed on"})
                continue
            document = extract_relations(
                build, sectors=seeds, hops=hops, game=game,
                source=item.name, population=item.population,
            )
        except Exception as exc:                       # reported, never swallowed
            errors.append({"map": item.name, "error": f"{type(exc).__name__}: {exc}"})
            continue
        for kind, count in document["counts"].items():
            kind_counts[kind] += count
        for relation in document["relations"]:
            kind = relation["kind"]
            for measure, (edges, labels) in _DISTRIBUTIONS.items():
                if measure[0] == kind and measure[1] in relation["measures"]:
                    key = f"{measure[0]}.{measure[1]}"
                    distributions[key][_bin(relation["measures"][measure[1]], edges, labels)] += 1
            if kind == "faces_wall":
                faces_total += 1
                faces_exact += relation["measures"]["angle_from_inward_normal"] == 0
            if kind == "repeats_along":
                runs.append({
                    "map": item.name, "population": item.population,
                    "members": relation["members"], **relation["measures"],
                })
        per_map.append({
            "map": item.name, "population": item.population,
            "seed_sectors": seeds, "neighborhood": document["neighborhood"],
            "counts": document["counts"],
        })

    runs.sort(key=lambda run: (-run["count"], run["map"], run["members"][0]))
    return {
        "$schema": "llmapper.object-relation-pilot",
        "schema_version": SCHEMA_VERSION,
        "population": population,
        "sampling": (
            f"the {seeds_per_map} sprite-densest sectors of the first {maps} maps, "
            f"expanded {hops} portal hop(s)"
        ),
        "maps_sampled": len(per_map),
        "relation_kinds": dict(RELATION_KINDS),
        "counts": {kind: kind_counts[kind] for kind in sorted(kind_counts)},
        "distributions": {key: dict(value) for key, value in sorted(distributions.items())},
        "faces_wall_exactly_perpendicular": {
            "count": faces_exact, "of": faces_total,
            "fraction": round(faces_exact / faces_total, 4) if faces_total else None,
        },
        "repeating_runs": runs,
        "per_map": per_map,
        "errors": errors,
        "limitations": [
            "A pilot over sampled neighborhoods, not a corpus statistic. It says "
            "what the extractor produces, not what Blood usually does.",
            "Seeds are the sprite-densest sectors, so the sample is biased toward "
            "furnished rooms -- deliberately, since that is where object-scale "
            "relations exist at all.",
            "Every relation is an OBSERVATION. Nothing here is interpreted.",
        ],
    }
