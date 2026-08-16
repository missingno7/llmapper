"""Demonstrate Design Probes on real Blood and Duke3D maps."""
import json

from bloodmap import probes  # noqa: F401 - registers probes
from bloodmap.build_ir import BuildIR
from bloodmap.duke import read_duke_map
from bloodmap.format import read_map
from bloodmap.probe_schema import DesignProbe, run_probe
from bloodmap.state_model import PlayerState, WorldState


def run_demonstrations():
    # --- Blood E1M1 ---
    disk = read_map("maps/blood/E1M1.MAP")
    build = disk.to_build_ir()
    start_sector = build.player_start["sector"]

    print("=" * 60)
    print("Blood E1M1: Progression probe")
    print("=" * 60)
    probe = DesignProbe(
        probe_type="progression",
        question="What is the initial progression structure of E1M1?",
        player_state=PlayerState(sector=start_sector),
    )
    result = run_probe(probe, build)
    print(f"Status: {result.status}")
    print(f"Reachable: {result.measurements['initial_reachable_count']}")
    print(f"Unreachable: {result.measurements['unreachable_count']}")
    print(f"Total: {result.measurements['total_sectors']}")
    print()

    print("=" * 60)
    print("Blood E1M1: Access probe to a far sector")
    print("=" * 60)
    probe = DesignProbe(
        probe_type="access",
        question="Can the player reach sector 153 initially?",
        player_state=PlayerState(sector=start_sector),
        parameters={"target_sector": 153},
    )
    result = run_probe(probe, build)
    print(f"Status: {result.status}")
    print(f"Answer: {result.answer}")
    if result.blocking_reasons:
        print(f"Blocking: {result.blocking_reasons}")
    print()

    print("=" * 60)
    print("Blood E1M1: Transition probe between adjacent sectors")
    print("=" * 60)
    probe = DesignProbe(
        probe_type="transition",
        question="Transition from sector 0 to sector 1",
        player_state=PlayerState(sector=0),
        parameters={"source_sector": 0, "destination_sector": 1},
    )
    result = run_probe(probe, build)
    print(f"Status: {result.status}")
    print(f"Area ratio: {result.measurements.get('area_ratio', 'N/A')}")
    print(f"Height delta: {result.measurements.get('clear_height_delta', 'N/A')}")
    print()

    print("=" * 60)
    print("Blood E1M1: Escape probe from player start")
    print("=" * 60)
    probe = DesignProbe(
        probe_type="escape",
        question="What are the escape options from the player start?",
        player_state=PlayerState(sector=start_sector),
    )
    result = run_probe(probe, build)
    print(f"Status: {result.status}")
    print(f"Viable exits: {result.measurements['viable_exit_count']}")
    print(f"Dead-end depth: {result.measurements['dead_end_depth']}")
    print()

    # --- Duke3D E1L1 ---
    duke_disk = read_duke_map("maps/duke3d/E1L1.MAP")
    duke_build = duke_disk.to_build_ir()
    duke_start = duke_build.player_start["sector"]

    print("=" * 60)
    print("Duke3D E1L1: Progression probe")
    print("=" * 60)
    probe = DesignProbe(
        probe_type="progression",
        question="What is the initial progression structure of E1L1?",
        player_state=PlayerState(sector=duke_start),
    )
    result = run_probe(probe, duke_build)
    print(f"Status: {result.status}")
    print(f"Reachable: {result.measurements['initial_reachable_count']}")
    print(f"Unreachable: {result.measurements['unreachable_count']}")
    print(f"Total: {result.measurements['total_sectors']}")
    print()

    # --- Counterfactual: compare entrance width candidates ---
    print("=" * 60)
    print("Counterfactual: Compare entrance width on E1M1")
    print("=" * 60)
    from bloodmap.counterfactual import evaluate_candidates

    probe = DesignProbe(
        probe_type="transition",
        question="Transition from sector 0 to sector 1",
        player_state=PlayerState(sector=0),
        parameters={"source_sector": 0, "destination_sector": 1},
    )
    candidates = {
        "wider_entrance": {
            "type": "set_sector_z",
            "sector_id": 1,
            "ceiling_z": -16384,
            "floor_z": 8192,
        },
        "narrower_entrance": {
            "type": "set_sector_z",
            "sector_id": 1,
            "ceiling_z": -4096,
            "floor_z": 4096,
        },
    }
    results = evaluate_candidates(build, [probe], candidates)
    comparison = results["comparison"]
    for key, data in comparison.items():
        print(f"Probe: {data['probe_type']}")
        print(f"  Original: {data['original']}")
        for cand in candidates:
            if cand in data:
                print(f"  {cand}: {data[cand]}")
    print()


if __name__ == "__main__":
    run_demonstrations()
