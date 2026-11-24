"""How Gravesend is played: six keys in any order, the station they open, what each wakes, the guns, the supplies, who walks the streets.

The owner, 2026-11-24: "I would make this level the way that you will be
collecting keys around the city and will need all of them to unlock station to
get to the exit. So instead of linear order of keys you just pick all of them in
any order and then use them at the end. For example that cabal circle is good
place for key which can be obtained after defeating that gargoyle in that room
that gets revealed. Another key might be for example at Aldemarck", and before
it: "better weapons hidden in secret places".

Numbers are the study's (`knowledge/blood/studies/supplies/notes.md`): the
sawed-off before the first fight, two more guns by a quarter of the foes, one of
each big gun, the biggest in secrets; ammo in threes, along a wall, past the fight
it is for; health scarce and mostly carried (a foe in six); half the keys wake
something. The lock is DWE1M9's (sprites 1399 to 1407): a keyed switch for each
key, once, all into one combination switch that counts them.

Everything here is a row: move a thing by editing its row. `place` finds the
region under a point, and refuses one that is nowhere, in a wall, or on another thing.
"""

from __future__ import annotations

import math

from bloodmap import motion, wiring

import keysign
import wires

PU = 1024
#: placed by type: (tile, repeat)
ITEMS = {41: (559, 48), 42: (558, 48), 43: (524, 48), 45: (539, 48), 46: (526, 48), 50: (800, 48), 60: (618, 40), 62: (589, 48),
         63: (809, 48), 64: (811, 40), 65: (810, 40), 66: (820, 24), 67: (619, 48), 68: (812, 48), 69: (813, 48), 70: (525, 48),
         72: (817, 48), 73: (548, 24), 76: (816, 48), 79: (801, 48), 107: (519, 48), 108: (822, 40), 109: (2169, 40),
         110: (2433, 40), 113: (896, 40), 114: (825, 40), 117: (829, 40), 121: (760, 40), 124: (2428, 40), 140: (2628, 64),
         141: (2586, 64), 143: (2602, 64), 144: (2594, 64)}
#: foes: (tile, repeat, palette)
FOES = {201: (2820, 40, 3), 202: (2825, 40, 0), 203: (1170, 40, 0), 204: (1370, 48, 0), 205: (3054, 40, 0), 206: (1470, 40, 0),
        210: (3060, 40, 0), 211: (1270, 40, 0), 217: (1570, 48, 0), 248: (2820, 40, 13),
        212: (1980, 32, 0), 220: (1745, 24, 0)}
STREET, SEWER, HALL, STATION, RITE = 8192, 61440, 102400, -12288, 102400

#: --- the six keys --------------------------------------------------------------
#: name -> (key number, x, y, floor, what its taking lets loose: (type, x, y, and its floor if not the key's)); the two with no point lie where
#: their own module puts them (the arcade's, and the Aldermack's on the trap).
KEYS = {
    "skull": (1, 29.02, 28.25, 51200, ((205, 28.1, 26.9), (205, 30.9, 27.2), (205, 30.9, 29.4), (205, 28.2, 29.6), (205, 31.0, 28.3))),
    "eye": (2, None, None, None, ((202, 40.7, 48.7), (201, 42.4, 48.7), (202, 40.6, 44.1), (203, 45.0, 41.7, 32768))),
    "flame": (3, 43.75, 9.5, None, ((204, 46.9, 12.6), (203, 41.0, 12.2), (203, 40.6, 4.4))),
    "dagger": (4, 27.5, 66.35, 102400, ((210, 24.2, 57.2), (210, 30.8, 57.2), (203, 27.5, 53.2))),
    "spider": (5, 12.0, 10.2, 56832, ((213, 11.6, 11.75), (213, 12.6, 11.75), (214, 9.4, 13.6), (214, 14.9, 13.8), (213, 12.0, 16.2))),
    "moon": (6, None, None, None, ()),
}
KEY_SHADE = -40

#: --- the station's lock ---------------------------------------------------------
#: along the pier between the two arches: each key's placard, its switch under it
PIER = (35328, 37376)
PIER_Y = -3072
SWITCH_TILE = 1048
#: who waits behind the gates
GUARD = ((201, 33.2, -7.6), (202, 37.8, -7.6), (202, 35.5, -8.2), (248, 36.3, -11.5), (204, 35.5, -14.6), (201, 32.0, -15.4))
#: who comes when the signal box's lever raises the tunnel's gate: the level's last fight, out of the dark and up the platform
LAST = ((211, 31.5, -20.6, 2048), (211, 33.5, -19.2, 2048), (204, 35.5, -20.4, 2048), (248, 36.8, -18.8, 2048),
        (201, 10.5, -15.4, STATION), (202, 6.5, -15.2, STATION), (201, 24.0, -15.0, STATION), (204, 14.5, -13.4, STATION))
#: a train's whistle a long way off (the Phantom's own, sound 276), and the ground
LAST_WHISTLE = 276
#: Caleb, when the last key turns: "Looks like my train's come in."
OPENED_SAYS = 3031

#: --- what lies about ------------------------------------------------------------
#: (types, x, y, floor, why). Several types at one point are laid a hand apart, along the nearest wall
SUPPLIES = (
    # the quay: armed before the first fight (DWE1M1: the sawed-off with no foe within 23 m)
    ((41, 67, 67, 67), 36.0, 50.6, STREET, "by the dead man at the avenue's foot"),
    ((43, 76, 76), 26.0, 60.3, STREET, "the jetty's end: a look out over the water"),
    ((68,), 13.0, 52.4, STREET, "the quay's west end"),
    ((67, 67), 44.5, 52.4, STREET, "the quay's east end"),
    # the market hall
    ((140,), 12.2, 47.0, STREET, "armor, across the hall from its door"),
    ((69, 69, 69), 9.6, 42.2, STREET, "along the market's north aisle"),
    ((68,), 5.0, 47.2, STREET, "behind the stalls"),
    # the arcade: the tommy gun behind its own keyed door
    ((67, 67), 49.3, 46.2, STREET, "the arcade's landing"),
    ((42, 72), 51.4, 44.7, STREET, "the arcade's service passage, behind the eye's door"),
    ((141,), 51.5, 42.9, STREET, "the arcade's cache: a secret"),
    ((68, 69), 42.5, 49.0, STREET, "Miguel's Guns and Ammo, once its shutter is up"),
    # old crossing and the church
    ((67, 67, 67), 27.2, 31.2, None, "the nave"),
    ((64, 64), 30.9, 25.2, None, "the vestry"),
    ((69, 69, 69), 20.8, 30.2, STREET, "the churchyard wall"),
    # the gallows steps: three bodies over the crossroads
    ((69, 69, 69), 13.9, 31.0, -32768, "the terrace, behind the parapet"),
    ((124,), 4.4, 31.0, -32768, "the hangman's house"),
    ((107,), 6.6, 30.8, -32768, "the hangman's house"),
    # theatre row
    ((68,), 9.0, 12.2, STREET, "the saloon"),
    ((108,), 5.2, 10.4, STREET, "the saloon's corner"),
    ((72,), 13.8, 12.6, STREET, "the parlor"),
    ((67, 67), 29.6, 9.4, STREET, "the foyer"),
    ((69, 69, 69), 17.9, 7.2, STREET, "backstage"),
    ((67, 67, 67), 30.8, 12.9, STREET, "the square before the Aldermack"),
    # foundry ward
    ((69, 69, 69), 50.2, 19.4, STREET, "the yard"),
    ((60, 79), 42.0, 24.4, 24576, "the underpass, at the bars"),
    ((69, 69), 46.9, 8.0, STREET, "the machine hall"),
    ((62, 62), 41.0, 13.2, STREET, "the machine hall's far corner"),
    # the sewer
    ((107,), 46.6, 5.2, SEWER, "the silt trap, at the stair's foot"),
    ((67, 67, 67), 41.0, 7.75, SEWER, "the north channel"),
    ((69, 69, 69), 33.75, 26.2, SEWER, "the west leg"),
    ((67, 67), 44.0, 13.6, SEWER, "the junction"),
    ((79,), 55.8, 19.0, SEWER, "the east annex"),
    ((67, 67, 67), 18.0, 18.75, SEWER, "Graves Brook"),
    ((67, 67), 38.0, 33.8, SEWER, "the south channel"),
    ((72,), 33.75, 38.5, SEWER, "the outfall, before the hall"),
    ((70,), 37.2, 21.4, SEWER, "the stash: a secret"),
    ((46, 79), 45.2, 38.2, 63488, "the flooded room's far corner: a secret"),
    ((114,), 55.7, 46.2, 56320, "the Rat King's offering: a secret"),
    ((68, 67), 52.4, 40.6, 57344, "the bleeding floor's dock"),
    ((143,), 60.4, 58.6, 69632, "across the blood by the trolley"),
    # the settling hall: what the stone beast cannot shrug off, under the Cabal's skull and in line with the falls
    ((45, 73, 73, 73), 33.0, 49.35, HALL, "between the fires at the foot of the falls"),
    ((107,), 17.9, 44.0, HALL, "the Toshers' Den, by the stove"),
    ((67, 67, 67), 13.6, 45.6, HALL, "the Toshers' Den, along the beds"),
    ((110, 73, 73), 9.7, 45.6, 106496, "the Toshers' Cache: a secret"),
    # the station, behind its gates
    ((72,), 33.0, -15.6, STATION, "the concourse"),
    ((68,), 9.2, -13.2, STATION, "the booking hall"),
    ((107,), 20.8, -12.6, STATION, "the waiting room"),
    ((69, 69, 69), 39.2, -17.4, None, "the goods store"),
)

#: --- who walks the streets --------------------------------------------------------
#: (type, x, y, floor, angle, the skills it is not on: a bit a skill, from the easiest)
PATROL = (
    (202, 35.4, 36.0, STREET, 512, 0), (201, 37.6, 27.0, STREET, 512, 3), (202, 33.6, 14.0, STREET, 512, 0),
    (203, 24.0, 38.6, STREET, 0, 0), (203, 30.6, 38.4, STREET, 1024, 1),
    (202, 10.0, 37.4, STREET, 0, 0), (201, 16.6, 33.0, STREET, 512, 3),
    (202, 10.0, 17.0, STREET, 0, 0), (201, 24.0, 16.6, STREET, 0, 0), (211, 14.0, 2.2, STREET, 512, 3),
    (211, 44.0, 2.0, STREET, 512, 0), (202, 55.4, 24.0, STREET, 1536, 0), (203, 56.4, 34.0, STREET, 1536, 0),
    (248, 34.6, 1.8, STREET, 512, 3), (202, 36.8, 2.4, STREET, 512, 0),
    (205, 22.6, 28.0, STREET, 0, 0), (205, 24.8, 33.0, STREET, 512, 0), (205, 21.4, 24.6, STREET, 512, 1),
    (201, 14.1, 33.6, -32768, 0, 0), (202, 12.2, 34.1, -32768, 512, 0), (201, 12.0, 26.6, -32768, 0, 3), (203, 5.6, 33.4, -32768, 0, 0),
    (248, 11.0, 31.2, -32768, 0, 7),
    (203, 20.0, 51.2, STREET, 0, 0), (202, 47.0, 51.0, STREET, 1024, 0), (201, 55.8, 45.0, STREET, 1536, 3),
)
#: --- who is in the sewers (2026-11-25) -----------------------------------------
#: the rows are the streets' own; a rat needs less room than a man
SEWERS = (
    # the bleeding floor: the butcher at his carcasses, two of his men, rats at the stains; a beast below in the blood
    (204, 47.2, 43.2, SEWER, 0, 0), (203, 47.2, 40.5, SEWER, 1536, 0), (203, 52.4, 43.2, 57344, 1024, 3),
    (220, 48.6, 43.6, SEWER, 300, 0), (220, 50.9, 42.4, SEWER, 900, 0), (217, 49.75, 48.2, 63488, 1536, 0),
    # the sampling chamber: one in each pool, so the trolley is a ride and not a walk
    (217, 56.0, 56.5, 71680, 1024, 0), (217, 57.5, 60.2, 71680, 1024, 1),
    # the ring: what waits under the south channel, hands in the west leg, a beast in the east, the toshers' rats
    (205, 40.2, 33.0, 63488, 0, 0), (205, 45.8, 33.0, 63488, 1024, 1), (212, 33.0, 22.0, 63488, 1536, 0), (212, 33.0, 24.4, 63488, 512, 3),
    (217, 52.0, 26.0, 63488, 1536, 0), (220, 45.0, 33.75, SEWER, 1024, 0),
    # the brook, and the Cabal's picket where the outfall goes down to the hall
    (220, 9.0, 18.75, SEWER, 0, 0), (203, 21.5, 19.5, 63488, 1024, 0),
    (202, 33.0, 38.4, 63488, 1536, 0), (201, 33.0, 40.2, 63488, 1536, 3),
)
#: (wire, the supply whose taking sends on it: its type and where it lies, what comes: (type, x, y, floor))
WAKES = (("sewer:stockyard-armor", 143, 60.4, ((217, 58.6, 56.5, 71680), (217, 58.6, 60.2, 71680))),)
#: a foe in six carries a life essence (the study: 75% of Blood's health is carried)
CARRIES_EVERY, CARRIES = 6, 109


class GameplayError(ValueError):
    """A row that cannot be placed."""


def _region(layout, x, y, floor):
    from shapely import Point, Polygon
    point = Point(x, y)
    found = []
    for region in layout.regions.values():
        xs, ys = [p[0] for p in region.outer], [p[1] for p in region.outer]
        if not (min(xs) <= x <= max(xs) and min(ys) <= y <= max(ys)):
            continue
        shape = Polygon(region.outer, region.holes)
        if shape.contains(point) and region.floor_z - region.ceiling_z > 8192:
            found.append((abs(region.floor_z - floor) if floor is not None else 0, region.region_id, region, shape))
    return min(found, key=lambda row: row[:2])[2:] if found else None


def _clear(layout, shape, x, y, floor, room_for) -> bool:
    from shapely import Point
    if shape.exterior.distance(Point(x, y)) < room_for or any(h.distance(Point(x, y)) < room_for for h in shape.interiors):
        return False
    return all(math.hypot(p.x - x, p.y - y) >= 220 or abs(p.z - floor) > 20000 or p.status not in (0, 3, 4, 6)
               for p in layout.placements)


def spot(layout, x, y, floor, *, room_for=200, within=2600):
    """The nearest point to (x, y), in plan units, where a thing can lie: its region, and where."""
    x, y = x * PU, y * PU
    for ring in range(0, within, 160):
        steps = max(1, ring // 50)
        for k in range(steps):
            turn = 2 * math.pi * k / steps
            px, py = round(x + ring * math.cos(turn)), round(y + ring * math.sin(turn))
            hit = _region(layout, px, py, floor)
            if hit is None:
                continue
            region, shape = hit
            if floor is not None and abs(region.floor_z - floor) > 12288:
                continue
            if region.floor_slope is not None or region.role == "doorway":
                continue
            if _clear(layout, shape, px, py, region.floor_z, room_for):
                return region, px, py
    _REFUSED.append(f"nowhere to put a thing near ({x / PU}, {y / PU}) at {floor}")
    region = next(iter(layout.regions.values()))
    return region, *region.outer[0]


def _seat(layout, name, region, x, y, tile, size, **fields):
    import wallplane
    from bloodmap.placement import seated_z
    _w, height, _x, offset = wallplane.art()[tile]
    cstat = fields.pop("cstat", 128)
    z = seated_z(seat="floor", floor_z=region.floor_z, ceiling_z=region.ceiling_z, tile_height=height, y_repeat=size,
                 y_offset=offset, cstat=cstat, clearance=16)
    return layout.add_sprite(name, region.region_id, x=x, y=y, z=z, picnum=tile, x_repeat=size, y_repeat=size, cstat=cstat,
                             **{"shade": -8, **fields})


def _spawn(layout, name, what, x, y, floor, **behavior):
    """A marker that puts a foe there when its wire fires (type 18)."""
    region, px, py = spot(layout, x, y, floor, room_for=420)
    return layout.add_sprite(name, region.region_id, x=px, y=py, z=region.floor_z - 4096, type=18, picnum=2077, shade=-128,
                             cstat=32896, status=0, behavior={"data_1": what, "trigger_once": 1, **behavior})


def place(layout) -> dict:
    """Everything above, set down. The keys and what they wake first, then the lock, the supplies and the patrols."""
    _REFUSED.clear()
    report = {"keys": _keys(layout), "lock": _lock(layout), "last": _last_fight(layout), "supplies": _supplies(layout)}
    report["patrol"] = _patrol(layout) + _patrol(layout, SEWERS, "sewer")
    report["wakes"] = _wakes(layout)
    report["carried"] = _carried(layout)
    if _REFUSED:
        raise GameplayError("; ".join(_REFUSED))
    return report


#: every row that could be placed nowhere, so that all of them are said at once
_REFUSED: list[str] = []


#: placements the keys are laid as by the modules that own their rooms
OWN = {"eye": "key:arcade_eye", "moon": "aldermack:moon_key"}


def _keys(layout) -> int:
    for name, (number, x, y, floor, wakes) in KEYS.items():
        _sign, kind, tile, _n = keysign.KEYS[number]
        if x is None:
            placement = OWN[name]
            if not any(p.placement_id == placement for p in layout.placements):
                raise GameplayError(f"the {name} key is not where its module lays it")
        else:
            hit = _region(layout, x * PU, y * PU, floor)
            if hit is None:
                raise GameplayError(f"the {name} key lies nowhere")
            placement = _seat(layout, f"key:{name}", hit[0], round(x * PU), round(y * PU), tile, 32, type=kind, status=3,
                              shade=KEY_SHADE)
        if not wakes:
            continue
        taken = wires.wire(f"key:{name}")
        taken.when(wiring.placement(placement), "pickup", command=motion.CMD_ON, once=True)
        near = floor if floor is not None else _floor_of(layout, placement)
        for k, (what, sx, sy, *own) in enumerate(wakes):
            # the dagger is taken behind the rose; what it wakes stands between it and the way out
            level_ = (118784, 118784, 102400)[k] if name == "dagger" else own[0] if own else near
            taken.then(wiring.placement(_spawn(layout, f"gameplay:{name}_{k}", what, sx, sy, level_)))
    return len(KEYS)


def _floor_of(layout, placement) -> int:
    row = next(p for p in layout.placements if p.placement_id == placement)
    return layout.regions[row.region_id].floor_z


def _lock(layout) -> int:
    """Six keyed switches on the pier between the station's arches, and the count that opens every gate."""
    from bloodmap.switches import pressed_switch
    turned, opened = wires.wire("station:keys"), wires.wire("station:unlock")
    step = (PIER[1] - PIER[0]) / 6
    courts = {}
    for region in layout.regions.values():
        if "station_forecourt_" in region.region_id and "pool" not in region.region_id:
            xs = [p[0] for p in region.outer]
            courts[min(xs), max(xs)] = region.region_id
    for k, name in enumerate(KEYS):
        number = KEYS[name][0]
        tile, _kind, _item, _n = keysign.KEYS[number]
        x = round(PIER[0] + step * (k + 0.5))
        court = next(r for (a, b), r in courts.items() if a < x < b)
        a, b = (x - 150, PIER_Y), (x + 150, PIER_Y)
        layout.place_on_wall(f"keysign:station_{name}", court, a1=a, a2=b, t=0.5, height_player_heights=1.18,
                             offset_player_widths=0.06, type=0, picnum=tile, cstat=keysign.PLACARD_CSTAT, shade=-8,
                             x_repeat=20, y_repeat=20, status=0)
        spec = dict(pressed_switch(tile=SWITCH_TILE, tx_id=0, command=motion.CMD_ON))
        spec["behavior"] = {"data_1": 206, "dude_lockout": 1}
        spec.pop("height_player_heights", None)
        spec.update(x_repeat=34, y_repeat=34)
        switch = layout.place_on_wall(f"station:key_{name}", court, a1=a, a2=b, t=0.5, height_player_heights=0.74,
                                      offset_player_widths=0.06, status=0, **spec)
        turned.when(wiring.placement(switch), "push", command=motion.CMD_ON, on=True, off=True, once=True, key=number)
    court = next(iter(courts.values()))
    hall = next(r for r in layout.regions if r.endswith("gravesend_station/east_hall"))
    room = layout.regions[hall]
    tally = layout.add_sprite("station:key_count", hall, x=33200, y=-5000, z=room.floor_z - 4096, type=22, picnum=0, shade=-128,
                              cstat=32896, status=0, behavior={"data_2": len(KEYS)})
    turned.then(wiring.placement(tally))
    opened.when(wiring.placement(tally), wiring.RELAY, command=motion.CMD_ON, once=True)
    for name, x, kind, data in (("says", 33400, 711, {"data_1": OPENED_SAYS}), ("quake", 33600, 19, {"data_1": 700})):
        opened.then(wiring.placement(layout.add_sprite(
            f"station:opened_{name}", hall, x=x, y=-5000, z=room.floor_z - 4096, type=kind, picnum=2519 if kind == 711 else 2072,
            shade=-128, cstat=32896, status=0, behavior=data)))
    for k, (what, x, y) in enumerate(GUARD):
        opened.then(wiring.placement(_spawn(layout, f"gameplay:guard_{k}", what, x, y, STREET if y > -9 else STATION)))
    return len(KEYS)


def _last_fight(layout) -> int:
    """The lever in the signal box: the gate rises, something whistles down the line, and they come."""
    raised = wires.wire("station:gate")
    for k, (what, x, y, floor) in enumerate(LAST):
        raised.then(wiring.placement(_spawn(layout, f"gameplay:last_{k}", what, x, y, floor)))
    region, px, py = spot(layout, 29.0, -20.0, 2048, room_for=420)
    raised.then(wiring.placement(layout.add_sprite(
        "gameplay:last_whistle", region.region_id, x=px, y=py, z=region.floor_z - 8192, type=708, picnum=2521, shade=-128,
        cstat=32896, status=0, behavior={"data_2": LAST_WHISTLE})))
    raised.then(wiring.placement(layout.add_sprite(
        "gameplay:last_quake", region.region_id, x=px + 128, y=py, z=region.floor_z - 8192, type=19, picnum=2072, shade=-128,
        cstat=32896, status=0, behavior={"data_1": 800, "trigger_once": 1})))
    return len(LAST)


def _supplies(layout) -> int:
    count = 0
    for row, (types, x, y, floor, _why) in enumerate(SUPPLIES):
        for k, what in enumerate(types):
            tile, size = ITEMS[what]
            region, px, py = spot(layout, x + 0.3 * (k - (len(types) - 1) / 2), y, floor,
                                  room_for=280 if 40 <= what <= 50 else 200)
            _seat(layout, f"gameplay:supply_{row}_{k}", region, px, py, tile, size, type=what, status=3)
            count += 1
        if types[0] == 41:
            # the dead man the gun fell from (DW: 23% of weapons lie by a corpse)
            region, px, py = spot(layout, x + 0.75, y - 0.45, floor)
            _seat(layout, f"gameplay:dead_{row}", region, px, py, 2333, 44, shade=0)
    return count


def _wakes(layout) -> int:
    """What comes when a supply is taken, beyond the keys."""
    for name, what, x, comes in WAKES:
        row = next(k for k, r in enumerate(SUPPLIES) if r[0] == (what,) and r[1] == x)
        taken = wires.wire(name)
        taken.when(wiring.placement(f"gameplay:supply_{row}_0"), "pickup", command=motion.CMD_ON, once=True)
        for k, (foe, fx, fy, floor) in enumerate(comes):
            taken.then(wiring.placement(_spawn(layout, f"gameplay:{name}_{k}", foe, fx, fy, floor)))
    return len(WAKES)


def _patrol(layout, rows=PATROL, named="patrol") -> int:
    for k, (what, x, y, floor, angle, not_on) in enumerate(rows):
        tile, size, pal = FOES[what]
        region, px, py = spot(layout, x, y, floor, room_for=180 if what in (212, 220) else 420)
        _seat(layout, f"gameplay:{named}_{k}", region, px, py, tile, size, cstat=384, type=what, status=6, pal=pal,
              angle=angle, behavior={"launch_skill": not_on} if not_on else {})
    return len(rows)


def _carried(layout) -> int:
    """A life essence on every sixth cultist or zombie that has nothing to carry."""
    count = 0
    for k, p in enumerate(p for p in layout.placements if p.type in (201, 202, 203, 248)):
        if k % CARRIES_EVERY == 0 and not p.behavior.get("drop_item"):
            p.behavior["drop_item"] = CARRIES
            count += 1
    return count
