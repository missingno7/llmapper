"""The whole test suite, a process a module, as many at once as the machine has room for: the same tests, in a tenth of the time.

    python -m tools.suite                  every module; work/suite.log holds what failed, the last lines say how it went
    python -m tools.suite --library        the library's and the tools' own tests (`tests/`): no level is needed
    python -m tools.suite --project blood-city   one project's regression tests (`projects/<name>/tests/`)
    python -m tools.suite door blasts      the modules whose name holds one of these words
    python -m tools.suite --changed        the modules that import what the working tree has changed, and the changed tests
    python -m tools.suite --slow 12        and the twelve slowest

`python -m unittest discover -s tests` runs one test after another in one process
(649 s on 2026-11-24, on a machine with 32 threads). Each module here is its own
process, so a module that leans on what another left behind fails: none does.
A module that takes long is cut into its tests (`SPLIT`).

Two kinds of test, in two places. `tests/` holds what must be true of the
library and the tools whatever levels exist: a test there builds its own
fixture or reads the corpus. `projects/<name>/tests/` holds what must stay true
of one level: its places, its walks, the owner's rulings on it. A project's
module is named `<project>:<module>` here, so a word finds it by either.
"""

from __future__ import annotations

import argparse
import ast
import os
import re
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LOG = ROOT / "work" / "suite.log"
#: modules run a test at a time, because one of them is as long as the rest together
SPLIT = ("test_anchors", "test_fragment")
#: started first, longest first, so that none is left running alone at the end
FIRST = ("test_corpus", "test_anchors", "test_completion", "test_fragment", "test_mining_population", "test_doom_semantics",
         "test_doom_convert", "test_duke_transport", "test_light_stage", "test_texture_frame", "test_assembly")


def modules() -> list[str]:
    """Every test module: the library's by name, a project's as `<project>:<name>`."""
    out = sorted(path.stem for path in (ROOT / "tests").glob("test_*.py"))
    for folder in sorted((ROOT / "projects").glob("*/tests")):
        out += sorted(f"{folder.parent.name}:{path.stem}" for path in folder.glob("test_*.py"))
    return out


def path_of(module: str) -> Path:
    if ":" in module:
        project, name = module.split(":", 1)
        return ROOT / "projects" / project / "tests" / f"{name}.py"
    return ROOT / "tests" / f"{module}.py"


def tests_of(module: str) -> list[str]:
    """Every test of a module by name, so that one can be run alone."""
    tree = ast.parse(path_of(module).read_text(encoding="utf-8"))
    return [f"tests.{module}.{cls.name}.{fn.name}" for cls in tree.body if isinstance(cls, ast.ClassDef)
            for fn in cls.body if isinstance(fn, ast.FunctionDef) and fn.name.startswith("test")]


def units(chosen: list[str]) -> list[str]:
    order = {name: k for k, name in enumerate(FIRST)}
    out = []
    for name in sorted(chosen, key=lambda m: (order.get(m, len(FIRST)), m)):
        out += [name] if ":" in name else (tests_of(name) or [f"tests.{name}"]) if name in SPLIT else [f"tests.{name}"]
    return out


def imports(path: Path) -> set[str]:
    """The modules of this repository a file names in an import, by their last name."""
    try:
        tree = ast.parse(path.read_text(encoding="utf-8"))
    except (OSError, SyntaxError):
        return set()
    names: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            names |= {alias.name.rsplit(".", 1)[-1] for alias in node.names}
        elif isinstance(node, ast.ImportFrom):
            names |= {(node.module or "").rsplit(".", 1)[-1]} | {alias.name for alias in node.names}
    return names


def changed() -> list[str]:
    """The test modules that reach a changed file through imports, and those that are changed themselves.

    A module that reads a file the change wrote (the city's MAP, a shelf of
    knowledge) does not say so in an import, so a changed MAP brings every
    `test_*` that names it.
    """
    said = subprocess.run(["git", "status", "--porcelain", "-uall"], cwd=ROOT, capture_output=True, text=True).stdout
    paths = [line[3:].strip().strip('"') for line in said.splitlines()]
    stems = {Path(p).stem for p in paths if p.endswith(".py")}
    texts = {Path(p).name for p in paths if not p.endswith(".py")}
    files = [p for where in ("bloodmap", "tools", "projects/*/level") for p in ROOT.glob(f"{where}/*.py")]
    reach = {p.stem: imports(p) for p in files}
    grown = True
    while grown:
        more = {name for name, used in reach.items() if name not in stems and used & stems}
        grown = bool(more)
        stems |= more
    # a project's tests load its build by path, which no import says: any change under a project brings all of them
    touched = {Path(p).parts[1] for p in paths if Path(p).parts[:1] == ("projects",) and len(Path(p).parts) > 2}
    out = []
    for name in modules():
        path = path_of(name)
        if (name.split(":", 1)[0] in touched or path.stem in stems or imports(path) & stems
                or any(t in path.read_text(encoding="utf-8") for t in texts)):
            out.append(name)
    return out


def run(unit: str) -> tuple[str, float, int, str]:
    start = time.perf_counter()
    where = path_of(unit).parent.relative_to(ROOT).as_posix() if ":" in unit else ""
    # a project's module is found in its own directory; the repository's root stays on the path for `bloodmap` and `tools`
    command = (["discover", "-s", where, "-t", where, "-p", unit.split(":", 1)[1] + ".py"] if where else [unit])
    made = subprocess.run([sys.executable, "-m", "unittest", *command], cwd=ROOT, capture_output=True, text=True,
                          encoding="utf-8", errors="replace")
    return unit, time.perf_counter() - start, made.returncode, made.stdout + made.stderr


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("words", nargs="*")
    parser.add_argument("--changed", action="store_true")
    parser.add_argument("--library", action="store_true", help="only tests/: what is true whatever levels exist")
    parser.add_argument("--project", default=None, help="only one project's tests: a directory under projects/")
    parser.add_argument("--slow", type=int, default=0)
    parser.add_argument("--jobs", type=int, default=max(2, min(16, (os.cpu_count() or 4) // 2)))
    args = parser.parse_args(argv)
    chosen = changed() if args.changed else modules()
    if args.library:
        chosen = [name for name in chosen if ":" not in name]
    if args.project:
        if not (ROOT / "projects" / args.project / "tests").is_dir():
            print(f"no tests at projects/{args.project}/tests: python -m tools.project list")
            return 2
        chosen = [name for name in chosen if name.startswith(args.project + ":")]
    if args.words:
        chosen = [name for name in chosen if any(word in name for word in args.words)]
    if not chosen and not args.changed:
        print("no test module answers to that: nothing ran, which is not a pass")
        return 2
    start = time.perf_counter()
    rows = []
    with ThreadPoolExecutor(args.jobs) as pool:
        for done in as_completed([pool.submit(run, unit) for unit in units(chosen)]):
            rows.append(done.result())
    counts = {"ran": 0, "failures": 0, "errors": 0, "skipped": 0, "expected failures": 0}
    failed = []
    for unit, _seconds, code, text in rows:
        ran = re.search(r"^Ran (\d+) test", text, re.M)
        counts["ran"] += int(ran[1]) if ran else 0
        for name in list(counts)[1:]:
            found = re.search(rf"(?<!expected ){name}=(\d+)", text) if name == "failures" else re.search(rf"{name}=(\d+)", text)
            counts[name] += int(found[1]) if found else 0
        if code or not ran:
            failed.append((unit, text))
    LOG.parent.mkdir(exist_ok=True)
    tail = [f"Ran {counts['ran']} tests in {time.perf_counter() - start:.1f}s ({len(chosen)} modules, {args.jobs} at once)",
            ("FAILED" if failed else "OK") + " (" + ", ".join(f"{k}={v}" for k, v in list(counts.items())[1:] if v) + ")"]
    LOG.write_text("\n".join([text for _u, text in sorted(failed)] + tail) + "\n", encoding="utf-8")
    for unit, text in sorted(failed):
        print("\n".join(line for line in text.splitlines() if line.startswith(("FAIL:", "ERROR:"))) or f"DIED: {unit}")
    for unit, seconds, _code, _text in sorted(rows, key=lambda r: -r[1])[:args.slow]:
        print(f"{seconds:6.1f} s  {unit}")
    print("\n".join(tail))
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
