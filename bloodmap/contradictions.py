"""Cross-layer disagreements, ranked, for the owner to settle by name.

Phase 11's second steering item, minimum viable. The project now holds the
same facts in four places -- the owner's anchors, the usage-kind table mined
from the campaign, the claims constructors make in code, and whatever the
built map actually contains -- and nothing compared them. Every gap this
project has shipped was a disagreement between two of those that no one had
asked about.

So: one pass, one ranked queue, each item named so the owner can confirm or
reject it individually. This is deliberately not clever. It asks four
questions that have bitten already, and it carries the two open items the
audit could not settle by measurement.

What it is NOT: a discovery frontier. It compares what is already written
down. Ranking candidates by novelty and coverage over community mining is
the other half of Phase 11 and remains open.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
QUEUE = ROOT / "reports" / "contradictions.json"

#: Ranks, worst first. A CONFLICT is two sources asserting incompatible
#: things; a DRIFT is one source having moved away from another without
#: contradicting it; an OPEN item is a question measurement could not settle
#: and only the owner can.
CONFLICT, DRIFT, OPEN = "conflict", "drift", "open"
RANK = {CONFLICT: 0, DRIFT: 1, OPEN: 2}


@dataclass
class Disagreement:
    """One thing two sources say differently, addressed by name."""

    name: str
    kind: str
    between: tuple[str, str]
    says: str
    ask: str
    detail: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {"name": self.name, "kind": self.kind,
                "between": list(self.between), "says": self.says,
                "ask": self.ask, "detail": self.detail}


def _anchors():
    try:
        from .owner_anchors import load_owner_anchors

        return load_owner_anchors()
    except Exception:
        return None


def anchors_against_usage(limit: int = 12) -> list[Disagreement]:
    """Owner anchors whose `kind` the campaign's own usage disagrees with.

    An anchor's `kind` is the owner's first-glance reading -- sprite, wall,
    surface, maskwall -- and the reading guide says outright that a tile can
    legitimately appear in other kinds. So this is a DRIFT, never a conflict:
    it lists tiles where the owner's glance and the corpus's practice point
    different ways, for the owner to confirm or wave off.
    """
    from .usage_kinds import slots_for

    anchors = _anchors()
    if anchors is None:
        return []
    kinds = {
        "wall": ("wall_one_sided", "wall_two_sided"),
        "surface": ("floor", "ceiling", "floor_parallax", "ceiling_parallax"),
        "sprite": ("sprite_face", "sprite_wall", "sprite_floor"),
        "maskwall": ("over_picnum",),
    }
    out = []
    for anchor in anchors.anchors:
        wanted = kinds.get(getattr(anchor, "kind", "") or "")
        if not wanted:
            continue
        slots = slots_for(anchor.picnum)
        if not slots:
            continue
        mine = sum(slots.get(slot, 0) for slot in wanted)
        total = sum(slots.values())
        if total and mine == 0:
            out.append(Disagreement(
                name=f"tile-{anchor.picnum}-kind",
                kind=DRIFT,
                between=("owner-anchors", "usage-kinds"),
                says=(f"the owner reads tile {anchor.picnum} as "
                      f"{anchor.kind!r} ({anchor.label_en}); the campaign "
                      f"never uses it that way, only "
                      f"{', '.join(sorted(slots))}"),
                ask="is the kind a first-glance label to correct, or is the "
                    "campaign simply not using it the way it could be?",
                detail={"picnum": anchor.picnum, "kind": anchor.kind,
                        "attested": slots},
            ))
    out.sort(key=lambda item: -item.detail["attested"].get("wall_one_sided", 0))
    return out[:limit]


def built_against_usage(map_path: str | Path,
                        limit: int = 12) -> list[Disagreement]:
    """A built map's tile use against what the campaign attests.

    Both halves of the audit's finding: slots the corpus never uses a tile
    in, and tiles the map leans on far harder than the campaign does. The
    second is the one that caught tile 400 at 786 times the campaign rate
    with every single use in an attested slot.
    """
    from .format import read_map
    from .usage_kinds import overused, unattested_uses

    disk = read_map(map_path)
    out = []
    for row in unattested_uses(disk)[:limit]:
        out.append(Disagreement(
            name=f"slot-{row['picnum']}-{row['slot']}",
            kind=CONFLICT,
            between=("built map", "usage-kinds"),
            says=(f"{row['where']} puts tile {row['picnum']} in "
                  f"{row['slot']}; the campaign attests it only in "
                  f"{', '.join(row['attested'])}"),
            ask="is this a first use, or a mistake?",
            detail=dict(row),
        ))
    for row in overused(disk):
        out.append(Disagreement(
            name=f"rate-{row['picnum']}",
            kind=DRIFT,
            between=("built map", "usage-kinds"),
            says=(f"tile {row['picnum']} is on {row['used']} walls, "
                  f"{row['times_the_campaign_rate']}x the campaign's rate; "
                  f"it has {row['campaign_slots']} wall slots in 43 maps"),
            ask="is this material meant to carry a whole level?",
            detail=dict(row),
        ))
    return out


def constructors_against_anchors() -> list[Disagreement]:
    """Tiles a constructor hard-codes, against the owner's reading of them.

    A constructor that names a tile is making an owner-facing claim, and the
    binding rule says only a STRONG anchor may name what it depicts. This
    reports constructor constants whose tile is graded weak or untested, so
    the claim is visible rather than buried in a default argument.
    """
    anchors = _anchors()
    if anchors is None:
        return []
    from . import mechanism

    named = {
        "mechanism.CURTAIN_PICNUM": getattr(mechanism, "CURTAIN_PICNUM", None),
        "mechanism.BLADE_PICNUM": getattr(mechanism, "BLADE_PICNUM", None),
        "mechanism.FENCE_PICNUM": getattr(mechanism, "FENCE_PICNUM", None),
    }
    by_picnum = {anchor.picnum: anchor for anchor in anchors.anchors}
    out = []
    for where, picnum in named.items():
        if picnum is None:
            continue
        anchor = by_picnum.get(int(picnum))
        if anchor is None:
            out.append(Disagreement(
                name=f"unanchored-{picnum}",
                kind=OPEN,
                between=("constructors", "owner-anchors"),
                says=f"{where} is tile {picnum}, which no anchor names",
                ask="what is this tile, in your words?",
                detail={"picnum": int(picnum), "where": where},
            ))
        elif (anchor.binding or "untested") != "strong":
            out.append(Disagreement(
                name=f"weakly-named-{picnum}",
                kind=DRIFT,
                between=("constructors", "owner-anchors"),
                says=(f"{where} is tile {picnum}, graded "
                      f"{anchor.binding or 'untested'}: "
                      f"{anchor.label_en}"),
                ask="a weak or untested tile may not name what it depicts; "
                    "is the constructor's use of it right anyway?",
                detail={"picnum": int(picnum), "where": where,
                        "binding": anchor.binding},
            ))
    return out


def standing_items() -> list[Disagreement]:
    """The two questions the audit measured and could not settle.

    Both are the owner's call by construction: one asks whether 23 slots are
    a family or an accident, and the other asks whether a norm applies to an
    artifact it was not measured on.
    """
    return [
        Disagreement(
            name="mask-law-two-sided-exception",
            kind=OPEN,
            between=("usage-kinds", "the mask law"),
            says=("tiles 142 and 2464 carry the mask colour and appear on "
                  "two-sided walls in 23 of 60839 slots. Nothing else "
                  "breaks the law anywhere: 0 of 26383 surfaces and 0 of "
                  "52422 one-sided walls"),
            ask="family or accident? If a family, the law gains a clause "
                "for door-leaf faces; if an accident, it gains a rate and "
                "two-sided walls come under it too",
            detail={"picnums": [142, 2464], "slots": 23, "of": 60839},
        ),
        Disagreement(
            name="gallery-topology-exemption",
            kind=OPEN,
            between=("norms-v1", "the pattern zoo"),
            says=("the zoo measures mean_degree 2.09 against a campaign "
                  "median of 2.74, and a dead-end fraction of 0.344 against "
                  "0.159. Thirty-one exhibits are terminal by construction, "
                  "so the only way to hit the norm is to add loops that go "
                  "nowhere"),
            ask="accept a documented exemption for gallery-shaped artifacts, "
                "rather than gaming the number?",
            detail={"mean_degree": 2.09, "campaign_median": 2.74,
                    "dead_end_fraction": 0.344, "campaign_median_dead_end":
                    0.159},
        ),
    ]


def run(map_path: str | Path | None = None) -> dict[str, Any]:
    """Every check, ranked worst first."""
    found: list[Disagreement] = []
    found.extend(constructors_against_anchors())
    found.extend(anchors_against_usage())
    if map_path is not None:
        found.extend(built_against_usage(map_path))
    found.extend(standing_items())
    found.sort(key=lambda item: (RANK.get(item.kind, 9), item.name))
    return {
        "$schema": "llmapper.contradictions", "schema_version": 1,
        "about": ("cross-layer disagreements between owner anchors, the "
                  "usage-kind table, constructor claims and a built map. "
                  "Each is addressed by name for confirm/reject."),
        "map": str(map_path).replace("\\", "/") if map_path else None,
        "counts": {kind: sum(1 for item in found if item.kind == kind)
                   for kind in (CONFLICT, DRIFT, OPEN)},
        "queue": [item.to_dict() for item in found],
    }


def write(report: dict[str, Any], path: Path | str = QUEUE) -> Path:
    out = Path(path)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, indent=1) + "\n", encoding="utf-8",
                   newline="\n")
    return out
