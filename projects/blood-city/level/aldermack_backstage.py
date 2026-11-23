"""Build and furnish the Aldermack's service passage, prop store and dressing room."""

from bloodmap.levelprog import RECT_FACES
from bloodmap.placement import seated_z
from bloodmap.player_space import PLAYER_PROFILES
from bloodmap.texture_align import sprite_tile_extents

import citytree
import detailing
import setpieces
import wallplane
from materials import Material
from resolution import GRADE


PLAYER = PLAYER_PROFILES["blood"]
AISLE = 2 * PLAYER.body_width
CORRIDOR_CLEAR = 32768
DRESSING_CLEAR = 24576
WEST, EAST = 17408, 19328
PARLOR = (7168, 8192)
STAIR = (4864, 5888)
COMPASS = dict(zip(RECT_FACES, range(4)))

# E3M4 s391: deep, framed openings and dark masonry. E3M6 s458: work
# against the wall, with tile 369's cornice and a different floor at the bench.
PASSAGE = Material(369, 21, 379, 253)
RACK = Material(28, 21, 20, 179)
KEEPER = Material(369, 296, 379, 179)
STORE = Material(409, 21, 141, 409)
CRATE = Material(452, 20, 379, 452)
# HUNT s673: chequered top, 6144 above s674. REALM4 s181: curtain 159
# at yrepeat 8/pal 2, marble 295, standing candelabra and framed art.
TRICK_TABLE = Material(290, 290, 141, 290)
DRESSING = Material(179, 390, 68, 179)
STAR = Material(159, 295, 295, 68)
VANITY = Material(36, 20, 68, 36)


def _room(parent, name, outline, material, clear, shades, *, faces=None,
          rise=0, role="interior", note):
    room = citytree.make_room(parent, name, outline, faces=faces, note=note,
                              role=role, intent={"kind": "furnished"},
                              region_kwargs=material.region_kwargs())
    floor, wall, ceiling = shades
    room.surfaces(**material.style_kwargs(
        floor_z=GRADE - rise, clear_height=clear, floor_shade=floor,
        wall_shade=wall, ceiling_shade=ceiling))
    return room


def _rect(parent, name, rect, material, clear, shades, **options):
    x0, y0, x1, y1 = rect
    return _room(parent, name, [(x0, y0), (x1, y0), (x1, y1), (x0, y1)],
                 material, clear, shades, faces=COMPASS, **options)


def _join(small, side, big, face, *, width=AISLE, clear=DRESSING_CLEAR,
          **options):
    citytree.join(small, big, at_a=side, at_b=face,
                  connection_id=f"connection:aldermack_{small.node_id}_{side}",
                  min_opening=clear, min_width=width, **options)


def _service(venue, fire_bay):
    bay_x, bay_north, bay_south = fire_bay
    # Keep the old door host's three edges exact. The parlor and future
    # stage stair have named faces so the other ends can anchor to them.
    corridor = _room(venue, "backstage", [
        (WEST, 4096), (17536, 4096), (17536, 4736), (19200, 4736),
        (19200, 4096), (EAST, 4096), (EAST, STAIR[0]), (EAST, STAIR[1]),
        (EAST, 6272), (18944, 6272), (18944, 7552), (EAST, 7552),
        (EAST, bay_north), (bay_x, bay_north), (bay_x, bay_south),
        (EAST, bay_south), (EAST, 11264), (WEST, 11264),
        (WEST, PARLOR[1]), (WEST, PARLOR[0]), (WEST, 6912),
        (17792, 6912), (17792, 5120), (WEST, 5120),
    ], PASSAGE, CORRIDOR_CLEAR, (35, 38, 46), faces={
        "north": 2, "east": 6, "stage_stair": 6, "keeper": 9,
        "bay_north": 12, "bay_west": 13, "bay_south": 14,
        "south": 16, "west": 18, "scenery": 21,
    }, note="Stage service passage, with a scenery rack and a keeper's post.")

    rack = _room(corridor, "scenery_rack", [
        (17504, 5184), (17792, 5184), (17792, 6848), (17504, 6848),
        (WEST, 6752), (WEST, 5280),
    ], RACK, 26624, (35, 30, 46), faces={"east": 1},
        note="Chamfered timber rack with nested scenery flats and their braces.")
    _join(rack, "east", corridor, "scenery", face_picnum=179)

    keeper = _rect(corridor, "keeper", (18944, 6336, 19424, 7488),
                   KEEPER, DRESSING_CLEAR, (27, 28, 45),
                   note="The stage-door keeper's recessed callboard and writing shelf.")
    _join(keeper, "west", corridor, "keeper", face_picnum=179)
    setpieces.raised_solid(keeper, "writing_shelf", keeper,
                          (19008, 6928, 19360, 7440), VANITY, grade=GRADE,
                          host_clear=DRESSING_CLEAR, face_picnum=36, shade=20,
                          note="Writing shelf under the duty board, with the cue book open.")

    store = _room(corridor, "prop_store", [
        (17600, 3584), (17856, 3584), (17856, 3968), (18880, 3968),
        (18880, 3584), (19136, 3584), (19136, 4736), (17600, 4736),
    ], STORE, 26624, (35, 40, 46), faces={
        "table_west": 1, "table_front": 2, "table_east": 3, "south": 6,
    }, note="Prop store let into the north masonry, with the trick table laid out.")
    _join(store, "south", corridor, "north", face_picnum=409)
    table = _rect(store, "trick_table", (17856, 3584, 18880, 3968),
                  TRICK_TABLE, 26624 - 6144, (22, 31, 46), rise=6144,
                  role="detail", note="Chequered conjuring table after HUNT s673.")
    for side, face in (("west", "table_west"), ("south", "table_front"),
                       ("east", "table_east")):
        _join(table, side, store, face, width=1, clear=0, face_picnum=290)
    setpieces.raised_solid(corridor, "prop_crate", corridor,
                          (18832, 10560, 19216, 11072), CRATE, grade=GRADE,
                          rise=6144, host_clear=CORRIDOR_CLEAR, face_picnum=452,
                          shade=24, note="A braced prop crate parked beside the dressing door.")
    return corridor


def _dressing(venue, corridor):
    threshold = _rect(venue, "dressing_entry", (17664, 11264, 19072, 11520),
                      DRESSING, DRESSING_CLEAR, (36, 32, 41), role="gateway",
                      note="A timber-lined deep threshold between service boards and carpet.")
    room = _rect(venue, "dressing", (WEST, 11520, 19456, 14336), DRESSING,
                 DRESSING_CLEAR, (33, 32, 44),
                 note="Two makeup stations, a costume rail and a folding screen.")
    _join(threshold, "north", corridor, "south", face_picnum=179)
    _join(threshold, "south", room, "north", face_picnum=179)

    for name, y0, y1, shade in (("makeup", 11776, 12736, 14),
                                ("star_makeup", 12928, 14144, 9)):
        vanity = setpieces.raised_solid(
            room, name, room, (19040, y0, 19408, y1), VANITY,
            grade=GRADE, host_clear=DRESSING_CLEAR, face_picnum=36,
            face_y_repeat_scale=0.5, shade=shade,
            note="Makeup counter with shallow timber drawers and a polished top.")
        vanity.intent["kind"] = "furnished"

    star = _room(room, "star", [
        (17664, 14336), (19200, 14336), (19200, 14784), (19072, 14912),
        (17792, 14912), (17664, 14784),
    ], STAR, DRESSING_CLEAR, (20, 21, 37), faces={"north": 0}, rise=512,
        note="The star's curtained corner. Her portrait and work are still laid out.")
    _join(star, "north", room, "south", face_picnum=68)
    return room


def build(venue, *, fire_bay):
    """Hand the two public room handles back to Theatre Row's joins and population."""
    corridor = _service(venue, fire_bay)
    return {"aldermack_backstage": corridor,
            "aldermack_dressing": _dressing(venue, corridor)}


def _child(room, name):
    return next(part for part in room.children if part.node_id == name)


def _sprite(layout, room, name, tile, point, *, repeat, up=0, seat="floor",
            cstat=128, **fields):
    x, y = point
    region = layout.regions[room.region_id]
    height, offset = sprite_tile_extents()[tile]
    z = seated_z(seat=seat, floor_z=region.floor_z, ceiling_z=region.ceiling_z,
                 tile_height=height, y_offset=offset, y_repeat=repeat[1],
                 cstat=cstat, clearance=up)
    layout.add_sprite(f"backstage:{name}", room.region_id, x=x, y=y,
                      z=z, picnum=tile, cstat=cstat,
                      x_repeat=repeat[0], y_repeat=repeat[1], **fields)


def _mount(layout, room, name, tile, wall, *, up, repeat, t=0.5,
           shade=-8, pal=0):
    return wallplane.sprite(
        layout, f"backstage:{name}", room.region_id, *wall, tile=tile,
        t=t, height_player_heights=up / PLAYER.standing_height,
        x_repeat=repeat[0], y_repeat=repeat[1], shade=shade, pal=pal,
        cstat=144, offset_player_widths=0.045, required=True)


def _sign(layout, room, word, wall, *, up, size=46, **options):
    wallplane.text(layout, f"backstage:sign:{word.lower().replace(' ', '_')}",
                   room.region_id, *wall, words=word, size=size, shade=-12,
                   height_player_heights=up / PLAYER.standing_height,
                   offset_player_widths=0.045, required=True, **options)


def _pool(layout, room, name, point, width, depth, shade):
    x, y = point
    dx, dy = width // 2, depth // 2
    layout.add_overlay(f"backstage:pool:{name}", room.region_id, [
        (x - dx, y - dy // 2), (x, y - dy), (x + dx, y - dy // 2),
        (x + dx, y + dy // 2), (x, y + dy), (x - dx, y + dy // 2),
    ], floor_shade=shade)


def _dress_service(layout, corridor):
    rack = _child(corridor, "scenery_rack")
    keeper = _child(corridor, "keeper")
    store = _child(corridor, "prop_store")
    shelf = _child(keeper, "writing_shelf")
    table = _child(store, "trick_table")
    crate = _child(corridor, "prop_crate")

    # Painted canvas viewed edge-on at the rack mouth, with the timber
    # braces visible at the ends. Angled ends are inside the rack's recess.
    for index, (point, tile, angle, repeat, pal) in enumerate((
        ((17500, 5512), 417, 104, (35, 40), 0),
        ((17598, 5736), 179, 896, (28, 42), 0),
        ((17564, 6224), 146, 168, (37, 37), 2),
        ((17662, 6504), 20, 856, (24, 31), 0),
    )):
        _sprite(layout, rack, f"scenery_flat_{index}", tile, point,
                repeat=repeat, cstat=144, angle=angle, pal=pal, shade=-4)
    _sprite(layout, rack, "rack_end_brace", 116, (17632, 6672),
            repeat=(17, 29), cstat=144, angle=1616, shade=4)

    # HUNT s673 sprites 1681/1683/1685, compressed to this shallower top.
    _sprite(layout, table, "trick_flask", 517, (18638, 3780),
            repeat=(42, 42), pal=2, shade=0)
    _sprite(layout, table, "trick_sack", 822, (18058, 3776),
            repeat=(36, 36), pal=5, shade=-8)
    _sprite(layout, table, "trick_balloon", 1115, (18372, 3760),
            repeat=(42, 34), up=672, pal=4, shade=0)
    _sprite(layout, table, "trick_balloon_shadow", 1115, (18564, 3596),
            repeat=(37, 34), cstat=144, angle=512, up=472, shade=63)
    _sprite(layout, store, "prop_store_lamp", 641, (19000, 4320),
            repeat=(60, 25), seat="ceiling", shade=-48)
    detailing.panel(table.region_id, (17856, 3584), (18880, 3584), 146,
                    shade=24, storeys=1, note="Cloth hung behind the trick table.")
    _sprite(layout, shelf, "duty_book", 349, (19172, 7200),
            repeat=(15, 13), cstat=160, angle=1024, shade=-12)
    _sprite(layout, shelf, "duty_ink", 802, (19301, 7336), repeat=(18, 18))
    _sprite(layout, shelf, "keeper_lamp", 693, (19300, 7050),
            repeat=(28, 28), shade=-36)

    keeper_wall = ((19424, 6336), (19424, 7488))
    _sign(layout, keeper, "CALLS", keeper_wall, up=15900, size=51)
    _mount(layout, keeper, "call_sheet", 742, keeper_wall,
           up=12150, repeat=(36, 27), t=0.38)
    _mount(layout, keeper, "call_bill", 356, keeper_wall,
           up=13100, repeat=(27, 26), t=0.68)

    north_pier = ((EAST, STAIR[1]), (EAST, 6272))
    _sign(layout, corridor, "STAGE", north_pier, up=18400, size=22)
    _sign(layout, corridor, "SILENCE", ((WEST, 5120), (WEST, 4096)),
          up=16900, size=51)
    _sign(layout, corridor, "DRESSING", ((EAST, 11264), (WEST, 11264)),
          up=28200, size=68, over_steps=True)

    fire_wall = ((WEST, 11264), (WEST, PARLOR[1]))
    _mount(layout, corridor, "fire_extinguisher", 658, fire_wall,
           up=9300, repeat=(40, 40), t=0.24)
    _sprite(layout, corridor, "fire_bucket", 3540, (17660, 10560),
            repeat=(42, 42), angle=1536, shade=-8)
    _sprite(layout, corridor, "costume_trunk", 523, (17680, 10848),
            repeat=(58, 58), shade=1)
    _sprite(layout, crate, "crate_ties", 2633, (19024, 10816),
            repeat=(45, 38), cstat=160, up=4, angle=940, shade=4)

    pin_rail = ((WEST, 10016), (WEST, 8320))
    _mount(layout, corridor, "pin_rail", 68, pin_rail,
           up=17920, repeat=(88, 14), shade=-7)
    for index, y in enumerate((8528, 8848, 9168)):
        _sprite(layout, corridor, f"fly_rope_{index}", 513, (17450, y),
                repeat=(5, 61), up=5080, cstat=144, angle=0, shade=-5)
        _sprite(layout, corridor, f"fly_weight_{index}", 822, (17518, y),
                repeat=(30, 35), up=(0, 384, 0)[index], shade=8)
    _sprite(layout, corridor, "second_trunk", 522, (17622, 9632),
            repeat=(56, 56), shade=5)

    for name, point, width, depth in (("scenery", (18400, 5736), 768, 1120),
                                      ("doors", (17920, 9472), 768, 960),
                                      ("dressing", (18420, 10820), 768, 760)):
        _sprite(layout, corridor, f"gas_lamp_{name}", 641, point,
                repeat=(62, 24), seat="ceiling", shade=-55)
        _pool(layout, corridor, name, point, width, depth, 21)

    # Painted service pipe and the scuffed line along the card-door route.
    detailing.panel(corridor.region_id, (EAST, 7568), (EAST, 8336), 498,
                    storeys=1, shade=34, note="Service feed into the keeper's recess.")
    detailing.panel(corridor.region_id, (WEST, 8400), (WEST, 10016), 28,
                    storeys=1, shade=27, note="Timber backing to the working pin rail.")
    _sprite(layout, corridor, "paint_stain", 955, (18150, 6550),
            repeat=(40, 24), cstat=160, up=4, angle=640, shade=15)
    layout.add_overlay("backstage:worn_boards", corridor.region_id, [
        (17874, 6480), (18144, 6160), (18568, 7976), (18384, 8232),
        (18108, 7944),
    ], floor_shade_offset=-5, floor_picnum=20,
        note="The path worn light between the scene rack and the parlor passage.")


def _dress_makeup(layout, room):
    star = _child(room, "star")
    for name, y, mirror in (("makeup", 12272, 710), ("star_makeup", 13520, 711)):
        wall = ((19456, y - 464), (19456, y + 464))
        _mount(layout, room, name + "_mirror", mirror, wall,
               up=14648, repeat=(46, 30), shade=-11)
        _mount(layout, room, name + "_bulbs", 77, wall,
               up=20240, repeat=(26, 14), shade=-92)
        _pool(layout, room, name, (18824, y), 1152, 960, 22 if mirror == 710 else 17)
        vanity = _child(room, name)
        _sprite(layout, vanity, name + "_jar", 834, (19217, y - 285),
                repeat=(26, 25), shade=-12)
        _sprite(layout, vanity, name + "_rouge", 802, (19295, y - 130),
                repeat=(25, 21), shade=-12)
        _sprite(layout, vanity, name + "_mask", 166, (19268, y + 300),
                repeat=(22, 15), cstat=144, angle=1024, shade=-8)

    _sprite(layout, room, "makeup_stool", 284, (18824, 12144),
            repeat=(32, 24), shade=-5)
    _sprite(layout, room, "star_stool", 284, (18736, 13776),
            repeat=(32, 24), shade=2)
    west = ((WEST, 12864), (WEST, 11520))
    _mount(layout, room, "costume_rail", 68, west, up=20140,
           repeat=(69, 14), shade=7)
    for index, (t, pal) in enumerate(((0.21, 14), (0.50, 12), (0.79, 11))):
        _mount(layout, room, f"costume_{index}", 73, west,
               up=14350, t=t, repeat=(36, 43), shade=-6, pal=pal)
    _sprite(layout, room, "wardrobe_trunk", 523, (17625, 12176),
            repeat=(48, 48), shade=6)

    # Three cloth-covered screen leaves in a shallow zigzag, with posts
    # sitting on the same floor. The screen only screens the costume end.
    for index, (point, angle) in enumerate((
        ((17562, 13036), 1664), ((17784, 13036), 1408), ((18006, 13036), 1664),
    )):
        _sprite(layout, room, f"screen_leaf_{index}", 251, point,
                repeat=(28, 126), cstat=145, angle=angle, shade=(6, -5, 11)[index])
    wardrobe_wall = ((WEST, 14336), (WEST, 13120))
    _sign(layout, room, "FINAL SHOW", wardrobe_wall, up=18800, size=32)
    _mount(layout, room, "wardrobe_bill", 742, wardrobe_wall,
           up=13700, t=0.26, repeat=(41, 30), shade=-16)
    _sprite(layout, room, "star_costume", 2377, (17744, 13568),
            repeat=(42, 43), shade=-5)

    # Pair the star's portrait with the broken glass and a cue the company
    # has kept writing and re-writing. The little book sits open below it.
    rear = ((19072, 14912), (17792, 14912))
    _mount(layout, star, "star_portrait", 163, rear, up=14750,
           repeat=(48, 50), shade=-8)
    _sign(layout, star, "ENCORE", rear, up=6500, size=42)
    _sprite(layout, star, "star_candelabrum", 580, (18892, 14630),
            repeat=(38, 48), shade=-14, pal=2)
    _sprite(layout, star, "star_trunk", 522, (17906, 14624),
            repeat=(48, 48), shade=3)
    _sprite(layout, _child(room, "star_makeup"), "last_cues", 348, (19272, 13550),
            repeat=(27, 22), cstat=160, angle=1088, shade=-9)
    for a, b in zip(star.outline, star.outline[1:] + star.outline[:1]):
        if a[1] == b[1] == 14336:
            continue
        detailing.panel(star.region_id, a, b, 159, pal=2, shade=21,
                        note="REALM4 s181, crumpled curtains dyed red.")
    layout.add_overlay("backstage:star_marble", star.region_id, star.outline,
                       floor_pal=2, ceiling_pal=2)


def furnish(layout, rooms):
    """Fit out each service volume after the room tree has declared the joins."""
    _dress_service(layout, rooms["aldermack_backstage"])
    _dress_makeup(layout, rooms["aldermack_dressing"])
