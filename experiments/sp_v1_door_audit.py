"""Write SP-v1 door audit reports from the frozen blueprint."""

from __future__ import annotations

import json
from pathlib import Path

from bloodmap.doors import authored_gate_audit, door_affordance_report, gate_audit_markdown
from experiments.sp_progression_v1 import make_layout


def main() -> None:
    compiled = make_layout().compile()
    audit = authored_gate_audit(compiled)
    payload = {"audit": audit, "affordance": door_affordance_report(compiled)}
    Path("reports/SP-v1-door-audit.json").write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n",
    )
    Path("reports/SP-v1-door-audit.md").write_text(
        gate_audit_markdown(audit), encoding="utf-8", newline="\n",
    )
    print("gates", audit["gate_count"], "affordance_ok", payload["affordance"]["ok"])


if __name__ == "__main__":
    main()
