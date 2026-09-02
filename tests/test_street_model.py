"""The kerb, once it is a record somebody declared.

P14's first run could not calibrate this gate and said so. Guessing from a
finished map which two-sided steps are kerbs picks up harbour walls, ledges
and rooftops; the campaign's outdoor kerb tiles are diverse (2490, 67, 110,
2499, 6... the top eight sharing 43% of 1046 records); and the narrower clause
"never the material above it" scored the campaign at 16% against the city's
0%, so the city was already better by it.

`overlay.HeightIsland` changes the question. A kerb is now a record the model
DECLARES, so the rule is about a stated population rather than an inferred
one, it needs no corpus threshold, and it is exact -- the same shape as P13's
record-ownership ledger. That closes owner-queue item 18.

The absolute check beside it (item 17): the rise is 2048, E3M1's on 11 of 11,
asserted as a number and not as "consistent with its neighbours".
"""

import unittest
from pathlib import Path

CITY = Path("projects/blood-city/level/blood-city-current.MAP")
SLICE = Path("projects/blood-city/level/slice1-west-street.MAP")


def _map(path):
    from bloodmap.format import read_map

    if not path.exists():
        raise unittest.SkipTest(f"{path} is not present")
    return read_map(path)


def _road_pieces(disk):
    return [i for i, s in enumerate(disk.sectors)
            if int(s.fields["floor_picnum"]) == 352]


class TheKerbIsWhatABodyOnTheRoadSees(unittest.TestCase):
    """The owner's acceptance test, as a reading."""

    def test_the_committed_city_shows_a_body_the_house(self):
        # FAIL-FIRST, and it is not close: of the 74 faces standing up around
        # blood-city's outdoor sectors, none wears a kerb tile. They wear 380,
        # 417, 384, 28, 393 and 400 -- facade stone, because the band was a
        # hole's edge in a street residue and inherited the building.
        from bloodmap.street_model import sees_the_kerb
        from bloodmap.texture_frame import sector_index

        disk = _map(CITY)
        owners = sector_index(disk)
        outdoor = [i for i, s in enumerate(disk.sectors)
                   if int(s.fields["ceiling_stat"]) & 1]
        tiles = set()
        faces = 0
        for sector_id in outdoor:
            view = sees_the_kerb(disk, sector_id, owners)
            faces += len(view["faces"])
            tiles.update(view["kerb_tiles"])
        self.assertGreater(faces, 50, "nothing to look at")
        self.assertNotIn(6, tiles,
                         "if this ever fails the city has been rebuilt and "
                         "this fixture should become the positive one")

    def test_the_slice_shows_a_body_the_kerb(self):
        from bloodmap.street_model import sees_the_kerb
        from bloodmap.texture_frame import sector_index

        disk = _map(SLICE)
        owners = sector_index(disk)
        roads = _road_pieces(disk)
        self.assertTrue(roads, "the slice has no road")
        for sector_id in roads:
            view = sees_the_kerb(disk, sector_id, owners)
            self.assertEqual(view["kerb_tiles"], [6], f"road s{sector_id}")
            self.assertEqual(view["materials_above"], [4],
                             "and what stands above the kerb is pavement")


class TheDeclaredKerbRule(unittest.TestCase):
    def _declared(self, disk):
        """Every road/pavement boundary in the slice, as the build declares."""
        from bloodmap.texture_frame import sector_index

        owners = sector_index(disk)
        out = []
        for wall_id, wall in enumerate(disk.walls):
            nxt = int(wall.fields["next_sector"])
            if nxt < 0:
                continue
            here = owners[wall_id]
            if int(disk.sectors[here].fields["floor_picnum"]) != 352:
                continue
            if int(disk.sectors[nxt].fields["floor_picnum"]) != 4:
                continue
            face = wall.fields
            after = disk.walls[int(face["point2"])].fields
            out.append({
                "island": f"s{nxt}", "road_piece": f"s{here}",
                "edge": ((int(face["x"]), int(face["y"])),
                         (int(after["x"]), int(after["y"]))),
                "picnum": 6, "rise": 2048})
        return out, owners

    def test_the_slices_declared_kerbs_all_pass(self):
        from bloodmap.street_model import kerb_faults

        disk = _map(SLICE)
        declared, owners = self._declared(disk)
        self.assertTrue(declared, "the slice declares no kerb")
        self.assertEqual(kerb_faults(disk, declared, owners=owners), [])

    def test_a_kerb_wearing_the_pavement_is_a_fault(self):
        # The owner's middle clause: a kerb is not the pavement folded down.
        from bloodmap.street_model import kerb_faults

        disk = _map(SLICE)
        declared, owners = self._declared(disk)
        target = declared[0]
        for wall in disk.walls:
            face = wall.fields
            after = disk.walls[int(face["point2"])].fields
            if ((int(face["x"]), int(face["y"])),
                    (int(after["x"]), int(after["y"]))) == target["edge"]:
                face["picnum"] = 4
        found = kerb_faults(disk, declared, owners=owners)
        self.assertTrue(found)
        self.assertTrue(any("standing above it" in line for line in found),
                        found)

    def test_the_rise_is_checked_absolutely(self):
        # ABSOLUTE: 2048, E3M1's on 11 of 11 kerbs. A kerb consistent with its
        # neighbours at 512 would pass any relative form of this.
        from bloodmap.street_model import KERB_RISE, kerb_faults

        self.assertEqual(KERB_RISE, 2048)
        disk = _map(SLICE)
        declared, owners = self._declared(disk)
        for sector in disk.sectors:
            if int(sector.fields["floor_picnum"]) == 4:
                sector.fields["floor_z"] = int(sector.fields["floor_z"]) + 1536
        found = kerb_faults(disk, declared, owners=owners)
        self.assertTrue(any("steps" in line for line in found), found)


class TheShadowRunsAtTheLevelsSun(unittest.TestCase):
    def test_an_edge_at_the_bearing_passes_and_an_axis_edge_does_not(self):
        from bloodmap.street_model import shadow_edge_faults

        import sys
        level = str(Path("projects/blood-city/level"))
        if level not in sys.path:
            sys.path.insert(0, level)
        try:
            from resolution import (SUN_BEARING_DEGREES,
                                    SUN_BEARING_TOLERANCE_DEGREES)
        except ImportError as error:                   # pragma: no cover
            self.skipTest(str(error))
        disk = _map(SLICE)
        good = [((0, 0), (416, 4096))]
        bad = [((0, 0), (4096, 0))]
        self.assertEqual(shadow_edge_faults(disk, good, SUN_BEARING_DEGREES,
                                            SUN_BEARING_TOLERANCE_DEGREES), [])
        self.assertTrue(shadow_edge_faults(disk, bad, SUN_BEARING_DEGREES,
                                           SUN_BEARING_TOLERANCE_DEGREES))


class TheFrameSurvivesTheCuts(unittest.TestCase):
    """The property the whole overlay model exists to give."""

    def test_the_editor_would_change_nothing_after_a_kerb_and_shadow_cut(self):
        from bloodmap.texture_align import wall_art_sizes
        from bloodmap.texture_frame import (
            auto_align_walls, run_partition, sector_index)

        art = wall_art_sizes()
        if not art:
            self.skipTest("no ART in reference/blood")
        disk = _map(SLICE)
        owners = sector_index(disk)
        keys = ("x_repeat", "x_panning", "y_repeat", "y_panning", "cstat")
        moved = 0
        for run in run_partition(disk, art_sizes=art, owners=owners):
            before = {w: {k: int(disk.walls[w].fields[k]) for k in keys}
                      for w in run}
            auto_align_walls(disk, run[0], flags=0x01, art_sizes=art,
                             owners=owners)
            moved += sum(1 for w in run
                         if any(int(disk.walls[w].fields[k]) != before[w][k]
                                for k in keys))
        self.assertEqual(moved, 0,
                         "a road cut by a kerb and a shadow must still be a "
                         "fixed point of the editor's own align")

    def test_the_road_is_drawn_at_the_campaigns_size(self):
        # ABSOLUTE, and the check P13 added after shipping an 8x map: texels
        # per sixteen world units, median 1.00 over the campaign.
        from bloodmap import rules_blood                       # noqa: F401
        from bloodmap.rules import RULES
        from bloodmap.texture_align import wall_art_sizes

        if not wall_art_sizes():
            self.skipTest("no ART in reference/blood")
        finding = RULES["material-is-drawn-at-campaign-size"].check(_map(SLICE))
        self.assertEqual(finding.violations, ())


if __name__ == "__main__":
    unittest.main()
