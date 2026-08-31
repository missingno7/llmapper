"""Static assemblies, the clearance they claim, and the scatter detector.

The synthetic scenes here are **validation only and never evidence**: they
exist so the authored-vs-scattered question has a case where the answer is
known by construction. Every number that describes Blood comes from
`reports/blood-assembly-counters.md`.
"""

from __future__ import annotations

import copy
import json
import unittest
from pathlib import Path

from bloodmap.anchors import (
    COUNTER_MIN_ASPECT,
    REJECTED_ZONE_NAMINGS,
    region_candidates,
    STEP_LIMIT,
    WAIST_RISE,
    compare_placements,
    find_bundles,
    scatter_verdict,
)
from bloodmap.format import SECTOR_FIELDS, WALL_FIELDS, encode_map, parse_map
from bloodmap.model import DiskObject
from bloodmap.player_space import (
    ACCESS_FRONT_MIN_PLAYER_WIDTHS,
    Clearance,
    bundle_clearance,
    check_clearance,
)
from tests.helpers import corpus_map, synthetic_two_sector_map


ROOT = Path(__file__).resolve().parents[1]
REPORT = ROOT / "reports" / "blood-assembly-counters.json"
REGIONS = ROOT / "reports" / "blood-assembly-regions.json"

#: A room with an island in it. The island's plan sits inside the host's, the
#: two are portal-linked all the way round, and the island's floor is raised
#: 6144 units -- E6M1's cashwrap rise, in the middle of the measured waist band.
HOST_LOOP = [(0, 0), (8192, 0), (8192, 8192), (0, 8192)]
HOLE_LOOP = [(2048, 3072), (2048, 4096), (6144, 4096), (6144, 3072)]
ISLAND_LOOP = [(2048, 3072), (6144, 3072), (6144, 4096), (2048, 4096)]
HOST_FLOOR = 8192
ISLAND_RISE = 6144


def counter_scene(*, props_on_the_island: bool = True):
    """A host room, a raised island, and three props placed one of two ways.

    `props_on_the_island=False` moves the *same three props* onto the host
    floor without touching anything else -- same count, same room, same
    sprites. That is the comparison Phase 5 exists to make.
    """
    disk = synthetic_two_sector_map()
    walls = []
    for loop in (HOST_LOOP, HOLE_LOOP, ISLAND_LOOP):
        first = len(walls)
        for offset, (x, y) in enumerate(loop):
            fields = {name: 0 for name, _codec in WALL_FIELDS}
            fields.update(x=x, y=y, point2=first + (offset + 1) % len(loop),
                          next_wall=-1, next_sector=-1, picnum=1,
                          over_picnum=-1, extra=-1)
            walls.append(DiskObject(fields))
    # The hole and the island are the same four edges from opposite sides.
    for hole_wall, island_wall in ((4, 11), (5, 10), (6, 9), (7, 8)):
        walls[hole_wall].fields.update(next_wall=island_wall, next_sector=1)
        walls[island_wall].fields.update(next_wall=hole_wall, next_sector=0)

    sectors = []
    for wall_ptr, wall_count, floor_z in ((0, 8, HOST_FLOOR),
                                          (8, 4, HOST_FLOOR - ISLAND_RISE)):
        fields = {name: 0 for name, _codec in SECTOR_FIELDS}
        fields.update(wall_ptr=wall_ptr, wall_count=wall_count, floor_z=floor_z,
                      ceiling_z=-40000, extra=-1)
        sectors.append(DiskObject(fields))

    template = copy.deepcopy(disk.sprites[0])
    sprites = []
    for index, x in enumerate((2560, 4096, 5632)):
        sprite = copy.deepcopy(template)
        if props_on_the_island:
            sector, y, z = 1, 3584, HOST_FLOOR - ISLAND_RISE
        else:
            sector, y, z = 0, 1024 + index * 2048, HOST_FLOOR
        sprite.fields.update(x=x, y=y, z=z, sector=sector, picnum=700 + index,
                             type=0, cstat=0, angle=0, index=index,
                             extra=-1, owner=-1)
        sprite.extra = None
        sprites.append(sprite)

    disk.sectors, disk.walls, disk.sprites = sectors, walls, sprites
    disk.header.update(num_sectors=2, num_walls=len(walls), num_sprites=len(sprites),
                       start_sector=0, start_x=512, start_y=512)
    return parse_map(encode_map(disk)).to_build_ir()


class BundleGroupingTests(unittest.TestCase):
    def setUp(self):
        self.build = counter_scene()
        self.bundles = find_bundles(self.build)

    def test_the_island_and_its_props_are_one_bundle(self):
        self.assertEqual(len(self.bundles), 1)
        bundle = self.bundles[0]
        self.assertEqual(bundle.core, 1)
        self.assertEqual(bundle.host, 0)
        self.assertEqual(len(bundle.props), 3)
        self.assertEqual(bundle.kind, "raised-island")
        self.assertTrue(bundle.basis)

    def test_the_measures_are_frame_independent_ratios(self):
        measures = self.bundles[0].measures
        self.assertEqual(measures["rise_units"], ISLAND_RISE)
        self.assertEqual(measures["aspect"], 4.0)
        self.assertEqual(measures["visible_props"], 3)
        for key in measures:
            self.assertNotIn(key, ("x", "y", "z", "bounds"))

    def test_a_kerb_is_not_a_bundle(self):
        """Raised by less than a step: the host floor and the top are one
        surface a player walks over, not two. Checked with the waist band
        relaxed, so it is the step limit doing the work and not the band."""
        build = counter_scene()
        build.sectors[1]["fields"]["floor_z"] = HOST_FLOOR - (STEP_LIMIT - 1)
        self.assertEqual(find_bundles(build), [])
        self.assertEqual(
            find_bundles(build, waist_only=False, require_elongated=False,
                         require_carried=False), [],
            "a floor within one step of its host is not a raised island at all")

    def test_a_wall_stub_is_not_a_counter(self):
        """Above the waist band it is architecture, not furniture. The default
        filters say so; relaxing them shows it is still a raised island."""
        build = counter_scene()
        build.sectors[1]["fields"]["floor_z"] = HOST_FLOOR - (WAIST_RISE[1] + 4096)
        self.assertEqual(find_bundles(build), [])
        self.assertEqual(len(find_bundles(build, waist_only=False)), 1)

    def test_a_square_island_is_not_a_counter(self):
        build = counter_scene()
        for wall_id, (x, y) in zip(range(8, 12), (
                (2048, 0), (6144, 0), (6144, 4096), (2048, 4096))):
            build.walls[wall_id]["fields"].update(x=x, y=y)
        for wall_id, (x, y) in zip(range(4, 8), (
                (2048, 0), (2048, 4096), (6144, 4096), (6144, 0))):
            build.walls[wall_id]["fields"].update(x=x, y=y)
        found = find_bundles(build)
        self.assertEqual(found, [], "aspect 1.0 is a pillar or a crate")
        self.assertEqual(len(find_bundles(build, require_elongated=False)), 1)

    def test_a_bare_island_carries_nothing_and_is_not_a_bundle(self):
        """Proximity alone is insufficient (`04_...md`): without a cap or a
        prop this is a plinth."""
        build = counter_scene()
        build.sprites = []
        build.header = dict(getattr(build, "header", {}) or {})
        self.assertEqual(find_bundles(build), [])
        self.assertEqual(len(find_bundles(build, require_carried=False)), 1)

    def test_wiring_does_not_count_as_a_prop(self):
        """A sound marker on a plinth does not make it a counter."""
        build = counter_scene()
        for sprite in build.sprites:
            sprite["fields"].update(lotag=709, cstat=32896)
        self.assertEqual(find_bundles(build), [])

    def test_off_map_geometry_is_not_mined(self):
        build = counter_scene()
        self.assertEqual(find_bundles(build, sector_kinds={0: "reachable",
                                                          1: "logic_closet"}), [])


class ClearanceTests(unittest.TestCase):
    def setUp(self):
        self.build = counter_scene()
        bundle = find_bundles(self.build)[0]
        self.clearance = bundle_clearance(self.build, bundle.core, bundle.host)

    def test_the_clearance_is_a_claim_not_geometry(self):
        self.assertFalse(self.clearance.hard)
        self.assertEqual(self.clearance.role, "access_front")
        self.assertEqual(self.clearance.owner, "sector:1")
        self.assertIn("bounding-box", self.clearance.basis)

    def test_the_sides_are_sorted_so_the_claim_carries_no_bearing(self):
        sides = self.clearance.sides_player_widths
        self.assertEqual(list(sides), sorted(sides))
        self.assertEqual(self.clearance.access_front, max(sides))

    def test_it_survives_a_quarter_turn(self):
        turned = counter_scene()
        turned.rotate_quarter_turns(1)
        turned.translate(4096, -8192)
        bundle = find_bundles(turned)[0]
        self.assertEqual(
            bundle_clearance(turned, bundle.core, bundle.host).sides_player_widths,
            self.clearance.sides_player_widths)

    def test_a_wide_access_front_passes(self):
        found = check_clearance(self.clearance)
        self.assertTrue(found["passes"])
        self.assertEqual(found["violations"], [])

    def test_a_pinched_access_front_is_reported(self):
        pinched = Clearance(id="x", owner="sector:1", role="access_front",
                            hard=False, sides_player_widths=(0.0, 0.0, 0.1, 0.2))
        found = check_clearance(pinched)
        self.assertFalse(found["passes"])
        self.assertEqual(found["violations"][0]["code"], "access-front-too-narrow")

    def test_the_check_is_not_a_clearance_all_round_rule(self):
        """Asserting free floor on every side rejects 77% of the campaign's own
        counters. The check must pass a counter that backs onto a wall."""
        backed = Clearance(id="x", owner="sector:1", role="access_front",
                           hard=False, sides_player_widths=(0.0, 0.0, 0.0, 9.5))
        self.assertTrue(backed.backs_onto_something)
        self.assertTrue(backed.asymmetric)
        self.assertTrue(check_clearance(backed)["passes"])


class ScatterDetectorTests(unittest.TestCase):
    """The exit criterion: the same props, placed two ways."""

    def setUp(self):
        self.authored = counter_scene(props_on_the_island=True)
        self.scattered = counter_scene(props_on_the_island=False)

    def test_the_two_scenes_hold_the_same_props(self):
        self.assertEqual(len(self.authored.sprites), len(self.scattered.sprites))
        self.assertEqual(
            sorted(int(s["fields"]["picnum"]) for s in self.authored.sprites),
            sorted(int(s["fields"]["picnum"]) for s in self.scattered.sprites))

    def test_the_authored_scene_has_its_props_on_the_support(self):
        found = scatter_verdict(self.authored, 0)
        self.assertEqual(found["verdict"], "props_on_supports")
        self.assertEqual(found["support_share"], 1.0)

    def test_the_scattered_scene_has_none_on_it(self):
        found = scatter_verdict(self.scattered, 0)
        self.assertEqual(found["verdict"], "props_off_supports")
        self.assertEqual(found["support_share"], 0.0)
        self.assertEqual(found["supports_available"], 1)

    def test_the_comparison_names_the_authored_one(self):
        found = compare_placements(self.authored, self.scattered, 0)
        self.assertTrue(found["same_prop_count"])
        self.assertEqual(found["verdict"], "the first is authored")
        self.assertGreater(found["support_share_gap"], 0)

    def test_the_comparison_is_not_fooled_by_the_order(self):
        found = compare_placements(self.scattered, self.authored, 0)
        self.assertEqual(found["verdict"], "the second is authored")

    def test_prop_count_cannot_be_carrying_the_answer(self):
        """Doubling the scattered props leaves it scattered."""
        crowded = counter_scene(props_on_the_island=False)
        extra = copy.deepcopy(crowded.sprites[0])
        crowded.sprites = list(crowded.sprites) + [extra, copy.deepcopy(extra)]
        self.assertEqual(scatter_verdict(crowded, 0)["verdict"], "props_off_supports")

    def test_a_room_with_no_support_says_so_rather_than_guessing(self):
        flat = counter_scene(props_on_the_island=False)
        flat.sectors[1]["fields"]["floor_z"] = HOST_FLOOR
        found = scatter_verdict(flat, 0)
        self.assertEqual(found["supports_available"], 0)
        self.assertEqual(found["verdict"], "mixed")
        self.assertTrue(found["limitations"])


class FunctionalRegionTests(unittest.TestCase):
    """Phase 6: a room explained as several zones, and nothing named."""

    def setUp(self):
        self.build = counter_scene()
        self.found = region_candidates(self.build, [0, 1])

    def test_the_counter_and_its_host_are_two_zones(self):
        self.assertEqual(self.found["zone_count"], 2)
        by_sector = {tuple(z["sectors"]): z for z in self.found["zones"]}
        self.assertIn((0,), by_sector)
        self.assertIn((1,), by_sector)

    def test_the_zone_carries_the_evidence_that_made_it(self):
        for zone in self.found["zones"]:
            self.assertIn("floor_z", zone)
            self.assertIn("floor_picnum", zone)
            self.assertIn("floor plane", zone["basis"])

    def test_the_hierarchy_reaches_the_bundle_and_its_parts(self):
        host_zone = next(z for z in self.found["zones"] if z["sectors"] == [0])
        self.assertEqual(len(host_zone["hosts_bundles"]), 1)
        bundle = host_zone["hosts_bundles"][0]
        self.assertEqual(bundle["core"], "sector:1")
        self.assertEqual(len(bundle["props"]), 3)
        core_zone = next(z for z in self.found["zones"] if z["sectors"] == [1])
        self.assertEqual(len(core_zone["is_a_bundle_core"]), 1)

    def test_a_counter_at_its_host_s_height_and_tile_is_not_a_separate_zone(self):
        """The 100% figure in the report is not a tautology: give the core its
        host's plane and tile and the partition merges them."""
        build = counter_scene()
        build.sectors[1]["fields"]["floor_z"] = HOST_FLOOR
        for sector in build.sectors:
            sector["fields"]["floor_picnum"] = 290
        self.assertEqual(region_candidates(build, [0, 1])["zone_count"], 1)

    def test_same_plane_and_tile_but_unconnected_stays_two_zones(self):
        """A shop floor and a corridor floor cut from the same slab are two
        places, so connectivity is part of the rule."""
        build = counter_scene()
        for sector in build.sectors:
            sector["fields"].update(floor_z=HOST_FLOOR, floor_picnum=290)
        for wall_id in (4, 5, 6, 7, 8, 9, 10, 11):
            build.walls[wall_id]["fields"].update(next_wall=-1, next_sector=-1)
        self.assertEqual(region_candidates(build, [0, 1])["zone_count"], 2)

    def test_the_zones_are_not_named(self):
        """`04_...md` offers customer_front and employee_workspace. Two ways of
        naming the sides were measured against the campaign and both failed, so
        the view carries the rejections instead of the names."""
        for zone in self.found["zones"]:
            self.assertNotIn("name", zone)
            self.assertNotIn("role", zone)
        self.assertEqual(len(self.found["rejected_namings"]), 2)
        for item in self.found["rejected_namings"]:
            self.assertIn("rejected", item["verdict"])
            self.assertTrue(item["measured"])

    def test_the_rejected_namings_keep_their_numbers(self):
        joined = " ".join(item["measured"] for item in REJECTED_ZONE_NAMINGS)
        self.assertIn("84.1%", joined)
        self.assertIn("+0.024", joined)
        self.assertIn("-0.080", joined)

    def test_an_out_of_range_sector_fails_closed(self):
        from bloodmap.spatial import SpatialAnalysisError

        with self.assertRaises(SpatialAnalysisError):
            region_candidates(self.build, [0, 99])


class CorpusBundleTests(unittest.TestCase):
    """The owner-identified counter, and the mined population."""

    def setUp(self):
        self.path = corpus_map("E6M1.MAP")
        if not self.path.exists():
            self.skipTest("E6M1.MAP is not present in the local corpus")

    def test_the_e6m1_cashwrap_is_found_with_both_register_caps(self):
        """`projects/blood-city/references/e6m1-shop.md`: S32 is the counter,
        S33/S34 the two register caps. The rule is told none of that."""
        from bloodmap.format import read_map
        from bloodmap.reachability import sector_kinds

        disk = read_map(self.path)
        build = disk.to_build_ir()
        found = [b for b in find_bundles(build, sector_kinds=sector_kinds(disk))
                 if b.core == 32]
        self.assertEqual(len(found), 1)
        self.assertEqual(set(found[0].caps), {33, 34})
        self.assertEqual(found[0].host, 61)
        self.assertEqual(found[0].measures["rise_units"], 6144)

    def test_the_shop_floor_is_not_called_scattered(self):
        """E6M1's selling floor carries sixteen props on the floor and three on
        the counter, every one deliberate. A detector that called that
        `scattered` would be wrong about hand-authored source material."""
        from bloodmap.format import read_map
        from bloodmap.reachability import sector_kinds

        disk = read_map(self.path)
        found = scatter_verdict(disk.to_build_ir(), 61,
                                sector_kinds=sector_kinds(disk))
        self.assertNotEqual(found["verdict"], "props_off_supports")


class EmittedRegionReportTests(unittest.TestCase):
    def setUp(self):
        if not REGIONS.exists():
            self.skipTest("the region survey has not been generated")
        self.doc = json.loads(REGIONS.read_text(encoding="utf-8"))
        self.camp = [r for r in self.doc["surveys"]
                     if r["population"] == "blood-campaign"]

    def test_every_counter_complex_holds_more_than_one_zone(self):
        self.assertTrue(self.camp)
        self.assertTrue(all(r["zones"] >= 2 for r in self.camp))

    def test_every_counter_sits_in_its_own_zone_not_its_host_s(self):
        self.assertTrue(all(r["core_zone_differs_from_host"] for r in self.camp))

    def test_curated_is_kept_separate(self):
        self.assertEqual(self.doc["populations"]["community-curated"],
                         "precedent, never convention")


class EmittedReportTests(unittest.TestCase):
    def setUp(self):
        if not REPORT.exists():
            self.skipTest("the assembly report has not been generated")
        self.doc = json.loads(REPORT.read_text(encoding="utf-8"))

    def test_every_campaign_bundle_passes_the_access_front_check(self):
        camp = [r for r in self.doc["bundles"] if r["population"] == "blood-campaign"]
        self.assertGreater(len(camp), 100)
        self.assertTrue(all(r["check"]["passes"] for r in camp),
                        "the floor is the campaign minimum, so nothing may fail it")

    def test_the_report_records_that_most_counters_back_onto_something(self):
        camp = [r for r in self.doc["bundles"] if r["population"] == "blood-campaign"]
        backed = sum(1 for r in camp if r["clearance"]["backs_onto_something"])
        self.assertGreater(backed / len(camp), 0.5,
                           "a clearance-all-round rule would reject the majority")

    def test_curated_is_kept_separate_from_campaign(self):
        populations = {r["population"] for r in self.doc["bundles"]}
        self.assertEqual(populations, {"blood-campaign", "community-curated"})
        self.assertEqual(self.doc["populations"]["community-curated"],
                         "precedent, never convention")


if __name__ == "__main__":
    unittest.main()
