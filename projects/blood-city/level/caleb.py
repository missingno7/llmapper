"""Wire Caleb's three scripted remarks at their moments in Gravesend."""

from bloodmap import wiring
from bloodmap.mechanism import CMD_ON

import wires


def _line(layout, wire, region, sound_id, x, y):
    z = (region.ceiling_z + region.floor_z) // 2
    speaker = layout.add_sprite(wire.name, region.region_id, x=x, y=y, z=z,
                                type=711, picnum=2519, cstat=32896, status=0,
                                shade=-128, pal=5, x_repeat=64, y_repeat=64,
                                behavior={"data_1": sound_id})
    wire.then(wiring.placement(speaker))


def level_opening(layout):
    """Play E3M1's town line after its half-second level-start relay."""
    start = layout.player_start
    opening = wires.wire("caleb:opening")
    relay = layout.add_sprite("caleb:start-relay", start.region_id,
                              x=start.x, y=start.y, z=start.z - 512,
                              type=21, picnum=0, cstat=32896, status=0)
    opening.when(wiring.placement(relay), wiring.LEVEL_START, command=CMD_ON,
                 on=False, off=True, once=True, wait_time=5)
    _line(layout, opening, layout.regions[start.region_id], 4509, start.x, start.y)


def spider_mother(layout, region_id, mother, x, y):
    """Play E2M8's rhyme when the spider mother is killed."""
    quote = wires.wire("caleb:spider-mother")
    # The engine raises OFF on death. A decoupled sender also fires if an
    # unaware mother dies before its AI first turns the state on.
    quote.when(wiring.placement(mother), "killed", command=CMD_ON,
               on=False, off=True, once=True, decoupled=1)
    _line(layout, quote, layout.regions[region_id], 4537, x, y)


def ghost_tunnel(layout, tunnel):
    """Play E1M3's end-of-line remark on entry to the blocked tunnel."""
    region = layout.regions[tunnel.region_id]
    quote = wires.wire("caleb:ghost-tunnel")
    quote.when(wiring.region(tunnel.region_id), "enter", command=CMD_ON,
               once=True, dude_lockout=1)
    x = sum(point[0] for point in region.outer) // len(region.outer)
    y = sum(point[1] for point in region.outer) // len(region.outer)
    _line(layout, quote, region, 3034, x, y)
