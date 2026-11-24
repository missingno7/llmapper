"""The Cabal's rite: the round storm chamber behind the settling hall, its sign, its well, and what is raised out of it.

Designed in `references/cabal-rite-design.md`, from the study `ritual-place`.
The chamber is one `bloodmap.arrangement`: circles, a star, a dais, teeth, laid
over one another; what each piece is made of is `level`, and what each shows
its neighbour `_face`.
"""

from __future__ import annotations

import math

from bloodmap import arrangement as A
from bloodmap import motion, wiring
from bloodmap.slope import SlopeSpec

import wallplane
import wires

LAYER = "rite"
KEY = "region:gravesend/sewer/settling_hall/rite"
CENTRE = (28160, 59200)
SIDES, HALF = 20, 1 / 40                     # a flat face to the north, and at every tenth of a turn's half
QUAY, QUAY_FACE = 102400, 51200
FLOOR = QUAY + 16384                         # a body under the gallery, four steps
WALL, INNER, ARENA, STEP_IN = 6784, 5632, 4480, 384
CEILING, VAULT, CROWN, SHAFT = 57344, 51200, 47104, 43008
NORTH = min(y for _x, y in A.circle(CENTRE, WALL, SIDES, HALF))
SOUTH = 2 * CENTRE[1] - NORTH
WEST = min(x for x, _y in A.circle(CENTRE, WALL, SIDES, HALF))
EAST = 2 * CENTRE[0] - WEST

MOUTH, CARPET = 768, 512                     # half the widths of the hole in the wall and of the runner through it
MOUTH_TOP = QUAY - 28672
GATE = (51968, 52224)
# the owner, 2026-11-24: "large pentagram on the floor out of red sectors": it fills the floor, and it burns
STAR, LINE, RING = 4032, 384, 192
SIGN_LIT, SIGN_DEAD, KERB = -6, 40, 36                    # shades: the blood's while the rite lives and after, the kerb's always
WELL, BRIM = 1040, FLOOR + 1024
SUNK = BRIM + 40960
TOOTH_RISE = 5600                            # over a length of 400: the point stands 8,750 over the rim
DAIS_HALF, DAIS_FROM, DAIS_STEP = 1920, 63520, 248
PULPIT = (27776, 65088, 28544, 65600)                     # behind the altar and over it: he stands in the rose
DAIS = FLOOR - 8192
ALTAR = (27520, 64128, 28800, 64768)
APSE = (27136, SOUTH, 29184, SOUTH + 1024)
APSE_FLOOR, SILL = DAIS - 4096, DAIS - 8192
APSE_TOP = SILL - 32768                                   # the rose is 2048 square, whole, and over the altar
GULLET = SOUTH + 1024                                     # behind the glass
HEART, COLUMN = (28160, GULLET + 3584), 512
HEART_FLOOR, HEART_TOP = SILL, SILL - 32768             # one of the eye's own tile, undistorted
BOX_FLOOR, BOX_DEPTH, BOX_HALF, RAIL = QUAY - 22528, 1152, 1000, 5120
NICHES = (2, 4, 6, 8, 12, 14, 16, 18)        # faces of the wall, counted clockwise from the mouth
NICHE_DEPTH, NICHE_HALF, NICHE_TOP = 640, 560, 40960
PILLARS = (1.5, 3.5, 6.5, 8.5, 11.5, 13.5, 16.5, 18.5)

BRICK, PILLAR, RUBBLE, COBBLE = 91, 123, 449, 110
PAVING, TREAD, TRIM, STONE = 253, 90, 89, 253
BLOOD, RUNNER, TOOTH, VAULTING, SHAFT_WALL = 1130, 306, 273, 90, 80
FLESH, FLESH_FLOOR, FLESH_ROOF, GUMS, ROSE, EYE = 240, 240, 240, 1095, 264, 235
WOOD = 88
HALF_SIZE = 8                                # floor_stat: the tile at half its size, a carpet's and not a pavement's


def face_span(index: float) -> tuple:
    """The two corners of one of the twenty faces of the wall: 0 the mouth's, clockwise."""
    return (A.spoke(CENTRE, WALL, index / SIDES - HALF), A.spoke(CENTRE, WALL, index / SIDES + HALF))


def outward(index: float, depth: float, half: float, start: float = 0) -> list:
    """A rectangle standing out of one face of the wall, centred on it."""
    (ax, ay), (bx, by) = face_span(index)
    mx, my = (ax + bx) / 2, (ay + by) / 2
    length = math.hypot(bx - ax, by - ay)
    ux, uy = (bx - ax) / length, (by - ay) / length
    ox, oy = uy, -ux                                     # clockwise on the page: outward is to the left
    near = [(mx - ux * half + ox * start, my - uy * half + oy * start),
            (mx + ux * half + ox * start, my + uy * half + oy * start)]
    deep = depth - start
    return [near[0], (near[0][0] + ox * deep, near[0][1] + oy * deep),
            (near[1][0] + ox * deep, near[1][1] + oy * deep), near[1]]


def _clip(ring, other):
    from shapely import Polygon
    return [(round(x), round(y)) for x, y in Polygon(ring).intersection(Polygon(other)).exterior.coords][:-1]


def _rect(x0, y0, x1, y1):
    return [(x0, y0), (x1, y0), (x1, y1), (x0, y1)]


def well_edges() -> list:
    corners = A.circle(CENTRE, WELL, 5, 0.5)
    return list(zip(corners, corners[1:] + corners[:1]))


def teeth() -> list:
    """Two bone fangs on each side of the well: (base a, base b, point), leaning in over it."""
    out = []
    for (ax, ay), (bx, by) in well_edges():
        length = math.hypot(bx - ax, by - ay)
        ux, uy = (bx - ax) / length, (by - ay) / length
        ix, iy = -uy, ux
        for lo, hi in ((0.16, 0.40), (0.60, 0.84)):
            a = (round(ax + ux * length * lo), round(ay + uy * length * lo))
            b = (round(ax + ux * length * hi), round(ay + uy * length * hi))
            tip = (round((a[0] + b[0]) / 2 + ix * 400), round((a[1] + b[1]) / 2 + iy * 400))
            out.append((a, b, tip))
    return out


def mouth_teeth() -> list:
    """The upper jaw: four fangs hung from the mouth's lintel over the runner, pointing in and down, no two as long."""
    x0, wide, y = CENTRE[0] - CARPET, CARPET // 2, QUAY_FACE + 64
    return [((x0 + k * wide + 24, y), (x0 + (k + 1) * wide - 24, y), (x0 + k * wide + wide // 2, y + (300, 384, 352, 270)[k]))
            for k in range(4)]


def jaws() -> list:
    """The teeth just behind the rose, hung as the mouth's are."""
    x0, wide, y = CENTRE[0] - 960, 384, GULLET + 64
    return [((x0 + k * wide + 20, y), (x0 + (k + 1) * wide - 20, y), (x0 + k * wide + wide // 2, y + 352))
            for k in range(5)]


def throat() -> list:
    """The way through the wall: hacked, and nowhere square."""
    x0, x1 = CENTRE[0] - MOUTH, CENTRE[0] + MOUTH
    return [(x0, QUAY_FACE), (x1, QUAY_FACE), (x1, QUAY_FACE + 160), (x1 + 150, QUAY_FACE + 384), (x1 + 40, GATE[0]),
            (x1 + 40, GATE[1]), (x1 + 170, NORTH), (x0 - 120, NORTH), (x0 - 60, GATE[1]), (x0 - 60, GATE[0]),
            (x0 - 190, QUAY_FACE + 470), (x0, QUAY_FACE + 224)]


def plan() -> list:
    """Every cell of the chamber."""
    round_ = lambda r: A.circle(CENTRE, r, SIDES, HALF)
    place = A.Arrangement()
    place.add("throat", throat())
    place.add("throat_runner", _rect(CENTRE[0] - CARPET, QUAY_FACE, CENTRE[0] + CARPET, NORTH))
    side = _clip(_rect(0, GATE[0], 60000, GATE[1]), throat())
    place.add("gate_side", side)
    place.add("gate_runner", _rect(CENTRE[0] - CARPET, GATE[0], CENTRE[0] + CARPET, GATE[1]))
    # the walk and the steps in arcs, so each is lit by the fires nearest it without being cut
    for arc in range(10):
        place.add(f"gallery_{arc}", A.arc(CENTRE, INNER, WALL, 2 * arc, 2 * arc + 2, SIDES, HALF))
    for k in range(3):
        outer = INNER - k * STEP_IN
        for arc in range(5):
            place.add(f"tier_{k + 1}_{arc}", A.arc(CENTRE, outer - STEP_IN, outer, 4 * arc, 4 * arc + 4, SIDES, HALF))
    # the kerb round the ring in arcs too; what is inside the ring stands under the crown
    for arc in range(10):
        place.add(f"floor_{arc}", A.arc(CENTRE, STAR + RING, ARENA, 2 * arc, 2 * arc + 2, SIDES, HALF))
    place.add("within", round_(STAR + RING))
    band = _rect(CENTRE[0] - CARPET, NORTH, CENTRE[0] + CARPET, CENTRE[1])
    outer = [WALL, *(INNER - k * STEP_IN for k in range(4))]
    for k in range(4):
        place.add(f"aisle_{k}", _clip(band, round_(outer[k])), holes=[round_(outer[k + 1])])
    place.add("sign_ring", round_(STAR + RING), holes=[round_(STAR)])
    place.add("sign", *A.star(CENTRE, STAR, 5, 2, LINE))
    for step, y in ((1, DAIS_FROM), (None, DAIS_FROM + DAIS_STEP)):
        name = "dais" if step is None else f"dais_step_{step}"
        place.add(name, _clip(_rect(CENTRE[0] - DAIS_HALF, y, CENTRE[0] + DAIS_HALF, SOUTH + 512), round_(WALL)))
    place.add("altar", _rect(*ALTAR))
    place.add("pulpit", _rect(*PULPIT))
    place.add("apse", _rect(*APSE))
    # the pane stands between two floors of one height: a record that carries a step band cannot carry glass
    place.add("sill", _rect(APSE[0], GULLET - 160, APSE[2], GULLET))
    gx, gy = CENTRE[0], GULLET
    place.add("gullet", [(gx - 1024, gy), (gx + 1024, gy), (gx + 900, gy + 420), (gx + 620, gy + 1100), (gx + 700, gy + 1600),
                         (gx + 520, gy + 2300), (gx - 600, gy + 2300), (gx - 560, gy + 1700), (gx - 760, gy + 1200),
                         (gx - 640, gy + 700), (gx - 980, gy + 330)])
    place.add("heart", A.circle(HEART, 1728, 12, 1 / 24))
    for side, way in (("west", -1), ("east", 1)):
        x, y = HEART[0] + way * 1669, HEART[1]
        place.add(f"cyst_{side}", _rect(min(x, x + 768 * way), y - 416, max(x, x + 768 * way), y + 416))
    place.solid(_rect(HEART[0] - COLUMN, HEART[1] - COLUMN, HEART[0] + COLUMN, HEART[1] + COLUMN))
    for k, jaw in enumerate(jaws()):
        place.add(f"jaw_{k}", jaw)
    for index, name in ((5, "east"), (15, "west")):
        place.add(f"box_{name}", outward(index, BOX_DEPTH, BOX_HALF))
        place.add(f"rail_{name}", outward(index, 96, BOX_HALF))
    for index in NICHES:
        place.add(f"niche_{index}", outward(index, NICHE_DEPTH, NICHE_HALF))
    fangs = teeth()                                      # their feet are corners of the well, so each is hinged on one whole edge
    place.add("well", [p for k, (a, _b) in enumerate(well_edges())
                       for p in (a, *fangs[2 * k][:2], *fangs[2 * k + 1][:2])])
    for k, tooth in enumerate(fangs):
        place.add(f"tooth_{k}", tooth)
    for k, tooth in enumerate(mouth_teeth()):
        place.add(f"fang_{k}", tooth)
    for spot in PILLARS:
        place.solid(A.circle(A.spoke(CENTRE, INNER, spot / SIDES), 224, 8, HALF))
    return place.resolve()


#: the blood creeps, and drags nobody
CREEP = {"pan_always": 1, "pan_floor": 1, "pan_velocity": 10, "pan_angle": 1536}
#: the first word of a cell's name -> (floor z, ceiling z, floor tile, ceiling tile, wall tile)
LEVELS = {
    "throat": (QUAY - 3072, MOUTH_TOP + 7168, RUBBLE, RUBBLE, RUBBLE),
    "gate": (QUAY - 3072, MOUTH_TOP + 7168, RUBBLE, RUBBLE, RUBBLE),
    "fang": (QUAY, MOUTH_TOP, RUNNER, TOOTH, RUBBLE),
    "gallery": (QUAY, CEILING, PAVING, VAULTING, BRICK),
    "floor": (FLOOR, VAULT, STONE, VAULTING, BRICK),
    "within": (FLOOR, CROWN, STONE, VAULTING, BRICK),
    "sign": (FLOOR + 512, CROWN, BLOOD, VAULTING, BRICK),
    "dais": (DAIS, CEILING, STONE, VAULTING, BRICK),
    "pulpit": (DAIS - 9216, CEILING, STONE, VAULTING, BRICK),
    "altar": (DAIS - 6144, CEILING, STONE, VAULTING, BRICK),
    "apse": (APSE_FLOOR, APSE_TOP, STONE, VAULTING, BRICK),
    "sill": (SILL, APSE_TOP, STONE, VAULTING, BRICK),
    "box": (BOX_FLOOR, CEILING, RUNNER, 120, 109),
    "rail": (BOX_FLOOR - RAIL, CEILING, WOOD, 120, 109),
    "niche": (QUAY - 1024, QUAY - 1024 - NICHE_TOP, COBBLE, COBBLE, COBBLE),
    "gullet": (HEART_FLOOR, APSE_TOP, FLESH_FLOOR, FLESH_ROOF, FLESH),
    "jaw": (HEART_FLOOR, APSE_TOP, FLESH_FLOOR, TOOTH, FLESH),
    "heart": (HEART_FLOOR, HEART_TOP, FLESH_FLOOR, FLESH_ROOF, FLESH),
    "cyst": (HEART_FLOOR - 1024, HEART_FLOOR - 1024, FLESH_FLOOR, FLESH_ROOF, 242),
    "well": (BRIM, SHAFT, BLOOD, 376, SHAFT_WALL),
    "tooth": (FLOOR, SHAFT, TOOTH, 376, SHAFT_WALL),
}
CARPETED = ("throat_runner", "gate_runner", "aisle", "box", "fang")


def kind(cell: str) -> str:
    return cell.split("_")[0]


def level(cell: str) -> tuple:
    part = cell.split("_")
    if part[0] == "tier":
        return QUAY + 4096 * int(part[1]), CEILING, TREAD, VAULTING, BRICK
    if part[0] == "aisle":
        return QUAY + 4096 * int(part[1]), CEILING, RUNNER, VAULTING, BRICK
    if cell.startswith("dais_step"):
        return DAIS + 4096 * int(part[2]), VAULT, STONE, VAULTING, BRICK
    if cell in _LIP:
        return FLOOR, SHAFT, STONE, 376, BRICK
    if cell.startswith(("throat_runner", "gate_runner")):
        return QUAY, MOUTH_TOP, RUNNER, RUBBLE, RUBBLE
    floor, ceiling, tile, roof, wall = LEVELS[part[0]]
    return floor, ceiling, RUNNER if cell.startswith(CARPETED) else tile, roof, wall


#: the cells of the floor inside the star's pentagon, round the well
_LIP: set[str] = set()
#: what `_face` painted: (region, a, b, tile)
_PAINTED: list[tuple] = []


def build(layout, quay) -> dict[str, str]:
    """Build the chamber behind the quay's south wall; returns {cell: region id}."""
    cells = plan()
    _LIP.clear()
    for cell in cells:
        if kind(cell.name) == "within" and max(math.dist(p, CENTRE) for p in cell.outer) < 1400:
            _LIP.add(cell.name)
    slopes = {}
    for k, (a, b, _tip) in enumerate(teeth()):
        slopes[f"tooth_{k}"] = {"floor_slope": SlopeSpec(hinge=(a, b), heinum=-TOOTH_RISE)}
    for name, row in (("fang", mouth_teeth()), ("jaw", jaws())):
        for k, (a, b, _tip) in enumerate(row):
            slopes[f"{name}_{k}"] = {"ceiling_slope": SlopeSpec(hinge=(a, b), heinum=6400)}

    def surface(name):
        floor, ceiling, floor_tile, ceiling_tile, wall = level(name)
        what = kind(name)
        return dict(floor_z=floor, ceiling_z=ceiling, floor_picnum=floor_tile, ceiling_picnum=ceiling_tile,
                    wall_picnum=wall, floor_shade=20, wall_shade=20, ceiling_shade=24, layer=LAYER,
                    floor_stat=HALF_SIZE if floor_tile == RUNNER else 0,
                    role="interior" if what in ("gallery", "floor", "within", "dais", "throat") else "detail",
                    declared_zero_exit=what not in ("gallery", "dais", "aisle"),
                    intent={"kind": "furnished"}, type=600 if what in ("well", "tooth", "cyst", "gate") else 0,
                    secret=name == "heart", sector_behavior=dict(CREEP) if what in ("sign", "well") else {},
                    **slopes.get(name, {}))

    _PAINTED.clear()

    def face(seen, beyond, a, b):
        paint = _face(seen, beyond, a, b)
        if "picnum" in paint:
            _PAINTED.append((f"{KEY}:{seen}", a, b, paint["picnum"]))
        return paint

    def joint(left, right, _a, _b):
        return {"gated": True} if "gate" in (kind(left), kind(right)) else {}

    regions = A.lay(layout, KEY, cells, surface, face, joint)
    mouth = ((CENTRE[0] - MOUTH, CENTRE[0] - CARPET, "throat"), (CENTRE[0] - CARPET, CENTRE[0] + CARPET, "throat_runner"),
             (CENTRE[0] + CARPET, CENTRE[0] + MOUTH, "throat"))
    for k, (x0, x1, name) in enumerate(mouth):
        near = next(c.name for c in cells if c.name.startswith(name) and (x0, QUAY_FACE) in c.outer and (x1, QUAY_FACE) in c.outer)
        layout.add_connection(f"connection:rite_mouth_{k}", quay.region_id, regions[near], a1=(x1, QUAY_FACE),
                              a2=(x0, QUAY_FACE), min_width=1, min_opening=0)
    dress(layout, regions, cells, quay.region_id)
    return regions


def _face(seen: str, beyond: str | None, a, b) -> dict:
    """What a cell shows along an edge."""
    here, there = kind(seen), kind(beyond) if beyond else None
    if seen in _LIP and there in ("well", "tooth") or beyond in _LIP and here in ("well", "tooth"):
        # nobody climbs in over the teeth: they are the rim's fence
        return {"picnum": TOOTH if there == "tooth" else SHAFT_WALL if here in ("well", "tooth") else STONE, "cstat": 1}
    if there == "tooth":
        return {"picnum": TOOTH}
    if "fang" in (here, there) or there == "jaw":
        return {"picnum": TOOTH}
    if there == "gate":
        return {"picnum": GUMS}
    if there is None and here == "heart" and math.dist(a, HEART) < COLUMN * 1.5:
        return _column(a, b)
    if there == "rail":
        return {"picnum": WOOD if here == "box" else BRICK}
    if here in ("throat", "fang") and there in ("throat", "fang"):
        return {"picnum": RUBBLE}
    if there in ("tier", "aisle", "gallery", "dais", "altar", "pulpit", "within", "floor", "sill") and here not in ("throat", "niche"):
        return {"picnum": TRIM}
    if here in ("gullet", "heart", "jaw", "cyst"):
        return {"picnum": GUMS if there in ("gullet", "heart") else FLESH}
    if here in ("sign", "well") or there in ("sign", "well"):
        return {"picnum": STONE}
    return {}


def _column(a, b) -> dict:
    """The chained column of flesh: an eye to the gullet, wounds and chains the other ways round."""
    if max(a[1], b[1]) < HEART[1] - COLUMN * 0.8:
        # one whole tile, rolled down until the eye is at a man's
        return {"picnum": EYE, "x_repeat": 8, "y_repeat": 8, "y_panning": 170}
    return {"picnum": 234 if (a[0] + b[0]) // 2 < HEART[0] else 231, "x_repeat": 8, "y_repeat": 8}


# ---- the people, the fires, the goods -----------------------------------------

#: who stands where: turn, radius, dude type, tile
CELEBRANTS = ((0.0, 3560, 201, 2820), (0.2, 3560, 202, 2825), (0.4, 3560, 201, 2820), (0.6, 3560, 202, 2825), (0.8, 3560, 201, 2820))
#: the theatre's audience, propped in the tiers in twos and threes: turn, tier, tile, size
AUDIENCE = ((0.085, 2, 2330, 36), (0.1, 2, 2334, 34), (0.18, 3, 2333, 32), (0.2, 2, 2330, 36), (0.29, 1, 2334, 34),
            (0.302, 2, 2330, 35), (0.36, 2, 2333, 34),
            (0.885, 3, 2330, 35), (0.872, 2, 2334, 33), (0.79, 2, 2330, 37), (0.722, 3, 2334, 32), (0.655, 1, 2330, 36))
#: worshippers who do not move, in robes of three colours (DWE1M4 s642): turn, tier, palette
CONGREGATION = ((0.12, 1, 13), (0.165, 2, 3), (0.24, 1, 11), (0.352, 1, 3), (0.905, 1, 11), (0.845, 1, 13), (0.755, 1, 3),
                (0.675, 2, 11))
#: The blasts of the rite's end, in the order they go off: (tenths of a second after the beast falls, x, y from the
#: middle, z). The statue bursts where it stands (a gib object: no blast, nobody hurt), the fire goes up the hanged one's
#: chain, over the heads of whoever stands below (`bloodmap.blasts.harmless`: every blast is 2.4 bodies over the floor, or
#: is out of sight down the emptied well), and round the crown, a step a tenth (DWE3M7's 172). Then the well's bottom.
CLIMB = ((20, 180, -90, 70400), (22, -160, 120, 64000), (24, 90, 160, 57600), (26, -60, -60, 51200), (28, 0, 0, 45600))
CROWN_RING = tuple((31 + k, *(round(2200 * f(2 * math.pi * k / 5 - math.pi / 2)) for f in (math.cos, math.sin)), CROWN + 3200)
                   for k in range(5))
DEEP = ((58, 240, 160, SUNK - 900), (61, -220, -140, SUNK - 900), (64, 0, 0, SUNK - 900))
#: where fire and stone fly and nothing hurts: (tenths, height over the floor)
FLARES = ((13, 14000), (15, 26000), (17, 38000))
#: the ones among the dead that get up when the rite is broken
RISERS = ((0.125, 3), (0.31, 3), (0.86, 3), (0.685, 3))
#: the fires, in the order they die: the two by the runner, the two at the sides, the two by the altar
FIRES = ((0.1, 0.9), (0.29, 0.71), "dais")
TAPESTRIES = {9: 267, 11: 267, 3: 614, 17: 614, 7: 614, 13: 614}
#: what the dead in the niches had on them: face, kind, tile, size, cstat
POCKETS = ((6, 109, 2169, 40, 128), (14, 109, 2169, 40, 128), (2, 68, 812, 48, 128), (4, 107, 519, 48, 128), (16, 73, 548, 24, 128), (18, 73, 548, 24, 128))


def _here(turn: float, radius: float) -> tuple[int, int]:
    return A.spoke(CENTRE, radius, turn)


def _toward(x: int, y: int, at=CENTRE) -> int:
    return round(math.atan2(at[1] - y, at[0] - x) * 1024 / math.pi) & 2047


def _stand(layout, regions, cell, name, x, y, tile, size, *, seat="floor", cstat=128, shade=-8, tall=None,
           lift=0, foot=None, **fields) -> str:
    """Seat a sprite on a cell's floor, hang it from its ceiling, or hang it with its foot that far over the floor."""
    from bloodmap.placement import drawn_extent, seated_z
    region = regions[cell]
    room = layout.regions[region]
    _w, height, _x, offset = wallplane.art()[tile]
    tall = size if tall is None else tall
    if foot is not None:                                   # its chain runs on into the ceiling, as far as it is long
        _top, bottom = drawn_extent(height, offset, tall, cstat)
        z = max(room.floor_z - foot - bottom, room.ceiling_z + 16)
        fields.setdefault("sunk", True)
    else:
        z = seated_z(seat=seat, floor_z=room.floor_z, ceiling_z=room.ceiling_z, tile_height=height, y_repeat=tall,
                     y_offset=offset, cstat=cstat, clearance=16)
        z = max(z - lift, room.ceiling_z + 16)
    return layout.add_sprite(f"cabal:{name}", region, x=round(x), y=round(y), z=z, picnum=tile, x_repeat=size,
                             y_repeat=tall, cstat=cstat, shade=shade, **fields)


def _flat(layout, regions, cell, name, x, y, tile, size, *, shade=0, angle=1536, cstat=160, tall=None):
    room = layout.regions[regions[cell]]
    return layout.add_sprite(f"cabal:{name}", regions[cell], x=round(x), y=round(y), z=room.floor_z - 16, picnum=tile,
                             x_repeat=size, y_repeat=tall or size, angle=angle, cstat=cstat, shade=shade)


def _unseen(layout, regions, cell, name, x, y, kind_, tile, *, status=0, z=None, **behavior):
    room = layout.regions[regions[cell]]
    return layout.add_sprite(f"cabal:{name}", regions[cell], x=round(x), y=round(y),
                             z=room.floor_z - 4096 if z is None else z, type=kind_, picnum=tile, shade=-128,
                             cstat=32896, status=status, behavior=behavior)


def _bill(layout, regions, cell, name, a, b, tile, repeat, height, *, tall=None, shade=0):
    return wallplane.sprite(layout, f"cabal:{name}", regions[cell], a, b, tile=tile, x_repeat=repeat,
                            y_repeat=tall or repeat, cstat=208, height_player_heights=height, shade=shade, required=True)


class _Place:
    """Which cell a point stands in."""

    def __init__(self, cells):
        from shapely import Polygon
        self.shapes = [(c.name, Polygon(c.outer, c.holes)) for c in cells]

    def __call__(self, x, y) -> str:
        from shapely import Point
        for name, shape in self.shapes:
            if shape.contains(Point(x, y)):
                return name
        raise ValueError(f"({x}, {y}) is in no cell of the chamber")


def _along_face(index, along=0.0, deep=0.0):
    """A point `along` a face of the wall from its middle, and `deep` behind it (negative: in front)."""
    (ax, ay), (bx, by) = face_span(index)
    length = math.hypot(bx - ax, by - ay)
    ux, uy = (bx - ax) / length, (by - ay) / length
    return (round((ax + bx) / 2 + ux * along + uy * deep), round((ay + by) / 2 + uy * along - ux * deep))


def dress(layout, regions, cells, quay) -> None:
    """Furnish the chamber and wire the rite."""
    cell = _Place(cells)
    broken = wires.wire("cabal:broken")
    _fires(layout, regions, cell, broken)
    _candles(layout, regions)
    _people(layout, regions, cell, broken)
    _goods(layout, regions, cell)
    _niches(layout, regions, broken)
    _boxes(layout, regions)
    _quay(layout, quay)
    stopped = _gullet(layout, regions, cells)
    _rite(layout, regions, cells, broken, stopped)


def _fires(layout, regions, cell, broken) -> None:
    """Six skull-headed stands that can be put out (view.cpp:2930), a pair at a time, and two torches nobody lights or kills."""
    waits = (None, 8, 16)
    for k, pair in enumerate(FIRES):
        spots = ([_here(t, INNER - 2.75 * STEP_IN) for t in pair] if pair != "dais"
                 else [(CENTRE[0] - 1440, 64300), (CENTRE[0] + 1440, 64300)])
        wire = wires.wire(f"cabal:fires-{k + 1}")
        for side, (x, y) in enumerate(spots):
            wire.then(wiring.placement(_stand(
                layout, regions, cell(x, y), f"fire_{k}_{side}", x, y, 564, 72, cstat=129, shade=-16, type=30,
                behavior={"state": 1, "busy": 65536})))
        # a one-way switch that waits before it lets go: each pair dies a little after the last (CASTLE23)
        now = waits[k] is None
        relay = _unseen(layout, regions, "dais", f"fires_relay_{k}", 28160 + 64 * k, 65720, 20 if now else 21, 0)
        broken.then(wiring.placement(relay))
        wire.when(wiring.placement(relay), wiring.RELAY, command=motion.CMD_OFF, on=now, off=not now,
                  **({} if now else {"wait_time": waits[k]}))
    for k, turn in enumerate((0.045, 0.955)):
        x, y = _here(turn, 6460)
        _stand(layout, regions, cell(x, y), f"torch_{k}", x, y, 560, 64, cstat=129, shade=-128, type=30)


def _candles(layout, regions) -> None:
    """On the altar, in two niches, along the dais; no two alike (SSR3 s230). None on the sign: a candle's art keeps its flame when its state is 0."""
    sizes = (40, 30, 52, 34, 46, 26, 56, 36)
    x0, y0, x1, y1 = ALTAR
    spots = [(x, y, "altar") for x, y in ((x0 + 90, y0 + 110), (x0 + 150, y1 - 100), (x1 - 90, y0 + 130),
                                           (x1 - 170, y1 - 90), (x1 - 90, y1 - 220))]
    spots += [(CENTRE[0] + x, DAIS_FROM + DAIS_STEP + 160 + abs(x) % 90, "dais") for x in (-1700, -1560, 1580, 1720)]
    for index in (6, 14):                                 # two niches full of them (HALL s135)
        spots += [(*_along_face(index, (k % 3 - 1) * 300 + (40 if k // 3 % 2 else -40), 150 + (k // 3) * 170),
                   f"niche_{index}") for k in range(9)]
    for k, (x, y, where) in enumerate(spots):
        _stand(layout, regions, where, f"candle_{k}", x, y, 938, sizes[k % 8], tall=sizes[(k * 3 + 1) % 8],
               cstat=384 | (4 if k % 2 else 0), shade=-128, type=32)


def _people(layout, regions, cell, broken) -> None:
    # the celebrants, their backs to the door, deaf to everything but the well
    for k, (turn, radius, dude, tile) in enumerate(CELEBRANTS):
        x, y = _here(turn, radius)
        _stand(layout, regions, cell(x, y), f"celebrant_{k}", x, y, tile, 40, cstat=384, type=dude, status=6,
               angle=_toward(x, y), pal=3 if dude == 201 else 0, behavior={"dude_deaf": 1})
    # the stone beast, on the pulpit behind the altar (the owner, 2026-11-24: "istead of defeating that beast cultist I would
    # put there stone gargoyle", and "Stone gargoyle I mean the enemy": the live one, 207, and no statue). Its back is to
    # whoever comes, dark in the rose over the horned thing's head; it turns when the mouth shuts, or at a shot, and its
    # death breaks the rite (E1M7's are wired so). It shrugs off bullets and blasts (dudeInfo: 10 of 256): the room must
    # hold what hurts it, as 21 of the 26 maps that have one give a Tesla Cannon
    priest = _stand(layout, regions, "pulpit", "stone_beast", (PULPIT[0] + PULPIT[2]) / 2, (PULPIT[1] + PULPIT[3]) / 2, 1470,
                    40, cstat=384, type=207, status=6, shade=-8, pal=5, angle=512, behavior={"dude_deaf": 1})
    wires.wire("cabal:shut").then(wiring.placement(priest))
    broken.when(wiring.placement(priest), "killed", command=motion.CMD_ON, on=False, off=True, once=True, decoupled=1)
    # the audience, carried down from the Aldermack; four of it get up
    for k, (turn, tier, tile, size) in enumerate(AUDIENCE):
        x, y = _here(turn, INNER - (tier - 0.25) * STEP_IN)
        _stand(layout, regions, cell(x, y), f"audience_{k}", x, y, tile, size, cstat=384 | (4 if k % 3 == 1 else 0),
               type=416, status=4, angle=_toward(x, y), behavior={"data_1": 8, "data_2": 16, "data_4": 318})
    for k, (turn, tier, pal) in enumerate(CONGREGATION):
        x, y = _here(turn, INNER - (tier - 0.25) * STEP_IN)
        # the art has five sides, so a still figure looks where its angle does (view.cpp:2740; the owner, 2026-11-24)
        _stand(layout, regions, cell(x, y), f"congregation_{k}", x, y, 2870, 40, cstat=384, pal=pal, angle=_toward(x, y),
               type=416, status=4, behavior={"data_1": 8, "data_2": 16, "data_4": 318})
    for k, (turn, tier) in enumerate(RISERS):
        x, y = _here(turn, INNER - (tier - 0.25) * STEP_IN)
        broken.then(wiring.placement(_stand(
            layout, regions, cell(x, y), f"riser_{k}", x, y, 1209, 40, cstat=384, type=244, status=6,
            angle=_toward(x, y))))
    # the boxes: whoever paid for them
    for index, name, sign in ((5, "east", 1), (15, "west", -1)):
        for k, dy in enumerate((-430, 430)):
            x, y = CENTRE[0] + sign * (EAST - CENTRE[0] + 560), CENTRE[1] + dy
            _stand(layout, regions, f"box_{name}", f"gunman_{name}_{k}", x, y, 2820 if k else 2825, 40, cstat=384,
                   type=201 if k else 202, status=6, angle=_toward(x, y), pal=3 if k else 0,
                   behavior={"launch_skill": 3 if k else 0})
        _stand(layout, regions, f"box_{name}", f"candelabrum_{name}", CENTRE[0] + sign * (EAST - CENTRE[0] + 900),
               CENTRE[1], 580, 56, cstat=384, shade=-128)


def _goods(layout, regions, cell) -> None:
    # the well: something horned stands half out of it, and one hangs over it
    # (its middle at the blood's level, so the floor cuts it at the waist)
    room = layout.regions[regions["well"]]
    horned = layout.add_sprite("cabal:horned", regions["well"], x=CENTRE[0], y=CENTRE[1], z=room.floor_z - 512, picnum=1840,
                               x_repeat=66, y_repeat=80, cstat=128, shade=-24, type=417, status=4, sunk=True, angle=1536,
                               behavior={"state": 1, "locked": 1, "data_1": 20, "data_2": 26, "data_4": 313})
    wires.wire("cabal:burst").then(wiring.placement(horned))
    _stand(layout, regions, "well", "offering", *CENTRE, 690, 64, foot=42000, tall=80, shade=0, type=416, status=4,
           behavior={"data_1": 8, "data_2": 16, "data_4": 319})
    # what hangs on the gallery's wall
    for index, tile in TAPESTRIES.items():
        a, b = face_span(index)
        _bill(layout, regions, cell(*_along_face(index, 0, -60)), f"hanging_{index}", a, b, tile, 48, 1.35, shade=-2)
    # the altar: a body, the book, the cup; and the blood that has run off it
    x0, y0, x1, y1 = ALTAR
    mid = (x0 + x1) / 2
    _stand(layout, regions, "altar", "victim", mid, (y0 + y1) / 2 - 40, 2334, 56, shade=-10)
    _stand(layout, regions, "altar", "book", mid + 330, y1 - 130, 518, 40, shade=-20)
    _stand(layout, regions, "altar", "cup", mid - 330, y1 - 150, 521, 36, shade=-20)
    _stand(layout, regions, "altar", "skull", mid - 420, y0 + 130, 601, 30, shade=-30)
    _bill(layout, regions, "dais", "run_off", (x1, y0), (x0, y0), 713, 44, 0.18, tall=20)
    _flat(layout, regions, "dais", "pooled", mid, y0 - 300, 732, 64, shade=0)
    for k, (x, y, tile, size) in enumerate((
            (CENTRE[0] - 120, 52950, 956, 44), (CENTRE[0] + 60, 55040, 956, 36))):
        _flat(layout, regions, cell(x, y), f"dragged_{k}", x, y, tile, size, shade=12, angle=512 + 300 * k)


def _niches(layout, regions, broken) -> None:
    """Flesh beasts that wake when the rose bursts, and the hung with what they had on them."""
    for index in (8, 12):
        x, y = _along_face(index, 0, 340)
        wires.wire("cabal:window").then(wiring.placement(_stand(
            layout, regions, f"niche_{index}", f"beast_{index}", x, y, 1530, 40, cstat=384, type=208, status=6,
            angle=_toward(x, y))))
    for index in (8, 12):
        _stand(layout, regions, f"niche_{index}", f"beast_candle_{index}", *_along_face(index, 400 if index == 8 else -400, 150),
               938, 44, cstat=384, shade=-128, type=32)
    for k, (index, tile) in enumerate(((2, 690), (18, 690), (4, 690), (16, 690))):
        x, y = _along_face(index, 0, 380)
        niche = f"niche_{index}"
        _stand(layout, regions, niche, f"hung_{index}", x, y, tile, 64, foot=3600, tall=72, shade=4)
        _flat(layout, regions, niche, f"under_{index}", x, y, 956, 60, shade=20)
        _stand(layout, regions, niche, f"skulls_{index}", *_along_face(index, -370, 480), 684, 34, shade=6)
        _stand(layout, regions, niche, f"niche_candle_{index}", *_along_face(index, 400, 150), 938, 36, cstat=384,
               shade=-128, type=32)
    for index, what, tile, size, cstat in POCKETS:
        _stand(layout, regions, f"niche_{index}", f"pocket_{index}", *_along_face(index, 180, 330), tile, size, cstat=cstat,
               type=what, status=3)


def _boxes(layout, regions) -> None:
    """The Aldermack's drapes, hung from each box's front."""
    for name, way, angle in (("east", 1, 1024), ("west", -1, 0)):
        region = regions[f"rail_{name}"]
        room = layout.regions[region]
        tall = room.floor_z - room.ceiling_z
        x = CENTRE[0] + way * (EAST - CENTRE[0] + 48)
        for k, dy in enumerate((-BOX_HALF + 330, BOX_HALF - 330)):
            flip = 4 if (k == 0) == (way > 0) else 0
            layout.add_sprite(f"cabal:drape_{name}_{k}", region, x=x, y=CENTRE[1] + dy, z=room.floor_z - tall // 2,
                              picnum=145, x_repeat=40, y_repeat=round(tall / (4 * 128)), angle=angle,
                              cstat=16 | 128 | flip, shade=4)


def _quay(layout, quay) -> None:
    """Outside: a face over the mouth, fires either side of it, the robes they came in, and what was dragged in."""
    room = layout.regions[quay]
    wall, floor = QUAY_FACE - 12, room.floor_z

    def on_wall(name, x, z, tile, size, tall=None, **more):
        layout.add_sprite(f"cabal:{name}", quay, x=x, y=wall, z=z, picnum=tile, x_repeat=size, y_repeat=tall or size,
                          angle=1536, cstat=16 | 64 | 128, **{"shade": 4, **more})

    def stand(name, x, y, tile, size, *, cstat=128, tall=None, **more):
        from bloodmap.placement import seated_z
        _w, height, _x, offset = wallplane.art()[tile]
        z = seated_z(seat="floor", floor_z=floor, ceiling_z=room.ceiling_z, tile_height=height, y_repeat=tall or size,
                     y_offset=offset, cstat=cstat, clearance=16)
        return layout.add_sprite(f"cabal:{name}", quay, x=x, y=y, z=z, picnum=tile, x_repeat=size, y_repeat=tall or size,
                                 cstat=cstat, **{"shade": -8, **more})

    mid = CENTRE[0]
    on_wall("face", mid, MOUTH_TOP - 11264, 226, 100, shade=-6)
    for k, dx in enumerate((-1200, 1200)):
        stand(f"mouth_fire_{k}", mid + dx, QUAY_FACE - 300, 564, 72, cstat=129, shade=-128, type=30)
    for k, dx in enumerate((-2780, -2290, -1800, 1800, 2290, 2780)):
        on_wall(f"robe_{k}", mid + dx, floor - 11264, 768, 64, 72, shade=10)
    # at the foot of the falls, where whoever comes down the outfall's line looks: the Cabal's skull, and fires under it
    on_wall("banner", mid + 5632, floor - 19000, 267, 64, shade=2)
    for k, dx in enumerate((4900, 6360)):
        stand(f"banner_fire_{k}", mid + dx, QUAY_FACE - 260, 564, 64, cstat=129, shade=-128, type=30)
    # what the hole was knocked out of
    for k, (dx, dy, tile, size) in enumerate(((-900, -150, 2621, 72), (-760, -240, 2622, 80), (-980, -330, 2623, 64),
                                              (830, -130, 2623, 80), (960, -250, 2621, 64), (760, -320, 2622, 60))):
        stand(f"spoil_{k}", mid + dx, QUAY_FACE + dy, tile, size, shade=34)
    for k, (dx, dy, tile, size) in enumerate(((-420, -1600, 956, 44), (320, -1000, 956, 48), (-260, -300, 732, 36))):
        layout.add_sprite(f"cabal:trail_{k}", quay, x=mid + dx, y=QUAY_FACE + dy, z=floor - 16, picnum=tile, x_repeat=size,
                          y_repeat=size, angle=512 + 340 * k, cstat=160, shade=14)
    for k, (dx, dy, dude, tile) in enumerate(((-2000, -900, 201, 2820), (2050, -700, 202, 2825))):
        stand(f"sentry_{k}", mid + dx, QUAY_FACE + dy, tile, 40, cstat=384, type=dude, status=6, angle=1536,
              pal=3 if dude == 201 else 0)
    for k, (dx, dy, tile, size) in enumerate(((-3300, -420, 523, 40), (-3750, -520, 2333, 40), (3500, -380, 684, 44))):
        stand(f"left_{k}", mid + dx, QUAY_FACE + dy, tile, size, shade=4)
    for k, (dx, dy) in enumerate(((-1560, -200), (-1680, -330), (1560, -240), (-3420, -300), (3300, -300), (3620, -250))):
        stand(f"quay_candle_{k}", mid + dx, QUAY_FACE + dy, 938, (40, 30, 46, 36, 52, 38)[k], cstat=384, shade=-128, type=32,
              tall=(30, 46, 38, 52, 36, 42)[k])


def _gullet(layout, regions, cells):
    """Behind the rose: braziers that light it from behind, the column with the eye, and what it has swallowed."""
    for k, dx in enumerate((-520, 520)):
        _stand(layout, regions, "gullet", f"ember_{k}", CENTRE[0] + dx, GULLET + 620, 550, 64, cstat=385, shade=-128, type=30)
    for k, turn in enumerate((0.1, 0.9, 0.4, 0.6)):
        _stand(layout, regions, "heart", f"heart_candle_{k}", *A.spoke(HEART, 1380, turn), 938, 40, cstat=384, shade=-128,
               type=32)
    # the eye: Blood's own "shoot the eye" (E1M5, E6M6); it answers a shot or a push, once
    heart = next(c for c in cells if c.name == "heart")
    a, b = next((p, q) for _n, p, q in A.rim(cells) if _n == "heart" and math.dist(p, HEART) < COLUMN * 1.5
                and max(p[1], q[1]) < HEART[1] - COLUMN * 0.8)
    stopped = wires.wire("cabal:heart")
    eye = wiring.face(regions[heart.name], a, b)
    stopped.when(eye, "vector", command=motion.CMD_ON, once=True, trigger_push=1)
    for k, (turn, radius, tile, size) in enumerate(((0.06, 1250, 2333, 44), (0.3, 1300, 2334, 44), (0.56, 1200, 684, 48),
                                                    (0.72, 1320, 2333, 40))):
        _stand(layout, regions, "heart", f"swallowed_{k}", *A.spoke(HEART, radius, turn), tile, size, shade=4)
    hoard = {"west": ((144, 2594, 64),), "east": ((117, 829, 40), (72, 817, 48))}
    for side, way in (("west", -1), ("east", 1)):
        sector = layout.regions[regions[f"cyst_{side}"]]
        shut = sector.floor_z
        for k, (what, tile, size) in enumerate(hoard[side]):
            layout.add_sprite(f"cabal:hoard_{side}_{k}", regions[f"cyst_{side}"], x=HEART[0] + way * 2060,
                              y=HEART[1] - 170 + 340 * k, z=shut, picnum=tile, type=what, status=3, x_repeat=size,
                              y_repeat=size, cstat=128, shade=-8)
        sector.sector_behavior.update(off_floor_z=shut, on_floor_z=shut, off_ceiling_z=shut, on_ceiling_z=shut - 20480,
                                      busy_time_a=20, busy_time_b=20)
        stopped.then(wiring.region(regions[f"cyst_{side}"]))
    return stopped


def _rite(layout, regions, cells, broken, stopped) -> None:
    """The voices, the quakes, the mouth that shuts, the well that sinks, the blasts, the window that bursts."""
    at = lambda cell, name, x, y, kind_, tile, **more: wiring.placement(
        _unseen(layout, regions, cell, name, x, y, kind_, tile, **more))
    entered = wires.wire("cabal:entered")
    inner = next(c.name for c in cells if c.name.startswith("throat_runner") and (CENTRE[0] - CARPET, NORTH) in c.outer)
    entered.when(wiring.region(regions[inner]), "enter", command=motion.CMD_ON, once=True, dude_lockout=1)
    entered.then(at(inner, "demand", 28160, 52400, 711, 2519, data_1=2367))

    # whoever steps down onto the kerb round the sign has the mouth shut behind them, until the rite is done or forty seconds are up
    shut = wires.wire("cabal:shut")
    gates = [regions[c.name] for c in cells if kind(c.name) == "gate"]
    for region in gates:
        room = layout.regions[region]
        room.sector_behavior.update(
            off_floor_z=room.floor_z, on_floor_z=room.floor_z, off_ceiling_z=room.ceiling_z, on_ceiling_z=room.floor_z,
            busy_time_a=12, busy_time_b=30,
            wait_time_a=400, retrigger_a=1)
        shut.then(wiring.region(region))
    for c in cells:
        if kind(c.name) == "floor":
            shut.when(wiring.region(regions[c.name]), "enter", command=motion.CMD_ON, once=True, dude_lockout=1)
    # and once he is dead the kerb is only a kerb
    disarm = wires.wire("cabal:disarm")
    lock = _unseen(layout, regions, "dais", "disarm_relay", 28520, 65720, 20, 0)
    broken.then(wiring.placement(lock))
    disarm.when(wiring.placement(lock), wiring.RELAY, command=motion.CMD_LOCK)
    for c in cells:
        if kind(c.name) == "floor":
            disarm.then(wiring.region(regions[c.name]))
    freed = _unseen(layout, regions, "dais", "freed_relay", 28460, 65720, 20, 0)
    shut.when(wiring.placement(freed), wiring.RELAY, command=motion.CMD_OFF)

    # the chant is heard until he falls (E1M5's, which its skull switches stop)
    wires.wire("cabal:fires-1").then(at("well", "chant", CENTRE[0] + 64, CENTRE[1], 710, 2521, status=12, z=FLOOR - 20000,
                                        state=1, busy=65536, data_1=500, data_2=1100, data_3=59, data_4=70))
    broken.then(at("dais", "pain", 28000, 65780, 711, 2519, data_1=2372))
    broken.then(at("dais", "quake", 27900, 65780, 19, 2072, data_1=1200))

    # the blood goes down the well and takes what stood in it, and the teeth draw back into the rim
    for c in cells:
        if kind(c.name) not in ("well", "tooth"):
            continue
        top, bottom = (BRIM, SUNK) if c.name == "well" else (FLOOR, FLOOR + 20480)
        layout.regions[regions[c.name]].sector_behavior.update(
            off_floor_z=top, on_floor_z=bottom, off_ceiling_z=SHAFT, on_ceiling_z=SHAFT, busy_time_a=60, busy_time_b=60)
        broken.then(wiring.region(regions[c.name]))
    _blasts(layout, regions, cells, broken, at)

    # when the well's bottom has gone up, the rose bursts and what was behind it comes through
    window = wires.wire("cabal:window")
    relay = _unseen(layout, regions, "dais", "window_relay", 28400, 65720, 21, 0)
    broken.then(wiring.placement(relay))
    window.when(wiring.placement(relay), wiring.RELAY, command=motion.CMD_ON, on=False, off=True, wait_time=WINDOW_AT)
    window.then(wiring.placement(freed))
    west, east = (APSE[0], GULLET), (APSE[2], GULLET)
    for region, a, b in ((regions["sill"], east, west), (regions["gullet"], west, east)):
        layout.paint_wall(region, a, b, type=511, over_picnum=ROSE, cstat=1 | 16 | 64, shade=-64, x_repeat=16, y_repeat=8,
                          fixed_frame=True)
        layout.wire_wall(region, a, b, data=12)
    window.then(wiring.face(regions["sill"], east, west))
    window.then(at("apse", "awaited", 28160, APSE[1] + 300, 711, 2519, data_1=2356))
    window.then(at("gullet", "quake_2", 28160, GULLET + 700, 19, 2072, data_1=900))
    for k, (what, not_on, dx) in enumerate(((206, 0, -320), (206, 3, 320))):
        window.then(at("gullet", f"comes_{k}", 28160 + dx, GULLET + 1500, 18, 2077, z=HEART_FLOOR - 8192, data_1=what,
                       launch_skill=not_on, trigger_once=1))

    # the heart
    still = _unseen(layout, regions, "heart", "still", HEART[0], HEART[1] - 900, 20, 0)
    stopped.then(wiring.placement(still))
    silent = wires.wire("cabal:silent")
    silent.when(wiring.placement(still), wiring.RELAY, command=motion.CMD_OFF)
    silent.then(at("heart", "beat", HEART[0], HEART[1] + 900, 710, 2521, status=12, state=1, busy=65536,
                   data_1=300, data_2=800, data_3=60, data_4=90))
    stopped.then(at("heart", "dies", HEART[0] + 64, HEART[1] - 900, 711, 2519, data_1=2380))
    stopped.then(at("heart", "quake_3", HEART[0] - 64, HEART[1] - 900, 19, 2072, data_1=1300))


#: tenths after the beast falls: the rose, and Caleb
WINDOW_AT, SAYS_AT = 70, 46
LINE_SAID = 3056                                          # "Rest in pieces."


def _blasts(layout, regions, cells, broken, at) -> None:
    """The horned thing bursts, fire climbs the chain and runs round the crown, and the emptied well answers (Death Wish's grammar, `bloodmap.blasts`)."""
    from bloodmap import blasts
    floor_bodies = [(*_here(t, r), FLOOR - 9000) for t in (0, 0.25, 0.5, 0.75) for r in (900, 1800, 2700, 3600)]
    steps = [(*_here(t, r), QUAY + 4096 * tier - 9000) for t in (0, 0.25, 0.75) for tier, r in ((0, 5700), (1, 5400), (2, 5050), (3, 4650))]
    rows = [(wait, CENTRE[0] + dx, CENTRE[1] + dy, z) for wait, dx, dy, z in (*CLIMB, *CROWN_RING, *DEEP)]
    if not blasts.harmless([r[1:] for r in rows], floor_bodies + steps):
        raise ValueError("a blast of the rite reaches the floor")
    where = _Place(cells)
    for k, (wait, x, y, z) in enumerate(rows):
        cell = where(x, y)
        if kind(cell) == "tooth":
            raise ValueError("a blast stands in a tooth")
        # those of the well's bottom lie on the blood and go down with it (cstat 8192: carried by the floor)
        deep = z > BRIM
        broken.then(wiring.placement(layout.add_sprite(
            f"cabal:blast_{k}", regions[cell], x=x, y=y, z=BRIM - 64 if deep else z, type=blasts.EXPLODER, picnum=908,
            shade=-128, x_repeat=64, y_repeat=64, cstat=32768 | (8192 if deep else 0), status=11, sunk=True,
            behavior={"wait_time": wait})))
    # a relay that waits, for each thing a wait of its own cannot be given (a gib object goes at once)
    def after(name, tenths, command, x, y, cell="dais"):
        relay = _unseen(layout, regions, cell, f"{name}_relay", x, y, 21, 0)
        broken.then(wiring.placement(relay))
        wire = wires.wire(f"cabal:{name}")
        wire.when(wiring.placement(relay), wiring.RELAY, command=command, on=False, off=True, wait_time=tenths)
        return wire

    after("burst", 12, motion.CMD_OFF, 28340, 65720)
    for k, (tenths, over) in enumerate(FLARES):
        wire = after(f"flare-{k + 1}", tenths, motion.CMD_ON, 27860 + 60 * k, 65720)
        wire.then(wiring.placement(layout.add_sprite(
            f"cabal:flare_{k}", regions["well"], x=CENTRE[0], y=CENTRE[1], z=FLOOR - over, type=417, picnum=1142, status=4,
            cstat=32768, x_repeat=32, y_repeat=32, shade=-8, sunk=True,
            behavior={"locked": 1, "data_1": 26, "data_2": 6, "data_4": 305 if k == 0 else 303})))
    # the hanged one goes with the fire, and what falls from the crown is stone
    for k, (_wait, dx, dy, _z) in enumerate(CROWN_RING):
        x, y = CENTRE[0] + dx, CENTRE[1] + dy
        layout.add_sprite(f"cabal:falls_{k}", regions[where(x, y)], x=x, y=y, z=CROWN + 5000, type=417, picnum=1142, status=4,
                          cstat=32768 | 256, x_repeat=48, y_repeat=48, shade=-8, sunk=True,
                          behavior={"data_1": 20, "data_2": 4, "data_4": 313 if k == 0 else 0})
    says = after("says", SAYS_AT, motion.CMD_ON, 27740, 65720)
    says.then(at("dais", "says", 27740, 65780, 711, 2519, data_1=LINE_SAID))
    again = after("deep", DEEP[0][0], motion.CMD_ON, 27680, 65720)
    again.then(at("dais", "quake_deep", 27680, 65780, 19, 2072, data_1=900))


def keep(level_, compiled) -> int:
    """Put back the rims and risers the city's lintel pass took for bands over doorways."""
    from bloodmap.model import record_fields
    where = {}
    for region in {r for r, *_rest in _PAINTED}:
        for wall in compiled.allocations[region].wall_ids:
            f = record_fields(level_.walls[wall])
            end = record_fields(level_.walls[int(f["point2"])])
            where[region, (f["x"], f["y"]), (end["x"], end["y"])] = f
    put = 0
    for region, a, b, tile in _PAINTED:
        f = where.get((region, tuple(a), tuple(b))) or where.get((region, tuple(b), tuple(a)))
        if f is not None and f["picnum"] != tile:
            f["picnum"] = tile
            put += 1
    # the hoard lies in closets of no height: seated now as the open closet will show it
    from bloodmap.placement import seated_z
    for name, index in compiled.placement_sprites.items():
        if name.startswith("cabal:hoard_"):
            f = record_fields(level_.sprites[index])
            _w, height, _x, offset = wallplane.art()[int(f["picnum"])]
            floor = int(record_fields(level_.sectors[int(f["sector"])])["floor_z"])
            f["z"] = seated_z(seat="floor", floor_z=floor, ceiling_z=floor - 20480, tile_height=height,
                              y_repeat=int(f["y_repeat"]), y_offset=offset, cstat=int(f["cstat"]), clearance=16)
    return put


def even(disk, compiled) -> int:
    """After the light: the floor under a fang is the floor beside it, or each tooth paints a triangle on the ground."""
    from collections import Counter
    from bloodmap.model import record_extra, record_fields
    from bloodmap.sector_geom import sector_walls, wall_length
    cells = {a.sector_id for r, a in compiled.allocations.items()
             if r.startswith(KEY) and kind(r.rsplit(":", 1)[-1]) in ("fang", "jaw")}
    for sector in cells:
        beside = Counter()
        for w in sector_walls(disk, sector):
            other = int(record_fields(disk.walls[w])["next_sector"])
            if other >= 0 and other not in cells:
                beside[other] += wall_length(disk, w)
        if beside:
            source = record_fields(disk.sectors[beside.most_common(1)[0][0]])
            record_fields(disk.sectors[sector])["floor_shade"] = source["floor_shade"]
    # the sign burns by itself while the rite lives and goes out with the second pair of fires: one shade for all of it,
    # whichever fire is nearest. Found by what it is, since the light may have cut it. The kerb round it keeps the
    # mouth's trigger on its one receiver, so it cannot follow the fires, and is dark from the first
    channel = wires.channel("cabal:fires-2")
    kerb = {a.sector_id for r, a in compiled.allocations.items() if r.startswith(f"{KEY}:floor_")}
    for index, sector in enumerate(disk.sectors):
        f = record_fields(sector)
        if index in kerb:
            f["floor_shade"] = KERB
        if f["floor_picnum"] != BLOOD or f["floor_z"] != FLOOR + 512 or f["ceiling_z"] != CROWN:
            continue
        x = record_extra(sector)
        assert x and x["rx_id"] in (0, channel), f"sector {index} of the sign answers to another wire"
        f["floor_shade"] = SIGN_DEAD
        x.update(rx_id=channel, state=1, busy=65536, shade_floor=1, shade_ceiling=0, shade_walls=0, shade_always=0,
                 shade_wave=0, shade_frequency=0, shade_phase=0, amplitude=SIGN_LIT - SIGN_DEAD)
    # the well is lit by nothing once it is empty; while it is full its walls are not seen
    for region, allocation in compiled.allocations.items():
        if region == f"{KEY}:well":
            for w in sector_walls(disk, allocation.sector_id):
                record_fields(disk.walls[w])["shade"] = 46
    return len(cells)


def movers() -> frozenset[str]:
    """The regions that move up and down and are no doors: the well and its teeth, the mouth, the cysts."""
    names = {c.name for c in plan() if kind(c.name) in ("well", "tooth", "gate", "cyst")}
    return frozenset(f"{KEY}:{name}" for name in names)


def light_groups(compiled):
    """The fires that die, pair by pair, and the horned thing's own light, each with the light it gives.

    Every one is put out by an OFF, so each is a group that starts ON
    (`light_stage.LampGroup`): drawn as its lamps leave it, its sectors
    authored dark and lit while their state is 1.
    """
    from bloodmap.light_stage import LampGroup

    def chamber(region):
        return "settling_hall/" in region

    def lamps(*names):
        return frozenset(compiled.placement_sprites[f"cabal:{name}"] for name in names)

    def walls_too(region):
        return chamber(region) and any(f"/rite:{part}" in region for part in ("gallery", "tier", "niche", "box", "rail", "apse"))

    # the stands die a pair at a time; the room goes dark with the second pair, all of it at once, or each piece of it
    # would keep the light of the pairs it does not answer to (round 2: "hard-edged wedges")
    fires = lamps(*(f"fire_{k}_{side}" for k in range(3) for side in (0, 1)))
    going = {"rx": wires.channel("cabal:fires-2")}
    return [LampGroup("the rite's fires, on the walls round", fires, "on", within=walls_too,
                      surfaces=frozenset({"floor", "walls"}), **going),
            LampGroup("the rite's fires, on the floors", fires, "on",
                      within=lambda region: chamber(region) and not walls_too(region), surfaces=frozenset({"floor"}), **going),
            LampGroup("the horned thing's light", lamps("horned"), "on", rx=wires.channel("cabal:burst"),
                      within=chamber, surfaces=frozenset({"floor"}))]
