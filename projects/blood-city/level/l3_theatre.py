"""Theatre Row's venues: the Aldermack, the saloon, the parlor, the pawn shop.

The four slots L1 reserved on the Aldermack superblock, built to the
anatomies venue-patterns.md measured:

* **landmark complex** -- a braid of rooms sharing one shell, no single
  room dominating (E3M1's complex runs a main-room share of 0.12-0.21),
  fronting more than one street: the foyer opens on the forecourt and a
  lobby opens on the avenue.
* **bar** -- counter and tables are *geometry*, not sprites: E3M1's saloon
  has its counter at rise 4096 and four identical table platforms at rise
  8192, with stools and bottles as face sprites.
* **walk-through** -- a deep plan behind a narrow mouth; the mouth
  undersells the inside, which is the whole trick of the type.
* **open-front shop** -- 512-square display pedestals at rise 2048 (the
  E6M1 module), merchandise as face sprites.

Everything lives in the superblock's void, so nothing here is carved out of
the street; the four street doors each get the porch reveal the facade
needs and land on the 1024 bay grid.
"""

from __future__ import annotations

from bloodmap.doors import z_motion_door
from bloodmap.levelprog import Frame, RECT_FACES, Style
from bloodmap.slope import SlopeSpec

import fixtures
import setpieces
import templates
from materials import FACADES, INTERIORS, MASONRY
from resolution import GRADE, PU, STREET_SKY

COMPASS = dict(zip(RECT_FACES, range(4)))

ROOM_H = 32768            # the campaign's median room height
# Campaign z-motion doors open to a median of 31,744 -- 1.87 player
# heights, measured over 1,269 of them; even their 10th percentile is
# 17,408.  Ours were 16,384, which is 0.97 of a player height: the owner
# called them "short like for midgets" and the census agrees.  Blood has
# no door TEXTURE to lean on (E3M1's own door leaves wear 379 and 449,
# plain wall stone), so an opening reads as a door through its proportion
# and its reveal -- which makes this number the whole fix.
DOOR_H = 31744
DOOR_D = PORCH_D = 256    # the reveal chain, inside the mass
# Replaced by the mined set-piece class.  `tools/mine_set_pieces.py` finds
# 363 raised blocks across 38 campaign maps and they agree on their height:
# rise median **0.48 player heights = 8,140 units**, p10 0.30.  Ours were
# 4,096 -- half a Blood counter -- which is why the bar and the card tables
# rendered as low platforms rather than as furniture.
COUNTER_RISE = setpieces.COUNTER      # 8140
TABLE_RISE = setpieces.COUNTER        # a table is the same class as a counter
PEDESTAL_RISE = setpieces.LOW_STEP    # 4070, the shallow-tier class
STAGE_RISE = 4096         # one max step: the player can get up on it
STAGE_CLEAR = 24576       # low, so the wall over the stage front is an arch
# A shallow roof pitch gives the largest interior a readable volume without
# compromising the already generous 2.9-player-height headroom.
AUDITORIUM_PITCH = 8192

#: The superblock's south face (on Theatre Row street) and east face (on
#: the avenue); the forecourt's north edge is where the Aldermack fronts.
#: Rooms stop 512 short of these, because the door and its porch occupy
#: that strip -- a room flush with the face contains its own doorway.
SOUTH_FACE, EAST_FACE, FORECOURT_EDGE = 15360, 32768, 11264

#: (name, x0, y0, x1, y1, material, note)
#:
#: Each venue takes its own INTERIORS entry, and its own height.  The first
#: build gave all four the "common" palette and one ceiling height, and the
#: frames came back as the same brown box four times: the saloon, the
#: shooting gallery and the city's landmark theatre were indistinguishable
#: from inside.  A campaign town puts a different palette in every building
#: (E3M1: 20 across 337 interior sectors) -- see materials.INTERIORS.
ROOMS = [
    # --- the saloon -----------------------------------------------------
    ("saloon_main", 4096, 8192, 10240, 13312, "saloon",
     "the saloon: counter and tables are geometry"),
    ("saloon_back", 4096, 6144, 7168, 8192, "saloon", "the saloon's back room"),
    ("saloon_passage", 6144, 13312, 7168, 14848, "saloon",
     "the saloon's entry passage"),
    # --- the shooting parlor --------------------------------------------
    ("parlor_gallery", 11264, 9216, 16384, 13312, "parlor",
     "the parlor's gallery, behind a one-bay mouth"),
    ("parlor_range", 11264, 6144, 16384, 9216, "parlor",
     "the range: the deep half the mouth does not show"),
    ("parlor_passage", 13312, 13312, 14336, 14848, "parlor",
     "the parlor's entry passage"),
    # --- the Aldermack ---------------------------------------------------
    ("aldermack_auditorium", 19456, 4096, 26624, 11264, "theatre",
     "the auditorium: the house, under the city's tallest interior"),
    ("aldermack_backstage", 17408, 4096, 19456, 11264, "service",
     "the backstage corridor"),
    ("aldermack_dressing", 17408, 11264, 19456, 14336, "service",
     "the dressing room"),
    ("aldermack_foyer", 26624, 6656, 30720, 10752, "theatre",
     "the foyer, opening on the forecourt"),
    ("aldermack_lobby", 30720, 7680, 32256, 9728, "theatre",
     "the avenue lobby: the complex's second front"),
    # --- the back-of-house circuit ---------------------------------------
    # Four venues hanging off one street is four dead-end trees, and the
    # discriminator reads it: dead_end_fraction 0.333 against a campaign
    # 0.159, mean_degree 2.18 against 2.74, loops per 100 sectors 9.6
    # against 37.7.  A campaign block is a web.  These two corridors run
    # through the void the venues left between them and close the circuit:
    # street -> saloon -> passage -> parlor -> street, and parlor ->
    # backstage -> the Aldermack.
    ("back_passage_west", 7168, 6656, 11264, 7680, "service",
     "the corridor behind the saloon and the parlor"),
    ("back_passage_east", 16384, 7168, 17408, 8192, "service",
     "the parlor's way through to the Aldermack's backstage"),
    # --- the pawn shop ---------------------------------------------------
    # Widened west over the foyer's shoulder: at 1536 x 2560 the shop was
     # two pedestals and no floor, and every frame of it was a wall.
    ("pawn_shop", 28672, 3584, 32256, 6144, "shop",
     "the pawn shop, open on the avenue"),
]

#: A district's own `floor_shade` is the STREET's: Theatre Row states 30 for
#: its pavement.  While the venues hung off the root they inherited the
#: city's 32 instead, by accident of where they sat.  Nesting them in the
#: district would have handed all 42 interior floors the pavement's shade,
#: which is a design change wearing a restructure's clothes -- so the value
#: they had is stated here, on the node that means it.
INTERIOR_FLOOR_SHADE = 32

#: **Which venue a room belongs to.**  This used to be the name prefix and
#: nothing else: `saloon_main` and `aldermack_dressing` were siblings in one
#: 42-room assembly called `theatre_venues`, told apart by string matching.
#: That is the failure mode this project documents everywhere else -- an
#: authored label standing in for structure -- so the containment is stated
#: once here and the tree carries it from then on.  The flat name survives
#: only as the lookup key the later passes index by.
MEMBERSHIP = {
    "saloon_main": ("saloon", "main"),
    "saloon_back": ("saloon", "back"),
    "saloon_passage": ("saloon", "passage"),
    "parlor_gallery": ("parlor", "gallery"),
    "parlor_range": ("parlor", "range"),
    "parlor_passage": ("parlor", "passage"),
    "aldermack_auditorium": ("aldermack", "auditorium"),
    "aldermack_backstage": ("aldermack", "backstage"),
    "aldermack_dressing": ("aldermack", "dressing"),
    "aldermack_foyer": ("aldermack", "foyer"),
    "aldermack_lobby": ("aldermack", "lobby"),
    "back_passage_west": ("back_of_house", "west"),
    "back_passage_east": ("back_of_house", "east"),
    "pawn_shop": ("pawn_shop", "shop"),
}

#: (material key, what it is).  A venue assembly states its own palette, so
#: a room that keeps it does not have to repeat it and a reader can see
#: where a value came from.
VENUES = {
    "saloon": ("saloon", "the saloon, on Theatre Row"),
    "parlor": ("parlor", "the shooting parlor, behind a one-bay mouth"),
    "aldermack": ("theatre", "the Aldermack: the district's landmark"),
    "pawn_shop": ("shop", "the pawn shop, open on the avenue"),
    "back_of_house": ("service", "the back-of-house circuit joining the three"),
}


#: A piece of furniture is made of whatever its room is made of.
ROOM_MATERIAL = {row[0]: row[5] for row in ROOMS}

#: Ceiling height per room, where it is not ROOM_H.  Height is the other
#: half of telling venues apart: the landmark's house is the tallest
#: interior in the city, the shop the meanest.
ROOM_HEIGHT = {
    "aldermack_auditorium": 49152,   # 2.9 player heights
    "aldermack_foyer": 40960,
    "aldermack_lobby": 40960,
    "parlor_gallery": 28672,
    "parlor_range": 28672,
    "parlor_passage": 28672,
    "pawn_shop": 24576,
    "back_passage_west": 20480,
    "back_passage_east": 20480,
    "aldermack_dressing": 24576,
}

#: (small room, its face, big room, its face) -- always anchored from the
#: smaller face, which is the rule this project keeps relearning.
JOINS = [
    ("saloon_back", "south", "saloon_main", "north"),
    ("saloon_passage", "north", "saloon_main", "south"),
    ("parlor_range", "south", "parlor_gallery", "north"),
    ("parlor_passage", "north", "parlor_gallery", "south"),
    ("aldermack_backstage", "east", "aldermack_auditorium", "west"),
    ("aldermack_dressing", "north", "aldermack_backstage", "south"),
    ("aldermack_foyer", "west", "aldermack_auditorium", "east"),
    ("aldermack_lobby", "west", "aldermack_foyer", "east"),
    ("back_passage_west", "west", "saloon_back", "east"),
    ("back_passage_west", "east", "parlor_range", "west"),
    ("back_passage_east", "west", "parlor_range", "east"),
    ("back_passage_east", "east", "aldermack_backstage", "west"),
]

#: Street doors: (name, room, x0, y0, x1, y1, face) -- each a door plus a
#: porch, both on the bay grid, the porch giving the facade the wall above.
DOORS = [
    ("saloon", "saloon_passage", 6144, 14848, 7168, SOUTH_FACE, "south"),
    ("parlor", "parlor_passage", 13312, 14848, 14336, SOUTH_FACE, "south"),
    ("aldermack", "aldermack_foyer", 27648, FORECOURT_EDGE - 512,
     28672, FORECOURT_EDGE, "south"),
    ("lobby", "aldermack_lobby", EAST_FACE - 512, 8192, EAST_FACE, 9216, "east"),
    ("pawn", "pawn_shop", EAST_FACE - 512, 4608, EAST_FACE, 5632, "east"),
]

#: Shop windows: (name, room, face, x0, y0, x1, y1, plinth).
#:
#: A window is a shallow DISPLAY BOX between the shop and the street, glazed
#: on its street edge -- which is the only construction that gives Blood
#: what it needs for breakable glass: a two-sided wall with the shop on one
#: side and the street on the other, so the pane has something to be
#: transparent *to*.  E6M1 glazes exactly such a pair (see glass.py).
#:
#: The pawn shop's long frontage is its NORTH face, on Theatre Row, not the
#: avenue end where its door is -- so the window goes there and gets two
#: full bays, with the goods on a plinth behind the glass.
WINDOWS = [
    ("pawn_display", "pawn_shop", "north", 29184, 3072, 31232, 3584, 2048),
]

#: Furniture cut into a room's floor: (room, x0, y0, x1, y1, rise, ceiling,
#: note).  `ceiling` is the clear height over the piece; None means it keeps
#: its host's ceiling, which is what a counter or a table does.
#:
#: The stage is the exception, and it is the whole point of a theatre: give
#: it a LOWER ceiling than the house and the wall between the two becomes a
#: proscenium arch, twenty thousand units of it, facing the audience.  With
#: the house's own ceiling carried over the stage the auditorium was a hall
#: with a step in it.
#: The saloon's three rows -- a counter and two card tables -- are gone from
#: this table: they are what every bar has, so they are `templates.bar` with
#: a length rather than three literal rects.
FURNITURE = [
    ("aldermack_auditorium", 20480, 4608, 25600, 6656, STAGE_RISE, STAGE_CLEAR,
     "the stage, under its proscenium"),
    # Three raked rows across the house, each an island in the floor so no
    # two of them share an undeclared edge.
    ("aldermack_auditorium", 20480, 8192, 25600, 8704, 1024, None,
     "the front row"),
    ("aldermack_auditorium", 20480, 9216, 25600, 9728, 2048, None,
     "the middle row"),
    ("aldermack_auditorium", 20480, 10240, 25600, 10752, 3072, None,
     "the back row"),
    ("aldermack_foyer", 27136, 7168, 30208, 7680, COUNTER_RISE, None,
     "the box office"),
    # The range: a firing line you stand behind, and what you shoot at.
    ("parlor_range", 11776, 8192, 15872, 8704, COUNTER_RISE, None,
     "the firing line"),
    ("parlor_range", 12288, 6656, 12800, 7168, TABLE_RISE, None, "a target"),
    ("parlor_range", 13824, 6656, 14336, 7168, TABLE_RISE, None, "a target"),
    ("parlor_range", 15360, 6656, 15872, 7168, TABLE_RISE, None, "a target"),
]


def build(district, theatre_st):
    """Everything on the Aldermack superblock, as venues under the district.

    `district` is Theatre Row's own assembly, not the city: a venue standing
    on Theatre Row is IN Theatre Row, and used to be its sibling.
    """
    import citytree
    facade = FACADES["theatre_row"]
    city = district
    while city.parent is not None:
        city = city.parent
    venue_nodes = {}
    for venue_id, (material_key, note) in VENUES.items():
        venue_nodes[venue_id] = district.assembly(
            venue_id,
            style=Style(**INTERIORS[material_key].style_kwargs(
                floor_z=GRADE, clear_height=ROOM_H,
                floor_shade=INTERIOR_FLOOR_SHADE)),
            note=note,
        )
    rooms: dict = {}

    def venue_for(name):
        """The venue this room belongs to, and its name inside that venue."""
        if name in MEMBERSHIP:
            return MEMBERSHIP[name]
        for suffix in ("_door", "_porch"):
            if name.endswith(suffix):
                stem = name[: -len(suffix)]
                served = next((row[1] for row in DOORS if row[0] == stem), None)
                if served is None:
                    continue
                venue_id = MEMBERSHIP[served][0]
                # A venue's own front door is just its door; the Aldermack
                # has two fronts, so the second keeps the name that tells
                # them apart.
                return venue_id, (suffix[1:] if stem == venue_id else name)
        host = next((row[1] for row in WINDOWS if row[0] == name), None)
        if host is not None:
            venue_id = MEMBERSHIP[host][0]
            local = name[len(venue_id) + 1:] if name.startswith(venue_id + "_") else name
            return venue_id, local
        raise KeyError(f"{name} belongs to no venue; add it to MEMBERSHIP")

    def make(name, x0, y0, x1, y1, material_key, note, *, role="interior",
             floor_z=GRADE, clear=ROOM_H, rk=None):
        material = INTERIORS[material_key]
        venue_id, local = venue_for(name)
        made = venue_nodes[venue_id].room(
            local, [(0, 0), (x1 - x0, 0), (x1 - x0, y1 - y0), (0, y1 - y0)],
            role=role, faces=dict(COMPASS), frame=Frame(int(x0), int(y0)),
            region_kwargs={**material.region_kwargs(), **(rk or {})},
            note=note)
        made.surfaces(**material.style_kwargs(floor_z=floor_z,
                                              clear_height=clear))
        rooms[name] = made
        return made

    for name, x0, y0, x1, y1, key, note in ROOMS:
        rk = None
        if name == "aldermack_auditorium":
            # The first wall is deliberately the south stage edge, so the
            # ceiling rises through the seating toward the rear of the house.
            rk = {"ceiling_slope": SlopeSpec(
                hinge=((x0, y0), (x1, y0)), rise_z=-AUDITORIUM_PITCH)}
        make(name, x0, y0, x1, y1, key, note,
             clear=ROOM_HEIGHT.get(name, ROOM_H), rk=rk)
    # A join is declared on the node that owns BOTH ends: inside a venue
    # that is the venue, between two venues it is the district.
    for small, sf, big, bf in JOINS:
        citytree.join(rooms[small], rooms[big], at_a=sf, at_b=bf,
                      connection_id=f"connection:venue_{small}_{big}")

    # Street doors: room -> door -> porch -> street, the reveal chain.
    # Each takes a channel so a lever beside it can open it; it keeps
    # direct use as well, so pushing the door itself still works.
    import doorswitch
    levers = []
    for door_index, (name, room_name, x0, y0, x1, y1, face) in enumerate(DOORS):
        channel = doorswitch.channel_for(door_index)
        inner = {"south": "north", "east": "west",
                 "north": "south", "west": "east"}[face]
        if face == "south":
            door = make(f"{name}_door", x0, y0, x1, y1 - PORCH_D, "common",
                        f"the {name} door", role="doorway", clear=0,
                        rk={"type": 600, "door_face": 22,
                            "inherit_finish": "both",
                            "sector_behavior": z_motion_door(
                                GRADE, GRADE - DOOR_H, interaction="both",
                                rx_id=channel)})
            porch = make(f"{name}_porch", x0, y1 - PORCH_D, x1, y1, "service",
                         f"the {name} reveal", role="gateway", clear=DOOR_H)
        else:
            door = make(f"{name}_door", x0, y0, x1 - PORCH_D, y1, "common",
                        f"the {name} door", role="doorway", clear=0,
                        rk={"type": 600, "door_face": 22,
                            "inherit_finish": "both",
                            "sector_behavior": z_motion_door(
                                GRADE, GRADE - DOOR_H, interaction="both",
                                rx_id=channel)})
            porch = make(f"{name}_porch", x1 - PORCH_D, y0, x1, y1, "service",
                         f"the {name} reveal", role="gateway", clear=DOOR_H)
        door.surfaces(wall_picnum=facade.opening, floor_z=GRADE, clear_height=0)
        porch.surfaces(wall_picnum=facade.opening, ceiling_picnum=facade.opening,
                       floor_z=GRADE, clear_height=DOOR_H)
        citytree.join(door, rooms[room_name], at_a=inner, at_b=face,
                      connection_id=f"connection:{name}_door_in")
        citytree.join(porch, door, at_a=inner, at_b=face,
                      connection_id=f"connection:{name}_porch_door")
        city.connect(porch.face(face), theatre_st.face("north"),
                     connection_id=f"connection:{name}_street")
        levers.append((f"lever:{name}", theatre_st.region_id,
                       doorswitch.lever_segment(face, x0, y0, x1, y1), channel))

    # Shop windows: a display box, glazed to the street by the glass pass.
    for name, room_name, face, x0, y0, x1, y1, plinth in WINDOWS:
        box = make(name, x0, y0, x1, y1, ROOM_MATERIAL[room_name],
                   f"the {name.replace('_', ' ')}: goods behind glass",
                   role="detail", floor_z=GRADE - plinth,
                   clear=ROOM_HEIGHT.get(room_name, ROOM_H) - plinth)
        citytree.join(box, rooms[room_name], at_a="south", at_b="north",
                      connection_id=f"connection:{name}_shop")
        city.connect(box.face("north"), theatre_st.face("north"),
                     connection_id=f"connection:{name}_street")

    # Furniture, through the set-piece constructors.  An object that has a
    # mined class is authored through that class: `raised_solid` is the
    # idiom, and the rise defaults come from the class, not from here.
    for index, (room_name, x0, y0, x1, y1, rise, over, note) in enumerate(FURNITURE):
        host = rooms[room_name]
        host_h = ROOM_HEIGHT.get(room_name, ROOM_H)
        piece = setpieces.raised_solid(
            host, f"furniture_{index}", host, (x0, y0, x1, y1),
            INTERIORS[ROOM_MATERIAL[room_name]], grade=GRADE, rise=rise,
            host_clear=host_h, note=note)
        if over is not None:
            piece.surfaces(floor_z=GRADE - rise, clear_height=over)
    # The pawn shop, furnished from the kit rather than by hand.  Every
    # dimension that is pinned in the campaign family stays pinned here;
    # only the run length is ours.  This is the first venue to compose
    # from `fixtures.py` instead of from literal rectangles.
    # Both venues are furnished by a template that reads the room it is
    # handed.  The pawn shop was a run plus two `place` calls at four
    # literal coordinates; the saloon was three rows of `FURNITURE`.  They
    # are a shop and a bar, and now they say so.
    templates.shop(rooms["pawn_shop"], material=INTERIORS["shop"],
                   grade=GRADE, host_clear=ROOM_HEIGHT["pawn_shop"])
    templates.bar(rooms["saloon_main"], material=INTERIORS["saloon"],
                  grade=GRADE, host_clear=ROOM_H)

    return rooms, levers


#: Who is in here, and what is worth finding.  Cultists hold the venues
#: (E3M1's town register); the pickups follow the campaign's 0.9-per-dude.
POPULATION = [
    ("saloon_main", 202, (0.78, 0.22)),      # clear of the counter island
    ("saloon_back", 203, (0.5, 0.5)),
    ("parlor_range", 202, (0.6, 0.4)),
    ("aldermack_auditorium", 202, (0.12, 0.6)),   # between stage and tier
    ("aldermack_backstage", 203, (0.5, 0.3)),
    ("pawn_shop", 203, (0.15, 0.08)),   # the strip north of the kit fixtures
]
PICKUPS = [
    ("saloon_back", 65, (0.3, 0.6)),
    ("parlor_range", 62, (0.25, 0.5)),
    ("aldermack_dressing", 109, (0.5, 0.5)),
    ("aldermack_lobby", 67, (0.4, 0.5)),
    ("pawn_shop", 63, (0.75, 0.08)),          # clear of the pedestals
]
#: A brazier in every venue room, BRACKETED TO A NAMED WALL.
#: (room, face, t along that face).  The campaign puts tile 506 within 512
#: units of a solid wall 92% of the time, at 1.03 player heights; placing
#: it in the middle of the floor at a third of a height is what made the
#: owner's "flying torches".  props.CATALOGUE carries the measurement.
#: Only **3%** of campaign rooms contain a light-emitting prop: Blood lights
#: a room with sector shade, not with lamp sprites.  We had one per room.
#: These are one per venue -- the light you actually navigate by -- and the
#: rest of the brightness comes from the shade passes.
LIT = [("saloon_main", "east", 0.30), ("aldermack_auditorium", "north", 0.12)]


def populate(layout, rooms, attested, flame_fields, flame_stand) -> int:
    import props
    placed = 0
    for name, type_id, local in POPULATION + PICKUPS:
        spec = attested(type_id)
        if spec is None or name not in rooms:
            continue
        # Where the furniture is now depends on how big the room is, so a
        # hand-chosen "clear of the counter" local has to be checked rather
        # than trusted.
        region_id = rooms[name].region_id
        free = props.free_local(layout.regions[region_id], local)
        if free is None:
            continue
        layout.place_on_floor(f"theatre:{name}_{type_id}", region_id,
                              local=free, **spec["fields"])
        placed += 1
    for index, (name, face, t) in enumerate(LIT):
        if name not in rooms:
            continue
        props.mount_on_wall(layout, f"theatre:brazier_{index}",
                            rooms[name], face, t=t)
        placed += 1
    return placed
