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
* **open-front shop** -- a broad E6M1-inspired storefront: large glazed
  bays, low crate-top display racks, garment rails and a sales counter.

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
    # This is a real, broad-fronted shop rather than a shallow row of props:
    # the sales floor is five by 2.5 plan units.  It stops 512 units east of
    # the Aldermack auditorium, preserving a real masonry wall instead of
    # turning the two interiors into an accidental overlap.
    ("pawn_shop", 27136, 3584, 32256, 6144, "shop",
     "the pawn shop: broad glazing, sales floor and avenue entrance"),
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
    "pawn_vault": ("pawn_shop", "vault"),
    "pawn_vault_neck": ("pawn_shop", "vault_neck"),
}

#: THE PLEDGE ROOM.  A pawnbroker's stock is not on the shop floor; it is
#: behind bars.  A blind reviewer said of this shop, dresses in its window,
#: "the pawn's goods say 'boutique', not 'pawn' ... no caged counter".  And
#: measured against Blood's own city (`tools/city_profile.py --interiors`),
#: Gravesend's interiors are flat: E3M1's median interior holds 15 floor
#: heights over 3 bodies and 37 shade steps between its darkest floor and
#: its brightest; this shop held one height and none.
#:
#: So: behind the shop, in the dead pocket between it and the Aldermack's
#: lobby, a strongroom a quarter of a body up, lower-ceilinged, walled in
#: pressed metal, lit by its own lamp -- and shut off by a grille.  The neck
#: stands at the room's own floor and ceiling, so the step is at the shop's
#: side of it and the bars hang where both sides are level.  You see what is
#: pledged and cannot reach it.  (x0, y0, x1, y1, floor above the shop's,
#: clear height.)
PAWN_VAULT = (30976, 6400, 32000, 7424, 4096, 16384)
PAWN_VAULT_NECK = (30976, 6144, 32000, 6400, 4096, 16384)
#: The grille stands in the neck's mouth to the vault: the owner's "grate"
#: mask (463), blocking, on the plane between two volumes -- the same record
#: law as a pane (`glass.shopfront`).  A thin box round that plane.
PAWN_GRILLE = (30992, 6384, 31984, 6416)
GRILLE_TILE = 463
VAULT_WALL = 215          # owner: "pressed metal"

#: (material key, what it is).  A venue assembly states its own palette, so
#: a room that keeps it does not have to repeat it and a reader can see
#: where a value came from.
#: (material key, what it is, the L1 venue slot it fills, its L1 type).
#: The last column is what closes the loop: `city_plan.VENUES` declares ten
#: venues and nothing checked that the tree agreed with it.  `back_of_house`
#: fills no slot -- it is circulation the plan does not name -- and says so
#: with `None`.
VENUES = {
    "saloon": ("saloon", "the saloon, on Theatre Row", "saloon", "bar"),
    "parlor": ("parlor", "the shooting parlor, behind a one-bay mouth",
               "shooting_parlor", "walk_through"),
    "aldermack": ("theatre", "the Aldermack: the district's landmark",
                  "aldermack", "landmark_complex"),
    "pawn_shop": ("shop", "the pawn shop, open on the avenue",
                  "pawn_shop", "open_front"),
    "back_of_house": ("service", "the back-of-house circuit joining the three",
                      None, None),
}


#: A piece of furniture is made of whatever its room is made of.
ROOM_MATERIAL = {row[0]: row[5] for row in ROOMS}

#: Ceiling height per room, where it is not ROOM_H.  Height is the other
#: half of telling venues apart: the landmark's house is the tallest
#: interior in the city, the shop the meanest.
#: THE SALOON, from its study (`knowledge/blood/studies/saloon`): Blood's
#: bars are 2.1 to 2.8 bodies high (E1M2 s278: 2.66) where ours stood under
#: an office ceiling at 1.93; their counter top is the brightest surface in
#: a dim room (shade 5 against a floor at 30) where ours was 32 everywhere;
#: and stools stand along the counter (DWE3M1 sprites 539-547: tile 284, a
#: gib object, 32 by 24, 768 apart). The study's larger moves -- a soffit
#: over the bar on a post, a back-bar niche of bottles -- are not built.
SALOON_SHADES = {"floor": 30, "ceiling": 44, "wall": 34}
STOOL = {"type": 416, "picnum": 284, "cstat": 385, "x_repeat": 32,
         "y_repeat": 24, "shade": 0, "status": 4,
         "behavior": {"data_1": 5, "data_2": 20, "data_4": 312}}
STOOL_PITCH, STOOL_LIFT = 768, 2880          # its drawn half height at 24
ROOM_HEIGHT = {
    "saloon_main": 45056,            # 2.66: E1M2's station bar
    #: 5.7 bodies. The theatre study (`knowledge/blood/studies/theatre`):
    #: "every exemplar house is 5.7 to 6.8 bodies tall" (SCHOOL_ s154,
    #: FORDTHEA s252); ours was 2.9. The study's other moves -- a framed
    #: three-bay proscenium, raked rows of real seats -- are NOT built yet.
    "aldermack_auditorium": 96256,
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
#: avenue end where its door is.  Four full bays make the shop legible
#: from the street; the west and east masonry piers leave it a real shell.
WINDOWS = [
    ("pawn_display", "pawn_shop", "north", 27648, 3072, 31744, 3584, 4096),
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
#: The hand table that used to live here is gone.  It iterated nine
#: rectangles into `furniture_0` .. `furniture_8`, so the Aldermack's stage,
#: its three rows of seating and its box office all wore one name and the
#: meaning lived only in a prose note -- `citytree find stage` returned
#: `backstage`.  `templates.theatre_house`, `templates.box_office` and
#: `templates.shooting_range` place the same geometry and name it, because
#: whoever builds a thing knows what the thing is.


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
    for venue_id, (material_key, note, l1_id, l1_type) in VENUES.items():
        venue_nodes[venue_id] = district.assembly(
            venue_id,
            style=Style(**INTERIORS[material_key].style_kwargs(
                floor_z=GRADE, clear_height=ROOM_H,
                floor_shade=INTERIOR_FLOOR_SHADE)),
            note=note,
        )
        if l1_id:
            citytree.declare_venue(venue_nodes[venue_id], l1_id, l1_type,
                                   built_by="l3_theatre")
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
        host = next((row[1] for row in WINDOWS
                     if name == row[0] or name.startswith(row[0] + "_")), None)
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

    # The pawnbroker's pledge room (see PAWN_VAULT).
    nx0, ny0, nx1, ny1, nrise, nclear = PAWN_VAULT_NECK
    vx0, vy0, vx1, vy1, vrise, vclear = PAWN_VAULT
    neck = make("pawn_vault_neck", nx0, ny0, nx1, ny1, "service",
                "the recess before the bars, at the pledge room's level", role="gateway",
                floor_z=GRADE - nrise, clear=nclear)
    vault = make("pawn_vault", vx0, vy0, vx1, vy1, "service",
                 "the pledge room: behind bars, two steps up, lit",
                 floor_z=GRADE - vrise, clear=vclear,
                 rk={"declared_zero_exit": True})
    vault.surfaces(wall_picnum=VAULT_WALL)
    vault.intent.update({"kind": "vault",
                         "generated_surfaces": ["floor", "ceiling", "wall"]})
    vault.light_source("pledge_lamp", local=(0.5, 0.5),
                       height_player_heights=0.55)
    citytree.join(neck, rooms["pawn_shop"], at_a="north", at_b="south",
                  connection_id="connection:pawn_vault_neck_shop")
    citytree.join(neck, vault, at_a="south", at_b="north",
                  connection_id="connection:pawn_vault_neck_vault")

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
    # The pane sits in a frame: reveal, sash pockets, then the box.  See
    # `glass.shopfront` for why none of it may be glazed on the facade line.
    import glass
    for name, room_name, face, x0, y0, x1, y1, plinth in WINDOWS:
        front = glass.shopfront((x0, y0, x1, y1), face)
        key = ROOM_MATERIAL[room_name]
        clear = ROOM_HEIGHT.get(room_name, ROOM_H) - plinth
        title = name.replace("_", " ")

        def part(part_name, rect, note, _key=key, _clear=clear, _plinth=plinth):
            return make(part_name, *rect, _key, note, role="detail",
                        floor_z=GRADE - _plinth, clear=_clear)

        box = part(name, front["box"], f"the {title}: goods behind glass")
        reveal = part(f"{name}_reveal", front["reveal"],
                      f"the {title} surround: riser, fascia and the name")
        glass.surround(front, name=name, kind="pawn", reveal=reveal, box=box,
                       shop=rooms[room_name], grade=GRADE, sill=plinth,
                       box_clear=clear, words="PAWNBROKER")
        out, into = front["outward"], front["inward"]
        for index, rect in enumerate(front["sashes"]):
            sash = part(f"{name}_sash_{index}", rect,
                        "a sash pocket: the pane hangs at its back")
            sash.surfaces(wall_picnum=glass.JAMB_TILE)
            citytree.join(sash, reveal, at_a=out, at_b=into,
                          connection_id=f"connection:{name}_sash_{index}_reveal")
            citytree.join(sash, box, at_a=into, at_b=out,
                          connection_id=f"connection:{name}_sash_{index}_box")
        citytree.join(box, rooms[room_name], at_a=into, at_b=out,
                      connection_id=f"connection:{name}_shop")
        city.connect(reveal.face(out), theatre_st.face("north"),
                     connection_id=f"connection:{name}_street")

    # Furniture, through the set-piece constructors.  An object that has a
    # mined class is authored through that class: `raised_solid` is the
    # idiom, and the rise defaults come from the class, not from here.
    # Each venue's fittings come from a template that knows what it places.
    house = templates.theatre_house(
        rooms["aldermack_auditorium"], material=INTERIORS["theatre"],
        grade=GRADE, host_clear=ROOM_HEIGHT["aldermack_auditorium"],
        stage_clear=STAGE_CLEAR, rows=3)
    # The curtain across the proscenium. A theatre whose stage has no curtain
    # is a room with a step in it, and the Aldermack is the district's
    # landmark -- so it gets the mechanism, not a painted stripe.
    import curtains

    ax0, ay0, ax1, _ay1 = next(
        (x0, y0, x1, y1) for name, x0, y0, x1, y1, _k, _n in ROOMS
        if name == "aldermack_auditorium")
    stage_rect = (ax0 + templates.HOUSE_MARGIN,
                  ay0 + templates.STAGE_INSET,
                  ax1 - templates.HOUSE_MARGIN,
                  ay0 + templates.STAGE_INSET + templates.STAGE_DEPTH)
    curtain = curtains.hang(
        rooms["aldermack_auditorium"], venue_nodes["aldermack"], stage_rect,
        grade=GRADE, clear=STAGE_CLEAR)
    #: The stage is what the curtain's light follows, so the link needs its
    #: region. It is a raised solid under the house node, named by whoever
    #: built it -- which is the point of naming things.
    curtain["stage_region"] = next(
        (room.region_id for room in citytree.rooms_under(house)
         if room.node_id == "stage"), None)
    templates.box_office(
        rooms["aldermack_foyer"], material=INTERIORS["theatre"],
        grade=GRADE, host_clear=ROOM_HEIGHT["aldermack_foyer"])
    templates.shooting_range(
        rooms["parlor_range"], material=INTERIORS["parlor"],
        grade=GRADE, host_clear=ROOM_HEIGHT["parlor_range"], targets=3)
    # E6M1's repetitive display modules become a full retail composition:
    # window-side racks, two free-standing garment rails and a sales counter
    # that leaves the door-side aisle open.
    templates.pawnbroker(rooms["pawn_shop"], material=INTERIORS["shop"],
                         grade=GRADE, host_clear=ROOM_HEIGHT["pawn_shop"],
                         back="west")
    #: The east wall has nothing behind it, and WHISKEY is lettered on it:
    #: the liquor shelf goes under the word, at the bar's end.
    templates.bar(rooms["saloon_main"], material=INTERIORS["saloon"],
                  grade=GRADE, host_clear=ROOM_HEIGHT["saloon_main"],
                  shelf=("east", 0.3, 2048))
    rooms["saloon_main"].surfaces(floor_shade=SALOON_SHADES["floor"],
                                  ceiling_shade=SALOON_SHADES["ceiling"],
                                  wall_shade=SALOON_SHADES["wall"])

    return rooms, levers, curtain


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

# E6M1's retail dress is not generic debris.  The source places nine hanging
# garments (tile 73) along one apparel wall, with palettes 11--14, and three
# mannequins (2377) in a separate window sector.  This smaller shop takes four
# garments at the source's height and palette range, plus the three-window
# mannequin rhythm.  The actual values were captured by tools.mine_e6m1_shop.
#: Hung west of the pledge room's bars and of the LOANS column beside
#: them: the first shirt used to hang at t 0.14, which is now the middle
#: of the grille.
SHOP_CLOTHES = ((0.42, 14), (0.57, 11), (0.72, 12), (0.87, 13))
SHOP_MANNEQUINS = ((0.25, 12, 385), (0.50, 13, 389), (0.75, 11, 385))
SHOP_CLOTHES_HEIGHT = 14336 / 16960
SHOP_MANNEQUIN_ABOVE_FLOOR = 10976
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


def stools(layout, rooms) -> int:
    """A row of stools along the customers' side of the saloon's counter."""
    import props
    import fixtures

    room = rooms["saloon_main"]
    x0, y0, x1, y1 = (int(v) for v in props.room_rect(room))
    #: `templates.bar` runs the counter 1,024 in from the walls
    front = y0 + 1024 + fixtures.BAR.depth + 320
    placed = 0
    x = x0 + 1024 + 384
    while x <= x1 - 1024 - 384:
        local = ((x - x0) / (x1 - x0), (front - y0) / (y1 - y0))
        free = props.free_local(layout.regions[room.region_id], local)
        if free is not None:
            layout.place_on_floor(
                f"saloon:stool_{placed}", room.region_id, local=free,
                height_player_heights=STOOL_LIFT / 16960.0, **STOOL)
            placed += 1
        x += STOOL_PITCH
    return placed


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
    # The large south wall is solid and away from both the street glass and
    # the east door.  It is the shop's apparel rack: a real wall-mounted
    # sequence rather than floor sprites pushed into a shelf sector.
    shop = rooms["pawn_shop"]
    sx0, sy0, sx1, sy1 = props.room_rect(shop)
    for index, (t, palette) in enumerate(SHOP_CLOTHES):
        layout.place_on_wall(
            f"theatre:pawn_clothes_{index}", shop.region_id,
            a1=(sx1 - 512, sy1), a2=(sx0 + 512, sy1), t=t,
            height_player_heights=SHOP_CLOTHES_HEIGHT,
            offset_player_widths=0.06, facing="into_region",
            type=417, picnum=73, cstat=144, pal=palette, shade=-8,
            x_repeat=64, y_repeat=64, status=4)
        placed += 1
    # The pledge room holds what was pledged: coats on its back wall, where
    # the shop's own stock hangs on the shop's, and a lamp to see them by.
    vault = rooms.get("pawn_vault")
    if vault is not None:
        import glass as _glass
        vx0, vy0, vx1, vy1 = props.room_rect(vault)
        for index, (t_along, palette) in enumerate(((0.3, 12), (0.7, 14))):
            layout.place_on_wall(
                f"theatre:pawn_pledge_{index}", vault.region_id,
                a1=(vx1 - 96, vy1), a2=(vx0 + 96, vy1), t=t_along,
                height_player_heights=0.62,
                offset_player_widths=0.06, facing="into_region",
                type=417, picnum=73, cstat=144, pal=palette, shade=-8,
                x_repeat=48, y_repeat=48, status=4)
            placed += 1
        # LOANS, stacked downward beside the bars, where a customer reads
        # the two together. Vertical: the campaign stacks letters in 11 of
        # its maps, at 1.25 drawn heights of pitch.
        import wallplane
        neck_west = PAWN_VAULT_NECK[0]
        wallplane.text(
            layout, "sign:pawn_loans", shop.region_id,
            (neck_west - 96, sy1), (neck_west - 736, sy1),
            words="LOANS", style="column_small", vertical=True,
            height_player_heights=1.38)
        region = layout.regions[vault.region_id]
        repeats = _glass.lamp_repeats(int(region.floor_z) - int(region.ceiling_z))
        layout.add_sprite(
            "lamp:pawn_vault", vault.region_id,
            x=(vx0 + vx1) // 2, y=(vy0 + vy1) // 2,
            z=int(region.ceiling_z) + 128 * repeats[1] * 4,
            picnum=_glass.DISPLAY_LAMP, cstat=0, shade=-32,
            x_repeat=repeats[0], y_repeat=repeats[1], status=0)
        placed += 1

    # E6M1 S50: mannequins sit in their own display volume behind the glass,
    # not in the player aisle.  Keeping their source z offset means the feet
    # stand visually on the display plinth without intersecting its walls.
    display = rooms["pawn_display"]
    dx0, dy0, dx1, dy1 = props.room_rect(display)
    display_floor = int(layout.regions[display.region_id].floor_z)
    #: No mannequins. The owner, 2026-11-18: "pawn shop could be rethinked
    #: a bit". Three dressed figures in the window made it a dress shop (a
    #: blind reviewer said "boutique" twice), and they were the build's
    #: three squeezed sprites. The window now holds pledges (`goods.ON_TOP`).
    for index, (u, palette, cstat) in enumerate(()):
        layout.add_sprite(
            f"theatre:pawn_mannequin_{index}", display.region_id,
            x=round(dx0 + (dx1 - dx0) * u), y=(dy0 + dy1) // 2,
            z=display_floor - SHOP_MANNEQUIN_ABOVE_FLOOR,
            type=416, picnum=2377, cstat=cstat, pal=palette, shade=-8,
            x_repeat=56, y_repeat=56, status=4, angle=512)
        placed += 1
    return placed
