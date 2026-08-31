"""Invisible walls standing in for stone.

Reported from play: "there are other places in the level where we are using
maskwalls for no reason... there are some other cases of invisible blocking
maskwalls."

A masked wall in Blood is a two-sided wall with something drawn on its
``over_picnum`` -- a grate, a grille, a sheet of falling water. This project had
been using it for something else entirely: a way to say "these two regions share
an edge and must not connect", by pairing them as a portal, setting the blocking
bit and copying the wall's own picnum onto its over_picnum so it looked solid.

The corpus is unambiguous that this is not how Blood is built:

* the campaign masks **600 of 113,261 walls, 0.53%**, median 0.30% per map;
  this level was masking **38 of 939, 4.0%**;
* of those 600, **14 copy their own picnum onto over_picnum -- 2%**; of this
  level's 38, **32 did, 84%**.

The real answer to "these must not connect" is that they must not be neighbours.
Give the wall thickness and every face of it becomes an ordinary one-sided wall
with rock behind: the gate sectors were reshaped so they are only wide on the
line their leaves travel along, the cascade shelf was stood a unit clear of the
grotto, the graveyard a unit clear of the tower, and the garden two units clear
of the graveyard. Thirty of the thirty-two went away and the level gained a
visible jamb, reveal and lintel everywhere one had been faked.

Eight masked walls are left, and each is a thing you can see through: four
grates (tile 266, the campaign's own commonest), the belfry window's grille
(463) and the cascade (1005).
"""

from __future__ import annotations

import glob
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
#: The campaign population directory (corpus reorganized 2026-08-31).
MAPS = ROOT / "maps" / "blood" / "campaign"
CANDIDATE = ROOT / "projects" / "reasoned-authoring-v1" / "level" / "candidate-v5.MAP"

CSTAT_MASKED = 16

#: Tiles this level is allowed to mask a wall with, and what each one is. A
#: masked wall has to be something the player looks through; if a new one turns
#: up here it should be added deliberately, with a reason.
LEGITIMATE = {
    266: "grate between a cloister walk and a working room",
    463: "the grille in the belfry window",
    1005: "the cascade, falling across the mouth of the grotto",
}


def campaign_maps() -> list[str]:
    return [
        path for path in sorted(glob.glob(str(MAPS / "*.MAP")))
        if re.match(r"^E[1-46]M[1-9]$", Path(path).stem.upper())
    ]


def masked_walls(disk) -> list[int]:
    return [i for i, w in enumerate(disk.walls)
            if int(w.fields["cstat"]) & CSTAT_MASKED]


def fake_solid(disk) -> list[tuple[int, int]]:
    """Masked walls wearing their own picnum, which is a wall pretending to be one."""
    return [
        (i, int(w.fields["picnum"])) for i, w in enumerate(disk.walls)
        if int(w.fields["cstat"]) & CSTAT_MASKED
        and int(w.fields["over_picnum"]) == int(w.fields["picnum"])
    ]


@unittest.skipUnless(CANDIDATE.exists(), "no built candidate")
class LevelMaskedWallTests(unittest.TestCase):

    def test_every_masked_wall_is_something_you_can_see_through(self):
        from bloodmap.format import read_map

        disk = read_map(CANDIDATE)
        unexplained = {}
        for index in masked_walls(disk):
            over = int(disk.walls[index].fields["over_picnum"])
            if over not in LEGITIMATE:
                unexplained[index] = over
        self.assertEqual({}, unexplained,
                         "masked walls with no stated reason: %s" % unexplained)

    def test_the_masked_share_is_inside_the_campaigns(self):
        from bloodmap.format import read_map

        disk = read_map(CANDIDATE)
        share = len(masked_walls(disk)) / len(disk.walls)
        # the campaign runs 0 to 0.0270 per map, median 0.0030
        self.assertLessEqual(share, 0.0270,
                             "more masked walls than any Blood level: %.4f" % share)

    def test_the_only_self_faced_masked_walls_are_the_cascade(self):
        """`over_picnum == picnum` is how you fake solidity, and the level used
        to do it 32 times. The two left are the falling water, which genuinely
        wants the same tile on both faces."""
        from bloodmap.format import read_map

        offenders = fake_solid(read_map(CANDIDATE))
        self.assertEqual(
            sorted({picnum for _, picnum in offenders}), [1005],
            "walls faking solidity with their own tile: %s" % offenders)


@unittest.skipUnless(bool(campaign_maps()), "no Blood campaign maps")
class CampaignMaskedWallTests(unittest.TestCase):

    def test_blood_masks_well_under_a_percent_of_its_walls(self):
        from bloodmap.format import read_map

        masked = walls = 0
        for path in campaign_maps():
            disk = read_map(path)
            masked += len(masked_walls(disk))
            walls += len(disk.walls)
        self.assertGreater(walls, 100000)
        self.assertLess(masked / walls, 0.01,
                        "the premise of this whole check has moved")

    def test_faking_solidity_is_rare_enough_to_be_a_mistake(self):
        """7 maps of 43 do it at all, and none more than four times."""
        from bloodmap.format import read_map

        counts = [len(fake_solid(read_map(path))) for path in campaign_maps()]
        self.assertLessEqual(max(counts), 8)
        self.assertLess(sum(1 for c in counts if c) / len(counts), 0.25)
