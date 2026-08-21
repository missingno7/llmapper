"""Build a searchable decompiled-level project from one original MAP.

    python -m tools.decompile_project maps/blood/E2M3.MAP \\
        -o projects/e2m3-decompiled --art reference/blood

The exact ``LevelIR`` stays authoritative and is deliberately *not* written
here: it is 2.3 MB for E2M3 and reproducible byte-for-byte from the MAP with
``python -m bloodmap decompile``, so the project records the command and the
CRC instead of duplicating the corpus into the repository.

What the project does contain is the part that is expensive to recompute and
useful to search: the hierarchy as a reading view, the recovered architectural
structures, the ART vocabulary with local role aliases, and one JSONL index a
future authoring agent can grep.
"""

from __future__ import annotations

import argparse
import json
import pathlib
from collections import Counter, defaultdict
from typing import Any

from bloodmap.decompiler import decompile_level
from bloodmap.format import read_map
from bloodmap.structures import detect_structures

SCHEMA = "llmapper.decompiled-project"
SCHEMA_VERSION = 1

PLAYER_WIDTH = 384


def _top(counts: dict[str, int], limit: int = 4) -> list[dict[str, Any]]:
    ordered = sorted(counts.items(), key=lambda item: (-item[1], int(item[0])))
    return [{"tile": int(tile), "count": count} for tile, count in ordered[:limit]]


def _reading_node(node: dict[str, Any]) -> dict[str, Any]:
    """One hierarchy node without the exhaustive wall list that dwarfs it."""
    geometry = node.get("geometry") or {}
    record = {
        "id": node["id"],
        "kind": node["kind"],
        "name": node["name"],
        "parent": node["parent"],
        "children": list(node["children"]),
        "sectors": list(node["sources"]["sectors"]),
        "sprite_count": len(node["sources"]["sprites"]),
        "wall_count": len(node["sources"]["walls"]),
        "basis": list((node.get("provenance") or {}).get("basis") or []),
    }
    if geometry:
        record["player_relative"] = geometry["player_relative"]
        record["floor_z_range"] = geometry["floor_z_range"]
        record["ceiling_z_range"] = geometry["ceiling_z_range"]
    assets = node.get("material_usage") or {}
    record["dominant_assets"] = {
        role: _top(values) for role, values in assets.items() if values
    }
    if "structure" in node:
        record["structure"] = node["structure"]
    candidate = (node.get("provenance") or {}).get("spatial_candidate")
    if candidate:
        record["spatial_candidate"] = candidate
    return record


def _local_aliases(source, level) -> list[dict[str, Any]]:
    """Name this level's dominant tiles by the role they actually hold here.

    These are *local* roles.  ``MAIN_WALL`` means "the tile this map uses for
    most of its wall area", not a claim about what the tile depicts or how any
    other map uses it.  Exact identity stays underneath as ``blood:tile:N``.
    """
    by_role: dict[str, Counter[int]] = defaultdict(Counter)
    for sector in level.sectors:
        fields = sector["fields"]
        by_role["floor"][int(fields["floor_picnum"])] += 1
        by_role["ceiling"][int(fields["ceiling_picnum"])] += 1
    for wall in level.walls:
        by_role["wall"][int(wall["fields"]["picnum"])] += 1
    for sprite in level.sprites:
        by_role["sprite"][int(sprite["fields"]["picnum"])] += 1

    names = {"wall": "MAIN_WALL", "floor": "MAIN_FLOOR", "ceiling": "MAIN_CEILING",
             "sprite": "MAIN_SPRITE"}
    aliases: dict[int, dict[str, Any]] = {}
    for role, counter in by_role.items():
        for rank, (tile, count) in enumerate(counter.most_common(3)):
            alias = names[role] if rank == 0 else f"{names[role]}_{rank + 1}"
            aliases.setdefault(tile, {
                "asset": f"blood:tile:{tile}",
                "local_alias": alias,
                "local_role": role,
                "interpretation_status": "local_role_only",
                "note": "the role this tile holds in this level, not a claim about the tile",
            })
            aliases[tile].setdefault("counts", {})[role] = count

    catalog = {item["id"]: item for item in source.assets}
    for tile, record in aliases.items():
        verified = catalog.get(record["asset"], {}).get("verified_usage")
        if verified:
            record["verified_usage"] = verified
    return [aliases[tile] for tile in sorted(aliases)]


def build(map_path: pathlib.Path, out_dir: pathlib.Path) -> dict[str, Any]:
    disk = read_map(map_path)
    level = disk.to_level_ir()
    source = decompile_level(level, source_name=map_path.name)
    structures = detect_structures(level)

    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "references").mkdir(exist_ok=True)

    nodes = [_reading_node(item) for item in source.hierarchy["nodes"]]
    hierarchy = {
        "$schema": "llmapper.level-hierarchy-reading-view",
        "of": map_path.name,
        "model": source.hierarchy["model"],
        "primary_root": source.hierarchy["primary_root"],
        "limitations": source.hierarchy["limitations"],
        "structure_recovery": source.hierarchy["structure_recovery"],
        "counts": dict(Counter(item["kind"] for item in nodes)),
        "nodes": nodes,
        "relations": source.hierarchy["relations"],
    }
    (out_dir / "hierarchy.json").write_text(
        json.dumps(hierarchy, indent=1), encoding="utf-8",
    )
    (out_dir / "structures.json").write_text(
        json.dumps(structures, indent=1), encoding="utf-8",
    )
    aliases = _local_aliases(source, level)
    (out_dir / "assets.json").write_text(
        json.dumps({
            "$schema": "llmapper.level-asset-roles",
            "of": map_path.name,
            "model": "local roles for this level's dominant tiles; exact ids stay authoritative",
            "aliases": aliases,
            "full_catalog": source.assets,
        }, indent=1),
        encoding="utf-8",
    )

    # One line per searchable thing, so retrieval is grep-able without a loader.
    index_lines: list[str] = []
    for node in nodes:
        entry = {
            "id": node["id"], "kind": node["kind"], "map": map_path.stem,
            "sectors": len(node["sectors"]), "sprites": node["sprite_count"],
            "dominant_assets": node.get("dominant_assets", {}),
        }
        if "player_relative" in node:
            entry["player_relative"] = node["player_relative"]
        if "structure" in node:
            entry["structure_kind"] = node["structure"]["kind"]
            entry["structure_parameters"] = node["structure"]["parameters"]
        index_lines.append(json.dumps(entry, sort_keys=True))
    for item in structures["structures"]:
        if item["kind"] in {"overlook", "pit"}:
            index_lines.append(json.dumps({
                "id": item["id"], "kind": "relation", "relation": item["kind"],
                "map": map_path.stem, "sectors": item["sectors"],
                "toward": item["attaches_to"], "parameters": item["parameters"],
            }, sort_keys=True))
    (out_dir / "nodes.jsonl").write_text("\n".join(index_lines) + "\n", encoding="utf-8")

    provenance = {
        "$schema": SCHEMA,
        "schema_version": SCHEMA_VERSION,
        "of": map_path.name,
        "source_crc32": level.metadata.get("source_crc32"),
        "format": level.metadata.get("format"),
        "counts": {
            "sectors": len(level.sectors), "walls": len(level.walls),
            "sprites": len(level.sprites),
        },
        "authority": (
            "exact_level_ir; regenerate it rather than reading anything here as truth"
        ),
        "regenerate_exact_truth": (
            f"python -m bloodmap decompile {map_path.as_posix()} "
            f"-o {out_dir.as_posix()}/exact-level-source.json"
        ),
        "regenerate_this_project": (
            f"python -m tools.decompile_project {map_path.as_posix()} -o {out_dir.as_posix()}"
        ),
        "derived_not_verified": [
            "hierarchy grouping", "structure recovery", "local asset aliases",
        ],
    }
    (out_dir / "provenance.json").write_text(json.dumps(provenance, indent=1), encoding="utf-8")
    return provenance


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("map")
    parser.add_argument("-o", "--output", required=True)
    args = parser.parse_args(argv)
    provenance = build(pathlib.Path(args.map), pathlib.Path(args.output))
    print(json.dumps(provenance["counts"], indent=1))
    print(f"wrote {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
