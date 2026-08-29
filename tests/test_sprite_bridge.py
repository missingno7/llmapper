"""Floor-sprite decks have geometry too: test their whole footprint."""

from __future__ import annotations

import unittest

from bloodmap.planar_layout import PlanarLayout
from bloodmap.prefab import PrefabError, _bridge_slabs_overlap, sprite_bridge


def host() -> PlanarLayout:
    layout = PlanarLayout(name="sprite-bridge")
    # Clockwise outer loop; the inner loop is the inverse winding, as a hole.
    layout.add_region(
        "region:host", [(0, 0), (10_000, 0), (10_000, 3_000), (0, 3_000)],
        holes=[[(4_000, 1_000), (4_000, 2_000),
                (6_000, 2_000), (6_000, 1_000)]],
    )
    return layout


class SpriteBridgeTests(unittest.TestCase):
    def test_panels_tile_the_named_span_without_positive_area_overlap(self):
        layout = host()
        ids = sprite_bridge(layout, "deck", "region:host",
                            start=(1_000, 400), end=(9_000, 400), z=0,
                            repeat=20)

        self.assertGreater(len(ids), 1)
        self.assertEqual(sum(item.x_repeat for item in layout.placements), 250)
        panels = [
            {"x": item.x, "y": item.y, "width": item.x_repeat * 32.0}
            for item in layout.placements
        ]
        self.assertFalse(any(
            _bridge_slabs_overlap(left, right, 1.0, 0.0)
            for left, right in zip(panels, panels[1:])
        ))

    def test_rejects_a_panel_that_would_cross_a_hole_or_a_wall(self):
        with self.assertRaisesRegex(PrefabError, "wall or hole"):
            sprite_bridge(host(), "deck", "region:host",
                          start=(1_000, 1_500), end=(9_000, 1_500), z=0)
        with self.assertRaisesRegex(PrefabError, "wall or hole"):
            sprite_bridge(host(), "edge", "region:host",
                          start=(1_000, 200), end=(9_000, 200), z=0,
                          repeat=48)

    def test_rejects_the_old_overlap_mode(self):
        with self.assertRaisesRegex(PrefabError, "overlapping floor sprites"):
            sprite_bridge(host(), "deck", "region:host",
                          start=(1_000, 400), end=(9_000, 400), z=0,
                          overlap=0.92)
