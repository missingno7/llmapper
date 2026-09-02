"""The rules themselves: claims about Blood, each with somewhere to check it.

Registered here rather than in `rules` so the machinery and the content stay
apart -- the registry has no opinions and this file is nothing but opinions,
every one of which is measured before it is allowed to have a severity.

Two kinds live side by side and the grading tells them apart:

* **engine laws**, where the source is a file and a symbol in the Build or Blood
  source and the campaign's violation rate should come out near zero;
* **corpus habits**, where the source is the corpus and the rate is the finding.

Nothing here decides which kind a rule is. `rules.grade` measures, and the rate
says.
"""

from __future__ import annotations

from math import hypot

from .rules import (
    Finding, Rule, Violation, _power_of_two, _wall_owners, art_sizes, register,
)

from .player_space import PLAYER_PROFILES

#: One standing human, from the player profile. Never hardcode this: it was
#: 0x1600 in a dozen modules, which is `POSTURE.eyeAboveZ` -- an offset from
#: the sprite's centre, not a body -- and every height in the project was
#: denominated in a unit 3x too small.
PLAYER_HEIGHT = PLAYER_PROFILES["blood"].standing_height
PLAYER_STEP = 4096

CSTAT_BLOCK = 1
CSTAT_TRANSLUCENT = 2
CSTAT_MASKED = 16
CSTAT_ALIGNMENT = 0x30
CSTAT_FLOOR_ALIGNED = 0x20
CSTAT_INVISIBLE = 0x8000

#: Below this a floor difference is a step the player takes without thinking.
STEPPABLE = 0.4 * PLAYER_HEIGHT


# ---------------------------------------------------------------------------
# surfaces
# ---------------------------------------------------------------------------

def _flat_tiles_are_power_of_two(disk) -> Finding:
    sizes = art_sizes()
    population = 0
    out = []
    for index, sector in enumerate(disk.sectors):
        fields = sector.fields
        for surface in ("floor", "ceiling"):
            if int(fields[f"{surface}_stat"]) & 1:
                continue                       # the sky is not sampled this way
            picnum = int(fields[f"{surface}_picnum"])
            size = sizes.get(picnum)
            if size is None:
                continue
            population += 1
            if not (_power_of_two(size[0]) and _power_of_two(size[1])):
                out.append(Violation(
                    f"sector[{index}].{surface}",
                    f"tile {picnum} is {size[0]}x{size[1]}"))
    return Finding(population, tuple(out))


register(Rule(
    id="flat-tile-power-of-two",
    statement="a floor or ceiling tile must have power-of-two sides",
    because=(
        "tileUpdatePicSiz rounds each dimension down to a power of two and the "
        "floor rasteriser masks its texture lookup with the result, so a 64x400 "
        "tile laid on a floor is sampled as 64x256 and the rest is never drawn"),
    source="NBlood/source/build/src/tiles.cpp:281 tileUpdatePicSiz",
    scope="sector",
    check=_flat_tiles_are_power_of_two,
))


def _masked_walls_are_not_faking_stone(disk) -> Finding:
    population = 0
    out = []
    for index, wall in enumerate(disk.walls):
        fields = wall.fields
        if not int(fields["cstat"]) & CSTAT_MASKED:
            continue
        population += 1
        if int(fields["over_picnum"]) == int(fields["picnum"]):
            out.append(Violation(f"wall[{index}]",
                                 f"wears its own tile {fields['picnum']}"))
    return Finding(population, tuple(out))


register(Rule(
    id="masked-wall-not-faking-stone",
    statement="a masked wall should be something you look through, not stone",
    because=(
        "copying a wall's picnum onto its over_picnum makes a two-sided wall "
        "look solid, which is a way of saying two regions must not connect "
        "without giving the wall between them any thickness"),
    source="corpus",
    scope="wall",
    check=_masked_walls_are_not_faking_stone,
))


def _blocked_walls_are_not_invisible_kerbs(disk) -> Finding:
    owner = _wall_owners(disk)
    population = 0
    out = []
    for index, wall in enumerate(disk.walls):
        fields = wall.fields
        other = int(fields["next_sector"])
        cstat = int(fields["cstat"])
        if other < 0 or not cstat & CSTAT_BLOCK:
            continue
        population += 1
        mine = owner.get(index)
        if mine is None:
            continue
        step = abs(int(disk.sectors[mine].fields["floor_z"])
                   - int(disk.sectors[other].fields["floor_z"]))
        if not cstat & CSTAT_MASKED and step < STEPPABLE:
            out.append(Violation(f"wall[{index}]",
                                 f"blocks a {step} step with nothing drawn on it"))
    return Finding(population, tuple(out))


register(Rule(
    id="blocked-wall-not-invisible-kerb",
    statement=(
        "a wall that blocks the player should either show why or stand at a "
        "drop they would not try to step"),
    because=(
        "the geometry says step and the wall says no. Blood's blocked two-sided "
        "walls sit at a median floor difference of 4.00 player heights and a q1 "
        "of 1.09, and a fifth of them are masked so you can see what stopped you"),
    source="corpus",
    scope="wall",
    check=_blocked_walls_are_not_invisible_kerbs,
))


# ---------------------------------------------------------------------------
# sprites
# ---------------------------------------------------------------------------

def _sprites_are_drawn_square(disk) -> Finding:
    population = 0
    out = []
    for index, sprite in enumerate(disk.sprites):
        fields = sprite.fields
        if int(fields["cstat"]) & CSTAT_INVISIBLE:
            continue
        x, y = int(fields["x_repeat"]), int(fields["y_repeat"])
        if y <= 0:
            continue
        population += 1
        if x != y:
            out.append(Violation(f"sprite[{index}]",
                                 f"repeat {x}/{y} on tile {fields['picnum']}"))
    return Finding(population, tuple(out))


register(Rule(
    id="sprite-drawn-square",
    statement="a sprite is normally drawn with equal repeats",
    because=(
        "x_repeat scales the tile's own width, so a tall narrow tile is already "
        "tall and narrow; scaling the axes differently squashes it twice"),
    source="corpus",
    scope="sprite",
    check=_sprites_are_drawn_square,
))


def _floor_aligned_sprites_rest_on_a_surface(disk) -> Finding:
    population = 0
    out = []
    for index, sprite in enumerate(disk.sprites):
        fields = sprite.fields
        cstat = int(fields["cstat"])
        if cstat & CSTAT_INVISIBLE or cstat & CSTAT_ALIGNMENT != CSTAT_FLOOR_ALIGNED:
            continue
        sector = int(fields["sector"])
        if not 0 <= sector < len(disk.sectors):
            continue
        population += 1
        plane = disk.sectors[sector].fields
        z = int(fields["z"])
        drift = min(abs(z - int(plane["floor_z"])), abs(z - int(plane["ceiling_z"])))
        if drift > 4096:
            out.append(Violation(f"sprite[{index}]",
                                 f"flat tile {fields['picnum']} floats {drift} "
                                 "from the nearest surface"))
    return Finding(population, tuple(out))


register(Rule(
    id="floor-aligned-sprite-rests-on-a-surface",
    statement="a flat sprite is a plate and lies on a floor or a ceiling",
    because=(
        "GetSpriteExtents skips the extent arithmetic for (cstat & 0x30) == "
        "0x20, so a floor-aligned sprite is a plane at its own z with no top to "
        "poke through a ceiling and no bottom to sink into a floor -- nothing "
        "that measures seating can see one hanging in the air"),
    source="NBlood/source/blood/src/db.h GetSpriteExtents",
    scope="sprite",
    check=_floor_aligned_sprites_rest_on_a_surface,
))


def _dudes_carry_an_xsprite(disk) -> Finding:
    population = 0
    out = []
    for index, sprite in enumerate(disk.sprites):
        fields = sprite.fields
        if int(fields["status"]) != 6:
            continue
        population += 1
        if int(fields["extra"]) <= 0:
            out.append(Violation(f"sprite[{index}]",
                                 f"dude type {fields['type']} has no XSprite"))
    return Finding(population, tuple(out))


register(Rule(
    id="dude-carries-an-xsprite",
    statement="a sprite on the dude list must carry an XSprite",
    because=(
        "aiInitSprite dereferences xsprite[pSprite->extra] and gDudeExtra with "
        "no guard, so a kStatDude sprite without one segfaults the engine on "
        "load. Every other statnum is guarded and merely does nothing"),
    source="NBlood/source/blood/src/ai.cpp:1452 aiInitSprite",
    scope="sprite",
    check=_dudes_carry_an_xsprite,
))


def _aquatic_sprites_are_under_water(disk) -> Finding:
    try:
        from .furniture import wet_only
        wet = wet_only()
    except Exception:
        return Finding(0)
    underwater = {
        index for index, sector in enumerate(disk.sectors)
        if sector.extra and int(sector.extra.fields.get("underwater", 0) or 0)
    }
    population = 0
    out = []
    for index, sprite in enumerate(disk.sprites):
        fields = sprite.fields
        if int(fields["cstat"]) & CSTAT_INVISIBLE:
            continue
        if int(fields["picnum"]) not in wet:
            continue
        population += 1
        if int(fields["sector"]) not in underwater:
            out.append(Violation(f"sprite[{index}]",
                                 f"tile {fields['picnum']} is aquatic and stands dry"))
    return Finding(population, tuple(out))


register(Rule(
    id="aquatic-sprite-is-under-water",
    statement="an aquatic tile belongs in a sector that is under water",
    because=(
        "664 appears in 82 campaign sectors and every one is submerged; 660 in "
        "142, likewise. They are weed, not creepers"),
    source="corpus",
    scope="sprite",
    check=_aquatic_sprites_are_under_water,
))


# ---------------------------------------------------------------------------
# structure
# ---------------------------------------------------------------------------

def _markers_name_a_real_owner(disk) -> Finding:
    population = 0
    out = []
    for index, sprite in enumerate(disk.sprites):
        fields = sprite.fields
        if int(fields["status"]) != 10:
            continue
        if int(fields["type"]) not in (3, 4, 5, 8):
            continue
        population += 1
        owner = int(fields["owner"])
        if not 0 <= owner < len(disk.sectors) or disk.sectors[owner].extra is None:
            out.append(Violation(f"sprite[{index}]",
                                 f"marker owner {owner} names no XSECTOR sector"))
    return Finding(population, tuple(out))


register(Rule(
    id="marker-names-a-real-owner",
    statement="a marker sprite's owner must name a sector that has an XSECTOR",
    because=(
        "PropagateMarkerReferences rebuilds marker0/marker1 from each marker's "
        "owner at load, and a marker whose owner names no XSECTOR sector reaches "
        "DeleteSprite -- the mechanism loses its markers before the level starts"),
    source="NBlood/source/blood/src/db.cpp:680 PropagateMarkerReferences",
    scope="sprite",
    check=_markers_name_a_real_owner,
))


def _two_sided_walls_are_reciprocal(disk) -> Finding:
    population = 0
    out = []
    for index, wall in enumerate(disk.walls):
        fields = wall.fields
        other = int(fields["next_wall"])
        if int(fields["next_sector"]) < 0:
            continue
        population += 1
        if not 0 <= other < len(disk.walls):
            out.append(Violation(f"wall[{index}]", f"next_wall {other} is out of range"))
            continue
        if int(disk.walls[other].fields["next_wall"]) != index:
            out.append(Violation(f"wall[{index}]",
                                 f"wall {other} does not point back at it"))
    return Finding(population, tuple(out))


register(Rule(
    id="two-sided-wall-is-reciprocal",
    statement="a two-sided wall and its partner must point at each other",
    because=(
        "the renderer and the clipper both follow next_wall to cross a portal; "
        "a one-way pairing is a hole the player falls through or a wall that "
        "draws from the wrong side"),
    source="NBlood/source/build/src/engine.cpp",
    scope="wall",
    check=_two_sided_walls_are_reciprocal,
))


def _glass_is_breakable(disk) -> Finding:
    """Panes of 266 the player cannot shoot out."""
    population = 0
    out = []
    for index, wall in enumerate(disk.walls):
        fields = wall.fields
        if int(fields["over_picnum"]) != 266 or int(fields["next_sector"]) < 0:
            continue
        population += 1
        if int(fields["type"]) != 511:
            out.append(Violation(f"wall[{index}]", "glass that cannot be broken"))
    return Finding(population, tuple(out))


register(Rule(
    id="glass-is-breakable",
    statement="a pane of glass should be a wall the player can shoot out",
    because=(
        "266 is Blood's commonest breakable wall by a distance -- 247 of the 406 "
        "walls carrying kWallGib across the campaign and Death Wish"),
    source="corpus",
    scope="wall",
    check=_glass_is_breakable,
))


# ---------------------------------------------------------------------------
# room over room
# ---------------------------------------------------------------------------
#
# `warpInit` (warp.cpp:43) collects one upper and one lower link marker per
# sector, then pairs them by XSPRITE `data_1`. `CheckLink` (warp.cpp:183) moves
# a sprite that crosses the threshold to the partner's sector and translates it
# by exactly (lower - upper). The boundary is a translation at a plane.
#
# Six marker types make four families, and mining all 43 campaign maps -- 251
# pairs -- shows that two of them are geometrically opposite things:
#
#     family   pairs   maps   congruent   overlaps in plan   median offset
#     water      191     24         77%                 7%         81.3 pw
#     stack       38     20         61%                66%          0.8 pw
#     link        22     12         68%                32%         60.0 pw
#
# A water link is a congruent copy of the room parked far away in free map
# space, dived into. A **stack is the same footprint in the same place**, one
# room directly over another. They are not variants of one idea.

STACK_MARKERS = {11: "floor", 12: "ceiling"}
LINK_MARKERS = {6, 7, 9, 10, 11, 12, 13, 14}

#: kMirrorTile. mirrors.cpp:37, and the reason a sector's other side is drawn at
#: all: `IsRorSector` returns true when the floor or ceiling picnum is this or in
#: the mirror range. This project spent a long time using 504 as a parallax sky
#: base and blaming the magenta on the tiles in its panel run.
MIRROR_TILE = 504


def _stack_portals_wear_the_mirror_tile(disk) -> Finding:
    population = 0
    out = []
    for index, sprite in enumerate(disk.sprites):
        kind = int(sprite.fields["type"])
        surface = STACK_MARKERS.get(kind)
        if surface is None:
            continue
        sector = int(sprite.fields["sector"])
        if not 0 <= sector < len(disk.sectors):
            continue
        population += 1
        picnum = int(disk.sectors[sector].fields[f"{surface}_picnum"])
        if picnum != MIRROR_TILE:
            out.append(Violation(
                f"sector[{sector}].{surface}",
                f"carries a stack marker but its tile is {picnum}, not {MIRROR_TILE}"))
    return Finding(population, tuple(out))


register(Rule(
    id="stack-portal-wears-the-mirror-tile",
    statement=(
        "a sector carrying a stack marker must wear the mirror tile on the "
        "surface the stack looks through"),
    because=(
        "IsRorSector is what decides whether the other side is drawn, and it "
        "decides by picnum: the mirror tile or the mirror range. Without it the "
        "link still moves the player and they cross it blind, looking at an "
        "ordinary floor the whole way"),
    source="NBlood/source/blood/src/mirrors.cpp:243 IsRorSector",
    scope="sector",
    check=_stack_portals_wear_the_mirror_tile,
))


def _link_markers_carry_an_xsprite(disk) -> Finding:
    population = 0
    out = []
    for index, sprite in enumerate(disk.sprites):
        if int(sprite.fields["type"]) not in LINK_MARKERS:
            continue
        population += 1
        if sprite.extra is None or int(sprite.fields["extra"]) <= 0:
            out.append(Violation(f"sprite[{index}]",
                                 "a link marker with no XSprite is never collected"))
    return Finding(population, tuple(out))


register(Rule(
    id="link-marker-carries-an-xsprite",
    statement="a room-over-room marker must carry an XSprite",
    because=(
        "warpInit only looks at sprites whose extra is greater than zero, and it "
        "reads the link id out of the XSprite's data_1. A marker without one is "
        "not collected into gUpperLink or gLowerLink and the link does not exist"),
    source="NBlood/source/blood/src/warp.cpp:43 warpInit",
    scope="sprite",
    check=_link_markers_carry_an_xsprite,
))


def _link_markers_are_paired(disk) -> Finding:
    uppers, lowers = [], []
    for index, sprite in enumerate(disk.sprites):
        kind = int(sprite.fields["type"])
        if kind not in LINK_MARKERS or sprite.extra is None:
            continue
        link = int(sprite.extra.fields.get("data_1", 0) or 0)
        (uppers if kind in (7, 9, 11, 13) else lowers).append((index, link))
    known = {link for _, link in lowers}
    out = [
        Violation(f"sprite[{index}]", f"link id {link} has no lower marker")
        for index, link in uppers if link not in known
    ]
    return Finding(len(uppers), tuple(out))


register(Rule(
    id="link-marker-is-paired",
    statement="an upper link marker needs a lower one sharing its link id",
    because=(
        "warpInit matches on XSPRITE data_1 alone. An upper marker with no "
        "partner leaves owner unset, and CheckLink then dereferences it -- the "
        "assertion in the middle of the crossing is dassert(nLower >= 0)"),
    source="NBlood/source/blood/src/warp.cpp:183 CheckLink",
    scope="sprite",
    check=_link_markers_are_paired,
))


def _open_neighbours_share_a_sky(disk) -> Finding:
    from .reachability import portal_graph

    graph = portal_graph(disk)
    open_sectors = {
        index for index in range(len(disk.sectors))
        if int(disk.sectors[index].fields["ceiling_stat"]) & 1
    }
    population = 0
    out = []
    seen = set()
    for index in sorted(open_sectors):
        for other in graph.get(index, ()):
            if other not in open_sectors or (other, index) in seen:
                continue
            seen.add((index, other))
            population += 1
            gap = abs(int(disk.sectors[index].fields["ceiling_z"])
                      - int(disk.sectors[other].fields["ceiling_z"]))
            if gap >= PLAYER_HEIGHT:
                out.append(Violation(
                    f"sector[{index}]",
                    f"its sky is {gap} from sector {other}'s"))
    return Finding(population, tuple(out))


register(Rule(
    id="open-neighbours-share-a-sky",
    statement="two open sectors that touch should hold their sky at one height",
    because=(
        "not because the difference is drawn -- it is not. engine.cpp:4688 skips "
        "the upper wall section entirely when *both* sectors are parallax, so two "
        "open yards whose skies are ten player heights apart show no seam at all; "
        "rendered it to be sure, after claiming the opposite here. What the "
        "ceiling z still does is clip. The player and every sprite are bounded by "
        "it whether or not anything is drawn there, so a mismatch is an invisible "
        "ceiling to walk into -- and a staircase, whose step ceilings track its "
        "step floors, carries one down with it a step at a time"),
    source="corpus",
    scope="sector",
    check=_open_neighbours_share_a_sky,
))


def _thresholds_follow_the_roofed_side(disk) -> Finding:
    from .reachability import design_sectors, portal_graph

    graph = portal_graph(disk)
    playable = set(design_sectors(disk))
    open_sectors = {
        index for index in playable
        if int(disk.sectors[index].fields["ceiling_stat"]) & 1
    }

    def area(index: int) -> float:
        fields = disk.sectors[index].fields
        start, count = int(fields["wall_ptr"]), int(fields["wall_count"])
        total = 0
        for wall in range(start, start + count):
            here = disk.walls[wall].fields
            there = disk.walls[int(here["point2"])].fields
            total += int(here["x"]) * int(there["y"]) - int(there["x"]) * int(here["y"])
        return abs(total) / 2.0 / (384.0 * 384.0)

    population = 0
    out = []
    for index in playable:
        if area(index) >= 20:
            continue                        # a room, not a threshold
        neighbours = [n for n in graph.get(index, ()) if n in playable]
        if len(neighbours) < 2:
            continue
        outdoors = sum(1 for n in neighbours if n in open_sectors)
        if outdoors == 0 or outdoors == len(neighbours):
            continue                        # not a threshold between the two
        population += 1
        if index in open_sectors:
            out.append(Violation(
                f"sector[{index}]",
                "a threshold onto a roofed space, open to the sky"))
    return Finding(population, tuple(out))


register(Rule(
    id="threshold-follows-the-roofed-side",
    statement=(
        "a small sector joining an open space to a roofed one usually takes "
        "the roof"),
    because=(
        "of the campaign's 849 small sectors touching both, 703 are roofed -- "
        "and of the 82 that are Z-motion doors, 74 are. Standing inside the door "
        "of a roofed building and looking up at clouds is the failure this "
        "describes; a gate in an outdoor wall is the 17% that is not"),
    source="corpus",
    scope="sector",
    check=_thresholds_follow_the_roofed_side,
))


def _ceiling_movers_are_not_open_to_the_sky(disk) -> Finding:
    population = 0
    out = []
    for index, sector in enumerate(disk.sectors):
        if int(sector.fields["type"]) not in (600, 602) or sector.extra is None:
            continue
        fields = sector.extra.fields
        moves_ceiling = int(fields["off_ceiling_z"]) != int(fields["on_ceiling_z"])
        if not moves_ceiling:
            continue
        population += 1
        if int(sector.fields["ceiling_stat"]) & 1:
            out.append(Violation(
                f"sector[{index}]",
                "a Z-motion door that moves its ceiling, with no ceiling to move"))
    return Finding(population, tuple(out))


register(Rule(
    id="ceiling-mover-is-not-open-to-the-sky",
    statement=(
        "a Z-motion door that opens by lifting its ceiling cannot have a "
        "parallax one"),
    because=(
        "not because the ceiling fails to move -- it moves, and the motion is "
        "drawn, because engine.cpp:4688 draws the upper wall section whenever "
        "*either* side is roofed. The reason is what the moving ceiling is: the "
        "sky. A doorway between two roofed rooms whose ceiling is the sky is a "
        "hole in the roof, and opening it shows daylight overhead in the middle "
        "of a building. Rendered both poses to check, because the first version "
        "of this rule asserted the opposite and was wrong. A door that opens by "
        "*dropping its floor* has no such problem: it is a gate in an outdoor "
        "wall and the sky above it belongs there. The campaign separates them "
        "sharply -- 18.4% of its floor-moving doors are open to the sky against "
        "0.5% of its ceiling-moving ones, and all three of those sit in one map"),
    source="NBlood/source/blood/src/triggers.cpp OperateDoor",
    scope="sector",
    check=_ceiling_movers_are_not_open_to_the_sky,
))


def _sky_is_never_below_a_roof(disk) -> Finding:
    from .reachability import portal_graph

    graph = portal_graph(disk)
    open_sectors = {
        index for index in range(len(disk.sectors))
        if int(disk.sectors[index].fields["ceiling_stat"]) & 1
    }
    population = 0
    out = []
    for index in sorted(open_sectors):
        here = int(disk.sectors[index].fields["ceiling_z"])
        for other in graph.get(index, ()):
            if not 0 <= other < len(disk.sectors) or other in open_sectors:
                continue                      # two open sectors: see the sibling rule
            population += 1
            there = int(disk.sectors[other].fields["ceiling_z"])
            if here > there:                  # z points down: larger is lower
                out.append(Violation(
                    f"sector[{index}]",
                    f"its sky is {here - there} below sector {other}'s ceiling"))
    return Finding(population, tuple(out))


register(Rule(
    id="sky-is-never-below-a-roof",
    statement=(
        "a sector open to the sky must hold its ceiling at least as high as any "
        "roofed neighbour's"),
    because=(
        "engine.cpp:4688 draws the upper wall section whenever either side is "
        "roofed, so a parallax ceiling below a roofed neighbour's is drawn with "
        "the sky *underneath* the surrounding roofline -- daylight showing below "
        "the level of the ceiling next to it, which cannot happen in a building. "
        "The campaign holds 73% of these pairs exactly equal and its median gap "
        "is zero; the four that go the other way are all in E3M4"),
    source="NBlood/source/build/src/engine.cpp:4688",
    scope="sector",
    check=_sky_is_never_below_a_roof,
))


# --------------------------------------------------------------------------
# Apertures. Both of these came out of one render: a doorway in the courtyard
# with a 4.35-human slab of smooth ashlar hanging above its mouth on a rubble
# wall. See `bloodmap/aperture.py` for the grammar that now prevents it.
# --------------------------------------------------------------------------

def _openings_clear_a_standing_body(disk) -> Finding:
    """A way between two rooms that a standing player cannot walk through."""
    from tools.mine_apertures import observe

    population = 0
    violations = []
    for row in observe("map", disk):
        if row["kind"] == "door_sector":
            continue                    # stored shut; its opening is its motion
        population += 1
        if row["leaf_player_heights"] < 1.0:
            violations.append(Violation(
                "wall %d" % row["wall"],
                "%.2f standing humans of clear opening between sectors %d and %d"
                % (row["leaf_player_heights"], row["sector"], row["next_sector"])))
    return Finding(population, tuple(violations))


register(Rule(
    id="opening-clears-a-standing-body",
    statement="a way through is at least one standing body tall",
    because=(
        "Build clips a body by its whole sprite extent, not by the camera "
        "height, so the clearance a standing player needs is bottom-top of the "
        "player sprite. The bot's own model agrees -- blood_terrain.cpp "
        "clearanceFor returns Standing only when freeHeight >= body.height. "
        "This project spent months testing clearance against 0x1600 instead, "
        "which is POSTURE.eyeAboveZ, an offset from the sprite's centre, and "
        "so passed passages a third of the height a player can enter"),
    source="NBlood/source/blood/src/db.h:325 GetSpriteExtents",
    scope="wall",
    check=_openings_clear_a_standing_body,
))


def _lintel_continues_the_facade(disk) -> Finding:
    """The band above a mouth should be made of the wall it is cut in."""
    from tools.mine_apertures import observe

    population = 0
    violations = []
    for row in observe("map", disk):
        if not row["aperture"] or row["lintel_player_heights"] <= 0:
            continue
        population += 1
        if not row["lintel_continues_facade"]:
            violations.append(Violation(
                "wall %d" % row["wall"],
                "%.2f humans of band above the mouth in tile %d, on a wall the "
                "room paints %d" % (row["lintel_player_heights"],
                                    row["wall_picnum"], row["facade_picnum"])))
    return Finding(population, tuple(violations))


register(Rule(
    id="lintel-continues-the-facade",
    statement="the band above an opening is made of the wall it is cut in",
    because=(
        "Build draws a two-sided wall's upper section from that wall's own "
        "picnum -- overpicnum is only read for masked one-way walls -- so the "
        "band above a mouth belongs to the facade it is seen from, not to the "
        "doorway behind it. Dressing a whole portal wall in the material's "
        "opening tile therefore hangs the dressing over the doorway as well as "
        "around it. The campaign dresses jambs freely and still keeps this: of "
        "its 10,475 lintels, 70% carry the room's own field tile"),
    source="corpus",
    scope="wall",
    check=_lintel_continues_the_facade,
))


# --------------------------------------------------------------------------
# Wall thickness. The thin-wall class: a sizing fault that looks like a
# positioning fault. See `bloodmap/layout.py` for the grammar that prevents it.
# --------------------------------------------------------------------------

def _walls_are_thick_enough(disk) -> Finding:
    """Solid mass between two rooms that share a height range."""
    from tools.mine_wall_thickness import MIN_WALL_LENGTH, observe

    population = 0
    violations = []
    seen: set[tuple[int, int]] = set()
    for row in observe("map", disk):
        pair = (min(row["sector"], row["other"]), max(row["sector"], row["other"]))
        if pair in seen:
            continue
        seen.add(pair)
        population += 1
        if row["thickness"] < 128:
            violations.append(Violation(
                "wall %d" % row["wall"],
                "%d units (%.2f body widths) of stone between sectors %d and %d"
                % (row["thickness"], row["thickness_player_widths"],
                   row["sector"], row["other"])))
    return Finding(population, tuple(violations))


register(Rule(
    id="wall-between-rooms-is-not-paper",
    statement="the mass between two rooms is at least 128 units thick",
    because=(
        "a wall nobody sized absorbs every rounding error in the layout, and "
        "the engine draws the result without complaint. Blood's own masonry is "
        "modal on multiples of 128 -- 128, 256, 384, and a long tail past 512 -- "
        "and it goes below 128 on 2.79% of the 48,019 places its solid walls "
        "face another room at the same height. Those thin ones are fake walls "
        "and hidden doors, which is to say they are on purpose"),
    source="corpus",
    scope="wall",
    check=_walls_are_thick_enough,
))


# --------------------------------------------------------------------------
# Keys. A lock the player cannot read is a lock they cannot plan around.
# See `bloodmap/keys.py` for the emblem vocabulary and its derivation.
# --------------------------------------------------------------------------

def _keyed_doors_say_which_key(disk) -> Finding:
    from bloodmap.keys import EMBLEM_NAME, PLACARD_REACH, emblem_for
    from tools.mine_keys import key_of

    locks = []
    for index, sector in enumerate(disk.sectors):
        key = key_of(sector)
        if not key:
            continue
        fields = sector.fields
        start, count = int(fields["wall_ptr"]), int(fields["wall_count"])
        xs = [int(disk.walls[w].fields["x"]) for w in range(start, start + count)]
        ys = [int(disk.walls[w].fields["y"]) for w in range(start, start + count)]
        locks.append((index, key, sum(xs) // len(xs), sum(ys) // len(ys)))

    placards = [(int(s.fields["picnum"]), int(s.fields["x"]), int(s.fields["y"]))
                for s in disk.sprites
                if int(s.fields["picnum"]) in EMBLEM_NAME
                and not int(s.fields["cstat"]) & 0x8000]

    violations = []
    for index, key, x, y in locks:
        if not any(hypot(px - x, py - y) <= PLACARD_REACH
                   and picnum == emblem_for(key)
                   for picnum, px, py in placards):
            violations.append(Violation(
                "sector %d" % index,
                "wants the %s key and nothing within %d units says so"
                % (EMBLEM_NAME[emblem_for(key)], PLACARD_REACH)))
    return Finding(len(locks), tuple(violations))


register(Rule(
    id="keyed-door-says-which-key",
    statement="a door that wants a key carries that key's emblem near it",
    because=(
        "the key requirement lives in the XSECTOR, where the engine reads it "
        "and the player cannot. What the player reads is the placard: six "
        "58x58 emblems -- skull, eye, flame, dagger, spider, moon -- that share "
        "a frame and differ only in the symbol, which is the whole message. "
        "Without one a locked door says it is locked and nothing else, so the "
        "player cannot tell whether they already hold the key"),
    source="corpus",
    scope="sector",
    check=_keyed_doors_say_which_key,
))


# --------------------------------------------------------------------------
# Controls. What a switch looks like and how high it hangs have to agree with
# how the player is meant to work it. See `bloodmap/switches.py`.
# --------------------------------------------------------------------------

def _pressed_switches_are_in_reach(disk) -> Finding:
    from bloodmap.switches import (PLAYER_HEIGHT as SPH, PRESSED_LIMIT,
                                   SWITCH_TYPES, _extra)

    population = 0
    violations = []
    for index, sprite in enumerate(disk.sprites):
        if int(sprite.fields["type"]) not in SWITCH_TYPES:
            continue
        extra = _extra(sprite)
        shot = bool(int(extra.get("trigger_impact", 0) or 0)
                    or int(extra.get("trigger_vector", 0) or 0))
        pushed = bool(int(extra.get("trigger_push", 0) or 0)
                      or int(extra.get("trigger_wall_push", 0) or 0))
        if not pushed or shot:
            continue
        sector = int(sprite.fields["sector"])
        if not 0 <= sector < len(disk.sectors):
            continue
        floor = int(disk.sectors[sector].fields["floor_z"])
        height = (floor - int(sprite.fields["z"])) / SPH
        population += 1
        if height > PRESSED_LIMIT:
            violations.append(Violation(
                "sprite %d" % index,
                "%.2f standing humans above the floor and worked by hand"
                % height))
    return Finding(population, tuple(violations))


register(Rule(
    id="pressed-switch-is-in-reach",
    statement="a switch worked by hand hangs where a hand can reach it",
    because=(
        "Blood's use is a hitscan from the eye, so a switch above the line the "
        "player is looking along cannot be pressed at all. The campaign's 453 "
        "hand-worked switches sit at a median 0.79 standing humans with a p95 "
        "of 0.84, against an eye at 0.83 -- at eye level or just under. Its 63 "
        "shot switches sit at a median 1.93 and wear different tiles, so height "
        "is not a free choice: it is half of how the player is told which kind "
        "of control this is"),
    source="corpus",
    scope="sprite",
    check=_pressed_switches_are_in_reach,
))


def _exit_switch_wears_the_exit_tile(disk) -> Finding:
    from bloodmap.switches import (CHANNEL_EXIT, CHANNEL_SECRET_EXIT, EXIT_TILE,
                                   SWITCH_TYPES, _extra)

    population = 0
    violations = []
    for index, sprite in enumerate(disk.sprites):
        if int(sprite.fields["type"]) not in SWITCH_TYPES:
            continue
        tx = int(_extra(sprite).get("tx_id", 0) or 0)
        if tx not in (CHANNEL_EXIT, CHANNEL_SECRET_EXIT):
            continue
        population += 1
        picnum = int(sprite.fields["picnum"])
        if picnum != EXIT_TILE:
            violations.append(Violation(
                "sprite %d" % index,
                "ends the level on channel %d but wears tile %d" % (tx, picnum)))
    return Finding(population, tuple(violations))


register(Rule(
    id="exit-switch-wears-the-exit-tile",
    statement="the switch that ends the level wears the tile that says so",
    because=(
        "kChannelLevelExitNormal is 4 and kChannelLevelExitSecret is 5 "
        "(eventq.h:30), and neither is visible to the player. What is visible "
        "is the art: 41 of the campaign's 50 exit switches wear tile 318, a "
        "downward blade, and that tile appears only 5 times anywhere else in 43 "
        "maps. An exit wearing the ordinary lever 1070 -- which the campaign "
        "uses 274 times to open doors -- gives the player no way to tell the "
        "end of the level from another door"),
    source="corpus",
    scope="sprite",
    check=_exit_switch_wears_the_exit_tile,
))


# ---------------------------------------------------------------------------
# usage laws: where a tile may go
# ---------------------------------------------------------------------------

def _mask_tiles_stay_off_plain_surfaces(disk) -> Finding:
    from .usage_kinds import CSTAT_MASKED, STAT_PARALLAX, masked_tiles

    masked = masked_tiles()
    if not masked:
        return Finding(0, ())
    population = 0
    out = []
    for index, sector in enumerate(disk.sectors):
        fields = sector.fields
        for role in ("floor", "ceiling"):
            if int(fields[f"{role}_stat"]) & STAT_PARALLAX:
                continue                  # a sky is not sampled this way
            population += 1
            picnum = int(fields[f"{role}_picnum"])
            if picnum in masked:
                out.append(Violation(f"sector[{index}].{role}",
                                     f"tile {picnum} carries the mask colour"))
    for index, wall in enumerate(disk.walls):
        fields = wall.fields
        if int(fields["next_sector"]) >= 0:
            continue                      # two-sided: 23 attested exceptions
        population += 1
        picnum = int(fields["picnum"])
        if picnum in masked:
            out.append(Violation(f"wall[{index}]",
                                 f"tile {picnum} carries the mask colour"))
    return Finding(population, tuple(out))


register(Rule(
    id="mask-tile-off-plain-surfaces",
    statement=(
        "a tile carrying the mask colour never goes on a floor, a ceiling, "
        "or a one-sided wall's picnum"),
    because=(
        "the mask colour is palette index 255, which the ART uses to mean "
        "see-through. Floors, ceilings and one-sided walls have nothing "
        "behind them, so the engine draws whatever was last in the buffer "
        "through the holes. A cut-out belongs to a sprite or to the "
        "over_picnum of a masked two-sided wall, where there IS something "
        "behind it. Measured over the campaign: 0 of 26383 non-parallax "
        "surface slots and 0 of 52422 one-sided wall slots. Exactly two "
        "tiles appear on two-sided walls, over 23 of 60839 slots, and the "
        "owner has ruled on both (2026-09-01): 142 is a skull-shaped "
        "FIREPLACE maskwall whose two-sided uses are the legitimate "
        "see-through fireplace mouth -- the masked-overlay case this rule "
        "deliberately permits -- and 2464 is an ejected shell casing whose "
        "two slots are mapper accidents. Neither is a curtain family, so the "
        "scope stays where it is for a reason rather than for want of data"),
    source=(
        "NBlood/source/build/src/engine.cpp:2902 ceilscan and :3000 florscan "
        "call the opaque hline path; transmaskwallscan (:3362) is reached "
        "only for masked two-sided walls. "
        "knowledge/blood/design/owner-anchors-v1.json reading_guide."
        "transparency"),
    scope="sector",
    check=_mask_tiles_stay_off_plain_surfaces,
))


def _parallax_wears_a_sky_tile(disk) -> Finding:
    from .usage_kinds import STAT_PARALLAX, sky_family

    family = sky_family()
    if not family:
        return Finding(0, ())
    population = 0
    out = []
    for index, sector in enumerate(disk.sectors):
        fields = sector.fields
        for role in ("floor", "ceiling"):
            if not int(fields[f"{role}_stat"]) & STAT_PARALLAX:
                continue
            population += 1
            picnum = int(fields[f"{role}_picnum"])
            if picnum not in family:
                out.append(Violation(
                    f"sector[{index}].{role}",
                    f"parallaxed but wears tile {picnum}, which the campaign "
                    f"never parallaxes"))
    return Finding(population, tuple(out))


register(Rule(
    id="parallax-wears-a-sky-tile",
    statement="a parallaxed surface wears a tile from the sky family",
    because=(
        "the parallax bit tells the engine to draw the tile as an infinitely "
        "distant backdrop scrolling with the view instead of as a surface at "
        "a z. A tile drawn that way has to be built for it -- the campaign's "
        "three are all 64x400 strips -- and an ordinary 64x64 ceiling tile "
        "smeared across the sky is the glitch this catches. The family is "
        "derived rather than assumed: every tile the campaign ever "
        "parallaxes, which is 2500, 3491 and 3678"),
    source=(
        "NBlood/source/build/src/engine.cpp parallaxtype handling; "
        "knowledge/blood/design/usage-kinds-v1.json sky_family, "
        "1768 parallaxed campaign surfaces"),
    scope="sector",
    check=_parallax_wears_a_sky_tile,
))


def _sky_tiles_are_parallaxed(disk) -> Finding:
    from .usage_kinds import STAT_PARALLAX, sky_family

    family = sky_family()
    if not family:
        return Finding(0, ())
    population = 0
    out = []
    for index, sector in enumerate(disk.sectors):
        fields = sector.fields
        for role in ("floor", "ceiling"):
            picnum = int(fields[f"{role}_picnum"])
            if picnum not in family:
                continue
            population += 1
            if not int(fields[f"{role}_stat"]) & STAT_PARALLAX:
                out.append(Violation(
                    f"sector[{index}].{role}",
                    f"sky tile {picnum} without the parallax bit"))
    return Finding(population, tuple(out))


register(Rule(
    id="sky-tile-is-parallaxed",
    statement="a sky-family tile on a surface carries the parallax bit",
    because=(
        "without the bit the sky is sampled as an ordinary surface through "
        "picsiz, and all three sky tiles are 64x400 -- so the flat-tile "
        "power-of-two law rejects them anyway and the engine draws 64x256 of "
        "the strip. The two laws interlock: a sky tile on an ordinary "
        "ceiling is wrong twice. The campaign does it 5 times in 1028, all "
        "with 2500"),
    source=(
        "NBlood/source/build/src/tiles.cpp:281 tileUpdatePicSiz with "
        "engine.cpp:2951 ceilscan; knowledge/blood/design/usage-kinds-v1.json "
        "sky_family.used_without_parallax"),
    scope="sector",
    check=_sky_tiles_are_parallaxed,
))


def _tiles_sit_in_attested_slots(disk) -> Finding:
    from .usage_kinds import load, unattested_uses

    table = load()
    if not table.get("usage"):
        return Finding(0, ())
    population = (len(disk.sectors) * 2) + len(disk.walls)
    found = unattested_uses(disk, table=table)
    return Finding(population, tuple(
        Violation(item["where"],
                  f"tile {item['picnum']} in {item['slot']}; the campaign "
                  f"attests it only in {', '.join(item['attested'])}")
        for item in found))


register(Rule(
    id="tile-sits-in-an-attested-slot",
    statement=(
        "a tile goes in a slot the campaign is attested to use it in"),
    because=(
        "this is the representation taxonomy as a measurement rather than an "
        "opinion. It says where each tile HAS been seen, never where it MAY "
        "go -- 43 maps is a small corpus and an authored map is allowed to "
        "be the first to do something. What it is not allowed to do is do it "
        "by accident, which is what this catches: shelf goods laid on a "
        "floor, a sprite cut-out painted on a wall, a facade backdrop used "
        "as bulk fill. An owner anchor's dual_role note is the override. "
        "Walls are judged by the BAND the engine draws (usage-kinds-v2, "
        "bloodmap.render_slots) when that table is present: a tile stored on "
        "a two-sided wall may show on a step, in a mask, or nowhere, and the "
        "storage vocabulary could not tell those apart. A wall that draws "
        "nothing is not this rule's business -- wall-tile-is-drawn-somewhere "
        "owns that"),
    source=("knowledge/blood/design/usage-kinds-v2.json (walls, by rendered "
            "band) and usage-kinds-v1.json (surfaces and sprites), 43 "
            "campaign maps"),
    scope="sector",
    check=_tiles_sit_in_attested_slots,
))


def _drawn_exemptions() -> set[int]:
    """Tiles that bypass the wall pass on purpose, plus the editor's blank."""
    from .render_slots import SKY_FAMILY
    from .usage_kinds import sky_family

    return (sky_family() or set(SKY_FAMILY)) | {MIRROR_TILE, 0}


def _walls_draw_their_own_tile(disk) -> Finding:
    from .render_slots import render_slots, undrawn_walls

    exempt = _drawn_exemptions()
    draws = render_slots(disk)
    population = sum(1 for d in draws if d.picnum not in exempt)
    found = undrawn_walls(disk, draws=draws, exempt=exempt)
    out = []
    for item in found:
        pair = ", ".join(f"{band} {tile}" for band, tile in item["pair_draws"])
        out.append(Violation(
            f"wall[{item['wall']}]",
            f"tile {item['picnum']} is drawn on no band from either side "
            f"(sector {item['sector']} -> {item['next_sector']}; the pair "
            f"draws {pair or 'nothing'}; partner wears "
            f"{item['partner_picnum']})"))
    return Finding(population, tuple(out))


register(Rule(
    id="wall-draws-its-own-tile",
    statement=(
        "a wall's picnum is drawn on some band, from one side or the other"),
    because=(
        "the engine draws bands, not fields. A two-sided wall's picnum "
        "shows only on its upper step (where the neighbour's ceiling is "
        "lower, engine.cpp:4690-4720) or its lower step (where the "
        "neighbour's floor is higher, :4801-4833, swapped to the partner's "
        "picnum under cstat&2); the middle shows over_picnum and only when "
        "masked or one-way (:4685, :4938). A flush, unmasked red wall "
        "therefore draws nothing on either side, whatever it wears. The "
        "campaign leaves a tile on such walls a quarter of the time -- the "
        "editor copies the previous wall's picnum on insert and nobody "
        "clears it -- so this is a habit, not a law, and the gate is "
        "wall-tile-is-drawn-somewhere. Sky tiles, the mirror tile and 0 "
        "are exempt: the first two bypass the wall pass by design"),
    source="NBlood/source/build/src/engine.cpp:4690 classicDrawBunches",
    scope="wall",
    check=_walls_draw_their_own_tile,
))


def _wall_tiles_are_drawn_somewhere(disk) -> Finding:
    from .render_slots import render_slots

    exempt = _drawn_exemptions()
    draws = render_slots(disk)
    drawn = {band.tile for draw in draws for band in draw.bands}
    authored: dict[int, list[int]] = {}
    for draw in draws:
        if draw.picnum in exempt:
            continue
        authored.setdefault(draw.picnum, []).append(draw.wall)
    out = []
    for picnum, walls in sorted(authored.items()):
        if picnum in drawn:
            continue
        shown = ", ".join(str(w) for w in walls[:6])
        more = f" and {len(walls) - 6} more" if len(walls) > 6 else ""
        reasons = sorted({r.split(" (")[0] for w in walls
                          for r in draws[w].skipped})
        out.append(Violation(
            f"tile[{picnum}]",
            f"authored on {len(walls)} wall(s) ({shown}{more}) and drawn on "
            f"no band anywhere in the map; {'; '.join(reasons)}"))
    return Finding(len(authored), tuple(out))


register(Rule(
    id="wall-tile-is-drawn-somewhere",
    statement=(
        "a tile authored on a map's walls is on screen somewhere in that map"),
    because=(
        "a tile chosen for a wall was chosen to be seen. When every wall "
        "wearing it is a flush, unmasked red wall -- no step on either side, "
        "no mask bit -- the engine never reads the field (engine.cpp:4690, "
        ":4801, :4685, :4938) and the material is absent from the level "
        "however deliberately it was authored. This is how the city's stage "
        "curtain lost its fabric: tile 146 on unmasked two-sided walls whose "
        "neighbour's ceiling is higher and whose floors are flush, so the "
        "auditorium draws its own stone on the step above and the walkable "
        "band is see-through. Per wall the campaign does this constantly "
        "(editor leftovers on invisible walls), which is why the population "
        "here is the map's distinct authored tiles: a leftover is drawn "
        "elsewhere in the same map, a lost material is not"),
    source="NBlood/source/build/src/engine.cpp:4690 classicDrawBunches",
    scope="map",
    check=_wall_tiles_are_drawn_somewhere,
))


def _transmitters_report_an_edge(disk) -> Finding:
    from .motion import silent_transmitters

    population = 0
    for sprite in disk.sprites:
        extra = _extra_of(sprite)
        if int(extra.get("tx_id") or 0) and "command" in extra:
            population += 1
    found = silent_transmitters(disk)
    return Finding(population, tuple(
        Violation(line.split(" carries")[0], line) for line in found))


def _extra_of(item):
    payload = getattr(item, "extra", None)
    if payload is None:
        return {}
    return payload.fields if hasattr(payload, "fields") else {}


register(Rule(
    id="transmitter-reports-an-edge",
    statement=(
        "a sprite that transmits must report its ON or its OFF edge"),
    because=(
        "a transmitter does not send because it has a tx_id and a command. "
        "SetSpriteState calls evSend only inside `if (pXSprite->triggerOn && "
        "pXSprite->state)` or the triggerOff mirror, so a switch with "
        "neither flag flips its own state and sends nothing at all. Every "
        "field on it is individually valid and no static reading of the "
        "finished map can tell -- the pattern zoo shipped five such switches "
        "and the owner found them by pushing each one"),
    source="NBlood/source/blood/src/triggers.cpp:100 SetSpriteState",
    scope="sprite",
    check=_transmitters_report_an_edge,
))

# ---------------------------------------------------------------------------
# texture continuity
# ---------------------------------------------------------------------------

#: What the campaign does at a join where a material meets itself, measured
#: over its 43 maps with the editor's own predicate (`texture_frame.
#: continuity_rows`; the law is `AlignWalls`, xmapedit/src_blood/xmpmaped.cpp:
#: 3024-3050). Per class: the joins counted, the aggregate rate, and the
#: **floor** -- the lowest any single campaign map with 30+ joins in that class
#: reaches, rounded DOWN to the nearest per cent -- rounding a floor to the
#: nearest per cent rounds it above the map it came from, which is how the
#: first version of this table flagged five campaign maps with their own
#: minimum.
#:
#: The floor is the number the rule uses, and the aggregate is only reported,
#: because the spread destroys the aggregate as a threshold. `bend solid-solid`
#: x runs from 28% to 95% across the campaign's own maps: a rule set fifteen
#: points under the 68% aggregate flags a third of Blood. That is not a rule
#: about Blood, it is a rule about being below average, and the first version
#: of this rule was exactly that -- it fired on E1M1 and E3M1.
#:
#: Below the floor is a different claim and a falsifiable one: *no campaign map
#: is ever this bad in this class*. It is satisfied by all 43 by construction,
#: so a built map that trips it is doing something the corpus never does.
CAMPAIGN_CONTINUITY: dict[str, dict[str, float]] = {
    "bend portal-portal": {"n": 28216, "x": 0.30, "x_floor": 0.14,
                           "y": 0.91, "y_floor": 0.58},
    "bend solid-solid": {"n": 20021, "x": 0.68, "x_floor": 0.28,
                         "y": 0.99, "y_floor": 0.95},
    "bend solid-portal": {"n": 13366, "x": 0.34, "x_floor": 0.21,
                          "y": 0.61, "y_floor": 0.27},
    "collinear solid-solid": {"n": 6760, "x": 0.94, "x_floor": 0.81,
                              "y": 0.99, "y_floor": 0.91},
    "collinear solid-portal": {"n": 4442, "x": 0.80, "x_floor": 0.65,
                               "y": 0.88, "y_floor": 0.75},
    "collinear portal-portal": {"n": 3588, "x": 0.57, "x_floor": 0.25,
                                "y": 0.89, "y_floor": 0.68},
    "reflex solid-portal": {"n": 2836, "x": 0.25, "x_floor": 0.06,
                            "y": 0.62, "y_floor": 0.29},
    "reflex portal-portal": {"n": 1910, "x": 0.21, "x_floor": 0.03,
                             "y": 0.73, "y_floor": 0.36},
    "reflex solid-solid": {"n": 871, "x": 0.19, "x_floor": 0.08,
                           "y": 0.99, "y_floor": 0.88},
}

#: A class the campaign itself continues less than half the time is a
#: deliberate restart, not a standard. Those are excluded by AXIS, which is the
#: distinction that matters: the campaign restarts x at an outside corner
#: (reflex x, 19-25%) and between two step bands (bend portal-portal x, 30%),
#: and continues y in the very same joins 62-91% of the time. A rule that
#: dropped the whole class would stop looking at the half that is broken.
DELIBERATE_RESTART = 0.50
#: Below this a class is too small to say anything about, and it is the same
#: floor the campaign floors were measured with.
CONTINUITY_MIN_JOINS = 30


def _texture_runs_continue_as_the_campaign_does(disk) -> Finding:
    from .texture_frame import continuity_rows

    rows = continuity_rows(disk)
    population = 0
    out = []
    for name in sorted(rows):
        row = rows[name]
        expected = CAMPAIGN_CONTINUITY.get(name)
        if expected is None or row["n"] < CONTINUITY_MIN_JOINS:
            continue
        for axis in ("x", "y"):
            if expected[axis] < DELIBERATE_RESTART:
                continue                   # the campaign restarts here too
            population += 1
            got = row[axis] / row["n"]
            floor = expected[f"{axis}_floor"]
            if got < floor:
                out.append(Violation(
                    f"joins[{name}].{axis}",
                    f"{got:.0%} of {row['n']} continue; no campaign map goes "
                    f"below {floor:.0%} (campaign {expected[axis]:.0%})"))
    return Finding(population, tuple(out))


register(Rule(
    id="texture-continues-across-a-join",
    statement=(
        "where a material meets itself at a vertex the texture continues at "
        "least as often as the weakest campaign map does"),
    because=(
        "AlignWalls advances the horizontal coordinate by x_repeat*8 texels "
        "per wall and shifts the vertical phase by the peg-height difference, "
        "so a run that restarts at a vertex puts a seam on a face that has no "
        "corner in it -- which is what splitting a wall to hang a doorway off "
        "it does to a facade. The axes are separated because the campaign "
        "restarts x deliberately at outside corners and between step bands "
        "while continuing y in those same joins, and a gate that did not know "
        "that would either flag the corpus or stop looking at the broken half"),
    source="xmapedit/src_blood/xmpmaped.cpp:3024-3050 AlignWalls, :2991 GetWallZPeg",
    scope="wall",
    check=_texture_runs_continue_as_the_campaign_does,
))

#: How big a material is drawn, as texels per sixteen world units -- one Build
#: texel step. A wall consumes `x_repeat * 8` texels (`AlignWalls`,
#: xmapedit/src_blood/xmpmaped.cpp:3036), so the figure is
#: `x_repeat * 128 / length`, and a 64-wide tile at 1.0 covers 1024 world
#: units, which is Blood's own module.
#:
#: Measured over the 43 campaign maps: **every map's median lies between 0.84
#: and 1.00**, for one-sided walls (43 maps, n=46873) and two-sided alike (43
#: maps, n=52801). That is the tightest number this project has found in the
#: corpus, and it is the one nothing was checking: after 8b70d51 both built
#: maps sat at a median of 8.00 -- every facade eight times too narrow -- and
#: the continuity gate, the read-back, the conformance sweep and the
#: `>`-invariance test all passed, because every one of them compares a wall
#: to its neighbour and the neighbour was wrong in the same way.
#:
#: The envelope below is deliberately twice as wide either side of that band.
#: A material drawn at half or double its natural size is a look a mapper may
#: want; eight times is not a look, it is an error.
TEXEL_STEP_ENVELOPE = (0.5, 2.0)
#: What the campaign actually occupies, kept beside the envelope so the
#: generosity is visible rather than assumed.
CAMPAIGN_TEXEL_STEP = {"one-sided": (0.84, 1.00), "two-sided": (0.93, 1.00)}
#: Below this a kind is too small a sample for a median to mean anything.
TEXEL_STEP_MIN_WALLS = 30


def _texel_step_rows(disk):
    """(kind, texels per 16 units) per measurable wall.

    Moving walls are their own class and excluded BY CONSTRUCT rather than by
    hand: a mover's length is not a fact about the world, since
    `TranslateSector` moves the flagged end every tick while `x_repeat` stays
    put. A curtain's fabric is authored for the span the cloth hangs across
    and the file is saved at the gathered pose, so its drawn length says
    nothing about its scale -- which is why `texture_frame.frame_map` refuses
    to project them and why they cannot be judged here either.
    """
    from .texture_frame import MOVING_SECTOR_TYPES, wall_length

    sizes = art_sizes()
    moving = set()
    for sector in disk.sectors:
        if int(sector.fields["type"]) not in MOVING_SECTOR_TYPES:
            continue
        start = int(sector.fields["wall_ptr"])
        moving.update(range(start, start + int(sector.fields["wall_count"])))
    out = []
    for index, wall in enumerate(disk.walls):
        if index in moving:
            continue
        picnum = int(wall.fields["picnum"])
        size = sizes.get(picnum)
        if not size or not size[0]:
            continue
        length = wall_length(disk, index)
        if length <= 0:
            continue
        kind = "two-sided" if int(wall.fields["next_sector"]) >= 0 else "one-sided"
        out.append((kind, index, int(wall.fields["x_repeat"]) * 128.0 / length))
    return out


def _materials_are_drawn_at_campaign_size(disk) -> Finding:
    import statistics
    from collections import defaultdict

    by_kind = defaultdict(list)
    for kind, _index, step in _texel_step_rows(disk):
        by_kind[kind].append(step)
    population = 0
    out = []
    low, high = TEXEL_STEP_ENVELOPE
    for kind in sorted(by_kind):
        steps = by_kind[kind]
        if len(steps) < TEXEL_STEP_MIN_WALLS:
            continue
        population += 1
        median = statistics.median(steps)
        if not (low <= median <= high):
            seen = CAMPAIGN_TEXEL_STEP.get(kind)
            out.append(Violation(
                f"walls[{kind}].texel_step",
                f"median {median:.2f} over {len(steps)} walls is outside "
                f"[{low}, {high}]; every campaign map lies in "
                f"{seen[0]:.2f}-{seen[1]:.2f}" if seen else
                f"median {median:.2f} is outside [{low}, {high}]"))
    return Finding(population, tuple(out))


register(Rule(
    id="material-is-drawn-at-campaign-size",
    statement=(
        "a map draws its wall materials at the size the campaign draws them, "
        "within a factor of two"),
    because=(
        "a wall consumes x_repeat*8 texels, so how big the material looks is "
        "x_repeat*128/length and nothing in the file states it. Every "
        "alignment check in this project is RELATIVE -- it compares a wall to "
        "its neighbour -- so a scale error applied uniformly passes all of "
        "them at once, which is exactly what happened: both built maps shipped "
        "at eight times too narrow with every continuity gate green"),
    source="xmapedit/src_blood/xmpmaped.cpp:3036 AlignWalls",
    scope="wall",
    check=_materials_are_drawn_at_campaign_size,
))
