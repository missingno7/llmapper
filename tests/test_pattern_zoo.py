"""The Pattern Zoo: registry conformance, and the map it generates.

The conformance test is what keeps the zoo current forever. A public
constructor with neither an exhibit nor a written reason to be skipped fails
here, so promoting a constructor and forgetting to show it is not possible
quietly.
"""

import importlib.util
import sys
import unittest
from pathlib import Path

ZOO = Path(__file__).resolve().parents[1] / "projects" / "pattern-zoo"


def _module(name):
    """Import a module out of the project directory.

    The directory has a hyphen in its name so it is not a package; the
    generator imports its neighbours the same way.
    """
    if str(ZOO) not in sys.path:
        sys.path.insert(0, str(ZOO))
    spec = importlib.util.spec_from_file_location(name, ZOO / f"{name}.py")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


try:
    registry = _module("registry")
    HAVE_ZOO = True
except Exception:
    HAVE_ZOO = False


#: Modules whose public constructors the zoo is answerable for.
COVERED_MODULES = ("bloodmap.mechanism", "bloodmap.vocabulary",
                   "bloodmap.doors", "bloodmap.aperture")


def public_constructors():
    """Every public callable in the covered modules, by dotted name."""
    import importlib

    found = []
    for name in COVERED_MODULES:
        module = importlib.import_module(name)
        for attribute in dir(module):
            if attribute.startswith("_"):
                continue
            value = getattr(module, attribute)
            if not callable(value) or isinstance(value, type):
                continue
            if getattr(value, "__module__", None) != name:
                continue          # re-exported from somewhere else
            found.append(f"{name}.{attribute}")
    return sorted(found)


@unittest.skipUnless(HAVE_ZOO, "the pattern-zoo project is not present")
class RegistryTest(unittest.TestCase):
    def setUp(self):
        self.exhibits = registry.exhibits()

    def test_the_zoo_has_exhibits(self):
        self.assertGreater(len(self.exhibits), 15)

    def test_every_label_is_unique(self):
        # Owner feedback arrives by label, so two exhibits sharing one would
        # merge two threads of corrections.
        labels = [item.label for item in self.exhibits]
        self.assertEqual(len(labels), len(set(labels)))

    def test_every_label_can_actually_be_written_on_a_wall(self):
        from bloodmap.lettering import tile_for

        for item in self.exhibits:
            for character in item.label:
                if character == " ":
                    continue
                self.assertIsNotNone(tile_for(character),
                                     f"{item.label}: {character!r}")

    def test_every_exhibit_says_what_to_try_and_where_it_came_from(self):
        for item in self.exhibits:
            self.assertTrue(item.try_this.strip(), item.label)
            self.assertTrue(item.provenance.strip(), item.label)

    def test_an_empty_stall_has_to_name_its_blocker(self):
        for item in self.exhibits:
            if item.is_empty():
                self.assertTrue(item.blocker.strip(), item.label)

    def test_an_exhibit_that_builds_nothing_and_says_nothing_is_refused(self):
        with self.assertRaises(ValueError):
            registry.Exhibit(label="X", about="a", try_this="b", provenance="c")

    def test_a_label_the_sign_alphabet_cannot_draw_is_refused(self):
        with self.assertRaises(ValueError):
            registry.Exhibit(label="Door #2", about="a", try_this="b",
                             provenance="c", blocker="none")


@unittest.skipUnless(HAVE_ZOO, "the pattern-zoo project is not present")
class ConformanceTest(unittest.TestCase):
    """The test that keeps the zoo current.

    Promote a constructor and this fails until it has a stall or a reason.
    """

    def test_every_public_constructor_has_an_exhibit_or_a_reason(self):
        covered = {name for item in registry.exhibits() for name in item.covers}
        missing = []
        for name in public_constructors():
            if name in covered or name in registry.SKIP:
                continue
            missing.append(name)
        self.assertEqual(missing, [], (
            "these public constructors have no exhibit and no skip reason. "
            "Add a stall to projects/pattern-zoo/registry.py, or an entry to "
            "its SKIP table saying why not: " + ", ".join(missing)))

    def test_every_skip_gives_a_reason(self):
        for name, reason in registry.SKIP.items():
            self.assertGreater(len(reason), 15, name)

    def test_the_skip_table_does_not_name_things_that_do_not_exist(self):
        # A stale skip hides a constructor that has since been renamed.
        known = set(public_constructors())
        stale = sorted(name for name in registry.SKIP if name not in known)
        self.assertEqual(stale, [], f"stale SKIP entries: {stale}")

    def test_a_covered_name_is_a_real_constructor(self):
        known = set(public_constructors())
        for item in registry.exhibits():
            for name in item.covers:
                self.assertIn(name, known, f"{item.label} covers {name}")


@unittest.skipUnless(HAVE_ZOO, "the pattern-zoo project is not present")
class GeneratedMapTest(unittest.TestCase):
    """The map is generated, and the generation is what is tested."""

    @classmethod
    def setUpClass(cls):
        build = _module("build_zoo")
        cls.layout = build.build_level()
        cls.compiled = cls.layout.compile()
        cls.disk = cls.compiled.level.to_disk_map()
        cls.build = build

    def test_it_compiles_to_a_map(self):
        self.assertGreater(len(self.disk.sectors), 40)
        self.assertGreater(len(self.disk.sprites), 50)

    def test_every_exhibit_got_a_stall(self):
        regions = set(self.layout.regions)
        for item in registry.exhibits():
            name = item.label.lower().replace(" ", "_")
            self.assertIn(f"stall:{name}", regions, item.label)

    def test_the_player_starts_at_the_entrance(self):
        self.assertIsNotNone(self.layout.player_start)
        self.assertEqual(self.layout.player_start.region_id, "region:spine")

    def test_two_room_over_room_exhibits_are_kept_apart(self):
        # Two ROR volumes in view at once make the renderer draw both. The
        # E1M1 lesson: the budget is why one sector there does two jobs.
        placed = self.build._place_exhibits(registry.exhibits())
        ror = [(row, side) for item, row, side in placed if item.room_over_room]
        for index, (row, side) in enumerate(ror):
            for other_row, other_side in ror[index + 1:]:
                if side != other_side:
                    continue
                distance = abs(row - other_row) * self.build.STALL_PITCH
                self.assertGreaterEqual(distance, self.build.ROR_SEPARATION)

    def test_the_map_round_trips_through_the_format(self):
        import tempfile

        from bloodmap.format import read_map, write_map

        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "zoo.MAP"
            write_map(self.disk, path)
            again = read_map(path)
        self.assertEqual(len(again.sectors), len(self.disk.sectors))
        self.assertEqual(len(again.sprites), len(self.disk.sprites))

    def test_the_crates_are_crates_and_not_a_mossy_rock(self):
        # 459 is a moss-grown rock. A build once shipped it as a crate.
        picnums = {int(sprite.fields["picnum"]) for sprite in self.disk.sprites}
        self.assertIn(452, picnums)
        self.assertNotIn(459, picnums)

    def test_the_tile_museum_shows_only_tiles_the_owner_graded_strong(self):
        from bloodmap.owner_anchors import load_owner_anchors

        anchors = load_owner_anchors()
        shown = {int(placement.picnum) for placement in self.layout.placements
                 if placement.placement_id.startswith("museum:")}
        self.assertTrue(shown)
        self.assertTrue(shown <= set(anchors.naming_picnums()))


if __name__ == "__main__":
    unittest.main()
