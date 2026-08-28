"""A level painted in one material, lit to one brightness.

The discriminator's four worst readings on this level were `visual.contrast` 18
against 48, `composition.wall` 0.665 against 0.501, `shade_spread` 4.4 against
11.2 and `tile_variety` 4 against 6. They are not four faults. A room with one
wall tile and one shade has nothing in it for the eye to measure the room by,
and every one of those numbers is a way of saying so.

Two corpus facts fix most of it, and neither is about taste.

**Openings are dressed and the field between them is not.** Blood's playable
sectors carry a median of 2 distinct wall tiles; only 37% use one, against this
level's 90%. And the division is structural: of the 8,320 campaign rooms with
more than one wall tile, 74% put a different tile on their two-sided walls than
on their solid ones. Rubble in the spans, ashlar at the jambs, which is how
masonry is built.

**The level was uniformly too bright.** Campaign medians are 31 for a wall, 30
for a floor, 34 for a ceiling; this level sat at 18, 22 and 16. That is not a
style, it is a level with the lights left on -- and it is why its fullbright
sprites did not read as bright. A frame's contrast is the distance from its
brightest surface to its darkest, and in the campaign that is a burning sprite
at -128 against a wall at 31 or more. This level had the sprites (more per
sector than the campaign's q3) and nothing dark to show them against.
"""

from __future__ import annotations

import glob
import re
import statistics
import unittest
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
MAPS = ROOT / "maps" / "blood"
CANDIDATE = ROOT / "projects" / "reasoned-authoring-v1" / "level" / "candidate-v5.MAP"


def campaign_maps() -> list[str]:
    return [
        path for path in sorted(glob.glob(str(MAPS / "*.MAP")))
        if re.match(r"^E[1-46]M[1-9]$", Path(path).stem.upper())
    ]


def rooms(disk):
    """(distinct wall tiles, wall shade spread) for each playable sector."""
    from bloodmap.reachability import design_sectors

    playable = set(design_sectors(disk))
    out = []
    for index, sector in enumerate(disk.sectors):
        if index not in playable:
            continue
        fields = sector.fields
        start, count = int(fields["wall_ptr"]), int(fields["wall_count"])
        if count < 4:
            continue
        tiles = Counter()
        shades = []
        for wall in range(start, start + count):
            face = disk.walls[wall].fields
            tiles[int(face["picnum"])] += 1
            shades.append(int(face["shade"]))
        out.append((len(tiles), max(shades) - min(shades)))
    return out


@unittest.skipUnless(CANDIDATE.exists(), "no built candidate")
class LevelMaterialTests(unittest.TestCase):

    @classmethod
    def setUpClass(cls) -> None:
        from bloodmap.format import read_map

        cls.disk = read_map(CANDIDATE)
        cls.rooms = rooms(cls.disk)

    def test_most_rooms_are_not_painted_in_a_single_tile(self):
        """It was 90%. The campaign is 37%; stairs keep this above that."""
        single = sum(1 for tiles, _ in self.rooms if tiles == 1) / len(self.rooms)
        self.assertLess(single, 0.70, "rooms with one wall tile: %.0f%%" % (100 * single))

    def test_wall_shade_spread_is_a_distribution_and_not_a_constant(self):
        """Every room used to be exactly 12, which is the campaign's median and
        still wrong: the campaign runs q1 2 to q3 22 with a p90 of 34."""
        spreads = sorted(spread for _, spread in self.rooms)
        q1 = spreads[len(spreads) // 4]
        q3 = spreads[3 * len(spreads) // 4]
        self.assertGreater(q3 - q1, 4, "one amplitude applied to every room")

    def test_the_level_is_exposed_where_the_campaign_is(self):
        from bloodmap.lighting import CORPUS_SHADE
        from bloodmap.reachability import design_sectors

        playable = set(design_sectors(self.disk))
        walls, floors, ceilings = [], [], []
        for index, sector in enumerate(self.disk.sectors):
            if index not in playable:
                continue
            fields = sector.fields
            floors.append(int(fields["floor_shade"]))
            if not int(fields["ceiling_stat"]) & 1:
                ceilings.append(int(fields["ceiling_shade"]))
            start, count = int(fields["wall_ptr"]), int(fields["wall_count"])
            for wall in range(start, start + count):
                walls.append(int(self.disk.walls[wall].fields["shade"]))
        for name, values in (("wall", walls), ("floor", floors), ("ceiling", ceilings)):
            self.assertAlmostEqual(
                statistics.median(values), CORPUS_SHADE[name], delta=6,
                msg="%s median shade is %s, the campaign's is %s"
                    % (name, statistics.median(values), CORPUS_SHADE[name]))


@unittest.skipUnless(bool(campaign_maps()), "no Blood campaign maps")
class CampaignMaterialTests(unittest.TestCase):
    """The two measurements the work rests on."""

    @classmethod
    def setUpClass(cls) -> None:
        from bloodmap.format import read_map

        cls.rooms = []
        cls.split = Counter()
        for path in campaign_maps():
            disk = read_map(path)
            cls.rooms.extend(rooms(disk))
            cls._count_split(disk, cls.split)

    @staticmethod
    def _count_split(disk, into):
        from bloodmap.reachability import design_sectors

        playable = set(design_sectors(disk))
        for index, sector in enumerate(disk.sectors):
            if index not in playable:
                continue
            fields = sector.fields
            start, count = int(fields["wall_ptr"]), int(fields["wall_count"])
            if count < 4:
                continue
            solid, portal = Counter(), Counter()
            for wall in range(start, start + count):
                face = disk.walls[wall].fields
                bucket = portal if int(face["next_sector"]) >= 0 else solid
                bucket[int(face["picnum"])] += 1
            if not solid or not portal:
                continue
            if len(solid + portal) < 2:
                continue      # a one-material room cannot differentiate anything
            same = solid.most_common(1)[0][0] == portal.most_common(1)[0][0]
            into["same" if same else "differs"] += 1

    def test_a_blood_room_carries_two_wall_tiles(self):
        counts = sorted(tiles for tiles, _ in self.rooms)
        self.assertEqual(statistics.median(counts), 2)
        single = sum(1 for c in counts if c == 1) / len(counts)
        self.assertLess(single, 0.45)

    def test_openings_are_dressed_differently_from_the_field(self):
        """Among rooms that use more than one wall tile -- 51% of all rooms with
        both kinds of wall use exactly one, and those cannot differentiate
        anything, so counting them measures how often Blood bothers rather than
        what it does when it does."""
        total = self.split["same"] + self.split["differs"]
        self.assertGreater(total, 5000)
        self.assertGreater(self.split["differs"] / total, 0.65,
                           "the premise of portal_wall_picnum has moved")
