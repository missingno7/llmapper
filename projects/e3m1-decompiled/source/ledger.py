"""The residue ledger: understanding is 100% minus residue, per layer.

Every stage writes its own evidence file under `references/`. This composes
them into one document that answers, per layer and per record, what nothing
explains. It reads only what the stages measured; nothing here is typed in.

    PYTHONPATH=. python projects/e3m1-decompiled/source/ledger.py

The two rules the ledger exists to keep:

* **a layer's denominator is its own population.** The surface layer is
  measured in wall records, the light layer in the outdoor sectors it can
  reach, the mechanism layer in triggered objects. Dividing everything by 382
  sectors would make every layer look the same and none of them true.
* **identity that cost nothing is not evidence.** Where a layer's gate is a
  recompile, a recovered object that reproduces one record because it was
  fitted to that one record counts as residue, not as understanding.
"""

from __future__ import annotations

import json
from typing import Any

from _common import PROJECT, REFERENCES

SCHEMA = "llmapper.residue-ledger"
SCHEMA_VERSION = 1

#: `(layer number, name, evidence file)`, in the order the experiment runs
#: them. A missing file is reported as "not yet read", never as zero residue.
LAYERS: tuple[tuple[int, str, str], ...] = (
    (1, "space tree", "space-tree.json"),
    (2, "surfaces and frames", "surfaces.json"),
    (3, "joins", "join-census.json"),
    (4, "overlays: islands, the light field, lamps", "overlays.json"),
    (5, "mechanisms as sentences", "mechanisms.json"),
    (6, "the edge chain", "edge-chain.json"),
    (7, "the plan", "plan.json"),
    (8, "intent", "intent.json"),
)


def _row(number: int, name: str, filename: str) -> dict[str, Any]:
    path = REFERENCES / filename
    if not path.exists():
        return {"layer": number, "name": name, "state": "not yet read",
                "evidence": filename}
    payload = json.loads(path.read_text(encoding="utf-8"))
    if "ledger" not in payload:
        raise SystemExit(
            f"{filename} has no 'ledger' block. Every stage states its own "
            f"population, what it explains and what it does not; a stage that "
            f"does not is not measured.")
    return {"layer": number, "name": name, "state": "read",
            "evidence": filename, **payload["ledger"]}


def build() -> dict[str, Any]:
    provenance = json.loads((PROJECT / "provenance.json").read_text(encoding="utf-8"))
    rows = [_row(*item) for item in LAYERS]
    read = [row for row in rows if row["state"] == "read"]
    return {
        "$schema": SCHEMA,
        "schema_version": SCHEMA_VERSION,
        "of": provenance["of"],
        "source_crc32": provenance["source_crc32"],
        "counts": provenance["counts"],
        "measure": ("understanding is 100% minus residue, per layer, in that "
                    "layer's own population; a layer with no evidence file is "
                    "'not yet read', which is not zero residue"),
        "layers_read": len(read),
        "layers": rows,
    }


def main() -> int:
    payload = build()
    (PROJECT / "residue-ledger.json").write_text(
        json.dumps(payload, indent=1, sort_keys=True), encoding="utf-8")
    for row in payload["layers"]:
        if row["state"] != "read":
            print(f"  layer {row['layer']} {row['name']:44s} not yet read")
            continue
        residue = row.get("residue")
        percent = row.get("residue_percent")
        print(f"  layer {row['layer']} {row['name']:44s} residue "
              f"{residue} ({percent}%) of {row.get('population')}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
