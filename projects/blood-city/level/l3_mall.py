"""The Gravesend Arcade: its street door, its service passage behind the eye door, and the secret in that.

The hall between them is `arcade`: rebuilt 2026-11-25 from the study `arcade`
(E4M9's atrium), because the row of six equal shops that stood here was the one
place in the city a blind reader could not name.

* **A key placard means a keyed door.** The service passage carries
  `XSECTOR.key`, and the eye emblem hangs beside it. The key is in the hall.
* **Ambience.** Sound 65 plays on five of E4M9's 11 ambient emitters and
  nowhere else in the campaign.
"""

from __future__ import annotations

import wires
from bloodmap import wiring

from bloodmap.doors import z_motion_door
from bloodmap.levelprog import Frame, RECT_FACES, Style
from bloodmap.slope import SlopeSpec

from materials import FACADES, INTERIORS, MASONRY, Material
from resolution import GRADE, PU

COMPASS = dict(zip(RECT_FACES, range(4)))

#: market_block_c, the biggest unbuilt block in the city.
MASS = (39 * PU, 40 * PU, 53 * PU, 50 * PU)

DOOR_H = 31744            # the campaign's median door opening
SERVICE_H = 24576

#: The key the service corridor needs.  2 is the eye; its placard is 2541
#: and its item is sprite type 101.
SERVICE_KEY = 2


def build(city, market_st):
    """The arcade, its units, its glazing and its locked service door."""
    facade = FACADES["market_slip"]
    arcade = city.assembly(
        "gravesend_arcade",
        style=Style(**INTERIORS["common"].style_kwargs(
            floor_z=GRADE, clear_height=65536)),
        note="the Gravesend Arcade, after E4M9's atrium (`arcade`)",
    )
    import citytree
    citytree.declare_venue(arcade, "arcade", "retail_row", built_by="l3_mall")
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

    # The service corridor's only exit is the keyed door, which is shut at
    # rest -- which is what "locked" means -- so it is DECLARED gated.
    make("service", 51968, 44544, 53760, 47616, "service", SERVICE_H,
         "the service corridor, behind the keyed door", rk={"declared_zero_exit": True})

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
    arcade.connect(key_door.face("east"), rooms["service"].face("west"),
                   connection_id="connection:arcade_service_out")

    # The extinguisher and what is behind it. The owner, 2026-11-18: "fire
    # extinguisher ... is usually thing that will explode and reveal hole
    # in the wall behind it, it is something that can possibly reveal
    # secret room for example in staff only part of arcades".
    #
    # Transcribed from E3M4 sprite 331 and E1M2 sprite 489 (the one whose
    # hole is a counted secret): the extinguisher is a kThingObjectGib that
    # a bullet breaks, its death sends its channel (actor.cpp:3513 ->
    # triggers.cpp:103), a closed Z-motion sector in the wall behind it
    # opens in a tenth of a second, and exploders on the same channel go
    # off staggered. None of the campaign's nine uses a gib WALL.
    cache = make("service_cache", *SECRET_CACHE, "service", SERVICE_H,
                 "the cache behind the service corridor's wall: a secret",
                 role="secret",
                 rk={"secret": True, "declared_zero_exit": True})
    # the hole the blast leaves: ragged, the way Blood's are (the owner,
    # 2026-11-22: "Blown out holes are usually using sloped floor and
    # ceiling and usually aren't regular"), blown from the corridor
    # (its near side, the north wall at y 44,544) through to the cache
    from bloodmap import breach
    x0, y0, x1, y1 = SECRET_SEAL
    wall = INTERIORS["service"]
    material = Material(wall=wall.wall, floor=wall.wall, ceiling=wall.wall, opening=wall.wall,
                        note="the blown wall: its own plaster and brick")
    for index, piece in enumerate(breach.lay(
            arcade, "service_seal", secret_pieces(), origin=(x1, y1), along=(-1, 0), through=(0, -1),
            near_floor=GRADE, region_kwargs=material.region_kwargs(), rx_id=SECRET_CHANNEL,
            note="the wall behind the extinguisher: blown open, once",
            surfaces=material.style_kwargs(floor_z=GRADE, clear_height=0))):
        rooms[piece.node_id] = piece
        wires.wire("arcade:cache").then(wiring.region(piece.region_id))
        LATE_TYPES[piece.region_id] = 600
        arcade.connect(piece.face("near"), rooms["service"].face("north"),
                       connection_id=f"connection:arcade_cache_blast_{index}")
        arcade.connect(piece.face("far"), cache.face("south"),
                       connection_id=f"connection:arcade_cache_in_{index}")

    def hall(layout, _room):
        import arcade as hall_of
        hall_of.build(layout, {"entry_door": door.region_id, "service_door": key_door.region_id})

    porch.raw("the arcade's hall: the gallery, the sunk court, the fallen span and three shops", hall)
    return rooms


#: The extinguisher's channel, the blast hole and the cache behind it.
SECRET_CHANNEL = wires.channel("arcade:cache")
#: the blown wall: 1,280 wide, the campaign's median blast hole (E3M4's
#: wall 2361 was 640, too narrow to leave a ragged hole a body walks
#: through), the cache's whole width, in four pieces
SECRET_SEAL = (52224, 44032, 53504, 44544)
SECRET_CACHE = (52224, 43008, 53504, 44032)
SECRET_HOLE = 20480                              # E3M4 s320: 18,432-26,624
#: its sills over the corridor's floor, and its ragged top under the
#: corridor's ceiling, or that ceiling's edge is all that shows of it
SECRET_SILL, SECRET_TOP = (256, 1536), SERVICE_H - 512
#: region id -> sector type, set by the build once the doors are framed
LATE_TYPES: dict = {}


def secret_pieces() -> list:
    """The blown wall's pieces, in its own frame (`bloodmap.breach.ragged`)."""
    from bloodmap import breach
    x0, y0, x1, y1 = SECRET_SEAL
    return breach.ragged(x1 - x0, y1 - y0, seed="arcade:service_seal", pieces=4,
                         sill=SECRET_SILL, top=SECRET_TOP)
#: E3M4 sprite 331, field for field
EXTINGUISHER = {"type": 416, "picnum": 658, "cstat": 464, "x_repeat": 40,
                "y_repeat": 40, "status": 4,
                "behavior": {"tx_id": SECRET_CHANNEL, "command": 1,
                             "trigger_on": 1, "trigger_off": 1,
                             "trigger_once": 1, "trigger_vector": 1,
                             "data_1": 5, "data_4": 314}}
#: E3M4 sprites 332-334: (local in the corridor, tenths of a second)
EXPLODERS = (((0.40, 0.06), 1), ((0.52, 0.10), 4), ((0.46, 0.14), 3))


def extinguisher_secret(layout, rooms) -> dict:
    """Hang the extinguisher on the seal and arm the charges behind it."""
    service = rooms["service"]
    x0, y0, x1, _y1 = 51968, 44544, 53760, 47616
    centre = (SECRET_SEAL[0] + SECRET_SEAL[2]) // 2
    layout.place_on_wall(
        "mall:service_extinguisher", service.region_id,
        a1=(x0, y0), a2=(x1, y0), t=(centre - x0) / (x1 - x0),
        height_player_heights=0.87, offset_player_widths=0.06,
        #: it hangs on the wall that opens, and goes with it
        spans_opening=True, **EXTINGUISHER)
    wires.wire("arcade:cache").when(
        wiring.placement("mall:service_extinguisher"), "vector", command=1,
        on=True, off=True, once=True)
    for index, (local, wait) in enumerate(EXPLODERS):
        layout.place_on_floor(
            f"mall:service_charge_{index}", service.region_id, local=local,
            type=459, picnum=908, cstat=128, x_repeat=4, y_repeat=64,
            status=11, behavior={"rx_id": SECRET_CHANNEL, "wait_time": wait})
        wires.wire("arcade:cache").then(
            wiring.placement(f"mall:service_charge_{index}"))
    return {"channel": SECRET_CHANNEL, "charges": len(EXPLODERS)}


def dress(layout, rooms, attested) -> dict:
    report = {}
    report["extinguisher_secret"] = extinguisher_secret(layout, rooms)
    for index, (type_id, local) in enumerate(((62, (0.3, 0.4)),
                                              (65, (0.7, 0.4)),
                                              (109, (0.5, 0.7)))):
        spec = attested(type_id)
        if spec is not None:
            layout.place_on_floor(f"mall:cache_{type_id}_{index}",
                                  rooms["service_cache"].region_id,
                                  local=local, **spec["fields"])
    report["keyed_door"] = "eye"
    import arcade as hall_of
    report["hall"] = hall_of.populate(layout, attested)
    for kind, local in ((202, (0.5, 0.5)), (109, (0.3, 0.6))):
        spec = attested(kind)
        if spec is not None:
            layout.place_on_floor(f"mall:service_{kind}", rooms["service"].region_id, local=local, **spec["fields"])
    return report
