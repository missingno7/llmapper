"""Run the vector ConflictRegion solver over a folder of Build maps.

For every XY overlap, every candidate origin domain gets one analytic
ConflictRegion -- a real polygon from the target-local arrangement, not a
sampled grid.  The union over domains is the map verdict.

    python -m tools.vector_report maps/sector_overlap -o work/vector-report
"""
from __future__ import annotations

import argparse
import json
import sys
from collections import deque
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from tools.build2d_core import Build2DModel
from tools import vector_solver as vs

PW = 384.0


def reach(model, start):
    seen = {start}
    q = deque([start])
    while q:
        u = q.popleft()
        for v in model.portal_graph[u]:
            if v not in seen:
                seen.add(v)
                q.append(v)
    return seen


def solve_map(model, audit=0, progress=False):
    """Every overlap, every candidate origin: the analytic region for each."""
    found = []
    reach_cache = {}
    for i, ov in enumerate(model.overlaps):
        A, B = ov.sector_a, ov.sector_b
        origins = []
        for s in model.sectors:
            if s in (A, B):
                continue
            r = reach_cache.get(s)
            if r is None:
                r = reach_cache[s] = reach(model, s)
            if A in r and B in r:
                origins.append(s)
        if progress:
            print("  [%d/%d] %s: %d candidate origins"
                  % (i + 1, len(model.overlaps), ov.id, len(origins)),
                  flush=True)
        done = set()
        seen_clusters = set()
        for root in origins:
            if root in done:
                continue
            # Different roots in one component dissolve to the same domain;
            # solving it again would repeat the whole arrangement.
            key = frozenset(vs.nested_transparent_cluster(model, root, {A, B}))
            if key in seen_clusters:
                continue
            seen_clusters.add(key)
            try:
                res = vs.solve(model, ov, root_sector=root, audit_n=audit)
            except RuntimeError:
                continue          # this domain has no direct A and B apertures
            except Exception as exc:
                found.append({"overlap": ov.id, "root": root,
                              "error": "%s: %s" % (type(exc).__name__, exc)})
                continue
            done |= set(res["cluster"])
            region = res["unified_region"]
            if region.is_empty or region.area <= 1.0:
                continue
            found.append({
                "overlap": ov.id, "root": root,
                "cluster": sorted(res["cluster"]),
                "area": float(region.area),
                "area_player_widths2": float(region.area) / (PW * PW),
                "components": len(list(vs.iter_polygons(region))),
                "cells": len(res["cells"]),
                "bad_cells": len(res["bad_cells"]),
                "critical_lines": res["meta"]["critical_lines"],
                "mismatches": len(res["mismatches"]),
                "wkt": region.wkt,
                "per_sector": {k: float(v.area) for k, v in
                               res["per_sector"].items() if v.area > 1.0},
                # A representative point of the *union* can land on a cell
                # boundary where the predicate does not hold.  The witness has
                # to come from an actual bad cell, or it is not checkable.
                "witness": list(max(
                    res["bad_cells"], key=lambda c: c.area
                ).representative_point().coords)[0],
            })
    return found


def draw(model, found, path, out_dir):
    fig, ax = plt.subplots(figsize=(9, 9))
    for r in found:
        if "wkt" not in r:
            continue
        from shapely import wkt as _wkt
        for p in vs.iter_polygons(_wkt.loads(r["wkt"])):
            x, y = p.exterior.xy
            ax.fill([v / PW for v in x], [v / PW for v in y],
                    color="#8b3fd6", alpha=0.45, zorder=2)
    for ov in model.overlaps:
        for p in vs.iter_polygons(ov.geometry):
            x, y = p.exterior.xy
            ax.fill([v / PW for v in x], [v / PW for v in y],
                    color="#00b8c4", alpha=0.35, hatch="///", zorder=3)
    for sid, sec in model.sectors.items():
        for w in sec.walls:
            ax.plot([w.a[0] / PW, w.b[0] / PW], [w.a[1] / PW, w.b[1] / PW],
                    "-" if w.kind == "solid" else ":",
                    color="0.15" if w.kind == "solid" else "#cc4444",
                    lw=2.0 if w.kind == "solid" else 1.1, zorder=4)
        rp = sec.polygon.representative_point()
        ax.annotate(sid, (rp.x / PW, rp.y / PW), ha="center",
                    fontsize=10, color="0.35", zorder=5)
    for r in found:
        if "witness" in r:
            ax.plot(r["witness"][0] / PW, r["witness"][1] / PW, "x",
                    color="#d62728", ms=11, mew=2.4, zorder=6)
    verdict = "CONFLICT" if any("wkt" in r for r in found) else "clean"
    pairs = ", ".join(sorted({r["overlap"] for r in found if "wkt" in r})) or "-"
    ax.set_title("%s -- %s\nflagged: %s   (cyan = XY overlap, "
                 "purple = ConflictRegion, x = witness)"
                 % (path.name, verdict, pairs), fontsize=11)
    ax.set_aspect("equal")
    ax.invert_yaxis()
    ax.grid(alpha=0.12)
    ax.set_xlabel("player widths")
    fig.tight_layout()
    png = Path(out_dir) / (path.stem + ".png")
    fig.savefig(png, dpi=110)
    plt.close(fig)
    return png


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("target")
    ap.add_argument("-o", "--out", default="work/vector-report")
    ap.add_argument("--audit", type=int, default=0)
    ap.add_argument("--progress", action="store_true")
    a = ap.parse_args(argv)
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    t = Path(a.target)
    maps = sorted(t.glob("*.map")) if t.is_dir() else [t]
    maps = [p for p in maps if "ASAVE" not in p.name]
    summary = []
    for p in maps:
        model = Build2DModel.load(p)
        found = solve_map(model, audit=a.audit, progress=a.progress)
        png = draw(model, found, p, out)
        real = [r for r in found if "wkt" in r]
        errs = [r for r in found if "error" in r]
        summary.append({"map": p.name,
                        "verdict": "CONFLICT" if real else "clean",
                        "overlaps": len(model.overlaps),
                        "regions": real, "errors": errs,
                        "plan": str(png)})
        print("%-12s %-9s overlaps %-2d regions %d%s" % (
            p.name, summary[-1]["verdict"], len(model.overlaps), len(real),
            "  (%d errors)" % len(errs) if errs else ""))
        for r in real[:3]:
            print("        %s from %s: area %.1f pw2, %d component(s), "
                  "witness (%.0f, %.0f)" % (
                      r["overlap"], r["root"], r["area_player_widths2"],
                      r["components"], r["witness"][0], r["witness"][1]))
    (out / "summary.json").write_text(json.dumps(summary, indent=1))
    print("\nwrote %s" % out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
