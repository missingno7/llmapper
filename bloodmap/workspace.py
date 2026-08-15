"""Persistent, replayable workspace records for an eventual design agent.

The MAP remains a compiled artifact.  This module persists briefs, decisions,
evidence, contextual slices, and probe episodes without assigning semantic truth
to any heuristic record.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Iterable

from .build_ir import BuildIR
from .design import design_fingerprint
from .experience import probe_progression
from .spatial import spatial_selection_context


class WorkspaceError(ValueError):
    pass


EVIDENCE_STATES = {"verified", "heuristic", "disputed", "superseded", "rejected"}


def _json(value: Any) -> str:
    return json.dumps(value, indent=2, sort_keys=True) + "\n"


def _read_json(path: Path, schema: str) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except OSError as exc:
        raise WorkspaceError(f"cannot read {path}") from exc
    except json.JSONDecodeError as exc:
        raise WorkspaceError(f"invalid JSON in {path}") from exc
    if value.get("$schema") != schema or int(value.get("schema_version", -1)) != 1:
        raise WorkspaceError(f"unsupported {schema} document at {path}")
    return value


def _write_new(path: Path, value: str) -> None:
    if path.exists():
        raise WorkspaceError(f"refusing to overwrite existing workspace file: {path}")
    path.write_text(value, encoding="utf-8", newline="\n")


def initialize_project(directory: str | Path, *, name: str, brief: str = "") -> dict[str, Any]:
    """Create a non-destructive level-design workspace skeleton."""
    root = Path(directory)
    if root.exists() and any(root.iterdir()):
        raise WorkspaceError(f"project directory is not empty: {root}")
    root.mkdir(parents=True, exist_ok=True)
    for relative in ("design", "level", "reports", "memory", "references"):
        (root / relative).mkdir(exist_ok=True)
    _write_new(root / "project.json", _json({
        "$schema": "bloodmap.level-project", "schema_version": 1,
        "name": str(name), "authoring_model": "brief -> recipe/operations -> MAP -> validation/probes",
        "boundaries": ["derived observations never overwrite MAP truth", "LLM is an external client, not a core dependency"],
    }))
    _write_new(root / "design" / "brief.md", brief or f"# {name}\n\nDescribe the intended player experience here.\n")
    _write_new(root / "design" / "plan.md", "# Design plan\n\n- [ ] Interpret brief\n- [ ] Establish progression\n- [ ] Block out and probe\n")
    _write_new(root / "design" / "decisions.jsonl", "")
    _write_new(root / "memory" / "episodes.jsonl", "")
    _write_new(root / "memory" / "evidence-ledger.json", _json({
        "$schema": "bloodmap.evidence-ledger", "schema_version": 1, "entries": [],
    }))
    _write_new(root / "memory" / "design-memory.json", _json({
        "$schema": "bloodmap.design-memory", "schema_version": 1, "samples": [],
    }))
    _write_new(root / "level" / "README.md", "# Level artifact\n\nStore the replayable recipe and generated MAP here.\n")
    return {
        "$schema": "bloodmap.level-project", "schema_version": 1, "root": str(root), "name": str(name),
        "created": ["design/brief.md", "design/plan.md", "design/decisions.jsonl", "memory/evidence-ledger.json", "memory/design-memory.json", "memory/episodes.jsonl"],
    }


def _project(root: str | Path) -> Path:
    path = Path(root)
    _read_json(path / "project.json", "bloodmap.level-project")
    return path


def append_evidence(root: str | Path, entry: dict[str, Any]) -> dict[str, Any]:
    """Append an evidence-backed semantic claim without silently replacing history."""
    project = _project(root)
    ledger_path = project / "memory" / "evidence-ledger.json"
    ledger = _read_json(ledger_path, "bloodmap.evidence-ledger")
    result = dict(entry)
    result["id"] = str(result.get("id") or f"evidence:{len(ledger['entries']):04d}")
    result["concept"] = str(result.get("concept", ""))
    result["claim"] = str(result.get("claim", ""))
    result["status"] = str(result.get("status", "heuristic"))
    if not result["concept"] or not result["claim"]:
        raise WorkspaceError("evidence entry requires concept and claim")
    if result["status"] not in EVIDENCE_STATES:
        raise WorkspaceError(f"unknown evidence status {result['status']!r}")
    result["evidence"] = list(result.get("evidence", []))
    result["unknowns"] = [str(item) for item in result.get("unknowns", [])]
    if any(item.get("id") == result["id"] for item in ledger["entries"]):
        raise WorkspaceError(f"duplicate evidence ID {result['id']!r}")
    ledger["entries"].append(result)
    ledger_path.write_text(_json(ledger), encoding="utf-8", newline="\n")
    return result


def append_jsonl(root: str | Path, relative: str, record: dict[str, Any]) -> dict[str, Any]:
    project = _project(root)
    path = project / relative
    if not path.is_file():
        raise WorkspaceError(f"workspace record file does not exist: {path}")
    with path.open("a", encoding="utf-8", newline="\n") as stream:
        stream.write(json.dumps(record, sort_keys=True) + "\n")
    return record


def append_decision(root: str | Path, *, intent: str, decision: str, expected: str, evidence: list[Any] | None = None, status: str = "proposed") -> dict[str, Any]:
    return append_jsonl(root, "design/decisions.jsonl", {
        "$schema": "bloodmap.design-decision", "schema_version": 1,
        "intent": str(intent), "decision": str(decision), "expected": str(expected),
        "evidence": list(evidence or []), "status": str(status),
    })


def append_episode(root: str | Path, *, intent: str, expected: str, observed: dict[str, Any], correction: str | None = None) -> dict[str, Any]:
    return append_jsonl(root, "memory/episodes.jsonl", {
        "$schema": "bloodmap.design-episode", "schema_version": 1,
        "intent": str(intent), "expected": str(expected), "observed": observed,
        "correction": None if correction is None else str(correction),
    })


def make_level_slice(build: BuildIR, sector_ids: Iterable[int], *, source: dict[str, Any]) -> dict[str, Any]:
    """Capture a contextual precedent selection without treating it as a prefab."""
    selected = sorted({int(value) for value in sector_ids})
    if not selected:
        raise WorkspaceError("LevelSlice selection is empty")
    progression = probe_progression(build)
    selected_refs = {f"sector:{value}" for value in selected}
    touching_gates = [
        item for item in progression["state_change_candidates"]
        if set(item["sectors"]) & selected_refs
    ]
    return {
        "$schema": "bloodmap.level-slice", "schema_version": 1,
        "source": dict(source), "sectors": [f"sector:{value}" for value in selected],
        "fingerprint": design_fingerprint(build, selected),
        "spatial_context": spatial_selection_context(build, selected),
        "static_progression": {
            "start_sector": progression["start_sector"],
            "selected_reachable_under_declared_state": sorted(selected_refs & set(progression["reachable_sectors"])),
            "selected_unreachable_under_declared_state": sorted(selected_refs & set(progression["unreachable_sectors"])),
            "touching_state_change_candidates": touching_gates,
            "limitations": progression["limitations"],
        },
        "status": "contextual design sample; not a room label or reusable prefab",
    }


def store_level_slice(root: str | Path, sample: dict[str, Any], *, sample_id: str | None = None) -> dict[str, Any]:
    project = _project(root)
    memory_path = project / "memory" / "design-memory.json"
    memory = _read_json(memory_path, "bloodmap.design-memory")
    result = dict(sample)
    result["id"] = str(sample_id or result.get("id") or f"slice:{len(memory['samples']):04d}")
    if any(item.get("id") == result["id"] for item in memory["samples"]):
        raise WorkspaceError(f"duplicate design sample ID {result['id']!r}")
    memory["samples"].append(result)
    memory_path.write_text(_json(memory), encoding="utf-8", newline="\n")
    return result


def source_identity(path: str | Path, *, game: str) -> dict[str, Any]:
    candidate = Path(path)
    data = candidate.read_bytes()
    return {"map": candidate.name, "path": str(candidate), "game": str(game), "sha256": hashlib.sha256(data).hexdigest()}
