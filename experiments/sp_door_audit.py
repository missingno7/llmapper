"""Forensic door-affordance audit of an authored single-player blueprint.

    python -m experiments.sp_door_audit --blueprint sp-v2 \
        --json reports/SP-v2-door-affordance.json

This was `python -m bloodmap door-audit`. It audits a blueprint that lives in
`experiments/`, and the library does not import from there, so the command
lives with the blueprints it reads. The audit itself is
`bloodmap.doors.authored_gate_audit`.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from bloodmap.doors import authored_gate_audit, door_affordance_report, gate_audit_markdown

BLUEPRINTS = ("sp-v1", "sp-v2")


def make_layout(blueprint: str):
    if blueprint == "sp-v1":
        from experiments.sp_progression_v1 import make_layout as make
    elif blueprint == "sp-v2":
        from experiments.sp_progression_v2 import make_layout as make
    else:
        raise ValueError(f"unknown blueprint {blueprint!r}")
    return make()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--blueprint", default="sp-v1", choices=BLUEPRINTS)
    parser.add_argument("--json", default=None,
                        help="default: reports/SP-<v>-door-audit.json")
    parser.add_argument("--markdown")
    args = parser.parse_args(argv)

    compiled = make_layout(args.blueprint).compile()
    audit = authored_gate_audit(compiled)
    affordance = door_affordance_report(compiled)
    version = args.blueprint.split("-")[1]
    target = Path(args.json or f"reports/SP-{version}-door-audit.json")
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(
        json.dumps({"audit": audit, "affordance": affordance},
                   indent=2, sort_keys=True) + "\n",
        encoding="utf-8", newline="\n")
    if args.markdown:
        Path(args.markdown).write_text(
            gate_audit_markdown(audit), encoding="utf-8", newline="\n")
    print(f"{args.blueprint}: {audit['gate_count']} gates "
          f"affordance_ok={affordance['ok']}")
    # v1 is the frozen blueprint whose affordance failures the audit exists to
    # show; only v2 is expected to pass.
    return 0 if affordance["ok"] or args.blueprint == "sp-v1" else 1


if __name__ == "__main__":
    raise SystemExit(main())
