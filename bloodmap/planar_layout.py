"""Planar authored layout: semantic regions compiled into valid LevelIR.

Wall indices are compiler output. Design identity lives on region, connection,
and partition IDs. Partial collinear overlaps and T-junctions are split into
atomic reversed coincidences before portals are paired. Proper crossings fail.
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field
from math import hypot
from typing import Any, Iterable, Sequence

from .analysis import validate_map
from .construction import ConstructionError, LevelBuilder, SectorAllocation, new_level
from .format import SECTOR_FIELDS, WALL_FIELDS
from .geometry_audit import (
    AuthoredGeometryError,
    construction_preflight,
    validate_authored_level,
)
from .model import LevelIR
from .placement import PLAYER_HEIGHT, seated_z, sprite_extent

#: Blood's own event channels. Channel 2 is "a secret was found"; channel 1
#: carries the level's secret total as `NUMERIC_COMMAND_BASE + n`.
from . import slope as _slope

#: A band above an opening thinner than this is not a lintel anybody built
#: -- it is a floor that stepped. The campaign's lintels start at 0.24
#: standing humans at q1, and this is that, in z.
#: buildtypes.h:24 -- sector stat bit 6, "Align texture to first wall of
#: sector". The bit that decides whether a rotated room's floor turns with it.
_RELATIVE_ALIGNMENT = 64

_LINTEL_FLOOR = 4096

SECRET_FOUND_CHANNEL = 2
TOTAL_SECRETS_CHANNEL = 1
NUMERIC_COMMAND_BASE = 64
from .planar_geom import (
    Point,
    Segment,
    area2,
    atomic_subsegments,
    classify_segment_pair,
    collinear_overlap_interval,
    exact_reversed,
    integer_intersection,
    loops_equivalent,
    on_segment_inclusive,
    on_segment_strict,
    point_in_loop,
    point_in_loops,
    polygon_relation,
    t_junction_point,
    undirected_key,
    validate_loop,
    z_interval,
    z_relation,
)

SCHEMA = "llmapper.planar-layout"
SCHEMA_VERSION = 1

PORTAL_ROLES = {"portal", "doorway", "window"}
PARTITION_ROLES = {
    "solid_boundary", "thin_partition", "masked_partition", "breakable_partition",
    "blocked_portal",
}

#: Partition roles that leave the shared edge unpaired, so each side emits its
#: own one-sided wall. Every other role pairs the edge into a real portal.
#:
#: Leaving an edge unpaired between two regions produces two coincident solid
#: walls with nothing between them, and the Blood campaign contains **no such
#: pair at all** -- zero across 113,261 walls in 43 maps. When Blood wants a
#: barrier the player can see across but not cross, it pairs the wall and sets
#: the blocking bit: 2,272 two-sided walls do that, and the share rises with the
#: floor gap, from 1% where the floors are level to 10% where they differ by
#: more than two player heights. ``blocked_portal`` is that idiom.
UNPAIRED_PARTITION_ROLES = {
    "solid_boundary", "thin_partition", "masked_partition", "breakable_partition",
}

#: Build sprite/wall cstat bit 1: blocks movement while staying see-through.
CSTAT_WALL_BLOCKING = 1

#: Build draws a two-sided wall's middle section only when it is masked, and
#: takes that section from `over_picnum`. Masked plus hitscan is how every one
#: of the campaign's 523 masked walls is built.
CSTAT_WALL_MASKED = 16
CSTAT_WALL_HITSCAN = 64

#: `CSTAT_WALL_1WAY` (buildtypes.h:154), value 32. clipmove tests
#: `wal->cstat & dawalclipmask` (clip.cpp:1626, :1913). CLIPMASK0 is
#: `((1L)<<16)+1L` (build.h:225) -- bits 0 and 16, **not** bit 5. Bit 5 alone
#: therefore does not stop the player. Bit 0 (`CSTAT_WALL_BLOCKING`) is in that
#: mask, and setting it is exactly what stops movement. A one-way wall that also
#: carries bit 0 is a blocked fake wall, not an open doorway.
#:
#: It is the only flag that cuts the sector flood, and it is *directional*: it
#: lives on one of the two coincident walls and cuts only the view that starts in
#: that wall's own sector. `bloodmap.overlap_visibility` already reads it as one
#: of the two proofs that two sectors can never be drawn together; this is the
#: side that writes it.
CSTAT_WALL_ONE_WAY = 32


def _marker_fields(item: Any) -> dict[str, Any]:
    return item["fields"] if isinstance(item, dict) else item.fields


#: The marker types the loader binds to a sector, and which XSECTOR field each
#: one fills. `kMarkerWarpDest` shares `marker0` with off and axis.
MARKER_OFF, MARKER_ON, MARKER_AXIS, MARKER_WARP = 3, 4, 5, 8
MARKER_FIELD = {
    MARKER_OFF: "marker_0",
    MARKER_AXIS: "marker_0",
    MARKER_WARP: "marker_0",
    MARKER_ON: "marker_1",
}

#: Blood keeps its markers on this list, and the loader walks it by statnum.
MARKER_STATNUM_LIST = 10


def bind_markers(level: Any, *, owners: dict[str, int] | None = None) -> dict[str, Any]:
    """Give every marker the `owner` the loader reads, and derive marker_0/1 from it.

    This is the binding that actually matters, and it is not the one it looks
    like. `dbLoadMap` does not read `marker0` and `marker1` from the file at all
    -- it *rebuilds* them, by walking the marker statnum and asking each marker
    sprite which sector it owns::

        for (nSprite = headspritestat[kStatMarker]; ...) {
            switch (sprite[nSprite].type) {
                case kMarkerOff: case kMarkerAxis: case kMarkerWarpDest: {
                    int nOwner = sprite[nSprite].owner;
                    if (nOwner >= 0 && nOwner < numsectors) {
                        int nXSector = sector[nOwner].extra;
                        if (nXSector > 0 && nXSector < kMaxXSectors) {
                            xsector[nXSector].marker0 = nSprite;
                            continue;
                        }
                    }
                }
                break;
                case kMarkerOn: { ... marker1 = nSprite; continue; }
            }
            DeleteSprite(nSprite);
        }

    Note the last line. A marker whose `owner` does not name a sector with an
    XSECTOR does not merely fail to bind -- **it is deleted**. So a level that
    writes `marker0` and `marker1` correctly and leaves `owner` at -1 loses every
    marker it has, and its moving sectors then dereference freed sprite slots.

    All 1,055 markers in the campaign carry an owner. All five in this project's
    level carried -1, through five separate audits, because every check the
    project had was looking at the field the engine ignores. The sample maps gave
    it away: `ENVIRONMENT-SLIDETRICKS` stores marker indices of 107 and 108 in a
    map with 62 sprites, which is only survivable if nothing reads them.

    `owner` is the sector the marker *controls*, which is usually but not always
    the one it stands in -- 387 of the campaign's markers sit in a different
    sector from the one they mark. `owners` overrides the default per placement
    id for those cases.
    """
    overrides = dict(owners or {})
    bound = 0
    for index, sprite in enumerate(level.sprites):
        fields = _marker_fields(sprite)
        kind = int(fields["type"])
        if kind not in MARKER_FIELD:
            continue
        if int(fields.get("status", 0)) != MARKER_STATNUM_LIST:
            continue
        sector_id = overrides.get(str(index), int(fields["sector"]))
        fields["owner"] = int(sector_id)
        sector = level.sectors[sector_id]
        blood = sector["blood"] if isinstance(sector, dict) else sector.extra
        if blood is None:
            raise PlanarLayoutError(
                f"marker sprite {index} owns sector {sector_id}, which has no XSECTOR; "
                f"the loader would delete the marker")
        target = blood["fields"] if isinstance(blood, dict) else blood.fields
        target[MARKER_FIELD[kind]] = index
        bound += 1
    return {
        "markers_bound": bound,
        "basis": (
            "dbLoadMap rebuilds marker0/marker1 from each marker's owner and "
            "deletes any marker whose owner names no XSECTOR sector"
        ),
    }



def _flat_lies_flush(cstat: Any, height_player_heights: float) -> int:
    """Clearance for a horizontal anchor, zeroed for floor-aligned tiles.

    A floor-aligned sprite is a flat plate drawn in the plane of its own z. It
    has no vertical extent, so it cannot hang from anything: given a clearance
    it simply floats, a disc suspended in mid-air with nothing above it. The
    campaign agrees -- 77% of its ceiling-side flat sprites and 63% of its
    floor-side ones sit within a build tolerance of their surface, both with a
    median drift of exactly zero.

    So the mounting wins over the requested drop, the same way it does on a
    wall. The difference is that a wall is an outright error (there is no
    reading under which a flat sprite belongs on one) while a plate wanted a
    little lower is merely a plate laid flush.
    """
    if int(cstat) & 0x30 == 0x20:
        return 0
    return int(round(float(height_player_heights) * PLAYER_HEIGHT))


class PlanarLayoutError(AuthoredGeometryError):
    pass


def _empty(schema) -> dict[str, int]:
    return {str(item[0]): 0 for item in schema}


def _connection_has_face(connection: ConnectionSpec) -> bool:
    return any(
        value is not None
        for value in (
            connection.face_picnum, connection.face_over_picnum, connection.face_shade,
            connection.face_cstat, connection.face_x_repeat, connection.face_y_repeat,
            connection.face_x_repeat_scale, connection.face_y_repeat_scale,
        )
    )


#: Build's Marked-slide payload flags, on WALLS. Sprites use their own
#: 8192/16384 and are dragged regardless of what the walls do.
WALL_MOVES_WITH = 16384
WALL_MOVES_AGAINST = 32768

#: Blood's room-over-room marker pair: kMarkerUpStack above and
#: kMarkerLowStack below, matched on their XSPRITE `data_1`.
STACK_UPPER, STACK_LOWER = 11, 12


def _cycle(points: Sequence[Point]) -> tuple[Point, ...]:
    return tuple((int(x), int(y)) for x, y in points)


#: Statnums whose sprites always carry an XSprite. Items (3), things (4), dudes
#: (6), traps (11) and ambient sound (12) do so in **15,071 of 15,071** sprites
#: across the 43 campaign maps -- not a single exception -- while decoration
#: (statnum 10) never does and statnum 0 does 63% of the time.
#:
#: For a dude the XSprite is load-bearing: `aiInitSprite` dereferences
#: `xsprite[pSprite->extra]` with no guard, so one without it segfaults the
#: engine. For the rest the engine guards, and the sprite merely never acts --
#: still not what the author asked for. The compiler supplies one either way,
#: which costs nothing and matches every map Blood shipped.
XSPRITE_REQUIRED_STATNUMS = frozenset({3, 4, 6, 11, 12})


@dataclass
class RegionSpec:
    region_id: str
    outer: tuple[Point, ...]
    holes: tuple[tuple[Point, ...], ...] = ()
    ceiling_z: int = -24576
    floor_z: int = 8192
    ceiling_picnum: int = 385
    floor_picnum: int = 292
    wall_picnum: int = 180
    #: Left unset, a surface takes the shade its region's description implies --
    #: see `bloodmap.lighting.derived_shade`. Pass a number only where one is
    #: actually a decision, such as a stair's ramp.
    ceiling_shade: int | None = None
    floor_shade: int | None = None
    wall_shade: int | None = None
    #: Raw Build flags on the horizontal surfaces.  Bits for texture flip,
    #: repeat-size variant and relative alignment are authoring data, not
    #: decoration; preserving them is what makes a prefab render like Blood.
    floor_stat: int = 0
    ceiling_stat: int = 0
    role: str = "gameplay"
    layer: str = "ground"
    special: str | None = None
    parallax_ceiling: bool = False
    #: Pitch this region's ceiling or floor about one of its outer edges, as a
    #: `bloodmap.slope.SlopeSpec`. The engine hinges a slope on the sector's
    #: *first* wall, so naming an edge here rotates the emitted wall loop -- and
    #: the two surfaces of one sector necessarily share the same hinge.
    ceiling_slope: Any = None
    floor_slope: Any = None
    #: Align this region's flats to its *first wall* instead of to the world.
    #:
    #: Build pastes a floor or ceiling texture from the world origin unless
    #: sector stat bit 6 is set (buildtypes.h:24, "Align texture to first wall
    #: of sector"). A room turned off the cardinal grid therefore keeps its
    #: planks running north-south while its walls run at 30 degrees, which reads
    #: as a floor that belongs to a different building.
    #:
    #: It is not on by default for rotated rooms, because the campaign does not
    #: do that. Of 13,649 playable sectors, 14.0% align the floor to the first
    #: wall; split by cause the signal is slope, not rotation --
    #: sloped 43.2% against flat 11.0%, but angled only 17.6% against cardinal
    #: 12.2%. Blood leaves most of its angled floors world-aligned, which is
    #: fine for rubble and stone. Set this where the flat has a direction to get
    #: wrong, and `bloodmap.vocabulary.stamp_alignment` decides it from the same
    #: two causes the campaign splits on.
    #:
    #: One of None, "floor", "ceiling" or "both".
    relative_alignment: str | None = None
    type: int = 0
    declared_zero_exit: bool = False
    stack_pair: str | None = None
    sector_behavior: dict[str, int] = field(default_factory=dict)
    #: Take the ceiling and/or floor finish from the largest room this region
    #: opens onto, instead of naming one.
    #:
    #: Blood paints regions rather than rooms: 65 to 78% of a level's sectors sit
    #: in a run of three or more sharing a finish, and 85% of its small
    #: mostly-portal sectors share a ceiling tile with a neighbour. A doorway is
    #: not its own painted area -- it is a hole cut in a room, and it keeps that
    #: room's ceiling.
    #:
    #: This level named a finish per region, so its doors and arches each sat
    #: alone: 24 ceiling groups across 50 sectors, and a `ceiling_patch_share` of
    #: 0.58 against a campaign median of 0.78. The door face itself belongs on
    #: the portals (see `door_face`), not on the ceiling you look up at.
    #:
    #: One of "ceiling", "floor" or "both".
    inherit_finish: str | None = None

    #: Whether reaching this region counts as finding a secret.
    #:
    #: Blood has no "secret" sector type. A secret is a plain sector wired to the
    #: engine's own channel 2 with the numeric command base, and the campaign is
    #: near-unanimous about the form: type 0, tx_id 2, command 64,
    #: trigger_enter, trigger_once, resting at state 0 -- 141 of its 152 secret
    #: sectors are exactly that. The count is declared separately, by a sprite
    #: transmitting `64 + n` on channel 1.
    #:
    #: A level with `role="secret"` regions and none of this wiring has hidden
    #: rooms that no player is ever told they found, which is what this one was.
    secret: bool = False

    #: The tile a doorway shows to the rooms it joins.
    #:
    #: A region's `wall_picnum` paints the walls that face *into* it, and for a
    #: sector the player never stands in -- a door, an arch, a gate -- those are
    #: the one set of surfaces they never look at. What is seen approaching a
    #: shut Z-door is the top section of the wall on the *room* side, and Build
    #: draws that from that wall's own `picnum` (engine.c: the top step takes
    #: `wal->picnum`; `overpicnum` is only for masked one-way walls). So a door
    #: face declared as `wall_picnum` ends up on the inside of the frame and
    #: nowhere the player can see it.
    #:
    #: `door_face` puts it where the engine reads it: on both sides of every
    #: portal this region owns, leaving the region's own solid walls -- the
    #: jambs -- to `wall_picnum`.
    door_face: int | None = None
    #: Dress this region's own openings in a different tile from its field walls.
    #:
    #: Blood does not paint a room in one material. Its playable sectors carry a
    #: median of 2 distinct wall tiles and a q3 of 3, and only 37% use just one;
    #: this project's level used one in 90% of its rooms, which is most of why
    #: its frames were 66% wall against a campaign 50% and its tile variety 4
    #: against 6.
    #:
    #: The division the campaign draws is not decorative, it is structural: of
    #: the 8,320 campaign rooms with more than one wall tile, **74% put a
    #: different tile on their two-sided walls than on their solid ones**, and
    #: the minority takes a quarter to a half of the walls. Openings are dressed
    #: and the field between them is not -- which is how masonry is actually
    #: built, ashlar at the jambs and rubble in the spans.
    #:
    #: Only this region's own face is painted. The room on the other side dresses
    #: its side itself, or does not. `door_face` still overrides this, because a
    #: door is a thing rather than an opening.
    portal_wall_picnum: int | None = None
    intent: dict[str, Any] = field(default_factory=dict)


@dataclass
class ConnectionSpec:
    connection_id: str
    region_a: str
    region_b: str
    role: str = "portal"
    a1: Point | None = None
    a2: Point | None = None
    min_width: int = 512
    min_opening: int = 8192
    gated: bool = False
    wall_behavior: dict[str, int] = field(default_factory=dict)
    attach_policy: str = "single_atomic"
    face_picnum: int | None = None
    face_over_picnum: int | None = None
    face_shade: int | None = None
    face_cstat: int | None = None
    face_x_repeat: int | None = None
    face_y_repeat: int | None = None
    #: Multiply the generated repeats on both records of a portal face.
    #:
    #: A prefab can be physically smaller than the construction default while
    #: still needing to show a complete art tile.  The scale is deliberately
    #: applied after geometry-derived repeats, so a two-crate-wide face keeps
    #: two complete tiles instead of stretching one tile across the stack.
    face_x_repeat_scale: float | None = None
    face_y_repeat_scale: float | None = None
    #: Cut the renderer's flood through this portal, from one side only.
    #:
    #: `"left"`/`"a"` cuts the view that starts in `region_a`, `"right"`/`"b"`
    #: the view that starts in `region_b`; a region id says the same thing
    #: explicitly.
    #:
    #: Bit 5 does not touch clipmove: CLIPMASK0 is bits 0 and 16 (build.h:225),
    #: tested at clip.cpp:1626. It also cannot resolve a *symmetric* co-visibility
    #: problem, because the flag lives on one wall and cuts one direction only
    #: (engine.c:3134). It is not a substitute for jogging the plan so that
    #: `wallfront` (engine.cpp:2227) is not handed collinear bunches. A masked
    #: wall (bit 4) changes what is painted, not what the sort can order, and
    #: must not be used for this.
    #:
    #: What it is for: a portal into a sector that overlaps something else the
    #: viewer can also reach, *and only when a named renderer pair's evidence
    #: demands that specific wall*. Build's flood collects a neighbour sector
    #: and then lets *all* of its walls compete for screen columns -- the
    #: portal's own opening does not clip them (engine.cpp:9739 orders bunches
    #: with `bunchfront`, which is `wallfront`, which has no z in it at all).
    #: So a storey above the viewer's eye can win the columns belonging to the
    #: room behind it. That is an overlap-and-flood fault, not the coplanar
    #: neighbour fault `wallfront` records when two same-height rooms share a
    #: line. Putting this flag on a doorway because an overlap exists nearby
    #: does not rank those neighbours, and with bit 0 set it is a blocked fake
    #: wall (CLIPMASK0, build.h:225).
    #:
    #: Declaring it makes the flagged side opaque: the wall's own picnum is
    #: copied to `over_picnum` so the face is masonry rather than tile 0.
    view_cut_from: str | None = None


@dataclass
class PartitionSpec:
    partition_id: str
    region_a: str
    region_b: str | None
    role: str = "thin_partition"
    a1: Point | None = None
    a2: Point | None = None
    wall_behavior: dict[str, int] = field(default_factory=dict)
    #: Make a blocked portal *opaque* as well as impassable.
    #:
    #: `blocked_portal` on its own sets cstat bit 1, which stops the player and
    #: leaves the wall see-through. That is right for a rail you look over and
    #: wrong for a stone jamb: the gate jambs in this project were invisible
    #: barriers, and the level read as a gate floating in a gap.
    #:
    #: Blood's opaque two-sided wall is the masked one -- block + masked(16) +
    #: hitscan(64), with the surface on `over_picnum`, which is how all 523 of
    #: its masked walls are built. Setting this copies the wall's own picnum
    #: onto its over_picnum, so the jamb is made of whatever the room is.
    opaque: bool = False


@dataclass
class PlacementSpec:
    placement_id: str
    region_id: str
    x: int
    y: int
    z: int
    type: int = 0
    picnum: int = 0
    status: int = 0
    angle: int = 0
    cstat: int = 128
    x_repeat: int = 64
    y_repeat: int = 64
    shade: int = 0
    pal: int = 0
    behavior: dict[str, int] = field(default_factory=dict)
    #: "floor", "ceiling" or "centre" -- how the sprite meets the room it is in.
    #: A seated placement has its z computed from the tile's drawn extent rather
    #: than taken as given, because Blood centres a sprite on its z and a
    #: standing object placed at `floor_z` is buried to the waist.
    seat: str | None = None
    #: For a marker sprite: the region whose sector this marker controls, when
    #: that is not the region it stands in.
    marker_owner: str | None = None
    seat_clearance: int = 0
    #: This sprite is meant to span an opening rather than hang on a wall.
    #:
    #: A wall placement whose wall turns out to be a portal has nothing behind it
    #: at the sprite's own height: it floats in the doorway. Six of this level's
    #: fifty wall placements did, and from inside they are the "wall sprites in
    #: mid air" that kept getting reported.
    #:
    #: It cannot simply be forbidden, because some sprites are *for* openings --
    #: a grille set in an arch, a plank nailed across a doorway. Those span the
    #: gap; a sconce, an emblem or a torch is fixed to masonry and needs masonry
    #: to be fixed to. The two are indistinguishable from geometry alone, so the
    #: author says which, and the compiler refuses the ones that say nothing.
    spans_opening: bool = False
    anchor: dict[str, Any] | None = None


@dataclass(frozen=True)
class LightSourceSpec:
    """A declared source for generated lighting.

    A source either follows a visual placement (the normal case for a torch or
    lamp) or names a raw point for light that has no sprite, such as daylight
    through a window.  In both cases it remains authored source, rather than a
    later pass guessing from tile ids or sprite shade.
    """

    light_id: str
    region_id: str
    placement_id: str | None = None
    x: int | None = None
    y: int | None = None
    z: int | None = None
    #: Multiplier for the measured LightBomb source model.  ``None`` uses the
    #: campaign-fitted default; a larger fixture may opt in to a stronger pool
    #: without reintroducing manual surface shades.
    intensity: float | None = None
    #: Optional height of a source that follows a sprite.  This is useful for
    #: a floor-mounted lamp whose visible fixture rests on the ground while
    #: its bulb illuminates from above it.
    height_player_heights: float | None = None


@dataclass
class PlayerStartSpec:
    region_id: str
    x: int
    y: int
    z: int
    angle: int = 0


@dataclass
class SourceEdge:
    edge_id: str
    region_id: str
    a: Point
    b: Point


@dataclass
class AtomicEdge:
    atomic_id: str
    source_id: str
    region_id: str
    a: Point
    b: Point


@dataclass
class ConservationReport:
    source_directed_edges: int
    emitted_directed_edges: int
    dropped_source_edges: list[str]
    duplicated_source_edges: list[str]
    unpaired_portal_candidates: list[str]
    split_count: int
    atomic_segments: int
    walls_owned_once: bool

    def to_dict(self) -> dict[str, Any]:
        return {
            "source_directed_edges": self.source_directed_edges,
            "emitted_directed_edges": self.emitted_directed_edges,
            "dropped_source_edges": list(self.dropped_source_edges),
            "duplicated_source_edges": list(self.duplicated_source_edges),
            "unpaired_portal_candidates": list(self.unpaired_portal_candidates),
            "split_count": self.split_count,
            "atomic_segments": self.atomic_segments,
            "walls_owned_once": self.walls_owned_once,
            "conserved": self.conserved,
        }

    @property
    def conserved(self) -> bool:
        return (
            not self.dropped_source_edges
            and not self.duplicated_source_edges
            and self.walls_owned_once
        )


@dataclass
class CompiledLayout:
    level: LevelIR
    allocations: dict[str, SectorAllocation]
    placement_sprites: dict[str, int]
    wall_from_atomic: dict[str, int]
    conservation: ConservationReport
    connection_report: list[dict[str, Any]]
    declared_specials: list[tuple[int, int, str]]
    layout: "PlanarLayout"
    lighting_report: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "$schema": "llmapper.compiled-layout",
            "schema_version": 1,
            "allocations": {
                key: {"sector_id": value.sector_id, "wall_ids": list(value.wall_ids)}
                for key, value in self.allocations.items()
            },
            "placement_sprites": dict(self.placement_sprites),
            "conservation": self.conservation.to_dict(),
            "connection_report": self.connection_report,
            "declared_specials": [
                {"sectors": [a, b], "kind": kind} for a, b, kind in self.declared_specials
            ],
            "lighting": dict(self.lighting_report),
        }




def _nearest_wall_of(level: Any, sector_id: int, x: int, y: int) -> int | None:
    """Which wall of this sector the point lies closest to."""
    from math import hypot

    fields = level.sectors[sector_id]["fields"]
    start, count = int(fields["wall_ptr"]), int(fields["wall_count"])
    best: tuple[float, int] | None = None
    for wall_id in range(start, start + count):
        here = level.walls[wall_id]["fields"]
        there = level.walls[int(here["point2"])]["fields"]
        ax, ay = int(here["x"]), int(here["y"])
        bx, by = int(there["x"]), int(there["y"])
        dx, dy = bx - ax, by - ay
        length2 = dx * dx + dy * dy
        if length2 <= 0:
            distance = hypot(x - ax, y - ay)
        else:
            t = max(0.0, min(1.0, ((x - ax) * dx + (y - ay) * dy) / length2))
            distance = hypot(x - (ax + t * dx), y - (ay + t * dy))
        if best is None or distance < best[0]:
            best = (distance, wall_id)
    return None if best is None else best[1]


def _open_band(level: Any, sector_id: int, wall_id: int) -> tuple[int, int] | None:
    """The z band a two-sided wall leaves open, or None if it is solid.

    Build draws a two-sided wall as a top section and a bottom section with a gap
    between them, and the gap is the hole you walk through: from the lower of the
    two ceilings down to the higher of the two floors.
    """
    here = level.walls[wall_id]["fields"]
    other = int(here.get("next_sector", -1))
    if other < 0:
        return None
    mine = level.sectors[sector_id]["fields"]
    theirs = level.sectors[other]["fields"]
    top = max(int(mine["ceiling_z"]), int(theirs["ceiling_z"]))
    bottom = min(int(mine["floor_z"]), int(theirs["floor_z"]))
    return (top, bottom) if bottom > top else None



def _region_shading(region: "RegionSpec") -> dict[str, int]:
    """The three shades this region will be built with.

    Anything the author set explicitly wins; the rest is derived from what the
    region is -- open to the sky or not, and how big its floor is.
    """
    from .lighting import derived_shade

    derived = derived_shade(
        outdoor=bool(region.parallax_ceiling),
        area_player_widths=abs(area2(region.outer)) / 2.0 / (384.0 * 384.0),
    )
    for name in ("floor_shade", "ceiling_shade", "wall_shade"):
        chosen = getattr(region, name)
        if chosen is not None:
            derived[name] = int(chosen)
    return derived



def _is_power_of_two(value: int) -> bool:
    return value > 0 and (value & (value - 1)) == 0


def _check_flat_tiles(level: Any, art_sizes: dict[int, tuple[int, int]],
                      allocations: dict) -> None:
    """A floor or ceiling texture has to have power-of-two sides.

    `tileUpdatePicSiz` takes the largest power of two **not greater than** each
    of a tile's dimensions, and the floor rasteriser masks its texture lookup
    with exactly that::

        globalxshift = 8 - (picsiz[globalpicnum] & 15);
        globalyshift = 8 - (picsiz[globalpicnum] >> 4);

    So a 64x400 tile laid on a floor is sampled as if it were 64x256: the last
    144 rows are never drawn, and it tiles at the wrong pitch. Walls escape this
    because `wallscan` handles arbitrary heights; floors and ceilings do not.

    The campaign obeys it in 26,376 of 26,383 non-parallax surfaces -- 99.97%.
    A parallax ceiling is exempt because the sky is not sampled this way at all.
    """
    offenders = []
    for region_id, allocation in allocations.items():
        fields = level.sectors[allocation.sector_id]["fields"]
        for surface in ("floor", "ceiling"):
            if int(fields.get(f"{surface}_stat", 0)) & 1:
                continue                      # parallax: not a sampled surface
            picnum = int(fields[f"{surface}_picnum"])
            size = art_sizes.get(picnum)
            if size is None:
                continue                      # no ART to check against
            width, height = int(size[0]), int(size[1])
            if _is_power_of_two(width) and _is_power_of_two(height):
                continue
            offenders.append(
                f"{region_id} {surface} tile {picnum} is {width}x{height}")
    if offenders:
        listing = "\n  " + "\n  ".join(sorted(offenders))
        raise PlanarLayoutError(
            "%d floor or ceiling surfaces carry a tile whose sides are not "
            "powers of two, so Build will sample only part of it:%s"
            "\nUse a power-of-two tile, or declare the surface parallax."
            % (len(offenders), listing))


def _rotate_to_hinge(loop: list["AtomicEdge"], region: "RegionSpec") -> list["AtomicEdge"]:
    """Put the slope's hinge edge first, because Build hinges on ``wallptr``."""
    specs = [s for s in (region.ceiling_slope, region.floor_slope) if s is not None]
    hinges = {(tuple(s.hinge[0]), tuple(s.hinge[1])) for s in specs}
    if len(hinges) > 1:
        raise PlanarLayoutError(
            f"{region.region_id} slopes its floor and ceiling about different "
            "edges; one sector has one first wall and so one hinge -- a second "
            "axis needs a second sector")
    (start, end), = hinges
    ux, uy = end[0] - start[0], end[1] - start[1]
    for offset, edge in enumerate(loop):
        if tuple(edge.a) != start:
            continue
        vx, vy = edge.b[0] - edge.a[0], edge.b[1] - edge.a[1]
        if ux * vy - uy * vx == 0 and ux * vx + uy * vy > 0:   # collinear, same way
            return loop[offset:] + loop[:offset]
    raise PlanarLayoutError(
        f"{region.region_id}: slope hinge {start}->{end} is not an edge of its outline")


class PlanarLayout:
    """Replayable source representation above LevelIR."""

    #: Every one of the 38 campaign maps that contains a parallax sector declares
    #: a 16-panel sky (``bits=4``, offsets 0..15); not one uses a single panel.
    #: ``new_level`` starts at ``bits=0``, which maps the whole 360 degrees onto
    #: one 64-pixel column of the sky tile -- in Blood's night sky that column is
    #: the dark edge, which is why every outdoor level this project generated
    #: rendered a black sky while its configuration matched the originals field
    #: for field.
    CORPUS_SKY_BITS = 4

    def __init__(self, *, visibility: int = 800, name: str = "", sky_bits: int | None = None,
                 tile_extents: dict[int, tuple[int, int]] | None = None):
        #: picnum -> (tile pixel height, picanm yofs). Needed only by seated
        #: placements; a layout that seats nothing does not need the game's ART.
        self.tile_extents: dict[int, tuple[int, int]] = dict(tile_extents or {})
        #: picnum -> (width, height) for every tile that might land on a floor or
        #: a ceiling. Only needed to enforce the power-of-two rule; a layout that
        #: does not supply it is simply not checked.
        self.flat_tile_sizes: dict[int, tuple[int, int]] = {}
        self.name = name
        self.visibility = int(visibility)
        self.sky_bits = None if sky_bits is None else int(sky_bits)
        #: Slopes that left the range the campaign built in. Not errors -- the
        #: campaign has a 13312 heinum somewhere -- but worth saying out loud.
        self.slope_notes: list[str] = []
        self.regions: dict[str, RegionSpec] = {}
        self.connections: dict[str, ConnectionSpec] = {}
        self.partitions: dict[str, PartitionSpec] = {}
        self.placements: list[PlacementSpec] = []
        #: (region_id, edge) -> cstat bits the sector's motion drags it by.
        #: See `carry_wall`.
        self.carried: dict[tuple[str, tuple], int] = {}
        #: (region_id, edge) -> wall fields written after emit. See
        #: `paint_wall`.
        self.painted: dict[tuple[str, tuple], dict[str, int]] = {}
        #: Declarative illumination, resolved after geometry and sprite seating.
        #: LightBomb only runs when this list is non-empty.
        self.light_sources: list[LightSourceSpec] = []
        self.player_start: PlayerStartSpec | None = None
        self.special_pairs: list[tuple[str, str, str]] = []
        #: Cross-layer overlaps `bloodmap.layers` approved during `compile`,
        #: carried forward so the geometry audit is told they are intended.
        self._approved_layer_overlaps: list[Any] = []
        #: Callables run on the emitted level at the end of `compile`, in order.
        #: They exist for finishing passes that need the compiled geometry --
        #: wall texture alignment needs each wall's picnum and its sector's
        #: heights, neither of which a region declaration has. A hook must not
        #: change what walls or sectors exist, only how they are dressed.
        self.post_compile: list[Any] = []

    def add_region(
        self,
        region_id: str,
        outer: Iterable[tuple[int, int]],
        *,
        holes: Iterable[Iterable[tuple[int, int]]] = (),
        **kwargs: Any,
    ) -> str:
        if region_id in self.regions:
            raise PlanarLayoutError(f"duplicate region id {region_id!r}")
        hole_tuples = tuple(_cycle(list(item)) for item in holes)
        self.regions[region_id] = RegionSpec(
            region_id=region_id, outer=_cycle(list(outer)), holes=hole_tuples, **kwargs,
        )
        return region_id

    def carve_hole(self, host_id: str, footprint: Iterable[tuple[int, int]]) -> None:
        host = self._region(host_id)
        hole = _cycle(list(footprint))
        if area2(hole) > 0:
            hole = tuple(reversed(hole))
        errors = validate_loop(hole, role="hole")
        if errors:
            raise PlanarLayoutError(f"hole for {host_id}: {errors[0]}")
        if point_in_loop(hole[0], host.outer) == 0 and point_in_loops(hole[0], [host.outer]) != 1:
            sample = hole[0]
            if point_in_loop(sample, host.outer) != 1 and point_in_loop(sample, host.outer) != -1:
                # centroid-like: require at least one vertex inside or on host
                if not any(point_in_loop(point, host.outer) != 0 for point in hole):
                    raise PlanarLayoutError(f"hole is not inside host {host_id}")
        host.holes = host.holes + (hole,)

    def insert_mass(self, host_id: str, outer_footprint: Iterable[tuple[int, int]], *, mass_id: str) -> str:
        self.carve_hole(host_id, outer_footprint)
        return f"mass:{mass_id}"

    def insert_building_shell(
        self,
        host_id: str,
        *,
        mass_id: str,
        outer_footprint: Iterable[tuple[int, int]],
        inner_footprint: Iterable[tuple[int, int]],
        entrances: Sequence[dict[str, Any]],
        **interior: Any,
    ) -> dict[str, Any]:
        outer = _cycle(list(outer_footprint))
        inner = _cycle(list(inner_footprint))
        if area2(outer) < 0:
            raise PlanarLayoutError("building outer footprint must be clockwise")
        if area2(inner) < 0:
            raise PlanarLayoutError("building inner footprint must be clockwise")
        for point in inner:
            state = point_in_loop(point, outer)
            if state == 0:
                raise PlanarLayoutError("inner footprint is not inside the outer shell")
        self.carve_hole(host_id, outer)
        interior_id = f"region:{mass_id}:interior"
        interior_kwargs = {
            "ceiling_z": interior.get("ceiling_z", -24576),
            "floor_z": interior.get("floor_z", 8192),
            "ceiling_picnum": interior.get("ceiling_picnum", 416),
            "floor_picnum": interior.get("floor_picnum", 2448),
            "wall_picnum": interior.get("wall_picnum", 5),
            "ceiling_shade": interior.get("ceiling_shade", 8),
            "floor_shade": interior.get("floor_shade", 16),
            "wall_shade": interior.get("wall_shade", 8),
            "role": "interior",
        }
        self.add_region(interior_id, inner, **interior_kwargs)
        doors = []
        for entrance in entrances:
            door_id = str(entrance.get("region_id") or f"region:{mass_id}:{entrance['id']}:door")
            oa = (int(entrance["outer_a"][0]), int(entrance["outer_a"][1]))
            ob = (int(entrance["outer_b"][0]), int(entrance["outer_b"][1]))
            ia = (int(entrance["inner_a"][0]), int(entrance["inner_a"][1]))
            ib = (int(entrance["inner_b"][0]), int(entrance["inner_b"][1]))
            quad = [oa, ob, ib, ia]
            if area2(quad) <= 0:
                quad = [oa, ia, ib, ob]
            if area2(quad) <= 0:
                raise PlanarLayoutError(f"doorway {entrance.get('id')} has non-positive area")
            door_kwargs = dict(entrance.get("door_kwargs") or {})
            if entrance.get("gated"):
                door_kwargs.setdefault("type", 600)
                door_kwargs.setdefault("ceiling_z", 8192)
                door_kwargs.setdefault("floor_z", 8192)
            self.add_region(door_id, quad, role="doorway", **door_kwargs)
            if entrance.get("sector_behavior"):
                self.regions[door_id].sector_behavior = dict(entrance["sector_behavior"])
            width = int(hypot(ob[0] - oa[0], ob[1] - oa[1]))
            self.add_connection(
                f"connection:{entrance['id']}:host",
                host_id, door_id, role="doorway", a1=oa, a2=ob,
                gated=bool(entrance.get("gated")),
                min_width=max(512, width),
            )
            inner_width = int(hypot(ib[0] - ia[0], ib[1] - ia[1]))
            self.add_connection(
                f"connection:{entrance['id']}:inner",
                door_id, interior_id, role="doorway", a1=ia, a2=ib,
                gated=bool(entrance.get("gated")),
                min_width=max(512, inner_width),
            )
            doors.append(door_id)
        return {"interior": interior_id, "doors": doors, "mass": f"mass:{mass_id}"}

    def stack_link(self, link_id: int, upper_region: str, lower_region: str,
                   *, upper_at: Point, lower_at: Point,
                   upper_z: int | None = None,
                   lower_z: int | None = None) -> tuple[str, str]:
        """Link two regions vertically: room-over-room.

        Blood joins two sectors across a horizontal plane with a PAIR of
        marker sprites carrying the same `data_1`, one from the upper family
        and one from the lower. `warpInit` pairs them by that key, and the
        renderer then draws the lower space through the upper's floor.

        Two things this gets right that cost the project a shipped map each.
        The markers go on **statnum 0**, not the 10 that every other marker
        uses: statnum 10 is culled at load, so a link built on it is a link
        that does not exist. And they carry an XSPRITE, because `data_1` is
        an XSPRITE field and a marker without one has no key to pair on.

        Returns the two placement ids.
        """
        for region in (upper_region, lower_region):
            if region not in self.regions:
                raise PlanarLayoutError(f"stack_link: no region {region!r}")
        #: 11 and 12 by name, not the first of the families: 6/7 are water
        #: and 9/10 goo, and picking one of those makes a link that pairs and
        #: then floods. E1M1's casket uses 11 above and 12 below, cstat 128.
        upper_type, lower_type = STACK_UPPER, STACK_LOWER
        #: Two rooms one above the other necessarily share plan area, which
        #: every other pair of regions is refused for. The link IS the
        #: declaration, so making one declares it.
        self.declare_special(upper_region, lower_region, "stack")
        made = []
        for tag, region, kind, point, z in (
                ("upper", upper_region, upper_type, upper_at, upper_z),
                ("lower", lower_region, lower_type, lower_at, lower_z)):
            spec = self.regions[region]
            default_z = (spec.floor_z if z is None else z)
            made.append(self.add_sprite(
                f"link:{link_id}:{tag}", region,
                x=int(point[0]), y=int(point[1]), z=int(default_z),
                type=int(kind), picnum=0, status=0, cstat=128,
                x_repeat=64, y_repeat=64, angle=0,
                behavior={"data_1": int(link_id)}))
        return (made[0], made[1])

    def paint_wall(self, region_id: str, a1: Point, a2: Point,
                   **fields: int) -> None:
        """Set fields on one named wall of a region, after it is emitted.

        `carry_wall` writes a payload flag this way; a masked panel needs to
        write `over_picnum` and a cstat the same way, because the surface of
        a see-through wall lives on the overlay and nothing in the region or
        partition spec reaches it.

        Matched by geometry rather than index, for the same reason
        `carry_wall` is: the compiler may rotate a loop.
        """
        if region_id not in self.regions:
            raise PlanarLayoutError(f"paint_wall: no region {region_id!r}")
        key = (region_id, _cycle((a1, a2)))
        self.painted.setdefault(key, {}).update(
            {k: int(v) for k, v in fields.items()})

    def _preflight_swept(self, disk) -> None:
        """Refuse a layout whose mechanisms break their own geometry."""
        try:
            from .swept_state import run as swept_run
        except Exception:
            return
        report = swept_run(disk)
        if report["problems"]:
            listing = "\n  " + "\n  ".join(report["problems"])
            raise PlanarLayoutError(
                "%d mechanism(s) break their geometry somewhere in "
                "their travel:%s\nEvery other check reads the pose the "
                "map is saved in, and a moving sector is only in that "
                "pose for an instant."
                % (len(report["problems"]), listing))

    def _apply_painted_walls(self, builder, allocations) -> None:
        for (region_id, edge), fields in self.painted.items():
            wall_id = self._wall_named(builder, allocations, region_id, edge,
                                       "paint_wall")
            target = builder.level.walls[wall_id]["fields"]
            for key, value in fields.items():
                if key == "cstat":
                    target["cstat"] = int(target["cstat"]) | int(value)
                else:
                    target[key] = int(value)

    def _wall_named(self, builder, allocations, region_id, edge, who):
        allocation = allocations.get(region_id)
        if allocation is None:
            raise PlanarLayoutError(f"{who}: {region_id!r} built no sector")
        walls = builder.level.walls
        wanted = {edge, (edge[1], edge[0])}
        for wall_id in allocation.wall_ids:
            fields = walls[wall_id]["fields"]
            end = walls[int(fields["point2"])]["fields"]
            segment = ((int(fields["x"]), int(fields["y"])),
                       (int(end["x"]), int(end["y"])))
            if segment in wanted:
                return wall_id
        raise PlanarLayoutError(
            f"{who}: {region_id!r} has no wall from {edge[0]} to {edge[1]}; "
            f"the region's own outline has to contain it")

    def _apply_carried_walls(self, builder, allocations) -> None:
        """OR each carried wall's flags onto the wall that actually got built.

        Matched by geometry rather than by index, because the compiler is free
        to rotate a loop -- a slope hinge does exactly that -- and a payload
        flag on the wrong wall is a mechanism that drags the wrong thing.
        """
        if not self.carried:
            return
        walls = builder.level.walls
        for (region_id, edge), bits in self.carried.items():
            allocation = allocations.get(region_id)
            if allocation is None:
                raise PlanarLayoutError(
                    f"carry_wall: {region_id!r} built no sector")
            hit = self._wall_named(builder, allocations, region_id, edge,
                                   "carry_wall")
            fields = walls[hit]["fields"]
            fields["cstat"] = int(fields["cstat"]) | int(bits)

    def carry_wall(self, region_id: str, a1: Point, a2: Point, *,
                   moves: str = "with") -> None:
        """Flag one wall of a region as dragged by that sector's motion.

        Build's Marked slide and rotate types -- 614 and 615 -- translate only
        the walls a mapper has flagged, and the flag says which way:
        `cstat & 16384` moves WITH the sector's travel and `& 32768` AGAINST
        it. (Sprites use their own 8192/16384 and are unaffected by either.)

        This is the payload half of the mechanism grammar, and without it two
        whole classes of Blood mechanism cannot be authored at all:

        * a **planar door** -- E1M1's casket -- is two sectors sharing one
          boundary wall, where the moving sector drags ONLY that wall, so the
          travel re-partitions plan area between hole and cover and the lid
          slides open;
        * a **curtain** -- E1M1 s125 -- is a thin sector whose two end caps
          carry OPPOSITE flags, so one end advances while the other retreats
          and the sector's own length changes, squashing and stretching the
          texture on its long faces. That deformation IS the animation.

        The edge is named the way connections name one, by its two endpoints
        in either order.
        """
        key = (region_id, _cycle((a1, a2)))
        bits = {"with": WALL_MOVES_WITH, "against": WALL_MOVES_AGAINST}
        if moves not in bits:
            raise PlanarLayoutError(
                f"carry_wall: moves is 'with' or 'against', not {moves!r}")
        if region_id not in self.regions:
            raise PlanarLayoutError(f"carry_wall: no region {region_id!r}")
        self.carried[key] = self.carried.get(key, 0) | bits[moves]

    def add_connection(
        self,
        connection_id: str,
        region_a: str,
        region_b: str,
        *,
        role: str = "portal",
        a1: Point | None = None,
        a2: Point | None = None,
        **kwargs: Any,
    ) -> str:
        if connection_id in self.connections:
            raise PlanarLayoutError(f"duplicate connection id {connection_id!r}")
        if role not in PORTAL_ROLES:
            raise PlanarLayoutError(f"unknown connection role {role!r}")
        self.connections[connection_id] = ConnectionSpec(
            connection_id=connection_id, region_a=region_a, region_b=region_b,
            role=role, a1=a1, a2=a2, **kwargs,
        )
        return connection_id

    def add_partition(
        self,
        partition_id: str,
        region_a: str,
        region_b: str | None = None,
        *,
        role: str = "thin_partition",
        a1: Point | None = None,
        a2: Point | None = None,
        **kwargs: Any,
    ) -> str:
        if role not in PARTITION_ROLES:
            raise PlanarLayoutError(f"unknown partition role {role!r}")
        self.partitions[partition_id] = PartitionSpec(
            partition_id=partition_id, region_a=region_a, region_b=region_b,
            role=role, a1=a1, a2=a2, **kwargs,
        )
        return partition_id

    def add_sprite(self, placement_id: str, region_id: str, *, x: int, y: int, z: int, **kwargs: Any) -> str:
        self.placements.append(PlacementSpec(
            placement_id=placement_id, region_id=region_id, x=int(x), y=int(y), z=int(z), **kwargs,
        ))
        return placement_id

    def add_light_source(self, light_id: str, region_id: str, *,
                         x: int, y: int, z: int,
                         intensity: float | None = None) -> str:
        """Declare an emissive point that is not tied to a sprite.

        Use this for an authored source such as window light.  Lights attached
        to a visible lamp should normally be declared with ``emits_light=True``
        on ``place_on_wall`` / ``place_on_floor`` so seating and sector lookup
        stay exactly in sync with that placement.
        """
        if any(item.light_id == light_id for item in self.light_sources):
            raise PlanarLayoutError(f"duplicate light id {light_id!r}")
        if region_id not in self.regions:
            raise PlanarLayoutError(f"light {light_id!r} names unknown region {region_id!r}")
        if intensity is not None and float(intensity) <= 0:
            raise PlanarLayoutError(f"light {light_id!r} has non-positive intensity")
        self.light_sources.append(LightSourceSpec(
            str(light_id), region_id, x=int(x), y=int(y), z=int(z),
            intensity=None if intensity is None else float(intensity),
        ))
        return light_id

    def _add_placement_light(self, placement_id: str, region_id: str,
                             intensity: float | None = None,
                             height_player_heights: float | None = None) -> None:
        light_id = (placement_id if placement_id.startswith("light:")
                    else f"light:{placement_id}")
        if any(item.light_id == light_id for item in self.light_sources):
            raise PlanarLayoutError(f"duplicate light id {light_id!r}")
        if intensity is not None and float(intensity) <= 0:
            raise PlanarLayoutError(f"light {light_id!r} has non-positive intensity")
        self.light_sources.append(LightSourceSpec(
            light_id, region_id, placement_id=placement_id,
            intensity=None if intensity is None else float(intensity),
            height_player_heights=(
                None if height_player_heights is None
                else float(height_player_heights)),
        ))

    def place_on_wall(
        self,
        placement_id: str,
        region_id: str,
        *,
        a1: tuple[int, int],
        a2: tuple[int, int],
        t: float = 0.5,
        height_player_heights: float = 0.65,
        offset_player_widths: float = 0.08,
        facing: str = "into_region",
        emits_light: bool = False,
        light_intensity: float | None = None,
        light_height_player_heights: float | None = None,
        **kwargs: Any,
    ) -> str:
        self.placements.append(PlacementSpec(
            placement_id=placement_id, region_id=region_id, x=0, y=0, z=0,
            anchor={
                "kind": "wall", "a1": [int(a1[0]), int(a1[1])], "a2": [int(a2[0]), int(a2[1])],
                "t": float(t), "height_player_heights": float(height_player_heights),
                "offset_player_widths": float(offset_player_widths), "facing": facing,
            },
            **kwargs,
        ))
        if emits_light:
            self._add_placement_light(
                placement_id, region_id, light_intensity,
                light_height_player_heights)
        return placement_id

    def place_on_floor(
        self,
        placement_id: str,
        region_id: str,
        *,
        local: tuple[float, float] = (0.5, 0.5),
        height_player_heights: float = 0.0,
        emits_light: bool = False,
        light_intensity: float | None = None,
        light_height_player_heights: float | None = None,
        **kwargs: Any,
    ) -> str:
        """Stand a sprite on the floor.

        `height_player_heights` lifts it off the floor by that much; at the
        default of zero the sprite's *bottom* rests on the floor, which is what
        "on the floor" has to mean. It did not: the anchor put the sprite's z --
        its centre, in Blood -- on the floor, so everything placed this way was
        buried to the waist. Callers that need the old behaviour can pass
        ``seat=None`` explicitly.
        """
        # Seating needs the tile's drawn height, so a layout built without the
        # game's ART keeps the old centre-on-the-anchor behaviour rather than
        # failing. Asking for `seat` explicitly is still an error if the tile is
        # unknown -- that is a request the compiler cannot honour quietly.
        if self.tile_extents:
            kwargs.setdefault("seat", "floor")
        kwargs["seat_clearance"] = _flat_lies_flush(
            kwargs.get("cstat", 0), height_player_heights)
        self.placements.append(PlacementSpec(
            placement_id=placement_id, region_id=region_id, x=0, y=0, z=0,
            anchor={
                "kind": "floor", "local": [float(local[0]), float(local[1])],
                "height_player_heights": float(height_player_heights),
            },
            **kwargs,
        ))
        if emits_light:
            self._add_placement_light(
                placement_id, region_id, light_intensity,
                light_height_player_heights)
        return placement_id

    def place_on_ceiling(
        self,
        placement_id: str,
        region_id: str,
        *,
        local: tuple[float, float] = (0.5, 0.5),
        height_player_heights: float = 0.0,
        **kwargs: Any,
    ) -> str:
        """Hang a sprite from the ceiling: its *top* against the ceiling.

        `height_player_heights` drops it below the ceiling by that much. The
        default was 0.15 and positioned the sprite's centre, which hung the top
        half of every lamp and chain through the ceiling.
        """
        if self.tile_extents:
            kwargs.setdefault("seat", "ceiling")
        kwargs["seat_clearance"] = _flat_lies_flush(
            kwargs.get("cstat", 0), height_player_heights)
        self.placements.append(PlacementSpec(
            placement_id=placement_id, region_id=region_id, x=0, y=0, z=0,
            anchor={
                "kind": "ceiling", "local": [float(local[0]), float(local[1])],
                "height_player_heights": float(height_player_heights),
            },
            **kwargs,
        ))
        return placement_id

    def set_player_start(self, region_id: str, *, x: int, y: int, z: int, angle: int = 0) -> None:
        self.player_start = PlayerStartSpec(region_id=region_id, x=int(x), y=int(y), z=int(z), angle=int(angle))

    def declared_joins(self) -> set[frozenset[str]]:
        """Region pairs the author has explicitly joined, by any means.

        A cross-layer edge is only allowed to take part in the planar pipeline
        where one of these says so, which is what makes "the layers meet where I
        said and nowhere else" a property of the source rather than a hope.
        """
        joins = {frozenset((a, b)) for a, b, _kind in self.special_pairs}
        for connection in self.connections.values():
            if connection.region_b:
                joins.add(frozenset((connection.region_a, connection.region_b)))
        for partition in self.partitions.values():
            if partition.region_b:
                joins.add(frozenset((partition.region_a, partition.region_b)))
        return joins

    def separate_arrangements(self, left: str, right: str,
                              joins: set[frozenset[str]] | None = None) -> bool:
        """Are these two regions in different planar arrangements?

        Two regions of different declared layers are two different plans that
        happen to be drawn on the same paper. Their edges must not split each
        other, pair with each other, or be refused for crossing each other --
        the whole point of a layer is that the street's kerb is allowed to run
        straight through the cellar's wall, because they are not at the same
        height.

        A layout that declares no layers answers False for every pair and
        behaves exactly as it did before layers existed.
        """
        if not getattr(self, "layers", None):
            return False
        left_region = self.regions.get(left)
        right_region = self.regions.get(right)
        if left_region is None or right_region is None:
            return False
        if left_region.layer == right_region.layer:
            return False
        known = self.declared_joins() if joins is None else joins
        return frozenset((left, right)) not in known

    def declare_special(self, region_a: str, region_b: str, kind: str) -> None:
        self.special_pairs.append((region_a, region_b, kind))
        if region_a in self.regions:
            self.regions[region_a].stack_pair = region_b
            self.regions[region_a].special = kind
        if region_b in self.regions:
            self.regions[region_b].stack_pair = region_a
            self.regions[region_b].special = kind

    def _region(self, region_id: str) -> RegionSpec:
        try:
            return self.regions[region_id]
        except KeyError as exc:
            raise PlanarLayoutError(f"unknown region {region_id!r}") from exc

    def to_dict(self) -> dict[str, Any]:
        return {
            "$schema": SCHEMA,
            "schema_version": SCHEMA_VERSION,
            "name": self.name,
            "visibility": self.visibility,
            "regions": [
                {
                    "region_id": region.region_id,
                    "outer": [list(point) for point in region.outer],
                    "holes": [[list(point) for point in hole] for hole in region.holes],
                    "ceiling_z": region.ceiling_z,
                    "floor_z": region.floor_z,
                    "ceiling_picnum": region.ceiling_picnum,
                    "floor_picnum": region.floor_picnum,
                    "ceiling_stat": region.ceiling_stat,
                    "floor_stat": region.floor_stat,
                    "ceiling_heinum": getattr(region.ceiling_slope, "heinum", None),
                    "floor_heinum": getattr(region.floor_slope, "heinum", None),
                    "wall_picnum": region.wall_picnum,
                    "layer": region.layer,
                    "special": region.special,
                    "parallax_ceiling": region.parallax_ceiling,
                    "type": region.type,
                    "role": region.role,
                    "intent": dict(region.intent),
                }
                for region in self.regions.values()
            ],
            "connections": [
                {
                    "connection_id": item.connection_id,
                    "region_a": item.region_a,
                    "region_b": item.region_b,
                    "role": item.role,
                    "interval": None if item.a1 is None else [list(item.a1), list(item.a2 or item.a1)],
                    "gated": item.gated,
                    "face_picnum": item.face_picnum,
                    "face_x_repeat_scale": item.face_x_repeat_scale,
                    "face_y_repeat_scale": item.face_y_repeat_scale,
                }
                for item in self.connections.values()
            ],
            "partitions": [
                {
                    "partition_id": item.partition_id,
                    "region_a": item.region_a,
                    "region_b": item.region_b,
                    "role": item.role,
                }
                for item in self.partitions.values()
            ],
            "placements": [
                {
                    "placement_id": item.placement_id,
                    "region_id": item.region_id,
                    "x": item.x, "y": item.y, "z": item.z,
                    "type": item.type, "picnum": item.picnum,
                }
                for item in self.placements
            ],
            "player_start": None if self.player_start is None else {
                "region_id": self.player_start.region_id,
                "x": self.player_start.x, "y": self.player_start.y,
                "z": self.player_start.z, "angle": self.player_start.angle,
            },
            "special_pairs": [
                {"region_a": a, "region_b": b, "kind": kind} for a, b, kind in self.special_pairs
            ],
        }

    def declare_layer(self, layer_id: str, *, ceiling_z: int, floor_z: int,
                      note: str = "") -> Any:
        """Name a height band that a set of regions occupies.

        Until a layout declares one, `RegionSpec.layer` is a label with no
        consequences and every region shares one plan. Declaring layers is what
        permits regions to overlap in XY -- and what makes them prove they can.
        See `bloodmap.layers`.
        """
        from .layers import declare_layer

        return declare_layer(self, layer_id, ceiling_z=ceiling_z,
                             floor_z=floor_z, note=note)

    def compile(self) -> CompiledLayout:
        if self.player_start is None:
            raise PlanarLayoutError("player start has not been assigned")
        self._validate_regions()
        self._approved_layer_overlaps = []
        if getattr(self, "layers", None):
            from .layers import enforce

            self._approved_layer_overlaps = [
                overlap for overlap in enforce(self) if not overlap.declared
            ]
        source_edges = self._source_edges()
        split_points = self._collect_split_points(source_edges)
        atomics = self._split_edges(source_edges, split_points)
        conservation = self._conservation(source_edges, atomics)
        if not conservation.conserved:
            raise PlanarLayoutError(
                "geometry conservation failed "
                f"dropped={conservation.dropped_source_edges} duplicated={conservation.duplicated_source_edges}"
            )
        pairs, connection_report, leftover = self._pair_portals(atomics)
        if leftover:
            conservation.unpaired_portal_candidates = leftover
            raise PlanarLayoutError(
                "unexplained unpaired portal candidates: " + ", ".join(leftover[:12])
            )
        level, allocations, wall_from_atomic = self._emit(atomics, pairs)
        builder = LevelBuilder(level)
        for region in self.regions.values():
            sector_id = allocations[region.region_id].sector_id
            if region.sector_behavior:
                builder.set_behavior("sector", sector_id, **region.sector_behavior)
        for connection in self.connections.values():
            if not connection.wall_behavior:
                continue
            realized = [
                item for item in connection_report
                if item["connection_id"] == connection.connection_id and item["status"] == "realized"
            ]
            atomic_ids = [aid for item in realized for aid in item.get("atomic_ids", [])]
            if len(realized) != 1 and connection.attach_policy != "all_atomic":
                raise PlanarLayoutError(
                    f"connection {connection.connection_id} split into {len(realized)} atomic portals; "
                    "refusing to duplicate XWALL (set attach_policy='all_atomic' or tighten the interval)"
                )
            for atomic_id in atomic_ids:
                wall_id = wall_from_atomic[atomic_id]
                builder.set_behavior("wall", wall_id, **connection.wall_behavior)
        # Finish inheritance, before anything reads a sector's tiles.
        for region in self.regions.values():
            if not region.inherit_finish:
                continue
            sector_id = allocations[region.region_id].sector_id
            sector = builder.level.sectors[sector_id]["fields"]
            start = int(sector["wall_ptr"])
            count = int(sector["wall_count"])
            # The donor is the largest neighbour, but a *roofed* neighbour is
            # preferred over an open one whatever their sizes.
            #
            # Picking purely by size gave the chapel's door and its south porch
            # the courtyard's sky, because the courtyard is the biggest thing
            # they touch -- so the player stood inside a doorway of a roofed
            # building and looked up at clouds. Blood does not do that: of the
            # 849 small campaign sectors that touch both an open space and a
            # roofed one, **83% are roofed**, and of the 82 that are Z-motion
            # doors, **90%** are.
            #
            # It is a strong habit rather than a law -- a gate in an outdoor wall
            # is legitimately open, and 7.1% of the campaign's doors are -- so a
            # region that genuinely wants the sky says `parallax_ceiling=True`
            # for itself and does not inherit.
            best = None
            for wall_id in range(start, start + count):
                other = int(builder.level.walls[wall_id]["fields"].get("next_sector", -1))
                if other < 0:
                    continue
                neighbour = builder.level.sectors[other]["fields"]
                roofed = not int(neighbour.get("ceiling_stat", 0)) & 1
                size = int(neighbour["wall_count"])
                rank = (roofed, size)
                if best is None or rank > best[0]:
                    best = (rank, other)
            if best is None:
                raise PlanarLayoutError(
                    f"{region.region_id} inherits its finish but opens onto nothing"
                )
            donor = builder.level.sectors[best[1]]["fields"]
            if region.inherit_finish in ("ceiling", "both"):
                sector["ceiling_picnum"] = int(donor["ceiling_picnum"])
                # ...and whether that ceiling is the sky, which is not a separate
                # decision. Inheriting the tile without the flag gave three
                # doorways a 64x400 sky panel drawn as an ordinary ceiling --
                # sampled at 64x256, so most of it was never drawn at all.
                sector["ceiling_stat"] = (
                    int(sector.get("ceiling_stat", 0)) & ~1
                    | int(donor.get("ceiling_stat", 0)) & 1)
            if region.inherit_finish in ("floor", "both"):
                sector["floor_picnum"] = int(donor["floor_picnum"])

        # Secrets: the wiring the engine counts, not a role name.
        for region in self.regions.values():
            if not region.secret:
                continue
            sector_id = allocations[region.region_id].sector_id
            builder.set_behavior(
                "sector", sector_id,
                tx_id=SECRET_FOUND_CHANNEL, command=NUMERIC_COMMAND_BASE,
                trigger_enter=1, trigger_once=1, state=0,
                **dict(region.sector_behavior))

        # Openings get their own material before doors do, so a door_face still
        # wins on the sectors that declare one.
        #
        # A portal wall is two surfaces at once, and only one of them is the
        # jamb. Build draws the band *above* the mouth from this same wall's
        # picnum, so painting the whole wall with the opening tile hangs a slab
        # of the dressing material over the doorway -- the "texture break above
        # a corridor mouth". One of these in the candidate was a 4.35-human
        # sheet of smooth ashlar (tile 5) floating on a rubble wall (110).
        #
        # The corpus draws the line the same place. Of the campaign's 10,475
        # lintels, **70% carry the room's own field tile**, while separately 74%
        # of its multi-tile rooms dress their two-sided walls. Both hold at once
        # because the dressing goes on openings that have no lintel to carry --
        # full-height mouths and seams. So: dress the opening, but where a
        # lintel exists, the facade keeps it. See `bloodmap/aperture.py`.
        for region in self.regions.values():
            if region.portal_wall_picnum is None:
                continue
            allocation = allocations[region.region_id]
            sector = builder.level.sectors[allocation.sector_id]
            start = int(sector["fields"]["wall_ptr"])
            count = int(sector["fields"]["wall_count"])
            my_ceiling = int(sector["fields"]["ceiling_z"])
            for wall_id in range(start, start + count):
                fields = builder.level.walls[wall_id]["fields"]
                other = int(fields.get("next_sector", -1))
                if other < 0:
                    continue                     # the field between the openings
                their_ceiling = int(
                    builder.level.sectors[other]["fields"]["ceiling_z"])
                if their_ceiling - my_ceiling > _LINTEL_FLOOR:
                    # This wall carries a visible band above the mouth. It is
                    # facade, and facade is this room's own material.
                    continue
                fields["picnum"] = int(region.portal_wall_picnum)

        # Doorway faces first, so an explicit connection face still overrides one.
        for region in self.regions.values():
            if region.door_face is None:
                continue
            sector = builder.level.sectors[allocations[region.region_id].sector_id]
            start = int(sector["fields"]["wall_ptr"])
            count = int(sector["fields"]["wall_count"])
            painted = 0
            for wall_id in range(start, start + count):
                fields = builder.level.walls[wall_id]["fields"]
                if int(fields.get("next_sector", -1)) < 0:
                    continue                      # a jamb keeps the region's own tile
                fields["picnum"] = int(region.door_face)
                nxt = int(fields.get("next_wall") or -1)
                if nxt >= 0:
                    builder.level.walls[nxt]["fields"]["picnum"] = int(region.door_face)
                painted += 1
            if not painted:
                raise PlanarLayoutError(
                    f"{region.region_id} declares a door_face but owns no portal to show it on"
                )

        self._apply_carried_walls(builder, allocations)
        self._apply_painted_walls(builder, allocations)

        for connection in self.connections.values():
            if not _connection_has_face(connection):
                continue
            realized = [
                item for item in connection_report
                if item["connection_id"] == connection.connection_id and item["status"] == "realized"
            ]
            painted: set[int] = set()
            for item in realized:
                for atomic_id in item.get("atomic_ids", []):
                    wall_id = wall_from_atomic[atomic_id]
                    painted.add(wall_id)
                    nxt = int(builder.level.walls[wall_id]["fields"].get("next_wall") or -1)
                    if nxt >= 0:
                        painted.add(nxt)
            for wall_id in painted:
                fields = builder.level.walls[wall_id]["fields"]
                if connection.face_picnum is not None:
                    fields["picnum"] = int(connection.face_picnum)
                if connection.face_over_picnum is not None:
                    fields["over_picnum"] = int(connection.face_over_picnum)
                if connection.face_shade is not None:
                    fields["shade"] = int(connection.face_shade)
                if connection.face_cstat is not None:
                    fields["cstat"] = int(connection.face_cstat)
                if connection.face_x_repeat is not None:
                    fields["x_repeat"] = int(connection.face_x_repeat)
                if connection.face_y_repeat is not None:
                    fields["y_repeat"] = int(connection.face_y_repeat)
                if connection.face_x_repeat_scale is not None:
                    fields["x_repeat"] = max(
                        1, min(255, round(int(fields["x_repeat"])
                                          * connection.face_x_repeat_scale)))
                if connection.face_y_repeat_scale is not None:
                    fields["y_repeat"] = max(
                        1, min(255, round(int(fields["y_repeat"])
                                          * connection.face_y_repeat_scale)))
        placement_sprites: dict[str, int] = {}
        for placement in self.placements:
            region = self.regions[placement.region_id]
            sector_id = allocations[placement.region_id].sector_id
            if placement.anchor:
                from .placement import resolve_anchor
                resolved = resolve_anchor(
                    kind=str(placement.anchor["kind"]),
                    a1=tuple(placement.anchor.get("a1") or (0, 0)),
                    a2=tuple(placement.anchor.get("a2") or (0, 0)),
                    floor_z=region.floor_z,
                    ceiling_z=region.ceiling_z,
                    t=float(placement.anchor.get("t") or 0.5),
                    height_player_heights=float(placement.anchor.get("height_player_heights") or 0.0),
                    offset_player_widths=float(placement.anchor.get("offset_player_widths") or 0.08),
                    facing=str(placement.anchor.get("facing") or "into_region"),
                    local=tuple(placement.anchor["local"]) if placement.anchor.get("local") else None,
                    outer=list(region.outer),
                )
                placement.x, placement.y, placement.z = resolved["x"], resolved["y"], resolved["z"]
                if placement.anchor.get("kind") == "wall":
                    placement.angle = resolved["angle"]
            # A wall placement must carry a wall mounting. A floor-aligned
            # sprite is a flat plane at its own z, so putting one on a wall
            # leaves it floating edge-on with nothing under it -- and because it
            # has no vertical extent, no seating check can see that it is wrong.
            if (placement.anchor or {}).get("kind") == "wall":
                if int(placement.cstat) & 0x30 == 0x20:
                    raise PlanarLayoutError(
                        f"placement {placement.placement_id} is mounted on a wall but "
                        f"tile {placement.picnum} carries floor alignment (cstat "
                        f"{placement.cstat}); a floor sprite on a wall hangs in the air"
                    )
            if not placement.seat and self.tile_extents:
                # A wall mount is positioned by its centre, so a tall tile can
                # still hang through the floor or poke out of the ceiling --
                # 15 of this level's 58 decorations did. Pull the whole sprite
                # back inside the room it is in, rather than only its z, which
                # is all `resolve_anchor` can do without knowing the tile.
                extent = self.tile_extents.get(int(placement.picnum))
                if extent is not None:
                    above, below = sprite_extent(
                        extent[0], placement.y_repeat, placement.cstat, y_offset=extent[1])
                    if above + below <= abs(region.floor_z - region.ceiling_z):
                        placement.z = max(region.ceiling_z + above,
                                          min(region.floor_z - below, placement.z))
            if placement.seat:
                extent = self.tile_extents.get(int(placement.picnum))
                if extent is None:
                    raise PlanarLayoutError(
                        f"placement {placement.placement_id} asks to be seated on the "
                        f"{placement.seat} but tile {placement.picnum} has no extent; "
                        f"pass tile_extents to PlanarLayout"
                    )
                tile_height, y_offset = extent
                above, below = sprite_extent(
                    tile_height, placement.y_repeat, placement.cstat, y_offset=y_offset)
                room = abs(region.floor_z - region.ceiling_z)
                if above + below > room:
                    # Not a rounding problem: the campaign draws some tiles at
                    # one size only -- tile 641 is 5.82 player heights in every
                    # one of its 71 uses -- so a room shorter than that is a room
                    # the decoration does not belong in. Saying so is more use
                    # than quietly shrinking it to a size Blood never draws.
                    raise PlanarLayoutError(
                        f"placement {placement.placement_id}: tile {placement.picnum} "
                        f"is {above + below} tall at y_repeat {placement.y_repeat} but "
                        f"{placement.region_id} is only {room} -- pick a tile the room "
                        f"can hold, or raise the room"
                    )
                placement.z = seated_z(
                    seat=placement.seat, floor_z=region.floor_z, ceiling_z=region.ceiling_z,
                    tile_height=tile_height, y_repeat=placement.y_repeat,
                    cstat=placement.cstat, y_offset=y_offset,
                    clearance=placement.seat_clearance,
                )
            try:
                sprite_id = builder.add_sprite(
                    sector=sector_id, x=placement.x, y=placement.y, z=placement.z,
                    type=placement.type, picnum=placement.picnum, status=placement.status,
                    angle=placement.angle, cstat=placement.cstat, x_repeat=placement.x_repeat,
                    y_repeat=placement.y_repeat, shade=placement.shade, pal=placement.pal,
                )
            except ConstructionError as exc:
                raise PlanarLayoutError(
                    f"placement {placement.placement_id} in {placement.region_id} "
                    f"at {(placement.x, placement.y, placement.z)}: {exc}"
                ) from exc
            placement_sprites[placement.placement_id] = sprite_id
            # A sprite on one of these statnums is given an XSprite whether or
            # not the author asked for behaviour, because an empty dict is falsy
            # and that is the line that shipped a segfault: a dude without an
            # XSprite sends `aiInitSprite` through xsprite[-1].
            if placement.behavior or int(placement.status) in XSPRITE_REQUIRED_STATNUMS:
                builder.set_behavior("sprite", sprite_id, **placement.behavior)
        start = self.player_start
        builder.set_player_start(
            sector=allocations[start.region_id].sector_id,
            x=start.x, y=start.y, z=start.z, angle=start.angle,
        )
        # Markers, before anything validates the structure. `dbLoadMap` rebuilds
        # marker0/marker1 from each marker's `owner` and deletes any marker it
        # cannot bind, so this is load-bearing rather than cosmetic.
        #: A marker's `owner` is the sector it CONTROLS, not the one it stands
        #: in -- 387 of the campaign's markers sit somewhere else, and E1M1's
        #: casket puts its "to" marker inside the cover, which has no XSECTOR
        #: at all. `marker_owner` on the placement says which sector it marks.
        marker_owners = {}
        for placement in self.placements:
            owner_region = getattr(placement, "marker_owner", None)
            if not owner_region:
                continue
            sprite_id = placement_sprites.get(placement.placement_id)
            allocation = allocations.get(owner_region)
            if sprite_id is None or allocation is None:
                raise PlanarLayoutError(
                    f"{placement.placement_id}: marker_owner "
                    f"{owner_region!r} built no sector")
            marker_owners[str(sprite_id)] = allocation.sector_id
        bind_markers(builder.level, owners=marker_owners)
        native_errors = [item for item in validate_map(builder.level.to_disk_map()) if item.severity == "error"]
        if native_errors:
            first = native_errors[0]
            raise PlanarLayoutError(f"native structure: {first.code} at {first.location}: {first.message}")
        specials = []
        for a, b, kind in self.special_pairs:
            specials.append((allocations[a].sector_id, allocations[b].sector_id, kind))
        # An overlap the layer conditions approved is a declared relationship
        # like any other, and the geometry audit has to be told so -- otherwise
        # it refuses in XY exactly what `bloodmap.layers` just proved safe in z.
        for overlap in self._approved_layer_overlaps:
            if overlap.left in allocations and overlap.right in allocations:
                specials.append((allocations[overlap.left].sector_id,
                                 allocations[overlap.right].sector_id, "layer"))
        for partition in self.partitions.values():
            if partition.region_b and partition.region_a in allocations and partition.region_b in allocations:
                specials.append((
                    allocations[partition.region_a].sector_id,
                    allocations[partition.region_b].sector_id,
                    partition.role,
                ))
        gated_sectors = {
            allocations[region.region_id].sector_id
            for region in self.regions.values()
            if region.type in {600, 602} or region.role in {"doorway", "gated_pocket"}
        }
        zero_exit = {
            allocations[region.region_id].sector_id
            for region in self.regions.values()
            if region.declared_zero_exit or region.special in {"water", "stack", "helper"}
        }
        intended = [(item.region_a, item.region_b) for item in self.connections.values()]
        # Which sectors are not on the same sheet of paper. The audit asks its
        # questions in plan, and two layers do not share one.
        joins = self.declared_joins()
        apart = [
            (allocations[left].sector_id, allocations[right].sector_id)
            for index, left in enumerate(self.regions)
            for right in list(self.regions)[index + 1:]
            if self.separate_arrangements(left, right, joins)
        ]
        diagnostics = validate_authored_level(
            builder.level,
            separate_arrangements=apart,
            intended_adjacency=intended,
            gated_sectors=gated_sectors,
            declared_zero_exit=zero_exit,
            declared_specials=specials,
            allocations={key: value.sector_id for key, value in allocations.items()},
            connection_report=connection_report,
        )
        try:
            construction_preflight(diagnostics)
            #: And the poses the map is NOT saved in. Everything above reads
            #: the rest pose; a moving sector is in it for one instant, and a
            #: travel that inverts the sector receiving it is invisible until
            #: something steps the motion.
            self._preflight_swept(builder.level.to_disk_map())
        except AuthoredGeometryError as exc:
            raise PlanarLayoutError(str(exc)) from exc
        owners = [-1] * len(builder.level.walls)
        for sector_id, sector in enumerate(builder.level.sectors):
            first = int(sector["fields"]["wall_ptr"])
            count = int(sector["fields"]["wall_count"])
            for wall_id in range(first, first + count):
                if owners[wall_id] != -1:
                    conservation.walls_owned_once = False
                owners[wall_id] = sector_id
        conservation.walls_owned_once = all(owner >= 0 for owner in owners) and -1 not in owners
        conservation.emitted_directed_edges = len(builder.level.walls)
        if not conservation.conserved:
            raise PlanarLayoutError("emitted walls were not owned exactly once")
        # Refresh connection report with native wall ids.
        atomic_to_wall = wall_from_atomic
        for item in connection_report:
            item["walls"] = [atomic_to_wall[aid] for aid in item.get("atomic_ids", []) if aid in atomic_to_wall]
            item["sectors"] = [
                allocations[item["region_a"]].sector_id,
                allocations[item["region_b"]].sector_id,
            ]
        # Wall sprites with nothing behind them.
        #
        # This cannot run with the other placement checks: those happen before
        # the portals are paired, and until a wall knows its neighbour there is
        # no way to ask whether it is solid. So it runs here, once the level is
        # otherwise finished and every `next_sector` is filled in.
        floating: list[str] = []
        for placement in self.placements:
            if (placement.anchor or {}).get("kind") != "wall":
                continue
            if placement.spans_opening:
                continue
            sprite_id = placement_sprites.get(placement.placement_id)
            if sprite_id is None:
                continue
            fields = builder.level.sprites[sprite_id]["fields"]
            sector_id = int(fields["sector"])
            wall_id = _nearest_wall_of(
                builder.level, sector_id, int(fields["x"]), int(fields["y"]))
            if wall_id is None:
                continue
            band = _open_band(builder.level, sector_id, wall_id)
            if band is None:
                continue
            extents = self.tile_extents.get(int(placement.picnum))
            half = 0
            if extents:
                half = int(fields["y_repeat"]) * 4 * int(extents[0]) // 2
            top, bottom = int(fields["z"]) - half, int(fields["z"]) + half
            if top < band[1] and bottom > band[0]:
                floating.append(
                    f"{placement.placement_id} (tile {placement.picnum}) on wall "
                    f"{wall_id} of sector {sector_id}, open over z "
                    f"{band[0]}..{band[1]}"
                )
        if floating:
            listing = ("\n  " + "\n  ".join(floating))
            raise PlanarLayoutError(
                "%d wall sprites hang over an opening and have nothing behind "
                "them:%s" % (len(floating), listing)
                + "\nMove each onto solid wall, or set spans_opening=True "
                "where it is meant to fill the gap."
            )

        if self.flat_tile_sizes:
            _check_flat_tiles(builder.level, self.flat_tile_sizes, allocations)

        lighting_report = self._apply_declared_lighting(
            builder.level, allocations, placement_sprites,
        )

        for hook in self.post_compile:
            hook(builder.level)
        return CompiledLayout(
            level=builder.level,
            allocations=allocations,
            placement_sprites=placement_sprites,
            wall_from_atomic=wall_from_atomic,
            conservation=conservation,
            connection_report=connection_report,
            declared_specials=specials,
            layout=self,
            lighting_report=lighting_report,
        )

    def _apply_declared_lighting(self, level: LevelIR,
                                 allocations: dict[str, SectorAllocation],
                                 placement_sprites: dict[str, int]) -> dict[str, Any]:
        """Run LightBomb from authored sources, preserving explicit shades.

        Region shade fields are overrides, not lighting input.  A surface with
        no stated shade starts at its derived campaign baseline and is then
        illuminated here.  An explicitly stated surface remains untouched,
        which makes the escape hatch local and inspectable.
        """
        if not self.light_sources:
            return {"enabled": False, "sources": 0}

        lights: list[tuple[int, int, int, int] | tuple[int, int, int, int, float]] = []
        source_ids: list[str] = []
        for source in self.light_sources:
            sector = allocations[source.region_id].sector_id
            if source.placement_id is not None:
                sprite_id = placement_sprites.get(source.placement_id)
                if sprite_id is None:
                    raise PlanarLayoutError(
                        f"light {source.light_id!r} follows missing placement "
                        f"{source.placement_id!r}"
                    )
                fields = level.sprites[sprite_id]["fields"]
                sprite_sector = int(fields["sector"])
                source_z = int(fields["z"])
                if source.height_player_heights is not None:
                    floor_z = int(level.sectors[sprite_sector]["fields"]["floor_z"])
                    source_z = floor_z - int(round(
                        source.height_player_heights * PLAYER_HEIGHT))
                position = (int(fields["x"]), int(fields["y"]),
                            source_z, sprite_sector)
            else:
                if source.x is None or source.y is None or source.z is None:
                    raise PlanarLayoutError(f"light {source.light_id!r} has no position")
                position = (source.x, source.y, source.z, sector)
            if source.intensity is None:
                lights.append(position)
            else:
                lights.append((*position, float(source.intensity)))
            source_ids.append(source.light_id)

        protected = {"wall": set(), "floor": set(), "ceiling": set()}
        for region_id, region in self.regions.items():
            allocation = allocations[region_id]
            generated = set(region.intent.get("generated_surfaces", ()))
            if region.wall_shade is not None and "wall" not in generated:
                protected["wall"].update(allocation.wall_ids)
            if region.floor_shade is not None and "floor" not in generated:
                protected["floor"].add(allocation.sector_id)
            if region.ceiling_shade is not None and "ceiling" not in generated:
                protected["ceiling"].add(allocation.sector_id)

        from .lightbomb import light_bomb

        report = light_bomb(level, lights, protected=protected)
        report.update(
            enabled=True,
            source_ids=source_ids,
            source_intensities={
                source.light_id: (source.intensity if source.intensity is not None else 1.0)
                for source in self.light_sources
            },
            source_heights={
                source.light_id: source.height_player_heights
                for source in self.light_sources
                if source.height_player_heights is not None
            },
        )
        return report

    def _validate_regions(self) -> None:
        for region in self.regions.values():
            errors = validate_loop(region.outer, role="outer")
            if errors:
                raise PlanarLayoutError(f"{region.region_id} outer: {errors[0]}")
            if int(region.ceiling_z) > int(region.floor_z):
                raise PlanarLayoutError(f"{region.region_id} ceiling is below its floor")
            for hole in region.holes:
                errors = validate_loop(hole, role="hole")
                if errors:
                    raise PlanarLayoutError(f"{region.region_id} hole: {errors[0]}")
        declared = {frozenset((left, right)) for left, right, _kind in self.special_pairs}
        joins = self.declared_joins()
        members = list(self.regions.values())
        for index, left in enumerate(members):
            for right in members[index + 1:]:
                if frozenset((left.region_id, right.region_id)) in declared:
                    continue
                # Two declared layers are two plans on one sheet of paper. What
                # they do to each other in XY is `bloodmap.layers`' business, and
                # it judges them on height band and portal separation rather than
                # refusing them outright.
                if self.separate_arrangements(left.region_id, right.region_id, joins):
                    continue
                if left.stack_pair == right.region_id or right.stack_pair == left.region_id:
                    continue
                if any(loops_equivalent(left.outer, hole) for hole in right.holes) or any(
                    loops_equivalent(right.outer, hole) for hole in left.holes
                ):
                    continue
                loops_l = [left.outer, *left.holes]
                loops_r = [right.outer, *right.holes]
                if loops_equivalent(left.outer, right.outer):
                    raise PlanarLayoutError(
                        f"independent regions {left.region_id} and {right.region_id} "
                        "have identical XY footprints without a declared stack/water relationship"
                    )
                relation = polygon_relation(loops_l, loops_r)
                kind = str(relation["kind"])
                if kind in {"partial_area_overlap", "full_containment_a_in_b", "full_containment_b_in_a"}:
                    raise PlanarLayoutError(
                        f"independent regions {left.region_id} and {right.region_id} "
                        f"have XY {kind} without a declared special relationship"
                    )
                for a1, a2 in _edges_of(left):
                    for b1, b2 in _edges_of(right):
                        classified = classify_segment_pair(a1, a2, b1, b2)
                        if classified and classified["kind"] == "proper_crossing":
                            crossing = integer_intersection(a1, a2, b1, b2)
                            if crossing is None:
                                raise PlanarLayoutError(
                                    f"proper crossing between {left.region_id} and {right.region_id} "
                                    "does not land on integer Build coordinates"
                                )
                            raise PlanarLayoutError(
                                f"proper crossing between {left.region_id} and {right.region_id} "
                                f"at {crossing}; refuse automatic junction"
                            )

    def _source_edges(self) -> list[SourceEdge]:
        edges: list[SourceEdge] = []
        for region in self.regions.values():
            for index, start in enumerate(region.outer):
                end = region.outer[(index + 1) % len(region.outer)]
                edges.append(SourceEdge(
                    edge_id=f"{region.region_id}:outer:{index}",
                    region_id=region.region_id, a=start, b=end,
                ))
            for hole_index, hole in enumerate(region.holes):
                for index, start in enumerate(hole):
                    end = hole[(index + 1) % len(hole)]
                    edges.append(SourceEdge(
                        edge_id=f"{region.region_id}:hole:{hole_index}:{index}",
                        region_id=region.region_id, a=start, b=end,
                    ))
        return edges

    def _collect_split_points(self, edges: list[SourceEdge]) -> dict[str, set[Point]]:
        points: dict[str, set[Point]] = {edge.edge_id: {edge.a, edge.b} for edge in edges}
        # A pair the author declared as stacked or overlapping is allowed to
        # cross.  Build has no XY exclusivity rule and original maps rely on
        # that; refusing here would mean no decompiled original could ever be
        # recompiled, while an *undeclared* crossing stays an error.
        declared = {
            frozenset((left, right)) for left, right, _kind in self.special_pairs
        }
        joins = self.declared_joins()
        for left in edges:
            for right in edges:
                if left.edge_id >= right.edge_id:
                    continue
                classified = classify_segment_pair(left.a, left.b, right.a, right.b)
                if classified is None:
                    continue
                kind = classified["kind"]
                if frozenset((left.region_id, right.region_id)) in declared:
                    continue
                # Edges of different layers are not in the same plan, so they
                # neither split nor obstruct each other. Splitting them here is
                # what would put a vertex from the street into the cellar's wall.
                if self.separate_arrangements(left.region_id, right.region_id, joins):
                    continue
                if kind == "proper_crossing":
                    if left.region_id == right.region_id:
                        continue
                    crossing = integer_intersection(left.a, left.b, right.a, right.b)
                    raise PlanarLayoutError(
                        f"proper crossing {left.edge_id} x {right.edge_id}"
                        + ("" if crossing is None else f" at {crossing}")
                        + ("" if crossing is not None else "; intersection is not an integer lattice point")
                    )
                if kind == "t_junction":
                    point = classified["point"]
                    if on_segment_strict(left.a, left.b, point):
                        points[left.edge_id].add(point)
                    if on_segment_strict(right.a, right.b, point):
                        points[right.edge_id].add(point)
                elif kind in {
                    "partial_collinear_overlap",
                    "exact_reversed_coincident",
                    "exact_same_direction_coincident",
                }:
                    overlap = classified.get("overlap")
                    extra = [left.a, left.b, right.a, right.b]
                    if overlap:
                        extra.extend(overlap)
                    for edge in (left, right):
                        for point in extra:
                            if on_segment_inclusive(edge.a, edge.b, point):
                                points[edge.edge_id].add(point)
        for connection in self.connections.values():
            if connection.a1 is None or connection.a2 is None:
                continue
            for edge in edges:
                if edge.region_id not in {connection.region_a, connection.region_b}:
                    continue
                for point in (connection.a1, connection.a2):
                    if on_segment_strict(edge.a, edge.b, point) or point in {edge.a, edge.b}:
                        if on_segment_inclusive(edge.a, edge.b, point):
                            points[edge.edge_id].add(point)
        for partition in self.partitions.values():
            if partition.a1 is None or partition.a2 is None:
                continue
            for edge in edges:
                if edge.region_id not in {partition.region_a, partition.region_b}:
                    continue
                for point in (partition.a1, partition.a2):
                    if on_segment_inclusive(edge.a, edge.b, point):
                        points[edge.edge_id].add(point)
        return points

    def _split_edges(
        self, edges: list[SourceEdge], split_points: dict[str, set[Point]],
    ) -> list[AtomicEdge]:
        atomics: list[AtomicEdge] = []
        for edge in edges:
            pieces = atomic_subsegments(edge.a, edge.b, split_points[edge.edge_id])
            if not pieces:
                raise PlanarLayoutError(f"source edge {edge.edge_id} produced no atomic segments")
            reconstructed: list[Point] = [pieces[0][0], *(item[1] for item in pieces)]
            if reconstructed[0] != edge.a or reconstructed[-1] != edge.b:
                raise PlanarLayoutError(f"split of {edge.edge_id} does not reconstruct the source edge")
            for index, (start, end) in enumerate(pieces):
                atomics.append(AtomicEdge(
                    atomic_id=f"{edge.edge_id}:{index}",
                    source_id=edge.edge_id,
                    region_id=edge.region_id,
                    a=start, b=end,
                ))
        return atomics

    def _conservation(self, source: list[SourceEdge], atomics: list[AtomicEdge]) -> ConservationReport:
        by_source: dict[str, list[AtomicEdge]] = defaultdict(list)
        for edge in atomics:
            by_source[edge.source_id].append(edge)
        dropped = []
        duplicated = []
        for edge in source:
            pieces = by_source.get(edge.edge_id, [])
            if not pieces:
                dropped.append(edge.edge_id)
                continue
            cursor = edge.a
            for piece in pieces:
                if piece.a != cursor:
                    dropped.append(edge.edge_id)
                    break
                cursor = piece.b
            else:
                if cursor != edge.b:
                    dropped.append(edge.edge_id)
        seen = [edge.atomic_id for edge in atomics]
        if len(seen) != len(set(seen)):
            duplicated = [item for item in seen if seen.count(item) > 1]
        split_count = sum(max(0, len(items) - 1) for items in by_source.values())
        return ConservationReport(
            source_directed_edges=len(source),
            emitted_directed_edges=len(atomics),
            dropped_source_edges=dropped,
            duplicated_source_edges=duplicated,
            unpaired_portal_candidates=[],
            split_count=split_count,
            atomic_segments=len(atomics),
            walls_owned_once=True,
        )

    def _pair_portals(
        self, atomics: list[AtomicEdge],
    ) -> tuple[list[tuple[AtomicEdge, AtomicEdge]], list[dict[str, Any]], list[str]]:
        by_undirected: dict[tuple[Point, Point], list[AtomicEdge]] = defaultdict(list)
        for edge in atomics:
            by_undirected[undirected_key(edge.a, edge.b)].append(edge)
        reverse_index: dict[tuple[str, tuple[Point, Point]], AtomicEdge] = {}
        for edge in atomics:
            reverse_index[(edge.region_id, (edge.b, edge.a))] = edge

        used: set[str] = set()
        pairs: list[tuple[AtomicEdge, AtomicEdge]] = []
        report: list[dict[str, Any]] = []

        def interval_contains(connection: ConnectionSpec, edge: AtomicEdge) -> bool:
            if connection.a1 is None or connection.a2 is None:
                return True
            overlap = collinear_overlap_interval(connection.a1, connection.a2, edge.a, edge.b)
            if overlap is None:
                return False
            return undirected_key(*overlap) == undirected_key(edge.a, edge.b)

        # A blocked portal is a portal for the purposes of pairing: the walls are
        # joined and then flagged, which is how Blood builds a rail. Turning it
        # into a ConnectionSpec here keeps one pairing pass rather than a second
        # one that would have to repeat the interval and reversal rules.
        blocked = [
            ConnectionSpec(
                connection_id=partition.partition_id,
                region_a=partition.region_a, region_b=partition.region_b,
                role="blocked_portal", a1=partition.a1, a2=partition.a2,
                min_width=0, min_opening=0,
            )
            for partition in self.partitions.values()
            if partition.role == "blocked_portal" and partition.region_b
        ]
        for connection in list(self.connections.values()) + blocked:
            candidates = []
            for edge in atomics:
                if edge.region_id != connection.region_a:
                    continue
                other = reverse_index.get((connection.region_b, (edge.a, edge.b)))
                if other is None:
                    continue
                if not interval_contains(connection, edge):
                    continue
                candidates.append((edge, other))
            if not candidates:
                report.append({
                    "connection_id": connection.connection_id,
                    "region_a": connection.region_a,
                    "region_b": connection.region_b,
                    "status": "missing",
                    "why": "no reversed coincident atomic segment exists for this intended connection",
                    "atomic_ids": [],
                })
                continue
            for edge, other in candidates:
                if edge.atomic_id in used or other.atomic_id in used:
                    continue
                if not exact_reversed(edge.a, edge.b, other.a, other.b):
                    continue
                used.add(edge.atomic_id)
                used.add(other.atomic_id)
                pairs.append((edge, other))
                width = hypot(edge.b[0] - edge.a[0], edge.b[1] - edge.a[1])
                report.append({
                    "connection_id": connection.connection_id,
                    "region_a": connection.region_a,
                    "region_b": connection.region_b,
                    "role": connection.role,
                    "status": "realized",
                    "atomic_ids": [edge.atomic_id, other.atomic_id],
                    "width": round(width),
                    "wide_enough": width >= connection.min_width,
                })

        allowed_unpaired = set()
        for partition in self.partitions.values():
            if partition.role not in UNPAIRED_PARTITION_ROLES:
                continue
            owners = {partition.region_a, partition.region_b}
            for edge in atomics:
                if edge.region_id not in owners:
                    continue
                if partition.a1 and partition.a2:
                    overlap = collinear_overlap_interval(partition.a1, partition.a2, edge.a, edge.b)
                    if overlap is None:
                        continue
                allowed_unpaired.add(edge.atomic_id)

        special_regions = set()
        for left_id, right_id, _kind in self.special_pairs:
            special_regions.add(left_id)
            special_regions.add(right_id)
        joins = self.declared_joins()
        leftover = []
        for _key, group in by_undirected.items():
            if len(group) < 2:
                continue
            for left in group:
                for right in group:
                    if left.atomic_id >= right.atomic_id:
                        continue
                    if left.region_id in special_regions or right.region_id in special_regions:
                        continue
                    # Two layers may run a wall along the same line without that
                    # line being a portal; they are at different heights.
                    if self.separate_arrangements(left.region_id, right.region_id, joins):
                        continue
                    if not exact_reversed(left.a, left.b, right.a, right.b):
                        if left.a == right.a and left.b == right.b:
                            if left.region_id in special_regions or right.region_id in special_regions:
                                continue
                            raise PlanarLayoutError(
                                f"same-direction coincident atomic segments {left.atomic_id} and {right.atomic_id}"
                            )
                        continue
                    if left.atomic_id in used and right.atomic_id in used:
                        continue
                    if left.atomic_id in allowed_unpaired or right.atomic_id in allowed_unpaired:
                        continue
                    leftover.append(f"{left.atomic_id}↔{right.atomic_id}")
        missing = [item for item in report if item["status"] == "missing"]
        if missing:
            leftover.extend(item["connection_id"] for item in missing)
        return pairs, report, leftover

    def _emit(
        self, atomics: list[AtomicEdge], pairs: list[tuple[AtomicEdge, AtomicEdge]],
    ) -> tuple[LevelIR, dict[str, SectorAllocation], dict[str, int]]:
        ir = new_level(visibility=self.visibility)
        # A sky panorama is only meaningful when something actually shows it.
        bits = self.sky_bits
        if bits is None:
            bits = self.CORPUS_SKY_BITS if any(
                region.parallax_ceiling for region in self.regions.values()
            ) else 0
        ir.sky = {"bits": int(bits), "offsets": list(range(1 << int(bits)))}
        by_region: dict[str, list[AtomicEdge]] = defaultdict(list)
        for edge in atomics:
            by_region[edge.region_id].append(edge)
        allocations: dict[str, SectorAllocation] = {}
        wall_from_atomic: dict[str, int] = {}
        for region in self.regions.values():
            loops = [region.outer, *region.holes]
            region_atomics = by_region[region.region_id]
            by_source: dict[str, list[AtomicEdge]] = defaultdict(list)
            for edge in region_atomics:
                by_source[edge.source_id].append(edge)
            build_loops: list[list[AtomicEdge]] = []
            source_ids: list[str] = []
            for index in range(len(region.outer)):
                source_ids.append(f"{region.region_id}:outer:{index}")
            hole_source_groups: list[list[str]] = []
            for hole_index, hole in enumerate(region.holes):
                group = [f"{region.region_id}:hole:{hole_index}:{index}" for index in range(len(hole))]
                hole_source_groups.append(group)

            def _ordered_loop(source_ids_for_loop: list[str]) -> list[AtomicEdge]:
                ordered: list[AtomicEdge] = []
                for source_id in source_ids_for_loop:
                    pieces = by_source.get(source_id, [])
                    if not pieces:
                        raise PlanarLayoutError(f"missing atomics for {source_id}")
                    pieces.sort(key=lambda edge: int(edge.atomic_id.rsplit(":", 1)[1]))
                    ordered.extend(pieces)
                if not ordered:
                    raise PlanarLayoutError(f"failed to reconstruct loop for {region.region_id}")
                return ordered

            outer_loop = _ordered_loop(source_ids)
            # A slope pivots about `wall[sector->wallptr]`, so the hinge is not a
            # wall the author picks -- it is whichever wall happens to come
            # first. Rotate the loop until the named edge does.
            #
            # The named edge may have been split into several atomics by a
            # connection crossing it. That is harmless: Build reads only the
            # first wall's origin and direction, and a collinear piece starting
            # at the same point describes the same plane.
            if region.ceiling_slope is not None or region.floor_slope is not None:
                outer_loop = _rotate_to_hinge(outer_loop, region)
            build_loops.append(outer_loop)
            for group in hole_source_groups:
                build_loops.append(_ordered_loop(group))
            wall_base = len(ir.walls)
            wall_ids: list[int] = []
            wall_count = sum(len(loop) for loop in build_loops)
            shading = _region_shading(region)
            fields = _empty(SECTOR_FIELDS)
            fields.update(
                wall_ptr=wall_base,
                wall_count=wall_count,
                ceiling_z=int(region.ceiling_z),
                floor_z=int(region.floor_z),
                ceiling_picnum=int(region.ceiling_picnum),
                floor_picnum=int(region.floor_picnum),
                ceiling_shade=int(shading["ceiling_shade"]),
                floor_shade=int(shading["floor_shade"]),
                type=int(region.type),
                extra=-1,
                floor_stat=int(region.floor_stat),
                ceiling_stat=(int(region.ceiling_stat)
                              | (1 if region.parallax_ceiling else 0)),
            )
            if region.relative_alignment is not None:
                if region.relative_alignment not in ("floor", "ceiling", "both"):
                    raise PlanarLayoutError(
                        f"{region.region_id}: relative_alignment must be "
                        f"'floor', 'ceiling' or 'both', not "
                        f"{region.relative_alignment!r}")
                wanted = (("floor", "ceiling") if region.relative_alignment == "both"
                          else (region.relative_alignment,))
                for surface in wanted:
                    key = f"{surface}_stat"
                    fields[key] = int(fields.get(key, 0)) | _RELATIVE_ALIGNMENT

            for surface, spec in (("ceiling", region.ceiling_slope),
                                  ("floor", region.floor_slope)):
                if spec is None:
                    continue
                heinum = (
                    int(spec.heinum) if spec.heinum is not None
                    else _slope.heinum_for_rise(
                        region.outer, spec.hinge, float(spec.rise_z)))
                fields[f"{surface}_heinum"] = heinum
                fields[f"{surface}_stat"] = int(fields.get(f"{surface}_stat", 0)) | 2
                note = _slope.steeper_than_campaign(heinum, surface)
                if note:
                    self.slope_notes.append(f"{region.region_id}: {note}")
            sector_id = len(ir.sectors)
            ir.sectors.append({"id": sector_id, "fields": fields, "blood": None})
            wall_id = wall_base
            for loop in build_loops:
                loop_start = wall_id
                for index, edge in enumerate(loop):
                    next_id = loop_start if index == len(loop) - 1 else wall_id + 1
                    wall = _empty(WALL_FIELDS)
                    nx, ny = edge.b
                    wall.update(
                        x=edge.a[0], y=edge.a[1], point2=next_id,
                        next_wall=-1, next_sector=-1, extra=-1,
                        picnum=int(region.wall_picnum),
                        shade=int(shading["wall_shade"]),
                        x_repeat=max(1, min(255, round(hypot(nx - edge.a[0], ny - edge.a[1]) / 128))),
                        y_repeat=8,
                    )
                    ir.walls.append({"id": wall_id, "fields": wall, "blood": None})
                    wall_from_atomic[edge.atomic_id] = wall_id
                    wall_ids.append(wall_id)
                    wall_id += 1
            allocations[region.region_id] = SectorAllocation(sector_id, tuple(wall_ids))

        owners = {}
        for region_id, alloc in allocations.items():
            for wall_id in alloc.wall_ids:
                owners[wall_id] = alloc.sector_id
        for left, right in pairs:
            wa, wb = wall_from_atomic[left.atomic_id], wall_from_atomic[right.atomic_id]
            a, b = ir.walls[wa]["fields"], ir.walls[wb]["fields"]
            a_end, b_end = ir.walls[int(a["point2"])]["fields"], ir.walls[int(b["point2"])]["fields"]
            if (a["x"], a["y"], a_end["x"], a_end["y"]) != (b_end["x"], b_end["y"], b["x"], b["y"]):
                raise PlanarLayoutError(
                    f"paired atomics {left.atomic_id} and {right.atomic_id} did not emit reversed coincident walls"
                )
            a.update(next_wall=wb, next_sector=owners[wb])
            b.update(next_wall=wa, next_sector=owners[wa])
            cut = self._view_cut_side(left, right)
            if cut is not None:
                near = a if cut == left.region_id else b
                # Bit 5 alone: engine.c:3134 skips `scansector` on it, and
                # engine.c:3157 then draws the wall solid from `over_picnum`.
                # Bit 4 is not consulted on either path -- engine.c:2920 takes a
                # wall into the masked list only when cstat&48 is exactly 16 --
                # so adding it would buy nothing and make this look like a grate.
                # The campaign agrees: of its 82 one-way walls, 95% carry an
                # over_picnum and only 32% also set masked.
                near["cstat"] = int(near["cstat"]) | CSTAT_WALL_ONE_WAY
                if not int(near["over_picnum"]):
                    near["over_picnum"] = int(near["picnum"])
            blocking = self._blocks(left, right)
            if blocking:
                a["cstat"] = int(a["cstat"]) | CSTAT_WALL_BLOCKING
                b["cstat"] = int(b["cstat"]) | CSTAT_WALL_BLOCKING
                if self._blocks_opaquely(left, right):
                    for face in (a, b):
                        face["cstat"] = int(face["cstat"]) | CSTAT_WALL_MASKED | CSTAT_WALL_HITSCAN
                        if not int(face["over_picnum"]):
                            face["over_picnum"] = int(face["picnum"])
        return ir, allocations, wall_from_atomic

    def _view_cut_side(self, left: "AtomicEdge", right: "AtomicEdge") -> str | None:
        """Which of this pair's two regions asked not to be seen through.

        Returns the region id whose own wall carries the flag, or None. The
        answer is a region id rather than a side name because by the time the
        walls exist, "left" and "right" no longer mean anything: only the two
        sectors do.
        """
        for connection in self.connections.values():
            if connection.view_cut_from is None:
                continue
            if {connection.region_a, connection.region_b} != {left.region_id, right.region_id}:
                continue
            if connection.a1 and connection.a2:
                if collinear_overlap_interval(connection.a1, connection.a2,
                                              left.a, left.b) is None:
                    continue
            return self._resolve_cut_side(connection)
        return None

    @staticmethod
    def _resolve_cut_side(connection: ConnectionSpec) -> str:
        named = str(connection.view_cut_from)
        if named in ("left", "a", connection.region_a):
            return connection.region_a
        if named in ("right", "b", connection.region_b):
            return connection.region_b
        raise PlanarLayoutError(
            f"connection {connection.connection_id!r} cuts the view from "
            f"{named!r}, which is neither of its regions "
            f"({connection.region_a!r}, {connection.region_b!r}) nor "
            f"'left'/'right'")

    def _blocks_opaquely(self, left: "AtomicEdge", right: "AtomicEdge") -> bool:
        """Whether the covering blocked_portal asked to be solid to look at."""
        for partition in self.partitions.values():
            if partition.role != "blocked_portal" or not partition.opaque:
                continue
            owners = {partition.region_a, partition.region_b}
            if {left.region_id, right.region_id} != owners:
                continue
            if partition.a1 and partition.a2:
                if collinear_overlap_interval(partition.a1, partition.a2, left.a, left.b) is None:
                    continue
            return True
        return False

    def _blocks(self, left: "AtomicEdge", right: "AtomicEdge") -> bool:
        """Whether a blocked_portal partition covers this paired edge."""
        for partition in self.partitions.values():
            if partition.role != "blocked_portal":
                continue
            owners = {partition.region_a, partition.region_b}
            if {left.region_id, right.region_id} != owners:
                continue
            if partition.a1 and partition.a2:
                if collinear_overlap_interval(partition.a1, partition.a2, left.a, left.b) is None:
                    continue
            return True
        return False


def _edges_of(region: RegionSpec) -> list[Segment]:
    edges: list[Segment] = []
    for loop in (region.outer, *region.holes):
        for index, start in enumerate(loop):
            edges.append((start, loop[(index + 1) % len(loop)]))
    return edges


def _on_source(edge: AtomicEdge, start: Point, end: Point) -> bool:
    return on_segment_inclusive(start, end, edge.a) and on_segment_inclusive(start, end, edge.b)
