"""Names where the numbers were.

v6 is v5 with its representation changed and nothing else: same 133 sectors,
same 913 walls, same 360 sprites. What differs is what the source says.

Before, a room was three picnums, a thing was a picnum and a cstat bitfield and
an invented height, and a shade was a number somebody chose. Every one of those
was a fact about Blood's ART carried in the author's head, and none of them could
be checked -- which is how the level acquired a 64x400 sky panel drawn as an
ordinary ceiling, trees a third of their proper size, aquatic weed on dry walls,
and eleven floor plates hung on walls.

Now a room is a material, a thing is a name, and both carry their rules with
them:

* a material's flat tiles must have power-of-two sides, or Build samples only
  part of them;
* a material declares whether its ceiling is the sky, because the tile and the
  parallax bit are one decision and splitting them lost three doorways;
* a thing's mounting comes from its tile's canonical cstat, so a floor-aligned
  plate cannot be described as hanging on a wall;
* a thing's size comes from the median the campaign draws it at;
* a thing is dry, wet, or either.
"""

from __future__ import annotations

import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ART = ROOT / "reference" / "blood"
V5 = ROOT / "projects" / "reasoned-authoring-v1" / "level" / "candidate-v5.MAP"
V6 = ROOT / "projects" / "reasoned-authoring-v1" / "level" / "candidate-v6.MAP"


class MaterialTests(unittest.TestCase):

    def test_every_material_would_draw(self):
        from bloodmap.surfaces import MATERIALS, check

        self.assertGreater(len(MATERIALS), 20)
        if not ART.exists():
            self.skipTest("no Blood ART")
        from bloodmap.texture_align import wall_art_sizes

        self.assertEqual([], check(wall_art_sizes()))

    def test_a_sky_material_carries_its_own_parallax(self):
        """A sky material names a sky, and names *which* sky.

        Levels do not share one. The monastery stands under `SKY_PANEL`; all 45
        of E3M1's parallax sectors name 3491 instead, and a city built out of
        these materials without `sky_tile` stood under the monastery's.
        """
        from bloodmap.surfaces import MATERIALS, SKY_PANEL, material

        outdoor = [name for name, m in MATERIALS.items() if m.sky]
        self.assertGreater(len(outdoor), 3)
        for name in outdoor:
            built = material(name)
            self.assertTrue(built["parallax_ceiling"], name)
            self.assertEqual(built["ceiling_picnum"],
                             MATERIALS[name].sky_tile or SKY_PANEL, name)

    def test_the_city_stands_under_the_city_sky(self):
        from bloodmap.surfaces import CITY_SKY, MATERIALS, SKY_PANEL, material

        self.assertEqual(material("leads")["ceiling_picnum"], CITY_SKY)
        self.assertEqual(material("courtyard")["ceiling_picnum"], SKY_PANEL)
        self.assertNotEqual(CITY_SKY, SKY_PANEL)

    def test_an_unknown_material_is_refused_by_name(self):
        from bloodmap.surfaces import SurfaceError, material

        with self.assertRaises(SurfaceError) as caught:
            material("marble")
        self.assertIn("marble", str(caught.exception))


class FurnitureTests(unittest.TestCase):

    def test_nothing_floor_aligned_claims_to_hang_on_a_wall(self):
        from bloodmap.furniture import FURNITURE, FLOOR_ALIGNED, ALIGNMENT_MASK

        for name, item in FURNITURE.items():
            if item.mounting == "wall":
                self.assertNotEqual(
                    item.cstat & ALIGNMENT_MASK, FLOOR_ALIGNED,
                    "%s is floor-aligned and mounted on a wall" % name)

    def test_a_floor_aligned_wall_mounting_is_refused_at_definition(self):
        from bloodmap.furniture import Furniture, FurnitureError

        with self.assertRaises(FurnitureError):
            Furniture("impossible", 795, 0x20 | 128, "wall")

    def test_size_comes_from_the_campaign_and_not_from_the_author(self):
        """The four trees, which is where this went wrong.

        The threshold used to read 5.0, when a "player height" in this project
        was 0x1600 -- the camera's offset from the player sprite's centre, not a
        body. In standing humans the same trees are 2.35 to 3.0, which is what a
        tree three times the height of a man measures. The trees did not change;
        the ruler did. See `bloodmap/player_space.py`.
        """
        from bloodmap.furniture import FURNITURE

        for name in ("oak", "elm", "deadwood", "pine"):
            self.assertGreater(
                FURNITURE[name].player_heights(), 2.0,
                "%s: Blood draws its trees at two to three standing humans" % name)

    def test_aquatic_things_are_labelled_aquatic(self):
        from bloodmap.furniture import wet_only

        self.assertEqual(sorted(wet_only()), [546, 660, 664, 668])

    def test_things_are_drawn_square_but_a_fence_leaf_is_not(self):
        from bloodmap.furniture import FURNITURE

        skewed = [n for n, f in FURNITURE.items() if f.aspect != 1.0]
        self.assertEqual(skewed, ["grille"])


@unittest.skipUnless(V5.exists() and V6.exists(), "both maps must be built")
class SameLevelTests(unittest.TestCase):
    """v6 began as a change of representation and then became an iteration.

    It was verified wall-for-wall against v5 at the point the vocabulary went
    in -- same 133 sectors, same 913 walls, same 360 sprites -- which is what
    established that naming the surfaces had changed nothing about the level.
    The carnival came afterwards, so what is left to check is that v6 still
    contains all of v5 and only adds.
    """

    def test_v6_keeps_everything_v5_had(self):
        from bloodmap.format import read_map

        five, six = read_map(V5), read_map(V6)
        self.assertGreater(len(six.sectors), len(five.sectors))
        self.assertGreater(len(six.sprites), len(five.sprites))
        # Not vertex-for-vertex: opening the carnival passage split the
        # refectory's north wall, which moves one of v5's vertices. What has to
        # hold is that the whole of v5's ground is still inside v6's.
        old_points = {(int(w.fields["x"]), int(w.fields["y"])) for w in five.walls}
        new_points = {(int(w.fields["x"]), int(w.fields["y"])) for w in six.walls}
        lost = old_points - new_points
        self.assertLess(len(lost) / len(old_points), 0.02, "v6 dropped %s" % lost)

    def test_v6_says_it_in_names(self):
        source = (ROOT / "projects" / "reasoned-authoring-v1" / "level"
                  / "candidate_v6.py").read_text(encoding="utf-8")
        self.assertGreater(source.count('material("'), 30)
        self.assertNotIn("_TILES = dict(", source)
        self.assertNotIn("**shades(", source)
        self.assertNotIn("**sky_shades(", source)
