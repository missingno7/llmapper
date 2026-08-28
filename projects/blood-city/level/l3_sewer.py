"""The sewer network proper: a ring, its branches, and places to go.

The parked network was a trunk with three chambers hanging off it -- enough
to prove the stack links, nowhere near the contract.  sewer-patterns.md
asks for a network with its own topology (internal cycle rank 7+, denser
than the street's), a wet share of 0.2-0.4 measured against E3M3, and a
secret branch.

Three things from E3M3 shape what gets built, not just how much:

* its **cross-section** is a ledge beside a channel -- 62 ledge-over-channel
  pairs, the walk one max step (4096) above the water;
* it is **wet**: 29% of its sectors, against DukCity's dry 0-2%;
* it is **lightly wired but restless**: 23 user channels, yet 175 of its 309
  sectors animate their shade.

Geometry rule that keeps the compiler happy, learned the hard way in this
project: two rooms may share an edge only if one face is *exactly* the
other, or *strictly inside* it, and the connection must be anchored from
the smaller face.  Tunnel segments are laid end to end with matching faces;
anything meeting a tunnel mid-run does so through a neck.
"""

from __future__ import annotations

from bloodmap.levelprog import Frame, RECT_FACES, Style

from materials import SEWER, SEWER_WET
from resolution import PU, SEWER_CHAMBER_CLEAR, SEWER_CLEAR, SEWER_FLOOR

COMPASS = dict(zip(RECT_FACES, range(4)))

#: The walk sits one max step above its channel (E3M3's median step).
LEDGE_STEP = 4096
#: E3M3's shallow-water form, the one that reads wet in our own frames.
WATER_DEPTH = 7

#: The ring, in the parked network's own plan units.  Corner-leg-corner-leg
#: all the way round, faces matching exactly at every join.  The north and
#: south legs are split lengthwise into a walk and a channel: that is the
#: cross-section, not decoration.
RING = [
    ("nw_corner", 32.0, 6.0, 34.0, 8.0),
    ("n_walk", 34.0, 6.0, 51.0, 7.0),
    ("n_channel", 34.0, 7.0, 51.0, 8.0),
    ("ne_corner", 51.0, 6.0, 53.0, 8.0),
    ("e_leg", 51.0, 8.0, 53.0, 32.0),
    ("se_corner", 51.0, 32.0, 53.0, 34.0),
    ("s_channel", 34.0, 32.0, 51.0, 33.0),
    ("s_walk", 34.0, 33.0, 51.0, 34.0),
    ("sw_corner", 32.0, 32.0, 34.0, 34.0),
    ("w_leg", 32.0, 8.0, 34.0, 32.0),
]

#: Ring joins, each anchored from the smaller face.
RING_JOINS = [
    ("n_walk", "west", "nw_corner", "east"),
    ("n_channel", "west", "nw_corner", "east"),
    ("n_walk", "east", "ne_corner", "west"),
    ("n_channel", "east", "ne_corner", "west"),
    ("n_walk", "south", "n_channel", "north"),
    ("ne_corner", "south", "e_leg", "north"),
    ("e_leg", "south", "se_corner", "north"),
    ("s_walk", "east", "se_corner", "west"),
    ("s_channel", "east", "se_corner", "west"),
    ("s_channel", "south", "s_walk", "north"),
    ("s_walk", "west", "sw_corner", "east"),
    ("s_channel", "west", "sw_corner", "east"),
    ("sw_corner", "north", "w_leg", "south"),
    ("w_leg", "north", "nw_corner", "south"),
]

#: Places to go, hanging off the ring: (name, rect, own face, leg, leg face).
CHAMBERS = [
    ("pump_room", 27.0, 12.0, 32.0, 18.0, "east", "w_leg", "west",
     "the pumping chamber: the network's one big room"),
    ("silt_trap", 46.0, 2.0, 50.0, 6.0, "south", "n_walk", "north",
     "a silt trap off the north walk"),
    ("east_annex", 53.0, 14.0, 57.0, 20.0, "west", "e_leg", "east",
     "the annex: an eastern dead end worth the walk for what is in it"),
    ("flooded", 40.0, 34.0, 46.0, 39.0, "north", "s_walk", "south",
     "the flooded branch, waist-deep"),
    ("station_foot", 43.5, 4.0, 45.5, 6.0, "south", "n_walk", "north",
     "the foot of the pumping station's shaft: where the stairs deliver "
     "you, and the way back up"),
]

#: Necks joining the ring to the network that already existed.
NECKS = [
    ("west_adit", 34.0, 11.0, 39.25, 13.0,
     [("west", "w_leg", "east"), ("east", "junction", "west")],
     "the west adit: the ring's way into the junction"),
    ("neck_cistern", 44.0, 31.0, 46.0, 32.0,
     [("north", "cistern", "south"), ("south", "s_channel", "north")],
     "the cistern's overflow into the ring"),
]


def expand(city, sewer, existing: dict) -> dict:
    """Build the ring, its chambers and the necks onto the parked network."""
    rooms: dict = {}

    #: The chambers stand taller than the runs, as E3M3's do: a network
    #: whose every sector is the same height reads as extruded plan, and it
    #: is the tunnels' flat low ceiling that fills our frames.
    chambers = {name for name, *_rest in CHAMBERS}

    def room(name, x0, y0, x1, y1, *, wet=False, note="", role="interior",
             animate=True):
        material = SEWER_WET if wet else SEWER
        # E3M3 animates 57% of its sectors; animating every plain leg put us
        # at 79%, so the restless light goes to the water and the chambers.
        behavior = {"amplitude": -16, "shade_frequency": 9} if animate else {}
        if wet:
            behavior["depth"] = WATER_DEPTH
        made = sewer.room(
            name,
            [(0, 0), (int((x1 - x0) * PU), 0),
             (int((x1 - x0) * PU), int((y1 - y0) * PU)),
             (0, int((y1 - y0) * PU))],
            role=role, faces=dict(COMPASS),
            frame=Frame(int(x0 * PU), int(y0 * PU)),
            region_kwargs={**material.region_kwargs(),
                           "sector_behavior": behavior},
            note=note)
        clear = SEWER_CHAMBER_CLEAR if name in chambers else SEWER_CLEAR
        made.surfaces(**material.style_kwargs(
            floor_z=SEWER_FLOOR + (LEDGE_STEP if wet else 0),
            clear_height=clear + (LEDGE_STEP if wet else 0),
            floor_shade=38 if wet else 40))
        rooms[name] = made
        return made

    for name, x0, y0, x1, y1 in RING:
        room(name, x0, y0, x1, y1, wet=name.endswith("channel"),
             animate=name.endswith(("channel", "corner")),
             note=f"sewer ring: {name.replace('_', ' ')}")
    for a, fa, b, fb in RING_JOINS:
        sewer.connect(rooms[a].face(fa), rooms[b].face(fb),
                      connection_id=f"connection:ring_{a}_{fa}_{b}")

    for name, x0, y0, x1, y1, own, leg, leg_face, note in CHAMBERS:
        made = room(name, x0, y0, x1, y1, wet=(name == "flooded"), note=note,
                    role="secret" if name == "flooded" else "interior")
        if name == "flooded":
            # SP's secret branch: `secret=True` emits the campaign's own
            # wiring rather than a label (channel 2, command 64, once).
            made.region_kwargs["secret"] = True
        sewer.connect(made.face(own), rooms[leg].face(leg_face),
                      connection_id=f"connection:sewer_{name}")

    for name, x0, y0, x1, y1, joins, note in NECKS:
        made = room(name, x0, y0, x1, y1, note=note, role="gateway")
        for own_face, other, other_face in joins:
            target = rooms.get(other) or existing[other]
            sewer.connect(made.face(own_face), target.face(other_face),
                          connection_id=f"connection:{name}_{own_face}")
    return rooms


#: What lives down here, from E3M3's own census: bone eels (17), rats (9),
#: gill beasts (7) -- water dwellers and scavengers, no cultist garrison.
POPULATION = [
    ("pump_room", 220, (0.3, 0.4)),      # rat
    ("pump_room", 220, (0.7, 0.6)),
    ("n_walk", 220, (0.2, 0.5)),
    ("east_annex", 217, (0.5, 0.5)),     # gill beast, guarding the annex
    ("flooded", 218, (0.5, 0.4)),        # bone eel, in the water
    ("s_walk", 220, (0.7, 0.5)),
]

#: Something to find at the end of each walk, so a branch is worth taking.
PICKUPS = [
    ("east_annex", 62, (0.35, 0.5)),
    ("silt_trap", 65, (0.5, 0.5)),
    ("flooded", 60, (0.7, 0.6)),
    ("pump_room", 109, (0.5, 0.75)),
]

#: A brazier at the chambers and the ring's corners, BRACKETED TO A WALL:
#: (room, face, t).  E3M3 is dark but not unlit, and our animated shade
#: needs a source to justify it.
#: The sewer keeps its corner lights: it is a dark ring with four
#: identical turns, and they are the only thing that tells one from
#: another.  Recorded as a deliberate deviation from the 3% rate.
LIT = [("pump_room", "north", 0.5), ("nw_corner", "north", 0.5),
       ("ne_corner", "east", 0.5), ("se_corner", "south", 0.5),
       ("sw_corner", "west", 0.5), ("station_foot", "north", 0.5)]

#: Every rectangle in this module, in plan units, so a bracket can find a
#: wall to hang on.
def _rects():
    out = {}
    for name, x0, y0, x1, y1 in RING:
        out[name] = (x0 * PU, y0 * PU, x1 * PU, y1 * PU)
    for name, x0, y0, x1, y1, *_rest in CHAMBERS:
        out[name] = (x0 * PU, y0 * PU, x1 * PU, y1 * PU)
    for name, x0, y0, x1, y1, *_rest in NECKS:
        out[name] = (x0 * PU, y0 * PU, x1 * PU, y1 * PU)
    return out


def populate(layout, rooms, attested, flame_fields,
             flame_stand: float = 0.33) -> list[str]:
    """Put the register, the finds and the braziers into the new network."""
    import props
    placed = []
    for name, type_id, local in POPULATION:
        spec = attested(type_id)
        if spec is None or name not in rooms:
            continue
        layout.place_on_floor(f"sewer:dude_{name}_{type_id}",
                              rooms[name].region_id, local=local,
                              **spec["fields"])
        placed.append(name)
    for index, (name, type_id, local) in enumerate(PICKUPS):
        spec = attested(type_id)
        if spec is None or name not in rooms:
            continue
        layout.place_on_floor(f"sewer:item_{index}", rooms[name].region_id,
                              local=local, **spec["fields"])
    for index, (name, face, t) in enumerate(LIT):
        if name not in rooms:
            continue
        props.mount_on_wall(layout, f"sewer:brazier_{index}",
                            rooms[name], face, t=t)
    # Water dressing belongs in water: fronds and bubbles go in the wet
    # channels and the flooded branch only.  Down a dry brick tunnel they
    # are the "underwater plant / underwater bubbling" the owner spotted.
    for index, (name, tile, local) in enumerate(
            [("n_channel", 668, (0.3, 0.5)), ("n_channel", 660, (0.7, 0.5)),
             ("s_channel", 668, (0.6, 0.5)), ("s_channel", 664, (0.25, 0.5)),
             ("flooded", 660, (0.35, 0.4)), ("flooded", 668, (0.7, 0.6))]):
        if name not in rooms:
            continue
        props.stand_on_floor(layout, f"sewer:water_{index}",
                             rooms[name].region_id, local=local, tile=tile)
    return placed
