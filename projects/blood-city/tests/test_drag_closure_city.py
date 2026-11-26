"""The DragPoint closure on the built city: its curtain no longer drags the auditorium."""

import unittest
from pathlib import Path

from tests.helpers import require_map

CITY = Path("projects/blood-city/level/blood-city-current.MAP")


def _map(path: Path):
    return require_map(path)


class OriginalsTest(unittest.TestCase):
    """The closure on maps whose motion sets are known."""

    def test_the_city_curtain_no_longer_drags_the_auditorium(self):
        # This is the case that motivated the closure, and the closure now
        # measures its repair. The supervisor measured the carved fin on
        # 2026-09-01: hole and room were the SAME polygon, all eight walls
        # paired as portals, and the auditorium's hole loop travelled with
        # the curtain (area 983040 -> 1302528). P1 rebuilt the proscenium as
        # a DOORWAY rect with a solid void notch, so the closure is the fin
        # alone -- the fin/isolation technique DOOR-CURTAINS s3 teaches.
        #
        # It is deliberately not written as `isolated is True` and nothing
        # else: a curtain that starts dragging the house again would be
        # caught by the second half whether or not it inverted.
        from bloodmap.motion_sim import closure_health

        disk = _map(CITY)
        curtains = []
        for sector_id, sector in enumerate(disk.sectors):
            if int(sector.fields["type"]) != 614 or sector.extra is None:
                continue
            start = int(sector.fields["wall_ptr"])
            count = int(sector.fields["wall_count"])
            if any(int(disk.walls[w].fields["picnum"]) == 146
                   for w in range(start, start + count)):
                curtains.append(sector_id)
        if not curtains:
            self.skipTest("the city has no curtain wearing tile 146")
        for sector_id in curtains:
            health = closure_health(disk, sector_id)
            self.assertTrue(health["isolated"],
                            f"s{sector_id} drags {health['neighbours']}")
            self.assertEqual([r for r in health["loops"] if not r["own"]], [])
            self.assertTrue(health["healthy"], health["problems"])
            self.assertEqual(health["disagreements"], [])


if __name__ == "__main__":
    unittest.main()
