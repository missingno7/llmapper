from __future__ import annotations

import copy
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .analysis import validate_map
from .composition import (
    CompositionError, find_layout_conflicts,
)
from .format import read_map
from .model import LevelIR


class RecipeError(ValueError):
    pass


@dataclass
class RecipeResult:
    level: LevelIR
    operations: list[dict[str, Any]]

    def report(self) -> dict[str, Any]:
        return {
            "operation": "build_composition_recipe",
            "operations": self.operations,
            "result_counts": {
                "sectors": len(self.level.sectors),
                "walls": len(self.level.walls),
                "sprites": len(self.level.sprites),
            },
        }


def _source_path(source_dir: Path, value: Any) -> Path:
    name = str(value)
    if Path(name).name != name:
        raise RecipeError(f"recipe source must be a filename, got {name!r}")
    path = source_dir / name
    if not path.is_file():
        raise RecipeError(f"recipe source does not exist: {path}")
    return path


def build_composition_recipe(
    value: dict[str, Any], source_dir: str | Path,
) -> RecipeResult:
    """Build a LevelIR from a deterministic, allocation-aware composition recipe."""
    if value.get("$schema") != "bloodmap.composition-recipe" or int(value.get("schema_version", -1)) != 1:
        raise RecipeError("unsupported composition recipe schema")
    source_root = Path(source_dir)
    base_path = _source_path(source_root, value["base"])
    level = read_map(base_path).to_level_ir()
    operation_reports: list[dict[str, Any]] = []
    allocations: dict[str, dict[str, dict[int, int]]] = {}

    def resolve_wall(reference: Any) -> int:
        if isinstance(reference, int):
            return reference
        if not isinstance(reference, dict):
            raise RecipeError(f"invalid wall reference {reference!r}")
        if "absolute" in reference:
            return int(reference["absolute"])
        operation_id = str(reference.get("operation", ""))
        if operation_id not in allocations:
            raise RecipeError(f"wall reference uses unknown operation {operation_id!r}")
        fragment_id = int(reference["fragment_wall"])
        try:
            return allocations[operation_id]["wall"][fragment_id]
        except KeyError as exc:
            raise RecipeError(
                f"operation {operation_id!r} has no fragment wall {fragment_id}"
            ) from exc

    seen_ids: set[str] = set()
    for index, operation_value in enumerate(value.get("operations", [])):
        operation = copy.deepcopy(operation_value)
        kind = str(operation.pop("op", ""))
        operation_id = str(operation.pop("id", f"operation_{index}"))
        if operation_id in seen_ids:
            raise RecipeError(f"duplicate recipe operation id {operation_id!r}")
        seen_ids.add(operation_id)

        if kind in {"attach", "insert"}:
            source_path = _source_path(source_root, operation.pop("source"))
            requested = [int(item) for item in operation.pop("sectors")]
            closure = read_map(source_path).to_level_ir().extract_closed(
                requested, max_sectors=int(operation.pop("max_sectors", 256)),
            )
            allow_unresolved = bool(operation.pop("allow_unresolved_gameplay", False))
            if closure.unresolved_relationships and not allow_unresolved:
                first = closure.unresolved_relationships[0]
                raise RecipeError(
                    f"operation {operation_id!r} has unresolved gameplay dependency: "
                    f"{first.to_dict()}"
                )
            old_sector_count, old_wall_count = len(level.sectors), len(level.walls)
            if kind == "attach":
                operation["destination_wall"] = resolve_wall(operation["destination_wall"])
                result = level.attach(closure.fragment, **operation)
                level = result.level
                operation_report = result.report()
                composition = result.composition
            else:
                result = level.insert(closure.fragment, **operation)
                conflicts = find_layout_conflicts(
                    result.level,
                    existing_sector_count=old_sector_count,
                    existing_wall_count=old_wall_count,
                )
                if conflicts:
                    raise RecipeError(
                        f"operation {operation_id!r} inserts overlapping geometry: {conflicts[0]}"
                    )
                level = result.level
                operation_report = result.report()
                operation_report["layout_check"] = {"status": "pass", "conflicts": []}
                composition = result
            allocations[operation_id] = {
                name: dict(mapping.fragment_to_destination)
                for name, mapping in composition.allocations.items()
            }
            operation_reports.append({
                "id": operation_id,
                "op": kind,
                "source": source_path.name,
                "closure": closure.report(),
                "result": operation_report,
            })
            continue

        if kind == "pathway":
            wall_a = resolve_wall(operation.pop("wall_a"))
            wall_b = resolve_wall(operation.pop("wall_b"))
            if "via" in operation:
                operation["via"] = [tuple(map(int, point)) for point in operation["via"]]
            result = level.connect_pathway(wall_a, wall_b, **operation)
            level = result.level
            operation_reports.append({"id": operation_id, "op": kind, "result": result.report()})
            continue

        raise RecipeError(f"unsupported recipe operation {kind!r}")

    errors = [item for item in validate_map(level.to_disk_map()) if item.severity == "error"]
    if errors:
        first = errors[0]
        raise RecipeError(
            f"recipe result violates structure: {first.code} at {first.location}: {first.message}"
        )
    return RecipeResult(level=level, operations=operation_reports)
