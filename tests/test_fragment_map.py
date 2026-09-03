"""`tools/fragment_map.py`: a cut that is still a map.

A fragment goes to the owner to LOOK at, so the only failure that matters is
one that makes it unopenable or unwalkable: a wall loop that leaves its
sector, a `next_sector` pointing at a sector that is no longer there, a
`next_wall` that is not reciprocal, or a start position outside the map. Each
is checked here on the three fragments that are committed, and on a cut made
fresh so the check is of the tool and not of a file.
"""

from __future__ import annotations

import pathlib
import tempfile
import unittest

FRAGMENTS = pathlib.Path("projects/e3m1-decompiled/fragments")


def _e3m1():
    from bloodmap.format import read_map
    from bloodmap.patterns import corpus_map_path

    try:
        return read_map(corpus_map_path("E3M1"))
    except Exception as error:  # pragma: no cover - corpus-dependent
        raise unittest.SkipTest(f"E3M1 is not readable here: {error}")


def _walkable(case, disk, name=""):
    """Every structural property Blood needs to open and draw the map."""
    case.assertTrue(disk.sectors, f"{name}: no sectors")
    for index, sector in enumerate(disk.sectors):
        fields = sector.fields
        first, count = int(fields["wall_ptr"]), int(fields["wall_count"])
        case.assertGreaterEqual(count, 3, f"{name}: sector {index} has {count} walls")
        owned = set(range(first, first + count))
        case.assertTrue(owned <= set(range(len(disk.walls))),
                        f"{name}: sector {index} owns walls outside the map")
        for wall_id in owned:
            wall = disk.walls[wall_id].fields
            case.assertIn(int(wall["point2"]), owned,
                          f"{name}: wall {wall_id} loops out of sector {index}")
            there = int(wall["next_sector"])
            if there < 0:
                case.assertEqual(int(wall["next_wall"]), -1,
                                 f"{name}: wall {wall_id} is sealed on one "
                                 f"side only")
                continue
            case.assertLess(there, len(disk.sectors),
                            f"{name}: wall {wall_id} leads to a sector that "
                            f"was cut away")
            back = int(wall["next_wall"])
            case.assertEqual(int(disk.walls[back].fields["next_wall"]), wall_id,
                             f"{name}: wall {wall_id} is not reciprocal")
    start = int(disk.header["start_sector"])
    case.assertTrue(0 <= start < len(disk.sectors),
                    f"{name}: the start sector is not in the map")
    for sprite in disk.sprites:
        case.assertTrue(0 <= int(sprite.fields["sector"]) < len(disk.sectors),
                        f"{name}: a sprite stands in a sector that was cut")


class ACutIsStillAMap(unittest.TestCase):
    def test_a_fresh_cut_is_walkable(self):
        from tools.fragment_map import cut

        disk = _e3m1()
        cut(disk, [3, 7, 8, 45])
        self.assertEqual(len(disk.sectors), 4)
        _walkable(self, disk, "a fresh cut")

    def test_every_wall_that_led_away_is_sealed_and_blocking(self):
        from bloodmap.format import read_map
        from bloodmap.patterns import corpus_map_path
        from tools.fragment_map import BLOCKING, cut

        before = read_map(corpus_map_path("E3M1"))
        disk = _e3m1()
        moved = cut(disk, [3, 7, 8, 45])
        sealed = [wall for wall in disk.walls
                  if int(wall.fields["next_sector"]) < 0]
        self.assertEqual(len(sealed), moved["walls_sealed"])
        for wall in sealed:
            self.assertTrue(int(wall.fields["cstat"]) & BLOCKING,
                            "a cut edge a body can walk through is a hole")
            self.assertTrue(int(wall.fields["picnum"]),
                            "a cut edge with no tile draws as a hole")
        self.assertGreater(len(before.sectors), len(disk.sectors))

    def test_the_start_is_inside_the_first_chosen_sector(self):
        from tools.fragment_map import cut

        disk = _e3m1()
        moved = cut(disk, [45, 3, 7])
        self.assertEqual(moved["start"]["sector_in_the_map"], 3,
                         "the sectors are taken in order, so the first is 3")
        self.assertEqual(int(disk.header["start_sector"]), 0)
        floor = int(disk.sectors[0].fields["floor_z"])
        self.assertEqual(int(disk.header["start_z"]), floor - 16960)

    def test_a_sector_that_is_not_in_the_map_is_refused(self):
        from tools.fragment_map import cut

        with self.assertRaises(SystemExit):
            cut(_e3m1(), [999999])

    def test_the_sidecar_carries_the_original_ids(self):
        """An answer is only useful if it lands on a sector of the whole map."""
        from tools.fragment_map import cut, sidecar

        disk = _e3m1()
        moved = cut(disk, [3, 7, 8, 45])
        text = sidecar("street", "Is this an avenue?", [3, 7, 8, 45], moved,
                       "because the classes disagree")
        self.assertIn("Is this an avenue?", text)
        self.assertIn("3, 7, 8, 45", text)
        self.assertIn("because the classes disagree", text)


class TheThreeCommittedFragments(unittest.TestCase):
    """The ones the owner is actually being handed."""

    def test_each_one_opens_and_is_walkable(self):
        from bloodmap.format import read_map

        for name in ("shade-step", "street-width", "refused-room"):
            path = FRAGMENTS / f"{name}.MAP"
            if not path.exists():
                self.skipTest(f"{name} is not committed here")
            _walkable(self, read_map(path), name)

    def test_each_one_has_a_question_and_its_original_ids(self):
        for name in ("shade-step", "street-width", "refused-room"):
            path = FRAGMENTS / f"{name}.md"
            if not path.exists():
                self.skipTest(f"{name} is not committed here")
            text = path.read_text(encoding="utf-8")
            self.assertIn("?", text, f"{name} asks nothing")
            self.assertIn("their ids in the whole map", text)

    def test_there_are_at_most_three(self):
        """The protocol's limit, and a limit worth keeping: a fragment is for
        a question no census can answer, and there are never many of those."""
        if not FRAGMENTS.exists():
            self.skipTest("no fragments here")
        self.assertLessEqual(len(list(FRAGMENTS.glob("*.MAP"))), 3)


class TheRoundTripIsNotAFragment(unittest.TestCase):
    def test_the_rebuilt_map_keeps_the_original_indices(self):
        """The two owner-facing products differ in exactly this way: a walk
        keeps every id, a fragment renumbers and says so in its sidecar."""
        from bloodmap.format import read_map

        path = pathlib.Path("projects/e3m1-decompiled/round-trip/E3M1.MAP")
        if not path.exists():
            self.skipTest("the round trip is not committed here")
        rebuilt, original = read_map(path), _e3m1()
        self.assertEqual(len(rebuilt.sectors), len(original.sectors))
        self.assertEqual(int(rebuilt.header["start_sector"]),
                         int(original.header["start_sector"]))
