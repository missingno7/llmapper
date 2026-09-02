"""The residue ledger: `(record, field) -> [claims]`, one ledger, every layer.

Each stage writes its own claims to `references/claims-layer<N>.json`; this
merges them into `bloodmap.read_ledger.ClaimLedger` -- the writer's
`RecordOwner` / `RegionLedger` shape at field granularity -- and that ledger
is the only place a residue number is computed.

    PYTHONPATH=. python projects/e3m1-decompiled/source/ledger.py

Two rules the ledger keeps, and they are the reason it is shaped this way:

* **a claim means the layer's model reproduces the field.** Naming a sector
  is not claiming a field. The space tree therefore claims nothing, which is
  the truest thing that can be said about a geometric hierarchy.
* **a sector is understood in proportion to its claimed fields.** No layer
  reports its own coverage; understanding is read off the shared ledger, so
  two layers claiming one field is corroboration or a conflict rather than
  double credit.
"""

from __future__ import annotations

import json
from typing import Any

from _common import PROJECT, REFERENCES, level

from bloodmap.read_ledger import ClaimLedger

SCHEMA = "llmapper.residue-ledger"
SCHEMA_VERSION = 2

#: `(layer number, name, evidence file)`. A missing claims file is reported as
#: "not yet read", never as zero residue.
LAYERS: tuple[tuple[int, str, str], ...] = (
    (1, "space tree", "space-tree.json"),
    (2, "surfaces, frames and structures", "surfaces.json"),
    (3, "joins", "join-census.json"),
    (4, "overlays: islands, the light field, lamps", "overlays.json"),
    (5, "mechanisms as sentences", "mechanisms.json"),
    (6, "the edge chain", "edge-chain.json"),
    (7, "the plan", "plan.json"),
    (8, "intent", "intent.json"),
)


def _evidence(filename: str) -> dict[str, Any] | None:
    path = REFERENCES / filename
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def build() -> dict[str, Any]:
    provenance = json.loads((PROJECT / "provenance.json").read_text(encoding="utf-8"))
    ledger = ClaimLedger()
    ledger.population(level())

    rows: list[dict[str, Any]] = []
    for number, name, filename in LAYERS:
        evidence = _evidence(filename)
        claims_path = REFERENCES / f"claims-layer{number}.json"
        if evidence is None:
            rows.append({"layer": number, "name": name, "state": "not yet read"})
            continue
        row = {"layer": number, "name": name, "state": "read",
               "evidence": filename, **evidence.get("ledger", {})}
        if claims_path.exists():
            payload = json.loads(claims_path.read_text(encoding="utf-8"))
            row["claims_note"] = payload.get("note", "")
            for claim in payload["claims"]:
                ledger.claim(claim["kind"], claim["index"], claim["field"],
                             layer=claim["layer"], owner=claim["owner"],
                             value=claim["value"], why=claim["why"],
                             intent=claim.get("intent", "function"))
        else:
            row["claims_note"] = "no claims file: this layer claims no field"
        rows.append(row)

    shared = ledger.to_dict()
    per_layer = shared["by_layer"]
    for row in rows:
        row["fields_claimed"] = per_layer.get(row["layer"], {}).get("fields_claimed", 0)
        row["share_of_all_fields"] = per_layer.get(row["layer"], {}).get(
            "share_of_all_fields", 0.0)
        row["claimed_by_channel"] = per_layer.get(row["layer"], {}).get("by_channel", {})
    return {
        "$schema": SCHEMA,
        "schema_version": SCHEMA_VERSION,
        "of": provenance["of"],
        "source_crc32": provenance["source_crc32"],
        "counts": provenance["counts"],
        "measure": ("understanding is the share of CLAIMED FIELDS in one "
                    "shared (record, field) -> [claims] ledger; a claim means "
                    "the layer's model reproduces the field, and naming a "
                    "sector claims nothing"),
        "layers": rows,
        "shared_ledger": shared,
        "per_record": {kind: shared_summary(ledger, kind)
                       for kind in ("sector", "wall", "sprite")},
    }


def shared_summary(ledger: ClaimLedger, kind: str) -> dict[str, Any]:
    per = ledger.per_record(kind)
    if not per:
        return {}
    shares = sorted(row["percent"] for row in per.values())
    return {
        "records": len(per),
        "records_with_no_claimed_field": sum(1 for row in per.values()
                                             if not row["claimed"]),
        "median_percent_claimed": shares[len(shares) // 2],
        "best_percent_claimed": shares[-1],
    }


def main() -> int:
    payload = build()
    (PROJECT / "residue-ledger.json").write_text(
        json.dumps(payload, indent=1, sort_keys=True), encoding="utf-8")
    (PROJECT / "claims.json").write_text(
        json.dumps(payload["shared_ledger"]["claims"], indent=1, sort_keys=True),
        encoding="utf-8")
    understanding = payload["shared_ledger"]["understanding"]
    print(f"E3M1 shared claim ledger: "
          f"{understanding['fields_with_a_claim']} of "
          f"{understanding['claimable_fields']} claimable fields have a claim "
          f"({understanding['understood_percent']}%)")
    for row in payload["layers"]:
        if row["state"] != "read":
            print(f"  layer {row['layer']} {row['name']:40s} not yet read")
            continue
        print(f"  layer {row['layer']} {row['name']:40s} "
              f"{row['fields_claimed']:6d} fields "
              f"({row['share_of_all_fields']}%)  {row.get('claimed_by_channel', {})}")
    conflicts = payload["shared_ledger"]["conflicts"]
    print(f"  conflicts on exclusive channels: {len(conflicts)}; "
          f"corroborated exclusive fields: "
          f"{payload['shared_ledger']['corroborated_exclusive_fields']}")
    for row in conflicts[:8]:
        owners = " vs ".join(f"{c['owner']}={c['value']}" for c in row["claims"])
        print(f"    {row['record']}.{row['field']} ({row['channel']}): {owners}")
    for kind, row in payload["per_record"].items():
        if row:
            print(f"  {kind:7s}: {row['records']} records, "
                  f"{row['records_with_no_claimed_field']} with no claimed "
                  f"field, median {row['median_percent_claimed']}% claimed, "
                  f"best {row['best_percent_claimed']}%")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
