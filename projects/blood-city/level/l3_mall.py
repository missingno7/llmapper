"""The Gravesend Arcade: a shopping mall, from E4M9's own proportions.

Owner: add a shopping mall; E4M9 is the campaign's, and E6M1 has the shop.

What E4M9 actually is, measured rather than remembered: a **tall concourse**
with units opening straight onto it.  Its concourse sectors run **3.86 to
4.35 player heights** where its retail units run 1.8 to 2.9 — the height
difference *is* the mall.  Units sit at the concourse's own floor level
(step +0) with a few raised half a player (-8192), and unit areas cluster
between 0.4M and 6M square units.

The shopfronts are E6M1's, which this project already built once for the
pawn shop: a shallow display box between the shop and the public space,
floor raised as a plinth, glazed on the public side with a masked
translucent wall and an XWALL that lets it be shot out (see `glass.py`).

Three lessons from elsewhere land here:

* **Name the uses.**  DukCity spells its businesses on the wall — SHOPPING
  CENTER, PHARMACY, TOYS US, BOOKS, NEWS — roughly ten named uses a map,
  where Gravesend had five venues in the whole city.  Each unit here is
  named, in `signage.py`.
* **A key placard means a keyed door.**  The service corridor behind the
  arcade is locked, carries `XSECTOR.key`, and the eye emblem hangs beside
  it because that is what the emblem is for.  The key itself is in a unit,
  reachable.
* **Ambience.**  Sound 65 is E4M9's own, and E4M9 is its heaviest user in
  the corpus (5 of its 11 instances).
"""

from __future__ import annotations

from bloodmap.doors import z_motion_door
from bloodmap.levelprog import Frame, RECT_FACES, Style
from bloodmap.slope import SlopeSpec

import keysign
import setpieces
import templates
from materials import FACADES, INTERIORS, MASONRY
from resolution import GRADE, PU

COMPASS = dict(zip(RECT_FACES, range(4)))

#: market_block_c, the biggest unbuilt block in the city.
MASS = (39 * PU, 40 * PU, 53 * PU, 50 * PU)

DOOR_D = PORCH_D = 256
DOOR_H = 31744            # the campaign's median door opening
CONCOURSE_H = 65536       # 3.86 player heights: E4M9's concourse
UNIT_H = 28672            # 1.69: E4M9's retail units
SERVICE_H = 24576
# A concourse is a hall, not an extra-wide room.  This shallow clerestory-like
# pitch supplies the missing interior volume while leaving every shop front
# and portal at its existing clear height.
CONCOURSE_PITCH = 8192

#: The key the service corridor needs.  2 is the eye; its placard is 2541
#: and its item is sprite type 101.
SERVICE_KEY = 2

#: The concourse, which is the only thing here stated as a rectangle: it is
#: the site, and everything else is derived from it.
CONCOURSE = (40448, 44544, 51712, 47616)

NECK_D = 512
#: The band each range's openings live in.
NORTH_BAND = (CONCOURSE[1] - NECK_D, CONCOURSE[1])
SOUTH_BAND = (CONCOURSE[3], CONCOURSE[3] + NECK_D)
UNIT_D = 2048
#: How deep a display box stands in front of its shop.
WINDOW_PLINTH = 2048

#: **The ranges are generated, not drawn.**  They used to be six literal
#: rectangles on a fixed 3x2 grid at absolute coordinates, so the arcade
#: could not answer the only question a retail row is ever asked: how many
#: shops fit here?  `templates.retail_row` answers it from the frontage,
#: at E4M9's own measured rhythm -- a 2,560-unit unit (its median across 51
#: units) opening on 1,536 (its median across 85 shared walls).  Hand it a
#: longer concourse and it builds more shops.
import templates as _templates

#: One unit per range is glazed, because a mall whose every unit is behind
#: glass has no way in and a mall with none is a corridor of doors.
GLAZED = (0,)

RANGES = {
    "north": _templates.retail_row(
        start=CONCOURSE[0], end=CONCOURSE[2], band=NORTH_BAND[0],
        side="north", depth=UNIT_D, glaze=GLAZED),
    "south": _templates.retail_row(
        start=CONCOURSE[0], end=CONCOURSE[2], band=SOUTH_BAND[1],
        side="south", depth=UNIT_D, glaze=GLAZED),
}
#: Unit names stay a, b, c ... so signage and the key placard keep working.
_LETTERS = "abcdefghijklmnop"


def _unit_name(side, index):
    return "unit_" + _LETTERS[index + (0 if side == "north" else
                                       len(RANGES["north"]))]


ROOMS = [
    ("concourse", *CONCOURSE, "common", CONCOURSE_H,
     "the arcade concourse: E4M9's height, which is what makes it a mall"),
] + [
    (_unit_name(side, unit.index), *unit.rect, "shop", UNIT_H,
     f"a retail unit ({side} range, {unit.index})")
    for side, units in RANGES.items() for unit in units
] + [
    ("service", 51968, 44544, 53760, 47616, "service", SERVICE_H,
     "the service corridor, behind the keyed door"),
]

#: Necks: each unit reaches the concourse through its own opening, so the
#: rest of its frontage can be glass.  (unit, x0, x1, side)
NECKS = [
    (_unit_name(side, unit.index), unit.opening[0], unit.opening[1], side)
    for side, units in RANGES.items() for unit in units
]

#: Glazed display boxes, the E6M1 shopfront: (unit, x0, x1, side, plinth).
#: One per range, because a mall whose every unit is behind glass has no way
#: in and a mall with none is a corridor of doors.  The pane takes the
#: frontage left over beside the unit's own opening, so it never overlaps it.
WINDOWS = [
    (_unit_name(side, unit.index), unit.window[0], unit.window[1],
     side, WINDOW_PLINTH)
    for side, units in RANGES.items() for unit in units
    if unit.window is not None
]


def build(city, market_st):
    """The arcade, its units, its glazing and its locked service door."""
    facade = FACADES["market_slip"]
    arcade = city.assembly(
        "gravesend_arcade",
        style=Style(**INTERIORS["common"].style_kwargs(
            floor_z=GRADE, clear_height=CONCOURSE_H)),
        note="the Gravesend Arcade: E4M9's concourse, E6M1's shopfronts",
    )
    rooms: dict = {}

    def make(name, x0, y0, x1, y1, key, clear, note, *, role="interior",
             floor_z=GRADE, rk=None):
        material = INTERIORS[key]
        made = arcade.room(
            name, [(0, 0), (x1 - x0, 0), (x1 - x0, y1 - y0), (0, y1 - y0)],
            role=role, faces=dict(COMPASS), frame=Frame(int(x0), int(y0)),
            region_kwargs={**material.region_kwargs(), **(rk or {})},
            note=note)
        made.surfaces(**material.style_kwargs(floor_z=floor_z,
                                              clear_height=clear))
        rooms[name] = made
        return made

    for name, x0, y0, x1, y1, key, clear, note in ROOMS:
        # The service corridor's only exit is the keyed door, which is shut
        # at rest -- which is what "locked" means.  The geometry audit
        # rightly flags a room with no walkable-at-rest exit unless it is
        # DECLARED as gated, so declare it rather than weaken the lock.
        rk = {"declared_zero_exit": True} if name == "service" else {}
        if name == "concourse":
            # Hinge on the long west edge so the roof pitch reads along the
            # public route, not across individual shop fronts.
            rk["ceiling_slope"] = SlopeSpec(
                hinge=((x0, y1), (x0, y0)), rise_z=-CONCOURSE_PITCH)
        make(name, x0, y0, x1, y1, key, clear, note, rk=rk)

    # Each unit reaches the concourse through its own neck, so the frontage
    # beside it is free for glass.
    for unit, nx0, nx1, side in NECKS:
        y0, y1 = NORTH_BAND if side == "north" else SOUTH_BAND
        neck = make(f"{unit}_neck", nx0, y0, nx1, y1, "shop", UNIT_H,
                    f"{unit}'s opening onto the concourse", role="gateway")
        # A north-range unit sits north of the concourse, so its opening
        # joins the unit on its north face and the concourse on its south.
        inner, outer = ("north", "south") if side == "north" else ("south", "north")
        arcade.connect(neck.face(inner), rooms[unit].face(outer),
                       connection_id=f"connection:{unit}_neck_shop")
        arcade.connect(neck.face(outer), rooms["concourse"].face(side),
                       connection_id=f"connection:{unit}_neck_concourse")

    # Glazed display boxes: shop on one side, concourse on the other, which
    # is the two-sided wall breakable glass needs.
    for unit, wx0, wx1, side, plinth in WINDOWS:
        y0, y1 = NORTH_BAND if side == "north" else SOUTH_BAND
        box = make(f"{unit}_window", wx0, y0, wx1, y1, "shop",
                   UNIT_H - plinth, f"{unit}'s display window",
                   role="detail", floor_z=GRADE - plinth)
        inner, outer = ("north", "south") if side == "north" else ("south", "north")
        arcade.connect(box.face(inner), rooms[unit].face(outer),
                       connection_id=f"connection:{unit}_window_shop")
        arcade.connect(box.face(outer), rooms["concourse"].face(side),
                       connection_id=f"connection:{unit}_window_concourse")

    # **The units are furnished by a template, not left empty.**  Six retail
    # units with nothing in them is what "the buildings are still empty"
    # meant; `templates.shop` fits each one out from its own rect -- a shelf
    # run of pedestals down its long side, a counter across its front --
    # and each of those runs is itself a parametric fixture family.  This is
    # the composition chain: retail_row -> shop -> run -> fixture.
    fitted = []
    for _side, _units in RANGES.items():
        for _unit in _units:
            _name = _unit_name(_side, _unit.index)
            fitted.append(templates.shop(
                rooms[_name], material=INTERIORS["shop"], grade=GRADE,
                host_clear=UNIT_H, margin=384))
    rooms["_fitted"] = fitted

    # The street entrance: concourse -> door -> porch -> the market street.
    entry_y0, entry_y1 = 45568, 46592
    door = make("entry_door", 40192, entry_y0, 40448, entry_y1, "common", 0,
                "the arcade entrance", role="doorway",
                rk={"type": 600, "door_face": 22, "inherit_finish": "both",
                    "sector_behavior": z_motion_door(GRADE, GRADE - DOOR_H)})
    door.surfaces(wall_picnum=facade.opening, floor_z=GRADE, clear_height=0)
    porch = make("entry_porch", 39936, entry_y0, 40192, entry_y1, "common",
                 DOOR_H, "the arcade reveal", role="gateway")
    porch.surfaces(wall_picnum=facade.opening, ceiling_picnum=facade.opening,
                   floor_z=GRADE, clear_height=DOOR_H)
    arcade.connect(door.face("east"), rooms["concourse"].face("west"),
                   connection_id="connection:arcade_entry_in")
    arcade.connect(porch.face("east"), door.face("west"),
                   connection_id="connection:arcade_entry_porch")
    city.connect(porch.face("west"), market_st.face("north"),
                 connection_id="connection:arcade_entry_street")

    # The keyed service door.  A placard is only ever emitted beside a door
    # that really carries the key -- see keysign.py.
    key_door = make("service_door", 51712, entry_y0, 51968, entry_y1,
                    "service", 0, "the service door: needs the eye key",
                    role="doorway",
                    rk={"type": 600, "door_face": 22,
                        "inherit_finish": "both",
                        "sector_behavior": z_motion_door(
                            GRADE, GRADE - DOOR_H, key=SERVICE_KEY)})
    key_door.surfaces(wall_picnum=MASONRY.wall, floor_z=GRADE, clear_height=0)
    arcade.connect(key_door.face("west"), rooms["concourse"].face("east"),
                   connection_id="connection:arcade_service_in")
    arcade.connect(key_door.face("east"), rooms["service"].face("west"),
                   connection_id="connection:arcade_service_out")

    # The four hand-placed counters that used to sit here are gone: they
    # were four of six units furnished, each a literal rect derived from
    # its host's own origin.  `templates.shop` furnishes all six, from the
    # same counter family, at whatever size the unit turns out to be.
    return rooms


#: Where the placard hangs, and where the key it names can be found.
def dress(layout, rooms, attested) -> dict:
    import ambience
    import props

    report = {}
    # The placard, on the concourse wall beside the service door.
    concourse = rooms["concourse"]
    keysign.placard(layout, "keysign:arcade_service", concourse.region_id,
                    ((51712, 46592), (51712, 47360)), SERVICE_KEY)
    # And the key itself, in a unit, so the lock is not a wall.
    keysign.item(layout, "key:arcade_eye", rooms["unit_f"].region_id,
                 SERVICE_KEY, local=(0.15, 0.8))   # clear of the counter
    report["keyed_door"] = "eye"

    # E4M9's own ambience, in the concourse and the two ranges.
    # Through `ambience.fill`, which tests containment: a furnished unit is
    # a unit with holes in it, and the centre of one is now its counter.
    spots = [(concourse.region_id, "mall", (0.25, 0.5)),
             (concourse.region_id, "mall", (0.75, 0.5)),
             (rooms["unit_b"].region_id, "mall", (0.5, 0.5)),
             (rooms["unit_e"].region_id, "mall", (0.5, 0.5))]
    report["ambience"] = ambience.fill(layout, spots)["placed"]

    # Population and finds, attested as everywhere else.
    for index, (name, type_id, local) in enumerate(
            [("concourse", 202, (0.2, 0.4)), ("concourse", 203, (0.8, 0.6)),
             ("unit_a", 202, (0.5, 0.4)), ("unit_e", 203, (0.5, 0.85)),
             ("service", 202, (0.5, 0.5)),
             ("unit_c", 65, (0.4, 0.85)), ("unit_d", 62, (0.5, 0.85)),
             ("service", 109, (0.3, 0.6))]):
        spec = attested(type_id)
        if spec is None or name not in rooms:
            continue
        # The units are furnished by a template now, so where the fixtures
        # are depends on how big the unit came out.  A hand-written local
        # that used to be "clear of the counter" cannot know that any more;
        # asking the room is the only version that stays true.
        region_id = rooms[name].region_id
        free = props.free_local(layout.regions[region_id], local)
        if free is None:
            continue
        layout.place_on_floor(f"mall:{name}_{type_id}_{index}",
                              region_id, local=free, **spec["fields"])
    # A brazier at each end of the concourse: it is the city's longest room.
    for index, (face, t) in enumerate((("north", 0.08), ("south", 0.92))):
        props.mount_on_wall(layout, f"mall:brazier_{index}", concourse, face,
                            t=t)
    return report
