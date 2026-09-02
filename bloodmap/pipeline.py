"""The compiler owns the pipeline; an emitter only declares.

Every ordering bug this project has had was a pass that simply did not run.
The frame gate caught 191 misaligned walls in slice 2h and the cause was not
a defect in the frames -- it was that the emitter never called `frame_map` at
all. A gate downstream of a missing pass reports the symptom; only the
compiler can report the absence.

So an emitter returns an `Emission` -- surfaces, declarations, light, joins,
frames -- and calls no pass. `compile_city` runs

    planes -> declare -> light -> joins -> frames

itself, through `channels.Compilation`, and refuses an emission that omits
one of the five **naming the pass**. The distinction that makes this work is
between an omission and a declared emptiness: `declarations=[]` says "this
map has no mechanisms", which is a statement, and `declarations=None` says
nothing at all, which is the bug. `None` is refused; the empty list is not.

`Compilation.require_complete` is the same assertion at the end: the order
assertion from slice 2d became a completeness assertion, because running the
passes in the right order is worth nothing if one of them never ran.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from .channels import PASSES, Compilation, OrderError, RegionLedger
from .light_field import build_field
from .lightbomb import apply_shade_channel
from .overlay import CutRegistry, partition_faults

Point = tuple[int, int]

#: Which declaration each pass consumes. A pass whose declaration is `None`
#: never runs, and the compiler says so with the pass's name.
PASS_DECLARATION = {
    "planes": "surfaces",
    "declare": "declarations",
    "light": "light",
    "joins": "joins",
    "frames": "frames",
}
assert tuple(PASS_DECLARATION) == PASSES


class PipelineError(OrderError):
    """An emission the compiler will not run."""


@dataclass(frozen=True)
class SurfaceSpec:
    """One surface an emitter declares. It is geometry and finish, no passes.

    `lit` is whether the sun field may cut it -- a zero-height horizon has no
    interior to cut and says so here rather than being special-cased inside
    the light pass.
    """

    surface_id: str
    rings: tuple
    floor_z: int
    ceiling_z: int
    floor_tile: int
    ceiling_tile: int
    wall_tile: int
    kind: str
    role: str = "street"
    parallax_ceiling: bool = True
    floor_stat: int = 0
    ceiling_stat: int = 0
    lit: bool = True
    #: Fields written straight onto the compiled sector, for what `RegionSpec`
    #: does not carry: `floor_pal` and friends.
    finish: dict = field(default_factory=dict)
    #: XSECTOR fields: `pan_floor`, `pan_always`, `drag`, `pan_velocity` ...
    behavior: dict = field(default_factory=dict)


@dataclass(frozen=True)
class Lamp:
    """A point source on a surface: a delta into the shade channel."""

    lamp_id: str
    point: Point
    delta: int


@dataclass(frozen=True)
class LightSpec:
    """One sun, its masses, the quantisation, and the lamps."""

    masses: tuple = ()
    bearing_units: int = 0
    per_height: float = 1.0
    base_shade: int = 8
    step: int = 12
    lamps: tuple = ()


@dataclass(frozen=True)
class JoinSpec:
    """Run the join table over every shared record."""

    strict: bool = False
    tiles: dict | None = None


@dataclass(frozen=True)
class FrameSpec:
    """Resolve one texture frame per run."""

    art_root: str = "reference/blood"


@dataclass
class Emission:
    """What an emitter says. `None` is an omission; an empty one is a claim."""

    name: str
    surfaces: list | None = None
    declarations: list | None = None
    light: LightSpec | None = None
    joins: JoinSpec | None = None
    frames: FrameSpec | None = None
    #: `(surface_id, angle)`: which surface the body starts on.
    start: tuple | None = None

    def missing(self) -> list[str]:
        """The passes this emission cannot run, in pipeline order."""
        return [name for name, attribute in PASS_DECLARATION.items()
                if getattr(self, attribute) is None]


@dataclass
class Built:
    layout: Any
    compiled: Any
    disk: Any
    pieces: list
    ledger: RegionLedger
    run: Compilation
    report: dict


def compile_city(emission: Emission, *, min_area: int | None = None) -> Built:
    """Run the five passes in order, and refuse an emission that omits one.

    The refusal comes FIRST, before any pass runs, so an emitter that forgot
    its frames is told about its frames and not about 191 walls.
    """
    from .planar_layout import PlanarLayout

    missing = emission.missing()
    if missing:
        raise PipelineError(
            f"{emission.name}: the emission declares no {missing[0]!r}, so "
            f"the {missing[0]!r} pass cannot run. The order is "
            f"{' -> '.join(PASSES)} and all five are compulsory; declare an "
            f"empty one to say a map has none, because 'no mechanisms' is a "
            f"statement and silence is a missing pass")

    run = Compilation()
    layout = PlanarLayout(name=emission.name)
    ledger = RegionLedger()
    report: dict[str, Any] = {"name": emission.name}
    pieces: list = []

    # --- 1. planes --------------------------------------------------------
    run.enter("planes")
    surfaces = list(emission.surfaces)
    if not surfaces:
        raise PipelineError(f"{emission.name}: no surfaces to build")
    report["surfaces"] = len(surfaces)

    # --- 2. declare -------------------------------------------------------
    run.enter("declare")
    report["declarations"] = len(emission.declarations)

    # --- 3. light ---------------------------------------------------------
    run.enter("light")
    light = emission.light
    report["welded_vertices"] = 0
    report["slivers_absorbed"] = 0
    faults: list = []
    for spec in surfaces:
        rings = [list(ring) for ring in spec.rings]
        if spec.lit and light.masses:
            registry = CutRegistry()
            field_out = build_field(
                rings, light.masses, bearing_units=light.bearing_units,
                per_height=light.per_height, registry=registry,
                **({} if min_area is None else {"min_area": min_area}))
            report["welded_vertices"] += field_out["welded_vertices"]
            report["slivers_absorbed"] += len(field_out["absorbed"])
            grown = field_out["pieces"]
            #: POST-CONDITION per surface: the pieces partition what was cut.
            faults.extend(f"{spec.surface_id}: {row}"
                          for row in partition_faults(
                              [p.rings for p in grown], rings))
        else:
            from .light_field import Piece

            grown = [Piece(rings=rings, depth=0)]
        for index, piece in enumerate(grown):
            name = (spec.surface_id if len(grown) == 1
                    else f"{spec.surface_id}#{index}")
            layout.add_region(
                name, piece.rings[0], holes=piece.rings[1:],
                floor_z=spec.floor_z, ceiling_z=spec.ceiling_z,
                floor_picnum=spec.floor_tile,
                ceiling_picnum=spec.ceiling_tile,
                wall_picnum=spec.wall_tile, floor_shade=light.base_shade,
                floor_stat=spec.floor_stat, ceiling_stat=spec.ceiling_stat,
                parallax_ceiling=spec.parallax_ceiling, role=spec.role,
                sector_behavior=dict(spec.behavior))
            pieces.append((name, piece, spec))
    report["partition_faults"] = faults
    report["pieces"] = len(pieces)
    report["levels"] = sorted({p.depth for _n, p, _s in pieces})

    paired = 0
    for index, (a_name, a_piece, _a) in enumerate(pieces):
        for b_name, b_piece, _b in pieces[index + 1:]:
            for number, edge in enumerate(shared_segments(a_piece.rings,
                                                          b_piece.rings)):
                layout.add_connection(
                    f"join:{a_name}:{b_name}:{number}", a_name, b_name,
                    role="portal", a1=edge[0], a2=edge[1])
                paired += 1
    report["portals_paired"] = paired

    if emission.start is not None:
        start_id, angle = emission.start
        name = next(n for n, _p, spec in pieces if spec.surface_id == start_id)
        spot = _centroid(layout.regions[name].outer)
        floor = next(spec.floor_z for n, _p, spec in pieces if n == name)
        layout.set_player_start(name, x=int(spot[0]), y=int(spot[1]),
                                z=int(floor), angle=int(angle))

    compiled = layout.compile()
    disk = compiled.level.to_disk_map()
    for name, _piece, spec in pieces:
        sector = compiled.allocations[name].sector_id
        for key, value in spec.finish.items():
            disk.sectors[sector].fields[key] = value
    report["sectors"] = len(disk.sectors)
    report["walls"] = len(disk.walls)

    #: The field's contribution, and the lamps', both as deltas -- LightBomb
    #: is the single summing owner of `floor_shade`.
    for name, piece, _spec in pieces:
        if piece.depth:
            sector = compiled.allocations[name].sector_id
            ledger.write(str(sector), "shade", "sun:field",
                         piece.depth * light.step, intent="presentation")
    lit_lamps = []
    for lamp in light.lamps:
        name = _piece_at(pieces, lamp.point)
        if name is None:
            report.setdefault("lamps_off_surface", []).append(lamp.lamp_id)
            continue
        sector = compiled.allocations[name].sector_id
        ledger.write(str(sector), "shade", f"lamp:{lamp.lamp_id}", lamp.delta,
                     intent="presentation")
        lit_lamps.append({"lamp": lamp.lamp_id, "sector": sector,
                          "region": name, "delta": lamp.delta})
    report["lamps"] = lit_lamps
    report["shade"] = apply_shade_channel(disk, ledger)

    # --- 4. joins ---------------------------------------------------------
    run.enter("joins")
    from . import joins as join_table

    kinds = {compiled.allocations[name].sector_id: spec.kind
             for name, _piece, spec in pieces}
    applied = join_table.apply(disk, kinds, tiles=emission.joins.tiles,
                               strict=emission.joins.strict)
    report["joins"] = {k: v for k, v in applied.items() if k != "applied"}
    report["join_rows"] = applied["applied"]

    # --- 5. frames --------------------------------------------------------
    run.enter("frames")
    from .texture_align import wall_art_sizes
    from .texture_frame import frame_map

    art = wall_art_sizes(emission.frames.art_root)
    report["art"] = bool(art)
    if art:
        report["frames"] = {k: v for k, v
                            in frame_map(disk, art_sizes=art).items()
                            if k != "basis"}

    run.require_complete()
    return Built(layout=layout, compiled=compiled, disk=disk, pieces=pieces,
                 ledger=ledger, run=run, report=report)


def shared_segments(a_rings, b_rings) -> list:
    """EVERY segment two pieces share, not the first.

    After the weld two pieces routinely share several -- a chord a later cut
    split, an island edge broken by a shadow crossing -- and declaring one
    leaves the rest as coincident walls nobody paired.
    """
    out = []
    for a in a_rings:
        for index, point in enumerate(a):
            nxt = a[(index + 1) % len(a)]
            for b in b_rings:
                for other, start in enumerate(b):
                    end = b[(other + 1) % len(b)]
                    if {tuple(point), tuple(nxt)} == {tuple(start),
                                                      tuple(end)}:
                        out.append((tuple(point), tuple(nxt)))
    return out


def _centroid(ring) -> Point:
    return (sum(p[0] for p in ring) // len(ring),
            sum(p[1] for p in ring) // len(ring))


def _piece_at(pieces, point):
    from .overlay import _point_in

    for name, piece, _spec in pieces:
        if _point_in(piece.rings, tuple(point)):
            return name
    return None
