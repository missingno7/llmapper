"""Texture frames, against the editor's own routine and the campaign.

The acceptance test for this module is not "does it produce nice numbers". It
is that **XMapEdit has nothing left to say**: resolve a frame onto a run, then
run the port of `ED32_AutoAlignWalls` over the same walls, and no field may
change. The editor's `.` key is the law the campaign was aligned with, so a
generator whose output is a fixed point of it is stating the same fact the
mappers stated -- and one whose output is not has invented something.

Fixtures are original maps and hand-built two-wall levels. No generated map is
evidence here.
"""

import unittest
from pathlib import Path

VANILLA = Path("maps/blood/mechanism/Vanilla")


def _campaign(stem):
    from bloodmap.format import read_map
    from bloodmap.patterns import list_corpus_maps

    found = [entry for entry in list_corpus_maps(population="blood-campaign")
             if entry.path.stem.upper() == stem]
    if not found:
        raise unittest.SkipTest(f"{stem} is not in the corpus")
    return read_map(found[0].path)


def _sizes():
    from bloodmap.texture_align import wall_art_sizes

    sizes = wall_art_sizes()
    if not sizes:
        raise unittest.SkipTest("no ART in reference/blood")
    return sizes


class TheEngineArithmetic(unittest.TestCase):
    """Transcriptions, checked against the source they came from."""

    def test_length_is_builds_octagonal_approximation(self):
        # `common_game.h:1004-1012`. The editor measures every wall with
        # approxDist, so a frame using the Euclidean length disagrees with
        # fixxrepeat on every diagonal: 3-4-5 comes out 7, not 5.
        from bloodmap.texture_frame import approx_dist

        self.assertEqual(approx_dist(4, 0), 4)
        self.assertEqual(approx_dist(3, 4), 4 + ((3 * 3) >> 3))
        self.assertEqual(approx_dist(-3, -4), approx_dist(3, 4))

    def test_division_truncates_toward_zero_the_way_c_does(self):
        # The bug this function exists for: AlignWalls's y term has a negative
        # numerator at every lintel, sill and kerb return, and Python's // is
        # off by one there -- which reads out as y_panning 255 instead of 0.
        from bloodmap.texture_frame import c_div

        self.assertEqual(c_div(-1, 8), 0)
        self.assertEqual(c_div(-9, 8), -1)
        self.assertEqual(c_div(9, 8), 1)
        self.assertNotEqual(c_div(-1, 8), -1 // 8)

    def test_a_floor_texel_is_sixteen_world_units_and_eight_expanded(self):
        # engine.cpp:2797-2799 with :2880. The expanded bit halves the world
        # size of the tile; it does not double it.
        from bloodmap.texture_frame import units_per_texel

        self.assertEqual(units_per_texel(False), 16)
        self.assertEqual(units_per_texel(True), 8)

    def test_a_sixty_four_tile_has_a_grid_line_every_1024_units(self):
        from bloodmap.texture_frame import surface_is_whole

        self.assertTrue(surface_is_whole((0, 0), (64, 64)))
        self.assertTrue(surface_is_whole((1024, -2048), (64, 64)))
        self.assertFalse(surface_is_whole((1536, 0), (64, 64)))
        # and expanded, every 512
        self.assertTrue(surface_is_whole((1536, 0), (64, 64), expanded=True))

    def test_panning_moves_the_grid_onto_an_arbitrary_corner(self):
        # The crate fix in one line: whatever corner the box has, there is a
        # panning that starts the tile there.
        from bloodmap.texture_frame import surface_is_whole, surface_panning

        for corner in ((1536, 0), (704, -1216), (-3008, 5312)):
            panning = surface_panning(corner, (64, 64))
            self.assertTrue(surface_is_whole(corner, (64, 64), panning=panning),
                            corner)


class TheZPegIsTheEditorsZPeg(unittest.TestCase):
    def test_a_one_sided_wall_hangs_from_the_ceiling_unless_cstat_four(self):
        # GetWallZPeg, xmpmaped.cpp:2996-3002.
        from bloodmap.texture_frame import (
            WALL_ORG_BOTTOM, sector_index, wall_z_peg)

        disk = _campaign("E1M1")
        owners = sector_index(disk)
        checked = 0
        for index, wall in enumerate(disk.walls):
            if int(wall.fields["next_sector"]) >= 0:
                continue
            here = disk.sectors[owners[index]].fields
            want = (int(here["floor_z"])
                    if int(wall.fields["cstat"]) & WALL_ORG_BOTTOM
                    else int(here["ceiling_z"]))
            self.assertEqual(wall_z_peg(disk, index, owners), want, index)
            checked += 1
            if checked > 200:
                break
        self.assertGreater(checked, 50)


class TheEditorHasNothingLeftToSay(unittest.TestCase):
    """The acceptance test. Resolve a frame, then let '.' try to improve it."""

    KEYS = ("x_repeat", "x_panning", "y_repeat", "y_panning", "cstat")

    def _invariant(self, disk, limit=250):
        from bloodmap.texture_frame import (
            WallRunFrame, auto_align_walls, resolve_run, run_from,
            sector_index)

        sizes = _sizes()
        owners = sector_index(disk)
        covered, runs, moved = set(), 0, 0
        for start in range(min(limit, len(disk.walls))):
            if start in covered:
                continue
            tile = int(disk.walls[start].fields["picnum"])
            if tile not in sizes or not sizes[tile][0]:
                continue
            run = [w for w in run_from(disk, start, art_sizes=sizes,
                                       owners=owners) if w not in covered]
            if len(run) < 2:
                continue
            covered.update(run)
            runs += 1
            resolve_run(disk, run, WallRunFrame(tile=tile), sizes, owners)
            before = {w: {k: int(disk.walls[w].fields[k]) for k in self.KEYS}
                      for w in run}
            auto_align_walls(disk, run[0], flags=0x01, art_sizes=sizes,
                             owners=owners)
            moved += sum(
                1 for w in run
                if any(int(disk.walls[w].fields[k]) != before[w][k]
                       for k in self.KEYS))
        return runs, moved

    def test_a_resolved_run_is_a_fixed_point_of_the_editors_align(self):
        # E1M1 is the fixture because it is an original: the frames are
        # resolved onto real campaign geometry -- diagonals, steps, portals,
        # bottom-swapped walls -- not onto a rectangle chosen to pass.
        runs, moved = self._invariant(_campaign("E1M1"))
        self.assertGreater(runs, 10, "no runs were tested")
        self.assertEqual(moved, 0,
                         "the editor would still change a resolved run")

    def test_the_same_holds_on_a_map_with_curved_geometry(self):
        runs, moved = self._invariant(_campaign("E3M1"))
        self.assertGreater(runs, 10)
        self.assertEqual(moved, 0)

    def test_the_invariance_test_can_fail(self):
        # A gate that cannot fail measures nothing. Nudge one wall's panning
        # after resolving and the editor must put it back.
        from bloodmap.texture_frame import (
            WallRunFrame, auto_align_walls, resolve_run, run_from,
            sector_index)

        disk = _campaign("E1M1")
        sizes = _sizes()
        owners = sector_index(disk)
        for start in range(len(disk.walls)):
            tile = int(disk.walls[start].fields["picnum"])
            if tile not in sizes or not sizes[tile][0]:
                continue
            run = run_from(disk, start, art_sizes=sizes, owners=owners)
            if len(run) < 3:
                continue
            resolve_run(disk, run, WallRunFrame(tile=tile), sizes, owners)
            fields = disk.walls[run[1]].fields
            fields["x_panning"] = (int(fields["x_panning"]) + 7) % 64
            before = int(fields["x_panning"])
            auto_align_walls(disk, run[0], flags=0x01, art_sizes=sizes,
                             owners=owners)
            self.assertNotEqual(int(fields["x_panning"]), before,
                                "the editor did not notice a nudged wall")
            return
        self.skipTest("no run of three same-tile walls found")


class ARunIsNotASectorLoop(unittest.TestCase):
    """The difference that makes a facade continue past its own doorway."""

    def test_a_run_crosses_into_the_neighbouring_sector(self):
        # ED32_AutoAlignWalls:3142-3143 steps `wall[wall[w1].nextwall].point2`,
        # which leaves the sector. `texture_align.align_wall_runs` iterates one
        # sector's wall list and cannot, which is why it seams every opening.
        from bloodmap.texture_frame import run_from, sector_index

        disk = _campaign("E1M1")
        owners = sector_index(disk)
        crossed = 0
        for start in range(400):
            run = run_from(disk, start, art_sizes=_sizes(), owners=owners)
            if len({owners[w] for w in run}) > 1:
                crossed += 1
        self.assertGreater(crossed, 0,
                           "no run left the sector it started in")

    def test_the_partition_covers_each_wall_once(self):
        from bloodmap.texture_frame import run_partition

        disk = _campaign("E1M1")
        runs = run_partition(disk, art_sizes=_sizes())
        seen = [w for run in runs for w in run]
        self.assertEqual(len(seen), len(set(seen)),
                         "a wall belongs to two runs")


class MovingWallsAreNotProjectable(unittest.TestCase):
    """The law the zoo's read-back taught this pass on its first run."""

    def test_a_movers_walls_are_left_to_their_mechanism(self):
        # A curtain's fabric repeat is authored for the span the cloth hangs
        # ACROSS and the file is saved at the gathered pose, so a scale taken
        # from the drawn length replaces a designed 2.0 with 0.02.
        from bloodmap.format import read_map
        from bloodmap.texture_frame import MOVING_SECTOR_TYPES, frame_map

        path = VANILLA / "DOOR-CURTAINS.map"
        if not path.exists():
            self.skipTest(f"{path} is absent")
        disk = read_map(path)
        moving = [i for i, s in enumerate(disk.sectors)
                  if int(s.fields["type"]) in MOVING_SECTOR_TYPES]
        self.assertTrue(moving, "the tutorial has no mover to protect")
        before = {}
        for sector_id in moving:
            fields = disk.sectors[sector_id].fields
            start = int(fields["wall_ptr"])
            for wall in range(start, start + int(fields["wall_count"])):
                before[wall] = int(disk.walls[wall].fields["x_repeat"])
        report = frame_map(disk, art_sizes=_sizes())
        self.assertEqual(report["walls_left_to_their_mechanism"], len(before))
        for wall, repeat in before.items():
            self.assertEqual(int(disk.walls[wall].fields["x_repeat"]), repeat,
                             f"wall {wall} of a mover was re-projected")


class TheCampaignSetsTheStandard(unittest.TestCase):
    """The gate is calibrated on the corpus, and the corpus passes it."""

    def test_no_campaign_map_trips_the_continuity_rule(self):
        # The threshold is each class's campaign FLOOR, so this holds by
        # construction -- and it is worth asserting because the first version
        # of the rule used the aggregate and flagged five campaign maps with
        # their own minimum.
        from bloodmap import rules_blood                       # noqa: F401
        from bloodmap.format import read_map
        from bloodmap.patterns import list_corpus_maps
        from bloodmap.rules import RULES

        rule = RULES["texture-continues-across-a-join"]
        entries = list(list_corpus_maps(population="blood-campaign"))
        if not entries:
            self.skipTest("no campaign corpus")
        _sizes()
        flagged = []
        for entry in entries:
            finding = rule.check(read_map(entry.path))
            if finding.violations:
                flagged.append(entry.path.stem.upper())
        self.assertEqual(flagged, [])

    def test_the_rule_fires_on_a_map_whose_runs_were_never_stated(self):
        # Fail-first, on the real defect: strip every panning and the map is
        # what a per-wall generator produces -- a restart at every vertex.
        from bloodmap import rules_blood                       # noqa: F401
        from bloodmap.rules import RULES

        disk = _campaign("E1M1")
        _sizes()
        for wall in disk.walls:
            wall.fields["x_panning"] = 0
            wall.fields["y_panning"] = 0
        finding = RULES["texture-continues-across-a-join"].check(disk)
        self.assertTrue(finding.violations,
                        "a map with every panning zeroed must be a finding")

    def test_a_deliberate_restart_is_never_a_finding(self):
        # The campaign restarts x at outside corners (19-25%) and between step
        # bands (30%). Those axes are excluded, or the gate would push built
        # maps away from the corpus rather than toward it.
        from bloodmap.rules_blood import (
            CAMPAIGN_CONTINUITY, DELIBERATE_RESTART)

        for name in ("reflex solid-solid", "reflex solid-portal",
                     "reflex portal-portal", "bend portal-portal"):
            self.assertLess(CAMPAIGN_CONTINUITY[name]["x"], DELIBERATE_RESTART,
                            f"{name} x should read as a deliberate restart")
            # and the same classes are still checked in y
            self.assertGreaterEqual(CAMPAIGN_CONTINUITY[name]["y"],
                                    DELIBERATE_RESTART, name)


if __name__ == "__main__":
    unittest.main()
