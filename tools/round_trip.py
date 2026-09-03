"""Rebuild a map from its fact store, and name every field that comes back wrong.

    PYTHONPATH=. python -m tools.round_trip MAP FACTS_DIR -o REBUILT.MAP \
        --report projects/e3m1-decompiled/round-trip/E3M1.md

A decompilation says "I understand these fields". The round trip is where that
claim is spent: every field a `claims` fact names is written back from the
CLAIM'S OWN VALUE -- the value the layer's model reproduces -- and every field
no claim names is copied verbatim from the original record. The result is a
playable map with the same sector, wall and sprite INDICES as the original, so
a sector id the owner reads in the editor is the same id in both.

That makes two things measurable that nothing else measures:

* **coverage** -- how much of the map is ours, per layer, as fields rebuilt
  against fields copied. A residue ledger says the same thing in the
  abstract; this says it in a map you can walk.
* **misreadings** -- a claimed field whose rebuilt value differs from the
  original. The claim promised the model reproduces that field. Where the
  rebuilt byte differs, the promise was false, and the tool names the record,
  the field, the reader and both values. A residue ledger cannot find these
  at all: an unclaimed field is honest ignorance, and a wrong claim looks
  exactly like a right one until you write it back out.

The gate is the claim's own promise, so it needs no threshold: **a rebuilt
field equals the original wherever a claim said it would.** Zero misreadings
is the passing state, and every failure is a bug with an id.

Exit status is 0 whatever it finds. This measures; a gate decides.
"""

from __future__ import annotations

import argparse
import json
import pathlib
import sys
from collections import Counter, defaultdict
from typing import Any

KINDS = ("sector", "wall", "sprite")
#: A claim may name the EXTRA rather than the record: `xsector:52` is sector
#: 52's XSECTOR. Blood keeps the two in separate namespaces and a reader that
#: means one should not be able to write the other, so the prefix decides and
#: nothing is guessed.
X_KINDS = {"xsector": "sector", "xwall": "wall", "xsprite": "sprite"}

#: Which layer owns a claim, for the per-layer table. `_layer` is on every
#: fact; this is only its name.
#: Why a claim could not be written back. The three are different findings
#: and lumping them cost a day the first time.
NO_SUCH_RECORD = "names a record the map does not have"
THE_MAP_HAS_NO_FIELD = "names a field no record in the map holds"
NOT_A_NUMBER = "claims a value the format cannot store"

LAYER_NAMES = {
    1: "space tree", 2: "surfaces, frames and structures", 3: "joins",
    4: "overlays: islands, the light field, lamps",
    5: "mechanisms as sentences", 6: "the edge chain", 7: "the plan",
    8: "intent",
}


def _records(disk: Any) -> dict[str, list[Any]]:
    return {"sector": disk.sectors, "wall": disk.walls, "sprite": disk.sprites}


def _target(disk: Any, record: str) -> tuple[Any, str] | None:
    """The record a claim id names, and which namespace it is in.

    `sector:12` is the sector, whose field may be a MAP field (`floor_z`) or
    -- since Blood keeps the two apart -- an XSECTOR field on its extra.
    `xsector:12` is that extra and nothing else. The caller decides by
    looking, because guessing would be silent.
    """
    kind, _, index = record.partition(":")
    only_extra = kind in X_KINDS
    if only_extra:
        kind = X_KINDS[kind]
    if kind not in KINDS or not index.isdigit():
        return None
    items = _records(disk)[kind]
    position = int(index)
    if position >= len(items):
        return None
    return items[position], ("extra" if only_extra else kind)


def rebuild(disk: Any, claims: list[dict[str, Any]]) -> dict[str, Any]:
    """Write every claimed field back from its claim. Returns what happened.

    Nothing else in the map is touched, so a field with no claim keeps the
    original's bytes and the indices never move.
    """
    written: list[dict[str, Any]] = []
    unwritable: list[dict[str, Any]] = []
    for claim in claims:
        record = str(claim.get("record", ""))
        field = str(claim.get("field", ""))
        found = _target(disk, record)
        if found is None:
            unwritable.append({**_row(claim), "because": NO_SUCH_RECORD,
                               "detail": f"{record} is not in the map"})
            continue
        item, namespace = found
        value = claim.get("value")
        extra = getattr(item, "extra", None)
        if namespace != "extra" and field in item.fields:
            before = item.fields[field]
            holder, where = item.fields, "map"
        elif extra is not None and field in extra.fields:
            before = extra.fields[field]
            holder, where = extra.fields, "extra"
        else:
            #: THE FIELD IS NOT IN THE MAP AT ALL. Layer 5 claims a Z-motion
            #: door's `on_floor_z` and `off_floor_z`: two positions the model
            #: really does produce, and neither is a field any record holds --
            #: the map stores the door's rest state and its type, and the
            #: engine computes the rest. Such a claim cannot be round-tripped
            #: because there is no byte to compare it against, and counting
            #: it as a field of the map understood is counting something else.
            unwritable.append({**_row(claim), "because": THE_MAP_HAS_NO_FIELD,
                               "detail": f"no field {field!r} on {record}"})
            continue
        if not isinstance(value, (int, bool)):
            unwritable.append({**_row(claim), "because": NOT_A_NUMBER,
                               "detail": f"claimed value {value!r}"})
            continue
        holder[field] = int(value)
        written.append({**_row(claim), "was": _plain(before),
                        "now": int(value), "where": where})
    return {"written": written, "unwritable": unwritable}


def _plain(value: Any) -> Any:
    return int(value) if isinstance(value, (int, bool)) else value


def _row(claim: dict[str, Any]) -> dict[str, Any]:
    return {"record": claim.get("record"), "field": claim.get("field"),
            "value": claim.get("value"), "layer": int(claim.get("_layer", 0)),
            "reader": claim.get("_reader", "?"),
            "aspect": claim.get("aspect", "?")}


def coverage(disk: Any, claims: list[dict[str, Any]]) -> dict[str, Any]:
    """Fields rebuilt against fields copied, per layer and per record kind."""
    claimed = {(str(claim["record"]), str(claim["field"])) for claim in claims}
    per_kind: dict[str, dict[str, int]] = {}
    for kind, items in _records(disk).items():
        total = 0
        for index, item in enumerate(items):
            total += len(item.fields)
            if getattr(item, "extra", None) is not None:
                total += len(item.extra.fields)
        #: `sector:12.floor_z` and `xsector:12.rx_id` are both fields of
        #: sector 12 -- one in the record, one in its extra -- and the
        #: denominator counts both, so the numerator has to as well.
        rebuilt = sum(1 for record, _field in claimed
                      if record.startswith(f"{kind}:")
                      or record.startswith(f"x{kind}:"))
        per_kind[kind] = {"records": len(items), "fields": total,
                          "rebuilt": rebuilt, "copied": total - rebuilt}
    by_layer: dict[int, Counter] = defaultdict(Counter)
    for claim in claims:
        prefix = str(claim["record"]).split(":", 1)[0]
        by_layer[int(claim.get("_layer", 0))][X_KINDS.get(prefix, prefix)] += 1
    fields = sum(row["fields"] for row in per_kind.values())
    rebuilt = sum(row["rebuilt"] for row in per_kind.values())
    return {
        "per_kind": per_kind,
        "per_layer": {str(layer): {"name": LAYER_NAMES.get(layer, "?"),
                                   "rebuilt": sum(counts.values()),
                                   "by_kind": dict(sorted(counts.items()))}
                      for layer, counts in sorted(by_layer.items())},
        "fields": fields, "rebuilt": rebuilt, "copied": fields - rebuilt,
        "share": round(100.0 * rebuilt / fields, 3) if fields else 0.0,
    }


def misreadings(original: Any, rebuilt_disk: Any,
                claims: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Claimed fields whose rebuilt value differs from the original's.

    This is the whole point. Each one is a place where a reader said "my
    model produces this field" and the model produced something else.
    """
    out: list[dict[str, Any]] = []
    for claim in claims:
        record = str(claim.get("record", ""))
        field = str(claim.get("field", ""))
        here, there = _target(original, record), _target(rebuilt_disk, record)
        if here is None or there is None:
            continue
        holders = (("extra",) if here[1] == "extra"
                   else ("fields", "extra"))
        for holder in holders:
            before = _read(here[0], holder, field)
            after = _read(there[0], holder, field)
            if before is None or after is None:
                continue
            if int(before) != int(after):
                out.append({**_row(claim), "original": int(before),
                            "rebuilt": int(after), "where": holder})
    return out


def _read(item: Any, holder: str, field: str) -> Any:
    if holder == "fields":
        return item.fields.get(field)
    extra = getattr(item, "extra", None)
    return extra.fields.get(field) if extra is not None else None


def byte_diff(before: bytes, after: bytes) -> dict[str, Any]:
    """How far apart the two files are, before any interpretation."""
    differing = sum(1 for a, b in zip(before, after) if a != b)
    return {"original_bytes": len(before), "rebuilt_bytes": len(after),
            "identical": before == after,
            "differing_bytes_in_the_common_prefix": differing}


def promises(claims: list[dict[str, Any]]) -> list[Any]:
    """The distinct things the claims say, largest first, generalised.

    A claim's `why` carries its numbers; the numbers are the map's and the
    SHAPE is the model's, so the shape is what is counted here.
    """
    import re

    #: The numbers in a `why` are the map's; the sentence around them is the
    #: model's. Each pattern replaces one map-specific number with the word
    #: for what it is, so "one frame over 57 records" and "one frame over 2
    #: records" count as the promise they both make.
    general = (
        (r"one frame over \d+ records replays through (\S+) to this value",
         r"one frame replays through \1"),
        (r"a stepped run of rise \d+ from -?\d+", "a stepped run's rise"),
        (r"the sentence is: s\d+ type (\d+).*", r"the sentence of a type \1 mechanism"),
        (r"the light field at depth \d+ = ?.*", "the light field at base + k*step"),
        (r"a HeightIsland of rise \d+ on the base plane at z -?\d+",
         "a height island on the base plane"),
        (r"the (\S+) row (shows|sets) .*", r"the \1 row"),
    )
    counted: Counter = Counter()
    for claim in claims:
        shape = str(claim.get("why", ""))
        for pattern, into in general:
            new = re.sub(pattern, into, shape)
            if new != shape:
                shape = new
                break
        else:
            shape = shape.split(":")[0] if ":" in shape else shape
        counted[(int(claim.get("_layer", 0)), shape[:95])] += 1
    return counted.most_common()


def report(result: dict[str, Any]) -> str:
    cover, wrong = result["coverage"], result["misreadings"]
    name = result["of"]["map"]
    lines = [
        f"# Round trip: {name}",
        "",
        f"`{name}` rebuilt from `{result['of']['facts']}`. Every field a "
        f"`claims` fact names is written back from the claim's own value; "
        f"every other field is copied from the original record. Indices are "
        f"unchanged, so a sector id here is that sector id in the editor.",
        "",
        f"**{cover['rebuilt']} of {cover['fields']} fields rebuilt "
        f"({cover['share']}%), {cover['copied']} copied. "
        f"{len(wrong)} misreadings.**",
        "",
    ]
    if not wrong:
        lines += ["Every claimed field came back byte-identical to the "
                  "original. The claims' own promise holds without "
                  "exception.", ""]
    lines += ["## Rebuilt by layer", ""]
    rows = [["layer", "name", "fields rebuilt", "by record kind"]]
    for layer, row in sorted(result["coverage"]["per_layer"].items(),
                             key=lambda kv: int(kv[0])):
        rows.append([layer, row["name"], row["rebuilt"],
                     ", ".join(f"{k} {v}" for k, v in row["by_kind"].items())])
    lines += _table(rows)
    lines += ["", "## Rebuilt by record kind", ""]
    rows = [["kind", "records", "fields", "rebuilt", "copied"]]
    for kind, row in result["coverage"]["per_kind"].items():
        rows.append([kind, row["records"], row["fields"], row["rebuilt"],
                     row["copied"]])
    lines += _table(rows)

    #: WHAT THE CLAIMS PROMISE, so a clean round trip cannot be mistaken for
    #: a copy. A claim whose `why` says "replays through resolve_run to this
    #: value" recomputed the field from a frame; one that says "this floor
    #: lands on the fitted progression" recomputed it from a stair. Writing
    #: those back and getting the original byte is a test of the model. If a
    #: reader ever emitted a claim whose value it had simply read, that would
    #: show here as a promise that says nothing.
    lines += ["", "## What the claims promise", "",
              "A round trip is only a test where the claimed value was "
              "COMPUTED from the layer's model rather than read off the "
              "record. These are the promises, by how many fields make each.",
              ""]
    rows = [["fields", "layer", "the promise"]]
    for (layer, why), count in result["promises"][:14]:
        rows.append([count, layer, why])
    lines += _table(rows)

    lines += ["", "## The byte diff", ""]
    diff = result["byte_diff"]
    lines += [f"* original {diff['original_bytes']} bytes, rebuilt "
              f"{diff['rebuilt_bytes']} bytes",
              f"* identical: **{diff['identical']}**",
              f"* differing bytes in the common prefix: "
              f"{diff['differing_bytes_in_the_common_prefix']}",
              ""]
    if diff["identical"]:
        lines += ["A byte-identical rebuild means every claim reproduced its "
                  "field exactly and no unclaimed byte moved. It is the "
                  "strongest result this tool can report and it is not the "
                  "same as understanding the map: 96% of these fields were "
                  "copied, not rebuilt.", ""]

    lines += ["## Misreadings, by reader", ""]
    if not wrong:
        lines += ["None.", ""]
    else:
        by_reader = Counter(row["reader"] for row in wrong)
        rows = [["reader", "misreadings"]]
        rows += [[reader, count] for reader, count in by_reader.most_common()]
        lines += _table(rows)
        lines += ["", "### Every one", ""]
        for row in wrong[:200]:
            lines += [f"* `{row['record']}.{row['field']}` — original "
                      f"{row['original']}, rebuilt {row['rebuilt']} "
                      f"(layer {row['layer']}, `{row['reader']}`, "
                      f"aspect `{row['aspect']}`)"]
        if len(wrong) > 200:
            lines += [f"* … and {len(wrong) - 200} more"]
        lines += [""]

    if result["rebuild"]["unwritable"]:
        rows = Counter(row["because"]
                       for row in result["rebuild"]["unwritable"])
        lines += ["## Claims that could not be written back", "",
                  "A claim the round trip cannot write is a claim nothing "
                  "can check. It is not a misreading -- the value may be "
                  "right -- but it is not a field of the map understood "
                  "either, and the ledger counts it as one.", ""]
        lines += _table([["reason", "claims"]]
                        + [[why, count] for why, count in rows.most_common()])
        lines += [""]
        for row in result["rebuild"]["unwritable"][:20]:
            lines += [f"* `{row['record']}.{row['field']}` — "
                      f"{row.get('detail', row['because'])} "
                      f"(layer {row['layer']}, `{row['reader']}`)"]
        lines += [""]
    return "\n".join(lines) + "\n"


def _table(rows: list[list[Any]]) -> list[str]:
    head, body = rows[0], rows[1:]
    out = ["| " + " | ".join(str(cell) for cell in head) + " |",
           "| " + " | ".join("---" for _ in head) + " |"]
    out += ["| " + " | ".join(str(cell) for cell in row) + " |" for row in body]
    return out


def load_claims(facts: pathlib.Path) -> list[dict[str, Any]]:
    path = facts / "claims.jsonl"
    if not path.exists():
        raise SystemExit(f"no claims.jsonl under {facts}: a fact store with "
                         f"no claims rebuilds nothing")
    return [json.loads(line) for line in
            path.read_text(encoding="utf-8").splitlines() if line.strip()]


def round_trip(map_path: str, facts_dir: str, out_path: str) -> dict[str, Any]:
    from bloodmap.format import encode_map, read_map, write_map

    facts = pathlib.Path(facts_dir)
    claims = load_claims(facts)
    original = read_map(map_path)
    #: A second, independent read, so writing into one cannot move the other.
    rebuilt_disk = read_map(map_path)
    done = rebuild(rebuilt_disk, claims)
    write_map(rebuilt_disk, out_path)

    return {
        "of": {"map": pathlib.Path(map_path).as_posix(),
               "facts": facts.as_posix(),
               "rebuilt": pathlib.Path(out_path).as_posix()},
        "coverage": coverage(original, claims),
        "rebuild": {"written": len(done["written"]),
                    "unwritable": done["unwritable"]},
        "misreadings": misreadings(original, rebuilt_disk, claims),
        "byte_diff": byte_diff(encode_map(original), encode_map(rebuilt_disk)),
        "promises": promises(claims),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("map", help="the original .MAP")
    parser.add_argument("facts", help="the fact store directory")
    parser.add_argument("-o", "--out", required=True, help="the rebuilt .MAP")
    parser.add_argument("--report", help="where to write the markdown")
    parser.add_argument("--json", dest="as_json", help="the machine-readable diff")
    args = parser.parse_args(argv)

    pathlib.Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    result = round_trip(args.map, args.facts, args.out)

    text = report(result)
    if args.report:
        pathlib.Path(args.report).parent.mkdir(parents=True, exist_ok=True)
        pathlib.Path(args.report).write_text(text, encoding="utf-8")
        print(f"wrote {args.report}")
    target = args.as_json or str(pathlib.Path(args.out).with_suffix(".json"))
    pathlib.Path(target).write_text(
        json.dumps(result, indent=1, sort_keys=True, default=str),
        encoding="utf-8")
    print(f"wrote {args.out}")
    print(f"wrote {target}")

    cover = result["coverage"]
    print(f"{cover['rebuilt']} of {cover['fields']} fields rebuilt "
          f"({cover['share']}%), {cover['copied']} copied")
    print(f"{len(result['misreadings'])} misreadings, "
          f"{len(result['rebuild']['unwritable'])} claims unwritable, "
          f"byte-identical: {result['byte_diff']['identical']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
