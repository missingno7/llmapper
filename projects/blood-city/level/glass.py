"""Shop windows: big, transparent, and breakable, the way E6M1 does it.

The owner asked for "bigger shop windows with breakable transparent glass"
and pointed at E6M1's shop.  That shop's front is four walls carrying an
XWALL, and reading them gives the recipe exactly:

    picnum 2293  over_picnum 266  cstat 0x00d5
    x_repeat 32  y_repeat 8  length 4096
    XWALL: trigger_vector = 1, data = 12

cstat 0xd5 decomposes to blocking(1) + align(4) + **masked(16)** +
hitscan-sensitive(64) + translucent(128).  The glass itself is the
`over_picnum`, drawn across the opening of a TWO-SIDED wall; the base
`picnum` is whatever the wall would otherwise be.

NBlood confirms the behaviour rather than us inferring it.  `actor.cpp`
case 4 -- a hitscan striking a masked wall -- reads
`surfType[wall.overpicnum]` and, if `pXWall->triggerVector` is set, calls
`trTriggerWall(..., kCmdWallImpact, ...)`.  `triggers.cpp` then clears
cstat bits 1, 64 and 16 on both sides of the pair: the glass stops
blocking, stops catching hitscans, and stops being drawn.  That is the
break, and it needs the XWALL -- glass without one is a permanent pane.

So a window here is declared as a span on a room's face, and this pass
turns the compiled wall pair into glass.  It runs after the facade pass,
because it must survive whatever that painted.
"""

from __future__ import annotations

#: E6M1's own glass tile, and the cstat that makes it breakable glass.
GLASS_TILE = 266
GLASS_CSTAT = 0x00d5          # blocking | align | masked | hitscan | translucent
GLASS_REPEATS = (32, 8)
#: The XWALL that lets a shot break it.  `data` copied from E6M1.
GLASS_XWALL = {"trigger_vector": 1, "data": 12}


def _fields(entry):
    return entry["fields"] if isinstance(entry, dict) else entry


def _attach_xwall(level, wall_id: int, **values) -> None:
    """Give one wall an XWALL, the way bloodmap.construction does.

    Without this the pane is permanent: NBlood's break path needs
    `wall.extra > 0` before it will even look at `triggerVector`, so glass
    with the right cstat but no XWALL is a wall you cannot shoot out.
    """
    from bloodmap.construction import _empty_fields
    from bloodmap.format import XWALL_SCHEMA
    item = level.walls[wall_id]
    if item.get("blood") is None:
        used = {int(w["fields"]["extra"]) for w in level.walls
                if int(w["fields"].get("extra", 0)) > 0}
        extra_id = 1
        while extra_id in used:
            extra_id += 1
        fields = _empty_fields(XWALL_SCHEMA)
        fields["reference"] = int(wall_id)
        item["fields"]["extra"] = extra_id
        item["blood"] = {"kind": "XWALL", "fields": fields,
                         "opaque_tail_hex": ""}
    item["blood"]["fields"].update(values)


def glaze(level, spans, *, tile: int = GLASS_TILE) -> dict:
    """Turn every wall lying inside one of `spans` into breakable glass.

    `spans` is a list of (x0, y0, x1, y1) world rectangles -- each the
    footprint of a shop window.  Both sides of the wall pair are glazed,
    which is what E6M1 does and what `trTriggerWall` expects when it
    clears the bits on `pWall2`.
    """
    report = {"panes": 0, "spans": len(spans), "skipped_solid": 0}
    for index in range(len(level.walls)):
        fields = _fields(level.walls[index])
        nxt = int(fields.get("next_sector", -1))
        after = _fields(level.walls[int(fields["point2"])])
        ax, ay = int(fields["x"]), int(fields["y"])
        bx, by = int(after["x"]), int(after["y"])
        mx, my = (ax + bx) / 2, (ay + by) / 2
        if not any(x0 <= mx <= x1 and y0 <= my <= y1
                   for x0, y0, x1, y1 in spans):
            continue
        if nxt < 0:
            # A window needs something to see through to.  A solid wall
            # inside the span is the shop's own pier, and stays a pier.
            report["skipped_solid"] += 1
            continue
        fields["over_picnum"] = int(tile)
        fields["cstat"] = GLASS_CSTAT
        fields["x_repeat"], fields["y_repeat"] = GLASS_REPEATS
        fields["y_panning"] = 0
        _attach_xwall(level, index, **GLASS_XWALL)
        report["panes"] += 1
    return report
