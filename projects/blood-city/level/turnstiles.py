"""Turnstiles at a public threshold, cut into the street the way a pool is.

The mechanism is `bloodmap.mechanism`'s, mined from E1M4 151/314 and DWE1M9
61/64: kSectorRotateMarked on the `level_start` broadcast, both waves
retriggering so one message spins it for ever, a kMarkerAxis at the pivot, and
four blade sprites that span the rotor from floor to ceiling. None of that is
restated here -- `turnstile_spec` hands it over, so there is one copy of it.

What belongs to the city is *where*: the Aldermack forecourt's mouth on Theatre
Row is 6,144 units wide, which is exactly a counter-rotating pair with a gap
between them, and a forecourt is the nearest thing Gravesend has to E1M4's
carnival entry.

**The mouth is deliberately not sealed.** A turnstile is passable machinery and
E1M4's really is the way in, but nothing here has proved a player can walk
through one at the mined spin rate -- the bot is not reliable yet and no oracle
walks a body through a moving aperture. The forecourt carries the objective, so
until passage is proven the rotors stand in an open mouth and the route around
them stays walkable. Sealing it afterwards is deleting one argument.
"""

from __future__ import annotations

from bloodmap.levelprog import Frame, RECT_FACES
from bloodmap.mechanism import turnstile_spec

COMPASS = dict(zip(RECT_FACES, range(4)))

#: All four mined rotors are 32768 clear, which is 64 blade tiles at y_repeat
#: 64. The opening was sized to the blade, so this is not a free choice.
ROTOR_CLEAR = 32768

#: A rotor is two plan units square: wide enough for a body between the blades
#: and small enough that a pair plus its gap is the 6,144 the mouth offers.
ROTOR = 2048
GAP = 2048

#: E1M4's own spin period. Death Wish runs 100; both are in the template.
PERIOD = 255


def pair(district, street_room, name: str, *, centre_x: int, y: int,
         floor_z: int, wall_picnum: int, floor_picnum: int,
         ceiling_picnum: int, period: int = PERIOD,
         rotor: int = ROTOR, gap: int = GAP) -> list:
    """Two counter-rotating rotors astride `centre_x`, cut into `street_room`.

    Both maps that build turnstile doors build them as a mirrored pair, so
    that is the default; the same-direction DNE3L6 arrangement is reachable
    through `bloodmap.mechanism` and is not offered here.
    """
    import citytree

    frame = street_room.world_frame()
    half = rotor // 2
    built = []
    for index, (side, clockwise) in enumerate((("west", True), ("east", False))):
        offset = -(gap // 2 + rotor) if side == "west" else gap // 2
        x0 = centre_x + offset
        y0 = y - half
        # Wound the way a hole's counterpart has to be: the pools get away
        # with either because a diamond never lies along the street's own
        # edges, and an axis-aligned square does.
        outline = [(0, 0), (0, rotor), (rotor, rotor), (rotor, 0)]
        world = [(x0 + px, y0 + py) for px, py in outline]
        # A hole runs opposite to the room it is cut in, or the two edges
        # coincide in the same direction and no portal pairs. The light
        # pools get away with the same winding because a diamond never
        # lies along the street's own edges; an axis-aligned square does.
        street_room.carve([(px - frame.dx, py - frame.dy) for px, py in world])

        spec = turnstile_spec(period=period, floor_z=floor_z,
                              ceiling_z=floor_z - ROTOR_CLEAR,
                              clockwise=clockwise)
        room = citytree.make_room(
            street_room, f"turnstile_{name}_{side}", outline,
            role="detail", faces=dict(COMPASS),
            frame=Frame(x0 - frame.dx, y0 - frame.dy, -frame.dz),
            region_kwargs={"type": spec["sector_type"],
                           "sector_behavior": spec["behavior"]},
            intent={"turnstile": f"{name}:{side}",
                    "template": spec["template"],
                    "passage_unproven": True},
            note=f"turnstile rotor: {name} {side}, "
                 f"busy {spec['behavior']['busy_time_a']}/"
                 f"{spec['behavior']['busy_time_b']}")
        room.surfaces(wall_picnum=wall_picnum, floor_picnum=floor_picnum,
                      ceiling_picnum=ceiling_picnum, floor_z=floor_z,
                      clear_height=ROTOR_CLEAR)

        # Every edge is a portal: the rotor is a way through, and the two
        # side edges keep the open mouth open while passage is unproven.
        for face in RECT_FACES:
            district.connect(room.face(face), street_room.face("north"),
                             connection_id=f"connection:turnstile_{name}_{side}_{face}")

        built.append({"region_id": room.region_id, "room": room, "side": side,
                      "pivot": (x0 + half, y0 + half), "spec": spec,
                      "name": f"{name}_{side}"})
    return built


def populate(layout, built: list, *, player_height: int = 16960) -> dict:
    """Put the axis marker and the blades in, once the layout exists.

    Sprites are placed on the compiled layout rather than on the program, the
    way every other fixture in this project is, so a rotor is carved in one
    phase and furnished in the next.
    """
    placed = {"axes": 0, "blades": 0}
    for rotor in built:
        spec, region = rotor["spec"], rotor["region_id"]
        axis = dict(spec["axis"])
        axis_z = axis.pop("z")
        layout.place_on_floor(
            f"placement:{rotor['name']}:axis", region, local=(0.5, 0.5),
            height_player_heights=0.0, **axis)
        placed["axes"] += 1
        px, py = rotor["pivot"]
        for index, blade in enumerate(spec["blades"]):
            fields = dict(blade)
            z = fields.pop("z")
            dx, dy = fields.pop("dx"), fields.pop("dy")
            # A blade radiates from the axis; placing them all at the pivot
            # stacks four sprites in one spot, which is what the first build
            # did. Absolute coordinates, because the offset is in world units.
            layout.add_sprite(
                f"placement:{rotor['name']}:blade:{index}", region,
                x=px + dx, y=py + dy, z=z, **fields)
            placed["blades"] += 1
    return placed


