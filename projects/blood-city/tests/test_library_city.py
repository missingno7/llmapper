"""The station built from the library, the owner's second walk of it, and what hangs on its walls: read off the built city."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

LEVEL = Path("projects/blood-city/level")
CITY = LEVEL / "blood-city-current.MAP"
E2M4 = Path("maps/blood/campaign/E2M4.MAP")


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

    def test_it_stands_outside_the_city_and_is_entered_by_the_avenues_arches(self):
        s = self.station
        self.assertLess(s.HALL[1], 0)                 # north of the edge
        (hall,) = self._sectors_at(s.HALL)
        self.assertEqual(int(self.sectors[hall]["floor_z"]), s.HALL_Z)
        self.assertEqual(int(self.sectors[hall]["floor_z"])
                         - int(self.sectors[hall]["ceiling_z"]), s.HALL_CLEAR)
        #: the owner, 2026-11-25: "That station side entry probably doesn't make sense
        #: any more": no way through the city's wall but the two arches' gates
        #: (under the street the sewers and the railway's stair go where they like)
        under = {w for f in self.sectors if int(f["floor_z"]) > 40000 for w in range(int(f["wall_ptr"]), int(f["wall_ptr"]) + int(f["wall_count"]))}
        ways = {(int(a["x"]), int(b["x"])) for a, b in ((w, self.walls[int(w["point2"])]) for k, w in enumerate(self.walls) if k not in under)
                if int(a["y"]) == int(b["y"]) == 0 and int(a["next_sector"]) >= 0 and abs(int(a["x"]) - int(b["x"])) > 0}
        for x0, x1 in ways:
            self.assertTrue(s.FORECOURT[0][0] <= min(x0, x1) and max(x0, x1) <= s.FORECOURT[-1][1], (x0, x1))

    def test_the_booking_hall_climbs_to_the_platform(self):
        import booking_hall as hall
        levels = sorted({int(sec["floor_z"]) for sec in self.sectors
                         if any(int(self.walls[w]["x"]) == round(hall.STAIR[0] * 1024)
                                and -13313 <= int(self.walls[w]["y"]) <= -11600
                                for w in range(int(sec["wall_ptr"]), int(sec["wall_ptr"]) + int(sec["wall_count"])))
                         and int(sec["floor_z"]) > hall.TOP})
        steps = [b - a for a, b in zip([hall.TOP, *levels], levels)]
        self.assertEqual(len(levels), hall.TREADS + 1)          # the flight's treads and the floor
        self.assertTrue(all(0 < step <= 5120 for step in steps), steps)

    def test_the_track_is_seen_and_the_tunnel_darkens(self):
        s = self.station
        tracks = [i for i, sec in enumerate(self.sectors)
                  if int(sec["floor_picnum"]) == s.TRACK and int(sec["floor_z"]) == s.BED_Z]
        self.assertGreaterEqual(len(tracks), 5)   # three beds, two bores
        #: "You didn't spot that rails are going 90 degrees from train than
        #: they should really go?" -- the track runs east-west, tile 1129's
        #: rails run along its x, so the floor must NOT swap x and y
        for i in tracks:
            self.assertFalse(int(self.sectors[i]["floor_stat"]) & 4)
        from bloodmap.tile_looks import directional_floor_faults
        self.assertEqual(directional_floor_faults(self.disk), [])
        wrong = self.disk
        for i in tracks:
            wrong.sectors[i].fields["floor_stat"] |= 4
        self.assertTrue(directional_floor_faults(wrong))
        for i in tracks:
            wrong.sectors[i].fields["floor_stat"] &= ~4
        #: two tracks wide, so the far one stands empty in view
        self.assertGreaterEqual(s.BED_Y[1] - s.BED_Y[0], 8192)
        shades = sorted(int(self.sectors[i]["floor_shade"]) for i in tracks)
        #: The far bore was shade 60 so the line ran out into the dark. It
        #: holds the level's exit switch now, and the owner, playing it on
        #: 2026-11-19: "that exit switch is in the very dark corridor, not
        #: sure why we made that one strip that dark when other rooms
        #: around it are lit." His walk outranks the round that asked for
        #: the dark: the tunnel keeps a step of fade and stays readable.
        #: (The switch is in the carriage since 2026-11-25, and the second
        #: bore holds nothing but the dark the line goes into.)
        self.assertGreater(shades[-1], shades[0])
        self.assertLessEqual(shades[-2], 36)

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
                  if int(sp.fields["picnum"]) == s.WHEELS["picnum"]
                  and s.FRAME[0] <= int(sp.fields["x"]) <= s.FRAME[2]
                  and abs(int(sp.fields["y"]) - s.AXIS) < 2048]
        #: tile 2320 is three coupled wheels in one picture: one sprite
        #: TO A SIDE (the owner, from the track: "locomotive is missing
        #: wheels on the other side"), each facing out
        self.assertEqual(len(wheels), 2)
        self.assertEqual(len({int(sp.fields["y"]) for sp in wheels}), 2)
        self.assertEqual(len({int(sp.fields["angle"]) for sp in wheels}), 2)

    def test_the_signal_opens_the_carriage_and_the_carriage_is_the_way_out(self):
        s = self.station

        def extra(item):
            return getattr(getattr(item, "extra", None), "fields", None) or {}

        relays = [sp for sp in self.disk.sprites
                  if int(extra(sp).get("tx_id", 0)) == s.CAR_DOOR_CHANNEL]
        doors = [sec for sec in self.disk.sectors
                 if int(extra(sec).get("rx_id", 0)) == s.CAR_DOOR_CHANNEL]
        self.assertEqual((len(relays), len(doors)), (1, 1))
        #: six seconds after the signal box's lever, and out of sight
        self.assertEqual(int(extra(relays[0])["rx_id"]), s.GATE_CHANNEL)
        self.assertEqual(int(extra(relays[0])["wait_time"]), 60)
        self.assertTrue(int(relays[0].fields["cstat"]) & 32768)
        #: the emblem that ends the level is inside it, at the engine's end
        exits = [sp.fields for sp in self.disk.sprites if int(extra(sp).get("tx_id", 0)) == 4]
        self.assertEqual(len(exits), 1)
        cx0, cy0, cx1, cy1 = s.CAR
        self.assertTrue(cx1 - 1024 < int(exits[0]["x"]) < cx1 and cy0 < int(exits[0]["y"]) < cy1)
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
        #: (a goods store stood at the line's end: the owner, 2026-11-25, "badly aligned box textures")
        self.assertFalse([w for w in self.walls if int(w["picnum"]) == s.CRATE and int(w["y"]) < 0])

    def test_it_says_its_name_and_was_built_from_a_study(self):
        from bloodmap.lettering import read_sign
        from tools import study

        words = {word for word, _ids in read_sign(self.disk)}
        self.assertIn("GRAVESEND", words)
        self.assertIn("GRAVESENDSTATION", words)      # over the portico
        boards = {int(sp.fields["picnum"]) for sp in self.disk.sprites}
        self.assertIn(self.station.BOARDS["tickets"], boards)
        self.assertEqual(study.notes_written(study.STUDIES / "station"), [])

    def test_the_first_version_failed_its_critique_and_the_record_is_kept(self):
        from tools import critique

        from bloodmap import project

        rounds = critique.verdict(project.named("blood-city"), "station")
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

    def test_the_first_round_is_kept_and_it_was_not_kind(self):
        from tools import critique

        from bloodmap import project

        city = project.named("blood-city")
        packet = city.rounds("station") / "things-1"
        if not (packet / "answers.json").exists():
            self.skipTest("no things round recorded")
        report = critique.score_things(city, "station", 1)
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


@unittest.skipUnless(CITY.exists(), "the city is not built")
class HungThingsTests(unittest.TestCase):
    """The owner, in the game: "there are places with posters which are
    hanging mid air"; and: "not all wall sprites will be on the wall and
    it doesn't mean it is wrong"."""

    def test_no_paper_or_board_hangs_on_no_wall(self):
        from bloodmap.format import read_map
        from tools import sprite_fit

        self.assertEqual(sprite_fit.unbacked(read_map(CITY)), [])

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


if __name__ == "__main__":
    unittest.main()
