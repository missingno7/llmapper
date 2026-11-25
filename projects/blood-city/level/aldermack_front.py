"""The Aldermack's marquee, box office and second entrance."""

from bloodmap import wiring
from bloodmap.levelprog import RECT_FACES, Frame
from bloodmap.mechanism import furnish_solid_slide, solid_slide_spec
from bloodmap.motion import MARKER_OFF, MARKER_ON
from l3_foundry import _attested
from bloodmap.placement import seated_z

import citytree
import detailing
import setpieces
import wallplane
import wing_doors
import wires
from materials import INTERIORS, Material
from resolution import GRADE, STANDING

FOYER_CLEAR = 40960
DOOR_CLEAR = 31744
PORCH_RISE = 1536
FORECOURT = 11264
AVENUE = 32768
CASE_PANE_Y = FORECOURT - 128
MARQUEE = (27520, 29376)
#: the forecourt entrance: the same pair of wings as the stage doors, opening
#: into the foyer over the whole middle of its south wall
FRONT_DOORS = wing_doors.Pair("front", "south", (28448, 10752), 768, depth=864)
FRONT_WALL = 192
SIDE_SPAN = (8192, 9216)
#: the avenue door as it was built: its spec and its region (the build seats its leaf)
SIDE_DOOR: dict = {}
SILL = 20                                              # planks, as Blood's own sills under wooden doors
STONE = 70
PANEL = 179
WOOD = 28
CARPET = 471
BORDER = 306
BOOTH_SILL = 6144
BOOTH_X = (27392, 30080)
TICKET_SPANS = ((27520, 28672), (28864, 29952))
POSTER_CASES = (
    ("bill_movie", (26752, 27456), 2047, 19, 23),
    ("bill_jojo", (29760, 30592), 981, 35, 45),
)
VENUE_MATERIAL = INTERIORS["theatre"]
COUNTER = Material(wall=PANEL, floor=390, ceiling=422, opening=WOOD)
COMPASS = dict(zip(RECT_FACES, range(4)))


def _room(parent, name, rect, *, floor=GRADE, clear=FOYER_CLEAR,
          role="detail", note, **fields):
    x0, y0, x1, y1 = rect
    origin = parent.world_frame()
    region_fields = {**VENUE_MATERIAL.region_kwargs(), **fields}
    room = citytree.make_room(
        parent, name, ((0, 0), (x1-x0, 0), (x1-x0, y1-y0), (0, y1-y0)),
        frame=Frame(x0-origin.dx, y0-origin.dy, -origin.dz),
        role=role, faces=COMPASS, note=note, region_kwargs=region_fields)
    room.surfaces(floor_z=floor, clear_height=clear,
                  floor_shade=28, ceiling_shade=32, wall_shade=30)
    return room


def _join(name, a, side_a, b, side_b, **fields):
    return citytree.join(a, b, at_a=side_a, at_b=side_b,
                         connection_id=f"connection:{name}", **fields)


def _entrances(foyer, lobby, street):
    venue = foyer.parent
    floor = GRADE - PORCH_RISE
    porch = _room(venue, "porch", (MARQUEE[0], 10944, MARQUEE[1], FORECOURT),
                  floor=floor, clear=34816, role="gateway",
                  note="A raised terrazzo landing under the forecourt marquee.")
    porch.surfaces(wall_picnum=STONE, floor_picnum=307, ceiling_picnum=422)
    _join("aldermack_street", porch, "south", street, "north")
    front_wire = wires.wire("theatre:front-doors")
    doors = wing_doors.build(
        venue, FRONT_DOORS, room=foyer,
        room_faces={side: f"bay_{side}" for side in ("north", "east", "west")},
        outside=porch, outside_face="north", wall=FRONT_WALL,
        material=VENUE_MATERIAL, room_clear=FOYER_CLEAR, grade=GRADE,
        bay_style=dict(floor_z=GRADE, clear_height=FOYER_CLEAR, floor_picnum=390, ceiling_picnum=422,
                       wall_picnum=119, floor_shade=31, ceiling_shade=39, wall_shade=34),
        frame_style=dict(floor_z=GRADE, clear_height=wing_doors.LEAF_HEIGHT, floor_picnum=307,
                         ceiling_picnum=WOOD, wall_picnum=WOOD,
                         floor_shade=28, ceiling_shade=32, wall_shade=30))
    foyer.raw("Hang the forecourt doors on their wire",
              lambda layout, room: wing_doors.furnish(layout, doors, front_wire))

    y0, y1 = SIDE_SPAN
    # The owner, 2026-11-25: "in door with knob (picnum 30) I would avoid doing
    # them as Z motion, these can be slide door to the other side than knob is
    # ... for example aldermack side door would be the case of this".
    spec = solid_slide_spec((32256, y0, AVENUE, y1), axis="y", pocket="low")
    street_edge, lobby_edge = spec["portals"]
    side = venue.room(
        "lobby_door", spec["outline"], frame=Frame(0, 0), role="doorway",
        faces={"east": spec["outline"].index(street_edge[0]), "west": spec["outline"].index(lobby_edge[0])},
        region_kwargs=VENUE_MATERIAL.region_kwargs(), note="The avenue door: one leaf with a knob, that slides into the wall.")
    side.surfaces(floor_z=GRADE, clear_height=wing_doors.LEAF_HEIGHT, wall_picnum=20, floor_picnum=SILL, ceiling_picnum=20,
                  floor_shade=28, ceiling_shade=32, wall_shade=30)
    _join("lobby_street", side, "east", street, "north")
    _join("lobby_door_in", side, "west", lobby, "east")
    SIDE_DOOR.update(spec=spec, region=side.region_id)
    side_wire = wires.wire("theatre:side-door")
    foyer.raw("Hang the avenue door on its wire", lambda layout, room: furnish_solid_slide(
        layout, side.region_id, spec, side_wire,
        marker_fields={kind: _attested("E1M3", kind, 3997)["fields"] for kind in (MARKER_OFF, MARKER_ON)}))
    return porch, side


def _box_office(foyer):
    # FORDTHEA s239 and s119. The 6,144-high counter is a continuous sill,
    # with two 1,100-wide openings and a solid wooden mullion between.
    left, right = BOOTH_X
    box = _room(foyer, "ticket_room", (left, 6272, right, 6528),
                floor=GRADE-BOOTH_SILL, clear=20480, declared_zero_exit=True,
                note="The clerk's room behind the two ticket windows.")
    box.surfaces(wall_picnum=179, floor_picnum=21, ceiling_picnum=179,
                 floor_shade=18, ceiling_shade=14, wall_shade=14)
    for i, (a, b) in enumerate(TICKET_SPANS):
        window = _room(foyer, f"ticket_window_{i}", (a, 6528, b, 6656),
                       floor=GRADE-BOOTH_SILL, clear=13568,
                       declared_zero_exit=True,
                       note="The ticket sill is high enough to keep the player at the counter.")
        window.surfaces(wall_picnum=PANEL, floor_picnum=390, ceiling_picnum=WOOD)
        _join(f"ticket_{i}_foyer", window, "south", foyer, "north",
              face_picnum=PANEL, min_opening=0)
        _join(f"ticket_{i}_room", window, "north", box, "south",
              face_picnum=PANEL, min_opening=0)
    return box


def _case(parent, street, name, bounds):
    left, right = bounds
    floor = GRADE - 8704
    parts = []
    for suffix, y0, y1 in (("case", 10976, CASE_PANE_Y), ("sash", CASE_PANE_Y, FORECOURT)):
        part = _room(parent, f"{name}_{suffix}", (left, y0, right, y1),
                     floor=floor, clear=12800, declared_zero_exit=True,
                     note="A theatre bill in a recessed, glazed street frame.")
        part.surfaces(floor_picnum=796, ceiling_picnum=796, wall_picnum=796,
                      floor_shade=12, ceiling_shade=12, wall_shade=10)
        parts.append(part)
    back, sash = parts
    _join(name, back, "south", sash, "north", min_opening=0)
    _join(f"{name}_street", sash, "south", street, "north", min_opening=0)
    return back


def glass_spans():
    """TEDE1M5 w3493 and w3497 put the pane behind the frame mouth."""
    return [(left, CASE_PANE_Y, right, CASE_PANE_Y)
            for _, (left, right), *_ in POSTER_CASES]


def build(foyer, lobby, street):
    """Keep the foyer's exterior outline and existing join to the house."""
    foyer.surfaces(floor_picnum=390, ceiling_picnum=422, wall_picnum=119,
                   floor_shade=31, ceiling_shade=39, wall_shade=34)
    lobby.surfaces(floor_picnum=BORDER, ceiling_picnum=422, wall_picnum=PANEL,
                   floor_shade=31, ceiling_shade=38, wall_shade=34)
    foyer.intent["kind"] = "aldermack_foyer"
    # The doors' bay is notched out of the foyer's south side.
    x0, y0, x1, _y1 = FRONT_DOORS.bay()
    x0, x1, y0 = x0 - 26624, x1 - 26624, y0 - 6656
    foyer.outline = [(0, 0), (4096, 0), (4096, 4096), (x1, 4096), (x1, y0), (x0, y0), (x0, 4096), (0, 4096)]
    foyer.faces.update(north=0, east=1, south=2, south_east=2, bay_east=3, bay_north=4, bay_west=5,
                       south_west=6, west=7)
    lobby.intent["kind"] = "aldermack_lobby"

    # The two solid wall returns leave one centred opening at x 30.
    lobby.outline = [(128, 0), (1536, 0), (1536, 2048), (128, 2048),
                     (128, 1536), (0, 1536), (0, 512), (128, 512)]
    lobby.faces.update(west=5)
    _join("venue_aldermack_lobby_aldermack_foyer", lobby,
          "west", foyer, "east")
    porch, side = _entrances(foyer, lobby, street)
    booth = _box_office(foyer)
    cases = [(spec, _case(foyer.parent, street, spec[0], spec[1]))
             for spec in POSTER_CASES]

    # A low carpeted platform leads toward the house. The west wall stays
    # clear for the vomitory, and the main exit paths remain at grade.
    landing = setpieces.raised_solid(
        foyer, "foyer_landing", foyer, (27136, 8376, 29952, 9832),
        VENUE_MATERIAL, grade=GRADE, rise=768, host_clear=FOYER_CLEAR,
        face_picnum=WOOD, note="The low carpet landing on the way to the house.")
    landing.surfaces(floor_picnum=BORDER, floor_shade=28)
    runner = setpieces.raised_solid(
        landing, "foyer_runner", landing, (27328, 8568, 29760, 9640),
        VENUE_MATERIAL, grade=GRADE-768, rise=0, host_clear=FOYER_CLEAR-768,
        note="The patterned carpet inside the gold border.")
    runner.surfaces(floor_picnum=CARPET, floor_shade=25)
    counter = setpieces.raised_solid(
        foyer, "foyer_cloak_counter", foyer, (29568, 7040, 30464, 7424),
        COUNTER, grade=GRADE, host_clear=FOYER_CLEAR, rise=7424,
        face_picnum=PANEL, note="The cloakroom's claim counter.")
    bench = setpieces.raised_solid(
        lobby, "lobby_settee", lobby, (31008, 9192, 32000, 9544),
        COUNTER, grade=GRADE, host_clear=FOYER_CLEAR, rise=4096,
        face_picnum=PANEL, note="The waiting settee has an upholstered seat.")
    bench.surfaces(floor_picnum=260, floor_shade=27)
    foyer.raw("Set the theatre's front-of-house fixtures and signs",
              lambda layout, room: furnish(layout, room, lobby, street, porch,
                                            side, booth, cases, runner, counter))


def _face(room, side, *, at=0.5, width=None):
    anchor = room.face(side, at=at, width=width).anchor()
    return anchor.a, anchor.b


def _panel(layout, name, room, segment, tile, size, height, **fields):
    xr, yr = size
    return wallplane.sprite(
        layout, f"aldermack:{name}", room.region_id, *segment, tile=tile,
        x_repeat=xr, y_repeat=yr, height_player_heights=height,
        cstat=208, required=True, **fields)


def _seated(layout, room, name, point, tile, size, *, seat="floor", cstat=128,
            **fields):
    region = layout.regions[room.region_id]
    _, art_height, _, yoff = wallplane.art()[tile]
    xr, yr = size
    z = seated_z(seat=seat, floor_z=int(region.floor_z),
                 ceiling_z=int(region.ceiling_z), tile_height=art_height,
                 y_offset=yoff, y_repeat=yr, cstat=cstat)
    layout.add_sprite(f"aldermack:{name}", room.region_id, x=point[0], y=point[1],
                      z=z, picnum=tile, x_repeat=xr, y_repeat=yr,
                      cstat=cstat, **fields)


def _plate(layout, room, name, *, point, tile, size, angle, shade, cstat=208):
    """A sign backing or fixed trim surface, centred about its draw point."""
    x, y, z = point
    xr, yr = size
    layout.add_sprite(f"aldermack:{name}", room.region_id, x=x, y=y, z=z,
                      picnum=tile, x_repeat=xr, y_repeat=yr, cstat=cstat,
                      angle=angle, shade=shade)


def _marquee(layout, street, porch, side):
    front = ((MARQUEE[0], FORECOURT), (MARQUEE[1], FORECOURT))
    # Keep the fascia below the letters. The wall-sprite painter can cover
    # individual glyphs with a wide backing when seen from the side.
    _plate(layout, street, "marquee_apron", point=(28448, FORECOURT+6, GRADE-37504),
           tile=PANEL, size=(116, 12), angle=512, shade=3)
    _panel(layout, "bulb_rail", street, front, 77, (55, 24), 2.17,
           over_steps=True, shade=-32)
    wallplane.text(layout, "sign:aldermack_marquee", street.region_id, *front,
                   words="ALDERMACK", size=69, palette=0, shade=-54,
                   height_player_heights=2.59, over_steps=True, required=True)
    _panel(layout, "prices", street, ((29376, FORECOURT), (29760, FORECOURT)),
           905, (24, 36), 1.24, shade=-4)
    # E1M4 s320's red-bulb rail marks the mouth. Its rows are recessed into
    # the soffit so they can be seen under the lip from the two door leaves.
    for x in (27872, 28448, 29024):
        _seated(layout, porch, f"soffit_{x}", (x, 11120), 795, (24, 24),
                seat="ceiling", cstat=32 | 64, shade=-36, angle=512)
    avenue = ((AVENUE, 9344), (AVENUE, 8064))
    _plate(layout, street, "avenue_fascia", point=(AVENUE+6, 8704, GRADE-38400),
           tile=PANEL, size=(80, 11), angle=0, shade=3)
    wallplane.text(layout, "sign:aldermack_avenue", street.region_id, *avenue,
                   words="ALDERMACK", size=47, palette=0, shade=-48,
                   height_player_heights=2.27, over_steps=True, required=True)
    _panel(layout, "avenue_bill", street, ((AVENUE, 8176), (AVENUE, 7680)),
           356, (29, 36), 0.94, shade=6)


def _blade(layout, street):
    # THESLUMS s484 looks onto these discs (s412 sprites 353-358 and
    # 367-372). The 4225 alphabet letters and the translucent 625 halos
    # are paired on a projecting blade, in the original palette and shade.
    x, y = 29552, FORECOURT + 252
    _plate(layout, street, "blade_backing", point=(x, y, GRADE-56064),
           tile=215, size=(32, 132), angle=0, shade=17, cstat=144)
    for face in (0, 1024):
        offset = 1 if face == 0 else -1
        for i, letter in enumerate("ALDERMACK"):
            z = GRADE - 84736 + i*7168
            layout.add_sprite(
                f"aldermack:blade_{face}_{i}", street.region_id,
                x=x+26*offset, y=y, z=z, picnum=4225+ord(letter)-ord("A"),
                x_repeat=99, y_repeat=94, cstat=208, angle=face, shade=-40, pal=7)
            layout.add_sprite(
                f"aldermack:halo_{face}_{i}", street.region_id,
                x=x+60*offset, y=y, z=z, picnum=625, x_repeat=28, y_repeat=26,
                cstat=210, angle=face, shade=-10, pal=7)


def _floor(layout, room, name, point, tile, size, angle, shade=0, pal=0):
    z = int(layout.regions[room.region_id].floor_z)
    layout.add_sprite(f"aldermack:{name}", room.region_id,
                      x=point[0], y=point[1], z=z-4, picnum=tile,
                      x_repeat=size[0], y_repeat=size[1], cstat=32 | 128,
                      angle=angle, shade=shade, pal=pal)


def _fittings(layout, street, foyer, lobby, porch):
    # Solid bays take their own frame after the city's facade pass.
    for a, b in ((26624, 26752), (27456, MARQUEE[0]),
                 (MARQUEE[1], 29504), (30592, 30720)):
        detailing.panel(street.region_id, (a, FORECOURT), (b, FORECOURT), 472,
                        note="A dressed stone pilaster beside the Aldermack's porch and bills.")
    for a, b in ((27392, 27520), (28672, 28864), (29952, 30720)):
        detailing.panel(foyer.region_id, (a, 6656), (b, 6656), PANEL,
                        note="The box office's wooden panel and central mullion.")
    for side, at, width in (("north", 0.04, 256), ("east", 0.20, 192),
                            ("east", 0.84, 192)):
        a, b = _face(foyer, side, at=at, width=width)
        detailing.panel(foyer.region_id, a, b, 149,
                        note="Carved pilasters divide the foyer wall into bays.")
    for face, point, angle in (
        ("north", (28672, 6662, GRADE-37488), 512),
        ("east", (30714, 8704, GRADE-37488), 1024),
    ):
        _plate(layout, foyer, f"cornice_{face}", point=point, tile=70,
               size=(127, 13), angle=angle, shade=11)
    _panel(layout, "book_signing", foyer, _face(foyer, "east", at=0.86, width=624),
           356, (38, 40), 1.16, shade=-9)

    # EU11_ s349's high drape legs on either side of a doorway.
    for k, (y0, y1) in enumerate(((7680, 8192), (9216, 9728))):
        detailing.panel(lobby.region_id, (30848, y0), (30848, y1), 146,
                        shade=22, pal=2, storeys=1, note="A drape leg at the foyer opening.")
        _panel(layout, f"drape_medallion_{k}", lobby, ((30848, y1), (30848, y0)),
               165, (21, 22), 1.35, shade=-2, pal=2)


def furnish(layout, foyer, lobby, street, porch, side, booth, cases, runner, counter):
    """Mount and seat fixtures after the rooms and apertures exist."""
    _marquee(layout, street, porch, side)
    _blade(layout, street)
    for (name, _bounds, tile, xr, yr), back in cases:
        _panel(layout, name, back, _face(back, "north"), tile,
               (xr, yr), 6400/STANDING, shade=-8)

    _fittings(layout, street, foyer, lobby, porch)
    north = _face(foyer, "north")
    wallplane.text(layout, "sign:aldermack_tickets", foyer.region_id, *north,
                   words="BOX OFFICE", size=82, palette="default", shade=-30,
                   height_player_heights=1.65, over_steps=True, required=True)
    # Silhouette in the left opening, light and an abandoned till on the right.
    # over the vomitory's mouth, in sight of the ticket windows
    wallplane.text(layout, "sign:aldermack_stalls", foyer.region_id, (26624, 10240), (26624, 8704),
                   words="STALLS", size=82, palette="default", shade=-30,
                   height_player_heights=1.72, over_steps=True, required=True)
    _seated(layout, booth, "clerk", (28160, 6416), 2330, (37, 37),
            shade=0, cstat=208, angle=512)
    _seated(layout, booth, "ticket_candle", (29456, 6416), 938, (31, 31),
            shade=-20)
    _seated(layout, booth, "coin_bowl", (29024, 6416), 550, (34, 34), shade=-10)
    _panel(layout, "cloak_mirror", foyer, _face(foyer, "east", at=0.105, width=736),
           711, (38, 36), 1.23, shade=6)
    for x, pal in ((30144, 12), (30528, 14)):
        segment = ((x-186, 6656), (x+186, 6656))
        _panel(layout, f"coat_{x}", foyer, segment, 73, (32, 39), 0.91,
               shade=3, pal=pal)
    _seated(layout, counter, "claim_tray", (30016, 7232), 550, (35, 22), shade=-8)

    _panel(layout, "shadow_show", foyer, _face(foyer, "south_west", at=0.5, width=720),
           225, (13, 30), 1.17, shade=-7)
    _panel(layout, "foyer_mirror", foyer, _face(foyer, "south_east", at=0.5, width=800),
           710, (40, 39), 1.02, shade=3)
    for x, tile in ((27072, 1009), (30240, 1013)):
        _seated(layout, foyer, f"planter_{x}", (x, 10256), tile, (43, 47), shade=6)
    for x in (27216, 29648):
        _panel(layout, f"candle_bracket_{x}", foyer,
               ((x+240, 10752), (x-240, 10752)), 554, (38, 37), 1.59,
               shade=-14)
    _seated(layout, foyer, "chandelier", (28672, 8160), 596, (56, 34),
            seat="ceiling", shade=-22, pal=2)
    _seated(layout, runner, "patron", (27648, 9072), 2334, (42, 42),
            shade=3, angle=768)
    for room, x, y, size, angle in (
        (runner, 27624, 9080, (29, 24), 916),
        (runner, 27364, 9440, (9, 12), 836),
        (foyer, 27040, 9432, (12, 18), 872),
        (foyer, 26784, 9472, (10, 14), 1012),
    ):
        _floor(layout, room, f"drag_{x}", (x, y), 1417, size, angle, -2, 2)
    for y in (8216, 8576):
        _seated(layout, foyer, f"rail_post_{y}", (26880, y), 534, (32, 30), shade=3)
    layout.add_sprite("aldermack:queue_rail", foyer.region_id,
                      x=26880, y=8396, z=GRADE-3700, picnum=588,
                      x_repeat=18, y_repeat=29, cstat=145, angle=0, shade=5)

    for name, face, backing, bill, size in (
        ("sloth", "north", (31552, 7686, GRADE-16640), 932, (46, 52)),
        ("wrestling", "south", (31552, 9722, GRADE-17920), 440, (57, 57)),
    ):
        angle = 512 if face == "north" else 1536
        _plate(layout, lobby, f"{name}_frame", point=backing, tile=70,
               size=(63, 34), angle=angle, shade=7)
        _panel(layout, f"avenue_{name}", lobby, _face(lobby, face), bill,
               size, (GRADE-backing[2])/STANDING, shade=-7,
               offset_player_widths=0.15)
    wallplane.text(layout, "sign:aldermack_lobby", lobby.region_id,
                   *_face(lobby, "north"), words="ALDERMACK", size=53,
                   palette="default", shade=-26, height_player_heights=1.85,
                   required=True)
    _seated(layout, lobby, "lobby_lamp", (31488, 8704), 641, (60, 28),
            seat="ceiling", shade=-21)
