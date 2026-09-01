"""Rules that know how sure they are.

This project accumulated forty-three compiler checks and eighteen hundred test
assertions, each one added the moment a fault was found, each one enforced at
whatever strength seemed right at the time. That is a checklist, and a checklist
cannot be wrong -- it can only be obeyed.

Running four of those checks back over Blood's own forty-three maps showed what
that costs::

    rule                                        campaign violates
    a flat tile has power-of-two sides                     0.03%
    a masked wall does not wear its own picnum             2.33%
    a sprite is drawn square                              11.20%
    a blocked wall is not an invisible kerb               12.98%

Two of those are engine laws and two are habits, and they had been enforced
identically. The last one cost something real: three rails were deleted from the
chapel on the stated grounds that "Blood does not do this", and Blood does it
**295 times, about seven per map**. The design argument for removing them was
sound; the evidence quoted for it was false.

So a rule here carries its own violation rate, measured over the corpus, and its
severity is *derived from that rate rather than chosen*:

* under 1% -- an **error**. The campaign essentially never does this, so a level
  that does is almost certainly broken rather than unusual.
* under 5% -- a **warning**.
* otherwise -- a **note**. Worth saying; never worth refusing a map over.

And a rule that has not been graded has no severity at all. `evaluate` will not
run one, because enforcing an unmeasured rule is exactly the mistake this module
exists to stop.

Each rule also carries a `source`: either a file and symbol in the engine, which
`unresolved_sources` checks exists, or the corpus itself. A rule whose evidence
does not resolve is not evidence.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Iterable, Sequence

ROOT = Path(__file__).resolve().parent.parent

#: Where the measured rates live, so they are not re-derived on every run.
GRADES_FILE = ROOT / "knowledge" / "blood" / "design" / "rules-v1.json"

#: Below this share of the corpus, doing it is a mistake rather than a choice.
ERROR_RATE = 0.01
#: Below this, it is unusual enough to mention firmly.
WARNING_RATE = 0.05

SEVERITIES = ("error", "warning", "note")


class RuleError(ValueError):
    """A rule used in a way the registry cannot stand behind."""


@dataclass(frozen=True)
class Violation:
    """One place a rule was broken, named precisely enough to go and look."""

    location: str
    detail: str = ""


@dataclass(frozen=True)
class Finding:
    """What a checker saw: how many things it looked at, and which failed."""

    population: int
    violations: tuple[Violation, ...] = ()

    @property
    def rate(self) -> float:
        return len(self.violations) / self.population if self.population else 0.0


@dataclass(frozen=True)
class Rule:
    """A claim about Blood, with somewhere to check it and a way to be wrong."""

    id: str
    statement: str
    because: str
    source: str
    scope: str
    check: Callable[[Any], Finding] = field(compare=False, repr=False)


@dataclass(frozen=True)
class Grade:
    """How often the corpus itself breaks a rule, and what that implies."""

    rule_id: str
    maps: int
    population: int
    violations: int

    @property
    def rate(self) -> float:
        return self.violations / self.population if self.population else 0.0

    @property
    def severity(self) -> str:
        return severity_for(self.rate)

    def to_dict(self) -> dict[str, Any]:
        return {
            "rule": self.rule_id, "maps": self.maps,
            "population": self.population, "violations": self.violations,
            "rate": round(self.rate, 5), "severity": self.severity,
        }


def severity_for(rate: float) -> str:
    if rate < ERROR_RATE:
        return "error"
    if rate < WARNING_RATE:
        return "warning"
    return "note"


RULES: dict[str, Rule] = {}


def register(rule: Rule) -> Rule:
    if rule.id in RULES:
        raise RuleError(f"duplicate rule id {rule.id!r}")
    if rule.scope not in ("wall", "sector", "sprite", "map"):
        raise RuleError(f"{rule.id}: unknown scope {rule.scope!r}")
    RULES[rule.id] = rule
    return rule


def unresolved_sources() -> list[str]:
    """Rules whose engine reference does not point at a file that exists.

    A corpus reference is taken on trust here -- `grade` measures it directly,
    which is a stronger check than any path could be.
    """
    out = []
    for rule in RULES.values():
        if not rule.source.startswith(("NBlood/", "xmapedit/")):
            continue
        # `path:line symbol` or `path symbol` -- the path is the first token,
        # up to a colon or a space.
        path = rule.source.split(":")[0].split()[0]
        if not (ROOT / path).exists():
            out.append(f"{rule.id}: {rule.source} does not resolve")
    return out


def grade(maps: Sequence[tuple[str, Any]],
          rules: Iterable[Rule] | None = None) -> dict[str, Grade]:
    """Measure every rule against the corpus.

    `maps` is (name, disk) pairs. Returns a grade per rule.
    """
    chosen = list(rules) if rules is not None else list(RULES.values())
    totals: dict[str, list[int]] = {r.id: [0, 0] for r in chosen}
    for _, disk in maps:
        for rule in chosen:
            found = rule.check(disk)
            totals[rule.id][0] += found.population
            totals[rule.id][1] += len(found.violations)
    return {
        rule.id: Grade(rule.id, len(maps), *totals[rule.id])
        for rule in chosen
    }


def save_grades(grades: dict[str, Grade], path: Path | str = GRADES_FILE) -> None:
    out = Path(path)
    out.parent.mkdir(parents=True, exist_ok=True)
    document = {
        "$schema": "llmapper.blood-rule-grades",
        "schema_version": 1,
        "error_below": ERROR_RATE,
        "warning_below": WARNING_RATE,
        "reading_guide": [
            "a rate is how often the campaign itself breaks the rule",
            "severity is derived from the rate and is never chosen by hand",
            "a rule with no grade here cannot be enforced at all",
        ],
        "rules": {
            rule_id: dict(g.to_dict(),
                          statement=RULES[rule_id].statement if rule_id in RULES else "",
                          source=RULES[rule_id].source if rule_id in RULES else "")
            for rule_id, g in sorted(grades.items())
        },
    }
    # newline="\n": the grades file is a committed artifact and every other
    # knowledge writer in the project pins LF, so a regrade on Windows must
    # not rewrite all 313 lines as a line-ending change.
    out.write_text(json.dumps(document, indent=1) + "\n", encoding="utf-8",
                   newline="\n")


def load_grades(path: Path | str = GRADES_FILE) -> dict[str, Grade]:
    try:
        raw = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    return {
        rule_id: Grade(rule_id, int(row["maps"]), int(row["population"]),
                       int(row["violations"]))
        for rule_id, row in raw.get("rules", {}).items()
    }


def evaluate(disk: Any, *, grades: dict[str, Grade] | None = None,
             rules: Iterable[Rule] | None = None,
             require_graded: bool = True) -> list[Any]:
    """Run the rules over one map and return `analysis.Diagnostic`s.

    The severity of each comes from the grade, not from the rule. A rule with no
    grade is skipped and reported as such -- enforcing an unmeasured rule is the
    mistake this module exists to prevent.
    """
    from .analysis import Diagnostic

    known = load_grades() if grades is None else grades
    chosen = list(rules) if rules is not None else list(RULES.values())
    out: list[Diagnostic] = []
    for rule in chosen:
        found = rule.check(disk)
        if rule.id not in known:
            if require_graded:
                out.append(Diagnostic(
                    "note", "rule-ungraded",
                    f"{rule.id} has not been measured against the corpus, so it "
                    "carries no severity and was not enforced",
                    "registry"))
            continue
        severity = known[rule.id].severity
        for violation in found.violations:
            out.append(Diagnostic(
                severity, rule.id,
                f"{rule.statement}{(' -- ' + violation.detail) if violation.detail else ''}",
                violation.location))
    return out


# ---------------------------------------------------------------------------
# helpers the checkers share
# ---------------------------------------------------------------------------

def _wall_owners(disk: Any) -> dict[int, int]:
    owner: dict[int, int] = {}
    for index, sector in enumerate(disk.sectors):
        start = int(sector.fields["wall_ptr"])
        for wall in range(start, start + int(sector.fields["wall_count"])):
            owner[wall] = index
    return owner


def _power_of_two(value: int) -> bool:
    return value > 0 and (value & (value - 1)) == 0


_ART_CACHE: dict[str, Any] = {}


def art_sizes() -> dict[int, tuple[int, int]]:
    """picnum -> (width, height), loaded once."""
    if "sizes" not in _ART_CACHE:
        try:
            from .art import read_art_directory
            art = read_art_directory(str(ROOT / "reference" / "blood"))
            _ART_CACHE["sizes"] = {t: (a.width, a.height) for t, a in art.items()}
        except Exception:
            _ART_CACHE["sizes"] = {}
    return _ART_CACHE["sizes"]
