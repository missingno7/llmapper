"""A wall texture that restarts at every vertex.

Reported from play as "not properly aligned textures". The level set no
horizontal panning at all, so every wall began its tile at zero and put a hard
vertical seam at each vertex -- including the vertices that are not corners,
where a long wall had only been split to hang a doorway off it.

Blood advances the horizontal texture coordinate by ``x_repeat * 8`` tile pixels
along a wall, so two walls read as one surface when

    x_panning(next) == (x_panning(this) + x_repeat(this) * 8) % tile_width

The campaign's 43 maps satisfy that on 34% to 69% of their same-tile joins,
median 48%. This level satisfied it on 3%.
"""

from __future__ import annotations

import glob
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
#: The campaign population directory (corpus reorganized 2026-08-31).
MAPS = ROOT / "maps" / "blood" / "campaign"
ART = ROOT / "reference" / "blood"
CANDIDATE = ROOT / "projects" / "reasoned-authoring-v1" / "level" / "candidate-v5.MAP"


def campaign_maps() -> list[str]:
    return [
        path for path in sorted(glob.glob(str(MAPS / "*.MAP")))
        if re.match(r"^E[1-46]M[1-9]$", Path(path).stem.upper())
    ]


def continued_share(disk, art) -> tuple[int, int]:
    """Joins where the texture carries on, and joins counted."""
    carried = total = 0
    for sector in disk.sectors:
        start = int(sector.fields["wall_ptr"])
        count = int(sector.fields["wall_count"])
        for wall in range(start, start + count):
            this = disk.walls[wall].fields
            nxt = int(this["point2"])
            if not start <= nxt < start + count:
                continue
            following = disk.walls[nxt].fields
            if int(this["picnum"]) != int(following["picnum"]):
                continue                                   # a change of material
            tile = art.get(int(this["picnum"]))
            if tile is None or tile.width <= 0:
                continue
            width = tile.width
            want = (int(this["x_panning"]) + int(this["x_repeat"]) * 8) % width
            got = int(following["x_panning"]) % width
            total += 1
            # a pixel of slack: panning is a byte and wall lengths are integers
            if min((want - got) % width, (got - want) % width) <= 1:
                carried += 1
    return carried, total


@unittest.skipUnless(CANDIDATE.exists() and ART.exists(), "no built candidate")
class WallRunTests(unittest.TestCase):

    def test_this_level_carries_its_runs_as_the_campaign_does(self):
        from bloodmap.art import read_art_directory
        from bloodmap.format import read_map

        art = read_art_directory(str(ART))
        if not art:
            self.skipTest("no Blood ART")
        carried, total = continued_share(read_map(CANDIDATE), art)
        self.assertGreater(total, 200)
        share = carried / total
        # the campaign's own range, ends included: E3M1 at 0.34, E6M1 at 0.69
        self.assertGreaterEqual(share, 0.34, "textures restart at the corners")
        self.assertLessEqual(share, 0.72, "tidier than any real Blood level")

    def test_a_run_stops_at_an_outside_corner(self):
        """Carrying every join would be its own kind of wrong.

        The campaign continues 23% of reflex corners against 82% of collinear
        joins, so an outside corner is where a surface ends and the next one
        begins -- there is no reading under which the two are one wall.
        """
        from bloodmap.art import read_art_directory
        from bloodmap.format import read_map
        from bloodmap.texture_align import RUN_BREAK_DEGREES, _wall_angle

        art = read_art_directory(str(ART))
        if not art:
            self.skipTest("no Blood ART")
        disk = read_map(CANDIDATE)
        reflex = 0
        for sector in disk.sectors:
            start = int(sector.fields["wall_ptr"])
            count = int(sector.fields["wall_count"])
            for wall in range(start, start + count):
                nxt = int(disk.walls[wall].fields["point2"])
                if not start <= nxt < start + count:
                    continue
                if _wall_angle(disk, wall, nxt) >= RUN_BREAK_DEGREES:
                    reflex += 1
        self.assertGreater(reflex, 0, "a level with no outside corners")


@unittest.skipUnless(bool(campaign_maps()) and ART.exists(), "no Blood campaign")
class CampaignRunTests(unittest.TestCase):

    def test_the_rule_is_the_campaigns_and_not_an_invention(self):
        """If the formula were wrong it would fit no map, not most of them."""
        from bloodmap.art import read_art_directory
        from bloodmap.format import read_map

        art = read_art_directory(str(ART))
        if not art:
            self.skipTest("no Blood ART")
        shares = []
        for path in campaign_maps():
            carried, total = continued_share(read_map(path), art)
            if total:
                shares.append(carried / total)
        self.assertGreaterEqual(len(shares), 20)
        self.assertGreater(min(shares), 0.30)
        self.assertGreater(sum(shares) / len(shares), 0.40)
