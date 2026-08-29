"""Draw what the overlap validator found, so a mapper can check it by eye.

One plan per map: sector outlines, the XY overlap of each flagged pair, the
ConflictRegion the validator computed, and the witness cameras.

    python -m tools.overlap_report maps/sector_overlap -o work/overlap-report
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from tools.bunch_order import Map
from tools.overlap_validator import overlap_cells, validate

PW = 384


def draw(path, out_dir, step):
    m = Map(str(path))
    stats, results = validate(str(path), step=step)
    ov = overlap_cells(m)
    flagged = {(r["overlap"]["parent_a"], r["overlap"]["parent_b"])
               for r in results}

    fig, ax = plt.subplots(figsize=(9, 9))
    for si in range(m.n):
        for (_w, a, b, nxt, _c, _p2) in m.walls[si]:
            solid = nxt < 0
            ax.plot([a[0] / PW, b[0] / PW], [a[1] / PW, b[1] / PW],
                    "-" if solid else ":",
                    color="0.15" if solid else "0.65",
                    lw=2.0 if solid else 1.0, zorder=2)
        xs = [q[0] for e in m.edges[si] for q in e]
        ys = [q[1] for e in m.edges[si] for q in e]
        ax.annotate("s%d" % si, (sum(xs) / len(xs) / PW, sum(ys) / len(ys) / PW),
                    ha="center", fontsize=11, color="0.35", zorder=5)

    # every XY overlap, cyan; the flagged ones brighter
    for pr, cells in ov.items():
        hot = pr in flagged
        ax.scatter([q[0] / PW for q in cells], [q[1] / PW for q in cells],
                   s=14, marker="s",
                   color="#00b8c4" if hot else "#bfe9ec",
                   alpha=0.9 if hot else 0.5, zorder=3,
                   label=None)

    # the conflict region, purple
    for r in results:
        cells = r.get("region_cells") or []
        if cells:
            ax.scatter([c[0] / PW for c in cells], [c[1] / PW for c in cells],
                       s=max(4, (step / PW) ** 2 * 14), marker="s",
                       color="#8b3fd6", alpha=0.28, zorder=1)
        for w in r["witnesses"]:
            ax.plot(w["x"] / PW, w["y"] / PW, "x", color="#d62728",
                    ms=11, mew=2.4, zorder=6)

    h = m.disk.header.fields if hasattr(m.disk.header, "fields") else m.disk.header
    ax.plot(int(h["start_x"]) / PW, int(h["start_y"]) / PW, "*",
            color="green", ms=16, zorder=6)

    verdict = "CONFLICT" if results else "clean"
    pairs = ", ".join("%d/%d" % p for p in sorted(flagged)) or "-"
    ax.set_title("%s  -- %s\nflagged pairs: %s   (cyan = XY overlap, "
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
    return stats, results, png


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("target", help="a .map file or a directory of them")
    ap.add_argument("-o", "--out", default="work/overlap-report")
    ap.add_argument("--step", type=int, default=256)
    a = ap.parse_args(argv)
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    target = Path(a.target)
    maps = sorted(target.glob("*.map")) if target.is_dir() else [target]
    maps = [p for p in maps if "ASAVE" not in p.name]
    summary = []
    for p in maps:
        stats, results, png = draw(p, out, a.step)
        row = {
            "map": p.name,
            "verdict": "CONFLICT" if results else "clean",
            "sectors": stats["sectors"],
            "xy_overlaps": stats["overlaps"],
            "flagged": [[r["overlap"]["parent_a"], r["overlap"]["parent_b"]]
                        for r in results],
            "witnesses": [w for r in results for w in r["witnesses"][:3]],
            "plan": str(png),
        }
        summary.append(row)
        print("%-12s %-9s overlaps %-3d flagged %s" % (
            p.name, row["verdict"], stats["overlaps"], row["flagged"] or "-"))
        for w in row["witnesses"][:3]:
            print("        witness: sector %d at (%d, %d)"
                  % (w["sector"], w["x"], w["y"]))
    (out / "summary.json").write_text(json.dumps(summary, indent=1))
    print("\nwrote %s" % out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
