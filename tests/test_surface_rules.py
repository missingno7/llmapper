"""Two rules the engine enforces and one the corpus does.

All three were reported from inside the level and none of them was visible to
anything the project could measure at the time.

**A floor or ceiling tile must have power-of-two sides.** `tileUpdatePicSiz`
takes the largest power of two *not greater than* each dimension, and the floor
rasteriser masks its lookup with exactly that::

    globalxshift = 8 - (picsiz[globalpicnum] & 15);
    globalyshift = 8 - (picsiz[globalpicnum] >> 4);

So a 64x400 sky panel laid on an ordinary ceiling is sampled as 64x256 -- the
last 144 rows are never drawn and it tiles at the wrong pitch. Walls escape it
because `wallscan` handles arbitrary heights. The campaign obeys the rule on
26,376 of 26,383 non-parallax surfaces, 99.97%. This level broke it fourteen
times, all of them outdoor stairs and doorways that had been given the sky tile
without the parallax flag -- three of them because `inherit_finish` copied a
neighbour's ceiling picnum and not its ceiling stat, which is the same decision.

**A blocked two-sided wall needs something to justify it.** Blood blocks 2,272
of them, and the floor difference across one has a median of 4.00 player heights
and a q1 of 1.09: they are ledges and railings, and a fifth of them are masked so
you can see what stopped you. This level had six at a 0.36 kerb with nothing
drawn on them at all -- you saw a step, read it as a step, and walked into an
invisible wall.

**A sector that hurts should look like it hurts.** The cistern has damaged and
dragged the player since it was built, wearing plain dark stone, so the only
clue was that the floor slid. Its damage type was never the problem: 27 of the
28 campaign damage sectors that set Drag use `kDamageExplode`, which is what
this one already used.
"""

from __future__ import annotations

import glob
import re
import statistics
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
#: The campaign population directory (corpus reorganized 2026-08-31).
MAPS = ROOT / "maps" / "blood" / "campaign"
ART = ROOT / "reference" / "blood"
CANDIDATE = ROOT / "projects" / "reasoned-authoring-v1" / "level" / "candidate-v5.MAP"

#: Below this a floor difference is a step, and a wall that blocks one is a wall
#: the player has no reason to expect.
STEPPABLE = 0.4 * 5632


def campaign_maps() -> list[str]:
    return [
        path for path in sorted(glob.glob(str(MAPS / "*.MAP")))
        if re.match(r"^E[1-46]M[1-9]$", Path(path).stem.upper())
    ]


def power_of_two(value: int) -> bool:
    return value > 0 and (value & (value - 1)) == 0


def wall_owners(disk) -> dict[int, int]:
    owner = {}
    for index, sector in enumerate(disk.sectors):
        start = int(sector.fields["wall_ptr"])
        for wall in range(start, start + int(sector.fields["wall_count"])):
            owner[wall] = index
    return owner


def flat_offenders(disk, art) -> list[tuple[int, str, int]]:
    out = []
    for index, sector in enumerate(disk.sectors):
        fields = sector.fields
        for surface in ("floor", "ceiling"):
            if int(fields[f"{surface}_stat"]) & 1:
                continue
            picnum = int(fields[f"{surface}_picnum"])
            tile = art.get(picnum)
            if tile is None:
                continue
            if not (power_of_two(tile.width) and power_of_two(tile.height)):
                out.append((index, surface, picnum))
    return out


def unexplained_blockers(disk) -> list[tuple[int, int]]:
    """Blocking two-sided walls that are invisible and at a steppable kerb."""
    owner = wall_owners(disk)
    out = []
    for index, wall in enumerate(disk.walls):
        fields = wall.fields
        other = int(fields["next_sector"])
        cstat = int(fields["cstat"])
        if other < 0 or not cstat & 1 or cstat & 16:
            continue
        mine = owner.get(index)
        if mine is None:
            continue
        step = abs(int(disk.sectors[mine].fields["floor_z"])
                   - int(disk.sectors[other].fields["floor_z"]))
        if step < STEPPABLE:
            out.append((index, step))
    return out


@unittest.skipUnless(CANDIDATE.exists() and ART.exists(), "no built candidate")
class LevelSurfaceTests(unittest.TestCase):

    @classmethod
    def setUpClass(cls) -> None:
        from bloodmap.art import read_art_directory
        from bloodmap.format import read_map

        cls.art = read_art_directory(str(ART))
        cls.disk = read_map(CANDIDATE)

    def test_no_flat_surface_carries_a_tile_build_cannot_sample(self):
        if not self.art:
            self.skipTest("no Blood ART")
        self.assertEqual([], flat_offenders(self.disk, self.art))

    def test_nothing_blocks_the_player_at_a_step_without_showing_why(self):
        self.assertEqual([], unexplained_blockers(self.disk))

    def test_the_sector_that_hurts_looks_like_it_hurts(self):
        """Damage sectors carry a surface that reads as dangerous."""
        dangerous = {1120, 530, 1005, 1029, 362, 373}
        found = 0
        for sector in self.disk.sectors:
            if int(sector.fields["type"]) != 618:
                continue
            found += 1
            self.assertIn(
                int(sector.fields["floor_picnum"]), dangerous,
                "a sector that damages the player wearing an innocent floor")
        self.assertGreaterEqual(found, 1)


@unittest.skipUnless(bool(campaign_maps()) and ART.exists(), "no Blood campaign")
class CampaignSurfaceTests(unittest.TestCase):
    """The evidence each rule rests on."""

    def test_blood_keeps_its_flat_tiles_power_of_two(self):
        from bloodmap.art import read_art_directory
        from bloodmap.format import read_map

        art = read_art_directory(str(ART))
        if not art:
            self.skipTest("no Blood ART")
        good = total = 0
        for path in campaign_maps():
            disk = read_map(path)
            for sector in disk.sectors:
                fields = sector.fields
                for surface in ("floor", "ceiling"):
                    if int(fields[f"{surface}_stat"]) & 1:
                        continue
                    tile = art.get(int(fields[f"{surface}_picnum"]))
                    if tile is None:
                        continue
                    total += 1
                    good += power_of_two(tile.width) and power_of_two(tile.height)
        self.assertGreater(total, 20000)
        self.assertGreater(good / total, 0.995)

    def test_a_blood_blocked_wall_is_a_ledge_not_a_kerb(self):
        from bloodmap.format import read_map

        steps = []
        for path in campaign_maps():
            disk = read_map(path)
            owner = wall_owners(disk)
            for index, wall in enumerate(disk.walls):
                fields = wall.fields
                other = int(fields["next_sector"])
                if other < 0 or not int(fields["cstat"]) & 1:
                    continue
                mine = owner.get(index)
                if mine is None:
                    continue
                steps.append(abs(int(disk.sectors[mine].fields["floor_z"])
                                 - int(disk.sectors[other].fields["floor_z"])))
        self.assertGreater(len(steps), 2000)
        self.assertGreater(statistics.median(steps), 2.0 * 5632)
