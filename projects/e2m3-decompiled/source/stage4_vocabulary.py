"""Stage 4 -- vocabulary: the recovered parameters, re-authored as new geometry.

Stage 3 read E2M3's better staircase down to four numbers.  This stage spends
those four numbers somewhere else: a small invented layout, no E2M3 coordinates,
built with ``bloodmap.vocabulary.staircase``, compiled, and then handed back to
the same detector that produced the numbers in the first place.

Two things get checked, and they are different questions:

1. **does the abstraction reproduce the structure?**  The detector should
   recover the same rises, rise height, width and headroom from geometry it has
   never seen, in a map that shares nothing else with E2M3.
2. **what does it not reproduce?**  E2M3's treads vary by 111 units around their
   mean and the constructor makes them all equal.  That difference is printed,
   not hidden, and it is the correct outcome: tread jitter did not transfer
   across the corpus split, so it is residual evidence and not a parameter.

The stage also runs the edit that stage 2 and 3 cannot: change one number in the
source, recompile, and watch the independent hierarchy change with it.
"""

from __future__ import annotations

import pathlib
import sys
from typing import Any

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[3]))

from bloodmap.planar_layout import PlanarLayout                      # noqa: E402
from bloodmap.structures import detect_structures                    # noqa: E402
from bloodmap.vocabulary import Anchor, recess, staircase            # noqa: E402

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from stage3_structures import stepped_runs                           # noqa: E402

U = 384
PH = 0x1600

ROOM = dict(wall_picnum=180, floor_picnum=292, ceiling_picnum=385,
            wall_shade=8, floor_shade=16, ceiling_shade=8)


def build(total_rise: int, step_rise: int, tread: int, clear_height: int,
          width: int = 4 * U) -> PlanarLayout:
    """A deliberately dull two-room layout whose only feature is the stair.

    Nothing here is E2M3's geometry.  The rooms are invented; only the stair's
    four parameters came from the original, and they are numbers, not vertices.
    """
    layout = PlanarLayout(name="e2m3-stair-transfer", visibility=800)
    lower_floor = 8192
    layout.add_region(
        "region:lower", [(0, 0), (12 * U, 0), (12 * U, 12 * U), (0, 12 * U)],
        role="interior", floor_z=lower_floor, ceiling_z=lower_floor - 8 * PH, **ROOM,
    )
    # The lower room's east face runs south to north, so the stair grows east.
    base = Anchor("region:lower", (12 * U, 4 * U), (12 * U, 4 * U + width))
    stairs = staircase(
        layout, "stairs:transfer", base=base,
        total_rise=-total_rise, step_rise=-step_rise, tread=tread,
        clear_height=clear_height, shade_ramp=(20, 32), **ROOM,
    )
    top = stairs.far
    layout.add_region(
        "region:upper",
        [top.a, (top.a[0] + 10 * U, top.a[1]), (top.a[0] + 10 * U, top.b[1]), top.b],
        role="interior", floor_z=lower_floor - total_rise,
        ceiling_z=lower_floor - total_rise - 10 * PH, **ROOM,
    )
    stairs.arrive_at("region:upper")
    # One recess, on the corpus default: floor flush with the host, ceiling
    # dropped.  The upper room's north face runs east to west.
    recess(
        layout, "recess:niche",
        anchor=Anchor("region:upper", (top.a[0] + 6 * U, top.b[1]), (top.a[0] + 3 * U, top.b[1])),
        depth=2 * U, ceiling_drop=6 * PH, **ROOM,
    )
    layout.set_player_start("region:lower", x=6 * U, y=6 * U, z=lower_floor)
    return layout


def recover(total_rise: int, step_rise: int, tread: int, clear_height: int,
            width: int = 4 * U) -> dict[str, Any]:
    layout = build(total_rise, step_rise, tread, clear_height, width)
    compiled = layout.compile()
    document = detect_structures(compiled.level)
    runs = [item for item in document["structures"] if item["kind"] == "stepped_run"]
    if len(runs) != 1:
        raise AssertionError(f"expected exactly one stepped run, recovered {len(runs)}")
    return {
        "sectors": len(compiled.level.sectors),
        "run": runs[0],
        "recesses": [item for item in document["structures"] if item["kind"] == "recess"],
    }


def main() -> None:
    original = next(run for run in stepped_runs() if run.reproducible)
    print(f"E2M3 {original.structure_id}: rises={original.rises} "
          f"step_rise={original.step_rise} width={original.width} "
          f"clear_height={original.clear_height} tread_mean={original.tread_mean:.0f}")

    result = recover(
        original.total_rise, original.step_rise,
        round(original.tread_mean), original.clear_height, original.width,
    )
    parameters = result["run"]["parameters"]
    print(f"re-authored:            rises={parameters['rises']} "
          f"step_rise={result['run']['evidence']['rise_sequence'][0]} "
          f"width={parameters['width']:.0f} clear_height={parameters['clear_height']} "
          f"tread={result['run']['residual']['step_run']['mean']:.0f}")

    assert parameters["rises"] == original.rises
    assert abs(parameters["total_rise"]) == original.total_rise
    assert set(result["run"]["evidence"]["rise_sequence"]) == {original.step_rise}
    assert parameters["clear_height"] == original.clear_height
    assert round(parameters["width"]) == original.width
    print("essential parameters: reproduced")

    print("residual NOT reproduced, by design:")
    print(f"  E2M3's treads vary by {original.tread_stdev:.0f} units around their mean "
          f"({original.tread_min:.0f} to {original.tread_max:.0f}); every tread here is "
          f"exactly {round(original.tread_mean)} because the constructor has one tread")
    print(f"  the detector reports a spread of "
          f"{result['run']['residual']['step_run']['stdev']:.0f} here, which is the hop "
          "from the wide lower room's centroid to the first tread, not tread variation")

    print()
    print("one-number source edit, recompiled:")
    for rises in (original.rises, original.rises + 3):
        changed = recover(
            original.step_rise * rises, original.step_rise,
            round(original.tread_mean), original.clear_height,
        )
        print(f"  total_rise={original.step_rise * rises:6d} -> "
              f"{changed['sectors']} sectors, derived run of "
              f"{changed['run']['parameters']['rises']} rises and "
              f"{changed['run']['parameters']['total_rise']} total")

    print()
    print(f"recess recovered: {result['recesses'][0]['parameters']}")


if __name__ == "__main__":
    main()
