"""The library: one vocabulary, searchable shelves, and the station built from it.

The owner, 2026-11-18: "that catalog needs to be coherent and usable ...
rather than tons of texts, it needs to be a real library you can use";
"annotations for the maps like these are hospitals, these are hospital
beds ... in different scales of magnitude"; "We also should be
understanding mechanisms, some levels have pretty complex chains of
them"; and, of the city's edge: "we can do something like train station".
"""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

DESIGN = Path("knowledge/blood/design")
PLACES = DESIGN / "places-v1.json"
LOOKS = DESIGN / "tile-looks"
E2M4 = Path("maps/blood/campaign/E2M4.MAP")


class VocabularyTests(unittest.TestCase):
    def test_an_unknown_word_is_refused(self):
        from tools import catalog

        with self.assertRaises(catalog.CatalogError):
            catalog.record_look(1, "thing", "tiles", "x", [], "test")
        with self.assertRaises(catalog.CatalogError):
            catalog.record_look(1, "material", "tiles", "x", ["trains"],
                                "test")
        with self.assertRaises(catalog.CatalogError):
            catalog.record_label("E1M1:1", "hospital ward", "", "test")
        with self.assertRaises(catalog.CatalogError):
            #: a thing is named from the things' list, not the places'
            catalog.record_label("E1M1:1", "hospital", "", "test",
                                 scale="thing")

    def test_every_filed_reading_uses_the_vocabulary(self):
        from tools import catalog

        vocab = catalog.vocabulary()
        looks = catalog.tile_looks()
        if not looks:
            self.skipTest("no tile readings yet")
        for tile, row in looks.items():
            self.assertIn(row["class"], vocab["tile_class"], tile)
            self.assertIn(row["layout"], vocab["tile_layout"], tile)
            for theme in row["tags"]:
                self.assertIn(theme, vocab["themes"], tile)
            self.assertLessEqual(len(row["looks"].split()), 10, tile)


@unittest.skipUnless(PLACES.exists() and LOOKS.exists(), "no library built")
class SearchTests(unittest.TestCase):
    def test_rail_finds_the_track_tile_and_the_station_that_wears_it(self):
        from tools import catalog

        self.assertIn(1129, [tile for tile, _said in
                             catalog.find_tiles(["rail"])])
        places = [row["id"] for _s, row, _w in
                  catalog.find_places(["rail"], None, 40)]
        self.assertTrue(any(p.startswith("E1M2:") for p in places))

    def test_a_guess_says_it_is_a_guess_and_names_its_evidence(self):
        from tools import catalog

        guesses = json.loads((DESIGN / "place-labels" / "part-0guess.json")
                             .read_text("utf-8"))
        self.assertGreater(len(guesses), 100)
        for row in list(guesses.values())[:50]:
            self.assertEqual(row["confidence"], "guessed")
            self.assertTrue(row["note"].startswith("tiles "))
        #: Blood's hospital map is guessed to hold a hospital
        self.assertTrue(any(k.startswith("E3M4:") and v["kind"] == "hospital"
                            for k, v in guesses.items()))

    def test_a_reader_s_label_outranks_a_guess(self):
        from tools import catalog

        with tempfile.TemporaryDirectory() as folder:
            old = catalog.LABELS
            catalog.LABELS = Path(folder)
            try:
                (Path(folder) / "part-0guess.json").write_text(json.dumps(
                    {"E9M9:1": {"kind": "factory", "confidence": "guessed",
                                "note": "tiles 1", "by": "guess"}}), "utf-8")
                catalog.record_label("E9M9:1", "bar", "looked", "reader")
                self.assertEqual(catalog.place_labels()["E9M9:1"]["kind"],
                                 "bar")
            finally:
                catalog.LABELS = old


@unittest.skipUnless(PLACES.exists(), "no library built")
class PlaceMembershipTests(unittest.TestCase):
    """A place row says which sectors it is and what they hold."""

    @classmethod
    def setUpClass(cls):
        cls.rows = json.loads(PLACES.read_text("utf-8"))["places"]

    def test_a_sector_belongs_to_one_room_and_the_host_is_a_member(self):
        claimed: dict[tuple[str, int], str] = {}
        for row in self.rows:
            self.assertEqual(len(row["members"]), row["sectors"], row["id"])
            self.assertIn(row["host"], row["members"], row["id"])
            for sector in row["members"]:
                self.assertIsNone(claimed.get((row["map"], sector)), row["id"])
                claimed[(row["map"], sector)] = row["id"]

    def test_a_room_ends_at_its_doors(self):
        """E1M1's funeral home was one "room" of 73 sectors: any small
        sector was taken in and the room went on from it, through every door
        leaf. A room with its moving sectors taken out is still one piece,
        so no room runs through a door to the next."""
        from bloodmap.format import read_map
        from tests.helpers import campaign_maps
        from tools import place_character as pc

        mine = [row for row in self.rows if row["map"] == "E1M1"]
        self.assertLessEqual(max(row["sectors"] for row in mine), 30)
        signs = {974: None, 1726: None, 789: None, 844: None}
        for row in mine:
            for tile in signs:
                if tile in row["tiles"] or str(tile) in row["sprites"]:
                    signs[tile] = row["id"]
        # the funeral home's welcome, the cemetery's arch, the memorial
        # plaque and the construction sign are four different places
        self.assertEqual(len(set(signs.values())), 4, signs)
        for path in campaign_maps()[:5]:
            geom = pc.Geometry(read_map(path))
            for place in pc.places(geom):
                # the sector a room is grown from is its floor even when
                # it is a moving type (E1M1's memorial hall is one)
                host = max(place, key=geom.area)
                still = {s for s in place if s == host or not pc.is_mover(geom, s)}
                seen, queue = set(), [host]
                while queue:
                    here = queue.pop()
                    if here in seen:
                        continue
                    seen.add(here)
                    queue += [int(geom.walls[w]["next_sector"])
                              for w in geom.wall_ids(here)
                              if int(geom.walls[w]["next_sector"]) in still]
                self.assertEqual(seen, still, (path.stem, sorted(place)[:6]))

    def test_what_a_room_holds_is_keyed_as_the_mechanisms_shelf_keys_it(self):
        kinds = set()
        for row in self.rows:
            for key, count in row["mechanisms"].items():
                kinds.add(key.split(":", 1)[0])
                self.assertGreater(count, 0, row["id"])
        self.assertEqual(kinds, {"sector", "wall", "sprite", "effect", "channel"})

    @unittest.skipUnless(E2M4.exists(), "no E2M4")
    def test_the_rooms_of_a_map_are_what_the_map_gives_today(self):
        from bloodmap import examples
        from bloodmap.format import read_map
        from tools import catalog
        from tools import place_character as pc

        disk = read_map(E2M4)
        mine = {row["id"]: row for row in self.rows if row["map"] == "E2M4"}
        geom = pc.Geometry(disk)
        fresh = {}
        for place in pc.places(geom):
            profile = pc.profile(geom, place)
            if profile["solid_wall"] >= 4096:
                fresh[f"E2M4:{profile['host']}"] = sorted(place)
        self.assertEqual({key: row["members"] for key, row in mine.items()}, fresh,
                         "run python -m tools.catalog build-places")
        held = examples.by_place(examples.observe("E2M4", disk),
                                 catalog.sector_places({"places": list(mine.values())})["E2M4"])
        for key, row in mine.items():
            self.assertEqual(row["mechanisms"], held.get(key, {}), key)

    def test_a_word_for_a_mechanism_finds_the_rooms_that_hold_one(self):
        from tools import catalog

        found = catalog.find_places(["conveyor"], None, 12)
        self.assertTrue(found)
        for _score, row, why in found:
            self.assertIn("effect:conveyor", row["mechanisms"], row["id"])
            self.assertTrue(any(said.startswith("holds effect:conveyor")
                                for said in why))
        # two words, two shelves: a lift, in a room somebody called a crypt
        both = catalog.find_places(["lift", "crypt"], None, 5)
        self.assertTrue(both)
        self.assertTrue(any("sector:600" in row["mechanisms"]
                            for _s, row, _w in both))

    def test_find_answers_with_parts_and_with_wiring_as_two_things(self):
        from tools import catalog

        said = catalog.find_all(["lift"])
        parts, wires = said.index("PARTS"), said.index("WIRING")
        self.assertLess(parts, wires)
        self.assertIn("carries a body between levels", said[wires:said.index("TILES")])
        self.assertIn("python -m tools.catalog mechanisms", said)
        shown = catalog.show("sector:600")
        self.assertIn("on a wire, set off by:", shown)
        self.assertIn("a part is not a mechanism", shown)

    def test_showing_a_room_says_what_works_in_it_and_what_to_run_next(self):
        from tools import catalog

        said = catalog.show("E1M8:243")
        self.assertIn("works by:", said)
        self.assertIn("effect:conveyor", said)
        self.assertIn("python -m tools.catalog mechanisms E1M8 --place E1M8:243", said)


@unittest.skipUnless(E2M4.exists(), "no E2M4")
class MechanismTests(unittest.TestCase):
    def test_a_chain_is_followed_through_its_relays(self):
        from tools import catalog

        chains = catalog.mechanisms("E2M4")
        self.assertGreater(len(chains), 20)
        deepest = chains[0]
        self.assertGreaterEqual(deepest["depth"], 3)
        self.assertTrue(deepest["cause"])
        #: every step names a sender, a channel and a typed receiver
        for step in deepest["steps"]:
            self.assertTrue(step["channel"] and step["to_type"])


class ThingNamingTests(unittest.TestCase):
    """One view, one thing, a reader told nothing; the name held to a key.

    The owner, 2026-11-19: "Are you doing review the way that you show
    certain thing without telling what it is and then compare description
    with what it supposed to be?"
    """

    def test_an_answer_is_parsed_whatever_surrounds_it(self):
        from tools import critique

        row = critique._parse(
            "[cx] thing-x-q_01 DONE 0m04s\nSTATUS: done\n"
            "NAME: Steam locomotive wheels\nSURE: 4 of 5\n"
            "WHY: spoked wheels and a rod\nODD: nothing\n")
        self.assertEqual(row["name"], "Steam locomotive wheels")
        self.assertEqual(row["sure"], 4)
        self.assertEqual(row["odd"], "nothing")


class FlatSpriteTests(unittest.TestCase):
    """Where a floor-aligned sprite lies, by the engine's arithmetic."""

    def test_a_tile_s_width_lies_a_quarter_turn_from_the_angle(self):
        from bloodmap import flatsprite

        sprite = {"x": 0, "y": 0, "angle": 0, "x_repeat": 64, "y_repeat": 32,
                  "cstat": 32}
        #: 64 texels at repeat 64 is 1,024; at repeat 32, 512. At angle 0
        #: the WIDTH (1,024) runs along the map's y.
        self.assertEqual(flatsprite.box(sprite, (64, 64)),
                         (-256, -512, 256, 512))
        sprite["angle"] = flatsprite.MAP_ALIGNED
        self.assertEqual(flatsprite.box(sprite, (64, 64)),
                         (-512, -256, 512, 256))

    def test_a_tile_s_own_offset_moves_its_centre(self):
        from bloodmap import flatsprite

        sprite = {"x": 0, "y": 0, "angle": flatsprite.MAP_ALIGNED,
                  "x_repeat": 64, "y_repeat": 64, "cstat": 32}
        plain = flatsprite.box(sprite, (64, 64))
        moved = flatsprite.box(sprite, (64, 64), (8, 0))
        self.assertEqual(moved[2] - moved[0], plain[2] - plain[0])
        self.assertNotEqual(moved[0], plain[0])

    def test_cover_tiles_a_rectangle_exactly_or_refuses(self):
        from bloodmap import flatsprite

        rect = (10496, -18560, 20736, -17024)
        pieces = flatsprite.cover(rect, (64, 64))
        boxes = [flatsprite.box({**p, "cstat": 32}, (64, 64)) for p in pieces]
        self.assertEqual(flatsprite.faults(rect, boxes),
                         {"bare": 0, "doubled": 0, "spill": 0})
        with self.assertRaises(flatsprite.FlatSpriteError):
            flatsprite.cover((0, 0, 1001, 1024), (64, 64))


class SecondWalkTests(unittest.TestCase):
    """The owner's second walk of 2026-11-19: split bands. (What it found on the
    built city is a test of the city's own, test_library_city.)"""

    def test_two_bands_one_origin(self):
        from bloodmap.texture_frame import peg_split_bands, wall_z_peg

        def sector(ceiling, floor, ptr, count):
            return {"fields": {"ceiling_z": ceiling, "floor_z": floor,
                               "wall_ptr": ptr, "wall_count": count,
                               "type": 0, "ceiling_stat": 0}}

        def wall(next_sector, cstat=0):
            return {"fields": {"next_sector": next_sector, "cstat": cstat,
                               "x": 0, "y": 0, "point2": 0}}

        class Level:
            sectors = [sector(-40000, 8192, 0, 2), sector(-20000, 0, 2, 1)]
            walls = [wall(1), wall(-1), wall(0)]

        level = Level()
        #: left alone, the engine hangs the window's wall from the sill
        self.assertEqual(wall_z_peg(level, 0), 0)
        self.assertEqual(peg_split_bands(level)["walls"], [0])
        #: now from the room's own ceiling, as the solid wall beside it
        self.assertEqual(wall_z_peg(level, 0), wall_z_peg(level, 1))
        self.assertEqual(peg_split_bands(level)["walls"], [])


class HungThingsTests(unittest.TestCase):
    """The owner, in the game: "there are places with posters which are
    hanging mid air"; and: "not all wall sprites will be on the wall and
    it doesn't mean it is wrong"."""

    def test_a_free_standing_wall_sprite_is_not_judged(self):
        from tools import sprite_fit

        hung = sprite_fit.hung_tiles()
        for poster in (742, 743, 356, 440, 943):
            self.assertIn(poster, hung)
        #: a railing, a gate, a curtain, a cobweb, a banner
        for free in (588, 1044, 147, 1067, 3558):
            self.assertNotIn(free, hung)


if __name__ == "__main__":
    unittest.main()
