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

from . import motion
from .planar_layout import PlanarLayout
from .texture_align import natural_x_repeat
from .player_space import PLAYER_PROFILES

#: Marker tile and mounting. All 308 campaign slide gates use tile 3997 on
#: statnum 10; 97% and 93% of their two markers carry cstat 32896, and none the
#: bare invisible bit alone.
#: kMarkerAxis, from blood_types: the pivot a RotateMarked sector turns about.
MARKER_AXIS_TYPE = 5

#: One standing human, from the player profile; never hardcoded.
PLAYER_HEIGHT = PLAYER_PROFILES["blood"].standing_height

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
#: Owner anchor 146, binding strong: the curtain texture. 147 is its
#: translucent variant and belongs on a maskwall or a sprite, never on a
#: plain wall -- it carries the mask colour.
CURTAIN_PICNUM = 146

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


#: kSectorRotateMarked. The engine motion is one family; whether an instance
#: is a *door* or *scenery* is a spatial question -- does the rotor sit in a
#: doorway? -- and not a field, so the template below is mined from the door
#: members by name and never from the root type.
ROTATE_MARKED = 615

#: The blades are grates (owner-identified). That is what makes a turnstile
#: read as passable machinery rather than a solid drum, and Death Wish reuses
#: the campaign's exact tile.
BLADE_PICNUM = 332
BLADE_COUNT = 4

#: **Vane count is the variant, and the mechanism is one.** Censused over the
#: corpus, every grated rotating door is the same kSectorRotateMarked sector
#: with a different number of vanes on it:
#:
#:     1 vane    15 rotors   a swinging gate   (DOOR-SWINGINGGATE[D])
#:     2 vanes    1 rotor    a double gate     (DOOR-SWINGINGGATE s52)
#:     4 vanes    9 rotors   a turnstile       (E1M4, DWE1M9, DNE3L6, DOOR-ROTATING)
#:
#: So `turnstile` is the four-vane case of a rotating door, not a thing of its
#: own, and `vanes` selects which.
TURNSTILE_VANES = 4
BLADE_QUARTER = 512

#: Two ways to build the same cross, both attested. E1M4 and DWE1M9 use two
#: angles and the flip bit to face the opposite halves outward (0, 0, 512, 512
#: with cstat 8593/8597); DNE3L6 and XMapEdit's own DOOR-ROTATING use four
#: distinct angles a quarter turn apart with one cstat. `FLIPPED_PAIRS` is the
#: campaign's and stays the default; `DISTINCT_ANGLES` generalizes to any vane
#: count, which is why a 1- or 2-vane gate uses it.
FLIPPED_PAIRS, DISTINCT_ANGLES = "flipped_pairs", "distinct_angles"

#: A vane's inner edge meets the axis: it stands off the pivot by **half its
#: own drawn width**, so the four of them close on the centre without
#: overlapping. Censused over every grated rotating door in the corpus --
#: 25 rotors in 6 maps -- this holds for **45 of 53 vanes**. The eight
#: exceptions are DWE1M9's, every one 64 short, so its vanes cross the pivot
#: slightly.
#:
#: An earlier version of this file called 384 a constant. It is not: 384 is
#: what E1M4's `x_repeat` 48 happens to produce, and DNE3L6 and the XMapEdit
#: door samples all sit at 448 on `x_repeat` 56. Two maps looked like a rule.
#:
#: Getting the offset wrong at all is what put every blade on the pivot,
#: stacked on top of one another, in the first build: z, angle, repeat and
#: cstat were measured and the position never was.
BLADE_TILE_WIDTH = 64


def blade_offset(x_repeat: int, tile_width: int = BLADE_TILE_WIDTH) -> int:
    """How far a vane stands off the axis: half its own drawn width."""
    return int(x_repeat) * int(tile_width) // 8

#: Build angle -> unit direction. A wall sprite's `ang` is the normal of its
#: face, so a vane extends along the *perpendicular* of its own angle: the
#: blades at angle 0 sit at (0, +-384) and those at 512 at (+-384, 0).
BUILD_DIRECTIONS = {0: (1, 0), 512: (0, 1), 1024: (-1, 0), 1536: (0, -1)}

#: Transcribed rather than composed from flags: E1M4 stores 8593 and 8597 on
#: the two faces of a panel, and the pair differ by bit 2 alone. 8192 is
#: `CARRY_WITH`, so a blade rides its rotor.
BLADE_CSTAT = 8593
BLADE_CSTAT_FLIPPED = 8597

#: A blade spans its rotor exactly: drawn height equals the clear height, top
#: on the ceiling and bottom on the floor, centred on the midpoint because
#: Blood centres a sprite on its own z. All four rotors are 32768 clear and
#: draw a 128-tall tile at y_repeat 64, which is 128 * 64 * 4 = 32768. That is
#: what makes the blade a barrier rather than something to step over -- and
#: getting it wrong leaves the blades hanging in mid air.
BLADE_X_REPEAT = 48
SPRITE_REPEAT_SCALE = 4

#: The ambient sound sprite. E1M4 puts one in *both* its rotors and DWE1M9 in
#: *neither*, so it is a map's habit rather than a trait of the family, and it
#: is off by default.
SFX_TYPE, SFX_PICNUM = 710, 2521

#: How far a rotor turns per cycle, carried on the axis marker's *angle*:
#: Blood interpolates 0 -> angle, so 2048 is one full turn and the sign is the
#: sense of the sweep. The four door rotors do not agree, so this is a choice
#: and not a default the template can force -- E1M4 turns -8192 (four turns)
#: and DWE1M9 2047 (one). The campaign's value is the default here.
TURN = 2048
CAMPAIGN_TRAVEL_ANGLE = -8192
DEATH_WISH_TRAVEL_ANGLE = 2047

#: The system channel `level_start`. The rotor is told once, and cycles for
#: ever because both waves retrigger.
LEVEL_START_CHANNEL = 7

#: What the four door rotors agree on, field by field, and where each came
#: from. `work/_turnstile_template.py` re-mines it.
TURNSTILE_TEMPLATE = {
    "mined_from": {"E1M4": [151, 314], "DWE1M9": [61, 64]},
    "populations": {"E1M4": "blood-campaign",
                    "DWE1M9": "community-curated (precedent, not convention)"},
    "sector_type": ROTATE_MARKED,
    "rx_id": LEVEL_START_CHANNEL,
    "busy_wave": (1, 1),
    "retrigger": (1, 1),
    "interruptable": 0,
    "marker": {"role": "kMarkerAxis", "count": 1, "picnum": MARKER_PICNUM},
    "blades": {"count": BLADE_COUNT, "picnum": BLADE_PICNUM,
               "role": "carried_with_panel",
               "arrangement": "two double-sided panels a quarter turn apart",
               "angles": {"E1M4 151": (0, 0, 512, 512),
                          "E1M4 314": (1024, 1024, 1536, 1536),
                          "DWE1M9 61/64": (1024, 1024, 1536, 1536)},
               "cstat": (BLADE_CSTAT, BLADE_CSTAT_FLIPPED),
               "spans": "floor to ceiling; drawn height == clear height, "
                        "32768 in all four rotors at y_repeat 64",
               "offset_from_axis": "half the vane's own drawn width; 45 of 53 "
                                   "corpus vanes, the 8 exceptions all DWE1M9",
               "counts": {"1 vane": "swinging gate, 15 rotors",
                          "2 vanes": "double gate, 1 rotor",
                          "4 vanes": "turnstile, 9 rotors"},
               "one_rotor_is_a_door": "all 25 grated rotating doors reach "
                                      "exactly two sectors on their own"},
    "busy_time": {"E1M4": (255, 0), "E1M4 partner": (0, 255),
                  "DWE1M9": (100, 0), "DWE1M9 partner": (0, 100)},
    "travel_angle": {"E1M4": -8192, "DWE1M9": 2047, "DNE3L6": 2032},
}


def turnstile_spec(
    *,
    period: int,
    floor_z: int,
    ceiling_z: int,
    travel_angle: int = CAMPAIGN_TRAVEL_ANGLE,
    clockwise: bool = True,
    blade_picnum: int = BLADE_PICNUM,
    blade_tile_height: int = 128,
    blade_tile_width: int = BLADE_TILE_WIDTH,
    blade_x_repeat: int = BLADE_X_REPEAT,
    vanes: int = TURNSTILE_VANES,
    arrangement: str = FLIPPED_PAIRS,
) -> dict[str, Any]:
    """The template's own facts, with no layout involved.

    `vanes` is the variant: 4 is a turnstile, 2 a double gate, 1 a swinging
    gate, and all three are the same sector with a different number of leaves
    on it. **One rotor is a complete door** -- all 25 grated rotating doors in
    the corpus reach exactly two sectors on their own -- so a pair is a
    composition someone chose, not part of the mechanism.

    `turnstile` builds a rotor into a `PlanarLayout`; a project with its own
    room grammar needs the same facts without the region-making, and there
    must not be two copies of them. Returns the sector behaviour, the axis
    marker and the blades, ready to apply to whatever a caller's grammar
    calls a room.
    """
    if period <= 0 or period > 65535:
        raise MechanismError("a spin period must be 1..65535")
    clear = abs(int(floor_z) - int(ceiling_z))
    denominator = int(blade_tile_height) * SPRITE_REPEAT_SCALE
    y_repeat = clear // denominator
    if y_repeat < 1 or y_repeat > 255:
        raise MechanismError(
            f"a {clear}-unit rotor cannot be spanned by a "
            f"{blade_tile_height}-tall blade (needs y_repeat {clear / denominator:.1f})")
    if y_repeat * denominator != clear:
        raise MechanismError(
            f"clear height {clear} is not a whole number of blade tiles "
            f"({denominator} each); the blade would not meet both surfaces")

    offset = blade_offset(blade_x_repeat, blade_tile_width)
    middle = (int(floor_z) + int(ceiling_z)) // 2

    def vane(angle, sign, cstat):
        ux, uy = BUILD_DIRECTIONS[(angle + BLADE_QUARTER) % 2048]
        return {"type": 0, "picnum": int(blade_picnum), "cstat": cstat,
                "angle": angle % 2048, "x_repeat": int(blade_x_repeat),
                "y_repeat": y_repeat, "z": middle,
                "dx": sign * ux * offset, "dy": sign * uy * offset}

    blades = []
    if vanes == 4 and arrangement == FLIPPED_PAIRS:
        # The campaign's: two angles, the flip bit facing the halves outward.
        for panel in range(2):
            angle = (panel * BLADE_QUARTER) % 2048
            blades.append(vane(angle, 1, BLADE_CSTAT))
            blades.append(vane(angle, -1, BLADE_CSTAT_FLIPPED))
    else:
        # The general form: one sprite per vane, evenly spaced, all facing out.
        step = 2048 // max(1, vanes)
        for index in range(vanes):
            blades.append(vane((index * step) % 2048, 1, BLADE_CSTAT))
    return {
        "sector_type": ROTATE_MARKED,
        "behavior": {
            "rx_id": LEVEL_START_CHANNEL,
            "busy_wave_a": 1, "busy_wave_b": 1,
            "retrigger_a": 1, "retrigger_b": 1,
            "interruptable": 0,
            "busy_time_a": int(period) if clockwise else 0,
            "busy_time_b": 0 if clockwise else int(period),
        },
        "axis": {"type": MARKER_AXIS_TYPE, "picnum": MARKER_PICNUM,
                 "cstat": MARKER_CSTAT, "status": MARKER_STATNUM,
                 "angle": int(travel_angle), "x_repeat": 64, "y_repeat": 64,
                 "z": int(floor_z)},
        "blades": blades,
        "blade_span": {"top_z": int(ceiling_z), "bottom_z": int(floor_z),
                       "centre_z": (int(floor_z) + int(ceiling_z)) // 2,
                       "y_repeat": y_repeat,
                       "drawn_height": y_repeat * denominator},
        "vanes": int(vanes), "arrangement": arrangement,
        "blade_offset": offset,
        "period": int(period), "clockwise": bool(clockwise),
        "travel_angle": int(travel_angle),
        "turns": round(travel_angle / TURN, 3),
        "template": "E1M4 151/314 + DWE1M9 61/64",
    }


def turnstile(
    layout: PlanarLayout,
    region_id: str,
    outline: list[tuple[int, int]],
    *,
    pivot: tuple[int, int],
    period: int,
    floor_z: int,
    ceiling_z: int,
    travel_angle: int = CAMPAIGN_TRAVEL_ANGLE,
    clockwise: bool = True,
    blade_picnum: int = BLADE_PICNUM,
    blade_tile_height: int = 128,
    blade_tile_width: int = BLADE_TILE_WIDTH,
    blade_x_repeat: int = BLADE_X_REPEAT,
    vanes: int = TURNSTILE_VANES,
    arrangement: str = FLIPPED_PAIRS,
    sound: bool = False,
    **region_kwargs: Any,
) -> dict[str, Any]:
    """One revolving turnstile rotor, built to the mined template.

    Two things differ between the four campaign and Death Wish door rotors,
    and they are the only two arguments that carry meaning here: where the
    opening is (`outline` and `pivot`) and how fast it spins (`period`, with
    `clockwise` choosing which of the two busy fields carries it).

    Every other fact is the template's, and every line of it was measured on
    E1M4 151/314 and DWE1M9 61/64:

    * the sector is type 615 kSectorRotateMarked -- all four;
    * `rx_id` is 7, the system `level_start` broadcast, so the rotor is told
      once and never again -- all four;
    * both busy waves are 1 and both retrigger, which is what turns a single
      broadcast into an endless cycle -- all four;
    * `interruptable` is 0: nothing stops it -- all four;
    * exactly one kMarkerAxis sprite sits at the pivot, tile 3997 on
      statnum 10 -- all four;
    * exactly four blade sprites ride the sector on tile 332, and they are
      grates, which is what makes the turnstile read as passable machinery
      rather than a drum -- all four, in both populations;
    * those four are **two double-sided panels at right angles**, not four
      evenly spaced vanes: E1M4 151 carries angles 0, 0, 512, 512 and its
      partner 1024, 1024, 1536, 1536, each pair differing only by the flip
      bit so the panel is drawn from either side;
    * **a blade spans the rotor exactly** -- top on the ceiling, bottom on the
      floor, centred on the midpoint because Blood centres a sprite on its own
      z. `y_repeat` is derived from the clear height rather than given, which
      is the difference between a barrier and four grates hanging in mid air;
    * the spin period lives in `busy_time_a` **or** `busy_time_b` and never
      both: E1M4 runs 255/0 against 0/255 and DWE1M9 100/0 against 0/100. Which
      field carries it is what makes a pair counter-rotate, which is why
      `clockwise` is a boolean and not an angle;
    * **how far it turns is the axis marker's own angle**, not a sector field.
      Blood interpolates 0 -> angle, so 2048 is one turn and the sign is the
      sense of the sweep. This one the four rotors do *not* agree on -- E1M4
      turns -8192 and DWE1M9 2047 -- so it is an argument with the campaign's
      value as its default, and a rotor left at angle 0 does not move at all.

    The ambient sound sprite is **off by default** and is not a trait of the
    family: E1M4 puts one in both its rotors and DWE1M9 in neither.

    Pairs are the convention -- `turnstile_pair` builds them counter-rotating,
    which is what both maps do. The same-direction DNE3L6 variant is attested,
    rarer, and reachable by asking for it.

    Returns what it built.
    """
    if len(outline) < 3:
        raise MechanismError(f"{region_id}: a rotor needs a closed outline")
    px, py = int(pivot[0]), int(pivot[1])
    try:
        spec = turnstile_spec(
            period=period, floor_z=floor_z, ceiling_z=ceiling_z,
            travel_angle=travel_angle, clockwise=clockwise,
            blade_picnum=blade_picnum, blade_tile_height=blade_tile_height,
            blade_tile_width=blade_tile_width, blade_x_repeat=blade_x_repeat,
            vanes=vanes, arrangement=arrangement)
    except MechanismError as exc:
        raise MechanismError(f"{region_id}: {exc}") from None
    behavior = spec["behavior"]
    layout.add_region(
        region_id, outline, floor_z=floor_z, ceiling_z=ceiling_z,
        type=ROTATE_MARKED, sector_behavior=behavior, **region_kwargs)

    marker_id = f"placement:{region_id}:axis"
    layout.add_sprite(marker_id, region_id, x=px, y=py, **spec["axis"])

    blades = []
    for index, blade in enumerate(spec["blades"]):
        fields = dict(blade)
        dx, dy = fields.pop("dx"), fields.pop("dy")
        blade_id = f"placement:{region_id}:blade:{index}"
        layout.add_sprite(blade_id, region_id, x=px + dx, y=py + dy, **fields)
        blades.append(blade_id)

    sfx = None
    if sound:
        sfx = f"placement:{region_id}:sfx"
        layout.add_sprite(sfx, region_id, x=px, y=py, z=int(floor_z),
                          type=SFX_TYPE, picnum=SFX_PICNUM, cstat=0,
                          x_repeat=64, y_repeat=64)

    return {
        "region": region_id, "pivot": [px, py],
        "vanes": spec["vanes"], "arrangement": spec["arrangement"],
        "blade_offset": spec["blade_offset"],
        "period": int(period), "clockwise": bool(clockwise),
        "travel_angle": int(travel_angle),
        "turns": round(travel_angle / TURN, 3),
        "behavior": behavior, "axis_marker": marker_id,
        "blades": blades, "sound": sfx,
        "blade_span": spec["blade_span"],
        "template": "E1M4 151/314 + DWE1M9 61/64",
    }


def turnstile_pair(
    layout: PlanarLayout,
    pair_id: str,
    *,
    outlines: tuple[list[tuple[int, int]], list[tuple[int, int]]],
    pivots: tuple[tuple[int, int], tuple[int, int]],
    period: int,
    floor_z: int,
    ceiling_z: int,
    travel_angle: int = CAMPAIGN_TRAVEL_ANGLE,
    counter_rotating: bool = True,
    **kwargs: Any,
) -> dict[str, Any]:
    """Two rotors flanking one entrance, counter-rotating by default.

    Both maps that build turnstile doors build them in pairs and mirror the
    busy field: E1M4 255/0 against 0/255, DWE1M9 100/0 against 0/100. The
    same-direction arrangement is attested on DNE3L6 3 and 11 and is reachable
    with `counter_rotating=False`.
    """
    left = turnstile(layout, f"{pair_id}:a", outlines[0], pivot=pivots[0],
                     period=period, floor_z=floor_z, ceiling_z=ceiling_z,
                     travel_angle=travel_angle, clockwise=True, **kwargs)
    right = turnstile(layout, f"{pair_id}:b", outlines[1], pivot=pivots[1],
                      period=period, floor_z=floor_z, ceiling_z=ceiling_z,
                      travel_angle=travel_angle,
                      clockwise=not counter_rotating, **kwargs)
    return {"pair": pair_id, "counter_rotating": bool(counter_rotating),
            "rotors": [left, right]}


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
    leaf_picnum: int = FENCE_PICNUM,
    leaves: int = 2,
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
    if leaves not in (1, 2):
        raise MechanismError(f"{region_id}: a gate has one leaf or two")
    leaf_x_repeat = leaf_repeat_for(travel, tile_width)
    leaf_width = leaf_x_repeat * tile_width // 4
    if leaf_width * leaves > span + 1:
        raise MechanismError(
            f"{region_id}: {leaves} leaf/leaves of {leaf_width} do not fit a "
            f"{span:.0f} opening; reduce travel or widen the threshold")

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

    #: The whole region id, not its last segment: three exhibits named their
    #: gate regions `<exhibit>:gate` and the short tag made all three build
    #: sprites called `gate_leaf_west`, so two of the three gates silently
    #: had no leaves at all. Region ids are unique; their tails are not.
    tag = region_id
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
    #: A single leaf covers the whole opening rather than meeting a partner
    #: in the middle, so it is authored one travel BEFORE the midpoint: a
    #: CARRY_WITH sprite rests at drawn + T, which puts the rest pose over
    #: the threshold and the open pose aside. Two leaves is the campaign
    #: template and stays the default; one is E1M1 s63's plainer form.
    panels = ((("west", CARRY_AGAINST, -1.0), ("east", CARRY_WITH, +1.0))
              if leaves == 2 else (("leaf", CARRY_WITH, -1.0),))
    if leaves == 1:
        drawn = float(travel)
    for name, carry, sign in panels:
        layout.add_sprite(
            f"{tag}_leaf_{name}", region_id,
            x=int(round(mid[0] + ux * sign * drawn)),
            y=int(round(mid[1] + uy * sign * drawn)),
            z=floor_z, seat="floor",
            type=0, picnum=int(leaf_picnum), status=0,
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
        "leaves": int(leaves),
    }


# `bind_markers` moved into `planar_layout`, because it is structural rather
# than decorative: the loader deletes a marker it cannot bind, so the binding has
# to exist before the native structure check runs, and every layout needs it and
# not just one that calls a constructor from here.
from .planar_layout import bind_markers  # noqa: E402,F401  (re-export)

# ---------------------------------------------------------------------------
# the payload family: mechanisms whose point is WHICH WALLS MOVE
# ---------------------------------------------------------------------------

#: Build's Marked-slide payload flags, on WALLS. `TranslateSector`'s
#: `bAllWalls` is true only for the unmarked types 616/617, so a 614 or 615
#: drags exactly the walls a mapper flagged -- 16384 with the travel, 32768
#: against it. Sprites carry their own 8192/16384 and are dragged regardless.
WALL_MOVES_WITH = 16384
WALL_MOVES_AGAINST = 32768

#: E1M1 s125, the curtain, measured: busy 40 out and 25 back, both waves 1.
CURTAIN_BUSY_OUT, CURTAIN_BUSY_BACK = 40, 25
#: E1M1 s28/s30, the casket: 40 both ways.
PLANAR_DOOR_BUSY = 50
#: The oracle's lid thickness: the tray sits one step above the hole.
PLANAR_LID_STEP = 1024
#: Neither side of the split may end the motion thinner than a body.
PLANAR_MIN_DEPTH = 128
#: Shared by every composition: no half of a motion may end thinner.
MOTION_MIN_DEPTH = 128
#: How far a curtain's fabric stands clear of its frame at each end, so
#: its moving vertices are the frame's wall interiors and not its corners.
#: DOOR-CURTAINS s3: a 64-wide tab in a 256 doorway, drawn 128 out.
#: Tile 146 is 32 wide. The fabric's repeat is computed against this rather
#: than read from the ART, so a constructor stays a pure function of its
#: arguments; `tile_width` overrides it when the fabric is a different tile.
CURTAIN_TILE_WIDTH = 32
CURTAIN_FIN_WIDTH = 64
CURTAIN_RETRACTED = 128
CURTAIN_BUSY = 15
CURTAIN_SEAM = 256
#: Owner anchor 195: the inside faces of jambs, which is what a seam is.
#: E1M1 s125: the strip is 128 deep and its shoulders 64, so the fabric
#: is recessed 64 behind the ends that hold it.
CURTAIN_DEPTH = 128
CURTAIN_SHOULDER = 64
#: One player width; the opening a body needs.
BODY_WIDTH = 384


def _sign(value: int) -> int:
    return (value > 0) - (value < 0)


def _slide_markers(layout, name, region_id, origin, offset, floor_z,
                   to_region=None):
    """The from/to marker pair a Marked slide reads its travel out of.

    Types 3 and 4 -- kMarkerOff and kMarkerOn -- on statnum 10, which the
    engine culls from the world and reads as instructions. The vector between
    them IS the travel; nothing else states it.
    """
    out = []
    #: The "to" marker frequently lands outside the moving sector -- in E1M1's
    #: casket it stands inside the COVER -- because the travel is most of the
    #: sector's own width. `to_region` says where it lives; a marker is on
    #: statnum 10 and is culled from the world, so which sector holds it
    #: matters only to the compiler's containment check.
    for tag, kind, point, where in (
            ("off", 3, origin, region_id),
            ("on", 4, (origin[0] + offset[0], origin[1] + offset[1]),
             to_region or region_id)):
        out.append(layout.add_sprite(
            f"{name}_marker_{tag}", where,
            x=int(point[0]), y=int(point[1]), z=int(floor_z),
            type=kind, picnum=MARKER_PICNUM, status=MARKER_STATNUM,
            cstat=MARKER_CSTAT, x_repeat=64, y_repeat=64, angle=MARKER_ANGLE,
            #: It marks the MOVING sector wherever it happens to stand.
            marker_owner=region_id))
    return out


def _signed_area(points) -> float:
    total = 0.0
    for index, (x, y) in enumerate(points):
        nx, ny = points[(index + 1) % len(points)]
        total += x * ny - nx * y
    return total / 2.0


#: The curtain family has four dialects in the originals. Measured over the
#: 43 campaign maps plus the tutorials: 39 type-614 sectors wear 146/147, of
#: which 26 carry one flagged wall, 12 carry two, and one (E2M1 s95) carries
#: three. (A 40th sector turns up if `maps/blood/campaign/ASAVE1.map` is
#: scanned -- editor autosave debris whose s125 duplicates E1M1's.)
CURTAIN_LEAVES = (1, 2)
#: What the leaf retracts INTO. `void` is the tutorial's default: the slot
#: walls are one-sided and the fabric is simply the wall. `pocket` is
#: DOOR-CURTAINSD s4: the slot is a real sector and the pocket-side wall is
#: MASKED with an over_picnum, which is the only reason the fabric draws in
#: the middle band there.
CURTAIN_SLOTS = ("void", "pocket")
#: DOOR-CURTAINSD s4's pocket overlay.
POCKET_OVER_PICNUM = 1060
#: block | masked | hitscan -- s4's pocket-side walls, cstat 81.
POCKET_CSTAT = 1 | 16 | 64


def curtain_spec(
    *,
    opening: tuple[int, int, int, int],
    axis: str,
    anchored: str = "high",
    leaves: int = 1,
    slot: str = "void",
    fin_width: int = CURTAIN_FIN_WIDTH,
    retracted: int = CURTAIN_RETRACTED,
    tile_width: int = CURTAIN_TILE_WIDTH,
) -> dict:
    """The FACTS of a curtain: outline, fabric edges, flags, markers, repeats.

    Separated from `curtain` for the same reason `turnstile_spec` is
    separated from `turnstile`: a project that speaks the levelprog TREE
    cannot call a PlanarLayout constructor, and blood-city speaks the tree.

    **`leaves`** is 1 or 2. One leaf hangs from the anchored jamb and draws
    the whole way across (DOOR-CURTAINS s3, and 26 of the campaign's 39). Two
    leaves hang from both jambs and CONVERGE, which is why their tips carry
    OPPOSITE flags -- `0x4000` moves with the travel and `0x8000` against it
    (DOOR-CURTAINSD s2, E1M1 s125, and 12 of the 39).

    **`slot`** is where a leaf retracts to. `void` leaves the slot walls
    one-sided, so the fabric is the wall and draws everywhere. `pocket` makes
    the slot a real sector, and then the pocket-side wall must be MASKED with
    an over_picnum or the engine draws nothing in the walkable band
    (engine.cpp:4938-4940: a two-sided wall's middle band is reached only for
    a one-way or masked wall). The pocket regions are the caller's to build;
    this returns where they go.

    `anchored` names the jamb a ONE-leaf curtain hangs from. It is ignored
    for two leaves, which hang from both.
    """
    if axis not in ("x", "y"):
        raise MechanismError(f"axis is 'x' or 'y', not {axis!r}")
    if anchored not in ("low", "high"):
        raise MechanismError("anchored is 'low' or 'high'")
    if int(leaves) not in CURTAIN_LEAVES:
        raise MechanismError(
            f"leaves is 1 or 2, not {leaves!r}; the campaign's 39 curtains "
            f"are 26 one-leaf and 12 two-leaf, and the single three-flag "
            f"sector (E2M1 s95) is not a dialect this builds")
    if slot not in CURTAIN_SLOTS:
        raise MechanismError(f"slot is 'void' or 'pocket', not {slot!r}")
    x0, y0, x1, y1 = (int(v) for v in opening)
    if axis == "y":
        a0, a1, c0, c1 = y0, y1, x0, x1
    else:
        a0, a1, c0, c1 = x0, x1, y0, y1
    if int(leaves) == 1 and anchored == "low":
        a0, a1 = a1, a0
    span = abs(a1 - a0)
    if span <= abs(int(retracted)):
        raise MechanismError(
            f"the fin is drawn {retracted} into an opening only {span} "
            f"across; there is nothing for it to draw over")
    if abs(c1 - c0) <= int(fin_width):
        raise MechanismError(
            f"a {fin_width}-wide fin does not fit a {abs(c1 - c0)}-thick "
            f"doorway")
    middle = (c0 + c1) // 2
    f0, f1 = middle - int(fin_width) // 2, middle + int(fin_width) // 2

    def _pt(along: int, across: int) -> tuple[int, int]:
        return (across, along) if axis == "y" else (along, across)

    low, high = min(a0, a1), max(a0, a1)
    tip_low = tip_high = None
    if int(leaves) == 1:
        step = 1 if (a0 - a1) > 0 else -1
        tip = a1 + step * int(retracted)
        jambs = [(a1, tip, 0x4000)]
        #: the fabric closes the whole span
        closed = [span]
    else:
        #: Two leaves converge from both jambs, each covering half. The tips
        #: carry OPPOSITE flags, which is what makes them approach rather
        #: than travel together.
        tip_low = low + int(retracted)
        tip_high = high - int(retracted)
        jambs = [(low, tip_low, 0x4000), (high, tip_high, 0x8000)]
        #: named for the outline walk below
        closed = [span // 2, span // 2]

    #: The notch is CUT OUT of the doorway rect, not stuck onto it -- the
    #: space inside it belongs to nobody, which is what leaves its three
    #: walls one-sided and the fabric visible. So the outline is a traversal
    #: of the rect with each notch inserted where the walk reaches its jamb.
    #: Appending them instead gave a polygon that crossed itself, because
    #: two notches at opposite ends cannot both follow the fourth corner.
    fabric, flagged, repeats, pockets = [], [], [], []

    def _notch(root, tip, first, second):
        """The four points of a slot cut inward from the `root` jamb."""
        return [_pt(root, first), _pt(tip, first),
                _pt(tip, second), _pt(root, second)]

    if int(leaves) == 1:
        outline = ([_pt(a1, c0), _pt(a0, c0), _pt(a0, c1), _pt(a1, c1)]
                   + _notch(a1, jambs[0][1], f1, f0))
    else:
        #: down c0, up the high jamb through its notch, back along c1, and
        #: down the low jamb through its own.
        outline = ([_pt(low, c0), _pt(high, c0)]
                   + _notch(high, tip_high, f0, f1)
                   + [_pt(high, c1), _pt(low, c1)]
                   + _notch(low, tip_low, f1, f0))

    for index, (root, tip, flag) in enumerate(jambs):
        first, second = (f1, f0) if (int(leaves) == 1 or index == 1) else (f0, f1)
        fabric += [(_pt(root, first), _pt(tip, first)),
                   (_pt(tip, first), _pt(tip, second)),
                   (_pt(tip, second), _pt(root, second))]
        flagged.append({"edge": (_pt(tip, first), _pt(tip, second)),
                        "cstat": flag,
                        "moves": "with" if flag == 0x4000 else "against"})
        shut = closed[index]
        repeats += [natural_x_repeat(shut, int(tile_width)),
                    natural_x_repeat(int(fin_width), int(tile_width)),
                    natural_x_repeat(shut, int(tile_width))]
        if slot == "pocket":
            back = root - (tip - root)
            corner_a, corner_b = _pt(root, f0), _pt(back, f1)
            pockets.append({
                "rect": (min(corner_a[0], corner_b[0]),
                         min(corner_a[1], corner_b[1]),
                         max(corner_a[0], corner_b[0]),
                         max(corner_a[1], corner_b[1])),
                "over_picnum": POCKET_OVER_PICNUM, "cstat": POCKET_CSTAT})

    if _signed_area(outline) < 0:
        outline.reverse()

    return {
        "outline": outline, "leaves": int(leaves), "slot": slot,
        "fabric": tuple(fabric),
        "flagged": tuple(flagged),
        #: kept for the one-leaf callers that predate `leaves`
        "flagged_edge": flagged[0]["edge"],
        #: DOOR-CURTAINSD s2 places a TWO-leaf pair's markers at the span's
        #: MIDDLE (off) and at one leaf's tip (on), so the delta is
        #: `span/2 - retracted` -- how far each tip travels to meet the
        #: other. Measured on s2: span 2048, retracted 64, travel 960.
        #: A one-leaf pair spans the whole opening instead.
        "off_at": (_pt(a0, middle) if int(leaves) == 1
                   else _pt((low + high) // 2, middle)),
        "on_at": (_pt(jambs[0][1], middle) if int(leaves) == 1
                  else _pt(tip_high, middle)),
        "closed_span": span, "x_repeats": tuple(repeats),
        "pockets": tuple(pockets),
        "anchored_at": a1, "closed_at": a0,
    }


def curtain(
    layout: PlanarLayout,
    name: str,
    *,
    opening: tuple[int, int, int, int],
    axis: str,
    channel: int,
    leaf_region: str,
    floor_z: int,
    ceiling_z: int,
    anchored: str = "high",
    leaves: int = 1,
    slot: str = "void",
    fin_width: int = CURTAIN_FIN_WIDTH,
    retracted: int = CURTAIN_RETRACTED,
    tile_width: int = CURTAIN_TILE_WIDTH,
    frame_picnum: int | None = None,
    state: int = 0,
    picnum: int = CURTAIN_PICNUM,
    busy_out: int = CURTAIN_BUSY,
    busy_back: int = CURTAIN_BUSY,
    route: str = "remote",
    **region_kwargs,
) -> dict:
    """A curtain: internal fins that draw across their own doorway.

    Built to `maps/blood/mechanism/Vanilla/DOOR-CURTAINS.map` and its double,
    and it now knows both leaf counts. `curtain_spec` carries the geometry so
    this and blood-city's tree-language version cannot drift apart.

    ONE leaf hangs from the anchored jamb and draws the whole way across --
    26 of the campaign's 39. TWO hang from both jambs and CONVERGE, their
    tips carrying opposite flags, which is the only thing that makes them
    approach rather than travel together -- 12 of the 39.

    Markers are state-anchored: type 3 is the position for state OFF, type 4
    for ON, the geometry is saved at ON, and `state` decides the snap. With
    state 0 the curtain comes up CLOSED.

    The repeats are authored for the CLOSED span, not the drawn one. The file
    holds the gathered bundle; sizing the texture to that is what left this
    project's first curtain at forty-eight times natural stretch.
    """
    spec = curtain_spec(opening=opening, axis=axis, anchored=anchored,
                        leaves=leaves, slot=slot, fin_width=fin_width,
                        retracted=retracted, tile_width=tile_width)
    if state not in (0, 1):
        raise MechanismError(f"{name}: state is 0 or 1")

    behavior = {
        "busy_time_a": int(busy_out), "busy_time_b": int(busy_back),
        "state": int(state), "busy": 65536 if state else 0,
    }
    behavior.update(motion.wiring(route=route, channel=channel,
                                  command=motion.CMD_TOGGLE,
                                  receiver_state=int(state)))
    #: NOT pushable through the sector: the shove belongs on the cloth, as
    #: XWALLs, which is how the tutorial wires it. A sector flag would make
    #: the whole doorway a button, frame included.
    layout.add_region(leaf_region, spec["outline"], role="doorway", type=614,
                      floor_z=floor_z, ceiling_z=ceiling_z,
                      wall_picnum=int(frame_picnum if frame_picnum is not None
                                      else picnum),
                      sector_behavior=behavior, **region_kwargs)
    for flag in spec["flagged"]:
        edge = flag["edge"]
        layout.carry_wall(leaf_region, edge[0], edge[1], moves=flag["moves"])
    for edge, repeat in zip(spec["fabric"], spec["x_repeats"]):
        layout.paint_wall(leaf_region, edge[0], edge[1],
                          picnum=int(picnum), x_repeat=int(repeat))
        motion.wall_button(layout, leaf_region, edge, channel=channel,
                           command=motion.CMD_TOGGLE, receiver_state=state)

    markers = motion.place_markers(
        layout, name.replace(":", "_"), driven_region=leaf_region,
        off_at=spec["off_at"], on_at=spec["on_at"], z=int(floor_z))
    return {
        "leaf": leaf_region, "channel": int(channel), "leaves": int(leaves),
        "slot": slot, "spec": spec,
        "state": int(state), "rests": "open" if state else "closed",
        "markers": markers,
        "declared_motion": [leaf_region],
    }


def planar_door(
    layout: PlanarLayout,
    name: str,
    *,
    footprint: tuple[int, int, int, int],
    axis: str,
    split: int,
    travel: int,
    channel: int,
    lid_region: str,
    hole_region: str,
    floor_z: int,
    ceiling_z: int,
    lid_step: int = PLANAR_LID_STEP,
    plane: str = "floor",
    motor: str = "lid",
    flags: str = "both",
    busy_time: int = PLANAR_DOOR_BUSY,
    transmits: int | None = None,
    lift_out: int = 0,
    route: str = "remote",
    lid_kwargs: dict | None = None,
    hole_kwargs: dict | None = None,
    **region_kwargs,
) -> dict:
    """A floor that slides aside to uncover the hole you drop through.

    The owner's definition, from `maps/blood/mechanism/casket.map`: ONE
    footprint SPLIT by a sliding boundary into a LID and a HOLE. The lid
    slides to cover or reveal the hole, and the hole is the passage.

    Composition of the same four primitives:

    * **marked-wall motion** -- one flagged wall, and it is the boundary the
      two halves share, so the travel re-partitions plan area between them.
      `flags` chooses whether one or both records of the pair carry it; the
      oracle flags both and E1M1 flags one, and both are legal.
    * **motion markers** -- from the boundary's REST pose to its OPEN pose,
      derived here. Each is placed in whichever half actually contains it,
      because with the motor on the hole the hole is thin when drawn.
    * **control wiring** -- `route` and the verb, checked against the state
      the motor is saved in. The zoo shipped a motor saved ON with a switch
      sending ON: valid fields, no-op mechanism.
    * **ROR stack** -- the caller links the revealed hole, see-through.

    Composition facts, derived or clamped and never trusted from a caller:
    the split must divide the footprint; the travel must land the boundary
    inside it; and neither half may end the motion thinner than a body. The
    zoo asked for 3072 into a cover 768 deep and the cover inverted.
    """
    if axis not in ("x", "y"):
        raise MechanismError(f"{name}: axis is 'x' or 'y', not {axis!r}")
    if motor not in ("lid", "hole"):
        raise MechanismError(f"{name}: motor is 'lid' or 'hole'")
    if flags not in ("one", "both"):
        raise MechanismError(f"{name}: flags is 'one' or 'both'")
    if not travel:
        raise MechanismError(f"{name}: a planar door with no travel is a wall")

    x0, y0, x1, y1 = (int(v) for v in footprint)
    low, high = (x0, x1) if axis == "x" else (y0, y1)
    if not low < int(split) < high:
        raise MechanismError(
            f"{name}: the split at {split} is outside the footprint "
            f"{low}..{high}; the boundary has to divide it")
    rest = int(split)
    opened = rest + int(travel)
    if not low < opened < high:
        raise MechanismError(
            f"{name}: travel {travel} carries the boundary from {rest} to "
            f"{opened}, outside the footprint {low}..{high}. The sector "
            f"receiving it would invert")
    for pose, where in ((rest, "covered"), (opened, "open")):
        if min(pose - low, high - pose) < MOTION_MIN_DEPTH:
            raise MechanismError(
                f"{name}: in its {where} pose the split at {pose} leaves "
                f"{min(pose - low, high - pose)} units on one side of a "
                f"{high - low}-unit footprint, under the {MOTION_MIN_DEPTH} "
                f"a body needs. Widen the footprint or shorten the travel")

    if plane not in ("floor", "ceiling"):
        raise MechanismError(f"{name}: plane is 'floor' or 'ceiling'")
    lid_first = int(travel) < 0
    def _rect(a: int, b: int) -> list[tuple[int, int]]:
        if axis == "x":
            return [(a, y0), (b, y0), (b, y1), (a, y1)]
        return [(x0, a), (x1, a), (x1, b), (x0, b)]

    lid_span = (low, rest) if lid_first else (rest, high)
    hole_span = (rest, high) if lid_first else (low, rest)
    #: A casket is TWO of these, one above the other: a lid in the upper
    #: room's FLOOR and its mirror in the lower room's CEILING, on one
    #: channel so the two openings appear together. The oracle's s2/s3 is the
    #: floor plane and s5/s6 the ceiling plane, and the lid's 1024 step goes
    #: on whichever surface the plane names -- s2's floor is 1024 above s3's,
    #: s5's ceiling 1024 below s6's.
    if plane == "floor":
        lid_floor, lid_ceiling = int(floor_z) - int(lid_step), int(ceiling_z)
        hole_floor, hole_ceiling = int(floor_z), int(ceiling_z)
    else:
        lid_floor, lid_ceiling = int(floor_z), int(ceiling_z) + int(lid_step)
        hole_floor, hole_ceiling = int(floor_z), int(ceiling_z)

    #: Saved COVERED and rested there, so the lid is shut when you arrive.
    behavior = {
        "busy_time_a": int(busy_time), "busy_time_b": int(busy_time),
        "state": 1, "busy": 65536,
    }
    behavior.update(motion.wiring(route=route, channel=channel,
                                  command=motion.CMD_TOGGLE,
                                  receiver_state=1))
    if transmits:
        behavior["tx_id"] = int(transmits)
        behavior["command"] = motion.CMD_TOGGLE
    if lift_out:
        if motor != "hole":
            raise MechanismError(
                f"{name}: lift_out raises the floor the player stands on, so "
                f"it belongs on the hole; this door's motor is the lid")
        behavior.update({
            "off_floor_z": int(floor_z),
            "on_floor_z": int(floor_z) - int(lift_out),
            "off_ceiling_z": int(ceiling_z),
            "on_ceiling_z": int(ceiling_z),
        })

    common = dict(region_kwargs)
    layout.add_region(
        lid_region, _rect(*lid_span), role="doorway",
        type=614 if motor == "lid" else 0,
        floor_z=lid_floor, ceiling_z=lid_ceiling,
        **({"sector_behavior": behavior} if motor == "lid" else {}),
        **common, **(lid_kwargs or {}))
    layout.add_region(
        hole_region, _rect(*hole_span), role="doorway",
        type=614 if motor == "hole" else 0,
        floor_z=hole_floor, ceiling_z=hole_ceiling,
        **({"sector_behavior": behavior} if motor == "hole" else {}),
        **common, **(hole_kwargs or {}))

    edge = ((rest, y0), (rest, y1)) if axis == "x" else ((x0, rest), (x1, rest))
    driver = lid_region if motor == "lid" else hole_region
    passenger = hole_region if motor == "lid" else lid_region
    layout.add_connection(f"{name}:boundary", lid_region, hole_region,
                          a1=edge[0], a2=edge[1], min_width=BODY_WIDTH)
    layout.carry_wall(driver, edge[0], edge[1], moves="with")
    if flags == "both":
        layout.carry_wall(passenger, edge[0], edge[1], moves="with")

    across = ((y0 + y1) // 2) if axis == "x" else ((x0 + x1) // 2)
    def _point(at: int) -> tuple[int, int]:
        return (at, across) if axis == "x" else (across, at)

    def _holds(along: int) -> str:
        return lid_region if lid_span[0] <= along <= lid_span[1] else hole_region

    def _floor_of(region: str) -> int:
        return lid_floor if region == lid_region else hole_floor

    off_where, on_where = _holds(opened), _holds(rest)
    markers = motion.place_markers(
        layout, name.replace(":", "_"), driven_region=driver,
        off_at=_point(opened), on_at=_point(rest),
        off_region=off_where, on_region=on_where,
        off_z=_floor_of(off_where), on_z=_floor_of(on_where))
    return {
        "lid": lid_region, "hole": hole_region, "motor": driver,
        "channel": int(channel), "axis": axis,
        "rest": rest, "opened": opened, "travel": int(travel),
        "footprint": (low, high), "lid_step": int(lid_step),
        "flags": flags, "markers": markers, "lift_out": int(lift_out),
        "hole_always": hole_span,
        "link_anchor": _point((hole_span[0] + hole_span[1]) // 2),
        "rests": "covered", "plane": plane,
        #: The two halves share the boundary, so both are in the motion set
        #: by construction and both are declared.
        "declared_motion": [lid_region, hole_region],
    }

#: E1M1's casket cover, s27: amplitude 2, frequency 5, wave 7, on floor,
#: ceiling and walls at once. The owner's grammar calls this the mechanism's
#: VOICE -- presentation synced to state, not decoration.
def shade_wave(*, amplitude: int = 2, frequency: int = 5, wave: int = 7,
               always: bool = True, floor: bool = True, ceiling: bool = True,
               walls: bool = True) -> dict[str, int]:
    """XSECTOR fields for a sector that breathes light with its state.

    Blood's mechanisms have a visual voice and the campaign uses it
    constantly -- 21 of this project's own level modules reach for shade by
    hand. The fields are independent axes, like every other group in the
    XSECTOR: amplitude and frequency say how much and how fast, `wave`
    selects the shape, and three flags say which surfaces join in.

    A negative amplitude darkens where a positive one brightens; E1M1's
    casket cover uses +2 and the hole it opens onto uses -16, so the lid
    lightens as the grave darkens.
    """
    fields = {
        "amplitude": int(amplitude),
        "shade_frequency": int(frequency),
        "shade_wave": int(wave),
    }
    if always:
        fields["shade_always"] = 1
    if floor:
        fields["shade_floor"] = 1
    if ceiling:
        fields["shade_ceiling"] = 1
    if walls:
        fields["shade_walls"] = 1
    return fields


#: MACHINERY-LIFT s2, the basic exemplar: fifteen tenths each way, and it is
#: pushable through the sector because a lift is a floor you stand on.
LIFT_BUSY = 15


def lift(
    layout: PlanarLayout,
    name: str,
    *,
    footprint: tuple[int, int, int, int],
    region: str,
    low_z: int,
    high_z: int,
    ceiling_z: int,
    channel: int | None = None,
    state: int = 0,
    starts: str = "low",
    busy_up: int = LIFT_BUSY,
    busy_down: int = LIFT_BUSY,
    route: str = "push",
    key: int | None = None,
    wait: int | None = None,
    **region_kwargs,
) -> dict:
    """A floor that travels between two heights on a state.

    Queue rank 2, built to `maps/blood/mechanism/Vanilla/MACHINERY-LIFT.map`,
    which is twenty-odd lifts differing one field at a time.

    The vertical is the same shape as the horizontal, and that is the whole
    idea: a z-moving sector carries `off_floor_z`/`on_floor_z` exactly as a
    slide carries a marker pair, and `state` chooses between them at load the
    same way (`ZTranslateSector` runs from the same busy that `trInit` set
    from `state`). So a lift needs no markers at all -- the pair IS in the
    XSECTOR -- and `starts` says which end it is found at.

    Unlike a curtain, a lift IS pushed through its sector: s2 carries
    `trigger_push` and `trigger_wall_push` itself. That is not inconsistency,
    it is what the two things are. You shove a curtain's cloth, so the cloth
    is the button; you stand on a lift and press, so the sector is.

    `wait` gives the self-returning lift of s4 -- a wait and a retrigger, so
    it comes back down on its own -- and `key` the locked lift of s5.
    """
    if starts not in ("low", "high"):
        raise MechanismError(f"{name}: starts is 'low' or 'high'")
    if state not in (0, 1):
        raise MechanismError(f"{name}: state is 0 or 1")
    low_z, high_z = int(low_z), int(high_z)
    if low_z <= high_z:
        raise MechanismError(
            f"{name}: low_z {low_z} must be BELOW high_z {high_z}; Build z "
            f"grows downward, so the low floor is the larger number")
    if int(ceiling_z) >= high_z:
        raise MechanismError(
            f"{name}: the ceiling at {ceiling_z} is not above the raised "
            f"floor at {high_z}; the lift would arrive inside it")
    #: `state` picks the pose, so which z is OFF depends on which end it
    #: starts at -- exactly the marker pair's rule, one dimension over.
    at_off = low_z if starts == "low" else high_z
    at_on = high_z if starts == "low" else low_z
    behavior = {
        "off_floor_z": at_off, "on_floor_z": at_on,
        "off_ceiling_z": int(ceiling_z), "on_ceiling_z": int(ceiling_z),
        "busy_time_a": int(busy_up), "busy_time_b": int(busy_down),
        "state": int(state), "busy": 65536 if state else 0,
    }
    behavior.update(motion.wiring(route=route, channel=channel,
                                  command=motion.CMD_TOGGLE,
                                  receiver_state=int(state), key=key,
                                  locked=key is not None))
    if wait:
        behavior.update({"wait_time_a": int(wait), "retrigger_a": 1})
    x0, y0, x1, y1 = (int(v) for v in footprint)
    outline = [(x0, y0), (x1, y0), (x1, y1), (x0, y1)]
    if _signed_area(outline) < 0:
        outline.reverse()
    layout.add_region(region, outline, role="platform",
                      type=600, floor_z=at_off if not state else at_on,
                      ceiling_z=int(ceiling_z), sector_behavior=behavior,
                      **region_kwargs)
    return {
        "region": region, "channel": channel, "travel": abs(low_z - high_z),
        "rests_at": starts if not state else
                    ("high" if starts == "low" else "low"),
        "low_z": low_z, "high_z": high_z, "state": int(state),
        #: A z motion deforms nothing in plan, so its motion set is itself.
        "declared_motion": [region],
    }
