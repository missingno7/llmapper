"""The aperture grammar, and the ruler it is measured with.

Two things are under test here and they are not the same thing.

The first is the **unit**. Until 2026-08-27 this project called 0x1600 a player
height. 0x1600 is ``POSTURE.eyeAboveZ``, the camera's offset from the player
sprite's own z -- and ``GetSpriteExtents`` puts that z at the body's *centre*,
not at its feet. So it was neither a body height nor a height above the floor,
and every height the project reasoned about was denominated in a unit 2.67 times
too small. The symptom nobody chased for months was that every rendered
observation was framed from a camera at 25% of room height instead of 67%.

The second is the **grammar**. An opening used to be an absence: its height fell
out of whatever the two rooms on either side happened to be, so a door into a
tall hall silently became a door as tall as the hall. `Aperture` makes that
unrepresentable -- a leaf past `DOOR_MAX` has to be given a word.
"""

from __future__ import annotations

import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CANDIDATE = ROOT / "projects" / "reasoned-authoring-v1" / "level" / "candidate-v7.MAP"


class TheRulerTests(unittest.TestCase):
    """The body, checked against the two engine facts that define it."""

    def test_the_body_is_the_drawn_figure_not_the_posture_offset(self):
        from bloodmap.player_space import PLAYER_PROFILES

        blood = PLAYER_PROFILES["blood"]
        # GetSpriteExtents: a dude's body is bottom-top, and Blood's human dudes
        # are 106px tiles at yrepeat 40 -> 106*40*4.
        self.assertEqual(blood.standing_height, 106 * 40 * 4)
        self.assertEqual(blood.eye_above_centre, 0x1600)
        self.assertNotEqual(blood.standing_height, blood.eye_above_centre,
                            "the body and the camera offset are different things")

    def test_the_eye_sits_between_the_centre_and_the_crown(self):
        """playerStart drops the feet onto the start z, so the eye is
        footOffset + eyeAboveZ above the floor -- and that has to land inside
        the body, not above its head or down at its knees."""
        from bloodmap.player_space import PLAYER_PROFILES

        blood = PLAYER_PROFILES["blood"]
        foot_offset = blood.standing_height // 2
        self.assertEqual(blood.eye_height, foot_offset + blood.eye_above_centre)
        self.assertLess(blood.eye_height, blood.standing_height)
        self.assertGreater(blood.eye_height, blood.standing_height * 0.75)

    def test_clearance_is_the_whole_body(self):
        """The check that was three times too permissive."""
        from bloodmap.player_space import PLAYER_PROFILES

        blood = PLAYER_PROFILES["blood"]
        self.assertEqual(blood.min_passage_height_standing, blood.standing_height)

    def test_no_module_carries_its_own_copy_of_the_unit(self):
        """It was hardcoded in a dozen places, which is how it drifted."""
        import bloodmap.furniture, bloodmap.rules_blood, bloodmap.slope
        import bloodmap.vocabulary, bloodmap.levelprog, bloodmap.patterns
        from bloodmap.player_space import PLAYER_PROFILES

        body = PLAYER_PROFILES["blood"].standing_height
        for module in (bloodmap.furniture, bloodmap.rules_blood, bloodmap.slope,
                       bloodmap.vocabulary, bloodmap.levelprog, bloodmap.patterns):
            self.assertEqual(module.PLAYER_HEIGHT, body, module.__name__)


class LeafTests(unittest.TestCase):

    def test_an_ordinary_door_needs_no_name(self):
        from bloodmap.aperture import Leaf

        leaf = Leaf()                    # the campaign median
        self.assertEqual(leaf.name, "door")
        self.assertAlmostEqual(leaf.height, 1.93)

    def test_a_monumental_leaf_must_be_named(self):
        """The door-into-the-sky rule."""
        from bloodmap.aperture import ApertureError, Leaf

        with self.assertRaises(ApertureError) as caught:
            Leaf(height=5.0)
        message = str(caught.exception)
        self.assertIn("has to be named", message)
        self.assertIn("gate", message)

    def test_the_exception_stays_expressible(self):
        """Cathedral portals are real -- 28% of campaign apertures are over
        three humans tall. The grammar makes them visible, not impossible."""
        from bloodmap.aperture import Leaf

        self.assertEqual(Leaf(height=5.0, name="gate").name, "gate")
        self.assertEqual(Leaf(height=9.0, name="full_height").name, "full_height")

    def test_a_name_may_not_be_stretched_past_its_band(self):
        from bloodmap.aperture import ApertureError, Leaf

        with self.assertRaises(ApertureError) as caught:
            Leaf(height=6.0, name="arch")
        self.assertIn("gate", str(caught.exception))

    def test_a_leaf_shorter_than_a_body_is_refused(self):
        from bloodmap.aperture import ApertureError, Leaf

        with self.assertRaises(ApertureError) as caught:
            Leaf(height=0.5)
        self.assertIn("sprite extent", str(caught.exception))


class MediationTests(unittest.TestCase):

    def test_a_facade_taller_than_the_leaf_needs_mediation_named(self):
        from bloodmap.aperture import Aperture, ApertureError, Leaf

        aperture = Aperture(id="a:test", leaf=Leaf(height=1.93))
        with self.assertRaises(ApertureError) as caught:
            aperture.check_against(4.0)
        message = str(caught.exception)
        self.assertIn("nothing to carry it", message)
        for word in ("lintel", "frame", "vestibule", "full_height"):
            self.assertIn(word, message, "the message should teach the fix")

    def test_a_facade_the_leaf_already_fills_needs_nothing(self):
        from bloodmap.aperture import Aperture, Leaf

        Aperture(id="a:test", leaf=Leaf(height=1.93)).check_against(2.0)

    def test_naming_a_mediation_settles_it(self):
        from bloodmap.aperture import Aperture, Leaf

        Aperture(id="a:test", leaf=Leaf(height=1.93),
                 mediation="lintel").check_against(6.0)

    def test_a_thickness_needs_a_reveal(self):
        from bloodmap.aperture import Aperture, ApertureError

        with self.assertRaises(ApertureError) as caught:
            Aperture(id="a:test", mediation="frame")
        self.assertIn("reveal", str(caught.exception))


class OwnershipTests(unittest.TestCase):
    """The band above a mouth belongs to the room it is seen from.

    Build draws a two-sided wall's upper section from that wall's own picnum, so
    painting a whole portal wall in the material's `opening` tile hangs the
    dressing over the doorway as well as around it. One of these in the
    candidate was a 4.35-human sheet of smooth ashlar on a rubble wall.
    """

    def _layout(self, hall_ceiling):
        from bloodmap.planar_layout import PlanarLayout

        U, PH = 384, 16960
        layout = PlanarLayout(name="ownership")
        layout.add_region(
            "region:hall", [(0, 0), (16 * U, 0), (16 * U, 12 * U), (0, 12 * U)],
            floor_z=0, ceiling_z=hall_ceiling,
            wall_picnum=110, portal_wall_picnum=5,
            floor_picnum=2448, ceiling_picnum=285)
        layout.add_region(
            "region:cell",
            [(16 * U, 4 * U), (22 * U, 4 * U), (22 * U, 8 * U), (16 * U, 8 * U)],
            floor_z=0, ceiling_z=-2 * PH,
            wall_picnum=110, floor_picnum=2448, ceiling_picnum=285)
        layout.add_connection("c:hall_cell", "region:hall", "region:cell",
                              a1=(16 * U, 4 * U), a2=(16 * U, 8 * U),
                              min_width=1536)
        layout.set_player_start("region:hall", x=8 * U, y=6 * U, z=0)
        return layout

    def _portal_tiles(self, layout):
        disk = layout.compile().level.to_disk_map()
        fields = disk.sectors[0].fields
        start, count = int(fields["wall_ptr"]), int(fields["wall_count"])
        return [int(disk.walls[w].fields["picnum"])
                for w in range(start, start + count)
                if int(disk.walls[w].fields["next_sector"]) >= 0]

    def test_an_opening_with_no_lintel_keeps_its_dressing(self):
        """Both ceilings equal: nothing is drawn above the mouth, so the
        dressed jamb is all the player sees and it stays dressed."""
        tiles = self._portal_tiles(self._layout(-2 * 16960))
        self.assertTrue(tiles)
        self.assertEqual(set(tiles), {5})

    def test_an_opening_with_a_lintel_gives_the_band_back_to_the_facade(self):
        """The hall is twice as tall as the cell, so a band is drawn above the
        mouth -- and a band is facade."""
        tiles = self._portal_tiles(self._layout(-4 * 16960))
        self.assertTrue(tiles)
        self.assertEqual(set(tiles), {110})


@unittest.skipUnless(CANDIDATE.exists(), "no built candidate")
class CandidateAuditTests(unittest.TestCase):
    """Part 2's audit, kept as a regression on the number it moved."""

    def test_the_candidate_does_not_break_the_facade_worse_than_blood_by_much(self):
        from bloodmap.format import read_map
        from tools.mine_apertures import observe

        rows = [r for r in observe("candidate", read_map(CANDIDATE))
                if r["aperture"] and r["lintel_player_heights"] > 0]
        self.assertTrue(rows)
        broke = sum(1 for r in rows if not r["lintel_continues_facade"])
        rate = broke / len(rows)
        # It was 60.7% before the compiler took ownership of the band; the
        # campaign runs 29.6%. This guards the fix without pretending the
        # remaining gap is closed.
        self.assertLess(rate, 0.50, "regressed toward dressing the lintels again")


class FramedDoorTests(unittest.TestCase):
    """A door that is a door, not a tile painted up a facade.

    The fault this fixes, measured on the monastery before it: all 8 of the
    level's door faces painted the room's own facade, at 2.00 to 11.00 vertical
    repeats. A shut Z-motion door has zero height, so the band a room shows
    toward it runs from the room's ceiling to the floor -- and `door_face` had
    set that band's tile to the door. The chapel door was 5.31 standing humans
    of plank-and-iron on a courtyard wall.
    """

    def _layout(self):
        from bloodmap.planar_layout import PlanarLayout

        U = 384
        layout = PlanarLayout(name="doortest")
        layout.add_region(
            "region:court", [(0, 0), (16 * U, 0), (16 * U, 12 * U), (0, 12 * U)],
            floor_z=8192, ceiling_z=8192 - 5 * 16960,
            wall_picnum=110, floor_picnum=2448, ceiling_picnum=285)
        layout.add_region(
            "region:door", [(16 * U, 4 * U), (18 * U, 4 * U),
                            (18 * U, 8 * U), (16 * U, 8 * U)],
            floor_z=8192, ceiling_z=8192, type=600,
            wall_picnum=449, floor_picnum=22, ceiling_picnum=22, door_face=22)
        layout.add_region(
            "region:nave", [(18 * U, 0), (34 * U, 0), (34 * U, 12 * U), (18 * U, 12 * U)],
            floor_z=8192, ceiling_z=8192 - 3 * 16960,
            wall_picnum=194, floor_picnum=294, ceiling_picnum=454)
        layout.add_connection("c:court_door", "region:court", "region:door",
                              a1=(16 * U, 4 * U), a2=(16 * U, 8 * U), min_width=1024)
        layout.add_connection("c:door_nave", "region:door", "region:nave",
                              a1=(18 * U, 4 * U), a2=(18 * U, 8 * U), min_width=1024)
        layout.set_player_start("region:court", x=8 * U, y=6 * U, z=8192)
        return layout

    def _framed(self, layout=None):
        from bloodmap.aperture import framed_door

        layout = layout or self._layout()
        built = framed_door(
            layout, "region:door",
            near_edge=((16 * 384, 4 * 384), (16 * 384, 8 * 384)),
            far_edge=((18 * 384, 4 * 384), (18 * 384, 8 * 384)),
            leaf_height_z=32768, face_picnum=22, face_tile_height=128,
            jamb_picnum=449)
        return layout, built

    def test_the_leaf_is_a_whole_number_of_tile_repeats(self):
        """5.50 spans slices the top course through its own iron band."""
        _, built = self._framed()
        self.assertEqual(built["leaf_repeats"], 1)
        self.assertEqual(built["leaf_height_z"], 128 * 2048 // 8)

    def test_one_repeat_is_the_campaign_median_leaf(self):
        """Tile 22 at the y_repeat Blood pins it to spans 32768 z -- 1.93
        standing humans, the campaign's median aperture, and the median number
        of times the tile actually draws up its wall is 1.00 over 540 campaign
        walls. The art's grid and the campaign's door height are the same
        number.
        """
        from bloodmap.aperture import PLAYER_HEIGHT, snap_leaf

        height, repeats = snap_leaf(128, 8, 32768)
        self.assertEqual(repeats, 1)
        self.assertEqual(height, 32768)
        self.assertAlmostEqual(height / PLAYER_HEIGHT, 1.93, places=2)

    def test_the_vertical_span_has_one_definition(self):
        """It had two, reciprocal in y_repeat, agreeing only at y_repeat 16."""
        from bloodmap.aperture import tile_span_z
        from bloodmap.texture_align import repeat_span

        for tile_height, y_repeat in ((128, 8), (64, 8), (256, 16), (128, 32)):
            self.assertEqual(tile_span_z(tile_height, y_repeat),
                             repeat_span(tile_height, y_repeat))

    def test_a_wall_texture_is_square_at_the_pairing_blood_pins(self):
        """Blood's z is 16x finer than x and y, so 2048/y_repeat z per texture
        pixel at y_repeat 8 is the same 16 world units per pixel the facade
        scale runs at horizontally at x_repeat 8.
        """
        from bloodmap.aperture import tile_span_z

        z_per_pixel = tile_span_z(128, 8) / 128
        self.assertEqual(z_per_pixel, 256)
        self.assertEqual(z_per_pixel / 16, 16)

    def test_the_repeat_itself_is_left_alone(self):
        """The obvious fix -- stretch the tile until it draws once -- is one the
        campaign refuses: 9 of its 10 commonest pairings for tile 22 pin
        y_repeat at 8 and vary only the horizontal."""
        _, built = self._framed()
        self.assertEqual(built["face_y_repeat"], 8)

    def test_batch_framer_keeps_motion_and_leaf_height_in_one_declaration(self):
        from bloodmap.aperture import frame_z_doors

        layout = self._layout()
        layout.regions["region:door"].sector_behavior = {
            "off_ceiling_z": 8192, "on_ceiling_z": -23552,
            "off_floor_z": 8192, "on_floor_z": 8192,
        }
        report = frame_z_doors(layout, art_sizes={22: (64, 128)})
        self.assertEqual(len(report["doors"]), 1)
        self.assertEqual(layout.regions["region:door"].sector_behavior["on_ceiling_z"],
                         -24576)
        self.assertIn("region:door_frame_near", layout.regions)
        self.assertIn("region:door_frame_far", layout.regions)

    def test_the_facade_above_the_door_stays_facade(self):
        layout, _ = self._framed()
        disk = layout.compile().level.to_disk_map()
        court = disk.sectors[0].fields
        start, count = int(court["wall_ptr"]), int(court["wall_count"])
        facing = [w for w in range(start, start + count)
                  if int(disk.walls[w].fields["next_sector"]) >= 0]
        self.assertTrue(facing)
        for wall in facing:
            self.assertEqual(int(disk.walls[wall].fields["picnum"]), 110,
                             "the courtyard's own wall should stay rubble")

    def test_the_flats_come_from_the_room_not_the_leaf(self):
        """75.9% of campaign door sectors take their floor picnum from a
        neighbour and 74.4% never use one of their own wall tiles on it. A door
        sector's floor is walked on; it is not the door."""
        layout, built = self._framed()
        near = layout.regions[built["frames"]["near"]]
        self.assertEqual(near.floor_picnum, 2448)
        self.assertNotEqual(near.floor_picnum, 22)
        leaf = layout.regions["region:door"]
        self.assertEqual(leaf.floor_picnum, 2448)
        self.assertNotEqual(leaf.ceiling_picnum, 22)

    def test_a_frame_off_an_open_room_does_not_borrow_its_sky(self):
        """The one exception: a parallax ceiling lent to a roofed frame puts sky
        under a roof, which grades as an engine error."""
        layout = self._layout()
        layout.regions["region:court"].parallax_ceiling = True
        layout.regions["region:court"].ceiling_picnum = 2500
        layout, built = self._framed(layout)
        near = layout.regions[built["frames"]["near"]]
        self.assertEqual(near.ceiling_picnum, 449)

    def test_it_breaks_no_engine_law(self):
        from bloodmap import rules_blood            # noqa: F401
        from bloodmap.rules import evaluate, load_grades

        layout, _ = self._framed()
        disk = layout.compile().level.to_disk_map()
        errors = [f for f in evaluate(disk, grades=load_grades())
                  if f.severity == "error"]
        self.assertEqual([], [(f.code, f.location) for f in errors])


@unittest.skipUnless(CANDIDATE.exists(), "no built candidate")
class CandidateDoorTests(unittest.TestCase):

    def test_no_door_leaf_is_cut_mid_pattern(self):
        """Was 8 of 8, at 2.00 to 11.00 repeats."""
        from bloodmap.format import read_map
        from bloodmap.rules import art_sizes

        sizes = art_sizes()
        if not sizes:
            self.skipTest("no Blood ART")
        disk = read_map(CANDIDATE)
        owner = {}
        for index, sector in enumerate(disk.sectors):
            start = int(sector.fields["wall_ptr"])
            for wall in range(start, start + int(sector.fields["wall_count"])):
                owner[wall] = index
        doors = {i for i, s in enumerate(disk.sectors)
                 if int(s.fields["type"]) in (600, 602)}
        offenders = []
        for wall, item in enumerate(disk.walls):
            other = int(item.fields["next_sector"])
            mine = owner.get(wall)
            if other not in doors or mine is None or mine in doors:
                continue
            here = disk.sectors[mine].fields
            there = disk.sectors[other].fields
            band = (max(int(here["ceiling_z"]), int(there["ceiling_z"]))
                    - int(here["ceiling_z"]))
            if band <= 0:
                continue
            size = sizes.get(int(item.fields["picnum"]))
            if not size:
                continue
            span = size[1] * int(item.fields["y_repeat"]) * 8
            repeats = band / span if span else 0
            if abs(repeats - round(repeats)) > 0.01:
                offenders.append((wall, round(repeats, 2)))
        self.assertEqual([], offenders,
                         "door leaves cut mid-pattern: %s" % offenders)

    def test_no_door_sector_walks_on_its_own_leaf(self):
        """The floor of a reveal is stone, not planking."""
        from bloodmap.format import read_map

        disk = read_map(CANDIDATE)
        offenders = []
        for index, sector in enumerate(disk.sectors):
            if int(sector.fields["type"]) not in (600, 602):
                continue
            start = int(sector.fields["wall_ptr"])
            walls = {int(disk.walls[w].fields["picnum"])
                     for w in range(start, start + int(sector.fields["wall_count"]))}
            if int(sector.fields["floor_picnum"]) in walls:
                offenders.append(index)
        self.assertEqual([], offenders,
                         "door sectors with their own leaf on the floor: %s"
                         % offenders)
