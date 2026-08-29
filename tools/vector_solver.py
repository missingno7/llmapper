#!/usr/bin/env python3
"""
transparent_domain_vector_solver.py

Finalized experiment for the current simplified XY model:

SECTOR TOPOLOGY PHASE
---------------------
Real sectors and red portal walls remain fully meaningful.

SHAPE PHASE
-----------
For a chosen origin sector, recursively collect nested red-wall portal sectors
that lie geometrically inside the origin shell.  Dissolve those sectors into
ONE transparent visibility domain.

Internal red boundaries disappear completely from the shape calculation.
Only:
  - white/solid boundaries,
  - the actual branch apertures leading toward the overlap,
  - and overlap/branch geometry
may shape the ConflictRegion.

The solver computes ONE vector ConflictRegion over the full transparent domain.

Only after that, the region is attributed back to real sectors with:

    G_sector = G_domain ∩ sector_polygon

Thus a single continuous glitch region may cross MAIN -> I1 -> I2 even though
those remain distinct Build sectors topologically.

This script reuses the point-classification oracle from
build2d_vector_conflict_solver.py, but the output geometry is created from a
target-local analytic arrangement, not from an XY sample grid.
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import math
import sys
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Set, Tuple

from shapely.geometry import (
    GeometryCollection,
    LineString,
    MultiPolygon,
    Point,
    Polygon,
    mapping,
)
from shapely.ops import polygonize, unary_union

Vec2 = Tuple[float, float]
EPS = 1e-8


# ---------------------------------------------------------------------------
# Core loading
# ---------------------------------------------------------------------------

def load_core(path: Path):
    spec = importlib.util.spec_from_file_location("build2d_core_domain", path)
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod


# ---------------------------------------------------------------------------
# Geometry helpers
# ---------------------------------------------------------------------------

def polygon_vertices(poly: Polygon) -> List[Vec2]:
    out = [(float(x), float(y)) for x, y in list(poly.exterior.coords)[:-1]]
    for ring in poly.interiors:
        out.extend(
            (float(x), float(y))
            for x, y in list(ring.coords)[:-1]
        )
    return out


def ring_vertices(ring) -> List[Vec2]:
    return [(float(x), float(y)) for x, y in list(ring.coords)[:-1]]


def canonical_line(p: Vec2, q: Vec2):
    dx = q[0] - p[0]
    dy = q[1] - p[1]
    n = math.hypot(dx, dy)
    if n < 1e-10:
        return None

    A = dy / n
    B = -dx / n
    C = -(A * p[0] + B * p[1])

    if A < -1e-12 or (abs(A) <= 1e-12 and B < -1e-12):
        A, B, C = -A, -B, -C

    return (round(A, 11), round(B, 11), round(C, 11))


def infinite_line(key, bounds):
    A, B, C = key
    minx, miny, maxx, maxy = bounds
    diag = max(1.0, math.hypot(maxx - minx, maxy - miny))
    L = diag * 100.0 + 100.0

    p0 = (-A * C, -B * C)
    d = (-B, A)

    return LineString([
        (p0[0] - d[0] * L, p0[1] - d[1] * L),
        (p0[0] + d[0] * L, p0[1] + d[1] * L),
    ])


def iter_polygons(geom):
    if geom.is_empty:
        return
    if geom.geom_type == "Polygon":
        yield geom
    elif geom.geom_type == "MultiPolygon":
        yield from geom.geoms
    elif hasattr(geom, "geoms"):
        for g in geom.geoms:
            if g.geom_type == "Polygon":
                yield g


def polygonal_only(geom):
    polys = list(iter_polygons(geom))
    if not polys:
        return GeometryCollection()
    return unary_union(polys)


# ---------------------------------------------------------------------------
# Transparent visibility domain
# ---------------------------------------------------------------------------

def _overlap_partners(model):
    """sector -> the sectors it shares ground with, computed once per map."""
    cached = getattr(model, "_ov_partners", None)
    if cached is None:
        from collections import defaultdict
        cached = defaultdict(set)
        for ov in model.overlaps:
            cached[ov.sector_a].add(ov.sector_b)
            cached[ov.sector_b].add(ov.sector_a)
        for sid in model.sectors:
            cached.setdefault(sid, set())
        model._ov_partners = cached
    return cached


def nested_transparent_cluster(
    model,
    root_sector: str,
    protected: Set[str],
) -> Set[str]:
    """Collect portal-connected sectors that are transparent for XY visibility.

    A red portal does not occlude, so every sector reachable from the root
    through portals -- without passing through an overlap parent -- is part of
    one visibility space, and the union of their polygons keeps exactly the
    solid walls as its boundary.

    The earlier form only took sectors geometrically nested inside the root
    shell.  That is right for a MAIN/I1/I2 stack but leaves a branch that sits
    two portals away with no direct aperture, so the solver refused the domain
    and the map came back clean; bad_1 and bad_7 are the regression tests.

    Two sectors that overlap each other must never be dissolved together: the
    union would erase the very geometry under test, so such a neighbour is left
    out of the cluster.
    """
    cluster = {root_sector}
    queue = [root_sector]

    while queue:
        sid = queue.pop(0)

        # Sorted, and a FIFO queue: portal_graph holds sets, and iterating one
        # follows Python's per-process string hashing, so the cluster -- and
        # with it the verdict -- used to differ between runs of the same map.
        for neighbour in sorted(model.portal_graph[sid]):
            if neighbour in cluster or neighbour in protected:
                continue

            # Whether two sectors share ground is a property of the map, not
            # of this walk: computing it with shapely per neighbour per cluster
            # member made the cluster build quadratic and dominated BB4.
            if _overlap_partners(model)[neighbour] & cluster:
                continue

            cluster.add(neighbour)
            queue.append(neighbour)

    return cluster


def dissolved_visibility_domain(model, cluster: Set[str]):
    """
    Unioning the sector polygons removes all shared internal red boundaries.
    Solid holes survive naturally as holes in the union.
    """
    return polygonal_only(
        unary_union([model.sectors[s].polygon for s in sorted(cluster)])
    )


def domain_solid_vertices(domain) -> Set[Vec2]:
    """
    Interior rings of the dissolved union are the remaining true occluders.
    The former red portal holes have vanished.

    Only vertices that are reflex as seen from the free space matter: a corner
    the free space wraps around is where a silhouette can pivot, while a corner
    pointing into the obstacle is never a shadow boundary.  Dropping the rest
    cuts the critical-line count, and the cell count goes with its square.
    """
    out: Set[Vec2] = set()

    for poly in iter_polygons(domain):
        for ring in poly.interiors:
            pts = ring_vertices(ring)
            if len(pts) < 3:
                out.update(pts)
                continue
            signed = 0.0
            for i, a in enumerate(pts):
                b = pts[(i + 1) % len(pts)]
                signed += a[0] * b[1] - b[0] * a[1]
            ccw = signed > 0
            for i, b in enumerate(pts):
                a = pts[i - 1]
                c = pts[(i + 1) % len(pts)]
                cr = ((b[0] - a[0]) * (c[1] - b[1])
                      - (b[1] - a[1]) * (c[0] - b[0]))
                if abs(cr) < 1e-9 or ((cr > 0) == ccw):
                    out.add(b)

    return out


def sector_for_point(model, cluster: Set[str], p: Point) -> Optional[str]:
    """
    Resolve actual Build sector identity for oracle classification.

    The shapes in the cluster are disjoint except at portal boundaries.
    Representative points are interior, so one should contain the point.
    Prefer the smallest containing polygon in the unlikely event of overlap.
    """
    hits = []
    for sid in cluster:
        poly = model.sectors[sid].polygon
        if poly.contains(p):
            hits.append((poly.area, sid))

    if not hits:
        return None

    hits.sort()
    return hits[0][1]


# ---------------------------------------------------------------------------
# Target-local constraints
# ---------------------------------------------------------------------------

def direct_domain_portal_endpoints(model, cluster: Set[str], parent: str):
    """
    Find portal walls leaving any sector in the transparent domain directly
    into the requested overlap parent branch.
    """
    pts = set()

    for sid in cluster:
        for w in model.sectors[sid].walls:
            if w.kind == "portal" and w.neighbor == parent:
                pts.add(w.a)
                pts.add(w.b)

    return sorted(pts)


def reflex_vertices(poly: Polygon) -> Set[Vec2]:
    pts = [(float(x), float(y)) for x, y in list(poly.exterior.coords)[:-1]]
    if len(pts) < 3:
        return set()

    signed = 0.0
    for i, p in enumerate(pts):
        q = pts[(i + 1) % len(pts)]
        signed += p[0] * q[1] - q[0] * p[1]
    ccw = signed > 0

    out = set()
    for i, b in enumerate(pts):
        a = pts[i - 1]
        c = pts[(i + 1) % len(pts)]

        v1 = (b[0] - a[0], b[1] - a[1])
        v2 = (c[0] - b[0], c[1] - b[1])
        cr = v1[0] * v2[1] - v1[1] * v2[0]

        if (ccw and cr < -1e-10) or ((not ccw) and cr > 1e-10):
            out.add(b)

    return out


def branch_constraint_vertices(model, parent: str) -> Set[Vec2]:
    poly = model.sectors[parent].polygon
    out = reflex_vertices(poly)

    # White holes inside the branch are real occluders.
    for ring in poly.interiors:
        out.update(ring_vertices(ring))

    return out


def _solid_segments(model):
    """Every one-sided wall in the map, cached: the only real occluders."""
    cached = getattr(model, "_solid_segs", None)
    if cached is None:
        cached = [(w.a, w.b) for sec in model.sectors.values()
                  for w in sec.walls if w.kind == "solid"]
        model._solid_segs = cached
    return cached


def _straddles(a, b, c, d):
    def side(p, q, r):
        v = (q[0]-p[0])*(r[1]-p[1]) - (q[1]-p[1])*(r[0]-p[0])
        return 0 if abs(v) < 1e-9 else (1 if v > 0 else -1)
    return (side(a, b, c) * side(a, b, d) < 0 and
            side(c, d, a) * side(c, d, b) < 0)


def _sees(model, v, t, trim=1e-3):
    """Is the straight segment v->t free of solid walls?

    A silhouette line only bounds anything where the blocker actually occludes
    the target, and occlusion inside one continuous space is a straight line --
    unlike reachability, which bends through portal chains.  Ends are trimmed
    so a wall meeting the segment at its own endpoint does not count.
    """
    dx, dy = t[0] - v[0], t[1] - v[1]
    a = (v[0] + dx * trim, v[1] + dy * trim)
    b = (t[0] - dx * trim, t[1] - dy * trim)
    for (c, d) in _solid_segments(model):
        if _straddles(a, b, c, d):
            return False
    return True


def target_local_lines(
    model,
    overlap,
    cluster: Set[str],
    domain,
):
    A = overlap.sector_a
    B = overlap.sector_b

    PA = direct_domain_portal_endpoints(model, cluster, A)
    PB = direct_domain_portal_endpoints(model, cluster, B)

    if len(PA) < 2 or len(PB) < 2:
        raise RuntimeError(
            "Concrete direct-branch experiment requires at least one domain->A "
            "and one domain->B portal aperture."
        )

    O = set(polygon_vertices(overlap.geometry))
    blockers = domain_solid_vertices(domain)

    branchA = branch_constraint_vertices(model, A)
    branchB = branch_constraint_vertices(model, B)

    branchA_reflex = reflex_vertices(model.sectors[A].polygon)
    branchB_reflex = reflex_vertices(model.sectors[B].polygon)

    keys = {}

    dropped = [0]

    def add(p, q, reason):
        if not _sees(model, p, q):
            dropped[0] += 1
            return
        key = canonical_line(p, q)
        if key is not None:
            keys[key] = reason

    # Overlap <-> exit apertures: basic clean view cones.
    for o in O:
        for p in PA:
            add(o, p, "overlap<->portalA")
        for p in PB:
            add(o, p, "overlap<->portalB")

    # White occluders inside the unified transparent domain.
    for v in blockers:
        for p in PA:
            add(v, p, "domain blocker<->portalA")
        for p in PB:
            add(v, p, "domain blocker<->portalB")
        for o in O:
            add(v, o, "domain blocker<->overlap")

    # Constraints inside A/B after the rays leave the domain.
    for v in branchA:
        for p in PA:
            add(v, p, "A geometry<->portalA")
        for o in O:
            add(v, o, "A geometry<->overlap")

    for v in branchB:
        for p in PB:
            add(v, p, "B geometry<->portalB")
        for o in O:
            add(v, o, "B geometry<->overlap")

    # Mixed silhouette transitions discovered by the previous MAIN experiment.
    for v in blockers:
        for q in branchA_reflex:
            add(v, q, "domain blocker<->A reflex")
        for q in branchB_reflex:
            add(v, q, "domain blocker<->B reflex")

    lines = []
    reason_counts: Dict[str, int] = {}

    for key, reason in keys.items():
        ln = infinite_line(key, domain.bounds)
        if ln.intersects(domain):
            lines.append(ln)
            reason_counts[reason] = reason_counts.get(reason, 0) + 1

    meta = {
        "transparent_cluster": sorted(cluster),
        "domain_area": float(domain.area),
        "domain_solid_occluder_vertices": len(blockers),
        "portalA_endpoints": PA,
        "portalB_endpoints": PB,
        "overlap_vertices": len(O),
        "branchA_constraint_vertices": len(branchA),
        "branchB_constraint_vertices": len(branchB),
        "critical_lines": len(lines),
        "pairs_dropped_unseen": dropped[0],
        "line_reasons": reason_counts,
    }

    return lines, meta


# ---------------------------------------------------------------------------
# Vector arrangement over the full transparent domain
# ---------------------------------------------------------------------------

def arrangement_cells(domain, lines: List[LineString]) -> List[Polygon]:
    pieces = [domain.boundary]

    for ln in lines:
        inter = ln.intersection(domain)

        if inter.is_empty:
            continue

        if inter.geom_type == "LineString":
            pieces.append(inter)
        elif inter.geom_type == "MultiLineString":
            pieces.extend(inter.geoms)
        elif hasattr(inter, "geoms"):
            pieces.extend(
                g for g in inter.geoms if g.geom_type == "LineString"
            )

    noded = unary_union(pieces)
    raw = list(polygonize(noded))

    cells: List[Polygon] = []

    for c in raw:
        rp = c.representative_point()

        if not domain.contains(rp):
            continue

        clipped = c.intersection(domain)

        for p in iter_polygons(clipped):
            if p.area > 1e-10:
                cells.append(p)

    return cells


def deterministic_audit_points(poly: Polygon, n: int):
    if n <= 0:
        return []

    rp = poly.representative_point()
    base = (rp.x, rp.y)
    vs = list(poly.exterior.coords)[:-1]

    out = []

    for i in range(min(n, len(vs))):
        vx, vy = vs[(i * 7) % len(vs)]
        q = (
            0.88 * base[0] + 0.12 * vx,
            0.88 * base[1] + 0.12 * vy,
        )

        if poly.contains(Point(*q)):
            out.append(q)

    return out


def solve(
    model,
    overlap,
    root_sector: str,
    audit_n: int,
):
    protected = {overlap.sector_a, overlap.sector_b}

    cluster = nested_transparent_cluster(
        model,
        root_sector,
        protected=protected,
    )

    domain = dissolved_visibility_domain(model, cluster)

    lines, meta = target_local_lines(
        model,
        overlap,
        cluster,
        domain,
    )

    cells = arrangement_cells(domain, lines)

    bad = []
    mismatches = []

    for idx, cell in enumerate(cells):
        # A representative point can land a few nanometres from the cell
        # edge, where the ray classification flips on rounding alone.
        # Shrinking the cell by one Build unit -- 1/384 of a player width,
        # far below any real feature -- puts the probe genuinely inside.
        # good_5 s3__s4 was such a sliver: 1 bad cell of 83, 3e-9 out.
        probe = cell.buffer(-1.0)
        rp = (probe if not probe.is_empty else cell).representative_point()
        start_sector = sector_for_point(model, cluster, rp)

        if start_sector is None:
            continue

        expected, _, _ = model.classify_point(
            start_sector,
            (rp.x, rp.y),
            overlap,
        )

        for q in deterministic_audit_points(cell, audit_n):
            qpoint = Point(*q)
            qsector = sector_for_point(model, cluster, qpoint)

            if qsector is None:
                continue

            actual, _, _ = model.classify_point(
                qsector,
                q,
                overlap,
            )

            if actual != expected:
                mismatches.append({
                    "cell": idx,
                    "representative_sector": start_sector,
                    "representative": [rp.x, rp.y],
                    "counterexample_sector": qsector,
                    "counterexample": [q[0], q[1]],
                    "expected": expected,
                    "actual": actual,
                })
                break

        if expected:
            bad.append(cell)

    unified = polygonal_only(
        unary_union(bad).intersection(domain)
        if bad
        else GeometryCollection()
    )

    # Only now restore real sector attribution.
    per_sector = {}
    for sid in sorted(cluster):
        piece = polygonal_only(
            unified.intersection(model.sectors[sid].polygon)
        )
        per_sector[sid] = piece

    return {
        "cluster": cluster,
        "domain": domain,
        "unified_region": unified,
        "per_sector": per_sector,
        "cells": cells,
        "bad_cells": bad,
        "mismatches": mismatches,
        "meta": meta,
    }


# ---------------------------------------------------------------------------
# Rendering / output
# ---------------------------------------------------------------------------

def render(
    model,
    overlap,
    root_sector: str,
    result,
    out_png: Path,
    out_svg: Path,
):
    import matplotlib.pyplot as plt

    fig, ax = plt.subplots(figsize=(10, 10))
    fig.patch.set_facecolor("#111111")
    ax.set_facecolor("#111111")

    # Unified region FIRST: draw over the entire dissolved domain so it visibly
    # crosses former MAIN/I1/I2 red boundaries.
    for p in iter_polygons(result["unified_region"]):
        x, y = p.exterior.xy
        ax.fill(
            x,
            y,
            color="#9b59b6",
            alpha=0.68,
            zorder=2,
        )

    # Target overlap.
    for p in iter_polygons(overlap.geometry):
        x, y = p.exterior.xy
        ax.fill(
            x,
            y,
            color="#00bcd4",
            alpha=0.30,
            hatch="////",
            zorder=3,
        )

    # Walls remain visible on top only as a map reference.
    for sid, sec in model.sectors.items():
        for w in sec.walls:
            ax.plot(
                [w.a[0], w.b[0]],
                [w.a[1], w.b[1]],
                color=("red" if w.kind == "portal" else "white"),
                linewidth=(2.7 if w.kind == "portal" else 1.6),
                alpha=(0.85 if w.kind == "portal" else 1.0),
                zorder=4,
            )

    # Label the transparent cluster.
    for sid in sorted(result["cluster"]):
        rp = model.sectors[sid].polygon.representative_point()
        ax.text(
            rp.x,
            rp.y,
            sid,
            color="white",
            fontsize=10,
            fontweight="bold",
            ha="center",
            va="center",
            zorder=5,
        )

    bounds = [s.polygon.bounds for s in model.sectors.values()]
    ax.set_xlim(min(b[0] for b in bounds) - 1, max(b[2] for b in bounds) + 1)
    ax.set_ylim(min(b[1] for b in bounds) - 1, max(b[3] for b in bounds) + 1)

    ax.set_aspect("equal")
    ax.tick_params(colors="white")
    ax.set_title(
        f"Unified transparent-domain ConflictRegion — root {root_sector}\n"
        f"purple crosses internal red sectors; red walls are sector boundaries only",
        color="white",
        fontsize=13,
    )

    handles = [
        plt.Line2D(
            [0], [0], color="#9b59b6", lw=9,
            label="one unified ConflictRegion"
        ),
        plt.Line2D(
            [0], [0], color="#00bcd4", lw=9,
            label=f"Overlap {overlap.id}"
        ),
        plt.Line2D(
            [0], [0], color="red", lw=3,
            label="internal portal / sector boundary"
        ),
        plt.Line2D(
            [0], [0], color="white", lw=2,
            label="solid occluder"
        ),
    ]

    ax.legend(
        handles=handles,
        loc="upper left",
        facecolor="#222222",
        labelcolor="white",
    )

    fig.tight_layout()

    fig.savefig(
        out_png,
        dpi=190,
        facecolor=fig.get_facecolor(),
    )
    fig.savefig(
        out_svg,
        format="svg",
        facecolor=fig.get_facecolor(),
        bbox_inches="tight",
    )
    plt.close(fig)


def write_geojson(path: Path, overlap, result):
    features = []

    features.append({
        "type": "Feature",
        "properties": {
            "kind": "unified_conflict_region",
            "overlap": overlap.id,
            "area": float(result["unified_region"].area),
        },
        "geometry": mapping(result["unified_region"]),
    })

    for sid, geom in result["per_sector"].items():
        features.append({
            "type": "Feature",
            "properties": {
                "kind": "sector_attribution",
                "sector": sid,
                "overlap": overlap.id,
                "area": float(geom.area),
            },
            "geometry": mapping(geom),
        })

    path.write_text(
        json.dumps(
            {
                "type": "FeatureCollection",
                "features": features,
            },
            indent=2,
        ),
        encoding="utf-8",
    )


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("map_json", type=Path)
    ap.add_argument("--core", type=Path, required=True)
    ap.add_argument("--root", default="MAIN")
    ap.add_argument("--overlap", default="A__B")
    ap.add_argument("--audit", type=int, default=3)
    ap.add_argument(
        "--out-dir",
        type=Path,
        default=Path("transparent_domain_out"),
    )
    args = ap.parse_args()

    core = load_core(args.core)
    model = core.Build2DModel.load(args.map_json)
    overlap = model.overlap_by_id[args.overlap]

    args.out_dir.mkdir(parents=True, exist_ok=True)

    result = solve(
        model,
        overlap,
        root_sector=args.root,
        audit_n=args.audit,
    )

    unified = result["unified_region"]

    print("root sector:", args.root)
    print("overlap:", overlap.id)
    print("transparent cluster:", sorted(result["cluster"]))
    print("domain area:", round(result["domain"].area, 9))
    print(
        "remaining solid blocker vertices:",
        result["meta"]["domain_solid_occluder_vertices"],
    )
    print("critical lines:", result["meta"]["critical_lines"])
    print("arrangement cells:", len(result["cells"]))
    print("bad cells:", len(result["bad_cells"]))
    print("unified region type:", unified.geom_type)
    print("unified region area:", round(unified.area, 9))
    print("unified components:", len(list(iter_polygons(unified))))
    print("audit mismatches:", len(result["mismatches"]))

    print()
    print("sector attribution:")
    for sid, geom in result["per_sector"].items():
        print(f"  {sid}: area={geom.area:.9f}")

    attributed_sum = sum(
        geom.area for geom in result["per_sector"].values()
    )
    print("sum attributed area:", round(attributed_sum, 9))
    print(
        "unified-attributed delta:",
        round(unified.area - attributed_sum, 12),
    )

    report = {
        "root_sector": args.root,
        "overlap": overlap.id,
        "transparent_cluster": sorted(result["cluster"]),
        "domain": {
            "geometry_type": result["domain"].geom_type,
            "area": float(result["domain"].area),
            "wkt": result["domain"].wkt,
        },
        "meta": result["meta"],
        "arrangement_cells": len(result["cells"]),
        "bad_cells": len(result["bad_cells"]),
        "unified_region": {
            "geometry_type": unified.geom_type,
            "area": float(unified.area),
            "components": len(list(iter_polygons(unified))),
            "wkt": unified.wkt,
        },
        "sector_attribution": {
            sid: {
                "geometry_type": geom.geom_type,
                "area": float(geom.area),
                "wkt": geom.wkt,
            }
            for sid, geom in result["per_sector"].items()
        },
        "attributed_area_sum": float(attributed_sum),
        "unified_minus_attributed": float(
            unified.area - attributed_sum
        ),
        "audit_mismatches": result["mismatches"],
    }

    (args.out_dir / "report.json").write_text(
        json.dumps(report, indent=2),
        encoding="utf-8",
    )

    write_geojson(
        args.out_dir / "regions.geojson",
        overlap,
        result,
    )

    render(
        model,
        overlap,
        args.root,
        result,
        args.out_dir / "unified_region.png",
        args.out_dir / "unified_region.svg",
    )

    if result["mismatches"]:
        print("RESULT: audit mismatch")
        return 2

    if unified.is_empty:
        print("RESULT: no conflict region")
        return 0

    print("RESULT: one unified transparent-domain conflict region found")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
