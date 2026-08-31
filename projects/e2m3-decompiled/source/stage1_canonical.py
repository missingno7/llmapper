"""Stage 1 -- canonical: exact truth, and the honest label for what it is.

``bloodmap.decompiler.emit_python_source`` will produce "readable Python" for
E2M3.  For this map that file is **138,008 lines and 8.4 MB**, of which 136,616
lines are one embedded ``LevelIR`` literal, and the functions around it only look
nodes up in that literal.  Nothing you edit in those functions changes a single
wall.  It is a viewer, not source code, and this stage exists to say so in one
place rather than let a later reader mistake it for authoring.

What *is* authoritative is the MAP.  This stage loads it and hands back exact
truth; every later stage is a reading of this one and may be wrong without any
of this becoming wrong.

    python -m projects.e2m3_decompiled.source.stage1_canonical   # not a package
    python projects/e2m3-decompiled/source/stage1_canonical.py

Regenerate the exact level source (2.3 MB) when it is actually needed:

    python -m bloodmap decompile maps/blood/E2M3.MAP -o work/E2M3.level-source.json
"""

from __future__ import annotations

import pathlib

from bloodmap.decompiler import decompile_level
from bloodmap.format import read_map
from bloodmap.patterns import corpus_map_path

#: The corpus is a registry of provenance directories, not a flat
#: folder; missing_ok so importing this module without a local corpus
#: still yields a path that simply does not exist.
MAP_PATH = corpus_map_path("E2M3", missing_ok=True)

#: From ``provenance.json``; the number every later claim is anchored to.
EXPECTED = {"sectors": 340, "walls": 2808, "sprites": 454}


def exact_level():
    """The authoritative Blood level, parsed from the MAP with no interpretation."""
    return read_map(MAP_PATH).to_level_ir()


def level_source():
    """Exact truth plus the derived hierarchy; ``exact_level_ir`` stays authority."""
    return decompile_level(exact_level(), source_name=MAP_PATH.name)


def main() -> None:
    level = exact_level()
    counts = {
        "sectors": len(level.sectors),
        "walls": len(level.walls),
        "sprites": len(level.sprites),
    }
    assert counts == EXPECTED, counts
    source = level_source()
    kinds: dict[str, int] = {}
    for node in source.hierarchy["nodes"]:
        kinds[node["kind"]] = kinds.get(node["kind"], 0) + 1
    print("exact:", counts)
    print("derived hierarchy:", kinds)
    print("structure recovery:", source.hierarchy["structure_recovery"]["coverage"])


if __name__ == "__main__":
    main()
