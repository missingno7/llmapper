"""A horizontal surface is a plane too, and things stand on it.

`wallplane.py` made a wall a 2D surface that refuses to carry two things in
the same place. This is its horizontal counterpart, and the scale below the
fixture: `fixtures.py` builds the counter, `templates.py` composes counters
into a bar, and this puts the candles on the counter.

That completes the chain the whole approach is aiming at:

    bar -> counter run -> counter fixture -> candle row -> candles

**What the corpus actually does, and it is not what "glasses on the bar"
suggests.** `tools/mine_surface_items.py` finds every sprite standing inside
a raised sector's footprint at about its floor, over ten maps:

* **56 of 1,198 surfaces carry anything at all -- 4.7%.** The fixture is the
  detail, the same answer `mine_fixtures` gave for goods.
* The item is **tile 2101**, a candle: 27 of the corpus's 78 surface items,
  and 301 uses across 45 maps overall. E1M5 stands 16 of them, one per
  surface; E1M4's carnival booths carry up to **6**.
* Spacing between neighbours has a median around **400 units** across the
  maps that have more than one (384, 448, 672, 448, 256, 384).
* They are **face sprites** where they are decorative (2101, shade -128, so
  a candle is also a light) and floor-aligned where they are flat.

So `CARRY_SHARE` is 0.047 and the counts are 1 to 6. A row put on every
counter in the city would be four times the campaign's rate and would say
something about Gravesend that is not true.

Items land as `native_detail` declarations **on the host room**, not on the
compiled layout: a candle is part of the counter it stands on, so it belongs
in the tree where `citytree.zoom` can find it and an agent can change it
without reading the level.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass

from bloodmap.levelprog import native_detail

PLAYER = 16960

#: The share of surfaces the campaign puts anything on at all.
CARRY_SHARE = 0.047
#: How many, when it does: 1 is the corpus's median and 6 is E1M4's most.
COUNTS = (1, 1, 1, 2, 2, 3, 4, 6)
#: Median gap between neighbours on one surface, in map units.
GAP = 400
#: How far a run keeps clear of its surface's own ends, as a fraction.
END_INSET = 0.12


@dataclass(frozen=True)
class Item:
    """One thing that stands on a surface, and where it is attested."""
    name: str
    tile: int
    x_repeat: int = 64
    y_repeat: int = 64
    cstat: int = 128
    shade: int = -8
    #: How far above the surface the sprite's own z sits, in player heights.
    height: float = 0.0
    #: Drawn footprint in map units, for the occupancy test.
    width: int = 416
    source: str = ""

    def fields(self) -> dict:
        return {"cstat": int(self.cstat), "shade": int(self.shade),
                "status": 0}


#: The corpus's surface item, and a light: cstat 128, shade -128, 26x37
#: pixels drawn at repeat 64 -- 416 map units across.
CANDLE = Item(
    "candle", 2101, 64, 64, 128, -128, height=0.0, width=416,
    source=("27 of the corpus's 78 surface items -- E1M5 x16, E1M4 x6, "
            "E2M1 x3, E3M1, E3M2; 301 uses across 45 maps"))

#: The other two small standers, both attested on surfaces.
BOTTLE = Item(
    "bottle", 693, 48, 48, 128, 0, height=0.0, width=192,
    source="DWE3M1 x2 on surfaces; 140 uses across 17 maps")
LANTERN = Item(
    "lantern", 584, 64, 64, 128, -128, height=0.0, width=416,
    source="E1M4 and E1M1 on surfaces; 39 uses across 14 maps")

ITEMS = {item.name: item for item in (CANDLE, BOTTLE, LANTERN)}


class SurfaceError(ValueError):
    """A surface that will not carry what it was asked to."""


def _roll(seed: str, n: int) -> int:
    digest = hashlib.sha256(seed.encode("utf-8")).digest()
    return int.from_bytes(digest[:4], "big") % max(1, n)


def carries(host, seed: str = "") -> bool:
    """Whether this surface carries anything, at the campaign's own rate.

    Deterministic in the room's own path, so the same counter rebuilds
    identically and two counters differ.
    """
    key = f"{seed or host.path()}:carries"
    return _roll(key, 1000) < int(CARRY_SHARE * 1000)


def count_for(host, seed: str = "") -> int:
    key = f"{seed or host.path()}:count"
    return COUNTS[_roll(key, len(COUNTS))]


def cost(count: int, item: Item = CANDLE) -> dict:
    """Declared before anything is emitted. Items are sprites, not walls."""
    return {"item": item.name, "sprites": int(count), "walls": 0,
            "source": item.source}


def _rect_of(host):
    import props
    return props.room_rect(host)


def row(host, name: str, *, item: Item = CANDLE, count: int | None = None,
        gap: int = GAP, axis: str | None = None, across: float = 0.5,
        seed: str = "") -> list:
    """Stand `count` items along this surface's long axis.

    The host is the *fixture room* -- a counter module, a pedestal -- so its
    floor is the surface. Items are spaced at the mined gap, centred, and
    kept `END_INSET` clear of the ends; a surface too short for the whole
    row carries fewer rather than overhanging.

    Returns the `DetailDecl`s it attached, so a caller can count them; they
    are already on the room.
    """
    x0, y0, x1, y1 = _rect_of(host)
    width, depth = x1 - x0, y1 - y0
    if width <= 0 or depth <= 0:
        raise SurfaceError(f"{name}: {host.node_id} has no surface")
    horizontal = (width >= depth) if axis is None else (axis == "x")
    run = width if horizontal else depth
    usable = run * (1.0 - 2 * END_INSET)
    if count is None:
        count = count_for(host, seed)
    # A surface only carries what fits at the mined spacing OR at the item's
    # own width, whichever is larger.  Counting on the gap alone put four
    # 416-wide candles on 1,556 units of usable counter and then rejected
    # two of them for overlapping -- an honest result reached the expensive
    # way, and a count that lied about what would appear.
    pitch = max(1, gap, item.width)
    fits = max(1, int(usable // pitch) + 1)
    count = max(0, min(int(count), fits))
    if not count:
        return []

    taken: list[tuple[float, float]] = []
    placed = []
    span = item.width / max(1.0, run)
    for index in range(count):
        centre = (END_INSET + (1.0 - 2 * END_INSET)
                  * ((index + 0.5) / count))
        lo, hi = centre - span / 2, centre + span / 2
        # The same rule as a wall: a surface refuses two things in one place.
        if any(lo < b and a < hi for a, b in taken):
            continue
        taken.append((lo, hi))
        local = (centre, across) if horizontal else (across, centre)
        detail = native_detail(
            f"{name}_{index}", item.tile,
            x_repeat=item.x_repeat, y_repeat=item.y_repeat,
            local=local, **item.fields())
        host.decorate(detail)
        placed.append(detail)
    return placed


def dress_run(run_node, name: str, *, item: Item = CANDLE,
              every: bool = False, seed: str = "") -> dict:
    """Put a row on the modules of a fixture run that carry one.

    `every=True` is the deliberate case -- a bar's own counter, where the
    author is saying this one is dressed. Left alone it asks `carries`, and
    most modules answer no, which is the campaign's rate rather than ours.
    """
    report = {"modules": 0, "dressed": 0, "items": 0, "item": item.name}
    for index, module in enumerate(run_node.children):
        report["modules"] += 1
        if not every and not carries(module, seed):
            continue
        got = row(module, f"{name}_{index}", item=item, seed=seed)
        if got:
            report["dressed"] += 1
            report["items"] += len(got)
    return report
