"""Measure every rule against Blood, and record what it found.

.. code-block:: bash

    python -m tools.grade_rules                       # measure and write the grades
    python -m tools.grade_rules --against a.MAP       # then judge one map by them

A rule's severity is not written down anywhere by hand. It comes out of the rate
at which the campaign itself breaks the rule, so a rule that turns out to
describe a habit rather than a law is demoted automatically -- and one that
describes nothing at all shows up as breaking half the corpus.
"""

from __future__ import annotations

import argparse
import glob
import pathlib
import re

from bloodmap import rules_blood            # noqa: F401  -- registers the rules
from bloodmap.format import read_map
from bloodmap.rules import (
    ERROR_RATE, RULES, WARNING_RATE, evaluate, grade, load_grades, save_grades,
    unresolved_sources,
)

CAMPAIGN = re.compile(r"^E[1-46]M[1-9]$")


def campaign_maps(directory: str) -> list[tuple[str, object]]:
    out = []
    for path in sorted(glob.glob(str(pathlib.Path(directory) / "*.MAP"))):
        name = pathlib.Path(path).stem.upper()
        if not CAMPAIGN.match(name):
            continue
        try:
            out.append((name, read_map(path)))
        except Exception as error:
            print(f"skipped {name}: {type(error).__name__}: {error}")
    return out


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--maps", default="maps/blood")
    parser.add_argument("--against", help="judge this map by the measured grades")
    parser.add_argument("--no-write", action="store_true")
    args = parser.parse_args(argv)

    broken = unresolved_sources()
    if broken:
        print("evidence that does not resolve:")
        for line in broken:
            print("   ", line)
        return 1

    maps = campaign_maps(args.maps)
    if not maps:
        print("no campaign maps")
        return 1
    grades = grade(maps)
    if not args.no_write:
        save_grades(grades)

    print("%d rules against %d campaign maps" % (len(grades), len(maps)))
    print("  error below %.0f%%, warning below %.0f%%, note otherwise"
          % (100 * ERROR_RATE, 100 * WARNING_RATE))
    print()
    print("%-42s %9s %10s %8s  %-8s %s" % (
        "rule", "breaks", "of", "rate", "severity", "source"))
    for rule_id, row in sorted(grades.items(), key=lambda kv: kv[1].rate):
        rule = RULES[rule_id]
        kind = "engine" if rule.source.startswith(("NBlood/", "xmapedit/")) else "corpus"
        print("%-42s %9d %10d %7.2f%%  %-8s %s" % (
            rule_id, row.violations, row.population, 100 * row.rate,
            row.severity, kind))

    if args.against:
        disk = read_map(args.against)
        findings = evaluate(disk, grades=grades)
        print()
        print("%s: %d findings" % (args.against, len(findings)))
        by_severity: dict[str, int] = {}
        for item in findings:
            by_severity[item.severity] = by_severity.get(item.severity, 0) + 1
        for severity in ("error", "warning", "note"):
            if severity in by_severity:
                print("   %-8s %d" % (severity, by_severity[severity]))
        for item in findings[:20]:
            print("   %-8s %-40s %s" % (item.severity, item.location, item.code))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
