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


# ---------------------------------------------------------------------------
# the shopfront, as E6M1 builds it
# ---------------------------------------------------------------------------

#: **A shop window is not a pane in a wall; it is a box you look into.**
#:
#: Measured on E6M1, which is where this module's whole recipe came from and
#: where nobody had looked at the geometry around the glass. Its four glazed
#: walls (22, 373, 381, 490) do not lie between the street and the shop. They
#: lie between the SHOP and a display recess: `s4` and `s64` are four-wall
#: sectors 4096 long and 512 deep, open to the street on their outer side,
#: with floor 81920 against the shop's 90112 and ceiling 36864 against
#: -40960. Blood's z grows downward, so that is a sill 8192 up and a head
#: 77824 down -- a box at chest height with a low soffit, which is exactly
#: what a shop window is.
#:
#: The consequence for the facade is the point: the street never meets the
#: glass. The facade material runs across the recess mouth as a lintel band
#: above and a stall riser below, and the pane sits half a metre back in
#: shadow. Glazing a room's own outward face -- which is what `glaze` does on
#: a span, and what blood-city's six shopfronts do -- puts the glass flush in
#: the stonework and gives the eye nothing to read as depth.
#:
#: Not universal, and the number matters: of the 356 glazed walls in the 43
#: campaign maps, **139 (39%) sit in a shallow pocket of six walls or fewer**
#: and 217 are on a room face. So the recess is a strong minority idiom for
#: shopfronts, not a law about all glass, and `recess_spec` is offered to a
#: constructor rather than forced on one.
RECESS_DEPTH = 512
#: E6M1 s52 floor 90112 - s4 floor 81920.
RECESS_SILL = 8192
#: E6M1 s52 ceiling -40960 - s4 ceiling 36864, as a drop from the room head.
RECESS_HEAD_DROP = 77824


def recess_spec(span: Sequence[int], *, axis: str = "x",
                outward: int = 1, depth: int = RECESS_DEPTH,
                sill: int = RECESS_SILL, head_drop: int = RECESS_HEAD_DROP,
                room_floor_z: int = 0, room_ceiling_z: int = 0
                ) -> dict[str, Any]:
    """The display box between a street and a shop, to E6M1's measurements.

    Returns the recess outline in world coordinates, the two z values it
    holds, and which of its edges is the pane and which is the mouth -- the
    mouth being the edge the FACADE run crosses, not a hole the facade stops
    at. A caller that carves this out of a facade wall and hangs the pane on
    `pane_edge` gets E6M1's arrangement; one that glazes `mouth_edge` gets
    what the city does today, and the two look nothing alike from the street.
    """
    x0, y0, x1, y1 = (int(v) for v in span)
    x0, x1 = min(x0, x1), max(x0, x1)
    y0, y1 = min(y0, y1), max(y0, y1)
    if axis not in ("x", "y"):
        raise GlassError(f"a recess runs along x or y, not {axis!r}")
    step = int(depth) * (1 if outward >= 0 else -1)
    if axis == "x":
        #: the span runs along x; the box is pushed in along y
        inner_y = y0
        outer_y = y0 + step
        outline = [(x0, inner_y), (x1, inner_y), (x1, outer_y), (x0, outer_y)]
        pane_edge = ((x0, inner_y), (x1, inner_y))
        mouth_edge = ((x1, outer_y), (x0, outer_y))
    else:
        inner_x = x0
        outer_x = x0 + step
        outline = [(inner_x, y0), (inner_x, y1), (outer_x, y1), (outer_x, y0)]
        pane_edge = ((inner_x, y0), (inner_x, y1))
        mouth_edge = ((outer_x, y1), (outer_x, y0))
    return {
        "outline": outline,
        "pane_edge": pane_edge,
        "mouth_edge": mouth_edge,
        "depth": int(depth),
        #: Blood's z grows downward: a sill is a floor ABOVE the shop's, so
        #: numerically smaller, and a dropped head is numerically larger.
        "floor_z": int(room_floor_z) - int(sill),
        "ceiling_z": int(room_ceiling_z) + int(head_drop),
        "sill": int(sill),
        "head_drop": int(head_drop),
        "source": ("E6M1 s4/s64 against s52: 4096 x 512, floor 81920 vs "
                   "90112, ceiling 36864 vs -40960"),
    }


def _face(entry: Any) -> Any:
    """The field mapping, whether this is a compiled dict or a `DiskObject`.

    `_fields` above returns the object itself for the disk case, because every
    other caller here then goes through `.fields`; this one indexes directly.
    """
    if isinstance(entry, dict):
        return entry["fields"] if "fields" in entry else entry
    return getattr(entry, "fields", entry)


def recess_faults(disk: Any, sector_id: int, *,
                  tile: int = GLASS_TILE) -> list[str]:
    """Is this sector a display recess with the pane on its inner face?

    The two ways the arrangement is lost. A recess whose glass is on the
    MOUTH is a pane flush in the facade with a pointless box behind it; a
    recess with no sill and no head drop is a doorway, and the eye reads it
    as one.
    """
    fields = _face(disk.sectors[sector_id])
    start = int(fields["wall_ptr"])
    count = int(fields["wall_count"])
    walls = list(range(start, start + count))
    glazed = [w for w in walls
              if int(_face(disk.walls[w]).get("over_picnum", 0)) == tile]
    out = []
    if not glazed:
        return [f"sector {sector_id} holds no glass"]
    #: Is this sector a display BOX, or is it the room itself? The measured
    #: separator, and the one the campaign census used: a shallow pocket of
    #: six walls or fewer whose short side is a recess depth. A pane on a
    #: room's own face has the whole room behind it and reads as glass set
    #: flush in the stonework.
    points = [(int(_face(disk.walls[w])["x"]), int(_face(disk.walls[w])["y"]))
              for w in walls]
    short = min(max(p[0] for p in points) - min(p[0] for p in points),
                max(p[1] for p in points) - min(p[1] for p in points))
    if count > 6 or short > 2 * RECESS_DEPTH:
        out.append(
            f"sector {sector_id} is a room ({count} walls, {short} across), "
            f"not a display recess: the pane is flush in the facade. E6M1 "
            f"holds its glass in a {RECESS_DEPTH}-deep box (s4, s64)")
    for wall in glazed:
        nxt = int(_face(disk.walls[wall])["next_sector"])
        if nxt < 0:
            out.append(f"wall {wall} is glazed but ONE-SIDED")
            continue
        there = _face(disk.sectors[nxt])
        if int(there["floor_z"]) == int(fields["floor_z"]):
            out.append(
                f"wall {wall}: no sill -- the recess floor is the shop's, so "
                f"this reads as a doorway (E6M1 lifts it {RECESS_SILL})")
    return out


def panes_without_a_recess(disk: Any, *, tile: int = GLASS_TILE) -> list[str]:
    """Glazed walls with a room on both sides, which is glass flush in stone.

    The map-level question, because `recess_faults` answers a per-sector one
    and a pane only needs a display box on ONE side: E6M1's wall 22 runs from
    the recess `s4` into the shop `s52`, and `s52` is emphatically a room.
    """
    owners: dict[int, int] = {}
    for sector_id, sector in enumerate(disk.sectors):
        fields = _face(sector)
        start = int(fields["wall_ptr"])
        for wall in range(start, start + int(fields["wall_count"])):
            owners[wall] = sector_id
    out = []
    for index, wall in enumerate(disk.walls):
        if int(_face(wall).get("over_picnum", 0)) != tile:
            continue
        here = owners.get(index, -1)
        there = int(_face(wall)["next_sector"])
        sides = [s for s in (here, there) if s >= 0]
        if any(not recess_faults(disk, s, tile=tile) for s in sides):
            continue
        out.append(f"wall {index}: rooms on both sides ({here}, {there}); "
                   f"no display recess holds this pane")
    return out
