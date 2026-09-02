"""The compiler's writer INTO the reader's fact store.

There is one store. `bloodmap/read_store.py` owns the row shape and the
predicate table; this module is the writing end, and it exists only to give a
compiler the two things a reader does not need: a level of detail on every
declaration, and the gate that makes one mean something.

Why they were merged
====================

Two files called `facts.py` landed on the same day from opposite ends of the
same research section, and neither knew about the other (queue item 31). They
were not interchangeable: the compiler's row was `{key, lod, source, fields}`
over a closed tuple of 14 predicates, the reader's is
`{id, ...attrs, _from, _reader, _layer}` over a declared table of 40 with a
description per predicate.

The argument for one store is the project's own. **The diff between what the
compiler declared and what a reader recovers from the built map is the
symmetry test of decisions section 20** -- "decompile, recompile, diff
STRUCTURE" becomes "diff two sets of rows". With two shapes that diff needed a
translation before it could be attempted at all.

So the reader's shape won, on the merits: its provenance is per row rather
than per declaration, its predicate table carries a description so a new
predicate cannot appear unannounced, and it is the superset -- it already
holds the map's own records and the ledger's `candidate`, `selection`,
`conflict` and `residue`. `lod` rides as an attribute and as `_layer`.

**A compiler predicate the table does not have is added to the table, with a
description, never invented locally.** `void`, `fill` and `lamp_delta` were
added there for this.

Level of detail
===============

    0  plan       the envelope solve: where the streets and islands are
    1  massing    shells, the ground surfaces, the light field
    2  facades    facade runs, openings, the frames
    3  dressing   inserts, lamps, decoration

**A pass at level N leaves every fact of level < N byte-identical.** A facade
pass that moves an envelope by one unit has changed the plan, and the plan is
not its to change; the map still compiles, every geometry gate still passes,
and the only evidence is a level-0 row that moved. The gate is now a QUERY
over `lod` rather than a shape of its own.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Iterable, Sequence

from .read_store import (
    BASE_PREDICATES, PREDICATES, Fact, FactError, FactStore as ReadStore)

#: The levels of detail, and the order they are built in.
LEVELS = {"plan": 0, "massing": 1, "facades": 2, "dressing": 3}
LEVEL_NAMES = {value: key for key, value in LEVELS.items()}

#: Which predicates a compiler writes. Not a second table -- every one of
#: these is in `read_store.PREDICATES`, and this list is only what a build
#: declares, so a query can ask for "the compiler's half" of a merged store.
COMPILER_PREDICATES = (
    "part_of", "surface", "island", "frame", "join", "void", "fill",
    "shade_depth", "lamp_delta", "link", "key", "sentence", "realises",
    "claims",
)
assert all(name in PREDICATES for name in COMPILER_PREDICATES)


class FactStore(ReadStore):
    """A `read_store.FactStore` a compiler can write declarations into.

    Nothing is added to the row shape. `add` takes the key as a tuple because
    a declaration's identity is compound -- ("piece", "plane#3") -- and joins
    it with colons into the `id` the reader's shape uses.
    """

    def add(self, predicate: str, key: Sequence, *, lod: int | None = None,
            source: str = "compiler", **fields: Any) -> Fact:
        if lod is None:
            raise FactError(
                f"{predicate!r}: a compiler's fact carries a level of detail. "
                f"It is what the LoD gate queries, and a declaration without "
                f"one cannot be told from a pass that had no business making "
                f"it")
        if lod not in LEVEL_NAMES:
            raise FactError(f"level of detail {lod!r} is not one of "
                            f"{sorted(LEVEL_NAMES)}")
        identity = key if isinstance(key, str) else ":".join(
            str(part) for part in key)
        return super().add(predicate, identity,
                           {**{k: _plain(v) for k, v in fields.items()},
                            "lod": int(lod)},
                           sources=(str(source),), reader="compiler",
                           layer=int(lod))

    # --- the queries a build asks -----------------------------------------

    def of(self, predicate: str) -> list:
        return self[predicate]

    def count(self) -> dict:
        return self.by_predicate()

    def by_level(self) -> dict:
        out: dict = {}
        for facts in self.rows.values():
            for fact in facts:
                level = fact.attrs.get("lod", fact.layer)
                if level is None:
                    continue
                out[int(level)] = out.get(int(level), 0) + 1
        return dict(sorted(out.items()))

    def lines_below(self, level: int) -> dict:
        """Every row of a level strictly below `level`, by predicate.

        A QUERY over `lod`, which is the whole of what the LoD gate is now.
        """
        out: dict = {}
        for predicate, facts in self.rows.items():
            keep = sorted(
                json.dumps(fact.to_dict(), sort_keys=True) for fact in facts
                if fact.attrs.get("lod", fact.layer) is not None
                and int(fact.attrs.get("lod", fact.layer)) < int(level))
            if keep:
                out[predicate] = keep
        return out


def _plain(value: Any) -> Any:
    if isinstance(value, (list, tuple)):
        return [_plain(item) for item in value]
    if isinstance(value, dict):
        return {str(k): _plain(v) for k, v in sorted(value.items())}
    if isinstance(value, bool) or value is None:
        return value
    if isinstance(value, (int, float, str)):
        return value
    return str(value)


# ---------------------------------------------------------------------------
# the level-of-detail gate
# ---------------------------------------------------------------------------

def compare_below(old: dict, new: dict, level: int) -> list[str]:
    """The difference between two `lines_below` snapshots, named."""
    out = []
    for predicate in sorted(set(old) | set(new)):
        a, b = old.get(predicate, []), new.get(predicate, [])
        if a == b:
            continue
        gone = [line for line in a if line not in b]
        came = [line for line in b if line not in a]
        out.append(
            f"{predicate}: a level-{level} "
            f"({LEVEL_NAMES.get(level, level)}) pass changed "
            f"{max(len(gone), len(came))} fact(s) below its level -- "
            f"{len(gone)} gone, {len(came)} new; first was {(gone or came)[0]}")
    return out


def lines_below(directory: str | Path, level: int) -> dict:
    """Every stored row of a level strictly below `level`, by predicate."""
    out: dict = {}
    for path in sorted(Path(directory).glob("*.jsonl")):
        keep = []
        for line in path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            row = json.loads(line)
            found = row.get("lod", row.get("_layer"))
            if found is not None and int(found) < int(level):
                keep.append(line)
        if keep:
            out[path.stem] = sorted(keep)
    return out


def lod_faults(before: str | Path, after: str | Path, level: int) -> list[str]:
    """A pass at level N leaves every fact of level < N byte-identical."""
    return compare_below(lines_below(before, level),
                         lines_below(after, level), level)


# ---------------------------------------------------------------------------
# the symmetry test: what was declared against what a reader recovers
# ---------------------------------------------------------------------------

def diff_stores(declared: ReadStore, recovered: ReadStore) -> dict:
    """Row for row, by predicate: the compiler's facts against a reader's.

    This is what one store buys. The two halves are not expected to agree --
    a compiler names a piece `plane#3` and a reader names it by sector -- and
    the SHAPE of the disagreement is the finding: a predicate the compiler
    writes and no reader recovers is a claim nothing checks, and a predicate a
    reader recovers and the compiler never declared is something the map says
    that the build did not mean to say.
    """
    out: dict[str, Any] = {}
    predicates = sorted(set(declared.rows) | set(recovered.rows))
    for predicate in predicates:
        mine = {fact.id for fact in declared[predicate]}
        theirs = {fact.id for fact in recovered[predicate]}
        out[predicate] = {
            "declared": len(mine),
            "recovered": len(theirs),
            "same_id": len(mine & theirs),
            "declared_only": len(mine - theirs),
            "recovered_only": len(theirs - mine),
            "base": predicate in BASE_PREDICATES,
        }
    return out


def diff_summary(diff: dict) -> dict:
    """The one line a manifest prints, and the two that matter under it."""
    both = [name for name, row in diff.items()
            if row["declared"] and row["recovered"]]
    return {
        "predicates": len(diff),
        "in both": sorted(both),
        "declared only": sorted(name for name, row in diff.items()
                                if row["declared"] and not row["recovered"]),
        "recovered only": sorted(name for name, row in diff.items()
                                 if row["recovered"] and not row["declared"]
                                 and not row["base"]),
        "rows declared": sum(row["declared"] for row in diff.values()),
        "rows recovered": sum(row["recovered"] for row in diff.values()),
        "ids that match": sum(row["same_id"] for row in diff.values()),
    }
