"""Which key a door wants, and how the player is told.

The convention: a keyed door in Blood keeps its requirement in the XSECTOR,
where the engine reads it and the player cannot. What the player reads is a
placard -- one of six 58x58 emblems in a shared spiked frame, hung beside the
door.

This level had none, and not by oversight. An earlier iteration had used all six
tiles as ordinary wall furniture -- a key symbol on the chapter house, the
reliquary, the ossuary and every "emblem" in the map -- so it signposted eight
keyed doors while holding one key. The fix at the time was to delete the tiles
outright, which stopped the level lying and left its one genuine lock with
nothing on it at all. Both halves are the same fault: a placard is not
decoration, it is a statement about a lock, and it has to be true.
"""

from __future__ import annotations

import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CANDIDATE = ROOT / "projects" / "reasoned-authoring-v1" / "level" / "candidate-v7.MAP"


class EmblemTests(unittest.TestCase):

    def test_every_key_has_an_emblem(self):
        from bloodmap.keys import EMBLEM_NAME, KEY_EMBLEM

        self.assertEqual(sorted(KEY_EMBLEM), [1, 2, 3, 4, 5, 6])
        for tile in KEY_EMBLEM.values():
            self.assertIn(tile, EMBLEM_NAME)

    def test_the_mapping_is_the_one_the_campaign_uses(self):
        """Derived by pairing each placard with the nearest keyed thing across
        all 43 maps, not from a table anybody remembered. The votes were
        67-to-2, 26-to-1, 27-to-1, and unanimous for the last three."""
        from bloodmap.keys import KEY_EMBLEM

        self.assertEqual(KEY_EMBLEM[1], 2540)   # skull
        self.assertEqual(KEY_EMBLEM[2], 2541)   # eye
        self.assertEqual(KEY_EMBLEM[3], 2542)   # flame
        self.assertEqual(KEY_EMBLEM[4], 2543)   # dagger
        self.assertEqual(KEY_EMBLEM[5], 2544)   # spider
        self.assertEqual(KEY_EMBLEM[6], 2545)   # moon

    def test_a_key_blood_does_not_have_is_refused(self):
        from bloodmap.keys import KeyError_, emblem_for

        with self.assertRaises(KeyError_) as caught:
            emblem_for(9)
        self.assertIn("skull", str(caught.exception))

    def test_the_placard_is_hung_the_way_the_campaign_hangs_it(self):
        from bloodmap.keys import PLACARD_CSTAT, PLACARD_HEIGHT, PLACARD_REPEAT

        self.assertAlmostEqual(PLACARD_HEIGHT, 0.845, places=3)
        self.assertEqual(PLACARD_REPEAT, 32)
        # wall-aligned(16) + one-sided(64) + centred(128) + hitscan(256)
        self.assertEqual(PLACARD_CSTAT, 16 | 64 | 128 | 256)


class SigningTests(unittest.TestCase):

    def _layout(self, key=1):
        from bloodmap.planar_layout import PlanarLayout

        U = 384
        layout = PlanarLayout(name="keytest")
        layout.add_region(
            "region:hall", [(0, 0), (20 * U, 0), (20 * U, 14 * U), (0, 14 * U)],
            floor_z=0, ceiling_z=-3 * 16960,
            wall_picnum=110, floor_picnum=2448, ceiling_picnum=285)
        layout.add_region(
            "region:gate", [(20 * U, 5 * U), (22 * U, 5 * U),
                            (22 * U, 9 * U), (20 * U, 9 * U)],
            # Open, not shut: a fixture whose door has floor == ceiling leaves
            # the hall and the vault with no walkable route between them, and
            # the compiler rejects the *map*, which says nothing about placards.
            floor_z=0, ceiling_z=-2 * 16960, type=600,
            wall_picnum=449, floor_picnum=2448, ceiling_picnum=449,
            sector_behavior={"key": key, "trigger_push": 1})
        layout.add_region(
            "region:vault", [(22 * U, 0), (36 * U, 0), (36 * U, 14 * U), (22 * U, 14 * U)],
            floor_z=0, ceiling_z=-3 * 16960,
            wall_picnum=194, floor_picnum=294, ceiling_picnum=454)
        layout.add_connection("c:hall_gate", "region:hall", "region:gate",
                              a1=(20 * U, 5 * U), a2=(20 * U, 9 * U), min_width=1024)
        layout.add_connection("c:gate_vault", "region:gate", "region:vault",
                              a1=(22 * U, 5 * U), a2=(22 * U, 9 * U), min_width=1024)
        layout.set_player_start("region:hall", x=4 * U, y=7 * U, z=0)
        return layout

    def test_a_keyed_door_gets_its_emblem(self):
        from bloodmap.keys import KEY_EMBLEM, sign_the_locks

        layout = self._layout(key=3)
        signed = sign_the_locks(layout)
        self.assertEqual(len(signed), 1)
        self.assertEqual(signed[0]["key"], 3)
        self.assertEqual(signed[0]["emblem"], "flame")
        self.assertGreater(signed[0]["placards"], 0)
        tiles = {p.picnum for p in layout.placements
                 if p.placement_id.startswith("placard_")}
        self.assertEqual(tiles, {KEY_EMBLEM[3]})

    def test_an_unkeyed_level_gets_no_placards(self):
        """The half of the fault that put a key symbol on the ossuary."""
        from bloodmap.keys import sign_the_locks

        layout = self._layout(key=0)
        layout.regions["region:gate"].sector_behavior = {"trigger_push": 1}
        self.assertEqual(sign_the_locks(layout), [])
        self.assertEqual([p for p in layout.placements
                          if p.placement_id.startswith("placard_")], [])

    def test_the_placard_lands_on_solid_wall(self):
        from bloodmap.keys import sign_the_locks

        layout = self._layout()
        sign_the_locks(layout)
        layout.compile()          # the compiler refuses a sprite over an opening

    def test_it_hangs_at_the_corpus_height(self):
        from bloodmap.keys import PLACARD_HEIGHT, sign_the_locks

        layout = self._layout()
        sign_the_locks(layout)
        placards = [p for p in layout.placements
                    if p.placement_id.startswith("placard_")]
        self.assertTrue(placards)
        for placard in placards:
            self.assertAlmostEqual(
                placard.anchor["height_player_heights"], PLACARD_HEIGHT, places=3)


@unittest.skipUnless(CANDIDATE.exists(), "no built candidate")
class CandidateKeyTests(unittest.TestCase):

    def test_the_locks_and_the_placards_agree(self):
        """`check` catches three disagreements: a placard by no lock, a lock
        with no placard, and a placard whose emblem is the wrong key."""
        from bloodmap.format import read_map
        from bloodmap.keys import check

        self.assertEqual([], check(read_map(CANDIDATE)))

    def test_the_level_still_holds_the_key_it_asks_for(self):
        from bloodmap.format import read_map
        from bloodmap.keys import KEY_ITEM_TYPE
        from tools.mine_keys import key_of

        disk = read_map(CANDIDATE)
        wanted = {key_of(s) for s in disk.sectors if key_of(s)}
        held = {int(s.fields["type"]) for s in disk.sprites}
        for key in wanted:
            self.assertIn(KEY_ITEM_TYPE[key], held,
                          "the level locks a door with key %d and never gives "
                          "the player one" % key)

    def test_the_registry_grades_the_convention(self):
        from bloodmap.rules import load_grades

        grade = load_grades().get("keyed-door-says-which-key")
        if grade is None:
            self.skipTest("rules not graded")
        # Blood leaves about one keyed sector in six unmarked, so this is a
        # convention rather than a law -- but a strong one.
        self.assertEqual(grade.severity, "note")
        self.assertLess(grade.rate, 0.25)
