"""Facade grammar (Phase 7).

`06_...md`: the facade owns the openings. So a facade is found as a coherent
run of street-facing wall and the openings are what interrupt it, and signage
is a member of the hierarchy rather than decoration.

Every number quoted here is measured in `reports/blood-facade-grammar.md`.
"""

from __future__ import annotations

import copy
import json
from collections import Counter
import unittest
from pathlib import Path

from bloodmap.anchors import (
    ALIGN_TO_CEILING,
    FACADE_BAY,
    FACADE_MIN_BAYS,
    FACADE_UNITS_PER_TILE_PIXEL,
    _collinear_runs,
    _facade_scale,
    _rhythm,
    find_facades,
)
from bloodmap.format import SECTOR_FIELDS, WALL_FIELDS, encode_map, parse_map
from bloodmap.lettering import FIRST_LETTER
from bloodmap.model import DiskObject
from tests.helpers import corpus_map, synthetic_two_sector_map


ROOT = Path(__file__).resolve().parents[1]
REPORT = ROOT / "reports" / "blood-facade-grammar.json"

STREET_FLOOR = 0
STREET_CEILING = -65536
SKY = 1


def quarter_turn(build):
    """`rotate_quarter_turns` mutates in place and returns None."""
    turned = copy.deepcopy(build)
    turned.rotate_quarter_turns(1)
    return turned


def street_scene(*, openings=(1, 3, 5), sign_at=None, stray_at=(), sky=True,
                 bays=8, step=FACADE_BAY, corner=False, room_depth=1024,
                 room_ceiling=STREET_CEILING + 16384, seam_at=()):
    """A sky-lit street with a straight wall along one side.

    The wall runs `bays` bays divided into walls of `step` units, and
    `openings` names the walls that are two-sided, each leading to a shallow
    room whose floor and ceiling give the run a sill and a header datum.
    `sign_at` places letter sprites against the wall, in bays;
    `stray_at` places them out in the roadway, at (x, y) in world units.
    `corner` opens the east wall too, so the street has two facades meeting at
    a right angle -- the case where one letter is within a bay of both.
    `room_depth` is how deep the rooms behind the openings are: shallower than
    half a bay and they are dressing, not rooms. `room_ceiling` is what makes
    a two-sided wall an opening: at the street's own ceiling there is no
    lintel, and the wall is a seam in the ground rather than a hole in a wall.
    `seam_at` names bays that get such a neighbour whatever `room_ceiling` is.
    Everything is on the 1024 grid, because the point of the fixture is that
    the extractor finds the grid when it is there.
    """
    disk = synthetic_two_sector_map()
    walls, sectors = [], []

    def add_wall(x, y, point2, *, next_wall=-1, next_sector=-1, picnum=400,
                 x_repeat=8, cstat=0):
        fields = {name: 0 for name, _codec in WALL_FIELDS}
        fields.update(x=x, y=y, point2=point2, next_wall=next_wall,
                      next_sector=next_sector, picnum=picnum, over_picnum=-1,
                      x_repeat=x_repeat, cstat=cstat, extra=-1)
        walls.append(DiskObject(fields))

    def add_sector(wall_ptr, wall_count, floor_z, ceiling_z, *, parallax=False):
        fields = {name: 0 for name, _codec in SECTOR_FIELDS}
        fields.update(wall_ptr=wall_ptr, wall_count=wall_count, floor_z=floor_z,
                      ceiling_z=ceiling_z, extra=-1,
                      ceiling_stat=SKY if parallax else 0)
        sectors.append(DiskObject(fields))

    # The street: a rectangle whose south edge is the facade, split into
    # walls of `step` units.
    span = bays * FACADE_BAY
    south = [(i * step, 0) for i in range(span // step)]
    loop = south + [(span, 0), (span, 4096), (0, 4096)]
    first = 0
    for index, (x, y) in enumerate(loop):
        add_wall(x, y, first + (index + 1) % len(loop))
    add_sector(0, len(loop), STREET_FLOOR, STREET_CEILING, parallax=sky)

    # One room per opening, linked to the wall it sits behind.
    for order, bay in enumerate(tuple(openings) + tuple(seam_at)):
        base = len(walls)
        x0 = bay * step
        room = [(x0, 0), (x0, -room_depth), (x0 + step, -room_depth),
                (x0 + step, 0)]
        for index, (x, y) in enumerate(room):
            add_wall(x, y, base + (index + 1) % len(room))
        walls[base + 3].fields.update(next_wall=bay, next_sector=1 + order)
        walls[bay].fields.update(next_wall=base + 3, next_sector=1 + order,
                                 cstat=ALIGN_TO_CEILING)
        add_sector(base, len(room), STREET_FLOOR - 2048,
                   STREET_CEILING if bay in seam_at else room_ceiling)

    if corner:
        base = len(walls)
        east = [(span, 0), (span + 1024, 0), (span + 1024, 4096), (span, 4096)]
        for index, (x, y) in enumerate(east):
            add_wall(x, y, base + (index + 1) % len(east))
        room = 1 + len(openings)
        walls[base + 3].fields.update(next_wall=bays, next_sector=0)
        walls[bays].fields.update(next_wall=base + 3, next_sector=room)
        add_sector(base, len(east), STREET_FLOOR - 2048, STREET_CEILING + 16384)

    sprites = []
    template = copy.deepcopy(disk.sprites[0])
    placements = [(int(bay * FACADE_BAY), 64) for bay in (sign_at or ())]
    placements += [(int(x), int(y)) for x, y in stray_at]
    for index, (x, y) in enumerate(placements):
        sprite = copy.deepcopy(template)
        sprite.fields.update(x=x, y=y, z=STREET_FLOOR - 40000, sector=0,
                             picnum=FIRST_LETTER + index, type=0, cstat=16,
                             angle=0, index=index, extra=-1, owner=-1)
        sprite.extra = None
        sprites.append(sprite)
    if not sprites:
        sprite = copy.deepcopy(disk.sprites[0])
        sprite.fields.update(x=2048, y=2048, z=STREET_FLOOR, sector=0, picnum=1,
                             type=0, cstat=0, extra=-1, owner=-1)
        sprite.extra = None
        sprites.append(sprite)

    disk.sectors, disk.walls, disk.sprites = sectors, walls, sprites
    disk.header.update(num_sectors=len(sectors), num_walls=len(walls),
                       num_sprites=len(sprites), start_sector=0,
                       start_x=2048, start_y=2048)
    return parse_map(encode_map(disk)).to_build_ir()


class FacadeRunTests(unittest.TestCase):
    def setUp(self):
        self.build = street_scene()
        self.facades = find_facades(self.build)

    def test_the_street_wall_is_one_facade_and_its_openings_belong_to_it(self):
        street = [f for f in self.facades if f.host == 0]
        self.assertTrue(street)
        facade = max(street, key=lambda f: f.measures["run_length_units"])
        self.assertEqual(len(facade.openings), 3)
        self.assertGreaterEqual(facade.bays["run_bays"], FACADE_MIN_BAYS)
        self.assertTrue(facade.basis)

    def test_an_opening_narrower_than_a_bay_is_not_called_a_whole_bay(self):
        """Only 31% of campaign street openings land on whole bays, so a rule
        that rounded them onto the grid would be reporting the grid it
        assumed rather than the one the level has.
        """
        build = street_scene(step=512, openings=(2, 6, 10))
        facade = max(find_facades(build),
                     key=lambda f: f.measures["run_length_units"])
        self.assertEqual(len(facade.openings), 3)
        self.assertEqual(facade.bays["whole_bay_openings"], 0)
        for opening in facade.openings:
            self.assertEqual(opening["width_bays"], 0.5)

    def test_the_openings_land_on_whole_bays(self):
        facade = max(self.facades, key=lambda f: f.measures["run_length_units"])
        self.assertEqual(facade.bays["whole_bay_openings"], len(facade.openings))
        for opening in facade.openings:
            self.assertEqual(opening["width_bays"], 1.0)

    def test_a_room_behind_an_opening_is_not_a_thin_helper(self):
        """44% of campaign multi-opening facades carry a thin helper sector --
        a kerb strip, an opening frame. That number means nothing if every
        room behind a window counts as one.
        """
        facade = max(self.facades, key=lambda f: f.measures["run_length_units"])
        self.assertEqual(facade.measures["helper_sectors"], 0)
        self.assertEqual(facade.helpers, ())

    def test_a_sector_shallower_than_half_a_bay_is_a_thin_helper(self):
        build = street_scene(room_depth=256)
        facade = max(find_facades(build),
                     key=lambda f: f.measures["run_length_units"])
        self.assertEqual(facade.measures["helper_sectors"], 3)

    def test_the_openings_share_a_sill_and_a_header_datum(self):
        """What makes them one facade: the same lines, not proximity."""
        facade = max(self.facades, key=lambda f: f.measures["run_length_units"])
        self.assertGreaterEqual(facade.datums["repeated_sill"], 2)
        self.assertGreaterEqual(facade.datums["repeated_header"], 2)

    def test_the_cornice_is_reported_absent_with_its_reason(self):
        """A street sector's ceiling is the sky, so the top of a facade is
        painted rather than built."""
        facade = self.facades[0]
        self.assertIsNone(facade.datums["cornice"])
        self.assertIn("sky", facade.datums["cornice_note"])

    def test_a_two_sided_wall_with_no_lintel_is_a_seam_not_an_opening(self):
        """A kerb, a step, the seam between two sectors of one street: the
        neighbour keeps the street's own ceiling, so there is no hole in any
        wall. 3187 of the 4331 two-sided walls on campaign facade runs are
        that, and the first version of this counted every one as an opening.
        """
        build = street_scene(room_ceiling=STREET_CEILING)
        facades = find_facades(build, require_openings=False)
        self.assertTrue(facades)
        facade = max(facades, key=lambda f: f.measures["run_length_units"])
        self.assertEqual(facade.openings, ())
        self.assertEqual(len(facade.seams), 3)
        self.assertEqual(facade.measures["seams"], 3)

    def test_a_run_interrupted_only_by_seams_is_not_a_facade(self):
        self.assertEqual(find_facades(street_scene(room_ceiling=STREET_CEILING)), [])

    def test_a_kerb_reached_through_a_seam_is_still_a_thin_helper(self):
        """The helper is a fact about the neighbour, not about how the run
        reaches it -- the E3M2 kerb strip is on the far side of a seam.
        """
        build = street_scene(room_ceiling=STREET_CEILING, room_depth=256)
        facade = max(find_facades(build, require_openings=False),
                     key=lambda f: f.measures["run_length_units"])
        self.assertEqual(facade.openings, ())
        self.assertEqual(facade.measures["helper_sectors"], 3)

    def test_an_indoor_wall_is_not_a_facade(self):
        """Without a sky-lit host there is no street to face."""
        self.assertEqual(find_facades(street_scene(sky=False)), [])

    def test_a_run_shorter_than_two_bays_is_not_a_facade(self):
        self.assertEqual(find_facades(street_scene(bays=1, openings=(0,))), [])

    def test_a_blank_wall_carries_no_facade_by_default(self):
        blank = street_scene(openings=())
        self.assertEqual(find_facades(blank), [])
        self.assertTrue(find_facades(blank, require_openings=False))

    def test_a_corner_ends_a_run(self):
        """A facade that turned a corner would have no plane to measure
        datums against."""
        build = street_scene()
        runs = _collinear_runs(build, list(range(0, 11)))
        self.assertEqual(runs[0], list(range(8)), "the eight-bay south wall")
        self.assertGreater(len(runs), 1)

    def test_a_corner_ends_a_north_south_run_too(self):
        """The mutation this catches: measuring the candidate wall's *near*
        end instead of its far end. In a closed loop the near end is the
        previous wall's end, which lies on the line by construction, so the
        offset collapses to |dx_run| * |dy| / L -- right for an east-west run
        and identically zero for a north-south one. That shipped once, and it
        ran every north-south street straight through its own corners.
        """
        build = street_scene()
        turned = quarter_turn(build)
        runs = _collinear_runs(turned, list(range(0, 11)))
        self.assertEqual(len(runs), len(_collinear_runs(build, list(range(0, 11)))))
        self.assertEqual(len(runs[0]), 8)

    def test_a_facade_is_the_same_facade_after_a_quarter_turn(self):
        """Frame independence: the whole extractor, not just the corner rule."""
        def summary(build):
            return sorted((f.host, f.bays["run_bays"], f.rhythm,
                           f.datums["repeated_header"], len(f.openings))
                          for f in find_facades(build))

        self.assertEqual(summary(self.build), summary(quarter_turn(self.build)))

    def test_off_map_geometry_is_not_mined(self):
        self.assertEqual(find_facades(self.build, sector_kinds={0: "signature"}), [])


class FacadeScaleTests(unittest.TestCase):
    def test_a_wall_at_sixteen_units_per_tile_pixel_is_at_facade_scale(self):
        """73% of 5275 campaign street walls are, which is what makes a
        1024-unit bay a real thing rather than a chosen number."""
        build = street_scene()
        self.assertTrue(_facade_scale(build, 0))
        self.assertEqual(FACADE_UNITS_PER_TILE_PIXEL * 64, FACADE_BAY)

    def test_a_wall_at_another_scale_is_not(self):
        build = street_scene()
        build.walls[0]["fields"]["x_repeat"] = 32
        self.assertFalse(_facade_scale(build, 0))


class RhythmTests(unittest.TestCase):
    def test_even_spacing_repeats(self):
        self.assertEqual(_rhythm([0, 1024, 2048, 3072], 4096), "repeating")

    def test_one_opening_has_no_rhythm(self):
        self.assertEqual(_rhythm([1024], 4096), "single")

    def test_two_openings_astride_the_middle_are_centered(self):
        self.assertEqual(_rhythm([1536, 2560], 4096), "centered")

    def test_two_openings_bunched_at_one_end_are_not_centered(self):
        """Two openings are the commonest multi-opening case, so `centered`
        has to mean something: astride the middle, not merely a pair."""
        self.assertEqual(_rhythm([0, 512], 8192), "irregular")

    def test_two_alternating_gaps_are_not_called_repeating(self):
        self.assertEqual(_rhythm([0, 512, 2048, 2560, 4096, 4608], 5632),
                         "alternating")

    def test_an_authored_break_is_kept_as_its_own_class(self):
        """`06_...md` asks not to regularize authored irregularity away."""
        self.assertEqual(_rhythm([0, 1024, 2048, 3072, 8192], 9216),
                         "intentionally_broken")

    def test_noise_is_called_irregular_rather_than_forced(self):
        self.assertEqual(_rhythm([0, 700, 2400, 2600, 6000], 7000), "irregular")


class SignageTests(unittest.TestCase):
    """Signage is a member of the hierarchy, not decoration."""

    def setUp(self):
        self.build = street_scene(sign_at=(2.0, 2.5, 3.0))
        self.facades = [f for f in find_facades(self.build) if f.signage]

    def test_the_letters_attach_to_the_facade_they_stand_on(self):
        self.assertEqual(len(self.facades), 1)
        self.assertEqual(len(self.facades[0].signage), 3)

    def test_a_sign_is_placed_in_bays_along_the_run_and_heights_above_the_street(self):
        signs = sorted(self.facades[0].signage, key=lambda s: s["along_run_bays"])
        self.assertAlmostEqual(signs[0]["along_run_bays"], 2.0, places=2)
        self.assertAlmostEqual(signs[-1]["along_run_bays"], 3.0, places=2)
        for sign in signs:
            self.assertGreater(sign["height_above_street_player_heights"], 0)
            self.assertTrue(sign["wall_aligned"])

    def test_a_letter_is_never_counted_on_two_facades(self):
        """Two runs of one street can both be within a bay of the same word --
        a letter near a corner is near both planes. Counting it twice reports
        one shopfront as two, so the nearest plane takes it.
        """
        build = street_scene(corner=True, stray_at=((8100, 100),))
        facades = find_facades(build)
        self.assertGreaterEqual(len(facades), 2, "a south run and an east run")
        seen = [s["sprite"] for f in facades for s in f.signage]
        self.assertEqual(seen, ["sprite:0"])
        self.assertEqual(len(seen), len(set(seen)))

    def test_a_map_without_letters_reports_no_signage(self):
        for facade in find_facades(street_scene()):
            self.assertEqual(facade.signage, ())

    def test_a_letter_out_in_the_roadway_belongs_to_no_facade(self):
        """The plane is what a sign is measured against, so a letter sprite
        standing free in the street -- on a pole, a van, a hoarding -- is not
        that facade's signage however close along the run it is.
        """
        build = street_scene(stray_at=((2048, 3900),))
        for facade in find_facades(build):
            self.assertEqual(facade.signage, ())

    def test_a_letter_past_the_end_of_the_run_belongs_to_no_facade(self):
        """Build binds a sprite to a sector by a field, not by geometry, so a
        letter listed in the street sector can sit past the end of any one of
        its runs -- around the corner, on the next frontage. The run's own
        extent is what decides, with a bay of slack at each end.
        """
        build = street_scene(stray_at=((10240, 64),))
        for facade in find_facades(build):
            self.assertEqual(facade.signage, ())

    def test_a_letter_on_the_plane_and_one_off_it_are_told_apart(self):
        build = street_scene(sign_at=(2.0,), stray_at=((2048, 3900),))
        signage = [s for f in find_facades(build) for s in f.signage]
        self.assertEqual(len(signage), 1)
        self.assertLess(signage[0]["offset_from_plane_units"], FACADE_BAY)


class CorpusFacadeTests(unittest.TestCase):
    """The pilots. Skips cleanly without the corpus."""

    def test_e3m2_carries_the_two_signs_the_rendered_frame_shows(self):
        from bloodmap.format import read_map
        from bloodmap.lettering import letter_from
        from bloodmap.reachability import sector_kinds

        path = corpus_map("E3M2.MAP")
        if not path.exists():
            self.skipTest("E3M2.MAP is not present in the local corpus")
        disk = read_map(path)
        facades = [f for f in find_facades(disk.to_build_ir(), disk=disk,
                                           sector_kinds=sector_kinds(disk))
                   if f.signage]
        self.assertEqual(len(facades), 2, "FEINMAN MEATS and LOADING")
        by_host = {f.host: f for f in facades}
        self.assertIn(179, by_host)
        self.assertIn(301, by_host)
        word = "".join(sorted(
            letter_from(s["picnum"]) or "?" for s in by_host[179].signage))
        self.assertEqual(word, "".join(sorted("LOADING")))
        for facade in facades:
            for sign in facade.signage:
                self.assertTrue(sign["wall_aligned"])

    def test_e6m3_is_the_campaigns_most_disciplined_street(self):
        """Not by rhythm -- E6M3 has no repeating run at all. By the bay grid:
        85% of its street openings are a whole number of bays wide, against
        31% campaign-wide.
        """
        from bloodmap.format import read_map
        from bloodmap.reachability import sector_kinds

        path = corpus_map("E6M3.MAP")
        if not path.exists():
            self.skipTest("E6M3.MAP is not present in the local corpus")
        disk = read_map(path)
        facades = find_facades(disk.to_build_ir(), disk=disk,
                               sector_kinds=sector_kinds(disk))
        whole = sum(f.bays["whole_bay_openings"] for f in facades)
        total = sum(f.bays["openings"] for f in facades)
        self.assertGreater(whole / total, 0.8)
        for facade in facades:
            self.assertGreaterEqual(facade.bays["run_bays"], FACADE_MIN_BAYS)
            self.assertTrue(facade.openings)


class EmittedFacadeReportTests(unittest.TestCase):
    """The emitted report has to say what the module measures, and has to stay
    small enough to live in the repository. Writing every candidate in full is
    32 MB, twenty times the largest report here.
    """

    def setUp(self):
        if not REPORT.exists():
            self.skipTest("the facade report has not been generated")
        self.doc = json.loads(REPORT.read_text(encoding="utf-8"))
        self.camp = self.doc["summary"]["blood-campaign"]

    def test_material_continuity_is_the_strongest_coherence_signal(self):
        """The headline: one material by a long way, then a header line and a
        sill line together, and the bay grid nowhere near the top.

        Header and sill are within two points of each other on 131 runs, so
        this deliberately does not rank them against one another.
        """
        co = self.camp["multi_opening_coherence"]
        multi = self.camp["multi_opening"]
        self.assertGreater(co["one_wall_tile"] / multi, 0.9)
        self.assertGreater(co["shared_header_datum"] / multi, 0.7)
        self.assertGreater(co["shared_sill_datum"] / multi, 0.7)
        for datum in ("shared_header_datum", "shared_sill_datum"):
            self.assertGreater(co["one_wall_tile"] - co[datum], 0.1 * multi)
        self.assertGreater(min(co["shared_header_datum"], co["shared_sill_datum"]),
                           co["whole_bay_openings"] / co["openings"] * multi)

    def test_the_bay_grid_is_not_claimed_as_a_rule(self):
        """A rule demanding whole-bay openings would reject two thirds of the
        campaign's own multi-opening facades."""
        co = self.camp["multi_opening_coherence"]
        self.assertLess(co["whole_bay_openings"] / co["openings"], 0.5)

    def test_curated_is_kept_separate(self):
        self.assertEqual(self.doc["populations"]["community-curated"],
                         "precedent, never convention")
        self.assertIn("community-curated", self.doc["summary"])

    def test_every_campaign_candidate_is_written_out_at_least_compactly(self):
        """The aggregates have to be recomputable from the file itself."""
        rows = self.doc["campaign_candidates"]
        self.assertEqual(len(rows), self.camp["candidates"])
        self.assertEqual(
            sum(1 for r in rows if r["openings"] >= 2), self.camp["multi_opening"])
        self.assertEqual(Counter(r["rhythm"] for r in rows), self.camp["rhythm"])

    def test_a_full_record_is_kept_for_every_claim_the_report_makes(self):
        full = self.doc["facades"]
        campaign_multi = [r for r in full if r["population"] == "blood-campaign"
                          and r["bays"]["openings"] >= 2]
        self.assertEqual(len(campaign_multi), self.camp["multi_opening"])
        signed = [r for r in full if r["signage"]]
        self.assertEqual(
            len(signed),
            sum(self.doc["summary"][p]["signed"] for p in self.doc["summary"]))

    def test_signage_is_recorded_with_its_placement(self):
        for facade in [r for r in self.doc["facades"] if r["signage"]]:
            for sign in facade["signage"]:
                self.assertIn("along_run_bays", sign)
                self.assertIn("height_above_street_player_heights", sign)
                self.assertIn("offset_from_plane_units", sign)

    def test_no_candidate_claims_a_cornice(self):
        self.assertIn("sky", self.doc["notes"]["cornice"])
        for facade in self.doc["facades"]:
            self.assertIsNone(facade["datums"]["cornice"])

    def test_the_report_stays_within_the_size_of_its_neighbours(self):
        largest_neighbour = max(
            path.stat().st_size for path in REPORT.parent.glob("*.json")
            if path != REPORT)
        self.assertLess(REPORT.stat().st_size, 2 * largest_neighbour)


if __name__ == "__main__":
    unittest.main()
