"""The Pattern Zoo's registry: sections, and the exhibits that live in them.

v3. Two owner rejections are built into this file's shape.

**The first (v1) was that nothing worked.** Stalls hand-assembled XSECTOR
dictionaries and never set the sector *type*, so the map held zero type-600
sectors and every door was inert. The only live machinery was the rotors,
because `mechanism.turnstile` sets its own type. Hence: **every exhibit is
built by the code that owns its concept**, or it is an honest EMPTY exhibit
with the gap lettered on its wall -- never a hand-rolled imitation.

**The second (v2) was that a corridor of cells is not a gallery.** A
mechanism shown in a generic box says nothing about how it is used. Hence
this file's structure: a **section** is one environment -- a shop, a street,
a sewer -- holding several exhibits that belong together in it, and the
section is the habitat claim. The SHOP section is E6M1's shop re-expressed
through our own constructors, which is also what functional zoning looks
like.

Three further things this file is answerable for.

**The representation taxonomy is binding.** Every concept is realized at its
own level: a standalone sprite (mannequin), a sector volume (crate, counter),
a wall texture on shallow sectors (shelf), a maskwall panel (grate), a thin
deforming sector (curtain). A concept realized at the wrong level is a build
failure, not a style choice, and `selfread.py` fails the build for it.

**Every exhibit is lettered, and the letters have to fit.** `min_bay()`
widens an exhibit whose bay is too narrow for its own name at sign size,
because a clipped label is how an exhibit loses the identity that owner
feedback arrives by.

**The zoo reads itself.** Every entry carries `expect` -- what
`bloodmap.effects` and `bloodmap.conditional` must find in the built map for
the claim on the wall to be true. Renders and a load smoke both passed on a
dead map; only reading the map back catches that.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable

#: Campaign median clear height, `norms-v1.json` `shape.median_height`:
#: 33280 units, 1.96 player heights.
MEDIAN_CLEAR = 33280
PLAYER_HEIGHT = 16960

#: Sign size for an exhibit label, and the pier of wall between two bays.
LABEL_SIZE = 48
PIER = 768


def min_bay(label: str, size: int = LABEL_SIZE) -> int:
    """The narrowest bay whose wall can carry this label unclipped.

    `lettering` refuses a word longer than its wall, which is the right
    behaviour and a build-time crash. This turns it into a registry-time
    fact, so an exhibit is sized for its own name instead of someone
    discovering at build time that a rename no longer fits.
    """
    from bloodmap.lettering import drawn_width, text_width

    return int(text_width(label, size) + drawn_width(size)) + 512


@dataclass(frozen=True)
class Expect:
    """What the understanding stack must find for the label to be true.

    Checked against the *built map* by `selfread.py`, not against the source
    that built it. That is the whole point: v1's source looked like doors.
    """

    #: The sector type the exhibit's mechanism must carry, if any.
    sector_type: int | None = None
    #: A trigger kind `conditional.route_edges` must report among its causes.
    trigger: str = ""
    #: What `effects.design_object` must read the mechanism as.
    reads_as: str = ""
    #: The route must require this key number.
    requires_key: int = 0
    #: The route must be one-way.
    irreversible: bool = False
    #: The mechanism must listen on this channel.
    rx_id: int | None = None
    #: At least this many sectors of `sector_type` in the exhibit's group.
    count: int = 1
    #: The exhibit must build a room-over-room link (a stack marker pair).
    stack_link: bool = False
    #: Tiles that must appear as WALL textures rather than as sprites: the
    #: representation taxonomy, made checkable.
    wall_tiles: tuple[int, ...] = ()
    #: Tiles that must appear as sprites rather than as surfaces.
    sprite_tiles: tuple[int, ...] = ()

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
        if self.stack_link:
            parts.append("stack-linked across a room-over-room plane")
        if self.wall_tiles:
            parts.append("tiles " + "/".join(str(t) for t in self.wall_tiles)
                         + " worn as wall texture, not thrown as sprites")
        if self.sprite_tiles:
            parts.append("tiles " + "/".join(str(t) for t in self.sprite_tiles)
                         + " placed as sprites")
        return ", ".join(parts)

    def is_empty(self) -> bool:
        return (self.sector_type is None and not self.trigger
                and not self.reads_as and not self.requires_key
                and not self.irreversible and self.rx_id is None
                and not self.stack_link and not self.wall_tiles
                and not self.sprite_tiles)


@dataclass(frozen=True)
class Exhibit:
    """One labelled thing, standing in a bay of its section."""

    label: str
    about: str
    try_this: str
    provenance: str
    #: Dotted names of the public constructors this exhibit stands for.
    covers: tuple[str, ...] = ()
    #: `(layout, section_id, bay, back, floor_z, ceiling_z, skin) -> None`.
    #: `None` makes an honest EMPTY exhibit, which must give a blocker.
    build: Callable[..., Any] | None = None
    #: What is missing, lettered on the wall where the exhibit would stand.
    blocker: str = ""
    #: Frontage along the section wall. The exhibit may open all of it.
    bay: int = 3072
    #: How far this exhibit's own sub-rooms run behind the section wall.
    depth: int = 5120
    expect: Expect = field(default_factory=Expect)
    room_over_room: bool = False
    #: Region-id prefix the exhibit's own sectors carry, for the self-read.
    prefix: str = ""
    #: Habitat dressing hand-composed because no constructor owns it yet.
    #: The promotion audit that follows this zoo runs on this list.
    hand_composed: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        allowed = set("ABCDEFGHIJKLMNOPQRSTUVWXYZ ")
        bad = sorted(set(self.label) - allowed)
        if bad:
            raise ValueError(
                f"label {self.label!r} has characters the sign alphabet "
                f"cannot draw: {bad}. A-Z and space only.")
        if self.build is None and not self.blocker:
            raise ValueError(
                f"exhibit {self.label!r} builds nothing and gives no blocker; "
                "an empty exhibit has to say what is missing")
        if self.build is None and not self.expect.is_empty():
            raise ValueError(
                f"exhibit {self.label!r} is empty but claims something for "
                "the self-read to find")


    def is_empty(self) -> bool:
        return self.build is None

    def pier(self) -> int:
        """The solid wall beside this bay that carries its label.

        The label cannot go on the bay's own wall: an exhibit is entitled to
        open all of it -- a doorway, a park, a facade -- and a sprite hung
        across an opening is refused, correctly. A pier is solid by
        construction, so it is sized to whichever word it has to carry.
        """
        #: A whole unit wider than the word, so the label can be justified
        #: hard against the bay it names. Centred on a tight pier it reads as
        #: belonging to either neighbour, which is exactly the ambiguity a
        #: stable identity cannot afford.
        return max(PIER, min_bay(self.label),
                   min_bay(self.blocker) if self.blocker else 0) + 1024

    def region_prefix(self) -> str:
        return self.prefix or self.label.lower().replace(" ", "_")


@dataclass(frozen=True)
class Section:
    """One environment, holding the exhibits that belong in it.

    The habitat rule at room scale. A section is not a container for
    unrelated things: it is a claim that these exhibits go together, in a
    place that looks like where the campaign puts them.
    """

    label: str
    about: str
    #: Wall / floor / ceiling tiles for the environment itself.
    skin: tuple[int, int, int]
    exhibits: tuple[Exhibit, ...]
    clear: int = MEDIAN_CLEAR
    #: Outdoors: the ceiling is sky, and the tile rules for it do not apply.
    outdoor: bool = False
    #: How much room to stand back in, in front of the bays.
    standing: int = 5 * 1024
    hand_composed: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        allowed = set("ABCDEFGHIJKLMNOPQRSTUVWXYZ ")
        bad = sorted(set(self.label) - allowed)
        if bad:
            raise ValueError(f"section label {self.label!r}: {bad}")
        if not self.exhibits:
            raise ValueError(f"section {self.label!r} holds no exhibits")

    def region_prefix(self) -> str:
        return self.label.lower().replace(" ", "_")

    def frontage(self) -> int:
        """How much wall the section needs for its bays and their piers."""
        return (sum(item.bay + item.pier() for item in self.exhibits)
                + PIER)


#: Owner-anchor material families. Nothing here is a gallery skin: each is
#: the family of the place it builds.
STONE = (400, 294, 285)
BRICK = (90, 294, 285)
TIMBER = (156, 294, 285)
SEWER_SKIN = (496, 294, 285)
STREET_SKIN = (1097, 294, 285)
PARK_SKIN = (400, 361, 285)
SHOP_SKIN = (202, 294, 285)


def sections() -> list[Section]:
    """The zoo, in walk order."""
    import stalls

    return [
        # ------------------------------------------------------------------
        Section(
            label="DOORS AND MECHANISMS",
            about="the gallery: the z-motion door family, a lift, a shot-open "
                  "breach, and the E1M1 blueprints the owner attested",
            skin=STONE, clear=MEDIAN_CLEAR,
            hand_composed=(
                "the gallery hall itself: a plain ashlar room, because no "
                "constructor owns a gallery",),
            exhibits=(
                Exhibit(
                    label="PUSH DOOR",
                    about="a z-motion door used from the room outside it",
                    try_this="press use on the door face; it should rise",
                    provenance="doors.z_motion_door(interaction='direct'). It "
                               "sets Push AND Wallpush together and says why: "
                               "a shut z-door has zero height, so the player "
                               "stands in the hall and Wallpush is what fires",
                    covers=("bloodmap.doors.z_motion_door",
                            "bloodmap.doors.xsector_direct_use"),
                    build=stalls.push_door, prefix="push_door",
                    expect=Expect(sector_type=600, trigger="push",
                                  reads_as="changes what fits through")),
                Exhibit(
                    label="SWITCHED DOOR",
                    about="the same motion, worked from a switch across the "
                          "room",
                    try_this="press the switch on the side wall, not the door",
                    provenance="doors.z_motion_door(interaction='remote') and "
                               "xsector_remote_rx; reports/"
                               "blood-effects-switches.md",
                    covers=("bloodmap.doors.xsector_remote_rx",),
                    build=stalls.switched_door, prefix="switched_door",
                    expect=Expect(sector_type=600, trigger="switch",
                                  rx_id=300,
                                  reads_as="changes what fits through")),
                Exhibit(
                    label="KEYED DOOR",
                    about="a door that wants the moon key, which lies in the "
                          "room",
                    try_this="try the door, then take the key and try again",
                    provenance="doors.z_motion_door(key=6); E1M4 sector 295 "
                               "wears the moon emblem; knowledge/blood/design/"
                               "keys-v1.json",
                    build=stalls.keyed_door, prefix="keyed_door",
                    expect=Expect(sector_type=600, requires_key=6,
                                  reads_as="changes what fits through")),
                Exhibit(
                    label="LIFT",
                    about="a floor that carries a body between two storeys, "
                          "with a landing worth arriving at",
                    try_this="ride it up, step off, and look back down",
                    provenance="reports/blood-effects-motion.md; E1M3 sector "
                               "241, whose floor endpoints are exactly its "
                               "neighbours'",
                    build=stalls.lift, prefix="lift", depth=8 * 1024,
                    hand_composed=(
                        "the mechanism itself: a floor-travelling z-motion. "
                        "doors.z_motion_door writes CEILING endpoints only, "
                        "so no constructor owns a lift",
                        "the upper room that makes the ride worth taking",),
                    expect=Expect(sector_type=600,
                                  reads_as="carries a body between levels")),
                Exhibit(
                    label="CRACK BARRIER",
                    about="a breach in a load-bearing wall, opened once by "
                          "shooting it",
                    try_this="shoot the crack; it opens once and stays open",
                    provenance="E1M4 sectors 276 and 277, flush at rest; "
                               "kThingWallCrack transmits once",
                    build=stalls.crack_barrier, prefix="crack",
                    hand_composed=(
                        "the load-bearing wall the breach interrupts is plain "
                        "masonry; no constructor owns a damaged-wall habitat",),
                    expect=Expect(sector_type=600, trigger="shot",
                                  irreversible=True, rx_id=301)),
                Exhibit(
                    label="CASKET",
                    about="the player start as a mechanism: a lid that slides "
                          "aside across a room-over-room plane",
                    try_this="look up, then walk out; E1M1 opens inside one",
                    provenance="owner-attested E1M1 reading, sectors 28/30 "
                               "(hole, slide-marked, ROR-linked) and 27/29 "
                               "(cover). Each slide sector moves exactly ONE "
                               "flagged wall, and that wall is the hole/cover "
                               "boundary",
                    build=stalls.casket, prefix="casket", room_over_room=True,
                    depth=6 * 1024,
                    hand_composed=(
                        "boundary-wall area re-partition: the lid works by a "
                        "flagged wall moving the line between hole and cover, "
                        "and no constructor expresses that",),
                    expect=Expect(sector_type=614, stack_link=True)),
                Exhibit(
                    label="DOUBLE SLIDE DOOR",
                    about="one sector, two leaves parting along their own line",
                    try_this="push it and watch where the leaves go",
                    provenance="owner-attested E1M1 sector 4; mechanism."
                               "sliding_gate built to the campaign template",
                    covers=("bloodmap.mechanism.sliding_gate",),
                    build=stalls.double_slide_door, prefix="double_slide",
                    expect=Expect(sector_type=614)),
                Exhibit(
                    label="PLAIN SLIDE DOOR",
                    about="a single leaf sliding aside, the load-bearing kind",
                    try_this="open it and step through; nothing is dressed up",
                    provenance="owner-attested E1M1 sector 63. Its two portals "
                               "are 512 apart on the SAME side, which is why "
                               "the cheap blocking test almost never fires",
                    build=stalls.plain_slide_door, prefix="plain_slide",
                    expect=Expect(sector_type=614)),
                Exhibit(
                    label="DOUBLE ROTATING DOOR",
                    about="two rotating leaves chained on one channel",
                    try_this="work one leaf; the other answers on the chain",
                    provenance="owner-attested E1M1 sectors 50 and 51: s50 "
                               "transmits to s51, which is a sentence in the "
                               "control-bus grammar, not two doors",
                    covers=("bloodmap.mechanism.turnstile",),
                    build=stalls.double_rotating_door, prefix="rotating_door",
                    bay=5 * 1024, depth=6 * 1024,
                    expect=Expect(sector_type=615, count=2)),
                Exhibit(
                    label="SHELF SECRET",
                    about="a shelf that slides aside and is the way into a "
                          "secret",
                    try_this="find what opens it, then step behind the shelf",
                    provenance="owner-attested E1M1 sector 70; the secret "
                               "sector transmits on channel 2, "
                               "kChannelSecretFound",
                    build=stalls.shelf_secret, prefix="shelf_secret",
                    bay=5 * 1024, depth=6 * 1024,
                    expect=Expect(sector_type=614, rx_id=304)),
                Exhibit(
                    label="CURTAIN",
                    about="a thin sector whose WIDTH changes -- the texture "
                          "squashing IS the animation",
                    try_this="nothing yet: read the wall and tell us if the "
                             "description matches what you know",
                    provenance="owner anchor 146/147, binding strong, and the "
                               "owner's note with them: a Blood curtain is a "
                               "thin deforming sector, not a pair of leaves",
                    blocker="COMING SOON",
                    prefix="curtain",
                    hand_composed=(
                        "the whole mechanism: a thin sector that changes "
                        "width, deforming tile 146. Pre-decided item of the "
                        "promotion audit that runs after this zoo",),
                ),
            )),
        # ------------------------------------------------------------------
        Section(
            label="FURNITURE HALL",
            about="one hall of the furniture kinds the pipeline can place, "
                  "each seated the way that thing is actually mounted",
            skin=TIMBER, clear=int(2.4 * PLAYER_HEIGHT),
            hand_composed=(
                "the hall itself; and the table volumes, which are raised "
                "sectors assembled here because templates.py's table lives "
                "on the levelprog stack and cannot be called from a "
                "PlanarLayout",),
            exhibits=(
                Exhibit(
                    label="LIGHT FITTINGS",
                    about="the four light kinds, each on the surface it hangs "
                          "from",
                    try_this="look up: the chandelier and lantern hang, the "
                             "torch and sconce are on the wall",
                    provenance="furniture.py, whose mounting field is mined "
                               "from the campaign: a torch is drawn fullbright "
                               "in 89% of its 150 uses because it is on fire",
                    covers=("bloodmap.furniture.furnish",
                            "bloodmap.furniture.place",
                            "bloodmap.furniture.mounting_for"),
                    build=stalls.light_fittings, prefix="lights",
                    expect=Expect(sprite_tiles=(506, 510, 641, 1701))),
                Exhibit(
                    label="WALL FITTINGS",
                    about="plaque, plank and ceiling plate: mounted things "
                          "that are not lights",
                    try_this="the ceiling plate is floor-aligned and lies "
                             "flat; it cannot hang on a wall and furniture.py "
                             "refuses to try",
                    provenance="furniture.py mounting rules; the alignment "
                               "state is a property of the tile, not of the "
                               "caller",
                    build=stalls.wall_fittings, prefix="wall_fittings",
                    expect=Expect(sprite_tiles=(68, 795, 915))),
                Exhibit(
                    label="TABLES",
                    about="tables as raised sector volumes at the campaign "
                          "rise, not as sprites",
                    try_this="walk up to one: it is geometry, and you can "
                             "stand on it",
                    provenance="projects/blood-city/level/templates.py "
                               "TABLE_RISE = 0.30 player heights, TABLE_SIDE "
                               "1024",
                    build=stalls.tables, prefix="tables"),
                Exhibit(
                    label="GRAVEYARD",
                    about="the headstone and tomb set, seated on their own "
                          "campaign heights",
                    try_this="check nothing floats and nothing is buried",
                    provenance="furniture.py graveyard entries; every height "
                               "is the mined campaign median for that tile",
                    build=stalls.graveyard, prefix="graveyard",
                    expect=Expect(sprite_tiles=(701, 703, 704, 706))),
                Exhibit(
                    label="SPRITE BRIDGE",
                    about="composing flat sprites into a solid volume you can "
                          "walk across",
                    try_this="nothing yet: this is the technique we do not "
                             "have, lettered where it would stand",
                    provenance="owner-named gap. Flat floor-aligned sprites "
                               "composed into a walkable volume is a "
                               "technique the pipeline cannot express",
                    blocker="NO CONSTRUCTOR OWNS THIS YET",
                    prefix="sprite_bridge"),
            )),
        # ------------------------------------------------------------------
        Section(
            label="SHOP",
            about="E6M1's shop re-expressed through our constructors: "
                  "counter, shelf runs, crate stock and a display row",
            skin=SHOP_SKIN, clear=MEDIAN_CLEAR,
            hand_composed=(
                "the shop room itself: worn facade tile 202 on the walls, "
                "which is a material choice and not a constructor",),
            exhibits=(
                Exhibit(
                    label="REGISTER",
                    about="a counter with the working clearance behind it",
                    try_this="try to reach the working side from the front; "
                             "the clearance is measured, not decorative",
                    provenance="reports/blood-assembly-counters.json, 384 "
                               "mined bundles: waist-band rise 4096-8192, "
                               "aspect at least 2, props on top, asymmetric "
                               "access. E1M1 sector 80 is the worked example",
                    build=stalls.register, prefix="register", bay=4 * 1024),
                Exhibit(
                    label="SHELF RUNS",
                    about="shelves as WALL TEXTURE on shallow sectors, in the "
                          "three shop tiles",
                    try_this="a shelf is not a sprite: walk along and see "
                             "them as geometry",
                    provenance="owner anchors 2026 and 2635, both strong "
                               "binding, plus 202. E6M1's shop kit",
                    build=stalls.shelf_runs, prefix="shelf_runs",
                    bay=5 * 1024,
                    expect=Expect(wall_tiles=(2026, 2635))),
                Exhibit(
                    label="CRATE STACK",
                    about="crates as sector VOLUMES wearing the crate modules",
                    try_this="check these are crates, and that you can climb "
                             "the small ones",
                    provenance="projects/blood-city/level/templates.py "
                               "SMALL_CRATE (452, 1024 side, 16384 rise) and "
                               "LARGE_CRATE (95, 2048, 32768). 459 is a "
                               "moss-grown rock and a build once shipped it "
                               "as a crate",
                    build=stalls.crate_stack, prefix="crate", bay=6 * 1024,
                    depth=6 * 1024,
                    hand_composed=(
                        "the crate VOLUMES: the modules are imported from "
                        "templates.py, but its _crate_block builds on the "
                        "levelprog space stack, so the volumes themselves are "
                        "assembled here on PlanarLayout",
                        "a free-standing crate in the middle of the floor is "
                        "not expressible at all: PlanarLayout refuses a "
                        "region wholly inside another, so these stand against "
                        "a wall",),
                    expect=Expect(wall_tiles=(452, 95))),
                Exhibit(
                    label="DISPLAY ROW",
                    about="three mannequins, standing on the floor they are "
                          "seated to",
                    try_this="check they stand on the ground; in v1 they "
                             "floated",
                    provenance="owner anchor 2377, binding strong. Its height "
                               "is the one number here no campaign map backs: "
                               "the tile has no mined median",
                    build=stalls.display_row, prefix="display",
                    expect=Expect(sprite_tiles=(2377,))),
            )),
        # ------------------------------------------------------------------
        Section(
            label="STREET",
            about="outdoor scale under sky: the frontage at two widths and "
                  "the turnstiles that admit you to somewhere public",
            skin=STREET_SKIN, clear=int(4.0 * PLAYER_HEIGHT), outdoor=True,
            standing=8 * 1024,
            hand_composed=(
                "street anatomy: there is no kerb, no roadway and no gutter, "
                "because no constructor owns them and no owner anchor grades "
                "a road surface. The ground here is the gallery's own floor "
                "tile, which is the honest placeholder rather than a guess",),
            exhibits=(
                Exhibit(
                    label="FACADE NARROW",
                    about="a six-bay frontage with two openings and a sign",
                    try_this="stand back and read it; then compare it with "
                             "the wide one",
                    provenance="reports/blood-facade-build.md: one wall tile "
                               "across the run in 98% of 131 campaign "
                               "multi-opening facades; bay 1024; reveal 256",
                    covers=("bloodmap.aperture.facade_run",),
                    build=stalls.facade_narrow, prefix="facade_narrow",
                    bay=7 * 1024, depth=6 * 1024),
                Exhibit(
                    label="FACADE WIDE",
                    about="the same frontage at ten bays and three openings",
                    try_this="every relationship should survive the width "
                             "change; only the counts differ",
                    provenance="reports/blood-facade-build.md width "
                               "invariance: header, sill, reveal and sign seat "
                               "are shared datums across both widths",
                    build=stalls.facade_wide, prefix="facade_wide",
                    bay=11 * 1024, depth=6 * 1024),
                Exhibit(
                    label="TURNSTILE PAIR",
                    about="two counter-rotating drums flanking a public way in",
                    try_this="walk into it. Whether a body passes a turning "
                             "rotor is the pipeline's longest unproven claim",
                    provenance="reports/blood-turnstile-build.md; E1M4's "
                               "carnival entry at period 255, four blades on "
                               "tile 332, each spanning its rotor exactly",
                    covers=("bloodmap.mechanism.turnstile_pair",),
                    build=stalls.turnstile_pair_stall, prefix="turnstile_pair",
                    bay=7 * 1024, depth=7 * 1024,
                    expect=Expect(sector_type=615, count=2)),
                Exhibit(
                    label="TURNSTILE SAME WAY",
                    about="the same pair turning the same way, the DNE3L6 "
                          "variant",
                    try_this="compare the two: counter-rotating is E1M4's, "
                             "same-way is the community precedent",
                    provenance="reports/blood-turnstile-build.md; the "
                               "community variant is precedent, never "
                               "convention",
                    build=stalls.turnstile_same_way, prefix="turnstile_same",
                    bay=7 * 1024, depth=7 * 1024,
                    expect=Expect(sector_type=615, count=2)),
            )),
        # ------------------------------------------------------------------
        Section(
            label="SEWER AND TECH",
            about="a wet service passage: the sewer kit by the role each "
                  "tile was mined under",
            skin=SEWER_SKIN, clear=MEDIAN_CLEAR,
            exhibits=(
                Exhibit(
                    label="PIPE RUN",
                    about="a passage you duck along, four pipe tiles down it",
                    try_this="the clear height is deliberately below the "
                             "campaign median; that is what a service run is",
                    provenance="reports/anchor-sewer-kit.json, role "
                               "pipe_walls: tiles 496 to 499",
                    build=stalls.pipe_run, prefix="sewer", bay=4 * 1024,
                    depth=8 * 1024,
                    hand_composed=(
                        "the passage: four pipe sectors chained by hand, "
                        "because no constructor owns a service run",
                        "the sewer grate 502: it carries mask pixels, so by "
                        "the measured transparency law it cannot go on a "
                        "floor, and nothing here builds a maskwall panel",),
                    expect=Expect(wall_tiles=(496, 497, 498, 499))),
                Exhibit(
                    label="SEWER DOOR",
                    about="the technical door face, on a working z-motion door",
                    try_this="open it; the face is tile 500 and the mechanism "
                             "is the same one the stone doors use",
                    provenance="reports/anchor-sewer-kit.json role sewer_door: "
                               "tile 500. The mechanism is doors.z_motion_door",
                    build=stalls.sewer_door, prefix="sewer_door",
                    expect=Expect(sector_type=600, trigger="push")),
                Exhibit(
                    label="SLIDING GATE",
                    about="two leaves parting into the jambs, serving the "
                          "passage",
                    try_this="press it and watch where the leaves go; they "
                             "rest shut and are drawn open",
                    provenance="mechanism.sliding_gate. A gate is authored in "
                               "its OPEN pose and rests shut, which is what "
                               "both campaign two-leaf gates do",
                    build=stalls.sliding_gate_stall, prefix="sliding_gate",
                    bay=4 * 1024,
                    expect=Expect(sector_type=614, rx_id=302)),
            )),
        # ------------------------------------------------------------------
        Section(
            label="PARK",
            about="outdoors under sky: the ground vocabulary and the things "
                  "that grow in it",
            skin=PARK_SKIN, clear=int(4.0 * PLAYER_HEIGHT), outdoor=True,
            standing=6 * 1024,
            exhibits=(
                Exhibit(
                    label="GROUND",
                    about="grass and dirt, the two-tile ground vocabulary",
                    try_this="the seam between them is where a path would go",
                    provenance="owner anchor 361 (grass, strong: dominant "
                               "floor of E1M1's open-sky sectors, 35 of 66 "
                               "uses under sky) with 270 dirt",
                    build=stalls.ground, prefix="ground", bay=5 * 1024,
                    hand_composed=(
                        "ground cover beyond two sectors: no constructor owns "
                        "a path or a planted bed",),
                    expect=Expect(wall_tiles=(361, 270))),
                Exhibit(
                    label="TREES",
                    about="the four tree kinds, each at its own campaign "
                          "height",
                    try_this="an oak is 2.82 player heights and a pine is "
                             "not; check they differ",
                    provenance="furniture.py growing things; every height is "
                               "the mined campaign median for that tile",
                    build=stalls.trees, prefix="trees", bay=5 * 1024,
                    expect=Expect(sprite_tiles=(541, 542, 543, 547))),
                Exhibit(
                    label="STRAW",
                    about="a heap of straw, at the height the campaign draws "
                          "it",
                    try_this="0.97 player heights: a heap you walk round, "
                             "not a scatter underfoot",
                    provenance="tile 515, owner-named in the zoo "
                               "specification. Campaign median height 0.97; "
                               "the anchor file grades it untested, so the "
                               "name here is the owner's and not ours",
                    build=stalls.straw, prefix="straw",
                    expect=Expect(sprite_tiles=(515,))),
            )),
        # ------------------------------------------------------------------
        Section(
            label="TILE MUSEUM",
            about="a gallery wall of the owner's anchor tiles, each lettered "
                  "with the owner's own name for it",
            skin=STONE, clear=MEDIAN_CLEAR,
            hand_composed=(
                "the panel bays: shallow sectors wearing one tile each, with "
                "no lighting of their own",),
            exhibits=(
                Exhibit(
                    label="STRONG BINDING",
                    about="the tiles the owner graded strong: these may name "
                          "what they depict",
                    try_this="read the names and correct any that are wrong",
                    provenance="knowledge/blood/design/owner-anchors-v1.json, "
                               "binding strong. Weak and untested tiles never "
                               "name -- that rule is executable in "
                               "owner_anchors.may_name",
                    covers=("bloodmap.owner_anchors.load_owner_anchors",
                            "bloodmap.owner_anchors.owner_label"),
                    build=stalls.tile_museum, prefix="museum",
                    bay=12 * 1024, depth=3 * 1024),
            )),
    ]


def exhibits() -> list[Exhibit]:
    """Every exhibit, in walk order, flattened out of the sections."""
    return [item for section in sections() for item in section.exhibits]


def section_of(label: str) -> Section:
    """Which section an exhibit label stands in."""
    for section in sections():
        for item in section.exhibits:
            if item.label == label:
                return section
    raise KeyError(label)


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
    "bloodmap.aperture.framed_door":
        "the frame around an already-built z-door; DRESSED DOORWAY and every "
        "door in the gallery are framed at build time by the same grammar, "
        "through _framed_opening rather than after the fact",
    "bloodmap.furniture.campaign_heights":
        "reads the mined sprite-height medians; every furnished exhibit "
        "consumes it and nothing stands in front of it",
    "bloodmap.furniture.wet_only":
        "the set of tiles that belong under water; PIPE RUN uses it to pick "
        "what may stand in a wet passage",
    "bloodmap.furniture.dry_only":
        "the dry counterpart of wet_only; a query over the catalogue",
    "bloodmap.owner_anchors.parse_owner_anchors":
        "the parser behind load_owner_anchors, which TILE MUSEUM uses",
    "bloodmap.aperture.frame_z_doors":
        "frames a whole map's z-doors at once; a pass over a layout rather "
        "than one exhibit",
}
