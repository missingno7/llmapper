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
                   "bloodmap.doors", "bloodmap.aperture",
                   "bloodmap.furniture", "bloodmap.owner_anchors")


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
        self.assertGreater(len(self.exhibits), 25)

    def test_no_two_exhibits_demonstrate_the_same_constructor(self):
        # The owner found repeats in v1. Two exhibits covering one
        # constructor is two chances to letter the same thing.
        seen = {}
        for item in self.exhibits:
            for name in item.covers:
                self.assertNotIn(name, seen,
                                 f"{item.label} and {seen.get(name)} both "
                                 f"claim {name}")
                seen[name] = item.label

    def test_a_hand_composed_habitat_says_what_it_hand_composed(self):
        # The habitat is itself a claim about correct usage. Where one was
        # assembled by hand rather than by a constructor that owns it, the
        # registry has to name it, so the promotion audit picks it up.
        for item in self.exhibits:
            for note in item.hand_composed:
                self.assertGreater(len(note), 20, item.label)

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
class SectionTest(unittest.TestCase):
    """v3's shape: sections, not a corridor of cells."""

    def setUp(self):
        self.sections = registry.sections()

    def test_the_zoo_is_made_of_sections(self):
        self.assertGreaterEqual(len(self.sections), 5)
        for section in self.sections:
            self.assertTrue(section.exhibits, section.label)

    def test_a_section_with_no_exhibits_is_refused(self):
        with self.assertRaises(ValueError):
            registry.Section(label="EMPTY", about="a", skin=(1, 2, 3),
                             exhibits=())

    def test_every_pier_can_carry_its_own_label(self):
        # A clipped label is how an exhibit loses the identity that owner
        # feedback arrives by, so the pier is sized from the word.
        for item in registry.exhibits():
            self.assertGreaterEqual(item.pier(), registry.min_bay(item.label),
                                    item.label)
            if item.blocker:
                self.assertGreaterEqual(item.pier(),
                                        registry.min_bay(item.blocker),
                                        item.label)

    def test_every_section_is_at_least_the_campaign_median_height(self):
        # v1 gave every stall 1.5 player heights and the owner walked it and
        # found the facades had no room to be facades. The campaign median is
        # 33280 -- 1.96 heights -- from norms-v1 shape.median_height.
        for section in self.sections:
            self.assertGreaterEqual(section.clear, registry.MEDIAN_CLEAR,
                                    section.label)


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
        self.assertGreater(len(self.disk.sectors), 60)
        self.assertGreater(len(self.disk.sprites), 200)

    def test_every_section_got_a_room(self):
        regions = set(self.layout.regions)
        for section in registry.sections():
            self.assertIn(f"section:{section.region_prefix()}", regions,
                          section.label)

    def test_every_exhibit_got_a_label_sprite(self):
        placed = {p.placement_id for p in self.layout.placements}
        for item in registry.exhibits():
            #: `write_on_wall` numbers one placement per letter.
            wanted = f"label:{item.region_prefix()}"
            self.assertTrue(
                any(pid.startswith(wanted) for pid in placed), item.label)

    def test_the_player_starts_at_the_entrance(self):
        self.assertIsNotNone(self.layout.player_start)
        self.assertEqual(self.layout.player_start.region_id, "region:spine")

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
        # In v3 a crate is a sector volume, so the tile is on a *wall*.
        walls = {int(wall.fields["picnum"]) for wall in self.disk.walls}
        sprites = {int(s.fields["picnum"]) for s in self.disk.sprites}
        self.assertIn(452, walls)
        self.assertNotIn(459, walls | sprites)

    def test_the_doors_are_real_sectors_and_not_decorated_dicts(self):
        # The v1 failure in one assertion: every door claimed a type-600
        # sector, and the map had none, because a hand-written XSECTOR dict
        # on a type-0 sector is inert.
        types = {int(sector.fields["type"]) for sector in self.disk.sectors}
        wanted = {item.expect.sector_type for item in registry.exhibits()
                  if item.expect.sector_type is not None}
        self.assertTrue(wanted)
        self.assertEqual(sorted(wanted - types), [])

    def test_the_tile_museum_shows_only_tiles_the_owner_graded_strong(self):
        # The binding rule, executable: strong may name, weak and untested
        # never may.
        from bloodmap.owner_anchors import load_owner_anchors

        anchors = load_owner_anchors()
        shown = {int(name.split(":")[1])
                 for name in self.layout.regions
                 if name.startswith("museum:") and name.count(":") == 1}
        self.assertTrue(shown)
        self.assertTrue(shown <= set(anchors.naming_picnums()))

    def test_the_tile_museum_shows_each_tile_where_it_belongs(self):
        # v3's museum was the worst violator of the rule it exists to teach:
        # it painted sprite cut-outs onto wall panels, shipping eighteen
        # transparency-law violations. Each panel now has to show its tile in
        # the slot the campaign actually uses it in.
        from bloodmap.usage_kinds import slots_for

        placements = {}
        for placement in self.layout.placements:
            placements.setdefault(placement.region_id, set()).add(
                int(placement.picnum))
        for name, region in self.layout.regions.items():
            if not name.startswith("museum:") or name.count(":") != 1:
                continue
            picnum = int(name.split(":")[1])
            slots = slots_for(picnum)
            if not slots:
                continue
            best = max(slots, key=slots.get)
            where = {"wall": int(region.wall_picnum),
                     "floor": int(region.floor_picnum)}
            if best.startswith("wall"):
                self.assertEqual(where["wall"], picnum, name)
            elif best in ("floor", "ceiling"):
                self.assertEqual(where["floor"], picnum, name)
            else:
                self.assertIn(picnum, placements.get(name, set()), name)

    def test_the_zoo_reads_itself(self):
        # The acceptance gate this rebuild exists for. Every claim in the
        # registry is checked against what `bloodmap.effects` and
        # `bloodmap.conditional` find when they read the built map -- the
        # same code that reads the campaign. v1 passed validation, round
        # trip, load smoke and twenty-four renders with every door dead.
        import json
        import tempfile

        from bloodmap.format import write_map

        selfread = _module("selfread")
        with tempfile.TemporaryDirectory() as directory:
            map_path = Path(directory) / "zoo.MAP"
            manifest_path = Path(directory) / "manifest.json"
            write_map(self.disk, map_path)
            sectors = {name: allocation.sector_id
                       for name, allocation
                       in self.compiled.allocations.items()}
            seated = sorted({
                self.compiled.placement_sprites[p.placement_id]
                for p in self.layout.placements
                if p.seat == "floor"
                and p.placement_id in self.compiled.placement_sprites})
            letters = sorted({
                self.compiled.placement_sprites[p.placement_id]
                for p in self.layout.placements
                if (p.placement_id.startswith(("label:", "sign:", "blocker:"))
                    and p.placement_id in self.compiled.placement_sprites)})
            manifest_path.write_text(json.dumps({
                "region_sectors": sectors,
                "floor_seated_sprites": seated,
                "letter_sprites": letters}), encoding="utf-8")
            report = selfread.run(map_path, manifest_path)
        self.assertGreater(report["claims_checked"], 15)
        self.assertEqual(report["problems"], [])


if __name__ == "__main__":
    unittest.main()
