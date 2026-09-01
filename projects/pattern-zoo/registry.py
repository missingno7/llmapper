"""The Pattern Zoo's exhibit registry.

v2. The owner walked v1 and it failed conceptually: **no mechanism worked.**
The map had zero type-600 sectors, because the stalls hand-assembled XSECTOR
dictionaries and never set the sector *type* -- and XSECTOR data on a type-0
sector does nothing. The only live machinery in v1 was the rotors, and they
were live because `mechanism.turnstile` sets its own type.

Three rules come out of that, and they are what this file is shaped by.

**One: every exhibit is built by the code that owns the concept.** A door is
`doors.z_motion_door` with `type=600`; a rotor is `mechanism.turnstile`; a
crate is a sector volume wearing a `templates` crate module; a frontage is
`aperture.facade_run`. Where no owning constructor exists the stall is an
honest **EMPTY** exhibit with the gap lettered on its wall -- never a
hand-rolled imitation. v1's crates were sprites, its shelf run was a sprite on
a wall, its mannequins floated: three depictions that passed a render and
failed a player.

**Two: each room is sized for what it shows.** v1's stalls were a grid of
equal boxes 1.5 player heights high; the campaign median is 33280 units,
1.96 heights (`norms-v1.json` `shape.median_height`). A lift needs two
storeys. A facade needs street scale and somewhere to stand back and look.

**Three: the zoo reads itself.** Every entry carries `expect` -- what
`bloodmap.effects` and `bloodmap.conditional` must find in the built map for
the claim on the wall to be true. Renders and load smoke both passed on a dead
map; only reading the map back catches that.

Owner feedback arrives **by label**, so `label` is a stable identity. Changing
one retires an exhibit and starts another.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable

#: Campaign median clear height, `norms-v1.json` `shape.median_height`:
#: 33280 units, 1.96 player heights. The default a room gets when the exhibit
#: does not need otherwise.
MEDIAN_CLEAR = 33280


@dataclass(frozen=True)
class Expect:
    """What the understanding stack must find for the label to be true.

    Checked against the *built map* by `selfread.py`, not against the source
    that built it. That is the whole point: v1's source looked like doors.
    """

    #: The sector type the exhibit's mechanism must carry, if any.
    sector_type: int | None = None
    #: A trigger kind `conditional.design_role` must report among its causes.
    trigger: str = ""
    #: What `effects.design_object` must read the mechanism as.
    reads_as: str = ""
    #: The route must require this key number.
    requires_key: int = 0
    #: The route must be one-way.
    irreversible: bool = False
    #: The mechanism must listen on this channel.
    rx_id: int | None = None
    #: At least this many sectors of `sector_type` in the stall's own group.
    count: int = 1

    def summary(self) -> str:
        """What the self-read had to find, in words, for the tour sheet."""
        parts = []
        if self.sector_type is not None:
            parts.append(f"{self.count} sector(s) of type {self.sector_type}")
        if self.reads_as:
            parts.append(f"read as a {self.reads_as}")
        if self.trigger:
            parts.append(f"worked by a {self.trigger}")
        if self.rx_id is not None:
            parts.append(f"listening on channel {self.rx_id}")
        if self.requires_key:
            parts.append(f"requiring key {self.requires_key}")
        if self.irreversible:
            parts.append("one-way")
        return ", ".join(parts)

    def is_empty(self) -> bool:
        return (self.sector_type is None and not self.trigger
                and not self.reads_as and not self.requires_key
                and not self.irreversible and self.rx_id is None)


@dataclass(frozen=True)
class Exhibit:
    """One stall."""

    #: Stable identity. Owner corrections are filed against it.
    label: str
    about: str
    try_this: str
    provenance: str
    #: Dotted names of the constructors this stall demonstrates.
    covers: tuple[str, ...] = ()
    #: Builds the stall's contents. `None` is an EMPTY stall and `blocker`
    #: then says what is missing.
    build: Callable[..., Any] | None = None
    blocker: str = ""
    #: Clear height in map units. The campaign median unless the exhibit
    #: needs otherwise.
    clear: int = MEDIAN_CLEAR
    #: Room footprint in map units, (across, deep).
    size: tuple[int, int] = (5120, 5120)
    #: Wall / floor / ceiling tiles, from the exhibit's own material family.
    skin: tuple[int, int, int] = (400, 294, 285)
    #: What the understanding stack must find.
    expect: Expect = field(default_factory=Expect)
    #: Room-over-room exhibits carry a visibility cost.
    room_over_room: bool = False
    #: Region-id prefix the exhibit's own sectors carry, for the self-read.
    #: Defaults to the label, lowercased with spaces as underscores.
    prefix: str = ""
    #: Habitat dressing this stall had to hand-compose because no constructor
    #: owns it yet. The owner's rule: a habitat is itself a claim about
    #: correct usage, so where one is assembled by hand rather than by an
    #: owning constructor, that is a promotion candidate and is named here.
    hand_composed: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        allowed = set("ABCDEFGHIJKLMNOPQRSTUVWXYZ ")
        bad = sorted(set(self.label) - allowed)
        if bad:
            raise ValueError(
                f"label {self.label!r} has characters the sign alphabet cannot "
                f"draw: {bad}. A-Z and space only.")
        if self.build is None and not self.blocker:
            raise ValueError(
                f"exhibit {self.label!r} builds nothing and gives no blocker; "
                "an empty stall has to say what is missing")
        if self.build is None and not self.expect.is_empty():
            raise ValueError(
                f"exhibit {self.label!r} is empty but claims something for the "
                "self-read to find")

    def is_empty(self) -> bool:
        return self.build is None

    def region_prefix(self) -> str:
        return self.prefix or self.label.lower().replace(" ", "_")


def exhibits() -> list[Exhibit]:
    """The v2 zoo, in tour order."""
    import stalls

    #: Owner-anchor material families. A stall wears the family of the thing
    #: it shows, not one gallery skin.
    STONE = (400, 294, 285)
    BRICK = (90, 294, 285)
    TIMBER = (156, 294, 285)
    SEWER = (496, 294, 285)
    STREET = (1097, 756, 3491)
    PARK = (400, 361, 3491)
    CRATE = (452, 294, 285)

    return [
        # -- the z-motion door family, each with a distinct interaction ----
        Exhibit(
            label="PUSH DOOR",
            about="a z-motion door opened by pushing its own wall",
            try_this="press use on the door face; it should rise",
            provenance="doors.z_motion_door(interaction='direct'), which sets "
                       "the busy times a bare endpoints dict leaves at zero",
            covers=("bloodmap.doors.z_motion_door",
                    "bloodmap.doors.xsector_direct_use"),
            build=stalls.push_door, skin=STONE,
            expect=Expect(sector_type=600, trigger="push",
                          reads_as="changes what fits through")),
        Exhibit(
            label="SWITCHED DOOR",
            about="the same motion, worked from a switch across the room",
            try_this="press the switch on the side wall, not the door",
            provenance="doors.z_motion_door(interaction='remote'); "
                       "reports/blood-effects-switches.md",
            covers=("bloodmap.doors.xsector_remote_rx",),
            build=stalls.switched_door, skin=BRICK,
            expect=Expect(sector_type=600, trigger="switch", rx_id=300,
                          reads_as="changes what fits through")),
        Exhibit(
            label="KEYED DOOR",
            about="a door that wants the moon key, which lies in the room",
            try_this="try the door, then take the key and try again",
            provenance="doors.z_motion_door(key=6); E1M4 sector 295 wears the "
                       "moon emblem; knowledge/blood/design/keys-v1.json",
            build=stalls.keyed_door, skin=STONE,
            expect=Expect(sector_type=600, requires_key=6,
                          reads_as="changes what fits through")),
        Exhibit(
            label="LIFT",
            about="a floor that carries a body between two standing levels",
            try_this="ride it up, step off, and look back down",
            provenance="reports/blood-effects-motion.md; E1M3 sector 241, "
                       "whose floor endpoints are exactly its neighbours'",
            build=stalls.lift, skin=STONE,
            #: Two storeys: a lift that fits under a median ceiling is not a
            #: lift, it is a step.
            clear=2 * MEDIAN_CLEAR, size=(5120, 7168),
            prefix="lift",
            hand_composed=(
                          "the mechanism itself: a floor-travelling z-motion, because doors.z_motion_door writes ceiling endpoints only",
                          "the upper room that makes the ride worth taking: material, light and two props placed by hand",),
            expect=Expect(sector_type=600,
                          reads_as="carries a body between levels")),
        Exhibit(
            label="CRACK BARRIER",
            about="a wall that opens once, when shot, and never closes again",
            try_this="shoot the crack; what it opens stays open",
            provenance="reports/blood-conditional-topology.md; E1M4 sprite 373 "
                       "on channel 119, listeners flush at rest",
            build=stalls.crack_barrier, skin=BRICK,
            prefix="crack",
            hand_composed=(
                          "the load-bearing wall the breach interrupts is plain masonry; no constructor owns a damaged-wall habitat",),
            expect=Expect(sector_type=600, trigger="shot", irreversible=True,
                          rx_id=301)),

        # -- the rotating family ------------------------------------------
        Exhibit(
            label="TURNSTILE PAIR",
            about="two counter-rotating four-vane rotors at E1M4's spin rate",
            try_this="WALK THROUGH IT. this settles the parked passage question",
            provenance="mechanism.turnstile_pair; reports/blood-rotating-doors.md; "
                       "passage unproven -- reports/blood-passage-oracle.md",
            covers=("bloodmap.mechanism.turnstile_pair",),
            build=stalls.turnstile_pair_stall, skin=STONE,
            clear=MEDIAN_CLEAR, size=(7168, 6144),
            prefix="turnstile_pair",
            hand_composed=(
                          "a public forecourt for the pair to flank, as E1M4's carnival entry does",),
            expect=Expect(sector_type=615, rx_id=7, count=2)),
        Exhibit(
            label="TURNSTILE SAME WAY",
            about="the DNE3L6 variant: both rotors turning the same way",
            try_this="walk through and compare with the pair next door",
            provenance="mechanism.turnstile_pair(counter_rotating=False); "
                       "DNE3L6 sectors 3 and 11",
            covers=("bloodmap.mechanism.turnstile",),
            build=stalls.turnstile_same_way, skin=STONE,
            clear=MEDIAN_CLEAR, size=(7168, 6144),
            prefix="turnstile_same",
            expect=Expect(sector_type=615, rx_id=7, count=2)),
        Exhibit(
            label="SLIDING GATE",
            about="two leaves that part along their own line into the jambs",
            try_this="press it and watch where the leaves go",
            provenance="mechanism.sliding_gate, built to the campaign template",
            covers=("bloodmap.mechanism.sliding_gate",),
            build=stalls.sliding_gate_stall, skin=STONE,
            prefix="sliding_gate",
            hand_composed=(
                          "the yard the gate closes off: a plain stone room, "
                          "not a courtyard with anything in it",),
            expect=Expect(sector_type=614)),

        # -- owner-attested E1M1 blueprints --------------------------------
        Exhibit(
            label="CASKET",
            about="the player start as a mechanism: a lid that lifts",
            try_this="look up, then walk out; E1M1 opens inside one of these",
            provenance="owner-attested E1M1 reading, sectors 30 and 28. The "
                       "full casket is slide, stack link and z at once; this "
                       "is its z half, which is as far as one constructor goes",
            build=stalls.casket, skin=STONE, clear=MEDIAN_CLEAR,
            room_over_room=True,
            prefix="casket",
            expect=Expect(sector_type=600)),
        Exhibit(
            label="CURTAIN",
            about="a slide used as furnishing, not as a way through",
            try_this="open it; nothing behind it was ever closed off",
            provenance="owner-attested E1M1 reading, sector 125; the leaves "
                       "wear owner anchor 146, curtain texture, graded strong",
            build=stalls.curtain, skin=TIMBER,
            prefix="curtain",
            hand_composed=(
                          "a proscenium for the curtain to hang in, "
                          "hand-composed as a framed opening",
                          "the curtain MECHANISM: this is a two-leaf slide "
                          "wearing tile 146. The owner's anchor note says a "
                          "Blood curtain is a thin sector whose WIDTH "
                          "changes, deforming the texture as it opens, and "
                          "no constructor builds one",),
            expect=Expect(sector_type=614)),
        Exhibit(
            label="SHELF SECRET",
            about="a shelf that slides aside and is the way into a secret",
            try_this="find what opens it, then step behind the shelf",
            provenance="owner-attested E1M1 reading, sector 70; the secret "
                       "sector transmits on channel 2, kChannelSecretFound",
            build=stalls.shelf_secret, skin=TIMBER,
            prefix="shelf_secret",
            expect=Expect(sector_type=614, rx_id=304)),

        # -- apertures and frontage ---------------------------------------
        Exhibit(
            label="FACADE",
            about="a street frontage with its bays, reveal and lettered sign",
            try_this="stand back across the street and read the sign",
            provenance="aperture.facade_run; reports/blood-facade-build.md",
            covers=("bloodmap.aperture.facade_run",),
            build=stalls.facade, skin=STREET,
            #: Street scale, and room to stand back: a frontage you cannot
            #: step away from is a wall.
            clear=3 * MEDIAN_CLEAR // 2, size=(9216, 8192),
            expect=Expect()),
        Exhibit(
            label="DRESSED DOORWAY",
            about="an opening wearing its jamb rail and threshold",
            try_this="look down at the threshold and up along the jambs",
            provenance="aperture.framed_door; owner anchors 195 (metal rail) "
                       "and 200 (riveted threshold)",
            covers=("bloodmap.aperture.framed_door",),
            build=stalls.dressed_doorway, skin=STONE,
            size=(5120, 6144),
            prefix="dressed",
            expect=Expect(sector_type=600, trigger="push")),

        # -- assemblies, as volumes and textures rather than sprites -------
        Exhibit(
            label="CRATE STACK",
            about="crates as what they are: sector volumes wearing crate art",
            try_this="walk round them and climb one; they are geometry",
            provenance="templates.SMALL_CRATE and LARGE_CRATE -- 452 at a "
                       "1024 module, 95 at 2048. v1 made these sprites. "
                       "459 is a moss-grown rock, not a crate",
            build=stalls.crate_stack, skin=CRATE,
            prefix="crate",
            hand_composed=(
                          "a stockroom around the crates",),
            expect=Expect()),
        Exhibit(
            label="SHELF RUN",
            about="a shelf as a shallow sector wearing the shelf texture",
            try_this="look along it; the depth is geometry, not a sprite",
            provenance="owner anchor 2026 (wall shelf, strong binding); the "
                       "E6M1 shop kit. v1 hung this on a wall as one sprite",
            build=stalls.shelf_run, skin=TIMBER,
            prefix="shelf",
            hand_composed=(
                          "a shop room around the shelf run",),
            expect=Expect()),
        Exhibit(
            label="PARK CORNER",
            about="grass and dirt with trees standing on the ground",
            try_this="check the trees meet the grass and do not float",
            provenance="furniture.furnish, which knows each tile's campaign "
                       "height; owner anchors 361 (grass, strong) and 270",
            build=stalls.park_corner, skin=PARK,
            clear=2 * MEDIAN_CLEAR, size=(6144, 6144),
            prefix="park",
            hand_composed=(
                          "outdoor ground cover beyond one grass and one dirt sector",),
            expect=Expect()),
        Exhibit(
            label="COUNTER",
            about="a shop counter, to the campaign's own five-clause rule",
            try_this="try to reach the working side from the front; the "
                     "clearance is measured, not decorative",
            provenance="reports/blood-assembly-counters.json, 384 mined "
                       "bundles: waist-band rise 4096-8192, aspect >= 2, "
                       "props on top, one host neighbour, asymmetric access. "
                       "E1M1 sector 80 is the worked example",
            build=stalls.counter, skin=TIMBER,
            size=(5 * 1024, 6 * 1024),
            prefix="counter",
            hand_composed=(
                          "the shop around the counter: shelf-tiled walls and "
                          "three props, assembled here rather than by a "
                          "constructor that owns shops",)),
        Exhibit(
            label="SEWER WALL",
            about="the sewer kit as a wet service passage you duck along",
            try_this="follow the pipe run and find the seam where the "
                     "technical door face starts it",
            provenance="reports/anchor-sewer-kit.json, mined by role: pipe "
                       "walls 496-499, door 500, light 501, grate 502",
            build=stalls.sewer_wall, skin=SEWER,
            size=(5 * 1024, 8 * 1024),
            prefix="sewer",
            hand_composed=(
                          "the passage itself: four pipe sectors chained by "
                          "hand, because no constructor owns a service run",)),
        Exhibit(
            label="TILE MUSEUM",
            about="the owner's strong-binding tiles, each on its own panel",
            try_this="read the panels and correct any tile that is wrong",
            provenance="knowledge/blood/design/owner-anchors-v1.json, the 15 "
                       "tiles graded strong",
            build=stalls.tile_museum, skin=STONE, size=(7168, 4096),
            prefix="museum",
            hand_composed=(
                          "panel bays with their own lighting",),
            expect=Expect()),

        # -- honest gaps ---------------------------------------------------
        Exhibit(
            label="SPRITE BRIDGE",
            about="composing solid flat sprites into a walkable volume",
            try_this="nothing yet; this stall is the gap itself",
            provenance="owner-named gap, 2026-09-01: the sprite-bridge "
                       "technique has no constructor in the repository",
            build=None,
            blocker="NO CONSTRUCTOR OWNS THIS YET",
            skin=STONE),
        Exhibit(
            label="STACK LINK",
            about="room over room: two floors standing in one place",
            try_this="nothing yet; see the casket for the other ROR exhibit",
            provenance="reachability.link_pairs; the owner's ROR visibility "
                       "budget -- two volumes must not be in view at once",
            build=None,
            blocker="NEEDS A SECOND ROR VOLUME",
            skin=STONE, room_over_room=True, size=(6144, 5120)),
    ]


#: Public constructors with no stall, and why. The conformance test reads
#: this, so a skip is a decision on the record rather than an omission.
SKIP: dict[str, str] = {
    "bloodmap.mechanism.turnstile_spec":
        "the pure-facts function behind turnstile; the stall exercises the "
        "constructor that consumes it",
    "bloodmap.mechanism.leaf_repeat_for":
        "a sizing helper, not a thing to stand in front of",
    "bloodmap.mechanism.blade_offset":
        "a sizing helper, not a thing to stand in front of",
    "bloodmap.vocabulary.sprite_repeats":
        "a sizing helper: turns a wanted height into repeats",
    "bloodmap.vocabulary.art_sizes_from_directory":
        "reads the ART files; nothing to exhibit",
    "bloodmap.vocabulary.arc_points":
        "geometry helper used by the exhibits that need an arc",
    "bloodmap.vocabulary.arc_through":
        "geometry helper: an arc through three points",
    "bloodmap.vocabulary.arc_turn_degrees":
        "geometry helper: the turn one arc segment makes",
    "bloodmap.vocabulary.outline":
        "geometry helper: joins point runs into one loop",
    "bloodmap.vocabulary.vocabulary_manifest":
        "reports what the vocabulary offers; not a built thing",
    "bloodmap.vocabulary.stamp_angle":
        "a helper: turns degrees into a Build angle",
    "bloodmap.vocabulary.stamp_alignment":
        "a helper: works out a surface's alignment bits",
    "bloodmap.vocabulary.stamp":
        "places a prefab; every stall that needs one uses it",
    "bloodmap.vocabulary.staircase":
        "PENDING: deserves a stall of its own in v3",
    "bloodmap.vocabulary.recess":
        "PENDING: deserves a stall of its own in v3",
    "bloodmap.doors.z_motion_endpoints":
        "the endpoints half of z_motion_door, which every door stall uses",
    "bloodmap.doors.observe_motion_sector":
        "a reading of an existing map, and the one the self-read gate uses",
    "bloodmap.doors.mine_map":
        "mining, not construction",
    "bloodmap.doors.mine_directory":
        "mining, not construction",
    "bloodmap.doors.query_door_precedents":
        "a query over mined doors",
    "bloodmap.doors.mine_key_signifiers":
        "mining, not construction",
    "bloodmap.doors.mine_scenic_candidates":
        "mining, not construction",
    "bloodmap.doors.authored_gate_audit":
        "a validator over a compiled layout",
    "bloodmap.doors.gate_audit_markdown":
        "formats the validator's output for a reader",
    "bloodmap.doors.door_affordance_report":
        "reports what a compiled layout's doors afford; a reading over a "
        "built map rather than something to stand in front of",
    "bloodmap.aperture.facade_of":
        "reads a facade off an existing map; a reading, not a constructor",
    "bloodmap.aperture.audit":
        "checks an authored aperture; a validator, not a built thing",
    "bloodmap.aperture.tile_span_z":
        "a helper: how much z one tile repeat covers",
    "bloodmap.aperture.snap_leaf":
        "a helper: rounds a leaf to whole tile repeats",
    "bloodmap.aperture.pierce":
        "the raw opening cut; DRESSED DOORWAY shows it dressed, which is the "
        "form the campaign actually builds",
    "bloodmap.aperture.frame_z_doors":
        "frames a whole map's z-doors at once; a pass over a layout rather "
        "than one exhibit",
}
