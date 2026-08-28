"""St Gallow's: the parish church, Gravesend's mandatory landmark.

Built to the contract in `references/church-patterns.md`, which mined E1M5
(Blood's own church, at whole-map scale) and E1M1 (its cemetery and crypt):
nave with an aisle, a raised chancel, an apse, a tower on the vista, a
vestry, and a stair down toward the crypt -- the monastery chapel grammar
at city dose.

The church stands in the void of `church_mass`, which the cemetery ground
excludes as a solid and which fronts the avenue directly: the street's
east boundary wall at x = 32 plan units *is* this building's face.  So it
has two entrances, which is what the landmark-complex type asks for -- the
portal on the avenue, and a side door onto the cemetery ground.

It is also this project's answer to a measured fault.  Gravesend's roofed
sectors run q3 8.39 Mu^2 against E3M1's 1.13, with 23% of them over 10M
against E3M1's 2%: we build halls where the campaign builds warrens, and
that single fact drives the level's ceiling share, its dead-end fraction
and its missing loops.  Eight rooms in six by ten plan units, braided so
that the nave touches five of them, is the shape the measurement asks for.
"""

from __future__ import annotations

from bloodmap.doors import xsector_direct_use, z_motion_endpoints
from bloodmap.levelprog import Frame, RECT_FACES, Style

import setpieces
from materials import FACADES, INTERIORS, MASONRY
from resolution import GRADE, PU

COMPASS = dict(zip(RECT_FACES, range(4)))

#: The mass, and the margin rooms keep from its faces so that a door and
#: its porch have somewhere to be.
MASS = (26 * PU, 21 * PU, 32 * PU, 31 * PU)
DOOR_D = PORCH_D = 256
# Campaign z-motion doors open to a median of 31,744 -- 1.87 player
# heights, measured over 1,269 of them; even their 10th percentile is
# 17,408.  Ours were 16,384, which is 0.97 of a player height: the owner
# called them "short like for midgets" and the census agrees.  Blood has
# no door TEXTURE to lean on (E3M1's own door leaves wear 379 and 449,
# plain wall stone), so an opening reads as a door through its proportion
# and its reveal -- which makes this number the whole fix.
DOOR_H = 31744

CHANCEL_RISE = 2048        # the chancel stands over the nave, one low step

#: (name, x0, y0, x1, y1, material, clear height, note)
#:
#: The tower is 98,304 -- 5.8 player heights, the tallest interior in the
#: city and half again the nave.  church-patterns asks for the bell tower
#: as the silhouette element on the avenue vista opposite the Aldermack,
#: and a tower you cannot tell from a room is not one.
ROOMS = [
    ("apse", 28672, 22016, 30208, 22528, "sanctuary", 40960,
     "the apse behind the altar"),
    ("chancel", 28160, 22528, 30720, 24064, "sanctuary", 49152,
     "the chancel, raised over the nave"),
    ("tower", 30720, 22528, 32256, 24064, "church", 98304,
     "the bell tower: the city's tallest interior"),
    ("nave", 28160, 24064, 30720, 30720, "church", 65536,
     "the nave, four repeats tall"),
    ("west_aisle", 27136, 24064, 28160, 30720, "church", 32768,
     "the aisle, low beside the nave so the nave reads tall"),
    ("vestry", 30720, 24576, 32256, 25600, "church", 32768,
     "the vestry"),
    ("crypt_stair", 30720, 25600, 32256, 27136, "crypt", 32768,
     "the head of the crypt stair"),
    ("narthex", 30720, 27136, 32256, 30208, "church", 40960,
     "the narthex, behind the avenue portal"),
]

#: (small room, its face, big room, its face).  Anchored from the smaller
#: face; equal faces either way round.
JOINS = [
    ("apse", "south", "chancel", "north"),
    ("chancel", "south", "nave", "north"),
    ("tower", "west", "chancel", "east"),
    ("west_aisle", "east", "nave", "west"),
    ("vestry", "west", "nave", "east"),
    ("crypt_stair", "west", "nave", "east"),
    ("narthex", "west", "nave", "east"),
    ("vestry", "south", "crypt_stair", "north"),
    ("crypt_stair", "south", "narthex", "north"),
]

#: The two portals: (name, room, face, span start, span end).  Both land on
#: the 1024 bay grid, both get the porch reveal that stops Build drawing
#: the whole facade above the opening from the door tile.
#: The avenue portal is two bays, not one: a church door the size of a
#: shop door is a service entrance.  The cemetery door stays at one bay,
#: because the ground only touches this face for three plan units and two
#: bays would run past it into the mausoleum row.
PORTALS = [
    ("avenue", "narthex", "east", 27648, 29696),
    ("cemetery", "west_aisle", "west", 28672, 29696),
]

#: Furniture, all of it geometry: (room, x0, y0, x1, y1, rise, note).
FURNITURE = [
    # One bench block per row across the middle of the nave, leaving a
    # 512-unit side aisle against each wall.  Six half-width pews touching
    # the walls left nowhere to bracket a light: the first wall-mounted
    # brazier landed inside a pew.
    ("nave", 28672, 25088, 30208, 25600, 5120, "a pew"),
    ("nave", 28672, 26112, 30208, 26624, 5120, "a pew"),
    ("nave", 28672, 27136, 30208, 27648, 5120, "a pew"),
    ("nave", 28672, 28160, 30208, 28672, 5120, "a pew"),
    ("narthex", 30976, 29184, 32000, 29696, 4096, "the font"),
]


def build(city, street, ground, gates):
    """The church, its portals, and the connections that carry them."""
    facade = FACADES["old_crossing"]
    parish = city.assembly(
        "st_gallows",
        style=Style(**INTERIORS["church"].style_kwargs(
            floor_z=GRADE, clear_height=65536, floor_shade=28)),
        note="St Gallow's: nave, chancel, apse, tower, vestry, narthex",
    )
    rooms: dict = {}

    def make(name, x0, y0, x1, y1, key, clear, note, *, role="interior",
             floor_z=GRADE, rk=None, shade=28):
        material = INTERIORS[key]
        made = parish.room(
            name, [(0, 0), (x1 - x0, 0), (x1 - x0, y1 - y0), (0, y1 - y0)],
            role=role, faces=dict(COMPASS), frame=Frame(int(x0), int(y0)),
            region_kwargs={**material.region_kwargs(), **(rk or {})},
            note=note)
        made.surfaces(**material.style_kwargs(floor_z=floor_z,
                                              clear_height=clear,
                                              floor_shade=shade))
        rooms[name] = made
        return made

    for name, x0, y0, x1, y1, key, clear, note in ROOMS:
        # The chancel and its apse stand a step over the nave: the one
        # height difference in a church that means something.
        rise = CHANCEL_RISE if name in ("chancel", "apse") else 0
        make(name, x0, y0, x1, y1, key, clear - rise, note,
             floor_z=GRADE - rise)
    for small, sf, big, bf in JOINS:
        parish.connect(rooms[small].face(sf), rooms[big].face(bf),
                       connection_id=f"connection:church_{small}_{big}")

    material_of = {row[0]: row[5] for row in ROOMS}
    for name, room_name, face, span0, span1 in PORTALS:
        host = rooms[room_name]
        hx0, hy0, hx1, hy1 = next((r[1], r[2], r[3], r[4]) for r in ROOMS
                                  if r[0] == room_name)
        inner = {"east": "west", "west": "east"}[face]
        if face == "east":
            door_x0, door_x1 = hx1, hx1 + DOOR_D
            porch_x0, porch_x1 = hx1 + DOOR_D, hx1 + DOOR_D + PORCH_D
        else:
            door_x0, door_x1 = hx0 - DOOR_D, hx0
            porch_x0, porch_x1 = hx0 - DOOR_D - PORCH_D, hx0 - DOOR_D
        door = make(f"{name}_door", door_x0, span0, door_x1, span1,
                    "church", 0, f"the {name} portal", role="doorway",
                    rk={"type": 600, "door_face": 390,
                        "inherit_finish": "both",
                        "sector_behavior": {
                            **z_motion_endpoints(GRADE, GRADE - DOOR_H),
                            **xsector_direct_use()}})
        porch = make(f"{name}_porch", porch_x0, span0, porch_x1, span1,
                     "church", DOOR_H, f"the {name} reveal", role="gateway")
        door.surfaces(wall_picnum=facade.opening, floor_z=GRADE,
                      clear_height=0)
        porch.surfaces(wall_picnum=facade.opening,
                       ceiling_picnum=facade.opening,
                       floor_z=GRADE, clear_height=DOOR_H)
        parish.connect(door.face(inner), host.face(face),
                       connection_id=f"connection:church_{name}_in")
        parish.connect(porch.face(inner), door.face(face),
                       connection_id=f"connection:church_{name}_porch")
        if name == "avenue":
            city.connect(porch.face(face), street.face("north"),
                         connection_id="connection:church_avenue_street")
        else:
            # The cemetery ground is a notched outline with no compass
            # faces -- the same reason its gates use raw span connections.
            edge_x = porch_x0
            gates.append(("connection:church_cemetery_ground",
                          porch.region_id, ground.region_id,
                          (edge_x, span0), (edge_x, span1)))

    # The altar, through the two-tier constructor: class of 42 pieces
    # across 16 maps, rise 0.60-0.97 player heights.  It was a single block
    # at 4,096 -- a quarter of a player -- which is a doorstep, not an altar.
    setpieces.altar(parish, "altar", rooms["chancel"],
                    (28928, 22784, 30208, 23808),
                    INTERIORS["sanctuary"], grade=GRADE - CHANCEL_RISE,
                    host_clear=49152 - CHANCEL_RISE,
                    note="the altar, from the mined two-tier class")

    for index, (room_name, x0, y0, x1, y1, rise, note) in enumerate(FURNITURE):
        host = rooms[room_name]
        hf = host.world_frame()
        host.carve([(x0 - hf.dx, y0 - hf.dy), (x1 - hf.dx, y0 - hf.dy),
                    (x1 - hf.dx, y1 - hf.dy), (x0 - hf.dx, y1 - hf.dy)])
        host_clear = next(r[6] for r in ROOMS if r[0] == room_name)
        host_rise = CHANCEL_RISE if room_name in ("chancel", "apse") else 0
        piece = make(f"church_furniture_{index}", x0, y0, x1, y1,
                     material_of[room_name], host_clear - host_rise - rise,
                     note, role="detail", floor_z=GRADE - host_rise - rise)
        for face in ("north", "east", "south", "west"):
            parish.connect(piece.face(face), host.face("north"),
                           connection_id=f"connection:church_fur_{index}_{face}")
    return rooms


#: The parish's own register.  E1M5 is the most flicker-dense and
#: sprite-dressed interior in the corpus -- candlelight is the church's
#: language -- so braziers line the nave and the chancel.  Each is
#: bracketed to a named wall at the height the campaign brackets it
#: (props.CATALOGUE), not floated in the middle of the floor.
#: Only **3%** of campaign rooms contain a light-emitting prop: Blood lights
#: a room with sector shade, not with lamp sprites.  We had one per room.
#: These are one per venue -- the light you actually navigate by -- and the
#: rest of the brightness comes from the shade passes.
#: The church is the one justified exception: E1M5, Blood's own church, is
#: the most flicker-dense interior in the corpus -- candlelight is what the
#: room is FOR.  Four, not thirteen.
LIT = [("nave", "south", 0.35), ("chancel", "west", 0.5)]

POPULATION = [("nave", 202, (0.5, 0.75)), ("west_aisle", 203, (0.5, 0.45)),
              ("crypt_stair", 203, (0.3, 0.5)), ("tower", 202, (0.35, 0.6))]
PICKUPS = [("vestry", 109, (0.35, 0.5)), ("apse", 67, (0.5, 0.35)),
           ("tower", 62, (0.7, 0.3))]


def populate(layout, rooms, attested, flame_fields, flame_stand) -> int:
    import props
    placed = 0
    for name, type_id, local in POPULATION + PICKUPS:
        spec = attested(type_id)
        if spec is None or name not in rooms:
            continue
        layout.place_on_floor(f"church:{name}_{type_id}", rooms[name].region_id,
                              local=local, **spec["fields"])
        placed += 1
    for index, (name, face, t) in enumerate(LIT):
        if name not in rooms:
            continue
        props.mount_on_wall(layout, f"church:brazier_{index}",
                            rooms[name], face, t=t)
        placed += 1
    return placed
