"""The rendering law as a gate, and the usage table re-mined by what is seen.

Written to FAIL FIRST on a defect that has since been fixed, which is why
the fixture is the map as it was COMMITTED rather than the map on disk:
`projects/blood-city/level/blood-city-current.MAP` at **8c42701**, sector 37
walls 276-278, fabric 146 on unmasked two-sided walls whose neighbour's
ceiling is higher and whose floors are flush. `_map_at_revision` pulls that
blob out of the object store with `git cat-file`, so the anchor outlives
P1's rebuild instead of quietly standing down. The same defect is also built
by hand as a two-box map, so the gate is testable without git.
"""

from __future__ import annotations

import json
import unittest
from pathlib import Path

from bloodmap.format import SECTOR_FIELDS, WALL_FIELDS
from bloodmap.model import DiskMap, DiskObject

ROOT = Path(__file__).resolve().parents[1]
CITY = ROOT / "projects" / "blood-city" / "level" / "blood-city-current.MAP"
V2 = ROOT / "knowledge" / "blood" / "design" / "usage-kinds-v2.json"


def _record(fields, **values):
    record = {name: 0 for name, _ in fields}
    record.update(values)
    return DiskObject(fields=record)


def _stage_and_house(fabric=146, house=119, *, house_ceiling=-40960,
                     stage_ceiling=-16384, masked=False, one_sided=False):
    """The Aldermack's proscenium, reduced.

    Sector 0 is the curtain sector (ceiling -16384, floor 8192), sector 1
    the auditorium (ceiling -40960, same floor). Every wall of both boxes
    wears the HOUSE tile; only the shared wall -- 1 on the stage side, 7 on
    the house side -- wears the fabric, because the defect under test is a
    material that exists nowhere else in the map. (An earlier draft of this
    fixture painted the whole stage box with the fabric, which made the
    stage's three white walls draw it and the map-scoped gate rightly saw
    nothing wrong.)
    """
    def box(points, ptr, picnum, ceiling):
        walls = [_record(WALL_FIELDS, x=x, y=y, point2=ptr + (i + 1) % 4,
                         next_wall=-1, next_sector=-1, picnum=picnum,
                         x_repeat=8, y_repeat=8)
                 for i, (x, y) in enumerate(points)]
        sector = _record(SECTOR_FIELDS, wall_ptr=ptr, wall_count=4,
                         ceiling_z=ceiling, floor_z=8192)
        return sector, walls

    s0, w0 = box([(0, 0), (1024, 0), (1024, 2048), (0, 2048)], 0, house,
                 stage_ceiling)
    s1, w1 = box([(1024, 0), (4096, 0), (4096, 2048), (1024, 2048)], 4, house,
                 house_ceiling)
    w0[1].fields.update(picnum=fabric)
    if not one_sided:
        cstat = 16 if masked else 0
        w0[1].fields.update(next_wall=7, next_sector=1, cstat=cstat,
                            over_picnum=fabric if masked else 0)
        w1[3].fields.update(next_wall=1, next_sector=0, cstat=cstat,
                            over_picnum=0)
    return DiskMap(version=7, header={}, extra_header=None, sky_offsets=[],
                   sectors=[s0, s1], walls=w0 + w1, sprites=[],
                   source_crc32=0, source_size=0)


def _map_at_revision(case, revision, path):
    """A map as it was committed, read without touching the working tree.

    The fail-first fixture has to outlive the fix. `git cat-file` gives the
    blob straight from the object store; when git or the revision is not
    there (a source export, a shallow clone) the test stands down rather
    than passing vacuously.
    """
    import subprocess
    import tempfile

    from bloodmap.format import read_map

    try:
        blob = subprocess.run(["git", "cat-file", "blob", revision + ":" + path],
                              cwd=ROOT, stdout=subprocess.PIPE,
                              stderr=subprocess.DEVNULL, check=True).stdout
    except (OSError, subprocess.CalledProcessError):
        case.skipTest(revision + ":" + path + " is not in this checkout")
    with tempfile.NamedTemporaryFile(suffix=".MAP", delete=False) as handle:
        handle.write(blob)
        name = handle.name
    try:
        return read_map(name)
    finally:
        Path(name).unlink(missing_ok=True)


class FailFirstTest(unittest.TestCase):
    def setUp(self):
        import bloodmap.rules_blood                       # noqa: F401
        from bloodmap.rules import RULES

        self.rules = RULES

    def test_the_reduced_city_curtain_fails_the_gate(self):
        # The defect: the fabric is on screen nowhere in the map. The house
        # draws its own tile on the 24576-unit step above the proscenium.
        found = self.rules["wall-tile-is-drawn-somewhere"].check(
            _stage_and_house())
        self.assertEqual([v.location for v in found.violations], ["tile[146]"])
        self.assertIn("wall(s) (1)", found.violations[0].detail)
        self.assertIn("neighbour's ceiling is not lower", found.violations[0].detail)
        # And per wall: the fabric wall, and nothing else -- 119 is drawn.
        per_wall = self.rules["wall-draws-its-own-tile"].check(_stage_and_house())
        self.assertEqual([v.location for v in per_wall.violations], ["wall[1]"])
        self.assertEqual(per_wall.population, 8)

    def test_masking_the_wall_makes_the_fabric_draw(self):
        # The pocket dialect: cstat 16 with the fabric as over_picnum puts it
        # in the masked middle, full height of the opening.
        found = self.rules["wall-tile-is-drawn-somewhere"].check(
            _stage_and_house(masked=True))
        self.assertEqual(found.violations, ())

    def test_a_one_sided_fin_makes_the_fabric_draw(self):
        # The void-slot dialect: the fabric on a white wall.
        found = self.rules["wall-tile-is-drawn-somewhere"].check(
            _stage_and_house(one_sided=True))
        self.assertEqual(found.violations, ())

    def test_a_lower_stage_ceiling_puts_the_fabric_on_a_step(self):
        # If the curtain sector's ceiling were the higher one, its own wall
        # would draw the fabric on the upper step.
        found = self.rules["wall-tile-is-drawn-somewhere"].check(
            _stage_and_house(house_ceiling=-16384, stage_ceiling=-40960))
        self.assertEqual(found.violations, ())

    def test_the_city_as_committed_before_the_curtain_rebuild_is_caught(self):
        # The real fail-first, and a real map rather than a reduction:
        # blood-city-current.MAP as committed at 8c42701, before P1 rebuilt
        # the proscenium. Sector 37 walls 276-278 wear 146, two-sided into
        # sector 23, cstat 0 (277 carries the 0x4000 move flag), s37 ceiling
        # -16384 against s23's -40960 with flush floors at 8192. Neither
        # step exists on the curtain's side and neither bit reaches the
        # middle, so the fabric is on screen nowhere in the level.
        disk = _map_at_revision(
            self, "8c42701", "projects/blood-city/level/blood-city-current.MAP")
        found = self.rules["wall-tile-is-drawn-somewhere"].check(disk)
        self.assertIn("tile[146]", [v.location for v in found.violations])
        per_wall = self.rules["wall-draws-its-own-tile"].check(disk)
        flagged = {v.location for v in per_wall.violations}
        self.assertTrue({"wall[276]", "wall[277]", "wall[278]"} <= flagged)

    def test_the_rebuilt_city_curtain_passes_the_same_gate(self):
        # And the fix is visible to the same gate: P1's one-sided fin puts
        # 146 in a one_sided_middle, so the map no longer loses the tile.
        # Five OTHER tiles are still lost -- the districts' `opening`
        # materials on flush doorway thresholds -- which is the finding this
        # rule was built to make and is in the owner review queue.
        if not CITY.exists():
            self.skipTest("no city build")
        from bloodmap.format import read_map

        found = self.rules["wall-tile-is-drawn-somewhere"].check(read_map(CITY))
        self.assertNotIn("tile[146]", [v.location for v in found.violations])

    def test_both_rules_are_registered_with_an_engine_source(self):
        for rule_id in ("wall-draws-its-own-tile", "wall-tile-is-drawn-somewhere"):
            rule = self.rules[rule_id]
            self.assertTrue(rule.source.startswith("NBlood/source/build/src/engine.cpp"))
            self.assertGreater(len(rule.because), 200)

    def test_the_gate_is_graded_as_a_warning_and_the_habit_as_a_note(self):
        # Measured 2026-09-01 over 43 campaign maps: 97 of 1979 authored
        # wall tiles are drawn nowhere in their map (4.9%); per wall it is
        # 28539 of 107785 (26.5%). The grades file is where severity lives.
        from bloodmap.rules import load_grades

        grades = load_grades()
        if "wall-tile-is-drawn-somewhere" not in grades:
            self.skipTest("the rules have not been graded")
        self.assertEqual(grades["wall-tile-is-drawn-somewhere"].severity, "warning")
        self.assertEqual(grades["wall-draws-its-own-tile"].severity, "note")


class RenderedUsageTableTest(unittest.TestCase):
    def setUp(self):
        from bloodmap.usage_kinds import load_rendered

        self.table = load_rendered()
        if not self.table.get("usage"):
            self.skipTest("the rendered usage-kind table has not been compiled")

    def test_the_table_is_by_rendered_slot(self):
        self.assertEqual(self.table["schema_version"], 2)
        self.assertEqual(self.table["maps"], 43)
        self.assertIn("one_sided_middle", self.table["band_totals"])
        self.assertNotIn("wall_two_sided", self.table["band_totals"])

    def test_tile_146_is_fabric_on_white_walls_and_floor_steps(self):
        # v1 said wall_two_sided 129. Rendered: 71 of those show on a lower
        # step, 3 on an upper step, and 55 walls wearing it draw nowhere
        # (E1M1 1203-1207 among them). NONE is a masked middle: the pocket
        # dialect's masked overlay in DOOR-CURTAINSD s4 is tile 1060, and
        # the campaign has no masked 146 at all.
        from bloodmap.usage_kinds import slots_for

        slots = slots_for(146, self.table)
        self.assertEqual(slots["one_sided_middle"], 173)
        self.assertEqual(slots["two_sided_lower"], 71)
        self.assertEqual(slots["two_sided_upper"], 3)
        self.assertEqual(slots["wall_undrawn"], 55)
        self.assertNotIn("masked_middle", slots)
        self.assertEqual(slots["over_unread"], 10)

    def test_the_grate_is_a_masked_middle(self):
        from bloodmap.usage_kinds import attested

        self.assertTrue(attested(502, "masked_middle", self.table))
        self.assertFalse(attested(502, "one_sided_middle", self.table))

    def test_the_mirror_tile_is_read_through_its_load_time_transform(self):
        # mirrors.cpp:466-469 forces CSTAT_WALL_1WAY on and copies 504 into
        # overpicnum before anything is drawn, so the file and the running
        # level disagree about the flags. The campaign stores 504 on eight
        # walls: seven white ones, which draw it either way, and ONE red one
        # (E2M2), which draws a one-way middle only because of that
        # transform. Reading the file's cstat alone would say "drawn
        # nowhere" and the must-draw gate would have to special-case it.
        from bloodmap.render_slots import CSTAT_ONE_WAY, MIRROR_TILE, mirror_pass
        from bloodmap.usage_kinds import slots_for

        self.assertEqual(mirror_pass(MIRROR_TILE, 0, 0),
                         (MIRROR_TILE, CSTAT_ONE_WAY))
        self.assertEqual(mirror_pass(109, 0, 0), (0, 0))
        slots = slots_for(504, self.table)
        self.assertEqual(slots.get("one_sided_middle"), 7)
        self.assertEqual(slots.get("oneway_middle"), 1)

    def test_the_mask_law_restated_by_band_names_the_same_two_tiles(self):
        law = self.table["mask_law_rendered"]
        if not law.get("art_read"):
            self.skipTest("the ART was not readable when the table was mined")
        self.assertEqual(sorted(law["masked_tiles_on_opaque_bands"]),
                         ["142", "2464"])

    def test_the_gate_judges_walls_by_band(self):
        # 502 (a grate) as a white wall's picnum: v1 would say "not attested
        # as wall_one_sided"; v2 says "not attested in one_sided_middle".
        from bloodmap.usage_kinds import rendered_wall_uses, unattested_uses

        disk = _stage_and_house(fabric=502, one_sided=True)
        found = rendered_wall_uses(disk, table=self.table)
        self.assertTrue(any(f["picnum"] == 502 and f["slot"] == "one_sided_middle"
                            for f in found))
        merged = unattested_uses(disk, rendered=self.table)
        self.assertEqual([f for f in merged if f["picnum"] == 502], found)

    def test_an_undrawn_wall_is_not_this_checks_business(self):
        from bloodmap.usage_kinds import rendered_wall_uses

        # 502 on a flush, unmasked red wall draws nowhere: no band, no
        # finding here; wall-tile-is-drawn-somewhere owns that.
        disk = _stage_and_house(fabric=502, house_ceiling=-16384)
        self.assertEqual(rendered_wall_uses(disk, table=self.table), [])


class SchemaTest(unittest.TestCase):
    def test_v2_sits_beside_v1_and_says_what_changed(self):
        if not V2.exists():
            self.skipTest("no v2 table")
        data = json.loads(V2.read_text(encoding="utf-8"))
        self.assertEqual(data["grade"], "DERIVED")
        self.assertIn("v1 counted where a tile is STORED", data["about"])
        self.assertIn("engine.cpp:4686", data["engine"])


if __name__ == "__main__":
    unittest.main()
