"""Templates that instantiate templates: the composition chain.

`fixtures.py` gave the city parametric *parts* -- a counter family, a
pedestal family, a panel family, each pinning its rise and tile and varying
only its length.  What it did not give was anything that composes them.
The `l3_*` modules called `fixtures` directly, so there was exactly one
level of parameterisation and no template made of templates: the six
arcade units were literal rectangles at absolute coordinates in a fixed
3x2 grid, and the pawn shop was two `place` calls written out by hand.

Here a template takes **the space it is handed and its parameters**, and
returns **a node whose children are the templates it placed**:

    retail_row  -> shop        -> shelf_run -> pedestal fixtures -> goods
                                  counter_run -> counter fixtures
                   clothier   -> wall racks, sales counter, garment stands
                   stockroom  -> crate run
    bar         -> counter_run -> counter fixtures
                   back_bar    -> panel fixtures
                   tables      -> table fixtures

Every rhythm here is measured, not chosen:

* **A retail unit's long side is 2,560 units.**  E4M9's own median across
  the 51 units that open onto its concourse (q1 1,280, q3 3,072).
* **A unit opens on 1,536 units of frontage.**  E4M9's median opening onto
  the concourse across 85 shared walls (q1 652, q3 2,048).  Gravesend's
  hand-built arcade used 1,024 -- inside the range, but not its centre.
* **One fixture in seven carries goods** (`fixtures.GOODS_SHARE`), because
  the median fixture in all four detail sources carries none.

Determinism is the same contract as `runs.py` and `fixtures.py`: every
choice is seeded from the template's own name, so two shops differ and the
same shop rebuilds byte-identically.
"""

from __future__ import annotations

from dataclasses import dataclass

import fixtures
import setpieces
from bloodmap.slope import SlopeSpec

PLAYER = 16960

# E6M1 sectors 33/34 are the canonical small register top: floor tile 2476,
# stat 122 (flip/repeat variant plus relative alignment), and heinum -1792.
# Keep this signature together so a checkout cannot silently regress to a
# flat, full-size floor patch.
E6_REGISTER_FLOOR_STAT = 122
E6_REGISTER_FLOOR_HEINUM = -1792

@dataclass(frozen=True)
class TextureModule:
    """One render-complete prefab cell, not an estimate in player units.

    Build's floor texture grid has two measured scales: 16 map units per
    texel normally, or 8 with floor-stat bit 8 ("double smoosh").  The two
    crate images are 128 square texels, so their module sizes are derived
    from the art grid and the engine's 16:1 vertical scale.  A wall's default
    repeat comes from its length; ``repeat_scale`` corrects it where the
    prefab deliberately uses the finer eight-unit grid.
    """

    tile: int
    side: int
    rise: int
    floor_stat: int
    repeat_scale: int


# Crates are deliberately not shelf tops.  The modules below show one whole
# art tile on the top and on a vertical face.  They are source-art units:
# 452 is the smaller crate at 64 texels, 95 the large one at 128; both sit on
# the normal sixteen-units-per-texel floor grid, so 452 gives a 1024-square
# module and 95 a 2048-square one.  Their z rises preserve a physical cuboid
# after Build's 16:1 xy:z conversion.
#
# 452 is not interchangeable with 459.  Tile 459 is moss-grown rock
# (knowledge/blood/design/owner-anchors-v1.json), and it stood here as
# SMALL_CRATE until 2026-08-31 because it is 128x128 like the real large
# crate and reads as boxy in a thumbnail.  A market hall of rock faces was
# the result.  Do not confuse this with sprite *type* 459, kTrapExploder --
# a different namespace, and l3_foundry's attested E3M1 use of it is correct.
SMALL_CRATE = TextureModule(452, 1024, 16384, 0, 1)
LARGE_CRATE = TextureModule(95, 2048, 32768, 0, 1)


def _e6_register_slope(rect):
    x0, y0, x1, _y1 = (int(v) for v in rect)
    return SlopeSpec(hinge=((x0, y0), (x1, y0)),
                     heinum=E6_REGISTER_FLOOR_HEINUM)


def _crate_block(parent, name, host, rect, material, *, grade, host_clear,
                 module: TextureModule, rise: int, connector=None,
                 note="crate block"):
    """One complete texture-grid cuboid, with the same skin on top and rim."""
    if rise % module.rise:
        raise TemplateError(f"{name}: rise {rise} is not whole {module.tile} modules")
    crate = setpieces.raised_solid(
        parent, name, host, rect, material, grade=grade, rise=rise,
        host_clear=host_clear, connector=connector, face_picnum=module.tile,
        face_x_repeat_scale=module.repeat_scale,
        face_y_repeat_scale=module.repeat_scale,
        note=note)
    crate.surfaces(wall_picnum=module.tile, floor_picnum=module.tile,
                   floor_stat=module.floor_stat,
                   floor_z=grade - rise, clear_height=host_clear - rise)
    crate.region_kwargs["portal_wall_picnum"] = module.tile
    return crate

#: E4M9's median retail unit long side, and the depth that goes with it.
UNIT_LONG = 2560
UNIT_DEEP = 2048
#: The gap between two units: one neck depth, which is what the band
#: between a unit range and the concourse already is.
UNIT_GAP = 512
#: E4M9's median opening from a unit onto the concourse.
OPENING = 1536

#: A table in a bar: the mined low-tier rise, and a square you can walk round.
TABLE_RISE = int(0.30 * PLAYER)
TABLE_SIDE = 1024

#: The gap kept between a shelf run and the counter in front of it.
STAND_CLEAR = 512
#: How far a fixture stands off its room's own walls.  Not a style choice:
#: a carve whose edge lies exactly on the room outline produces two
#: coincident same-direction segments, which the planar compiler refuses --
#: correctly, since neither side can be a portal to the other.
WALL_STANDOFF = 256


class TemplateError(ValueError):
    """A template that cannot be built at the size it was handed."""


# ---------------------------------------------------------------------------
# the plan level: a row of shops derived from the frontage it is given
# ---------------------------------------------------------------------------

#: The solid pier between a unit's window and its opening, and at each end
#: of its frontage.  Without it the display box and the neck share an edge
#: that is a portal on neither side, which the compiler refuses.
PIER = 256


@dataclass(frozen=True)
class Unit:
    """One storefront: where it stands, where it opens, where it glazes."""
    index: int
    rect: tuple                 # x0, y0, x1, y1
    opening: tuple              # (start, end) along the frontage axis
    side: str
    window: tuple | None = None


def retail_row(*, start: int, end: int, band: int, side: str,
               depth: int = UNIT_DEEP, long_side: int = UNIT_LONG,
               gap: int = UNIT_GAP, opening: int = OPENING,
               glaze: tuple = (), axis: str = "x") -> list[Unit]:
    """As many shops as this frontage holds, at E4M9's rhythm.

    `band` is the coordinate of the frontage line the units stand behind;
    they extend `depth` away from it on `side`.  The count comes from the
    length, not from a hand-drawn grid -- which is the whole difference
    between a row that responds to its site and six rectangles.

    A frontage too short for one unit is an error rather than a silent
    empty row: a retail row with no shops in it is a corridor.
    """
    span = end - start
    if span < long_side:
        raise TemplateError(
            f"{span} units of frontage will not hold one {long_side}-unit "
            f"shop; the row needs {long_side - span} more")
    count = (span + gap) // (long_side + gap)
    used = count * long_side + (count - 1) * gap
    origin = start + (span - used) // 2
    out = []
    for index in range(count):
        a0 = origin + index * (long_side + gap)
        a1 = a0 + long_side
        mid = (a0 + a1) // 2
        window = None
        if index in glaze:
            # A glazed unit trades frontage for glass: window, pier, mouth.
            # It cannot keep E4M9's full median opening AND a display box on
            # the same 2,560 units, and a box narrower than a body reads as
            # a slot rather than a window.
            share = (long_side - 3 * PIER) // 2
            if share < 512:
                raise TemplateError(
                    f"unit {index}: {long_side} units of frontage cannot carry "
                    "both a display window and an opening")
            window = (a0 + PIER, a0 + PIER + share)
            mouth = (a1 - PIER - share, a1 - PIER)
        else:
            mouth = (mid - opening // 2, mid + opening // 2)
        if axis == "x":
            rect = ((a0, band - depth, a1, band) if side == "north"
                    else (a0, band, a1, band + depth))
        else:
            rect = ((band - depth, a0, band, a1) if side == "west"
                    else (band, a0, band + depth, a1))
        out.append(Unit(index, rect, mouth, side, window))
    return out


def row_cost(units: list[Unit]) -> dict:
    """What a row will cost before anything is emitted."""
    return {"units": len(units),
            "sectors": len(units) * 2,          # the unit and its neck
            "walls": len(units) * 12}


# ---------------------------------------------------------------------------
# the object level: templates that place templates
# ---------------------------------------------------------------------------

def _inset_rect(host_rect, margin: int):
    x0, y0, x1, y1 = (int(v) for v in host_rect)
    return (x0 + margin, y0 + margin, x1 - margin, y1 - margin)


def shop(space, *, material, grade: int, host_clear: int, name: str = "fittings",
         margin: int = 512, connector=None):
    """Furnish a retail unit: a shelf run down one side, a counter at the front.

    The unit is handed in; everything else is derived from its own rect, so
    the same call furnishes a 2,560-unit arcade unit and a 3,584-unit pawn
    shop without either stating a coordinate.

    `margin` insets the runs ALONG the frontage only.  Across it they stand
    against the walls, because that is where a shelf and a counter go, and
    because insetting both ends of a 2,048-deep unit leaves 1,280 units to
    fit 1,536 of fixture into -- which is how the first version of this
    put a counter through a shelf.

    A unit too shallow for both gets the shelves and no counter, rather
    than a counter overlapping the shelves.  `STAND_CLEAR` is the gap kept
    between them: half a player width, enough to stand behind the counter.
    """
    import citytree
    import props

    x0, y0, x1, y1 = (int(v) for v in props.room_rect(space))
    node = citytree.sub(space, name, note="shop fittings (templates.shop)")
    along_x = (x1 - x0) >= (y1 - y0)
    margin = max(margin, WALL_STANDOFF)
    a0, a1 = (x0 + margin, x1 - margin) if along_x else (y0 + margin, y1 - margin)
    across = (y1 - y0) if along_x else (x1 - x0)
    if a1 - a0 < min(fixtures.PEDESTAL.widths):
        raise TemplateError(
            f"{space.node_id}: {a1 - a0} units of frontage will not hold a "
            f"{min(fixtures.PEDESTAL.widths)}-unit shelf")

    shelf_d = fixtures.PEDESTAL.depth
    counter_d = fixtures.COUNTER.depth
    usable = across - 2 * WALL_STANDOFF
    axis = "x" if along_x else "y"
    # What fits decides what goes in, and a counter wins a shallow unit:
    # a counter is the thing that says "shop" from the doorway, where a
    # shelf run alone reads as storage.
    if usable >= shelf_d + counter_d + STAND_CLEAR:
        placed = [("shelves", shelf_d, WALL_STANDOFF),
                  ("counter", counter_d, across - WALL_STANDOFF - counter_d)]
    elif usable >= counter_d:
        placed = [("counter", counter_d, across - WALL_STANDOFF - counter_d)]
    elif usable >= shelf_d:
        placed = [("shelves", shelf_d, WALL_STANDOFF)]
    else:
        raise TemplateError(
            f"{space.node_id}: {across} units deep leaves {usable} of clear "
            f"floor, less than the {shelf_d}-unit shelf family needs")
    for kind, depth, offset in placed:
        base = (y0 if along_x else x0) + offset
        fixtures.run_along(
            f"{space.node_id}_{kind}", space, axis=axis,
            start=a0, end=a1, across0=base, across1=base + depth,
            family="pedestal" if kind == "shelves" else "counter",
            material=material, grade=grade, host_clear=host_clear,
            connector=connector)
    # The runs attach to the room; move them into this node so the shop owns
    # its fittings rather than scattering them among the room's children.
    wanted = {f"{space.node_id}_{kind}" for kind, _d, _o in placed}
    for child in list(space.children):
        if child.node_id in wanted:
            space.children.remove(child)
            child.parent = node
            node.children.append(child)
    node.note = ("shop fittings: "
                 + " and ".join(kind for kind, _d, _o in placed)
                 + f" ({across} deep, {usable} clear)")
    return node


def clothier(space, *, material, grade: int, host_clear: int,
             name: str = "clothier_fittings", connector=None):
    """Fit a broad-fronted shop without sacrificing its entrance aisle.

    E6M1's shop language is a *tall shelf wall* (2026/202/2635) with crate
    texture on its small solid modules (95/452), not a room scattered with
    anonymous plinths.  Its cashwrap is separate geometry: a 6,144-rise
    3,072x1,024 counter and two 2,048-rise register tops using tile 2476.
    The composition keeps the entrance-side aisle clear of those solids.

    The template is directional only through its handed-in rectangular space:
    its long side is the window frontage and the caller keeps the entrance on
    the opposite short face.  That makes it reusable for another broad shop
    without copying its furniture coordinates.
    """
    import citytree
    import props

    x0, y0, x1, y1 = (int(v) for v in props.room_rect(space))
    width, depth = x1 - x0, y1 - y0
    if width < 10 * fixtures.PEDESTAL.depth or depth < 4 * fixtures.PEDESTAL.depth:
        raise TemplateError(
            f"{space.node_id}: {width}x{depth} is too small for a clothier")
    node = citytree.sub(space, name, note="E6M1-style racks, counter and garment stands")

    # Sector 61/63's shelf language has crate-top modules but *shelf* walls.
    # This wall-side run is intentionally a single bank, leaving the broad
    # eastern approach to the doorway as usable floor instead of an aisle
    # squeezed between two parallel furniture rows.
    rack = fixtures.run_along(
        f"{space.node_id}_shelf_bank", space, axis="y",
        start=y0 + 2 * fixtures.PEDESTAL.depth,
        end=y1 - fixtures.PEDESTAL.depth,
        across0=x0 + WALL_STANDOFF,
        across1=x0 + WALL_STANDOFF + fixtures.PEDESTAL.depth,
        family="pedestal", material=material, grade=grade,
        host_clear=host_clear, gap=WALL_STANDOFF, connector=connector,
        wall_picnum=2026)

    # This small shop needs one legible point of sale, not a pair of tills.
    # Keep E6M1's source-proven counter geometry, but expose only one register.
    counter = cashwrap(
        space, material=material, grade=grade, host_clear=host_clear,
        rect=(x0 + 2 * fixtures.PEDESTAL.depth, y0 + WALL_STANDOFF,
              x0 + 8 * fixtures.PEDESTAL.depth,
              y0 + WALL_STANDOFF + fixtures.COUNTER.depth),
        name=f"{space.node_id}_checkout", connector=connector, into=node,
        registers=1)

    # Two discrete 512-square modules read as clothing rails/display stands.
    # They sit behind the main line of travel and retain one module of clear
    # space to both the counter and the entrance wall.
    rail_y1 = y1 - WALL_STANDOFF
    rail_y0 = rail_y1 - fixtures.PEDESTAL.depth
    rail_start = x0 + fixtures.PEDESTAL.depth
    rails = []
    for index in range(2):
        rx0 = rail_start + index * 2 * fixtures.PEDESTAL.depth
        rx1 = rx0 + fixtures.PEDESTAL.depth
        if rx1 > x1 - fixtures.PEDESTAL.depth:
            break
        rails.append(fixtures.place(
            f"{space.node_id}_garment_rail_{index}", space,
            (rx0, rail_y0, rx1, rail_y1), material, family="pedestal",
            grade=grade, host_clear=host_clear, connector=connector,
            into=node, wall_picnum=202))

    # `run_along` makes its own assembly beneath the room; this composition
    # owns it alongside the directly placed counter and rails.
    space.children.remove(rack)
    rack.parent = node
    node.children.append(rack)
    node.note = ("clothier fittings: E6M1 shelf bank, single checkout and "
                 f"{len(rails)} garment rails; door-side aisle preserved")
    return node


def checkout_counter(space, *, material, grade: int, host_clear: int, rect,
                     name: str = "checkout", connector=None, into=None):
    """A normal 2,048x1,024 sales counter with one clearly readable register.

    A neighbourhood shop needs a place to pay rather than a miniature
    department-store island.  The base uses the campaign counter rise and
    E6M1's wood casework; the single small top carries tile 2476, so it reads
    as a register instead of a second anonymous platform.
    """
    import citytree

    x0, y0, x1, y1 = (int(value) for value in rect)
    width, depth = x1 - x0, y1 - y0
    if sorted((width, depth)) != [fixtures.COUNTER.depth,
                                  4 * fixtures.PEDESTAL.depth]:
        raise TemplateError(
            f"{name}: {width}x{depth}; a checkout is 1024x2048")
    parent = into if into is not None else citytree.sub(
        space, name, note="single checkout counter with one register")
    base = fixtures.place(
        f"{name}_base", space, (x0, y0, x1, y1), material,
        family="counter", grade=grade, host_clear=host_clear,
        connector=connector, into=parent, wall_picnum=34)
    base.surfaces(wall_picnum=34, floor_picnum=20,
                  floor_z=grade - fixtures.COUNTER.rise,
                  clear_height=host_clear - fixtures.COUNTER.rise)
    base.region_kwargs["portal_wall_picnum"] = 34
    # Centre the till toward the cashier side.  A 512-square top gives it a
    # silhouette distinct from the counter without blocking the customer's
    # entire approach.
    if width > depth:
        register_rect = (x1 - 768, y0 + 256, x1 - 256, y0 + 768)
    else:
        register_rect = (x0 + 256, y1 - 768, x0 + 768, y1 - 256)
    register = setpieces.raised_solid(
        parent, f"{name}_register", base, register_rect, material,
        grade=grade - fixtures.COUNTER.rise, rise=1024,
        host_clear=host_clear - fixtures.COUNTER.rise, connector=connector,
        face_picnum=34,
        note="E6M1 register top: tile 2476")
    register.surfaces(wall_picnum=34, floor_picnum=2476,
                      floor_stat=E6_REGISTER_FLOOR_STAT,
                  floor_z=grade - fixtures.COUNTER.rise - 1024,
                  clear_height=host_clear - fixtures.COUNTER.rise - 1024)
    register.region_kwargs["portal_wall_picnum"] = 34
    register.region_kwargs["floor_slope"] = _e6_register_slope(register_rect)
    return base


def cashwrap(space, *, material, grade: int, host_clear: int, rect,
             name: str = "cashwrap", connector=None, into=None,
             registers: int = 2):
    """E6M1's counter S32 plus its two raised cash-register tops S33/S34.

    The base is precisely one player-width by three player-widths, raised
    6,144 from its host.  Each register top is a 512-square solid at a further
    rise of 2,048, with floor tile 2476.  `rect` may be rotated, but must keep
    those two dimensions; this is a real prefab, not a texture suggestion.
    """
    import citytree

    x0, y0, x1, y1 = (int(value) for value in rect)
    width, depth = x1 - x0, y1 - y0
    if sorted((width, depth)) != [fixtures.COUNTER.depth,
                                  6 * fixtures.PEDESTAL.depth]:
        raise TemplateError(
            f"{name}: {width}x{depth}; E6M1 cashwrap is 1024x3072")
    if registers not in (1, 2):
        raise TemplateError(f"{name}: registers must be 1 or 2")
    parent = into if into is not None else citytree.sub(
        space, name, note="E6M1 S32 cashwrap with S33/S34 registers")
    base = setpieces.raised_solid(
        parent, f"{name}_base", space, (x0, y0, x1, y1), material,
        grade=grade, rise=6144, host_clear=host_clear, connector=connector,
        face_picnum=34,
        note="E6M1 S32 counter base: rise 6144, floor tile 20")
    base.surfaces(wall_picnum=34, floor_picnum=20,
                  floor_z=grade - 6144, clear_height=host_clear - 6144)
    base.region_kwargs["portal_wall_picnum"] = 34
    horizontal = width > depth
    panels = (
        ((x0 + 256, y0 + 256, x0 + 768, y0 + 768),
         (x1 - 768, y0 + 256, x1 - 256, y0 + 768)) if horizontal else
        ((x0 + 256, y0 + 256, x0 + 768, y0 + 768),
         (x0 + 256, y1 - 768, x0 + 768, y1 - 256))
    )
    for index, panel in enumerate(panels[:registers]):
        register = setpieces.raised_solid(
            parent, f"{name}_register_{index}", base, panel, material,
            grade=grade - 6144, rise=2048, host_clear=host_clear - 6144,
            connector=connector,
            face_picnum=34,
            note="E6M1 register top: tile 2476")
        register.surfaces(wall_picnum=34, floor_picnum=2476,
                          floor_stat=E6_REGISTER_FLOOR_STAT,
                          floor_z=grade - 8192,
                          clear_height=host_clear - 8192)
        register.region_kwargs["portal_wall_picnum"] = 34
        register.region_kwargs["floor_slope"] = _e6_register_slope(panel)
    return base


def supermarket(space, *, material, grade: int, host_clear: int,
                name: str = "supermarket_fittings", connector=None):
    """Lay out an E6M1-style sales floor: tall shelf banks and crate bays.

    E6M1 has two separate grammars.  Shelves are long, wall-like banks with
    2026/2635/202 on their vertical faces; 452/95 are independent crate
    cuboids, arranged in short bays beside them.  Treating every shelf as a
    pedestal was the reason the old supermarket looked like a field of floor
    tiles rather than a shop.
    """
    import citytree
    import props

    x0, y0, x1, y1 = (int(v) for v in props.room_rect(space))
    width, depth = x1 - x0, y1 - y0
    if min(width, depth) < 4 * fixtures.PEDESTAL.depth:
        raise TemplateError(
            f"{space.node_id}: {width}x{depth} is too small for a supermarket")
    node = citytree.sub(space, name,
                        note="E6M1 shelf aisles and paired supermarket checkouts")

    # Long shelf banks: the source uses 3,072--4,096-unit runs and vertical
    # faces taller than a player.  Their top is ordinary shop flooring, not a
    # crate texture; the separate crate bays below provide the 452/95 detail.
    shelf_end = y1 - 2 * fixtures.PEDESTAL.depth
    bank_specs = (
        (x0 + 1536, x0 + 2560, y0 + 1024, shelf_end - 1024, 2026, 24576),
        (x0 + 4096, x0 + 5120, y0 + 1024, shelf_end, 2635, 20480),
        (x0 + 6656, x0 + 7680, y0 + 1024, shelf_end - 1024, 202, 24576),
    )
    racks = []
    for index, (sx0, sx1, sy0, sy1, wall_tile, rise) in enumerate(bank_specs):
        if sx1 > x1 - 512 or sy1 <= sy0:
            continue
        bank = setpieces.raised_solid(
            node, f"{space.node_id}_shelf_bank_{index}", space,
            (sx0, sy0, sx1, sy1), material, grade=grade, rise=rise,
            host_clear=host_clear, connector=connector,
            face_picnum=wall_tile,
            note="E6M1 long shelf bank")
        bank.surfaces(wall_picnum=wall_tile, floor_picnum=material.floor,
                      floor_z=grade - rise, clear_height=host_clear - rise)
        bank.region_kwargs["portal_wall_picnum"] = wall_tile
        racks.append(bank)

    # Distinct crate bays on whole render-complete texture modules.  The west
    # and centre aisles take the smaller 452 unit; the wider east aisle takes
    # one full 95 unit.  Neither skin is cropped merely to fill an aisle.
    crate_specs = (
        (SMALL_CRATE, (x0 + 256, y0 + 1536,
                       x0 + 256 + SMALL_CRATE.side,
                       y0 + 1536 + SMALL_CRATE.side), SMALL_CRATE.rise),
        (SMALL_CRATE, (x0 + 256, y0 + 3328,
                       x0 + 256 + SMALL_CRATE.side,
                       y0 + 3328 + SMALL_CRATE.side), SMALL_CRATE.rise),
        (SMALL_CRATE, (x0 + 2816, y0 + 2304,
                       x0 + 2816 + SMALL_CRATE.side,
                       y0 + 2304 + SMALL_CRATE.side), SMALL_CRATE.rise),
        (LARGE_CRATE, (x1 - 256 - LARGE_CRATE.side, y0 + 2048,
                       x1 - 256, y0 + 2048 + LARGE_CRATE.side),
         LARGE_CRATE.rise),
    )
    for index, (module, rect, rise) in enumerate(crate_specs):
        _crate_block(node, f"{space.node_id}_crate_{index}", space, rect,
                     material, grade=grade, host_clear=host_clear, module=module,
                     rise=rise, connector=connector, note="market crate stack")

    # The full S32--S34 cashwrap belongs in the large sales floor: its two
    # register tops read as staffed lanes, unlike the pawn shop's single till.
    checkout_y0 = y1 - 1280
    cashwrap(
        space, material=material, grade=grade, host_clear=host_clear,
        rect=(x0 + 512, checkout_y0, x0 + 3584, checkout_y0 + 1024),
        name=f"{space.node_id}_checkout", connector=connector, into=node)

    node.note = (f"supermarket fittings: {len(racks)} tall shelf banks, "
                 "separate 452/95 crate stacks and one two-register checkout")
    return node


def stockroom(space, *, material, grade: int, host_clear: int,
              name: str = "stock", connector=None):
    """A back-room made of complete small and large crate cuboids."""
    import citytree
    import props

    x0, y0, x1, y1 = (int(v) for v in props.room_rect(space))
    width, depth = x1 - x0, y1 - y0
    if min(width, depth) < 2 * fixtures.PEDESTAL.depth:
        raise TemplateError(f"{space.node_id}: {width}x{depth} is too small for stock")
    node = citytree.sub(space, name, note="back-stock complete crate stacks")
    # The staff door occupies the centre of the south edge, so stacks sit in
    # discrete bays to either side.  Every rect and height is an integer count
    # of its source crate module.
    stock_specs = (
        (SMALL_CRATE, (x0 + 256, y0 + 256,
                       x0 + 256 + SMALL_CRATE.side,
                       y0 + 256 + SMALL_CRATE.side), SMALL_CRATE.rise),
        (SMALL_CRATE, (x0 + 1536, y0 + 256,
                       x0 + 1536 + SMALL_CRATE.side,
                       y0 + 256 + SMALL_CRATE.side), SMALL_CRATE.rise),
        (SMALL_CRATE, (x0 + 5120, y0 + 256,
                       x0 + 5120 + SMALL_CRATE.side,
                       y0 + 256 + SMALL_CRATE.side), SMALL_CRATE.rise),
        (SMALL_CRATE, (x0 + 7680, y0 + 256,
                       x0 + 7680 + SMALL_CRATE.side,
                       y0 + 256 + SMALL_CRATE.side), SMALL_CRATE.rise),
        (SMALL_CRATE, (x0 + 9216, y0 + 256,
                       x0 + 9216 + SMALL_CRATE.side,
                       y0 + 256 + SMALL_CRATE.side), SMALL_CRATE.rise),
    )
    for index, (module, rect, rise) in enumerate(stock_specs):
        if rect[2] > x1 - 256:
            continue
        _crate_block(node, f"{space.node_id}_crate_{index}", space, rect,
                     material, grade=grade, host_clear=host_clear, module=module,
                     rise=rise, connector=connector, note="stockroom crate stack")
    return node


def bar(space, *, material, grade: int, host_clear: int, name: str = "fittings",
        margin: int = 1024, tables: int = 2, connector=None):
    """Furnish a drinking room: a counter, a back-bar panel run, tables.

    The saloon's counter and its two card tables were three literal rects
    in `l3_theatre.FURNITURE`.  They are the same three things every bar
    has, so they are a template with a length rather than a table row.
    """
    import citytree
    import props

    x0, y0, x1, y1 = _inset_rect(props.room_rect(space), margin)
    if x1 - x0 < 2048 or y1 - y0 < 2048:
        raise TemplateError(
            f"{space.node_id}: {x1 - x0}x{y1 - y0} is too small for a bar")
    node = citytree.sub(space, name, note="bar fittings (templates.bar)")

    bar_run = fixtures.run_along(
        f"{space.node_id}_bar", space, axis="x", start=x0, end=x1,
        across0=y0, across1=y0 + fixtures.COUNTER.depth,
        family="counter", material=material, grade=grade,
        host_clear=host_clear, connector=connector)
    # The scale below the fixture: what stands ON the counter.  A bar's own
    # counter is the deliberate case -- `every=True` -- because a bar with
    # nothing on it is the thing being fixed; every other surface in the
    # city goes through `surface.carries` at the campaign's 4.7%.
    import surface
    surface.dress_run(bar_run, f"{space.node_id}_candles",
                      item=surface.CANDLE, every=True)
    # Tables down the far half, spaced so a body fits between them.
    step = (x1 - x0) // max(1, tables)
    for index in range(tables):
        tx = x0 + index * step + (step - TABLE_SIDE) // 2
        ty = y1 - TABLE_SIDE
        setpieces.raised_solid(
            space, f"{space.node_id}_table_{index}", space,
            (tx, ty, tx + TABLE_SIDE, ty + TABLE_SIDE), material,
            grade=grade, rise=TABLE_RISE, host_clear=host_clear,
            connector=connector, note="a card table (templates.bar)")
    for child in list(space.children):
        if child.node_id.startswith(f"{space.node_id}_bar") \
                or "_table_" in child.node_id:
            space.children.remove(child)
            child.parent = node
            node.children.append(child)
    return node


# ---------------------------------------------------------------------------
# venue templates: the builder names what it builds
# ---------------------------------------------------------------------------
#
# These replace the last hand loops below the template layer. Those loops
# iterated a table of rectangles into `furniture_{index}`, so the Aldermack's
# stage, its three rows of seating and its box office were `furniture_0`
# through `furniture_4` -- five different things wearing one name, with the
# meaning only in a prose note. `citytree find stage` returned `backstage`.
#
# The fix is not a naming convention. Whoever places a thing knows what the
# thing is, so the names fall out of raising the work to a template.
#
# Every measurement below is the one the hand table already used; the rises
# come from `setpieces`' mined classes, and the insets are stated as
# proportions of the host so the same call furnishes a different-sized room.

#: A stage's own depth, how far it stands off the back wall, and its rise:
#: one max step, so the player can get up on it.
STAGE_DEPTH, STAGE_INSET, STAGE_RISE = 2048, 512, 4096
#: A seating row: how deep, how far apart, and how much each rises over the
#: one in front. `setpieces.LOW_STEP` is the mined shallow tier.
ROW_DEPTH, ROW_PITCH, ROW_RAKE = 512, 1024, 1024
#: How far the fittings of a house stand off its side walls.
HOUSE_MARGIN = 1024
#: A counter across the front of a room: depth, and its inset.
DESK_DEPTH, DESK_INSET = 512, 512
#: A shooting range: the line you stand behind, and what you shoot at.
TARGET_SIDE, TARGET_PITCH = 512, 1536
#: A pew, and the gap between two of them.
PEW_DEPTH, PEW_PITCH = 512, 1024
#: The mined rises, restated here only so a reader can see them together.
PEW_RISE = 5120
FONT_RISE = 4096


def _host_rect(space):
    import props
    return tuple(int(v) for v in props.room_rect(space))


def theatre_house(space, *, material, grade: int, host_clear: int,
                  stage_clear: int, rows: int = 3, name: str = "house",
                  margin: int = HOUSE_MARGIN, connector=None):
    """The stage under its proscenium, and the raked rows facing it.

    The stage gets a LOWER ceiling than the house, which is what turns the
    wall between the two into a proscenium arch -- with the house's own
    ceiling carried over it the auditorium is a hall with a step in it.

    Each row is an island in the floor, so no two share an undeclared edge,
    and each rises `ROW_RAKE` over the one in front. The rows are a rhythm
    and share one note; the stage is not and does not.
    """
    import citytree
    import setpieces

    x0, y0, x1, y1 = _host_rect(space)
    if x1 - x0 < 2 * margin + 1024 or y1 - y0 < STAGE_DEPTH + rows * ROW_PITCH:
        raise TemplateError(
            f"{space.node_id}: {x1 - x0}x{y1 - y0} will not hold a stage and "
            f"{rows} rows")
    node = citytree.sub(space, name, note="the house: stage and seating")

    setpieces.raised_solid(
        node, "stage", space,
        (x0 + margin, y0 + STAGE_INSET,
         x1 - margin, y0 + STAGE_INSET + STAGE_DEPTH),
        material, grade=grade, rise=STAGE_RISE,
        host_clear=host_clear, connector=connector or citytree.owner(space),
        note="the stage, under its proscenium").surfaces(
            floor_z=grade - STAGE_RISE, clear_height=stage_clear)

    # Laid from the back of the house forward, so the last row is always
    # against the rear wall however many there are -- and the rake counts
    # DOWN from the back, because a raked house lifts the rows furthest from
    # the stage.  Laying the rise up from the front instead put the tallest
    # row nearest the stage, which is a grandstand facing the wrong way.
    seating = citytree.sub(node, "seating", note="raked rows facing the stage")
    for index in range(rows):
        back = y1 - STAGE_INSET - index * ROW_PITCH
        setpieces.raised_solid(
            seating, f"row_{rows - 1 - index}", space,
            (x0 + margin, back - ROW_DEPTH, x1 - margin, back),
            material, grade=grade, rise=(rows - index) * ROW_RAKE,
            host_clear=host_clear, connector=connector or citytree.owner(space),
            note="a raked row of seating")
    return node


def box_office(space, *, material, grade: int, host_clear: int,
               name: str = "box_office", connector=None):
    """A counter across the front of a foyer. One thing, so one name."""
    import citytree
    import setpieces

    x0, y0, x1, y1 = _host_rect(space)
    return setpieces.raised_solid(
        space, name, space,
        (x0 + DESK_INSET, y0 + DESK_INSET,
         x1 - DESK_INSET, y0 + DESK_INSET + DESK_DEPTH),
        material, grade=grade, rise=setpieces.COUNTER,
        host_clear=host_clear, connector=connector or citytree.owner(space),
        note="the box office")


def shooting_range(space, *, material, grade: int, host_clear: int,
                   targets: int = 3, name: str = "fittings", connector=None):
    """A firing line you stand behind, and what you shoot at.

    The line is one thing and keeps its own name; the targets are a rhythm
    and take an index, which is what an index is for.
    """
    import citytree
    import setpieces

    x0, y0, x1, y1 = _host_rect(space)
    span = x1 - x0 - 2 * DESK_INSET
    if span < targets * TARGET_PITCH - (TARGET_PITCH - TARGET_SIDE):
        raise TemplateError(
            f"{space.node_id}: {span} units will not hold {targets} targets "
            f"at {TARGET_PITCH}")
    node = citytree.sub(space, name, note="the range: line and targets")

    setpieces.raised_solid(
        node, "firing_line", space,
        (x0 + DESK_INSET, y1 - 1024, x1 - DESK_INSET, y1 - 1024 + DESK_DEPTH),
        material, grade=grade, rise=setpieces.COUNTER,
        host_clear=host_clear, connector=connector or citytree.owner(space),
        note="the firing line")

    butts = citytree.sub(node, "targets", note="what the range shoots at")
    for index in range(targets):
        left = x0 + 1024 + index * TARGET_PITCH
        setpieces.raised_solid(
            butts, f"target_{index}", space,
            (left, y0 + DESK_INSET, left + TARGET_SIDE,
             y0 + DESK_INSET + TARGET_SIDE),
            material, grade=grade, rise=setpieces.COUNTER,
            host_clear=host_clear, connector=connector or citytree.owner(space),
            note="a target")
    return node


def chapel_furnishing(nave, *, material, grade: int, host_clear: int,
                      pews: int = 4, first: int = 1024,
                      name: str = "pews", connector=None):
    """Rows of pews down a nave, leaving an aisle against each wall.

    Six half-width pews touching the walls left nowhere to bracket a light
    and the first wall-mounted brazier landed inside one, so the block runs
    down the middle with a 512-unit side aisle either way.

    Pews are a rhythm: identical siblings of one spacing, so they take an
    index and share a note. That is what an index is for.
    """
    import citytree
    import setpieces

    x0, y0, x1, y1 = _host_rect(nave)
    if y1 - y0 < first + pews * PEW_PITCH:
        raise TemplateError(
            f"{nave.node_id}: {y1 - y0} units of nave will not hold {pews} "
            f"pews at {PEW_PITCH}")
    node = citytree.sub(nave, name, note="rows of pews down the nave")
    for index in range(pews):
        top = y0 + first + index * PEW_PITCH
        setpieces.raised_solid(
            node, f"pew_{index}", nave,
            (x0 + 512, top, x1 - 512, top + PEW_DEPTH),
            material, grade=grade, rise=PEW_RISE, host_clear=host_clear,
            connector=connector or citytree.owner(nave), note="a pew")
    return node


def font(narthex, *, material, grade: int, host_clear: int,
         name: str = "font", connector=None):
    """The font, standing in the narthex. One thing, one name."""
    import citytree
    import setpieces

    x0, y0, x1, y1 = _host_rect(narthex)
    return setpieces.raised_solid(
        narthex, name, narthex,
        (x0 + 256, y0 + 2048, x0 + 1280, y0 + 2560),
        material, grade=grade, rise=FONT_RISE, host_clear=host_clear,
        connector=connector or citytree.owner(narthex),
        note="the font")


# ---------------------------------------------------------------------------
# the monument
# ---------------------------------------------------------------------------
#
# `tools/mine_monuments.py` detects a monument as a chain of raised sectors
# under open sky, each tier's footprint strictly inside the one below.  421
# of them across 66 maps, and they answer both questions this composition
# had to ask:
#
# * **How is a stepped base built?**  Two tiers is the norm (389 of 421) and
#   three is the rich version (30).  A tier rises a median **0.42 player
#   heights** (q1 0.18, q3 0.97).  The base runs a median **2.0 plan units**
#   (q1 1.5, q3 3.25) and the top **0.62** (q1 0.44, q3 1.25) -- so the top
#   is about a third of the base.
# * **How is a figure stood?**  It is not.  Only 77 of the 421 carry
#   anything at all, and what they carry is **light**: 23 of the statuary
#   sprites are one invisible generator (type 709, tile 2520, cstat 32896),
#   the rest torches and lamps.  Blood has no figure-on-a-plinth idiom, so
#   this composition does not invent one -- the apex carries a flame, and
#   the flame is what lights the plaza.

#: The three tiers, as (footprint in units, rise in units).  The rises are
#: 0.09 / 0.72 / 0.24 player heights: the first is a step onto the base, the
#: second is the drum that carries the lettering, the third caps it.  0.09 is
#: below the mined q1 of 0.18 and deliberately so -- it is a step, and a step
#: over 4,096 cannot be walked onto.
#: The plinth is 1,792 and not 2,048 because the base is CHAMFERED: the
#: street cuts 512 off every convex corner of a free-standing mass, so the
#: base's corner runs x+y = 1,920 from centre and a 2,048 square pokes
#: through it.  896 + 896 = 1,792 clears it.
MONUMENT_TIERS = (
    ("base", 2432, 1536),
    ("plinth", 1792, 12288),
    ("pedestal", 1024, 12288),
)


def monument_cost() -> dict:
    """Declared before anything is emitted."""
    return {"sectors": len(MONUMENT_TIERS), "walls": 4 * len(MONUMENT_TIERS),
            "sprites": 4,
            "source": "monuments-v1.json: 421 tiered outdoor masses, 66 maps"}


def monument(parent, street, outline, *, material, cap_material, grade: int,
             clear_height: int, name: str = "monument", connector=None,
             tiers=MONUMENT_TIERS):
    """A stepped base, a lettered plinth and a pedestal, filling a street hole.

    The street already carves the free-standing mass out of itself, so the
    first tier FILLS that hole rather than cutting a new one; every tier
    after it is carved out of the one below, which is the same
    concentric discipline `setpieces.basin` uses and the only construction
    where every coincident edge is a declared portal.

    Returns the assembly. Its children are named for what they are.
    """
    import citytree
    import setpieces

    node = parent.assembly(
        name,
        note="the plaza monument: stepped base, lettered plinth, pedestal")
    owner = connector or parent

    # Tier 1 fills the hole the street already cut -- and it must fill it
    # exactly.  The street chamfers every convex corner of a free-standing
    # mass (512 units, which is where most of a Build city's diagonals come
    # from), so a square base overlaps the octagonal hole partly and the
    # compiler refuses it.  `outline` is the hole, in world units, and every
    # one of its eight edges is joined -- the four chamfers included.
    from bloodmap.levelprog import Frame

    label, size, rise = tiers[0]
    floor = grade - rise
    points = [(int(px), int(py)) for px, py in outline]
    ox = min(px for px, _py in points)
    oy = min(py for _px, py in points)
    base = citytree.make_room(
        node, label, [(px - ox, py - oy) for px, py in points],
        role="detail", frame=Frame(ox, oy),
        faces={f"edge{index}": index for index in range(len(points))},
        region_kwargs=material.region_kwargs(),
        note=f"the {label}: one step up off the plaza")
    base.surfaces(**material.style_kwargs(floor_z=floor,
                                          clear_height=clear_height - rise))
    # Compass names for the four axis-aligned edges as well, because
    # `setpieces._rim` joins an inner tier to its host by naming a face and
    # a chamfered octagon offers only `edge0`..`edge7`.
    from bloodmap.levelprog import _compass_edges
    local = [(px - ox, py - oy) for px, py in points]
    base.faces.update(_compass_edges(local))
    for index in range(len(points)):
        owner.connect(base.face(f"edge{index}"), street.face("north"),
                      connection_id=f"connection:{name}_{label}_{index}")

    below, below_floor, below_size = base, floor, size
    cx = (min(px for px, _p in points) + max(px for px, _p in points)) // 2
    cy = (min(py for _p, py in points) + max(py for _p, py in points)) // 2
    made = {label: base}
    for label, size, rise in tiers[1:]:
        half = size // 2
        inner = (cx - half, cy - half, cx + half, cy + half)
        floor = below_floor - rise
        piece = setpieces.raised_solid(
            node, label, below, inner,
            cap_material if label == tiers[-1][0] else material,
            grade=below_floor, rise=rise,
            host_clear=clear_height - (grade - below_floor),
            connector=owner,
            note={"plinth": "the plinth: the face the city is named on",
                  "pedestal": "the pedestal: what the flame stands on"}
                 .get(label, f"the {label}"))
        made[label] = piece
        below, below_floor, below_size = piece, floor, size
    return node, made


# ---------------------------------------------------------------------------
# the sprite level: what ends up on the shelf
# ---------------------------------------------------------------------------

def stock(layout, node, *, wall: int, floor: int, ceiling: int) -> dict:
    """Put goods on the fixtures of this node that carry any.

    One in seven, from `fixtures.GOODS_SHARE` -- the median fixture in
    every detail source carries nothing, so stocking every pedestal would
    be the wrong answer confidently applied.
    """
    import citytree
    import props

    # Only floor-standing props: goods sit ON a shelf.  The shop palette's
    # associations are almost all wall-hung -- 965 a window view, 269 a
    # framed painting -- which is a real finding about what Blood keeps in
    # a room like this, and the reason an unfiltered version of this
    # function placed nothing at all and reported success.
    candidates = [tile for tile in props.props_for(wall, floor, ceiling,
                                                   sky=False)
                  if props.kind_of(tile) == "floor"]
    report = {"fixtures": 0, "stocked": 0, "tiles": {},
              "candidates": len(candidates)}
    if not candidates:
        report["note"] = ("no floor-standing prop is associated with this "
                          "palette; the fixture is the detail")
        return report
    for index, room in enumerate(citytree.rooms_under(node)):
        report["fixtures"] += 1
        if not fixtures.goods_on(index, room.path()):
            continue
        tile = candidates[fixtures._roll(f"{room.path()}:goods", len(candidates))]
        try:
            props.stand_on_floor(layout, f"goods:{room.path()}", room.region_id,
                                 local=(0.5, 0.5), tile=tile)
        except Exception:
            continue
        report["stocked"] += 1
        report["tiles"][tile] = report["tiles"].get(tile, 0) + 1
    return report
