"""A zero with a zero denominator is untested, never green.

Slice 2h's manifest said "light domain: admits 104, refuses 0" and every
reader of it -- me included -- read that as the rule holding. Nothing in that
map was a mechanism, an insert or a holder, so the rule was never asked. The
line was true and it was empty.
"""

from __future__ import annotations

import unittest

from bloodmap.overlay import (
    LIGHT_DOMAIN, refusal_denominator, refusal_line)
from bloodmap.planar_layout import PlanarLayout

SKY = 3491


def _two_regions(*, mover: bool):
    """Two road pieces under sky; optionally one of them is a mover."""
    layout = PlanarLayout(name="denominator-fixture")
    for index, x0 in enumerate((0, 8192)):
        layout.add_region(
            f"piece{index}",
            [(x0, 0), (x0 + 8192, 0), (x0 + 8192, 8192), (x0, 8192)],
            floor_z=10240, ceiling_z=10240 - 6 * 32768,
            floor_picnum=352, ceiling_picnum=SKY, wall_picnum=6,
            parallax_ceiling=True, role="street",
            type=600 if (mover and index == 1) else 0)
    layout.add_connection("join", "piece0", "piece1", role="portal",
                          a1=(8192, 0), a2=(8192, 8192))
    layout.set_player_start("piece0", x=4096, y=4096, z=10240, angle=0)
    return layout.compile().level.to_disk_map()


class AZeroNeedsItsDenominator(unittest.TestCase):

    def test_nothing_eligible_reads_as_untested(self):
        # THE FAIL-FIRST, and it is the line slice 2h actually shipped.
        disk = _two_regions(mover=False)
        result = refusal_denominator(disk, LIGHT_DOMAIN,
                                     range(len(disk.sectors)))
        self.assertEqual(result["refused"], 0)
        self.assertEqual(result["eligible"], 0)
        self.assertEqual(result["verdict"], "untested")
        self.assertIn("UNTESTED", refusal_line(result))

    def test_a_mechanism_makes_the_denominator_real(self):
        disk = _two_regions(mover=True)
        result = refusal_denominator(disk, LIGHT_DOMAIN,
                                     range(len(disk.sectors)))
        self.assertEqual(result["eligible"], 1)
        self.assertEqual(result["verdict"], "tested")
        self.assertGreaterEqual(result["refused"], 1)
        self.assertNotIn("UNTESTED", refusal_line(result))

    def test_the_eligible_region_names_why_it_was_at_risk(self):
        disk = _two_regions(mover=True)
        result = refusal_denominator(disk, LIGHT_DOMAIN,
                                     range(len(disk.sectors)))
        self.assertEqual(result["eligible_regions"][0]["flags"],
                         ["has_sector_type"])

    def test_a_region_refused_for_its_ceiling_is_not_eligible(self):
        # Refused and eligible are different questions: a region with no sky
        # is refused, but it was never a mechanism, so it does not make the
        # denominator real.
        disk = _two_regions(mover=False)
        disk.sectors[1].fields["ceiling_stat"] = 0
        result = refusal_denominator(disk, LIGHT_DOMAIN,
                                     range(len(disk.sectors)))
        self.assertEqual(result["refused"], 1)
        self.assertEqual(result["eligible"], 0)
        self.assertEqual(result["verdict"], "untested")


if __name__ == "__main__":
    unittest.main()
