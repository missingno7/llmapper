"""The stair down to the Phantom Terminus: two flights under sloped roofs, and between them the landing the public way came in by, bricked up.

The owner, 2026-11-25: "Stairs to ghost station have repeated wall pattern on each step
instead of being aligned. Check how these stairs looks like and try to improve them." They
were twenty-eight boxes of one sewer wall, a roof stepping down with them, and no light.

What Blood does with a flight this long: the wall's courses run on from step to step
(E6M5 s304, s305, s314), and the roof comes down with it (E4M5 s113-s114 slope with the flight;
E3M8 s113-s115 keep one flat roof). So the hatch is the last of the waterworks: behind it
is the railway's own plaster and slabs, a stone string along either side of the flight with
its top sloped as the stair is, and half way a landing, where a lamp is failing. The way the
passengers came down joins it there, and three steps up it is brick: whoever walled it up
left a lantern on this side.

Built of `bloodmap.arrangement` between the hatch (`phantom_terminus.build`) and the booking
hall; the strings are in pieces two treads long, so that the light on them goes by degrees.
"""

from __future__ import annotations

from bloodmap import arrangement as A
from bloodmap.slope import SlopeSpec

KEY = "region:gravesend/sewer/ghost_stair"
LAYER = "ghost_station"
HATCH_FLOOR, FOOT_FLOOR = 61440, 118784
STEPS, STEP, TREAD = 14, 2048, 256                             # to a flight, of which there are two
CLEAR = 24576                                                  # over the nosings
#: across: the strings' outer faces and the treads between them (the hatch is 47,808 to 49,088)
WEST, EAST, STRING = 47616, 49152, 128
#: along, going north: the hatch, the first nosing, the landing, the second, the booking hall
HATCH, FIRST, LANDING, SECOND, FOOT = 1024, 512, 512 - STEPS * TREAD, -7936 + STEPS * TREAD, -7936
#: how far the string's top is over the line of the nosings
PROUD = 4608
HALF_WAY = HATCH_FLOOR + STEPS * STEP
#: the way in that was walled up: its mouth along the landing's east side, how deep to the steps, the steps and how far each goes
WAY, WAY_DEEP, WAY_STEPS, WAY_TREAD, WAY_CLEAR = (-4224, -3200), 512, 3, 256, 22528
PLASTER, SLABS, ROOF, BRICK = 369, 374, 379, 383
PIECE = 2                                                      # treads to a piece of string


def _flights():
    """(name, its head along y, the floor and the roof there)."""
    return (("upper", FIRST, HATCH_FLOOR, HATCH_FLOOR - CLEAR), ("lower", SECOND, HALF_WAY, HALF_WAY - CLEAR))


def plan() -> list:
    """Every cell between the hatch and the booking hall."""
    place = A.Arrangement()

    def rect(name, x0, y0, x1, y1):
        place.add(name, [(x0, y0), (x1, y0), (x1, y1), (x0, y1)])
    rect("head", WEST, FIRST, EAST, HATCH)
    for flight, head, _floor, _roof in _flights():
        for k in range(STEPS):
            y = head - TREAD * k
            rect(f"{flight}_{k + 1}", WEST + STRING, y - TREAD, EAST - STRING, y)
        for k in range(0, STEPS, PIECE):
            y0, y1 = head - TREAD * (k + PIECE), head - TREAD * k
            rect(f"{flight}_west_{k}", WEST, y0, WEST + STRING, y1)
            rect(f"{flight}_east_{k}", EAST - STRING, y0, EAST, y1)
    rect("landing", WEST, SECOND, EAST, LANDING)
    rect("way", EAST, WAY[0], EAST + WAY_DEEP, WAY[1])
    for k in range(WAY_STEPS):
        x = EAST + WAY_DEEP + WAY_TREAD * k
        rect(f"way_{k + 1}", x, WAY[0], x + WAY_TREAD, WAY[1])
    return place.resolve()


def _where(cell: str) -> tuple[str, str, int]:
    """("upper", "step", 3), ("lower", "west", 4), ("landing", "", 0)."""
    part, *rest = cell.split("_")
    if part in ("upper", "lower"):
        return (part, "step", int(rest[0])) if len(rest) == 1 else (part, rest[0], int(rest[1]))
    return part, "", int(rest[0]) if rest else 0


def levels(cell: str) -> tuple[int, int, int]:
    """A cell's floor and roof at its upper edge, and how far its roof falls to the lower one."""
    part, kind, k = _where(cell)
    for flight, _head, floor, roof in _flights():
        if part == flight and kind == "step":
            return floor + STEP * k, roof + STEP * (k - 1), STEP
        if part == flight:
            return floor + STEP * k - PROUD, roof + STEP * k, STEP * PIECE
    return {"head": (HATCH_FLOOR, HATCH_FLOOR - CLEAR, 0), "landing": (HALF_WAY, HALF_WAY - CLEAR, 0)}.get(
        part, (HALF_WAY - STEP * k, HALF_WAY - WAY_CLEAR, 0))


def _surface(cell: str, outer) -> dict:
    part, kind, _k = _where(cell)
    floor, roof, falls = levels(cell)
    fields = dict(floor_z=floor, ceiling_z=roof, floor_picnum=SLABS, ceiling_picnum=ROOF, wall_picnum=PLASTER, floor_shade=20,
                  ceiling_shade=24, wall_shade=18, layer=LAYER, role="interior", declared_zero_exit=True, intent={"kind": "furnished"})
    if falls:
        top = max(y for _x, y in outer)
        hinge = next((a, b) for a, b in zip(outer, [*outer[1:], outer[0]]) if a[1] == b[1] == top)
        fields["ceiling_slope"] = SlopeSpec(hinge=hinge, rise_z=falls)
        if kind != "step":
            fields.update(floor_slope=SlopeSpec(hinge=hinge, rise_z=falls), floor_picnum=ROOF, role="detail")
    return fields


def _run(a, b, start: int) -> dict:
    """How a wall's pattern is laid so that it goes on from the one before it: from `start` along the stair, whichever way it is walked."""
    along = 1 if a[0] == b[0] else 0
    goes = b[along] - a[along]
    return {"x_repeat": max(1, round(abs(goes) / 128)), "y_repeat": 8,
            "x_panning": ((a[along] - start if goes > 0 else start - a[along]) // 16) % 64}


def _courses(top: int, tall: int = 64) -> int:
    """The panning that hangs a tile's rows on one height everywhere: `top` is what the wall is drawn down from."""
    return (top - HATCH_FLOOR) // 256 * 256 // tall % 256


def _face(seen: str, beyond: str | None, a, b) -> dict:
    here, there = _where(seen), _where(beyond) if beyond else None
    floor, roof, _falls = levels(seen)
    if there is None and a[1] == b[1] in (HATCH, FOOT):
        return {}                                              # the hatch's and the booking hall's side: joined in `build`
    if there is None:
        tile = BRICK if here[0] == "way" and here[2] == WAY_STEPS and a[0] == b[0] else PLASTER
        return {"picnum": tile, "cstat": 0, "y_panning": _courses(roof), **_run(a, b, HATCH)}
    other = levels(beyond)[0]
    if other < floor and (there[1] in ("west", "east") or here[1] in ("west", "east")):
        return {"picnum": PLASTER, "cstat": 0, "y_panning": _courses(other), **_run(a, b, HATCH)}
    if other < floor:
        return {"picnum": ROOF, "cstat": 0, "y_panning": 0, **_run(a, b, WEST)}                   # a riser, its edge at the nosing
    return {"picnum": PLASTER, "cstat": 0, "y_panning": _courses(roof), **_run(a, b, HATCH)}


def build(layout, hatch: str, booking: str) -> dict[str, str]:
    """Lay the stair and join it at both ends; light it, and hang what is left on its walls."""
    cells = plan()
    outline = {c.name: list(c.outer) for c in cells}
    regions = A.lay(layout, KEY, cells, lambda name: _surface(name, outline[name]), _face)
    for name, a, b in A.rim(cells):
        if a[1] == b[1] == HATCH:
            # the hatch is narrower than the head of the stair: the wall either side of it is the head's own
            x0, x1 = 47808, 49088
            flip = a[0] < b[0]
            p, q = ((x0, HATCH), (x1, HATCH)) if flip else ((x1, HATCH), (x0, HATCH))
            layout.add_connection("connection:ghost_stair_head", hatch, regions[name], a1=q, a2=p, min_width=1, min_opening=0)
        elif a[1] == b[1] == FOOT:
            layout.add_connection(f"connection:ghost_stair_foot:{name}", booking, regions[name], a1=b, a2=a, min_width=1, min_opening=0)
            layout.paint_wall(booking, b, a, picnum=PLASTER)
    _light(layout, regions)
    _dress(layout, regions)
    return regions


def _light(layout, regions) -> None:
    for cell, y, size, shade in (("head", (FIRST + HATCH) // 2, 40, -30), ("landing", (LANDING + SECOND) // 2, 48, -40)):
        region = regions[cell]
        layout.add_sprite(f"phantom:stair_lamp_{cell}", region, x=(WEST + EAST) // 2, y=y, z=layout.regions[region].ceiling_z + 64,
                          picnum=795, cstat=160, x_repeat=size, y_repeat=size, shade=shade)


#: bills down the strings' walls: (flight, side, treads down, tile, size)
BILLS = (("upper", "west", 5, 356, 34), ("upper", "east", 9, 453, 32), ("upper", "west", 11, 356, 34),
         ("lower", "east", 3, 356, 34), ("lower", "west", 7, 453, 32), ("lower", "east", 10, 356, 34))


def _dress(layout, regions) -> None:
    from bloodmap import wallplane
    from phantom_terminus import _prop, _sign
    for n, (flight, side, down, tile, size) in enumerate(BILLS):
        head, floor = next((y, f) for name, y, f, _r in _flights() if name == flight)
        cell = f"{flight}_{side}_{down // PIECE * PIECE}"
        x = WEST + 6 if side == "west" else EAST - 6
        tall = wallplane.art()[tile][1] * size * 4
        nose = floor + STEP * down                              # the line of the nosings there
        layout.add_sprite(f"phantom:stair_bill_{n}", regions[cell], x=x, y=head - TREAD * down - TREAD // 2, z=nose - 18432 + tall // 2 - STEP // 2,
                          picnum=tile, x_repeat=size, y_repeat=size, angle=0 if side == "west" else 1024, cstat=16 | 64 | 128, shade=6)
    _sign(layout, regions["landing"], "stair_trains", (WEST, LANDING), (WEST, SECOND), "TRAINS", size=56, height=1.05)
    way = regions["way"]
    y0, y1 = WAY
    _prop(layout, way, "stair_lantern", EAST + 420, y0 + 120, 693, 34, 36, shade=-20)
    for i, (x, y, tile, size) in enumerate(((EAST + 250, y1 - 160, 2621, 34), (EAST + 420, y1 - 120, 2622, 36), (EAST + 330, y1 - 330, 2623, 30))):
        _prop(layout, way, f"stair_brick_{i}", x, y, tile, size, size, shade=0)
    _prop(layout, way, "stair_mason", EAST + 256, (y0 + y1) // 2, 2333, 32, 34, shade=0)
