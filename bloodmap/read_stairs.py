"""Stairs as structures with parameters and a residual, and what they claim.

E2M3's stage 3 established the shape: a stepped run is a constant rise and a
tread, plus the residual the constructor must not pretend to reproduce. This
reads E3M1's runs the same way and then does the thing stage 3 could not --
it says which FIELDS the recovered parameters reproduce exactly, so a stair
claims its sectors' floor and ceiling z in the shared ledger and its residual
stays unclaimed.

A stair is a STRUCTURE, not a mechanism. E3M1's helix (25 sectors, 24 rises)
carries no sector type and no XSECTOR: nothing about it moves, and reading it
as a mechanism would put 25 sectors in layer 5 that belong here.

`structures.detect_structures` is reused unchanged; the fit and the claim are
what is new.
"""

from __future__ import annotations

from typing import Any, Sequence

STAIR = "stepped_run"


def _face(item: Any) -> Any:
    return item["fields"] if isinstance(item, dict) else item.fields


def fit_run(level: Any, sectors: Sequence[int]) -> dict[str, Any]:
    """One rise, one origin, and the sectors it reproduces exactly.

    The run is ordered by its own floor z rather than by sector id -- Build
    numbers a spiral in the order it was drawn, which need not be the order it
    climbs -- and the rise is the modal difference between consecutive levels.
    A run whose rise is not constant reproduces only the sectors that happen
    to land on the fitted progression, and the rest are its residual.
    """
    levels = sorted({int(_face(level.sectors[index])["floor_z"])
                     for index in sectors})
    if len(levels) < 2:
        return {"rise": 0, "origin": levels[0] if levels else 0,
                "reproduces": [], "residual": list(sectors)}
    gaps = [levels[index + 1] - levels[index] for index in range(len(levels) - 1)]
    rise = max(set(gaps), key=gaps.count)
    origin = levels[0]
    exact, residual = [], []
    for index in sectors:
        here = int(_face(level.sectors[index])["floor_z"])
        offset = here - origin
        (exact if rise and offset % rise == 0 else residual).append(index)
    return {
        "rise": int(rise),
        "origin": int(origin),
        "levels": len(levels),
        "rises_seen": {int(value): gaps.count(value) for value in sorted(set(gaps))},
        "constant_rise": len(set(gaps)) == 1,
        "reproduces": sorted(exact),
        "residual": sorted(residual),
    }


def read_stairs(level: Any, structures: dict[str, Any] | None = None
                ) -> dict[str, Any]:
    """Every stepped run in the level, fitted, with its residual."""
    if structures is None:
        from .structures import detect_structures

        structures = detect_structures(level)
    runs = []
    for item in structures["structures"]:
        if item["kind"] != STAIR:
            continue
        fit = fit_run(level, item["sectors"])
        moves = sorted(index for index in item["sectors"]
                       if int(_face(level.sectors[index])["type"])
                       or level.sectors[index].get("blood"))
        runs.append({
            "id": item["id"],
            "sectors": list(item["sectors"]),
            "attaches_to": list(item.get("attaches_to", [])),
            "parameters": item.get("parameters", {}),
            "structure_residual": item.get("residual", {}),
            "fit": fit,
            "sectors_that_also_carry_a_mechanism": moves,
        })
    runs.sort(key=lambda row: -len(row["sectors"]))
    covered = {index for row in runs for index in row["fit"]["reproduces"]}
    residual = {index for row in runs for index in row["fit"]["residual"]}
    return {
        "runs": runs,
        "sectors_in_a_run": sorted({index for row in runs
                                    for index in row["sectors"]}),
        "sectors_the_fit_reproduces": sorted(covered),
        "sectors_in_the_residual": sorted(residual - covered),
        "runs_with_a_constant_rise": sum(1 for row in runs
                                         if row["fit"]["constant_rise"]),
    }
