"""Every plan view uses XMapEdit's orientation: Build +Y is DOWN.

The owner reads this map in XMapEdit. Three renderers drew it mirrored --
north at the bottom, the sun's 84-degree bearing running the wrong way down
the page -- because each flipped Y to match a screen convention nobody here
uses. One assertion pins all three, and it has to be an ASYMMETRIC one:
"larger page y for larger world y" is satisfied by a mirrored drawing too, so
the fixture is a wedge whose north edge is short and whose south edge is long,
and the test asks which end of the page the long edge landed on.
"""

from __future__ import annotations

import re
import unittest
from pathlib import Path

from bloodmap.planar_layout import PlanarLayout

SKY = 3491
#: The wedge: 2048 wide at the north (y 0), 16384 wide at the south (y 16384).
NORTH_WIDTH = 2048
SOUTH_WIDTH = 16384
DEPTH = 16384


def _wedge():
    layout = PlanarLayout(name="orientation-fixture")
    layout.add_region("wedge", [(0, 0), (NORTH_WIDTH, 0),
                                (SOUTH_WIDTH, DEPTH), (0, DEPTH)],
                      floor_z=10240, ceiling_z=10240 - 6 * 32768,
                      floor_picnum=352, ceiling_picnum=SKY, wall_picnum=6,
                      parallax_ceiling=True, role="street",
                      declared_zero_exit=True)
    layout.set_player_start("wedge", x=1024, y=8192, z=10240, angle=0)
    return layout.compile().level.to_disk_map()


def _points(svg: str):
    out = set()
    for a, b, c, d in re.findall(
            r'x1="(-?[\d.]+)" y1="(-?[\d.]+)" x2="(-?[\d.]+)" '
            r'y2="(-?[\d.]+)"', svg):
        out.add((float(a), float(b)))
        out.add((float(c), float(d)))
    return out


def _row_width(points, page_y):
    row = [x for x, y in points if abs(y - page_y) < 0.51]
    return max(row) - min(row) if len(row) > 1 else 0.0


class BuildPlusYIsDown(unittest.TestCase):

    def test_the_short_north_edge_is_drawn_at_the_top(self):
        # THE FAIL-FIRST. Flipped, the 16384-wide south edge lands at the top
        # of the page and this reads 8x too wide.
        from bloodmap.analysis import render_svg

        points = _points(render_svg(_wedge(), labels=False))
        self.assertTrue(points)
        top = min(y for _x, y in points)
        bottom = max(y for _x, y in points)
        self.assertAlmostEqual(_row_width(points, top)
                               / _row_width(points, bottom),
                               NORTH_WIDTH / SOUTH_WIDTH, places=2)

    def test_no_renderer_still_flips_y(self):
        for module in ("analysis", "sector_map", "materials"):
            source = Path(f"bloodmap/{module}.py").read_text(encoding="utf-8")
            self.assertNotIn("height - margin - (y - min_y)", source,
                             f"bloodmap/{module}.py still flips Y")

    def test_sector_map_puts_the_short_edge_at_the_top_too(self):
        from bloodmap.sector_map import render_sector_map

        svg = render_sector_map(_wedge())
        body = " ".join(re.findall(r'd="([^"]+)"', svg))
        pairs = [(float(a), float(b)) for a, b in
                 re.findall(r'(-?[\d.]+) (-?[\d.]+)', body)]
        self.assertTrue(pairs)
        top = min(y for _x, y in pairs)
        bottom = max(y for _x, y in pairs)
        self.assertLess(_row_width(pairs, top), _row_width(pairs, bottom))

    def test_the_editor_s_orientation_is_named_in_the_source(self):
        source = Path("bloodmap/analysis.py").read_text(encoding="utf-8")
        self.assertIn("+Y IS DOWN", source)


if __name__ == "__main__":
    unittest.main()
