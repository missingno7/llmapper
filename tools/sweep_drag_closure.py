"""Sweep every slide/rotate mechanism in the originals through its DragPoint closure.

The question this answers: when an original map's mechanism moves, what
ELSE moves, and does any of it break? `motion_sim.closure_health` walks
`nextwall` exactly as `DragPoint` does (triggers.cpp:817-854), so a
neighbour whose loop inverts, crosses itself, or cuts through standing
geometry at any pose is reported, and so is a vertex that sits on the moved
point without being paired to it (the engine leaves those behind).

Populations: the mechanism curriculum (`maps/blood/mechanism/*.MAP` primers
and `Vanilla/`; `Modern/` is the NBlood-extension dialect and is excluded)
and the campaign. Generated maps are never mined here.

    python -m tools.sweep_drag_closure [--steps 16] [--out reports/...json]
"""

from __future__ import annotations

import argparse
import json
import pathlib
import sys
from collections import Counter
from typing import Any

ROOT = pathlib.Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from bloodmap.format import read_map                        # noqa: E402
from bloodmap.motion_sim import closure_health             # noqa: E402
from bloodmap.patterns import corpus_root, list_corpus_maps  # noqa: E402

SWEPT_TYPES = (614, 615, 616, 617)
OUT = ROOT / "reports" / "blood-mechanism-drag-closure.json"


def curriculum_maps() -> list[pathlib.Path]:
    """The vanilla course: top-level primers and Vanilla/. Never Modern/."""
    folder = corpus_root() / "mechanism"
    picked = [p for p in folder.glob("*.[mM][aA][pP]")
              if not p.name.upper().startswith("ASAVE")]
    picked += list((folder / "Vanilla").glob("*.[mM][aA][pP]"))
    return sorted(picked, key=lambda p: str(p).lower())


def campaign_maps() -> list[pathlib.Path]:
    return sorted(item.path for item in list_corpus_maps(population="blood-campaign"))


def sweep_map(path: pathlib.Path, population: str, *, steps: int) -> list[dict[str, Any]]:
    disk = read_map(path)
    rows: list[dict[str, Any]] = []
    for sector_id, sector in enumerate(disk.sectors):
        type_id = int(sector.fields["type"])
        if type_id not in SWEPT_TYPES or sector.extra is None:
            continue
        row: dict[str, Any] = {"map": path.name, "population": population,
                               "sector": sector_id, "type": type_id}
        try:
            health = closure_health(disk, sector_id, steps=steps)
        except ValueError as exc:
            row["not_swept"] = str(exc)
            rows.append(row)
            continue
        #: JUDGED neighbours are the ones a single-mechanism sweep is the
        #: right frame for: not movers themselves, and not hubs some other
        #: mechanism in the map drags too. The rest are counted and listed
        #: as candidates, never as defects.
        others = [r for r in health["loops"] if not r["own"]]
        neighbours = [r for r in others if not r["co_mover"] and not r["co_driven_by"]]
        assembly = [r for r in others if r["co_mover"] or r["co_driven_by"]]
        row.update({
            "moved_walls": health["moved_walls"],
            "sectors": health["sectors"],
            "neighbours": health["neighbours"],
            "co_movers": health["co_movers"],
            "co_driven_sectors": health["co_driven_sectors"],
            "static_neighbours": [s for s in health["neighbours"]
                                  if s not in health["co_movers"]],
            "coincidence_sectors": health["coincidence_sectors"],
            "isolated": health["isolated"],
            "neighbour_loops": len(neighbours),
            "assembly_loops": len(assembly),
            "co_mover_notes": health["notes"],
            "assembly_loops_breaking": [
                {"sector": r["sector"], "loop": r["loop"],
                 "shared_with": sorted(set(r["co_driven_by"]))[:8],
                 "inverts": bool(r["inverted_steps"]),
                 "folds": bool(r["self_intersecting_steps"])}
                for r in assembly
                if r["inverted_steps"] or r["self_intersecting_steps"]],
            "neighbour_loops_inverting": [
                {"sector": r["sector"], "loop": r["loop"], "steps": r["inverted_steps"],
                 "area_drawn": r["area_drawn"]}
                for r in neighbours if r["inverted_steps"]],
            "neighbour_loops_self_intersecting": [
                {"sector": r["sector"], "loop": r["loop"], "steps": r["self_intersecting_steps"]}
                for r in neighbours if r["self_intersecting_steps"]],
            "own_loops_inverting": [
                {"loop": r["loop"], "steps": r["inverted_steps"]}
                for r in health["loops"] if r["own"] and r["inverted_steps"]],
            "own_loops_self_intersecting": [
                {"loop": r["loop"], "steps": r["self_intersecting_steps"]}
                for r in health["loops"] if r["own"] and r["self_intersecting_steps"]],
            "crossings": health["crossings"][:4],
            "crossing_count": len(health["crossings"]),
            "disagreements": [
                {"kind": d["kind"], "vertex": d["vertex"], "walls": d["walls"],
                 "sectors": d["sectors"]}
                for d in health["disagreements"]],
            "problems": health["problems"],
        })
        rows.append(row)
    return rows


def summarize(rows: list[dict[str, Any]]) -> dict[str, Any]:
    swept = [r for r in rows if "not_swept" not in r]
    label = lambda r: f"{r['map']} s{r['sector']} (type {r['type']})"  # noqa: E731
    deforming = [r for r in swept if r["neighbours"]]
    deforming_static = [r for r in swept if r["static_neighbours"]]
    with_co_movers = [r for r in swept if r["co_movers"]]
    inverting = [r for r in swept if r["neighbour_loops_inverting"]]
    folding = [r for r in swept if r["neighbour_loops_self_intersecting"]]
    own_bad = [r for r in swept if r["own_loops_inverting"] or r["own_loops_self_intersecting"]]
    crossing = [r for r in swept if r["crossing_count"]]
    disagree = [r for r in swept if r["disagreements"]]
    kinds = Counter(d["kind"] for r in swept for d in r["disagreements"])
    coincidence_wider = [r for r in swept
                         if set(r["coincidence_sectors"]) - set(r["sectors"])]
    chain_wider = [r for r in swept
                   if set(r["sectors"]) - set(r["coincidence_sectors"])]
    return {
        "mechanisms": len(rows),
        "swept": len(swept),
        "not_swept": [f"{label(r)}: {r['not_swept']}" for r in rows if "not_swept" in r],
        "by_type": dict(sorted(Counter(r["type"] for r in swept).items())),
        "deform_a_neighbour": len(deforming),
        "deform_a_static_neighbour": len(deforming_static),
        "in_a_co_moving_assembly": len(with_co_movers),
        "isolated": sum(1 for r in swept if r["isolated"]),
        "neighbour_loops_touched": sum(r["neighbour_loops"] for r in swept),
        "assembly_loops_touched": sum(r["assembly_loops"] for r in swept),
        #: Candidates, not defects: a hub several mechanisms drag is only
        #: whole when they all travel, and this sweeps one at a time.
        "assembly_loops_breaking_swept_alone": sorted({
            f"{r['map']} s{n['sector']} loop {n['loop']} "
            f"(dragged by {sorted(set([r['sector']] + n['shared_with']))})"
            for r in swept for n in r["assembly_loops_breaking"]}),
        "neighbour_inverts": [
            f"{label(r)} -> " + ", ".join(
                f"s{n['sector']} loop {n['loop']} at steps {n['steps']}"
                for n in r["neighbour_loops_inverting"])
            for r in inverting],
        "neighbour_self_intersects": [
            f"{label(r)} -> " + ", ".join(
                f"s{n['sector']} loop {n['loop']} at steps {n['steps']}"
                for n in r["neighbour_loops_self_intersecting"])
            for r in folding],
        "mover_inverts_or_folds": [label(r) for r in own_bad],
        "cuts_standing_geometry": [
            f"{label(r)}: {r['crossing_count']} crossing(s), first wall "
            f"{r['crossings'][0]['wall']} of s{r['crossings'][0]['sector']} through "
            f"wall {r['crossings'][0]['static_wall']} of s{r['crossings'][0]['static_sector']} "
            f"at step {r['crossings'][0]['step']}"
            for r in crossing],
        "closure_disagreements": {
            "mechanisms": len(disagree),
            "by_kind": dict(kinds),
            "coincidence_reaches_more_sectors": [label(r) for r in coincidence_wider],
            "chain_reaches_more_sectors": [label(r) for r in chain_wider],
            "examples": [
                f"{label(r)}: {d['kind']} at ({d['vertex'][0]}, {d['vertex'][1]}) "
                f"walls {d['walls']} of sectors {d['sectors']}"
                for r in disagree for d in r["disagreements"]][:40],
        },
    }


#: Fields worth carrying per mechanism into the JSON. The dropped ones are
#: either derivable (`static_neighbours`) or long lists of ids whose only
#: consumer is the summary above it.
KEEP = ("map", "sector", "type", "not_swept", "moved_walls",
        "sectors", "co_movers", "co_driven_sectors", "isolated",
        "neighbour_loops", "assembly_loops", "neighbour_loops_inverting",
        "neighbour_loops_self_intersecting", "assembly_loops_breaking",
        "own_loops_inverting", "own_loops_self_intersecting",
        "crossing_count", "disagreements", "problems")


def interesting(row: dict[str, Any]) -> bool:
    """Does this mechanism have anything the summary does not already say?

    The census is a count; the JSON is the evidence behind the count. A
    mechanism that deforms nothing, breaks nothing and disagrees with nothing
    is fully described by the summary line, and 900 such rows are what made
    the first version of this file 1.1 MB. They are counted, not listed.
    """
    return bool(
        row.get("not_swept") or row.get("problems") or row.get("disagreements")
        or row.get("neighbour_loops_inverting")
        or row.get("neighbour_loops_self_intersecting")
        or row.get("assembly_loops_breaking")
        or row.get("own_loops_inverting") or row.get("own_loops_self_intersecting")
        or row.get("crossing_count"))


def trim(row: dict[str, Any]) -> dict[str, Any]:
    kept = {key: row[key] for key in KEEP if key in row and row[key] not in ([], {}, 0)}
    for key, cap in (("disagreements", 6), ("problems", 3),
                     ("assembly_loops_breaking", 4)):
        trimmed = row.get(key, [])[:cap]
        total = len(row.get(key, []))
        if trimmed:
            kept[key] = trimmed
            if total > cap:
                kept[f"{key}_total"] = total
        else:
            kept.pop(key, None)
    return kept


def run(*, steps: int = 16) -> dict[str, Any]:
    out: dict[str, Any] = {
        "$schema": "llmapper.drag-closure-sweep", "schema_version": 1,
        "steps": steps,
        "basis": "triggers.cpp:817-854 DragPoint; :897-926 flagged-wall and "
                 "point2 propagation; :2144-2151 setBaseWallSect records the "
                 "mover's walls only; engine.cpp:13227 lastwall. Vanilla "
                 "branch: the only gModernMap split in TranslateSector "
                 "(:874-878) is for reverse-flagged sprites, not walls.",
        "populations": {},
    }
    for name, maps in (("curriculum", curriculum_maps()), ("campaign", campaign_maps())):
        rows: list[dict[str, Any]] = []
        unreadable: list[str] = []
        for path in maps:
            try:
                rows.extend(sweep_map(path, name, steps=steps))
            except Exception as exc:                       # pragma: no cover
                unreadable.append(f"{path.name}: {exc}")
        summary = summarize(rows)
        summary["maps"] = len(maps)
        summary["unreadable"] = unreadable
        listed = [trim(row) for row in rows if interesting(row)]
        summary["mechanisms_listed"] = len(listed)
        summary["mechanisms_clean_and_unlisted"] = len(rows) - len(listed)
        out["populations"][name] = {"summary": summary, "mechanisms": listed}
    return out


def markdown(report: dict[str, Any]) -> str:
    lines = ["```text"]
    for name, block in report["populations"].items():
        s = block["summary"]
        lines.append(f"{name:11s} maps {s['maps']:4d}  swept mechanisms {s['swept']:4d}  "
                     f"(not swept {len(s['not_swept'])})")
        lines.append(f"{'':11s} deform a neighbour {s['deform_a_neighbour']:4d}   "
                     f"(a STATIC one {s['deform_a_static_neighbour']:4d}; in a "
                     f"co-moving assembly {s['in_a_co_moving_assembly']:4d})   "
                     f"isolated (fin technique) {s['isolated']:4d}")
        lines.append(f"{'':11s} judgeable neighbour loops touched "
                     f"{s['neighbour_loops_touched']}   assembly loops (not "
                     f"judged) {s['assembly_loops_touched']}")
        lines.append(f"{'':11s} neighbour inverts {len(s['neighbour_inverts']):3d}   "
                     f"neighbour self-intersects {len(s['neighbour_self_intersects']):3d}   "
                     f"mover inverts/folds {len(s['mover_inverts_or_folds']):3d}   "
                     f"cuts standing geometry {len(s['cuts_standing_geometry']):3d}")
        lines.append(f"{'':11s} assembly hubs that break swept ALONE "
                     f"{len(s['assembly_loops_breaking_swept_alone']):3d} "
                     f"(candidates, not defects)")
        d = s["closure_disagreements"]
        lines.append(f"{'':11s} nextwall vs coincidence disagree on {d['mechanisms']} "
                     f"mechanism(s) {d['by_kind']}")
    lines.append("```")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--steps", type=int, default=16)
    parser.add_argument("--out", type=pathlib.Path, default=OUT)
    args = parser.parse_args(argv)
    report = run(steps=args.steps)
    args.out.write_text(json.dumps(report, indent=1) + "\n", encoding="utf-8", newline="\n")
    print(markdown(report))
    for name, block in report["populations"].items():
        s = block["summary"]
        for key in ("neighbour_inverts", "neighbour_self_intersects",
                    "mover_inverts_or_folds", "cuts_standing_geometry"):
            for line in s[key]:
                print(f"  {name} {key}: {line}")
        for line in s["closure_disagreements"]["examples"][:12]:
            print(f"  {name} disagreement: {line}")
    print(f"wrote {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
