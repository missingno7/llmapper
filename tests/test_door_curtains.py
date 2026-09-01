"""DOOR-CURTAINS.map: the tutorial that settled the marker law.

`maps/blood/mechanism/Vanilla/` holds one single-mechanism tutorial per file
and this project had read none of them. DOOR-CURTAINS alone carries
twenty-five curtain exemplars, and it settles two things that had been wrong
for weeks: what a marker pair MEANS, and what a curtain IS.

Owner-supplied evidence, mechanism-tutorial population: cited and fixtured,
never edited.
"""

import unittest
from pathlib import Path

TUTORIAL = Path("maps/blood/mechanism/Vanilla/DOOR-CURTAINS.map")


def _map():
    from bloodmap.format import read_map

    if not TUTORIAL.exists():
        raise unittest.SkipTest("DOOR-CURTAINS.map is not present")
    return read_map(TUTORIAL)


def _extra(item):
    payload = getattr(item, "extra", None)
    if payload is None:
        return {}
    return payload.fields if hasattr(payload, "fields") else {}


class MarkerLawTest(unittest.TestCase):
    """Markers are STATE-anchored, not journey-anchored.

    Type 3 is the position FOR STATE OFF and type 4 the position FOR STATE
    ON. The mapper draws the geometry at the ON pose and `state` decides
    which one it snaps to at load. There is no from/to journey and no rest
    marker -- rest is whatever `state` says.
    """

    @classmethod
    def setUpClass(cls):
        cls.disk = _map()

    def test_the_fabric_is_saved_exactly_at_its_on_marker(self):
        # s3's fin tip is at y -1152 and its type-4 marker sits at y -1152;
        # the type-3 marker is away at -2048 where the fabric will be when
        # it is drawn across. Three exemplars, to the coordinate.
        from bloodmap.motion import marker_pair

        for sector_id, off_at, on_at in ((3, -2048, -1152),
                                         (6, -8192, -7296),
                                         (8, -11264, -10368)):
            pair = marker_pair(self.disk, sector_id)
            self.assertEqual(pair["off"]["y"], off_at, f"s{sector_id}")
            self.assertEqual(pair["on"]["y"], on_at, f"s{sector_id}")

    def test_every_exemplar_is_drawn_at_its_on_pose(self):
        from bloodmap.motion import MOVING_TYPES, drawn_pose

        checked = 0
        for sector_id, sector in enumerate(self.disk.sectors):
            if int(sector.fields["type"]) not in MOVING_TYPES:
                continue
            if sector.extra is None:
                continue
            pose = drawn_pose(self.disk, sector_id)
            if pose is None:
                continue
            self.assertEqual(pose, "on", f"s{sector_id}")
            checked += 1
        self.assertGreater(checked, 15)

    def test_state_zero_means_it_comes_up_closed(self):
        # None of the tutorial's curtains sets `state`, so all rest at OFF --
        # fabric drawn across. A state-0 sector therefore displaces itself by
        # the whole marker separation at load, which is not a defect: it is
        # how a curtain drawn open comes up closed.
        from bloodmap.motion import marker_pair
        from bloodmap.motion_sim import blood_sweep, rest_displacement

        for sector_id in (3, 6, 8):
            pair = marker_pair(self.disk, sector_id)
            self.assertEqual(pair["state"], 0, f"s{sector_id}")
            frames = blood_sweep(self.disk, sector_id, steps=4)
            moved = rest_displacement(self.disk, sector_id, frames)
            self.assertAlmostEqual(moved, abs(pair["travel"][1]), delta=2)

    def test_the_horizontal_exemplar_obeys_the_same_law(self):
        # s24 draws along x instead of y and nothing else changes.
        from bloodmap.motion import drawn_pose, marker_pair

        pair = marker_pair(self.disk, 24)
        self.assertEqual(pair["off"]["x"], 512)
        self.assertEqual(pair["on"]["x"], 1408)
        self.assertEqual(drawn_pose(self.disk, 24), "on")


class FinTopologyTest(unittest.TestCase):
    """The fabric is an internal FIN with its own vertices."""

    @classmethod
    def setUpClass(cls):
        cls.disk = _map()

    def test_the_sector_carries_the_fabric_inside_its_own_outline(self):
        # s3 is eight walls: four sides of the doorway, then back along the
        # anchored edge and out into a narrow tab. Not a separate thin
        # sector, and not a pair of caps.
        fields = self.disk.sectors[3].fields
        self.assertEqual(int(fields["wall_count"]), 8)
        start = int(fields["wall_ptr"])
        fabric = [i for i in range(start, start + 8)
                  if int(self.disk.walls[i].fields["picnum"]) == 146]
        self.assertEqual(len(fabric), 3)      # two sides and the free end

    def test_exactly_the_fins_free_end_is_flagged(self):
        from bloodmap.motion import flagged_walls

        for sector_id in (3, 24, 53):
            flags = flagged_walls(self.disk, sector_id)
            self.assertEqual(len(flags), 1, f"s{sector_id}")
            self.assertEqual(list(flags.values()), [1], f"s{sector_id}")

    def test_nothing_outside_the_curtain_is_ever_deformed(self):
        # Every moved vertex is interior to the sector's own outline, which
        # is what the fin buys and why tutorial curtains never disturb their
        # rooms. This is the seam being part of the sector.
        from bloodmap.motion import motion_set

        for sector_id in (3, 24, 53):
            found = motion_set(self.disk, sector_id)
            self.assertEqual(found["sectors"], [sector_id], f"s{sector_id}")

    def test_the_fin_is_narrow_inside_a_wider_doorway(self):
        # s3: a 64-wide tab centred in a 256 opening.
        start = int(self.disk.sectors[3].fields["wall_ptr"])
        xs = {int(self.disk.walls[i].fields["x"]) for i in range(start, start + 8)}
        self.assertEqual(max(xs) - min(xs), 256)
        fin = sorted(x for x in xs if min(xs) < x < max(xs))
        self.assertEqual(fin[-1] - fin[0], 64)


class WiringExemplarTest(unittest.TestCase):
    """The other facets the tutorial demonstrates, one sector each."""

    @classmethod
    def setUpClass(cls):
        cls.disk = _map()

    def test_s6_closes_itself_after_a_wait(self):
        extra = _extra(self.disk.sectors[6])
        self.assertEqual(int(extra["wait_time_a"]), 20)
        self.assertTrue(int(extra["retrigger_a"]))

    def test_s8_wants_a_key(self):
        # Key 6 is the moon.
        self.assertEqual(int(_extra(self.disk.sectors[8])["key"]), 6)

    def test_s21_drives_a_light_with_command_five(self):
        # The command-5 LINK: s21 transmits on 106 and s20 receives it with a
        # shade wave. kCmdLink is excluded from the evSend guards in
        # SetSpriteState, which is exactly why it is a different verb -- it
        # couples state continuously instead of firing an edge.
        curtain, light = _extra(self.disk.sectors[21]), _extra(self.disk.sectors[20])
        self.assertEqual(int(curtain["tx_id"]), 106)
        self.assertEqual(int(curtain["command"]), 5)
        self.assertEqual(int(light["rx_id"]), 106)
        self.assertEqual(int(light["amplitude"]), -20)

    @unittest.expectedFailure
    def test_the_light_link_is_read_as_a_facet(self):
        # Blueprint: roadmap grammar, control bus. Nothing in the stack
        # reports "this mechanism drives that light", and command 5 is still
        # unread. Counted rather than absent.
        from bloodmap.doors import _wall_owners
        from bloodmap.effects import read_mechanism

        reading = read_mechanism(self.disk, 21, owners=_wall_owners(self.disk))
        self.assertEqual(reading.get("drives"), [20])


class ConstructorMatchesTutorialTest(unittest.TestCase):
    """What `mechanism.curtain` builds, against what the tutorial builds."""

    def _built(self, **overrides):
        from bloodmap.mechanism import curtain
        from bloodmap.planar_layout import PlanarLayout

        layout = PlanarLayout(name="probe")
        layout.add_region("room", [(0, 0), (2048, 0), (2048, 1024), (0, 1024)],
                          floor_z=0, ceiling_z=-33280)
        layout.add_region("far", [(0, 2048), (2048, 2048), (2048, 3072),
                                  (0, 3072)],
                          floor_z=0, ceiling_z=-33280, declared_zero_exit=True)
        layout.set_player_start("room", x=512, y=512, z=0, angle=0)
        kwargs = dict(opening=(0, 1024, 2048, 2048), axis="x", channel=200,
                      leaf_region="cur", floor_z=0, ceiling_z=-33280,
                      declared_zero_exit=True)
        kwargs.update(overrides)
        built = curtain(layout, "cur", **kwargs)
        layout.add_connection("c0", "room", "cur", a1=(0, 1024),
                              a2=(2048, 1024), min_width=512)
        layout.add_connection("c1", "cur", "far", a1=(0, 2048),
                              a2=(2048, 2048), min_width=512)
        return layout, built

    def test_it_builds_the_eight_wall_fin(self):
        layout, _built = self._built()
        self.assertEqual(len(layout.regions["cur"].outer), 8)

    def test_it_is_drawn_at_on_and_rests_closed(self):
        from bloodmap.motion import drawn_pose

        layout, built = self._built()
        self.assertEqual(built["rests"], "closed")
        compiled = layout.compile()
        disk = compiled.level.to_disk_map()
        self.assertEqual(drawn_pose(disk, compiled.allocations["cur"].sector_id),
                         "on")

    def test_its_motion_never_leaves_its_own_sector(self):
        from bloodmap.motion import motion_set

        layout, _built = self._built()
        compiled = layout.compile()
        disk = compiled.level.to_disk_map()
        sector_id = compiled.allocations["cur"].sector_id
        self.assertEqual(motion_set(disk, sector_id)["sectors"], [sector_id])

    def test_a_fin_with_nothing_to_draw_over_is_refused(self):
        from bloodmap.mechanism import MechanismError

        with self.assertRaises(MechanismError):
            self._built(retracted=4096)


if __name__ == "__main__":
    unittest.main()
