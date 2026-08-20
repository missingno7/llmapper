from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from bloodmap.cli import main
from bloodmap.decompiler import DecompilerError, LevelSource, decompile_level, emit_python_source
from bloodmap.format import encode_map, write_map
from tests.helpers import synthetic_two_sector_map


class LevelDecompilerTests(unittest.TestCase):
    def test_decompilation_keeps_exact_truth_and_partitions_primary_spaces(self):
        disk = synthetic_two_sector_map()
        level = disk.to_level_ir()

        source = decompile_level(level, source_name="fixture.MAP")

        self.assertEqual(source.schema, "llmapper.level-source")
        self.assertEqual(source.to_level_ir().to_dict(), level.to_dict())
        self.assertEqual(LevelSource.from_dict(json.loads(json.dumps(source.to_dict()))).to_dict(), source.to_dict())
        root = source.node("level")
        self.assertEqual(root["sources"]["sectors"], [0, 1])
        self.assertEqual(root["sources"]["walls"], list(range(8)))
        self.assertEqual(root["sources"]["sprites"], [0, 1])
        spaces = [item for item in source.hierarchy["nodes"] if item["kind"] == "space"]
        self.assertEqual(
            sorted(sector for item in spaces for sector in item["sources"]["sectors"]),
            [0, 1],
        )
        self.assertTrue(any(
            item["kind"] in {"connects", "internal_connection"}
            and item["wall_refs"] == [1, 7]
            for item in source.hierarchy["relations"]
        ))
        self.assertTrue(all(asset["interpreted_meaning"] is None for asset in source.assets))

    def test_python_source_is_executable_and_reconstructs_level_source(self):
        original = synthetic_two_sector_map().to_level_ir()
        source = decompile_level(original)
        text = emit_python_source(source)
        namespace: dict[str, object] = {}

        exec(compile(text, "generated_level.py", "exec"), namespace)

        rebuilt = namespace["level_source"]()  # type: ignore[index,operator]
        self.assertIsInstance(rebuilt, LevelSource)
        self.assertEqual(rebuilt.to_level_ir().to_dict(), original.to_dict())
        tree = namespace["build_level"]()  # type: ignore[index,operator]
        self.assertEqual(tree["kind"], "level")
        self.assertTrue(tree["compiled_children"])

    def test_validation_rejects_semantic_document_that_loses_native_sources(self):
        source = decompile_level(synthetic_two_sector_map().to_level_ir()).to_dict()
        source["hierarchy"]["nodes"][0]["sources"]["walls"].pop()

        with self.assertRaisesRegex(DecompilerError, "root does not preserve every exact walls"):
            LevelSource.from_dict(source)

    def test_cli_decompile_python_and_compile_source_are_byte_exact(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            original = root / "original.MAP"
            document = root / "level-source.json"
            python_source = root / "level_source.py"
            rebuilt = root / "rebuilt.MAP"
            disk = synthetic_two_sector_map()
            write_map(disk, original)

            self.assertEqual(main([
                "decompile", str(original), "-o", str(document), "--python", str(python_source),
            ]), 0)
            self.assertEqual(main(["compile-source", str(document), "-o", str(rebuilt)]), 0)

            payload = json.loads(document.read_text(encoding="utf-8"))
            self.assertEqual(payload["source"]["authority"], "exact_level_ir")
            self.assertIn("def build_level", python_source.read_text(encoding="utf-8"))
            self.assertEqual(rebuilt.read_bytes(), encode_map(disk))


if __name__ == "__main__":
    unittest.main()
