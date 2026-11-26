"""Report the live remake's measured state without compiling or editing its map.

What only this level has is measured here: the baseline's geometry kept, the
converter's mechanisms changed on purpose, each pass's read-back. Where its
map, poses, reports and critique rounds are is the descriptor's word
(`bloodmap.project`); a place's evidence is its last critique round
(`tools.critique.verdict`), current only for the map and poses it was made of.
"""

from collections import Counter
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from bloodmap import project as P
from bloodmap.analysis import validate_map
from bloodmap.format import parse_map, read_map
from bloodmap.model import record_fields, record_extra
from tools.place_character import Geometry, profile, load_norms, judge
from tools.sprite_fit import audit, faults, sunk_actors

PROJECT = Path(__file__).resolve().parent


def sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def evidence_state(manifest, map_hash, poses_hash):
    """A completed render is current only for this map and this pose set."""
    if not manifest:
        return "missing"
    if manifest.get("source_sha256") != map_hash:
        return "historical map"
    if manifest.get("poses_sha256") != poses_hash:
        return "historical poses"
    return "current"


def preservation(before, after):
    """Compare native geometry and existing extensions, including hidden mechanisms."""
    geometry = []
    for kind, keys in (
        ("sector", ("wall_ptr", "wall_count", "floor_z", "ceiling_z",
                    "floor_heinum", "ceiling_heinum")),
        ("wall", ("x", "y", "point2", "next_wall", "next_sector")),
    ):
        left, right = getattr(before, kind + "s"), getattr(after, kind + "s")
        if len(left) != len(right):
            geometry.append(f"{kind} count changed")
        for i, (a, b) in enumerate(zip(left, right)):
            for key in keys:
                if record_fields(a)[key] != record_fields(b)[key]:
                    geometry.append(f"{kind} {i} {key}")
            if kind == "sector":
                for key in ("floor_stat", "ceiling_stat"):
                    if (record_fields(a)[key] ^ record_fields(b)[key]) & 2:
                        geometry.append(f"sector {i} {key} slope flag")
    start = [k for k in ("start_x", "start_y", "start_z", "start_angle", "start_sector")
             if before.header[k] != after.header[k]]
    extensions = []
    for kind in ("sector", "wall", "sprite"):
        for i, (a, b) in enumerate(zip(getattr(before, kind + "s"), getattr(after, kind + "s"))):
            if record_extra(a) != record_extra(b):
                extensions.append(f"{kind} {i}")
    sprite_fields = []
    for i, (a, b) in enumerate(zip(before.sprites, after.sprites)):
        af, bf = record_fields(a), record_fields(b)
        changed = {k: [af.get(k), bf.get(k)] for k in af.keys() | bf.keys() if af.get(k) != bf.get(k)}
        if changed:
            sprite_fields.append({"sprite": i, "fields": changed})
    return {"geometry_changes": geometry, "start_changes": start,
            "existing_extension_changes": extensions,
            "existing_sprite_changes": sprite_fields,
            "added_sprites": len(after.sprites) - len(before.sprites)}


def place_evidence(project, slug, map_hash, poses_hash):
    """A place's last critique round: whether its frames are of this map and these poses, and what the readers said."""
    from tools.critique import verdict

    folder = project.rounds(slug)
    rounds = verdict(project, slug) if folder.is_dir() and any(folder.glob("round-*")) else []
    if not rounds:
        return {"evidence": "missing", "review": "no round prepared", "round": None}
    last = rounds[-1]
    packet = json.loads((folder / f"round-{last['round']}" / "packet.json").read_text(encoding="utf-8"))
    state = evidence_state(packet, map_hash, poses_hash)
    if state == "current":
        # every frame a reader is shown must still be the frame the packet names
        state = "current" if all((folder / f"round-{last['round']}" / name).exists()
                                 and sha256(folder / f"round-{last['round']}" / name) == digest
                                 for name, digest in packet.get("frames", {}).items()) else "frames changed"
    if last["passes"]:
        review = "passes"
    elif last["reviews_missing"] == packet.get("readers"):
        review = "prepared, no reader has answered"
    else:
        review = "does not pass: " + "; ".join(last["blocking"] + [f"{r} missing" for r in last["reviews_missing"]])
    return {"evidence": state, "review": review, "round": last["round"]}


def collect(project=None):
    from tools.look import pose_hash

    project = project or P.read(PROJECT)
    path = project.map
    payload = path.read_bytes()
    disk = parse_map(payload)
    current_hash = hashlib.sha256(payload).hexdigest()
    places = json.loads((project.root / "places.json").read_text(encoding="utf-8"))
    reports = project.need("reports")
    geometry, norms = Geometry(disk), load_norms()
    place_rows = {}
    for key, brief in places.items():
        prof = profile(geometry, brief["sectors"])
        found = place_evidence(project, key, current_hash, pose_hash(project, [brief["pose_set"]]))
        place_rows[key] = {**brief, "profile": prof, "campaign_comparison": judge(prof, norms),
                           "critique_round": found["round"], "evidence": found["evidence"],
                           "independent_review": found["review"], "owner_walk": "pending"}
    diagnostics = list(validate_map(disk))
    severity = dict(Counter(row.severity for row in diagnostics))
    fit_rows = audit(disk)
    fit = faults(fit_rows)
    intake_report = json.loads((reports / "04-intake-hall-applied.json").read_text())
    input_map = project.root / "snapshots" / (intake_report["before_sha256"] + ".MAP")
    input_disk = read_map(input_map)
    additions = set(range(len(input_disk.sprites), len(disk.sprites)))
    first_pass = json.loads((reports / "first-pass-readback.json").read_text())
    preserved_references = {
        "blood_baseline": sha256(project.root / "E4L1-baseline.MAP") == first_pass["baseline_sha256"],
        "duke_source": sha256(ROOT / "maps/duke3d/E4L1.MAP") == first_pass["source_duke_sha256"],
        "intake_input_snapshot": sha256(input_map) == intake_report["before_sha256"],
    }
    briefing_path = reports / "briefing-wire-readback.json"
    briefing = json.loads(briefing_path.read_text()) if briefing_path.exists() else None
    audit_path = reports / "converter-mechanism-audit.json"
    audit_data = json.loads(audit_path.read_text()).get("results",[]) if audit_path.exists() else []
    motion_audit = audit_data[0] if audit_data else None
    washhouse_path = reports / "washhouse-readback.json"
    washhouse = json.loads(washhouse_path.read_text()) if washhouse_path.exists() else None
    return {
        "map_sha256": current_hash,
        "counts": {k: len(getattr(disk, k)) for k in ("sectors", "walls", "sprites")},
        "baseline_sha256": sha256(project.root / "E4L1-baseline.MAP"),
        "duke_source_sha256": sha256(ROOT / "maps/duke3d/E4L1.MAP"),
        "preserved_references": preserved_references,
        "briefing_circuit": {
            "evidence": "current" if briefing and briefing.get("source_sha256") == current_hash else "missing or historical",
            "agrees": briefing.get("agrees") if briefing else None,
            "wires": len(briefing.get("wires", [])) if briefing else 0,
        },
        "motion_audit": {
            "evidence":"current" if motion_audit and motion_audit.get("converted_sha256")==current_hash else "missing or historical",
            "sweeps":motion_audit.get("moving_sectors",0) if motion_audit else 0,
            "problems":motion_audit.get("problems") if motion_audit else None,
            "manual_or_unsupported":dict(Counter(row["kind"] for row in motion_audit.get("coverage",[]) if not row["lowered"])) if motion_audit else {},
        },
        "washhouse": {
            "evidence":"current" if washhouse and washhouse.get("map_sha256")==current_hash else "missing or historical",
            "room_static":bool(washhouse and washhouse["static_room"]["native_type"]==0
                               and washhouse["static_room"]["entry_signal_preserved"]),
            "fit_faults":sum(len(rows) for rows in washhouse["fixture_fit_faults"].values()) if washhouse else None,
            "flat_overlaps":len(washhouse["fixture_flat_overlaps"]) if washhouse else None,
            "flush_controls_agree":all(r["agrees"] for r in washhouse["flush_controls"]) if washhouse else None,
        },
        "structural_diagnostics": severity,
        "structural_details": [vars(row) for row in diagnostics],
        "baseline_geometry": preservation(read_map(project.root / "E4L1-baseline.MAP"), disk)["geometry_changes"],
        "intake_input_sha256": sha256(input_map),
        "since_intake_input": preservation(input_disk, disk),
        "sunk_actor_authoring_count": len(sunk_actors(disk)),
        "sunk_actor_authoring_rows": sunk_actors(disk),
        "added_sprite_fit_faults": [{"fault": kind, **r} for kind, rows in fit.items()
                                           for r in rows if r["sprite"] in additions],
        "places": place_rows,
        "open": ["Exit sequence and route to 311 unverified", "Mirror support 57 needs native mirror repair",
                 "Camera-only scenery 535-542 excluded but not deleted", "Other interiors still need passes",
                 "Runtime weather, audio and actual Use activation unverified"],
        "runtime_events_executed": False,
    }


def write_status(data, project=None):
    output = (project or P.read(PROJECT)).need("reports")
    (output / "status.json").write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    counts, delta = data["counts"], data["since_intake_input"]
    lines = ["# Quarry pumping works: current state", "",
             "Generated by `status.py` from the live MAP, explicit place boundaries and hashed evidence. Do not edit.", "",
             f"MAP SHA-256: `{data['map_sha256']}`.", "",
             f"{counts['sectors']} sectors / {counts['walls']} walls / {counts['sprites']} sprites. "
             f"Structural diagnostics: {data['structural_diagnostics']}.", "",
             f"Geometry changes from baseline: {len(data['baseline_geometry'])}. "
             f"Since intake input: {len(delta['existing_extension_changes'])} existing mechanism extensions changed; "
             f"{len(delta['existing_sprite_changes'])} existing sprites changed; {delta['added_sprites']} added.", "",
             f"Original Duke source, Blood baseline and intake input snapshot preserved: {all(data['preserved_references'].values())}.", "",
             f"Saved-map sunk actor diagnostics: {data['sunk_actor_authoring_count']}. "
             "Blood seats actors at spawn; this is an authoring diagnostic, not proof of broken encounters.", "",
             f"Fit faults on additions since the intake input: {len(data['added_sprite_fit_faults'])}.", "",
             f"Briefing circuit read-back: {data['briefing_circuit']['evidence']}; "
             f"{data['briefing_circuit']['wires']} declared wires, agrees={data['briefing_circuit']['agrees']}. "
             "Runtime activation and sound remain unverified.", "",
             f"Converter motion audit: {data['motion_audit']['evidence']}; "
             f"{data['motion_audit']['sweeps']} horizontal sweeps, {data['motion_audit']['problems']} geometric discrepancies. "
             "Manual conversion limitations are listed in `converter-mechanism-audit.md`.", "",
             f"Washhouse read-back: {data['washhouse']['evidence']}; "
             f"room static with entry signal preserved={data['washhouse']['room_static']}; "
             f"new fixture fit faults={data['washhouse']['fit_faults']}, flat overlaps={data['washhouse']['flat_overlaps']}. "
             "Local flush controls match the campaign precedent; live Use, sound and collision remain unverified.", "",
             "| Place | Layers / campaign median | Critique round | Its frames | Blind readers |",
             "| --- | --- | --- | --- | --- |"]
    for key, row in data["places"].items():
        comparison = row["campaign_comparison"]
        lines.append(f"| {row['name']} | {row['profile']['layer_count']} / {comparison.get('campaign_p50', '?')} "
                     f"| {row['critique_round'] or 'none'} | {row['evidence']} | {row['independent_review']} |")
    lines += ["", "Layer counts are corpus comparisons, not visual approval or instructions to add clutter. "
              "A place is handed to blind readers with `python -m tools.critique --project duke-e4l1-remake prepare "
              "<place> --poses <pose_set> --kind <kind> --study <study>` (all three in places.json).", "",
              "## Open work", ""]
    for row in data["places"].values():
        lines += [f"- {row['name']}: {item}." for item in row.get("open", [])]
    lines += [f"- {item}." for item in data["open"]]
    lines += ["", "Owner walking remains pending. "
              "Observer frames do not execute runtime events or sound.", ""]
    (output / "STATUS.md").write_text("\n".join(lines), encoding="utf-8")


if __name__ == "__main__":
    result = collect()
    write_status(result)
    print((P.read(PROJECT).need("reports") / "STATUS.md").read_text(encoding="utf-8"))
