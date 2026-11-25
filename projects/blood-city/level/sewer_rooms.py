"""The sewer's oldest rooms, refitted in E3M3's manner: the trunk and its ducts, the junction, the cistern, the pump room, the screens and the silt bed.

They were the first things built under the city: nine boxes of one tile under flat roofs,
beside a ring that has E3M3's section (a walk either side of a channel, the roof sloping from
the crown over the water to the walls). Seen all in one sweep on 2026-11-25 they were the
weakest place left, and the owner: "Yes, rebuild them". Each is what its name says now:

* the trunk and its ducts carry the ring's section on, with ribs of E3M3's cast blocks (487);
* the junction is a crossing: four piers round the well, and over it a drum lined with pipes
  (510, E3M3 s174) under its girders;
* the cistern is an arcade: a nave the way through takes, the tank on one side of it, on the
  other an aisle that stands in water;
* the pump room has pumps, one of which still goes, over the trench they drained;
* the annex is the screen chamber: bars across the room, and behind them what they have
  stopped, up the wall;
* the silt trap's bed is sunk, with the last of the water down the middle of it.

`refit.refit` cuts each room in place, so what is joined to it and wired to it is untouched.
Their lamps are here (`LAMPS`).
"""

from __future__ import annotations

from bloodmap import arrangement as A, wiring
from bloodmap.slope import SlopeSpec

import refit

PU = 1024
S = "region:gravesend/sewer/"
TRUNK, JUNCTION, CISTERN = S + "trunk/main_duct", S + "trunk/junction", S + "trunk/cistern"
RISER, FALL, ADIT = S + "trunk/duct_junction", S + "trunk/duct_cistern", S + "necks/west_adit"
PUMPS, ANNEX, SILT = S + "chambers/pump_room", S + "chambers/east_annex", S + "chambers/silt_trap"
FLOOR, CHANNEL, CROWN, SPRING, RIB = 61440, 63488, 32768, 40960, 43008
TOP = 28672                                                    # the sewer's band begins here
STONE, ROOF, WALL, WATER, BLOCKS, PIPES, TWIN = 568, 255, 492, 1120, 487, 510, 211
EARTH, IRON, GIRDER, BARS, PLATE, CASING, STEEL, GRATE = 270, 200, 191, 58, 438, 2453, 206, 470
SHIMMER = {"amplitude": -4, "shade_frequency": 4}
LIVING: dict[str, str] = {}


def _q(v: float) -> int:
    return round(v * PU)


def _rect(x0, y0, x1, y1):
    return [(_q(x0), _q(y0)), (_q(x1), _q(y0)), (_q(x1), _q(y1)), (_q(x0), _q(y1))]


def _flow(angle: int, velocity: int) -> dict:
    from l3_sewer import flow_behavior
    return {**SHIMMER, **flow_behavior(angle, velocity, False)}


class Room:
    """Cells over one room's rectangle: what each is, and what its walls wear."""

    def __init__(self, host: str, keep: str):
        self.host, self.keep, self.place = host, keep, A.Arrangement()
        self.what: dict[str, dict] = {}
        self.faces: list = []

    def cell(self, name: str, shape, floor=FLOOR, roof=CROWN, *, up=None, tread=None, flat=STONE, over=ROOF, wall=WALL, behavior=None, **more):
        """`up=(side, fall)`: the roof is `roof` on that side of the cell and falls to the other; `tread` the same of the floor."""
        self.place.add(name, _rect(*shape) if isinstance(shape[0], (int, float)) else shape)
        self.what[name] = {"floor": floor, "roof": roof, "up": up, "tread": tread, "flat": flat, "over": over, "wall": wall, "behavior": behavior or {}, "more": more}

    def rock(self, shape):
        self.place.solid(_rect(*shape) if isinstance(shape[0], (int, float)) else shape)

    def surface(self, name: str, outer) -> dict:
        w = self.what[name]
        fields = dict(floor_z=w["floor"], ceiling_z=w["roof"], floor_picnum=w["flat"], ceiling_picnum=w["over"], wall_picnum=w["wall"],
                      floor_shade=34, wall_shade=30, ceiling_shade=32, sector_behavior=dict(w["behavior"]), **w["more"])
        for key, slope in (("ceiling_slope", w["up"]), ("floor_slope", w["tread"])):
            if slope:
                side, fall = slope
                ax, pick = (0, min) if side == "w" else (0, max) if side == "e" else (1, min) if side == "n" else (1, max)
                at = pick(p[ax] for p in outer)
                hinge = next((a, b) for a, b in zip(outer, [*outer[1:], outer[0]]) if a[ax] == b[ax] == at)
                fields[key] = SlopeSpec(hinge=hinge, rise_z=fall)
        return fields

    def build(self, layout, face=lambda *_: {}) -> dict[str, str]:
        return refit.refit(layout, self.host, self.place.resolve(), self.keep, self.surface, face)


def _blocks(a, b) -> dict:
    """E3M3's cast blocks, whole ones across a rib."""
    length = ((a[0] - b[0]) ** 2 + (a[1] - b[1]) ** 2) ** 0.5
    return {"picnum": BLOCKS, "x_repeat": max(2, round(length / 128)), "y_repeat": 8, "x_panning": 0, "y_panning": 0}


def _ribs(name: str):
    return name.startswith("rib")


def _rib_face(seen, beyond, a, b) -> dict:
    """A rib wears the blocks on its own sides, and on the face that hangs before the vault."""
    if _ribs(seen) and beyond is None or beyond and _ribs(beyond) and not _ribs(seen):
        return _blocks(a, b)
    return {}


# ---- the runs -------------------------------------------------------------------

def _trunk(layout) -> dict:
    room = Room(TRUNK, "water_0")
    x0, x1, y0, y1 = 39.25, 50.0, 20.5, 22.5
    room.cell("head", (x0, y0, 40.75, y1), roof=36864)
    ribs = ((40.75, 41.0), (44.75, 45.0), (47.0, 47.25), (49.75, x1))
    for k, (a, b) in enumerate(ribs):
        room.cell(f"rib_{k}_n", (a, y0, b, 21.0), roof=RIB)
        room.cell(f"rib_{k}_w", (a, 21.0, b, 22.0), floor=CHANNEL, roof=SPRING, flat=WATER, behavior=_flow(0, 8))
        room.cell(f"rib_{k}_s", (a, 22.0, b, y1), roof=RIB)
    for k, (a, b) in enumerate((ribs[i][1], ribs[i + 1][0]) for i in range(3)):
        room.cell(f"walk_{k}_n", (a, y0, b, 21.0), up=("s", SPRING - CROWN))
        room.cell(f"water_{k}", (a, 21.0, b, 22.0), floor=CHANNEL, flat=WATER, behavior=_flow(0, 8))
        room.cell(f"walk_{k}_s", (a, 22.0, b, y1), up=("n", SPRING - CROWN))
    return room.build(layout, _rib_face)


def _riser(layout) -> dict:
    """A dry way with the mains beside it: the valve wheel is on its west wall."""
    room = Room(RISER, "west")
    room.cell("west", (39.25, 15.0, 40.0, 20.5), roof=36864, up=("e", 6144))
    room.cell("east", (40.0, 15.0, 40.5, 20.5), roof=36864, up=("w", 4096))
    room.cell("mains", (40.5, 15.0, 40.75, 20.5), floor=FLOOR - 9216, roof=SPRING, up=("w", 2048), flat=GRATE, wall=TWIN, role="detail")

    def face(seen, beyond, a, b):
        return {"picnum": TWIN, "x_repeat": max(1, round(abs(a[1] - b[1]) / 128)), "y_repeat": 8} if beyond == "mains" else {}
    return room.build(layout, face)


def _fall(layout) -> dict:
    room = Room(FALL, "water_0")
    for k, (a, b) in enumerate(((22.5, 24.5), (24.75, 27.0))):
        room.cell(f"walk_{k}_w", (45.25, a, 45.75, b), roof=36864, up=("e", 6144))
        room.cell(f"water_{k}", (45.75, a, 46.25, b), floor=FLOOR + 1024, roof=36864, flat=WATER, behavior=_flow(512, 12))
        room.cell(f"walk_{k}_e", (46.25, a, 46.75, b), roof=36864, up=("w", 6144))
    for side, a, b in (("w", 45.25, 45.75), ("e", 46.25, 46.75)):
        room.cell(f"rib_{side}", (a, 24.5, b, 24.75), roof=RIB)
    room.cell("rib_m", (45.75, 24.5, 46.25, 24.75), floor=FLOOR + 1024, roof=SPRING, flat=WATER, behavior=_flow(512, 12))
    return room.build(layout, _rib_face)


def _adit(layout) -> dict:
    room = Room(ADIT, "n_1")
    edges = (34.0, 35.5, 35.75, 37.5, 37.75, 39.25)
    for k in range(3):
        a, b = edges[2 * k], edges[2 * k + 1]
        room.cell(f"n_{k}", (a, 11.0, b, 12.0), roof=34816, up=("s", 8192))
        room.cell(f"s_{k}", (a, 12.0, b, 13.0), roof=34816, up=("n", 8192))
    for k in range(2):
        a, b = edges[2 * k + 1], edges[2 * k + 2]
        room.cell(f"rib_{k}", (a, 11.0, b, 13.0), roof=RIB)
    return room.build(layout, _rib_face)


# ---- the junction ---------------------------------------------------------------

CROSS, CROSS_R, PIER = (42.25, 12.0), 1.894, 0.35


def _junction(layout) -> dict:
    room = Room(JUNCTION, "drum")
    c = (_q(CROSS[0]), _q(CROSS[1]))
    room.cell("round", (39.25, 9.0, 44.0, 15.0), roof=RIB)
    room.rock((44.0, 9.0, 44.25, 15.0))
    for first in (0, 2, 4, 6):
        room.rock(A.arc(c, _q(CROSS_R) - 2, _q(CROSS_R + PIER), first, first + 1, 8, 1 / 16))
    room.cell("drum", A.circle(c, _q(CROSS_R), 8, 1 / 16), roof=TOP)
    room.cell("niche", (44.0, 11.4, 44.25, 12.6), roof=RIB, floor=FLOOR - 2048, wall=498)

    def face(seen, beyond, a, b):
        if seen == "drum" and beyond != "niche":
            length = ((a[0] - b[0]) ** 2 + (a[1] - b[1]) ** 2) ** 0.5
            if beyond is None:
                return {"picnum": BLOCKS, "x_repeat": max(2, round(length / 128)), "y_repeat": 8}
            return {"picnum": PIPES, "x_repeat": max(1, round(length / 128)), "y_repeat": 8}
        if seen == "round" and beyond is None and a[0] != b[0] and a[1] != b[1]:
            return _blocks(a, b)
        return {}
    return room.build(layout, face)


# ---- the cistern ----------------------------------------------------------------

ARCADE = (46.75, 47.1)
ARCHES = ((27.0, 28.0), (28.4, 29.6), (30.0, 31.0))


def _cistern(layout) -> dict:
    room = Room(CISTERN, "tank")
    room.cell("tank", (43.0, 27.0, 45.25, 31.0), roof=36864)
    room.cell("nave_w", (45.25, 27.0, 46.0, 31.0), roof=TOP, up=("e", 36864 - TOP))
    room.cell("nave_e", (46.0, 27.0, 46.75, 31.0), roof=TOP, up=("w", 36864 - TOP))
    room.cell("aisle", (ARCADE[1], 27.0, 49.0, 31.0), floor=CHANNEL, roof=SPRING, flat=WATER, behavior={**SHIMMER, "depth": 2})
    room.rock((ARCADE[0], 27.0, ARCADE[1], 31.0))
    for k, (a, b) in enumerate(ARCHES):
        room.cell(f"arch_{k}", (ARCADE[0], a, ARCADE[1], b), roof=RIB, wall=BLOCKS)

    def face(seen, beyond, a, b):
        if beyond is None and a[0] == b[0] and abs(a[1] - b[1]) < _q(0.5):
            return _blocks(a, b)
        if beyond is None and seen.startswith("arch"):
            return _blocks(a, b)
        return {}
    return room.build(layout, face)


# ---- the pump room --------------------------------------------------------------

MACHINES = ((28.15, 13.3), (28.15, 15.0), (28.15, 16.7))
CASE_R, ROD_R, CASE, LOW, HIGH = 0.5, 0.3, 14336, 17408, 29696
TRENCH, BRIDGE = (29.35, 12.6, 30.45, 17.4), (14.55, 15.45)


def _pump_room(layout) -> dict:
    import wires
    room = Room(PUMPS, "floor")
    room.cell("floor", (27.0, 12.0, 32.0, 18.0), roof=TOP)
    for a, b in ((13.4, 13.9), (16.1, 16.6)):
        room.rock((31.6, a, 32.0, b))
    room.cell("trench_n", (TRENCH[0], TRENCH[1], TRENCH[2], BRIDGE[0]), floor=FLOOR + 4096, roof=TOP, flat=WATER, wall=GRATE,
              behavior=dict(SHIMMER))
    room.cell("trench_s", (TRENCH[0], BRIDGE[1], TRENCH[2], TRENCH[3]), floor=FLOOR + 4096, roof=TOP, flat=WATER, wall=GRATE,
              behavior=dict(SHIMMER))
    room.cell("bridge", (TRENCH[0], BRIDGE[0], TRENCH[2], BRIDGE[1]), roof=TOP, flat=PLATE)
    for k, (x, y) in enumerate(MACHINES):
        c = (_q(x), _q(y))
        room.cell(f"case_{k}", A.circle(c, _q(CASE_R), 8, 1 / 16), floor=FLOOR - CASE, roof=TOP, flat=GRATE, wall=CASING, role="detail")
        more = {"type": 600, "behavior": {
            "busy_time_a": 21, "busy_time_b": 17, "busy_wave_a": 0, "busy_wave_b": 0, "retrigger_a": 1, "retrigger_b": 1,
            "off_floor_z": FLOOR - LOW, "on_floor_z": FLOOR - HIGH, "off_ceiling_z": TOP, "on_ceiling_z": TOP}} if k == 1 else {}
        room.cell(f"rod_{k}", A.circle(c, _q(ROD_R), 8, 1 / 16), floor=FLOOR - (LOW if k == 1 else LOW + 1024 * (k + 1)), roof=TOP, flat=PLATE,
                  wall=STEEL, role="detail", **more)

    def face(seen, beyond, a, b):
        if beyond and beyond.startswith("case") and seen == "floor":
            return {"picnum": CASING, "x_repeat": 8, "y_repeat": 9, "x_panning": 0, "y_panning": 0}
        if beyond and beyond.startswith("rod"):
            return {"picnum": STEEL, "x_repeat": 4, "y_repeat": 8, "x_panning": 0, "y_panning": 0}
        if beyond is None and a[0] >= _q(31.6) and b[0] >= _q(31.6) and not (a[0] == b[0] == _q(32.0)):
            return _blocks(a, b)
        if beyond and beyond.startswith("trench"):
            return {}
        return {}
    regions = room.build(layout, face)
    LIVING["rod"] = regions["rod_1"]
    wires.wire("pump:engine").then(wiring.region(regions["rod_1"]))
    return regions


# ---- the screens and the silt ---------------------------------------------------

LINE, GAP = 55.5, (16.4, 17.6)


def _screens(layout) -> dict:
    room = Room(ANNEX, "heap_m")
    room.cell("front", (53.0, 14.0, LINE, 20.0), roof=TOP)
    for name, a, b, up in (("heap_n", 14.0, GAP[0], 18432), ("heap_m", *GAP, 7168), ("heap_s", GAP[1], 20.0, 13312)):
        room.cell(name, (LINE, a, 57.0, b), roof=TOP, flat=EARTH, tread=("w", -up))

    def face(seen, beyond, a, b):
        pair = {seen, beyond}
        if "front" in pair and pair & {"heap_n", "heap_s"}:
            return {"over_picnum": BARS, "cstat": 1 | 16 | 64, "x_repeat": round(abs(a[1] - b[1]) / 256), "y_repeat": 4, "x_panning": 0, "y_panning": 0}
        if beyond in ("heap_n", "heap_m", "heap_s"):
            return {"picnum": 110}
        return {}
    return room.build(layout, face)


BED = (46.5, 3.5, 49.4, 5.3)


def _silt(layout) -> dict:
    room = Room(SILT, "floor")
    x0, y0, x1, y1 = BED
    room.cell("floor", (45.5, 2.0, 50.0, 6.0), roof=SPRING)
    for a, b in ((46.6, 47.0), (48.4, 48.8)):
        room.rock((a, 5.6, b, 6.0))
    room.cell("bank_n", (x0, y0, x1, 4.2), roof=SPRING, flat=EARTH, tread=("n", 3584))
    room.cell("last", (x0, 4.2, x1, 4.6), floor=FLOOR + 3840, roof=SPRING, flat=WATER, behavior=dict(SHIMMER))
    room.cell("bank_s", (x0, 4.6, x1, y1), roof=SPRING, flat=EARTH, tread=("s", 3584))

    def face(seen, beyond, a, b):
        if beyond is None and a[1] >= _q(5.6) and b[1] >= _q(5.6) and not a[1] == b[1] == _q(6.0):
            return _blocks(a, b)
        return {}
    return room.build(layout, face)


# ---- all of it ------------------------------------------------------------------

BUILT: dict[str, dict[str, str]] = {}


def build(layout) -> dict:
    """Refit the nine rooms. Before anything is carved in them (`underwater`'s pools)."""
    refit.begin()
    BUILT.clear()
    for name, make in (("trunk", _trunk), ("riser", _riser), ("fall", _fall), ("adit", _adit), ("junction", _junction), ("cistern", _cistern),
                       ("pumps", _pump_room), ("annex", _screens), ("silt", _silt)):
        BUILT[name] = make(layout)
    return {name: len(regions) for name, regions in BUILT.items()}


def movers() -> frozenset[str]:
    """What rises and is no door."""
    return frozenset(LIVING.values())


#: the lamps: (room, cell, x, y, tile, x and y repeat)
TUBE, ROUND = 796, 795
LAMPS = (("trunk", "head", 40.0, 21.5, TUBE, 64, 48), ("trunk", "water_0", 42.9, 21.5, TUBE, 48, 64), ("trunk", "water_2", 48.5, 21.5, TUBE, 48, 64),
         ("fall", "water_1", 46.0, 25.9, ROUND, 40, 40), ("adit", "rib_0", 35.62, 12.0, ROUND, 28, 28), ("adit", "rib_1", 37.62, 12.0, ROUND, 28, 28),
         ("junction", "round", 39.9, 14.2, ROUND, 48, 48), ("junction", "drum", 41.2, 12.0, ROUND, 96, 96),
         ("cistern", "tank", 44.1, 27.4, TUBE, 64, 48), ("cistern", "aisle", 48.0, 30.2, ROUND, 56, 56),
         ("pumps", "floor", 27.9, 14.15, ROUND, 80, 80), ("pumps", "floor", 31.0, 16.8, ROUND, 64, 64),
         ("annex", "front", 54.3, 15.4, TUBE, 64, 48), ("annex", "heap_s", 56.2, 18.9, ROUND, 48, 48),
         ("silt", "floor", 49.0, 2.75, TUBE, 64, 48), ("silt", "floor", 46.0, 5.2, ROUND, 48, 48))
#: what lies on the heap (827, boots, is the jump boots' picture: `tiles-have-jobs`): (room, cell, x, y, tile, x and y repeat, cstat, seat)
LYING = (("annex", "heap_n", 55.95, 15.1, 2333, 40, 42, 128), ("annex", "heap_s", 56.0, 18.5, 2334, 40, 42, 128),
         ("annex", "heap_n", 56.3, 16.0, 684, 40, 40, 128), ("annex", "heap_s", 55.85, 19.3, 683, 30, 30, 128),
         ("annex", "heap_n", 56.6, 14.6, 683, 34, 34, 128), ("annex", "heap_m", 56.2, 16.75, 683, 32, 32, 128),
         ("annex", "heap_s", 56.7, 17.9, 684, 40, 40, 128))


def dress(layout) -> dict:
    """The lamps, the girders over the drum, the pumps' pipes, and what the bars have stopped."""
    import math
    import wallplane
    for k, (room, cell, x, y, tile, xr, yr) in enumerate(LAMPS):
        region = BUILT[room][cell]
        r = layout.regions[region]
        layout.add_sprite(f"sewer_rooms:lamp_{k}", region, x=_q(x), y=_q(y), z=r.ceiling_z + 64, picnum=tile, x_repeat=xr, y_repeat=yr,
                          cstat=32 | 128, shade=-128)
    # E3M3 hangs its girders flat under the roof of such a hall (s15, twelve of them)
    drum = BUILT["junction"]["drum"]
    roof = layout.regions[drum].ceiling_z
    layout.add_sprite("sewer_rooms:girders", drum, x=_q(CROSS[0]), y=_q(CROSS[1]), z=roof + 4096, picnum=GIRDER, x_repeat=104, y_repeat=104,
                      cstat=1 | 32 | 128 | 256, shade=12)
    art = wallplane.art()
    for k, (x, y) in enumerate(MACHINES):
        a, b, up = x + CASE_R, TRENCH[0] + 0.45, 9216
        length = _q(b - a)
        layout.add_sprite(f"sewer_rooms:pipe_{k}", BUILT["pumps"]["floor"], x=_q((a + b) / 2) - 64, y=_q(y), z=FLOOR - up, picnum=303,
                          x_repeat=min(255, round(length * 4 / art[303][0])), y_repeat=12, angle=512, cstat=16 | 128, shade=24, pal=5)
    from bloodmap.placement import drawn_extent
    for k, (room, cell, x, y, tile, xr, yr, cstat) in enumerate(LYING):
        region = BUILT[room][cell]
        r = layout.regions[region]
        rise = -r.floor_slope.rise_z * (x - LINE) / (57.0 - LINE)
        _w, height, _x, offset = art[tile]
        _top, bottom = drawn_extent(height, offset, yr, cstat)
        layout.add_sprite(f"sewer_rooms:lying_{k}", region, x=_q(x), y=_q(y), z=round(r.floor_z - rise - bottom) - 96, picnum=tile, x_repeat=xr,
                          y_repeat=yr, cstat=cstat, shade=8, sunk=True)
    return {"lamps": len(LAMPS), "lying": len(LYING)}
