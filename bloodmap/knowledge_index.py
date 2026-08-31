"""One entry point for "what do we know about this?".

The knowledge store grew faster than the way in. `compile_catalog.py` indexed
the pattern catalog and stopped there; everything since -- object-context
families, contrast verdicts, assemblies, functional regions, facades, effect
and conditional-route summaries, and the owner's own tile readings -- lives in
its own report and is found by remembering which one.

This is the index over all of it. It is not a second store: every entry points
back at the file it came from and carries that file's provenance, so the
answer to a query is a list of sources rather than a new claim.

Three provenance grades, and the distinction is the point:

* **OWNER** -- the owner said so. Reproduced, never rewritten by mining.
* **DERIVED** -- measured from maps. A number with a population behind it.
* **INTERPRETED** -- a name or role put on a measurement. A hypothesis that
  survives until a counterexample splits it.

`design-index` indexes *maps* by fingerprint and is a different axis; this
indexes knowledge. Neither subsumes the other and neither duplicates it.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

SCHEMA = "llmapper.knowledge-index"
SCHEMA_VERSION = 1

OWNER = "OWNER"
DERIVED = "DERIVED"
INTERPRETED = "INTERPRETED"
GRADES = (OWNER, DERIVED, INTERPRETED)

#: What an entry can be about. A query names one of these and an id.
SUBJECT_TILE = "tile"
SUBJECT_FAMILY = "family"
SUBJECT_SECTOR = "map-sector"
SUBJECT_CONSTRUCTOR = "constructor"
SUBJECT_MAP = "map"
SUBJECTS = (SUBJECT_TILE, SUBJECT_FAMILY, SUBJECT_SECTOR, SUBJECT_CONSTRUCTOR,
            SUBJECT_MAP)


class KnowledgeIndexError(ValueError):
    pass


def _tokens(text: str) -> list[str]:
    out, current = [], []
    for char in text:
        if char.isalnum():
            current.append(char)
        elif current:
            out.append("".join(current))
            current = []
    if current:
        out.append("".join(current))
    return out


def _stem(token: str) -> str:
    """Trim a trailing plural. Nothing cleverer -- a stemmer would start
    matching things the writer did not mean."""
    return token[:-1] if len(token) > 3 and token.endswith("s") else token


@dataclass(frozen=True)
class Entry:
    """One thing known, and where it is written down."""

    subject_kind: str
    subject: str
    says: str
    provenance: str
    source: str
    population: str = ""
    terms: tuple[str, ...] = ()
    detail: Mapping[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        out = {
            "subject_kind": self.subject_kind, "subject": self.subject,
            "says": self.says, "provenance": self.provenance,
            "source": self.source,
        }
        if self.population:
            out["population"] = self.population
        if self.terms:
            out["terms"] = list(self.terms)
        if self.detail:
            out["detail"] = dict(self.detail)
        return out

    def haystack(self) -> list[str]:
        text = " ".join((self.subject, self.says, " ".join(self.terms))).lower()
        return [token for token in _tokens(text) if token]

    def matches(self, needle: str) -> bool:
        """Every word of the query has to land somewhere in the entry.

        Token-wise, not substring-wise, and that is not fussiness: a
        substring search for tile `332` also returns `2332`, the stack
        marker, which is a different tile with a different meaning. A bare
        number must match a whole token.

        Trailing plurals are trimmed on both sides, so "swinging doors"
        reaches an entry indexed under "swinging door".
        """
        wanted = [_stem(token) for token in _tokens(needle.lower()) if token]
        if not wanted:
            return False
        available = [_stem(token) for token in self.haystack()]
        for token in wanted:
            if token.isdigit():
                if token not in available:
                    return False
            elif not any(token in item for item in available):
                return False
        return True


def _repo() -> Path:
    return Path(__file__).resolve().parents[1]


def _read(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None


def _rel(path: Path) -> str:
    try:
        return str(path.relative_to(_repo())).replace("\\", "/")
    except ValueError:
        return str(path).replace("\\", "/")


# ---------------------------------------------------------------------------
# The sources
# ---------------------------------------------------------------------------

def _owner_entries() -> list[Entry]:
    from .owner_anchors import OwnerAnchorError, load_owner_anchors

    try:
        anchors = load_owner_anchors()
    except OwnerAnchorError:
        return []
    source = "knowledge/blood/design/owner-anchors-v1.json"
    out = []
    for anchor in anchors:
        terms = [anchor.label_en, anchor.kind, str(anchor.picnum)]
        if anchor.binding:
            terms.append(f"{anchor.binding} binding")
        if anchor.wiring:
            terms.append("wiring marker")
        says = f"tile {anchor.picnum} is {anchor.label_en} ({anchor.kind})"
        if anchor.binding:
            says += f"; {anchor.binding} binding"
            says += (", may contribute to naming" if anchor.may_name
                     else ", material only -- never names")
        if anchor.state_pair:
            pairs = ", ".join(f"{k}={v}" for k, v in sorted(anchor.state_pair.items()))
            says += f"; state pair {pairs}"
            terms.append("state pair")
        out.append(Entry(SUBJECT_TILE, str(anchor.picnum), says, OWNER, source,
                         terms=tuple(terms),
                         detail={"binding": anchor.binding,
                                 "may_name": anchor.may_name,
                                 "kind": anchor.kind}))
    return out


def _catalog_entries() -> list[Entry]:
    path = _repo() / "knowledge" / "blood" / "design" / "catalog-v1.json"
    document = _read(path)
    if not isinstance(document, dict):
        return []
    source = _rel(path)
    out = []
    for pattern in document.get("patterns", []) or []:
        if not isinstance(pattern, dict):
            continue
        name = str(pattern.get("label") or pattern.get("id") or "")
        terms = [name, str(pattern.get("id") or ""), *(pattern.get("tags") or [])]
        out.append(Entry(
            SUBJECT_FAMILY, name or str(pattern.get("id")),
            str(pattern.get("description") or name),
            INTERPRETED, source,
            population=str(pattern.get("population") or ""),
            terms=tuple(str(item) for item in terms if item),
            detail={"status": pattern.get("status"),
                    "confidence": pattern.get("confidence")}))
    return out


def _knowledge_file_entries() -> list[Entry]:
    """Every other versioned knowledge file, at file granularity.

    A whole-file entry rather than one per row: these files hold measured
    numbers whose shapes differ, and inventing a common row schema for them
    would be a second store. The query points a reader at the file.
    """
    directory = _repo() / "knowledge" / "blood" / "design"
    skip = {"catalog-v1.json", "owner-anchors-v1.json"}
    out = []
    for path in sorted(directory.glob("*-v*.json")):
        if path.name in skip:
            continue
        document = _read(path)
        if not isinstance(document, dict):
            continue
        name = path.stem.rsplit("-v", 1)[0].replace("-", " ")
        rows = next((len(value) for value in document.values()
                     if isinstance(value, list)), 0)
        out.append(Entry(
            SUBJECT_FAMILY, name,
            f"{name}: {rows} recorded entries" if rows else name,
            DERIVED, _rel(path),
            population=str(document.get("population") or ""),
            terms=(name, path.stem)))
    return out


#: Report families worth indexing, and what each is about. A report not named
#: here is still findable by filename; naming them is what lets a query for
#: "swinging doors" reach the rotating-door census.
REPORT_TERMS: dict[str, tuple[str, ...]] = {
    "blood-rotating-doors": ("rotating door", "swinging gate", "turnstile",
                             "swinging door", "vane", "rotor"),
    "blood-swept-mechanisms": ("slide", "rotate", "swept", "payload",
                               "carried sprites", "room over room", "ror"),
    "blood-conditional-topology": ("conditional", "gate", "crack", "keyed door",
                                   "lift", "base graph", "blocking"),
    "blood-effects-motion": ("effect", "door", "lift", "z-motion", "embedding"),
    "blood-effects-switches": ("switch", "hidden switch", "channel"),
    "blood-hidden-switch-placement": ("hidden switch", "placement", "closet"),
    "blood-facade-grammar": ("facade", "frontage", "bay", "street"),
    "blood-door-families": ("door family", "door"),
    "blood-key-signifiers": ("key", "lock", "emblem"),
    "blood-passage-oracle": ("passage", "oracle", "turnstile"),
    "blood-role-v2": ("design role", "naming", "plane"),
    "E1M4-bundle": ("bundle", "multi-view", "disagreement"),
}


def _report_entries() -> list[Entry]:
    directory = _repo() / "reports"
    out = []
    for path in sorted(directory.glob("*.json")):
        document = _read(path)
        if not isinstance(document, dict):
            continue
        stem = path.stem
        source = _rel(path)
        population = str(document.get("population") or "")
        terms = REPORT_TERMS.get(stem, ())
        markdown = path.with_suffix(".md")
        says = str(document.get("question") or document.get("model")
                   or document.get("$schema") or stem)
        out.append(Entry(
            SUBJECT_FAMILY, stem, says, DERIVED, source, population=population,
            terms=(stem, *terms),
            detail={"markdown": _rel(markdown) if markdown.exists() else None}))
        #: A bundle knows about individual sectors, which is the only place
        #: a "what about E1M4 sector 26" question can be answered from.
        views = document.get("views")
        if isinstance(views, dict):
            out.extend(_bundle_sector_entries(stem, source, views))
    #: Reports that are prose only. `blood-rotating-doors.md` has no JSON
    #: sibling and is where the swinging-gate census lives, so a query for
    #: "swinging doors" reached nothing until these were indexed too.
    indexed = {entry.subject for entry in out}
    for path in sorted(directory.glob("*.md")):
        if path.stem in indexed:
            continue
        heading = ""
        for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
            if line.startswith("# "):
                heading = line[2:].strip()
                break
        out.append(Entry(
            SUBJECT_FAMILY, path.stem, heading or path.stem, DERIVED,
            _rel(path), terms=(path.stem, *REPORT_TERMS.get(path.stem, ()))))
    return out


def _bundle_sector_entries(stem: str, source: str,
                           views: Mapping[str, Any]) -> list[Entry]:
    map_name = stem.split("-")[0]
    found: dict[int, list[str]] = {}
    effects = views.get("effects") or {}
    for record in effects.get("records", []) or []:
        sector = record.get("sector_id")
        if sector is None:
            continue
        found.setdefault(int(sector), []).append(
            f"{record.get('design_object')} ({record.get('primitive', {}).get('motion')})")
    conditional = views.get("conditional_topology") or {}
    for route in conditional.get("records", []) or []:
        sector = route.get("mechanism")
        if sector is None or route.get("mechanism_kind") != "sector":
            continue
        found.setdefault(int(sector), []).append(
            f"gates {route.get('joins')}, {route.get('reads_as')}")
    facades = views.get("facades") or {}
    for host in facades.get("hosts", []) or []:
        found.setdefault(int(host), []).append("carries a street facade")
    return [
        Entry(SUBJECT_SECTOR, f"{map_name} sector {sector}",
              "; ".join(sorted(set(says))), DERIVED, source,
              terms=(map_name, f"sector {sector}", f"s{sector}"))
        for sector, says in sorted(found.items())
    ]


def _constructor_entries() -> list[Entry]:
    """The promoted constructors and what each still lacks."""
    path = _repo() / "knowledge" / "blood" / "design" / "README.md"
    if not path.is_file():
        return []
    out = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.startswith("| `") or "| ---" in line:
            continue
        cells = [cell.strip() for cell in line.strip("|").split("|")]
        if len(cells) < 4:
            continue
        name = cells[0].strip("`")
        out.append(Entry(
            SUBJECT_CONSTRUCTOR, name,
            f"promoted in {cells[1]}; still missing: {cells[3]}",
            INTERPRETED, _rel(path),
            terms=tuple(part.strip("` ") for part in name.split("/"))))
    return out


def build_index() -> dict[str, Any]:
    """Gather every source into one index."""
    entries: list[Entry] = []
    entries.extend(_owner_entries())
    entries.extend(_catalog_entries())
    entries.extend(_knowledge_file_entries())
    entries.extend(_report_entries())
    entries.extend(_constructor_entries())
    grades: dict[str, int] = {}
    for entry in entries:
        grades[entry.provenance] = grades.get(entry.provenance, 0) + 1
    return {
        "$schema": SCHEMA, "schema_version": SCHEMA_VERSION,
        "entries": [entry.to_dict() for entry in entries],
        "count": len(entries),
        "by_provenance": grades,
        "note": "an index over the knowledge store, not a second copy of it: "
                "every entry names the file it came from",
    }


def load_index(path: str | Path | None = None) -> list[Entry]:
    if path is None:
        document = build_index()
    else:
        document = _read(Path(path))
        if not isinstance(document, dict):
            raise KnowledgeIndexError(f"{path} is not a knowledge index")
    return [
        Entry(subject_kind=item["subject_kind"], subject=item["subject"],
              says=item["says"], provenance=item["provenance"],
              source=item["source"], population=item.get("population", ""),
              terms=tuple(item.get("terms") or ()),
              detail=item.get("detail") or {})
        for item in document.get("entries", [])
    ]


def lookup(query: str, *, entries: Sequence[Entry] | None = None,
           subject_kind: str | None = None,
           provenance: str | None = None) -> dict[str, Any]:
    """What do we know about this? Answered with sources, from one call.

    The query is matched against the subject, what the entry says, and the
    terms it was indexed under -- so "332", "swinging doors" and "E1M4
    sector 26" all reach something without the caller knowing which report
    holds it.
    """
    if subject_kind is not None and subject_kind not in SUBJECTS:
        raise KnowledgeIndexError(
            f"no such subject kind {subject_kind!r}; {list(SUBJECTS)}")
    if provenance is not None and provenance not in GRADES:
        raise KnowledgeIndexError(
            f"no such provenance {provenance!r}; {list(GRADES)}")
    pool = list(entries) if entries is not None else load_index()
    hits = [entry for entry in pool if entry.matches(query)]
    relaxed = ""
    if not hits:
        #: Nothing knows about every word of the query. Rather than answer
        #: "no", drop words from the end and say what was dropped -- a query
        #: for a sector nothing has measured should still return what is
        #: known about its map.
        words = _tokens(query.lower())
        while len(words) > 1 and not hits:
            words = words[:-1]
            shorter = " ".join(words)
            hits = [entry for entry in pool if entry.matches(shorter)]
            if hits:
                relaxed = shorter
    if subject_kind:
        hits = [entry for entry in hits if entry.subject_kind == subject_kind]
    if provenance:
        hits = [entry for entry in hits if entry.provenance == provenance]
    #: The owner's word first, then measurements, then interpretations.
    order = {OWNER: 0, DERIVED: 1, INTERPRETED: 2}
    hits.sort(key=lambda entry: (order.get(entry.provenance, 9), entry.subject))
    return {
        "$schema": "llmapper.knowledge-lookup", "schema_version": 1,
        "query": query,
        "relaxed_to": relaxed or None,
        "nothing_known_about_the_exact_query": bool(relaxed),
        "results": len(hits),
        "by_provenance": {grade: sum(1 for e in hits if e.provenance == grade)
                          for grade in GRADES},
        "entries": [entry.to_dict() for entry in hits],
    }
