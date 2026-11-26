"""Apply guarded, incremental edits to the live Blood map without rebuilding its geometry."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from bloodmap.analysis import validate_map
from bloodmap.construction import LevelBuilder
from bloodmap.format import encode_map, parse_map
from bloodmap.model import record_fields, record_extra

PROJECT = Path(__file__).resolve().parent


class EditConflict(ValueError):
    """The live map no longer agrees with the reviewed field preconditions."""


def digest(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def _fields(disk, kind, index, extension=False):
    if kind == "sky" and not extension:
        return disk.sky
    objects = getattr(disk, kind + "s")
    if not 0 <= index < len(objects):
        raise EditConflict(f"{kind} {index} no longer exists")
    return (record_extra(objects[index]) or {}) if extension else record_fields(objects[index])


def apply_patch(map_path: Path, patch_path: Path, *, dry_run=False) -> dict:
    """Check every touched field before writing; unrelated manual edits survive."""
    map_path, patch_path = Path(map_path), Path(patch_path)
    if map_path.name.lower() == "e4l1-baseline.map":
        raise EditConflict("The reference baseline is immutable; edit E4L1-current.MAP")
    payload = map_path.read_bytes()
    source = parse_map(payload)
    if encode_map(source) != payload:
        raise EditConflict("Native read/write is not byte-exact; refusing to edit")
    patch_bytes = patch_path.read_bytes()
    patch = json.loads(patch_bytes)
    report_path = map_path.parent / "reports" / (patch["id"] + "-applied.json")
    previous = json.loads(report_path.read_text()) if report_path.exists() else None
    if previous and previous["patch_sha256"] != digest(patch_bytes):
        raise EditConflict("This pass was already applied with a different patch; create a new pass")
    builder = LevelBuilder(source.to_level_ir())
    work = builder.level
    changes = []
    for operation in patch["edits"]:
        kind, index = operation["kind"], operation["index"]
        base = _fields(work, kind, index)
        for field, value in operation.get("identity", {}).items():
            if base.get(field) != value:
                raise EditConflict(f"{kind} {index}: identity {field} changed; review indices in XMapEdit")
        for extension, key in ((False, "fields"), (True, "extra")):
            if not operation.get(key):
                continue
            current = _fields(work, kind, index, extension)
            for field, pair in operation.get(key, {}).items():
                before, after = pair
                default = -1 if field in {"marker_0", "marker_1", "target", "burn_source"} else 0
                actual = current.get(field, default)
                if actual == after:
                    continue
                if actual != before:
                    raise EditConflict(f"{kind} {index} {field}: expected {before} or {after}, found {actual}; manual edit preserved")
                if extension:
                    builder.set_behavior(kind, index, **{field: after})
                    current = _fields(work, kind, index, True)
                else:
                    current[field] = after
                changes.append({"kind": kind, "index": index, "extension": extension,
                                "field": field, "before": before, "after": after})
    appended = {}
    for item in patch.get("sprites", []):
        name = item["name"]
        if previous and name in previous["sprites"]:
            index = previous["sprites"][name]
            base, extra = _fields(work, "sprite", index), _fields(work, "sprite", index, True)
            if any(base.get(k) != v for k, v in item["fields"].items()) or any(extra.get(k) != v for k, v in item.get("extra", {}).items()):
                raise EditConflict(f"Appended sprite {name} changed or was renumbered; refusing to duplicate it")
        else:
            matches = [i for i, sprite in enumerate(work.sprites)
                       if all(record_fields(sprite).get(k) == v for k, v in item["fields"].items())
                       and all((record_extra(sprite) or {}).get(k) == v for k, v in item.get("extra", {}).items())]
            if len(matches) > 1:
                raise EditConflict(f"Several sprites match {name}; review instead of adding a duplicate")
            if matches:
                index = matches[0]  # recover a map saved before its pass report
            else:
                index = builder.add_sprite(**item["fields"])
                if item.get("extra"):
                    builder.set_behavior("sprite", index, **item["extra"])
        appended[name] = index
    target = work.to_disk_map()
    target_bytes = encode_map(target)
    read_back = parse_map(target_bytes)
    errors = [d for d in validate_map(read_back) if d.severity == "error"]
    if errors:
        raise EditConflict(f"Edited map fails structural validation: {errors[0]}")
    # A pass may add sprites and extensions, never replace the source layout.
    assert len(target.sectors) == len(source.sectors) and len(target.walls) == len(source.walls)
    for name in ("start_x", "start_y", "start_z", "start_angle", "start_sector"):
        assert source.header[name] == target.header[name]
    for before, after in zip(source.walls, target.walls):
        assert all(record_fields(before)[k] == record_fields(after)[k]
                   for k in ("x", "y", "point2", "next_wall", "next_sector"))
    if previous and target_bytes == payload:
        return {"id": patch["id"], "unchanged": True, "map_sha256": digest(payload), "sprites": appended}
    report = {
        "id": patch["id"], "patch_sha256": digest(patch_bytes),
        "before_sha256": digest(payload), "after_sha256": digest(target_bytes),
        "changes": changes, "sprites": appended,
        "counts": {k: len(getattr(read_back, k)) for k in ("sectors", "walls", "sprites")},
        "structural_errors": 0, "geometry_and_start_preserved": True,
        "dry_run": dry_run,
    }
    if dry_run:
        return report
    if map_path.read_bytes() != payload:
        raise EditConflict("Map was saved by another editor during this pass; no edits written")
    backup = map_path.parent / "snapshots" / (digest(payload) + ".MAP")
    backup.parent.mkdir(parents=True, exist_ok=True)
    if not backup.exists():
        backup.write_bytes(payload)
    temporary = map_path.with_suffix(".MAP.pending")
    if temporary.exists():
        raise EditConflict(f"Review existing interrupted write {temporary} before applying a pass")
    temporary.write_bytes(target_bytes)
    if map_path.read_bytes() != payload:
        temporary.unlink()
        raise EditConflict("Map changed while preparing the atomic write; no edits written")
    temporary.replace(map_path)
    report["backup"] = str(backup.relative_to(map_path.parent))
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("patch", type=Path)
    parser.add_argument("--map", type=Path, default=PROJECT / "E4L1-current.MAP")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    try:
        report = apply_patch(args.map, args.patch, dry_run=args.dry_run)
    except EditConflict as exc:
        parser.exit(1, f"Edit conflict: {exc}\n")
    print(json.dumps({k: v for k, v in report.items() if k != "changes"}, indent=2))


if __name__ == "__main__":
    main()
