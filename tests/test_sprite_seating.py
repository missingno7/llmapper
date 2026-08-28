"""Two faults that every structural check passes and the player sees at once.

A fence sunk to its waist in the floor, and a switch that visibly does nothing.
Neither is a malformed map: both are the natural reading of a field, and both
are wrong about what Blood does with it.
"""

from __future__ import annotations

import glob
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
MAPS = ROOT / "maps" / "blood"
CANDIDATE = ROOT / "projects" / "reasoned-authoring-v1" / "level" / "candidate-v5.MAP"

MOVING = frozenset({613, 614, 615, 616, 617})


def campaign_maps() -> list[str]:
    return [
        path for path in sorted(glob.glob(str(MAPS / "*.MAP")))
        if re.match(r"^E[1-46]M[1-9]$", Path(path).stem.upper())
    ]


def have_campaign() -> bool:
    return bool(campaign_maps())


class SpriteExtentTests(unittest.TestCase):
    """Blood centres a sprite on its own z, whatever the centring bit says."""

    def test_the_centring_bit_does_not_enter_into_it(self):
        """`GetSpriteExtents` (db.h) tests only `cstat & 0x30 == 0x20`.

        Bit 128 is Duke's y-centring flag and Blood sets it on most sprites, so
        reading it as "this one is centred and the others hang from z" is the
        natural mistake. Blood centres them all; only a floor-aligned sprite is
        a flat plane at z.
        """
        from bloodmap.placement import sprite_extent

        self.assertEqual(sprite_extent(128, 64, 0), (16384, 16384))
        self.assertEqual(sprite_extent(128, 64, 128), (16384, 16384))
        self.assertEqual(sprite_extent(128, 64, 16), (16384, 16384))
        self.assertEqual(sprite_extent(128, 64, 32), (0, 0))

    def test_a_picanm_offset_moves_the_centre(self):
        """Tile 641 carries yofs -60, so it is not centred on its middle."""
        from bloodmap.placement import sprite_extent

        self.assertEqual(sprite_extent(128, 64, 0, y_offset=-60), (1024, 31744))

    def test_seating_puts_the_edge_where_it_was_asked_for(self):
        from bloodmap.placement import seated_z, sprite_extent

        above, below = sprite_extent(128, 64, 8337)
        floor_z, ceiling_z = 8192, -24576
        z = seated_z(seat="floor", floor_z=floor_z, ceiling_z=ceiling_z,
                     tile_height=128, y_repeat=64, cstat=8337)
        self.assertEqual(z + below, floor_z)
        z = seated_z(seat="ceiling", floor_z=floor_z, ceiling_z=ceiling_z,
                     tile_height=128, y_repeat=64, cstat=8337)
        self.assertEqual(z - above, ceiling_z)


@unittest.skipUnless(have_campaign(), "no Blood campaign maps")
class CampaignSeatingTests(unittest.TestCase):
    def test_the_campaign_stands_its_fences_on_the_floor(self):
        """43 of 65 fence sprites sit at bottom - floor == 0 exactly."""
        from bloodmap.format import read_map
        from bloodmap.placement import sprite_extent
        from bloodmap.texture_align import sprite_tile_extents

        extents = sprite_tile_extents()
        if not extents:
            self.skipTest("no Blood ART")
        on_floor = total = 0
        for path in campaign_maps():
            disk = read_map(path)
            for sprite in disk.sprites:
                fields = sprite.fields
                if int(fields["picnum"]) not in (1044, 1064):
                    continue
                tile_height, y_offset = extents[int(fields["picnum"])]
                _above, below = sprite_extent(
                    tile_height, int(fields["y_repeat"]), int(fields["cstat"]),
                    y_offset=y_offset)
                floor_z = int(disk.sectors[int(fields["sector"])].fields["floor_z"])
                total += 1
                if int(fields["z"]) + below == floor_z:
                    on_floor += 1
        self.assertGreaterEqual(total, 60)
        self.assertGreater(on_floor / total, 0.6)

    @unittest.skipUnless(CANDIDATE.exists(), "no built candidate")
    def test_the_monastery_buries_nothing(self):
        from bloodmap.format import read_map
        from bloodmap.placement import misseated_sprites
        from bloodmap.texture_align import sprite_tile_extents

        extents = sprite_tile_extents()
        if not extents:
            self.skipTest("no Blood ART")
        self.assertEqual(misseated_sprites(read_map(CANDIDATE), extents), [])


@unittest.skipUnless(have_campaign(), "no Blood campaign maps")
class MovingSectorPoseTests(unittest.TestCase):
    """A slide or rotate sector's state and busy are one fact written twice."""

    def test_the_campaign_never_separates_state_from_busy(self):
        """579 sectors rest at (0, 0) and 80 at (1, 65536). Nothing rests at (1, 0).

        `trInit` translates the sector to busy = -65536, takes that as the base,
        and only then translates to the authored busy -- so busy 65536 is the
        pose the geometry was drawn in and busy 0 is a pose the author never saw.
        A sector claiming state 1 while sitting at busy 0 claims to be open while
        drawn shut, and both of this level's doors did exactly that.
        """
        from bloodmap.format import read_map

        pairs: dict[tuple[int, int], int] = {}
        for path in campaign_maps():
            for sector in read_map(path).sectors:
                if int(sector.fields["type"]) not in MOVING or sector.extra is None:
                    continue
                fields = sector.extra.fields
                key = (int(fields.get("state", 0)), int(fields.get("busy", 0)))
                pairs[key] = pairs.get(key, 0) + 1
        self.assertEqual(set(pairs), {(0, 0), (1, 65536)})

    @unittest.skipUnless(CANDIDATE.exists(), "no built candidate")
    def test_the_monastery_doors_rest_in_a_pose_the_campaign_uses(self):
        from bloodmap.format import read_map

        found = 0
        for sector in read_map(CANDIDATE).sectors:
            if int(sector.fields["type"]) not in MOVING or sector.extra is None:
                continue
            found += 1
            fields = sector.extra.fields
            self.assertIn(
                (int(fields.get("state", 0)), int(fields.get("busy", 0))),
                {(0, 0), (1, 65536)})
        self.assertGreaterEqual(found, 2)

    @unittest.skipUnless(CANDIDATE.exists(), "no built candidate")
    def test_no_switch_sends_a_door_to_the_state_it_is_already_in(self):
        """`SetSectorState` returns 0 when state already equals the target.

        So kCmdOn to a sector resting at state 1 is a switch that does nothing
        at all. The campaign bears it out: a state-1 slide or rotate sector is
        sent toggle 42 times and off 34, and kCmdOn not once.
        """
        from bloodmap.format import read_map

        disk = read_map(CANDIDATE)
        senders: dict[int, list[int]] = {}
        for sprite in disk.sprites:
            if sprite.extra is None:
                continue
            fields = sprite.extra.fields
            if int(fields.get("tx_id", 0)):
                senders.setdefault(int(fields["tx_id"]), []).append(
                    int(fields.get("command", 0)))
        checked = 0
        for sector in disk.sectors:
            if int(sector.fields["type"]) not in MOVING or sector.extra is None:
                continue
            fields = sector.extra.fields
            state = int(fields.get("state", 0))
            for command in senders.get(int(fields.get("rx_id", 0)), []):
                checked += 1
                if command == 1:
                    self.assertNotEqual(state, 1, "kCmdOn to a sector already on")
                if command == 0:
                    self.assertNotEqual(state, 0, "kCmdOff to a sector already off")
        self.assertGreaterEqual(checked, 2)


if __name__ == "__main__":
    unittest.main()


@unittest.skipUnless(have_campaign(), "no Blood campaign maps")
class FenceOrientationTests(unittest.TestCase):
    """A wall-aligned sprite's angle is its face normal, not its lie.

    So a gate leaf blocks the opening only when its angle is a quarter turn from
    the wall it sits against. All three of this level's moving fences were set to
    the wall's own direction and stood edge-on in their doorways.
    """

    FENCE_TILES = frozenset({1044, 1064})

    @staticmethod
    def _wall_direction(ax, ay, bx, by):
        import math

        return int(round(math.atan2(by - ay, bx - ax) / (2 * math.pi) * 2048)) & 2047

    @classmethod
    def _relative_angles(cls, disk):
        """(sprite index, angle - direction of the nearest wall) for each fence."""
        import math

        out = []
        for index, sprite in enumerate(disk.sprites):
            fields = sprite.fields
            if int(fields["picnum"]) not in cls.FENCE_TILES:
                continue
            sector = disk.sectors[int(fields["sector"])].fields
            start, count = int(sector["wall_ptr"]), int(sector["wall_count"])
            sx, sy = int(fields["x"]), int(fields["y"])
            best = None
            for wall in range(start, start + count):
                ax, ay = int(disk.walls[wall].fields["x"]), int(disk.walls[wall].fields["y"])
                nxt = int(disk.walls[wall].fields["point2"])
                bx, by = int(disk.walls[nxt].fields["x"]), int(disk.walls[nxt].fields["y"])
                dx, dy = bx - ax, by - ay
                length = dx * dx + dy * dy
                t = 0.0 if not length else max(0.0, min(1.0, ((sx - ax) * dx + (sy - ay) * dy) / length))
                distance = math.hypot(sx - (ax + t * dx), sy - (ay + t * dy))
                if best is None or distance < best[0]:
                    best = (distance, ax, ay, bx, by)
            if best is None:
                continue
            wall_angle = cls._wall_direction(*best[1:])
            out.append((index, (int(fields["angle"]) - wall_angle) & 2047))
        return out

    def test_the_campaign_stands_its_fences_across_the_wall(self):
        """59 of 65 fence sprites are a quarter turn from the wall they lie on."""
        from bloodmap.format import read_map

        across = total = 0
        for path in campaign_maps():
            for _index, relative in self._relative_angles(read_map(path)):
                total += 1
                if relative in (512, 1536):
                    across += 1
        self.assertGreaterEqual(total, 60)
        self.assertGreater(across / total, 0.85)

    @unittest.skipUnless(CANDIDATE.exists(), "no built candidate")
    def test_every_moving_fence_blocks_its_own_opening(self):
        from bloodmap.format import read_map

        disk = read_map(CANDIDATE)
        moving = {
            index for index, sprite in enumerate(disk.sprites)
            if int(sprite.fields["picnum"]) in self.FENCE_TILES
            and int(disk.sectors[int(sprite.fields["sector"])].fields["type"]) in MOVING
        }
        checked = 0
        for index, relative in self._relative_angles(disk):
            if index not in moving:
                continue
            checked += 1
            self.assertIn(relative, (512, 1536),
                          f"fence sprite {index} stands edge-on in its own doorway")
        self.assertGreaterEqual(checked, 3)


@unittest.skipUnless(have_campaign(), "no Blood campaign maps")
class PushableFenceTests(unittest.TestCase):
    """A fence you can open is the switch for the sector it stands in."""

    def test_every_pushable_campaign_fence_opens_its_own_sector(self):
        """All 12 of them, without exception: tx_id equals its sector's rx_id."""
        from bloodmap.format import read_map

        pushable = matching = 0
        for path in campaign_maps():
            disk = read_map(path)
            for sprite in disk.sprites:
                if int(sprite.fields["picnum"]) not in (1044, 1064) or sprite.extra is None:
                    continue
                fields = sprite.extra.fields
                if not int(fields.get("trigger_push", 0)):
                    continue
                pushable += 1
                sector = disk.sectors[int(sprite.fields["sector"])]
                own_rx = int(sector.extra.fields.get("rx_id", 0)) if sector.extra else 0
                if own_rx and own_rx == int(fields.get("tx_id", 0)):
                    matching += 1
        self.assertGreaterEqual(pushable, 12)
        self.assertEqual(pushable, matching)

    @unittest.skipUnless(CANDIDATE.exists(), "no built candidate")
    def test_the_gate_leaves_open_their_own_gate(self):
        from bloodmap.format import read_map

        disk = read_map(CANDIDATE)
        found = 0
        for sprite in disk.sprites:
            if int(sprite.fields["picnum"]) not in (1044, 1064) or sprite.extra is None:
                continue
            fields = sprite.extra.fields
            if not int(fields.get("trigger_push", 0)):
                continue
            found += 1
            sector = disk.sectors[int(sprite.fields["sector"])]
            self.assertIsNotNone(sector.extra)
            self.assertEqual(int(fields["tx_id"]), int(sector.extra.fields["rx_id"]))
        self.assertGreaterEqual(found, 2)


class FlatSpriteMountingTests(unittest.TestCase):
    """A floor-aligned sprite is a plate, and a plate lies on a surface.

    Reported from play as "weirdly placed floor flat sprites in mid air". Eleven
    of them were, and the reason is that a table of canonical cstats is a table
    of *mountings*: tile 795's 224 is not a look, it is floor alignment, and it
    had been read as one more decorative sprite and hung on walls.

    Nothing could see it. A floor-aligned sprite is drawn as a flat plane at its
    own z -- `GetSpriteExtents` skips the extent arithmetic entirely for
    `(cstat & 0x30) == 0x20` -- so it has no top to poke through a ceiling and
    no bottom to sink into a floor, and every seating check in this project
    passed it.
    """

    def test_a_flat_tile_cannot_be_hung_on_a_wall(self):
        from bloodmap.planar_layout import PlanarLayout, PlanarLayoutError

        layout = PlanarLayout()
        layout.add_region("region:r", [(0, 0), (2048, 0), (2048, 2048), (0, 2048)],
                          floor_z=0, ceiling_z=-8192)
        layout.set_player_start("region:r", x=1024, y=1024, z=0)
        layout.place_on_wall("flat_on_wall", "region:r", a1=(0, 0), a2=(2048, 0),
                             t=0.5, height_player_heights=1.5,
                             picnum=795, cstat=224)
        with self.assertRaises(PlanarLayoutError) as caught:
            layout.compile()
        self.assertIn("floor alignment", str(caught.exception))

    def test_a_flat_tile_ignores_a_requested_hang(self):
        """The mounting outranks the drop, so the plate lands on its surface."""
        from bloodmap.planar_layout import _flat_lies_flush

        self.assertEqual(_flat_lies_flush(224, 0.5), 0)     # floor-aligned
        self.assertEqual(_flat_lies_flush(232, 0.35), 0)
        self.assertNotEqual(_flat_lies_flush(128, 0.5), 0)  # a facing sprite hangs

    @unittest.skipUnless(CANDIDATE.exists(), "no built candidate")
    def test_every_flat_sprite_in_this_level_rests_on_a_surface(self):
        from bloodmap.format import read_map

        disk = read_map(CANDIDATE)
        adrift = []
        for index, sprite in enumerate(disk.sprites):
            fields = sprite.fields
            if int(fields["cstat"]) & 0x30 != 0x20:
                continue
            sector = int(fields["sector"])
            if not 0 <= sector < len(disk.sectors):
                continue
            plane = disk.sectors[sector].fields
            z = int(fields["z"])
            drift = min(abs(z - int(plane["floor_z"])), abs(z - int(plane["ceiling_z"])))
            if drift > 256:
                adrift.append((index, int(fields["picnum"]), drift))
        self.assertEqual(adrift, [])
