"""What every stage needs: the project, the map, the ART, and where to put its evidence.

One copy of the stage program serves every `projects/<map>-decompiled`; the
project is the first command-line argument of whichever stage runs:

    python -m tools.decompile_stages.run_all projects/e3m1-decompiled

Absolute paths only. A worktree has no `maps/` and no `reference/` of its own
-- the corpus is reached through `BLOODMAP_CORPUS` and the ART through
`BLOODMAP_ART`, never through a junction (`10_AGENT_EXECUTION_PROTOCOL.md`,
"Irreplaceable local data"). A stage that cannot find either STOPS: a reader
that silently measures nothing reports the map as understood.
"""

from __future__ import annotations

import json
import os
import pathlib
import sys
from typing import Any

USAGE = "usage: python -m tools.decompile_stages.<stage> projects/<map>-decompiled"

_PROJECT: pathlib.Path | None = None


def use(path: str | os.PathLike[str]) -> pathlib.Path:
    """Make `path` the project every stage in this process reads and writes."""
    global _PROJECT
    resolved = pathlib.Path(path).resolve()
    if not resolved.is_dir():
        raise SystemExit(f"{path!s} is not a project directory. {USAGE}")
    _PROJECT = resolved
    _check_map_name()
    return resolved


def project() -> pathlib.Path:
    """The project directory: set by `use`, else the first command-line argument."""
    if _PROJECT is None:
        if len(sys.argv) < 2:
            raise SystemExit(f"which project? {USAGE}")
        use(sys.argv[1])
    assert _PROJECT is not None
    return _PROJECT


def references() -> pathlib.Path:
    return project() / "references"


def map_name() -> str:
    """The map a project is about, taken from the project's own directory name.

    `projects/e3m1-decompiled` is about E3M1. Derived rather than written down
    so that a second decompilation needs no edit to any stage: the whole
    eight-layer machinery is one copy of the same code, and what differs
    between two maps is the map. Verified against `provenance.json`, which the
    decompile wrote, so a directory renamed by hand fails loudly instead of
    quietly reading somebody else's level.
    """
    return project().name.upper().replace("-DECOMPILED", "")


def _check_map_name() -> None:
    path = project() / "provenance.json"
    if not path.exists():
        return
    of = json.loads(path.read_text(encoding="utf-8")).get("of", "")
    if of and pathlib.Path(of).stem.upper() != map_name():
        raise SystemExit(
            f"{project().name} says it is about {map_name()}, and its "
            f"provenance.json was written for {of}. One of the two is wrong, "
            f"and reading the wrong level silently is worse than stopping.")


def art_dir() -> str:
    """Where the Blood ART lives. `BLOODMAP_ART` wins, then `reference/blood`."""
    return os.environ.get("BLOODMAP_ART", "reference/blood")


def art_sizes() -> dict[int, tuple[int, int]]:
    from bloodmap.texture_align import wall_art_sizes

    sizes = wall_art_sizes(art_dir())
    if not sizes:
        raise SystemExit(
            f"no Blood ART under {art_dir()!r}. Set BLOODMAP_ART to an "
            f"absolute path; a texture reader without tile sizes measures "
            f"nothing and would call the map understood.")
    return sizes


def level() -> Any:
    from bloodmap.format import read_map
    from bloodmap.corpus import corpus_map_path

    return read_map(corpus_map_path(map_name())).to_level_ir()


def write(name: str, payload: Any) -> pathlib.Path:
    references().mkdir(parents=True, exist_ok=True)
    path = references() / name
    path.write_text(json.dumps(payload, indent=1, sort_keys=True), encoding="utf-8")
    return path


def read(name: str) -> Any:
    return json.loads((references() / name).read_text(encoding="utf-8"))
