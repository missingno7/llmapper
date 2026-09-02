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


class TheScaleIsAnAbsoluteNumber(unittest.TestCase):
    """The tests P11 did not have, and the reason it shipped an 8x error.

    `>`-invariance is necessary and NOT sufficient. It compares the resolver
    against the editor's accumulator, and both sides accumulate whatever
    `x_repeat` the resolver chose -- so a resolver that makes every wall eight
    times too narrow is a perfect fixed point of it. Every test here pins an
    ABSOLUTE number instead: what `x_repeat` must be for a wall of a known
    length at a known scale.

    The number comes from the campaign. Texels per 16 world units --
    `x_repeat * 128 / length`, one Build texel step -- has median **1.00**
    over 46873 one-sided campaign walls (quartiles 0.93-1.00) and 1.00 over
    52801 two-sided ones. blood-city and pattern-zoo measured 8.00 after
    8b70d51.
    """

    def _level(self, points, tile=200, tile_size=(64, 64)):
        """A one-sector map with the given outline, walls all wearing `tile`."""
        walls = []
        count = len(points)
        for index, point in enumerate(points):
            walls.append({"fields": {
                "x": point[0], "y": point[1],
                "point2": (index + 1) % count,
                "next_wall": -1, "next_sector": -1, "cstat": 0,
                "picnum": tile, "over_picnum": 0,
                "x_repeat": 8, "y_repeat": 8,
                "x_panning": 0, "y_panning": 0, "shade": 0, "extra": -1}})
        sectors = [{"fields": {
            "wall_ptr": 0, "wall_count": count,
            "floor_z": 0, "ceiling_z": -33280, "type": 0,
            "floor_picnum": tile, "ceiling_picnum": tile,
            "floor_stat": 0, "ceiling_stat": 0,
            "floor_x_panning": 0, "floor_y_panning": 0,
            "floor_shade": 0, "ceiling_shade": 0}}]
        level = type("L", (), {})()
        level.walls = walls
        level.sectors = sectors
        return level, {tile: tile_size}

    def test_a_1024_wall_at_natural_scale_gets_x_repeat_8(self):
        # The campaign's own number: a 64-wide tile covers 1024 world units,
        # which is Blood's module. `texture_align.natural_x_repeat` has said
        # length / (2 * tile_width) since long before texture_frame existed.
        from bloodmap.texture_align import natural_x_repeat
        from bloodmap.texture_frame import WallRunFrame, resolve_run

        level, sizes = self._level([(0, 0), (1024, 0), (1024, 1024), (0, 1024)])
        resolve_run(level, [0], WallRunFrame(tile=200), sizes, [0, 0, 0, 0])
        self.assertEqual(int(level.walls[0]["fields"]["x_repeat"]), 8)
        self.assertEqual(int(level.walls[0]["fields"]["x_repeat"]),
                         natural_x_repeat(1024, 64))

    def test_a_512_return_in_the_same_run_gets_four(self):
        # Scale is per unit, so a wall half as long takes half the repeat.
        # This is the owner's "scale changes with wall length" in one line.
        from bloodmap.texture_frame import WallRunFrame, resolve_run

        level, sizes = self._level([(0, 0), (1024, 0), (1024, 512), (0, 512)])
        resolve_run(level, [0, 1], WallRunFrame(tile=200), sizes, [0] * 4)
        self.assertEqual(int(level.walls[0]["fields"]["x_repeat"]), 8)
        self.assertEqual(int(level.walls[1]["fields"]["x_repeat"]), 4)

    def test_the_texel_step_lands_on_the_campaign_median(self):
        # The measurement the gate uses, asserted on a resolved wall: texels
        # per 16 units = x_repeat * 128 / length.
        from bloodmap.texture_frame import WallRunFrame, resolve_run

        for length in (512, 1024, 2048, 4096):
            level, sizes = self._level(
                [(0, 0), (length, 0), (length, 512), (0, 512)])
            resolve_run(level, [0], WallRunFrame(tile=200), sizes, [0] * 4)
            repeat = int(level.walls[0]["fields"]["x_repeat"])
            self.assertAlmostEqual(repeat * 128.0 / length, 1.0, places=6,
                                   msg=f"length {length}")

    def test_cutting_a_run_with_a_doorway_changes_no_scale(self):
        # The whole point of the representation: splitting a wall to hang a
        # doorway off it moves no stone, so it must move no texel. One 4096
        # face against the same face cut into 1024 + 2048 + 1024.
        from bloodmap.texture_frame import WallRunFrame, resolve_run

        whole, sizes = self._level([(0, 0), (4096, 0), (4096, 512), (0, 512)])
        resolve_run(whole, [0], WallRunFrame(tile=200), sizes, [0] * 4)
        one = int(whole.walls[0]["fields"]["x_repeat"])

        cut, sizes = self._level([(0, 0), (1024, 0), (3072, 0), (4096, 0),
                                  (4096, 512), (0, 512)])
        resolve_run(cut, [0, 1, 2], WallRunFrame(tile=200), sizes, [0] * 6)
        pieces = [int(cut.walls[i]["fields"]["x_repeat"]) for i in (0, 1, 2)]
        self.assertEqual(pieces, [8, 16, 8])
        self.assertEqual(sum(pieces), one,
                         "the cut face consumes a different number of texels")
        # and the phase picks up where each piece left off
        self.assertEqual([int(cut.walls[i]["fields"]["x_panning"])
                          for i in (0, 1, 2)],
                         [0, (8 * 8) % 64, ((8 + 16) * 8) % 64])

    def test_an_explicit_scale_is_honoured_absolutely(self):
        # Twice natural is twice the repeat, so a caller asking for a stretched
        # material gets exactly that and not eight times it.
        from bloodmap.texture_frame import (
            NATURAL_TEXELS_PER_UNIT, WallRunFrame, resolve_run)

        level, sizes = self._level([(0, 0), (1024, 0), (1024, 512), (0, 512)])
        resolve_run(level, [0],
                    WallRunFrame(tile=200,
                                 texels_per_unit=2 * NATURAL_TEXELS_PER_UNIT),
                    sizes, [0] * 4)
        self.assertEqual(int(level.walls[0]["fields"]["x_repeat"]), 16)

    def test_the_natural_scale_is_one_texel_per_sixteen_units(self):
        from bloodmap.texture_frame import NATURAL_TEXELS_PER_UNIT

        self.assertAlmostEqual(NATURAL_TEXELS_PER_UNIT, 1.0 / 16.0)
        # 8 * that * 16 == 1 texel step, i.e. the campaign median
        self.assertAlmostEqual(NATURAL_TEXELS_PER_UNIT * 16, 1.0)


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


class TheMagnitudeGate(unittest.TestCase):
    """A relative check cannot see a uniform error. This one can."""

    def _rule(self):
        from bloodmap import rules_blood                       # noqa: F401
        from bloodmap.rules import RULES

        _sizes()
        return RULES["material-is-drawn-at-campaign-size"]

    def test_the_campaign_is_inside_its_own_envelope(self):
        from bloodmap.format import read_map
        from bloodmap.patterns import list_corpus_maps

        rule = self._rule()
        entries = list(list_corpus_maps(population="blood-campaign"))
        if not entries:
            self.skipTest("no campaign corpus")
        flagged = [entry.path.stem.upper() for entry in entries
                   if rule.check(read_map(entry.path)).violations]
        self.assertEqual(flagged, [])

    def test_it_fires_on_the_regression_it_was_written_for(self):
        # THE FAIL-FIRST CASE, reproduced rather than stored: multiplying
        # every x_repeat by eight is exactly what `resolve_run` did between
        # 8b70d51 and this commit, and it is invisible to every relative
        # check in the project because each wall's neighbour is wrong by the
        # same factor.
        rule = self._rule()
        disk = _campaign("E1M1")
        self.assertEqual(rule.check(disk).violations, ())
        for wall in disk.walls:
            wall.fields["x_repeat"] = min(255, int(wall.fields["x_repeat"]) * 8)
        found = rule.check(disk).violations
        self.assertTrue(found, "an 8x map must be a finding")
        self.assertIn("outside", found[0].detail)

    def test_the_relative_gate_SCORES_THE_BROKEN_MAP_HIGHER(self):
        # Worse than blind. At eight times natural every `x_repeat` is a
        # multiple of 8, so every wall consumes a whole multiple of 64 texels
        # and the panning never advances from zero -- so every join
        # "continues" trivially. Measured on E1M1: `bend solid-portal` 59% at
        # natural against 77% at 8x, `collinear portal-portal` 64% against
        # 89%, `reflex solid-solid` 9% against 36%. Not one class falls.
        #
        # So the continuity gate rewarded the regression, which is why P11's
        # class table looked better than the fixed build's does. Only an
        # absolute measure can tell the two apart.
        from bloodmap.texture_frame import (
            WallRunFrame, continuity_rows, resolve_run, run_partition,
            sector_index)

        from bloodmap.texture_frame import NATURAL_TEXELS_PER_UNIT

        sizes = _sizes()

        def resolved(scale):
            disk = _campaign("E1M1")
            owners = sector_index(disk)
            for run in run_partition(disk, art_sizes=sizes, owners=owners):
                tile = int(disk.walls[run[0]].fields["picnum"])
                resolve_run(disk, run,
                            WallRunFrame(tile=tile, texels_per_unit=scale),
                            sizes, owners)
            return disk

        natural = resolved(NATURAL_TEXELS_PER_UNIT)
        eight_times = resolved(NATURAL_TEXELS_PER_UNIT * 8)
        good = continuity_rows(natural, sizes)
        broken = continuity_rows(eight_times, sizes)
        for name, row in good.items():
            if row["n"] < 30:
                continue
            self.assertGreaterEqual(
                broken[name]["x"] / broken[name]["n"] + 0.02,
                row["x"] / row["n"],
                f"{name}: the 8x map should score at least as well, which is "
                f"the whole problem")
        # and only the magnitude gate can tell them apart
        self.assertEqual(self._rule().check(natural).violations, ())
        self.assertTrue(self._rule().check(eight_times).violations)


class ANotchInAFacade(unittest.TestCase):
    """The owner's point: scale follows length, phase follows height.

    A facade with things cut into it is where the per-wall representation did
    its worst damage, because a notch changes both quantities at once. The
    recess is shorter than the face it sits in, so its walls need a different
    `x_repeat` at the SAME texels-per-unit; and it has its own lower ceiling,
    so a wall pegged to that ceiling starts the material at a different
    height. Get the first wrong and the stone is a different size inside the
    opening; get the second wrong and the courses step at every reveal.

    The fixture is a facade 4096 long with a 512-deep display recess and a
    doorway cut into it, built by hand so every number is checkable:

        (0,0) ---- (1024,0)                    (3072,0) ---- (4096,0)
                      |                            |
                   (1024,512) --- (3072,512)  [the recess, 512 deep]
    """

    TILE = 200
    SIZE = (64, 64)

    def _facade(self):
        """A facade run, a recess sector, and a doorway sector."""
        #: sector 0: the street, whose north face is the facade run.
        #: sector 1: the recess, 2048 x 512, with a ceiling 12288 lower than
        #: the street's -- deliberately NOT 16384. At `y_repeat` 8 on a
        #: 64-high tile the panning offset is `dz / 64`, so a 16384 drop wraps
        #: to exactly zero and a fixture built on it would pass whatever the
        #: resolver did. A sill is added only by the both-steps test, so the
        #: mouth wall has exactly one step until then.
        #: sector 2: the doorway, a 1024 opening at the east end.
        street = [(0, 0), (1024, 0), (1024, 512), (3072, 512), (3072, 0),
                  (4096, 0), (4096, -4096), (0, -4096)]
        recess = [(1024, 0), (3072, 0), (3072, 512), (1024, 512)]
        walls = []
        sectors = []

        def add(points, floor_z, ceiling_z):
            start = len(walls)
            for index, point in enumerate(points):
                walls.append({"fields": {
                    "x": point[0], "y": point[1],
                    "point2": start + (index + 1) % len(points),
                    "next_wall": -1, "next_sector": -1, "cstat": 0,
                    "picnum": self.TILE, "over_picnum": 0,
                    "x_repeat": 8, "y_repeat": 8, "x_panning": 0,
                    "y_panning": 0, "shade": 0, "extra": -1}})
            sectors.append({"fields": {
                "wall_ptr": start, "wall_count": len(points),
                "floor_z": floor_z, "ceiling_z": ceiling_z, "type": 0,
                "floor_picnum": self.TILE, "ceiling_picnum": self.TILE,
                "floor_stat": 0, "ceiling_stat": 0, "floor_x_panning": 0,
                "floor_y_panning": 0, "floor_shade": 0, "ceiling_shade": 0}})
            return start

        street_start = add(street, 0, -32768)
        recess_start = add(recess, 0, -20480)
        level = type("L", (), {})()
        level.walls = walls
        level.sectors = sectors
        #: The street's wall 2 (1024,512)->(3072,512) is the recess mouth seen
        #: from the street; the recess's wall 0 faces back. Pair them.
        mouth = street_start + 2
        back = recess_start + 0
        for a, b in ((mouth, back), (back, mouth)):
            level.walls[a]["fields"]["next_wall"] = b
        level.walls[mouth]["fields"]["next_sector"] = 1
        level.walls[back]["fields"]["next_sector"] = 0
        return level, {self.TILE: self.SIZE}, street_start, recess_start

    def test_each_wall_takes_the_repeat_its_own_length_asks_for(self):
        # (a) One scale, four lengths: 1024, 512, 2048, 512, 1024. A notch
        # does not change how big the stone is, only how much of it there is.
        from bloodmap.texture_frame import WallRunFrame, resolve_run

        level, sizes, street, _recess = self._facade()
        run = [street + i for i in (0, 1, 2, 3, 4)]
        resolve_run(level, run, WallRunFrame(tile=self.TILE), sizes,
                    [0] * len(level.walls))
        repeats = [int(level.walls[w]["fields"]["x_repeat"]) for w in run]
        self.assertEqual(repeats, [8, 4, 16, 4, 8])
        for wall, repeat in zip(run, repeats):
            length = abs(int(level.walls[level.walls[wall]["fields"]["point2"]]
                             ["fields"]["x"]) - int(level.walls[wall]["fields"]["x"])) \
                or abs(int(level.walls[level.walls[wall]["fields"]["point2"]]
                           ["fields"]["y"]) - int(level.walls[wall]["fields"]["y"]))
            self.assertAlmostEqual(repeat * 128.0 / length, 1.0, places=6)

    def test_the_phase_follows_the_runs_v0_not_the_recesss_own_ceiling(self):
        # (b) The recess ceiling is 16384 higher than the street's, so a wall
        # pegged to it would start the material half a storey up and every
        # course inside the opening would step. `frame.v0` is a WORLD z and it
        # wins for every wall of the run.
        from bloodmap.texture_frame import (
            WallRunFrame, join_continues, resolve_run)

        level, sizes, street, _recess = self._facade()
        owners = [0] * 8 + [1] * 4
        run = [street + i for i in (0, 1, 2, 3, 4)]
        resolve_run(level, run, WallRunFrame(tile=self.TILE, v0=-32768),
                    sizes, owners)
        #: The invariant is NOT that every wall shares a `y_panning` -- the
        #: mouth wall pegs to the recess ceiling and MUST be offset to
        #: compensate, which is precisely what AlignWalls's y term is for. It
        #: is that the material lands at the same world height everywhere,
        #: and the way to check that without restating the resolver is the
        #: editor's own pairwise predicate.
        self.assertNotEqual(
            int(level.walls[street + 2]["fields"]["y_panning"]), 0,
            "the mouth wall pegs lower and must carry an offset; a zero here "
            "means the fixture has no phase problem to solve")
        for this, nxt in zip(run, run[1:]):
            _x_ok, y_ok = join_continues(level, this, nxt, self.SIZE, owners)
            self.assertTrue(y_ok, f"the phase breaks between {this} and {nxt}")

    def test_the_phase_check_can_fail(self):
        # Zero the mouth wall's compensation by hand -- which is what a
        # per-wall pass that anchors each wall to its own sector does -- and
        # the editor's predicate says the phase is broken on both sides of it.
        from bloodmap.texture_frame import (
            WallRunFrame, join_continues, resolve_run)

        level, sizes, street, _recess = self._facade()
        owners = [0] * 8 + [1] * 4
        run = [street + i for i in (0, 1, 2, 3, 4)]
        resolve_run(level, run, WallRunFrame(tile=self.TILE, v0=-32768),
                    sizes, owners)
        level.walls[street + 2]["fields"]["y_panning"] = 0
        broken = [(a, b) for a, b in zip(run, run[1:])
                  if not join_continues(level, a, b, self.SIZE, owners)[1]]
        self.assertEqual(len(broken), 2,
                         "a wall anchored to its own sector breaks the phase "
                         "on both sides of itself")

    def test_without_a_shared_v0_the_mouth_wall_breaks_the_phase(self):
        # The same fixture proves the check can fail: peg the mouth wall to
        # its own sector's step instead and the phase moves. This is what the
        # per-wall representation did at every reveal.
        from bloodmap.texture_frame import c_div, sector_index, wall_z_peg

        level, sizes, street, _recess = self._facade()
        owners = sector_index(level)
        mouth = street + 2
        #: GetWallZPeg on a two-sided wall with no cstat 4 takes the step, and
        #: the recess ceiling is the top step here.
        self.assertEqual(wall_z_peg(level, mouth, owners), -20480)
        self.assertEqual(wall_z_peg(level, street, owners), -32768)
        offset = c_div((-20480 - -32768) * 8, self.SIZE[1] << 3)
        self.assertNotEqual(offset % 256, 0,
                            "the fixture must actually have a phase break in "
                            "it, or this proves nothing")

    def test_cstat_four_pegs_the_header_back_to_the_facades_own_ceiling(self):
        # (c) `GetWallZPeg` (xmpmaped.cpp:3009-3011): on a two-sided wall
        # kWallOrgOutside takes THIS sector's ceiling instead of the step's,
        # which is how a header continues the facade across an opening.
        # Measured on E3M1: of its 246 walls whose neighbour ceiling is lower,
        # 68 carry the bit -- 27%.
        from bloodmap.texture_frame import (
            WALL_ORG_OUTSIDE, sector_index, wall_z_peg)

        level, sizes, street, _recess = self._facade()
        owners = sector_index(level)
        mouth = street + 2
        self.assertEqual(wall_z_peg(level, mouth, owners), -20480)
        level.walls[mouth]["fields"]["cstat"] |= WALL_ORG_OUTSIDE
        self.assertEqual(wall_z_peg(level, mouth, owners), -32768,
                         "cstat 4 must return the wall's own sector ceiling")

    def test_the_bottom_step_wins_when_a_wall_has_both(self):
        # The clause that is two ifs rather than an if/else
        # (xmpmaped.cpp:3013-3018), transcribed deliberately: a wall with a
        # top step AND a bottom step ends up pegged to the bottom one, because
        # the second assignment overwrites the first.
        from bloodmap.texture_frame import sector_index, wall_z_peg

        level, sizes, street, _recess = self._facade()
        #: give the recess a raised sill as well as its lowered head, which is
        #: E6M1's shopfront: sill up, head down.
        level.sectors[1]["fields"]["floor_z"] = -8192
        owners = sector_index(level)
        mouth = street + 2
        #: street floor 0 > recess floor -8192, so there IS a bottom step, and
        #: the recess ceiling -16384 > street ceiling -32768 gives a top step.
        self.assertEqual(wall_z_peg(level, mouth, owners), -8192)

    def test_the_editor_has_nothing_to_change_on_the_notched_run(self):
        # (d) The acceptance test, on the shape that broke everything else.
        from bloodmap.texture_frame import (
            WallRunFrame, auto_align_walls, resolve_run)

        level, sizes, street, _recess = self._facade()
        owners = [0] * 8 + [1] * 4
        run = [street + i for i in (0, 1, 2, 3, 4)]
        resolve_run(level, run, WallRunFrame(tile=self.TILE), sizes, owners)
        keys = ("x_repeat", "x_panning", "y_repeat", "y_panning", "cstat")
        before = {w: {k: int(level.walls[w]["fields"][k]) for k in keys}
                  for w in run}
        auto_align_walls(level, run[0], flags=0x01, art_sizes=sizes,
                         owners=owners)
        moved = [w for w in run
                 if any(int(level.walls[w]["fields"][k]) != before[w][k]
                        for k in keys)]
        self.assertEqual(moved, [])
