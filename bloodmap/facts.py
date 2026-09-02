"""The map is a fact store, and the manifest is a query over it.

Research section 2.1: base facts are the records' fields as stored; derived
facts carry provenance -- the declaration they came from and the reader that
made them; the store only grows within a run, and a later pass may SELECT
among candidates but never delete. JSONL per predicate on disk, a list of
rows in memory, no engine.

Why a compiler needs this and a manifest does not suffice
========================================================

Slice 2i's read-back named three gaps and every one of them is a gap in the
MAP, not in what the compiler knew. Two islands joined by a path are one
connected component on disk, and the compiler declared them as two surfaces.
The depth `k` is nowhere in a Build sector, and the compiler cut the piece
that has it. A lamp's delta is summed into `floor_shade` before it is
written, and the ledger arbitrated it. Writing the facts beside the map closes
all three -- and the ones that remain open are then genuinely about the map,
which is the distinction worth having.

Level of detail
===============

Every declaration carries one, and the numbers are the owner's::

    0  plan       the envelope solve: where the streets and islands are
    1  massing    shells, the ground surfaces, the light field
    2  facades    facade runs, openings, the frames
    3  dressing   inserts, lamps, decoration

The gate that makes it mean something: **a pass at level N leaves every fact
of level < N byte-identical.** A facade pass that moves an envelope by one
unit has changed the plan, and the plan is not its to change.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterable, Sequence

#: The levels of detail, and the order they are built in.
LEVELS = {"plan": 0, "massing": 1, "facades": 2, "dressing": 3}
LEVEL_NAMES = {value: key for key, value in LEVELS.items()}

#: The predicates this store holds. A predicate not named here is refused
#: rather than defaulted -- the same rule as the join table's, for the same
#: reason: an undeclared kind of fact is a question for a person.
#:
#: The space graph and the mission graph are kept APART (research 2.3):
#: `part_of` and `join` are the space; `link`, `key`, `sentence` are the
#: mission; `realises` is the correspondence between them.
PREDICATES = (
    # the space graph
    "part_of", "surface", "island", "frame", "join", "void", "fill",
    # the field
    "shade_depth", "lamp_delta",
    # the mission graph
    "link", "key", "sentence", "realises",
    # the ledger
    "claims",
)


class FactError(ValueError):
    """A fact nobody declared the shape of."""


@dataclass(frozen=True)
class Fact:
    """One row. `key` is the thing it is about; `fields` is what is said.

    `source` is the declaration it came from, so a fact can always be traced
    back to the sentence that produced it rather than to the pass that
    happened to write it.
    """

    predicate: str
    key: tuple
    fields: dict
    lod: int
    source: str

    def __post_init__(self) -> None:
        if self.predicate not in PREDICATES:
            raise FactError(
                f"{self.predicate!r} is not a predicate. The store holds "
                f"{sorted(PREDICATES)}; a kind of fact nobody declared is a "
                f"question for a person, not a new column")
        if self.lod not in LEVEL_NAMES:
            raise FactError(f"level of detail {self.lod!r} is not one of "
                            f"{sorted(LEVEL_NAMES)}")

    def row(self) -> dict:
        return {"key": list(self.key), "lod": int(self.lod),
                "source": str(self.source),
                "fields": {k: _plain(v) for k, v in sorted(self.fields.items())}}

    def line(self) -> str:
        return json.dumps(self.row(), sort_keys=True, separators=(",", ":"))


def _plain(value: Any) -> Any:
    if isinstance(value, (list, tuple)):
        return [_plain(item) for item in value]
    if isinstance(value, dict):
        return {str(k): _plain(v) for k, v in sorted(value.items())}
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float, str)) or value is None:
        return value
    return str(value)


@dataclass
class FactStore:
    """Rows, by predicate. It only grows."""

    rows: dict = field(default_factory=dict)

    def add(self, predicate: str, key: Sequence, *, lod: int, source: str,
            **fields: Any) -> Fact:
        fact = Fact(str(predicate), tuple(key), dict(fields), int(lod),
                    str(source))
        self.rows.setdefault(fact.predicate, []).append(fact)
        return fact

    def of(self, predicate: str) -> list:
        return list(self.rows.get(predicate, ()))

    def count(self) -> dict:
        return {name: len(rows) for name, rows in sorted(self.rows.items())}

    def by_level(self) -> dict:
        out: dict = {}
        for rows in self.rows.values():
            for fact in rows:
                out[fact.lod] = out.get(fact.lod, 0) + 1
        return dict(sorted(out.items()))

    def lines_below(self, level: int) -> dict:
        """The in-memory twin of the on-disk `lines_below`, for a live run."""
        out: dict = {}
        for predicate, rows in self.rows.items():
            keep = sorted(fact.line() for fact in rows
                          if fact.lod < int(level))
            if keep:
                out[predicate] = keep
        return out

    def write(self, directory: str | Path) -> list:
        """One file per predicate, sorted, so a diff is a diff of facts.

        Sorted on purpose: the LoD gate compares files byte for byte, and a
        store that wrote its rows in whatever order a pass happened to visit
        them would report every reordering as a change.
        """
        target = Path(directory)
        target.mkdir(parents=True, exist_ok=True)
        written = []
        for predicate in PREDICATES:
            rows = self.rows.get(predicate)
            path = target / f"{predicate}.jsonl"
            if not rows:
                continue
            lines = sorted(fact.line() for fact in rows)
            path.write_text("\n".join(lines) + "\n", encoding="utf-8",
                            newline="\n")
            written.append(path)
        return written

    @classmethod
    def read(cls, directory: str | Path) -> "FactStore":
        store = cls()
        for path in sorted(Path(directory).glob("*.jsonl")):
            predicate = path.stem
            for line in path.read_text(encoding="utf-8").splitlines():
                if not line.strip():
                    continue
                row = json.loads(line)
                store.add(predicate, row["key"], lod=row["lod"],
                          source=row["source"], **row["fields"])
        return store


def lines_below(directory: str | Path, level: int) -> dict:
    """Every stored line of a level strictly below `level`, by predicate."""
    out: dict = {}
    for path in sorted(Path(directory).glob("*.jsonl")):
        keep = []
        for line in path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            if int(json.loads(line)["lod"]) < int(level):
                keep.append(line)
        if keep:
            out[path.stem] = sorted(keep)
    return out


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


def lod_faults(before: str | Path, after: str | Path, level: int) -> list[str]:
    """A pass at level N leaves every fact of level < N byte-identical.

    The one gate that makes a level of detail mean anything. A facade pass
    that moves an envelope by a unit has changed the plan, and the plan is not
    its to change -- the map still compiles, every geometry gate still passes,
    and the only evidence is that a level-0 line moved.
    """
    return compare_below(lines_below(before, level),
                         lines_below(after, level), level)
