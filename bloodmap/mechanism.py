"""Build a mechanism from its mined template, instead of checking one against it.

`bloodmap.assembly` decompiles the campaign's machinery into templates: what
parts a sliding gate has, what fields each carries, and -- the part no
field-by-field mining can reach -- what each part's position, angle and size must
be *relative to the others*.

That was half a loop. This is the other half. A gate here is one call taking the
two things that actually differ between one gate and the next -- where the
opening is, and how far the leaves travel -- and every other fact comes from the
template. The twelve facts that took four sessions to get right individually are
no longer twelve decisions.

Each constructor states, in its own docstring, which template line each fact
comes from, so the derivation stays visible at the point of use rather than
living only in a JSON file. Where the template is silent or thin, that is said
too: `MIN_OBSERVATIONS` is the difference between a convention and an anecdote,
and a constructor should not launder one into the other.
"""

from __future__ import annotations

from math import atan2, hypot, pi
from typing import Any

from .planar_layout import PlanarLayout

#: Marker tile and mounting. All 308 campaign slide gates use tile 3997 on
#: statnum 10; 97% and 93% of their two markers carry cstat 32896, and none the
#: bare invisible bit alone.
MARKER_PICNUM = 3997
MARKER_STATNUM = 10
MARKER_CSTAT = 32896

#: Both markers at angle 0, in 98% and 100% of gates. `TranslateSector`
#: interpolates rotation between them, so a shared non-zero angle would turn the
#: whole sector through it for the length of the slide.
MARKER_ANGLE = 0

#: The fence tile the campaign actually uses: 63 placements from 3.64 player
#: heights up. Tile 1064 appears twice in the whole game, both at 5.82.
FENCE_PICNUM = 1044

#: A leaf's mounting: blocking, wall-aligned, one-sided, centred, hitscan.
#: E1M1's two leaves are exactly 16797 and 8605 -- this plus the carry bit.
LEAF_CSTAT = 1 | 4 | 8 | 16 | 128 | 256
CARRY_WITH = 8192
CARRY_AGAINST = 16384

#: Blood's own commands.
CMD_OFF, CMD_ON, CMD_TOGGLE = 0, 1, 3

#: The two resting poses the campaign uses, and nothing else: 579 slide and
#: rotate sectors at (0, 0) and 80 at (1, 65536). `trInit` translates a sector
#: to busy -65536, takes that as its base, then translates to the authored busy
#: -- so busy 65536 is the pose the geometry was drawn in.
POSE_DRAWN_SHUT = (1, 65536)
POSE_DRAWN_OPEN = (0, 0)


class MechanismError(ValueError):
    pass


def _fields(item: Any) -> dict[str, Any]:
    return item["fields"] if isinstance(item, dict) else item.fields


def _direction(a: tuple[int, int], b: tuple[int, int]) -> int:
    return int(round(atan2(b[1] - a[1], b[0] - a[0]) / (2 * pi) * 2048)) & 2047


def leaf_repeat_for(travel: int, tile_width: int = 128) -> int:
    """The widest x_repeat whose leaf clears the opening when the gate opens.

    A leaf moves by the marker separation and no further, so a leaf wider than
    that distance is still standing in the doorway when the gate has finished
    opening. The campaign builds to just inside the limit -- E1M1 travels 1448
    against a 1536 leaf, E1M5 1600 against 1792 -- so the rule is
    ``width <= travel``.
    """
    return max(1, min(255, (int(travel) * 4) // int(tile_width)))


def sliding_gate(
    layout: PlanarLayout,
    region_id: str,
    outline: list[tuple[int, int]],
    *,
    threshold: tuple[tuple[int, int], tuple[int, int]],
    travel: int,
    channel: int,
    floor_z: int,
    ceiling_z: int,
    tile_height: int = 128,
    tile_width: int = 128,
    busy_time: int = 20,
    pushable: bool = True,
    drawn_shut: bool = True,
    **region_kwargs: Any,
) -> dict[str, Any]:
    """A two-leaf sliding gate, built to the campaign's own template.

    `threshold` is the line the shut gate hangs in -- the opening it fills. The
    leaves are placed on it, part along it, and retract into the jambs at either
    end.

    Every other fact is the template's:

    * the sector rests at ``(state, busy) = (1, 65536)`` when drawn shut, which
      is one fact and not two -- no campaign gate separates them;
    * both markers sit on the threshold's midpoint, `travel` apart along it, at
      angle 0, tile 3997, statnum 10, cstat 32896;
    * each leaf's angle is the threshold direction plus a quarter turn, because
      a wall-aligned sprite's angle is the normal of its face and 59 of the
      campaign's 65 fence sprites are perpendicular to the wall they lie on;
    * each leaf is no wider than `travel`, and seated on the floor -- Blood
      centres a sprite on its own z, so a leaf placed at `floor_z` is buried to
      the waist;
    * one leaf carries 8192 and the other 16384, so they part rather than
      travelling together;
    * a pushable gate transmits to its own sector with `kCmdToggle`, which is
      what all twelve of the campaign's pushable fences do.

    Returns what it built, so a caller can wire more to the same channel.
    """
    (ax, ay), (bx, by) = threshold
    span = hypot(bx - ax, by - ay)
    if span <= 0:
        raise MechanismError(f"{region_id}: the threshold has no length")
    leaf_x_repeat = leaf_repeat_for(travel, tile_width)
    leaf_width = leaf_x_repeat * tile_width // 4
    if leaf_width * 2 > span + 1:
        raise MechanismError(
            f"{region_id}: two leaves of {leaf_width} do not fit a {span:.0f} opening; "
            f"reduce travel or widen the threshold")

    along = _direction((ax, ay), (bx, by))
    ux, uy = (bx - ax) / span, (by - ay) / span
    mid = ((ax + bx) / 2.0, (ay + by) / 2.0)

    # A gate is authored in its OPEN pose and rests shut, which is the opposite
    # of the obvious reading and is what both of the campaign's two-leaf gates
    # do. The engine's sequence is why:
    #
    #   trInit:  if (state) busy = 65536;              // busy derives from state
    #            TranslateSector(i, 0, -65536, ...);   // displace by -T
    #            setBaseSpriteSect(i);                 // *that* becomes the base
    #            TranslateSector(i, 0, busy, ...);     // and back out to busy
    #
    # so at busy 0 an 8192 sprite sits at its authored position minus T, and a
    # 16384 sprite at plus T. Resting at (0, 0) therefore pulls the two leaves
    # *together* by T each, and opening to 65536 pushes them apart to where they
    # were drawn.
    #
    # E1M1 measures out exactly so: leaves authored 5.7 player widths either side
    # of the first marker with a travel of 3.77, resting at 1.93 -- half a leaf,
    # meeting in the middle.
    #
    # Authoring them shut and resting at (1, 65536) -- which is what this did --
    # inverts the whole thing: the leaves rest where they were drawn and then
    # travel *inward* when opened, swapping sides and leaving the doorway clear
    # for the moment they pass each other.
    state, busy = POSE_DRAWN_OPEN if drawn_shut else POSE_DRAWN_SHUT
    behavior = {
        "state": state, "busy": busy,
        "busy_time_a": busy_time, "busy_time_b": busy_time,
        "rx_id": channel, "trigger_push": 0, "trigger_wall_push": 0,
    }
    layout.add_region(region_id, outline, role="doorway", type=614,
                      ceiling_z=ceiling_z, floor_z=floor_z,
                      sector_behavior=behavior, **region_kwargs)

    tag = region_id.split(":")[-1]
    for name, kind, offset in (("off", 3, 0.0), ("on", 4, float(travel))):
        layout.add_sprite(
            f"{tag}_marker_{name}", region_id,
            x=int(round(mid[0] + ux * offset)), y=int(round(mid[1] + uy * offset)),
            z=floor_z, type=kind, picnum=MARKER_PICNUM, status=MARKER_STATNUM,
            cstat=MARKER_CSTAT, x_repeat=64, y_repeat=64, angle=MARKER_ANGLE)

    height = abs(floor_z - ceiling_z)
    leaf_y_repeat = max(8, ((height // (4 * tile_height)) // 8) * 8)
    leaf_behavior = (
        {"tx_id": channel, "command": CMD_TOGGLE, "trigger_on": 1, "trigger_push": 1}
        if pushable else {})
    # Drawn parted by a further `travel`, so that the rest pose closes them.
    half = leaf_width / 2.0
    drawn = half + travel if drawn_shut else half
    for name, carry, sign in (("west", CARRY_AGAINST, -1.0), ("east", CARRY_WITH, +1.0)):
        layout.add_sprite(
            f"{tag}_leaf_{name}", region_id,
            x=int(round(mid[0] + ux * sign * drawn)),
            y=int(round(mid[1] + uy * sign * drawn)),
            z=floor_z, seat="floor",
            type=0, picnum=FENCE_PICNUM, status=0,
            cstat=carry | LEAF_CSTAT,
            x_repeat=leaf_x_repeat, y_repeat=leaf_y_repeat,
            shade=-8, angle=(along + 512) & 2047,
            behavior=dict(leaf_behavior))

    return {
        "region": region_id,
        "channel": channel,
        "travel": int(travel),
        "leaf_x_repeat": leaf_x_repeat,
        "leaf_width": leaf_width,
        "leaf_angle": (along + 512) & 2047,
        "state_busy": (state, busy),
        "leaf_drawn_offset": drawn,
        "pushable": pushable,
    }


# `bind_markers` moved into `planar_layout`, because it is structural rather
# than decorative: the loader deletes a marker it cannot bind, so the binding has
# to exist before the native structure check runs, and every layout needs it and
# not just one that calls a constructor from here.
from .planar_layout import bind_markers  # noqa: E402,F401  (re-export)
