"""A level is a project the shared tools are pointed at: none of them has a level of its own, and the starter builds."""

from __future__ import annotations

import json
import os
import re
import runpy
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from bloodmap import project as P

ROOT = Path(__file__).resolve().parent.parent
OWED: set[str] = set()


class Descriptor(unittest.TestCase):
    def setUp(self):
        self.home = Path(tempfile.mkdtemp())
        self.root = self.home / "some-level"
        self.root.mkdir()
        (self.root / "project.json").write_text(json.dumps(
            {"$schema": P.SCHEMA, "schema_version": 1, "name": "Some Level", "kind": "level", "map": "level/some.MAP"}), "utf-8")

    def test_what_it_does_not_say_is_where_the_convention_puts_it(self):
        project = P.read(self.root)
        self.assertEqual((project.key, project.title, project.kind, project.plan_unit, project.ground_z),
                         ("some-level", "Some Level", "level", 1024, 0))
        self.assertEqual(project.map, self.root.resolve() / "level" / "some.MAP")
        self.assertEqual(project.rounds("crypt"), self.root.resolve() / "reports" / "critique" / "crypt")
        self.assertEqual(project.need("poses").name, "poses.py")

    def test_poses_are_a_python_table_or_a_hand_edited_maps_json(self):
        (self.root / "level").mkdir()
        (self.root / "level" / "poses.py").write_text('POSE_SETS = {"a": {"v": (1, 2, 3, 4, 100, "north")}}\n', "utf-8")
        self.assertEqual(P.read(self.root).pose_sets()["a"]["v"][5], "north")
        (self.root / "poses.json").write_text(json.dumps({"q": [{"id": "arrival", "x": 1, "y": 2, "angle": 3, "sector": 4}]}), "utf-8")
        data = json.loads((self.root / "project.json").read_text("utf-8"))
        (self.root / "project.json").write_text(json.dumps({**data, "poses": "poses.json"}), "utf-8")
        self.assertEqual(P.read(self.root).pose_sets()["q"]["arrival"]["sector"], 4)

    def test_a_directory_must_say_what_it_is(self):
        (self.root / "project.json").write_text(json.dumps({"$schema": P.SCHEMA, "kind": "castle"}), "utf-8")
        with self.assertRaises(P.ProjectError):
            P.read(self.root)
        with self.assertRaises(P.ProjectError):
            P.read(self.home / "nothing-here")

    def test_there_is_no_default_level(self):
        with mock.patch.dict(os.environ, {P.ENV: ""}):
            with self.assertRaises(P.ProjectError) as caught:
                P.named(None)
        self.assertIn("which project", str(caught.exception))
        with mock.patch.dict(os.environ, {P.ENV: str(self.root)}):
            self.assertEqual(P.named(None).key, "some-level")


class Repository(unittest.TestCase):
    def test_every_directory_under_projects_says_what_it_is(self):
        unnamed = [d.name for d in sorted(P.HOME.iterdir()) if d.is_dir() and not (d / "project.json").exists()]
        self.assertEqual(unnamed, [], "give each a project.json: its name, kind (level, analysis, fixture, pilot) and what it is about")
        for project in P.projects():
            self.assertIn(project.kind, P.KINDS, project.key)

    def test_no_shared_tool_or_library_module_has_a_level_typed_into_it(self):
        """A tool is told which level (`--project`, `LLMAPPER_PROJECT`); it may name one only in an example or a comment."""
        import ast

        live = [p.key for p in P.projects("level")]
        self.assertTrue(live)
        #: one-off miners that still write their corpus-wide output into the level they were written for, and two
        #: experiments on Gravesend's station: each is a debt, and none may be added to
        owed = OWED
        found = set()
        for folder in ("bloodmap", "tools"):
            for path in sorted((ROOT / folder).glob("*.py")):
                tree = ast.parse(path.read_text(encoding="utf-8"))
                said = {id(node.body[0].value) for node in ast.walk(tree)
                        if isinstance(node, (ast.Module, ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)) and node.body
                        and isinstance(node.body[0], ast.Expr) and isinstance(node.body[0].value, ast.Constant)}
                for node in ast.walk(tree):
                    if (isinstance(node, ast.Constant) and isinstance(node.value, str) and id(node) not in said
                            and any(name in node.value for name in live) and chr(10) not in node.value):
                        found.add(f"{folder}/{path.name}")
        self.assertEqual(sorted(found - owed), [], "take the level from bloodmap.project.named(args.project)")
        self.assertEqual(sorted(owed - found), [], "paid: take it off the list of what is owed")


class Starter(unittest.TestCase):
    def test_a_new_level_builds_as_it_stands_and_can_be_finished(self):
        from bloodmap import completion
        from tools import project as tool

        home = Path(tempfile.mkdtemp()) / "projects"
        # three levels down from a root that holds bloodmap/: the starter's build finds the repository by its own place
        root = tool.new("trial-level", "A Trial Level", home=home)
        self.assertEqual(P.read(root).map, root.resolve() / "level" / "trial-level.MAP")
        text = (root / "level" / "build.py").read_text("utf-8")
        self.assertNotIn("__NAME__", text)
        self.assertNotIn("blood-city", "".join(p.read_text("utf-8") for p in root.rglob("*") if p.is_file()))
        build = runpy.run_path(str(root / "level" / "build.py"))["build"]
        made = build()
        self.assertEqual(made.refused, [])
        self.assertTrue(P.read(root).map.exists())
        self.assertTrue(any(e["reached"] for e in completion.read(made.disk)["exits"]))
        self.assertEqual([s["name"] for s in made.manifest["stages"]], ["compile", "alignment", "gates", "light", "write"])
        with self.assertRaises(P.ProjectError):
            tool.new("trial-level", "Again", home=home)
        with self.assertRaises(P.ProjectError):
            tool.new("Bad Name", "x", home=home)


if __name__ == "__main__":
    unittest.main()
