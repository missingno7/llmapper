"""How high a control hangs, and what its art says it is.

Two faults, one of them self-inflicted.

**The heights.** `place_on_wall` takes `height_player_heights`, denominated in
the player profile's `standing_height`. Correcting that constant from 0x1600
(5632) to the drawn body (16960) multiplied every wall-mounted sprite in the
level by 3.01 without touching a single authored number. `SWITCH_HEIGHT = 2.18`
had been 12,277 z -- right in the campaign's band -- and silently became 36,972.
The switches were correct before the unit fix and the unit fix broke them.

**The exit.** `kChannelLevelExitNormal = 4` was wired correctly all along, on a
sprite wearing tile 1070 -- the ordinary lever the campaign uses 274 times to
open doors. 41 of the campaign's 50 exits wear tile 318 instead, which appears
only 5 times anywhere else in 43 maps. The level ended without ever saying which
switch ended it.
"""

from __future__ import annotations

import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CANDIDATE = ROOT / "projects" / "reasoned-authoring-v1" / "level" / "candidate-v7.MAP"


class VocabularyTests(unittest.TestCase):

    def test_the_types_are_the_engine_s(self):
        """NBlood common_game.h:231-236."""
        from bloodmap.switches import SWITCH_TYPES

        self.assertEqual(sorted(SWITCH_TYPES), [20, 21, 22, 23])
        self.assertEqual(SWITCH_TYPES[20], "toggle")

    def test_the_exit_channel_is_the_engine_s(self):
        """NBlood eventq.h:30-31."""
        from bloodmap.switches import CHANNEL_EXIT, CHANNEL_SECRET_EXIT

        self.assertEqual(CHANNEL_EXIT, 4)
        self.assertEqual(CHANNEL_SECRET_EXIT, 5)

    def test_a_pressed_switch_sits_just_under_the_eye(self):
        from bloodmap.switches import (EYE_HEIGHT, PLAYER_HEIGHT, PRESSED_HEIGHT)

        self.assertAlmostEqual(PRESSED_HEIGHT, 0.79, places=2)
        self.assertLess(PRESSED_HEIGHT, EYE_HEIGHT / PLAYER_HEIGHT)

    def test_a_shot_switch_is_more_than_twice_as_high(self):
        from bloodmap.switches import PRESSED_HEIGHT, SHOT_HEIGHT

        self.assertGreater(SHOT_HEIGHT, 2 * PRESSED_HEIGHT)

    def test_the_two_tile_families_do_not_overlap(self):
        """Height is only half the message; the art is the other half."""
        from bloodmap.switches import PRESSED_TILES, SHOT_TILES

        self.assertEqual(set(PRESSED_TILES) & set(SHOT_TILES), set())

    def test_a_shot_tile_is_refused_for_a_pressed_switch(self):
        from bloodmap.switches import SHOT_TILES, SwitchError, pressed_switch

        with self.assertRaises(SwitchError) as caught:
            pressed_switch(tile=SHOT_TILES[0], tx_id=100)
        self.assertIn("press", str(caught.exception))

    def test_the_exit_switch_carries_the_exit_tile_and_channel(self):
        from bloodmap.switches import CHANNEL_EXIT, EXIT_TILE, exit_switch

        built = exit_switch()
        self.assertEqual(built["picnum"], EXIT_TILE)
        self.assertEqual(built["behavior"]["tx_id"], CHANNEL_EXIT)
        self.assertEqual(built["height_player_heights"],
                         __import__("bloodmap.switches", fromlist=["x"]).PRESSED_HEIGHT)

    def test_the_secret_exit_uses_its_own_channel(self):
        from bloodmap.switches import CHANNEL_SECRET_EXIT, EXIT_TILE, exit_switch

        built = exit_switch(secret=True)
        self.assertEqual(built["behavior"]["tx_id"], CHANNEL_SECRET_EXIT)
        self.assertEqual(built["picnum"], EXIT_TILE)


@unittest.skipUnless(CANDIDATE.exists(), "no built candidate")
class CandidateSwitchTests(unittest.TestCase):

    def test_every_control_can_be_worked(self):
        from bloodmap.format import read_map
        from bloodmap.switches import check

        self.assertEqual([], check(read_map(CANDIDATE)))

    def test_the_level_has_an_exit_switch(self):
        from bloodmap.format import read_map
        from bloodmap.switches import CHANNEL_EXIT, SWITCH_TYPES, _extra

        disk = read_map(CANDIDATE)
        exits = [s for s in disk.sprites
                 if int(s.fields["type"]) in SWITCH_TYPES
                 and int(_extra(s).get("tx_id", 0) or 0) == CHANNEL_EXIT]
        self.assertEqual(len(exits), 1, "a level needs exactly one way out")

    def test_no_wall_sprite_sits_above_the_campaign_for_its_tile(self):
        """The general form of the fault: the unit correction raised every
        wall-mounted sprite by 3.01x, not just the switches.

        Measured per tile against the campaign, with letter tiles pooled --
        individually they carry one to seventeen samples each, which is not a
        distribution.
        """
        import glob
        import re
        from collections import defaultdict
        from bloodmap.format import read_map
        from bloodmap.player_space import PLAYER_PROFILES

        body = PLAYER_PROFILES["blood"].standing_height
        letters = set(range(3808, 3834))
        maps = [p for p in sorted(glob.glob(str(ROOT / "maps" / "blood" / "*.MAP")))
                if re.match(r"^E[1-46]M[1-9]$", Path(p).stem.upper())]
        if not maps:
            self.skipTest("no Blood campaign maps")

        campaign = defaultdict(list)
        for path in maps:
            disk = read_map(path)
            for sprite in disk.sprites:
                fields = sprite.fields
                if int(fields["cstat"]) & 0x30 != 0x10:
                    continue
                sector = int(fields["sector"])
                if not 0 <= sector < len(disk.sectors):
                    continue
                floor = int(disk.sectors[sector].fields["floor_z"])
                picnum = int(fields["picnum"])
                key = "letters" if picnum in letters else picnum
                campaign[key].append((floor - int(fields["z"])) / body)

        disk = read_map(CANDIDATE)
        offenders = []
        for index, sprite in enumerate(disk.sprites):
            fields = sprite.fields
            if int(fields["cstat"]) & 0x30 != 0x10:
                continue
            sector = int(fields["sector"])
            if not 0 <= sector < len(disk.sectors):
                continue
            picnum = int(fields["picnum"])
            key = "letters" if picnum in letters else picnum
            band = campaign.get(key)
            if not band or len(band) < 4:
                continue
            band = sorted(band)
            p95 = band[min(len(band) - 1, int(0.95 * (len(band) - 1)))]
            height = (int(disk.sectors[sector].fields["floor_z"])
                      - int(fields["z"])) / body
            if height > p95 + 0.15:
                offenders.append((index, picnum, round(height, 2), round(p95, 2)))
        self.assertEqual([], offenders,
                         "wall sprites above the campaign's p95 for their tile: %s"
                         % offenders)

    def test_the_registry_grades_both_conventions(self):
        from bloodmap.rules import load_grades

        grades = load_grades()
        reach = grades.get("pressed-switch-is-in-reach")
        exit_tile = grades.get("exit-switch-wears-the-exit-tile")
        if reach is None or exit_tile is None:
            self.skipTest("rules not graded")
        self.assertEqual(reach.severity, "warning")
        self.assertEqual(exit_tile.severity, "note")
