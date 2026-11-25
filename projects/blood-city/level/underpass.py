"""The underpass under the works: a long tiled passage from the yard to the avenue, lit from a few tubes, with a shut metro behind bars.

The owner, 2026-11-24: "I would also rework the underpass, add there some posters
and things, making it look more liminal." What it was: five metres of brick
between two stairs, and from the avenue a blank recess with a carpet.

What it is (`references/underpass-design.md`): six bays of one passage, alike to
the poster, 22 metres from a blind corner under the yard's stair to another at the
foot of the avenue's. One tube is dead, one is failing. Half way a shut ticket
hall opens on the east side; behind its bars is the bed of a line that was begun,
and far down it one bulb, and a pram. Nobody is here. Leaving the hall for the
first time is the one thing that is answered.

The finish is DWE2M2's passage (s634: grey plaster over a red tiled dado 2294,
tubes 2290 in the roof) and the owner's own (DNE3L6 s171: grimy tiles 296 on
the stairs, interlocking paving 287, slabs 40 overhead). Built of
`bloodmap.arrangement`, but for the two porches, which are rooms of the tree
because the street is joined to them.
"""

from __future__ import annotations

from bloodmap import arrangement as A, wiring
from bloodmap.slope import SlopeSpec

PU = 1024
KEY = "region:gravesend/foundry_ward/works_stair/underpass"
LAYER = "underpass"
GRADE, FLOOR = 8192, 24576
#: ceilings: the passage (1.7 bodies), the beams across it, the ticket hall and the tunnel (one tile of bars high)
CEILING, BEAM, HALL, TUNNEL = -4096, 0, -8192, -8192
STEP, TREADS, TREAD = 2048, 7, 0.375
PORCH_HEAD = GRADE - 32768
#: the two street faces, and the flights down from a porch half a unit deep in each
YARD_FACE, AVENUE_FACE, PORCH = 49.0, 39.0, 0.5
YARD_MOUTH, AVENUE_MOUTH = (18.0, 20.0), (31.0, 33.0)
YARD_FOOT = YARD_FACE - PORCH - TREADS * TREAD
AVENUE_FOOT = AVENUE_FACE + PORCH + TREADS * TREAD
#: the passage, its beams and its bays
WEST, EAST = 43.0, 45.0
BEAMS = (20.75, 22.75, 24.75, 26.75, 28.75, 30.75)
BEAM_DEEP = 0.25
#: the ticket hall: its box, the shut window, the bench, and the mouth of the line
TICKETS = (EAST, 25.5, 47.5, 30.75)
WINDOW = (47.5, 28.5, 47.75, 30.0)
BENCH = (45.5, 30.375, 47.25, 30.75)
MOUTH = (25.75, 27.25)
BARS, BED, BRICKED = 47.5, 51.0, 52.625
#: where the pram stands, and how far it comes: its sweep is clear in plan of the
#: cistern's wall under it (y 27) and of the ring's (x 51)
PLATE = (50.1875, 26.125, 50.9375, 26.875)
COMES = 2.125
LIGHTBOX = (43.5, 33.0, 44.5, 33.125)
#: the freight recess opens off the second bay
RECESS = (23.0, 24.5)
SILL, SEAT = 9216, 5120

DADO, GRIMY, PAVING, SLAB, STONE, EDGE = 2294, 296, 287, 40, 281, 429
BRICK, CONCRETE, GRAVEL, SHUTTER, WOOD, PLANK, LIT = 417, 272, 416, 9, 34, 28, 2290
#: 2294 is 256 rows: the dado's top is row 154, and it is shown 0.8 of a body high (DWE2M2)
DADO_TOP, DADO_ROWS = 154, 52
TUBE, DEAD_TUBE, BULB, PRAM = 2290, 2291, 947, 183

WIRE = "underpass:pram"


def _q(v: float) -> int:
    return round(v * PU)


def _rect(x0, y0, x1, y1):
    return [(_q(x0), _q(y0)), (_q(x1), _q(y0)), (_q(x1), _q(y1)), (_q(x0), _q(y1))]


def plan() -> list:
    """Every cell between the two porches."""
    place = A.Arrangement()
    for k in range(TREADS):
        x = YARD_FACE - PORCH - TREAD * k
        place.add(f"yard_{k + 1}", _rect(x - TREAD, YARD_MOUTH[0], x, YARD_MOUTH[1]))
        x = AVENUE_FACE + PORCH + TREAD * k
        place.add(f"avenue_{k + 1}", _rect(x, AVENUE_MOUTH[0], x + TREAD, AVENUE_MOUTH[1]))
    place.add("north", _rect(WEST, YARD_MOUTH[0], YARD_FOOT, YARD_MOUTH[1]), _rect(WEST, YARD_MOUTH[1], EAST, BEAMS[0]))
    for k, y in enumerate(BEAMS, 1):
        place.add(f"beam_{k}", _rect(WEST, y, EAST, y + BEAM_DEEP))
        if k < len(BEAMS):
            place.add(f"bay_{k}", _rect(WEST, y + BEAM_DEEP, EAST, BEAMS[k]))
    place.add("south", _rect(AVENUE_FOOT, AVENUE_MOUTH[0], EAST, AVENUE_MOUTH[1]))
    place.add("lightbox", _rect(*LIGHTBOX))
    place.add("tickets", _rect(*TICKETS))
    place.add("window", _rect(*WINDOW))
    place.add("bench", _rect(*BENCH))
    place.add("bed", _rect(BARS, MOUTH[0], BED, MOUTH[1]))
    place.add("plate", _rect(*PLATE))
    place.add("end", _rect(BED, MOUTH[0], BRICKED, MOUTH[1]))
    return place.resolve()


def _part(cell: str) -> tuple[str, int]:
    kind, _, number = cell.partition("_")
    return kind, int(number or 0)


def levels(cell: str) -> tuple[int, int]:
    """A cell's floor and ceiling."""
    kind, k = _part(cell)
    if kind in ("yard", "avenue"):
        # the roof comes down with the stair in one slope: this is its head, at the tread's upper edge
        return GRADE + STEP * k, PORCH_HEAD + round((CEILING - PORCH_HEAD) * (k - 1) / TREADS)
    return {"beam": (FLOOR, BEAM), "tickets": (FLOOR, HALL), "window": (FLOOR - SILL, FLOOR - 22528),
            "bench": (FLOOR - SEAT, HALL), "bed": (FLOOR, TUNNEL), "plate": (FLOOR, TUNNEL),
            "end": (FLOOR, TUNNEL), "lightbox": (FLOOR - 7168, FLOOR - 24576)}.get(kind, (FLOOR, CEILING))


TUNNEL_CELLS = ("bed", "plate", "end")


def _surface(cell: str, outer=()) -> dict:
    kind, k = _part(cell)
    floor, ceiling = levels(cell)
    wall, under, over, slope = DADO, PAVING, SLAB, {}
    if kind in ("yard", "avenue"):
        wall, under = GRIMY, STONE
        xs = [p[0] for p in outer]
        head = max(xs) if kind == "yard" else min(xs)
        hinge = next((a, b) for a, b in zip(outer, outer[1:] + outer[:1]) if a[0] == b[0] == head)
        slope = {"ceiling_slope": SlopeSpec(hinge=hinge, rise_z=round((CEILING - PORCH_HEAD) * k / TREADS) + PORCH_HEAD - ceiling)}
    elif kind in TUNNEL_CELLS:
        wall, under, over = BRICK, CONCRETE, GRAVEL
    elif kind == "lightbox":
        wall, under, over = LIT, LIT, LIT
    elif kind == "window":
        wall, under = SHUTTER, WOOD
    elif kind == "bench":
        under = WOOD
    more = {"role": "detail"} if kind in ("window", "bench", "lightbox") else {}
    if kind == "lightbox":
        more |= {"floor_shade": 0, "ceiling_shade": -8, "wall_shade": -8}      # kept (`lights.OWN_LIGHT`)
    return {"floor_z": floor, "ceiling_z": ceiling, "floor_picnum": under, "ceiling_picnum": over, "wall_picnum": wall,
            "floor_shade": 16, "ceiling_shade": 18, "wall_shade": 14, "layer": LAYER, "role": "interior",
            "declared_zero_exit": True, "intent": {"kind": "furnished"}, **slope, **more}


def _dado(cell: str, a, b, lower: int) -> dict:
    """The plaster and its dado, hung so that the dado stands on the floor at its own height."""
    _floor, ceiling = levels(cell)
    length = abs(a[0] - b[0]) + abs(a[1] - b[1])
    return {"picnum": DADO, "x_repeat": max(1, min(255, round(length / 128))), "y_repeat": 8, "x_panning": 0,
            "y_panning": (DADO_TOP + DADO_ROWS - (lower - ceiling) // 256) % 256, "cstat": 0}


def _face(seen: str, beyond: str | None, a, b) -> dict:
    here, there = _part(seen)[0], _part(beyond)[0] if beyond else None
    if beyond is None:
        if here == "window":
            return {"picnum": SHUTTER if a[0] == b[0] == _q(WINDOW[2]) else CONCRETE}
        if here in ("north", "south", "bay", "beam", "tickets", "bench"):
            if seen == "bay_2" and a[0] == b[0] == _q(EAST):
                return {}                                  # split by the freight recess: painted in `build`
            return _dado(seen, a, b, FLOOR)
        return {}
    if there == "bench":
        return {"picnum": PLANK}
    if there in ("window", "lightbox") or here in ("yard", "avenue") or there in ("yard", "avenue"):
        # what is drawn over and under an opening, and the steps' risers
        return {"picnum": EDGE if there in ("yard", "avenue") or here in ("yard", "avenue") else CONCRETE}
    if there == "beam" or here == "beam":
        return {"picnum": CONCRETE}
    return {}


def build(layout, porches: dict[str, str], recess: str) -> dict:
    """Lay the passage between the two porches, and join the freight recess to it."""
    cells = plan()
    outline = {c.name: c.outer for c in cells}
    regions = A.lay(layout, KEY, cells, lambda name: _surface(name, outline[name]), _face)
    doors = {_q(YARD_FACE - PORCH): porches["yard"], _q(AVENUE_FACE + PORCH): porches["avenue"]}
    for name, a, b in A.rim(cells):
        if _part(name)[0] in ("yard", "avenue") and a[0] == b[0] and a[0] in doors:
            layout.add_connection(f"connection:underpass:{name}", doors[a[0]], regions[name], a1=b, a2=a, min_width=1, min_opening=0)
    layout.add_connection("connection:freight_recess", regions["bay_2"], recess, a1=(_q(EAST), _q(RECESS[0])),
                          a2=(_q(EAST), _q(RECESS[1])), min_width=1, min_opening=0)
    jamb = (_q(EAST), _q(RECESS[1])), (_q(EAST), _q(BEAMS[2]))
    layout.paint_wall(regions["bay_2"], *jamb, fixed_frame=True, **_dado("bay_2", *jamb, FLOOR))
    _light(layout, regions)
    _hang(layout, regions)
    _line(layout, regions)
    return regions


def shoot_out(layout) -> None:
    """Make the lit tubes answer a bullet, the mirror's with the passage's."""
    import wires
    from bloodmap import breakables
    placed = {p.placement_id: p for p in layout.placements}
    for cell, name in SHOT.items():
        breakables.smash(layout, placed[name], wires.wire(f"underpass:tube-{cell}"), breakables.TUBE_GLASS)


def bars() -> tuple[int, int, int, int]:
    """Where the iron bars stand: across the tunnel's mouth."""
    return _q(BARS) - 16, _q(MOUTH[0]) - 16, _q(BARS) + 16, _q(MOUTH[1]) + 16


#: one tube to a bay, down the passage's middle: (cell, x, y, lit)
TUBES = (("north", 44.0, 19.0, True), ("bay_1", 44.0, 21.875, True), ("bay_2", 44.0, 23.875, True),
         ("bay_3", 44.0, 25.875, False), ("bay_4", 44.0, 27.875, True), ("bay_5", 44.0, 29.875, True),
         ("south", 44.0, 32.0, False), ("tickets", 46.25, 28.5, False))
#: the one that is failing
LOOSE = "bay_5"
#: those that can be shot out, and what each is called: the light goes with it (`light_groups`)
SHOT = {"north": "underpass:tube_north", "bay_1": "underpass:tube_bay_1", "bay_2": "underpass:tube_bay_2",
        "bay_4": "underpass:tube_bay_4", "mirror": "loading:tube"}
#: the folding gate (1060, the lattice the owner hangs before his own ticket windows)
GATE = 1060


def _light(layout, regions) -> None:
    for cell, x, y, lit in TUBES:
        room = layout.regions[regions[cell]]
        layout.add_sprite(f"underpass:tube_{cell}", regions[cell], x=_q(x), y=_q(y), z=room.ceiling_z + 64,
                          picnum=TUBE if lit else DEAD_TUBE, x_repeat=64, y_repeat=64, angle=1536,
                          cstat=32 | 128 | 8, shade=-16 if lit else 8)
    import wallplane
    from bloodmap.placement import drawn_extent
    _w, height, _x, offset = wallplane.art()[BULB]
    top, _bottom = drawn_extent(height, offset, 32, 128)
    layout.add_sprite("underpass:bulb", regions["end"], x=_q(BED + 0.4), y=_q(sum(MOUTH) / 2), z=TUNNEL + 16 - top, picnum=BULB,
                      x_repeat=32, y_repeat=32, cstat=128, shade=-8)


def _hang(layout, regions) -> None:
    """The bills, the boards, and the little that stands on the floor."""
    import props
    import wallplane

    def bill(name, cell, a, b, tile, size, *, t=0.5, high=1.18, cstat=16 | 64 | 128, shade=6, **more):
        wallplane.sprite(layout, f"underpass:{name}", regions[cell], (_q(a[0]), _q(a[1])), (_q(b[0]), _q(b[1])), tile=tile,
                         x_repeat=size, y_repeat=size, cstat=cstat, t=t, height_player_heights=high,
                         offset_player_widths=0.04, shade=shade, required=True, **more)

    # the west wall: the same bill in the same place in every bay, but the last
    for k in range(1, len(BEAMS)):
        y0, y1 = BEAMS[k - 1] + BEAM_DEEP, BEAMS[k]
        tile, size, high = (931, 40, 1.06) if k == 5 else (981, 40, 1.18)
        bill(f"bill_{k}", f"bay_{k}", (WEST, y1), (WEST, y0), tile, size, high=high)
    bill("wrestling", "bay_1", (EAST, 21.0), (EAST, 22.75), 440, 44, t=0.5)
    bill("sloth", "south", (EAST, 31.0), (EAST, 33.0), 932, 48, t=0.5)
    # the canteen upstairs advertises by the stair that comes down from its yard, and nobody has found these
    wallplane.text(layout, "sign:underpass_ratdogs", regions["north"], (_q(43.0), _q(18.0)), (_q(45.0), _q(18.0)), words="RAT DOGS",
                   style="ratdogs", height_player_heights=1.25)
    # and which way (the owner: "there should be ... arrow under it pointing to the direction like rat dogs this way"): E1M4
    # points at its own with 1042. The stair up to the yard, and the stand over it, are to the right as one reads it.
    bill("ratdogs_arrow", "north", (43.0, 18.0), (45.0, 18.0), 1042, 120, t=0.5, high=0.82, shade=-8)
    wallplane.text(layout, "sign:underpass_missing", regions["bench"], (_q(BENCH[2]), _q(BENCH[3])), (_q(BENCH[0]), _q(BENCH[3])),
                   words="MISSING", style="label", height_player_heights=1.35)
    # what a traveller reads: the board across from the yard's stair, and the way out at each end
    bill("board", "north", (WEST, 20.75), (WEST, 18.0), 431, 72, t=0.63, high=1.15)
    bill("exit_yard", "north", (43.0, 18.0), (YARD_FOOT, 18.0), 761, 64, t=0.86, high=1.3, shade=-16)
    bill("exit_avenue", "south", (EAST, 33.0), (AVENUE_FOOT, 33.0), 761, 64, t=0.75, high=1.3, shade=-16)
    # the lit case at the end of the passage, seen from the other end of it
    layout.place_on_wall("underpass:case", regions["lightbox"], a1=(_q(44.5), _q(33.125)), a2=(_q(43.5), _q(33.125)), t=0.5,
                         height_player_heights=8704 / 16960, offset_player_widths=0.02, picnum=2047, x_repeat=32, y_repeat=32,
                         cstat=16 | 64 | 128, type=0, status=0, shade=-24)
    # the ticket hall: the shut window and its boards, a clock, four notices, the works board by the bars
    x0, y0, x1, y1 = TICKETS
    layout.place_on_wall("underpass:tickets", regions["tickets"], a1=(_q(x1), _q(WINDOW[1])), a2=(_q(x1), _q(WINDOW[3])), t=0.5,
                         height_player_heights=1.58, offset_player_widths=0.04, picnum=943, x_repeat=56, y_repeat=56,
                         cstat=16 | 64 | 128, type=0, status=0, shade=4, spans_opening=True)
    bill("prices", "tickets", (x1, WINDOW[3]), (x1, y1), 905, 36, t=0.5, high=1.1)
    bill("track_board", "tickets", (x1, MOUTH[1]), (x1, WINDOW[1]), 444, 48, t=0.5, high=1.2)
    bill("clock", "tickets", (x0, y0), (x1, y0), 1165, 40, t=0.3, high=1.35)
    bill("wanted", "tickets", (x0, y0), (x1, y0), 356, 40, t=0.66, high=1.15)
    for k, t in enumerate((0.3, 0.7)):
        bill(f"notice_{k}", "bench", (BENCH[2], y1), (BENCH[0], y1), 742, 48, t=t, high=0.95)
    # paper on the floor, where the light is
    for k, (cell, x, y, tile, angle) in enumerate((("bay_5", 43.5, 29.4, 1167, 300), ("bay_2", 43.4, 24.2, 743, 1100),
                                                   ("tickets", 46.9, 27.9, 1167, 1700))):
        layout.add_sprite(f"underpass:paper_{k}", regions[cell], x=_q(x), y=_q(y), z=FLOOR, picnum=tile, x_repeat=40,
                          y_repeat=40, angle=angle, cstat=32 | 128, shade=8)
    _rails(layout, regions)
    import ambience
    layout.add_sprite("underpass:hum", regions[LOOSE], x=_q(44.0), y=_q(29.875), z=FLOOR - 8192,
                      **ambience.fields("tubes"))


def _rails(layout, regions) -> None:
    """An iron rail down the middle of each flight (DWE2M10's 104), solid and seen from both sides."""
    for flight, (y0, y1) in (("yard", YARD_MOUTH), ("avenue", AVENUE_MOUTH)):
        for k in range(1, TREADS + 1):
            room = layout.regions[regions[f"{flight}_{k}"]]
            xs = [p[0] for p in room.outer]
            layout.add_sprite(f"underpass:rail_{flight}_{k}", regions[f"{flight}_{k}"], x=(min(xs) + max(xs)) // 2,
                              y=_q((y0 + y1) / 2), z=room.floor_z - 4096, picnum=104, x_repeat=24, y_repeat=32, angle=512,
                              cstat=16 | 128 | 1, shade=8)


def _line(layout, regions) -> None:
    """The pram under the bulb, and what leaving the ticket hall does to it.

    The plate it stands on is a sliding sector in the tunnel's bed and never
    leaves it. It is saved where it is drawn, at the far end; the first time
    the player walks out of the ticket hall the bulb goes out and it comes
    down to the bars, behind him.
    """
    import wallplane
    import wires
    from bloodmap import mechanism
    from bloodmap.motion import CMD_TOGGLE
    from bloodmap.placement import seated_z
    body = mechanism.rigid_body(layout, "underpass:pram", members=[regions["plate"]], host_region=regions["bed"],
                                travel=(_q(COMES), 0), lead=regions["plate"], busy_time=22, carry_host=False)
    _w, height, _x, offset = wallplane.art()[PRAM]
    layout.add_sprite("underpass:pram", regions["plate"], x=_q((PLATE[0] + PLATE[2]) / 2), y=_q((PLATE[1] + PLATE[3]) / 2),
                      z=seated_z(seat="floor", floor_z=FLOOR, ceiling_z=TUNNEL, tile_height=height, y_repeat=40, y_offset=offset,
                                 cstat=129, clearance=16),
                      picnum=PRAM, x_repeat=40, y_repeat=40, cstat=129, shade=-8)
    mechanism.carry_fittings(layout, [regions["plate"]])
    wire = wires.wire(WIRE)
    wire.when(wiring.region(regions["tickets"]), "exit", command=CMD_TOGGLE, once=True, dude_lockout=1)
    for region in body["receivers"]:
        wire.then(wiring.region(region), rx_id=wire.channel)


def light_groups(compiled) -> list:
    """The failing tube, and the bulb that goes out: the light goes with the lamp (`light_stage.LampGroup`)."""
    import wires
    from bloodmap.light_stage import LampGroup

    def lamps(*names):
        return frozenset(compiled.placement_sprites[f"underpass:{name}"] for name in names)

    def tunnel(region):
        return region.startswith(KEY) and region.rsplit(":", 1)[-1] in TUNNEL_CELLS

    def passage(region):
        return region.startswith(KEY) and not tunnel(region)

    return [LampGroup(f"the underpass's tube in {cell}", frozenset({compiled.placement_sprites[name]}), "on",
                      rx=wires.channel(f"underpass:tube-{cell}"), within=lambda region: "/works_stair/" in region and not tunnel(region))
            for cell, name in SHOT.items()] + [
            LampGroup("the underpass's failing tube", lamps(f"tube_{LOOSE}"), wave=8, frequency=4, within=passage),
            LampGroup("the bulb in the metro's tunnel", lamps("bulb"), "on", rx=wires.channel(WIRE), within=tunnel)]
