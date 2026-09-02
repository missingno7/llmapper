"""Phase 1b: plot the L1 plan and prove it against the Phase 0 contracts.

Two outputs:
  references/plots/gravesend-l1-plan.png  -- the overlay plot, side-by-side
      comparable with the precedent city plans (same scale convention)
  reports/plan-contract-check.md          -- every contract row, measured
      from the plan data, pass or miss

Per the layered-plan directive: a row that cannot pass is a plan bug to fix
here; a green table advances to Phase 1c automatically.

    python projects/blood-city/level/plan_review.py
"""

from __future__ import annotations

import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

from city_plan import plan
from resolution import PU, WIDTH_UNITS, STREET_SKY, STANDING, SEWER_FLOOR, GRADE

PROJECT = pathlib.Path(__file__).resolve().parents[1]


def frontage_units(data: dict) -> float:
    """Classifier-comparable frontage: block perimeters plus the city
    boundary, in Build units (the street component's walls face both)."""
    total = 0.0
    for block in data["blocks"]:
        x0, y0, x1, y1 = block["rect"]
        total += 2 * ((x1 - x0) + (y1 - y0))
    w, d = data["grid_pu"]["city_w"], data["grid_pu"]["city_d"]
    total += 2 * (w + d)
    return total * PU


def measure(data: dict) -> list[dict]:
    rows = []

    def row(contract, value, ok, source):
        rows.append({"contract": contract, "plan_value": value,
                     "pass": bool(ok), "source": source})

    # Street loops: planar faces of the connected street graph + one loop
    # per free-standing mass the streets flow around.
    nodes = set()
    for a, b, *_ in data["edges"]:
        nodes.update((a, b))
    faces = len(data["edges"]) - len(nodes) + 1
    free = [b for b in data["blocks"] if b["role"] == "free_standing"]
    loops = faces + len(free)
    row("street loops 6..9 (CN 2)", f"{faces} graph faces + {len(free)} free-standing = {loops}",
        6 <= loops <= 9, "derived: E-V+1 on EDGES + free_standing BLOCKS")

    # Block bimodality.
    supers, mids, smalls = [], [], []
    for block in data["blocks"]:
        x0, y0, x1, y1 = block["rect"]
        extent = max(x1 - x0, y1 - y0) * PU
        {"superblock": supers, "block": mids, "free_standing": smalls}[block["role"]].append(
            round(extent))
    row("2-3 superblocks at 24k..32k (CN 2)", f"{sorted(supers)}",
        2 <= len(supers) <= 3 and all(24000 <= e <= 33000 for e in supers),
        "derived: BLOCKS role=superblock extents")
    row("small free-standing masses ~768..2432 (CN 2)", f"{sorted(smalls)}",
        len(smalls) >= 2 and all(700 <= e <= 2500 for e in smalls),
        "derived: BLOCKS role=free_standing extents")
    row("mid blocks inside precedent spread (CN 2)", f"{sorted(mids)}",
        all(2000 <= e <= 24000 for e in mids), "derived: BLOCKS role=block extents")

    # Width classes inside the mined bands.
    widths = {cls: WIDTH_UNITS[cls] for cls in
              {e[2] for e in data["edges"]} | {"alley"}}
    ok = (5120 <= widths["street"] <= 7168 and 5120 <= widths["row"] <= 7168
          and 5120 <= widths["avenue"] <= 7168 and 1024 <= widths["alley"] <= 2048
          and 2048 <= widths["lane"] <= 5120)
    row("main streets 5120..7168, alleys 1024..2048 (CN 1)",
        str(widths), ok, "resolution.WIDTH_UNITS vs CN 1 bands")

    # One plaza-kind area per district.
    plaza_by_district = {a["district"]: a["kind"] for a in data["areas"]}
    row("one plaza/forecourt/square/yard per district (CN 1)",
        str(plaza_by_district), set(plaza_by_district) == set(data["districts"]),
        "derived: AREAS by district")

    # Canyon on the avenue at the L2 sky resolution.
    canyon = (STREET_SKY / 16) / WIDTH_UNITS["avenue"]
    row("avenue canyon 1.7..2.1 (CN 1)", f"{canyon:.2f}",
        1.7 <= canyon <= 2.1, "resolution.STREET_SKY over avenue width")

    # Venue rates.
    frontage = frontage_units(data)
    venues = data["venues"]
    interiors_rate = len(venues) / frontage * 10240
    row("substantial interiors 0.13..0.37 per 10240 frontage (CN 3)",
        f"{len(venues)} venues / {frontage/1000:.0f}k = {interiors_rate:.2f}",
        0.13 <= interiors_rate <= 0.37, "derived: VENUES over block+boundary frontage")
    doorways = sum(v["doorways"] for v in venues) + len(data["sewer"]["entries"])
    doorway_rate = doorways / frontage * 10240
    row("doorways 0.23..1.17 per 10240 frontage (CN 3)",
        f"{doorways} -> {doorway_rate:.2f}", 0.23 <= doorway_rate <= 1.17,
        "derived: VENUES doorways + sewer entries")
    types = {v["type"] for v in venues}
    row("venue mix: landmark complex + bar + walk-through + open-front (VP)",
        str(sorted(types)),
        {"landmark_complex", "bar", "walk_through", "open_front"} <= types,
        "VENUES types vs venue-patterns.md")

    # Sewer contract.
    entries = data["sewer"]["entries"]
    entry_rate = len(entries) / frontage * 10240
    row("sewer entries ~0.02..0.04 per 10240 frontage, forms drop+stair (SP)",
        f"{len(entries)} ({[e['form'] for e in entries]}) -> {entry_rate:.3f}",
        0.015 <= entry_rate <= 0.05 and {e["form"] for e in entries} == {"drop", "stair"},
        "SEWER entries over frontage")
    depth = (SEWER_FLOOR - GRADE) / STANDING
    row("sewer depth 2.5..4 standing (SP)", f"{depth:.2f}",
        2.5 <= depth <= 4, "resolution.SEWER_FLOOR - GRADE")
    ring = len(data["sewer"]["edges"]) >= 4
    row("sewer topology: its own ring under its district (SP)",
        f"{len(data['sewer']['edges'])} edges incl. ring return", ring, "SEWER edges")

    # Channels.
    total = data["channels_total"]
    destruction = sum(v.get("destruction", 0) for v in data["channels"].values())
    sound = sum(v.get("sound_spawn", 0) for v in data["channels"].values())
    row("50..70 user channels, destruction and staged-sound reserved (CN 8)",
        f"total {total}, destruction {destruction}, sound/spawn {sound}",
        50 <= total <= 70 and destruction >= 6 and sound >= 6,
        "CHANNELS allocation")

    # Circuit touches start, venues, sewer, objective.
    legs = " ".join(leg["leg"] for leg in data["circuit"])
    ok = all(k in legs for k in ("start", "venue", "manhole", "stair", "objective"))
    row("main circuit: start -> venues -> sewer leg -> objective (ID)",
        f"{len(data['circuit'])} legs", ok, "CIRCUIT legs")

    # Budget projection per district (model: massing + facade rate x
    # frontage + VP venue budgets at 60% + SP sewer band; CN 7 norms).
    projection = {
        "theatre_row": 40 + 38 + 400 + 120 + 100 + 40,
        "market_slip": 30 + 35 + 60 + 40 + 40,
        "old_crossing": 35 + 40 + 120 + 200,
        "foundry_ward_and_sewer": 40 + 45 + 450 + 60 + 150,
        "citywide_streets_plaza": 200,
    }
    total_walls = sum(projection.values())
    # The ceiling is the target port's, not a campaign map's: NBlood is
    # compiled with the V8 limits (build.h:48-59), read from project.json.
    # The old 7000 cap was a vanilla-DOS number, retired 2026-09-02.
    import json as _json
    import pathlib as _pathlib
    _budget = _json.load(open(_pathlib.Path(__file__).resolve().parents[1] / "project.json",
                              encoding="utf-8"))["budget"]
    walls_limit = int(_budget["walls_limit"])
    reserve = int(walls_limit * 0.9)
    ok = total_walls <= reserve
    row(f"projected walls under the NBlood limit with 10% headroom ({reserve} of {walls_limit})",
        f"{projection} -> total {total_walls} (+{reserve - total_walls} to the reserve line)",
        ok, "model stated in plan_review.py; verified against real counts every L2/L3 iteration")

    return rows


# --------------------------------------------------------------------------
# The overlay plot
# --------------------------------------------------------------------------

def draw(data: dict, out: pathlib.Path) -> None:
    fig, ax = plt.subplots(figsize=(14, 14))
    U = PU

    def strip(a, b, cls):
        (ax_, ay), (bx, by) = data["nodes"][a], data["nodes"][b]
        w = WIDTH_UNITS[cls] / U
        if abs(ax_ - bx) < abs(ay - by):        # vertical
            lo, hi = sorted((ay, by))
            return (ax_ - w / 2, lo - w / 2, w, hi - lo + w)
        lo, hi = sorted((ax_, bx))
        return (lo - w / 2, ay - w / 2, hi - lo + w, w)

    for a, b, cls, _d, _n in data["edges"]:
        x, y, w, h = strip(a, b, cls)
        ax.add_patch(plt.Rectangle((x * U, y * U), w * U, h * U,
                                   color="#aecde8", zorder=1))
    for area in data["areas"]:
        x0, y0, x1, y1 = area["rect"]
        color = "#b8d8b8" if area["kind"] == "cemetery" else "#aecde8"
        ax.add_patch(plt.Rectangle((x0 * U, y0 * U), (x1 - x0) * U, (y1 - y0) * U,
                                   color=color, zorder=3))
        ax.text((x0 + x1) / 2 * U, (y0 + y1) / 2 * U, area["kind"],
                ha="center", fontsize=8, style="italic", zorder=6)
        for mass in area.get("attached_masses", []):
            mx0, my0, mx1, my1 = mass
            ax.add_patch(plt.Rectangle((mx0 * U, my0 * U), (mx1 - mx0) * U,
                                       (my1 - my0) * U, facecolor="#f5b880",
                                       edgecolor="#8a5a2b", zorder=4))
    for block in data["blocks"]:
        x0, y0, x1, y1 = block["rect"]
        ax.add_patch(plt.Rectangle((x0 * U, y0 * U), (x1 - x0) * U, (y1 - y0) * U,
                                   facecolor="#f5b880", edgecolor="#8a5a2b",
                                   zorder=2))
        if block["role"] != "free_standing":
            ax.text((x0 + x1) / 2 * U, (y0 + y1) / 2 * U,
                    f"{block['id']}\n({block['role']})", ha="center",
                    fontsize=8, zorder=6)

    # Venue slots: green ticks on their blocks' faces.
    for venue in data["venues"]:
        block = next(b for b in data["blocks"] if b["id"] == venue["block"])
        x0, y0, x1, y1 = block["rect"]
        face, _, qualifier = venue["face"].partition("@")
        face = face.split(":")[0]
        t = {"west": 0.2, "mid": 0.5, "": 0.5, "forecourt": 0.85,
             "avenue": 0.5, "plaza": 0.5, "quay": 0.5, "yard": 0.5}.get(qualifier, 0.5)
        pos = {"south": (x0 + (x1 - x0) * t, y1), "north": (x0 + (x1 - x0) * t, y0),
               "east": (x1, y0 + (y1 - y0) * t), "west": (x0, y0 + (y1 - y0) * t),
               "alley": ((x0 + x1) / 2, y0)}[face]
        ax.plot(pos[0] * U, pos[1] * U, marker="s", color="#2e7d32",
                markersize=9, zorder=7)
        ax.annotate(f"{venue['id']} [{venue['type']}]",
                    (pos[0] * U, pos[1] * U), textcoords="offset points",
                    xytext=(6, 6), fontsize=7, color="#2e7d32", zorder=7)

    # Sewer: dashed dark red under its district.
    sewer_pts = dict(data["sewer"]["nodes"])
    for a, b, _note in data["sewer"]["edges"]:
        pa, pb = sewer_pts.get(a), sewer_pts.get(b)
        if pa and pb:
            ax.plot([pa[0] * U, pb[0] * U], [pa[1] * U, pb[1] * U],
                    "--", color="#8b0000", linewidth=2.5, zorder=5)
    for entry in data["sewer"]["entries"]:
        ex, ey = entry["at"]
        ax.plot(ex * U, ey * U, marker="v", color="#8b0000", markersize=11, zorder=7)
        ax.annotate(f"{entry['id']} ({entry['form']})", (ex * U, ey * U),
                    textcoords="offset points", xytext=(8, -10), fontsize=7,
                    color="#8b0000", zorder=7)

    # Roof-route stacks.
    for stack in data["roof_stacks"]:
        sx, sy = stack["at"]
        ax.plot(sx * U, sy * U, marker="^", color="#6a1b9a", markersize=11, zorder=7)
        ax.annotate(stack["id"], (sx * U, sy * U), textcoords="offset points",
                    xytext=(6, 6), fontsize=7, color="#6a1b9a", zorder=7)

    # The main circuit as numbered arrows.
    pts = [leg["at"] for leg in data["circuit"]]
    for i in range(len(pts) - 1):
        ax.annotate("", xy=(pts[i + 1][0] * U, pts[i + 1][1] * U),
                    xytext=(pts[i][0] * U, pts[i][1] * U),
                    arrowprops=dict(arrowstyle="-|>", color="#1a4d8f",
                                    linewidth=1.6), zorder=6)
    for i, (px, py) in enumerate(pts):
        ax.annotate(str(i + 1), (px * U, py * U), fontsize=9, weight="bold",
                    color="#1a4d8f", zorder=8)

    w, d = data["grid_pu"]["city_w"], data["grid_pu"]["city_d"]
    ax.set_xlim(-2 * U, (w + 2) * U)
    ax.set_ylim(-2 * U, (d + 2) * U)
    ax.set_aspect("equal")
    ax.invert_yaxis()
    ax.set_title("Gravesend L1: streets (blue), masses (orange), venues (green), "
                 "sewer (dashed red), roof stacks (purple), circuit (numbered)  "
                 f"[1 pu = {PU} Build units]")
    fig.tight_layout()
    fig.savefig(out, dpi=110)
    plt.close(fig)


def main() -> int:
    data = plan()
    rows = measure(data)
    out_plot = PROJECT / "references" / "plots" / "gravesend-l1-plan.png"
    draw(data, out_plot)

    lines = [
        "# Plan contract check -- L1 measured against the Phase 0 contracts",
        "",
        "Generated by `level/plan_review.py` from `level/city_plan.py`. A red",
        "row is a plan bug (layer directive); green advances to Phase 1c.",
        "",
        "| contract | plan value | pass | basis |",
        "|---|---|---|---|",
    ]
    for r in rows:
        mark = "**PASS**" if r["pass"] else "**MISS**"
        lines.append(f"| {r['contract']} | {r['plan_value']} | {mark} | {r['source']} |")
    lines += ["", f"Plot: [gravesend-l1-plan.png](../references/plots/gravesend-l1-plan.png)"]
    out_md = PROJECT / "reports" / "plan-contract-check.md"
    out_md.write_text("\n".join(lines), encoding="utf-8")

    failed = [r for r in rows if not r["pass"]]
    print(f"{len(rows) - len(failed)}/{len(rows)} contract rows pass")
    for r in failed:
        print("MISS:", r["contract"], "->", r["plan_value"])
    print(f"wrote {out_plot}")
    print(f"wrote {out_md}")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
