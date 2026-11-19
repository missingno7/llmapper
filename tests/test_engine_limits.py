"""One statement of the engine's limits, and what crossing each one means.

The target is NBlood, which compiles with Build's V8 limits. A map past those
loads nowhere and is an error. A map past the original DOS game's limits loads
in the ports and not in the game as shipped: a warning, because how big the
map is allowed to be is the author's decision. Until 2026-11-19
`validate_build_ir` enforced the first set and `validate_map` the second, so
one map was valid or not depending on which validator read it.
"""

from __future__ import annotations

import copy
import unittest

from bloodmap.analysis import BLOOD_X_LIMITS, validate_map
from bloodmap.build_ir import BUILD_LIMITS, VANILLA_LIMITS, limit_diagnostics
from tests.helpers import synthetic_map


def _with_sectors(count: int):
    disk = synthetic_map()
    disk.sectors = [copy.deepcopy(disk.sectors[0]) for _ in range(count)]
    disk.header["num_sectors"] = count
    return disk


def _count_codes(disk) -> set[tuple[str, str]]:
    return {(item.severity, item.code) for item in validate_map(disk)
            if item.code.startswith("count-")}


class LimitTests(unittest.TestCase):
    def test_the_figures_are_the_engines_own(self):
        """NBlood build.h:48-54 and db.h:25-27."""
        self.assertEqual(BUILD_LIMITS, {"sectors": 4096, "walls": 16384, "sprites": 16384})
        self.assertEqual(VANILLA_LIMITS, {"sectors": 1024, "walls": 8192, "sprites": 4096})
        self.assertEqual(BLOOD_X_LIMITS, {"sector": 4096, "wall": 16384, "sprite": 16384})

    def test_a_map_at_the_original_limit_says_nothing(self):
        self.assertEqual(_count_codes(_with_sectors(VANILLA_LIMITS["sectors"])), set())

    def test_past_the_original_limit_is_a_warning_and_not_an_error(self):
        self.assertEqual(_count_codes(_with_sectors(VANILLA_LIMITS["sectors"] + 1)),
                         {("warning", "count-vanilla-limit")})

    def test_past_the_ports_limit_is_an_error(self):
        self.assertEqual(_count_codes(_with_sectors(BUILD_LIMITS["sectors"] + 1)),
                         {("error", "count-limit")})

    def test_both_validators_ask_the_same_question(self):
        """The shared one is what `validate_build_ir` calls too."""
        self.assertEqual(
            [(severity, code) for severity, code, _message in limit_diagnostics(
                {"sectors": 1025, "walls": 16385, "sprites": 10})],
            [("warning", "count-vanilla-limit"), ("error", "count-limit")])

    def test_an_extension_index_is_in_range_up_to_the_ports_limit(self):
        disk = synthetic_map()
        sprite = disk.sprites[0]
        sprite.fields["extra"] = 5000            # past the old 4096, inside NBlood's
        codes = {item.code for item in validate_map(disk)}
        self.assertNotIn("extra-range", codes)
        sprite.fields["extra"] = BLOOD_X_LIMITS["sprite"]
        self.assertIn("extra-range", {item.code for item in validate_map(disk)})


if __name__ == "__main__":
    unittest.main()
