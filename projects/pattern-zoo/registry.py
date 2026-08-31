"""The Pattern Zoo's exhibit registry.

Every pattern, mechanism and constructor the pipeline has learned stands here
as one entry. The map is **generated from this list** -- no geometry is placed
by hand anywhere in this project -- so the zoo stays current by the registry
staying current, and a conformance test fails when a public constructor has
neither an exhibit nor a written reason to be skipped.

Owner feedback arrives **by label**, so `label` is a stable identity, not a
caption. Changing one loses the thread of corrections attached to it.

Labels are drawn with `lettering.write_on_wall`, whose alphabet is A-Z and
space only. Keep them short: a stall wall is 4096 units and a size-64 letter
is about 93 wide.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable, Sequence

#: Everything a stall needs, and nothing about where it sits -- the generator
#: decides that.
Builder = Callable[..., None]


@dataclass(frozen=True)
class Exhibit:
    """One stall."""

    #: Stable identity. Owner corrections are filed against it, so treat a
    #: rename as retiring one exhibit and adding another.
    label: str
    #: What the visitor is looking at, in a sentence.
    about: str
    #: What the owner should do here. The whole point of a playable zoo.
    try_this: str
    #: Which report, phase or owner note this came from.
    provenance: str
    #: The constructor or template it demonstrates, by dotted name. Used by
    #: the conformance test to tell which public constructors are covered.
    covers: tuple[str, ...] = ()
    #: Builds the stall's contents. `None` means an EMPTY stall, and
    #: `blocker` then says why -- an honest gap is an exhibit too.
    build: Builder | None = None
    blocker: str = ""
    #: Room-over-room exhibits carry a visibility cost: two ROR volumes must
    #: not be in view at once. The generator keeps these apart.
    room_over_room: bool = False

    def __post_init__(self) -> None:
        if not self.label.strip():
            raise ValueError("an exhibit needs a label")
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

    def is_empty(self) -> bool:
        return self.build is None


def exhibits() -> list[Exhibit]:
    """The v1 zoo, in tour order."""
    import stalls

    return [
        # -- doors, the z-motion family ----------------------------------
        Exhibit(
            label="PUSH DOOR",
            about="a z-motion door opened by pushing its own wall",
            try_this="walk up to it and press use on the door face",
            provenance="doors.z_motion_door; reports/blood-door-families.md",
            covers=("bloodmap.doors.z_motion_door",
                    "bloodmap.doors.xsector_direct_use"),
            build=stalls.push_door),
        Exhibit(
            label="SWITCHED DOOR",
            about="the same door, worked from a switch across the stall",
            try_this="press the switch on the side wall, not the door",
            provenance="doors.xsector_remote_rx; reports/blood-effects-switches.md",
            covers=("bloodmap.doors.xsector_remote_rx",),
            build=stalls.switched_door),
        Exhibit(
            label="KEYED DOOR",
            about="a door with a key emblem; the key lies in the stall",
            try_this="try the door first, then take the key and try again",
            provenance="doors.KEY_TYPES + knowledge/blood/design/keys-v1.json; "
                       "E1M4 sector 295 wears the moon emblem",
            covers=("bloodmap.doors.z_motion_endpoints",),
            build=stalls.keyed_door),
        Exhibit(
            label="LIFT",
            about="a floor that carries a body between two standing levels",
            try_this="ride it up, then step off and look down",
            provenance="reports/blood-effects-motion.md; E1M3 sector 241",
            build=stalls.lift),
        Exhibit(
            label="CRACK BARRIER",
            about="a wall that opens once, when shot, and never closes",
            try_this="shoot the crack; the way behind it stays open",
            provenance="reports/blood-conditional-topology.md; "
                       "E1M4 sprite 373 on channel 119",
            build=stalls.crack_barrier),

        # -- the rotating-door family ------------------------------------
        Exhibit(
            label="TURNSTILE PAIR",
            about="two counter-rotating four-vane rotors, E1M4's spin rate",
            try_this="WALK THROUGH IT. this settles the parked passage question",
            provenance="mechanism.turnstile_pair; reports/blood-rotating-doors.md; "
                       "passage unproven -- reports/blood-passage-oracle.md",
            covers=("bloodmap.mechanism.turnstile_pair",),
            build=stalls.turnstile_pair_stall),
        Exhibit(
            label="TURNSTILE SAME WAY",
            about="the DNE3L6 variant: both rotors turning the same way",
            try_this="walk through and compare with the pair next door",
            provenance="reports/blood-rotating-doors.md; DNE3L6 sectors 3 and 11",
            covers=("bloodmap.mechanism.turnstile",),
            build=stalls.turnstile_same_way),
        Exhibit(
            label="SLIDING GATE",
            about="a gate that slides rather than turning",
            try_this="watch which way it goes and try to follow it",
            provenance="mechanism.sliding_gate",
            covers=("bloodmap.mechanism.sliding_gate",),
            build=stalls.sliding_gate_stall),

        # -- E1M1 blueprints, owner-attested -----------------------------
        Exhibit(
            label="CASKET",
            about="the player start as a mechanism: slide, stack link and z at once",
            try_this="look up, then walk out; this is E1M1's opening shot",
            provenance="owner-attested E1M1 reading, sectors 30 and 28, "
                       "stack link 10; roadmap Phase 8 note",
            room_over_room=True,
            build=stalls.casket),
        Exhibit(
            label="DOUBLE SLIDE DOOR",
            about="one sector carrying both leaves, parting in opposite directions",
            try_this="stand in the middle and watch both halves go",
            provenance="owner-attested E1M1 reading, sector 4",
            build=stalls.double_slide_door),
        Exhibit(
            label="DOUBLE ROTATE DOOR",
            about="two rotating leaves chained by channel, one firing the next",
            try_this="press once and watch the second leaf follow",
            provenance="owner-attested E1M1 reading, sectors 50 and 51 "
                       "(rx 105 -> tx 106 -> rx 106)",
            build=stalls.double_rotate_door),
        Exhibit(
            label="CURTAIN",
            about="a slide used as furnishing rather than as a way through",
            try_this="open it; nothing beyond it was closed off",
            provenance="owner-attested E1M1 reading, sector 125. Its tile has "
                       "no owner binding, which is why the dressing plane "
                       "cannot name it -- reports/blood-role-v2.md",
            build=stalls.curtain),
        Exhibit(
            label="SHELF SECRET",
            about="a shelf that slides aside and is a secret entrance",
            try_this="find what opens it, then look behind the shelf",
            provenance="owner-attested E1M1 reading, sector 70",
            build=stalls.shelf_secret),
        Exhibit(
            label="STACK LINK",
            about="room over room: two floors in one place",
            try_this="walk the lower floor, then the upper, and look down",
            provenance="reachability.link_pairs; owner note on the ROR "
                       "visibility budget -- two volumes must not be in view "
                       "at once",
            room_over_room=True,
            build=None,
            blocker="NEEDS A SECOND ROR VOLUME OUT OF SIGHT OF THE CASKET"),

        # -- apertures and facades ---------------------------------------
        Exhibit(
            label="FACADE NARROW",
            about="a street frontage at its narrow width, with its lettered sign",
            try_this="stand back in the corridor and read the sign",
            provenance="aperture.facade_run; reports/blood-facade-build.md",
            covers=("bloodmap.aperture.facade_run",),
            build=stalls.facade_narrow),
        Exhibit(
            label="FACADE WIDE",
            about="the same grammar at the wide width",
            try_this="compare the bay rhythm with the narrow one",
            provenance="aperture.facade_run; reports/blood-facade-grammar.md",
            build=stalls.facade_wide),
        Exhibit(
            label="DRESSED DOORWAY",
            about="a doorway wearing jamb rail and threshold",
            try_this="look down at the threshold and along the jambs",
            provenance="owner anchors 195 (metal rail) and 200 (threshold); "
                       "reports/blood-facade-grammar.md",
            build=stalls.dressed_doorway),

        # -- assemblies ---------------------------------------------------
        Exhibit(
            label="COUNTER",
            about="a counter with the working clearance behind it",
            try_this="try to stand behind the counter; the gap is measured",
            provenance="reports/blood-assembly-counters.json",
            build=stalls.counter),
        Exhibit(
            label="CRATE STACK",
            about="crates built from the owner's tiles: intact, broken, large",
            try_this="check these are crates and not mossy rocks",
            provenance="owner anchors 452 / 462 / 95; a build once shipped "
                       "tile 459, a moss-grown rock, as a crate",
            build=stalls.crate_stack),
        Exhibit(
            label="SHELF RUN",
            about="a run of wall shelves, the owner's strong-binding tile",
            try_this="look along the run; the tile is 2026",
            provenance="owner anchor 2026 (wall shelf, strong binding)",
            build=stalls.shelf_run),
        Exhibit(
            label="MANNEQUIN ROW",
            about="three mannequins in a display row",
            try_this="the tile binds its meaning almost always -- does it here",
            provenance="owner anchor 2377 (mannequin, strong binding); "
                       "reports/blood-contrast-shelf-vs-crate.json",
            build=stalls.mannequin_row),

        # -- materials ----------------------------------------------------
        Exhibit(
            label="PARK CORNER",
            about="grass and dirt with trees",
            try_this="walk the grass and look at where it meets the dirt",
            provenance="owner anchors 361 (grass, strong) and 270 (dirt); "
                       "furniture.py park vocabulary",
            build=stalls.park_corner),
        Exhibit(
            label="SEWER WALL",
            about="the sewer kit: pipe walls and a technical door",
            try_this="look for the seam between the pipe run and the door",
            provenance="reports/anchor-sewer-kit.json; owner anchors 496-502",
            build=stalls.sewer_wall),
        Exhibit(
            label="TILE MUSEUM",
            about="the owner's strong-binding tiles, each with its name",
            try_this="read the names and correct any that are wrong",
            provenance="knowledge/blood/design/owner-anchors-v1.json, "
                       "binding strong",
            build=stalls.tile_museum),
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
    "bloodmap.doors.z_motion_endpoints":
        "covered by KEYED DOOR, which builds its endpoints with it",
    "bloodmap.doors.observe_motion_sector":
        "a reading of an existing map, not a constructor",
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
    "bloodmap.vocabulary.stamp":
        "places a prefab; every stall that needs one uses it",
    "bloodmap.vocabulary.staircase":
        "PENDING: deserves a stall of its own in v2",
    "bloodmap.vocabulary.recess":
        "PENDING: deserves a stall of its own in v2",
    "bloodmap.aperture.facade_of":
        "reads a facade off an existing map; a reading, not a constructor",
    "bloodmap.aperture.audit":
        "checks an authored aperture; a validator, not a built thing",
    "bloodmap.aperture.tile_span_z":
        "a helper: how much z one tile repeat covers",
    "bloodmap.aperture.snap_leaf":
        "a helper: rounds a leaf to whole tile repeats",
    "bloodmap.aperture.pierce":
        "PENDING: the raw opening cut, shown dressed by DRESSED DOORWAY; "
        "deserves its own undressed stall in v2",
    "bloodmap.aperture.framed_door":
        "PENDING: a framed door needs a stall of its own in v2",
    "bloodmap.aperture.frame_z_doors":
        "PENDING: frames a whole map's z-doors at once; a pass over a "
        "layout rather than one exhibit",
}
