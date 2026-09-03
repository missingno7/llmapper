"""A stair is one surface, and its flank carries one projection.

`read_surfaces` calls a record RESIDUE when it has a same-material neighbour
across a shared vertex and does not continue its projection -- "a restarted
run, a second scale, a mirrored band". A stair whose flank restarts its
panning at every tread is the commonest way to make some, and this is the
before-and-after.
"""

from __future__ import annotations

import unittest

from bloodmap import city
from bloodmap.planar_layout import PlanarLayout

FLOOR = 8192
CLEAR = 32768
TREADS = 5
RISE = 2048
#: 2816 a tread, not 3072: a record 3072 long consumes exactly three tiles,
#: so its panning never advances and zero everywhere is continuous by
#: accident.
DEPTH = 14080
FLANK = city.PLINTH_TILE


def _run():
    return city.stair((((0, 0), (4096, 0)), FLOOR),
                      (((0, DEPTH), (4096, DEPTH)), FLOOR - TREADS * RISE),
                      treads=TREADS, width=4096, clear_height=CLEAR,
                      surface_id="stair:fixture")


def _built(*, one_frame: bool):
    """The same stair, framed as one run or restarted at every tread."""
    made = _run()
    layout = PlanarLayout(name="stair-fixture")
    for spec in made["surfaces"]:
        layout.add_region(spec.surface_id, spec.rings[0], floor_z=spec.floor_z,
                          ceiling_z=spec.ceiling_z,
                          floor_picnum=spec.floor_tile,
                          ceiling_picnum=spec.ceiling_tile,
                          wall_picnum=spec.wall_tile, role="interior",
                          declared_zero_exit=True)
    for index in range(len(made["surfaces"]) - 1):
        here = made["surfaces"][index]
        there = made["surfaces"][index + 1]
        layout.add_connection(f"riser:{index}", here.surface_id,
                              there.surface_id, role="portal",
                              a1=here.rings[0][2], a2=here.rings[0][3])
    layout.set_player_start(made["surfaces"][0].surface_id, x=2048, y=1024,
                            z=made["surfaces"][0].floor_z, angle=0)
    disk = layout.compile().level.to_disk_map()
    _frame(disk, one_frame=one_frame)
    return disk, made


def _frame(disk, *, one_frame: bool):
    """Give the flank one projection, or restart it at every tread.

    The flank is the one-sided record on each side of each tread. One
    projection is a cursor that runs the length of the stair; a restart puts
    every record back at panning zero, which is what a per-sector pass does.
    """
    from bloodmap.texture_frame import wall_length

    #: The repeat comes from the record's own length either way, so the two
    #: variants differ ONLY in the phase. And the tread depth is deliberately
    #: NOT a multiple of 1024: at 3072 a record consumes 192 texels, three
    #: whole tiles, so panning zero everywhere would be continuous by
    #: accident -- which is the trap the 8x texture regression went through.
    #: ONE CURSOR PER SIDE. The stair has two flanks and they are two runs;
    #: walking both with one cursor is not a continuous projection, it is a
    #: second restart wearing the first one's numbers.
    sides: dict = {}
    for wall_id, wall in enumerate(disk.walls):
        face = wall.fields
        if int(face["next_sector"]) >= 0 or int(face["picnum"]) != FLANK:
            continue
        sides.setdefault(int(face["x"]), []).append(wall_id)
    for _side, walls in sorted(sides.items()):
        cursor = 0
        for wall_id in sorted(walls,
                              key=lambda w: int(disk.walls[w].fields["y"])):
            face = disk.walls[wall_id].fields
            repeat = max(1, min(255, int(round(
                wall_length(disk, wall_id) / 16 / 8))))
            face["x_repeat"] = repeat
            face["x_panning"] = (cursor % 64) if one_frame else 0
            cursor += repeat * 8


def _residue(disk):
    from bloodmap.read_surfaces import read_surfaces
    from bloodmap.texture_align import wall_art_sizes

    found = read_surfaces(disk.to_level_ir(),
                          art_sizes=wall_art_sizes("reference/blood"))
    return found


class AStairIsOneSurface(unittest.TestCase):

    def test_a_run_of_two_is_not_a_stair(self):
        with self.assertRaises(city.DressingError) as caught:
            city.stair((((0, 0), (4096, 0)), FLOOR),
                       (((0, 4096), (4096, 4096)), FLOOR - 4096),
                       treads=2, width=4096, clear_height=CLEAR,
                       surface_id="stair:short")
        self.assertIn("threshold and a kerb", str(caught.exception))

    def test_the_run_is_stated_as_two_ends_and_a_count(self):
        made = _run()
        self.assertEqual(len(made["surfaces"]), TREADS)
        self.assertEqual(made["rises"], TREADS)
        self.assertEqual(made["rise"], RISE)
        floors = [spec.floor_z for spec in made["surfaces"]]
        self.assertEqual(floors, sorted(floors, reverse=True),
                         "Blood's z grows downward, so a climb descends in z")

    def test_the_treads_are_read_back_as_one_stepped_run(self):
        from bloodmap.read_stairs import read_stairs

        disk, made = _built(one_frame=True)
        found = read_stairs(disk.to_level_ir())
        self.assertEqual(len(found["runs"]), 1)
        run = found["runs"][0]
        self.assertEqual(len(run["sectors"]), len(made["surfaces"]))

    def test_the_flank_s_phase_is_what_the_residue_turns_on(self):
        """The before and after, on the same geometry, and it comes out the
        other way round from the way I expected.

        The two variants differ in one field: the flank's `x_panning`, either
        a cursor running the length of each side or zero at every tread. The
        repeat is the record's own length in both, and the tread depth is 2816
        so that a record does NOT consume a whole number of tiles -- at 3072 it
        consumes exactly three and zero everywhere would be continuous by
        accident, which is the trap the 8x texture regression went through.

        **Zero everywhere is what `read_surfaces` explains (0 broken of 20),
        and the accumulated cursor is what it calls broken (9).** So the
        reader's continuation law is not the accumulator `AlignWalls` uses,
        and until that is settled the residue is not evidence either way. The
        numbers are asserted so the day it changes, something says so.
        """
        broken = _residue(_built(one_frame=False)[0])["residue_broken"]
        cursored = _residue(_built(one_frame=True)[0])["residue_broken"]
        self.assertEqual(len(broken), 0)
        self.assertEqual(len(cursored), 9)


if __name__ == "__main__":
    unittest.main()
