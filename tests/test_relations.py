"""Object-scale relation extraction regressions.

The load-bearing claim is frame independence: the same neighborhood of a
translated or quarter-turn-rotated map must produce an identical document. It
is pinned twice -- on a synthetic map that always runs, and on real campaign
maps when the corpus is present.
"""

from __future__ import annotations

import copy
import unittest

from bloodmap.build_ir import BuildIR
from bloodmap.format import encode_map, parse_map
from bloodmap.patterns import list_corpus_maps
from bloodmap.relations import (
    FORBIDDEN_MEASURE_KEYS,
    context_signature,
    excluded_dense_seeds,
    sprite_kind,
    RELATION_KINDS,
    RelationError,
    extract_relations,
    mine_relations,
    neighborhood,
    sprite_dense_seeds,
)
from tests.helpers import corpus_map, synthetic_two_sector_map


def furnished_map():
    """Two portal-linked sectors carrying a deliberate object arrangement.

    sector 0 holds three identical sprites in an evenly spaced row on the
    floor, mid-room and clear of every wall, plus one sprite pressed against
    the south wall and square to it; sector 1 holds one sprite floating clear
    of every surface. The room is 1024 units -- 2.67 player widths -- across,
    so "mid-room" has to be deliberate: at x=200 a sprite is already 0.52
    player widths off the side wall, inside the against_wall band.
    """
    disk = synthetic_two_sector_map()
    template = copy.deepcopy(disk.sprites[0])
    floor_z = int(disk.sectors[0].fields["floor_z"])
    sprites = []
    # An evenly spaced row of three, resting exactly on the floor plane.
    for index, x in enumerate((400, 512, 624)):
        sprite = copy.deepcopy(template)
        sprite.fields.update(x=x, y=512, z=floor_z, sector=0, picnum=700,
                             type=0, cstat=0, angle=0, index=index, extra=-1,
                             owner=-1)
        sprite.extra = None
        sprites.append(sprite)
    # Against the south wall (0,0)-(1024,0), square to its inward normal.
    flush = copy.deepcopy(template)
    flush.fields.update(x=512, y=20, z=floor_z, sector=0, picnum=701,
                        type=0, cstat=0, angle=512, index=3, extra=-1, owner=-1)
    flush.extra = None
    sprites.append(flush)
    # Clear of floor, ceiling and every wall.
    free = copy.deepcopy(template)
    free.fields.update(x=1536, y=512, z=0, sector=1, picnum=702,
                       type=0, cstat=0, angle=0, index=4, extra=-1, owner=-1)
    free.extra = None
    sprites.append(free)

    disk.sprites = sprites
    disk.header["num_sprites"] = len(sprites)
    return parse_map(encode_map(disk)).to_build_ir()


def stacked_map():
    """A small raised volume sitting over the middle of a bigger room.

    Sector 1's four walls are moved inside sector 0's plan and lifted above
    its ceiling, and the portal between them is unlinked -- the shape a loft,
    a shelf volume or a room-over-room upper leaf has. Blood z grows downward,
    so "above" is the smaller z.
    """
    disk = synthetic_two_sector_map()
    disk.walls[1].fields.update(next_wall=-1, next_sector=-1)
    disk.walls[7].fields.update(next_wall=-1, next_sector=-1)
    for wall_id, (x, y) in zip(range(4, 8), ((384, 384), (640, 384), (640, 640), (384, 640))):
        disk.walls[wall_id].fields.update(x=x, y=y)
    ceiling_0 = int(disk.sectors[0].fields["ceiling_z"])
    disk.sectors[1].fields.update(floor_z=ceiling_0 - 4096, ceiling_z=ceiling_0 - 4096 - 16384)
    disk.sprites = [disk.sprites[0]]
    disk.sprites[0].fields.update(x=512, y=512, z=int(disk.sectors[0].fields["floor_z"]),
                                  sector=0, picnum=700, type=0, cstat=0,
                                  extra=-1, owner=-1)
    disk.sprites[0].extra = None
    disk.header["num_sprites"] = 1
    return parse_map(encode_map(disk)).to_build_ir()


def notched_map():
    """An L-shaped room, one small sector genuinely inside it and one in the notch.

    Both small sectors have plan bounding boxes contained by the L's bounding
    box, so a bbox-only containment test calls both of them `inside`. Only one
    of them is. This is the fixture that separates `inside` from `bbox`.
    """
    from bloodmap.format import SECTOR_FIELDS, WALL_FIELDS
    from bloodmap.model import DiskObject

    disk = synthetic_two_sector_map()
    loops = [
        # The L: the quadrant x>1024, y<1024 is cut away.
        [(0, 0), (1024, 0), (1024, 1024), (2048, 1024), (2048, 2048), (0, 2048)],
        [(256, 1280), (768, 1280), (768, 1792), (256, 1792)],      # inside the L
        [(1280, 256), (1792, 256), (1792, 768), (1280, 768)],      # in the notch
    ]
    walls, sectors, first = [], [], 0
    for index, loop in enumerate(loops):
        for offset, (x, y) in enumerate(loop):
            fields = {name: 0 for name, _codec in WALL_FIELDS}
            fields.update(x=x, y=y, point2=first + (offset + 1) % len(loop),
                          next_wall=-1, next_sector=-1, picnum=1, over_picnum=-1, extra=-1)
            walls.append(DiskObject(fields))
        sector = {name: 0 for name, _codec in SECTOR_FIELDS}
        sector.update(wall_ptr=first, wall_count=len(loop), ceiling_z=-8192,
                      floor_z=8192, extra=-1)
        sectors.append(DiskObject(sector))
        first += len(loop)

    disk.sectors, disk.walls = sectors, walls
    disk.sprites = [disk.sprites[0]]
    disk.sprites[0].fields.update(x=512, y=512, z=8192, sector=0, picnum=700,
                                  type=0, cstat=0, extra=-1, owner=-1)
    disk.sprites[0].extra = None
    disk.header.update(num_sectors=len(sectors), num_walls=len(walls), num_sprites=1,
                       start_sector=0, start_x=512, start_y=512)
    return parse_map(encode_map(disk)).to_build_ir()


def wired_map():
    """A room with two visible objects, and a sealed closet full of wiring.

    Sector 1 is unreachable from sector 0 -- the portal is unlinked -- and
    holds nothing but sound markers. It is the shape of the defect: by raw
    sprite count it is the denser sector, and a furniture survey that ranks on
    that puts a switch closet at the top.
    """
    disk = synthetic_two_sector_map()
    disk.walls[1].fields.update(next_wall=-1, next_sector=-1)
    disk.walls[7].fields.update(next_wall=-1, next_sector=-1)
    template = copy.deepcopy(disk.sprites[0])
    floor_z = int(disk.sectors[0].fields["floor_z"])
    sprites = []
    for index, x in enumerate((400, 624)):                 # visible decorations
        sprite = copy.deepcopy(template)
        sprite.fields.update(x=x, y=512, z=floor_z, sector=0, picnum=700,
                             type=0, cstat=0, index=index, extra=-1, owner=-1)
        sprite.extra = None
        sprites.append(sprite)
    for index in range(4):                                 # kSoundSector markers
        sprite = copy.deepcopy(template)
        sprite.fields.update(x=1400 + 64 * index, y=512, z=floor_z, sector=1,
                             picnum=2520, type=709, cstat=32896,
                             index=2 + index, extra=-1, owner=-1)
        sprite.extra = None
        sprites.append(sprite)
    disk.sprites = sprites
    disk.header["num_sprites"] = len(sprites)
    return parse_map(encode_map(disk)).to_build_ir()


def _relations(document, kind):
    return [item for item in document["relations"] if item["kind"] == kind]


class VisibilityAndReachabilityTests(unittest.TestCase):
    """Wiring is labelled, never dropped, and never counted as furniture."""

    def setUp(self):
        self.build = wired_map()

    def test_a_sound_marker_is_wiring_and_a_decoration_is_visible(self):
        self.assertEqual(sprite_kind(self.build, 0), "visible")
        self.assertEqual(sprite_kind(self.build, 2), "wiring")

    def test_visibility_is_only_claimed_for_blood(self):
        """BuildIR keeps Blood's sprite type in the shared `lotag` slot, which
        means something else on Duke."""
        self.assertEqual(sprite_kind(self.build, 2, game="duke3d"), "unknown")

    def test_every_in_sector_relation_carries_the_label(self):
        document = extract_relations(self.build, sectors=[0, 1], hops=0)
        placed = _relations(document, "in_sector")
        self.assertEqual(len(placed), 6, "wiring stays in the dump")
        kinds = {item["subject"]: item["measures"]["visibility"] for item in placed}
        self.assertEqual(kinds["sprite:0"], "visible")
        self.assertEqual(kinds["sprite:2"], "wiring")
        self.assertEqual(document["object_visibility"], {"visible": 2, "wiring": 4})

    def test_the_signature_counts_visible_objects_only(self):
        document = extract_relations(self.build, sectors=[1], hops=0)
        visible = context_signature(document, 1)
        self.assertIn("objects:0", visible)
        wiring = context_signature(document, 1, visible_only=False)
        self.assertIn("objects:3+", wiring)

    def test_a_run_of_sound_markers_is_tagged_as_wiring(self):
        document = extract_relations(self.build, sectors=[1], hops=0)
        runs = _relations(document, "repeats_along")
        self.assertEqual(len(runs), 1)
        self.assertEqual(runs[0]["measures"]["visibility"], "wiring")

    def test_the_denser_sector_is_not_seeded_on(self):
        """Sector 1 has four sprites to sector 0's two, and is still not a
        place a furniture survey should point at."""
        raw = sprite_dense_seeds(self.build, limit=1, visible_only=False,
                                 reachable_only=False)
        self.assertEqual(raw, [1])
        self.assertEqual(sprite_dense_seeds(self.build, limit=1), [0])

    def test_an_offmap_sector_is_not_seeded_on_and_is_reported(self):
        kinds = {0: "reachable", 1: "logic_closet"}
        self.assertEqual(
            sprite_dense_seeds(self.build, limit=2, sector_kinds=kinds,
                               visible_only=False), [0])
        held = excluded_dense_seeds(self.build, limit=2, sector_kinds=kinds)
        self.assertEqual([row["sector"] for row in held], [1])
        self.assertEqual(held[0]["sector_kind"], "logic_closet")
        self.assertIn("off-map: logic_closet", held[0]["reasons"])
        self.assertIn("4 of 4 sprites are wiring", held[0]["reasons"])

    def test_sector_kinds_are_recorded_on_the_document(self):
        kinds = {0: "reachable", 1: "logic_closet"}
        document = extract_relations(self.build, sectors=[0, 1], hops=0,
                                     sector_kinds=kinds)
        self.assertEqual(document["sector_kinds"], {"0": "reachable", "1": "logic_closet"})
        self.assertEqual(document["seed_sector_kinds"], ["logic_closet", "reachable"])

    def test_an_absent_reachability_map_labels_unknown_rather_than_reachable(self):
        document = extract_relations(self.build, sectors=[0], hops=0)
        self.assertEqual(document["sector_kinds"], {"0": "unknown"})


class NeighborhoodTests(unittest.TestCase):
    def test_hops_expand_through_portals(self):
        build = furnished_map()
        near = neighborhood(build, sectors=[0], hops=0)
        self.assertEqual(near.sectors, (0,))
        self.assertEqual(len(near.sprites), 4)
        wider = neighborhood(build, sectors=[0], hops=1)
        self.assertEqual(wider.sectors, (0, 1))
        self.assertEqual(len(wider.sprites), 5)

    def test_a_sprite_seed_resolves_to_its_sector(self):
        build = furnished_map()
        self.assertEqual(neighborhood(build, sprites=[4], hops=0).sectors, (1,))

    def test_an_empty_or_invalid_seed_fails_closed(self):
        build = furnished_map()
        with self.assertRaises(RelationError):
            neighborhood(build, hops=1)
        with self.assertRaises(RelationError):
            neighborhood(build, sectors=[99], hops=0)
        with self.assertRaises(RelationError):
            neighborhood(build, sectors=[0], hops=-1)


class RelationKindTests(unittest.TestCase):
    def setUp(self):
        self.build = furnished_map()
        self.document = extract_relations(self.build, sectors=[0], hops=1)

    def test_every_sprite_is_placed_in_its_sector(self):
        placed = {item["subject"]: item["object"] for item in _relations(self.document, "in_sector")}
        self.assertEqual(len(placed), 5)
        self.assertEqual(placed["sprite:4"], "sector:1")

    def test_the_row_of_three_is_found_as_one_even_run(self):
        runs = _relations(self.document, "repeats_along")
        self.assertEqual(len(runs), 1, runs)
        run = runs[0]
        self.assertEqual(run["members"], ["sprite:0", "sprite:1", "sprite:2"])
        self.assertEqual(run["measures"]["count"], 3)
        self.assertEqual(run["measures"]["picnum"], 700)
        self.assertEqual(run["measures"]["axis"], "plan")
        self.assertEqual(run["measures"]["spacing_variation"], 0.0)

    def test_an_uneven_row_is_not_a_run(self):
        build = furnished_map()
        build.sprites[2]["fields"]["x"] = 800          # 400, 512, 800: uneven
        document = extract_relations(build, sectors=[0], hops=1)
        self.assertEqual(_relations(document, "repeats_along"), [])

    def test_the_flush_sprite_is_against_the_wall_it_faces(self):
        against = {item["subject"]: item for item in _relations(self.document, "against_wall")}
        # Only the flush sprite. The row is mid-room, over one player width
        # off every wall -- if this set grows, the distance threshold has
        # stopped meaning something.
        self.assertEqual(set(against), {"sprite:3"})
        self.assertLess(against["sprite:3"]["measures"]["distance_player_widths"], 0.1)
        faces = {item["subject"]: item for item in _relations(self.document, "faces_wall")}
        self.assertIn("sprite:3", faces)
        self.assertEqual(faces["sprite:3"]["measures"]["angle_from_inward_normal"], 0)
        self.assertEqual(faces["sprite:3"]["object"], against["sprite:3"]["object"])

    def test_the_free_sprite_rests_on_nothing_and_faces_nothing(self):
        self.assertNotIn("sprite:4", {item["subject"] for item in _relations(self.document, "rests_on")})
        self.assertNotIn("sprite:4", {item["subject"] for item in _relations(self.document, "faces_wall")})

    def test_floor_sprites_rest_on_the_floor_plane(self):
        rests = {item["subject"]: item["measures"] for item in _relations(self.document, "rests_on")}
        for ref in ("sprite:0", "sprite:1", "sprite:2", "sprite:3"):
            self.assertEqual(rests[ref]["surface"], "floor")
            self.assertEqual(rests[ref]["clearance_player_heights"], 0.0)

    def test_the_two_sectors_are_adjacent_and_share_their_planes(self):
        adjacent = _relations(self.document, "adjacent_to")
        self.assertEqual(len(adjacent), 1)
        self.assertEqual((adjacent[0]["subject"], adjacent[0]["object"]), ("sector:0", "sector:1"))
        self.assertGreater(adjacent[0]["measures"]["width_player_widths"], 0)
        planes = {item["measures"]["surface"]: item["members"]
                  for item in _relations(self.document, "shares_plane")}
        self.assertEqual(planes["floor"], ["sector:0", "sector:1"])
        self.assertEqual(planes["ceiling"], ["sector:0", "sector:1"])

    def test_every_emitted_kind_is_declared_with_a_consumer(self):
        for item in self.document["relations"]:
            self.assertIn(item["kind"], RELATION_KINDS)
            self.assertTrue(item["basis"], item)

    def test_no_measure_carries_a_world_frame(self):
        for item in self.document["relations"]:
            self.assertFalse(set(item["measures"]) & FORBIDDEN_MEASURE_KEYS, item)


class StackedVolumeTests(unittest.TestCase):
    """`above` and `inside`, which a side-by-side pair cannot exercise."""

    def setUp(self):
        self.document = extract_relations(stacked_map(), sectors=[0, 1], hops=0)

    def test_the_raised_volume_is_above_the_room_and_not_the_other_way_round(self):
        above = [(item["subject"], item["object"]) for item in _relations(self.document, "above")]
        self.assertEqual(above, [("sector:1", "sector:0")])
        measures = _relations(self.document, "above")[0]["measures"]
        self.assertEqual(measures["plan_bbox_overlap_fraction"], 1.0)
        self.assertGreater(measures["gap_player_heights"], 0)

    def test_a_volume_lowered_below_the_room_is_not_above_it(self):
        build = stacked_map()
        floor_0 = int(build.sectors[0]["fields"]["floor_z"])
        build.sectors[1]["fields"].update(floor_z=floor_0 + 20480, ceiling_z=floor_0 + 4096)
        document = extract_relations(build, sectors=[0, 1], hops=0)
        above = [(item["subject"], item["object"]) for item in _relations(document, "above")]
        self.assertEqual(above, [("sector:0", "sector:1")])

    def test_the_smaller_volume_is_inside_the_bigger_one(self):
        inside = [(item["subject"], item["object"]) for item in _relations(self.document, "inside")]
        self.assertEqual(inside, [("sector:1", "sector:0")])
        self.assertLess(_relations(self.document, "inside")[0]["measures"]["area_fraction"], 0.1)

    def test_coincident_footprints_do_not_nest_inside_each_other(self):
        """A room-over-room stack has two sectors with the *same* footprint.
        Plan-bounds containment holds in both directions there, so without the
        area test `inside` would claim each contains the other."""
        build = stacked_map()
        for wall_id, (x, y) in zip(range(4, 8), ((0, 0), (1024, 0), (1024, 1024), (0, 1024))):
            build.walls[wall_id]["fields"].update(x=x, y=y)
        document = extract_relations(build, sectors=[0, 1], hops=0)
        self.assertEqual(_relations(document, "inside"), [])
        self.assertEqual(
            [(item["subject"], item["object"]) for item in _relations(document, "above")],
            [("sector:1", "sector:0")],
        )

    def test_a_bounding_box_inside_a_notch_is_not_inside_the_room(self):
        """Both small sectors' bounding boxes sit inside the L's bounding box.
        Only the one in the L's interior is `inside` it."""
        document = extract_relations(notched_map(), sectors=[0, 1, 2], hops=0)
        self.assertEqual(
            [(item["subject"], item["object"]) for item in _relations(document, "inside")],
            [("sector:1", "sector:0")],
        )

    def test_frame_independence_holds_for_the_stack_too(self):
        base = stacked_map()
        reference = extract_relations(base, sectors=[0, 1], hops=0)["relations"]
        for turns in (1, 2, 3):
            with self.subTest(turns=turns):
                moved = copy.deepcopy(base)
                moved.rotate_quarter_turns(turns)
                moved.translate(-6144, 10240)
                self.assertEqual(
                    extract_relations(moved, sectors=[0, 1], hops=0)["relations"], reference)


class FrameIndependenceTests(unittest.TestCase):
    """The claim the module exists to make, on a map that always exists."""

    TRANSFORMS = (
        ("translate", 8192, -4096, 0),
        ("quarter turn", 0, 0, 1),
        ("half turn", 0, 0, 2),
        ("three quarter turns", 0, 0, 3),
        ("half turn then translate", -20480, 12288, 2),
    )

    def _document(self, build: BuildIR):
        return extract_relations(build, sectors=[0], hops=1)

    def test_translation_and_quarter_turns_do_not_change_one_relation(self):
        base = furnished_map()
        reference = self._document(base)
        self.assertTrue(reference["relations"])
        for label, dx, dy, turns in self.TRANSFORMS:
            with self.subTest(transform=label):
                moved = copy.deepcopy(base)
                if turns:
                    moved.rotate_quarter_turns(turns)
                if dx or dy:
                    moved.translate(dx, dy)
                self.assertEqual(self._document(moved)["relations"], reference["relations"])

    def test_a_half_turn_does_not_reverse_a_repeating_run(self):
        """The first invariance run failed exactly here: member order was
        sorted by position, so a half turn read the row backwards."""
        base = furnished_map()
        forward = _relations(self._document(base), "repeats_along")[0]["members"]
        turned = copy.deepcopy(base)
        turned.rotate_quarter_turns(2)
        self.assertEqual(_relations(self._document(turned), "repeats_along")[0]["members"], forward)


class CorpusRelationTests(unittest.TestCase):
    """Real campaign geometry. Skips cleanly when the corpus is absent."""

    def setUp(self):
        self.path = corpus_map("E6M1.MAP")
        if not self.path.exists():
            self.skipTest("E6M1.MAP is not present in the local corpus")

    def _build(self):
        from bloodmap.format import read_map

        return read_map(self.path).to_build_ir()

    def test_the_e6m1_shop_display_row_is_recovered_without_being_told(self):
        """picnum 2377 is the mannequin in `tools/mine_e6m1_shop.py`'s
        owner-identified asset table. The extractor is told no such thing: it
        finds three identical sprites, collinear, evenly spaced."""
        document = extract_relations(
            self._build(), sectors=[32, 34, 45, 50, 61, 63, 79], hops=1)
        runs = [item for item in _relations(document, "repeats_along")
                if item["measures"]["picnum"] == 2377]
        self.assertEqual(len(runs), 1, "the mannequin row was not recovered")
        self.assertEqual(runs[0]["measures"]["count"], 3)
        self.assertEqual(runs[0]["measures"]["spacing_variation"], 0.0)

    def test_the_counter_subsectors_are_inside_the_counter(self):
        document = extract_relations(self._build(), sectors=[32], hops=1)
        inside = {(item["subject"], item["object"]) for item in _relations(document, "inside")}
        self.assertIn(("sector:34", "sector:32"), inside)

    def test_campaign_neighborhoods_survive_translation_and_rotation(self):
        from bloodmap.format import read_map

        maps = list_corpus_maps(population="blood-campaign")[:3]
        if not maps:
            self.skipTest("no campaign maps")
        for item in maps:
            build = read_map(item.path).to_build_ir()
            seeds = sprite_dense_seeds(build, limit=2)
            reference = extract_relations(build, sectors=seeds, hops=1)
            for turns in (1, 2, 3):
                with self.subTest(map=item.name, turns=turns):
                    moved = copy.deepcopy(build)
                    moved.rotate_quarter_turns(turns)
                    moved.translate(4096 * turns, -8192)
                    self.assertEqual(
                        extract_relations(moved, sectors=seeds, hops=1)["relations"],
                        reference["relations"],
                    )

    def test_the_pilot_reports_provenance_and_swallows_nothing(self):
        payload = mine_relations(population="blood-campaign", maps=2, seeds_per_map=1)
        self.assertEqual(payload["maps_sampled"], 2)
        self.assertTrue(payload["counts"])
        self.assertEqual(payload["errors"], [])
        for item in payload["per_map"]:
            self.assertEqual(item["population"], "blood-campaign")
            self.assertTrue(item["map"])
        self.assertTrue(payload["limitations"])


if __name__ == "__main__":
    unittest.main()
