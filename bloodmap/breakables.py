"""Which things break, as Blood's own maps have them, and the two ways a thing is made to.

A thing that breaks is a kThingObjectGib or kThingObjectExplode on the thing
list: damage reaches only dudes and things (actor.cpp actRadiusDamage), and a
bullet only what stops a bullet (cstat 256). Its data says what it breaks into and
the sound of it. Which tiles break, and by what record, is mined from the campaign
(`tools.mine_breakables`): 254 of its 271 iron-hooped barrels do.

A clock or a mirror does not fall to pieces: it is a one-way switch that answers a
bullet, and a switch shows its next picture when its state changes (view.cpp:2735),
so 1165 becomes the smashed clock 1166 and 710 the broken mirror 711. It fires an
unseen gib object where it hangs, which throws the glass and makes the noise (E1M1
sprites 505 and 506, E2M4's 275 and 879).
"""

from __future__ import annotations

import json
from dataclasses import replace
from functools import lru_cache
from pathlib import Path
from typing import Any

DATA = Path(__file__).resolve().parents[1] / "knowledge" / "blood" / "design" / "breakables-v1.json"
#: what a placed sprite breaks as; what answers a bullet with its next picture; a breakable's own fields
KINDS, SHOT_KINDS = frozenset({416, 417}), frozenset({20, 21})
RECORD = ("data_1", "data_2", "data_3", "data_4", "trigger_vector")
THING_STATUS, HITSCAN = 4, 256
#: a face that smashes: tile -> its gib object's record (E1M1 sprite 506, E2M4 sprite 879)
FACES: dict[int, dict[str, int]] = {1165: {"data_1": 2, "data_2": 6, "data_4": 301}, 710: {"data_1": 1, "data_4": 301}}
#: a fluorescent tube (2290, then dark 2291), which is shot out the same way and takes its light with it if its wire is
#: given to the light (`light_stage.LampGroup`): E1M1 sprites 132 and 328, and sector 80. 39 of the campaign's 288 are.
TUBE_GLASS = {"data_1": 13, "data_2": 7, "data_4": 300}


@lru_cache(maxsize=1)
def table() -> dict[int, dict[str, Any]]:
    """Every mined tile's row."""
    return {int(tile): row for tile, row in json.loads(DATA.read_text("utf-8"))["tiles"].items()}


def breaks(tile: int, *, share: float = 0.3, least: int = 2) -> dict[str, int] | None:
    """The record this tile breaks by, if Blood breaks at least this share of them."""
    row = table().get(int(tile))
    if row is None or row["breaks"] < least or row["breaks"] < share * row["seen"]:
        return None
    return dict(row["record"])


def apply(placements, *, leave=frozenset(), share: float = 0.3) -> dict[int, int]:
    """Make each plain placement whose tile breaks in Blood break as Blood's does; returns how many, by tile.

    Left as they are: a thing with a type or a behaviour of its own, a thing
    unseen, a solid flat sprite (it may be stood on) and the tiles in `leave`.
    """
    done: dict[int, int] = {}
    for p in placements:
        if p.type or p.behavior or p.cstat & 32768 or p.picnum in leave or (p.cstat & 48) == 32 and p.cstat & 1:
            continue
        record = breaks(p.picnum, share=share)
        if record is None:
            continue
        p.type, p.status = record.pop("type"), THING_STATUS
        if record.pop("hitscan"):
            p.cstat |= HITSCAN
        p.behavior = record
        done[p.picnum] = done.get(p.picnum, 0) + 1
    return done


def smash(layout, placement, wire, glass_record: dict[str, int] | None = None) -> str:
    """Make a clock, a mirror or a tube smash when it is shot: it changes its picture, once, and throws glass."""
    from . import wiring
    placement.type, placement.cstat = 21, placement.cstat | HITSCAN
    glass = f"{placement.placement_id}:glass"
    layout.placements.append(replace(placement, placement_id=glass, picnum=0, type=416, status=THING_STATUS,
                                     cstat=placement.cstat & ~HITSCAN | 32768, behavior=dict(glass_record or FACES[placement.picnum])))
    wire.when(wiring.placement(placement.placement_id), "vector", on=True, off=True, once=True, trigger_impact=1)
    wire.then(wiring.placement(glass))
    return glass
