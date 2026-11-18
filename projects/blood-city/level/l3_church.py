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

from bloodmap.doors import z_motion_door
from bloodmap.levelprog import Frame, RECT_FACES, Style
from bloodmap.slope import SlopeSpec

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
#: The tower door stands 2.4 bodies: a square door was read, twice, as "a
#: garage door", and this one is 1024 wide by 2560 tall.
PORTAL_H = {"tower": 40960}

CHANCEL_RISE = 2048        # the chancel stands over the nave, one low step
#: How much taller the nave gets across its span. 1.29 player heights is
#: the campaign's median slope rise; 21,878 units.
PITCH = 21878

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
    ("tower", 30720, 22528, 32640, 24064, "church", 57344,
     "the room behind the tower: 3.4 bodies, under the low roof"),
    # The belfry: the tower's foot, inside the part of it that stands proud
    # of the avenue face, and the church's way in (see TOWER_DOORS).  It is
    # the one room with nothing over it but the tower.
    ("belfry", 32896, 22784, 33920, 23808, "church", 81920,
     "the belfry: 4.8 bodies, inside the tower the avenue sees"),
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

#: ---- the massing: what the church is from the street -------------------
#:
#: Until 2026-11-17 it was nothing: the church's street faces were walls of
#: the district's street sector and were drawn to the district's sky, 11.6
#: bodies, like every other block.  `experiments/church-skyline` gave it a
#: height by LOWERING THE SKY in front of each face, and the owner, walking it
#: in NBlood the same day, named what that costs: "when you put parallax sky
#: low it is covering view like a normal ceiling".  From the churchyard the
#: tower was gone and so was every block beyond the wall.
#:
#: So this is `experiments/church-roofs`: nothing here is short because its
#: sky is low.  The yard wall, the church's low range and its nave are ROOFS
#: -- sectors whose floor is their top, under the city's own sky -- and the
#: view passes over them.  The one sky that is not the city's is RAISED, for
#: the tower.  See `bloodmap.skyline` for the rule, and PORTALS below for
#: what it costs: no door in any wall the roof is seen over.
APRON = 512
#: The eaves of the low range, above grade: 2 texture repeats, 3.9 bodies.
#: A wall shows its top at a level gaze only from about 1.7 heights away, and
#: the avenue is 7 plan units wide, so this is about the most that can front
#: it and still show sky from the far kerb (measured last round: at 6.8 the
#: sky share from across the avenue was 0.000).
BODY_HEIGHT = 65536
#: The nave stands over the low range: eaves at 3 repeats (5.8 bodies, clear
#: of its own ridge inside at 5.2), pitching up to a ridge 1.2 bodies higher.
NAVE_EAVES = 98304
NAVE_PITCH = 20480
#: The churchyard wall and the mausoleum row let into it: just over three
#: bodies, which nothing on the ground can climb or see over.
YARD_WALL_HEIGHT = 53248
#: The tower's ridge: 9 repeats, 17.4 bodies -- half again over every block
#: in the city.  city-norms records landmark skylines of 6 to 10; the excess
#: is the point, and is the owner's to overrule.
TOWER_HEIGHT = 294912
#: How far each tower face falls from its centre line to its corners: two
#: repeats, 3.9 bodies, so the eaves stand at 13.5.  Every face is a gable,
#: which is the nearest thing to a spire Build's one slope per sector can
#: say.  One repeat was tried first and a blind review read "obelisk".
TOWER_GABLE = 65536
#: The tower's plan: 1536 proud of the avenue face, 2048 along it, over the
#: belfry inside.  Its west face rises out of the church's roof.
TOWER = (MASS[2], 22272, MASS[2] + 1536, 24320)
#: Layers.  The roofs stand over the rooms, so each is its own layer with a
#: height band clear of what is beneath it (`bloodmap.layers`): the low rooms
#: top out at 57,344 above grade under a roof at 65,536; the nave and belfry
#: at about 79,000 under a nave roof at 98,304.
LAYERS = {
    "church_low": (GRADE - 57344, 16384, "St Gallow's rooms under the low roof"),
    "church_tall": (GRADE - 81920, 16384, "the nave and the belfry"),
    "roof_low": (GRADE - TOWER_HEIGHT - 4096, GRADE - BODY_HEIGHT,
                 "the church's low roof, and the tower's foot on it"),
    "roof_nave": (GRADE - 196608 - 4096, GRADE - NAVE_EAVES,
                  "the nave's pitched roof"),
}
TALL_ROOMS = ("nave", "belfry")

#: Lancets: stained glass (tile 569, owner-named 2026-09-03) as a wall sprite.
#: E1M5 glazes 512-wide openings with it at x_repeat 4, y_repeat 8 on a
#: masked wall; here the light is hung on the face.  384 wide, 1.45 bodies
#: tall, sill a little over a body up.
LANCET = {"tile": 569, "x_repeat": 48, "y_repeat": 192, "cstat": 16 | 64,
          "height": 1.95}
#: Along the avenue face, evenly; and three under the chancel's north
#: end, which is where a church keeps its great window.
#: (clear of the tower's ring, which owns the face for 512 past the tower)
LANCETS_AVENUE = (31232, 30208, 29184, 28160, 27136, 26112, 25216)
LANCETS_ROW = (28928, 29440, 29952)
#: How high the belfry lights hang, in bodies: under the tower's eaves (13.5)
#: and clear over every roofline in the city (11.6).
BELFRY_HEIGHT = 11.9

#: Filled by `massing`: what `populate` needs to hang the glass.
_FACES: dict = {}
#: Every ground-level sky sector `massing` made; the build manifest counts
#: them, because they join the street's at-grade component.
APRONS: list = []
#: region id -> the tile its raised face wears (`skyline.dress_steps`).
ROOF_FACES: dict = {}


def declare_layers(city) -> None:
    for name, (ceiling_z, floor_z, note) in LAYERS.items():
        city.declare_layer(name, ceiling_z=ceiling_z, floor_z=floor_z, note=note)


def street_hole(area_rect) -> list[tuple[int, int]]:
    """What the street gives up: the cemetery, and the tower with its ring.

    One polygon, because a street's holes may not share an edge.
    """
    ax0, ay0, ax1, ay1 = (int(v) for v in area_rect)
    _mx0, my0, mx1, _my1 = MASS
    _tx0, ty0, tx1, ty1 = TOWER
    a = APRON
    if (ax1, ay0) != (mx1, my0):
        raise ValueError("the church no longer stands in the cemetery's "
                         "north-east corner; the massing assumes it does")
    return [(ax0, ay0), (mx1, ay0), (mx1, ty0 - a), (tx1 + a, ty0 - a),
            (tx1 + a, ty1 + a), (mx1, ty1 + a), (mx1, ay1), (ax0, ay1)]


def _shared(left, right) -> list[tuple[tuple[int, int], tuple[int, int]]]:
    """The straight stretches two outlines have in common, as segments."""
    from shapely.geometry import Polygon
    from shapely.ops import linemerge
    both = Polygon(left).boundary.intersection(Polygon(right).boundary)
    if both.is_empty:
        return []
    lines = [g for g in getattr(both, "geoms", [both])
             if g.geom_type == "LineString"]
    if not lines:
        return []
    merged = linemerge(lines) if len(lines) > 1 else lines[0]
    out = []
    for line in getattr(merged, "geoms", [merged]):
        points = [(int(round(x)), int(round(y))) for x, y in line.coords]
        for start, end in zip(points, points[1:]):
            if start != end:
                out.append((start, end))
    return out


def _with_vertices(outline, points):
    """`outline` with every point that lies on one of its edges made a vertex."""
    out = []
    count = len(outline)
    for index in range(count):
        a, b = outline[index], outline[(index + 1) % count]
        out.append(a)
        on = []
        for p in set(points):
            if p in (a, b):
                continue
            cross = (b[0] - a[0]) * (p[1] - a[1]) - (b[1] - a[1]) * (p[0] - a[0])
            if cross:
                continue
            dot = (p[0] - a[0]) * (b[0] - a[0]) + (p[1] - a[1]) * (b[1] - a[1])
            if 0 < dot < (b[0] - a[0]) ** 2 + (b[1] - a[1]) ** 2:
                on.append((dot, p))
        out.extend(p for _d, p in sorted(on))
    return out


def massing(parish, district, street, ground, gates, area_rect, gate_rects, *,
            floor_shade: int) -> dict:
    """Roofs over the church and its yard wall; a raised sky for the tower."""
    from bloodmap import skyline
    from bloodmap.slope import depth
    from materials import SKY
    from resolution import STREET_SKY
    from shapely.geometry import Polygon, box

    ax0, ay0, ax1, ay1 = (int(v) for v in area_rect)
    mx0, my0, mx1, my1 = MASS
    _tx0, ty0, tx1, ty1 = TOWER
    a = APRON
    tmx, tmy = (mx1 + tx1) // 2, (ty0 + ty1) // 2
    facade = FACADES["old_crossing"]
    stone = INTERIORS["church"].wall
    roof_tile = INTERIORS["church"].ceiling
    links = 0
    ROOF_FACES.clear()

    def link(left, right, start, end):
        nonlocal links
        links += 1
        gates.append((f"connection:church_massing_{links}",
                      getattr(left, "region_id", left),
                      getattr(right, "region_id", right),
                      tuple(start), tuple(end), 0))

    def edges(room):
        points = [tuple(p) for p in room.world_outline()]
        return list(zip(points, points[1:] + points[:1]))

    # ---- sky raised, never lowered: the tower's street faces ------------
    def gable(name, outline, hinge, half, note):
        reach = depth(outline, hinge)
        return skyline.apron(
            parish, name, outline, wall_height=TOWER_HEIGHT, floor_z=GRADE,
            sky_picnum=SKY, wall_picnum=stone, floor_picnum=facade.floor,
            floor_shade=floor_shade, layer="street", note=note,
            ceiling_slope=SlopeSpec(hinge=hinge,
                                    rise_z=TOWER_GABLE * reach / half))

    north_w = gable("tower_north_w", [
        (mx1, ty0 - a), (tmx, ty0 - a), (tmx, ty0), (mx1, ty0)],
        ((tmx, ty0 - a), (tmx, ty0)), tmx - mx1,
        "the tower's north gable, west half")
    north_e = gable("tower_north_e", [
        (tmx, ty0 - a), (tx1 + a, ty0 - a), (tx1, ty0), (tmx, ty0)],
        ((tmx, ty0), (tmx, ty0 - a)), tx1 - tmx,
        "the tower's north gable, east half")
    east_n = gable("tower_east_n", [
        (tx1, ty0), (tx1 + a, ty0 - a), (tx1 + a, tmy), (tx1, tmy)],
        ((tx1 + a, tmy), (tx1, tmy)), tmy - ty0,
        "the tower's avenue gable, north half")
    east_s = gable("tower_east_s", [
        (tx1, tmy), (tx1 + a, tmy), (tx1 + a, ty1 + a), (tx1, ty1)],
        ((tx1, tmy), (tx1 + a, tmy)), ty1 - tmy,
        "the tower's avenue gable, south half")
    south_e = gable("tower_south_e", [
        (tx1, ty1), (tx1 + a, ty1 + a), (tmx, ty1 + a), (tmx, ty1)],
        ((tmx, ty1 + a), (tmx, ty1)), tx1 - tmx,
        "the tower's south gable, east half")
    south_w = gable("tower_south_w", [
        (tmx, ty1), (tmx, ty1 + a), (mx1, ty1 + a), (mx1, ty1)],
        ((tmx, ty1), (tmx, ty1 + a)), tmx - mx1,
        "the tower's south gable, west half")
    ring = [north_w, north_e, east_n, east_s, south_e, south_w]
    for room, index in ((north_w, 0), (north_e, 0), (east_n, 1), (east_s, 1),
                        (south_e, 1), (south_w, 1)):
        link(room, street, *edges(room)[index])
    for left, index, right in ((north_w, 1, north_e), (north_e, 1, east_n),
                               (east_n, 2, east_s), (east_s, 2, south_e),
                               (south_e, 2, south_w)):
        link(left, right, *edges(left)[index])

    # ---- roofs: everything that is merely low --------------------------
    def top(name, outline, height, layer, note, *, tile=stone, sky=STREET_SKY,
            **slopes):
        made = skyline.roof(
            parish, name, outline, top_height=height, sky_height=sky,
            grade_z=GRADE, sky_picnum=SKY, wall_picnum=tile,
            top_picnum=roof_tile, top_shade=floor_shade, layer=layer,
            note=note, **slopes)
        ROOF_FACES[made.region_id] = tile
        return made

    ground_outline = [tuple(p) for p in ground.world_outline()]
    solid = (box(ax0, ay0, ax1, ay1).difference(box(*MASS))
             .difference(Polygon(ground_outline)))
    for rect in gate_rects:
        solid = solid.difference(box(*rect[:4]))
    yard_walls = []
    for index, piece in enumerate(getattr(solid, "geoms", [solid])):
        if piece.is_empty or piece.area < 256 * 256:
            continue
        if piece.interiors:
            raise ValueError("the churchyard wall encloses a hole; it needs "
                             "a gate through it to be one outline")
        outline = [(int(round(x)), int(round(y)))
                   for x, y in list(piece.exterior.coords)[:-1]]
        yard_walls.append((f"yard_wall_{index}", outline))

    # The low roof: the whole mass, less the tower's west strip and the nave.
    nx0, ny0, nx1, ny1 = next((r[1], r[2], r[3], r[4]) for r in ROOMS
                              if r[0] == "nave")
    ridge = (nx0 + nx1) // 2
    low_outline = [(mx0, my0), (mx1, my0), (mx1, ty0 - a), (mx1, ty0),
                   (mx1 - a, ty0), (mx1 - a, tmy), (mx1 - a, ty1), (mx1, ty1),
                   (mx1, ty1 + a), (mx1, my1), (mx0, my1)]
    neighbours = [ground_outline] + [outline for _n, outline in yard_walls]
    low_outline = _with_vertices(
        low_outline, [p for other in neighbours
                      for seg in _shared(low_outline, other) for p in seg])
    low = top("roof_low", low_outline, BODY_HEIGHT, "roof_low",
              "the low roof: aisle, chancel, vestry and narthex under it")
    low.carve([(nx0, ny0), (nx1, ny0), (nx1, ny1), (nx0, ny1)])

    walls = []
    for name, outline in yard_walls:
        outline = _with_vertices(
            outline, [p for seg in _shared(outline, low_outline) for p in seg])
        walls.append(top(name, outline, YARD_WALL_HEIGHT, "street",
                         "the churchyard wall: a wall you can see over",
                         tile=MASONRY.wall))

    # The tower's west face, rising out of the low roof under its own gable.
    tw_n = top("tower_west_n", [(mx1 - a, ty0), (mx1, ty0), (mx1, tmy),
                                (mx1 - a, tmy)], BODY_HEIGHT, "roof_low",
               "the tower's west gable over the roof, north half",
               sky=TOWER_HEIGHT,
               ceiling_slope=SlopeSpec(hinge=((mx1, tmy), (mx1 - a, tmy)),
                                       rise_z=TOWER_GABLE))
    tw_s = top("tower_west_s", [(mx1 - a, tmy), (mx1, tmy), (mx1, ty1),
                                (mx1 - a, ty1)], BODY_HEIGHT, "roof_low",
               "the tower's west gable over the roof, south half",
               sky=TOWER_HEIGHT,
               ceiling_slope=SlopeSpec(hinge=((mx1 - a, tmy), (mx1, tmy)),
                                       rise_z=TOWER_GABLE))
    link(tw_n, tw_s, (mx1, tmy), (mx1 - a, tmy))
    for strip in (tw_n, tw_s):
        for start, end in _shared([tuple(p) for p in strip.world_outline()],
                                  low_outline):
            link(strip, low, start, end)

    # The nave: two pitches hinged on their eaves, meeting at the ridge, so
    # each end of it is a gable.
    nave_w = top("roof_nave_w", [(nx0, ny0), (ridge, ny0), (ridge, ny1),
                                 (nx0, ny1)], NAVE_EAVES, "roof_nave",
                 "the nave roof, west pitch",
                 floor_slope=SlopeSpec(hinge=((nx0, ny1), (nx0, ny0)),
                                       rise_z=-NAVE_PITCH))
    nave_e = top("roof_nave_e", [(ridge, ny0), (nx1, ny0), (nx1, ny1),
                                 (ridge, ny1)], NAVE_EAVES, "roof_nave",
                 "the nave roof, east pitch",
                 floor_slope=SlopeSpec(hinge=((nx1, ny0), (nx1, ny1)),
                                       rise_z=-NAVE_PITCH))
    link(nave_w, nave_e, (ridge, ny0), (ridge, ny1))
    for half, indices in ((nave_w, (0, 2, 3)), (nave_e, (0, 1, 2))):
        for index in indices:
            link(half, low, *edges(half)[index])

    # The low roof's own neighbours: the street, the tower's ring, the yard.
    street_spans = [((mx0, my0), (mx1, my0)), ((mx1, my0), (mx1, ty0 - a)),
                    ((mx1, ty1 + a), (mx1, my1))]
    for start, end in street_spans:
        link(low, street, start, end)
    link(north_w, low, (mx1, ty0), (mx1, ty0 - a))
    link(south_w, low, (mx1, ty1 + a), (mx1, ty1))
    for start, end in _shared(low_outline, ground_outline):
        link(low, ground, start, end)

    # The yard wall's: ground inside, street outside, the church at its ends.
    area_box = [(ax0, ay0), (ax1, ay0), (ax1, ay1), (ax0, ay1)]
    for wall in walls:
        outline = [tuple(p) for p in wall.world_outline()]
        for start, end in _shared(outline, ground_outline):
            link(wall, ground, start, end)
        for start, end in _shared(outline, area_box):
            link(wall, street, start, end)
        for start, end in _shared(outline, low_outline):
            link(wall, low, start, end)
        # A gate through the wall: its jambs are the wall's own ends, and
        # are drawn only as tall as the wall is.
        for x0, y0, x1, y1, gate_region in gate_rects:
            for start, end in _shared(
                    outline, [(x0, y0), (x1, y0), (x1, y1), (x0, y1)]):
                link(wall, gate_region, start, end)

    APRONS[:] = [room.region_id for room in ring]
    _FACES.clear()
    _FACES.update({
        "avenue": (street.region_id, mx1), "row": (street.region_id, my0),
        # Twin belfry lights either side of each ridge, each stated in its
        # own gable's winding so the glass faces the street.
        "tower": {
            "north_w": (north_w.region_id, (tmx - 64, ty0), (tmx - 448, ty0)),
            "north_e": (north_e.region_id, (tmx + 448, ty0), (tmx + 64, ty0)),
            "east_n": (east_n.region_id, (tx1, tmy - 64), (tx1, tmy - 448)),
            "east_s": (east_s.region_id, (tx1, tmy + 448), (tx1, tmy + 64)),
            "south_e": (south_e.region_id, (tmx + 64, ty1), (tmx + 448, ty1)),
            "south_w": (south_w.region_id, (tmx - 448, ty1), (tmx - 64, ty1)),
        },
    })
    return {"south_w": south_w, "south_e": south_e, "ridge_x": tmx,
            "roof_low": low, "yard_walls": walls}


def glaze(layout) -> dict:
    """Hang the lancets on the faces `massing` made.  Returns what it hung."""
    import wallplane
    hung, refused = [], []

    def lancet(name, region_id, a1, a2, *, height=LANCET["height"],
               on_step=False):
        placement = f"church:lancet_{name}"
        if not on_step:
            got = wallplane.sprite(
                layout, placement, region_id, a1, a2,
                tile=LANCET["tile"], x_repeat=LANCET["x_repeat"],
                y_repeat=LANCET["y_repeat"], cstat=LANCET["cstat"], t=0.5,
                height_player_heights=height, offset_player_widths=0.02)
        else:
            # The church's street faces are the lower step of a two-sided
            # wall now: a portal in the span table, solid up to the eaves.
            # `wallplane.sprite` reads a portal as an opening; `find_slot`
            # takes the caller's word that this one is a step.
            left, right, above, below = wallplane.extents(
                LANCET["tile"], LANCET["x_repeat"], LANCET["y_repeat"],
                LANCET["cstat"])
            slot = wallplane.find_slot(
                layout, region_id, a1, a2, width=left + right, above=above,
                below=below, t=0.5, height_player_heights=height,
                offset_player_widths=0.02, over_steps=True)
            got = slot and layout.place_on_wall(
                placement, region_id, a1=a1, a2=a2, t=slot[0],
                height_player_heights=slot[1], offset_player_widths=0.02,
                type=0, picnum=LANCET["tile"], cstat=LANCET["cstat"],
                x_repeat=LANCET["x_repeat"], y_repeat=LANCET["y_repeat"])
        (hung if got else refused).append(name)

    region_id, x = _FACES["avenue"]
    for centre in LANCETS_AVENUE:
        lancet(f"avenue_{centre}", region_id, (x, centre + 192),
               (x, centre - 192), on_step=True)
    region_id, y = _FACES["row"]
    for centre in LANCETS_ROW:
        lancet(f"row_{centre}", region_id, (centre + 192, y),
               (centre - 192, y), on_step=True)
    # The belfry lights, under the gables.
    for face, (region_id, a1, a2) in _FACES["tower"].items():
        # (the south face has the door's reveal under it: a portal in the
        # span table, masonry at this height)
        lancet(f"tower_{face}", region_id, a1, a2, height=BELFRY_HEIGHT,
               on_step=face.startswith("south"))
    return {"hung": hung, "refused": refused}


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

#: THE WAY IN IS THROUGH THE TOWER, and nowhere else.
#:
#: Until 2026-11-17 the church had a portal in its avenue face and a door in
#: its cemetery face.  Both are gone, and the reason is the engine's, not
#: taste.  Build keeps one open span per screen column.  Once the church's
#: walls are low enough to see over, the columns above them stay open for the
#: roof and the tower -- and anything the renderer reaches through a door in
#: that wall paints into them too.  Measured with the avenue portal standing
#: open: 18,000 to 23,000 pixels of narthex ceiling smeared across the sky
#: over the facade (`experiments/church-roofs/README.md`).  Closed, the porch
#: alone left a "pole" beside the door that a blind reviewer found in five
#: frames.  `bloodmap.layers` states the law: the space you enter the ground
#: floor from must not also open into the storey above it through the same
#: facade.
#:
#: The tower is the one face of the church nothing is seen over: its walls
#: are one-sided to their own tall sky and close every column they cover.
#: So the door is in the tower's south return, a side porch facing down the
#: avenue toward the spawn; it opens into the belfry, which lies wholly
#: inside the tower's plan; and a second door stands between the belfry and
#: the rooms under the roof, so the renderer never reaches those from the
#: street unless both stand open.
PORTALS: list = []
#: (name, x0, y0, x1, y1): the outer leaf in the tower's south wall, its
#: reveal on the pavement side, and the inner leaf in its west wall.
#: Both shut themselves three seconds after opening -- the campaign's own
#: commonest wait.  With both leaves standing open the rooms under the roof
#: can be reached from the avenue through the tower, and they paint 6,000
#: to 14,000 pixels of ceiling into the sky (measured:
#: `round3-both-doors-open`).  A player cannot open the second, get back
#: outside and look, in three seconds.
DOOR_CLOSES = 30
TOWER_DOOR = ("tower_door", 32896, 23808, 33920, 24064)
TOWER_PORCH = ("tower_porch", 32896, 24064, 33920, 24320)
TOWER_INNER = ("tower_inner_door", 32640, 22784, 32896, 23808)

#: Furniture, all of it geometry: (room, x0, y0, x1, y1, rise, note).
#: The hand table that used to live here is gone: it iterated four pews and
#: a font into `church_furniture_0` .. `church_furniture_4`.
#: `templates.chapel_furnishing` and `templates.font` place the same
#: geometry under their own names.  Four pews ARE a rhythm and keep an
#: index; the font is not one and does not.


def build(city, street, ground, gates, area_rect, gate_rects=()):
    """The church, its portals, and the connections that carry them."""
    facade = FACADES["old_crossing"]
    parish = city.assembly(
        "st_gallows",
        style=Style(layer="church_low", **INTERIORS["church"].style_kwargs(
            floor_z=GRADE, clear_height=65536)),
        note="St Gallow's: nave, chancel, apse, tower, vestry, narthex",
    )
    import citytree
    citytree.declare_venue(parish, "church", "church_complex",
                           built_by="l3_church")
    # Declared and not built: the tower has a bell chamber in the plan and
    # nothing in it yet.  A named empty node says that; an absent one says
    # nothing at all.
    citytree.plan(parish, "bell_chamber",
                  "the tower's bell chamber -- church-patterns.md wants the "
                  "vista silhouette; no geometry yet")
    rooms: dict = {}
    from resolution import DISTRICT_STYLE
    aprons = massing(parish, city, street, ground, gates, area_rect,
                     gate_rects,
                     floor_shade=DISTRICT_STYLE["old_crossing"]["floor_shade"])

    def make(name, x0, y0, x1, y1, key, clear, note, *, role="interior",
             floor_z=GRADE, rk=None):
        material = INTERIORS[key]
        made = parish.room(
            name, [(0, 0), (x1 - x0, 0), (x1 - x0, y1 - y0), (0, y1 - y0)],
            role=role, faces=dict(COMPASS), frame=Frame(int(x0), int(y0)),
            region_kwargs={**material.region_kwargs(), **(rk or {})},
            note=note)
        made.surfaces(**material.style_kwargs(floor_z=floor_z,
                                              clear_height=clear))
        if name in TALL_ROOMS or name.startswith("tower_door") \
                or name == "tower_porch":
            # the belfry and what opens off it stand in the tower, with
            # no roof over them
            made.surfaces(layer="church_tall")
        rooms[name] = made
        return made

    for name, x0, y0, x1, y1, key, clear, note in ROOMS:
        # The chancel and its apse stand a step over the nave: the one
        # height difference in a church that means something.
        rise = CHANCEL_RISE if name in ("chancel", "apse") else 0
        # A church has a pitched roof.  Gravesend had 0 sloped surfaces in
        # 182 sectors against a campaign median of 21.7%, and
        # `bloodmap.slope` was sitting unused the whole time -- a sloped
        # ceiling "costs nothing but headroom", which is exactly what a
        # nave has spare.  Campaign rise median is 1.29 player heights.
        rk = None
        if name == "nave":
            rk = {"ceiling_slope": SlopeSpec(
                hinge=((x0, y1), (x0, y0)), rise_z=-PITCH)}   # the west edge, in the outline's own winding
        make(name, x0, y0, x1, y1, key, clear - rise, note,
             floor_z=GRADE - rise, rk=rk)
    for small, sf, big, bf in JOINS:
        parish.connect(rooms[small].face(sf), rooms[big].face(bf),
                       connection_id=f"connection:church_{small}_{big}")

    material_of = {row[0]: row[5] for row in ROOMS}

    def leaf(name, x0, y0, x1, y1, height):
        made = make(name, x0, y0, x1, y1, "church", 0, f"the {name} leaf",
                    role="doorway",
                    rk={"type": 600, "door_face": 22, "inherit_finish": "both",
                        "sector_behavior": z_motion_door(
                            GRADE, GRADE - height, close_after=DOOR_CLOSES)})
        made.surfaces(wall_picnum=facade.opening, floor_z=GRADE, clear_height=0)
        return made

    tall = PORTAL_H["tower"]
    outer = leaf(*TOWER_DOOR, tall)
    porch = make(*TOWER_PORCH, "church", tall, "the tower door's reveal",
                 role="gateway")
    porch.surfaces(wall_picnum=facade.opening, ceiling_picnum=facade.opening,
                   floor_z=GRADE, clear_height=tall)
    inner = leaf(*TOWER_INNER, DOOR_H)
    parish.connect(outer.face("north"), rooms["belfry"].face("south"),
                   connection_id="connection:church_tower_door_in")
    parish.connect(porch.face("north"), outer.face("south"),
                   connection_id="connection:church_tower_porch")
    parish.connect(inner.face("west"), rooms["tower"].face("east"),
                   connection_id="connection:church_tower_inner_west")
    parish.connect(inner.face("east"), rooms["belfry"].face("west"),
                   connection_id="connection:church_tower_inner_east")
    # The reveal opens onto the tower's own ring of raised sky, which is two
    # sectors along this face; a face may carry more than one opening.
    px0, py, px1 = TOWER_PORCH[1], TOWER_PORCH[4], TOWER_PORCH[3]
    ridge_x = aprons["ridge_x"]
    for half, (x0, x1) in ((aprons["south_w"], (px0, ridge_x)),
                           (aprons["south_e"], (ridge_x, px1))):
        gates.append((f"connection:church_tower_porch_{x0}", half.region_id,
                      porch.region_id, (x0, py), (x1, py)))

    # The altar, through the two-tier constructor: class of 42 pieces
    # across 16 maps, rise 0.60-0.97 player heights.  It was a single block
    # at 4,096 -- a quarter of a player -- which is a doorstep, not an altar.
    setpieces.altar(parish, "altar", rooms["chancel"],
                    (28928, 22784, 30208, 23808),
                    INTERIORS["sanctuary"], grade=GRADE - CHANCEL_RISE,
                    host_clear=49152 - CHANCEL_RISE,
                    note="the altar, from the mined two-tier class")

    import templates
    nave_clear = next(r[6] for r in ROOMS if r[0] == "nave")
    templates.chapel_furnishing(
        rooms["nave"], material=INTERIORS[material_of["nave"]],
        grade=GRADE, host_clear=nave_clear, pews=4)
    templates.font(
        rooms["narthex"], material=INTERIORS[material_of["narthex"]],
        grade=GRADE,
        host_clear=next(r[6] for r in ROOMS if r[0] == "narthex"))
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
    glass = glaze(layout)
    print("church glass:", glass)
    return placed + len(glass["hung"])
