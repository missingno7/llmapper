"""bloodmap.breach: a blown hole is ragged pieces, solid when shut, passable through its middle, under its top."""

import pathlib
import sys
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from bloodmap import breach  # noqa: E402
from bloodmap.player_space import PLAYER_PROFILES  # noqa: E402

BODY = PLAYER_PROFILES["blood"].standing_height


def _over(piece):
    """(floor above the near floor, open height) at every corner of a piece."""
    out = []
    for p in piece.outline:
        d = breach._distance(p, piece.hinge)
        floor = piece.sill - piece.floor_heinum * d / 256
        out.append((floor, piece.opening - (piece.ceiling_heinum - piece.floor_heinum) * d / 256))
    return out


class BreachTests(unittest.TestCase):
    SEEDS = [f"seed-{k}" for k in range(40)]

    def test_the_same_seed_is_the_same_hole(self):
        a = breach.ragged(1536, 512, seed="x", sill=(256, 1536), top=19968)
        b = breach.ragged(1536, 512, seed="x", sill=(256, 1536), top=19968)
        self.assertEqual(a, b)

    def test_shut_it_is_solid_everywhere_not_only_at_its_hinge(self):
        for seed in self.SEEDS:
            for piece in breach.ragged(1536, 512, seed=seed, sill=(256, 1536), top=19968):
                self.assertGreaterEqual(piece.ceiling_heinum, piece.floor_heinum, seed)

    def test_its_middle_clears_a_body_and_its_top_stays_under_the_bound(self):
        for seed in self.SEEDS:
            pieces = breach.ragged(1536, 512, seed=seed, sill=(256, 1536), top=19968)
            self.assertEqual(len(pieces), 4)
            for piece in pieces[1:-1]:
                for floor, clear in _over(piece):
                    self.assertGreaterEqual(clear, BODY + breach.HEADROOM, seed)
                    self.assertGreaterEqual(floor, 256 - 1, seed)
                    self.assertLessEqual(floor, 1536 + 1, seed)
                    self.assertLessEqual(floor + clear, 19968 + 1, seed)
            for piece in (pieces[0], pieces[-1]):
                for floor, clear in _over(piece):
                    self.assertGreaterEqual(clear, breach.SHOULDER_GAP, seed)
                    self.assertLessEqual(floor + clear, 19968 + 1, seed)

    def test_it_is_ragged(self):
        """Slanted seams, and tops that differ: the shoulders well under the middle."""
        for seed in self.SEEDS:
            pieces = breach.ragged(1536, 512, seed=seed, sill=(256, 1536), top=19968)
            slanted = sum(1 for p in pieces for a, b in ((p.outline[1], p.outline[2]), (p.outline[3], p.outline[0]))
                          if a[0] != b[0])
            self.assertGreaterEqual(slanted, 3, seed)
            middle = min(p.sill + p.opening for p in pieces[1:-1])
            self.assertLess(max(p.sill + p.opening for p in (pieces[0], pieces[-1])), middle - 2048, seed)

    def test_the_pieces_meet_along_their_seams(self):
        pieces = breach.ragged(1536, 512, seed="x")
        for left, right in zip(pieces, pieces[1:]):
            self.assertEqual((left.outline[1], left.outline[2]), (right.outline[0], right.outline[3]))
        self.assertEqual(pieces[0].outline[0][0] * pieces[0].outline[3][0], 0)   # one end on the wall's edge


if __name__ == "__main__":
    unittest.main()
