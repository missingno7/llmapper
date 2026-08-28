"""The XMapEdit sample maps: isolated mechanisms, read and understood.

133 maps, each demonstrating one thing with nothing else in the way. They are a
better oracle than the campaign for anything mechanical, because a campaign map
answers "what did the designers usually do" and a sample answers "what does the
engine actually require".

The first one they answered was a fault five audits had missed.
"""

from __future__ import annotations

import glob
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SAMPLES = ROOT / "maps" / "blood" / "samples"
MAPS = ROOT / "maps" / "blood"
CANDIDATE = ROOT / "projects" / "reasoned-authoring-v1" / "level" / "candidate-v5.MAP"


def sample_maps() -> list[str]:
    return sorted(glob.glob(str(SAMPLES / "*" / "*.map")))


def campaign_maps() -> list[str]:
    return [
        p for p in sorted(glob.glob(str(MAPS / "*.MAP")))
        if re.match(r"^E[1-46]M[1-9]$", Path(p).stem.upper())
    ]


@unittest.skipUnless(sample_maps(), "no sample maps")
class SampleFidelityTests(unittest.TestCase):
    def test_every_sample_parses_and_re_encodes_byte_for_byte(self):
        """The strongest statement the reader can make about a file.

        Not "it parsed" -- that only says nothing raised. Byte equality after a
        full parse and re-encode says every field was understood well enough to
        put back exactly where it came from, including the ones nothing reads.
        """
        from bloodmap.format import encode_map, parse_map, read_map

        checked = 0
        for path in sample_maps():
            disk = read_map(path)
            blob = encode_map(disk)
            self.assertEqual(parse_map(blob), disk, path)
            self.assertEqual(blob, Path(path).read_bytes(), path)
            checked += 1
        self.assertGreater(checked, 120)

    def test_no_sample_has_a_structural_error(self):
        """These are reference maps: an error against one is a bug in the check."""
        from bloodmap.analysis import validate_map
        from bloodmap.format import read_map

        for path in sample_maps():
            errors = [d for d in validate_map(read_map(path)) if d.severity == "error"]
            self.assertEqual(errors, [], f"{path}: {errors[:2]}")


@unittest.skipUnless(sample_maps() and campaign_maps(), "no maps")
class MarkerOwnerTests(unittest.TestCase):
    """A marker is bound by its `owner`, and deleted when that binding fails.

    `dbLoadMap` does not read `marker0`/`marker1` from the file. It rebuilds
    them by walking the marker statnum and asking each marker which sector it
    owns -- and a marker whose owner names no XSECTOR sector reaches
    `DeleteSprite`. A level can therefore write both marker fields correctly,
    leave `owner` at -1, and lose every marker it has.

    That is what this project's level did, through five audits, because every
    check it had was looking at the field the engine ignores.
    """

    MARKER_TYPES = frozenset({3, 4, 5, 8})

    #: The rule is keyed on the *statnum*, not the type. `dbLoadMap` walks
    #: `headspritestat[kStatMarker]`, so a marker-typed sprite filed anywhere
    #: else is neither bound nor deleted -- it is simply not a marker as far as
    #: that loop is concerned. Three sprites in the Modern samples are exactly
    #: that: kMarkerWarpDest on statnum 0, used by the NoOne extension through a
    #: different path.
    MARKER_STATNUM = 10

    def _markers(self, path):
        from bloodmap.format import read_map

        disk = read_map(path)
        for sprite in disk.sprites:
            if int(sprite.fields["type"]) not in self.MARKER_TYPES:
                continue
            if int(sprite.fields["status"]) != self.MARKER_STATNUM:
                continue
            yield disk, sprite

    def test_every_campaign_and_sample_marker_has_an_owner(self):
        total = owned = 0
        for path in campaign_maps() + sample_maps():
            for disk, sprite in self._markers(path):
                total += 1
                owner = int(sprite.fields["owner"])
                if 0 <= owner < len(disk.sectors) and disk.sectors[owner].extra is not None:
                    owned += 1
        self.assertGreater(total, 1500)
        self.assertEqual(total, owned)

    def test_a_marker_off_the_marker_statnum_is_not_subject_to_the_rule(self):
        """Three Modern samples file a kMarkerWarpDest on statnum 0.

        They are untouched by the loader's marker loop, which is why they can
        carry owner -1 and still work.
        """
        from bloodmap.format import read_map

        found = 0
        for path in sample_maps():
            disk = read_map(path)
            for sprite in disk.sprites:
                if int(sprite.fields["type"]) not in self.MARKER_TYPES:
                    continue
                if int(sprite.fields["status"]) == self.MARKER_STATNUM:
                    continue
                found += 1
                self.assertEqual(int(sprite.fields["owner"]), -1)
        self.assertGreaterEqual(found, 3)

    def test_the_owner_is_not_always_the_sector_the_marker_stands_in(self):
        """387 campaign markers mark a sector they are not inside.

        So a constructor cannot simply copy the containing sector: `owner` is
        the sector the marker *controls*, and the two coincide only usually.
        """
        same = different = 0
        for path in campaign_maps():
            for _disk, sprite in self._markers(path):
                if int(sprite.fields["owner"]) == int(sprite.fields["sector"]):
                    same += 1
                else:
                    different += 1
        self.assertGreater(different, 200)
        self.assertGreater(same, different)

    def test_the_validator_catches_an_unowned_marker(self):
        from bloodmap.analysis import validate_map
        from bloodmap.format import read_map

        disk = read_map(campaign_maps()[0])
        self.assertEqual(
            [d for d in validate_map(disk) if d.code == "marker-unowned"], [])
        for sprite in disk.sprites:
            if int(sprite.fields["type"]) in self.MARKER_TYPES:
                sprite.fields["owner"] = -1
                break
        found = [d for d in validate_map(disk) if d.code == "marker-unowned"]
        self.assertEqual(len(found), 1)
        self.assertEqual(found[0].severity, "error")

    @unittest.skipUnless(CANDIDATE.exists(), "no built candidate")
    def test_the_level_binds_every_marker(self):
        from bloodmap.analysis import validate_map
        from bloodmap.format import read_map

        disk = read_map(CANDIDATE)
        self.assertEqual(
            [d for d in validate_map(disk) if d.code == "marker-unowned"], [])
        markers = [s for s in disk.sprites if int(s.fields["type"]) in self.MARKER_TYPES]
        self.assertGreaterEqual(len(markers), 5)
        for sprite in markers:
            owner = int(sprite.fields["owner"])
            self.assertTrue(0 <= owner < len(disk.sectors))
            self.assertIsNotNone(disk.sectors[owner].extra)


if __name__ == "__main__":
    unittest.main()
