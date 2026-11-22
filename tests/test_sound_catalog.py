"""The SFX parser and catalog expose the game's sound IDs and their evidence."""

import struct
import unittest
from pathlib import Path
from unittest.mock import patch

from tools import catalog, sound_catalog


class SoundCatalogTests(unittest.TestCase):
    def test_sfx_headers_join_raw_by_name_at_the_engine_rate(self):
        entries = {
            ("SFX", 66, "LOOP"): struct.pack("<5i", 100, 65536, 0, 1, 4) + b"hum\0",
            ("SFX", 3001, "QUOTE"): struct.pack("<5i", 120, 32768, 0, 5, -1) + b"voice\0",
            ("SFX", 800, "SILENT"): struct.pack("<5i", 0, 65536, 0, 1, -1) + b"\0",
            ("RAW", 0, "HUM"): b"\x80" * 25,
            ("RAW", 0, "VOICE"): b"\x80" * 50,
        }
        with patch.object(sound_catalog, "read_rff", return_value=entries):
            samples = sound_catalog.read_samples(Path("SOUNDS.RFF"))
        self.assertEqual((samples[66].raw_name, samples[66].rate, samples[66].loop_start),
                         ("HUM", 11025, 4))
        self.assertEqual(len(samples[66].pcm), 25)
        self.assertEqual((samples[3001].rate, samples[3001].playback_rate), (22050, 11025))
        self.assertEqual(samples[3001].loop_start, -1)
        self.assertIsNone(samples[800].pcm)

    def test_checked_in_entries_keep_independent_evidence(self):
        rows = sound_catalog.facts()
        self.assertEqual((rows["3001"]["name"], rows["3001"]["rate_hz"]), ("1002", 22050))
        self.assertIn("boomstick", rows["3001"]["transcript"]["text"].lower())
        self.assertEqual(rows["66"]["loop_start_sample"], 0)
        self.assertIsNone(rows["23"]["sample_count"])
        self.assertEqual(len([d for d in rows["742"]["descriptions"]
                              if "neocities.org" in d["source"]]), 2)
        wall = next(use for use in rows["300"]["campaign_uses"] if use["kind"] == "kWallGib")
        self.assertEqual((wall["count"], wall["example"]["map_index"]), (206, "E1M1:180"))

    def test_catalog_find_and_show_sounds(self):
        self.assertIn("SOUND 3001", catalog.show("sound:3001"))
        self.assertIn("Whisper", catalog.show("sound:3001"))
        self.assertIn("No sound ID", catalog.show("sound:99999"))
        self.assertIn("sound:100", catalog.find_all(["door", "creaking", "open"]))
        self.assertIn("sound:3001", sound_catalog.find(["boomstick"])[0])


if __name__ == "__main__":
    unittest.main()
