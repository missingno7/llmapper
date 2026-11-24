"""Exercise a welded slide and check it against two shipped vehicles."""

import unittest
from types import SimpleNamespace

from bloodmap.corpus import CorpusError, corpus_map_path
from bloodmap.format import read_map
from bloodmap.model import DiskObject, PackedExtra
from bloodmap.motion_sim import body_health, rigid_bodies
from bloodmap.swept_state import run


def _vehicle():
    # Two 1024-square cells, one shared red wall and separate marker pairs.
    polygons = [[(0, 0), (1024, 0), (1024, 1024), (0, 1024)],
                [(1024, 0), (2048, 0), (2048, 1024), (1024, 1024)],
                [(-2048, -2048), (4096, -2048), (4096, 4096), (-2048, 4096),
                 (0, 0), (0, 1024), (1024, 1024), (2048, 1024),
                 (2048, 0), (1024, 0)]]
    walls, sectors, sprites = [], [], []
    for i, polygon in enumerate(polygons):
        first = len(walls)
        for j, (x, y) in enumerate(polygon):
            start, size = (4, 6) if j >= 4 else (0, 4)
            point2 = first + start + (j - start + 1) % size
            walls.append(DiskObject(dict(x=x, y=y, point2=point2, cstat=0,
                                         next_wall=-1, next_sector=-1)))
        extra = None
        if i < 2:
            extra = PackedExtra("sector", dict(
                rx_id=100, busy_time_a=10, busy_time_b=10, busy_wave_a=1,
                busy_wave_b=1, state=0, drag=1, marker_0=2*i, marker_1=2*i+1))
            for x in (first * 256, first * 256 + 512):
                sprites.append(DiskObject(dict(x=x, y=512, z=0, angle=0, sector=i,
                                               cstat=32768, status=10, picnum=3997)))
        sectors.append(DiskObject(dict(wall_ptr=first, wall_count=len(polygon),
                                       type=616 if extra else 0, floor_z=0,
                                       ceiling_z=-20000, floor_stat=64, ceiling_stat=64),
                                  extra))
    for a, b, a_sector, b_sector in [(1, 7, 0, 1), (0, 17, 0, 2), (2, 13, 0, 2),
                                     (3, 12, 0, 2), (4, 16, 1, 2), (5, 15, 1, 2),
                                     (6, 14, 1, 2)]:
        walls[a].fields.update(next_wall=b, next_sector=b_sector)
        walls[b].fields.update(next_wall=a, next_sector=a_sector)
    return SimpleNamespace(sectors=sectors, walls=walls, sprites=sprites)


class RigidBodyTest(unittest.TestCase):
    def test_two_welded_sectors_move_as_one(self):
        disk = _vehicle()
        body, = rigid_bodies(disk)
        self.assertEqual(body.members, (0, 1))
        found = body_health(disk, body)
        self.assertEqual(found["problems"], [])
        self.assertEqual(found["host"], 2)
        self.assertEqual({(r["sector"], r["loop"]) for r in found["loops"]},
                         {(0, 0), (1, 0), (2, 1)})
        report = run(disk)
        self.assertTrue(report["passed"], report["problems"])
        self.assertEqual(report["bodies"], [found])
        self.assertEqual(len(report["per_sector"]), 2)

    def test_a_different_busy_time_prevents_a_rigid_body_and_is_noted(self):
        disk = _vehicle()
        disk.sectors[1].extra.busy_time_b = 12
        self.assertEqual(rigid_bodies(disk), [])
        self.assertTrue(any("busy_time_b" in note and "seam can tear" in note
                            for note in run(disk)["notes"]))

    def test_a_wall_sprite_needs_to_be_carried(self):
        disk = _vehicle()
        disk.sprites.append(DiskObject(dict(x=500, y=512, z=-4000, sector=0, cstat=16,
                                            status=0, picnum=0, y_repeat=32)))
        body, = rigid_bodies(disk)
        self.assertTrue(any("sprite 4" in note and "left behind" in note
                            for note in body_health(disk, body)["notes"]))
        disk.sprites[-1].fields["cstat"] |= 8192
        self.assertFalse(any("sprite 4" in note for note in body_health(disk, body)["notes"]))

    def test_only_uniform_marked_slides_can_join(self):
        disk = _vehicle()
        disk.sectors[1].fields["type"] = 614
        for wall in disk.walls[4:8]:
            wall.fields["cstat"] = 16384
        self.assertEqual(rigid_bodies(disk)[0].members, (0, 1))
        disk.walls[4].fields["cstat"] = 0
        self.assertEqual(rigid_bodies(disk), [])

    def test_body_cannot_leave_its_single_host(self):
        disk = _vehicle()
        for marker in disk.sprites[1::2]:
            marker.fields["x"] += 4096
        body, = rigid_bodies(disk)
        found = body_health(disk, body)
        self.assertTrue(any("body leaves sector 2" in p for p in found["problems"]))
        self.assertTrue(found["crossings"])
        self.assertFalse(run(disk)["passed"])

    def test_mismatched_shared_coordinates_are_reported_before_the_snap(self):
        disk = _vehicle()
        disk.walls[4].fields["x"] += 32
        body, = rigid_bodies(disk)
        self.assertTrue(any("shared vertex" in p for p in body_health(disk, body)["problems"]))

    def test_the_body_sweeps_a_non_member_loop(self):
        disk = _vehicle()
        # A 256-deep static bay fills the west side of the host hole.
        # At load the body moves 512 west, past the bay's fixed outer edge.
        disk.sectors[2].fields["wall_count"] += 2
        disk.walls[12].fields["point2"] = 18
        for x, y, point2 in [(-256, 0, 19), (-256, 1024, 13), (0, 0, 21),
                             (0, 1024, 22), (-256, 1024, 23), (-256, 0, 20)]:
            disk.walls.append(DiskObject(dict(x=x, y=y, point2=point2, cstat=0,
                                              next_sector=-1, next_wall=-1)))
        disk.sectors.append(DiskObject(dict(wall_ptr=20, wall_count=4, type=0,
                                           floor_z=0, ceiling_z=-20000)))
        for wall, partner, sector in [(20, 3, 0), (21, 19, 2), (22, 18, 2), (23, 12, 2)]:
            disk.walls[wall].fields.update(next_wall=partner, next_sector=sector)
            disk.walls[partner].fields.update(next_wall=wall, next_sector=3)
        body, = rigid_bodies(disk)
        self.assertIn("step 0/16: loop 0 of sector 3 inverts", body_health(disk, body)["problems"])

    def test_tutorial(self):
        self.assert_shipped_body("MACHINERY-1WAYVEHICLE", "mechanism-tutorial",
                                 tuple(range(2, 11)))

    def test_death_wish_car(self):
        self.assert_shipped_body("DWE1M2", "community-curated",
                                 (225, 226, 227, 228, 418, 419, 420, 421, 422, 423))

    def assert_shipped_body(self, name, population, sectors):
        try:
            path = corpus_map_path(name, populations=(population,))
        except CorpusError:
            self.skipTest(f"{name} is not in the corpus")
        disk = read_map(path)
        bodies = [body for body in rigid_bodies(disk) if set(sectors) & set(body.members)]
        self.assertEqual([body.members for body in bodies], [sectors])
        self.assertEqual(body_health(disk, bodies[0])["problems"], [])
