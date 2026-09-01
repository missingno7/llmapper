"""The engine usage laws, and the two payload shapes the model learned.

Each law is sourced in the Build source and measured on the campaign before
it is allowed a severity, so what these tests protect is the *plumbing*: that
the table is readable, that the rules are registered and check what they say,
and that the two new constructors reproduce the E1M1 sectors they were
derived from.
"""

import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class UsageTableTest(unittest.TestCase):
    def setUp(self):
        from bloodmap.usage_kinds import load

        self.table = load()
        if not self.table.get("usage"):
            self.skipTest("the usage-kind table has not been compiled")

    def test_the_table_covers_the_whole_campaign(self):
        self.assertEqual(self.table["maps"], 43)
        self.assertGreater(len(self.table["usage"]), 3000)

    def test_the_sky_family_is_derived_and_small(self):
        from bloodmap.usage_kinds import sky_family

        # Every tile the campaign ever parallaxes, which is three. If this
        # grows, something has changed about the corpus, not about the rule.
        self.assertEqual(sky_family(), {2500, 3491, 3678})

    def test_every_sky_tile_is_exempt_from_the_aspect_law(self):
        # The two laws interlock: all three are 64x400, so a sky tile on an
        # ordinary ceiling breaks the power-of-two law as well as this one.
        from bloodmap.usage_kinds import sky_family, tile_size

        for picnum in sky_family():
            width, height = tile_size(picnum)
            self.assertFalse(width & (width - 1) == 0
                             and height & (height - 1) == 0,
                             f"tile {picnum} is {width}x{height}")

    def test_a_shelf_is_a_wall_tile_and_the_table_says_so(self):
        from bloodmap.usage_kinds import attested

        self.assertTrue(attested(2026, "wall_one_sided"))
        self.assertFalse(attested(2026, "floor"))
        self.assertFalse(attested(2026, "ceiling"))

    def test_a_grate_belongs_on_an_overlay(self):
        from bloodmap.usage_kinds import attested

        # 502 appears as the over_picnum of a masked wall 27 times and on a
        # plain wall or a floor never. It is why maskwall_panel exists.
        self.assertTrue(attested(502, "over_picnum"))
        self.assertFalse(attested(502, "floor"))


class RulesRegisteredTest(unittest.TestCase):
    def setUp(self):
        import bloodmap.rules_blood                       # noqa: F401
        from bloodmap.rules import RULES

        self.rules = RULES

    def test_the_four_usage_laws_are_registered_with_sources(self):
        for rule_id in ("mask-tile-off-plain-surfaces",
                        "parallax-wears-a-sky-tile",
                        "sky-tile-is-parallaxed",
                        "tile-sits-in-an-attested-slot"):
            rule = self.rules[rule_id]
            self.assertTrue(rule.source.strip(), rule_id)
            self.assertGreater(len(rule.because), 80, rule_id)

    def test_the_mask_law_catches_a_cut_out_on_a_floor(self):
        from bloodmap.usage_kinds import masked_tiles

        masked = masked_tiles()
        if not masked:
            self.skipTest("no ART to read mask ratios from")
        disk = _one_sector_map(floor_picnum=sorted(masked)[0])
        found = self.rules["mask-tile-off-plain-surfaces"].check(disk)
        self.assertEqual(len(found.violations), 1)

    def test_the_parallax_law_catches_a_smeared_ceiling(self):
        disk = _one_sector_map(ceiling_picnum=285, ceiling_stat=1)
        found = self.rules["parallax-wears-a-sky-tile"].check(disk)
        self.assertEqual(len(found.violations), 1)

    def test_a_sky_tile_without_the_bit_is_caught(self):
        disk = _one_sector_map(ceiling_picnum=2500, ceiling_stat=0)
        found = self.rules["sky-tile-is-parallaxed"].check(disk)
        self.assertEqual(len(found.violations), 1)

    def test_a_sky_tile_with_the_bit_is_not(self):
        disk = _one_sector_map(ceiling_picnum=2500, ceiling_stat=1)
        found = self.rules["sky-tile-is-parallaxed"].check(disk)
        self.assertEqual(found.violations, ())


def _one_sector_map(**overrides):
    """A map of one sector and no walls, for checking a rule in isolation."""
    from bloodmap.format import read_map, write_map
    import tempfile

    from bloodmap.planar_layout import PlanarLayout

    layout = PlanarLayout(name="probe")
    layout.add_region("only", [(0, 0), (1024, 0), (1024, 1024), (0, 1024)],
                      floor_z=0, ceiling_z=-16960, declared_zero_exit=True)
    layout.set_player_start("only", x=512, y=512, z=0, angle=0)
    disk = layout.compile().level.to_disk_map()
    disk.sectors[0].fields.update(overrides)
    with tempfile.TemporaryDirectory() as directory:
        path = Path(directory) / "probe.MAP"
        write_map(disk, path)
        return read_map(path)


class PayloadShapeTest(unittest.TestCase):
    """The two shapes read off the maps they were derived from."""

    @classmethod
    def setUpClass(cls):
        from bloodmap.format import read_map
        from bloodmap.patterns import list_corpus_maps

        found = [e for e in list_corpus_maps(population="blood-campaign")
                 if e.path.stem.upper().startswith("E1M1")]
        if not found:
            raise unittest.SkipTest("E1M1 is not in the corpus")
        cls.disk = read_map(found[0].path)

    def test_the_casket_reads_as_a_boundary_re_partition(self):
        from bloodmap.effects import payload

        # One flagged wall, and it is the portal to the cover: its travel
        # moves the line between the two sectors.
        for sector_id, cover in ((28, 27), (30, 29)):
            shape = payload(self.disk, sector_id)["shape"]
            self.assertEqual(shape["shape"], "boundary re-partition")
            self.assertEqual(shape["re_partitions_with"], cover)

    def test_the_curtain_reads_as_a_self_resize(self):
        from bloodmap.effects import payload

        shape = payload(self.disk, 125)["shape"]
        self.assertEqual(shape["shape"], "the sector resizes itself")
        self.assertTrue(shape["advancing"])
        self.assertTrue(shape["retreating"])

    def test_a_sprite_only_gate_moves_no_geometry(self):
        from bloodmap.effects import payload

        # E1M1 s65: 49 walls, none flagged, two wall sprites doing the whole
        # job of a gate.
        self.assertEqual(payload(self.disk, 65)["shape"]["shape"],
                         "nothing moves")


class ConstructorTest(unittest.TestCase):
    """The constructors reproduce the signatures they were derived from."""

    def _layout(self):
        from bloodmap.planar_layout import PlanarLayout

        layout = PlanarLayout(name="probe")
        layout.add_region("room", [(0, 0), (6144, 0), (6144, 6144), (0, 6144)],
                          floor_z=0, ceiling_z=-33280)
        layout.set_player_start("room", x=1024, y=1024, z=0, angle=0)
        return layout

    def test_a_curtain_flags_its_two_caps_opposite_ways(self):
        # The construct moved to `bloodmap.motion`'s factoring and its
        # signature changed with it; `tests/test_motion_primitives.py` holds
        # the contract. What is pinned HERE is the reading, beside the other
        # payload shapes: two flagged caps with opposite signs.
        from bloodmap.mechanism import curtain
        from bloodmap.motion import payload_shape

        layout = self._layout()
        curtain(layout, "cur", frame=(6144, 1024, 6272, 1024 + 4096),
                axis="y", travel=1024, channel=310, leaf_region="leaf",
                floor_z=0, ceiling_z=-33280, host_side="low")
        layout.add_connection("c", "room", "leaf", a1=(6144, 1024),
                              a2=(6144, 1024 + 4096), min_width=512)
        compiled = layout.compile()
        disk = compiled.level.to_disk_map()
        shape = payload_shape(disk, compiled.allocations["leaf"].sector_id)
        self.assertEqual(shape["shape"], "the sector resizes itself")
        self.assertTrue(shape["advancing"])
        self.assertTrue(shape["retreating"])

    def test_a_curtain_wears_the_owners_curtain_tile(self):
        from bloodmap.mechanism import CURTAIN_PICNUM

        # Owner anchor 146, binding strong. 147 is its translucent variant and
        # carries the mask colour, so it belongs on a maskwall or a sprite.
        self.assertEqual(CURTAIN_PICNUM, 146)

    def test_a_planar_door_flags_exactly_one_wall(self):
        # The signature changed with the owner's oracle: the construct now
        # takes ONE footprint and splits it, rather than being handed two
        # outlines and trusted about the travel between them.
        # `tests/test_swept_state.py` holds the constructor's full contract;
        # this keeps the payload-shape reading pinned here beside the others.
        from bloodmap.effects import payload
        from bloodmap.mechanism import planar_door

        from bloodmap.planar_layout import PlanarLayout

        # The room stops where the lid ends, so only the LID shares a wall
        # with it -- the hole beyond is reached through the door, which is
        # the whole point of the construct.
        layout = PlanarLayout(name="probe")
        layout.add_region("room", [(0, 1024), (6144, 1024), (6144, 3072),
                                   (0, 3072)],
                          floor_z=0, ceiling_z=-33280)
        layout.set_player_start("room", x=1024, y=2048, z=0, angle=0)
        planar_door(layout, "casket",
                    footprint=(6144, 1024, 8192, 1024 + 2176), axis="y",
                    split=1024 + 2048, travel=-1920, channel=311,
                    lid_region="lid", hole_region="hole",
                    floor_z=0, ceiling_z=-33280,
                    hole_kwargs={"declared_zero_exit": True})
        layout.add_connection("c0", "room", "lid", a1=(6144, 1024),
                              a2=(6144, 1024 + 2048), min_width=512)
        compiled = layout.compile()
        disk = compiled.level.to_disk_map()
        shape = payload(disk, compiled.allocations["lid"].sector_id)["shape"]
        self.assertEqual(shape["shape"], "boundary re-partition")
        self.assertEqual(shape["flagged"], 1)

    def test_a_lift_out_composes_a_z_verb_on_the_same_sector(self):
        # E1M1's own proof that the two XSECTOR z states are not a type-600
        # privilege: s30 is 614 AND carries floor endpoints. It goes on the
        # HOLE, because that is the sector the body stands in.
        from bloodmap.mechanism import planar_door

        layout = self._layout()
        built = planar_door(layout, "casket",
                            footprint=(6144, 1024, 8192, 1024 + 2176),
                            axis="y", split=1024 + 2048, travel=-1920,
                            channel=311, lid_region="lid",
                            hole_region="hole", floor_z=0, ceiling_z=-33280,
                            motor="hole", lift_out=6144,
                            hole_kwargs={"declared_zero_exit": True})
        self.assertEqual(built["lift_out"], 6144)
        behavior = layout.regions["hole"].sector_behavior
        self.assertEqual(behavior["on_floor_z"], -6144)
        self.assertEqual(behavior["off_ceiling_z"], behavior["on_ceiling_z"])

    def test_a_planar_door_will_not_build_without_travel(self):
        from bloodmap.mechanism import MechanismError, planar_door

        layout = self._layout()
        with self.assertRaises(MechanismError):
            planar_door(layout, "x", footprint=(0, 0, 1024, 2176), axis="y",
                        split=1024, travel=0, channel=1, lid_region="l",
                        hole_region="h", floor_z=0, ceiling_z=-33280)


class CarryWallTest(unittest.TestCase):
    def test_a_wall_that_is_not_in_the_outline_is_refused(self):
        from bloodmap.planar_layout import PlanarLayout, PlanarLayoutError

        layout = PlanarLayout(name="probe")
        layout.add_region("a", [(0, 0), (1024, 0), (1024, 1024), (0, 1024)],
                          floor_z=0, ceiling_z=-16960, declared_zero_exit=True)
        layout.set_player_start("a", x=512, y=512, z=0, angle=0)
        layout.carry_wall("a", (0, 0), (555, 0))
        with self.assertRaises(PlanarLayoutError):
            layout.compile()

    def test_both_directions_are_available(self):
        from bloodmap.planar_layout import PlanarLayout

        layout = PlanarLayout(name="probe")
        layout.add_region("a", [(0, 0), (1024, 0), (1024, 1024), (0, 1024)],
                          floor_z=0, ceiling_z=-16960, declared_zero_exit=True)
        layout.set_player_start("a", x=512, y=512, z=0, angle=0)
        layout.carry_wall("a", (0, 0), (1024, 0), moves="with")
        layout.carry_wall("a", (1024, 1024), (0, 1024), moves="against")
        disk = layout.compile().level.to_disk_map()
        flags = [int(w.fields["cstat"]) for w in disk.walls]
        self.assertIn(16384, flags)
        self.assertIn(32768, flags)


if __name__ == "__main__":
    unittest.main()
