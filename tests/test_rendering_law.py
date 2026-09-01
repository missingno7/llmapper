"""The rendering law as a gate, and the usage table re-mined by what is seen.

Written to FAIL FIRST: the fixture is the city's stage curtain as committed
in `projects/blood-city/level/blood-city-current.MAP` (sector 37, walls
276-278: fabric 146 on unmasked two-sided walls whose neighbour's ceiling is
higher and whose floors are flush), reduced to a two-box map so the test
outlives the curtain's rebuild. The corpus map itself is checked too, and
skipped once the defect is gone.
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
    the auditorium (ceiling -40960, same floor). The shared wall is 1 (stage
    side, wearing the fabric) and 7 (house side, wearing the house tile).
    """
    def box(points, ptr, picnum, ceiling):
        walls = [_record(WALL_FIELDS, x=x, y=y, point2=ptr + (i + 1) % 4,
                         next_wall=-1, next_sector=-1, picnum=picnum,
                         x_repeat=8, y_repeat=8)
                 for i, (x, y) in enumerate(points)]
        sector = _record(SECTOR_FIELDS, wall_ptr=ptr, wall_count=4,
                         ceiling_z=ceiling, floor_z=8192)
        return sector, walls

    s0, w0 = box([(0, 0), (1024, 0), (1024, 2048), (0, 2048)], 0, fabric,
                 stage_ceiling)
    s1, w1 = box([(1024, 0), (4096, 0), (4096, 2048), (1024, 2048)], 4, house,
                 house_ceiling)
    if not one_sided:
        cstat = 16 if masked else 0
        w0[1].fields.update(next_wall=7, next_sector=1, cstat=cstat,
                            over_picnum=fabric if masked else 0)
        w1[3].fields.update(next_wall=1, next_sector=0, cstat=cstat,
                            over_picnum=fabric if masked else 0)
    return DiskMap(version=7, header={}, extra_header=None, sky_offsets=[],
                   sectors=[s0, s1], walls=w0 + w1, sprites=[],
                   source_crc32=0, source_size=0)


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

    def test_the_committed_city_curtain_is_caught(self):
        # Sector 37 walls 276-278 as committed. Once the curtain is rebuilt
        # the fixture above carries the defect and this test stands down.
        if not CITY.exists():
            self.skipTest("no city build")
        from bloodmap.format import read_map

        disk = read_map(CITY)
        walls = [disk.walls[w].fields for w in (276, 277, 278)]
        defect = all(int(f["picnum"]) == 146 and int(f["next_sector"]) >= 0
                     and not int(f["cstat"]) & 48 for f in walls)
        if not defect:
            self.skipTest("the city curtain no longer carries the defect")
        found = self.rules["wall-tile-is-drawn-somewhere"].check(disk)
        self.assertIn("tile[146]", [v.location for v in found.violations])
        per_wall = self.rules["wall-draws-its-own-tile"].check(disk)
        flagged = {v.location for v in per_wall.violations}
        self.assertTrue({"wall[276]", "wall[277]", "wall[278]"} <= flagged)

    def test_both_rules_are_registered_with_an_engine_source(self):
        for rule_id in ("wall-draws-its-own-tile", "wall-tile-is-drawn-somewhere"):
            rule = self.rules[rule_id]
            self.assertTrue(rule.source.startswith("NBlood/source/build/src/engine.cpp"))
            self.assertGreater(len(rule.because), 200)

    def test_the_gate_is_graded_as_a_warning_and_the_habit_as_a_note(self):
        # Measured 2026-09-01 over 43 campaign maps: 97 of 1979 authored
        # wall tiles are drawn nowhere in their map (4.9%); per wall it is
        # 28539 of 113253 (25%). The grades file is where severity lives.
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

    def test_the_mirror_tile_is_never_a_drawn_wall_overlay(self):
        # mirrors.cpp turns picnum 504 into a one-way overlay at load; the
        # map itself stores it as a white wall's picnum.
        from bloodmap.usage_kinds import slots_for

        slots = slots_for(504, self.table)
        self.assertEqual(slots.get("one_sided_middle"), 7)
        self.assertNotIn("oneway_middle", slots)

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
        disk = _stage_and_house(fabric=502, house=502, house_ceiling=-16384)
        self.assertEqual(rendered_wall_uses(disk, table=self.table), [])


class SchemaTest(unittest.TestCase):
    def test_v2_sits_beside_v1_and_says_what_changed(self):
        if not V2.exists():
            self.skipTest("no v2 table")
        data = json.loads(V2.read_text(encoding="utf-8"))
        self.assertEqual(data["grade"], "DERIVED")
        self.assertIn("v1 counted where a tile is STORED", data["about"])
        self.assertIn("engine.cpp:4685", data["engine"])


if __name__ == "__main__":
    unittest.main()
