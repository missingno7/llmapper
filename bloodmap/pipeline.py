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
from .facts import LEVELS, FactStore, compare_below
from .light_field import build_field
from .lightbomb import apply_shade_channel
from .overlay import CutRegistry, partition_faults, seed_coincident_vertices

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
    #: Level of detail. A surface solved by the envelope program is plan (0);
    #: the ground and the shells it carries are massing (1).
    lod: int = LEVELS["massing"]
    #: A backdrop is not a place. A zero-height horizon has no way in on
    #: purpose, and saying so is a claim the geometry audit accepts; leaving
    #: it unsaid is the `zero_exit_gameplay_sector` refusal.
    declared_zero_exit: bool = False
    #: Fields written straight onto the compiled sector, for what `RegionSpec`
    #: does not carry: `floor_pal` and friends.
    finish: dict = field(default_factory=dict)
    #: XSECTOR fields: `pan_floor`, `pan_always`, `drag`, `pan_velocity` ...
    behavior: dict = field(default_factory=dict)
    #: A Blood sector type. A region carrying one in 600..619 is a MECHANISM
    #: to `overlay.Domain` and is excluded from every overlay.
    sector_type: int = 0


@dataclass(frozen=True)
class Lamp:
    """A point source on a surface: a sprite, and a delta into the channel.

    Both halves, because they are two different claims. The sprite is what a
    body sees -- E3M1's street lights are tile 2519/2521 drawn at shade -128
    -- and the delta is what the sector reads. E3M1 makes only the first
    claim, so a level that makes the second is deciding something, and the
    channel is where a decision like that belongs.
    """

    lamp_id: str
    point: Point
    delta: int
    tile: int = 0
    sprite_shade: int = -128
    sprite_type: int = 0
    #: How far the lamp hangs above its floor. Blood's median for tile 641 is
    #: 58368, which is 3.44 player heights.
    height: int = 0
    cstat: int = 128
    clipdist: int = 32
    #: "wall" snaps the sprite onto the nearest wall record of the piece it
    #: lands on and aligns it to that wall. A light under an open sky has
    #: nothing overhead to hang from, so out there it mounts or it stands.
    mount: str = "free"


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
    #: The emitter's own facts -- the plan, at level 0. The compiler adds the
    #: rest as it runs, so the store beside the map is the whole declaration
    #: and not just the part a Build sector can hold.
    facts: FactStore | None = None

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
    store: FactStore


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
    store = emission.facts if emission.facts is not None else FactStore()
    report: dict[str, Any] = {"name": emission.name}
    pieces: list = []

    # --- 1. planes --------------------------------------------------------
    run.enter("planes")
    surfaces = list(emission.surfaces)
    if not surfaces:
        raise PipelineError(f"{emission.name}: no surfaces to build")
    report["surfaces"] = len(surfaces)
    for spec in surfaces:
        store.add("surface", ("surface", spec.surface_id), lod=spec.lod,
                  source=f"emitter:{emission.name}", kind=spec.kind,
                  floor_z=spec.floor_z, ceiling_z=spec.ceiling_z,
                  floor_tile=spec.floor_tile, wall_tile=spec.wall_tile,
                  ceiling_tile=spec.ceiling_tile, role=spec.role,
                  lit=spec.lit, rings=[list(map(list, ring))
                                       for ring in spec.rings])

    # --- 2. declare -------------------------------------------------------
    run.enter("declare")
    report["declarations"] = len(emission.declarations)
    #: AN OPENING VOIDS ITS HOLDER AND AN INSERT FILLS THE OPENING. Two facts,
    #: not one, because they are two different claims about two different
    #: records: the void is a hole in the facade and belongs to the facade;
    #: the fill is a sector of its own with its own frame.
    for row in emission.declarations:
        lod = int(row.get("lod", LEVELS["facades"]))
        if row.get("holder") and row.get("void"):
            store.add("void", ("void", row["surface"]), lod=lod,
                      source=f"declaration:{row.get('kind', 'opening')}",
                      holder=row["holder"], outline=row["void"])
        store.add("fill", ("fill", row["surface"]), lod=lod,
                  source=f"declaration:{row.get('kind', 'insert')}",
                  kind=row.get("kind", "insert"),
                  opening=row["surface"], room=row.get("room"),
                  sector_type=int(row.get("sector_type", 0)))

    # --- 3. light ---------------------------------------------------------
    run.enter("light")
    light = emission.light
    report["welded_vertices"] = 0
    report["slivers_absorbed"] = 0
    faults: list = []
    whole: dict = {}
    #: ONE REGISTRY FOR THE WHOLE CITY, seeded before any field runs. Two
    #: surfaces that share an edge are the same edge seen from two sides, and
    #: a plaza let into a street puts a corner in the middle of the street's
    #: edge that no cut ever made. Both are crossings to the weld, and it does
    #: not care which kind they were.
    registry = CutRegistry()
    report["seeded_vertices"] = seed_coincident_vertices(
        registry, [[list(ring) for ring in spec.rings] for spec in surfaces])
    for spec in surfaces:
        rings = [list(ring) for ring in spec.rings]
        if spec.lit and light.masses:
            field_out = build_field(
                rings, light.masses, bearing_units=light.bearing_units,
                per_height=light.per_height, registry=registry,
                weld_now=False,
                **({} if min_area is None else {"min_area": min_area}))
            report["slivers_absorbed"] += len(field_out["absorbed"])
            grown = field_out["pieces"]
        else:
            from .light_field import Piece

            grown = [Piece(rings=rings, depth=0)]
        for index, piece in enumerate(grown):
            name = (spec.surface_id if len(grown) == 1
                    else f"{spec.surface_id}#{index}")
            pieces.append((name, piece, spec))
            whole.setdefault(spec.surface_id, rings)

    #: THE WELD, once, over every piece of every surface. A crossing recorded
    #: while cutting the last surface belongs to the first one's edge too.
    from .overlay import declared_vertices, weld

    welded, added = weld(
        [piece.rings for _n, piece, _s in pieces], registry,
        declared=declared_vertices([[list(r) for r in spec.rings]
                                    for spec in surfaces]))
    #: THE THIRD POPULATION, and it is the closure of the other two. A cut
    #: that lands collinear with an edge is merged into it, and the merged
    #: edge has no parent -- so a crossing recorded against either half
    #: reaches neither. Every vertex any piece carries is an exact integer
    #: point, so exact collinearity is the right question for all of them at
    #: once: insert each into every edge it lies exactly on. Build needs a
    #: vertex wherever two sectors meet, and these are exactly those.
    everywhere = {tuple(point) for rings in welded for ring in rings
                  for point in ring}
    welded, again = weld(welded, CutRegistry(), declared=everywhere)
    for (_name, piece, _spec), rings_out in zip(pieces, welded):
        piece.rings = rings_out
    report["welded_vertices"] = added + again

    #: POST-CONDITION per surface, AFTER the weld. Before it, every surface
    #: fails: two pieces that ought to share an edge diverge by the fraction
    #: of a unit their crossings rounded by, and the assertion reads that as
    #: an overlap -- correctly. Asking before the weld would be asking a
    #: question whose answer is known.
    by_surface: dict = {}
    for _name, piece, spec in pieces:
        by_surface.setdefault(spec.surface_id, []).append(piece.rings)
    for surface_id, cut in sorted(by_surface.items()):
        faults.extend(f"{surface_id}: {row}"
                      for row in partition_faults(cut, whole[surface_id]))
    report["partition_faults"] = faults

    for name, piece, spec in pieces:
        store.add("part_of", ("piece", name), lod=spec.lod,
                  source=f"surface:{spec.surface_id}",
                  parent=spec.surface_id, depth=piece.depth,
                  rings=[list(map(list, ring)) for ring in piece.rings])
        layout.add_region(
            name, piece.rings[0], holes=piece.rings[1:],
            floor_z=spec.floor_z, ceiling_z=spec.ceiling_z,
            floor_picnum=spec.floor_tile,
            ceiling_picnum=spec.ceiling_tile,
            wall_picnum=spec.wall_tile, floor_shade=light.base_shade,
            floor_stat=spec.floor_stat, ceiling_stat=spec.ceiling_stat,
            parallax_ceiling=spec.parallax_ceiling, role=spec.role,
            declared_zero_exit=spec.declared_zero_exit,
            type=spec.sector_type,
            sector_behavior=dict(spec.behavior))
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
        name, piece, spec = next((n, p, s) for n, p, s in pieces
                                 if s.surface_id == start_id)
        #: A REPRESENTATIVE INTERIOR POINT, not a centroid. The ground plane
        #: is concave -- it is a street lattice -- so its centroid sits in a
        #: block, and the compiler refuses a start that is not strictly inside
        #: its sector. With the field on, the plane is cut into pieces small
        #: enough that the centroid happens to land inside one; with the sun
        #: off it is one piece and the centroid is in a building.
        spot = _inside_point(piece.rings)
        layout.set_player_start(name, x=int(spot[0]), y=int(spot[1]),
                                z=int(spec.floor_z), angle=int(angle))

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
        depth = next(p.depth for n, p, _s in pieces if n == name)
        lit_lamps.append({"lamp": lamp.lamp_id, "sector": sector,
                          "region": name, "delta": lamp.delta,
                          "depth": depth})
        if lamp.tile:
            floor = next(spec.floor_z for n, _p, spec in pieces if n == name)
            _place_lamp(disk, sector, lamp, floor)
    report["lamps"] = lit_lamps
    report["shade"] = apply_shade_channel(disk, ledger)
    for name, piece, spec in pieces:
        sector = compiled.allocations[name].sector_id
        #: THE DEPTH k, which no Build sector holds: the map records the sum
        #: and the store records what it was made of.
        store.add("shade_depth", ("sector", sector), lod=spec.lod,
                  source=f"piece:{name}", depth=piece.depth,
                  base=light.base_shade, step=light.step,
                  sources=list(piece.sources),
                  shade=int(disk.sectors[sector].fields["floor_shade"]))
    for row in lit_lamps:
        store.add("lamp_delta", ("lamp", row["lamp"]),
                  lod=LEVELS["dressing"], source=f"piece:{row['region']}",
                  sector=row["sector"], delta=row["delta"], depth=row["depth"])
    for write in ledger.writes:
        store.add("claims", ("claim", write.region, write.channel,
                             write.owner), lod=LEVELS["massing"],
                  source=write.owner, region=write.region,
                  channel=write.channel, value=write.value,
                  intent=write.intent)

    # --- 4. joins ---------------------------------------------------------
    run.enter("joins")
    from . import joins as join_table

    kinds = {compiled.allocations[name].sector_id: spec.kind
             for name, _piece, spec in pieces}
    applied = join_table.apply(disk, kinds, tiles=emission.joins.tiles,
                               strict=emission.joins.strict)
    report["joins"] = {k: v for k, v in applied.items() if k != "applied"}
    report["join_rows"] = applied["applied"]
    for row in applied["applied"]:
        store.add("join", ("wall", row["wall"]), lod=LEVELS["massing"],
                  source="joins.apply", a=row["a"], b=row["b"],
                  height=row["height"], shows=row["shows"],
                  frame=row["frame"],
                  picnum=int(disk.walls[row["wall"]].fields["picnum"]),
                  shade=int(disk.walls[row["wall"]].fields["shade"]))

    # --- 5. frames --------------------------------------------------------
    #: THE LEVEL-OF-DETAIL GATE, live. The frames pass is level 2, so every
    #: fact of level 0 and 1 -- the plan and the massing -- must come out of
    #: it byte-identical. A facade pass that moves an envelope by one unit
    #: still compiles and still passes every geometry gate; the only evidence
    #: is a level-0 line that moved.
    below = store.lines_below(LEVELS["facades"])
    run.enter("frames")
    from .texture_align import wall_art_sizes
    from .texture_frame import frame_map

    art = wall_art_sizes(emission.frames.art_root)
    report["art"] = bool(art)
    #: THE JOIN TABLE'S ANSWER, USED. A row whose frame is "boundary" says a
    #: run may not cross that record, and that is the reason joins run before
    #: frames. Until it was passed in, a run walked out of a street into a
    #: building's room and the editor disagreed with the closed form on 84
    #: walls, every one of them on the y term, because the two sides of such a
    #: record peg to different floors.
    boundaries = {row["wall"] for row in applied["applied"]
                  if row["frame"] == "boundary"}
    report["frame_boundary_walls"] = sorted(boundaries)
    if art:
        report["frames"] = {k: v for k, v
                            in frame_map(disk, art_sizes=art,
                                         boundaries=boundaries).items()
                            if k != "basis"}

        from .texture_frame import run_partition, sector_index

        owners = sector_index(disk)
        for number, chain in enumerate(run_partition(disk, art_sizes=art,
                                                     owners=owners,
                                                     boundaries=boundaries)):
            store.add("frame", ("run", number), lod=LEVELS["facades"],
                      source="texture_frame.frame_map", walls=list(chain),
                      tile=int(disk.walls[chain[0]].fields["picnum"]),
                      x_repeat=[int(disk.walls[w].fields["x_repeat"])
                                for w in chain],
                      x_panning=[int(disk.walls[w].fields["x_panning"])
                                 for w in chain])

    report["lod_faults"] = compare_below(below,
                                        store.lines_below(LEVELS["facades"]),
                                        LEVELS["facades"])
    run.require_complete()
    report["facts"] = store.count()
    report["facts_by_level"] = store.by_level()
    return Built(layout=layout, compiled=compiled, disk=disk, pieces=pieces,
                 ledger=ledger, run=run, report=report, store=store)


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


def _inside_point(rings) -> Point:
    """Some point strictly inside these rings, found rather than assumed."""
    from .overlay import _point_in

    ring = rings[0]
    spot = (sum(p[0] for p in ring) // len(ring),
            sum(p[1] for p in ring) // len(ring))
    if _point_in(rings, spot):
        return spot
    xs = sorted({p[0] for ring in rings for p in ring})
    ys = sorted({p[1] for ring in rings for p in ring})
    for index in range(len(xs) - 1):
        for row in range(len(ys) - 1):
            candidate = ((xs[index] + xs[index + 1]) // 2,
                         (ys[row] + ys[row + 1]) // 2)
            if _point_in(rings, candidate):
                return candidate
    raise PipelineError("no point of the start surface is inside it")


def _centroid(ring) -> Point:
    return (sum(p[0] for p in ring) // len(ring),
            sum(p[1] for p in ring) // len(ring))


def _piece_at(pieces, point):
    from .overlay import _point_in

    for name, piece, _spec in pieces:
        if _point_in(piece.rings, tuple(point)):
            return name
    return None


def _place_lamp(disk: Any, sector: int, lamp: Lamp, floor_z: int) -> None:
    """Put the lamp's sprite in the map, on the sector the delta went to.

    Straight onto the disk map rather than through `PlanarLayout`, because
    the piece the lamp lands on is not known until the field has cut the
    surface -- the region a placement would have named does not exist when
    the emitter speaks.
    """
    from .format import SPRITE_FIELDS
    from .model import DiskObject

    x, y, angle = int(lamp.point[0]), int(lamp.point[1]), 0
    if lamp.mount == "wall":
        x, y, angle = _against_a_wall(disk, sector, (x, y))
    fields = {name: 0 for name, _code in SPRITE_FIELDS}
    fields.update({
        "x": x, "y": y, "angle": angle,
        "z": int(floor_z) - int(lamp.height),
        "sector": int(sector), "picnum": int(lamp.tile),
        "shade": int(lamp.sprite_shade), "type": int(lamp.sprite_type),
        "initial_type": int(lamp.sprite_type), "cstat": int(lamp.cstat),
        "clipdist": int(lamp.clipdist), "x_repeat": 64, "y_repeat": 64,
        "owner": -1, "index": len(disk.sprites), "extra": -1,
    })
    disk.sprites.append(DiskObject(fields=fields))


def _against_a_wall(disk: Any, sector: int, point) -> tuple:
    """The nearest point ON a wall of this sector, and the way it faces.

    A wall-aligned sprite that is not on a wall is the same mistake as a
    lantern under the sky, one step along, so the mount puts it there rather
    than trusting the caller to have.
    """
    import math

    fields = disk.sectors[sector].fields
    start = int(fields["wall_ptr"])
    best = None
    for wall_id in range(start, start + int(fields["wall_count"])):
        here = disk.walls[wall_id].fields
        nxt = disk.walls[int(here["point2"])].fields
        ax, ay = int(here["x"]), int(here["y"])
        dx, dy = int(nxt["x"]) - ax, int(nxt["y"]) - ay
        span = dx * dx + dy * dy
        if not span:
            continue
        share = max(0.0, min(1.0, ((point[0] - ax) * dx
                                   + (point[1] - ay) * dy) / span))
        near = (ax + dx * share, ay + dy * share)
        distance = math.hypot(point[0] - near[0], point[1] - near[1])
        if best is None or distance < best[0]:
            #: Build's angle is 2048 to the turn, and a wall sprite faces the
            #: wall's normal: the wall runs (dx, dy), so its inward normal is
            #: (dy, -dx).
            facing = int(round(math.atan2(-dx, dy) * 2048 / (2 * math.pi)))
            best = (distance, (int(round(near[0])), int(round(near[1]))),
                    facing % 2048)
    if best is None:
        return int(point[0]), int(point[1]), 0
    return best[1][0], best[1][1], best[2]
