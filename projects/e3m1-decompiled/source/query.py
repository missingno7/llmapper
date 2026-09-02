"""Every number a report quotes, as a query over `facts/`. Nothing is typed.

    PYTHONPATH=. python projects/e3m1-decompiled/source/query.py

Writes `residue-ledger.json` -- which is now a QUERY RESULT over the fact
store rather than a document anybody maintains -- and prints the same figures.
If a report says 3.64%, this script is where that 3.64 comes from; if the
readers change, both move together and neither can be quietly stale.
"""

from __future__ import annotations

import json
from collections import Counter, defaultdict
from typing import Any

from _common import PROJECT

from bloodmap.channels import ADDITIVE, EXCLUSIVE
from bloodmap.read_store import FactStore
from bloodmap.read_ledger import channel_kind, channel_of, fields_of

KINDS = ("sector", "wall", "sprite", "xsector", "xwall", "xsprite")

LAYERS = {
    1: "space tree",
    2: "surfaces, frames and structures",
    3: "joins",
    4: "overlays: islands, the light field, lamps",
    5: "mechanisms as sentences",
    6: "the edge chain",
    7: "the plan",
    8: "intent",
}


def claimable(store: FactStore) -> dict[str, int]:
    return {kind: store.count(kind) * len(fields_of(kind)) for kind in KINDS}


def understanding(store: FactStore) -> dict[str, Any]:
    total = sum(claimable(store).values())
    held = {(row.attrs["record"], row.attrs["field"]) for row in store["claims"]}
    return {
        "claimable_fields": total,
        "fields_with_a_claim": len(held),
        "understood_percent": round(100.0 * len(held) / total, 3) if total else 0.0,
        "residue_fields": total - len(held),
        "claimable_by_record_kind": claimable(store),
    }


def conflicts(store: FactStore) -> list[dict[str, Any]]:
    """Two EXCLUSIVE claims on one field with different values (42010: an
    inconsistency is a recorded fact with an owner, never a silent choice)."""
    by_field: dict[tuple[str, str], list] = defaultdict(list)
    for row in store["claims"]:
        by_field[(row.attrs["record"], row.attrs["field"])].append(row)
    out = []
    for (record, name), rows in sorted(by_field.items()):
        if channel_kind(rows[0].attrs["channel"]) != EXCLUSIVE:
            continue
        values = {json.dumps(row.attrs["value"], sort_keys=True) for row in rows}
        if len(rows) > 1 and len(values) > 1:
            out.append({"record": record, "field": name,
                        "channel": rows[0].attrs["channel"],
                        "claims": [{"aspect": row.attrs["aspect"],
                                    "layer": row.layer,
                                    "value": row.attrs["value"]}
                                   for row in rows]})
    return out


def corroborations(store: FactStore) -> int:
    by_field: dict[tuple[str, str], list] = defaultdict(list)
    for row in store["claims"]:
        by_field[(row.attrs["record"], row.attrs["field"])].append(row)
    return sum(1 for rows in by_field.values()
               if len(rows) > 1
               and channel_kind(rows[0].attrs["channel"]) == EXCLUSIVE
               and len({json.dumps(row.attrs["value"], sort_keys=True)
                        for row in rows}) == 1)


def by_layer(store: FactStore) -> dict[int, dict[str, Any]]:
    fields: Counter = Counter()
    channels: dict[int, Counter] = defaultdict(Counter)
    facts: Counter = Counter()
    residue: Counter = Counter()
    for predicate, rows in store.rows.items():
        for row in rows:
            if row.layer is None:
                continue
            facts[row.layer] += 1
            if predicate == "claims":
                fields[row.layer] += 1
                channels[row.layer][row.attrs["channel"]] += 1
            if predicate == "residue":
                residue[row.layer] += 1
    total = sum(claimable(store).values()) or 1
    out = {}
    for layer, name in LAYERS.items():
        out[layer] = {
            "name": name,
            "state": "read" if facts.get(layer) else "not yet read",
            "facts": facts.get(layer, 0),
            "fields_claimed": fields.get(layer, 0),
            "share_of_all_fields": round(100.0 * fields.get(layer, 0) / total, 3),
            "residue_facts": residue.get(layer, 0),
            "by_channel": dict(sorted(channels.get(layer, Counter()).items())),
        }
    return out


def per_record(store: FactStore, kind: str) -> dict[str, Any]:
    names = fields_of(kind)
    held: dict[int, set] = defaultdict(set)
    for row in store["claims"]:
        record = row.attrs["record"]
        prefix, index = record.split(":", 1)
        if prefix == kind:
            held[int(index)].add(row.attrs["field"])
    count = store.count(kind)
    if not count or not names:
        return {}
    shares = sorted(round(100.0 * len(held.get(index, ())) / len(names), 1)
                    for index in range(count))
    return {
        "records": count,
        "records_with_no_claimed_field": sum(1 for value in shares if value == 0),
        "median_percent_claimed": shares[len(shares) // 2],
        "best_percent_claimed": shares[-1],
    }


def residue_by_aspect(store: FactStore) -> dict[str, int]:
    return dict(sorted(Counter(row.attrs.get("aspect", "?")
                               for row in store["residue"]).items()))


def build() -> dict[str, Any]:
    store = FactStore.read(PROJECT / "facts")
    provenance = json.loads((PROJECT / "provenance.json").read_text(encoding="utf-8"))
    return {
        "$schema": "llmapper.residue-ledger",
        "schema_version": 3,
        "of": provenance["of"],
        "source_crc32": provenance["source_crc32"],
        "counts": provenance["counts"],
        "measure": ("a query over projects/e3m1-decompiled/facts/. "
                    "Understanding is the share of CLAIMED FIELDS in the "
                    "shared (record, field) -> [claims] ledger, which is the "
                    "`claims` predicate; residue and conflict are predicates "
                    "like any other. No number here is typed."),
        "predicates": store.by_predicate(),
        "readers": store.readers(),
        "understanding": understanding(store),
        "layers": by_layer(store),
        "conflicts": conflicts(store),
        "corroborated_exclusive_fields": corroborations(store),
        "residue_by_aspect": residue_by_aspect(store),
        "candidates": [row.to_dict() for row in store["candidate"]],
        "selections": [row.to_dict() for row in store["selection"]],
        "per_record": {kind: per_record(store, kind)
                       for kind in ("sector", "wall", "sprite")},
    }


def panels(store: FactStore) -> tuple[dict, dict]:
    """What a record's fact panel shows: its claims and its candidates.

    Written beside the ledger because the review pack reads them: the panel
    has to list what explains each field, what is still ambiguous about the
    record, and what nothing explains at all.
    """
    claims: dict[str, list] = defaultdict(list)
    for row in store["claims"]:
        key = f"{row.attrs['record']}:{row.attrs['field']}"
        claims[key].append({"layer": row.layer, "owner": row.attrs["aspect"],
                            "value": row.attrs["value"],
                            "channel": row.attrs["channel"],
                            "why": row.attrs.get("why", "")})
    #: A candidate is ABOUT something, and that something is usually not a
    #: record: `plan:corridor:02`, `name:sentence:sector:105`. The panel is
    #: per record, so each candidate's sources are followed through the store
    #: until they land on records -- one hop is enough for everything here,
    #: and anything that does not resolve is reported against its own id
    #: rather than dropped.
    resolve: dict[str, tuple] = {}
    for predicate, rows in store.rows.items():
        if predicate in ("candidate", "claims", "residue", "selection"):
            continue
        for row in rows:
            resolve[row.id] = row.sources

    def records_of(name: str) -> list[str]:
        if name.split(":", 1)[0] in ("sector", "wall", "sprite",
                                     "xsector", "xwall", "xsprite"):
            return [name]
        out = []
        for source in resolve.get(name, ()):
            out.extend(records_of(source) if source != name else [])
        return out or [name]

    candidates: dict[str, list] = defaultdict(list)
    for row in store["candidate"]:
        seeds = row.sources or (row.attrs.get("about", ""),)
        seen = set()
        for seed in seeds:
            for record in records_of(str(seed)):
                if record in seen:
                    continue
                seen.add(record)
                candidates[record].append(
                    {"about": row.attrs.get("about", row.id),
                     "id": row.id, "layer": row.layer,
                     "readings": row.attrs.get("readings", []),
                     "why": row.attrs.get("why", "")})
    return dict(claims), dict(candidates)


def main() -> int:
    payload = build()
    store = FactStore.read(PROJECT / "facts")
    claims, candidates = panels(store)
    (PROJECT / "claims.json").write_text(
        json.dumps(claims, indent=1, sort_keys=True), encoding="utf-8")
    (PROJECT / "candidates.json").write_text(
        json.dumps(candidates, indent=1, sort_keys=True), encoding="utf-8")
    (PROJECT / "residue-ledger.json").write_text(
        json.dumps(payload, indent=1, sort_keys=True), encoding="utf-8")
    u = payload["understanding"]
    print(f"E3M1, queried from the fact store: "
          f"{u['fields_with_a_claim']} of {u['claimable_fields']} claimable "
          f"fields have a claim ({u['understood_percent']}%)")
    for layer, row in payload["layers"].items():
        if row["state"] != "read":
            print(f"  layer {layer} {row['name']:40s} not yet read")
            continue
        print(f"  layer {layer} {row['name']:40s} {row['facts']:6d} facts, "
              f"{row['fields_claimed']:5d} fields "
              f"({row['share_of_all_fields']}%), "
              f"{row['residue_facts']:5d} residue  {row['by_channel']}")
    print(f"  conflicts {len(payload['conflicts'])}, corroborated "
          f"{payload['corroborated_exclusive_fields']}, candidates "
          f"{len(payload['candidates'])}, selections "
          f"{len(payload['selections'])}")
    print(f"  residue by aspect: {payload['residue_by_aspect']}")
    for kind, row in payload["per_record"].items():
        if row:
            print(f"  {kind:7s}: {row['records']} records, "
                  f"{row['records_with_no_claimed_field']} with no claimed "
                  f"field, median {row['median_percent_claimed']}%, best "
                  f"{row['best_percent_claimed']}%")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
