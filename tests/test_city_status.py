"""The city's status is data the build writes, and it is never out of date.

Two pages used to say where the city stood. One gave September's 215
sectors and a 7,000-wall budget; the other called the full city "the older
artifact" while every later session worked on it. What each place's critique
had found lived in one agent's private notes. `status.py` generates the
answer from the build manifest and the critique rounds, and these tests fail
while what it wrote and what it would write differ.
"""

from __future__ import annotations

import importlib.util
import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
LEVEL = ROOT / "projects" / "blood-city" / "level"
REPORTS = LEVEL.parent / "reports"


def _status():
    """Load the project's status module without leaving its folder on the path."""
    added = str(LEVEL) not in sys.path
    if added:
        sys.path.insert(0, str(LEVEL))
    try:
        spec = importlib.util.spec_from_file_location("blood_city_status",
                                                      LEVEL / "status.py")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module, module.gather()
    finally:
        if added:
            sys.path.remove(str(LEVEL))


@unittest.skipUnless((REPORTS / "build-manifest.json").exists()
                     and (LEVEL / "blood-city-current.MAP").exists(),
                     "the city has not been built")
class CityStatusTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.module, cls.status = _status()

    def test_the_two_files_are_what_the_sources_give_today(self):
        data, page = self.module.render(self.status)
        for name, text in (("status.json", data), ("STATUS.md", page)):
            with self.subTest(file=name):
                path = REPORTS / name
                self.assertTrue(path.exists(), "run projects/blood-city/level/status.py")
                current = path.read_text(encoding="utf-8").replace("\r\n", "\n")
                self.assertTrue(
                    current == text,
                    f"{name} is stale: run python projects/blood-city/level/status.py")

    def test_it_counts_the_map_that_is_on_disk(self):
        from bloodmap.format import read_map

        disk = read_map(LEVEL / "blood-city-current.MAP")
        build = self.status["build"]
        self.assertEqual((build["sectors"], build["walls"], build["sprites"]),
                         (len(disk.sectors), len(disk.walls), len(disk.sprites)))

    def test_every_place_on_the_character_sheet_is_reported(self):
        manifest = json.loads((REPORTS / "build-manifest.json").read_text("utf-8"))
        self.assertEqual([place["name"] for place in self.status["places"]],
                         list(manifest["character"]["places"]))

    def test_an_open_item_says_what_where_who_and_how_to_see_it(self):
        self.assertTrue(self.status["open"])
        for row in self.status["open"]:
            with self.subTest(kind=row["kind"]):
                self.assertTrue(row["says"])
                self.assertTrue(row["owner"])
                self.assertTrue(row["see"])
        counted = sum(self.status["open_by_kind"].values())
        self.assertEqual(counted, len(self.status["open"]))

    def test_an_owner_that_names_a_file_names_one_that_exists(self):
        checked = 0
        for row in self.status["open"]:
            owner = row["owner"].split(":")[0].split(" ")[0]
            if "/" not in owner:
                continue
            checked += 1
            self.assertTrue((ROOT / owner).exists(), row["owner"])
        self.assertGreater(checked, 10)

    def test_a_place_that_failed_its_critique_carries_what_the_readers_said(self):
        failed = [place for place in self.status["places"]
                  if place["critique"] and not place["critique"]["passes"]]
        for place in failed:
            said = [row for row in self.status["open"]
                    if row["place"] == place["name"] and row["kind"] == "critique"]
            self.assertEqual(len(said),
                             len(place["critique"]["blocking"])
                             + len(place["critique"]["readers_missing"]),
                             place["name"])

    def test_every_stage_that_ran_is_at_a_line_that_starts_it(self):
        """The build is two thousand lines; a stage's name is how an agent is
        sent to the right hundred of them."""
        stages = self.status["stages"]
        self.assertGreater(len(stages), 20)
        self.assertEqual(len({row["name"] for row in stages}), len(stages))
        source = (LEVEL / "build_skeleton.py").read_text(encoding="utf-8").splitlines()
        for row in stages:
            with self.subTest(stage=row["name"]):
                path, _colon, line = row["at"].rpartition(":")
                self.assertTrue((ROOT / path).exists(), row["at"])
                self.assertIn(f'STAGE("{row["name"]}"', source[int(line) - 1])
                self.assertTrue(row["says"])
        # the seconds are a machine's, so they are not in what is committed
        self.assertNotIn("seconds", json.dumps(self.status["stages"]))

    def test_the_citys_declared_wiring_agrees_with_its_map(self):
        """Read back with the campaign's reader: a declared wire is on the
        map as declared, nothing wired is unable to send, and no wire of the
        level's own sits on an engine channel."""
        from bloodmap import wiring
        from bloodmap.format import read_map

        manifest = json.loads((REPORTS / "build-manifest.json").read_text("utf-8"))
        wires = manifest["wires"]
        self.assertTrue(wires["agrees"], [row for row in wires["wires"] if row["faults"]])
        self.assertGreaterEqual(len(wires["declared"]), 1)
        for row in wires["declared"]:
            self.assertTrue(row["says"].strip(), row["name"])
            if row["engine"] is None:
                self.assertGreaterEqual(row["channel"], 100, row["name"])
        disk = read_map(LEVEL / "blood-city-current.MAP")
        self.assertEqual([node["id"] for node in wiring.silent_senders(disk)], [])
        self.assertEqual(manifest["character"]["engine_channels_wired"], [])
        # every channel typed by hand is an open item until a wire declares it
        typed = [row for row in self.status["open"] if row["kind"] == "undeclared-wire"]
        self.assertEqual(len(typed), len(wires["undeclared"]))

    def test_the_city_is_given_the_mark_the_campaign_is_given(self):
        """Our own map is held to what a shipped map is: can it be finished.
        On 2026-11-19 it could not -- it has no exit -- and no gate, rule or
        status line had said so."""
        finish = self.status["finish"]
        self.assertEqual(finish["exit_reached"], bool(
            [row for row in finish["exits"] if row["reached"]]))
        said = [row for row in self.status["open"] if row["kind"] == "cannot-finish"]
        if not finish["exit_reached"]:
            self.assertTrue(said)
        # its one key works a door that is pushed by hand, on no wire
        self.assertTrue(all(row["key"] in {lock["key"] for lock in finish["locked"]}
                            for row in [{"key": 2}] if finish["keys"]))
        self.assertGreater(len(finish["gated_areas"]), 1)

    def test_no_channel_in_the_city_is_typed_by_hand(self):
        """Thirteen were, in six modules, until 2026-11-19. Every wire is now
        a line of `wires.py` saying what it is for, numbered by its place."""
        from bloodmap.wiring import ENGINE_SENDS, USER_CHANNELS_FROM, USER_CHANNELS_TO

        manifest = json.loads((REPORTS / "build-manifest.json").read_text("utf-8"))
        wires = manifest["wires"]
        self.assertEqual(wires["undeclared"], [])
        # one planned wire is idle on purpose: the foundry's staged moment
        # was taken off the yard and waits to be rebuilt underground
        self.assertEqual(wires["idle"], ["foundry:staged-moment"])
        self.assertGreaterEqual(len(wires["declared"]), 14)
        numbers = sorted(row["channel"] for row in wires["declared"]
                         if row["engine"] is None)
        self.assertEqual(len(set(numbers)), len(numbers))
        self.assertTrue(all(USER_CHANNELS_FROM <= number <= USER_CHANNELS_TO
                            for number in numbers))
        for row in wires["wires"]:
            engine_sends = row["engine"] is not None and row["channel"] in ENGINE_SENDS
            self.assertEqual(bool(row["senders"]), not engine_sends, row["name"])
            #: (a shot lamp's answer is the floor it lights: tests/test_shot_lamps.py)
            self.assertEqual(bool(row["answers"] or row.get("later")), engine_sends or row["engine"] is None,
                             row["name"])

    def test_the_city_ends_at_a_switch_in_the_station_tunnel(self):
        """It had no exit at all. The way out is declared like any wire,
        ends at the engine, and lies behind the gate the lever raises. It is
        a pushed switch because that is how the campaign ends a level: the
        first version ended it by walking in, a shape the campaign never
        has, and the reading of the city beside the campaign said so."""
        finish = self.status["finish"]
        self.assertTrue(finish["exit_reached"])
        (way_out,) = finish["exits"]
        self.assertEqual((way_out["cause"], way_out["to"]),
                         ("push", "kChannelLevelExitNormal"))
        self.assertEqual(finish["reached"], finish["space"],
                         "player space is what a body can stand in: no scenery")
        self.assertFalse([row for row in self.status["open"]
                          if row["kind"] == "cannot-finish" and "exit" in row["says"]])
        (wire,) = [row for row in self.status["wires"] if row["name"] == "station:way-out"]
        self.assertEqual(wire["engine"], "kChannelLevelExitNormal")

    def test_the_plan_numbers_a_wire_by_its_place(self):
        added = str(LEVEL) not in sys.path
        if added:
            sys.path.insert(0, str(LEVEL))
        try:
            import wires
        finally:
            if added:
                sys.path.remove(str(LEVEL))
        names = [name for name, _says in wires.PLAN]
        self.assertEqual(len(set(names)), len(names))
        self.assertEqual(names[0], "foundry:staged-moment")     # append only
        for index, (name, says) in enumerate(wires.PLAN):
            self.assertEqual(wires.channel(name), 100 + index)
            self.assertGreater(len(says.split()), 5, name)

    def test_the_brief_is_short_and_says_what_is_not_verified(self):
        _data, page = self.module.render(self.status)
        self.assertLess(len(page.splitlines()), 80)
        self.assertIn("## Not verified", page)
        self.assertIn("Do not edit", page)


if __name__ == "__main__":
    unittest.main()
