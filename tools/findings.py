"""Look up and file findings: what building levels has taught us, each saying how it is known.

.. code-block:: bash

    python -m tools.findings find stair flight            # every word must answer; the firmest first
    python -m tools.findings find lamp --standing engine  # only what the engine itself says
    python -m tools.findings show wall-courses-run-on-down-a-flight
    python -m tools.findings list --topic renderer
    python -m tools.findings standings                    # the kinds of knowing, and what each must cite
    python -m tools.findings add --id ambient-sound-needs-a-falloff --topic sound --standing engine \\
        --claim "An ambient sound sprite (type 710) whose data_1 is not below data_2 plays nothing." \\
        --evidence "NBlood/source/blood/src/asound.cpp:60" --use "Give data_1 < data_2." \\
        --code bloodmap.ambience --in blood-city
    python -m tools.findings check                        # exit 1 if a finding is badly made or names code that is gone

`python -m tools.catalog find <words>` shows the findings first, with every other shelf.
The shelf and its rules are `bloodmap.findings`.
"""

from __future__ import annotations

import argparse
import sys

from bloodmap import findings as F


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="cmd", required=True)
    for name in ("find", "list"):
        p = sub.add_parser(name)
        if name == "find":
            p.add_argument("words", nargs="+")
        p.add_argument("--topic", choices=F.TOPICS)
        p.add_argument("--standing", choices=tuple(F.STANDINGS))
        p.add_argument("--scope")
    sub.add_parser("show").add_argument("id")
    sub.add_parser("standings")
    sub.add_parser("check")
    add = sub.add_parser("add")
    add.add_argument("--id", required=True)
    add.add_argument("--topic", required=True, choices=F.TOPICS)
    add.add_argument("--standing", required=True, choices=tuple(F.STANDINGS))
    add.add_argument("--claim", required=True)
    add.add_argument("--evidence", action="append", default=[], help="once for each thing to check it by")
    add.add_argument("--use", default="")
    add.add_argument("--code", action="append", default=[], help="a function that already does it: bloodmap.module.name")
    add.add_argument("--scope", default="blood")
    add.add_argument("--in", dest="learned_in", required=True, help="the project it was learned in")
    add.add_argument("--date")
    add.add_argument("--words", nargs="*", default=[], help="other words it should be found by")
    add.add_argument("--instead", default="", help="for a refuted finding: what is true")
    add.add_argument("--replace", action="store_true")
    args = parser.parse_args(argv)

    if args.cmd in ("find", "list"):
        rows = F.find(getattr(args, "words", []), topic=args.topic, standing=args.standing, scope=args.scope)
        print("\n".join(F.line(row) for row in rows) or "  nothing on file")
        return 0
    if args.cmd == "show":
        rows = [row for row in F.read() if row["id"] == args.id]
        if not rows:
            near = F.find(args.id.split("-"))[:5]
            print(f"no finding {args.id}" + ("; near it:\n" + "\n".join(F.line(r) for r in near) if near else ""))
            return 1
        print(F.show(rows[0]))
        return 0
    if args.cmd == "standings":
        for name, said in F.STANDINGS.items():
            print(f"  {name:<11}{said}")
        return 0
    if args.cmd == "check":
        wrong = F.check()
        print("\n".join(wrong) or f"{len(F.read())} findings, all well made")
        return 1 if wrong else 0
    try:
        row = F.record(id=args.id, topic=args.topic, standing=args.standing, claim=args.claim, evidence=args.evidence,
                       use=args.use, code=args.code, scope=args.scope, learned_in=args.learned_in, date=args.date,
                       words=args.words, instead=args.instead, replace=args.replace)
    except F.FindingError as exc:
        print(f"not filed: {exc}", file=sys.stderr)
        return 1
    print(F.show(row))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
