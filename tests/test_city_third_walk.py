"""What the owner found on the third walk of Gravesend, held.

2026-11-18, after the second build of the day: "Edges of that sea looks bad
because they connect straight to buildings, it should have something to
visually divide it, places where player can't reach, but will see"; "We
should have more windows in buildings around the city"; the fire
extinguisher "is usually thing that will explode and reveal hole in the
wall behind it ... secret room for example in staff only part of arcades";
"Some things you created are simpistic ... there is no combination of
decals and textures making it to look like something, for example in that
pump station"; "I would add these stained window glass decorative sprites
also inside"; "come up with some tools or conventions how to really make
the places to be memorable"; and "think about stuff in relations, like
this machine connects to this, there is a control panel here, there is a
dirty water tank".
"""

from __future__ import annotations

import json
import sys
import types
import unittest
from pathlib import Path

LEVEL = Path("projects/blood-city/level")
CITY = LEVEL / "blood-city-current.MAP"
MANIFEST = LEVEL.parent / "reports" / "build-manifest.json"
E3M5 = Path("maps/blood/campaign/E3M5.MAP")


def _level():
    if str(LEVEL) not in sys.path:
        sys.path.insert(0, str(LEVEL))


def _extra(item) -> dict:
    return getattr(getattr(item, "extra", None), "fields", None) or {}


class PlaceCharacterTests(unittest.TestCase):
    def test_a_bare_box_carries_no_layer_and_a_dressed_one_does(self):
        from tools.place_character import Geometry, place_of, profile

        def disk(tiles, sprites=()):
            corners = [(0, 0), (4096, 0), (4096, 4096), (0, 4096)]
            walls = [types.SimpleNamespace(fields={
                "x": x, "y": y, "point2": (i + 1) % 4, "next_sector": -1,
                "next_wall": -1, "picnum": tiles[i], "cstat": 0})
                for i, (x, y) in enumerate(corners)]
            sector = types.SimpleNamespace(extra=None, fields={
                "wall_ptr": 0, "wall_count": 4, "floor_z": 8192,
                "ceiling_z": -8192, "floor_picnum": 1, "ceiling_picnum": 2,
                "floor_shade": 0, "ceiling_stat": 0, "type": 0})
            return types.SimpleNamespace(
                sectors=[sector], walls=walls,
                sprites=[types.SimpleNamespace(fields=dict(
                    {"sector": 0, "status": 0, "type": 0, "picnum": 9}, **s))
                    for s in sprites])

        bare = Geometry(disk([5, 5, 5, 5]))
        self.assertEqual(profile(bare, place_of(bare, 0))["layer_count"], 0)
        dressed = Geometry(disk([5, 5, 6, 6], [{"cstat": 16}, {"cstat": 32}]))
        got = profile(dressed, place_of(dressed, 0))
        self.assertTrue(got["layers"]["second"])
        self.assertTrue(got["layers"]["wall_art"])
        self.assertTrue(got["layers"]["flat_art"])

    @unittest.skipUnless(E3M5.exists(), "no E3M5")
    def test_bloods_foundry_is_not_thin_by_its_own_measure(self):
        from bloodmap.format import read_map
        from tools.place_character import (Geometry, judge, load_norms,
                                           place_of, profile)

        geom = Geometry(read_map(E3M5))
        got = profile(geom, place_of(geom, 2))
        self.assertGreaterEqual(got["wall_tile_count"], 4)
        self.assertFalse(judge(got, load_norms())["thin"])


class DetailingTests(unittest.TestCase):
    def test_a_panel_gets_its_own_vertices(self):
        _level()
        import detailing

        detailing.reset()
        region = types.SimpleNamespace(
            outer=((0, 0), (4096, 0), (4096, 4096), (0, 4096)), holes=())
        layout = types.SimpleNamespace(regions={"r": region})
        detailing.panel("r", (1024, 0), (2048, 0), 498)
        self.assertEqual(detailing.split(layout)["vertices"], 2)
        self.assertIn((1024, 0), region.outer)
        self.assertIn((2048, 0), region.outer)
        detailing.reset()


@unittest.skipUnless(CITY.exists() and MANIFEST.exists(),
                     "the city is not built")
class ThirdWalkTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from bloodmap.format import read_map

        cls.disk = read_map(CITY)
        cls.sectors = [s.fields for s in cls.disk.sectors]
        cls.walls = [w.fields for w in cls.disk.walls]
        cls.sprites = [s.fields for s in cls.disk.sprites]
        cls.manifest = json.loads(MANIFEST.read_text("utf-8"))
        cls.tags = json.loads(
            (LEVEL / "blood-city-current.tags.json").read_text("utf-8"))

    def test_rock_stands_between_the_sea_and_the_town(self):
        _level()
        import l3_market

        rocks = [self.sectors[i] for i in self.tags["sea_rock"]]
        heads = [s for s in rocks
                 if int(s["floor_picnum"]) == l3_market.ROCK_FLOOR]
        self.assertGreaterEqual(len(heads), 5)    # 2 heads, 2 crests, skerry
        piles = [s for s in rocks
                 if int(s["floor_picnum"]) == l3_market.PILE_TILE]
        self.assertEqual(len(piles), 8)
        water = 8192 + l3_market.SEA_DROP
        for s in rocks:
            #: out of reach: over a body above the water it stands in
            self.assertGreater(water - int(s["floor_z"]), 16960)

    def test_the_far_sea_is_seen_and_not_reached(self):
        water = [i for i, s in enumerate(self.sectors)
                 if int(s["floor_picnum"]) == 2490
                 and int(s["ceiling_stat"]) & 1]
        near = min(water, key=lambda i: min(
            int(self.walls[w]["y"]) for w in range(
                int(self.sectors[i]["wall_ptr"]),
                int(self.sectors[i]["wall_ptr"])
                + int(self.sectors[i]["wall_count"]))))
        s = self.sectors[near]
        out = [self.walls[w] for w in range(
            int(s["wall_ptr"]), int(s["wall_ptr"]) + int(s["wall_count"]))
            if int(self.walls[w]["next_sector"]) in water]
        self.assertTrue(out)
        for wall in out:
            self.assertTrue(int(wall["cstat"]) & 1)

    def test_every_edge_building_has_windows(self):
        _level()
        import facade_pass

        edge = self.manifest["building_backs"]["edge"]
        blank = 0
        for s in self.sectors:
            if not int(s["ceiling_stat"]) & 1:
                continue
            for w in range(int(s["wall_ptr"]),
                           int(s["wall_ptr"]) + int(s["wall_count"])):
                a = self.walls[w]
                if int(a["next_sector"]) >= 0:
                    continue
                b = self.walls[int(a["point2"])]
                x0, y0, x1, y1 = (int(a["x"]), int(a["y"]),
                                  int(b["x"]), int(b["y"]))
                on_edge = ((x0 == x1 and x0 in (edge[0], edge[2]))
                           or (y0 == y1 and y0 in (edge[1], edge[3])))
                if on_edge and abs(x1 - x0) + abs(y1 - y0) >= 4096:
                    blank += int(a["picnum"]) not in facade_pass.WINDOWED
        self.assertEqual(blank, 0)

    def test_the_extinguisher_opens_a_secret(self):
        _level()
        import l3_mall

        channel = l3_mall.SECRET_CHANNEL
        senders = [s for s in self.disk.sprites
                   if int(_extra(s).get("tx_id", 0)) == channel]
        self.assertEqual(len(senders), 1)
        f, x = senders[0].fields, _extra(senders[0])
        #: E3M4 sprite 331: a gib object a bullet breaks, sending on death
        self.assertEqual((int(f["picnum"]), int(f["type"]), int(f["status"])),
                         (658, 416, 4))
        self.assertTrue(int(x["trigger_vector"]) and int(x["trigger_off"]))
        seals = [s for s in self.disk.sectors
                 if int(_extra(s).get("rx_id", 0)) == channel]
        self.assertEqual(len(seals), 1)
        seal = seals[0].fields
        self.assertEqual(int(seal["type"]), 600)
        self.assertEqual(int(seal["floor_z"]), int(seal["ceiling_z"]))  # shut
        self.assertEqual(int(_extra(seals[0])["busy_time_a"]), 1)
        charges = [s for s in self.disk.sprites
                   if int(s.fields["type"]) == 459
                   and int(_extra(s).get("rx_id", 0)) == channel]
        self.assertEqual(len(charges), 3)
        self.assertTrue(all(int(_extra(s)["wait_time"]) > 0 for s in charges))
        secrets = [s for s in self.disk.sectors
                   if int(_extra(s).get("tx_id", 0)) == 2
                   and int(_extra(s).get("command", 0)) == 64]
        self.assertEqual(len(secrets), 3)

    def test_shop_glass_can_be_shot_out(self):
        glazed = [w for w in self.walls if int(w["over_picnum"]) == 266
                  and int(w["cstat"]) & 16]
        self.assertTrue(glazed)
        for wall in glazed:
            self.assertEqual(int(wall["type"]), 511)     # kWallGib

    def test_the_church_has_its_glass_inside(self):
        inside = [s for s in self.sprites if int(s["picnum"]) == 569
                  and 27136 <= int(s["x"]) <= 32256
                  and 22016 <= int(s["y"]) <= 30720]
        self.assertGreaterEqual(len(inside), 16)
        #: a clerestory on BOTH sides of the nave
        east = [s for s in inside if abs(int(s["x"]) - 30720) < 64]
        west = [s for s in inside if abs(int(s["x"]) - 28160) < 64]
        self.assertGreaterEqual(len(east), 5)
        self.assertGreaterEqual(len(west), 5)

    def test_the_machine_hall_is_composed_and_wired(self):
        _level()
        import l3_shed

        row = self.manifest["character"]["places"]["pump machine hall"]
        self.assertGreaterEqual(row["layer_count"], row["campaign_p50"])
        tiles = {t for t, _share in row["wall_tiles"]}
        self.assertGreaterEqual(len(tiles & set(l3_shed.PIPES)), 2)
        self.assertGreaterEqual(row["shade_spread"], 12)
        consoles = {int(w["picnum"]) for w in self.walls} & set(l3_shed.CONSOLES)
        self.assertEqual(consoles, set(l3_shed.CONSOLES))
        #: the lever by the consoles runs the belt, and nothing else does
        channel = l3_shed.BELT_CHANNEL
        belts = [s for s in self.disk.sectors
                 if int(_extra(s).get("rx_id", 0)) == channel]
        self.assertEqual(len(belts), sum(
            1 for _n, press in l3_shed.BELT_SECTIONS if not press))
        #: the presses are E3M5's crushers: they slam, kill, and re-trigger
        presses = [s for s in self.disk.sectors
                   if int(_extra(s).get("rx_id", 0)) == l3_shed.CRUSH_CHANNEL]
        self.assertEqual(len(presses), 2)
        for press in presses:
            x = _extra(press)
            self.assertEqual(int(press.fields["type"]), 600)
            self.assertEqual((int(x["crush"]), int(x["retrigger_a"]),
                              int(x["retrigger_b"]), int(x["pan_always"])),
                             (1, 1, 1, 1))
            self.assertEqual(int(x["on_ceiling_z"]), int(x["on_floor_z"]))
            self.assertLess(int(x["off_ceiling_z"]), int(x["on_ceiling_z"]))
        starters = [s for s in self.disk.sprites
                    if int(_extra(s).get("tx_id", 0)) == l3_shed.CRUSH_CHANNEL]
        self.assertEqual(len(starters), 1)
        self.assertEqual(int(_extra(starters[0])["rx_id"]),
                         l3_shed.LEVEL_START)
        for belt in belts:
            x = _extra(belt)
            self.assertEqual((int(x["pan_floor"]), int(x["pan_always"]),
                              int(x["state"])), (1, 0, 1))
        levers = [s for s in self.disk.sprites
                  if int(_extra(s).get("tx_id", 0)) == channel]
        self.assertEqual(len(levers), 1)
        #: the settling basin is open and its sewage moves
        basins = [s for s in self.disk.sectors
                  if int(s.fields["floor_picnum"]) == l3_shed.SEWAGE
                  and not int(s.fields["ceiling_stat"]) & 1
                  and int(_extra(s).get("pan_floor", 0))
                  and int(s.fields["floor_z"]) < 8192]
        self.assertEqual(len(basins), 1)

    def test_the_quay_wall_has_a_flank_and_the_piles_a_jetty(self):
        #: "the sea connection to city looks poor, there is a wall that
        #: directly ends into sky"
        _level()
        import l3_market

        import facade_pass
        #: a flank is its building's wall WITHOUT the window
        flank = [w for w in self.walls
                 if int(w["picnum"]) in set(facade_pass.BLANK_OF.values())
                 and int(w["next_sector"]) < 0
                 and int(w["x"]) in (4096, 53248)
                 and 57344 <= int(w["y"]) <= 65536]
        self.assertGreaterEqual(len(flank), 4)
        jetties = [self.sectors[i] for i in self.tags["jetty"]]
        self.assertEqual(len(jetties), 1)
        self.assertEqual(int(jetties[0]["floor_z"]), 8192)   # the quay's
        #: every post stands IN the jetty
        jetty = self.tags["jetty"][0]
        posts = [i for i in self.tags["sea_rock"]
                 if int(self.sectors[i]["floor_picnum"])
                 == l3_market.PILE_TILE]
        for i in posts:
            s = self.sectors[i]
            around = {int(self.walls[w]["next_sector"]) for w in range(
                int(s["wall_ptr"]), int(s["wall_ptr"]) + int(s["wall_count"]))}
            self.assertEqual(around, {jetty})

    def test_windows_are_looked_through_and_glazed_or_barred(self):
        #: "Windows should really be windows where you can look from inside
        #: outside, you can put bars there or glass"
        _level()
        import windows

        ids = set(self.tags["window"])
        self.assertGreaterEqual(len(ids), 6)      # a reveal and a pocket each
        owner = {}
        for i, s in enumerate(self.sectors):
            for w in range(int(s["wall_ptr"]),
                           int(s["wall_ptr"]) + int(s["wall_count"])):
                owner[w] = i
        glass = bars = 0
        to_street = to_room = 0
        for i in ids:
            s = self.sectors[i]
            self.assertEqual(int(s["floor_z"]), 8192 - windows.THROUGH_SILL)
            self.assertEqual(int(s["floor_z"]) - int(s["ceiling_z"]),
                             windows.THROUGH_HEIGHT)
            for w in range(int(s["wall_ptr"]),
                           int(s["wall_ptr"]) + int(s["wall_count"])):
                wall = self.walls[w]
                other = int(wall["next_sector"])
                if other < 0:
                    continue
                if other in ids:
                    #: the pane: between the window's own two volumes, so
                    #: no step band shares its record, and it blocks
                    self.assertTrue(int(wall["cstat"]) & 16)
                    self.assertTrue(int(wall["cstat"]) & 1)
                    if int(wall["over_picnum"]) == windows.BARS:
                        bars += 1
                    else:
                        self.assertEqual(int(wall["over_picnum"]), 266)
                        self.assertEqual(int(wall["type"]), 511)
                        glass += 1
                else:
                    self.assertFalse(int(wall["cstat"]) & 16)
                    if int(self.sectors[other]["ceiling_stat"]) & 1:
                        to_street += 1
                    else:
                        to_room += 1
        #: every window opens on a street one side and a room the other
        self.assertEqual(to_street, len(ids) // 2)
        self.assertEqual(to_room, len(ids) // 2)
        self.assertGreaterEqual(glass, 2)
        self.assertGreaterEqual(bars, 2)
        #: and the blind recesses are gone
        self.assertNotIn("window_niche", self.tags)

    def test_the_sea_is_bloods_sea_and_the_ship_has_a_deck(self):
        #: the harbour study: two blind reviews read the water as grass
        _level()
        import l3_market

        seas = [(i, s) for i, s in enumerate(self.sectors)
                if int(s["floor_picnum"]) == l3_market.SEA_TILE
                and int(s["ceiling_stat"]) & 1]
        self.assertGreaterEqual(len(seas), 3)
        for i, s in seas:
            self.assertEqual(int(s["floor_pal"]), l3_market.SEA_PAL)
            self.assertEqual(int(s["floor_z"]) - 8192, l3_market.SEA_DROP)
            self.assertGreaterEqual(int(s["floor_shade"]), 38)
            x = _extra(self.disk.sectors[i])
            self.assertTrue(int(x.get("pan_floor", 0)))      # it moves
        #: nobody steps off the quay into water he cannot leave
        near = min(seas, key=lambda r: min(
            int(self.walls[w]["y"]) for w in range(
                int(r[1]["wall_ptr"]),
                int(r[1]["wall_ptr"]) + int(r[1]["wall_count"]))))[1]
        for w in range(int(near["wall_ptr"]),
                       int(near["wall_ptr"]) + int(near["wall_count"])):
            wall = self.walls[w]
            other = int(wall["next_sector"])
            if other >= 0 and int(self.sectors[other]["floor_z"]) == 8192:
                self.assertTrue(int(wall["cstat"]) & 1)
        #: crates on the deck and the black flag at the mast
        flags = [s for s in self.sprites if int(s["picnum"]) == 3558]
        self.assertEqual(len(flags), 1)
        crates = [s for s in self.sectors
                  if int(s["floor_picnum"]) == l3_market.CRATE
                  and int(s["ceiling_stat"]) & 1]
        self.assertEqual(len(crates), 2)

    def test_the_church_is_lit_from_the_floor_and_toward_the_altar(self):
        #: the church study: every surface stood at shade 32
        _level()
        import l3_church

        def room(x, y):
            for s in self.sectors:
                pts = [(int(self.walls[w]["x"]), int(self.walls[w]["y"]))
                       for w in range(int(s["wall_ptr"]),
                                      int(s["wall_ptr"]) + int(s["wall_count"]))]
                xs = [p[0] for p in pts]
                ys = [p[1] for p in pts]
                if (min(xs) <= x <= max(xs) and min(ys) <= y <= max(ys)
                        and int(s["floor_z"]) in (8192, 6144)
                        and not int(s["ceiling_stat"]) & 1
                        and max(xs) - min(xs) <= 2560):
                    return s
            return None

        nave, chancel = room(29440, 30400), room(29440, 22600)
        self.assertLess(int(nave["floor_shade"]), int(nave["ceiling_shade"]))
        self.assertLess(int(chancel["floor_shade"]), int(nave["floor_shade"]))
        great = [s for s in self.sprites
                 if int(s["picnum"]) == l3_church.GREAT_WINDOW["tile"]]
        self.assertEqual(len(great), 1)
        self.assertLess(int(great[0]["shade"]), 0)
        self.assertEqual(sum(1 for s in self.sprites
                             if int(s["picnum"]) == 580), 2)

    def test_nothing_is_laid_on_the_belt(self):
        #: "that pipe entrance decoration on the conveyor belt instead on
        #: the floor, sometimes we have details like this missed"
        from tools.sprite_fit import on_travelling_floor

        self.assertEqual(on_travelling_floor(self.disk), [])

    def test_the_crypt_is_under_the_church_and_a_slab_goes_down_to_it(self):
        #: "it says crypt, but shouldn't there be access to crypt? the
        #: crypt should be under the church"
        _level()
        import l3_church

        lifts = [i for i, s in enumerate(self.disk.sectors)
                 if int(s.fields["type"]) == 600
                 and int(_extra(s).get("on_floor_z", 0))
                 == l3_church.CRYPT_FLOOR
                 and int(_extra(s).get("off_floor_z", 0)) == 8192]
        self.assertEqual(len(lifts), 1)
        lift = self.disk.sectors[lifts[0]]
        self.assertTrue(int(_extra(lift)["trigger_enter"]))
        self.assertGreater(int(_extra(lift)["busy_time_a"]), 0)
        s = lift.fields
        around = {int(self.walls[w]["next_sector"]) for w in range(
            int(s["wall_ptr"]), int(s["wall_ptr"]) + int(s["wall_count"]))}
        floors = {int(self.sectors[n]["floor_z"]) for n in around if n >= 0}
        #: one neighbour on the church's floor, one on the crypt's
        self.assertEqual(floors, {8192, l3_church.CRYPT_FLOOR})
        x0, y0, x1, y1 = l3_church.CRYPT
        self.assertLessEqual(27136, y1)          # under the narthex's plan

    def test_the_crypt_is_e1m1s_kind_of_crypt(self):
        #: "The crypt doesn't really look like a crypt, check E1M1"
        _level()
        import l3_church

        crypts = [s for s in self.sectors
                  if int(s["floor_z"]) == l3_church.CRYPT_FLOOR
                  and int(s["floor_picnum"]) == l3_church.CRYPT_EARTH]
        self.assertEqual(len(crypts), 1)
        crypt = crypts[0]
        rubble = sum(1 for w in range(
            int(crypt["wall_ptr"]),
            int(crypt["wall_ptr"]) + int(crypt["wall_count"]))
            if int(self.walls[w]["picnum"]) == l3_church.CRYPT_WALL
            and int(self.walls[w]["next_sector"]) < 0)
        self.assertGreaterEqual(rubble, 4)
        #: one sarcophagus: a wooden lid, and four SLOPED shoulders under it
        parts = [self.sectors[i] for i in self.tags["sarcophagus"]]
        lids = [s for s in parts
                if int(s["floor_picnum"]) == l3_church.LID_TILE]
        shoulders = [s for s in parts if int(s["floor_heinum"])
                     and int(s["floor_stat"]) & 2]
        self.assertEqual((len(lids), len(shoulders)), (1, 4))
        lid = lids[0]
        self.assertEqual(l3_church.CRYPT_FLOOR - int(lid["floor_z"]),
                         l3_church.CHEST_SIDE + l3_church.SHOULDER_RISE + 2048)
        #: plaques and cobwebs, E1M1's own fields
        plaques = [s for s in self.sprites if int(s["picnum"]) == 128
                   and int(s["pal"]) == 8 and int(s["type"]) == 417]
        webs = [s for s in self.sprites
                if int(s["picnum"]) in (1067, 1068) and int(s["cstat"]) & 2]
        self.assertEqual(len(plaques), len(l3_church.PLAQUES))
        self.assertEqual(len(webs), len(l3_church.COBWEBS))
        #: room to walk round it: a body's aisle on every side
        lx0, ly0, lx1, ly1 = l3_church.SARCOPHAGUS
        x0, y0, x1, y1 = l3_church.CRYPT
        edge = l3_church.SHOULDER
        self.assertGreaterEqual(min(lx0 - edge - x0, x1 - lx1 - edge), 1024)

    def test_the_crypt_wall_cracks_through_to_the_sewer(self):
        #: "connect crypt to sewers, like a wall crack that you need use
        #: explosive to"; "TNT barrels storage ... with cascade explosions"
        import math
        _level()
        import l3_church

        channel = l3_church.BREACH_CHANNEL
        cracks = [s for s in self.disk.sprites
                  if int(s.fields["type"]) == 408
                  and int(_extra(s).get("tx_id", 0)) == channel]
        self.assertEqual(len(cracks), 2)             # crypt side, sewer side
        seals = [i for i, s in enumerate(self.disk.sectors)
                 if int(_extra(s).get("rx_id", 0)) == channel]
        #: a ragged hole: three pieces that open to different heights
        self.assertEqual(len(seals), len(l3_church.BREACH_PIECES))
        opens = set()
        for i in seals:
            seal = self.disk.sectors[i].fields
            self.assertEqual(int(seal["type"]), 600)
            self.assertEqual(int(seal["floor_z"]), int(seal["ceiling_z"]))
            x = _extra(self.disk.sectors[i])
            opens.add(int(x["off_ceiling_z"]) - int(x["on_ceiling_z"]))
        self.assertGreater(len(opens), 1)
        barrels = [s.fields for s in self.disk.sprites
                   if int(s.fields["type"]) == 400]
        self.assertEqual(len(barrels), len(l3_church.BARRELS))
        #: a fuse: each within reach of the next (the campaign stacks them
        #: 512 apart), and the last within reach of the crack
        for a, b in zip(barrels, barrels[1:]):
            self.assertLessEqual(math.hypot(int(a["x"]) - int(b["x"]),
                                            int(a["y"]) - int(b["y"])), 640)
        crack = min(cracks, key=lambda s: int(s.fields["x"])).fields
        self.assertLessEqual(math.hypot(
            int(barrels[-1]["x"]) - int(crack["x"]),
            int(barrels[-1]["y"]) - int(crack["y"])), 640)
        for barrel in barrels:
            floor = int(self.sectors[int(barrel["sector"])]["floor_z"])
            self.assertEqual(floor - int(barrel["z"]),
                             l3_church.BARREL_LIFT)   # standing, not sunk

    def test_things_are_the_size_blood_builds_them(self):
        #: "crypt feels tiny, crypt elevator is just for a player to stand
        #: ... That hole that get blown into sewers is just a narrow strip
        #: ... pump station ... feels like a miniature"
        _level()
        import l3_church
        import l3_shed
        import scale

        lx0, ly0, lx1, ly1 = l3_church.CRYPT_LIFT
        self.assertGreaterEqual(min(lx1 - lx0, ly1 - ly0), 1024)
        self.assertGreaterEqual((lx1 - lx0) * (ly1 - ly0),
                                scale.LIFT_MEDIAN[0] * scale.LIFT_MEDIAN[1])
        width = l3_church.BREACH[3] - l3_church.BREACH[1]
        self.assertGreaterEqual(width, scale.HOLE_MEDIAN[0])
        tallest = max(h for _a, _b, h in l3_church.BREACH_PIECES)
        self.assertGreaterEqual(tallest, scale.bodies(scale.HOLE_MEDIAN[1]))
        self.assertGreaterEqual(l3_church.CRYPT_CLEAR,
                                scale.bodies(scale.ROOM_HEIGHT[0]))
        self.assertGreaterEqual(l3_shed.HALL_CLEAR, scale.bodies(5.5))
        self.assertGreaterEqual(l3_shed.TANK_RADIUS, 1024)
        places = self.manifest["character"]["places"]
        crypt, hall = places["St Gallow's crypt"], places["pump machine hall"]
        self.assertEqual(crypt["cramped"], [])
        self.assertEqual(hall["cramped"], [])
        #: metres: short side, long side, height
        self.assertGreaterEqual(crypt["metres"][0], 6.0)
        self.assertGreaterEqual(crypt["metres"][2], 3.4)
        self.assertGreaterEqual(hall["metres"][2], 10.0)
        #: room to walk round what stands in it
        self.assertGreaterEqual(crypt["free_floor_share"], 0.7)

    def test_scale_speaks_in_bodies_and_metres(self):
        _level()
        import scale

        self.assertEqual(scale.bodies(1), 16896)        # 16,960 on the grid
        self.assertAlmostEqual(scale.metres(1060), 1.8, places=1)
        self.assertAlmostEqual(scale.metres(1024), 1.7, places=1)

    def test_no_named_place_is_thin_and_no_channel_dangles(self):
        sheet = self.manifest["character"]
        self.assertEqual(sheet["thin"], [])
        self.assertEqual(sheet["unfound"], [])
        self.assertEqual(sheet["dangling_channels"], [])
        for name, row in sheet["places"].items():
            self.assertTrue(row["hero"], name)
            self.assertTrue(row["exemplar"], name)


if __name__ == "__main__":
    unittest.main()
