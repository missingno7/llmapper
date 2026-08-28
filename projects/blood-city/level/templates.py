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

PLAYER = 16960

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
