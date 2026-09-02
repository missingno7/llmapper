"""What every stage needs: the map, the ART, and where to put its evidence.

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
from typing import Any

MAP_NAME = "E3M1"
PROJECT = pathlib.Path(__file__).resolve().parent.parent
REFERENCES = PROJECT / "references"


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
    from bloodmap.patterns import corpus_map_path

    return read_map(corpus_map_path(MAP_NAME)).to_level_ir()


def write(name: str, payload: Any) -> pathlib.Path:
    REFERENCES.mkdir(parents=True, exist_ok=True)
    path = REFERENCES / name
    path.write_text(json.dumps(payload, indent=1, sort_keys=True), encoding="utf-8")
    return path


def read(name: str) -> Any:
    return json.loads((REFERENCES / name).read_text(encoding="utf-8"))
