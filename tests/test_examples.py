"""The mechanisms shelf: "which levels have one of these", answered.

Before 2026-11-19 a search for "conveyor", "lift" or "614" returned nothing,
while the type names, 136 taught lessons and a reader of every moving sector
sat in three modules that did not know about each other. These tests hold the
join: an effect is exactly its fields, an example can be gone to, a mapper's
word reaches the engine's name, and the committed index is what the campaign
and the code produce today.
"""

from __future__ import annotations

import json
import unittest
from pathlib import Path

from bloodmap import examples
from bloodmap.model import PackedExtra
from bloodmap.format import XSECTOR_SCHEMA
from tests.helpers import campaign_maps, synthetic_two_sector_map

ROOT = Path(__file__).resolve().parent.parent
INDEX = ROOT / "knowledge" / "blood" / "design" / "mechanism-examples-v1.json"


def _xsector(**fields) -> PackedExtra:
    values = {name: 0 for name, _bits, _signed in XSECTOR_SCHEMA}
    values.update(fields)
    return PackedExtra("XSECTOR", values)


class EffectTests(unittest.TestCase):
    def test_every_field_an_effect_names_is_a_real_xsector_field(self):
        """A misspelt field makes the rule never match, and the index then
        says the campaign never does the thing."""
        known = examples.xsector_field_names()
        for name, rule in examples.EFFECTS.items():
            for clause in ("all", "any", "none"):
                for field in rule.get(clause, ()):
                    self.assertIn(field, known, f"{name}: {field}")

    def test_a_conveyor_is_a_panning_floor_with_drag_and_not_without(self):
        self.assertEqual(
            examples.effects_of({"pan_floor": 1, "drag": 1, "pan_velocity": 64}),
            ["conveyor"])
        self.assertEqual(examples.effects_of({"pan_floor": 1, "pan_velocity": 64}),
                         ["panning floor"])
        self.assertEqual(examples.effects_of({"pan_velocity": 64}), [])
        self.assertEqual(examples.effects_of(None), [])
        self.assertEqual(examples.effects_of({}), [])

    def test_an_any_rule_needs_one_of_its_fields(self):
        self.assertIn("wind", examples.effects_of({"wind_always": 1}))
        self.assertIn("wind", examples.effects_of({"wind_velocity": 300}))
        self.assertNotIn("wind", examples.effects_of({"wind_angle": 512}))


class SlotTableTests(unittest.TestCase):
    def test_the_curriculums_slots_name_real_xsector_fields(self):
        """`wind_vel`, `pan_vel`, `wave`, `phase` and `freq` are not fields.
        The table spelt them that way until 2026-11-19, so a sector with a
        wind velocity and no `wind_always` spent no wind slot: 16 readings in
        7,045, quietly."""
        from bloodmap.curriculum import SLOTS

        known = examples.xsector_field_names()
        for slot, fields in SLOTS.items():
            for field in fields:
                self.assertIn(field, known, f"{slot}: {field}")


class ObserveTests(unittest.TestCase):
    def _map(self):
        disk = synthetic_two_sector_map()
        disk.sectors[0].fields["type"] = 614
        disk.sectors[1].extra = _xsector(pan_floor=1, drag=1, tx_id=4)
        disk.sectors[1].fields["extra"] = 2
        disk.walls[5].fields["type"] = 511
        return disk

    def test_an_instance_says_where_to_stand_and_which_object(self):
        seen = examples.observe("TEST", self._map())
        self.assertEqual(seen["types"]["sector:614"], [(0, 0)])
        self.assertEqual(seen["types"]["wall:511"], [(1, 5)])      # wall 5 is sector 1's
        self.assertEqual(seen["types"]["sprite:1"], [(0, 0), (1, 1)])
        self.assertEqual(seen["effects"]["conveyor"], [(1, 1)])

    def test_a_reserved_channel_records_its_senders(self):
        seen = examples.observe("TEST", self._map())
        self.assertEqual(seen["sends"]["channel:4"], [(1, 1)])     # kChannelLevelExitNormal


class BuildAndSearchTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        disk = ObserveTests()._map()
        curriculum = {"maps": [
            {"map": "DOOR-SLIDING.map", "tier": "1", "sectors": 7, "walls": 40,
             "sprites": 9, "sprite_roles": {},
             "constructs": [{"sector": 2, "type": 614, "slots": ["rx"],
                             "sentence": "s2 type 614, markers 960 apart"}]},
            {"map": "MACHINERY-CONVEYOR.map", "tier": "1", "sectors": 7,
             "walls": 49, "sprites": 13, "sprite_roles": {},
             "constructs": [{"sector": 3, "type": 0, "slots": ["panning"],
                             "sentence": "s3 type 0"}]},
        ]}
        cls.index = examples.build(
            [examples.observe("AAA", disk), examples.observe("BBB", disk)],
            curriculum=curriculum,
            cited={"DOOR-SLIDING": ["bloodmap.mechanism.slide"]})

    def test_examples_are_spread_one_map_at_a_time(self):
        entry = self.index["entries"]["sprite:1"]
        self.assertEqual(entry["count"], 4)
        self.assertEqual(entry["maps"], 2)
        self.assertEqual([item["map"] for item in entry["examples"]],
                         ["AAA", "BBB", "AAA", "BBB"])

    def test_a_type_knows_its_name_its_lessons_and_a_place_to_look(self):
        entry = self.index["entries"]["sector:614"]
        self.assertEqual(entry["name"], "kSectorSlideMarked")
        self.assertEqual(entry["lessons"], ["DOOR-SLIDING"])
        self.assertEqual(entry["examples"][0], {"map": "AAA", "sector": 0, "id": 0})

    def test_a_lesson_knows_what_it_uses_and_who_cites_it(self):
        entry = self.index["entries"]["lesson:DOOR-SLIDING"]
        self.assertEqual(entry["types"], ["sector:614"])
        self.assertEqual(entry["sectors"], [2])
        self.assertEqual(entry["cited_by"], ["bloodmap.mechanism.slide"])

    def test_an_effect_finds_the_lesson_named_for_it(self):
        entry = self.index["entries"]["effect:conveyor"]
        self.assertEqual(entry["lessons"], ["MACHINERY-CONVEYOR"])
        self.assertEqual(entry["count"], 2)

    def test_a_mappers_word_reaches_the_engines_name(self):
        def keys(*words):
            return [key for key, _entry in examples.search(self.index, words)]

        # asked for by its own name, the entry leads; then the lesson
        self.assertEqual(keys("conveyor"),
                         ["effect:conveyor", "lesson:MACHINERY-CONVEYOR"])
        self.assertIn("effect:conveyor", keys("belt"))
        self.assertEqual(keys("sliding", "door"), ["lesson:DOOR-SLIDING"])
        self.assertEqual(keys("614")[0], "sector:614")        # asked for by number
        self.assertEqual(keys("exit")[0], "channel:4")
        self.assertEqual(keys("no-such-thing"), [])
        # three words for one thing: what answers to most of them
        self.assertEqual(keys("conveyor", "no-such-thing"),
                         ["effect:conveyor", "lesson:MACHINERY-CONVEYOR"])

    def test_an_entry_is_found_by_key_by_name_or_by_bare_word(self):
        for said, key in (("sector:614", "sector:614"),
                          ("kSectorSlideMarked", "sector:614"),
                          ("DOOR-SLIDING", "lesson:DOOR-SLIDING"),
                          ("conveyor", "effect:conveyor"),
                          ("4", None), ("nothing", None)):
            with self.subTest(said=said):
                self.assertEqual(examples.resolve(self.index, said), key)


class CitationTests(unittest.TestCase):
    def test_a_constructor_that_names_its_lesson_is_linked_to_it(self):
        cited = examples.cited_lessons(ROOT / "bloodmap")
        self.assertIn("bloodmap.mechanism.lift", cited.get("MACHINERY-LIFT", []))
        self.assertFalse(any("examples." in name for names in cited.values()
                             for name in names), "the index must not cite itself")


@unittest.skipUnless(campaign_maps() and INDEX.exists(), "no campaign corpus")
class CommittedIndexTests(unittest.TestCase):
    """The file an agent reads is the one the campaign and the code give today."""

    @classmethod
    def setUpClass(cls):
        from bloodmap.curriculum import mine_course
        from bloodmap.format import read_map
        from tests.helpers import blood_corpus_root

        cls.committed = json.loads(INDEX.read_text(encoding="utf-8"))
        seen = [examples.observe(path.stem.upper(), read_map(path))
                for path in campaign_maps()]
        cls.fresh = examples.build(
            seen,
            curriculum={"maps": mine_course(blood_corpus_root() / "mechanism")},
            cited=examples.cited_lessons(ROOT / "bloodmap"))

    def test_it_is_current(self):
        stale = []
        for key, entry in self.fresh["entries"].items():
            theirs = dict(self.committed["entries"].get(key, {}))
            theirs.pop("file", None)                 # the lesson's path is local
            if theirs != entry:
                stale.append(key)
        self.assertEqual(stale[:10], [],
                         "run python -m tools.catalog build-mechanisms")
        self.assertEqual(set(self.committed["entries"]), set(self.fresh["entries"]))

    def test_the_questions_that_used_to_return_nothing_are_answered(self):
        for words, expected in ((["conveyor"], "effect:conveyor"),
                                (["lift"], "lesson:MACHINERY-LIFT"),
                                (["elevator"], "sector:600"),
                                (["614"], "sector:614"),
                                (["teleport"], "lesson:MACHINERY-TELEPORT"),
                                (["secret"], "channel:2"),
                                (["zombie"], "sprite:203")):
            with self.subTest(words=words):
                found = [key for key, _e in examples.search(self.committed, words)]
                self.assertIn(expected, found)

    def test_every_example_is_an_object_that_exists(self):
        from bloodmap.format import read_map

        maps = {path.stem.upper(): read_map(path) for path in campaign_maps()[:6]}
        checked = 0
        for key, entry in self.committed["entries"].items():
            kind = entry["kind"].split()[0]
            for item in entry.get("examples", []):
                disk = maps.get(item["map"])
                if disk is None:
                    continue
                self.assertLess(item["sector"], len(disk.sectors), key)
                if kind in ("sprite", "wall"):
                    group = disk.sprites if kind == "sprite" else disk.walls
                    self.assertEqual(int(group[item["id"]].fields["type"]),
                                     int(key.split(":")[1]), key)
                checked += 1
        self.assertGreater(checked, 200)


if __name__ == "__main__":
    unittest.main()
