"""The two constructors Gravesend places from its levelprog TREE, read back (the city's own placers)."""

from __future__ import annotations

import importlib
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]

PLAYER = 16960


# ---------------------------------------------------------------------------
# the harness
# ---------------------------------------------------------------------------


def _assert_agrees(case, result):
    case.assertTrue(result.agrees, result.report())
    case.assertEqual(result.unmeasured, [], result.report())


# ---------------------------------------------------------------------------
# 1. bloodmap.mechanism
# ---------------------------------------------------------------------------


CITY_LEVEL = ROOT / "projects" / "blood-city" / "level"


def _city_module(name):
    """Import a blood-city level module; the directory is not a package."""
    import sys

    for path in (str(ROOT), str(CITY_LEVEL)):
        if path not in sys.path:
            sys.path.insert(0, path)
    return importlib.import_module(name)


def _tree(node_id="probe"):
    """The smallest level program a city placer will stand in."""
    from bloodmap.levelprog import LevelProgram, Style

    return LevelProgram(node_id, style=Style(
        wall_picnum=180, floor_picnum=292, ceiling_picnum=385,
        floor_z=0, clear_height=8 * PLAYER))


@unittest.skipUnless(CITY_LEVEL.is_dir(), "blood-city is not present")
class CityTreeReadBack(unittest.TestCase):
    """The two constructors blood-city places from the TREE, read back.

    The level is authored in two dialects -- the levelprog tree and flat
    `PlanarLayout` -- and the constructors are split by dialect. That split
    is what let the city's curtain drift from the zoo's: the tree placer
    consumes `curtain_spec` and lays the geometry itself, so a flat-side test
    proves nothing about it. These build the tree side and read the same
    sentence back.
    """

    def test_the_city_places_two_counter_rotating_rotors_from_the_tree(self):
        from bloodmap.readback import read_back, sentence

        turnstiles = _city_module("turnstiles")
        level = _tree()
        district = level.assembly("district")
        street = district.rect_room(
            "street", size=(24 * 1024, 8 * 1024),
            region_kwargs={"declared_zero_exit": True})
        level.set_start(street)
        built = turnstiles.pair(district, street, "probe",
                                centre_x=12 * 1024, y=4 * 1024, floor_z=0,
                                wall_picnum=180, floor_picnum=292,
                                ceiling_picnum=385)
        layout = level.compile()
        placed = turnstiles.populate(layout, built)
        self.assertEqual(placed["axes"], 2)
        self.assertEqual(placed["blades"], 8)
        compiled = layout.compile()
        disk = compiled.level.to_disk_map()
        claims = [sentence(
            "turnstile", name=rotor["name"],
            sector=compiled.allocations[rotor["region_id"]].sector_id,
            sectors=[compiled.allocations[rotor["region_id"]].sector_id],
            sector_type=615, members=[], drag={"closure": True},
            state={"changes": True}) for rotor in built]
        _assert_agrees(self, read_back(disk, claims,
                                       map_name="tree turnstiles"))

    def test_the_city_hangs_a_curtain_from_the_tree_that_reads_back_clean(self):
        # The mechanism the whole assignment is about. Its sentence is the
        # one the pre-P1 build failed: the fin deforms only itself, and its
        # fabric draws where a body can see it.
        from bloodmap.readback import read_back, sentence

        curtains = _city_module("curtains")
        level = _tree()
        district = level.assembly("district")
        house = district.rect_room(
            "house", size=(16 * 1024, 16 * 1024),
            region_kwargs={"declared_zero_exit": True})
        level.set_start(house)
        frame = house.world_frame()
        stage = (frame.dx + 4 * 1024, frame.dy + 2 * 1024,
                 frame.dx + 12 * 1024, frame.dy + 6 * 1024)
        built = curtains.hang(house, district, stage, grade=0,
                              clear=8 * PLAYER)
        layout = level.compile()
        furnished = curtains.furnish(layout, built,
                                     stage_region=house.region_id, grade=0)
        self.assertEqual(furnished["markers"], 2)
        self.assertEqual(furnished["flagged"], built["spec"]["leaves"])
        compiled = layout.compile()
        disk = compiled.level.to_disk_map()
        sector = compiled.allocations[built["room"].region_id].sector_id
        result = read_back(disk, [sentence(
            "curtain", name="stage_curtain", sector=sector, sectors=[sector],
            sector_type=614, members=[],
            wiring={"channel": curtains.CH_CURTAIN,
                    "rx_id": curtains.CH_CURTAIN},
            drag={"closure": True},
            visibility={"tiles": [146], "walkable_band": True, "per_leaf": 1},
            state={"changes": True})], map_name="tree curtain")
        _assert_agrees(self, result)


if __name__ == "__main__":
    unittest.main()
