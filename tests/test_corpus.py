from __future__ import annotations

import unittest
import os
from pathlib import Path

from bloodmap.analysis import channel_graph, geometry_view, validate_map
from bloodmap.format import encode_map, parse_map, read_map
from bloodmap.corpus import list_corpus_maps
from tests.helpers import campaign_directory, corpus_map, named_corpus_maps


MAPS = Path(os.environ.get("BLOODMAP_CORPUS", Path(__file__).resolve().parents[1] / "maps" / "blood"))


def what_is_wrong(path: Path) -> list[str]:
    """What a map fails of: its version, its bytes through either model, its validity, what is observed of it."""
    original = path.read_bytes()
    disk = read_map(path)
    level = disk.to_level_ir()
    observation, focused = level.observe(), level.observe([level.player_start["sector"]])
    return [name for name, holds in (
        (f"version 0x{disk.version:04x}", disk.version >> 8 in {6, 7}),
        ("bytes", encode_map(disk) == original),
        ("bytes through the level", encode_map(level.to_disk_map()) == original),
        ("bytes through the build", encode_map(disk.to_build_ir().to_native_disk_map()) == original),
        ("parsed again", parse_map(encode_map(disk)) == disk),
        ("no error", not [d for d in validate_map(disk) if d.severity == "error"]),
        ("sectors observed", len(observation["sector_index"]) == len(disk.sectors)),
        ("walls observed", observation["level"]["counts"]["walls"] == len(disk.walls)),
        ("the start observed", focused["selection"]["sector_ids"] == [level.player_start["sector"]]),
    ) if not holds]


class CorpusTests(unittest.TestCase):
    def test_every_available_map_is_supported_and_byte_exact_through_both_models(self):
        """Every named-population Blood MAP must parse as a supported major (6 or 7).

        Campaign maps (`E*M*.MAP`) are v7. Hand-picked and converted maps in the
        other population directories may be v6 (for example BB9.MAP); the parser
        handles both, and this gate must not assume one population.

        The bulk `community/` population is deliberately out of scope: it has
        not passed the gate. `reports/blood-corpus-health.md` covers it
        fail-closed instead.
        """
        paths = named_corpus_maps()
        if not paths:
            self.skipTest("no local Blood MAP corpus; set BLOODMAP_CORPUS to enable")
        # each map is a check of its own, so they are shared between processes
        from concurrent.futures import ProcessPoolExecutor
        with ProcessPoolExecutor(max(2, min(12, (os.cpu_count() or 4) // 2))) as pool:
            for path, wrong in zip(paths, pool.map(what_is_wrong, paths)):
                with self.subTest(path=path.name):
                    self.assertEqual(wrong, [])

    def test_campaign_episode_maps_are_v7(self):
        paths = [item.path for item in list_corpus_maps(MAPS, population="blood-campaign")]
        if not paths:
            self.skipTest("no local Blood campaign E*M*.MAP files")
        self.assertTrue(campaign_directory().is_dir() or not paths)
        for path in paths:
            with self.subTest(path=path.name):
                self.assertEqual(read_map(path).version, 0x0700)

    def test_derived_views_cover_objects(self):
        path = corpus_map("E1M1.MAP")
        if not path.exists():
            self.skipTest("E1M1.MAP is not present in the local corpus")
        disk = read_map(path)
        geometry = geometry_view(disk)
        self.assertEqual(len(geometry), len(disk.sectors))
        self.assertEqual(sum(len(item["sprites"]) for item in geometry), len(disk.sprites))
        graph = channel_graph(disk)
        self.assertTrue(graph["channels"])


if __name__ == "__main__":
    unittest.main()
