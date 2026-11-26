"""The pump station's big machine: the filter that hangs over its basin, and a pump either side of it that never stops.

The owner, 2026-11-25: "I would focus on that pump station now". A blind reader of its best
view (showcase round 14): it lacks "a recognizable piece of machinery that connects the sludge
vats to the controls and shows what the hall does". A filter drum stood in it once, a unit and
a half before the way in, and was all a player saw (`references/pump-hall-design.md`, 7); so
this is at the far side of what one looks over from the deck. (The belt's hood shuts off the
other half: pumps in the south bay were seen from nowhere but beside them.)

The filter is the basin's own sector: its ceiling comes down to two bodies over the floor, and
what is seen is the ten-sided drum between that and the roof (its faces are the rim's walls),
with one round lamp (795) in its mesh over the sludge. Two pipes go from it: to the consoles
and to the head of the belt. A linked floor is one sector and stays one: nothing is cut in it.

The pumps stand in the corners of the north wall, a casing each, and in it a rod that goes up
and down (type 600 from the level's start, `retrigger` at both ends, as E4M7's nine movers
are), each at its own pace. Nobody can get under them.
"""

from __future__ import annotations

import math

from bloodmap import arrangement as A, wiring

PU = 1024
STATION = "region:gravesend/foundry_ward/pump_station"
HALL, TANK, RIM = f"{STATION}/machine_hall", f"{STATION}/tank_0", f"{STATION}/tank_0_plinth"
KEY = f"{STATION}/pumps"
GRADE = 8192
#: the filter's underside over the hall's floor, what its sides are and what that is: pressed metal, a filter's mesh. (It was 501, and
#: the owner: "That ceiling texture on over that water tank is texture of lights, I would use different texture for that, there is
#: already ceiling light as a sprite anyway".)
UNDER, DRUM, MESH = 37376, 488, 215
#: each pump: its middle, its stroke's tenths up and down
PUMPS = ((40.46, 4.02, 14, 11), (43.6, 4.02, 17, 13))
CASE_R, ROD_R = 0.36, 0.23
CASE, LOW, HIGH = 27648, 30720, 55296                          # over the floor: the casing's head, and the rod's at either end
PLATE, CLADDING, STEEL, HEAD, PLATING = 438, 2453, 206, 487, 470
#: tubes on the wall behind them, so that they are seen against it
TUBES, TUBE = (40.88, 43.18), 796
#: pipes: (from, to, how far over the floor)
PIPES, PIPE = (((40.0, 4.6), (41.2, 4.6), 70000), ((41.75, 6.05), (41.75, 8.45), 62000)), 303
IRON = 5                                                       # grey: the pipe's own is copper, and reads as timber
_MADE: dict[str, str] = {}
_PAINTED: list[tuple[str, tuple, tuple, dict]] = []


def _q(v: float) -> int:
    return round(v * PU)


def build(layout) -> dict:
    """The filter's ceiling, the casings and the rods."""
    import wires
    _MADE.clear()
    _PAINTED.clear()
    tank = layout.regions[TANK]
    tank.ceiling_z, tank.ceiling_picnum, tank.ceiling_shade = GRADE - UNDER, MESH, 10
    hall = layout.regions[HALL]
    place = A.Arrangement()
    for k, (x, y, _up, _down) in enumerate(PUMPS):
        place.add(f"case_{k}", A.circle((_q(x), _q(y)), _q(CASE_R), 8, 1 / 16))
        place.add(f"rod_{k}", A.circle((_q(x), _q(y)), _q(ROD_R), 8, 1 / 16))
    cells = place.resolve()
    kind = {c.name: c.name.split("_")[0] for c in cells}
    rises = {"case": CASE, "rod": LOW}
    tops = {"case": PLATING, "rod": PLATE}
    faces = {"case": CLADDING, "rod": STEEL}

    def surface(cell):
        fields = dict(floor_z=GRADE - rises[kind[cell]], ceiling_z=hall.ceiling_z, floor_picnum=tops[kind[cell]], wall_picnum=faces[kind[cell]],
                      ceiling_picnum=hall.ceiling_picnum, layer=hall.layer, floor_shade=hall.floor_shade, wall_shade=hall.wall_shade,
                      ceiling_shade=hall.ceiling_shade, role="detail", declared_zero_exit=True, intent={"kind": "furnished"})
        if kind[cell] == "rod":
            _x, _y, up, down = PUMPS[int(cell.split("_")[1])]
            fields.update(type=600, sector_behavior={
                "busy_time_a": up, "busy_time_b": down, "busy_wave_a": 0, "busy_wave_b": 0, "retrigger_a": 1, "retrigger_b": 1,
                "off_floor_z": GRADE - LOW, "on_floor_z": GRADE - HIGH, "off_ceiling_z": hall.ceiling_z, "on_ceiling_z": hall.ceiling_z})
        return fields

    def face(seen, beyond, a, b):
        if beyond is None or rises[kind[beyond]] <= rises[kind[seen]]:
            return {}
        paint = {"picnum": faces[kind[beyond]], "x_repeat": 4, "y_repeat": 8, "x_panning": 0, "y_panning": 0}
        _PAINTED.append((f"{KEY}:{seen}", a, b, paint))
        return paint
    for cell in cells:
        if kind[cell.name] == "case":
            layout.carve_hole(HALL, list(cell.outer))
    regions = A.lay(layout, KEY, cells, surface, face)
    for cell, a, b in A.rim(cells):
        layout.add_connection(f"connection:pumps:{a[0]}:{a[1]}", HALL, regions[cell], a1=b, a2=a, min_width=1, min_opening=0)
        paint = {"picnum": CLADDING, "x_repeat": 8, "y_repeat": 9, "x_panning": 0, "y_panning": 0}
        layout.paint_wall(HALL, b, a, fixed_frame=True, **paint)
        _PAINTED.append((HALL, b, a, paint))
    _MADE.update(regions)
    started = wires.wire("pump:engine")
    for k in range(len(PUMPS)):
        started.then(wiring.region(regions[f"rod_{k}"]))
    return {"pumps": len(PUMPS), "filter": tank.ceiling_z}


def movers() -> frozenset[str]:
    """What rises and is no door."""
    return frozenset(r for name, r in _MADE.items() if name.startswith("rod_"))


def _art(tile: int):
    from bloodmap import wallplane
    return wallplane.art()[tile]


def dress(layout) -> dict:
    """The tubes behind the pumps, the filter's pipes, and the light under it."""
    for k, x in enumerate(TUBES):
        layout.add_sprite(f"pumps:tube_{k}", HALL, x=_q(x), y=_q(3.5) + 6, z=GRADE - 40000, picnum=TUBE, x_repeat=40, y_repeat=56, angle=512,
                          cstat=16 | 64 | 128, shade=-64)
    for k, ((ax, ay), (bx, by), up) in enumerate(PIPES):
        length = math.hypot(_q(bx - ax), _q(by - ay))
        count = max(1, round(length / 1400))
        for n in range(count):
            t = (n + 0.5) / count
            layout.add_sprite(f"pumps:pipe_{k}_{n}", HALL, x=_q(ax + (bx - ax) * t), y=_q(ay + (by - ay) * t), z=GRADE - up,
                              picnum=PIPE, x_repeat=min(255, round(length / count * 4 / _art(PIPE)[0])), y_repeat=28,
                              angle=512 if ay == by else 0, cstat=16 | 128, shade=20, pal=IRON)
    middle = layout.regions[TANK]
    xs, ys = [p[0] for p in middle.outer], [p[1] for p in middle.outer]
    layout.add_sprite("pumps:under", TANK, x=(min(xs) + max(xs)) // 2, y=(min(ys) + max(ys)) // 2, z=middle.ceiling_z + 64, picnum=795, x_repeat=128,
                      y_repeat=128, cstat=32 | 64 | 128 | 8, shade=-64, sunk=True)
    return {"tubes": len(TUBES), "pipes": len(PIPES)}


def keep(level, compiled) -> int:
    """The machines' faces, put back after the passes that take a step for a facade; and the drum on the rim's inner walls."""
    from bloodmap.model import record_fields
    where = {}
    for region in {r for r, *_rest in _PAINTED}:
        for wall in compiled.allocations[region].wall_ids:
            f = record_fields(level.walls[wall])
            end = record_fields(level.walls[int(f["point2"])])
            where[region, (f["x"], f["y"]), (end["x"], end["y"])] = f
    put = 0
    for region, a, b, paint in _PAINTED:
        f = where.get((region, tuple(a), tuple(b))) or where.get((region, tuple(b), tuple(a)))
        if f is not None:
            f.update(paint)
            put += 1
    tank = compiled.allocations[TANK].sector_id
    for wall in compiled.allocations[RIM].wall_ids:
        f = record_fields(level.walls[wall])
        if int(f["next_sector"]) == tank:
            f.update(picnum=DRUM, x_repeat=8, y_repeat=8, x_panning=0, y_panning=0)
            put += 1
    return put
