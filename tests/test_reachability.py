"""Reachability, and telling level design apart from the things beside it.

The corpus-backed cases skip themselves without the commercial maps; the rules
themselves are tested on fixtures that need nothing.
"""

from __future__ import annotations

import glob
import re
import unittest
from pathlib import Path

from bloodmap.blood_types import (
    NUMERIC_COMMAND_BASE,
    NUMERIC_COMMAND_MEANING,
    RESERVED_CHANNELS,
    SPRITE_TYPES,
    classify,
)
from bloodmap.levelprog import LevelProgram, Style
from bloodmap.reachability import (
    SIGNATURE_GLYPHS,
    analyze_reachability,
    classify_offmap,
    design_sectors,
    glyph_shape,
    link_pairs,
    player_start,
    portal_graph,
)

U = 384
PH = 0x1600

ROOT = Path(__file__).resolve().parent.parent
CAMPAIGN = re.compile(r"^E[1-46]M[1-9]$")


def campaign_maps() -> list[Path]:
    result = []
    for path in sorted(glob.glob(str(ROOT / "maps" / "blood" / "campaign" / "*.MAP"))):
        if CAMPAIGN.match(Path(path).stem.upper()):
            result.append(Path(path))
    return result


HAVE_CAMPAIGN = bool(campaign_maps())


def two_room_map():
    """A hall, a side room, and a sealed closet nothing connects to."""
    program = LevelProgram(
        "reach", name="reach",
        style=Style(wall_picnum=1, floor_picnum=2, ceiling_picnum=3,
                    floor_z=0, clear_height=6 * PH),
    )
    house = program.assembly("house")
    hall = house.rect_room("hall", size=(10 * U, 8 * U))
    side = house.rect_room("side", size=(6 * U, 6 * U))
    side.place_against("west", hall.face("east", at=0.5, width=6 * U))
    closet = house.rect_room(
        "closet", origin=(40 * U, 40 * U), size=(2 * U, 2 * U),
        region_kwargs={"declared_zero_exit": True},
    )
    program.connect(hall.face("east", at=0.5, width=6 * U),
                    side.face("west", at=0.5, width=6 * U),
                    connection_id="connection:hall_side")
    program.set_start(hall)
    compiled = program.compile().compile()
    return program, compiled, compiled.level.to_disk_map()


class RuleTests(unittest.TestCase):
    def setUp(self):
        self.program, self.compiled, self.disk = two_room_map()

    def test_a_sealed_room_is_not_reachable(self):
        reach = analyze_reachability(self.disk)
        closet = self.compiled.allocations["region:reach/house/closet"].sector_id
        self.assertIn(closet, reach.offmap)
        self.assertEqual(len(reach.reached), len(self.disk.sectors) - 1)

    def test_a_closed_portal_is_still_part_of_the_level(self):
        """Gating decides when, not whether."""
        graph = portal_graph(self.disk)
        hall = self.compiled.allocations["region:reach/house/hall"].sector_id
        side = self.compiled.allocations["region:reach/house/side"].sector_id
        self.assertIn(side, graph[hall])

    def test_design_sectors_drops_what_the_player_cannot_reach(self):
        kept = design_sectors(self.disk)
        closet = self.compiled.allocations["region:reach/house/closet"].sector_id
        self.assertNotIn(closet, kept)
        self.assertEqual(len(kept), len(self.disk.sectors) - 1)

    def test_a_kept_kind_comes_back(self):
        report = classify_offmap(self.disk)
        kinds = {component["kind"] for component in report["components"]}
        self.assertTrue(kinds)
        kept = design_sectors(self.disk, keep=sorted(kinds))
        self.assertEqual(len(kept), len(self.disk.sectors))

    def test_a_glyph_shape_ignores_where_the_sector_sits(self):
        """The same letter in two maps has to hash the same."""
        hall = self.compiled.allocations["region:reach/house/hall"].sector_id
        closet = self.compiled.allocations["region:reach/house/closet"].sector_id
        self.assertNotEqual(glyph_shape(self.disk, hall), ())
        self.assertNotEqual(glyph_shape(self.disk, hall), glyph_shape(self.disk, closet))

    def test_the_report_states_what_it_cannot_do(self):
        report = classify_offmap(self.disk)
        joined = " ".join(report["limitations"] + report["reachability"]["limitations"])
        self.assertIn("gating is ignored", joined)
        self.assertIn("bare", joined)


class TypeCatalogTests(unittest.TestCase):
    def test_enemies_are_in_the_catalog(self):
        """4,400 of the campaign's typed sprites are dudes; they used to be absent."""
        self.assertEqual(classify("sprite", 202)["name"], "kDudeCultistShotgun")
        self.assertEqual(classify("sprite", 202)["category"], "dude")
        self.assertTrue(all(t in SPRITE_TYPES for t in range(201, 254) if t != 243))

    def test_the_most_common_typed_sprite_in_the_corpus_is_named(self):
        record = classify("sprite", 459)
        self.assertEqual(record["name"], "kTrapExploder")
        self.assertTrue(record["known"])

    def test_a_numeric_command_carries_a_number_not_an_instruction(self):
        record = classify("command", NUMERIC_COMMAND_BASE + 5)
        self.assertEqual(record["category"], "number")
        self.assertEqual(record["value"], 5)
        self.assertTrue(record["known"])

    def test_what_a_number_means_depends_on_the_channel(self):
        self.assertIn(1, NUMERIC_COMMAND_MEANING)   # total secrets
        self.assertIn(2, NUMERIC_COMMAND_MEANING)   # secret found
        self.assertIn(3, NUMERIC_COMMAND_MEANING)   # message
        self.assertNotEqual(NUMERIC_COMMAND_MEANING[1]["call"],
                            NUMERIC_COMMAND_MEANING[2]["call"])

    def test_an_inert_type_is_recorded_rather_than_unknown(self):
        record = classify("sector", 607)
        self.assertTrue(record["known"])
        self.assertEqual(record["category"], "anomaly")
        self.assertIn("no case", record["provenance"] + (record.get("notes") or ""))

    def test_the_event_cause_commands_are_distinguished_from_instructions(self):
        self.assertEqual(classify("command", 30)["category"], "cause")
        self.assertEqual(classify("command", 1)["category"], "command")

    def test_reserved_channels_cover_the_ones_levels_actually_use(self):
        for channel in (1, 2, 3, 4, 5):
            self.assertIn(channel, RESERVED_CHANNELS)


@unittest.skipUnless(HAVE_CAMPAIGN, "no Blood campaign maps under maps/blood")
class CorpusTests(unittest.TestCase):
    """What the 43 campaign maps actually contain, as regression pins."""

    @classmethod
    def setUpClass(cls):
        from bloodmap.format import read_map

        cls.maps = {path.stem.upper(): read_map(path) for path in campaign_maps()}

    def test_every_campaign_map_names_its_single_player_spawn_with_a_marker(self):
        for name, disk in self.maps.items():
            with self.subTest(name):
                self.assertEqual(player_start(disk)["source"],
                                 "kMarkerSPStart with data1 == 0")

    def test_the_map_header_start_is_not_where_the_player_spawns(self):
        """warpInit overrides gStartZone from the data1 == 0 marker.

        The header disagrees with the marker on 37 of the 43 campaign maps, so
        reading the header is wrong far more often than it is right.
        """
        disagree = [name for name, disk in self.maps.items()
                    if int(disk.header["start_sector"]) != player_start(disk)["sector"]]
        self.assertGreaterEqual(len(disagree), 30)

    def test_a_kMarkerSPStart_that_is_not_player_one_is_not_the_spawn(self):
        """Taking the first marker by sprite index picks a coop slot instead."""
        wrong = [name for name, disk in self.maps.items()
                 if (first := next((s for s in disk.sprites
                                    if int(s.fields["type"]) == 1), None)) is not None
                 and int(first.fields["sector"]) != player_start(disk)["sector"]]
        self.assertEqual(sorted(wrong), ["E3M7", "E4M3", "E6M7"])

    def test_crossing_links_and_teleports_matters(self):
        """Walls alone leave whole levels unreachable."""
        for name in ("E6M5", "E4M3"):
            if name not in self.maps:
                continue
            with self.subTest(name):
                disk = self.maps[name]
                reach = analyze_reachability(disk)
                self.assertLess(reach.offmap_fraction, 0.10)

    def test_off_map_geometry_is_a_small_tail_everywhere(self):
        for name, disk in self.maps.items():
            with self.subTest(name):
                self.assertLess(analyze_reachability(disk).offmap_fraction, 0.15)

    def test_every_campaign_map_has_off_map_geometry(self):
        for name, disk in self.maps.items():
            with self.subTest(name):
                self.assertTrue(analyze_reachability(disk).offmap)

    def test_the_signature_stamp_is_recognised_where_it_occurs(self):
        self.assertTrue(SIGNATURE_GLYPHS)
        carriers = []
        for name, disk in self.maps.items():
            report = classify_offmap(disk)
            if report["counts"].get("signature"):
                carriers.append(name)
        self.assertGreaterEqual(len(carriers), 14)
        self.assertIn("E2M3", carriers)

    def test_a_logic_closet_is_one_sector_of_switches(self):
        closets = []
        for disk in self.maps.values():
            for component in classify_offmap(disk)["components"]:
                if component["kind"] == "logic_closet":
                    closets.append(component)
        self.assertGreater(len(closets), 30)
        self.assertTrue(all(len(c["sectors"]) == 1 for c in closets))
        self.assertGreater(max(c["switches"] for c in closets), 40)

    def test_no_type_id_in_the_campaign_is_unknown(self):
        unknown = []
        for name, disk in self.maps.items():
            for kind, group in (("sprite", disk.sprites), ("sector", disk.sectors),
                                ("wall", disk.walls)):
                for item in group:
                    if not classify(kind, int(item.fields["type"]))["known"]:
                        unknown.append((name, kind, int(item.fields["type"])))
                    if item.extra is not None:
                        command = int(item.extra.fields.get("command", 0))
                        if not classify("command", command)["known"]:
                            unknown.append((name, "command", command))
        self.assertEqual(unknown, [])

    def test_links_are_paired_by_the_data1_the_engine_matches_on(self):
        for name, disk in self.maps.items():
            with self.subTest(name):
                for pair in link_pairs(disk):
                    left, right = pair["sprites"]
                    self.assertEqual(disk.sprites[left].extra.fields["data_1"],
                                     disk.sprites[right].extra.fields["data_1"])


if __name__ == "__main__":
    unittest.main()
