"""Write E2M2 / BB3 / SP-v1 analysis artifacts for the progression experiment."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from bloodmap.format import read_map
from bloodmap.placement import mine_attachments
from bloodmap.progression import analyze_progression, classify_mechanisms, compact_progression_report, completion_witness
from bloodmap.sp_understand import (
    analyze_floor_bands,
    build_sp_packet,
    e2m2_mechanism_patterns,
    mine_mechanism_compositions,
    retrieve_vertical_in_campaign,
)
from bloodmap.understanding import understand_map
from experiments.sp_progression_v1 import make_layout


def _write(path: str | Path, payload: Any) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n")


def write_reports(*, maps_dir: str = "maps/blood") -> dict[str, str]:
    written = {}
    placement = mine_attachments(maps_dir, population="blood-campaign")
    _write("reports/blood-object-placement.json", placement)
    written["placement"] = "reports/blood-object-placement.json"

    compositions = mine_mechanism_compositions(maps_dir, population="blood-campaign")
    e2m2 = read_map("maps/blood/E2M2.MAP")
    packet = build_sp_packet(e2m2, map_name="E2M2.MAP")
    _write("reports/E2M2-understanding.json", packet)
    written["e2m2_understanding"] = "reports/E2M2-understanding.json"

    progression = packet["progression"]
    _write("reports/E2M2-progression.json", progression)
    written["e2m2_progression"] = "reports/E2M2-progression.json"

    patterns = e2m2_mechanism_patterns(progression, compositions)
    _write("reports/E2M2-mechanism-patterns.json", {"compositions": compositions, "e2m2": patterns})
    written["e2m2_mechanisms"] = "reports/E2M2-mechanism-patterns.json"

    bb3 = read_map("maps/blood/BB3.MAP")
    bb3_vertical = analyze_floor_bands(bb3)
    retrieval = retrieve_vertical_in_campaign(
        maps_dir, query_delta_min=0.4, query_delta_max=3.0, population="blood-campaign",
    )
    _write("reports/BB3-vertical-patterns.json", {
        "bb3": bb3_vertical,
        "campaign_retrieval": retrieval,
        "population_note": "BB3 is BloodBath vertical morphology only; not an SP progression reference",
    })
    written["bb3"] = "reports/BB3-vertical-patterns.json"

    generated = make_layout().compile().level.to_disk_map()
    gen_packet = build_sp_packet(generated, map_name="SP-progression-v1.MAP")
    _write("reports/SP-progression-v1-understanding.json", gen_packet)
    written["sp_understanding"] = "reports/SP-progression-v1-understanding.json"
    return written


if __name__ == "__main__":
    written = write_reports()
    for key, path in written.items():
        print(f"{key}: {path}")
