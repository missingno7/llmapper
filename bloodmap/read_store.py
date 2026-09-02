"""A DECOMPILATION's fact store: base facts, derived facts, provenance.

Not to be confused with `bloodmap/facts.py`, which is the COMPILER's and
landed on `blood-city-arcade` from the same research document while this was
being written. The two are independent implementations of section 2.1 from
opposite ends, and they differ in row shape: the compiler's row is
`{key, lod, source, fields}` with a closed tuple of 16 predicates and a
level-of-detail gate; the reader's is `{id, ...attrs, _from, _reader,
_layer}` with 35 declared predicates including the base records and the
ledger's own (`claims`, `candidate`, `selection`, `conflict`, `residue`).

Whether they should become one store is the owner's call and is in the review
queue, with the argument for it stated there: one store would let the
compiler's facts and the reader's facts be diffed directly, which IS the
symmetry test of decisions section 20. Merging them silently is not on --
neither shape is a superset of the other, and the writer's is not this
agent's to change.

`RESEARCH-OVERLAPPING-LAYERS-2026-09-02.md` section 2.1: the map's records are
the extensional database; every reader is a rule set that reads facts and
emits facts; a derived fact carries what it came from and which reader made
it; the store only grows within a run, and a later pass may SELECT among
candidates but never delete. JSONL per predicate on disk, a dict of tuples in
memory, no engine.

What that buys, concretely
==========================

* **relations are records** (IFC's objectified relationship): `join`, `void`,
  `fill`, `link`, `key`, `stack`, `attachment` are predicates with attributes
  and evidence, not fields hung on a wall. So is the space tree -- it is a set
  of `part_of` facts, which is why two hierarchies can coexist without either
  being the tree.
* **ambiguity survives** (Manifold's superset decompilation): a reading that
  could go two ways is emitted as two `candidate` facts and resolved by a
  named selection pass with its criterion stated, never inside the reader.
* **inconsistency is recorded** (ISO/IEC/IEEE 42010): `conflict` and `residue`
  are predicates like any other, with owners, rather than something the model
  hides by picking a side.
* **no percentage is typed.** Every number a report quotes is a query over
  these files.

The predicates this store knows are not a closed set -- a reader may emit a
new one -- but each must be declared in `PREDICATES` with what its `id` means,
so a file nobody described cannot appear in the directory.
"""

from __future__ import annotations

import json
import pathlib
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from typing import Any, Iterable, Sequence

SCHEMA = "llmapper.fact-store"
SCHEMA_VERSION = 1

#: `predicate -> what one row of it is`. Declared so the store can refuse a
#: file nobody described, and so a reader has to say what it is emitting.
PREDICATES: dict[str, str] = {
    # --- base: the records, as the map stores them ----------------------
    "sector": "one Build sector record, its fields verbatim",
    "wall": "one Build wall record, its fields verbatim",
    "sprite": "one Build sprite record, its fields verbatim",
    "xsector": "one XSECTOR, its fields verbatim",
    "xwall": "one XWALL, its fields verbatim",
    "xsprite": "one XSPRITE, its fields verbatim",
    # --- space ----------------------------------------------------------
    "part_of": "a record belongs to a place, in one aspect's hierarchy",
    "connects": "two sectors share a two-sided record",
    # --- surfaces -------------------------------------------------------
    "surface": "a set of wall records one projected material would produce",
    "frame": "the projection of one surface: origin, scale, phase",
    "attachment": "a wall record carried by a surface's frame",
    "stepped_run": "a stair: an origin, a rise, and the sectors on it",
    # --- kinds and joins -------------------------------------------------
    "surface_kind": "what kind of surface a sector's floor is",
    "join": "how two surfaces meet at one shared record",
    "unknown_join": "a shared record whose pair the writer's table has no row for",
    # --- overlays --------------------------------------------------------
    "island": "a height island: sectors standing one rise above the ground",
    #: Added by the compiler (P14b, slice 4). A void and a fill are two
    #: different claims about two different records, which is why they are two
    #: predicates: the void is a hole in a holder and belongs to the holder;
    #: the fill is what is in it, in a sector of its own with its own frame.
    "void": "an opening cut in a holder surface, and the holder it belongs to",
    "fill": "what occupies an opening, in a sector of its own",
    "lamp_delta": "one source's contribution to a sector's shade, before it "
                  "was summed",
    "kerb": "the band a road-side record shows at an island's edge",
    "sun": "the level's directional source, as a throw bearing",
    "shade_edge": "a same-z boundary where the floor shade changes",
    "shade_depth": "how many shadows deep a sector's floor is",
    "light_source": "a source that is not the sun",
    # --- edges -----------------------------------------------------------
    "edge_segment": "a run of boundary records of one edge kind",
    "offmap": "geometry the player cannot reach",
    # --- the plan ---------------------------------------------------------
    "corridor": "a street: road pieces of one axis and one width",
    "plan_edge": "an edge of the street graph, with a width class",
    "block": "a mass between the streets, with its envelope",
    # --- mechanisms --------------------------------------------------------
    "sentence": "one mechanism, read as a sentence",
    "realises": "which records a sentence is made of",
    "link": "a tx -> rx relation between records",
    "key": "a lock and the key that opens it",
    "stack": "a room-over-room link between two sectors",
    "condition": "a state a topology depends on",
    # --- the ledger, as predicates like any other -------------------------
    "claims": "an aspect says it determines one field of one record",
    "candidate": "a reading that could go more than one way, kept",
    "selection": "a named pass choosing among candidates, with its criterion",
    "conflict": "two exclusive claims on one field with different values",
    "residue": "something no reader explains, named",
}


#: The extensional database: the records as the map stores them. Everything
#: else in the store is derived from these, and these are regenerated rather
#: than committed -- they are the corpus restated.
BASE_PREDICATES = frozenset({
    "sector", "wall", "sprite", "xsector", "xwall", "xsprite", "connects"})


class FactError(ValueError):
    """A fact nobody declared, or a store asked for something it has not got."""


@dataclass(frozen=True)
class Fact:
    """One row. `sources` is what it was derived from; base facts have none."""

    predicate: str
    id: str
    attrs: dict[str, Any] = field(default_factory=dict)
    sources: tuple[str, ...] = ()
    reader: str = "map"
    layer: int | None = None

    def to_dict(self) -> dict[str, Any]:
        row: dict[str, Any] = {"id": self.id, **self.attrs}
        if self.sources:
            row["_from"] = list(self.sources)
        row["_reader"] = self.reader
        if self.layer is not None:
            row["_layer"] = int(self.layer)
        return row

    @classmethod
    def from_dict(cls, predicate: str, row: dict[str, Any]) -> "Fact":
        attrs = {key: value for key, value in row.items()
                 if not key.startswith("_") and key != "id"}
        return cls(predicate=predicate, id=str(row["id"]), attrs=attrs,
                   sources=tuple(row.get("_from", ())),
                   reader=str(row.get("_reader", "map")),
                   layer=row.get("_layer"))


@dataclass
class FactStore:
    """Facts by predicate. It only grows; nothing here deletes."""

    rows: dict[str, list[Fact]] = field(default_factory=lambda: defaultdict(list))

    def add(self, predicate: str, id: str, attrs: dict[str, Any] | None = None,
            *, sources: Iterable[str] = (), reader: str = "map",
            layer: int | None = None) -> Fact:
        if predicate not in PREDICATES:
            raise FactError(
                f"{predicate!r} is not a declared predicate. Declare it in "
                f"facts.PREDICATES with what one of its rows is; a file "
                f"nobody described is not a fact store")
        fact = Fact(predicate, str(id), dict(attrs or {}), tuple(sources),
                    reader, layer)
        self.rows[predicate].append(fact)
        return fact

    def extend(self, facts: Iterable[Fact]) -> int:
        count = 0
        for fact in facts:
            if fact.predicate not in PREDICATES:
                raise FactError(f"{fact.predicate!r} is not declared")
            self.rows[fact.predicate].append(fact)
            count += 1
        return count

    def __getitem__(self, predicate: str) -> list[Fact]:
        return list(self.rows.get(predicate, ()))

    def count(self, predicate: str) -> int:
        return len(self.rows.get(predicate, ()))

    def where(self, predicate: str, **equals: Any) -> list[Fact]:
        """Every row of one predicate whose attributes match."""
        out = []
        for fact in self.rows.get(predicate, ()):
            if all(fact.attrs.get(key) == value for key, value in equals.items()):
                out.append(fact)
        return out

    def by_predicate(self) -> dict[str, int]:
        return {key: len(value) for key, value in sorted(self.rows.items())}

    # --- disk ------------------------------------------------------------

    def write(self, directory: str | pathlib.Path) -> dict[str, int]:
        path = pathlib.Path(directory)
        path.mkdir(parents=True, exist_ok=True)
        written = {}
        for predicate, facts in sorted(self.rows.items()):
            lines = [json.dumps(fact.to_dict(), sort_keys=True) for fact in facts]
            (path / f"{predicate}.jsonl").write_text(
                "\n".join(lines) + "\n", encoding="utf-8")
            written[predicate] = len(lines)
        (path / "_manifest.json").write_text(json.dumps({
            "$schema": SCHEMA, "schema_version": SCHEMA_VERSION,
            "predicates": {key: PREDICATES[key] for key in sorted(written)},
            "rows": written,
            "readers": self.readers(),
            "base_predicates_are_the_corpus": {
                "which": sorted(BASE_PREDICATES),
                "why": ("these are the map's records verbatim. They are "
                        "regenerated rather than committed, on the project's "
                        "standing rule that the corpus is never committed and "
                        "the command that reproduces it is"),
            },
        }, indent=1, sort_keys=True), encoding="utf-8")
        return written

    @classmethod
    def read(cls, directory: str | pathlib.Path) -> "FactStore":
        store = cls()
        for path in sorted(pathlib.Path(directory).glob("*.jsonl")):
            predicate = path.stem
            if predicate not in PREDICATES:
                raise FactError(f"{path} holds an undeclared predicate")
            for line in path.read_text(encoding="utf-8").splitlines():
                if line.strip():
                    store.rows[predicate].append(
                        Fact.from_dict(predicate, json.loads(line)))
        return store

    def readers(self) -> dict[str, int]:
        counts: Counter = Counter()
        for facts in self.rows.values():
            for fact in facts:
                counts[fact.reader] += 1
        return dict(sorted(counts.items()))


# ---------------------------------------------------------------------------
# base facts: the records, as the map stores them
# ---------------------------------------------------------------------------

def _fields(item: Any) -> dict[str, Any]:
    return dict(item["fields"] if isinstance(item, dict) else item.fields)


def _extra(item: Any) -> dict[str, Any] | None:
    extra = item["blood"] if isinstance(item, dict) else getattr(item, "extra", None)
    if extra is None:
        return None
    return dict(extra["fields"] if isinstance(extra, dict) else extra.fields)


def base_facts(level: Any, *, source: str = "map") -> list[Fact]:
    """The extensional database: every record's fields, verbatim.

    Nothing is interpreted, nothing is dropped, and the extras are read
    through the key a `LevelIR` actually uses -- reading them through an
    `extra` attribute reports a map with 133 XSECTORs as having none.
    """
    out: list[Fact] = []
    for kind, items, extra_kind in (
            ("sector", level.sectors, "xsector"),
            ("wall", level.walls, "xwall"),
            ("sprite", level.sprites, "xsprite")):
        for index, item in enumerate(items):
            out.append(Fact(kind, f"{kind}:{index}", _fields(item),
                            reader=source))
            extra = _extra(item)
            if extra is not None:
                out.append(Fact(extra_kind, f"{extra_kind}:{index}", extra,
                                sources=(f"{kind}:{index}",), reader=source))
    return out
