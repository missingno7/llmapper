"""What the city DECLARED against what its built map SAYS, row for row.

    PYTHONPATH=. python -m tools.symmetry_diff projects/blood-city \
        --map projects/blood-city/level/slice2-streets.MAP \
        --report projects/blood-city/reports/symmetry-diff.md

The compiler writes a fact store as it builds (`projects/blood-city/facts/`).
The readers recover a fact store from the finished `.MAP`
(`bloodmap.read_facts.recover`). Symmetry is the claim that those two stores
say the same thing. This tool is where that claim is CHECKED rather than
assumed, and its output is a list of disagreements, each classed:

* **missing id** -- declared and not recovered. The compiler says it built a
  thing the readers cannot find. Either it did not build it, or no reader can
  see it; both are worth knowing and the tool cannot tell them apart, so it
  says which predicate and which ids.
* **extra id** -- recovered and not declared. The map says something the
  build did not mean to say. On a base predicate (`sector`, `wall`, …) this
  is normal and is reported separately; anywhere else it is a finding.
* **different attrs** -- the same id on both sides with different fields.
  The strongest kind: two halves of one pipeline disagreeing about a thing
  they both name. Every differing field is listed with both values.
* **unknown kind** -- a value in a field the READERS use as a vocabulary
  (`join.a`, `join.b`, `surface_kind.kind`) that the other side has never
  heard of. This is how a kind the reader gained and the writer has not --
  or the reverse -- shows up as one line instead of a thousand.
* **field only one side writes** -- the compiler calls a tile `picnum` and
  the reader calls it `wears_tile`. That is one disagreement about the SHAPE
  of a predicate, not one per row, and reporting it per row buries the
  content disagreements underneath it. Such fields are named once and taken
  out of the attribute comparison, so "same id different attrs" means what it
  says: both sides wrote this field, and wrote different values in it.

`bloodmap.facts.diff_stores` counts ids per predicate and is P14b's; it
answers "how far apart are they". This answers "where, and how". Neither
replaces the other and this one does not modify the writer side.

The report is markdown, so the owner reads it; the JSON beside it is what a
gate reads. Exit status is 0 whatever it finds: this measures, it does not
enforce. A gate decides what is fatal.
"""

from __future__ import annotations

import argparse
import json
import pathlib
import sys
from collections import Counter, defaultdict
from typing import Any

#: A literal backtick, so a markdown span can be built without an f-string
#: fighting the quoting.
TICK = chr(96)

MISSING, EXTRA, ATTRS, KIND, SHAPE = (
    "missing id", "extra id", "same id different attrs", "unknown kind",
    "field only one side writes")

#: Fields whose VALUES are a vocabulary both sides must share. A kind one side
#: has and the other has not is a single finding about the grammar, not one
#: finding per record, so it is counted here and taken out of the attribute
#: comparison's noise.
VOCABULARY = {
    "join": ("a", "b", "height", "frame"),
    "surface_kind": ("kind",),
    "part_of": ("kind",),
    "sentence": ("kind",),
    "edge_segment": ("kind",),
    "surface": ("kind",),
}

#: Provenance, not content. Two stores written by two programs disagree about
#: these by construction and saying so 3000 times hides the disagreements that
#: matter.
PROVENANCE = {"_from", "_reader", "_layer", "lod"}


def _attrs(fact: Any) -> dict[str, Any]:
    row = fact.to_dict() if hasattr(fact, "to_dict") else dict(fact)
    return {key: value for key, value in row.items()
            if key not in PROVENANCE and key != "id"}


def _index(store: Any, predicate: str) -> dict[str, Any]:
    return {fact.id: fact for fact in store[predicate]}


def compare(declared: Any, recovered: Any, *,
            base_predicates: frozenset[str]) -> dict[str, Any]:
    """Every predicate on either side, and every disagreement in it, classed."""
    findings: list[dict[str, Any]] = []
    per_predicate: dict[str, Any] = {}
    predicates = sorted(set(declared.rows) | set(recovered.rows))

    #: Where each vocabulary value is used ANYWHERE on a side. The compiler
    #: keeps its surface kinds in `surface.kind` and the readers keep theirs
    #: in `surface_kind.kind`; both know the word "pavement" and neither
    #: knows it in the other's predicate. Saying where a value does live
    #: turns nine "unknown kind" lines into one fact about the shape.
    def vocabulary(store: Any) -> dict[str, set[str]]:
        out: dict[str, set[str]] = defaultdict(set)
        for name in store.rows:
            for field in VOCABULARY.get(name, ()):
                for fact in store[name]:
                    row = _attrs(fact)
                    if field in row:
                        out[str(row[field])].add(f"{name}.{field}")
        return out

    declared_vocabulary = vocabulary(declared)
    recovered_vocabulary = vocabulary(recovered)

    for predicate in predicates:
        mine = _index(declared, predicate)
        theirs = _index(recovered, predicate)
        base = predicate in base_predicates
        missing = sorted(set(mine) - set(theirs))
        extra = sorted(set(theirs) - set(mine))
        shared = sorted(set(mine) & set(theirs))

        #: Which fields each side EVER writes in this predicate. A field
        #: only one side writes is the predicate's shape, and is taken out of
        #: the per-id comparison so a content disagreement stays visible.
        ours = {name for fact in mine.values() for name in _attrs(fact)}
        yours = {name for fact in theirs.values() for name in _attrs(fact)}
        one_sided = sorted((ours - yours) | (yours - ours))
        both_write = ours & yours

        differing: list[dict[str, Any]] = []
        for one in shared:
            here, there = _attrs(mine[one]), _attrs(theirs[one])
            moved = {name: [here.get(name, "--"), there.get(name, "--")]
                     for name in sorted(both_write)
                     if here.get(name) != there.get(name)}
            if moved:
                differing.append({"id": one, "fields": moved})

        vocab: list[dict[str, Any]] = []
        for field in VOCABULARY.get(predicate, ()):
            here = {str(_attrs(fact).get(field)) for fact in mine.values()
                    if field in _attrs(fact)}
            there = {str(_attrs(fact).get(field)) for fact in theirs.values()
                     if field in _attrs(fact)}
            for value in sorted(there - here):
                vocab.append({"field": field, "value": value,
                              "seen_by": "readers only",
                              "elsewhere": sorted(
                                  declared_vocabulary.get(value, ()))})
            for value in sorted(here - there):
                vocab.append({"field": field, "value": value,
                              "seen_by": "compiler only",
                              "elsewhere": sorted(
                                  recovered_vocabulary.get(value, ()))})

        per_predicate[predicate] = {
            "declared": len(mine), "recovered": len(theirs),
            "same_id": len(shared), "base": base,
            "missing_ids": len(missing), "extra_ids": len(extra),
            "differing_ids": len(differing), "unknown_kinds": len(vocab),
            "one_sided_fields": one_sided,
        }
        if one_sided and shared:
            findings.append({"class": SHAPE, "predicate": predicate,
                             "count": len(one_sided), "base": base,
                             "compiler_only": sorted(ours - yours),
                             "readers_only": sorted(yours - ours),
                             "both": sorted(both_write)})
        if missing:
            findings.append({"class": MISSING, "predicate": predicate,
                             "count": len(missing), "base": base,
                             "ids": missing[:40],
                             "elided": max(0, len(missing) - 40)})
        if extra:
            findings.append({"class": EXTRA, "predicate": predicate,
                             "count": len(extra), "base": base,
                             "ids": extra[:40],
                             "elided": max(0, len(extra) - 40)})
        if differing:
            fields = Counter(name for row in differing for name in row["fields"])
            findings.append({"class": ATTRS, "predicate": predicate,
                             "count": len(differing), "base": base,
                             "fields": dict(fields.most_common()),
                             "examples": differing[:10],
                             "elided": max(0, len(differing) - 10)})
        if vocab:
            findings.append({"class": KIND, "predicate": predicate,
                             "count": len(vocab), "base": base,
                             "values": vocab})

    order = {MISSING: 0, ATTRS: 1, KIND: 2, SHAPE: 3, EXTRA: 4}
    findings.sort(key=lambda row: (row["base"], order[row["class"]],
                                   -row["count"]))
    by_class = Counter(row["class"] for row in findings)
    return {
        "predicates": per_predicate,
        "findings": findings,
        "summary": {
            "predicates": len(predicates),
            "declared_only": sorted(name for name, row in per_predicate.items()
                                    if row["declared"] and not row["recovered"]),
            "recovered_only": sorted(
                name for name, row in per_predicate.items()
                if row["recovered"] and not row["declared"] and not row["base"]),
            "rows_declared": sum(row["declared"] for row in per_predicate.values()),
            "rows_recovered": sum(row["recovered"] for row in per_predicate.values()),
            "ids_that_match": sum(row["same_id"] for row in per_predicate.values()),
            "findings_by_class": {name: by_class.get(name, 0)
                                  for name in (MISSING, EXTRA, ATTRS, KIND,
                                               SHAPE)},
            "rows_in_disagreement": sum(
                row["missing_ids"] + row["extra_ids"] + row["differing_ids"]
                for name, row in per_predicate.items() if not row["base"]),
        },
    }


def _table(rows: list[list[str]], head: list[str]) -> list[str]:
    out = ["| " + " | ".join(head) + " |",
           "| " + " | ".join("---" for _ in head) + " |"]
    out += ["| " + " | ".join(str(cell) for cell in row) + " |" for row in rows]
    return out


def report(result: dict[str, Any], *, project: str, map_path: str,
           layer1_error: str | None) -> str:
    summary = result["summary"]
    lines = [
        f"# Symmetry diff: {project}",
        "",
        f"What `{project}/facts/` DECLARES against what "
        f"`bloodmap.read_facts.recover` reads back from `{map_path}`. "
        f"Produced by `tools/symmetry_diff.py`; every number is a query over "
        f"the two stores.",
        "",
        f"**{summary['rows_declared']} rows declared, "
        f"{summary['rows_recovered']} recovered, "
        f"{summary['ids_that_match']} ids on both sides, "
        f"{summary['rows_in_disagreement']} rows in disagreement outside the "
        f"base predicates.**",
        "",
    ]
    if layer1_error:
        lines += [f"Layer 1 did not run: `{layer1_error}`. Every `part_of` "
                  f"row below is therefore a missing id by construction.", ""]

    counts = summary["findings_by_class"]
    lines += ["## Disagreements by class", ""]
    lines += _table([[name, counts[name]] for name in
                     (MISSING, EXTRA, ATTRS, KIND, SHAPE)],
                    ["class", "findings"])
    lines += ["",
              "* **missing id** — declared, not recovered: the compiler says "
              "it built something no reader finds.",
              "* **extra id** — recovered, not declared: the map says "
              "something the build did not mean to say. Normal on a base "
              "predicate, a finding anywhere else.",
              "* **same id different attrs** — both halves name one thing and "
              "disagree about it.",
              "* **unknown kind** — a vocabulary value one side has never "
              "heard of, and where the other side does keep it.",
              "* **field only one side writes** — a difference in the "
              "SHAPE of a predicate, counted once per field rather than once "
              "per row.",
              ""]

    lines += ["## Per predicate", ""]
    rows = []
    for name, row in sorted(result["predicates"].items()):
        rows.append([name + (" *(base)*" if row["base"] else ""),
                     row["declared"], row["recovered"], row["same_id"],
                     row["missing_ids"], row["extra_ids"],
                     row["differing_ids"], row["unknown_kinds"]])
    lines += _table(rows, ["predicate", "declared", "recovered", "same id",
                           "missing", "extra", "attrs differ", "unknown kind"])
    lines += [""]

    if summary["declared_only"]:
        lines += [f"**Declared and never recovered:** "
                  f"{', '.join('`' + one + '`' for one in summary['declared_only'])}"
                  f" — a claim nothing checks.", ""]
    if summary["recovered_only"]:
        lines += [f"**Recovered and never declared:** "
                  f"{', '.join('`' + one + '`' for one in summary['recovered_only'])}"
                  f" — what the map says beyond the build.", ""]

    lines += ["## Every finding", ""]
    if not result["findings"]:
        lines += ["None. The two stores agree row for row.", ""]
    for finding in result["findings"]:
        head = (f"### `{finding['predicate']}` — {finding['class']}, "
                f"{finding['count']}")
        if finding["base"]:
            head += " *(base predicate)*"
        lines += [head, ""]
        if finding["class"] == ATTRS:
            lines += ["Fields that differ, by how many ids: "
                      + ", ".join(f"`{name}` ({count})" for name, count
                                  in finding["fields"].items()), ""]
            for example in finding["examples"]:
                moved = "; ".join(
                    f"`{name}` declared {before!r}, recovered {after!r}"
                    for name, (before, after) in example["fields"].items())
                lines += [f"* `{example['id']}`: {moved}"]
            if finding["elided"]:
                lines += [f"* … and {finding['elided']} more"]
        elif finding["class"] == KIND:
            for value in finding["values"]:
                where = (", and kept in "
                         + ", ".join(TICK + one + TICK
                                     for one in value["elsewhere"])
                         if value.get("elsewhere") else "")
                lines += [f"* `{value['field']} = {value['value']}` — "
                          f"{value['seen_by']}{where}"]
        elif finding["class"] == SHAPE:
            for label, names in (("compiler only", finding["compiler_only"]),
                                 ("readers only", finding["readers_only"]),
                                 ("both", finding["both"])):
                shown = ", ".join(TICK + one + TICK for one in names) or "—"
                lines += [f"* {label}: {shown}"]
        else:
            shown = ", ".join(f"`{one}`" for one in finding["ids"])
            lines += [shown + (f" … and {finding['elided']} more"
                               if finding["elided"] else "")]
        lines += [""]
    return "\n".join(lines) + "\n"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("project", help="a project directory with facts/")
    parser.add_argument("--map", required=True, help="the built .MAP to read")
    parser.add_argument("--report", help="where to write the markdown")
    parser.add_argument("--json", dest="as_json",
                        help="where to write the machine-readable diff")
    args = parser.parse_args(argv)

    from bloodmap.read_facts import recover
    from bloodmap.read_store import BASE_PREDICATES, FactStore

    project = pathlib.Path(args.project)
    declared = FactStore.read(project / "facts")
    found = recover(args.map)
    result = compare(declared, found["store"],
                     base_predicates=frozenset(BASE_PREDICATES))
    #: Forward slashes whatever the platform: the report is committed and
    #: read on both, and a path that changes shape by machine is a diff.
    shown = project.as_posix()
    map_shown = pathlib.Path(args.map).as_posix()
    result["of"] = {"project": shown, "map": map_shown,
                    "layer1_error": found["layer1_error"]}

    text = report(result, project=shown, map_path=map_shown,
                  layer1_error=found["layer1_error"])
    if args.report:
        pathlib.Path(args.report).parent.mkdir(parents=True, exist_ok=True)
        pathlib.Path(args.report).write_text(text, encoding="utf-8")
        print(f"wrote {args.report}")
    else:
        print(text)
    target = args.as_json or (project / "references"
                              / "symmetry-diff.json").as_posix()
    pathlib.Path(target).parent.mkdir(parents=True, exist_ok=True)
    pathlib.Path(target).write_text(json.dumps(result, indent=1,
                                               sort_keys=True, default=str),
                                    encoding="utf-8")
    print(f"wrote {target}")

    summary = result["summary"]
    print(f"{summary['rows_declared']} declared, "
          f"{summary['rows_recovered']} recovered, "
          f"{summary['ids_that_match']} ids match, "
          f"{summary['rows_in_disagreement']} rows disagree "
          f"(outside base predicates)")
    for name, count in summary["findings_by_class"].items():
        print(f"  {name:26s} {count}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
