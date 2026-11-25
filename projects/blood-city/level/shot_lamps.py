"""Lamps that can be shot out, and the light goes with each: the ones of glass, where a room is lit by them.

The owner, 2026-11-25: "maybe some things can be breakable, like lights on some more
places, but check how many TX channels we have left and what would make the most sense".

Channels are not what is short: 100 to 1,023 are a level's own, and the city used 76 of
them (the campaign's most is 145; with these, 95 of 924, 654 XSECTORs). What a lamp costs is an XSECTOR for every piece of
floor it lights (NBlood has 4,096; the city used 571), and one receiver to a sector: a
piece that two lamps light can answer only one of them, so lamps go where each has its
own pool.

Which: over 102 of Blood's maps 62 of 288 fluorescent panels (2290) break, 8 of 9 of the
long ones, 6 of 14 brass lamps, 5 of 148 brass lanterns (693; all five take their light
with them: E2M1 sprites 10, 43 and 53), a round glass lamp (676, E1M3 sprite 18). A lamp
post, a chain lamp, a torch, a candle: none, or two with nothing behind them. So the
panels, the lanterns and the globes: the hall of meat, the pawn shop, the arcade, the
station's offices and the signal box, the stalls, the den. Not where a lamp is somebody's
doing (the railway's, the rite's, the bulb over the pram), nor under water.

A lantern or a globe is a wire of its own, and falls to pieces. The panels of a room are
circuits, a row to one, as E1M2's are (sprites 630 to 633 all send and listen on 189):
shoot one and its row goes, each panel to its dark picture. (A hall of nine lamps whose
pools lie over one another, each piece of floor able to answer one, would be lit for ever
by what the other eight gave it.) `light_stage.LampGroup` says what goes with each.
"""

from __future__ import annotations

PU = 1024
PANEL, LANTERN, GLOBE = 2290, 693, 676
#: panels this module hangs, where the light stage hung its own (`lights.RULES` leaves these rooms to it): a name, a point, the floor
#: of the room there
PANELS = (*((f"market_{i}{j}", (x, y), 8192) for i, x in enumerate((7.665, 10.0, 12.333)) for j, y in enumerate((41.75, 44.25, 46.75))),
          ("pawn_0", (27.469, 4.75), 8192), ("pawn_1", (30.156, 4.75), 8192))
#: which panels go together
CIRCUITS = {"market_row_0": ("market_00", "market_10", "market_20"), "market_row_1": ("market_01", "market_11", "market_21"),
            "market_row_2": ("market_02", "market_12", "market_22"), "pawn": ("pawn_0", "pawn_1")}
#: everything of these two tiles is shot out, but what is somebody's doing or is under water
LEAVE = ("phantom", "ghost", "prop", "underwater", "boat_lantern", "newel_light", "clerk_lamp", "mortar", "buffer", "drowned",
         "front_lamp", "ship:", "fair:carousel")                              # the portico's light nothing that is walked on; the Demeter's is drawn by hand

#: too high to be a lamp one shoots at, or no more than a spark
LEAST_SIZE, MOST_UP = 30, 60000
#: what is shot: its name -> its lamps, its wire, the venue, and whether it is a circuit of panels
WIRED: dict[str, tuple[tuple[str, ...], str, str, bool]] = {}


def hang(layout) -> int:
    """The panels of the rooms this module lights."""
    from shapely import Point, Polygon
    done = 0
    for name, (x, y), floor in PANELS:
        at = Point(x * PU, y * PU)
        room = next(r for r in layout.regions.values() if int(r.floor_z) == floor and not r.parallax_ceiling
                    and r.role == "interior" and Polygon(r.outer, r.holes).contains(at))
        layout.add_sprite(f"lamp:{name}", room.region_id, x=round(x * PU), y=round(y * PU), z=int(room.ceiling_z) + 64, picnum=PANEL,
                          x_repeat=64, y_repeat=64, cstat=32 | 128, shade=-16, sunk=True)
        done += 1
    return done


def _place(region: str) -> str:
    """The venue a region is of: where the light of a lamp in it may be switched."""
    return region.rsplit(":", 1)[0] if region.count(":") > 1 else region.rsplit("/", 1)[0]


def declare(layout, first: int) -> dict[str, int]:
    """Make each of them answer a bullet; `first` is how many wires of that kind there are already."""
    import wires
    from dataclasses import replace
    from bloodmap import breakables, motion, wiring
    from bloodmap.breakables import HITSCAN, THING_STATUS
    WIRED.clear()
    report: dict[str, int] = {}
    light = "the sectors it lights (`light_stage.switch_lamps`)"
    placed = {p.placement_id: p for p in layout.placements}
    for name, panels in CIRCUITS.items():
        wire = wires.shot(first + len(WIRED), f"lamp:{name}").answered_by(light)
        for panel in panels:
            p = placed[f"lamp:{panel}"]
            p.type, p.cstat = 21, p.cstat | HITSCAN
            glass = f"{p.placement_id}:glass"
            layout.placements.append(replace(p, placement_id=glass, picnum=0, type=416, status=THING_STATUS,
                                             cstat=p.cstat & ~HITSCAN | 32768, behavior=dict(breakables.TUBE_GLASS)))
            wire.when(wiring.placement(p.placement_id), "vector", command=motion.CMD_ON, on=True, once=True, trigger_impact=1)
            wire.then(wiring.placement(p.placement_id))
            wire.then(wiring.placement(glass))
        WIRED[name] = (tuple(f"lamp:{panel}" for panel in panels), wire.name, _place(placed[f"lamp:{panels[0]}"].region_id), True)
        report[name] = wire.channel
    for p in placed.values():
        if p.picnum not in (LANTERN, GLOBE) or p.type or p.behavior or p.cstat & 32768:
            continue
        if (p.x_repeat < LEAST_SIZE or int(layout.regions[p.region_id].floor_z) - int(p.z) > MOST_UP
                or any(word in p.placement_id or word in p.region_id.rsplit("gravesend/", 1)[-1] for word in LEAVE)):
            continue
        wire = wires.shot(first + len(WIRED), p.placement_id).answered_by(light)
        record = dict(breakables.table()[p.picnum]["record"])
        record.pop("hitscan")
        p.type, p.status, p.cstat = record.pop("type"), THING_STATUS, p.cstat | HITSCAN
        p.behavior = record
        cause = "vector" if record.get("trigger_vector") else "destroyed"
        wire.when(wiring.placement(p.placement_id), cause, command=motion.CMD_ON, on=True, off=True, once=True)
        WIRED[p.placement_id] = ((p.placement_id,), wire.name, _place(p.region_id), False)
        report[p.placement_id] = wire.channel
    return report


def light_groups(compiled) -> list:
    """Each of them with the light it gives: authored lit, and put out by the ON it sends (E1M2 s114 under its tubes, E1M3 s81 under its globe)."""
    import wires
    from bloodmap.light_stage import LampGroup
    channels = {made.name: made.channel for made in wires.circuit().wires}
    return [LampGroup(f"the lamp {name}", frozenset(compiled.placement_sprites[lamp] for lamp in lamps), "out", rx=channels[wire],
                      within=lambda region, place=place: region.startswith(place))
            for name, (lamps, wire, place, _circuit) in WIRED.items()]
