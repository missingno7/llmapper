"""What a working example of a mechanism looks like, mined whole.

`tools.mine_mechanisms` counts channels. `tools.mine_decoration` counts sprite
sizes. Neither can state what a *gate* is, because a gate is six objects and
half of what makes it work is the relations between them.

This mines the whole assembly. For a chosen root -- a sector type, usually --
it finds every instance in the campaign, closes over the objects bound to it,
and reports for each part both its modal fields and its modal relations to the
rest. The output is a template an author can be held to.

.. code-block:: bash

    python -m tools.mine_assemblies --root 614            # sliding gates
    python -m tools.mine_assemblies --root 617 --examples 3
    python -m tools.mine_assemblies --root 614 \\
        --against projects/.../candidate-v5.MAP

The `--against` form is the point of it: it checks a built level's own instances
against the template and names every part that disagrees. Seven of the faults
found in the monastery by playing it were relations this reports.
"""

from __future__ import annotations

import argparse
import json
import pathlib
import re
import statistics
from collections import Counter, defaultdict
from typing import Any

from bloodmap.assembly import Assembly, assembly_around
from bloodmap.format import read_map
from bloodmap.patterns import list_corpus_maps

CAMPAIGN = re.compile(r"^E[1-46]M[1-9]$")

#: Fields that are addresses or runtime scratch: never comparable across maps.
IGNORED = frozenset({
    "reference", "marker_0", "marker_1", "target", "burn_source",
    "target_x", "target_y", "target_z", "rx_id", "tx_id", "busy",
})

#: A modal value has to hold this often before it is stated as the template's.
SETTLED = 0.6

#: Fields whose correct value depends on the size of the thing being built, and
#: which the template states again as a scale-free relation. Judged there.
COVERED_BY_RELATION = frozenset({"x_repeat", "y_repeat"})

#: How many times a role has to appear before the template will say anything
#: about it. Without this the tool announces conventions from samples of one:
#: exactly one campaign sludge sector has a switch in it, and the first version
#: reported that switch's picnum, type and cstat as 100% rules and then failed
#: this level for using a different switch. A share means nothing without a
#: denominator, which is the same mistake as reading a percentile as a limit or
#: a raw count as a norm.
MIN_OBSERVATIONS = 8


def instances(directory: str, root_type: int, *, campaign_only: bool = True) -> list[Assembly]:
    """Every instance of this root in a corpus.

    `campaign_only` restricts to the shipped episodes, which is right when the
    question is "what did the designers usually do". It is wrong when the
    question is "how does this mechanism work at all", because the campaign is
    not a complete demonstration of the engine: the XMapEdit samples use two
    sector types, one wall type and 48 sprite types that appear nowhere in the
    43 shipped maps. A path sector has *no* campaign instance, so a template
    mined campaign-only can say nothing about it.
    """
    found: list[Assembly] = []
    # These used to be two globs over a flat corpus. The corpus is now a
    # registry of provenance directories, so ask it for the population the
    # docstring above names: the shipped episodes, or the mechanism samples.
    population = "blood-campaign" if campaign_only else "mechanism-tutorial"
    for path in sorted(str(item.path) for item in
                       list_corpus_maps(directory or None, population=population)):
        name = pathlib.Path(path).stem.upper()
        if campaign_only and not CAMPAIGN.match(name):
            continue
        try:
            disk = read_map(path)
        except Exception:
            continue
        for index, sector in enumerate(disk.sectors):
            fields = sector["fields"] if isinstance(sector, dict) else sector.fields
            if int(fields["type"]) != root_type:
                continue
            if (sector["blood"] if isinstance(sector, dict) else sector.extra) is None:
                continue
            found.append(assembly_around(disk, index, map_name=name))
    return found


def _modal(values: list[Any]) -> tuple[Any, float] | None:
    if not values:
        return None
    counts = Counter(values)
    value, count = counts.most_common(1)[0]
    return value, count / len(values)


def build_template(found: list[Assembly]) -> dict[str, Any]:
    roles: dict[str, list[Any]] = defaultdict(list)
    for one in found:
        for member in one.members:
            roles[member.role].append(member)

    shapes = Counter(one.shape() for one in found)
    per_role: dict[str, Any] = {}
    for role, members in sorted(roles.items()):
        settled = len(members) >= MIN_OBSERVATIONS
        fields: dict[str, Any] = {}
        for name in sorted({k for m in members for k in m.fields}):
            if name in IGNORED:
                continue
            column = [m.fields.get(name) for m in members if name in m.fields]
            got = _modal(column)
            if settled and got and got[1] >= SETTLED:
                counts = Counter(column)
                fields[name] = {
                    "value": got[0], "share": round(got[1], 3),
                    "seen": {k: round(v / len(column), 4) for k, v in counts.items()},
                }
        extras: dict[str, Any] = {}
        for name in sorted({k for m in members for k in m.extra}):
            if name in IGNORED:
                continue
            got = _modal([m.extra.get(name, 0) for m in members])
            if settled and got and got[1] >= SETTLED and got[0] != 0:
                extras[name] = {"value": got[0], "share": round(got[1], 3)}
        relations: dict[str, Any] = {}
        for name in sorted({k for m in members for k in m.relations}):
            values = [m.relations[name] for m in members if name in m.relations]
            if not values or not settled:
                continue
            if all(isinstance(v, (int, float)) and not isinstance(v, bool) for v in values):
                ordered = sorted(values)
                got = _modal(values)
                relations[name] = {
                    "median": round(statistics.median(ordered), 3),
                    "q1": ordered[len(ordered) // 4],
                    "q3": ordered[3 * len(ordered) // 4],
                    "modal": got[0] if got else None,
                    "modal_share": round(got[1], 3) if got else None,
                }
            else:
                got = _modal(values)
                if got:
                    relations[name] = {"modal": got[0], "modal_share": round(got[1], 3)}
        per_role[role] = {
            "instances": len(members),
            "settled": settled,
            "per_assembly": round(len(members) / len(found), 2),
            "fields": fields,
            "xsprite": extras,
            "relations": relations,
        }

    whole: dict[str, Any] = {}
    for name in sorted({k for one in found for k in one.relations}):
        values = [one.relations[name] for one in found if name in one.relations]
        column = [tuple(v) if isinstance(v, list) else v for v in values]
        got = _modal(column)
        entry: dict[str, Any] = {"observed": len(values)}
        if got:
            entry["modal"] = got[0]
            entry["modal_share"] = round(got[1], 3)
            entry["seen"] = {k: round(v / len(column), 4)
                             for k, v in Counter(column).items()}
        numeric = [v for v in values if isinstance(v, (int, float)) and not isinstance(v, bool)]
        if numeric:
            ordered = sorted(numeric)
            entry["median"] = round(statistics.median(ordered), 3)
            entry["q1"] = ordered[len(ordered) // 4]
            entry["q3"] = ordered[3 * len(ordered) // 4]
        whole[name] = entry

    return {
        "instances": len(found),
        "maps": len({one.map_name for one in found}),
        "shapes": [{"roles": dict(shape), "count": count}
                   for shape, count in shapes.most_common(4)],
        "roles": per_role,
        "assembly_relations": whole,
    }


def _attested(values: dict[Any, float], value: Any) -> bool:
    return values.get(value, 0.0) > 0.0


def check(found: list[Assembly], template: dict[str, Any],
          *, strict: bool = False) -> list[dict[str, Any]]:
    """Parts of these instances the campaign gives no precedent for.

    The distinction that makes this usable: a value the campaign *never* uses is
    a fault, and a value it uses less often than some other is a choice. The
    first version reported both, and its output for a correct gate was nineteen
    lines of which one was real -- a state-and-busy pair used by 9% of campaign
    gates, a switch of the other of the two switch types, and so on. Reporting a
    legitimate minority form as an error trains the reader to ignore the tool.

    `strict` restores the noisier behaviour, which is worth having when the
    question is "how conventional is this" rather than "is this wrong".
    """
    out: list[dict[str, Any]] = []
    for one in found:
        present = {m.role for m in one.members}
        for role, spec in template["roles"].items():
            if spec["per_assembly"] >= 0.9 and role not in present:
                out.append({"root": one.root_index, "role": role,
                            "problem": "missing", "detail":
                            f"the campaign has {spec['per_assembly']} of these per assembly"})
        for member in one.members:
            spec = template["roles"].get(member.role)
            if spec is None:
                continue
            for name, want in spec["fields"].items():
                if name not in member.fields:
                    continue
                if name in COVERED_BY_RELATION and not strict:
                    # An absolute the template also states as a ratio. A gate leaf
                    # in a narrow doorway must be narrower than one in a wide
                    # doorway, so its x_repeat is not comparable across maps and
                    # `width_over_travel` is. Flagging the absolute as well
                    # reports a correctly-scaled part as wrong.
                    continue
                got = member.fields[name]
                if got == want["value"]:
                    continue
                seen = want.get("seen") or {}
                if _attested(seen, got) and not strict:
                    continue
                out.append({
                    "root": one.root_index, "role": member.role,
                    "index": member.index, "problem": f"field {name}",
                    "detail": "%s -- the campaign never uses that here (it uses %s in %.0f%%)"
                              % (got, want["value"], 100 * want["share"])})
            for name, want in spec["relations"].items():
                if name not in member.relations:
                    continue
                got = member.relations[name]
                if not isinstance(got, (int, float)) or isinstance(got, bool):
                    continue
                if want.get("modal_share", 0) >= SETTLED and got != want.get("modal"):
                    out.append({
                        "root": one.root_index, "role": member.role,
                        "index": member.index, "problem": f"relation {name}",
                        "detail": "%s, campaign uses %s in %.0f%%" % (
                            got, want["modal"], 100 * want["modal_share"])})
                elif not (want["q1"] <= got <= want["q3"]):
                    out.append({
                        "root": one.root_index, "role": member.role,
                        "index": member.index, "problem": f"relation {name}",
                        "detail": "%s, campaign q1..q3 %s..%s" % (
                            got, want["q1"], want["q3"])})
        for name, want in template["assembly_relations"].items():
            if name not in one.relations:
                continue
            got = one.relations[name]
            got = tuple(got) if isinstance(got, list) else got
            if want.get("modal_share", 0) < SETTLED or got == want.get("modal"):
                continue
            seen = want.get("seen") or {}
            if _attested(seen, got) and not strict:
                continue
            out.append({
                "root": one.root_index, "role": "assembly", "problem": name,
                "detail": "%s -- the campaign never uses that (it uses %s in %.0f%%)" % (
                    got, want["modal"], 100 * want["modal_share"])})
    return out


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--maps", default=None,
                        help="corpus root; defaults to the registry's")
    parser.add_argument("--samples", action="store_true",
                        help="mine the XMapEdit sample maps instead of the campaign")
    parser.add_argument("--root", type=int, required=True, help="root sector type")
    parser.add_argument("--against")
    parser.add_argument("--strict", action="store_true",
                        help="also report values the campaign uses, but rarely")
    parser.add_argument("-o", "--output")
    args = parser.parse_args(argv)

    found = instances(args.maps, args.root, campaign_only=not args.samples)
    if not found:
        print("no campaign instances of sector type %d" % args.root)
        return 1
    template = build_template(found)

    print("sector type %d: %d instances across %d maps" % (
        args.root, template["instances"], template["maps"]))
    print("\nthe assembly, as the campaign builds it:")
    for role, spec in sorted(template["roles"].items(),
                             key=lambda kv: -kv[1]["per_assembly"]):
        print("  %-18s x%-5.2f per assembly%s" % (
            role, spec["per_assembly"],
            "" if spec["settled"] else "   (too few to state anything)"))
        for name, want in spec["fields"].items():
            print("      %-22s %-10s %.0f%%" % (name, want["value"], 100 * want["share"]))
        for name, want in spec["xsprite"].items():
            print("      xsprite.%-14s %-10s %.0f%%" % (name, want["value"], 100 * want["share"]))
        for name, want in spec["relations"].items():
            if want.get("modal_share") and want["modal_share"] >= SETTLED:
                print("      rel %-18s %-10s %.0f%%" % (name, want["modal"], 100 * want["modal_share"]))
            elif "q1" in want:
                print("      rel %-18s median %-6s q1..q3 %s..%s" % (
                    name, want["median"], want["q1"], want["q3"]))
    print("\n  whole-assembly:")
    for name, want in template["assembly_relations"].items():
        if want.get("modal_share", 0) >= SETTLED:
            print("      %-22s %-14s %.0f%%" % (name, want["modal"], 100 * want["modal_share"]))
        elif "median" in want:
            print("      %-22s median %-8s q1..q3 %s..%s" % (
                name, want["median"], want["q1"], want["q3"]))

    if args.output:
        pathlib.Path(args.output).write_text(
            json.dumps(template, indent=1, default=str) + "\n", encoding="utf-8")

    if args.against:
        disk = read_map(args.against)
        mine = [
            assembly_around(disk, index, map_name=pathlib.Path(args.against).stem)
            for index, sector in enumerate(disk.sectors)
            if int((sector["fields"] if isinstance(sector, dict) else sector.fields)["type"]) == args.root
            and (sector["blood"] if isinstance(sector, dict) else sector.extra) is not None
        ]
        print("\ncandidate: %d instance(s)" % len(mine))
        problems = check(mine, template, strict=args.strict)
        if not problems:
            print("  every part agrees with the template")
        for row in problems:
            print("  sector %-4s %-16s %-22s %s" % (
                row["root"], row["role"], row["problem"], row["detail"]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
