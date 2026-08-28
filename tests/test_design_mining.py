"""The three mining passes that answer authoring questions, not census questions.

Each of these pins a *finding*, not a plumbing detail: if the corpus stopped
saying what it says, the authoring advice built on it would be wrong and these
would fail.  The corpus cases skip themselves without the Blood maps.
"""

from __future__ import annotations

import glob
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
MAPS = ROOT / "maps" / "blood"
ART = ROOT / "reference" / "blood"


def have_campaign() -> bool:
    return bool(glob.glob(str(MAPS / "E?M?.MAP")))


class BandingTests(unittest.TestCase):
    def test_bands_are_ordered_and_total(self):
        from tools.mine_surface_palettes import AREA_BANDS, HEIGHT_BANDS, _band

        limits = [limit for limit, _name in AREA_BANDS]
        self.assertEqual(limits, sorted(limits))
        self.assertEqual(_band(0.5, AREA_BANDS), "tiny")
        self.assertEqual(_band(10_000.0, AREA_BANDS), "vast")   # nothing falls out
        self.assertEqual(_band(2.0, HEIGHT_BANDS), "low")


class MechanismShapeTests(unittest.TestCase):
    def test_shapes_are_named_by_what_they_do(self):
        from tools.mine_mechanisms import _shape

        def record(tx, rx):
            return {"transmitters": tx, "receivers": rx}

        self.assertEqual(_shape(record(1, 1)), "one_to_one")
        self.assertEqual(_shape(record(1, 4)), "fan_out")
        self.assertEqual(_shape(record(3, 1)), "fan_in")
        self.assertEqual(_shape(record(2, 2)), "mesh")
        self.assertEqual(_shape(record(0, 2)), "orphan_receiver")
        self.assertEqual(_shape(record(2, 0)), "orphan_transmitter")


@unittest.skipUnless(have_campaign(), "no Blood campaign maps")
class SurfaceEvidenceTests(unittest.TestCase):
    """Texture is inherited from what adjoins it, not looked up per room."""

    @classmethod
    def setUpClass(cls):
        import tools.mine_surface_palettes as mod

        rows = []
        seen = set()
        for path in sorted(glob.glob(str(MAPS / "*.MAP"))):
            name = Path(path).stem.upper()
            if name in seen or not mod.CAMPAIGN.match(name):
                continue
            seen.add(name)
            rows.extend(mod.observe_map(Path(path)))
        cls.rows = rows
        cls.predictors = mod.compare_predictors(rows)["accuracy"]

    def test_adjacency_beats_both_the_map_favourite_and_the_room_context(self):
        """The finding the authoring rule rests on.

        If a per-context lookup table beat adjacency, picking each sector's tile
        independently would be the right model. It does not, on any surface.
        """
        for role in ("wall", "floor", "ceiling"):
            with self.subTest(role=role):
                favourite = self.predictors["map_favourite"][role]
                context = self.predictors["context"][role]
                neighbours = self.predictors["neighbours"][role]
                self.assertGreater(context, favourite)
                self.assertGreater(neighbours, context)

    def test_context_still_carries_information(self):
        """Adjacency winning does not make the space irrelevant."""
        for role in ("wall", "floor", "ceiling"):
            with self.subTest(role=role):
                self.assertGreaterEqual(
                    self.predictors["neighbours_in_context"][role],
                    self.predictors["neighbours"][role],
                )


@unittest.skipUnless(have_campaign() and ART.exists(), "no Blood campaign maps or ART")
class DecorationEvidenceTests(unittest.TestCase):
    """A decoration has a canonical size and alignment; both belong to the tile."""

    @classmethod
    def setUpClass(cls):
        import tools.mine_decoration as mod
        from bloodmap.art import read_art_directory

        art = read_art_directory(str(ART))
        rows = []
        seen = set()
        for path in sorted(glob.glob(str(MAPS / "*.MAP"))):
            name = Path(path).stem.upper()
            if name in seen or not mod.CAMPAIGN.match(name):
                continue
            seen.add(name)
            rows.extend(mod.observe(Path(path), art))
        cls.document = mod.build(rows, min_uses=20)

    def test_decorations_are_drawn_at_their_natural_size(self):
        """Which is why asking an author for a height is asking for a mistake."""
        sizing = self.document["sizing"]
        self.assertGreater(sizing["natural_size_share"], 0.5)
        self.assertGreater(sizing["power_of_two_share"], 0.7)

    def test_hardly_any_decoration_scales_with_its_room(self):
        sizing = self.document["sizing"]
        self.assertLess(sizing["median_room_height_correlation"], 0.3)
        self.assertGreater(sizing["tiles_drawn_at_one_size"],
                           sizing["tiles_that_scale_with_the_room"])

    def test_alignment_belongs_to_the_tile(self):
        """Most tiles are only ever hung one way, so it is not a per-use choice."""
        decided = 0
        for tile in self.document["tiles"]:
            if max(tile["alignment"].values()) >= 0.9:
                decided += 1
        self.assertGreater(decided, len(self.document["tiles"]) // 2)


@unittest.skipUnless(have_campaign(), "no Blood campaign maps")
class MechanismEvidenceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        import tools.mine_mechanisms as mod

        observations = []
        seen = set()
        for path in sorted(glob.glob(str(MAPS / "*.MAP"))):
            name = Path(path).stem.upper()
            if name in seen or not mod.CAMPAIGN.match(name):
                continue
            seen.add(name)
            observations.append(mod.observe(Path(path)))
        cls.document = mod.build(observations)

    def test_a_level_is_dozens_of_wired_mechanisms(self):
        self.assertGreater(self.document["user_channels_per_map"]["median"], 20)

    def test_most_channels_are_not_a_switch_and_a_door(self):
        """Fan-out and fan-in together outnumber the one-to-one pairs."""
        shapes = self.document["shapes"]
        branching = shapes["fan_out"]["share"] + shapes["fan_in"]["share"]
        self.assertGreater(branching, shapes["one_to_one"]["share"])

    def test_the_campaign_carries_orphan_channels_too(self):
        """So a converted map with a few is in normal company, not broken."""
        shapes = self.document["shapes"]
        orphans = shapes["orphan_receiver"]["share"] + shapes["orphan_transmitter"]["share"]
        self.assertGreater(orphans, 0.02)
        self.assertLess(orphans, 0.25)



class DecorationTableTests(unittest.TestCase):
    """The mined table, as the authoring path would use it."""

    def test_a_known_decoration_comes_back_at_its_campaign_size(self):
        from bloodmap.decoration import DECORATION, decoration_appearance

        self.assertTrue(DECORATION)
        appearance = decoration_appearance(2915)
        self.assertEqual(appearance["type"], 0)
        self.assertEqual(appearance["picnum"], 2915)
        self.assertEqual(appearance["y_repeat"], DECORATION[2915]["y_repeat"])
        self.assertEqual(appearance["cstat"], DECORATION[2915]["cstat"])

    def test_an_unknown_tile_falls_back_to_the_natural_size(self):
        from bloodmap.decoration import (
            decoration_appearance, height_range, is_confident_size,
        )

        appearance = decoration_appearance(999_999)
        self.assertEqual(appearance["y_repeat"], 64)
        self.assertEqual(appearance["cstat"], 128)
        self.assertFalse(is_confident_size(999_999))
        self.assertIsNone(height_range(999_999))

    def test_size_and_mounting_are_answered_separately(self):
        """Tile 641 is one size in 96% of its uses and hung several ways.

        Asking one question about both would throw its size away, which is what
        the monastery was doing: it drew 641 at a quarter of the only height the
        campaign ever gives it.
        """
        from bloodmap.decoration import (
            CONFIDENT_SHARE, DECORATION, is_confident_mounting, is_confident_size,
        )

        self.assertTrue(is_confident_size(641))
        self.assertFalse(is_confident_mounting(641))

        sized = [t for t in DECORATION if is_confident_size(t)]
        mounted = [t for t in DECORATION if is_confident_mounting(t)]
        self.assertTrue(sized)
        self.assertTrue(mounted)
        self.assertNotEqual(set(sized), set(mounted))
        for picnum in sized:
            with self.subTest(picnum=picnum):
                self.assertGreaterEqual(DECORATION[picnum]["size_share"], CONFIDENT_SHARE)

    def test_the_observed_height_range_brackets_the_canonical_size(self):
        from bloodmap.decoration import DECORATION, height_range

        for picnum, record in DECORATION.items():
            low, high = height_range(picnum)
            with self.subTest(picnum=picnum):
                self.assertLessEqual(low, record["height_median"])
                self.assertLessEqual(record["height_median"], high)

    def test_overrides_win(self):
        from bloodmap.decoration import decoration_appearance

        self.assertEqual(decoration_appearance(2915, shade=0)["shade"], 0)


@unittest.skipUnless(have_campaign(), "no Blood campaign maps")
class PatchShareTests(unittest.TestCase):
    """Blood paints regions; a level that paints rooms scores low here."""

    def test_the_campaign_paints_most_of_a_level_in_patches(self):
        from bloodmap.format import read_map
        from bloodmap.level_profile import level_profile

        shares = []
        for path in sorted(glob.glob(str(MAPS / "E?M?.MAP")))[:8]:
            profile = level_profile(read_map(path))
            shares.append(profile["materials"]["floor_patch_share"])
        self.assertGreater(min(shares), 0.4)
        self.assertGreater(sum(shares) / len(shares), 0.6)

    def test_a_level_painted_room_by_room_would_score_near_zero(self):
        """The measure has to be able to fail, or it is not measuring anything."""
        from bloodmap.level_profile import _patch_share

        playable = {0, 1, 2, 3, 4}
        chain = {0: {1}, 1: {0, 2}, 2: {1, 3}, 3: {2, 4}, 4: {3}}
        every_room_its_own = {i: i for i in playable}
        one_finish = {i: 7 for i in playable}

        self.assertEqual(_patch_share(None, playable, chain, every_room_its_own), 0.0)
        self.assertEqual(_patch_share(None, playable, chain, one_finish), 1.0)



class BlockedPortalTests(unittest.TestCase):
    """Blood's way to stop a player at a boundary it can see across."""

    def _layout(self, role):
        from bloodmap.planar_layout import PlanarLayout

        U = 384
        PH = 0x1600
        surface = dict(wall_picnum=180, floor_picnum=292, ceiling_picnum=385,
                       wall_shade=8, floor_shade=16, ceiling_shade=8)
        layout = PlanarLayout(name="rail", visibility=800)
        layout.add_region("region:west", [(0, 0), (4 * U, 0), (4 * U, 4 * U), (0, 4 * U)],
                          role="interior", floor_z=0, ceiling_z=-6 * PH, **surface)
        layout.add_region("region:east", [(4 * U, 0), (8 * U, 0), (8 * U, 4 * U), (4 * U, 4 * U)],
                          role="interior", floor_z=-2048, ceiling_z=-6 * PH, **surface)
        # Half the shared edge is a way through and half is the rail, which is the
        # arrangement the monastery's chancel has: you go round rather than over.
        layout.add_connection("connection:door", "region:west", "region:east",
                              a1=(4 * U, 0), a2=(4 * U, 2 * U), min_width=512)
        layout.add_partition("partition:rail", "region:west", "region:east", role=role,
                             a1=(4 * U, 2 * U), a2=(4 * U, 4 * U))
        layout.set_player_start("region:west", x=2 * U, y=2 * U, z=0)
        return layout

    def test_a_blocked_portal_joins_the_sectors_and_flags_the_wall(self):
        from bloodmap.format import encode_map, parse_map
        from bloodmap.level_profile import coincident_solid_pairs

        level = parse_map(encode_map(self._layout("blocked_portal").compile().level.to_disk_map()))

        joined = [w for w in level.walls if int(w.fields["next_sector"]) >= 0]
        blocking = [w for w in joined if int(w.fields["cstat"]) & 1]
        self.assertEqual(len(blocking), 2)             # one wall each side
        self.assertGreater(len(joined), len(blocking))  # the doorway stays open
        self.assertEqual(coincident_solid_pairs(level), [])

    def test_a_solid_boundary_leaves_a_wall_with_no_inside(self):
        """The shape that started this: legal, renders, and Blood never does it."""
        from bloodmap.format import encode_map, parse_map
        from bloodmap.level_profile import coincident_solid_pairs

        level = parse_map(encode_map(self._layout("solid_boundary").compile().level.to_disk_map()))

        self.assertTrue(coincident_solid_pairs(level))


@unittest.skipUnless(have_campaign(), "no Blood campaign maps")
class CoincidentSolidPairTests(unittest.TestCase):
    def test_no_campaign_map_contains_one(self):
        """113,261 walls, 43 maps, zero. That is what makes it a defect."""
        from bloodmap.format import read_map
        from bloodmap.level_profile import coincident_solid_pairs

        for path in sorted(glob.glob(str(MAPS / "E?M?.MAP"))):
            with self.subTest(map=Path(path).stem):
                self.assertEqual(coincident_solid_pairs(read_map(path)), [])


@unittest.skipUnless(have_campaign() and ART.exists(), "no Blood campaign maps or ART")
class MonasteryDecorationTests(unittest.TestCase):
    """Every decoration in the authored level sits at a size Blood uses.

    Before the corpus sizes were applied, all 55 of them sat below the smallest
    size the campaign ever draws them at -- tile 1044 by a factor of five -- and
    the same tile appeared at four or five different sizes in one level.
    """

    CANDIDATE = ROOT / "projects" / "reasoned-authoring-v1" / "level" / "candidate-v5.MAP"

    @unittest.skipUnless(CANDIDATE.exists(), "candidate not built")
    def test_no_decoration_is_outside_the_campaign_range(self):
        from bloodmap.art import read_art_directory
        from bloodmap.decoration import height_bounds
        from bloodmap.format import read_map

        art = read_art_directory(str(ART))
        level = read_map(self.CANDIDATE)
        checked = 0
        for sprite in level.sprites:
            fields = sprite.fields
            if int(fields["type"]) != 0 or int(fields["cstat"]) & 32768:
                continue
            tile = art.get(int(fields["picnum"]))
            span = height_bounds(int(fields["picnum"]))
            if tile is None or not tile.height or span is None:
                continue
            drawn = ((int(fields["y_repeat"]) * tile.height) << 2) / 0x1600
            checked += 1
            with self.subTest(picnum=int(fields["picnum"])):
                # The true bounds, not p10/p90: a percentile band is where the
                # campaign usually draws a tile, and 6% of its own decorations
                # sit outside their tile's band, so using it as a limit rejects
                # Blood itself. Tile 1044 is the case that showed it -- p10 5.09
                # against three shipped fences at 4.36 and two at 3.64.
                # Rounded to two decimals, so compare with a little slack.
                self.assertGreaterEqual(drawn, span[0] * 0.98)
                self.assertLessEqual(drawn, span[1] * 1.02)
        self.assertGreater(checked, 40)

    @unittest.skipUnless(CANDIDATE.exists(), "candidate not built")
    def test_one_tile_is_drawn_at_one_size(self):
        """Blood does not use a tile at five sizes in a level, and nor should this."""
        from collections import defaultdict

        from bloodmap.decoration import is_confident_size
        from bloodmap.format import read_map

        level = read_map(self.CANDIDATE)
        sizes = defaultdict(set)
        for sprite in level.sprites:
            fields = sprite.fields
            if int(fields["type"]) != 0 or int(fields["cstat"]) & 32768:
                continue
            sizes[int(fields["picnum"])].add(int(fields["y_repeat"]))
        for picnum, values in sizes.items():
            if not is_confident_size(picnum):
                continue
            with self.subTest(picnum=picnum):
                self.assertEqual(len(values), 1)


@unittest.skipUnless(
    (ROOT / "projects" / "reasoned-authoring-v1" / "level" / "candidate-v5.MAP").exists(),
    "candidate not built")
class MonasteryMechanismTests(unittest.TestCase):
    """The mechanisms added from campaign precedent, and that they stay safe."""

    CANDIDATE = ROOT / "projects" / "reasoned-authoring-v1" / "level" / "candidate-v5.MAP"

    @classmethod
    def setUpClass(cls):
        from bloodmap.format import read_map

        cls.level = read_map(cls.CANDIDATE)

    def test_the_cracked_wall_is_wired_the_way_the_campaign_wires_one(self):
        """108 cracks in 27 of 43 maps, always tile 1127, on statnum 4, wired to
        exploders and a type-600 hole.

        The statnum is the load-bearing part and was wrong here: `actDamageSprite`
        runs its health-and-trigger path under `case kStatThing` and `actInit`
        hands out `startHealth` on the same list, so a crack anywhere else cannot
        be damaged and never transmits.

        This used to assert `trigger_vector`, on the reasoning that a crack takes
        no bullet damage of its own and so needs the bit to answer a shot. The
        first half is right and the conclusion does not follow: `thingInfo` for
        kThingWallCrack is dmgControl {0, 0, 0, 256, 0, 0, 0} and index 3 is
        kDamageExplode, so a bullet is multiplied by zero however the sprite is
        flagged. A crack is opened by a blast, which is why 107 of the
        campaign's 108 leave the bit clear.
        """
        cracks = [s for s in self.level.sprites if int(s.fields["type"]) == 408]
        self.assertEqual(len(cracks), 1)
        crack = cracks[0]
        self.assertEqual(int(crack.fields["picnum"]), 1127)
        self.assertEqual(int(crack.fields["status"]), 4)
        extra = crack.extra.fields
        self.assertEqual(int(extra["state"]), 0)
        self.assertFalse(int(extra["trigger_vector"]))
        self.assertTrue(int(extra["trigger_off"]))
        channel = int(extra["tx_id"])
        self.assertGreater(channel, 0)

        traps = [s for s in self.level.sprites
                 if int(s.fields["type"]) == 459
                 and int(s.extra.fields.get("rx_id", 0)) == channel]
        holes = [s for s in self.level.sectors
                 if s.extra and int(s.extra.fields.get("rx_id", 0)) == channel
                 and int(s.fields["type"]) == 600]
        self.assertGreaterEqual(len(traps), 2)
        self.assertGreaterEqual(len(holes), 1)
        for trap in traps:
            with self.subTest(trap=int(trap.fields["picnum"])):
                self.assertEqual(int(trap.fields["status"]), 11)   # kStatTraps
                self.assertGreaterEqual(int(trap.extra.fields["wait_time"]), 1)

    def test_the_level_uses_more_than_one_kind_of_door(self):
        from collections import Counter

        kinds = Counter(int(s.fields["type"]) for s in self.level.sectors
                        if 600 <= int(s.fields["type"]) <= 619)
        self.assertGreaterEqual(len(kinds), 3)
        self.assertIn(600, kinds)   # z-motion
        self.assertIn(614, kinds)   # the sliding fence gate
        self.assertIn(617, kinds)   # the rotating panel

    def test_a_fence_sprite_carries_the_bit_that_makes_it_travel(self):
        """TranslateSector moves a sprite with its sector only for cstat 8192 or
        16384. Without one the sector moves and the fence stands still."""
        fences = [s for s in self.level.sprites
                  if int(s.fields["picnum"]) in (1044, 1064)
                  and int(s.fields["cstat"]) & (8192 | 16384)]
        self.assertGreaterEqual(len(fences), 3)
        # E1M1 parts its gate by giving one leaf each bit.
        gate = [s for s in fences if int(s.fields["picnum"]) == 1044]
        bits = {int(s.fields["cstat"]) & (8192 | 16384) for s in gate}
        self.assertEqual(bits, {8192, 16384})

    def test_a_sprite_gate_moves_no_geometry_at_all(self):
        """Which is why it cannot distort the courtyard it shares a wall with.

        E1M1's fence gate is a 49-wall type-614 sector with none of them marked.
        """
        from bloodmap.motion_sim import blood_sweep

        for index, sector in enumerate(self.level.sectors):
            if int(sector.fields["type"]) != 614:
                continue
            start = int(sector.fields["wall_ptr"])
            count = int(sector.fields["wall_count"])
            marked = [w for w in range(start, start + count)
                      if int(self.level.walls[w].fields["cstat"]) & (16384 | 32768)]
            with self.subTest(sector=index):
                self.assertEqual(marked, [])
                frames = blood_sweep(self.level, index, steps=8)
                for frame in frames:
                    self.assertEqual(frame, frames[0])

    def test_every_moving_sector_stays_clear_of_what_it_does_not_touch(self):
        from bloodmap.motion_sim import (
            blood_sector_walls, blood_sweep, polygons_overlap, rest_displacement,
            self_intersections,
        )

        moving = [i for i, s in enumerate(self.level.sectors)
                  if int(s.fields["type"]) in (614, 615, 616, 617)]
        self.assertTrue(moving)
        for index in moving:
            sector = self.level.sectors[index]
            start = int(sector.fields["wall_ptr"])
            count = int(sector.fields["wall_count"])
            neighbours = {int(self.level.walls[w].fields["next_sector"])
                          for w in range(start, start + count)}
            neighbours.discard(-1)
            neighbours.add(index)
            frames = blood_sweep(self.level, index, steps=16)
            with self.subTest(sector=index):
                # It must start where it was drawn, never fold, and never sweep
                # into a sector it does not share a wall with.
                self.assertLess(rest_displacement(self.level, index, frames), 8.0)
                for step, frame in enumerate(frames):
                    self.assertEqual(self_intersections(frame), [], f"folds at step {step}")
                    for other in range(len(self.level.sectors)):
                        if other in neighbours:
                            continue
                        self.assertFalse(
                            polygons_overlap(frame, blood_sector_walls(self.level, other)),
                            f"sweeps into sector {other} at step {step}",
                        )


@unittest.skipUnless(
    (ROOT / "projects" / "reasoned-authoring-v1" / "level" / "candidate-v5.MAP").exists(),
    "candidate not built")
class MonasteryWaterTests(unittest.TestCase):
    """The dive, built the way the campaign builds one."""

    CANDIDATE = ROOT / "projects" / "reasoned-authoring-v1" / "level" / "candidate-v5.MAP"

    @classmethod
    def setUpClass(cls):
        from bloodmap.format import read_map

        cls.level = read_map(cls.CANDIDATE)

    def test_the_water_is_a_marker_pair_not_a_hole_in_the_floor(self):
        """kMarkerUpWater and kMarkerLowWater matched on data1: 191 pairs across
        24 of the 43 maps, tiles 2332 and 2331 on statnum 0."""
        from bloodmap.reachability import link_pairs

        pairs = link_pairs(self.level)
        self.assertGreaterEqual(len(pairs), 2)
        ups = [s for s in self.level.sprites if int(s.fields["type"]) == 9]
        lows = [s for s in self.level.sprites if int(s.fields["type"]) == 10]
        self.assertEqual(len(ups), len(lows))
        for sprite in ups:
            self.assertEqual(int(sprite.fields["picnum"]), 2332)
        for sprite in lows:
            self.assertEqual(int(sprite.fields["picnum"]), 2331)

    def test_only_the_lower_side_is_underwater(self):
        """180 of the campaign's 191 pairs put Underwater on the sunk sector and
        leave it off the pool: the surface is air you dive through."""
        from bloodmap.reachability import link_pairs

        for pair in link_pairs(self.level):
            left, right = pair["sectors"]
            flags = []
            for sector_id in (left, right):
                extra = self.level.sectors[sector_id].extra
                flags.append(bool(extra and int(extra.fields.get("underwater", 0))))
            with self.subTest(pair=pair["sectors"]):
                self.assertEqual(sorted(flags), [False, True])

    def test_the_sunk_rooms_are_reachable_only_by_diving(self):
        """They share no wall with the dry level, which is what makes the marker
        pair the way in rather than a shortcut beside it."""
        from bloodmap.reachability import portal_graph

        walls_only = portal_graph(self.level)
        underwater = {i for i, s in enumerate(self.level.sectors)
                      if s.extra and int(s.extra.fields.get("underwater", 0))}
        self.assertTrue(underwater)
        for sector_id in underwater:
            for neighbour in walls_only.get(sector_id, ()):
                with self.subTest(sector=sector_id, neighbour=neighbour):
                    self.assertIn(neighbour, underwater)

    def test_every_sector_is_still_reachable(self):
        from bloodmap.reachability import analyze_reachability

        reach = analyze_reachability(self.level)
        self.assertEqual(len(reach.offmap), 0)

    def test_the_surface_is_the_same_tile_from_above_and_below(self):
        """A pool's floor and the sunk room's ceiling are one surface.

        2915 is the *floor* of 96 pool sectors in the campaign and the *ceiling*
        of 99 underwater ones, and 1120 is the same idea. Dressing the pool in
        ordinary masonry is the tell that it was never thought of as water.
        """
        from bloodmap.reachability import link_pairs

        surfaces = {2915, 1120}
        for pair in link_pairs(self.level):
            left, right = pair["sectors"]
            lower = left if self._is_underwater(left) else right
            upper = right if lower == left else left
            with self.subTest(pair=pair["sectors"]):
                self.assertIn(int(self.level.sectors[upper].fields["floor_picnum"]), surfaces)
                self.assertIn(int(self.level.sectors[lower].fields["ceiling_picnum"]), surfaces)
                # ...and the bottom is ground, not more water.
                self.assertNotIn(int(self.level.sectors[lower].fields["floor_picnum"]), surfaces)

    def _is_underwater(self, sector_id):
        extra = self.level.sectors[sector_id].extra
        return bool(extra and int(extra.fields.get("underwater", 0)))

    def test_the_swim_covers_the_distance_it_claims_to(self):
        """The one way to get a dive wrong that the engine will not object to.

        Across the campaign's 732 pool-to-pool routes the underwater path runs a
        median 1.19 times the straight-line gap between the pools and is almost
        never shorter, p10 0.95. A shorter one puts the player out somewhere the
        swim could not have carried them.
        """
        from bloodmap.level_profile import water_route_ratios

        ratios = water_route_ratios(self.level)
        self.assertTrue(ratios)
        for ratio in ratios:
            self.assertGreaterEqual(ratio, 0.95)

    def test_the_dive_is_not_a_wormhole(self):
        """Two mouths you can also walk between must dive by the same offset.

        This is the condition the earlier reading missed. Measured over every
        campaign pool pair that shares one underwater region:

        * both mouths reachable on foot -- 630 agree, 4 disagree;
        * not both reachable on foot -- 8 agree, 100 disagree.

        So the translation is only pinned when the player can walk the same trip
        and compare. Two genuinely separate flooded places owe each other
        nothing, which is why "a third of maps are consistent" looked like a weak
        convention: it was averaging a near-law with a free choice.
        """
        from bloodmap.level_profile import water_wormholes

        self.assertEqual(water_wormholes(self.level), [])

    def test_a_disagreeing_pair_is_only_a_wormhole_when_you_can_walk_it(self):
        """The check must not fire on two unconnected flooded places."""
        from bloodmap.level_profile import water_wormholes

        self.assertEqual(len(water_wormholes(self.level)), 0)
        from bloodmap.format import read_map

        moved = read_map(self.CANDIDATE)
        for sprite in moved.sprites:
            if sprite.extra is None or int(sprite.fields["type"]) != 10:
                continue
            if int(sprite.extra.fields.get("data_1", 0)) == 2:
                sprite.fields["x"] = int(sprite.fields["x"]) + 40 * 384
        # Now one shaft dives by a different offset than the other, and the two
        # mouths are still walkable, so the swim would come out 40 widths from
        # where the walk says it should.
        self.assertEqual(len(water_wormholes(moved)), 1)
        self.assertGreater(water_wormholes(moved)[0]["drift_player_widths"], 30)


@unittest.skipUnless(have_campaign(), "no Blood campaign maps")
class XSpriteRequiredTests(unittest.TestCase):
    """The fault that loaded cleanly and then segfaulted NBlood.

    Every structural validator the project had passed the map: 0 native
    diagnostics, 0 authored errors, all 13 hard gates green. It crashed anyway,
    because Blood reaches through `sprite.extra` into `xsprite[]` for sprites on
    certain statnums, and a sprite without an XSprite sends it to index -1.
    Bisecting against the real engine narrowed it to a single dude; giving that
    dude an empty XSprite fixed it.
    """

    REQUIRED = frozenset({3, 4, 6, 11, 12})

    @staticmethod
    def _campaign():
        import re
        return [p for p in sorted(glob.glob(str(MAPS / "*.MAP")))
                if re.match(r"^E[1-46]M[1-9]$", Path(p).stem.upper())]

    def test_the_campaign_never_omits_one(self):
        """15,071 of 15,071 -- but unanimity is not the same as necessity."""
        from bloodmap.format import read_map

        total = missing = 0
        for path in self._campaign():
            disk = read_map(path)
            for sprite in disk.sprites:
                if int(sprite.fields["status"]) in self.REQUIRED:
                    total += 1
                    if sprite.extra is None:
                        missing += 1
        self.assertGreater(total, 15000)
        self.assertEqual(missing, 0)

    def test_only_a_dude_actually_crashes(self):
        """The severities have to follow the engine, not the corpus.

        `aiInitSprite` dereferences xsprite[extra] unguarded for dudes, so that
        one is an error. `actInit` skips items and guards things and traps, and
        `ambInit` guards ambience -- and the Death Wish add-on ships playable
        maps whose type-710 sprites have no XSprite, which is why treating the
        campaign's unanimity as a hard rule rejected working maps.
        """
        from bloodmap.analysis import (
            XSPRITE_CRASHES_WITHOUT, XSPRITE_EXPECTED_STATNUMS)

        self.assertEqual(XSPRITE_CRASHES_WITHOUT, frozenset({6}))
        self.assertEqual(
            XSPRITE_CRASHES_WITHOUT | XSPRITE_EXPECTED_STATNUMS, self.REQUIRED)

    def test_the_validator_now_catches_it(self):
        from bloodmap.analysis import validate_map
        from bloodmap.format import read_map

        disk = read_map(self._campaign()[0])
        self.assertEqual(
            [d for d in validate_map(disk) if d.code == "sprite-missing-xsprite"], [])
        # Strip one dude's XSprite and the validator must object.
        for sprite in disk.sprites:
            if int(sprite.fields["status"]) == 6:
                sprite.extra = None
                sprite.fields["extra"] = -1
                break
        found = [d for d in validate_map(disk) if d.code == "sprite-missing-xsprite"]
        self.assertEqual(len(found), 1)
        self.assertEqual(found[0].severity, "error")

    def test_an_omitted_ambient_xsprite_is_only_a_warning(self):
        """Shipping add-on maps do this and play, so it must not reject them."""
        from bloodmap.analysis import validate_map
        from bloodmap.format import read_map

        disk = read_map(self._campaign()[0])
        for sprite in disk.sprites:
            if int(sprite.fields["status"]) == 12:
                sprite.extra = None
                sprite.fields["extra"] = -1
                break
        found = [d for d in validate_map(disk) if d.code == "sprite-xsprite-omitted"]
        self.assertEqual(len(found), 1)
        self.assertEqual(found[0].severity, "warning")
        self.assertFalse([d for d in validate_map(disk) if d.severity == "error"])

    def test_the_compiler_supplies_one_without_being_asked(self):
        """A dude placed with no behaviour still gets an XSprite.

        `if placement.behavior:` treated an empty dict as "no XSprite wanted",
        which is the line that shipped the crash.
        """
        from bloodmap.planar_layout import XSPRITE_REQUIRED_STATNUMS

        self.assertEqual(XSPRITE_REQUIRED_STATNUMS, self.REQUIRED)


class TopologyGraphTests(unittest.TestCase):
    """Topology counts the graph the player walks, not the one the walls make."""

    def test_a_water_link_closes_a_loop_the_wall_graph_cannot_see(self):
        from bloodmap.level_profile import _topology

        class FakeSector:
            def __init__(self, extra=None):
                self.fields = {"wall_ptr": 0, "wall_count": 0}
                self.extra = extra

        # Two chains joined only by a dive would read as a tree on walls alone.
        import bloodmap.level_profile as module

        playable = {0, 1, 2, 3}
        walked = {0: {1, 3}, 1: {0, 2}, 2: {1, 3}, 3: {2, 0}}

        class FakeReach:
            graph = walked

        original = module.analyze_reachability
        module.analyze_reachability = lambda disk: FakeReach()
        try:
            result = _topology(None, playable)
        finally:
            module.analyze_reachability = original
        self.assertEqual(result["independent_loops"], 1)
        self.assertEqual(result["dead_end_fraction"], 0.0)


if __name__ == "__main__":
    unittest.main()
