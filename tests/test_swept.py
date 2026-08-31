"""Slide and rotate, read with the same vocabulary as everything else.

The owner's eleven E1M1 cases are the specification: one machinery, many
design objects. What is pinned here is the part the fields determine --
what the engine drags, how wide a gap that vacates, and which of the eight
names the embedding can and cannot assign.
"""

import unittest

from bloodmap.effects import (
    BODY_WIDTH, PAYLOAD_BOTH, PAYLOAD_NOTHING, PAYLOAD_SPRITES, PAYLOAD_WALLS,
    ROTATE_ABOUT_AXIS, TRANSLATE_XY, leaf_blocks, leaf_segments,
    motion_markers, payload, portal_midpoint, swept_motion, swept_opening,
)
from bloodmap.conditional import (
    LEVEL_START_CHANNELS, ROLE_FIXTURE, ROLE_NARRATIVE, ROLE_ROR_CARRIER,
    level_start_closure, ror_sectors,
)

try:
    from bloodmap.patterns import list_corpus_maps
    CORPUS = bool(list_corpus_maps(population="blood-campaign"))
except Exception:
    CORPUS = False


class Extra:
    def __init__(self, fields):
        self.fields = fields


class Item:
    def __init__(self, fields, extra=None):
        self.fields = fields
        self.extra = Extra(extra) if extra is not None else None


class Disk:
    def __init__(self, sectors=(), walls=(), sprites=()):
        self.sectors, self.walls, self.sprites = list(sectors), list(walls), list(sprites)


def wall(x, y, point2, *, next_sector=-1, cstat=0):
    return Item({"x": x, "y": y, "point2": point2, "next_sector": next_sector,
                 "next_wall": -1, "cstat": cstat, "type": 0, "picnum": 0,
                 "over_picnum": 0, "shade": 0, "pal": 0, "x_repeat": 8,
                 "y_repeat": 8, "hitag": 0, "x_panning": 0, "y_panning": 0})


def marker(index, x, y, angle=0, type_id=3):
    return Item({"type": type_id, "picnum": 0, "sector": 0, "cstat": 0,
                 "x": x, "y": y, "z": 0, "angle": angle, "pal": 0, "shade": 0,
                 "x_repeat": 64, "y_repeat": 64, "status": 10, "hitag": 0})


class PayloadTest(unittest.TestCase):
    """What the motion drags, which is not always the sector's own walls."""

    def disk(self, *, type_id=614, wall_cstats=(0, 0, 0, 0), sprite_cstats=()):
        walls = [wall(0, 0, 1, cstat=wall_cstats[0]),
                 wall(1024, 0, 2, cstat=wall_cstats[1]),
                 wall(1024, 1024, 3, cstat=wall_cstats[2]),
                 wall(0, 1024, 0, cstat=wall_cstats[3])]
        sprites = [Item({"type": 0, "picnum": 0, "sector": 0, "cstat": cstat,
                         "x": 0, "y": 0, "z": 0, "angle": 0, "pal": 0,
                         "shade": 0, "x_repeat": 48, "y_repeat": 48,
                         "status": 0, "hitag": 0})
                   for cstat in sprite_cstats]
        sector = Item({"type": type_id, "wall_ptr": 0, "wall_count": 4,
                       "floor_z": 0, "ceiling_z": -40000,
                       "floor_picnum": 0, "ceiling_picnum": 0}, {})
        return Disk([sector], walls, sprites)

    def test_a_marked_slide_drags_only_the_flagged_walls(self):
        load = payload(self.disk(wall_cstats=(16384, 0, 32768, 0)), 0)
        self.assertEqual(load["carries"], PAYLOAD_WALLS)
        self.assertEqual(load["walls_with"], [0])
        self.assertEqual(load["walls_against"], [2])
        self.assertFalse(load["moves_every_wall"])

    def test_an_unmarked_slide_drags_every_wall(self):
        # bAllWalls is `type == kSectorSlide`, so 616 needs no flags at all.
        load = payload(self.disk(type_id=616), 0)
        self.assertTrue(load["moves_every_wall"])
        self.assertEqual(load["carries"], PAYLOAD_WALLS)

    def test_a_payload_can_be_sprites_and_no_geometry_at_all(self):
        # E1M1's sector 65: 49 walls, none flagged, two wall sprites doing
        # the whole job. A reading that only sweeps geometry sees nothing.
        load = payload(self.disk(sprite_cstats=(8192, 16384)), 0)
        self.assertEqual(load["carries"], PAYLOAD_SPRITES)
        self.assertEqual(load["sprites_with"], [0])
        self.assertEqual(load["sprites_against"], [1])

    def test_walls_and_sprites_together_are_reported_as_both(self):
        load = payload(self.disk(wall_cstats=(16384, 0, 0, 0),
                                 sprite_cstats=(8192,)), 0)
        self.assertEqual(load["carries"], PAYLOAD_BOTH)

    def test_a_marked_sector_with_nothing_flagged_moves_nothing(self):
        load = payload(self.disk(), 0)
        self.assertEqual(load["carries"], PAYLOAD_NOTHING)


class SweptOpeningTest(unittest.TestCase):
    """How wide a gap the leaf vacates."""

    def motion(self, effect, travel, *, turn=0, leaf=1024.0, parts=1):
        return {"effect": effect, "travel": travel, "turn": turn,
                "payload": {"moves_every_wall": False, "walls_with": [],
                            "walls_against": [], "sprites_with": [],
                            "sprites_against": [], "wall_count": 4}}, leaf, parts

    def test_a_leaf_vacates_the_lesser_of_its_travel_and_its_length(self):
        from bloodmap.effects import swept_opening as measure

        class Fake:
            sectors = [Item({"wall_ptr": 0, "wall_count": 2, "type": 614}, {})]
            walls = [wall(0, 0, 1), wall(1024, 0, 0)]
            sprites = []

        motion = {"effect": TRANSLATE_XY, "travel": 4096,
                  "payload": {"moves_every_wall": False, "walls_with": [0],
                              "walls_against": [], "sprites_with": [],
                              "sprites_against": [], "wall_count": 2}}
        #: Travel beyond the leaf's own length buys nothing.
        self.assertEqual(measure(Fake(), 0, motion)["opening"], 1024)
        motion["travel"] = 256
        result = measure(Fake(), 0, motion)
        self.assertEqual(result["opening"], 256)
        self.assertFalse(result["admits_a_body"])

    def test_a_gap_narrower_than_a_body_admits_nobody(self):
        self.assertEqual(BODY_WIDTH, 384)

    def test_a_door_of_several_panels_opens_as_wide_as_its_widest(self):
        # Not as wide as their sum. Two 1024 leaves meeting in the middle
        # make a 1024 doorway, not a 2048 one.
        from bloodmap.effects import swept_opening as measure

        class Fake:
            sectors = [Item({"wall_ptr": 0, "wall_count": 4, "type": 614}, {})]
            walls = [wall(0, 0, 1), wall(1024, 0, 2),
                     wall(1024, 0, 3), wall(1536, 0, 0)]
            sprites = []

        motion = {"effect": TRANSLATE_XY, "travel": 4096,
                  "payload": {"moves_every_wall": False, "walls_with": [0],
                              "walls_against": [2], "sprites_with": [],
                              "sprites_against": [], "wall_count": 4}}
        result = measure(Fake(), 0, motion)
        self.assertEqual(result["leaf_parts"], 2)
        self.assertEqual(result["leaf_length"], 1024.0)
        self.assertEqual(result["opening"], 1024)


class LeafTest(unittest.TestCase):
    """Which state blocks, measured on the leaf rather than assumed."""

    def door(self, *, sign=1):
        """Two portals north and south, one leaf across the middle."""
        walls = [wall(0, 0, 1, next_sector=1), wall(2048, 0, 2),
                 wall(2048, 2048, 3, next_sector=2), wall(0, 2048, 4),
                 #: the leaf, a solid wall straight across
                 wall(0, 1024, 5, cstat=16384 if sign > 0 else 32768),
                 wall(2048, 1024, 4, cstat=16384 if sign > 0 else 32768)]
        sector = Item({"type": 614, "wall_ptr": 0, "wall_count": 6,
                       "floor_z": 0, "ceiling_z": -40000,
                       "floor_picnum": 0, "ceiling_picnum": 0}, {})
        return Disk([sector, sector, sector], walls, [])

    def motion(self, dx, dy, sign=1):
        return {"effect": TRANSLATE_XY, "travel": abs(dx) + abs(dy),
                "translation": {"dx": dx, "dy": dy}, "turn": 0,
                "payload": {"moves_every_wall": False,
                            "walls_with": [4, 5] if sign > 0 else [],
                            "walls_against": [] if sign > 0 else [4, 5],
                            "sprites_with": [], "sprites_against": [],
                            "wall_count": 6}}

    def test_a_leaf_across_the_way_blocks_at_rest_and_not_when_moved(self):
        disk = self.door()
        motion = self.motion(0, 4096)
        a, b = (1024.0, 0.0), (1024.0, 2048.0)
        self.assertTrue(leaf_blocks(disk, 0, motion, a, b, moved=False))
        self.assertFalse(leaf_blocks(disk, 0, motion, a, b, moved=True))

    def test_a_portal_is_never_part_of_the_leaf(self):
        # A leaf is something solid. Counting portals as leaf segments makes
        # every door block its own doorway, in both states, for ever.
        disk = self.door()
        motion = self.motion(0, 4096)
        segments = leaf_segments(disk, 0, motion)
        self.assertEqual(len(segments), 2)
        for start, end, _sign in segments:
            self.assertNotIn(start, {(0.0, 0.0), (2048.0, 2048.0)})
        #: With the portals counted in, the way is blocked whatever happens.
        motion["payload"]["walls_with"] = [0, 2, 4, 5]
        self.assertEqual(len(leaf_segments(disk, 0, motion)), 2)

    def test_the_two_halves_of_a_double_door_travel_opposite_ways(self):
        # `cstat & 32768` moves against the motion. Translating both halves
        # the same way leaves half the door still across the opening -- and
        # the door then reads as never opening at all.
        disk = self.door(sign=-1)
        motion = self.motion(0, 4096, sign=-1)
        segments = leaf_segments(disk, 0, motion)
        self.assertEqual({sign for _, _, sign in segments}, {-1})
        a, b = (1024.0, 0.0), (1024.0, 2048.0)
        #: Travelling against the motion clears the way just as travelling
        #: with it does; only the direction differs.
        self.assertTrue(leaf_blocks(disk, 0, motion, a, b, moved=False))
        self.assertFalse(leaf_blocks(disk, 0, motion, a, b, moved=True))

    def test_a_true_double_door_retracts_into_opposite_jambs(self):
        # The left leaf goes left and the right leaf goes right. Sliding
        # both the same way carries one of them straight across the opening
        # it was supposed to clear, and the door reads as never opening.
        left = wall(0, 1024, 1, cstat=32768)      # against: retracts to -x
        left_end = wall(1024, 1024, 0, cstat=32768)
        right = wall(1024, 1024, 3, cstat=16384)  # with: retracts to +x
        right_end = wall(2048, 1024, 2, cstat=16384)
        walls = [left, left_end, right, right_end,
                 wall(0, 0, 5, next_sector=1), wall(2048, 0, 4),
                 wall(0, 2048, 7, next_sector=2), wall(2048, 2048, 6)]
        sector = Item({"type": 614, "wall_ptr": 0, "wall_count": 8,
                       "floor_z": 0, "ceiling_z": -40000,
                       "floor_picnum": 0, "ceiling_picnum": 0}, {})
        disk = Disk([sector, sector, sector], walls, [])
        motion = {"effect": TRANSLATE_XY, "travel": 700,
                  "translation": {"dx": 700, "dy": 0}, "turn": 0,
                  "payload": {"moves_every_wall": False,
                              "walls_with": [2, 3], "walls_against": [0, 1],
                              "sprites_with": [], "sprites_against": [],
                              "wall_count": 8}}
        #: Cross at x=1500, inside the right leaf rather than exactly on
        #: the seam where the two meet.
        a, b = (1500.0, 0.0), (1500.0, 2048.0)
        self.assertTrue(leaf_blocks(disk, 0, motion, a, b, moved=False))
        #: With the signs honoured the right leaf retracts to 1724..2748 and
        #: the way is clear. Without them the *left* leaf lands on 700..1724
        #: and is still across it.
        self.assertFalse(leaf_blocks(disk, 0, motion, a, b, moved=True))

    def test_a_sector_with_no_solid_moving_wall_has_no_leaf_to_judge(self):
        # None, not False: "no leaf found" and "the leaf is not in the way"
        # are different answers and only one of them is a measurement.
        disk = self.door()
        motion = self.motion(0, 4096)
        motion["payload"]["walls_with"] = []
        self.assertIsNone(leaf_blocks(disk, 0, motion, (0.0, 0.0),
                                      (1.0, 1.0), moved=False))

    def test_a_portal_midpoint_is_the_middle_of_the_shared_wall(self):
        self.assertEqual(portal_midpoint(self.door(), 0, 1), (1024.0, 0.0))
        self.assertIsNone(portal_midpoint(self.door(), 0, 99))


class MarkerTest(unittest.TestCase):
    def test_a_slide_interpolates_between_two_markers(self):
        disk = Disk([Item({"type": 614, "wall_ptr": 0, "wall_count": 0,
                           "floor_z": 0, "ceiling_z": -1},
                          {"marker_0": 0, "marker_1": 1})],
                    [], [marker(0, 100, 200), marker(1, 100, 1200, type_id=4)])
        record = {"type_id": 614, "busy_time_a": 10}
        motion = swept_motion(disk, 0, record)
        self.assertEqual(motion["effect"], TRANSLATE_XY)
        self.assertEqual(motion["translation"], {"dx": 0, "dy": 1000})
        self.assertEqual(motion["travel"], 1000)

    def test_a_rotate_turns_about_one_marker(self):
        disk = Disk([Item({"type": 617, "wall_ptr": 0, "wall_count": 0,
                           "floor_z": 0, "ceiling_z": -1},
                          {"marker_0": 0, "marker_1": -1})],
                    [], [marker(0, 500, 500, angle=512, type_id=5)])
        motion = swept_motion(disk, 0, {"type_id": 617, "busy_time_a": 8})
        self.assertEqual(motion["effect"], ROTATE_ABOUT_AXIS)
        self.assertEqual(motion["pivot"], {"x": 500, "y": 500})
        self.assertEqual(motion["turn"], 512)

    def test_a_marked_motion_with_no_marker_claims_no_travel(self):
        disk = Disk([Item({"type": 614, "wall_ptr": 0, "wall_count": 0,
                           "floor_z": 0, "ceiling_z": -1},
                          {"marker_0": -1, "marker_1": -1})], [], [])
        motion = swept_motion(disk, 0, {"type_id": 614, "busy_time_a": 10})
        self.assertIsNone(motion["travel"])
        self.assertTrue(motion["undriven"])

    def test_a_z_motion_sector_is_not_a_swept_one(self):
        disk = Disk([Item({"type": 600, "wall_ptr": 0, "wall_count": 0,
                           "floor_z": 0, "ceiling_z": -1}, {})], [], [])
        self.assertIsNone(swept_motion(disk, 0, {"type_id": 600,
                                                 "busy_time_a": 10}))


class LevelStartTest(unittest.TestCase):
    """Some of a level has already happened before the player moves."""

    def test_the_broadcast_channels_are_the_engine_s(self):
        self.assertIn(7, LEVEL_START_CHANNELS)

    def test_a_switch_listening_on_level_start_fires_before_anyone_arrives(self):
        # E1M1's casket: the player starts inside it, and the switch that
        # opens it is elsewhere on rx 7. Treating that as a player action
        # reports the level unreachable.
        disk = Disk([], [], [Item({"type": 20, "picnum": 0, "sector": 9,
                                   "cstat": 0, "x": 0, "y": 0, "z": 0,
                                   "angle": 0, "pal": 0, "shade": 0,
                                   "x_repeat": 8, "y_repeat": 8,
                                   "status": 0, "hitag": 0},
                                  {"rx_id": 7, "tx_id": 102})])
        fired = level_start_closure(disk)
        self.assertIn(102, fired)

    def test_the_closure_follows_a_chain(self):
        def relay(rx, tx):
            return Item({"type": 20, "picnum": 0, "sector": 0, "cstat": 0,
                         "x": 0, "y": 0, "z": 0, "angle": 0, "pal": 0,
                         "shade": 0, "x_repeat": 8, "y_repeat": 8,
                         "status": 0, "hitag": 0}, {"rx_id": rx, "tx_id": tx})

        fired = level_start_closure(Disk([], [], [relay(7, 200), relay(200, 300)]))
        self.assertIn(300, fired)

    def test_a_channel_nothing_reaches_from_the_start_stays_unfired(self):
        def item(rx, tx):
            return Item({"type": 20, "picnum": 0, "sector": 0, "cstat": 0,
                         "x": 0, "y": 0, "z": 0, "angle": 0, "pal": 0,
                         "shade": 0, "x_repeat": 8, "y_repeat": 8,
                         "status": 0, "hitag": 0}, {"rx_id": rx, "tx_id": tx})

        self.assertNotIn(400, level_start_closure(Disk([], [], [item(150, 400)])))


@unittest.skipUnless(CORPUS, "the Blood corpus is not present")
class OwnerCasesTest(unittest.TestCase):
    """The owner's attested reading of E1M1, as far as fields determine it."""

    def setUp(self):
        from bloodmap.format import read_map
        entry = [item for item in list_corpus_maps(population="blood-campaign")
                 if item.path.stem == "E1M1"][0]
        self.disk = read_map(entry.path)

    def motion(self, sector_id):
        from bloodmap.doors import observe_motion_sector

        record = observe_motion_sector(self.disk, sector_id)
        return swept_motion(self.disk, sector_id, record)

    def test_sector_65_carries_its_gate_as_sprites_and_no_walls(self):
        load = self.motion(65)["payload"]
        self.assertEqual(load["carries"], PAYLOAD_SPRITES)
        self.assertEqual(load["wall_count"], 49)
        self.assertEqual(load["walls_with"], [])
        self.assertEqual(load["walls_against"], [])
        self.assertEqual(sorted(load["sprites_with"] + load["sprites_against"]),
                         [37, 38])

    def test_sector_4_is_one_sector_carrying_both_leaves(self):
        load = self.motion(4)["payload"]
        self.assertEqual(len(load["walls_with"]), 3)
        self.assertEqual(len(load["walls_against"]), 3)

    def test_sector_90_is_an_ror_volume_that_moves_nothing(self):
        self.assertEqual(self.motion(90)["payload"]["carries"], PAYLOAD_NOTHING)

    def test_both_halves_of_the_casket_are_one_room_over_room_pair(self):
        from bloodmap.conditional import build_graph

        graph = build_graph(self.disk)
        linked = ror_sectors(graph.reach)
        self.assertIn(30, linked)
        self.assertIn(28, linked)

    def test_the_arc_turns_about_its_axis(self):
        motion = self.motion(26)
        self.assertEqual(motion["effect"], ROTATE_ABOUT_AXIS)
        self.assertEqual(abs(motion["turn"]), 512)

    def test_the_sink_never_opens_a_body_s_width(self):
        from bloodmap.conditional import build_graph, design_role

        graph = build_graph(self.disk)
        self.assertEqual(design_role(graph, 86)["role"], ROLE_FIXTURE)

    def test_the_casket_is_where_the_player_starts(self):
        from bloodmap.conditional import build_graph, design_role

        graph = build_graph(self.disk)
        self.assertEqual(design_role(graph, 30)["role"], ROLE_NARRATIVE)

    def test_the_reused_ror_volume_reads_as_a_technical_workaround(self):
        from bloodmap.conditional import build_graph, design_role

        graph = build_graph(self.disk)
        self.assertEqual(design_role(graph, 65)["role"], ROLE_ROR_CARRIER)


if __name__ == "__main__":
    unittest.main()
