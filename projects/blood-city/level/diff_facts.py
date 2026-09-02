"""The symmetry test: what the compiler declared against what a reader finds.

Decisions section 20 asks for "decompile, recompile, diff STRUCTURE". With one
store that is a diff of two sets of rows, and this is it: the city's own facts
against the facts P15's readers recover from the city's own map.

The two halves are not expected to agree row for row, and the SHAPE of the
disagreement is the finding. A predicate the compiler writes and no reader
recovers is a claim nothing checks. A predicate a reader recovers and the
compiler never declared is something the map says that the build did not mean
to say. And where both speak, the id conventions differ -- a compiler names a
piece `plane#3` and a reader names it by sector -- so a matching id is a
stronger agreement than a matching count, and both are reported.

The readers run here are the ones that need nothing hand-authored: joins,
islands, light, surfaces, stairs, edges and the plan. Layer 1 wants a
hierarchy somebody wrote and layer 5 wants the mechanism curriculum, so
neither is in this diff, and that absence is named rather than hidden.

    PYTHONPATH=. python projects/blood-city/level/diff_facts.py
"""

from __future__ import annotations

import json
import pathlib
import sys

HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parents[2]
for path in (str(ROOT), str(HERE)):
    if path not in sys.path:
        sys.path.insert(0, path)

from bloodmap import read_facts                                   # noqa: E402
from bloodmap.facts import diff_stores, diff_summary              # noqa: E402
from bloodmap.format import read_map                              # noqa: E402
from bloodmap.read_edges import read_edges                        # noqa: E402
from bloodmap.read_islands import read_islands                    # noqa: E402
from bloodmap.read_joins import (                                 # noqa: E402
    join_census, surface_kinds)
from bloodmap.read_light import read_light                        # noqa: E402
from bloodmap.read_plan import read_plan                          # noqa: E402
from bloodmap.read_stairs import read_stairs                      # noqa: E402
from bloodmap.read_store import FactStore as ReadStore            # noqa: E402
from bloodmap.read_surfaces import read_surfaces                  # noqa: E402
from bloodmap.texture_align import wall_art_sizes                 # noqa: E402
from bloodmap.texture_frame import sector_index                   # noqa: E402

MAP = HERE / "slice2-streets.MAP"
FACTS = ROOT / "projects/blood-city/facts"

#: Named, so the diff's silence about them is not read as agreement.
NOT_RUN = (
    "layer 1 (part_of, the space tree) wants a hierarchy somebody wrote",
    "layer 5 (sentence, link, key, realises) wants the mechanism curriculum",
    "layer 8 (the ledger's candidate/selection/conflict/residue) is layer 5's",
)


def recovered(level, *, art_sizes) -> ReadStore:
    owners = sector_index(level)
    store = ReadStore()
    kinds = surface_kinds(level, owners=owners)
    census = join_census(level, kinds["kinds"], owners=owners)
    store.extend(read_facts.layer3(level, {"kinds": kinds, "census": census}))
    surfaces = read_surfaces(level, art_sizes=art_sizes)
    stairs = read_stairs(level)
    store.extend(read_facts.layer2(level, surfaces, stairs))
    islands = read_islands(level, kinds["kinds"], owners=owners)
    light = read_light(level, kinds["kinds"], owners=owners)
    store.extend(read_facts.layer4(level, islands, light))
    store.extend(read_facts.layer6(
        level, read_edges(level, kinds["kinds"], owners=owners)))
    store.extend(read_facts.layer7(
        level, read_plan(level, kinds["kinds"], owners=owners)))
    return store


def main() -> int:
    if not MAP.exists() or not FACTS.exists():
        print("build the city first")
        return 1
    level = read_map(MAP).to_level_ir()
    theirs = recovered(level, art_sizes=wall_art_sizes("reference/blood"))
    mine = ReadStore.read(FACTS)
    diff = diff_stores(mine, theirs)
    print(json.dumps(diff_summary(diff), indent=1))
    print("\nrow for row, by predicate:")
    print(f"  {'predicate':<16}{'declared':>9}{'recovered':>10}"
          f"{'same id':>9}{'mine only':>11}{'theirs only':>12}")
    for name, row in sorted(diff.items()):
        if row["base"]:
            continue
        print(f"  {name:<16}{row['declared']:>9}{row['recovered']:>10}"
              f"{row['same_id']:>9}{row['declared_only']:>11}"
              f"{row['recovered_only']:>12}")
    print("\nnot in this diff, and why:")
    for line in NOT_RUN:
        print(f"  - {line}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
