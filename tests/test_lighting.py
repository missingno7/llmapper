"""How Blood lights a room, and the pass that reproduces the reconstructible part.

The finding these pin: a level can be structurally perfect and read flat, and
the campaign's answer is not a light model but a rule about *facing*.
"""

from __future__ import annotations

import glob
import math
import re
import statistics
import unittest
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
#: The campaign population directory (corpus reorganized 2026-08-31).
MAPS = ROOT / "maps" / "blood" / "campaign"
CANDIDATE = ROOT / "projects" / "reasoned-authoring-v1" / "level" / "candidate-v5.MAP"


def campaign_maps() -> list[str]:
    return [
        path for path in sorted(glob.glob(str(MAPS / "*.MAP")))
        if re.match(r"^E[1-46]M[1-9]$", Path(path).stem.upper())
    ]


def have_campaign() -> bool:
    return bool(campaign_maps())


class LightOffsetTests(unittest.TestCase):
    def test_the_gradient_is_the_pool_the_campaign_actually_casts(self):
        """Twenty-three shades deep, and still below zero at its edge.

        This asserted -6 to +6 over four player widths, which was wrong twice.
        Measuring the campaign's walls by their distance from the nearest burning
        sprite gives median shades of 8, 17, 24 and 28 at under one player width,
        one to three, three to six, and beyond -- against 31 for a wall in a room
        with no light in it at all.

        So the pool is twenty-three deep, not twelve; and *every* wall in a lit
        room is brighter than one in an unlit room, even six widths off, so the
        far end is -3 rather than +6. A lamp lifts the whole room and then pools
        on top of that. The old far offset darkened what the corpus brightens.
        """
        from bloodmap.lighting import FALLOFF, light_offset

        self.assertEqual(FALLOFF, 6 * 384)
        self.assertEqual(light_offset(0), -23)
        self.assertEqual(light_offset(FALLOFF), -3)
        self.assertEqual(light_offset(FALLOFF * 10), -3)
        self.assertEqual(light_offset(FALLOFF / 2), -13)
        # the measured medians, as offsets from the unlit baseline of 31
        for distance, want in ((0, -23), (2 * 384, -14), (4.5 * 384, -7)):
            self.assertLessEqual(abs(light_offset(distance) - want), 2)

    def test_only_the_tiles_the_campaign_actually_lights_with(self):
        """The sconces and emblems look like lights and are not.

        Tiles 506, 641 and 1701 are drawn at shade -128 in 89%, 86% and 89% of
        their uses; 510 manages 25% and 915 none at all, and 2540-2545 are drawn
        at -8, the ordinary decoration value. The first version of this set
        included those and made every wall plaque a lamp.
        """
        from bloodmap.lighting import LIGHT_TILES

        self.assertEqual(LIGHT_TILES, frozenset({506, 641, 1701}))

    def test_lighting_a_room_and_flickering_it_are_different_questions(self):
        """A lantern casts light and does not gutter.

        `FLICKER_TILES` was `LIGHT_TILES` until 641 joined the second set and
        broke the first: the campaign animates 63% of torch sectors and 71% of
        chandelier sectors, but only 3% of the 59 sectors holding a hanging
        lantern -- below the 21% baseline for a sector with no light in it. That
        is a flame in a glass, and Blood draws the distinction on purpose.
        """
        from bloodmap.lighting import FLICKER_TILES, LIGHT_TILES

        self.assertEqual(FLICKER_TILES, frozenset({506, 1701}))
        self.assertTrue(FLICKER_TILES < LIGHT_TILES)


@unittest.skipUnless(have_campaign(), "no Blood campaign maps")
class CampaignLightingTests(unittest.TestCase):
    """The measurements the pass is built on, so they cannot drift unnoticed."""

    @staticmethod
    def _rooms(disk):
        from bloodmap.reachability import design_sectors

        playable = set(design_sectors(disk))
        for index, sector in enumerate(disk.sectors):
            if index not in playable:
                continue
            fields = sector.fields
            start, count = int(fields["wall_ptr"]), int(fields["wall_count"])
            rows = []
            for wall in range(start, start + count):
                wall_fields = disk.walls[wall].fields
                ax, ay = int(wall_fields["x"]), int(wall_fields["y"])
                nxt = int(wall_fields["point2"])
                bx = int(disk.walls[nxt].fields["x"])
                by = int(disk.walls[nxt].fields["y"])
                if (ax, ay) == (bx, by):
                    continue
                angle = int(round(math.atan2(by - ay, bx - ax) / (2 * math.pi) * 2048)) & 2047
                rows.append((angle, int(wall_fields["shade"])))
            if len(rows) >= 4:
                yield rows

    def test_a_room_is_not_lit_with_one_number(self):
        """Within-room wall shade spread: median 12, q1 2, q3 22."""
        from bloodmap.format import read_map

        spreads = []
        for path in campaign_maps():
            for rows in self._rooms(read_map(path)):
                shades = [s for _angle, s in rows]
                spreads.append(max(shades) - min(shades))
        ordered = sorted(spreads)
        self.assertGreater(len(ordered), 5000)
        self.assertGreaterEqual(statistics.median(ordered), 10)
        self.assertLessEqual(statistics.median(ordered), 14)

    def test_facing_explains_most_of_the_variation(self):
        """81%, against 52% for grouping by texture.

        The number matters because it is what says the rule is directional
        lighting rather than per-surface taste.
        """
        from bloodmap.format import read_map

        total = []
        residual = []
        for path in campaign_maps():
            for rows in self._rooms(read_map(path)):
                shades = [s for _angle, s in rows]
                if max(shades) == min(shades):
                    continue
                total.append(statistics.pvariance(shades))
                groups = defaultdict(list)
                for angle, shade in rows:
                    groups[angle * 8 // 2048].append(shade)
                left = []
                for values in groups.values():
                    mean = statistics.mean(values)
                    left.extend((v - mean) ** 2 for v in values)
                residual.append(sum(left) / len(rows))
        explained = 1 - (sum(residual) / len(residual)) / (sum(total) / len(total))
        self.assertGreater(explained, 0.7)

    def test_no_direction_is_globally_darker(self):
        """Every facing octant has a median offset of 0.

        This is what makes the direction a per-room choice rather than a level
        or engine convention, and it is why the pass derives one per room.
        """
        from bloodmap.format import read_map

        buckets = defaultdict(list)
        for path in campaign_maps():
            for rows in self._rooms(read_map(path)):
                shades = [s for _angle, s in rows]
                if max(shades) == min(shades):
                    continue
                base = statistics.median(shades)
                for angle, shade in rows:
                    buckets[angle * 8 // 2048].append(shade - base)
        self.assertEqual(len(buckets), 8)
        for octant, values in buckets.items():
            self.assertEqual(statistics.median(values), 0, f"octant {octant} is biased")


@unittest.skipUnless(CANDIDATE.exists(), "no built candidate")
class MonasteryLightingTests(unittest.TestCase):
    def test_no_room_is_lit_with_a_single_number(self):
        from bloodmap.format import read_map
        from bloodmap.reachability import design_sectors

        disk = read_map(CANDIDATE)
        playable = set(design_sectors(disk))
        flat = 0
        spreads = []
        for index, sector in enumerate(disk.sectors):
            if index not in playable:
                continue
            fields = sector.fields
            start, count = int(fields["wall_ptr"]), int(fields["wall_count"])
            shades = [int(disk.walls[w].fields["shade"]) for w in range(start, start + count)]
            if not shades:
                continue
            spread = max(shades) - min(shades)
            spreads.append(spread)
            if spread == 0:
                flat += 1
        self.assertGreater(len(spreads), 40)
        self.assertEqual(flat, 0, "a room still has one shade on every wall")
        # The campaign's median is 12; this should be in the same country.
        self.assertGreaterEqual(statistics.median(spreads), 8)


@unittest.skipUnless(have_campaign(), "no Blood campaign maps")
class AnimatedShadeTests(unittest.TestCase):
    """Blood animates the shade of one playable sector in five.

    The XMapEdit sample `LIGHTING-LIGHTS` is what surfaced this: 52 of its
    sectors carry an amplitude, and the fields around it -- wave, frequency,
    phase, and which surfaces are affected -- are a whole subsystem the campaign
    mining had never named.
    """

    def test_the_campaign_animates_about_a_fifth_of_its_sectors(self):
        from bloodmap.format import read_map
        from bloodmap.reachability import design_sectors

        animated = total = 0
        for path in campaign_maps():
            disk = read_map(path)
            playable = set(design_sectors(disk))
            for index, sector in enumerate(disk.sectors):
                if index not in playable:
                    continue
                total += 1
                if sector.extra and int(sector.extra.fields.get("amplitude", 0)):
                    animated += 1
        self.assertGreater(total, 10000)
        self.assertGreater(animated / total, 0.15)
        self.assertLess(animated / total, 0.30)

    def test_a_lamp_more_than_triples_the_odds(self):
        """65% of campaign sectors with a lamp are animated, against 20% without."""
        from bloodmap.format import read_map
        from bloodmap.lighting import FLICKER_TILES
        from bloodmap.reachability import design_sectors

        with_lamp = [0, 0]
        without = [0, 0]
        for path in campaign_maps():
            disk = read_map(path)
            playable = set(design_sectors(disk))
            lit = {
                int(s.fields["sector"]) for s in disk.sprites
                if int(s.fields["picnum"]) in FLICKER_TILES and int(s.fields["shade"]) <= -64
            }
            for index, sector in enumerate(disk.sectors):
                if index not in playable:
                    continue
                animated = bool(sector.extra and int(sector.extra.fields.get("amplitude", 0)))
                bucket = with_lamp if index in lit else without
                bucket[0 if animated else 1] += 1
        lamp_rate = with_lamp[0] / sum(with_lamp)   # FLICKER_TILES, not LIGHT_TILES
        plain_rate = without[0] / sum(without)
        self.assertGreater(lamp_rate, 0.55)
        self.assertGreater(lamp_rate, 2.5 * plain_rate)

    def test_shade_always_is_what_makes_a_static_room_flicker(self):
        """Without it the effect only runs while the sector is busy.

        `sectorfx.cpp`: `if (pXSector->shadeAlways || pXSector->busy)`. The 1,194
        campaign sectors that leave it clear are lifts and doors, which are busy
        when it matters.
        """
        from bloodmap.lighting import SHADE_ALWAYS

        self.assertEqual(SHADE_ALWAYS, 1)

    @unittest.skipUnless(CANDIDATE.exists(), "no built candidate")
    def test_the_level_moves_its_shade_where_something_moves_the_light(self):
        """Two reasons and no others: a flame, or water over your head.

        This used to assert that the animated sectors were exactly the sectors
        holding a torch. Then the flooded run learned to ripple -- 112 of the
        campaign's 618 underwater sectors do -- so the set grew a second half
        with a different cause. It is still a closed set, which is the property
        worth keeping: a sector whose shade moves for no reason is a sector
        somebody forgot about.
        """
        from bloodmap.format import read_map
        from bloodmap.lighting import FLICKER_TILES, FLICKER_WAVE

        disk = read_map(CANDIDATE)
        lit = {
            int(s.fields["sector"]) for s in disk.sprites
            if int(s.fields["picnum"]) in FLICKER_TILES and int(s.fields["shade"]) <= -64
        }
        under = {
            index for index, sector in enumerate(disk.sectors)
            if sector.extra and int(sector.extra.fields.get("underwater", 0) or 0)
        }
        animated = {
            index for index, sector in enumerate(disk.sectors)
            if sector.extra and int(sector.extra.fields.get("amplitude", 0))
        }
        self.assertTrue(animated)
        self.assertTrue(lit)
        self.assertTrue(under)
        self.assertEqual(animated, lit | under)
        phases = set()
        for index in sorted(animated):
            fields = disk.sectors[index].extra.fields
            self.assertEqual(int(fields["shade_wave"]), FLICKER_WAVE)
            self.assertEqual(int(fields["shade_always"]), 1)
            self.assertEqual(int(fields["shade_floor"]), 1)
            self.assertEqual(int(fields["shade_ceiling"]), 1)
            self.assertEqual(int(fields["shade_walls"]), 1)
            phases.add(int(fields["shade_phase"]))
        # they must not breathe in unison
        self.assertEqual(len(phases), len(animated))


if __name__ == "__main__":
    unittest.main()
