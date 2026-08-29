"""The overlap-visibility validator, proved on geometry built to fail it.

A checker that has never fired is not known to work. This builds three maps, one
per tier, and shows the validator telling them apart:

* an overlap in two disconnected components, safe with no geometry at all;
* an overlap joined by a route whose one wall is one-way, safe because the flood
  stops at `cstat & 32`;
* an overlap with a plain portal route, which one viewer reaches both halves of.

The third is the fault the whole check exists to catch, and it is built here
deliberately so that a regression that stops catching it fails a test.
"""

from __future__ import annotations

import unittest

from bloodmap import overlap_visibility as ov
from bloodmap.format import SECTOR_FIELDS, WALL_FIELDS, encode_map, parse_map
from bloodmap.model import DiskMap, DiskObject, ExtraHeader


def _empty(fields):
    return {name: 0 for name, _codec in fields}


def _extra_header() -> ExtraHeader:
    return ExtraHeader(
        copyright=b"\0" * 64, xsprite_size=56, xwall_size=24, xsector_size=60,
        xmp_signature=b"\0" * 3, xmp_header_version=0, xmp_map_flags=0,
        xmp_board_width=0, xmp_board_height=0, xmp_palette=0,
        xmp_sky_repeat_count=0, xmp_sky_visibility=0, reserved=b"\0" * 37,
    )


class Builder:
    """The smallest thing that can express 'these sectors, joined like this'.

    Rectangles only, and joins named as (sector, side) pairs, because every
    question this module asks is about the portal graph rather than about shape.
    """

    SIDES = {"north": 0, "east": 1, "south": 2, "west": 3}

    def __init__(self) -> None:
        self.rects: list[tuple[int, int, int, int, int, int]] = []
        self.joins: list[tuple[int, str, int, str, bool]] = []

    def add(self, x0: int, y0: int, x1: int, y1: int,
            ceiling_z: int = -8192, floor_z: int = 8192) -> int:
        self.rects.append((x0, y0, x1, y1, ceiling_z, floor_z))
        return len(self.rects) - 1

    def join(self, left: int, left_side: str, right: int, right_side: str,
             *, one_way: bool = False, blind: bool = False) -> None:
        """Make two walls a portal.

        `one_way` sets cstat 32 on the first wall only, which is what the flag
        normally means: the flood cannot cross that way and can cross back.
        `blind` sets it on both, giving a portal a body walks through and the
        renderer refuses to look through in either direction.
        """
        self.joins.append((left, left_side, right, right_side, one_way, blind))

    def build(self) -> DiskMap:
        sectors, walls = [], []
        wall_of: dict[tuple[int, str], int] = {}
        for index, (x0, y0, x1, y1, ceiling_z, floor_z) in enumerate(self.rects):
            first = len(walls)
            corners = [(x0, y0), (x1, y0), (x1, y1), (x0, y1)]
            for offset, (x, y) in enumerate(corners):
                fields = _empty(WALL_FIELDS)
                fields.update(x=x, y=y, point2=first + (offset + 1) % 4,
                              next_wall=-1, next_sector=-1, picnum=1,
                              over_picnum=-1, extra=-1)
                walls.append(DiskObject(fields))
            for name, offset in self.SIDES.items():
                wall_of[(index, name)] = first + offset
            sector = _empty(SECTOR_FIELDS)
            sector.update(wall_ptr=first, wall_count=4, ceiling_z=ceiling_z,
                          floor_z=floor_z, extra=-1)
            sectors.append(DiskObject(sector))

        for left, left_side, right, right_side, one_way, blind in self.joins:
            a, b = wall_of[(left, left_side)], wall_of[(right, right_side)]
            walls[a].fields.update(next_wall=b, next_sector=right)
            walls[b].fields.update(next_wall=a, next_sector=left)
            if one_way or blind:
                walls[a].fields["cstat"] |= ov.CSTAT_WALL_1WAY
            if blind:
                walls[b].fields["cstat"] |= ov.CSTAT_WALL_1WAY

        header = {
            "start_x": 0, "start_y": 0, "start_z": 0, "start_angle": 0,
            "start_sector": 0, "sky_bits": 0, "visibility": 800, "matt_id": 0,
            "sky_type": 0, "revision": 1, "num_sectors": len(sectors),
            "num_walls": len(walls), "num_sprites": 0,
        }
        disk = DiskMap(version=0x0700, header=header,
                       extra_header=_extra_header(), sky_offsets=[0],
                       sectors=sectors, walls=walls, sprites=[],
                       source_crc32=0, source_size=0)
        return parse_map(encode_map(disk))


def _overlap_pair(disk) -> tuple[int, int]:
    pairs = ov.overlapping_pairs(disk)
    assert pairs, "the fixture was supposed to contain an overlap"
    return (pairs[0][0], pairs[0][1])


class TierTests(unittest.TestCase):
    """One map per tier, and the validator has to name the right one."""

    def test_tier_1_disconnected_components_are_proved_safe(self):
        # Two sectors on the same ground with nothing joining either of them to
        # the other's half of the map. The flood follows nextsector and nothing
        # else, so no viewpoint anywhere can hold both.
        b = Builder()
        b.add(0, 0, 4096, 4096)                       # 0: a room
        b.add(6144, 0, 10240, 4096)                   # 1: a room elsewhere
        b.add(1024, 1024, 3072, 3072, 16384, 24576)   # 2: under room 0
        b.join(0, "east", 1, "west")
        disk = b.build()

        verdicts = ov.audit(disk)
        self.assertEqual(len(verdicts), 1)
        self.assertEqual(verdicts[0].cut, "disconnection")
        self.assertTrue(verdicts[0].safe)
        self.assertEqual(verdicts[0].depends_on_walls, 0)

    def test_tier_2_a_wall_blind_from_both_sides_severs_the_flood(self):
        # The same overlap, but now the cellar is reachable -- through a wall
        # carrying cstat 32 on *both* of its sides. `!(wal->cstat & 32)` is the
        # traversal condition in both renderers, so the flood stops dead there
        # whichever way it arrives. A body still walks through: blocking is bit
        # 1 and this is bit 5.
        b = Builder()
        b.add(0, 0, 4096, 4096)                       # 0: the room
        b.add(0, 4096, 4096, 6144)                    # 1: a passage south of it
        b.add(1024, 1024, 3072, 3072, 16384, 24576)   # 2: under the room
        b.join(0, "south", 1, "north")
        b.join(1, "east", 2, "east", blind=True)
        disk = b.build()

        verdicts = ov.audit(disk)
        self.assertEqual(len(verdicts), 1)
        self.assertEqual(verdicts[0].cut, "one_way")
        self.assertTrue(verdicts[0].safe)
        # One wall's flag is the whole proof, which is worth saying out loud.
        self.assertEqual(verdicts[0].depends_on_walls, 1)

    def test_one_sided_is_not_a_proof(self):
        """A finding, not a nicety: half a cut is no cut.

        `cstat & 32` lives on one wall. Flagging the wall the flood would use on
        the way *in* leaves the partner wall open, so a viewer standing on the
        far side floods back out and reaches both halves after all. The tier-2
        construction has to be blind from both sides to be a proof.
        """
        b = Builder()
        b.add(0, 0, 4096, 4096)
        b.add(0, 4096, 4096, 6144)
        b.add(1024, 1024, 3072, 3072)                 # same band, so only the
        b.join(0, "south", 1, "north")                # cut could save it
        b.join(1, "east", 2, "east", one_way=True)
        verdict = ov.audit(b.build())[0]
        self.assertEqual(verdict.cut, "uncut")
        # And the viewer is the cellar itself, looking back out.
        self.assertEqual(verdict.witness, 2)

    def test_tier_3_a_plain_portal_route_is_co_rendered(self):
        # Nothing cuts the flood, so one sector reaches both halves and the
        # renderer is asked to order two sets of walls it cannot. The two also
        # share a height band, so the z-aware fallback cannot tell them apart
        # either -- this is the case with nothing left to save it.
        b = Builder()
        b.add(0, 0, 4096, 4096)                       # 0: the room
        b.add(0, 4096, 4096, 6144)                    # 1: a passage
        b.add(1024, 1024, 3072, 3072)                 # 2: inside the room, same z
        b.join(0, "south", 1, "north")
        b.join(1, "east", 2, "east")
        disk = b.build()

        verdicts = ov.audit(disk)
        self.assertEqual(len(verdicts), 1)
        verdict = verdicts[0]
        self.assertEqual(verdict.cut, "uncut")
        self.assertFalse(verdict.safe)
        self.assertIsNotNone(verdict.witness)
        self.assertEqual(ov.refused(disk), [verdict])

    def test_the_direction_of_a_one_way_wall_is_respected(self):
        """cstat 32 lives on one wall, so the cut has a direction."""
        b = Builder()
        b.add(0, 0, 4096, 4096)
        b.add(0, 4096, 4096, 6144)
        b.add(1024, 1024, 3072, 3072, 16384, 24576)
        b.join(0, "south", 1, "north")
        b.join(1, "east", 2, "east", one_way=True)
        disk = b.build()
        forward, _backward = ov.flood_graph(disk)
        # The passage cannot flood into the cellar; the cellar can flood back.
        self.assertNotIn(2, forward[1])
        self.assertIn(1, forward[2])


class ExemptionTests(unittest.TestCase):
    def test_a_room_over_room_pair_is_not_a_fault(self):
        """`mirrors.cpp` draws a link's far side; `scansector` never sees it."""
        b = Builder()
        b.add(0, 0, 4096, 4096)
        b.add(0, 4096, 4096, 6144)
        b.add(1024, 1024, 3072, 3072)                 # same band on purpose
        b.join(0, "south", 1, "north")
        b.join(1, "east", 2, "east")
        disk = b.build()
        self.assertEqual(ov.audit(disk)[0].cut, "uncut")

        # Give the two halves a matching link id and the verdict changes.
        from bloodmap.format import SPRITE_FIELDS, XSPRITE_SCHEMA
        from bloodmap.model import PackedExtra

        for sector, marker in ((0, 11), (2, 12)):
            fields = _empty(SPRITE_FIELDS)
            fields.update(x=2048, y=2048, z=0, sector=sector, status=0,
                          type=marker, picnum=2332, extra=len(disk.sprites) + 1,
                          owner=-1, index=len(disk.sprites))
            xfields = {name: 0 for name, _bits, _signed in XSPRITE_SCHEMA}
            xfields.update(reference=len(disk.sprites), data_1=1, target=-1,
                           burn_source=-1)
            disk.sprites.append(DiskObject(fields, PackedExtra(
                "XSPRITE", xfields, b"\0" * 4)))
        disk.header["num_sprites"] = len(disk.sprites)

        self.assertEqual(ov.audit(disk)[0].cut, "link")
        self.assertEqual(ov.refused(disk), [])


class BandTests(unittest.TestCase):
    """What the campaign actually leans on, and it is not a cut.

    Cuts account for 10.8% of the campaign's 2,929 overlapping pairs, and one of
    the two kinds is a single map's idiom. Everything else is height bands and
    distance, so a classification that had no name for that would call Blood
    unsafe 89% of the time and mean nothing.
    """

    def test_a_cellar_under_a_room_is_safe_without_any_cut(self):
        b = Builder()
        b.add(0, 0, 4096, 4096)                       # 0: the room
        b.add(0, 4096, 4096, 6144)                    # 1: a passage
        b.add(1024, 1024, 3072, 3072, 16384, 24576)   # 2: a cellar under it
        b.join(0, "south", 1, "north")
        b.join(1, "east", 2, "east")
        verdict = ov.audit(b.build())[0]
        self.assertEqual(verdict.cut, "band_separated")
        self.assertTrue(verdict.safe)
        # 16384 below the room's floor: the masonry between them.
        self.assertEqual(verdict.slab, 8192)

    def test_a_cut_is_reported_ahead_of_a_band(self):
        """A proof beats a property. Disconnection is checked first."""
        b = Builder()
        b.add(0, 0, 4096, 4096)
        b.add(6144, 0, 10240, 4096)
        b.add(1024, 1024, 3072, 3072, 16384, 24576)
        b.join(0, "east", 1, "west")
        self.assertEqual(ov.audit(b.build())[0].cut, "disconnection")


class ReportTests(unittest.TestCase):
    def test_a_pair_resting_on_one_wall_is_named(self):
        b = Builder()
        b.add(0, 0, 4096, 4096)
        b.add(0, 4096, 4096, 6144)
        b.add(1024, 1024, 3072, 3072, 16384, 24576)
        b.join(0, "south", 1, "north")
        b.join(1, "east", 2, "east", blind=True)
        summary = ov.report(b.build())
        self.assertEqual(summary["by_cut"], {"one_way": 1})
        self.assertEqual(len(summary["resting_on_one_wall"]), 1)
        self.assertEqual(summary["uncut"], [])


if __name__ == "__main__":
    unittest.main()
