"""Stage 3 -- structures: the parts the places are built from, with residuals.

Stage 2 says *large_interior* has a stepped run in it.  This stage says what
that run is: how many rises, how tall each one, how wide, how much headroom --
and, separately, how far the original strays from those numbers.

The separation is the whole point.  A reusable abstraction should carry the
first set and refuse the second.  Reproducing ``step_run=[512, 768, 768, 768]``
because E2M3 happens to say so would be memorising, not learning.
"""

from __future__ import annotations

import json
import pathlib
from dataclasses import dataclass
from typing import Any

STRUCTURES = pathlib.Path("projects/e2m3-decompiled/structures.json")

PLAYER_WIDTH = 384
PLAYER_HEIGHT = 0x1600


@dataclass(frozen=True)
class RunFacts:
    """What a stepped run is, and what it merely happens to be."""

    structure_id: str
    rises: int
    step_rise: int | None          # essential when the run is uniform
    total_rise: int
    width: int                     # essential
    clear_height: int              # essential
    tread_mean: float              # essential, as a single number
    tread_stdev: float             # residual
    tread_min: float               # residual
    tread_max: float               # residual
    width_stdev: float             # residual
    rise_sequence: tuple[int, ...] # residual when not uniform

    @property
    def reproducible(self) -> bool:
        """Can one constant-rise constructor stand in for this run?"""
        return self.step_rise is not None and self.step_rise in (2048, 3072, 4096)

    def as_call(self) -> str:
        if not self.reproducible:
            return (
                "# not reproducible by staircase(): rises "
                f"{list(self.rise_sequence)} are not one repeated corpus rise"
            )
        return (
            "staircase(layout, structure_id, base=anchor,\n"
            f"          total_rise={self.total_rise}, step_rise={self.step_rise},\n"
            f"          tread={round(self.tread_mean)}, clear_height={self.clear_height})"
        )

    def residual(self) -> dict[str, Any]:
        return {
            "tread_stdev": self.tread_stdev,
            "portal_width_stdev": self.width_stdev,
            "rise_sequence": list(self.rise_sequence),
        }


def _document() -> dict[str, Any]:
    return json.loads(STRUCTURES.read_text(encoding="utf-8"))


def stepped_runs() -> list[RunFacts]:
    result = []
    for item in _document()["structures"]:
        if item["kind"] != "stepped_run":
            continue
        parameters, residual = item["parameters"], item["residual"]
        sequence = tuple(abs(int(value)) for value in item["evidence"]["rise_sequence"])
        uniform = residual["uniform_rise"]
        result.append(RunFacts(
            structure_id=item["id"],
            rises=int(parameters["rises"]),
            step_rise=sequence[0] if uniform else None,
            total_rise=abs(int(parameters["total_rise"])),
            width=int(round(parameters["width"])),
            clear_height=int(parameters["clear_height"]),
            tread_mean=float(residual["step_run"]["mean"]),
            tread_stdev=float(residual["step_run"]["stdev"]),
            tread_min=float(residual["step_run"]["min"]),
            tread_max=float(residual["step_run"]["max"]),
            width_stdev=float(residual["portal_width"]["stdev"]),
            rise_sequence=sequence,
        ))
    return result


def recesses() -> list[dict[str, Any]]:
    """Recesses as the three numbers that matter, plus what they sit in."""
    return [
        {
            "id": item["id"],
            "opening_player_widths": round(item["parameters"]["opening_width"] / PLAYER_WIDTH, 2),
            "footprint_player_areas": round(item["parameters"]["area"] / PLAYER_WIDTH ** 2, 2),
            "fraction_of_host": item["parameters"]["depth_ratio"],
            "floor_delta": item["parameters"]["floor_delta"],
            "ceiling_drop": item["parameters"]["ceiling_delta"],
            "host_sector": item["attaches_to"][0],
        }
        for item in _document()["structures"] if item["kind"] == "recess"
    ]


def shells() -> list[dict[str, Any]]:
    """Embedded shells, largest first, with the vertex count of the hole."""
    rows = [
        {
            "id": item["id"],
            "footprint_player_areas": round(item["parameters"]["footprint"] / PLAYER_WIDTH ** 2, 1),
            "contained_sectors": item["parameters"]["contained_sectors"],
            "occupies_host": item["parameters"]["occupies_host"],
            "hole_vertices": item["evidence"]["vertices"],
            "host_sector": item["attaches_to"][0],
        }
        for item in _document()["structures"] if item["kind"] == "embedded_shell"
    ]
    return sorted(rows, key=lambda row: -row["footprint_player_areas"])


def main() -> None:
    print("stepped runs")
    for run in stepped_runs():
        print(f"  {run.structure_id}: {run.rises} rises, total {run.total_rise}, "
              f"width {run.width}, headroom {run.clear_height / PLAYER_HEIGHT:.1f} PH, "
              f"reproducible={run.reproducible}")
        print("   ", run.as_call().replace("\n", "\n    "))
        print("    residual:", run.residual())
    print()
    print("recesses (first 5 of %d)" % len(recesses()))
    for item in recesses()[:5]:
        print("  ", item)
    print()
    print("embedded shells (largest 5 of %d)" % len(shells()))
    for item in shells()[:5]:
        print("  ", item)


if __name__ == "__main__":
    main()
