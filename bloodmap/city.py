"""The city's vocabulary: the constructors, named where a reader can find them.

A constructor here is one word of the language the project is trying to
speak, and P15's readers of E3M1 have to recognise the same words coming the
other way. So they live in `bloodmap` and not in the project: a project may
choose its numbers, and it may not own its nouns.

    street(...)      the ground plane: one region per connected network
    island(...)      a pavement standing on it, kerb being its exposed edge
    end_wall(...)    where a street reaches the boundary and stops
    waterfront(...)  quay walk, shore, sea, horizon -- DWE3M10's dialect
    shell(...)       a building: facade, opening, insert, room
    facade(...)      the wall of a shell, cut open at its openings
    opening(...)     a void in a facade
    insert(...)      what fills an opening, in a sector of its own

Each returns `pipeline.SurfaceSpec`s and, where it has a mechanism, the
declaration that goes with them. Nothing here compiles, cuts or writes: the
compiler owns the pipeline and a constructor only says what a thing is.

The numbers are the corpus's
============================

* the kerb steps 2048 and its face wears tile 6, on 11 of E3M1's 11 records;
* a step's face is shaded its floor's shade **+6**, median over those same 11;
* the facade family is E3M1's one-sided outdoor records weighted by LENGTH --
  401 at 27.6%, 417 at 21.5%, 181 at 11.6%, 400 at 8.7% -- all at y_repeat 8;
* a roof wears 379;
* the shore stands one walkable step (3072) below the quay, the sea meets it
  at equal z under palette 10 with pan_floor, pan_always and drag, and the
  horizon is a zero-height sector wearing the SAME sky as the space it ends,
  because 271 of 271 campaign outdoor regions wear exactly one.
"""

from __future__ import annotations

from typing import Any, Iterable, Sequence

from . import joins
from .pipeline import SurfaceSpec

Point = tuple[int, int]

#: The ground's own materials, and E3M1's numbers for them.
ROAD_TILE = 352
PAVEMENT_TILE = 4
KERB_TILE = joins.TILE_CLASSES["kerb class"]
ROAD_WALL_TILE = 400
PAVEMENT_WALL_TILE = 401
FACADE_FAMILY = joins.FACADE_FAMILY
ROOF_TILE = joins.ROOF_TILE
#: A pavement stands this far above the road it borders.
KERB_RISE = 2048


def _rect(x0: int, y0: int, x1: int, y1: int) -> list:
    return [(int(x0), int(y0)), (int(x1), int(y0)),
            (int(x1), int(y1)), (int(x0), int(y1))]


def street(surface_id: str, rings: Sequence[Sequence[Point]], *,
           floor_z: int, sky_z: int, sky_tile: int,
           wall_tile: int = ROAD_WALL_TILE,
           floor_tile: int = ROAD_TILE) -> SurfaceSpec:
    """The ground plane: ONE region per connected street network.

    A junction is not a thing to declare -- it is the part of the plane no
    island covers -- and the kerb is not an object either: it is what the join
    road|pavement looks like. The wall material is NOT the kerb tile, because
    a kerb exists only where a road meets a pavement; making it the plane's
    default put a kerb face on every shadow cut and every map edge.
    """
    return SurfaceSpec(
        surface_id=surface_id, rings=tuple(list(ring) for ring in rings),
        floor_z=int(floor_z), ceiling_z=int(sky_z), floor_tile=int(floor_tile),
        ceiling_tile=int(sky_tile), wall_tile=int(wall_tile),
        kind=joins.ROAD)


def island(surface_id: str, rings: Sequence[Sequence[Point]], *,
           floor_z: int, sky_z: int, sky_tile: int,
           wall_tile: int = PAVEMENT_WALL_TILE,
           floor_tile: int = PAVEMENT_TILE) -> SurfaceSpec:
    """A pavement standing on the plane. Its exposed edge IS the kerb."""
    return SurfaceSpec(
        surface_id=surface_id, rings=tuple(list(ring) for ring in rings),
        floor_z=int(floor_z), ceiling_z=int(sky_z), floor_tile=int(floor_tile),
        ceiling_tile=int(sky_tile), wall_tile=int(wall_tile),
        kind=joins.PAVEMENT)


def end_wall(surface_id: str, rect: Sequence[int], *, road_floor_z: int,
             standing_height: int, sky_tile: int,
             facade_tile: int = joins.TILE_CLASSES["facade stone"]
             ) -> SurfaceSpec:
    """Where a street reaches the boundary and stops, in E3M1's dialect.

    The numbers come from `street.end_wall`, which measured s0, s339 and s343:
    3.86 to 5.80 player heights up, 5.80 to 7.73 of sky above that, floor 379,
    and blocking faces in the district's own stone.
    """
    from .street import end_wall as _record

    found = _record(_rect(*rect), road_floor_z=int(road_floor_z),
                    standing_height=int(standing_height),
                    facade_tile=int(facade_tile), sky_tile=int(sky_tile),
                    name=surface_id)
    return SurfaceSpec(
        surface_id=surface_id, rings=(found["outline"],),
        floor_z=found["floor_z"], ceiling_z=found["ceiling_z"],
        floor_tile=found["floor_picnum"],
        ceiling_tile=found["ceiling_picnum"], wall_tile=int(facade_tile),
        kind=joins.END_WALL, lit=False)


def waterfront(prefix: str, *, x0: int, x1: int, y: int, walk_depth: int,
               shore_depth: int, sea_depth: int, horizon_depth: int,
               pavement_z: int, sky_z_of, sky_tile: int) -> list:
    """Quay walk, shore, sea and horizon, in DWE3M10's dialect.

    Four surfaces and three joins. The shore stands one WALKABLE step below
    the walk -- 3072, inside Blood's 4096 autostep, which is DWE3M10's gentle
    case; its other seven landward records step 35840, and that is a quay wall
    rather than a shore. The sea meets the shore at equal z. The horizon is a
    zero-height sector at the sea's own z with the sky on BOTH surfaces and
    the parallax bit on both -- and the sky is the CITY's, because one
    connected outdoor space wears one sky.
    """
    shore_z = int(pavement_z) + joins.SHORE_STEP
    walk = _rect(x0, y - walk_depth, x1, y)
    shore = _rect(x0, y, x1, y + shore_depth)
    sea = _rect(x0, y + shore_depth, x1, y + shore_depth + sea_depth)
    horizon = _rect(x0, y + shore_depth + sea_depth,
                    x1, y + shore_depth + sea_depth + horizon_depth)
    return [
        island(f"{prefix}walk", (walk,), floor_z=int(pavement_z),
               sky_z=sky_z_of(int(pavement_z)), sky_tile=int(sky_tile)),
        SurfaceSpec(surface_id=f"{prefix}shore", rings=(shore,),
                    floor_z=shore_z, ceiling_z=sky_z_of(shore_z),
                    floor_tile=joins.SHORE_TILES[0], ceiling_tile=int(sky_tile),
                    wall_tile=joins.TILE_CLASSES["quay class"],
                    kind=joins.SHORE),
        SurfaceSpec(surface_id=f"{prefix}sea", rings=(sea,), floor_z=shore_z,
                    ceiling_z=sky_z_of(shore_z), floor_tile=joins.SEA_TILE,
                    ceiling_tile=int(sky_tile),
                    wall_tile=joins.TILE_CLASSES["quay class"],
                    kind=joins.SEA,
                    finish={"floor_pal": joins.SEA_PALETTE},
                    behavior={"pan_floor": 1, "pan_always": 1, "drag": 1,
                              "pan_velocity": joins.SEA_PAN_VELOCITY,
                              "pan_angle": joins.SEA_PAN_ANGLE}),
        SurfaceSpec(surface_id=f"{prefix}horizon", rings=(horizon,),
                    floor_z=shore_z, ceiling_z=shore_z,
                    floor_tile=int(sky_tile), ceiling_tile=int(sky_tile),
                    wall_tile=int(sky_tile), kind=joins.HORIZON,
                    floor_stat=1, lit=False, declared_zero_exit=True),
    ]


def facade(surface_id: str, rect: Sequence[int], inner: Sequence[int],
           door: Sequence[int], *, roof_z: int, sky_z: int, sky_tile: int,
           wall_tile: int) -> SurfaceSpec:
    """A shell's wall, as ONE simple polygon cut open at its door.

    Not a rectangle with a hole: the doorway reaches the outside, so the room
    is not enclosed by the wall and a hole would TOUCH the outer ring at the
    mouth. That shape is degenerate, and `PlanarLayout` says so.
    """
    x0, y0, x1, y1 = (int(v) for v in rect)
    ix0, iy0, ix1, iy1 = (int(v) for v in inner)
    dx0, dx1 = int(door[0]), int(door[2])
    ring = [(x0, y0), (x1, y0), (x1, y1), (dx1, y1), (dx1, iy1),
            (ix1, iy1), (ix1, iy0), (ix0, iy0), (ix0, iy1),
            (dx0, iy1), (dx0, y1), (x0, y1)]
    return SurfaceSpec(
        surface_id=surface_id, rings=(ring,), floor_z=int(roof_z),
        ceiling_z=int(sky_z), floor_tile=ROOF_TILE, ceiling_tile=int(sky_tile),
        wall_tile=int(wall_tile), kind=joins.FACADE, lit=False)


def opening(surface_id: str, rect: Sequence[int], *, floor_z: int,
            head_z: int, wall_tile: int, floor_tile: int = PAVEMENT_TILE,
            ceiling_tile: int = ROOF_TILE, sector_type: int = 0,
            lod: int = 2) -> SurfaceSpec:
    """A void in a facade, as a sector of its own.

    P13's law, and the reason this is a sector rather than a wall band: a
    material with its own scale needs a record no other surface uses. The
    facade's run crosses the mouth above it; nothing of the facade's frame
    touches these records.
    """
    return SurfaceSpec(
        surface_id=surface_id, rings=(_rect(*rect),), floor_z=int(floor_z),
        ceiling_z=int(head_z), floor_tile=int(floor_tile),
        ceiling_tile=int(ceiling_tile), wall_tile=int(wall_tile),
        kind=joins.OPENING, role="opening", parallax_ceiling=False,
        lit=False, lod=int(lod), sector_type=int(sector_type))


def room(surface_id: str, rect: Sequence[int], *, floor_z: int,
         ceiling_z: int, wall_tile: int, floor_tile: int = PAVEMENT_TILE,
         ceiling_tile: int = ROOF_TILE, lod: int = 1) -> SurfaceSpec:
    """The space behind a facade. Not ground: the sun does not reach it."""
    return SurfaceSpec(
        surface_id=surface_id, rings=(_rect(*rect),), floor_z=int(floor_z),
        ceiling_z=int(ceiling_z), floor_tile=int(floor_tile),
        ceiling_tile=int(ceiling_tile), wall_tile=int(wall_tile),
        kind=joins.INTERIOR, role="interior", parallax_ceiling=False,
        lit=False, lod=int(lod))


#: A curtain's leaf: `conformance.CURTAIN`'s own numbers. One flagged tip or
#: two carrying opposite flags, and the deformation is only visible on the
#: fabric, so the leaf wears 146 and not the wall it hangs in.
CURTAIN_FABRIC = 146
DRAG_FORWARD = 0x4000
#: MASKED. `engine.cpp:4938-4940` draws a two-sided wall's middle band only
#: when it is masked or one-way; unmasked, the fabric shows on the step bands
#: and nowhere a body walks -- which is what `conformance.measure_curtain`
#: says when it counts 0 visible fabric walls.
MASKED = 16


def insert(surface: str, *, holder: str, room_id: str, void: Sequence,
           kind: str = "curtain", sector_type: int = 0, lod: int = 2,
           wiring: Iterable[dict] = (), key: int | None = None,
           key_realised: bool = False, key_why: str = "",
           leaf: dict | None = None) -> dict:
    """What fills an opening: the declaration, not the geometry.

    Two facts come out of this and they are two different claims. `void` says
    the facade has a hole here and names the holder it belongs to; `fill` says
    what is in it. A link whose tx nobody carries is written with
    `realised: false` rather than being quietly absent.
    """
    return {"kind": str(kind), "surface": str(surface), "holder": str(holder),
            "room": str(room_id), "void": [list(point) for point in void],
            "sector_type": int(sector_type), "lod": int(lod),
            "wiring": [dict(row) for row in wiring],
            "key": key, "key_realised": bool(key_realised),
            "key_why": str(key_why),
            "leaf": dict(leaf) if leaf else None}


def shell(key: str, rect: Sequence[int], *, wall_thickness: int,
          door_width: int, roof_z: int, floor_z: int, interior_z: int,
          head_z: int, sky_z: int, sky_tile: int, wall_tile: int,
          sector_type: int = 0, wiring: Iterable[dict] = (),
          gate_key: int | None = None, key_why: str = "") -> tuple:
    """A building: facade, opening, insert and room, from one rectangle.

    The mouth is on the SOUTH face, which is the one the sun lights and the
    street sees, and which `city_plan.ENVELOPES` faces its venues towards.
    """
    x0, y0, x1, y1 = (int(v) for v in rect)
    inner = (x0 + wall_thickness, y0 + wall_thickness,
             x1 - wall_thickness, y1 - wall_thickness)
    mid = (x0 + x1) // 2
    door = (mid - door_width // 2, inner[3], mid + door_width // 2, y1)
    surfaces = [
        facade(f"shell:{key}", (x0, y0, x1, y1), inner, door, roof_z=roof_z,
               sky_z=sky_z, sky_tile=sky_tile, wall_tile=wall_tile),
        room(f"interior:{key}", inner, floor_z=floor_z, ceiling_z=interior_z,
             wall_tile=wall_tile),
        opening(f"door:{key}", door, floor_z=floor_z, head_z=head_z,
                wall_tile=wall_tile, sector_type=sector_type),
    ]
    #: THE LEAF. A sector type alone is not a curtain: `drag_closure` finds
    #: nothing to drag and `conformance.measure_curtain` says so in two
    #: sentences -- "found 0 leaves" and "fabric: wanted 146". The leaf is the
    #: record at the mouth, flagged and wearing the fabric.
    declaration = insert(f"door:{key}", holder=f"shell:{key}",
                         room_id=f"interior:{key}", void=_rect(*door),
                         sector_type=sector_type, wiring=wiring,
                         key=gate_key, key_why=key_why,
                         leaf={"tile": CURTAIN_FABRIC,
                               "flags": DRAG_FORWARD | MASKED,
                               "over_picnum": CURTAIN_FABRIC,
                               "faces": joins.PAVEMENT})
    return surfaces, declaration
