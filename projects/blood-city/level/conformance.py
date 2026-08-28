"""The standing conformance check: the classifier's reading vs. L1's claim.

Runs the Phase 0 city classifier on the compiled skeleton and diffs what it
reads -- street component, loops, blocks, widths -- against what the plan
declares.  Drift is a finding, never silent (references/design-layers.md).

    python projects/blood-city/level/conformance.py

writes reports/plan-conformance.md and exits nonzero on a red row.
"""

from __future__ import annotations

import json
import pathlib
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

from city_plan import plan
from resolution import PU, WIDTH_UNITS, STANDING, SEWER_FLOOR, GRADE

PROJECT = pathlib.Path(__file__).resolve().parents[1]
SKELETON = PROJECT / "level" / "city-skeleton.MAP"
CLASSIFIER_JSON = PROJECT / "reports" / "skeleton-classifier.json"


def classify() -> dict:
    subprocess.run(
        [sys.executable, "-m", "tools.mine_city_norms", "--maps", "NONE",
         "--input", f"SKELETON=blood={SKELETON.relative_to(ROOT).as_posix()}",
         "-o", str(CLASSIFIER_JSON.relative_to(ROOT).as_posix())],
        cwd=ROOT, check=True, capture_output=True)
    return json.load(open(CLASSIFIER_JSON))["per_map"][0]


#: Free-standing walkable masses with no doorway onto them.  Each adds a
#: walk-around loop and no urbanism, which is this project's own screening
#: rule ("loops without enterability are landscape, not urbanism" -- the
#: reason DWE2M1 was rejected as a street source).  They are counted, named
#: here, and set aside before the CN 2 block band is applied.
MONUMENTS = ("plaza_fountain",)


def main() -> int:
    data = plan()
    read = classify()
    rows = []

    def row(metric, declared, measured, ok, note=""):
        rows.append({"metric": metric, "declared": declared,
                     "measured": measured, "pass": bool(ok), "note": note})

    # ---- the plan against the tree ---------------------------------------
    #
    # `city_plan.VENUES` declares ten venues with types and frontages and
    # nothing checked that the tree agreed: three of them had no node at
    # all, one had been superseded by the Arcade, and none of that showed
    # anywhere.  Intent was traceable INSIDE the tree and not from the plan
    # into it, which is exactly the step where the planner is supposed to be
    # visible.  Each venue node now declares the slot it fills, so this
    # checks both directions and the type as well.
    import build_skeleton
    import citytree
    program = build_skeleton.build()[0]
    declared = citytree.venues(program)
    slots = {v["id"]: v for v in data["venues"]}
    slots.update({b["id"]: dict(b, type=b["role"])
                  for b in data["blocks"] if b["role"] == "free_standing"})
    missing = sorted(set(slots) - set(declared))
    unplanned = sorted(set(declared) - set(slots))
    doubled = sorted(k for k, v in declared.items() if len(v) > 1)
    mismatched = sorted(
        f"{k}: L1 {slots[k]['type']} vs node {getattr(nodes[0], 'l1_type', '?')}"
        for k, nodes in declared.items()
        if k in slots and getattr(nodes[0], "l1_type", None) != slots[k]["type"])
    built = [k for k, nodes in declared.items()
             if getattr(nodes[0], "built_by", "") != "(planned)"]
    row("L1 venues and masses with a node", len(slots), len(declared),
        not missing and not unplanned and not doubled and not mismatched,
        f"{len(built)} built, {len(declared) - len(built)} declared and not "
        f"built yet"
        + (f"; MISSING {missing}" if missing else "")
        + (f"; UNPLANNED {unplanned}" if unplanned else "")
        + (f"; DOUBLED {doubled}" if doubled else "")
        + (f"; TYPE {mismatched}" if mismatched else ""))

    # Indexed siblings are a rhythm or they are a naming fault.
    faults = citytree.rhythm_faults(program)
    row("indexed siblings sharing one note", 0, len(faults), not faults,
        "a numbered sibling is right only when one note serves them all"
        + (f"; {faults[:2]}" if faults else ""))

    # Loops: graph faces + free-standing masses + the church loop.
    free = [b for b in data["blocks"] if b["role"] == "free_standing"]
    nodes = set()
    for a, b, *_ in data["edges"]:
        nodes.update((a, b))
    declared_loops = len(data["edges"]) - len(nodes) + 1 + len(free) + len(MONUMENTS)
    measured_loops = read["blocks"]["street_loop_count"]
    # The CN 2 band counts BLOCKS.  A monument -- a free-standing mass with
    # no doorway onto it -- adds a walk-around loop without adding
    # urbanism, which is the screening rule this project adopted when
    # DWE2M1's landscape was rejected as a street.  So monuments are
    # counted, declared and then set aside before the band is applied.
    monuments = len(MONUMENTS)
    urban_loops = measured_loops - monuments
    row("street loops", declared_loops, measured_loops,
        measured_loops == declared_loops
        and 6 <= urban_loops <= 9,
        f"CN 2 band 6..9 applies to {urban_loops} block loops; "
        f"{monuments} monument loop(s) set aside")

    # Blocks: the walk-around census should match the plan's enclosed masses.
    # A monument is walkable and is not an L1 block, but the classifier
    # counts it as a walk-around mass, so the declaration has to own it.
    declared_blocks = len([b for b in data["blocks"]]) + len(MONUMENTS)
    measured_blocks = read["blocks"]["enclosed_walkaround_blocks"]
    extents = sorted(round(e) for e in
                     ([max(b["rect"][2] - b["rect"][0], b["rect"][3] - b["rect"][1]) * PU
                       for b in data["blocks"]]))
    measured_extents = read["blocks"]["block_extent_units"]
    row("walk-around blocks", declared_blocks, measured_blocks,
        measured_blocks == declared_blocks,
        f"declared extents {extents}; measured median {measured_extents.get('median')} "
        f"max {measured_extents.get('max')}")

    # Widths: the classifier's street-width band should bracket the declared
    # classes (its samples mix all streets, so compare the span).
    declared_span = (WIDTH_UNITS["alley"], WIDTH_UNITS["avenue"])
    width = read["street"]["width_units"]
    ok = width.get("n", 0) > 50 and \
        declared_span[0] <= width["p10"] <= width["p90"] and \
        width["median"] <= 3 * declared_span[1]
    row("street widths", f"classes {declared_span[0]}..{declared_span[1]}",
        f"p10 {width.get('p10')} median {width.get('median')} p90 {width.get('p90')}",
        ok, "plaza samples widen the top end by design")

    # Street component: every district's street region plus the cemetery and
    # gate rooms should join one at-grade component.
    # The generator declares what it built; the classifier says what is
    # there.  Reading the manifest keeps the two honest as the city grows
    # (light pools joined the street network and this check caught it).
    manifest = json.load(open(PROJECT / "reports" / "build-manifest.json"))
    # Name the keys this row means.  Summing everything in the manifest has
    # broken it three times now -- a list (`monuments`), then two structured
    # records (the lighting report, the rule summary), then a count that is
    # real but not street-joined (`door_frames`, the aperture reveal frames,
    # which are interior).  What this row asserts is: how many sectors join
    # the street's at-grade component.
    STREET_JOINED = ("districts", "carved_areas", "gates",
                     "stack_mouths_at_grade", "grate_kerb", "light_pools",
                     "market_furniture")
    expected_component = sum(int(manifest.get(k, 0)) for k in STREET_JOINED)
    row("street component joined",
        f"{' + '.join(f'{k} {manifest.get(k, 0)}' for k in STREET_JOINED)} "
        f"= {expected_component}",
        read["street"]["sectors"],
        read["street"]["sectors"] == expected_component,
        "a lower reading means a seam or gate failed to join")

    # Doorways from street at massing stage: the stair mouth. The manhole
    # pit is sky-ceilinged, so the classifier correctly reads it as street
    # space -- a drop entry is not a doorway.
    doors = read["enterability"]["doorways_from_street"]
    row("massing-stage doorways", ">=1 (works stair mouth)", doors,
        doors >= 1, "venue doorways arrive with Phase 3 facades")

    # Sewer depth as compiled (parked form: network floor below grade).
    depth_std = (SEWER_FLOOR - GRADE) / STANDING
    row("sewer depth", f"{depth_std:.2f} standing", "same constant",
        2.5 <= depth_std <= 4, "resolution.SEWER_FLOOR - GRADE")

    # The wormhole law: every sewer stack pair shares one XY translation
    # (owner sewer directive; campaign water holds this at 99%).
    # Read the pairs through the project's own stack miner rather than
    # hardcoded marker ids: this check silently passed nothing when the
    # links were rebuilt in the stack family (11/12) while it still looked
    # for the link family (6/7).
    from bloodmap.format import read_map
    from tools.mine_stacks import observe as observe_stacks
    pairs = [r for r in observe_stacks("CITY", read_map(SKELETON))
             if r.get("paired")]
    offsets = {r["link_id"]: tuple(r["offset"]) for r in pairs}
    families = {r["family"] for r in pairs}
    distinct = set(offsets.values())
    row("sewer stack links: one shared translation, stack family",
        f"{len(pairs)} pairs, families {sorted(families)}",
        f"offsets {sorted(distinct)}",
        len(pairs) >= 2 and len(distinct) == 1 and families == {"stack"},
        "owner sewer directive; the campaign's walkable ROR floors are the "
        "stack family, and every pair shares one translation")

    # ROR markers must survive the map loader.  NBlood db.cpp
    # PropagateMarkerReferences() deletes every sprite on statnum 10
    # (kStatMarker) whose type is not kMarkerOff/Axis/WarpDest/On -- and it
    # runs at the end of dbLoadMap, before warpInit registers any link.  A
    # stack marker on statnum 10 is therefore gone before it can connect
    # anything: the symptom is a solid floor and no way down.
    disk = read_map(SKELETON)
    markers = [sp for sp in disk.sprites
               if int(sp.fields.get("type", 0)) in (9, 10, 11, 12, 13, 14)]
    doomed = [sp for sp in markers if int(sp.fields["status"]) == 10]
    without_xsprite = [sp for sp in markers if int(sp.fields["extra"]) <= 0]
    # Marker tiles: the whole campaign (273 markers, every family) uses
    # 2332 on the upper half and 2331 on the lower.  bloodmap's MARKER_TILE
    # is 3997, which XMapEdit draws as a torch -- the symptom that started
    # this investigation.
    wrong_tile = [sp for sp in markers
                  if int(sp.fields["picnum"]) not in (2331, 2332)]
    upper_bad = [sp for sp in markers
                 if int(sp.fields.get("type", 0)) in (7, 9, 11)
                 and int(sp.fields["picnum"]) != 2332]
    lower_bad = [sp for sp in markers
                 if int(sp.fields.get("type", 0)) in (6, 10, 12)
                 and int(sp.fields["picnum"]) != 2331]
    row("ROR marker tiles match the campaign",
        "upper 2332 / lower 2331 (273 of 273 campaign markers)",
        f"wrong tile: {len(wrong_tile)}; upper wrong: {len(upper_bad)}; "
        f"lower wrong: {len(lower_bad)}",
        not wrong_tile and not upper_bad and not lower_bad,
        "so the editor shows a link, not a torch")

    # Falling must not hurt, and there must be a way back up.  Both from
    # NBlood: kDudeGravity 58254/tic, kFallDamageFloor 100<<4 forgiven, and
    # the standing human's normalJumpZ 0xbaaaa.
    GRAVITY, FORGIVEN, JUMP_RISE = 58254, 100 << 4, 21113
    drops, climbs = [], []
    for pair in pairs:
        upper_sec = disk.sectors[pair["upper_sector"]]
        lower_sec = disk.sectors[pair["lower_sector"]]
        plane = int(lower_sec.fields["ceiling_z"])
        drop = int(lower_sec.fields["floor_z"]) - plane
        z, zvel = 0, 0
        while z < drop:
            zvel += GRAVITY
            z += zvel >> 8
        drops.append((pair["link_id"], drop, max(0, ((zvel * zvel) >> 30) - FORGIVEN)))
        climbs.append((pair["link_id"], drop))
    harmful = [d for d in drops if d[2] > 0]
    climbable = [c for c in climbs if c[1] <= JUMP_RISE]
    row("no link drop injures the player",
        "impact damage 0 on every link (kFallDamageFloor forgives it)",
        "; ".join(f"link {i}: {d} units -> {dmg/16:.1f} HP" for i, d, dmg in drops),
        not harmful, "NBlood actor.cpp MoveDude + kDudeGravity")
    row("at least one link is climbable back out",
        f"a drop <= the {JUMP_RISE}-unit jump rise, so the sewer is not a trap",
        f"climbable links: {[c[0] for c in climbable]}",
        bool(climbable), "NBlood player.cpp gPostureDefaults normalJumpZ 0xbaaaa")

    row("ROR markers survive dbLoadMap",
        f"{len(markers)} link markers, none on statnum 10, all with XSprite",
        f"on statnum 10: {len(doomed)}; without XSprite: {len(without_xsprite)}",
        markers and not doomed and not without_xsprite,
        "NBlood db.cpp:680 PropagateMarkerReferences + warp.cpp warpInit")

    lines = [
        "# Plan conformance -- the classifier's reading vs. L1",
        "",
        "Standing per-iteration check (design-layers.md). Generated by",
        "`level/conformance.py` from the compiled skeleton.",
        "",
        "| metric | L1 declares | classifier reads | ok | note |",
        "|---|---|---|---|---|",
    ]
    for r in rows:
        mark = "**OK**" if r["pass"] else "**DRIFT**"
        lines.append(f"| {r['metric']} | {r['declared']} | {r['measured']} | "
                     f"{mark} | {r['note']} |")
    out = PROJECT / "reports" / "plan-conformance.md"
    out.write_text("\n".join(lines), encoding="utf-8")
    bad = [r for r in rows if not r["pass"]]
    print(f"{len(rows) - len(bad)}/{len(rows)} conformance rows ok")
    for r in bad:
        print("DRIFT:", r["metric"], "declared", r["declared"], "measured", r["measured"])
    print(f"wrote {out}")
    return 1 if bad else 0


if __name__ == "__main__":
    raise SystemExit(main())
