"""The canonical demonstration maps in maps/blood/mechanism.

Thirty-odd official XMapEdit tutorial maps, one mechanism each, and this
project had never read one of them. Two things it got wrong for weeks are
stated plainly in the first two I opened, so these are fixtures now: every
one is owner-supplied evidence, cited and never edited.
"""

import unittest
from pathlib import Path

DEMOS = Path("maps/blood/mechanism")


def _demo(name):
    from bloodmap.format import read_map

    path = DEMOS / name
    if not path.exists():
        raise unittest.SkipTest(f"{name} is not present")
    return read_map(path)


def _extra(item):
    payload = getattr(item, "extra", None)
    if payload is None:
        return {}
    return payload.fields if hasattr(payload, "fields") else {}


class SwitchWiringTest(unittest.TestCase):
    """Why a switch sends -- and why the zoo's five did not.

    `SetSpriteState` (triggers.cpp:100) calls `evSend` only inside

        if (pXSprite->txID) {
            if (command != kCmdLink && pXSprite->triggerOn  && state)  ...
            if (command != kCmdLink && pXSprite->triggerOff && !state) ...

    so a transmitter with a valid tx_id, a valid command and a valid
    trigger_push, but neither edge flag, flips its own state and sends
    nothing. Nothing static can see it; you find it by pushing.
    """

    def test_the_canonical_switch_reports_its_on_edge(self):
        disk = _demo("#TYPE600.MAP")
        switches = [s for s in disk.sprites if int(s.fields["type"]) == 21]
        self.assertEqual(len(switches), 2)
        for sprite in switches:
            extra = _extra(sprite)
            self.assertTrue(int(extra["trigger_on"]))
            self.assertTrue(int(extra["trigger_push"]))
            self.assertTrue(int(extra["tx_id"]))
            # And it springs back, so a push fires once instead of latching.
            self.assertEqual(int(extra["wait_time"]), 30)

    def test_the_campaign_almost_never_ships_a_silent_sender(self):
        from bloodmap.format import read_map
        from bloodmap.motion import silent_transmitters
        from bloodmap.patterns import list_corpus_maps

        entries = list(list_corpus_maps(population="blood-campaign"))[:8]
        if not entries:
            self.skipTest("no campaign maps")
        total = sum(len(silent_transmitters(read_map(e.path)))
                    for e in entries)
        self.assertLessEqual(total, 8)

    def test_a_transmitter_that_reports_no_edge_is_refused(self):
        from bloodmap.motion import WiringError, transmitter

        with self.assertRaises(WiringError):
            transmitter(channel=100, on=False, off=False)

    def test_the_built_transmitter_carries_the_edge(self):
        from bloodmap.motion import transmitter

        fields = transmitter(channel=100)
        self.assertEqual(fields["trigger_on"], 1)
        self.assertEqual(fields["tx_id"], 100)


class DoorRouteTest(unittest.TestCase):
    """The canonical doors have no switch at all."""

    def test_a_sliding_door_is_worked_by_pushing_its_own_wall(self):
        # #SLDOOR and #SWDOOR carry `trigger_wall_push` on the SECTOR and
        # contain no switch sprite. The route is orthogonal to the channel:
        # neither door has an rx_id.
        for name in ("#SLDOOR.MAP", "#SWDOOR.MAP"):
            disk = _demo(name)
            movers = [i for i, s in enumerate(disk.sectors)
                      if int(s.fields["type"]) in (614, 615, 616, 617)]
            self.assertTrue(movers, name)
            for sector_id in movers:
                extra = _extra(disk.sectors[sector_id])
                self.assertTrue(int(extra["trigger_wall_push"]), name)
                self.assertEqual(int(extra.get("rx_id") or 0), 0, name)
                self.assertEqual(int(extra["command"]), 3, name)

    def test_they_toggle_and_report_both_edges(self):
        disk = _demo("#SLDOOR.MAP")
        for sector_id, sector in enumerate(disk.sectors):
            extra = _extra(sector)
            if int(sector.fields["type"]) in (616, 617):
                self.assertTrue(int(extra["trigger_on"]))
                self.assertTrue(int(extra["trigger_off"]))


class StackSeeThroughTest(unittest.TestCase):
    """Both halves of a stack are marked, not just the upper."""

    def test_the_upper_floor_and_the_lower_ceiling_both_wear_504(self):
        # #STACK.MAP: s2 is the upper sector with floor_picnum 504 and the
        # type-11 marker at its floor; s0 is the lower with ceiling_picnum
        # 504 and the type-12 marker at its ceiling. Marking only the upper
        # leaves the view from below looking at a solid ceiling, which is
        # what the pattern zoo shipped.
        disk = _demo("#STACK.MAP")
        self.assertEqual(int(disk.sectors[2].fields["floor_picnum"]), 504)
        self.assertEqual(int(disk.sectors[0].fields["ceiling_picnum"]), 504)

    def test_the_markers_sit_on_the_planes_they_join(self):
        disk = _demo("#STACK.MAP")
        upper = next(s for s in disk.sprites if int(s.fields["type"]) == 11)
        lower = next(s for s in disk.sprites if int(s.fields["type"]) == 12)
        self.assertEqual(int(lower.fields["z"]),
                         int(disk.sectors[int(lower.fields["sector"])]
                             .fields["ceiling_z"]))
        self.assertEqual(int(_extra(upper)["data_1"]),
                         int(_extra(lower)["data_1"]))

    def test_the_oracle_marks_both_halves_too(self):
        disk = _demo("casket.map")
        self.assertEqual(int(disk.sectors[3].fields["floor_picnum"]), 504)
        self.assertEqual(int(disk.sectors[6].fields["ceiling_picnum"]), 504)


class CasketTwoPlaneTest(unittest.TestCase):
    """The oracle is FOUR sectors in TWO planes, and both lids move."""

    def test_both_planes_carry_a_motor_on_one_channel(self):
        disk = _demo("casket.map")
        for sector_id in (2, 5):
            self.assertEqual(int(disk.sectors[sector_id].fields["type"]), 614)
            self.assertEqual(int(_extra(disk.sectors[sector_id])["rx_id"]), 100)

    def test_the_step_is_in_the_floor_above_and_the_ceiling_below(self):
        # s2's floor is 1024 above s3's; s5's ceiling is 1024 below s6's.
        # That mirroring is what makes the ceiling under you open as the
        # floor you stand on does.
        disk = _demo("casket.map")
        self.assertEqual(int(disk.sectors[3].fields["floor_z"])
                         - int(disk.sectors[2].fields["floor_z"]), 1024)
        self.assertEqual(int(disk.sectors[5].fields["ceiling_z"])
                         - int(disk.sectors[6].fields["ceiling_z"]), 1024)

    def test_both_planes_travel_the_same_way(self):
        from bloodmap.motion import marker_pair

        disk = _demo("casket.map")
        self.assertEqual(marker_pair(disk, 2)["travel"],
                         marker_pair(disk, 5)["travel"])


if __name__ == "__main__":
    unittest.main()
