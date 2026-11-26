"""Which parts of the library a project's code uses, which findings it leans on, and what nothing uses.

.. code-block:: bash

    python -m tools.library_usage blood-city              # what Gravesend uses, and the findings it leans on
    python -m tools.library_usage blood-city --json work/usage.json
    python -m tools.library_usage --unused                # library modules no project and no tool imports

Read off the source (every ``import`` and ``from ... import`` under the
project, and the names it takes), not off a run: a module a level imports and
never calls is still counted. A finding is leaned on when its ``code`` names a
module or function the project uses, or a file inside the project.
"""

from __future__ import annotations

import argparse
import ast
import json
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from bloodmap import findings as F  # noqa: E402
from bloodmap import project as P  # noqa: E402

SKIP_PARTS = {"__pycache__", "work"}


def _python(folder: Path) -> list[Path]:
    return [p for p in sorted(folder.rglob("*.py")) if not SKIP_PARTS & set(p.parts)]


def imports(files: list[Path]) -> dict[str, set[str]]:
    """bloodmap module -> the names taken from it ("*" when the module itself is imported)."""
    used: dict[str, set[str]] = defaultdict(set)
    for path in files:
        try:
            tree = ast.parse(path.read_text(encoding="utf-8"))
        except (SyntaxError, UnicodeDecodeError):
            continue
        aliases: dict[str, str] = {}
        inside = "bloodmap" in path.parts
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom) and inside and node.level == 1:
                # the library's own relative imports: `from .x import y`, `from . import x`
                if node.module:
                    used[f"bloodmap.{node.module}"].update(alias.name for alias in node.names)
                else:
                    for alias in node.names:
                        used[f"bloodmap.{alias.name}"].add("*")
            elif isinstance(node, ast.ImportFrom) and node.module:
                if node.module == "bloodmap":
                    for alias in node.names:
                        used[f"bloodmap.{alias.name}"].add("*")
                        aliases[alias.asname or alias.name] = f"bloodmap.{alias.name}"
                elif node.module.startswith("bloodmap."):
                    for alias in node.names:
                        used[node.module].add(alias.name)
            elif isinstance(node, ast.Import):
                for alias in node.names:
                    if alias.name.startswith("bloodmap."):
                        used[alias.name].add("*")
                        aliases[alias.asname or alias.name] = alias.name
        # `from bloodmap import wallplane` then `wallplane.text(...)`: the attribute is a name taken
        for node in ast.walk(tree):
            if isinstance(node, ast.Attribute) and isinstance(node.value, ast.Name) and node.value.id in aliases:
                used[aliases[node.value.id]].add(node.attr)
    return used


def project_usage(name: str) -> dict[str, Any]:
    """What one project's code takes from the library, and the findings whose code it uses."""
    project = P.named(name)
    used = imports(_python(project.root))
    names = {f"{module}.{n}" for module, taken in used.items() for n in taken if n != "*"}
    leaned = []
    for row in F.read():
        codes = row.get("code", [])
        # a module the project imports, a function it takes or calls, or a file of its own
        if any(code in used or code in names or code.startswith(f"projects/{project.key}/")
               or code.replace("/", ".").removesuffix(".py") in used for code in codes):
            leaned.append(row["id"])
    return {"project": project.key, "modules": {m: sorted(t) for m, t in sorted(used.items())},
            "findings": sorted(set(leaned))}


def unused_modules() -> list[str]:
    """Library modules that no project, no tool and no other library module imports (tests do not count)."""
    files = _python(ROOT / "projects") + _python(ROOT / "tools")
    used = set(imports(files))
    inside = imports(_python(ROOT / "bloodmap"))
    used |= set(inside)
    modules = sorted(f"bloodmap.{p.stem}" for p in (ROOT / "bloodmap").glob("*.py") if p.stem not in ("__init__", "__main__"))
    return [m for m in modules if m not in used]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split(chr(10))[0])
    parser.add_argument("project", nargs="?")
    parser.add_argument("--unused", action="store_true")
    parser.add_argument("--json")
    args = parser.parse_args(argv)
    if args.unused:
        rows = unused_modules()
        print(f"{len(rows)} library modules nothing outside the tests imports:")
        print(chr(10).join("  " + m for m in rows))
        return 0
    if not args.project:
        parser.error("name a project, or --unused")
    out = project_usage(args.project)
    print(f"{out['project']}: {len(out['modules'])} library modules, "
          f"{sum(len(v) for v in out['modules'].values())} names taken; leans on {len(out['findings'])} findings")
    for module, taken in out["modules"].items():
        print(f"  {module}: {', '.join(taken)}")
    if args.json:
        Path(args.json).parent.mkdir(parents=True, exist_ok=True)
        Path(args.json).write_text(json.dumps(out, indent=1), encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
