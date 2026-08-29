from __future__ import annotations

import unittest

from bloodmap import layers
from bloodmap.planar_layout import PlanarLayout, PlanarLayoutError

STANDING = layers.STANDING_HEIGHT

#: BB4's own bands, which the fragment adopts. See
#: projects/vertical-fragment/design/layer-conditions.md.
UNDERCROFT = dict(ceiling_z=16384, floor_z=49152)
STREET = dict(ceiling_z=-24576, floor_z=8192)
UPPER = dict(ceiling_z=-65536, floor_z=-32768)


def rect(x0: int, y0: int, x1: int, y1: int) -> list[tuple[int, int]]:
    return [(x0, y0), (x1, y0), (x1, y1), (x0, y1)]


def three_layers() -> PlanarLayout:
    """A street, a cellar under part of it, and a floor over part of it.

    Deliberately unjoined, so the conditions are exercised on geometry alone.
    `connected_stack` is the one that has to survive a compile.
    """
    layout = PlanarLayout(name="stack")
    layout.declare_layer("undercroft", **UNDERCROFT)
    layout.declare_layer("street", **STREET)
    layout.declare_layer("upper", **UPPER)
    layout.add_region("street:road", rect(0, 0, 16384, 8192), layer="street", **STREET)
    layout.add_region("undercroft:cellar", rect(2048, 2048, 8192, 6144),
                      layer="undercroft", **UNDERCROFT)
    layout.add_region("upper:floor", rect(10240, 2048, 14336, 6144),
                      layer="upper", **UPPER)
    layout.set_player_start("street:road", x=1024, y=1024, z=STREET["floor_z"])
    return layout


def connected_stack() -> PlanarLayout:
    """A road, a stair down off its south edge, and a cellar under the road.

    The stair is the only place the two layers meet, which is what a declared
    join is for. It spans both bands because the thing joining two layers has to.
    """
    layout = PlanarLayout(name="connected")
    layout.declare_layer("undercroft", **UNDERCROFT)
    layout.declare_layer("street", **STREET)
    layout.add_region("street:road", rect(0, 0, 16384, 8192), layer="street", **STREET)
    layout.add_region("undercroft:stair", rect(4096, 8192, 8192, 12288),
                      layer="undercroft",
                      ceiling_z=STREET["ceiling_z"], floor_z=UNDERCROFT["floor_z"])
    layout.add_region("undercroft:cellar", rect(8192, 2048, 16384, 12288),
                      layer="undercroft", **UNDERCROFT)
    layout.add_connection("down", "street:road", "undercroft:stair",
                          a1=(4096, 8192), a2=(8192, 8192))
    layout.add_connection("in", "undercroft:stair", "undercroft:cellar",
                          a1=(8192, 8192), a2=(8192, 12288))
    layout.set_player_start("street:road", x=1024, y=1024, z=STREET["floor_z"])
    return layout


class LayerDeclarationTests(unittest.TestCase):
    def test_a_band_needs_its_ceiling_above_its_floor(self):
        layout = PlanarLayout(name="upside down")
        with self.assertRaises(layers.LayerError) as caught:
            layout.declare_layer("street", ceiling_z=8192, floor_z=-24576)
        self.assertIn("z points down", str(caught.exception))

    def test_a_layer_cannot_be_declared_twice(self):
        layout = PlanarLayout(name="twice")
        layout.declare_layer("street", **STREET)
        with self.assertRaises(layers.LayerError):
            layout.declare_layer("street", **STREET)

    def test_a_layout_that_declares_nothing_is_unchanged(self):
        layout = PlanarLayout(name="flat")
        layout.add_region("a", rect(0, 0, 4096, 4096))
        layout.add_region("b", rect(8192, 0, 12288, 4096))
        self.assertEqual(layers.layers_of(layout), {})
        self.assertFalse(layout.separate_arrangements("a", "b"))
        self.assertEqual(layers.check(layout), [])


class OverlapConditionTests(unittest.TestCase):
    def test_layers_may_overlap_in_plan_when_their_bands_are_disjoint(self):
        layout = three_layers()
        found = layers.find_overlaps(layout)
        self.assertEqual(len(found), 2)
        for overlap in found:
            self.assertTrue(overlap.safe, overlap.to_dict())
            self.assertIn("bands", overlap.movement_resolved_by)
        self.assertEqual(layers.check(layout), [])

    def test_a_layer_overlapping_itself_is_refused(self):
        layout = three_layers()
        layout.add_region("street:island", rect(3072, 3072, 5120, 5120),
                          layer="street", **STREET)
        codes = {finding.code for finding in layers.check(layout)}
        self.assertIn("layer-overlap-within", codes)

    def test_two_layers_at_the_same_height_may_not_share_ground(self):
        layout = PlanarLayout(name="same height")
        layout.declare_layer("street", **STREET)
        layout.declare_layer("gallery", **STREET)
        layout.add_region("street:road", rect(0, 0, 16384, 8192), layer="street", **STREET)
        layout.add_region("gallery:walk", rect(2048, 2048, 8192, 6144),
                          layer="gallery", **STREET)
        layout.set_player_start("street:road", x=1024, y=1024, z=STREET["floor_z"])
        findings = [f for f in layers.check(layout) if f.code == "layer-bands-intersect"]
        self.assertEqual(len(findings), 1)
        self.assertEqual(findings[0].severity, "error")

    def test_a_region_may_not_leave_its_layer_band(self):
        layout = three_layers()
        layout.regions["street:road"].ceiling_z = -40960
        codes = {f.code for f in layers.check(layout)}
        self.assertIn("layer-band-escape", codes)

    def test_a_region_in_an_undeclared_layer_is_refused(self):
        layout = three_layers()
        layout.add_region("roof:leads", rect(0, 16384, 4096, 20480), layer="roof",
                          ceiling_z=-106496, floor_z=-73728)
        codes = {f.code for f in layers.check(layout)}
        self.assertIn("layer-undeclared", codes)

    def test_a_transposable_overlap_is_noted_rather_than_refused(self):
        """Bands alone resolve it, and the clip list does not read bands.

        `a` and `c` share ground, sit two portal hops apart through `b`, and the
        whole walk fits inside one mover's clip box -- so `clipmove_compat` can
        hold both and has only the plan to choose by.
        """
        layout = PlanarLayout(name="transposable")
        layout.declare_layer("street", **STREET)
        layout.declare_layer("upper", **UPPER)
        layout.add_region("street:a", rect(0, 0, 2048, 2048), layer="street", **STREET)
        layout.add_region("street:b", rect(2048, 0, 4096, 2048), layer="street", **STREET)
        layout.add_region("upper:c", rect(1024, 512, 3072, 1536), layer="upper", **UPPER)
        layout.add_connection("ab", "street:a", "street:b",
                              a1=(2048, 0), a2=(2048, 2048))
        layout.add_connection("bc", "street:b", "upper:c",
                              a1=(3072, 512), a2=(3072, 1536))
        layout.set_player_start("street:b", x=3800, y=1900, z=STREET["floor_z"])
        findings = layers.check(layout)
        close = [f for f in findings if f.code == "layer-overlap-close"]
        # `c` hangs over both rooms below it, so both pairs are transposable.
        self.assertEqual([f.severity for f in close], ["note", "note"])
        self.assertNotIn("error", [f.severity for f in findings])
        self.assertIn("does not read them", close[0].message)

    def test_a_stair_between_two_storeys_is_not_a_confusion(self):
        """The case a hop count gets wrong, and the reason it was replaced.

        The road and the cellar share ground and are only two portal hops apart,
        but the stair between them stands outside the clip box either of them
        would fix, so no mover can hold both.
        """
        layout = connected_stack()
        overlap = layers.find_overlaps(layout)[0]
        self.assertEqual(overlap.hops, 2)
        self.assertFalse(overlap.one_clip_list)
        self.assertTrue(overlap.separated)
        # No movement finding: the mover cannot be transposed. The road and the
        # cellar do still share a boundary line -- the stair's own wall runs
        # along both -- and that is the renderer's separate complaint.
        codes = [f.code for f in layers.check(layout)]
        self.assertEqual(sorted(codes),
                         ["layer-unorderable-walls", "layer-walls-coincide"])
        # Two ways of saying the same thing about the same two walls, and both
        # notes: `layer-walls-coincide` finds the shared boundary geometrically,
        # `layer-unorderable-walls` gets there through the engine's own
        # predicate. Neither refuses the build, because the campaign does this
        # in 91% of its overlapping pairs.

    def test_a_connector_may_span_the_bands_it_joins(self):
        layout = connected_stack()
        self.assertEqual(
            layers.permitted_band(layout, "undercroft:stair"),
            (STREET["ceiling_z"], UNDERCROFT["floor_z"]))
        self.assertEqual(
            layers.permitted_band(layout, "undercroft:cellar"),
            (UNDERCROFT["ceiling_z"], UNDERCROFT["floor_z"]))
        self.assertNotIn("layer-band-escape", {f.code for f in layers.check(layout)})

    def test_a_region_that_joins_nothing_may_not_span(self):
        layout = connected_stack()
        layout.regions["undercroft:cellar"].ceiling_z = STREET["ceiling_z"]
        codes = {f.code for f in layers.check(layout)}
        self.assertIn("layer-band-escape", codes)

    def test_a_declared_stack_is_its_own_contract(self):
        layout = three_layers()
        layout.declare_special("street:road", "undercroft:cellar", "stack")
        found = layers.find_overlaps(layout)
        declared = [o for o in found if o.declared == "stack"]
        self.assertEqual(len(declared), 1)
        self.assertEqual(layers.check(layout), [])


class DeclaredOwnerTests(unittest.TestCase):
    def test_a_player_start_over_an_overlap_is_refused(self):
        layout = three_layers()
        layout.set_player_start("street:road", x=4096, y=4096, z=STREET["floor_z"])
        findings = [f for f in layers.check(layout)
                    if f.code == "layer-owner-over-overlap"]
        self.assertEqual(len(findings), 1)
        self.assertEqual(findings[0].severity, "error")
        self.assertIn("reads this sprite's sector off the map", findings[0].message)

    def test_a_start_clear_of_every_overlap_is_accepted(self):
        layout = three_layers()
        self.assertEqual([f for f in layers.check(layout)
                          if f.code == "layer-owner-over-overlap"], [])


class SpatialQueryTests(unittest.TestCase):
    def test_column_at_reports_the_stack_top_first_with_the_air_between(self):
        layout = three_layers()
        column = layers.column_at(layout, 4096, 4096)
        self.assertEqual([slab.region_id for slab in column],
                         ["street:road", "undercroft:cellar"])
        self.assertIsNone(column[0].air_above)
        # BB4's slab: half a body of masonry between the two.
        self.assertEqual(column[1].air_above, 8192)

    def test_column_at_is_empty_off_the_plan(self):
        self.assertEqual(layers.column_at(three_layers(), -9999, -9999), [])

    def test_can_see_is_blocked_by_a_wall_between(self):
        layout = PlanarLayout(name="sight")
        layout.declare_layer("street", **STREET)
        layout.add_region("street:a", rect(0, 0, 4096, 4096), layer="street", **STREET)
        layout.add_region("street:b", rect(8192, 0, 12288, 4096), layer="street", **STREET)
        layout.set_player_start("street:a", x=1024, y=1024, z=STREET["floor_z"])
        self.assertFalse(layers.can_see(layout, "street:a", "street:b"))

    def test_can_see_is_open_along_a_shared_edge(self):
        layout = PlanarLayout(name="open")
        layout.declare_layer("street", **STREET)
        layout.add_region("street:a", rect(0, 0, 4096, 4096), layer="street", **STREET)
        layout.add_region("street:b", rect(4096, 0, 8192, 4096), layer="street", **STREET)
        layout.set_player_start("street:a", x=1024, y=1024, z=STREET["floor_z"])
        self.assertTrue(layers.can_see(layout, "street:a", "street:b"))


class FallTests(unittest.TestCase):
    """Blood's own arithmetic, not a guess. See actor.cpp:4595, 4628, 4835."""

    def test_one_storey_of_bb4s_grammar_is_painless(self):
        layout = three_layers()
        drop = layers.drop_between(layout, "street:road", "undercroft:cellar")
        self.assertEqual(drop.distance, 40960)
        self.assertAlmostEqual(drop.bodies, 2.42, places=2)
        self.assertTrue(drop.painless)

    def test_the_painless_limit_sits_between_these_two_drops(self):
        self.assertEqual(layers.fall_cost(62564)[0], 0.0)
        self.assertGreater(layers.fall_cost(68025)[0], 0.0)

    def test_seven_and_a_half_bodies_kills_from_full_health(self):
        damage, _ticks = layers.fall_cost(127411)
        self.assertGreaterEqual(damage, 100.0)

    def test_climbing_is_not_a_drop(self):
        layout = three_layers()
        with self.assertRaises(layers.LayerError):
            layers.drop_between(layout, "undercroft:cellar", "street:road")


class CompilerIntegrationTests(unittest.TestCase):
    def test_compile_refuses_a_layout_whose_layers_do_not_separate(self):
        layout = PlanarLayout(name="bad")
        layout.declare_layer("street", **STREET)
        layout.declare_layer("gallery", **STREET)
        layout.add_region("street:road", rect(0, 0, 16384, 8192), layer="street", **STREET)
        layout.add_region("gallery:walk", rect(2048, 2048, 8192, 6144),
                          layer="gallery", **STREET)
        layout.set_player_start("street:road", x=1024, y=1024, z=STREET["floor_z"])
        with self.assertRaises(layers.LayerError) as caught:
            layout.compile()
        self.assertIn("layer-bands-intersect", str(caught.exception))

    def test_an_undeclared_overlap_is_still_refused_without_layers(self):
        """The old rule is untouched where no layer says otherwise."""
        layout = PlanarLayout(name="flat")
        layout.add_region("a", rect(0, 0, 16384, 8192))
        layout.add_region("b", rect(2048, 2048, 8192, 6144))
        layout.set_player_start("a", x=1024, y=1024, z=8192)
        with self.assertRaises(PlanarLayoutError) as caught:
            layout.compile()
        self.assertIn("without a declared special relationship", str(caught.exception))

    def test_stacked_layers_compile_to_a_map(self):
        compiled = connected_stack().compile()
        self.assertEqual(len(compiled.level.sectors), 3)
        report = layers.report(connected_stack())
        self.assertEqual(len(report["layers"]), 2)
        self.assertEqual(len(report["overlaps"]), 1)
        self.assertEqual(set(f["severity"] for f in report["findings"]), {"note"})

    def test_the_cellar_really_does_sit_under_the_road(self):
        """The overlap survives compilation instead of being split away."""
        layout = connected_stack()
        column = layers.column_at(layout, 12288, 4096)
        self.assertEqual([slab.region_id for slab in column],
                         ["street:road", "undercroft:cellar"])
        self.assertEqual(column[1].air_above, 8192)
        compiled = layout.compile()
        # Three regions in, three sectors out: nothing was split by the layer
        # it happens to sit over.
        self.assertEqual(len(compiled.level.sectors), 3)


if __name__ == "__main__":
    unittest.main()


class RoomOverRoomTests(unittest.TestCase):
    """The link has to survive `dbLoadMap`, not merely be written to the file."""

    def test_a_link_marker_lives_on_the_decoration_list(self):
        from bloodmap import roomoverroom

        # `PropagateMarkerReferences` (db.cpp:681) deletes every sprite on
        # statnum 10 that is not an Off/On/Axis/WarpDest marker, and it runs
        # inside `dbLoadMap` -- before `warpInit` can pair anything. A link
        # marker put there is gone before the engine looks for it, and the map
        # file gives no sign: the mirror tiles are still on both surfaces and
        # the floor is simply solid.
        self.assertEqual(roomoverroom.MARKER_STATNUM, 0)
        self.assertNotEqual(roomoverroom.MARKER_STATNUM, 10)

    def test_the_two_markers_wear_the_campaign_tiles(self):
        from bloodmap import roomoverroom

        self.assertEqual(roomoverroom.MARKER_TILE_UPPER, 2332)
        self.assertEqual(roomoverroom.MARKER_TILE_LOWER, 2331)

    def test_a_stack_pair_emits_two_paired_markers(self):
        from bloodmap import roomoverroom

        layout = PlanarLayout(name="ror")
        layout.declare_layer("street", **STREET)
        layout.declare_layer("undercroft", **UNDERCROFT)
        layout.add_region("street:hatch", rect(0, 0, 2048, 2048),
                          layer="street", **STREET)
        layout.add_region("undercroft:below", rect(0, 0, 2048, 2048),
                          layer="undercroft", **UNDERCROFT)
        built = roomoverroom.room_over_room(
            layout, "hatch", "street:hatch", "undercroft:below",
            link_id=1, at=(1024, 1024), family="stack")
        layout.set_player_start("street:hatch", x=200, y=200, z=STREET["floor_z"])

        self.assertEqual(built["family"], "stack")
        markers = [p for p in layout.placements
                   if p.placement_id in built["markers"].values()]
        self.assertEqual(len(markers), 2)
        for marker in markers:
            self.assertEqual(int(marker.status), 0)
            self.assertEqual(marker.behavior["data_1"], 1)
        self.assertEqual({int(m.picnum) for m in markers}, {2331, 2332})
        # The lower room's ceiling becomes the upper room's floor, so the
        # crossing has no step in it.
        self.assertEqual(layout.regions["undercroft:below"].ceiling_z,
                         layout.regions["street:hatch"].floor_z)
        self.assertEqual(layout.regions["street:hatch"].floor_picnum,
                         roomoverroom.MIRROR_TILE)
        self.assertEqual(layout.regions["undercroft:below"].ceiling_picnum,
                         roomoverroom.MIRROR_TILE)
        # A declared stack is its own contract; the layer conditions leave it be.
        self.assertEqual(layers.check(layout), [])


class SightConditionTests(unittest.TestCase):
    """The condition that sat inert, and the case that proves it runs.

    `_shared_sight_findings` used to filter to pairs that were *not*
    `separated` -- a movement property built from `clipmove_compat`'s clip box.
    MALTX had sixty-nine overlapping pairs and no z-clash, so every pair was
    separated, the list came back empty, and the sight condition examined
    exactly zero pairs while the fragment shipped a visible tear.

    Movement and rendering are different questions. `wallfront`
    (build/src/engine.cpp:2227) takes two walls' x/y and the viewer's x/y and has
    no z in it, so disjoint bands cannot help it order anything; and the
    renderer's flood is gated by `testvisiblemost` on per-column occlusion, which
    has never heard of a clip box.
    """

    def _far_apart_but_visible(self) -> PlanarLayout:
        layout = PlanarLayout(name="inert")
        layout.declare_layer("street", **STREET)
        layout.declare_layer("upper", **UPPER)
        layout.add_region("street:hall", rect(0, 0, 8192, 8192),
                          layer="street", **STREET)
        layout.add_region("street:porch", rect(8192, 0, 12288, 8192),
                          layer="street", **STREET)
        layout.add_region("street:stair", rect(12288, 0, 16384, 8192),
                          layer="street", **STREET)
        # Hangs over the hall, and reached only the long way round.
        layout.add_region("upper:gallery", rect(4096, 2048, 14336, 6144),
                          layer="upper", **UPPER)
        layout.add_connection("a", "street:hall", "street:porch",
                              a1=(8192, 0), a2=(8192, 8192))
        layout.add_connection("b", "street:porch", "street:stair",
                              a1=(12288, 0), a2=(12288, 8192))
        layout.add_connection("c", "street:stair", "upper:gallery",
                              a1=(14336, 2048), a2=(14336, 6144))
        layout.set_player_start("street:porch", x=10240, y=7000,
                                z=STREET["floor_z"])
        return layout

    def test_a_band_separated_overlap_is_still_asked_about_sight(self):
        layout = self._far_apart_but_visible()
        overlap = next(o for o in layers.find_overlaps(layout)
                       if not o.declared and "gallery" in o.right + o.left)
        # Exactly the shape the old filter threw away: bands disjoint, and the
        # engine can tell them apart by where the player is.
        self.assertTrue(overlap.bands_disjoint)
        self.assertTrue(overlap.separated)
        self.assertIn("bands", overlap.movement_resolved_by)

        codes = [f.code for f in layers.check(layout)]
        self.assertIn("layer-overlap-in-one-view", codes)

    def test_a_condition_that_examined_nothing_is_reported(self):
        """Silence and success have to look different in the report."""
        report = layers.report(self._far_apart_but_visible())
        sight = report["conditions"]["layer-overlap-in-one-view"]
        self.assertGreater(sight["examined"], 0)
        self.assertFalse(sight["inert"])
        self.assertGreaterEqual(sight["failed"], 1)
        self.assertIn("wallfront", report["draw_order_rule"])
        self.assertNotEqual(report["rule"], report["draw_order_rule"])

    def test_movement_resolution_does_not_claim_to_settle_rendering(self):
        """`resolved_by` used to read as though either half settled the pair."""
        overlap = next(o for o in layers.find_overlaps(self._far_apart_but_visible())
                       if not o.declared and "gallery" in o.right + o.left)
        self.assertTrue(overlap.safe_to_move_through)
        self.assertFalse(hasattr(overlap, "resolved_by"))

    def test_only_a_proof_of_no_shared_flood_may_skip_the_sight_check(self):
        """Nothing else: not distance, not bands, not a hop count."""
        layout = PlanarLayout(name="sealed")
        layout.declare_layer("street", **STREET)
        layout.declare_layer("undercroft", **UNDERCROFT)
        layout.add_region("street:road", rect(0, 0, 16384, 8192),
                          layer="street", **STREET)
        layout.add_region("undercroft:cellar", rect(2048, 2048, 8192, 6144),
                          layer="undercroft", **UNDERCROFT)
        layout.set_player_start("street:road", x=15000, y=7000, z=STREET["floor_z"])
        # Nothing joins the cellar, so no flood reaches it from anywhere.
        self.assertIsNone(layers.covisible(layout, "street:road",
                                           "undercroft:cellar"))
        self.assertNotIn("layer-overlap-in-one-view",
                         [f.code for f in layers.check(layout)])


class ViewCutTests(unittest.TestCase):
    """A one-way wall can silence an overlap-in-one-view warning from one side.

    It is not a fix for collinear same-height neighbours -- `wallfront`
    (engine.cpp:2227) still returns -1 for those -- and it cannot resolve a
    symmetric co-visibility problem, because the flag lives on one wall and
    `scansector` skips the portal from that side only (engine.c:3134). Bit 5
    does not stop the player; CLIPMASK0 is bits 0 and 16 (build.h:225).
    """

    def _overlooked(self, **cut) -> PlanarLayout:
        """A yard, a shed off it, and the shed's own roof reaching the yard too.

        The roof is a tongue: it meets the yard along one stretch of the yard's
        south edge and the shed meets it along the two either side, so the pair
        is a plan overlap and not a set of coincident walls. That is the store
        and its leads, reduced to the smallest thing that still fails.
        """
        layout = PlanarLayout(name="cut")
        layout.declare_layer("street", **STREET)
        layout.declare_layer("upper", **UPPER)
        # The yard is open to the sky, so its own band spans both storeys --
        # which is the only reason a sightline in it can reach either.
        layout.add_region("street:yard", rect(0, 0, 12288, 4096), layer="street",
                          floor_z=STREET["floor_z"], ceiling_z=UPPER["ceiling_z"])
        # The shed stands back from the yard along the stretch the roof comes
        # forward on, so no wall of one lies along a wall of the other: the two
        # are a plan overlap and nothing else, which is the case condition C is
        # for. The roof's near half is over open air, which is why the yard has
        # a plan sightline into it at all.
        layout.add_region("street:shed", [
            (0, 4096), (6144, 4096), (6144, 6656), (12288, 6656),
            (12288, 10240), (0, 10240)], layer="street", **STREET)
        layout.add_region("upper:roof", rect(6400, 4096, 11264, 8192),
                          layer="upper", **UPPER)
        layout.add_connection("into_shed", "street:yard", "street:shed",
                              a1=(0, 4096), a2=(6144, 4096))
        layout.add_connection("onto_roof", "street:yard", "upper:roof",
                              a1=(6400, 4096), a2=(11264, 4096), **cut)
        layout.set_player_start("street:yard", x=1024, y=2048,
                                z=STREET["floor_z"])
        return layout

    def test_without_the_cut_the_pair_is_seen_from_the_yard(self):
        layout = self._overlooked()
        self.assertEqual(layers.covisible(layout, "street:shed", "upper:roof"),
                         "street:yard")

    def test_a_declared_opening_is_not_an_occluder_from_either_side(self):
        """`solid_edges` used to cancel only same-layer neighbours.

        A cross-layer join had the lower region's edge cancelled and the upper
        region's left standing, so `can_see` called a real opening masonry from
        one side. Condition C then stayed silent on a pair it should have named.
        """
        layout = self._overlooked()
        walls = layers.solid_edges(layout)
        self.assertTrue(layers.can_see(layout, "street:yard", "upper:roof",
                                       occluders=walls))
        self.assertTrue(layers.can_see(layout, "upper:roof", "street:yard",
                                       occluders=walls))
        # The join stored against the upper room's winding must still cancel
        # the yard's reverse-coincident edge. Dropping one side is how
        # `can_see` treated a real opening as masonry.
        reversed_join = PlanarLayout(name="reversed")
        reversed_join.declare_layer("street", **STREET)
        reversed_join.declare_layer("upper", **UPPER)
        reversed_join.add_region("street:a", rect(0, 0, 4096, 4096),
                                 layer="street", **STREET)
        reversed_join.add_region("upper:b", rect(0, 4096, 4096, 8192),
                                 layer="upper", **UPPER)
        reversed_join.add_connection("portal", "street:a", "upper:b",
                                     a1=(4096, 4096), a2=(0, 4096))
        rev_walls = layers.solid_edges(reversed_join)
        self.assertTrue(layers.can_see(reversed_join, "street:a", "upper:b",
                                       occluders=rev_walls))
        self.assertTrue(layers.can_see(reversed_join, "upper:b", "street:a",
                                       occluders=rev_walls))
        self.assertIn("layer-overlap-in-one-view",
                      [f.code for f in layers.check(layout)])

    def test_with_the_cut_the_yard_is_no_longer_a_vantage(self):
        """The proof condition C and `layer-walls-coincide` are both gated on."""
        layout = self._overlooked(view_cut_from="left")
        self.assertNotEqual(layers.covisible(layout, "street:shed", "upper:roof"),
                            "street:yard")

    def test_the_cut_is_read_in_the_direction_it_was_declared(self):
        layout = self._overlooked(view_cut_from="left")
        self.assertEqual(layers.view_cuts(layout),
                         {("street:yard", "upper:roof")})
        # From the yard the roof is no longer collected...
        self.assertNotIn("upper:roof", layers.sight_reach(layout, "street:yard"))
        # ...but from the roof the yard still is. The flag lives on one wall.
        self.assertIn("street:yard", layers.sight_reach(layout, "upper:roof"))

    def test_a_cut_naming_neither_region_is_refused(self):
        layout = self._overlooked(view_cut_from="street:nowhere")
        with self.assertRaises(Exception) as caught:
            layout.compile()
        self.assertIn("neither of its regions", str(caught.exception))

    def test_the_cut_writes_bit_five_on_one_wall_only(self):
        """And dresses it, because engine.c:3157 draws it from over_picnum."""
        layout = self._overlooked(view_cut_from="left")
        disk = layout.compile().level.to_disk_map()
        flagged = [w for w in disk.walls if int(w.fields["cstat"]) & 32]
        self.assertEqual(len(flagged), 1)
        wall = flagged[0]
        self.assertGreaterEqual(int(wall.fields["next_sector"]), 0,
                                "the wall must stay two-sided or nothing crosses it")
        self.assertTrue(int(wall.fields["over_picnum"]),
                        "a one-way wall with no over_picnum draws tile 0")
        # Masked would buy nothing: engine.c:2920 takes a wall into the masked
        # list only when cstat&48 is exactly 16, and 68% of the campaign's
        # one-way walls leave the bit clear.
        self.assertFalse(int(wall.fields["cstat"]) & 16)

    def test_movement_across_the_cut_is_untouched(self):
        """clipmove tests CLIPMASK0 -- bits 0 and 16 (build.h:225) -- not bit 5.

        Bit 5 alone therefore does not stop the player (clip.cpp:1626, :1913).
        This test asserts we did not also set bit 0, which *is* in that mask.
        """
        layout = self._overlooked(view_cut_from="left")
        disk = layout.compile().level.to_disk_map()
        wall = next(w for w in disk.walls if int(w.fields["cstat"]) & 32)
        self.assertFalse(int(wall.fields["cstat"]) & 1)


class StackedStoreyTests(unittest.TestCase):
    """The fault the fragment actually had, and the two detector bugs that hid it.

    A second storey on the ground floor's own footprint, with a way into each
    from the same yard. The renderer's sort is 2D and cannot rank the two, so
    whichever is enumerated first takes the columns and the other's opening goes
    black. Blood never ships this: across BB4, E1M1, E3M1 and E4M2, every pair on
    one footprint is either near-coplanar -- floors 0 to 5,120 apart, a step --
    or a room-over-room link, and in 658 views holding such a pair the sort
    failed to order it exactly zero times.
    """

    def _two_storeys(self, upper: list[tuple[int, int]] | None = None,
                     upper_door: bool = True) -> PlanarLayout:
        layout = PlanarLayout(name="storeys")
        layout.declare_layer("street", **STREET)
        layout.declare_layer("upper", **UPPER)
        layout.add_region("street:yard", rect(0, 8192, 12288, 14336), layer="street",
                          floor_z=STREET["floor_z"], ceiling_z=UPPER["ceiling_z"])
        layout.add_region("street:floor", rect(2048, 0, 10240, 7680),
                          layer="street", **STREET)
        layout.add_region("upper:loft", upper or rect(2048, 0, 10240, 7680),
                          layer="upper", **UPPER)
        # The way in at street level.
        layout.add_region("street:door", rect(3072, 7680, 4096, 8192),
                          layer="street", **STREET)
        layout.add_connection("in", "street:yard", "street:door",
                              a1=(3072, 8192), a2=(4096, 8192))
        layout.add_connection("through", "street:door", "street:floor",
                              a1=(3072, 7680), a2=(4096, 7680))
        if upper_door:
            # ...and a loading door into the storey above, off the same yard.
            layout.add_region("upper:hoist", rect(7168, 7680, 8192, 8192),
                              layer="upper", **UPPER)
            layout.add_connection("hoist_out", "street:yard", "upper:hoist",
                                  a1=(7168, 8192), a2=(8192, 8192))
            layout.add_connection("hoist_in", "upper:hoist", "upper:loft",
                                  a1=(7168, 7680), a2=(8192, 7680))
        layout.set_player_start("street:yard", x=6144, y=12288, z=STREET["floor_z"])
        return layout

    def _codes(self, layout) -> list[str]:
        return [f.code for f in layers.check(layout)]

    def test_a_storey_on_the_same_footprint_seen_from_the_yard_is_an_error(self):
        layout = self._two_storeys()
        findings = [f for f in layers.check(layout)
                    if f.code == "layer-stacked-and-seen-together"]
        self.assertEqual(len(findings), 1, self._codes(layout))
        self.assertEqual(findings[0].severity, "error")
        self.assertIn("street:yard", findings[0].message)

    def test_setting_the_upper_storey_in_is_a_different_condition(self):
        """Inset and flush are the only two options for an envelope.

        Flush, the walls are coincident and the sort cannot rank them -- that is
        this condition. Set in, they are parallel and it can, but every wall of
        the loft now stands inside the floor's plan, retiring that column whole
        (engine.c:3216) and stopping the recursion behind it (engine.c:3156).
        The evidence for an *error* covers only the flush case, so the inset one
        is left to `layer-overlap-in-one-view`, which is graded a warning.
        """
        layout = self._two_storeys(upper=rect(2304, 256, 9984, 7424),
                                   upper_door=False)
        layout.add_region("upper:hoist", rect(7168, 7424, 8192, 8192),
                          layer="upper", **UPPER)
        layout.add_connection("hoist_out", "street:yard", "upper:hoist",
                              a1=(7168, 8192), a2=(8192, 8192))
        layout.add_connection("hoist_in", "upper:hoist", "upper:loft",
                              a1=(7168, 7424), a2=(8192, 7424))
        codes = self._codes(layout)
        self.assertNotIn("layer-stacked-and-seen-together", codes)
        self.assertIn("layer-overlap-in-one-view", codes)

    def test_separate_ways_in_clear_it(self):
        """The fix is architectural: the loft is reached by its own stair."""
        layout = self._two_storeys(upper_door=False)
        self.assertNotIn("layer-stacked-and-seen-together", self._codes(layout))

    def test_a_side_porch_is_not_the_same_facade(self):
        """BB4's pattern: both storeys open to the yard, on perpendicular walls.

        The tear is one vertical sightline through two openings on one wall.
        A porch on the east of the yard is a different line, so `wallfront`
        can rank the pair and the frame does not hole.
        """
        layout = self._two_storeys(upper_door=False)
        # East side of the yard, x=12288, y=8192..12288 in the fixture.
        layout.add_region("upper:porch", rect(12288, 9216, 13312, 11264),
                          layer="upper", **UPPER)
        layout.add_connection("porch_out", "street:yard", "upper:porch",
                              a1=(12288, 9216), a2=(12288, 11264))
        layout.add_region("upper:side_door", rect(10240, 10240, 12288, 11264),
                          layer="upper", **UPPER)
        layout.add_connection("porch_along", "upper:porch", "upper:side_door",
                              a1=(12288, 10240), a2=(12288, 11264))
        layout.add_connection("side_in", "upper:side_door", "upper:loft",
                              a1=(10240, 10240), a2=(10240, 11264))
        self.assertNotIn("layer-stacked-and-seen-together", self._codes(layout))

    def test_a_step_between_two_rooms_is_not_a_storey(self):
        """Blood's own same-footprint pairs are 0 to 5,120 apart. That is fine."""
        layout = self._two_storeys()
        layout.regions["upper:loft"].floor_z = STREET["floor_z"] - 4096
        layout.regions["upper:loft"].ceiling_z = STREET["ceiling_z"] - 4096
        self.assertNotIn("layer-stacked-and-seen-together", self._codes(layout))

    def test_the_pair_is_detected_at_all(self):
        """Both halves of the detector bug that hid this for the whole session.

        `loops_equivalent` wants matching vertex lists, and two storeys never
        have those -- each has its own doorways splitting its own walls. The pair
        then fell through to `polygon_relation`, which calls it
        `exactly_shared_boundary`, which was not in `OVERLAPPING_KINDS`. Blood's
        normal way of stacking space was invisible to every check built on it.
        """
        layout = self._two_storeys()
        kinds = {(o.left, o.right): o.kind for o in layers.find_overlaps(layout)}
        self.assertIn(("street:floor", "upper:loft"), kinds)
        # And the same footprint cut up differently is still the same footprint.
        subdivided = [(2048, 0), (6144, 0), (10240, 0), (10240, 7680),
                      (7168, 7680), (2048, 7680)]
        layout2 = self._two_storeys(upper=subdivided)
        kinds2 = {(o.left, o.right) for o in layers.find_overlaps(layout2)}
        self.assertIn(("street:floor", "upper:loft"), kinds2)

    def test_a_sector_filling_a_hole_is_not_shared_ground(self):
        """`exactly_shared_boundary` is also true of a cut-out, which is not one."""
        from bloodmap.planar_geom import same_ground
        square = rect(0, 0, 4096, 4096)
        subdivided = [(0, 0), (2048, 0), (4096, 0), (4096, 4096), (0, 4096)]
        self.assertTrue(same_ground(square, subdivided))
        self.assertFalse(same_ground(square, rect(0, 0, 4096, 2048)))
