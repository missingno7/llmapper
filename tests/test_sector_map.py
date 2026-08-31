import json
import tempfile
import unittest
from pathlib import Path

from bloodmap.format import read_map
from bloodmap.sector_map import render_sector_map


class SectorMapTests(unittest.TestCase):
    def _map_path(self) -> Path:
        path = Path(__file__).parents[1] / "maps" / "blood" / "campaign" / "E1M1.MAP"
        if not path.exists():
            self.skipTest("E1M1.MAP is not present in the local Blood corpus")
        return path

    def test_real_map_contains_authoritative_labels_and_highlights(self):
        path = self._map_path()
        svg = render_sector_map(
            read_map(path),
            highlight_sectors=(150, 149, 133, 36, 34, 33, 32),
            highlight_walls=(1453, 241),
        )
        for sector in (150, 149, 133, 36, 34, 33, 32):
            self.assertIn(f'data-sector-label="{sector}"', svg)
            self.assertIn(f">S{sector}</text>", svg)
        for wall in (1453, 241):
            self.assertIn(f'data-wall="{wall}"', svg)
            self.assertIn(f">W{wall}</text>", svg)
        self.assertIn('id="sectors"', svg)

    def test_trajectory_overlay_ignores_malformed_lines(self):
        path = self._map_path()
        with tempfile.TemporaryDirectory() as folder:
            trajectory = Path(folder) / "trajectory.ndjson"
            trajectory.write_text(
                json.dumps({"x": 0, "y": 0}) + "\nnot json\n" +
                json.dumps({"x": 100, "y": 200}) + "\n", encoding="utf-8"
            )
            svg = render_sector_map(read_map(path), trajectory=trajectory)
        self.assertIn('id="trajectory"', svg)
        self.assertIn('stroke="#ffe66d"', svg)


if __name__ == "__main__":
    unittest.main()
