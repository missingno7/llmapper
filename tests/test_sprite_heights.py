"""Trees a third of the size Blood draws them, and nothing that could see it.

Reported from play: "the maze is tiny, trees are tiny, statue is tiny, it looks
like they are for ants." Every measurement this project had said the garden was
fine. Its floor area was ordinary for the campaign, its sprite density sat on the
campaign median, its height-over-root-area was *below* the campaign median. All
of those are ratios, and the thing being read was an absolute: four tree sprites
authored at 2.8 to 3.4 player heights, on the reasoning that a tree is about
three times a person, standing in a space the campaign would fill with trees of
7.2 to 8.5.

`decoration.height_range` exists to stop exactly this and returned ``None`` for
every one of them, because `DECORATION` catalogues what the corpus files as
decoration and the corpus files its trees elsewhere. The hole was in the
coverage, not the rule: a tile the table does not know is a tile with no size
discipline at all.

So `tools.mine_sprite_heights` mines every picnum the campaign draws, without
asking what kind of thing it is -- 433 tiles with four or more observations --
and this holds the level to it.
"""

from __future__ import annotations

import glob
import json
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
MAPS = ROOT / "maps" / "blood"
ART = ROOT / "reference" / "blood"
KNOWLEDGE = ROOT / "knowledge" / "blood" / "design" / "sprite-heights-v1.json"
CANDIDATE = ROOT / "projects" / "reasoned-authoring-v1" / "level" / "candidate-v5.MAP"


def campaign_maps() -> list[str]:
    return [
        path for path in sorted(glob.glob(str(MAPS / "*.MAP")))
        if re.match(r"^E[1-46]M[1-9]$", Path(path).stem.upper())
    ]


@unittest.skipUnless(KNOWLEDGE.exists() and ART.exists(), "no mined sprite heights")
class SpriteHeightTests(unittest.TestCase):

    @classmethod
    def setUpClass(cls) -> None:
        cls.tiles = json.loads(KNOWLEDGE.read_text(encoding="utf-8"))["tiles"]

    @unittest.skipUnless(CANDIDATE.exists(), "no built candidate")
    def test_no_sprite_is_a_size_the_campaign_never_draws_it(self):
        from bloodmap.art import read_art_directory
        from bloodmap.format import read_map
        from tools.mine_sprite_heights import offenders

        art = read_art_directory(str(ART))
        if not art:
            self.skipTest("no Blood ART")
        rows = offenders(read_map(CANDIDATE), art, self.tiles)
        self.assertEqual(
            [], rows,
            "sprites drawn at a size the campaign never draws that tile: %s" % rows)

    def test_the_garden_is_planted_at_the_campaigns_own_scale(self):
        """The four trees and the bush, named, because these are the ones that
        were wrong and a range check alone would let a near miss through.

        Thresholds are in standing humans (16960 z). They were three times
        larger when the project measured everything against 0x1600, which is
        `POSTURE.eyeAboveZ` and not a body at all.
        """
        for picnum, low in ((541, 2.0), (542, 2.0), (543, 2.0), (547, 1.6), (599, 0.6)):
            band = self.tiles.get(str(picnum))
            self.assertIsNotNone(band, "tile %d fell out of the mined set" % picnum)
            self.assertGreaterEqual(
                band["median"], low,
                "tile %d: the campaign draws it at %s" % (picnum, band["median"]))

    @unittest.skipUnless(bool(campaign_maps()), "no Blood campaign maps")
    def test_the_mined_heights_still_match_the_maps(self):
        """The knowledge file is a measurement, so it has to survive re-measuring."""
        from bloodmap.art import read_art_directory
        from collections import defaultdict
        from tools.mine_sprite_heights import build, observe

        art = read_art_directory(str(ART))
        if not art:
            self.skipTest("no Blood ART")
        seen: dict[int, list[float]] = defaultdict(list)
        for path in campaign_maps():
            observe(path, art, seen)
        self.assertEqual(build(seen)["tiles"], self.tiles)

    def test_height_is_the_engines_arithmetic_and_not_the_width_formula(self):
        """`GetSpriteExtents` scales by ``yrepeat<<2`` against the tile height.

        Sprite *width* is ``x_repeat * tile_width / 4``, which divides where this
        multiplies. Confusing the two is a factor of sixteen, and it briefly made
        a correctly-sized tree look like a 0.2-player-height fault.
        """
        from bloodmap.art import read_art_directory
        from tools.mine_sprite_heights import PLAYER_HEIGHT, drawn_height

        art = read_art_directory(str(ART))
        if not art:
            self.skipTest("no Blood ART")
        tile = art[541]
        self.assertAlmostEqual(
            drawn_height({"y_repeat": 60}, tile), 60 * 4 * tile.height / PLAYER_HEIGHT)
