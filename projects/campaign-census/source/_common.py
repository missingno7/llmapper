"""What every census stage needs: the campaign, the ART, and where to store it.

Absolute paths only; the corpus is reached through `BLOODMAP_CORPUS` and the
ART through `BLOODMAP_ART`, never a junction.
"""

from __future__ import annotations

import json
import os
import pathlib
from typing import Any, Iterator

PROJECT = pathlib.Path(__file__).resolve().parent.parent
REFERENCES = PROJECT / "references"
POPULATION = "blood-campaign"


def art_sizes() -> dict:
    from bloodmap.texture_align import wall_art_sizes

    sizes = wall_art_sizes(os.environ.get("BLOODMAP_ART", "reference/blood"))
    if not sizes:
        raise SystemExit("no Blood ART; set BLOODMAP_ART to an absolute path. "
                         "A texture census without tile sizes measures nothing.")
    return sizes


def campaign() -> list:
    """Every campaign map, by path, in a stable order."""
    from bloodmap.patterns import list_corpus_maps

    return sorted((item.path for item in list_corpus_maps(population=POPULATION)),
                  key=lambda path: path.stem.upper())


def levels() -> Iterator[tuple[str, Any]]:
    """One decompiled level at a time, so 43 maps never sit in memory at once."""
    from bloodmap.format import read_map

    for path in campaign():
        yield path.stem.upper(), read_map(path).to_level_ir()


def write(name: str, payload: Any) -> pathlib.Path:
    REFERENCES.mkdir(parents=True, exist_ok=True)
    path = REFERENCES / name
    path.write_text(json.dumps(payload, indent=1, sort_keys=True), encoding="utf-8")
    return path
