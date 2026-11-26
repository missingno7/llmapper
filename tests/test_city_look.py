"""A frame shows what a player sees: the viewer hides what the game hides.

The owner, 2026-11-18: "When you are viewing the level look you should be
hiding these control things which are normally invisible like player
starts, stack markers, sounds, etc."
"""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

E1M1 = Path("maps/blood/campaign/E1M1.MAP")


@unittest.skipUnless(E1M1.exists(), "no E1M1")
class AsPlayedTests(unittest.TestCase):
    def test_starts_markers_sounds_and_exploders_are_hidden(self):
        from bloodmap import visual as look
        from bloodmap.format import read_map

        with tempfile.TemporaryDirectory() as folder:
            played = read_map(look.as_played(E1M1, folder))
        original = read_map(E1M1)
        seen = [s.fields for s in played.sprites
                if not int(s.fields["cstat"]) & 32768]
        for f in seen:
            self.assertNotIn(int(f["type"]), look.HIDDEN_TYPES, f)
        #: the eight numbered start flags of its crypt among them
        starts = [s for s in original.sprites
                  if int(s.fields["type"]) in (1, 2)]
        self.assertGreaterEqual(len(starts), 8)
        #: and nothing a player does see is touched: the plaques stay
        self.assertEqual(
            sum(1 for f in seen if int(f["picnum"]) == 128),
            sum(1 for s in original.sprites
                if int(s.fields["picnum"]) == 128
                and not int(s.fields["cstat"]) & 32768))

    def test_a_lit_torch_is_drawn_lit_with_its_flame(self):
        #: view.cpp:2930: a kDecorationTorch with no XSPRITE (or state 1)
        #: is drawn as the next tile with a flame (2101) at its top; the
        #: spider lair's readers saw "empty brown sconces" without this
        from bloodmap.corpus import corpus_map_path
        from bloodmap.format import read_map
        from bloodmap.visual import TORCH_FLAME, TORCH_TYPE, as_played

        source = corpus_map_path("E2M1")
        original = read_map(source)
        torches = [s.fields for s in original.sprites if int(s.fields["type"]) == TORCH_TYPE
                   and not int(s.fields["cstat"]) & 32768 and s.extra is None]
        self.assertTrue(torches)
        with tempfile.TemporaryDirectory() as folder:
            played = read_map(as_played(source, folder))
        lit = [s.fields for s in played.sprites if int(s.fields["type"]) == TORCH_TYPE
               and not int(s.fields["cstat"]) & 32768 and s.extra is None]
        self.assertEqual(sorted(int(f["picnum"]) for f in lit),
                         sorted(int(f["picnum"]) + 1 for f in torches))
        flames = [s.fields for s in played.sprites if int(s.fields["picnum"]) == TORCH_FLAME
                  and int(s.fields["shade"]) == -128]
        self.assertGreaterEqual(len(flames), len(torches))
        for torch in lit:
            self.assertTrue(any((f["x"], f["y"]) == (torch["x"], torch["y"])
                                and int(f["z"]) < int(torch["z"]) for f in flames))

    def test_a_place_can_be_seen_with_nobody_and_nothing_in_it(self):
        #: the owner: "check how it looks like without enemies and pickups
        #: for example to get rid of visual noise"
        from bloodmap import visual as look
        from bloodmap.format import read_map

        with tempfile.TemporaryDirectory() as folder:
            path = look.as_played(E1M1, folder, empty=True)
            self.assertEqual(path.name, "as-empty.MAP")
            empty = read_map(path)
        original = read_map(E1M1)
        seen = [s.fields for s in empty.sprites
                if not int(s.fields["cstat"]) & 32768]
        for f in seen:
            self.assertNotIn(int(f["type"]), look.EMPTY_TYPES, f)
        #: E1M1 has enemies and pickups to hide
        self.assertGreater(sum(1 for s in original.sprites if int(
            s.fields["type"]) in range(200, 255)), 10)
        self.assertGreater(sum(1 for s in original.sprites if int(
            s.fields["type"]) in range(100, 150)), 3)
        #: decoration is the room and stays: every type-0 sprite a player
        #: sees is still there (the flames the engine adds over lit torches,
        #: `visual.light_torches`, come after the map's own and are not
        #: counted)
        def decor(disk):
            return sum(1 for s in disk.sprites[:len(original.sprites)]
                       if int(s.fields["type"]) == 0
                       and int(s.fields.get("status", 0)) != 10
                       and not int(s.fields["cstat"]) & 32768)
        self.assertEqual(decor(empty), decor(original))


if __name__ == "__main__":
    unittest.main()
