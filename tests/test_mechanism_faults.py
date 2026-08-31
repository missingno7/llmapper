"""Three mechanisms that were built, valid, and did not work.

Each was reported by looking at the level rather than by any check the project
had, and each turned out to be a rule the engine enforces and the corpus states
plainly. They are here so the next one is caught by a test instead.
"""

from __future__ import annotations

import glob
import math
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
#: The campaign population directory (corpus reorganized 2026-08-31).
MAPS = ROOT / "maps" / "blood" / "campaign"
CANDIDATE = ROOT / "projects" / "reasoned-authoring-v1" / "level" / "candidate-v5.MAP"

SLIDE_TYPES = frozenset({613, 614, 615})
FENCE_TILES = frozenset({1044, 1064})


def campaign_maps() -> list[str]:
    return [
        path for path in sorted(glob.glob(str(MAPS / "*.MAP")))
        if re.match(r"^E[1-46]M[1-9]$", Path(path).stem.upper())
    ]


def have_campaign() -> bool:
    return bool(campaign_maps())


class SlidingLeafTests(unittest.TestCase):
    """A gate leaf that travels less than its own width never fully opens."""

    def test_the_leaf_repeat_never_exceeds_the_travel(self):
        from bloodmap.placement import blocked_when_open, leaf_repeat, sprite_width

        for travel in (384, 768, 1448, 1600, 2048):
            repeat = leaf_repeat(travel, 128)
            self.assertLessEqual(sprite_width(128, repeat), travel)
            self.assertEqual(blocked_when_open(travel, 128, repeat), 0)

    def test_the_campaign_builds_to_just_inside_the_limit(self):
        """E1M1 travels 1448 against a 1536 leaf; E1M5 1600 against 1792.

        Both are a shade under one, which is what says the rule is about the leaf
        clearing itself rather than about any proportion of the doorway.
        """
        from bloodmap.placement import sprite_width

        self.assertAlmostEqual(1448 / sprite_width(128, 48), 0.94, places=2)
        self.assertAlmostEqual(1600 / sprite_width(128, 56), 0.89, places=2)

    @unittest.skipUnless(CANDIDATE.exists() and have_campaign(), "no built candidate")
    def test_no_leaf_in_this_level_blocks_its_own_opening(self):
        from bloodmap.art import read_art_directory
        from bloodmap.format import read_map
        from bloodmap.placement import blocked_when_open

        art = read_art_directory(str(ROOT / "reference" / "blood"))
        if not art:
            self.skipTest("no Blood ART")
        disk = read_map(CANDIDATE)
        checked = 0
        for index, sector in enumerate(disk.sectors):
            if int(sector.fields["type"]) not in SLIDE_TYPES or sector.extra is None:
                continue
            fields = sector.extra.fields
            first, second = int(fields["marker_0"]), int(fields["marker_1"])
            if not (0 <= first < len(disk.sprites) and 0 <= second < len(disk.sprites)):
                continue
            a, b = disk.sprites[first].fields, disk.sprites[second].fields
            travel = math.hypot(int(b["x"]) - int(a["x"]), int(b["y"]) - int(a["y"]))
            for sprite in disk.sprites:
                if int(sprite.fields["sector"]) != index:
                    continue
                if int(sprite.fields["picnum"]) not in FENCE_TILES:
                    continue
                checked += 1
                self.assertEqual(
                    blocked_when_open(
                        travel, art[int(sprite.fields["picnum"])].width,
                        int(sprite.fields["x_repeat"])),
                    0, "a leaf still stands in the doorway when the gate is open")
        self.assertGreaterEqual(checked, 2)


@unittest.skipUnless(have_campaign(), "no Blood campaign maps")
class SpriteStatnumTests(unittest.TestCase):
    """Blood dispatches by statnum; a sprite on the wrong list stops working."""

    def test_a_wall_crack_belongs_on_kstatthing(self):
        """All 108 campaign cracks are on statnum 4.

        `actDamageSprite` runs its health-and-trigger path under `case
        kStatThing` and `actInit` hands out `startHealth` on the same list, so a
        crack anywhere else cannot be damaged, never reaches zero health, and
        never transmits to the charges behind it.
        """
        from bloodmap.format import read_map

        seen = set()
        total = 0
        for path in campaign_maps():
            for sprite in read_map(path).sprites:
                if int(sprite.fields["type"]) == 408:
                    seen.add(int(sprite.fields["status"]))
                    total += 1
        self.assertGreaterEqual(total, 100)
        self.assertEqual(seen, {4})

    @unittest.skipUnless(CANDIDATE.exists(), "no built candidate")
    def test_this_level_files_every_sprite_where_the_campaign_does(self):
        from bloodmap.format import read_map
        from tools.unattested_values import misfiled_sprites, statnum_distribution

        self.assertEqual(
            misfiled_sprites(read_map(CANDIDATE), statnum_distribution(str(MAPS))), [])


@unittest.skipUnless(have_campaign(), "no Blood campaign maps")
class DoorFaceTests(unittest.TestCase):
    """The face of a door is on the room's wall, not on the door sector's."""

    @unittest.skipUnless(CANDIDATE.exists(), "no built candidate")
    def test_every_z_door_shows_its_face_to_the_rooms_it_joins(self):
        """Build draws the top section of a two-sided wall from that wall's own
        `picnum` (`overpicnum` is only for masked one-way walls), and a shut
        Z-door is all top section. A door face declared as the door region's
        `wall_picnum` therefore lands on the inside of the frame -- the one set
        of surfaces the player never sees.
        """
        from bloodmap.format import read_map

        disk = read_map(CANDIDATE)
        doors = 0
        for sector in disk.sectors:
            if int(sector.fields["type"]) != 600:
                continue
            doors += 1
            start = int(sector.fields["wall_ptr"])
            count = int(sector.fields["wall_count"])
            portals = 0
            faces = set()
            for wall in range(start, start + count):
                fields = disk.walls[wall].fields
                if int(fields["next_sector"]) < 0:
                    continue
                portals += 1
                room_side = disk.walls[int(fields["next_wall"])].fields
                # both faces of the portal carry the door, so the frame reads
                # the same from either room
                faces.add(int(room_side["picnum"]))
                faces.add(int(fields["picnum"]))
            self.assertGreaterEqual(portals, 2, "a door with fewer than two ways through")
            self.assertEqual(len(faces), 1, "the two sides of the door disagree")
        self.assertGreaterEqual(doors, 4)


@unittest.skipUnless(have_campaign(), "no Blood campaign maps")
class SlidingGateDirectionTests(unittest.TestCase):
    """A gate is authored OPEN and rests shut, not the other way round.

    Reported from play: the leaves swapped sides instead of parting, leaving the
    doorway clear as they crossed. The engine says why. `trInit` runs

        if (state) busy = 65536;
        TranslateSector(i, 0, -65536, ...);   // displace by -T
        setBaseSpriteSect(i);                 // and *that* becomes the base
        TranslateSector(i, 0, busy, ...);

    so an 8192 sprite sits at `authored - T` when busy is 0 and at `authored`
    when busy is 65536; a 16384 sprite is the mirror. Resting at (1, 65536)
    therefore puts the leaves exactly where they were drawn and moves them
    *inward* on opening.
    """

    def test_the_campaign_rests_its_gates_at_zero(self):
        """Both of its two-leaf gates: state 0, busy 0."""
        from bloodmap.format import read_map

        found = 0
        for path in campaign_maps():
            disk = read_map(path)
            for sector in disk.sectors:
                if int(sector.fields["type"]) not in SLIDE_TYPES or sector.extra is None:
                    continue
                fields = sector.extra.fields
                leaves = [
                    s for s in disk.sprites
                    if int(s.fields["sector"]) == int(fields["reference"])
                    and int(s.fields["picnum"]) in FENCE_TILES
                    and int(s.fields["cstat"]) & (8192 | 16384)
                ]
                if len(leaves) < 2:
                    continue
                found += 1
                self.assertEqual(
                    (int(fields.get("state", 0)), int(fields.get("busy", 0))), (0, 0))
        self.assertGreaterEqual(found, 2)

    @unittest.skipUnless(CANDIDATE.exists(), "no built candidate")
    def test_this_levels_leaves_close_and_then_part(self):
        from bloodmap.format import read_map

        disk = read_map(CANDIDATE)
        checked = 0
        for index, sector in enumerate(disk.sectors):
            if int(sector.fields["type"]) not in SLIDE_TYPES or sector.extra is None:
                continue
            fields = sector.extra.fields
            first, second = int(fields["marker_0"]), int(fields["marker_1"])
            if not (0 <= first < len(disk.sprites) and 0 <= second < len(disk.sprites)):
                continue
            a, b = disk.sprites[first].fields, disk.sprites[second].fields
            tx = int(b["x"]) - int(a["x"])
            leaves = []
            for sprite in disk.sprites:
                sf = sprite.fields
                if int(sf["sector"]) != index or int(sf["picnum"]) not in FENCE_TILES:
                    continue
                cstat = int(sf["cstat"])
                if not cstat & (8192 | 16384):
                    continue
                drawn = int(sf["x"])
                rest = drawn - tx if cstat & 8192 else drawn + tx
                leaves.append((rest, drawn))
            if len(leaves) != 2:
                continue
            checked += 1
            leaves.sort()
            (rest_a, open_a), (rest_b, open_b) = leaves
            # shut: the two rest positions are closer together than the drawn ones
            self.assertLess(abs(rest_b - rest_a), abs(open_b - open_a),
                            "the leaves do not close when the gate is at rest")
            # and each moves outward, not across
            self.assertLess(open_a, rest_a, "a leaf travels inward on opening")
            self.assertGreater(open_b, rest_b, "a leaf travels inward on opening")
        self.assertGreaterEqual(checked, 2)


if __name__ == "__main__":
    unittest.main()


@unittest.skipUnless(CANDIDATE.exists(), "no built candidate")
class MechanismTravelTests(unittest.TestCase):
    """Every gate in this level is checked through its travel, not at rest.

    The crossing bug rested correctly at both ends and was wrong in between,
    which is invisible to anything that reads the map file as one instant.
    """

    def test_every_closure_shuts_at_rest_and_clears_when_open(self):
        from tools.inspect_mechanisms import CLOSURE_THRESHOLD, expect_closure, report

        rows = report(str(CANDIDATE), steps=7,
                      art_dir=str(ROOT / "reference" / "blood"))
        closures = 0
        for row in rows:
            if max(row["blocked"]) < CLOSURE_THRESHOLD:
                continue
            closures += 1
            self.assertEqual(
                expect_closure(row["blocked"]), [],
                "sector %d: %s" % (row["sector"], row["blocked"]))
        self.assertGreaterEqual(closures, 3)

    def test_the_profile_is_monotonic(self):
        """A parting gate uncovers steadily; it never re-blocks."""
        from tools.inspect_mechanisms import CLOSURE_THRESHOLD, report

        rows = report(str(CANDIDATE), steps=7,
                      art_dir=str(ROOT / "reference" / "blood"))
        for row in rows:
            if max(row["blocked"]) < CLOSURE_THRESHOLD:
                continue
            series = row["blocked"]
            for earlier, later in zip(series, series[1:]):
                self.assertLessEqual(
                    later, earlier + 0.01,
                    "sector %d re-blocks partway: %s" % (row["sector"], series))
