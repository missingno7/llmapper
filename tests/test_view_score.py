"""bloodmap.view_score: a view of one wall scores below a view of the place and its things."""

import unittest
from types import SimpleNamespace

from bloodmap.view_score import Subject, measure_view, score


def _level():
    # one square sector 0..4096 with four walls and two sprites inside it
    pts = [(0, 0), (4096, 0), (4096, 4096), (0, 4096)]
    walls = [{"fields": {"x": x, "y": y, "point2": (i + 1) % 4}} for i, (x, y) in enumerate(pts)]
    sectors = [{"fields": {"wall_ptr": 0, "wall_count": 4, "floor_z": 8192}}]
    sprites = [{"fields": {"x": 1024, "y": 1024, "sector": 0}},
               {"fields": {"x": 3000, "y": 3000, "sector": 0}}]
    return SimpleNamespace(sectors=sectors, walls=walls, sprites=sprites)


class ViewScoreTest(unittest.TestCase):
    def setUp(self):
        self.subject = Subject(_level(), (2048, 2048), 4096)

    def test_one_wall_scores_below_a_room(self):
        wall = {"frame": {"pixels": 307200, "unwritten": 0}, "surfaces": [
            {"kind": "wall", "sector": 0, "wall": 0, "picnum": 1, "pixels": 300000},
            {"kind": "floor", "sector": 0, "picnum": 2, "pixels": 7200}]}
        room = {"frame": {"pixels": 307200, "unwritten": 0}, "surfaces": [
            {"kind": "wall", "sector": 0, "wall": w, "picnum": 10 + w, "pixels": 50000}
            for w in range(4)] + [
            {"kind": "floor", "sector": 0, "picnum": 2, "pixels": 60000},
            {"kind": "ceiling", "sector": 0, "picnum": 3, "pixels": 40000},
            {"kind": "sprite", "sector": 0, "sprite": 0, "picnum": 20, "pixels": 4000},
            {"kind": "sprite", "sector": 0, "sprite": 1, "picnum": 21, "pixels": 3200}]}
        m_wall, m_room = measure_view(wall, self.subject), measure_view(room, self.subject)
        self.assertGreater(m_wall["dominant"], 0.9)
        self.assertEqual(m_room["things"], 2)
        self.assertGreater(score(m_room), score(m_wall))

    def test_far_sprite_is_not_the_place(self):
        far = Subject(_level(), (100000, 100000), 1024)
        self.assertFalse(far.owns({"kind": "sprite", "sprite": 0}))
        self.assertFalse(far.owns({"kind": "floor", "sector": 0}))


if __name__ == "__main__":
    unittest.main()
