"""St Gallow's: the parish church, Gravesend's mandatory landmark.

Built to the contract in `knowledge/blood/references/church-patterns.md`, which mined E1M5
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
sectors run q3 8.39 Mu^2 against E3M1's 1.05, with 23% of them over 10M
against E3M1's 2%: we build halls where the campaign builds warrens, and
that single fact drives the level's ceiling share, its dead-end fraction
and its missing loops.  Eight rooms in six by ten plan units, braided so
that the nave touches five of them, is the shape the measurement asks for.
"""

from __future__ import annotations

import wires
from bloodmap import wiring

from bloodmap.doors import z_motion_door
from bloodmap.levelprog import Frame, RECT_FACES, Style
from bloodmap.slope import SlopeSpec

import setpieces
from materials import FACADES, INTERIORS, MASONRY, Material
from resolution import GRADE, PU

COMPASS = dict(zip(RECT_FACES, range(4)))

#: The mass, and the margin rooms keep from its faces so that a door and
#: its porch have somewhere to be.
MASS = (26 * PU, 21 * PU, 32 * PU, 31 * PU)
DOOR_D = PORCH_D = 256
# Blood's ceiling-lifting doors (594 in the campaign) open to a median of
# 28,672 -- 1.69 player heights -- and 87% are taller than a body.  The
# 31,744 used here is the median over all 1,231 type-600 sectors, lifts
# included, not a door height; it is kept because changing it moves every
# door in Gravesend.  Ours were 16,384, which is 0.97 of a player height: the owner
# called them "short like for midgets" and the census agrees.  Blood has
# no door TEXTURE to lean on (E3M1's own door leaves wear 379 and 449,
# plain wall stone), so an opening reads as a door through its proportion
# and its reveal -- which makes this number the whole fix.
DOOR_H = 31744
#: The tower door stands 2.4 bodies: a square door was read, twice, as "a
#: garage door", and this one is 1024 wide by 2560 tall.
PORTAL_H = {"tower": 40960}

CHANCEL_RISE = 2048        # the chancel stands over the nave, one low step
#: How much taller the nave gets across its span: 21,878 units, 1.29 player
#: heights. The campaign's median slope rise is 0.43 (about 7,290 units).
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
    ("crypt_stair", 30720, 25600, 31232, 27136, "crypt", 32768,
     "the crypt's antechamber: the slab in its east wall goes down"),
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
#: The crypt. The owner, 2026-11-18: "in church I see that it says crypt,
#: but shouldn't there be access to crypt? the crypt should be under the
#: church, you might need to move some obelisk or something to get there".
#: The sign hung in a room called `crypt_stair` that had no stair and
#: nothing beneath it.
#:
#: Nothing is under the church (the sewer runs under the avenue, east of x
#: 32,768), so the crypt lies under the narthex at the sewer's depth, on a
#: layer of its own. The way down is the thing that moves: a stone slab in
#: the antechamber's east wall, a Z-motion sector whose FLOOR travels the
#: 3.1 bodies between the church and the crypt (E3M2 has 28 such lifts).
#: (It sank when it was stepped on until 2026-11-25. The owner: "should be done the
#: way that you need to press skull switch or something instead of going up and down
#: when you just get into it.") The skull it carries sends it; the skull at either
#: stop calls it: `slab_switches`.
CRYPT_SHAFT_X = 31744
#: SIZES, redone. The owner walked the first crypt: "crypt feels tiny,
#: crypt elevator is just for a player to stand, but there is really no
#: negative space. That hole that get blown into sewers is just a narrow
#: strip instead of looking like a actual hole." It was 1,536 by 3,328
#: under 1.45 bodies -- 2.6 m by 5.6 m with a 2.6 m ceiling -- with a lift
#: 512 square and a hole 512 wide; `scale.py` has what Blood builds.
#:
#: The lift is 1,024 square (campaign median 600 by 1,408). The crypt runs
#: under the nave AND the narthex: 4,096 by 3,840 (7 m by 6.5 m, the
#: campaign's median indoor room is 14M and this is 15.7M) under 2.4
#: bodies. The tombs stand FREE in two rows down the middle, 768 by 1,280,
#: with a 1,024 aisle along each wall and 512 between the rows: floor to
#: walk round, which is what "negative space" is.
CRYPT_LIFT = (31232, 25856, 32256, 26880)
CRYPT = (28160, 26880, 32256, 30720)
CRYPT_FLOOR, CRYPT_CLEAR = 61440, 40960
LIFT_CLEAR = 28672
#: The top of the shaft is a linked floor, as E4M4's is (s159 under s154), so that the crypt and all under it need not stand
#: under the church (`references/sewers-outside.md`). The plane is the church's floor; the slab stops a step under it,
#: where a body standing on it has its middle over the plane and is the church's already.
SLAB_TOP, SLAB_LINK = GRADE + 4096, 20
LIFT_TIME = 40                                 # four seconds for 53,248
TOMBS = ()                       # (the four grey boxes are gone)
TOMB_RISE = 10240
#: WHAT A CRYPT IS. The owner, on the enlarged one: "The crypt doesn't
#: really look like a crypt, check E1M1 for reference". It was a room of
#: neat grey brick with four plain boxes in it.
#:
#: E1M1's (sector 150, looked at in six frames with the control sprites
#: hidden): walls of COBBLESTONE (110), an EARTH floor (270) under dark
#: worked stone (253); ONE sarcophagus as the thing the room is for -- a
#: stone chest whose sides stand a third of a body, then a bevelled
#: shoulder 256 wide rising 2,048 (sectors 1-3: floor 273, heinum -2048,
#: hinged on the outer edge), then a WOODEN lid (504) a lip above it (28:
#: 1,920 by 1,024), its faces grey brick (421); gold burial PLAQUES on
#: the walls (128, palette 8, 48 by 48, 1.2 bodies up: sprites 185-189,
#: kThingObjectExplode, so a blast breaks them); and COBWEBS hung from the
#: ceiling in open air (1067/1068, sprites 150-154, translucent, 64 by
#: 76). Every field below is E1M1's.
CRYPT_WALL, CRYPT_EARTH, CRYPT_VAULT = 110, 270, 253
#: the lid, in world units; the shoulder runs 256 outside it
#: The lid is CLOSED. The owner, on the first version, which had E1M1's
#: wooden top: "there is that ROR which I wouldn't use here, so instead of
#: it just put a sarcophagus texture on the top of it and it will look
#: good, like closed sarcophagus". E1M1's planks are the coffin the player
#: climbs out of. E3M8 has the closed one (s249, s445): tile 128, the
#: carved figure, laid as the FLOOR of a chest top 1,024 by 2,048 -- the
#: tile is 64 by 128, so that is the whole figure once, at Blood's scale.
SARCOPHAGUS = (29696, 27904, 30720, 29952)
SHOULDER = 256
CHEST_SIDE, SHOULDER_RISE, LID_RISE = 6144, 2048, 8192
#: (The owner, a minute after the carved figure went on: "picnum 346 is
#: what I meant for that top of the coffin" -- his "gravestone". E1M1 lays
#: it exactly so, on its two flanking tombs: s0 and s9, 2,048 by 1,024,
#: floor_stat 64, the tile begun at the tomb's own first wall.)
SHOULDER_TILE, LID_TILE, CHEST_FACE = 273, 346, 421
PLAQUE = {"type": 417, "picnum": 128, "cstat": 464, "x_repeat": 48,
          "y_repeat": 48, "status": 4, "pal": 8, "shade": 4,
          "behavior": {"data_1": 5, "data_2": 5, "data_3": 5, "data_4": 502}}
#: (a1, a2): short stretches of wall, wound with the room on the left
PLAQUES = (((28160, 28672), (28160, 27904)), ((28160, 30208), (28160, 29440)),
           ((29440, 30720), (28672, 30720)), ((31744, 30720), (30976, 30720)))
COBWEB = {"type": 417, "cstat": 146, "x_repeat": 64, "y_repeat": 76,
          "status": 4, "shade": -28, "behavior": {"data_1": 6}}
#: (tile, x, y, angle): in the open, under the vault
COBWEBS = ((1067, 28800, 27520, 512), (1067, 31200, 27900, 0),
           (1068, 28900, 30100, 0), (1067, 30208, 27300, 512),
           (1067, 31500, 30300, 512))
#: region id -> the tile its raised faces wear (`skyline.dress_steps`)
CRYPT_FACES: dict = {}
#: The breach. The owner, 2026-11-18: "We can add something that will
#: connect crypt to sewers, like a wall crack that you need use explosive
#: to ... It should also make sense in space relations". It does: the
#: sewer trunk runs under the avenue, and the avenue is the far side of
#: the crypt's east wall -- 512 of earth between them. So that wall is
#: cracked, between the two eastern tombs, and the same crack shows in the
#: sewer; a bundle of TNT lies by a tomb. E6M1 sprite 262 is the assembly:
#: a kThingWallCrack (tile 1127, which only an explosion breaks) sending
#: on its death to a shut Z-motion sector, with E3M1's staggered charges.
#: The hole: 1,536 wide (campaign blast holes: median 1,280 wide and 1.45
#: bodies, upper quartile 1,792 and 1.8), ragged the way Blood's are
#: (`bloodmap.breach`; the owner, 2026-11-22: "Blown out holes are usually
#: using sloped floor and ceiling and usually aren't regular"): four pieces
#: with slanted seams, each pitched its own way, the middle two at least
#: 1.45 bodies clear and the ends low rubble shoulders. Its near side is
#: the crypt, where the fuse of barrels is lit and the hole is seen from;
#: the sewer's vault, 1.2 bodies at its wall, cuts its top on the far side.
BREACH = (32256, 28672, 32768, 30208)
BREACH_SILL = (256, 1536)
#: a standing body and this, everywhere in a middle piece: 1.47 bodies, over
#: the campaign's median hole (1.45, `scale.HOLE_MEDIAN`)
BREACH_HEADROOM = 7936
BREACH_TOP = 32768
#: the broken faces are the crypt wall's own rubble
BREACH_MATERIAL = Material(wall=CRYPT_WALL, floor=CRYPT_WALL, ceiling=CRYPT_WALL,
                           opening=CRYPT_WALL, note="the crypt breach: its own rubble")


def breach_pieces() -> list:
    """The crypt breach's pieces, in its own frame (`bloodmap.breach.ragged`)."""
    from bloodmap import breach
    x0, y0, x1, y1 = BREACH
    return breach.ragged(y1 - y0, x1 - x0, seed="church:crypt_breach", sill=BREACH_SILL,
                         top=BREACH_TOP, headroom=BREACH_HEADROOM)


#: the breach's rooms as built, west to east they open crypt to sewer
BREACH_ROOMS: list = []
BREACH_CHANNEL = wires.channel("church:breach")
BREACH_HOLE = 20480
#: The powder store. The owner again: "Maybe we can have it as a TNT
#: barrels storage or something with cascade explosions (check other
#: levels for similar things)". Blood does exactly this: its TNT barrels
#: (type 400, tile 907, cstat 385, 64 by 64) stand in threes about 512
#: apart, and three of the campaign's four such stacks stand within 1,200
#: of a wall crack (E1M8 s390, E2M9 s1, E1M2 s270). A barrel sets off its
#: neighbour, so a line of them is a fuse: shoot the first from the slab
#: and the last one takes the wall. World x, y, down the aisle and round
#: to the crack; 512 apart.
BARRELS = ((31744, 27392), (31744, 27904), (31744, 28416), (31744, 28928),
           (31936, 29440))
BARREL = {"type": 400, "picnum": 907, "cstat": 385, "x_repeat": 64,
          "y_repeat": 64, "status": 4}
BARREL_LIFT = 5888             # its drawn half height: it stands on the floor
CRACK = {"type": 408, "picnum": 1127, "cstat": 16 | 64 | 128, "x_repeat": 64,
         "y_repeat": 64, "status": 4,
         "behavior": {"tx_id": BREACH_CHANNEL, "command": 1, "trigger_on": 1,
                      "trigger_off": 1, "trigger_once": 1}}

#: region id -> sector type, set by the build once the doors are framed
LATE_TYPES: dict = {}

LAYERS = {
    "crypt": (GRADE, CRYPT_FLOOR + 4096,
              "St Gallow's crypt, under the narthex"),
    "church_low": (GRADE - 57344, GRADE, "St Gallow's rooms under the low roof"),
    "church_tall": (GRADE - 81920, GRADE, "the nave and the belfry"),
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
    from bloodmap import wallplane
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
    # A torch by the tower's door, on the pier the avenue's side of it: blind readers of the street could not find the way in.
    import props
    _tx0, _ty0, tx1, ty1 = TOWER
    layout.place_on_wall("church:door_torch", _FACES["tower"]["south_e"][0], a1=(TOWER_PORCH[3], ty1), a2=(tx1, ty1), t=0.5,
                         height_player_heights=1.55, offset_player_widths=0.06, emits_light=True, **props.fields(props.FLAME))
    # and what says from the avenue that this is the church, and its door: the haloed window over it, lit from within, and the name on
    # the wall beside it (a blind reader: "The small wooden door gets lost at the foot of the tower").
    from shapely import Point, Polygon

    def there(x, y):
        return next(r.region_id for r in layout.regions.values() if r.parallax_ceiling and r.floor_z == GRADE
                    and Polygon(r.outer, r.holes).contains(Point(x, y)))
    over = (TOWER_PORCH[1] + TOWER_PORCH[3]) // 2
    layout.add_sprite("church:door_window", there(over, ty1 + 10), x=over, y=ty1 + 10, z=GRADE - 72000, picnum=GREAT_WINDOW["tile"], x_repeat=48,
                      y_repeat=64, angle=512, cstat=16 | 64 | 128, shade=-12)
    for k, letter in enumerate(NAME):
        if letter != " ":
            y = NAME_AT[0] + round((len(NAME) - 1) / 2 * NAME_PITCH) - k * NAME_PITCH
            layout.add_sprite(f"church:name_{k}", there(MASS[2] + 12, y), x=MASS[2] + 10, y=y, z=GRADE - NAME_AT[1],
                              picnum=3808 + ord(letter) - ord("A"), x_repeat=64, y_repeat=64, angle=0, cstat=16 | 64 | 128, shade=-4)
    return {"hung": hung, "refused": refused}


#: the name on the avenue's wall: its middle along it and how far up, between the plinth and the string course
NAME, NAME_AT, NAME_PITCH = "ST GALLOWS", (25984, 24500), 150


#: The glass, from inside. The owner, 2026-11-18: "Church looks good from
#: the outside, but inside doesn't fully correspond ... I would add these
#: stained window glass decorative sprites also inside to be like a
#: counterpart of what is outside, to have a feeling that you are really
#: inside that church." Sixteen lancets outside and not one within: the
#: nave touched no glazed wall.
#:
#: Blood pairs a window by position (E1M5 walls 29/31: one masked wall, an
#: arch sprite duplicated on each face at the same x) and also hangs glass
#: inside with nothing outside (E3M2 s312-314, DWE1M4 s822-835), brighter
#: than its wall. So: a CLERESTORY in the nave at the avenue lancets' own
#: stations, on both sides, in the wall over the aisle and the side rooms
#: -- the height the lancets have outside (sill 1.95 to head 3.4; here 2.45
#: so the sill clears the narthex arch, 2.42) -- and a lower light on the
#: inside of each glazed outer wall a room really has.
CLERESTORY = {"y_repeat": 176, "height": 2.45}
CANDELABRUM_LIFT = 0.0          # set below from the tile's own height
GLASS_SHADE = 8                     # the walls stand at 27-31
#: (room, face, the station along the wall, y_repeat, sill in bodies)
INSIDE_LIGHTS = (
    ("narthex", "east", 29184, 160, 0.9), ("narthex", "east", 28160, 160, 0.9),
    ("vestry", "east", 25216, 128, 0.7),
    #: the east end has ONE subject (the church study: "our twelve
    #: identical lancets are why the reviewer said stamped"): the great
    #: window below, flanked by two narrow lights
    ("apse", "north", 28800, 128, 0.9), ("apse", "north", 30080, 128, 0.9),
)
#: The great window behind the altar: tile 265, a haloed figure, which
#: E3M2 s312-314 hangs so; no see-through pixels, so it may hang on a
#: solid wall. The apse is only 1,536 wide, so it is 960 by a body and a
#: half, between the two narrow lights: the brightest thing in sight.
GREAT_WINDOW = {"tile": 265, "x_repeat": 48, "y_repeat": 80, "sill": 0.8,
                "shade": -6, "station": 29440}
#: DWE1M4 sprites 314/315: a candelabrum at each south corner of the chancel
CANDELABRUM = {"type": 0, "picnum": 580, "cstat": 385, "x_repeat": 64,
               "y_repeat": 64, "shade": -6, "status": 0}


def glaze_inside(layout, rooms) -> dict:
    """The inside counterparts of `glaze`'s lancets."""
    import props
    from bloodmap import wallplane
    hung, refused = [], []

    def light(name, room, face, station, y_repeat, sill, over_steps):
        x0, y0, x1, y1 = (int(v) for v in props.room_rect(room))
        half = 192
        a1, a2 = {"east": ((x1, station - half), (x1, station + half)),
                  "west": ((x0, station + half), (x0, station - half)),
                  "north": ((station - half, y0), (station + half, y0)),
                  "south": ((station + half, y1), (station - half, y1))}[face]
        left, right, above, below = wallplane.extents(
            LANCET["tile"], LANCET["x_repeat"], y_repeat, LANCET["cstat"])
        slot = wallplane.find_slot(
            layout, room.region_id, a1, a2, width=left + right, above=above,
            below=below, t=0.5, height_player_heights=sill,
            offset_player_widths=0.02, slide=False, stack=False,
            over_steps=over_steps)
        got = slot and layout.place_on_wall(
            f"church:inside_{name}", room.region_id, a1=a1, a2=a2, t=slot[0],
            height_player_heights=slot[1], offset_player_widths=0.02,
            type=0, picnum=LANCET["tile"], cstat=LANCET["cstat"],
            x_repeat=LANCET["x_repeat"], y_repeat=y_repeat,
            shade=GLASS_SHADE)
        (hung if got else refused).append(name)

    nave = rooms["nave"]
    _x0, ny0, _x1, ny1 = (int(v) for v in props.room_rect(nave))
    for station in LANCETS_AVENUE:
        if not ny0 + 256 <= station <= ny1 - 256:
            continue
        for face in ("east", "west"):
            light(f"clerestory_{face}_{station}", nave, face, station,
                  CLERESTORY["y_repeat"], CLERESTORY["height"], True)
    for room, face, station, y_repeat, sill in INSIDE_LIGHTS:
        light(f"{room}_{station}", rooms[room], face, station, y_repeat,
              sill, False)
    apse = rooms["apse"]
    ax0, ay0, ax1, _ay1 = (int(v) for v in props.room_rect(apse))
    got = wallplane.sprite(
        layout, "church:great_window", apse.region_id, (ax0, ay0), (ax1, ay0),
        tile=GREAT_WINDOW["tile"], x_repeat=GREAT_WINDOW["x_repeat"],
        y_repeat=GREAT_WINDOW["y_repeat"], cstat=LANCET["cstat"],
        t=(GREAT_WINDOW["station"] - ax0) / (ax1 - ax0),
        height_player_heights=GREAT_WINDOW["sill"],
        offset_player_widths=0.02, shade=GREAT_WINDOW["shade"])
    (hung if got else refused).append("great_window")
    chancel = rooms["chancel"]
    for index, u in enumerate((0.08, 0.92)):
        layout.place_on_floor(
            f"church:candelabrum_{index}", chancel.region_id,
            local=(u, 0.9), height_player_heights=CANDELABRUM_LIFT,
            **CANDELABRUM)
    return {"hung": len(hung), "refused": refused}


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
        # 182 sectors against a campaign median of 9.5% of surfaces (15% of
        # sectors), and
        # `bloodmap.slope` was sitting unused the whole time -- a sloped
        # ceiling "costs nothing but headroom", which is exactly what a
        # nave has spare.  Campaign rise median is 0.43 player heights.
        rk = None
        if name == "nave":
            rk = {"ceiling_slope": SlopeSpec(
                hinge=((x0, y1), (x0, y0)), rise_z=-PITCH)}   # the west edge, in the outline's own winding
        make(name, x0, y0, x1, y1, key, clear - rise, note,
             floor_z=GRADE - rise, rk=rk)
    for small, sf, big, bf in JOINS:
        parish.connect(rooms[small].face(sf), rooms[big].face(bf),
                       connection_id=f"connection:church_{small}_{big}")

    # ---- the crypt, and the slab that goes down to it -------------------
    shaft = make("crypt_shaft", *CRYPT_LIFT, "crypt", LIFT_CLEAR,
                 "the head of the slab's shaft, in the antechamber's east wall: its floor is the link",
                 role="gateway")
    lift = make("crypt_lift", *CRYPT_LIFT, "crypt", SLAB_TOP - GRADE,
                "the slab: a lift between the antechamber and the crypt",
                role="gateway", floor_z=SLAB_TOP,
                rk={"sector_behavior": {
                    "off_floor_z": SLAB_TOP, "on_floor_z": CRYPT_FLOOR,
                    "off_ceiling_z": GRADE, "on_ceiling_z": GRADE,
                    "busy_time_a": LIFT_TIME, "busy_time_b": LIFT_TIME}})
    lift.surfaces(layer="crypt")
    #: Typed after the door pass: `frame_z_doors` takes every type-600
    #: region for a door leaf between two opposite edges, and a lift is
    #: entered from one side above and left by another below.
    LATE_TYPES[lift.region_id] = 600
    crypt = make("crypt", *CRYPT, "crypt", CRYPT_CLEAR,
                 "the crypt under the narthex: four tombs",
                 floor_z=CRYPT_FLOOR, rk={"declared_zero_exit": True})
    crypt.surfaces(layer="crypt")
    parish.connect(shaft.face("west"), rooms["crypt_stair"].face("east"),
                   connection_id="connection:church_crypt_lift_top")
    parish.connect(lift.face("south"), crypt.face("north"),
                   connection_id="connection:church_crypt_lift_bottom")
    from bloodmap import breach
    # the near side is the crypt's east wall (x 32,256), the hole running
    # north along it from its south end and east through it to the sewer
    BREACH_ROOMS.clear()
    for index, piece in enumerate(breach.lay(
            parish, "crypt_breach", breach_pieces(), origin=(BREACH[0], BREACH[3]),
            along=(0, -1), through=(1, 0), near_floor=CRYPT_FLOOR,
            region_kwargs=BREACH_MATERIAL.region_kwargs(), rx_id=BREACH_CHANNEL,
            note="the cracked wall between the crypt and the sewer",
            surfaces={**BREACH_MATERIAL.style_kwargs(floor_z=CRYPT_FLOOR, clear_height=0),
                      "layer": "crypt"})):
        rooms[piece.node_id] = piece
        BREACH_ROOMS.append(piece.node_id)
        wires.wire("church:breach").then(wiring.region(piece.region_id))
        #: typed after the door pass, like the lift: pieces side by side
        #: are a hole, not doors
        LATE_TYPES[piece.region_id] = 600
        parish.connect(piece.face("near"), crypt.face("east"),
                       connection_id=f"connection:church_crypt_breach_{index}")
    crypt.surfaces(wall_picnum=CRYPT_WALL, floor_picnum=CRYPT_EARTH,
                   ceiling_picnum=CRYPT_VAULT, floor_shade=34,
                   ceiling_shade=28, wall_shade=30)
    # The sarcophagus: a lid, and four bevelled shoulders mitred round it.
    cx0, cy0 = CRYPT[0], CRYPT[1]
    lx0, ly0, lx1, ly1 = SARCOPHAGUS
    ox0, oy0, ox1, oy1 = (lx0 - SHOULDER, ly0 - SHOULDER, lx1 + SHOULDER,
                          ly1 + SHOULDER)
    crypt.carve([(ox0 - cx0, oy0 - cy0), (ox1 - cx0, oy0 - cy0),
                 (ox1 - cx0, oy1 - cy0), (ox0 - cx0, oy1 - cy0)])

    def piece(name, points, floor_z, tile, note, slope=None):
        x0 = min(x for x, _y in points)
        y0 = min(y for _x, y in points)
        rk = {"declared_zero_exit": True}
        if slope is not None:
            rk["floor_slope"] = slope
        made = parish.room(
            name, [(x - x0, y - y0) for x, y in points], role="detail",
            faces={f"e{k}": k for k in range(len(points))},
            frame=Frame(x0, y0),
            region_kwargs={**INTERIORS["crypt"].region_kwargs(), **rk},
            intent={"kind": "sarcophagus"}, note=note)
        made.surfaces(**INTERIORS["crypt"].style_kwargs(
            floor_z=floor_z, clear_height=floor_z - (CRYPT_FLOOR - CRYPT_CLEAR)))
        made.surfaces(layer="crypt", floor_picnum=tile, wall_picnum=CHEST_FACE,
                      ceiling_picnum=CRYPT_VAULT, floor_shade=26)
        rooms[name] = made
        CRYPT_FACES[made.region_id] = CHEST_FACE
        return made

    lid = piece("sarcophagus_lid",
                [(lx0, ly0), (lx1, ly0), (lx1, ly1), (lx0, ly1)],
                CRYPT_FLOOR - CHEST_SIDE - SHOULDER_RISE - 2048, LID_TILE,
                "the sarcophagus's lid: a gravestone slab, closed")
    #: begun at the lid's own corner, so the one figure fills it
    lid.surfaces(floor_stat=64, floor_shade=14)
    outer = [(ox0, oy0), (ox1, oy0), (ox1, oy1), (ox0, oy1)]
    inner = [(lx0, ly0), (lx1, ly0), (lx1, ly1), (lx0, ly1)]
    shoulders = []
    for k in range(4):
        a, b = outer[k], outer[(k + 1) % 4]
        c, d = inner[(k + 1) % 4], inner[k]
        shoulders.append(piece(
            f"sarcophagus_shoulder_{k}", [a, b, c, d],
            CRYPT_FLOOR - CHEST_SIDE, SHOULDER_TILE,
            "a bevelled shoulder of the sarcophagus",
            slope=SlopeSpec(hinge=(a, b), rise_z=-SHOULDER_RISE)))
    for k, shoulder in enumerate(shoulders):
        parish.connect(shoulder.face("e0"), crypt.face("north"),
                       connection_id=f"connection:sarcophagus_side_{k}")
        parish.connect(shoulder.face("e2"), lid.face("e0"),
                       connection_id=f"connection:sarcophagus_lid_{k}")
        parish.connect(shoulder.face("e1"), shoulders[(k + 1) % 4].face("e3"),
                       connection_id=f"connection:sarcophagus_mitre_{k}")

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
        grade=GRADE, host_clear=nave_clear, pews=3)
    # LIGHT, from the church study: every surface stood at shade 32. Blood
    # lights a church from the floor up and toward the altar -- E3M4 s286,
    # floor 9-11 under a ceiling at 45; DWE1M4 s288, chancel 24 against a
    # nave at 36 -- so the roof is the darkest thing and the chancel the
    # brightest.
    for name, floor, ceiling in (("nave", 20, 44), ("west_aisle", 28, 40),
                                 ("chancel", 14, 36), ("apse", 14, 36),
                                 ("narthex", 26, 40)):
        rooms[name].surfaces(floor_shade=floor, ceiling_shade=ceiling,
                             wall_shade=floor + 6)
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
LIT = [("nave", "south", 0.35), ("chancel", "west", 0.5),
       #: the crypt has no other light: two flames, and the dark between
       ("crypt", "north", 0.3), ("crypt", "south", 0.5)]

POPULATION = [("nave", 202, (0.5, 0.9)), ("west_aisle", 203, (0.5, 0.45)),
              ("crypt_stair", 203, (0.3, 0.5)), ("tower", 202, (0.35, 0.6)),
              #: what the slab goes down to: between the tombs, and one
              #: waiting by the far wall
              ("crypt", 203, (0.12, 0.3)), ("crypt", 202, (0.15, 0.85))]
PICKUPS = [("vestry", 109, (0.35, 0.5)), ("apse", 67, (0.5, 0.35)),
           ("tower", 62, (0.7, 0.3)), ("crypt", 109, (0.4, 0.09)),
           #: the TNT the cracked wall wants, by the tomb facing it
           ("crypt", 62, (0.12, 0.12))]


#: the campaign's skull in its frame (1048, 73 of them pushed; E1M5 sprite 629 is this record)
SKULL_SWITCH = {"picnum": 1048, "cstat": 464, "shade": -8, "status": 0}


def link_slab(layout, rooms) -> dict:
    """The floor of the shaft's head opens on the slab under it. One sector either side, and neither is ever cut."""
    from bloodmap.roomoverroom import room_over_room
    x0, y0, x1, y1 = CRYPT_LIFT
    return room_over_room(layout, "church:slab_link", rooms["crypt_shaft"].region_id, rooms["crypt_lift"].region_id,
                          link_id=SLAB_LINK, at=((x0 + x1) // 2, (y0 + y1) // 2))


def slab_switches(layout, rooms) -> None:
    """A skull on the shaft's back wall at either stop, for whoever stands on the slab, and one outside that calls it.

    (It carried one with it until the link: what is carried stays on its own side of the plane, and at the top the skull was
    in the crypt's half with the church's air where it should have been. E4M4's s159 is worked from a wall too.)
    """
    from bloodmap import motion
    wire = wires.wire("church:slab")
    wire.then(wiring.region(rooms["crypt_lift"].region_id))
    x0, y0, x1, y1 = CRYPT_LIFT
    for name, room, a, b, size, kind, flags, sends in (
            ("aboard", "crypt_shaft", (x1, y0), (x1, y1), 40, 21, 0, dict(command=motion.CMD_ON, wait_time=10)),
            ("top", "crypt_stair", (x0, 25600), (x0, y0), 28, 21, 0, dict(command=motion.CMD_OFF, wait_time=10)),
            ("foot", "crypt", (x0 - 768, y1), (x0, y1), 40, 21, 0, dict(command=motion.CMD_ON, wait_time=10))):
        switch = f"church:slab_{name}"
        layout.place_on_wall(switch, rooms[room].region_id, a1=a, a2=b, t=0.5, height_player_heights=0.79,
                             offset_player_widths=0.04, type=kind, x_repeat=size, y_repeat=size, behavior={"data_1": 200, "data_2": 200},
                             **{**SKULL_SWITCH, "cstat": SKULL_SWITCH["cstat"] | flags})
        wire.when(wiring.placement(switch), "push", **sends)
    # the one at the bottom of the shaft hangs under the slab while it is up
    layout.add_sprite("church:slab_below", rooms["crypt_lift"].region_id, x=x1 - 16, y=(y0 + y1) // 2, z=CRYPT_FLOOR - 13400,
                      type=21, x_repeat=40, y_repeat=40, angle=1024, behavior={"data_1": 200, "data_2": 200}, sunk=True, **SKULL_SWITCH)
    wire.when(wiring.placement("church:slab_below"), "push", command=motion.CMD_OFF, wait_time=10)


def crack(layout, rooms, trunk_region_id) -> dict:
    """The crack on both faces of the breach, and the charges behind it."""
    crypt = rooms["crypt"]
    x0, y0, x1, y1 = CRYPT
    centre = (BREACH[1] + BREACH[3]) // 2
    layout.place_on_wall(
        "church:crypt_crack", crypt.region_id, a1=(x1, y0), a2=(x1, y1),
        t=(centre - y0) / (y1 - y0), height_player_heights=0.6,
        offset_player_widths=0.04, spans_opening=True, **CRACK)
    # the sewer's side of the same wall: the trunk's west face
    layout.place_on_wall(
        "church:sewer_crack", trunk_region_id,
        a1=(BREACH[2], BREACH[3] + 1024), a2=(BREACH[2], BREACH[1] - 1024),
        t=0.5, height_player_heights=0.6, offset_player_widths=0.04,
        spans_opening=True, **CRACK)
    for cracked in ("church:crypt_crack", "church:sewer_crack"):
        wires.wire("church:breach").when(
            wiring.placement(cracked), "destroyed", command=1,
            on=True, off=True, once=True)
    for index, (local, wait) in enumerate((((0.96, 0.52), 1),
                                           ((0.96, 0.66), 3),
                                           ((0.96, 0.82), 2))):
        layout.place_on_floor(
            f"church:crypt_charge_{index}", crypt.region_id, local=local,
            type=459, picnum=908, cstat=128, x_repeat=4, y_repeat=64,
            status=11, behavior={"rx_id": BREACH_CHANNEL, "wait_time": wait})
        wires.wire("church:breach").then(
            wiring.placement(f"church:crypt_charge_{index}"))
    for index, (a1, a2) in enumerate(PLAQUES):
        layout.place_on_wall(
            f"church:crypt_plaque_{index}", crypt.region_id, a1=a1, a2=a2,
            t=0.5, height_player_heights=1.2, offset_player_widths=0.02,
            **PLAQUE)
    for index, (tile, wx, wy, angle) in enumerate(COBWEBS):
        layout.place_on_floor(
            f"church:crypt_cobweb_{index}", crypt.region_id,
            local=((wx - x0) / (x1 - x0), (wy - y0) / (y1 - y0)),
            height_player_heights=CRYPT_CLEAR / 16960.0, picnum=tile,
            angle=angle, **COBWEB)
    for index, (bx, by) in enumerate(BARRELS):
        layout.place_on_floor(
            f"church:crypt_barrel_{index}", crypt.region_id,
            local=((bx - x0) / (x1 - x0), (by - y0) / (y1 - y0)),
            height_player_heights=BARREL_LIFT / 16960.0, **BARREL)
    return {"channel": BREACH_CHANNEL, "barrels": len(BARRELS)}


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
    glass["inside"] = glaze_inside(layout, rooms)
    print("church glass:", glass)
    return placed + len(glass["hung"])
