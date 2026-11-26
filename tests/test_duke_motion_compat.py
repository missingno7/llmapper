"""Source-anchored motion regressions independent of the converter's shared sweep model."""

import unittest
import tempfile
from pathlib import Path

from bloodmap.duke_motion import tagged_z_motion, sector_extra
from bloodmap.e3l11 import convert_playable_duke_to_blood
from bloodmap.format import encode_map, parse_map
from bloodmap.model import record_fields as fields, record_extra
from bloodmap.motion_sim import blood_sweep, closure_sweep, self_intersections, duke_loop_sweeps, compare_sweeps
from bloodmap.duke import read_duke_map, encode_duke_map
from bloodmap.corpus import corpus_map_path
from tests.test_duke_transport import board, ROOT


def adjoining(*sprites, tag=20, ceiling=0):
    duke = board(*sprites)
    # Join rooms 0 and 1 along the same wall, with reciprocal endpoints.
    for i in range(4, 8):
        fields(duke.walls[i])["x"] -= 4096
    fields(duke.walls[1]).update(next_sector=1, next_wall=7)
    fields(duke.walls[7]).update(next_sector=0, next_wall=1)
    fields(duke.sectors[0]).update(lotag=tag, floor_z=0, ceiling_z=ceiling)
    fields(duke.sectors[1]).update(floor_z=0, ceiling_z=-16384)
    return duke


class MotionCompatibilityTests(unittest.TestCase):
    def convert(self, duke):
        disk, report = convert_playable_duke_to_blood(duke)
        return parse_map(encode_map(disk)), report

    def test_vertical_duration_uses_travel_and_120hz_animation_velocity(self):
        duke = adjoining()
        disk, _ = self.convert(duke)
        self.assertEqual(disk.sectors[0].extra.busy_time_a, 5)  # 16384/(256*4)=16 Duke ticks
        fields(duke.sectors[1])["ceiling_z"] = -32768
        disk, _ = self.convert(duke)
        self.assertEqual(disk.sectors[0].extra.busy_time_a, 11)  # 32 Duke ticks
        self.assertEqual(disk.sectors[0].extra.busy_wave_a, 1)

    def test_open_ceiling_door_closes_instead_of_being_silently_skipped(self):
        duke = adjoining(ceiling=-16384)
        disk, _ = self.convert(duke)
        self.assertEqual(disk.sectors[0].type, 600)
        self.assertEqual((disk.sectors[0].extra.off_ceiling_z, disk.sectors[0].extra.on_ceiling_z),
                         (-24576, 0))

    def test_elevator_uses_down_stop_when_no_up_stop_exists(self):
        duke = adjoining(tag=19)
        fields(duke.sectors[1])["floor_z"] = 8192
        motion = tagged_z_motion(duke, 0)
        self.assertEqual((motion["on_floor_z"], motion["on_ceiling_z"]), (8192, 8192))
        disk, _ = self.convert(duke)
        self.assertEqual(disk.sectors[0].extra.on_floor_z, 12288)

    def test_gpspeed_zero_is_preserved_and_diagnosed(self):
        duke = adjoining({"picnum":10,"sector":0,"lotag":0})
        self.assertEqual(sector_extra(duke, 0), 0)
        disk, report = self.convert(duke)
        self.assertEqual(disk.sectors[0].type, 0)
        self.assertTrue(any(r["code"]=="duke-motion-unsupported" for r in report["diagnostics"]))

    def test_first_swing_negates_spawn_direction_with_independent_point_oracle(self):
        for angle, expected in [(512,(1536,0)), (1536,(0,1536))]:
            with self.subTest(angle=angle):
                duke = board({"picnum":1,"lotag":11,"sector":0,"angle":angle})
                fields(duke.sectors[0])["lotag"] = 23
                disk, _ = self.convert(duke)
                # Rotate source (0,0) about (512,512), then scale 3:2.
                final = blood_sweep(disk, 0, steps=8)[-1][0]
                self.assertEqual(tuple(round(v) for v in final), expected)

    def test_inert_se11_does_not_make_a_plain_room_rotate_on_entry(self):
        duke = board({"picnum":1,"lotag":11,"sector":0,"hitag":409},
                     {"picnum":3,"sector":0,"lotag":406},
                     {"picnum":1,"lotag":12,"sector":0,"hitag":561})
        disk, report = self.convert(duke)
        self.assertEqual(disk.sectors[0].type,0)
        extra = disk.sectors[0].extra
        self.assertEqual((extra.state,extra.trigger_push,extra.trigger_wall_push,extra.marker_0), (0,0,0,-1))
        self.assertEqual((extra.trigger_enter,extra.command,extra.rx_id), (1,1,0))
        self.assertGreater(extra.tx_id,0)
        self.assertTrue(any(r["code"]=="duke-inactive-swing-controller" for r in report["diagnostics"]))
        self.assertTrue(any(r["code"]=="duke-light-control-conflict" and r["source_sector"]==0
                            for r in report["diagnostics"]))

    def test_plain_member_of_an_operable_swing_group_can_still_move_remotely(self):
        duke = board({"picnum":1,"lotag":11,"sector":0,"hitag":409},
                     {"picnum":1,"lotag":11,"sector":1,"hitag":409})
        fields(duke.sectors[1])["lotag"] = 23
        disk, _ = self.convert(duke)
        self.assertEqual(disk.sectors[0].type,617)
        self.assertEqual((disk.sectors[0].extra.trigger_push,
                          disk.sectors[0].extra.trigger_wall_push), (0,0))

    def test_independent_light_cannot_overwrite_a_moving_sectors_control(self):
        duke = board({"picnum":1,"lotag":11,"sector":0,"angle":1536},
                     {"picnum":1,"lotag":12,"sector":0,"hitag":571})
        fields(duke.sectors[0])["lotag"] = 23
        disk, report = self.convert(duke)
        self.assertEqual((disk.sectors[0].extra.busy_time_a, disk.sectors[0].extra.rx_id), (3,0))
        self.assertTrue(any(r["code"]=="duke-light-motion-conflict" for r in report["diagnostics"]))

    def test_slide_first_operation_reverses_the_authored_effector_facing(self):
        duke = board({"picnum":1,"lotag":15,"sector":0,"angle":0})
        fields(duke.sectors[0])["lotag"] = 25
        disk, _ = self.convert(duke)
        self.assertEqual(tuple(round(v) for v in blood_sweep(disk,0,steps=8)[-1][0]), (-768,0))

    def test_marked_stretch_edge_moves_two_vertices_without_dragging_a_third(self):
        duke = board({"picnum":1,"lotag":20,"sector":0,"angle":0,"hitag":0})
        fields(duke.sectors[0])["lotag"] = 27
        disk, _ = self.convert(duke)
        frames = blood_sweep(disk,0,steps=8)
        self.assertEqual([i for i,(a,b) in enumerate(zip(frames[0],frames[-1])) if a!=b], [0,1])

    def test_rotation_with_rise_keeps_authored_floor_at_load_then_moves_to_effector(self):
        duke = board({"picnum":1,"lotag":0,"sector":0,"z":0,"angle":512,"hitag":50},
                     {"picnum":1,"lotag":1,"sector":1,"hitag":50})
        fields(duke.sectors[0])["lotag"] = 30
        disk, _ = self.convert(duke)
        self.assertEqual((disk.sectors[0].extra.state,disk.sectors[0].extra.on_floor_z,
                          disk.sectors[0].extra.off_floor_z), (1,24576,0))

    def test_se31_speed_is_sector_extra_and_not_effector_shade(self):
        duke = board({"picnum":1,"lotag":31,"sector":0,"z":0,"angle":512,"shade":-12})
        disk, _ = self.convert(duke)
        self.assertEqual(disk.sectors[0].extra.busy_time_a, 21)  # 16384/256=64 ticks

    def test_rotation_extent_keeps_the_engines_integer_speed_shift(self):
        duke = board({"picnum":1,"lotag":0,"sector":0,"z":0,"angle":512,"hitag":50},
                     {"picnum":1,"lotag":1,"sector":1,"hitag":50},
                     {"picnum":10,"lotag":33,"sector":0})
        fields(duke.sectors[0])["lotag"] = 30
        disk, report = self.convert(duke)
        rotation = next(r for r in report["mechanisms"]["records"] if r["kind"]=="rotate-bridge")
        self.assertEqual(rotation["rotation"],-64)  # 64*(33>>5), not 2*33.

    def test_autoclose_uses_open_state_of_rotation_and_thirty_hertz_hitag(self):
        duke = board({"picnum":1,"lotag":11,"sector":0,"angle":1536},
                     {"picnum":1,"lotag":10,"sector":0,"hitag":90})
        fields(duke.sectors[0])["lotag"] = 23
        disk, _ = self.convert(duke)
        extra = disk.sectors[0].extra
        self.assertEqual((extra.wait_time_a,extra.retrigger_a), (0,0))
        self.assertEqual((extra.wait_time_b,extra.retrigger_b), (28,1))  # (90+2-8)/3

    def test_verifier_audits_the_supplied_map_and_rejects_an_old_wrong_marker(self):
        from tools.verify_motion import verify_map
        duke = board({"picnum":1,"lotag":11,"sector":0,"angle":512})
        fields(duke.sectors[0])["lotag"] = 23
        disk, _ = self.convert(duke)
        fields(disk.sprites[disk.sectors[0].extra.marker_0])["angle"] = 512
        with tempfile.TemporaryDirectory() as folder:
            source,target = Path(folder)/"source.MAP",Path(folder)/"target.MAP"
            source.write_bytes(encode_duke_map(duke))
            target.write_bytes(encode_map(disk))
            result = verify_map(source,steps=8,tolerance=8,check_intrusion=False,converted_path=target)
        self.assertEqual(result["problems"],1)
        self.assertIn("deviation",result["findings"][0]["problems"])

    @unittest.skipUnless((ROOT/"maps/duke3d/E4L1.MAP").exists(), "no Duke corpus")
    def test_e4l1_actual_bathroom_is_static_but_its_stall_door_moves(self):
        duke = read_duke_map(corpus_map_path("E4L1", root=ROOT/"maps/duke3d", populations=("other",)))
        disk, report = self.convert(duke)
        self.assertEqual((disk.sectors[152].type,disk.sectors[152].extra.marker_0), (0,-1))
        self.assertEqual((disk.sectors[152].extra.trigger_enter,disk.sectors[152].extra.command), (1,1))
        self.assertEqual(disk.sectors[61].type,617)
        self.assertTrue(any(r["code"]=="duke-inactive-swing-controller"
                            and r["source_sprite"]==487 and r["hitag"]==409
                            for r in report["diagnostics"]))

    @unittest.skipUnless((ROOT/"maps/duke3d/E1L2.MAP").exists(), "no Duke corpus")
    def test_e1l2_inert_swing_controller_also_preserves_a_static_room(self):
        duke = read_duke_map(corpus_map_path("E1L2", root=ROOT/"maps/duke3d", populations=("other",)))
        disk, report = self.convert(duke)
        self.assertEqual(disk.sectors[262].type,0)
        self.assertTrue(any(r["code"]=="duke-inactive-swing-controller"
                            and r["source_sprite"]==250 and r["hitag"]==284
                            for r in report["diagnostics"]))

    @unittest.skipUnless((ROOT/"maps/duke3d/E4L1.MAP").exists(), "no Duke corpus")
    def test_e4l1_room389_boundary_no_longer_folds_when_its_door_opens(self):
        duke = read_duke_map(corpus_map_path("E4L1", root=ROOT/"maps/duke3d", populations=("other",)))
        disk, report = self.convert(duke)
        sweep = closure_sweep(disk, 50, steps=16)
        self.assertIn((389,3), sweep.loops)
        self.assertFalse([i for i, loop in enumerate(sweep.loops[(389,3)]) if self_intersections(loop)])
        source = duke_loop_sweeps(duke,474,steps=16)
        self.assertLess(compare_sweeps(source[(389,3)],sweep.loops[(389,3)])["max_deviation"],2)
        self.assertTrue(any(r.get("source_sector")==329 and not r["lowered"]
                            for r in report["mechanisms"]["coverage"]))


if __name__ == "__main__":
    unittest.main()
