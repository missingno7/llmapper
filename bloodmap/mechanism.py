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
