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
PLACES = ROOT / "knowledge" / "blood" / "design" / "places-v1.json"


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

    def test_no_channel_and_a_levels_own_channel_are_not_the_engines(self):
        """`tx_id` 0 sends nothing (`if (pXSprite->txID)`), and 100 is the
        first channel a level may use for itself. Counting both, the index
        said 24,610 objects "send on kChannelZero" until 2026-11-19."""
        disk = self._map()
        disk.sectors[0].extra = _xsector(tx_id=0, rx_id=100)
        disk.sectors[0].fields["extra"] = 1
        seen = examples.observe("TEST", disk)
        self.assertEqual(set(seen["sends"]), {"channel:4"})
        self.assertEqual(seen["hears"], {})


class PlaceJoinTests(unittest.TestCase):
    def test_a_room_holds_what_stands_in_its_sectors_and_nothing_else(self):
        seen = examples.observe("TEST", ObserveTests()._map())
        held = examples.by_place(seen, {1: "TEST:1"})
        self.assertEqual(held, {"TEST:1": {"channel:4": 1, "effect:conveyor": 1,
                                           "sprite:1": 1, "wall:511": 1}})
        self.assertEqual(examples.by_place(seen, {}), {})

    def test_an_entry_names_its_richest_rooms_and_each_example_its_own(self):
        disk = ObserveTests()._map()
        index = examples.build(
            [examples.observe("AAA", disk), examples.observe("BBB", disk)],
            places={"AAA": {0: "AAA:0", 1: "AAA:0"}, "BBB": {1: "BBB:1"}})
        entry = index["entries"]["sprite:1"]
        self.assertEqual(entry["place_count"], 2)
        self.assertEqual(entry["places"], [{"id": "AAA:0", "count": 2},
                                           {"id": "BBB:1", "count": 1}])
        self.assertEqual([item["place"] for item in entry["examples"]],
                         ["AAA:0", None, "AAA:0", "BBB:1"])

    def test_a_part_says_what_sets_it_off_and_what_it_drives(self):
        """A type alone is not a mechanism; the index says so by carrying
        the wire it is found on."""
        from bloodmap.model import PackedExtra as Extra
        from bloodmap.format import XSPRITE_SCHEMA

        disk = ObserveTests()._map()
        switch = {name: 0 for name, _bits, _signed in XSPRITE_SCHEMA}
        switch.update(tx_id=120, trigger_push=1)
        disk.sprites[0].fields["type"] = 20
        disk.sprites[0].extra = Extra("XSPRITE", switch)
        disk.sprites[0].fields["extra"] = 1
        disk.sectors[0].extra = _xsector(rx_id=120)
        disk.sectors[0].fields["extra"] = 1
        index = examples.build([examples.observe("AAA", disk)])
        (row,) = [row for row in index["wiring"] if row["sender"] == "kSwitchToggle"]
        self.assertEqual((row["cause"], row["answers"], row["count"]),
                         ("push", ["kSectorSlideMarked"], 1))
        self.assertEqual(row["examples"], [{"map": "AAA", "sector": 0, "root": "sprite 0"}])
        self.assertEqual(index["entries"]["sector:614"]["set_off_by"],
                         {"kSwitchToggle (push)": 1})
        self.assertEqual(index["entries"]["sprite:20"]["drives"],
                         {"kSectorSlideMarked": 1})
        self.assertEqual(examples.search_wiring(index, ["button", "slide"]), [row])
        self.assertEqual(examples.search_wiring(index, ["lift"]), [])

    def test_without_the_catalogue_an_entry_claims_no_room(self):
        index = examples.build([examples.observe("AAA", ObserveTests()._map())])
        entry = index["entries"]["sprite:1"]
        self.assertNotIn("places", entry)
        self.assertNotIn("place", entry["examples"][0])


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
        from tools import catalog

        cls.fresh = examples.build(
            seen,
            curriculum={"maps": mine_course(blood_corpus_root() / "mechanism")},
            cited=examples.cited_lessons(ROOT / "bloodmap"),
            places=catalog.sector_places() if PLACES.exists() else None)

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
        self.assertTrue(self.committed.get("wiring") == self.fresh["wiring"],
                        "the wiring is stale: run python -m tools.catalog build-mechanisms")

    def test_a_lift_and_a_door_are_found_as_wiring_and_not_as_a_type(self):
        """`kSectorZMotion` is 671 times something that changes what fits
        through and 186 times something that carries a body between levels.
        The word a mapper uses picks the reading, on a wire."""
        for word, does in (("lift", "carries a body between levels"),
                           ("door", "changes what fits through")):
            with self.subTest(word=word):
                found = examples.search_wiring(self.committed, [word])
                self.assertGreater(len(found), 20)
                for row in found:
                    self.assertTrue(any(does in answer for answer in row["answers"]), row)
        locked = examples.search_wiring(self.committed, ["locked", "door"])
        self.assertTrue(locked)
        self.assertTrue(all(row["keyed"] for row in locked))
        # and a secret is an act that ends at the engine, with no sector type at all
        secret = examples.search_wiring(self.committed, ["enter", "secret"])[0]
        self.assertEqual((secret["sender"], secret["answers"]),
                         ("a plain sector", ["the engine (kChannelSecretFound)"]))
        self.assertGreater(secret["count"], 100)

    def test_the_campaigns_wiring_is_written_in_phrases_that_can_be_counted(self):
        """The same parts mean different things on different wires; a phrase
        is a test on the wire, so each is a number and a place to look."""
        said = {phrase["name"]: phrase for phrase in examples.idioms(self.committed)}
        self.assertEqual(set(said), set(examples.IDIOMS))
        for name, phrase in said.items():
            with self.subTest(phrase=name):
                self.assertGreater(phrase["chains"], 10)
                self.assertTrue(phrase["commonest"]["examples"])
        rows = self.committed["wiring"]
        self.assertEqual(said["never fires"]["chains"], sum(row["silent"] for row in rows))
        self.assertEqual(said["locked"]["chains"], sum(row["keyed"] for row in rows))
        # a switch nobody pushes: every row is shot, and is a switch
        for row in examples.search_wiring(self.committed, ["shot", "switch"]):
            self.assertTrue(row["sender"].startswith("kSwitch"), row["sender"])
            self.assertNotIn("push", row["cause"])
        # a phrase and a word together: locked ways through
        for row in examples.search_wiring(self.committed, ["locked", "door"]):
            self.assertTrue(row["keyed"])
        self.assertGreater(said["closet relay"]["chains"], 500)

    def test_every_chain_is_counted_once_and_no_cause_is_no_channel(self):
        from bloodmap import wiring
        from bloodmap.format import read_map

        total = sum(len(wiring.chains(read_map(path))) for path in campaign_maps())
        self.assertEqual(sum(row["count"] for row in self.committed["wiring"]), total)
        self.assertFalse([row for row in self.committed["wiring"]
                          if "channel 0" in row["cause"]])

    def test_a_wiring_example_is_a_sender_that_exists(self):
        from bloodmap.format import read_map

        maps = {path.stem.upper(): read_map(path) for path in campaign_maps()[:4]}
        checked = 0
        for row in self.committed["wiring"]:
            for item in row["examples"]:
                disk = maps.get(item["map"])
                if disk is None:
                    continue
                kind, index = item["root"].split()
                group = {"sprite": disk.sprites, "sector": disk.sectors,
                         "wall": disk.walls}[kind]
                self.assertIsNotNone(group[int(index)].extra, item)
                checked += 1
        self.assertGreater(checked, 100)

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

    def test_there_is_no_entry_for_no_channel(self):
        self.assertNotIn("channel:0", self.committed["entries"])
        self.assertNotIn("channel:100", self.committed["entries"])

    @unittest.skipUnless(PLACES.exists(), "no places catalogue")
    def test_a_room_an_entry_names_holds_that_many_of_it(self):
        """The two shelves say the same thing from both sides."""
        rooms = {row["id"]: row for row in
                 json.loads(PLACES.read_text(encoding="utf-8"))["places"]}
        checked = 0
        for key, entry in self.committed["entries"].items():
            for room in entry.get("places", []):
                self.assertEqual(rooms[room["id"]]["mechanisms"].get(key),
                                 room["count"], f"{key} in {room['id']}")
                checked += 1
            for item in entry.get("examples", []):
                if item["place"] is not None:
                    self.assertIn(item["sector"], rooms[item["place"]]["members"], key)
        self.assertGreater(checked, 400)

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
