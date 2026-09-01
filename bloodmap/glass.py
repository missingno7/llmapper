"""Breakable glass: a masked two-sided wall you can shoot out.

Promoted out of `projects/blood-city/level/glass.py`, which read the recipe
off E6M1's shopfront and has been glazing Gravesend for several phases. It is
here now because a constructor that only one project can call is not a
promotion, and because the zoo's conformance rule says a public constructor
owes an exhibit -- which this had no way to have while it lived in a level.

**The recipe, from E6M1's own shop front**, four walls carrying an XWALL:

```text
picnum 2293   over_picnum 266   cstat 0x00d5
x_repeat 32   y_repeat 8        length 4096
XWALL: trigger_vector = 1, data = 12
```

`0xd5` is blocking(1) + align(4) + **masked(16)** + hitscan-sensitive(64) +
translucent(128). The glass is the `over_picnum` -- the masked overlay of a
TWO-SIDED wall -- and the base picnum stays whatever the wall would otherwise
be. That is the same law the mask rule states from the other side: a cut-out
belongs on an overlay, where there is something behind it.

**The break is the engine's, not ours.** `actor.cpp` case 4 -- a hitscan
striking a masked wall -- reads `surfType[wall.overpicnum]` and, if
`pXWall->triggerVector` is set, calls `trTriggerWall(..., kCmdWallImpact)`.
`triggers.cpp` then clears cstat bits 1, 64 and 16 on BOTH sides of the pair:
the glass stops blocking, stops catching hitscans, and stops being drawn.

So `kWallGib` is the one mechanism in Blood that REOPENS a blocked wall, which
`bloodmap.conditional` already reads. Everything else in the engine closes
things.

**The holder is a mediation, not decoration.** A pane needs two sectors and a
reason: the shop behind it and the street in front, so there is something to
be transparent TO. A span glazed on a one-sided wall is a pier, not a window,
and is left alone -- which is why `glaze` reports `skipped_solid` rather than
quietly doing nothing.

Glass without an XWALL is a permanent pane: NBlood needs `wall.extra > 0`
before it will even look at `triggerVector`. `pane_faults` is the check for
that, and it is the failure mode nothing else can see -- every field is
individually legal and the window simply never breaks.
"""

from __future__ import annotations

from typing import Any, Iterable, Sequence

#: E6M1's own glass tile, and the cstat that makes it breakable glass.
GLASS_TILE = 266
GLASS_CSTAT = 0x00D5      # blocking | align | masked | hitscan | translucent
GLASS_REPEATS = (32, 8)
#: The XWALL that lets a shot break it. `data` copied from E6M1.
GLASS_XWALL = {"trigger_vector": 1, "data": 12}

#: The bits `trTriggerWall` clears on both sides when the pane breaks.
BREAK_CLEARS = 1 | 16 | 64


class GlassError(ValueError):
    """A pane that cannot be built where it was asked for."""


def _fields(entry: Any) -> Any:
    return entry["fields"] if isinstance(entry, dict) else entry


def holder(region_a: str, region_b: str, span: Sequence[int]) -> dict[str, Any]:
    """The pane's HOLDER, declared as a mediation rather than assumed.

    A window is not a property of a wall; it is a relationship between two
    rooms that a wall happens to carry. Naming the two sides makes the
    construct's members explicit -- and makes it checkable that a pane has
    something to be transparent to, which is the difference between a shop
    window and a translucent pier.
    """
    if region_a == region_b:
        raise GlassError(
            f"a pane needs two sides; {region_a!r} cannot hold one alone")
    return {
        "kind": "glass pane", "role": "holder",
        "inside": region_a, "outside": region_b,
        "span": tuple(int(v) for v in span),
        "why": ("E6M1 glazes a two-sided wall between the shop and the "
                "street; the overlay is only see-through because there is a "
                "room behind it"),
    }


def attach_xwall(level: Any, wall_id: int, **values: int) -> None:
    """Give one wall an XWALL, the way `bloodmap.construction` does."""
    from .construction import _empty_fields
    from .format import XWALL_SCHEMA

    item = level.walls[wall_id]
    if item.get("blood") is None:
        used = {int(w["fields"]["extra"]) for w in level.walls
                if int(w["fields"].get("extra", 0)) > 0}
        extra_id = 1
        while extra_id in used:
            extra_id += 1
        fields = _empty_fields(XWALL_SCHEMA)
        fields["reference"] = int(wall_id)
        #: `kind` and `opaque_tail_hex` are not optional: `model._dict_to_extra`
        #: reads both by name when the IR becomes a DiskMap, and a record
        #: without them fails at write time rather than at build time.
        item["blood"] = {"kind": "XWALL", "fields": fields,
                         "opaque_tail_hex": ""}
        item["fields"]["extra"] = extra_id
    item["blood"]["fields"].update({k: int(v) for k, v in values.items()})


def glaze(level: Any, spans: Iterable[Sequence[int]], *,
          tile: int = GLASS_TILE, cstat: int = GLASS_CSTAT,
          repeats: Sequence[int] = GLASS_REPEATS,
          xwall: dict[str, int] | None = None) -> dict[str, Any]:
    """Turn every two-sided wall inside one of `spans` into breakable glass.

    Both sides of the pair are glazed, which is what E6M1 does and what
    `trTriggerWall` expects when it clears the bits on `pWall2`.
    """
    spans = [tuple(int(v) for v in span) for span in spans]
    report = {"panes": 0, "spans": len(spans), "skipped_solid": 0,
              "walls": []}
    fields_of = _fields
    for index in range(len(level.walls)):
        fields = fields_of(level.walls[index])
        neighbour = int(fields.get("next_sector", -1))
        after = fields_of(level.walls[int(fields["point2"])])
        mx = (int(fields["x"]) + int(after["x"])) / 2.0
        my = (int(fields["y"]) + int(after["y"])) / 2.0
        if not any(x0 <= mx <= x1 and y0 <= my <= y1
                   for x0, y0, x1, y1 in spans):
            continue
        if neighbour < 0:
            #: A window needs something to see through to. A solid wall
            #: inside the span is the shop's own pier and stays a pier.
            report["skipped_solid"] += 1
            continue
        fields["over_picnum"] = int(tile)
        fields["cstat"] = int(fields["cstat"]) | int(cstat)
        fields["x_repeat"], fields["y_repeat"] = (int(repeats[0]),
                                                  int(repeats[1]))
        attach_xwall(level, index, **(xwall or GLASS_XWALL))
        report["panes"] += 1
        report["walls"].append(index)
    return report


def pane_faults(disk: Any, *, tile: int = GLASS_TILE) -> list[str]:
    """Panes that can never break, and panes with nothing behind them.

    Both are invisible to every other reading: the cstat is right, the tile
    is right, and the window is simply permanent.
    """
    out = []
    for index, wall in enumerate(disk.walls):
        fields = wall.fields
        if int(fields.get("over_picnum", 0)) != int(tile):
            continue
        extra = getattr(wall, "extra", None)
        values = (extra.fields if extra is not None and hasattr(extra, "fields")
                  else {})
        if not values.get("trigger_vector"):
            out.append(
                f"wall {index} wears the glass overlay but reports no "
                f"trigger_vector: NBlood needs it before it will even look at "
                f"the pane, so this window is permanent")
        if int(fields.get("next_sector", -1)) < 0:
            out.append(
                f"wall {index} is glazed on a ONE-SIDED wall: there is "
                f"nothing behind it to be transparent to, and the mask law "
                f"forbids the overlay there")
        if not int(fields["cstat"]) & 16:
            out.append(
                f"wall {index} carries the glass tile without the masked bit, "
                f"so the overlay is never drawn")
    return out


def breaks_to(cstat: int) -> int:
    """What a pane's cstat becomes when it is shot out.

    `trTriggerWall` clears blocking, hitscan and masked on both sides. Useful
    for reading a map's post-break topology without running the engine --
    which is what makes kWallGib the one mechanism that OPENS a route.
    """
    return int(cstat) & ~BREAK_CLEARS
