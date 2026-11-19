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
import sys
import tempfile
import unittest
from pathlib import Path

DESIGN = Path("knowledge/blood/design")
PLACES = DESIGN / "places-v1.json"
LOOKS = DESIGN / "tile-looks"
LEVEL = Path("projects/blood-city/level")
CITY = LEVEL / "blood-city-current.MAP"
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


@unittest.skipUnless(CITY.exists(), "the city is not built")
class StationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from bloodmap.format import read_map

        if str(LEVEL) not in sys.path:
            sys.path.insert(0, str(LEVEL))
        import l3_station

        cls.station = l3_station
        cls.disk = read_map(CITY)
        cls.sectors = [s.fields for s in cls.disk.sectors]
        cls.walls = [w.fields for w in cls.disk.walls]

    def _sectors_at(self, rect):
        x0, y0, x1, y1 = rect
        out = []
        for i, s in enumerate(self.sectors):
            pts = [(int(self.walls[w]["x"]), int(self.walls[w]["y"]))
                   for w in range(int(s["wall_ptr"]),
                                  int(s["wall_ptr"]) + int(s["wall_count"]))]
            xs = [p[0] for p in pts]
            ys = [p[1] for p in pts]
            if (min(xs), min(ys), max(xs), max(ys)) == (x0, y0, x1, y1):
                out.append(i)
        return out

    def test_it_stands_outside_the_city_and_is_entered_through_its_wall(self):
        s = self.station
        (door,) = self._sectors_at(s.DOOR)
        d = self.sectors[door]
        around = {int(self.walls[w]["next_sector"]) for w in range(
            int(d["wall_ptr"]), int(d["wall_ptr"]) + int(d["wall_count"]))}
        #: one side is a street under the sky, the other the passage
        self.assertTrue(any(n >= 0 and int(self.sectors[n]["ceiling_stat"]) & 1
                            for n in around))
        self.assertLess(s.HALL[1], 0)                 # north of the edge
        (hall,) = self._sectors_at(s.HALL)
        self.assertEqual(int(self.sectors[hall]["floor_z"]), s.HALL_Z)
        self.assertEqual(int(self.sectors[hall]["floor_z"])
                         - int(self.sectors[hall]["ceiling_z"]), s.HALL_CLEAR)

    def test_the_stair_up_is_one_sloped_floor(self):
        (ramp,) = self._sectors_at(self.station.RAMP)
        self.assertTrue(int(self.sectors[ramp]["floor_heinum"]))
        self.assertTrue(int(self.sectors[ramp]["floor_stat"]) & 2)

    def test_the_track_is_seen_and_the_tunnel_darkens(self):
        s = self.station
        tracks = [i for i, sec in enumerate(self.sectors)
                  if int(sec["floor_picnum"]) == s.TRACK]
        self.assertGreaterEqual(len(tracks), 5)   # three beds, two bores
        #: "You didn't spot that rails are going 90 degrees from train than
        #: they should really go?" -- the track runs east-west, tile 1129's
        #: rails run along its x, so the floor must NOT swap x and y
        for i in tracks:
            self.assertFalse(int(self.sectors[i]["floor_stat"]) & 4)
        from tools import catalog
        self.assertEqual(catalog.directional_floor_faults(self.disk), [])
        wrong = self.disk
        for i in tracks:
            wrong.sectors[i].fields["floor_stat"] |= 4
        self.assertTrue(catalog.directional_floor_faults(wrong))
        for i in tracks:
            wrong.sectors[i].fields["floor_stat"] &= ~4
        #: two tracks wide, so the far one stands empty in view
        self.assertGreaterEqual(s.BED_Y[1] - s.BED_Y[0], 8192)
        shades = sorted(int(self.sectors[i]["floor_shade"]) for i in tracks)
        self.assertGreaterEqual(shades[-1], 55)

    def test_the_carriage_can_be_boarded_and_seen_through(self):
        #: round 1 of the critique: "The train has no windows, doors,
        #: wheels or ends ... reads as a giant billiard-table felt"
        s = self.station
        cx0, cy0, cx1, cy1 = s.CAR
        inside = self._sectors_at((cx0 + s.HULL, cy0 + s.HULL,
                                   cx1 - s.HULL, cy1 - s.HULL))
        self.assertEqual(len(inside), 1)
        car = self.sectors[inside[0]]
        #: its floor is the platform's: one steps in
        self.assertEqual(int(car["floor_z"]), s.HALL_Z)
        self.assertEqual(int(car["floor_picnum"]), s.CARPET)
        #: a person's size: under 5.5 m over all (the first was 7)
        self.assertLessEqual(cy1 - cy0, 3072)
        #: its windows are stretches of its wall that stand only sill
        #: high, eight of them, under the same sky as the platform
        sills = [sec for sec in self.sectors
                 if int(sec["floor_z"]) == s.HALL_Z - s.WINDOW_SILL
                 and int(sec["floor_picnum"]) == s.WOOD
                 and int(sec["ceiling_stat"]) & 1]
        self.assertEqual(len(sills), 8)
        self.assertTrue(int(car["ceiling_stat"]) & 1)
        #: and its roof is twenty solid floor sprites at the walls' top
        roof = [sp.fields for sp in self.disk.sprites
                if int(sp.fields["picnum"]) == s.ROOF
                and int(sp.fields["cstat"]) & 32
                and cx0 <= int(sp.fields["x"]) <= cx1
                and cy0 <= int(sp.fields["y"]) <= cy1]
        self.assertEqual(len(roof), 20)
        for sprite in roof:
            self.assertTrue(int(sprite["cstat"]) & 1)          # solid
            self.assertEqual(int(sprite["z"]), s.HALL_Z - s.CAR_H)
        #: and it FITS. The owner, in the game: "sprite roof on carriage
        #: doesn't align". Measured with the engine's own arithmetic, the
        #: pieces cover the inside with nothing bare, doubled or spilt.
        from bloodmap import flatsprite
        from tools import sprite_fit
        tile = sprite_fit.art()[s.ROOF]
        inner = (cx0 + s.HULL, cy0 + s.HULL, cx1 - s.HULL, cy1 - s.HULL)
        boxes = [flatsprite.box(sp, (tile.width, tile.height)) for sp in roof]
        self.assertEqual(flatsprite.faults(inner, boxes),
                         {"bare": 0, "doubled": 0, "spill": 0})
        #: the first roof, as it was written: angle 0, 64 by 48
        wrong = [dict(sp, angle=0, x_repeat=64, y_repeat=48) for sp in roof]
        was = flatsprite.faults(inner, [flatsprite.box(
            sp, (tile.width, tile.height)) for sp in wrong])
        self.assertGreater(was["bare"], 0)
        self.assertGreater(was["spill"], 0)
        livery = [w for w in self.walls if int(w["picnum"]) == s.LIVERY]
        self.assertGreaterEqual(len(livery), 8)
        wheels = [sp for sp in self.disk.sprites
                  if int(sp.fields["picnum"]) == s.WHEELS["picnum"]]
        #: tile 2320 is three coupled wheels in one picture: one sprite
        #: TO A SIDE (the owner, from the track: "locomotive is missing
        #: wheels on the other side"), each facing out
        self.assertEqual(len(wheels), 2)
        self.assertEqual(len({int(sp.fields["y"]) for sp in wheels}), 2)
        self.assertEqual(len({int(sp.fields["angle"]) for sp in wheels}), 2)

    def test_the_office_lever_opens_the_carriage(self):
        s = self.station

        def extra(item):
            return getattr(getattr(item, "extra", None), "fields", None) or {}

        levers = [sp for sp in self.disk.sprites
                  if int(extra(sp).get("tx_id", 0)) == s.CAR_DOOR_CHANNEL]
        doors = [sec for sec in self.disk.sectors
                 if int(extra(sec).get("rx_id", 0)) == s.CAR_DOOR_CHANNEL]
        self.assertEqual((len(levers), len(doors)), (1, 1))
        #: on the hall's column beside the door's bay, where pulling it is
        #: SEEN to do something (critique rounds 3 and 4)
        self.assertLess(abs(int(levers[0].fields["x"]) - s.CAR_DOOR_X[0]),
                        1024)
        self.assertLess(abs(int(levers[0].fields["y"]) - s.HALL[1]), 512)
        door = doors[0].fields
        self.assertEqual(int(door["type"]), 600)
        #: shut: its floor stands at the roof; the lever sinks it
        self.assertEqual(int(door["floor_z"]), s.HALL_Z - s.CAR_H)
        self.assertEqual(int(extra(doors[0])["on_floor_z"]), s.HALL_Z)
        #: a clerk behind bars, and the tunnel barred
        bars = [w for w in self.walls if int(w["over_picnum"]) == s.BARS]
        self.assertGreaterEqual(len(bars), 2)

    def test_the_signal_box_s_lever_raises_the_tunnel_s_gate(self):
        #: the owner: "you might add some more places, rooms, balcony (some
        #: height to it) ... add some interactivity, triggers"
        s = self.station

        def extra(item):
            return getattr(getattr(item, "extra", None), "fields", None) or {}

        levers = [sp for sp in self.disk.sprites
                  if int(extra(sp).get("tx_id", 0)) == s.GATE_CHANNEL]
        gates = [sec for sec in self.disk.sectors
                 if int(extra(sec).get("rx_id", 0)) == s.GATE_CHANNEL]
        self.assertEqual((len(levers), len(gates)), (1, 1))
        self.assertEqual(int(gates[0].fields["type"]), 600)
        (box,) = self._sectors_at(s.SIGNAL_BOX)
        self.assertEqual(int(levers[0].fields["sector"]), box)
        #: the box stands 1.2 bodies over the platform, with a balcony
        (balcony,) = self._sectors_at(s.BALCONY)
        for index in (box, balcony):
            self.assertEqual(int(self.sectors[index]["floor_z"]),
                             s.HALL_Z - s.SIGNAL_UP)
        self.assertTrue(int(self.sectors[balcony]["ceiling_stat"]) & 1)
        #: the gate wears the owner's roll-up gate
        self.assertTrue(any(int(w["picnum"]) == s.ROLLUP for w in self.walls))

    def test_no_sky_is_lowered_and_the_line_goes_somewhere(self):
        #: the owner: "this will make it working without lowering sky which
        #: looks bad from the outside"
        s = self.station
        from bloodmap import rules_blood, skyline
        self.assertEqual(
            rules_blood._open_neighbours_share_a_sky(self.disk).violations, ())
        cx0, cy0, cx1, cy1 = s.CAR
        lowered = {row["sector"] for row in skyline.lowered_skies(self.disk)}
        for i in lowered:
            w = self.walls[int(self.sectors[i]["wall_ptr"])]
            self.assertFalse(cx0 - 512 <= int(w["x"]) <= cx1 + 512
                             and cy0 - 512 <= int(w["y"]) <= cy1 + 512, i)
        (store,) = [i for i in self._sectors_at(s.STORE)] or [None]
        self.assertIsNotNone(store)
        (waiting,) = [i for i in self._sectors_at(s.WAITING)] or [None]
        self.assertIsNotNone(waiting)

    def test_it_says_its_name_and_was_built_from_a_study(self):
        from bloodmap.lettering import read_sign
        from tools import study

        words = {word for word, _ids in read_sign(self.disk)}
        self.assertIn("GRAVESEND", words)
        self.assertIn("STATION", words)               # on the street
        boards = {int(sp.fields["picnum"]) for sp in self.disk.sprites}
        self.assertIn(self.station.BOARDS["tickets"], boards)
        self.assertEqual(study.notes_written(study.STUDIES / "station"), [])

    def test_the_first_version_failed_its_critique_and_the_record_is_kept(self):
        from tools import critique

        rounds = critique.verdict("station")
        self.assertGreaterEqual(len(rounds), 1)
        first = rounds[0]
        #: three readers, 2 out of 5 each, not recognised without words
        self.assertFalse(first["passes"])
        self.assertEqual(first["reviews_missing"], [])
        self.assertTrue(first["blocking"])


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

    def test_the_first_round_is_kept_and_it_was_not_kind(self):
        from tools import critique

        packet = critique.STUDIES / "station" / "critique" / "things-1"
        if not (packet / "answers.json").exists():
            self.skipTest("no things round recorded")
        report = critique.score_things("station", 1)
        #: every reader got more of Blood's own right than of ours
        for model, row in report["models"].items():
            got, asked = row["controls_named"]
            ours, of = row["ours_named"]
            self.assertGreater(got / asked, ours / of, model)
        #: the track was named by everyone; the carriage's side by nobody
        self.assertEqual(report["things"]["t_track"]["hits"],
                         report["things"]["t_track"]["asked"])
        self.assertEqual(report["things"]["t_car_side"]["hits"], 0)
        #: a key that leaks is no key: the questions carry no thing's name
        key = critique.json.loads((packet / "key.json").read_text("utf-8"))
        for q in key:
            self.assertRegex(q, r"^q_\d\d$")


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


@unittest.skipUnless(CITY.exists(), "the city is not built")
class SecondWalkTests(unittest.TestCase):
    """The owner's second walk of 2026-11-19: the station's sprites, the
    jetty, the ship's crates, the flanks, the back door, split bands."""

    @classmethod
    def setUpClass(cls):
        from bloodmap.format import read_map

        cls.disk = read_map(CITY)
        cls.sectors = [s.fields for s in cls.disk.sectors]
        cls.walls = [w.fields for w in cls.disk.walls]
        cls.owner = {}
        for index, s in enumerate(cls.sectors):
            for w in range(int(s["wall_ptr"]),
                           int(s["wall_ptr"]) + int(s["wall_count"])):
                cls.owner[w] = index

    def _box(self, sector):
        s = self.sectors[sector]
        ws = range(int(s["wall_ptr"]), int(s["wall_ptr"]) + int(s["wall_count"]))
        xs = [int(self.walls[w]["x"]) for w in ws]
        ys = [int(self.walls[w]["y"]) for w in ws]
        return min(xs), min(ys), max(xs), max(ys)

    def test_the_railing_blocks_and_the_face_is_seen_from_behind(self):
        rails = [s.fields for s in self.disk.sprites
                 if int(s.fields["picnum"]) == 588]
        self.assertTrue(rails)
        for rail in rails:
            self.assertTrue(int(rail["cstat"]) & 1)            # solid
            self.assertFalse(int(rail["cstat"]) & 64)          # two-sided
        faces = [s.fields for s in self.disk.sprites
                 if int(s.fields["picnum"]) == 634
                 and int(s.fields["y"]) < 0]
        self.assertTrue(faces)
        for face in faces:
            self.assertFalse(int(face["cstat"]) & 64)

    def test_a_body_fits_between_the_jetty_s_posts(self):
        import sys as _sys
        if str(LEVEL) not in _sys.path:
            _sys.path.insert(0, str(LEVEL))
        import l3_market

        jx0, jx1, _length = l3_market.JETTY
        clear = (jx1 - jx0) * 1024 - 2 * (64 + 256)
        #: Blood's player is 2 * 164 wide to the engine's clipping, and
        #: 384 between the posts was not enough in the game
        self.assertGreaterEqual(clear, 1024)

    def test_the_ship_s_crates_wear_whole_tiles(self):
        crates = [i for i, s in enumerate(self.sectors)
                  if int(s["floor_picnum"]) == 452
                  and 56 * 1024 < self._box(i)[1] < 62 * 1024]
        self.assertEqual(len(crates), 2)
        for i in crates:
            x0, y0, x1, y1 = self._box(i)
            self.assertEqual((x1 - x0, y1 - y0), (1024, 1024))
            faces = [w for w in self.walls if int(w["next_sector"]) == i]
            self.assertEqual(len(faces), 4)
            for w in faces:
                self.assertEqual(int(w["picnum"]), 452)
                #: 64 texels across a 64-texel tile, begun at its edge
                self.assertEqual(int(w["x_repeat"]), 8)
                self.assertEqual(int(w["x_panning"]) % 64, 0)
            #: and 64 texels up it: 16,384 at y_repeat 8
            lower = max(int(self.sectors[self.owner[k]]["floor_z"])
                        for k, w in enumerate(self.walls)
                        if int(w["next_sector"]) == i)
            self.assertEqual(lower - int(self.sectors[i]["floor_z"]), 16384)

    def test_a_flank_is_its_building_without_the_windows(self):
        import sys as _sys
        if str(LEVEL) not in _sys.path:
            _sys.path.insert(0, str(LEVEL))
        import facade_pass

        for x, beyond in ((4096, -1), (53248, 1)):
            front = [w for k, w in enumerate(self.walls)
                     if int(w["next_sector"]) < 0 and int(w["y"]) == 57344
                     and int(self.walls[int(w["point2"])]["y"]) == 57344
                     and x in (int(w["x"]),
                               int(self.walls[int(w["point2"])]["x"]))
                     and (int(w["x"]) + int(self.walls[int(w["point2"])]["x"])
                          - 2 * x) * beyond > 0]
            self.assertEqual(len(front), 1)
            flank = [w for w in self.walls
                     if int(w["next_sector"]) < 0 and int(w["x"]) == x
                     and int(self.walls[int(w["point2"])]["x"]) == x
                     and 57344 <= int(w["y"]) <= 65536]
            self.assertTrue(flank)
            for w in flank:
                self.assertEqual(int(w["picnum"]),
                                 facade_pass.BLANK_OF[int(front[0]["picnum"])])
                self.assertNotIn(int(w["picnum"]), facade_pass.WINDOWED)

    def test_the_hall_s_back_door_is_a_door_in_a_frame(self):
        leaves = [i for i, s in enumerate(self.sectors)
                  if int(s["type"]) == 600
                  and 6144 <= self._box(i)[0] and self._box(i)[2] <= 8192
                  and 50688 <= self._box(i)[1] and self._box(i)[3] <= 51200]
        self.assertEqual(len(leaves), 1)
        #: the leaf is not on the street: a reveal stands between them, at
        #: door height, so the wall above belongs to the facade
        around = {int(self.walls[w]["next_sector"]) for w in range(
            int(self.sectors[leaves[0]]["wall_ptr"]),
            int(self.sectors[leaves[0]]["wall_ptr"])
            + int(self.sectors[leaves[0]]["wall_count"]))} - {-1}
        self.assertEqual(len(around), 2)
        for other in around:
            s = self.sectors[other]
            self.assertFalse(int(s["ceiling_stat"]) & 1)
            self.assertLess(int(s["floor_z"]) - int(s["ceiling_z"]), 40000)

    def test_no_wall_in_two_bands_hangs_from_two_places(self):
        from bloodmap.texture_frame import split_bands_unpegged

        self.assertEqual(split_bands_unpegged(self.disk), [])

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


@unittest.skipUnless(CITY.exists(), "the city is not built")
class HungThingsTests(unittest.TestCase):
    """The owner, in the game: "there are places with posters which are
    hanging mid air"; and: "not all wall sprites will be on the wall and
    it doesn't mean it is wrong"."""

    def test_no_paper_or_board_hangs_on_no_wall(self):
        from bloodmap.format import read_map
        from tools import sprite_fit

        self.assertEqual(sprite_fit.unbacked(read_map(CITY)), [])

    def test_a_free_standing_wall_sprite_is_not_judged(self):
        from tools import sprite_fit

        hung = sprite_fit.hung_tiles()
        for poster in (742, 743, 356, 440, 943):
            self.assertIn(poster, hung)
        #: a railing, a gate, a curtain, a cobweb, a banner
        for free in (588, 1044, 147, 1067, 3558):
            self.assertNotIn(free, hung)

    def test_the_balcony_s_railing_is_seen_from_both_sides(self):
        from bloodmap.format import read_map

        rails = [s.fields for s in read_map(CITY).sprites
                 if int(s.fields["picnum"]) == 588]
        self.assertTrue(rails)
        for rail in rails:
            self.assertEqual(int(rail["cstat"]) & 48, 16)      # wall aligned
            self.assertFalse(int(rail["cstat"]) & 64)          # two-sided

    def test_one_can_step_off_the_platform_onto_the_track(self):
        import sys as _sys
        if str(LEVEL) not in _sys.path:
            _sys.path.insert(0, str(LEVEL))
        import l3_station as s
        from bloodmap.format import read_map

        disk = read_map(CITY)
        sectors = [x.fields for x in disk.sectors]
        walls = [x.fields for x in disk.walls]
        edges = 0
        for index, sec in enumerate(sectors):
            if int(sec["floor_z"]) != s.HALL_Z:
                continue
            for w in range(int(sec["wall_ptr"]),
                           int(sec["wall_ptr"]) + int(sec["wall_count"])):
                other = int(walls[w]["next_sector"])
                if (other >= 0 and int(sectors[other]["floor_picnum"]) == s.TRACK
                        and int(sectors[other]["floor_z"]) == s.BED_Z):
                    edges += 1
                    self.assertFalse(int(walls[w]["cstat"]) & 1, w)
        self.assertGreaterEqual(edges, 5)


class CriticBenchTests(unittest.TestCase):
    """The owner: "which model is best critic ... how to do objective test"."""

    def test_an_answer_with_a_fault_is_parsed(self):
        from tools import critic_bench

        row = critic_bench.parse("NAME: Railway track\nSURE: 4\n"
                                 "FAULT: Yes\nWHAT: rails run across\n")
        self.assertTrue(row["ok"] and row["fault"])
        self.assertFalse(critic_bench.parse("NAME: x\n")["ok"])

    def test_every_fault_has_a_clean_twin_and_the_key_names_nothing(self):
        from tools import critic_bench

        path = critic_bench.BENCH / "key.json"
        if not path.exists():
            self.skipTest("no benchmark built")
        key = critic_bench.json.loads(path.read_text("utf-8"))
        kinds = [row["kind"] for row in key.values()]
        self.assertEqual(kinds.count("fault"), len(critic_bench.FAULTS))
        self.assertGreaterEqual(kinds.count("clean") + kinds.count("naming"),
                                2 * kinds.count("fault"))
        twins = {row["truth"].split(": ")[1] for row in key.values()
                 if row["kind"] == "clean"}
        self.assertEqual(twins, {pose for pose, _ in
                                 critic_bench.FAULTS.values()})
        for q in key:
            self.assertRegex(q, r"^b_\d\d$")


if __name__ == "__main__":
    unittest.main()
