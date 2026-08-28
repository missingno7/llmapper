"""Authoring vocabulary: composable structures over :class:`PlanarLayout`.

Every constructor here earned its place from corpus evidence, and every entry
carries that evidence in :data:`CORPUS_SUPPORT` so the reason can be re-read and
disagreed with.  The rule is deliberately strict, because a vocabulary that
grows on taste stops being knowledge:

* a concept becomes a **constructor** only when it occurs across most original
  maps and a compact parameter set reproduces held-out examples;
* a concept that occurs but does not transfer stays **compositional** -- you can
  still build it, out of the pieces, in the one map that needs it;
* a concept that is a consequence of other decisions rather than a thing you
  draw stays a **relation** for search and never becomes a constructor.

Composition, not parameter count, is how this layer gets expressive.  A
``staircase`` does not grow a ``railing=``, ``lamps=`` or ``landing=`` argument;
it exposes anchors and accepts decorations.

Nothing in this module reads or writes an authored label as evidence, and
nothing here compiles: the output is more ``PlanarLayout`` source.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from math import atan2, cos, hypot, radians, sin
from typing import Any, Iterable, Sequence

from .planar_geom import Point, area2
from .planar_layout import PlanarLayout, PlanarLayoutError

SCHEMA = "llmapper.authoring-vocabulary"
SCHEMA_VERSION = 1

#: Mined from ``maps/blood`` E?M*.MAP with :mod:`bloodmap.structures`.  42 maps
#: analysed (E6M7 is excluded: its sector 144 has invalid wall ownership and
#: ``analyze_spatial`` refuses it, which predates this module).  The fit set is
#: episodes 1-3 and the held-out set is episodes 4 and 6.
CORPUS_SUPPORT: dict[str, dict[str, Any]] = {
    "staircase": {
        "derived_from": "structures.stepped_run",
        "occurrences": 186,
        "maps_with_at_least_one": "38/42",
        "essential_parameters": ["total_rise", "tread", "clear_height"],
        "expressive_parameters": ["step_rise", "shade_ramp"],
        "residual_not_exposed": [
            "per-step width variation (median 5.5% of the mean, no transfer)",
            "single odd lead-in rises (2 of 59 held-out runs begin with 1024)",
        ],
        "step_rise_vocabulary": [2048, 3072, 4096],
        "held_out_test": (
            "the fitted rise vocabulary explains 48/59 held-out runs exactly as a "
            "constant rise, 9 more using only fitted values, leaving 2 residual"
        ),
        "decision": "global constructor",
    },
    "recess": {
        "derived_from": "structures.recess",
        "occurrences": 792,
        "maps_with_at_least_one": "42/42",
        "essential_parameters": ["depth", "opening width (implied by the anchor)"],
        "expressive_parameters": ["ceiling_drop", "floor_delta"],
        "residual_not_exposed": ["exact footprint shape"],
        "corpus_profile": {
            "floor_flush_fraction": {"fit": 0.719, "held_out": 0.777},
            "lower_ceiling_fraction": {"fit": 0.346, "held_out": 0.301},
            "area_fraction_of_host_median": {"fit": 0.0521, "held_out": 0.0582},
        },
        "held_out_test": "every profile figure moves by less than 0.06 across the split",
        "decision": "global constructor",
    },
    "arc": {
        "derived_from": "morphology segmented-arc chains",
        "occurrences": 1473,
        "maps_with_at_least_one": "41/42",
        "essential_parameters": ["center", "radius", "sweep_deg", "segments"],
        "expressive_parameters": ["start_deg"],
        "residual_not_exposed": ["per-vertex integer rounding"],
        "corpus_profile": {
            "chains_per_map_median": 30,
            "segments_per_chain_median": {"fit": 7, "held_out": 8},
            "turn_per_segment_deg_median": {"fit": 28.8, "held_out": 22.5},
            "segment_length_player_widths_median": {"fit": 1.012, "held_out": 0.816},
            "sweep_deg_median": {"fit": 167.2, "held_out": 167.8},
            "relative_turn_stdev_median": {"fit": 0.016, "held_out": 0.023},
        },
        "held_out_test": (
            "turns inside a chain are uniform to within 2% of their mean, so one "
            "constant-turn constructor reproduces the chain shape"
        ),
        "decision": "global constructor",
        "note": (
            "original curvature is mostly many small features -- eight segments of "
            "about one player width -- not a few grand curved rooms"
        ),
    },
    "landing": {
        "derived_from": "structures.landing",
        "occurrences": 19,
        "maps_with_at_least_one": "12/42",
        "decision": "rejected as a parameter; compose two staircases against one region",
        "why": (
            "14 of the 19 are ordinary rooms above 10 player areas that two stairs "
            "happen to meet in, and 4 of the 5 genuinely stair-sized ones are in "
            "E4M6 alone. A landing= argument would encode one map's habit"
        ),
    },
    "overlook": {
        "derived_from": "structures.overlook",
        "occurrences": 4764,
        "maps_with_at_least_one": "42/42",
        "decision": "relation, indexed for search, no constructor",
        "why": (
            "an overlook is what happens when an open portal spans more than one "
            "player step; it is a consequence of two height decisions, not a thing "
            "drawn separately, and a constructor would only re-say the heights"
        ),
    },
    "pit": {
        "derived_from": "structures.pit",
        "occurrences": 146,
        "maps_with_at_least_one": "33/42",
        "decision": "relation, indexed for search, no constructor",
        "why": "same as overlook, in the other direction",
    },
    "embedded_shell": {
        "derived_from": "structures.embedded_shell",
        "occurrences": 467,
        "maps_with_at_least_one": "40/42",
        "decision": "already global as PlanarLayout.insert_building_shell; principle refined",
        "principle": (
            "originals draw shells non-rectangular (22% of fit and 26% of held-out "
            "shells are quadrilaterals) and large (the enclosed footprint is about "
            "53% of the host plus itself in both halves of the split)"
        ),
    },
}


class VocabularyError(PlanarLayoutError):
    """A structure request cannot be expressed as valid planar source."""


def _point(value: Sequence[float]) -> Point:
    return (int(round(value[0])), int(round(value[1])))


@dataclass(frozen=True)
class Anchor:
    """A directed edge of a region outline: the face a structure grows from.

    ``a -> b`` must run the same way the region's outline runs, which for a
    Build outer loop means the region lies to the *left*.  Structures therefore
    grow to the right, and because the constructor generates both sides of the
    shared edge it cannot get the winding backwards -- which is the single
    mistake that costs the most time when the same geometry is written by hand.
    """

    region_id: str
    a: Point
    b: Point

    @property
    def width(self) -> float:
        return hypot(self.b[0] - self.a[0], self.b[1] - self.a[1])

    @property
    def direction(self) -> tuple[float, float]:
        length = self.width
        if length == 0:
            raise VocabularyError(f"anchor on {self.region_id} has zero length")
        return ((self.b[0] - self.a[0]) / length, (self.b[1] - self.a[1]) / length)

    @property
    def outward(self) -> tuple[float, float]:
        """Unit normal pointing away from the region the anchor belongs to."""
        dx, dy = self.direction
        return (dy, -dx)

    def offset(self, distance: float) -> "Anchor":
        nx, ny = self.outward
        return Anchor(
            self.region_id,
            _point((self.a[0] + nx * distance, self.a[1] + ny * distance)),
            _point((self.b[0] + nx * distance, self.b[1] + ny * distance)),
        )

    def reversed(self, region_id: str) -> "Anchor":
        """The same edge as seen from the region on the other side."""
        return Anchor(region_id, self.b, self.a)

    def to_dict(self) -> dict[str, Any]:
        return {"region": self.region_id, "a": list(self.a), "b": list(self.b)}


@dataclass(frozen=True)
class Decoration:
    """A sprite to hang on a structure, sized from the tile's real ART pixels.

    ``player_heights`` is what the decoration should actually measure in the
    room it lands in.  Build draws a sprite at ``tile_pixels * repeat * 4`` world
    units, so the repeat is derived rather than copied; copied repeats are how
    the previous pilot shipped eighteen decorations taller than the space they
    stood in.
    """

    decoration_id: str
    picnum: int
    player_heights: float
    where: str = "flank"
    cstat: int = 16
    shade: int = -8
    aspect: float = 1.0
    every: int = 1
    t: float = 0.5
    height_player_heights: float = 0.65
    extra: dict[str, Any] = field(default_factory=dict)


WHERE_VALUES = {"flank", "tread", "back", "floor"}

#: Blood's player, restated so this module stays free of a profile lookup at
#: import time.  ``bloodmap.player_space.player_profile("blood")`` is the source.
PLAYER_WIDTH = 384

from .player_space import PLAYER_PROFILES

#: One standing human, from the player profile. Never hardcode this: it was
#: 0x1600 in a dozen modules, which is `POSTURE.eyeAboveZ` -- an offset from
#: the sprite's centre, not a body -- and every height in the project was
#: denominated in a unit 3x too small.
PLAYER_HEIGHT = PLAYER_PROFILES["blood"].standing_height


def sprite_repeats(
    picnum: int, player_heights: float, art_sizes: dict[int, tuple[int, int]],
    *, aspect: float = 1.0,
) -> dict[str, int]:
    """Repeats that make ``picnum`` the stated number of player heights tall."""
    size = art_sizes.get(int(picnum))
    if size is None:
        raise VocabularyError(
            f"no ART size known for tile {picnum}; read it from the game's ART "
            "files rather than guessing a repeat"
        )
    height = int(size[1])
    if height <= 0:
        raise VocabularyError(f"tile {picnum} has no pixel height")
    y_repeat = max(4, min(255, round(player_heights * PLAYER_HEIGHT / (height * 4))))
    return {"y_repeat": y_repeat, "x_repeat": max(4, min(255, round(y_repeat * aspect)))}


def art_sizes_from_directory(directory: str) -> dict[int, tuple[int, int]]:
    """Real tile dimensions from the game's ART files, for :func:`sprite_repeats`."""
    from .art import read_art_directory

    return {
        tile_id: (int(tile.width), int(tile.height))
        for tile_id, tile in read_art_directory(directory).items()
    }


@dataclass
class Structure:
    """A generated group of regions with anchors other structures can grow from."""

    structure_id: str
    kind: str
    layout: PlanarLayout
    regions: tuple[str, ...]
    far: Anchor | None = None
    flanks: tuple[Anchor, ...] = ()
    provenance: dict[str, Any] = field(default_factory=dict)
    _decorations: int = 0

    def arrive_at(self, region_id: str, **connection: Any) -> str:
        """Connect this structure's far face to an existing region."""
        if self.far is None:
            raise VocabularyError(f"{self.structure_id} has no far face to arrive with")
        connection.setdefault("min_width", max(512, int(self.far.width)))
        return self.layout.add_connection(
            f"connection:{self.structure_id}:arrive", self.regions[-1], region_id,
            a1=self.far.a, a2=self.far.b, **connection,
        )

    def decorate(self, *decorations: Decoration, art_sizes: dict[int, tuple[int, int]]) -> "Structure":
        """Hang decorations on this structure without widening its constructor."""
        for decoration in decorations:
            if decoration.where not in WHERE_VALUES:
                raise VocabularyError(
                    f"unknown decoration placement {decoration.where!r}; expected one of "
                    f"{sorted(WHERE_VALUES)}"
                )
            fields = {
                "type": 0, "picnum": int(decoration.picnum), "cstat": int(decoration.cstat),
                "shade": int(decoration.shade),
                **sprite_repeats(
                    decoration.picnum, decoration.player_heights, art_sizes,
                    aspect=decoration.aspect,
                ),
                **decoration.extra,
            }
            self._place(decoration, fields)
        return self

    def _place(self, decoration: Decoration, fields: dict[str, Any]) -> None:
        targets: list[tuple[str, Anchor | None]]
        if decoration.where in {"flank", "back"}:
            targets = [(anchor.region_id, anchor) for anchor in self.flanks]
        else:
            targets = [(region_id, None) for region_id in self.regions]
        for index, (region_id, anchor) in enumerate(targets):
            if index % max(1, decoration.every):
                continue
            self._decorations += 1
            placement_id = f"placement:{self.structure_id}:{decoration.decoration_id}:{self._decorations:03d}"
            if anchor is None:
                self.layout.place_on_floor(
                    placement_id, region_id, local=(0.5, 0.5),
                    height_player_heights=decoration.height_player_heights, **fields,
                )
            else:
                self.layout.place_on_wall(
                    placement_id, region_id, a1=anchor.a, a2=anchor.b, t=decoration.t,
                    height_player_heights=decoration.height_player_heights, **fields,
                )

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.structure_id,
            "kind": self.kind,
            "regions": list(self.regions),
            "far": None if self.far is None else self.far.to_dict(),
            "flanks": [anchor.to_dict() for anchor in self.flanks],
            "provenance": dict(self.provenance),
        }


def staircase(
    layout: PlanarLayout,
    structure_id: str,
    *,
    base: Anchor,
    total_rise: int,
    tread: int,
    clear_height: int,
    step_rise: int = 4096,
    base_floor_z: int | None = None,
    shade_ramp: tuple[int, int] | None = None,
    role: str = "stair",
    intent: dict[str, Any] | None = None,
    connection: dict[str, Any] | None = None,
    **surface: Any,
) -> Structure:
    """A monotone run of equal steps growing outward from ``base``.

    Corpus support: :data:`CORPUS_SUPPORT`\\ ``["staircase"]``.  ``step_rise``
    defaults to 4096 because that is both the player's maximum step and the most
    common rise in the corpus by two to one; 2048 and 3072 are the only other
    values the corpus uses often enough to be worth naming.

    ``total_rise`` must be a whole number of steps.  Width is not a parameter --
    it is the length of ``base`` -- and neither is a landing, which the corpus
    does not support as a stair component (see the rejection note).
    """
    if step_rise == 0:
        raise VocabularyError("step_rise must be nonzero")
    if total_rise == 0:
        raise VocabularyError("a staircase must change height")
    if (total_rise > 0) != (step_rise > 0):
        step_rise = -step_rise
    if total_rise % step_rise:
        steps = abs(total_rise) / abs(step_rise)
        legal = [
            value for value in (4096, 3072, 2048)
            if abs(total_rise) % value == 0
        ]
        raise VocabularyError(
            f"{structure_id}: total_rise {total_rise} is {steps:.2f} steps of {step_rise}; "
            f"the corpus rises that divide it exactly are {legal or 'none'}"
        )
    if abs(step_rise) > 4096:
        raise VocabularyError(
            f"{structure_id}: a {abs(step_rise)}-unit rise is taller than the player can "
            "step; that is an overlook, not a stair"
        )
    if tread <= 0 or clear_height <= 0:
        raise VocabularyError(f"{structure_id}: tread and clear_height must be positive")
    if base_floor_z is None:
        base_floor_z = layout.regions[base.region_id].floor_z if base.region_id in layout.regions else 0

    count = total_rise // step_rise
    connection = dict(connection or {})
    connection.setdefault("min_width", max(512, int(base.width)))
    regions: list[str] = []
    flanks: list[Anchor] = []
    previous_region, previous_anchor = base.region_id, base
    for index in range(1, count + 1):
        near, far = base.offset(tread * (index - 1)), base.offset(tread * index)
        outline_points = [near.a, far.a, far.b, near.b]
        if area2(tuple(outline_points)) < 0:
            outline_points = [near.b, far.b, far.a, near.a]
        floor_z = base_floor_z + step_rise * index
        region_id = f"region:{structure_id}:step_{index:02d}"
        fields = dict(surface)
        if shade_ramp is not None:
            start, end = shade_ramp
            span = max(1, count - 1)
            value = int(round(start + (end - start) * (index - 1) / span))
            fields.setdefault("floor_shade", value)
            fields.setdefault("ceiling_shade", value)
            fields.setdefault("wall_shade", max(-128, value - 2))
        step_intent = dict(intent or {})
        step_intent.setdefault("purpose", f"{structure_id} step {index} of {count}")
        layout.add_region(
            region_id, outline_points, role=role,
            floor_z=floor_z, ceiling_z=floor_z - clear_height,
            intent=step_intent, **fields,
        )
        layout.add_connection(
            f"connection:{structure_id}:step_{index:02d}",
            previous_region, region_id,
            a1=previous_anchor.a, a2=previous_anchor.b, **connection,
        )
        regions.append(region_id)
        # The two side faces of this step, wound as this region's own outline
        # runs them, so a decoration anchored to either lands inside the sector.
        flanks.append(Anchor(region_id, outline_points[0], outline_points[1]))
        flanks.append(Anchor(region_id, outline_points[2], outline_points[3]))
        previous_region, previous_anchor = region_id, Anchor(region_id, far.a, far.b)

    return Structure(
        structure_id=structure_id, kind="staircase", layout=layout,
        regions=tuple(regions), far=previous_anchor, flanks=tuple(flanks),
        provenance={
            "vocabulary": "bloodmap.vocabulary.staircase",
            "corpus_support": CORPUS_SUPPORT["staircase"]["held_out_test"],
            "steps": count, "step_rise": step_rise, "tread": tread,
            "width": round(base.width, 1), "total_rise": total_rise,
        },
    )


def recess(
    layout: PlanarLayout,
    structure_id: str,
    *,
    anchor: Anchor,
    depth: int,
    clear_height: int | None = None,
    ceiling_drop: int = 0,
    floor_delta: int = 0,
    role: str = "detail",
    intent: dict[str, Any] | None = None,
    connection: dict[str, Any] | None = None,
    **surface: Any,
) -> Structure:
    """A shallow dead end cut into one face of a host region.

    Corpus support: :data:`CORPUS_SUPPORT`\\ ``["recess"]``.  The corpus defaults
    are a flush floor (72-78% of originals) and an optional lowered ceiling
    (30-35%), so ``floor_delta`` and ``ceiling_drop`` both default to zero and
    are named when the design wants them.  The opening width is the anchor.
    """
    if depth <= 0:
        raise VocabularyError(f"{structure_id}: depth must be positive")
    host = layout.regions.get(anchor.region_id)
    if host is None:
        raise VocabularyError(f"{structure_id}: unknown host region {anchor.region_id!r}")
    far = anchor.offset(depth)
    outline_points = [anchor.a, far.a, far.b, anchor.b]
    if area2(tuple(outline_points)) < 0:
        outline_points = [anchor.b, far.b, far.a, anchor.a]
    floor_z = host.floor_z + floor_delta
    ceiling_z = (host.ceiling_z + ceiling_drop) if clear_height is None else floor_z - clear_height
    if ceiling_z > floor_z:
        raise VocabularyError(f"{structure_id}: the recess ceiling is below its floor")
    region_id = f"region:{structure_id}"
    recess_intent = dict(intent or {})
    recess_intent.setdefault("purpose", f"{structure_id} recess in {anchor.region_id}")
    layout.add_region(
        region_id, outline_points, role=role,
        floor_z=floor_z, ceiling_z=ceiling_z, intent=recess_intent, **surface,
    )
    options = dict(connection or {})
    options.setdefault("min_width", max(512, int(anchor.width)))
    layout.add_connection(
        f"connection:{structure_id}:mouth", anchor.region_id, region_id,
        a1=anchor.a, a2=anchor.b, **options,
    )
    return Structure(
        structure_id=structure_id, kind="recess", layout=layout,
        regions=(region_id,),
        far=Anchor(region_id, far.a, far.b),
        flanks=(Anchor(region_id, outline_points[1], outline_points[2]),),
        provenance={
            "vocabulary": "bloodmap.vocabulary.recess",
            "corpus_support": CORPUS_SUPPORT["recess"]["held_out_test"],
            "depth": depth, "opening_width": round(anchor.width, 1),
            "ceiling_drop": ceiling_drop, "floor_delta": floor_delta,
        },
    )


def arc_points(
    center: Sequence[float], radius: float, *,
    start_deg: float, sweep_deg: float, segments: int,
) -> list[Point]:
    """Vertices of a segmented arc, the way original maps build curvature.

    Corpus support: :data:`CORPUS_SUPPORT`\\ ``["arc"]``.  1473 chains across
    41 of 42 campaign maps, a median of 30 per map, 7-8 segments and 22-29
    degrees per segment, and turns uniform to within about 2% inside a chain --
    so one constant-turn generator is the right shape for the abstraction.

    The returned points include both endpoints and are meant to be spliced into
    an outline by :func:`outline`.
    """
    if segments < 1:
        raise VocabularyError("an arc needs at least one segment")
    if radius <= 0:
        raise VocabularyError("an arc needs a positive radius")
    result: list[Point] = []
    for index in range(segments + 1):
        angle = radians(start_deg + sweep_deg * index / segments)
        result.append(_point((center[0] + radius * cos(angle), center[1] + radius * sin(angle))))
    deduped: list[Point] = []
    for point in result:
        if not deduped or point != deduped[-1]:
            deduped.append(point)
    if len(deduped) < 2:
        raise VocabularyError(
            f"arc of radius {radius} in {segments} segments collapsed to one integer point; "
            "Build coordinates are integers, so a small arc needs fewer segments"
        )
    return deduped


def arc_through(
    a: Sequence[float], b: Sequence[float], *, bulge: float, segments: int,
) -> list[Point]:
    """A segmented arc from ``a`` to ``b`` bowing ``bulge`` units to its right.

    Same corpus support as :func:`arc_points`; this is the form an author can
    actually reach for, because an outline is written as a sequence of points
    and what you know at the point of writing is *these two corners* and *how
    far it should bow out*, not a centre and a radius.

    ``a`` and ``b`` are returned exactly, so the arc can be spliced into an
    outline whose neighbouring edges other regions already connect to.  Right is
    taken the same way :class:`Anchor` takes it: the outward side of ``a -> b``
    for a Build outer loop.
    """
    ax, ay = float(a[0]), float(a[1])
    bx, by = float(b[0]), float(b[1])
    chord = hypot(bx - ax, by - ay)
    if chord == 0:
        raise VocabularyError("an arc needs two distinct endpoints")
    if bulge == 0:
        raise VocabularyError("a zero bulge is a straight edge, not an arc")
    if segments < 2:
        raise VocabularyError("an arc through two points needs at least two segments")
    depth = float(bulge)
    # Circular segment: with chord c and sagitta s, the swept angle is
    # 4*atan(2s/c), which gives 180 degrees exactly when s is half the chord.
    sweep = 4.0 * atan2(2.0 * abs(depth), chord)
    radius = (chord * chord / 4.0 + depth * depth) / (2.0 * abs(depth))
    mx, my = (ax + bx) / 2.0, (ay + by) / 2.0
    ux, uy = (bx - ax) / chord, (by - ay) / chord
    # The right-hand normal of a -> b, matching Anchor.outward.
    nx, ny = uy, -ux
    sign = 1.0 if depth > 0 else -1.0
    offset = radius - abs(depth)
    cx, cy = mx - nx * offset * sign, my - ny * offset * sign
    start = atan2(ay - cy, ax - cx)
    end = atan2(by - cy, bx - cx)
    # Walk the short way round unless the bulge asked for the major arc.
    delta = end - start
    while delta <= -3.141592653589793:
        delta += 2.0 * 3.141592653589793
    while delta > 3.141592653589793:
        delta -= 2.0 * 3.141592653589793
    if abs(abs(delta) - sweep) > 1e-6 and abs(delta) < sweep:
        delta = (sweep if delta >= 0 else -sweep)
    result: list[Point] = [(int(round(ax)), int(round(ay)))]
    for index in range(1, segments):
        angle = start + delta * index / segments
        result.append(_point((cx + radius * cos(angle), cy + radius * sin(angle))))
    result.append((int(round(bx)), int(round(by))))
    deduped: list[Point] = []
    for point in result:
        if not deduped or point != deduped[-1]:
            deduped.append(point)
    if len(deduped) < 3:
        raise VocabularyError(
            "arc collapsed to a straight edge at Build integer resolution; "
            "use fewer segments or a larger bulge"
        )
    return deduped


def arc_turn_degrees(sweep_deg: float, segments: int) -> float:
    """The per-corner turn an arc will produce, for checking it against the corpus."""
    return abs(float(sweep_deg)) / max(1, int(segments))


def outline(*parts: Iterable[Sequence[float]]) -> list[Point]:
    """Concatenate outline pieces, dropping repeated and wrap-around duplicates."""
    result: list[Point] = []
    for part in parts:
        for value in part:
            point = _point(value)
            if not result or point != result[-1]:
                result.append(point)
    while len(result) > 1 and result[0] == result[-1]:
        result.pop()
    if len(result) < 3:
        raise VocabularyError("an outline needs at least three distinct points")
    return result


def vocabulary_manifest() -> dict[str, Any]:
    """What this vocabulary offers, what it refuses, and why."""
    return {
        "$schema": SCHEMA,
        "schema_version": SCHEMA_VERSION,
        "constructors": sorted(
            name for name, item in CORPUS_SUPPORT.items()
            if item["decision"] == "global constructor"
        ),
        "refused": {
            name: item["decision"] for name, item in CORPUS_SUPPORT.items()
            if item["decision"] != "global constructor"
        },
        "support": CORPUS_SUPPORT,
        "rules": [
            "a constructor must transfer to maps it was not derived from",
            "historical jitter is residual evidence, never an authoring parameter",
            "expressive power comes from composition, not from more arguments",
        ],
    }


# ---------------------------------------------------------------------------
# Stamping: arbitrary rotation, composed in floats and rounded exactly once
# ---------------------------------------------------------------------------

#: Slope direction and first-wall-relative texture alignment both reference a
#: sector's *first wall*, so an outline rotated as a whole -- winding intact,
#: first vertex still first -- carries them without being asked. Sprite angles
#: are absolute and do not follow; `stamp` rotates them explicitly.
#:
#: Whether to switch a rotated sector to relative alignment is a real question
#: and the campaign answers it: of 13,649 playable sectors, 14.0% align their
#: floor to the first wall. Split by cause, the signal is slope, not rotation --
#:
#:     floor / flat      11.0%        floor / cardinal   12.2%
#:     floor / sloped    43.2%        floor / angled     17.6%
#:
#: -- so a rotated room does *not* get relative alignment by default. Blood
#: leaves most of its angled floors world-aligned, which is fine for the rubble
#: and stone its flats mostly are. A *sloped* floor is the case that needs it,
#: at four times the base rate, because the slope direction is first-wall
#: relative and a world-aligned texture on it slides against its own gradient.
RELATIVE_ALIGNMENT = 64

#: The shortest edge a stamp will rotate. Rounding costs up to half a unit per
#: vertex, which is negligible against a wall and fatal against a chamfer.
MIN_STAMP_EDGE = 32


def stamp(
    points: Iterable[Sequence[float]],
    degrees: float,
    *,
    about: Sequence[float] = (0, 0),
    offset: Sequence[float] = (0, 0),
) -> list[Point]:
    """Rotate an outline by an arbitrary angle, rounding once at the end.

    This is the escape hatch `Frame` deliberately does not provide. A frame
    holds quarter-turns, which are exact; anything else accumulates half a unit
    of residual per vertex per level of nesting, and a residual that accumulates
    is how two rooms that should share an edge end up 1 unit apart with a sliver
    of solid space between them.

    The discipline that makes an arbitrary angle safe is the same one
    :func:`arc_through` follows, and it is the only reason this is allowed:

    * compose the whole transform in floating point -- rotation, offset, the
      lot -- and **round exactly once**, at emission;
    * emit before the planar overlay, so the arrangement sees integer points and
      both sides of a shared edge are generated from *the same* integers;
    * never re-round downstream, and never nest one stamp inside another.

    Residual is therefore bounded at half a unit per vertex and never
    accumulates, because nothing after this touches the coordinates again.

    `about` is the local point the rotation turns around, and `offset` is
    applied after it, so "turn the chapel 45 degrees about its own door and put
    the door here" is one call.

    A rotation preserves every edge length, so what rounding costs is measured
    against the *shortest* edge: half a unit of error on a 1024-unit wall is
    nothing, and on an 8-unit wall it is the wall. Below `MIN_STAMP_EDGE` this
    refuses rather than emitting a shape that is no longer the one written --
    a unit square stamped at 45 degrees comes back as a triangle with three
    collinear points, at exactly the right area, which is the kind of wrong that
    an area check would pass.
    """
    source = [(float(p[0]), float(p[1])) for p in points]
    if len(source) < 3:
        raise VocabularyError("an outline needs at least three points to stamp")
    shortest = min(
        hypot(source[i][0] - source[i - 1][0], source[i][1] - source[i - 1][1])
        for i in range(len(source)))
    if shortest < MIN_STAMP_EDGE:
        raise VocabularyError(
            "the shortest edge of this outline is %.1f units, and a stamp rounds "
            "each vertex by up to half a unit. Below %d units that is enough to "
            "change the shape rather than turn it -- a unit square stamped at 45 "
            "degrees comes back a triangle. Build the part larger, or keep it "
            "cardinal and use Frame(turns=...), which is exact at any size."
            % (shortest, MIN_STAMP_EDGE))
    points = source
    theta = radians(float(degrees))
    cos_t, sin_t = cos(theta), sin(theta)
    ox, oy = float(about[0]), float(about[1])
    tx, ty = float(offset[0]), float(offset[1])
    result: list[Point] = []
    for point in points:
        x, y = float(point[0]) - ox, float(point[1]) - oy
        rx = x * cos_t - y * sin_t
        ry = x * sin_t + y * cos_t
        result.append((int(round(rx + ox + tx)), int(round(ry + oy + ty))))
    deduped: list[Point] = []
    for point in result:
        if not deduped or point != deduped[-1]:
            deduped.append(point)
    if len(deduped) > 2 and deduped[0] == deduped[-1]:
        deduped.pop()
    if len(deduped) < 3:
        raise VocabularyError(
            "the outline collapsed to fewer than three distinct points at Build "
            "integer resolution; it is too small to rotate at this scale"
        )
    return deduped


def stamp_angle(angle: int, degrees: float) -> int:
    """The Build angle a sprite carries after its room is stamped.

    2048 units to a full turn. Sprites are the one thing a rotated outline does
    not bring with it: a torch bracket keeps pointing the way it pointed, into
    the wall the room used to have.
    """
    return int(round(int(angle) + float(degrees) * 2048.0 / 360.0)) % 2048


def stamp_alignment(floor_stat: int, *, sloped: bool, directional: bool) -> int:
    """The floor's alignment flag after a stamp, from the campaign's own habit.

    Turns on first-wall-relative alignment when the surface is sloped -- where
    Blood uses it 43.2% of the time against an 11.0% baseline -- or when the
    material says its flat has a direction to get wrong. Leaves an ordinary flat
    world-aligned, which is what Blood does with its angled rooms 82% of the
    time.
    """
    if sloped or directional:
        return int(floor_stat) | RELATIVE_ALIGNMENT
    return int(floor_stat)
