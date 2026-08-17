"""Small quality-diversity slice over the v3 planar blueprint.

Only candidates that compile and pass every hard geometry/connectivity gate
may enter the archive. Morphology is scored only after that gate.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from bloodmap.geometry_audit import validate_authored_level
from bloodmap.morphology import analyze_morphology
from bloodmap.exposure import spawn_neighborhood_report
from experiments.bb2_reconstruction_v3 import make_layout


def _perturb(seed: int) -> dict[str, int]:
    return {
        "south_inset": 2 + (seed % 5),
        "east_span": 10 + (seed % 9),
        "chamfer": 2 + (seed % 5),
    }


def run_slice(n: int = 64) -> dict[str, Any]:
    archive: list[dict[str, Any]] = []
    rejected: list[dict[str, Any]] = []
    for seed in range(n):
        params = _perturb(seed)
        layout = make_layout(**params)
        try:
            compiled = layout.compile()
        except Exception as exc:
            rejected.append({"seed": seed, "params": params, "reason": str(exc)})
            continue
        # compile() already ran native validation and authored gates with declarations.
        diagnostics = validate_authored_level(
            compiled.level,
            declared_specials=compiled.declared_specials,
            gated_sectors={
                compiled.allocations[key].sector_id
                for key, region in compiled.layout.regions.items()
                if region.type in {600, 602} or region.role in {"doorway", "gated_pocket"}
            },
            declared_zero_exit={
                compiled.allocations[key].sector_id
                for key, region in compiled.layout.regions.items()
                if region.declared_zero_exit or region.special in {"water", "stack", "helper"}
            },
            allocations={key: value.sector_id for key, value in compiled.allocations.items()},
            connection_report=compiled.connection_report,
        )
        errors = [item for item in diagnostics if item.severity == "error"]
        if errors:
            rejected.append({"seed": seed, "params": params, "reason": errors[0].code})
            continue
        build = compiled.level.to_disk_map().to_build_ir()
        morph = analyze_morphology(build)
        neighborhoods = spawn_neighborhood_report(build, include_sp_start=False)
        sky = 0
        for sector in compiled.level.sectors:
            if int(sector["fields"].get("ceiling_stat") or 0) & 1:
                sky += 1
        archive.append({
            "seed": seed,
            "params": params,
            "orientation_diversity": morph["walls"]["orientation_diversity"],
            "rectangular_fraction": morph["sectors"]["rectangular_fraction"],
            "max_spawn_area": max(item["spawn_sector_area_player_areas"] for item in neighborhoods["neighborhoods"]),
            "sky_sectors": sky,
            "sectors": len(compiled.level.sectors),
        })
    return {
        "attempted": n,
        "archived": len(archive),
        "rejected": len(rejected),
        "archive": archive,
        "rejected_sample": rejected[:12],
        "note": "invalid geometry never enters the archive; morphology is second-order",
    }


if __name__ == "__main__":
    report = run_slice(64)
    Path("reports/BB2-qd-slice.json").write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n",
    )
    print(f"QD slice: archived {report['archived']}/{report['attempted']}")
