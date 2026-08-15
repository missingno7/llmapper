from __future__ import annotations

import argparse
import copy
import hashlib
import json
import sys
from pathlib import Path
from typing import Any

from .analysis import channel_graph, corpus_statistics, geometry_view, render_svg, validate_map
from .build_ir import BuildIR
from .composition import (
    CompositionError, attach_fragment, connect_portals, connect_with_pathway, insert_fragment,
)
from .construction import ConstructionError
from .conversion import ConversionError, convert_build_ir
from .designs import build_first_puzzle_room
from .differential import compare_e3l1_pair
from .duke import DukeMapError, encode_duke_map, read_duke_map, write_duke_map
from .design import DesignUnderstandingError, design_fingerprint
from .e3l11 import E3L11ConversionError, convert_e3l11_to_blood
from .duke_semantics import analyze_duke_mechanisms
from .format import BloodMapError, SIGNATURE, encode_map, locate_offset, read_map, write_map
from .fragment import (
    FragmentError, LevelFragment, apply_fragment_in_place,
    extract_behavior_closed_fragment, extract_fragment,
)
from .model import LevelIR
from .oracle import (
    OracleError, run_eduke32_oracle, run_nblood_action_oracle, run_nblood_behavior_oracle,
    run_nblood_oracle,
)
from .recipe import RecipeError, build_composition_recipe
from .semantics import ObservationError


def _json(value: Any) -> str:
    return json.dumps(value, indent=2, sort_keys=True) + "\n"


def _write_text(path: str | None, value: str) -> None:
    if path:
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        Path(path).write_text(value, encoding="utf-8", newline="\n")
    else:
        sys.stdout.write(value)


def _map_files(directory: Path) -> list[Path]:
    return sorted(path for path in directory.iterdir() if path.is_file() and path.suffix.lower() == ".map")


def _game_for_path(path: str | Path) -> str:
    prefix = Path(path).read_bytes()[:4]
    if prefix == SIGNATURE:
        return "blood"
    if len(prefix) == 4 and int.from_bytes(prefix, "little", signed=True) == 7:
        return "duke3d"
    raise ValueError(f"cannot detect MAP game/format for {path}")


def _read_build_ir(path: str | Path):
    return read_map(path).to_build_ir() if _game_for_path(path) == "blood" else read_duke_map(path).to_build_ir()


def _inventory(directory: Path) -> dict[str, Any]:
    files = []
    versions: dict[str, int] = {}
    for path in _map_files(directory):
        data = path.read_bytes()
        entry: dict[str, Any] = {
            "filename": path.name, "size": len(data),
            "sha256": hashlib.sha256(data).hexdigest(),
        }
        try:
            game = _game_for_path(path)
            disk = read_map(path) if game == "blood" else read_duke_map(path)
            version = f"0x{disk.version:04x}" if game == "blood" else str(disk.version)
            versions[version] = versions.get(version, 0) + 1
            entry.update(
                detected_format=disk.format_name, game=game, map_version=version,
                sectors=len(disk.sectors), walls=len(disk.walls), sprites=len(disk.sprites),
                status="ok",
            )
            if game == "blood":
                entry["crc32"] = f"{disk.source_crc32:08x}"
        except Exception as exc:
            entry.update(detected_format="unknown", status="error", error=str(exc))
        files.append(entry)
    ignored = sorted(path.name for path in directory.iterdir() if path.is_file() and path.suffix.lower() != ".map")
    return {
        "directory": str(directory), "maps_discovered": len(files), "versions": versions,
        "ignored_non_map_files": ignored, "files": files,
    }


def cmd_corpus(args: argparse.Namespace) -> int:
    directory = Path(args.directory)
    inventory = _inventory(directory)
    _write_text(args.output, _json(inventory))
    return 1 if any(item["status"] != "ok" for item in inventory["files"]) else 0


def cmd_duke_mechanisms(args: argparse.Namespace) -> int:
    """Build a reusable evidence corpus for classic Duke mechanisms."""
    directory = Path(args.directory)
    maps: list[dict[str, Any]] = []
    aggregate: dict[str, int] = {}
    for path in _map_files(directory):
        try:
            inventory = analyze_duke_mechanisms(read_duke_map(path))
        except DukeMapError as exc:
            maps.append({"map": path.name, "status": "error", "error": str(exc)})
            continue
        maps.append({"map": path.name, "status": "ok", "inventory": inventory})
        for lotag, count in inventory["counts_by_effector_lotag"].items():
            aggregate[lotag] = aggregate.get(lotag, 0) + count
    _write_text(args.output, _json({
        "$schema": "llmapper.duke-mechanism-corpus",
        "schema_version": 1,
        "directory": str(directory),
        "maps": maps,
        "aggregate_effector_lotags": dict(sorted(aggregate.items(), key=lambda item: int(item[0]))),
    }))
    return 0


def cmd_dump(args: argparse.Namespace) -> int:
    ir = read_map(args.map).to_level_ir()
    _write_text(args.output, _json(ir.to_dict()))
    return 0


def cmd_build(args: argparse.Namespace) -> int:
    value = json.loads(Path(args.json).read_text(encoding="utf-8"))
    disk = LevelIR.from_dict(value).to_disk_map()
    write_map(disk, args.output)
    return 0


def cmd_validate(args: argparse.Namespace) -> int:
    game = _game_for_path(args.map)
    disk = read_map(args.map) if game == "blood" else read_duke_map(args.map)
    diagnostics = validate_map(disk) if game == "blood" else disk.to_build_ir().validate()
    errors = sum(x.severity == "error" for x in diagnostics)
    warnings = sum(x.severity == "warning" for x in diagnostics)
    if args.json:
        print(_json({"file": args.map, "game": game, "errors": errors, "warnings": warnings,
                     "diagnostics": [x.__dict__ for x in diagnostics]}), end="")
    else:
        for item in diagnostics:
            print(f"{item.severity.upper():7} {item.code:26} {item.location}: {item.message}")
        print(f"{args.map}: {errors} error(s), {warnings} warning(s)")
    return 1 if errors else 0


def cmd_roundtrip(args: argparse.Namespace) -> int:
    path = Path(args.map)
    original = path.read_bytes()
    game = _game_for_path(path)
    disk = read_map(path) if game == "blood" else read_duke_map(path)
    rebuilt = encode_map(disk) if game == "blood" else encode_duke_map(disk)
    if rebuilt == original:
        print(f"PASS {path}: byte-exact ({len(original)} bytes)")
        if args.output:
            Path(args.output).write_bytes(rebuilt)
        return 0
    limit = min(len(original), len(rebuilt))
    offset = next((i for i in range(limit) if original[i] != rebuilt[i]), limit)
    a = original[offset] if offset < len(original) else None
    b = rebuilt[offset] if offset < len(rebuilt) else None
    location = locate_offset(disk, offset) if game == "blood" else "Duke v7 record stream"
    print(f"FAIL {path}: first mismatch at 0x{offset:08x}; original={a!r}, rebuilt={b!r}; {location}")
    return 1


def cmd_roundtrip_all(args: argparse.Namespace) -> int:
    results = []
    failed = 0
    for path in _map_files(Path(args.directory)):
        try:
            original = path.read_bytes()
            game = _game_for_path(path)
            disk = read_map(path) if game == "blood" else read_duke_map(path)
            encoder = encode_map if game == "blood" else encode_duke_map
            rebuilt = encoder(disk)
            ir_rebuilt = encoder(disk.to_build_ir().to_native_disk_map())
            diagnostics = validate_map(disk) if game == "blood" else disk.to_build_ir().validate()
            errors = sum(x.severity == "error" for x in diagnostics)
            item = {
                "filename": path.name, "game": game, "parse": True, "byte_exact": original == rebuilt,
                "ir_byte_exact": original == ir_rebuilt, "validation_errors": errors,
                "validation_warnings": sum(x.severity == "warning" for x in diagnostics),
            }
        except Exception as exc:
            item = {"filename": path.name, "parse": False, "error": str(exc)}
        ok = item.get("parse") and item.get("byte_exact") and item.get("ir_byte_exact") and item.get("validation_errors") == 0
        item["status"] = "pass" if ok else "fail"
        failed += not ok
        results.append(item)
        if not args.json:
            print(f"{item['status'].upper():4} {path.name}" + (f": {item.get('error')}" if not ok and item.get("error") else ""))
    summary = {"maps": len(results), "passed": len(results) - failed, "failed": failed, "results": results}
    if args.json:
        print(_json(summary), end="")
    else:
        print(f"{summary['passed']}/{summary['maps']} maps passed parse, byte roundtrip, IR roundtrip, and validation")
    return 1 if failed else 0


def cmd_dump_build_ir(args: argparse.Namespace) -> int:
    _write_text(args.output, _json(_read_build_ir(args.map).to_dict()))
    return 0


def cmd_build_build_ir(args: argparse.Namespace) -> int:
    build = BuildIR.from_dict(json.loads(Path(args.json).read_text(encoding="utf-8")))
    disk = build.to_native_disk_map()
    diagnostics = validate_map(disk) if build.source_game == "blood" else disk.to_build_ir().validate()
    errors = [item for item in diagnostics if item.severity == "error"]
    if errors:
        raise ValueError(f"BuildIR output has {len(errors)} structural error(s); first: {errors[0].message}")
    Path(args.output).parent.mkdir(parents=True, exist_ok=True)
    if build.source_game == "blood":
        write_map(disk, args.output)
        reparsed = read_map(args.output)
    else:
        write_duke_map(disk, args.output)
        reparsed = read_duke_map(args.output)
    if len(reparsed.sectors) != len(build.sectors) or len(reparsed.walls) != len(build.walls):
        raise ValueError("written BuildIR output changed object counts during reparse")
    reparsed_diagnostics = validate_map(reparsed) if build.source_game == "blood" else reparsed.to_build_ir().validate()
    if any(item.severity == "error" for item in reparsed_diagnostics):
        raise ValueError("written BuildIR output failed structural validation after reparse")
    print(f"WROTE {args.output}: {build.source_game} BuildIR, reparsed and validated")
    return 0


def cmd_compare_pair(args: argparse.Namespace) -> int:
    _write_text(args.output, _json(compare_e3l1_pair(args.duke, args.blood)))
    return 0


def cmd_convert(args: argparse.Namespace) -> int:
    build = _read_build_ir(args.map)
    disk, report = convert_build_ir(build, args.to, policy=args.policy)
    target = "duke3d" if args.to in {"duke", "duke3d"} else "blood"
    Path(args.output).parent.mkdir(parents=True, exist_ok=True)
    if target == "blood":
        write_map(disk, args.output)
        reparsed = read_map(args.output)
        diagnostics = validate_map(reparsed)
    else:
        write_duke_map(disk, args.output)
        reparsed = read_duke_map(args.output)
        diagnostics = reparsed.to_build_ir().validate()
    errors = [item for item in diagnostics if item.severity == "error"]
    if errors:
        raise ConversionError(f"written conversion failed reparse validation: {errors[0].code}")
    payload = Path(args.output).read_bytes()
    report["output"] = {
        "path": str(args.output), "size": len(payload), "sha256": hashlib.sha256(payload).hexdigest(),
        "counts": {"sectors": len(reparsed.sectors), "walls": len(reparsed.walls), "sprites": len(reparsed.sprites)},
        "reparsed": True,
    }
    _write_text(args.report, _json(report))
    print(f"WROTE {args.output}: {build.source_game}->{target} {args.policy}, reparsed and validated")
    return 0


def cmd_convert_e3l11(args: argparse.Namespace) -> int:
    source = read_duke_map(args.map)
    disk, report = convert_e3l11_to_blood(
        source,
        duke_art=args.duke_art,
        blood_art=args.blood_art,
        blood_maps=args.blood_maps,
    )
    Path(args.output).parent.mkdir(parents=True, exist_ok=True)
    write_map(disk, args.output)
    reparsed = read_map(args.output)
    diagnostics = validate_map(reparsed)
    errors = [item for item in diagnostics if item.severity == "error"]
    if errors:
        raise E3L11ConversionError(f"written conversion failed validation: {errors[0].code}")
    payload = Path(args.output).read_bytes()
    report["output"] = {
        "path": str(args.output), "size": len(payload),
        "sha256": hashlib.sha256(payload).hexdigest(),
        "counts": {"sectors": len(reparsed.sectors), "walls": len(reparsed.walls), "sprites": len(reparsed.sprites)},
        "reparsed": True,
        "validation_warnings": sum(item.severity == "warning" for item in diagnostics),
    }
    _write_text(args.report, _json(report))
    print(f"WROTE {args.output}: Duke E3L11 -> playable Blood approximation, reparsed and validated")
    return 0


def cmd_diff(args: argparse.Namespace) -> int:
    a_path, b_path = Path(args.a), Path(args.b)
    a, b = a_path.read_bytes(), b_path.read_bytes()
    if a == b:
        print(f"IDENTICAL: {len(a)} bytes")
        return 0
    limit = min(len(a), len(b))
    offset = next((i for i in range(limit) if a[i] != b[i]), limit)
    try:
        location = locate_offset(read_map(a_path, verify_crc=False), offset)
    except Exception:
        location = "unavailable"
    av = f"{a[offset]:02x}" if offset < len(a) else "EOF"
    bv = f"{b[offset]:02x}" if offset < len(b) else "EOF"
    print(f"Byte mismatch at 0x{offset:08x}\n{a_path.name}: {av}\n{b_path.name}: {bv}\nlocation: {location}")
    return 1


def cmd_inspect(args: argparse.Namespace) -> int:
    disk = read_map(args.map)
    if args.sector is not None:
        i = args.sector
        if not 0 <= i < len(disk.sectors):
            raise BloodMapError(f"sector {i} is out of range")
        value = {"sector": i, "record": disk.to_level_ir().sectors[i], "geometry": geometry_view(disk)[i]}
    elif args.wall is not None:
        i = args.wall
        if not 0 <= i < len(disk.walls):
            raise BloodMapError(f"wall {i} is out of range")
        value = {"wall": i, "record": disk.to_level_ir().walls[i]}
    elif args.sprite is not None:
        i = args.sprite
        if not 0 <= i < len(disk.sprites):
            raise BloodMapError(f"sprite {i} is out of range")
        value = {"sprite": i, "record": disk.to_level_ir().sprites[i]}
    else:
        value = {
            "file": args.map, "version": f"0x{disk.version:04x}", "revision": disk.header["revision"],
            "player_start": disk.to_level_ir().player_start,
            "counts": {"sectors": len(disk.sectors), "walls": len(disk.walls), "sprites": len(disk.sprites)},
            "extended_counts": {
                "xsectors": sum(x.extra is not None for x in disk.sectors),
                "xwalls": sum(x.extra is not None for x in disk.walls),
                "xsprites": sum(x.extra is not None for x in disk.sprites),
            },
        }
    print(_json(value), end="")
    return 0


def cmd_channels(args: argparse.Namespace) -> int:
    print(_json(channel_graph(read_map(args.map), args.channel)), end="")
    return 0


def cmd_render(args: argparse.Namespace) -> int:
    selected = None
    for kind in ("sector", "wall", "sprite"):
        value = getattr(args, kind)
        if value is not None:
            selected = (kind, value)
    svg = render_svg(read_map(args.map), labels=not args.no_labels, selected=selected)
    Path(args.output).parent.mkdir(parents=True, exist_ok=True)
    Path(args.output).write_text(svg, encoding="utf-8", newline="\n")
    return 0


def cmd_stats(args: argparse.Namespace) -> int:
    maps = [(p.name, read_map(p)) for p in _map_files(Path(args.directory))]
    _write_text(args.output, _json(corpus_statistics(maps)))
    return 0


def _read_design_build(path: str | Path) -> tuple[str, BuildIR]:
    game = _game_for_path(path)
    if game == "blood":
        return game, read_map(path).to_build_ir()
    return game, read_duke_map(path).to_build_ir()


def cmd_design_fingerprint(args: argparse.Namespace) -> int:
    game, build = _read_design_build(args.map)
    fingerprint = design_fingerprint(build, _parse_id_set(args.sectors) if args.sectors else None)
    fingerprint["map"] = str(args.map)
    fingerprint["detected_game"] = game
    _write_text(args.output, _json(fingerprint))
    return 0


def _fingerprint_vector(fingerprint: dict[str, Any]) -> dict[str, float]:
    metrics = fingerprint["metrics"]
    paths = (
        ("topology.average_degree", metrics["topology"]["average_degree"]["value"]),
        ("topology.branching_ratio", metrics["topology"]["branching_ratio"]["value"]),
        ("topology.dead_end_ratio", metrics["topology"]["dead_end_ratio"]["value"]),
        ("topology.loopiness", metrics["topology"]["loopiness"]["value"]),
        ("topology.linearity", metrics["topology"]["linearity"]["value"]),
        ("space.mean_sector_area", metrics["space"]["mean_sector_area"]["value"]),
        ("space.mean_clear_height", metrics["space"]["mean_clear_height"]["value"]),
        ("space.vertical_range", metrics["space"]["vertical_range"]["value"]),
        ("space.connector_width_mean", metrics["space"]["connector_width_mean"]["value"]),
        ("architecture.repeated_shape_ratio", metrics["architecture"]["repeated_shape_ratio"]["value"]),
        ("architecture.irregularity_proxy", metrics["architecture"]["irregularity_proxy"]["value"]),
        ("architecture.material_diversity", metrics["architecture"]["material_diversity"]["value"]),
        ("visual.shade_mean", metrics["visual"]["shade_mean"]["value"]),
        ("visual.shade_range", metrics["visual"]["shade_range"]["value"]),
        ("gameplay.enemy_count", metrics["gameplay"]["enemy_count"]["value"]),
        ("gameplay.mechanism_density", metrics["gameplay"]["mechanism_density"]["value"]),
    )
    return {name: float(value) for name, value in paths if value is not None}


def _fingerprint_distance(left: dict[str, Any], right: dict[str, Any]) -> float:
    a, b = _fingerprint_vector(left), _fingerprint_vector(right)
    common = sorted(set(a) & set(b))
    if not common:
        return float("inf")
    # Log-scale large spatial values so area does not drown topology/gameplay.
    import math

    distance = 0.0
    for name in common:
        av, bv = a[name], b[name]
        if "area" in name or "height" in name or "width" in name or "range" in name:
            av, bv = math.log1p(abs(av)), math.log1p(abs(bv))
        denominator = max(1.0, abs(av), abs(bv))
        distance += abs(av - bv) / denominator
    return round(distance / len(common), 6)


def _motif_match(fingerprint: dict[str, Any], motif: str) -> tuple[bool, str]:
    """Apply a deliberately soft, evidence-backed retrieval heuristic.

    Motifs are search vocabulary, not structural truth.  The returned basis
    makes the threshold visible to an LLM or a human reviewing the corpus.
    """
    metrics = fingerprint["metrics"]
    topology, space, architecture = metrics["topology"], metrics["space"], metrics["architecture"]
    if motif == "loop":
        value = topology["loopiness"]["value"]
        return value > 0, f"loopiness={value} > 0"
    if motif == "branching":
        value = topology["branching_ratio"]["value"]
        return value >= 0.34, f"branching_ratio={value} >= 0.34"
    if motif == "vertical":
        vertical, clear = space["vertical_range"]["value"], space["mean_clear_height"]["value"]
        return vertical > max(4096, clear * 0.5), f"vertical_range={vertical} > max(4096, mean_clear_height*0.5)"
    if motif == "repeated-bays":
        value = architecture["repeated_shape_ratio"]["value"]
        # Real maps contain gradual scale variation, so retrieval uses a
        # lower soft signal than the stronger interpretation emitted by the
        # fingerprint itself.
        return value >= 0.1, f"repeated_shape_ratio={value} >= 0.1"
    if motif == "compressed":
        value = space["connector_width_mean"]["value"]
        return value is not None and value < 2048, f"connector_width_mean={value} < 2048"
    if motif == "arena":
        branching = topology["branching_ratio"]["value"]
        degree = topology["average_degree"]["value"]
        dead_ends = topology["dead_end_ratio"]["value"]
        return branching >= 0.2 and degree >= 1.5 and dead_ends <= 0.5, (
            f"branching_ratio={branching} >= 0.2, average_degree={degree} >= 1.5, "
            f"dead_end_ratio={dead_ends} <= 0.5"
        )
    raise ValueError(f"unknown design motif: {motif}")


def cmd_design_index(args: argparse.Namespace) -> int:
    directory = Path(args.directory)
    entries: list[dict[str, Any]] = []
    for path in _map_files(directory):
        try:
            game, build = _read_design_build(path)
            fingerprint = design_fingerprint(build)
            entries.append({"map": path.name, "path": str(path), "game": game, "fingerprint": fingerprint, "status": "ok"})
        except (DukeMapError, BloodMapError, DesignUnderstandingError, ValueError) as exc:
            entries.append({"map": path.name, "path": str(path), "status": "error", "error": str(exc)})
    _write_text(args.output, _json({
        "$schema": "bloodmap.design-index",
        "schema_version": 1,
        "directory": str(directory),
        "entries": entries,
    }))
    return 0


def cmd_design_search(args: argparse.Namespace) -> int:
    document = json.loads(Path(args.index).read_text(encoding="utf-8"))
    query = None
    if args.like:
        _game, query_build = _read_design_build(args.like)
        query = design_fingerprint(query_build)
    results: list[dict[str, Any]] = []
    for entry in document.get("entries", []):
        if entry.get("status") != "ok":
            continue
        fingerprint = entry["fingerprint"]
        if args.game and entry.get("game") != args.game:
            continue
        if args.mechanism:
            if args.mechanism not in fingerprint.get("source_mechanisms", {}).get("kinds", {}):
                continue
        match_basis = None
        if args.motif:
            matched, match_basis = _motif_match(fingerprint, args.motif)
            if not matched:
                continue
        if args.min_enemies is not None and fingerprint["metrics"]["gameplay"]["enemy_count"]["value"] < args.min_enemies:
            continue
        result = {"map": entry["map"], "path": entry["path"], "game": entry["game"], "evidence": fingerprint["evidence"], "interpretations": fingerprint["interpretations"]}
        if match_basis is not None:
            result["motif"] = args.motif
            result["match_basis"] = match_basis
        if query is not None:
            result["distance"] = _fingerprint_distance(query, fingerprint)
        results.append(result)
    results.sort(key=lambda item: (item.get("distance", 0), item["map"]))
    _write_text(args.output, _json({
        "$schema": "bloodmap.design-search",
        "schema_version": 1,
        "query": {"like": args.like, "game": args.game, "mechanism": args.mechanism, "motif": args.motif, "min_enemies": args.min_enemies},
        "results": results[:args.limit],
    }))
    return 0


def _parse_id_set(value: str) -> list[int]:
    result: set[int] = set()
    for part in value.split(","):
        part = part.strip()
        if not part:
            continue
        if "-" in part:
            first_text, last_text = part.split("-", 1)
            first, last = int(first_text), int(last_text)
            if last < first:
                raise ValueError(f"invalid descending range {part!r}")
            result.update(range(first, last + 1))
        else:
            result.add(int(part))
    if not result:
        raise ValueError("sector selection is empty")
    return sorted(result)


def cmd_extract(args: argparse.Namespace) -> int:
    fragment = extract_fragment(read_map(args.map).to_level_ir(), _parse_id_set(args.sectors))
    _write_text(args.output, _json(fragment.to_dict()))
    return 0


def cmd_extract_closed(args: argparse.Namespace) -> int:
    result = extract_behavior_closed_fragment(
        read_map(args.map).to_level_ir(),
        _parse_id_set(args.sectors),
        max_sectors=args.max_sectors,
    )
    _write_text(args.output, _json(result.fragment.to_dict()))
    if args.report:
        _write_text(args.report, _json(result.report()))
    return 0


def cmd_observe(args: argparse.Namespace) -> int:
    level = read_map(args.map).to_level_ir()
    sector_ids = _parse_id_set(args.sectors) if args.sectors is not None else None
    _write_text(args.output, _json(level.observe(sector_ids)))
    return 0


def cmd_apply_fragment(args: argparse.Namespace) -> int:
    source = read_map(args.map).to_level_ir()
    value = json.loads(Path(args.fragment).read_text(encoding="utf-8"))
    fragment = LevelFragment.from_dict(value)
    rebuilt = apply_fragment_in_place(source, fragment).to_disk_map()
    errors = [item for item in validate_map(rebuilt) if item.severity == "error"]
    if errors:
        raise FragmentError(f"fragment application produced {len(errors)} validation errors")
    Path(args.output).parent.mkdir(parents=True, exist_ok=True)
    write_map(rebuilt, args.output)
    read_map(args.output)
    print(f"WROTE {args.output}: same-source fragment applied, reparsed, and validated")
    return 0


def cmd_compose(args: argparse.Namespace) -> int:
    destination = read_map(args.map).to_level_ir()
    fragment = LevelFragment.from_dict(json.loads(Path(args.fragment).read_text(encoding="utf-8")))
    result = insert_fragment(
        destination, fragment, dx=args.x, dy=args.y, dz=args.z,
        quarter_turns=args.turns, pivot_x=args.pivot_x, pivot_y=args.pivot_y,
        channel_policy=args.channel_policy,
    )
    Path(args.output).parent.mkdir(parents=True, exist_ok=True)
    write_map(result.level.to_disk_map(), args.output)
    reparsed = read_map(args.output)
    if any(item.severity == "error" for item in validate_map(reparsed)):
        raise CompositionError("written composition failed reparse validation")
    if args.report:
        _write_text(args.report, _json(result.report()))
    print(f"WROTE {args.output}: fragment inserted, reparsed, and validated")
    return 0


def cmd_connect(args: argparse.Namespace) -> int:
    level = connect_portals(read_map(args.map).to_level_ir(), args.wall_a, args.wall_b)
    Path(args.output).parent.mkdir(parents=True, exist_ok=True)
    write_map(level.to_disk_map(), args.output)
    reparsed = read_map(args.output)
    if any(item.severity == "error" for item in validate_map(reparsed)):
        raise CompositionError("written portal connection failed reparse validation")
    print(f"WROTE {args.output}: walls {args.wall_a} and {args.wall_b} connected and validated")
    return 0


def _parse_point(value: str) -> tuple[int, int]:
    try:
        x_text, y_text = value.split(",", 1)
        return int(x_text), int(y_text)
    except ValueError as exc:
        raise ValueError(f"invalid point {value!r}; expected X,Y") from exc


def cmd_pathway(args: argparse.Namespace) -> int:
    level = read_map(args.map).to_level_ir()
    result = connect_with_pathway(
        level,
        args.wall_a,
        args.wall_b,
        via=[_parse_point(value) for value in args.via],
        sectors=args.sectors,
        max_step_height=args.max_step_height,
        min_opening=args.min_opening,
        clear_blocking=args.clear_blocking,
        allow_overlap=args.allow_overlap,
    )
    Path(args.output).parent.mkdir(parents=True, exist_ok=True)
    write_map(result.level.to_disk_map(), args.output)
    reparsed = read_map(args.output)
    if any(item.severity == "error" for item in validate_map(reparsed)):
        raise CompositionError("written pathway failed reparse validation")
    if args.report:
        _write_text(args.report, _json(result.report()))
    print(
        f"WROTE {args.output}: generated {len(result.sector_ids)}-sector pathway "
        f"between walls {args.wall_a} and {args.wall_b}, reparsed and validated"
    )
    return 0


def cmd_recipe(args: argparse.Namespace) -> int:
    value = json.loads(Path(args.recipe).read_text(encoding="utf-8"))
    result = build_composition_recipe(value, args.source_dir)
    Path(args.output).parent.mkdir(parents=True, exist_ok=True)
    write_map(result.level.to_disk_map(), args.output)
    reparsed = read_map(args.output)
    if any(item.severity == "error" for item in validate_map(reparsed)):
        raise RecipeError("written recipe result failed reparse validation")
    if args.report:
        _write_text(args.report, _json(result.report()))
    print(
        f"WROTE {args.output}: {len(result.operations)} recipe operations, "
        "reparsed and validated"
    )
    return 0


def cmd_design_first_room(args: argparse.Namespace) -> int:
    result = build_first_puzzle_room()
    Path(args.output).parent.mkdir(parents=True, exist_ok=True)
    write_map(result.level.to_disk_map(), args.output)
    reparsed = read_map(args.output)
    if any(item.severity == "error" for item in validate_map(reparsed)):
        raise ConstructionError("written first puzzle room failed reparse validation")
    if args.report:
        _write_text(args.report, _json(result.report))
    print(
        f"WROTE {args.output}: scratch puzzle room with {len(result.level.sectors)} sectors, "
        f"{len(result.level.walls)} walls, and {len(result.level.sprites)} sprites"
    )
    return 0


def cmd_oracle_nblood_action(args: argparse.Namespace) -> int:
    report = run_nblood_action_oracle(
        args.map,
        nblood=args.nblood,
        game_dir=args.game_dir,
        startup_timeout=args.startup_timeout,
        settle_seconds=args.settle_seconds,
        work_dir=args.work_dir,
    )
    _write_text(args.output, _json(report))
    return 0 if report["status"] == "pass" else 1


def cmd_oracle_eduke32(args: argparse.Namespace) -> int:
    report = run_eduke32_oracle(
        args.map, eduke32=args.eduke32, game_dir=args.game_dir,
        baseline=args.baseline, startup_timeout=args.startup_timeout,
        grace_seconds=args.seconds, work_dir=args.work_dir,
    )
    _write_text(args.output, _json(report))
    return 0 if report["status"] == "pass" else 1


def cmd_attach(args: argparse.Namespace) -> int:
    destination = read_map(args.map).to_level_ir()
    fragment = LevelFragment.from_dict(json.loads(Path(args.fragment).read_text(encoding="utf-8")))
    result = attach_fragment(
        destination,
        fragment,
        destination_wall=args.destination_wall,
        fragment_wall=args.fragment_wall,
        dz=args.z,
        quarter_turns=args.turns,
        channel_policy=args.channel_policy,
        clear_blocking=args.clear_blocking,
        allow_blocked=args.allow_blocked,
        allow_overlap=args.allow_overlap,
    )
    Path(args.output).parent.mkdir(parents=True, exist_ok=True)
    write_map(result.level.to_disk_map(), args.output)
    reparsed = read_map(args.output)
    if any(item.severity == "error" for item in validate_map(reparsed)):
        raise CompositionError("written attachment failed reparse validation")
    if args.report:
        _write_text(args.report, _json(result.report()))
    print(
        f"WROTE {args.output}: fragment wall {args.fragment_wall} attached to "
        f"destination wall {args.destination_wall}, reparsed and validated"
    )
    return 0


def cmd_oracle_nblood(args: argparse.Namespace) -> int:
    report = run_nblood_oracle(
        args.map, nblood=args.nblood, game_dir=args.game_dir,
        baseline=args.baseline, grace_seconds=args.seconds, work_dir=args.work_dir,
    )
    _write_text(args.output, _json(report))
    return 0 if report["status"] == "pass" else 1


def cmd_oracle_nblood_behavior(args: argparse.Namespace) -> int:
    report = run_nblood_behavior_oracle(
        nblood=args.nblood, game_dir=args.game_dir,
        startup_timeout=args.startup_timeout, settle_seconds=args.settle_seconds,
        work_dir=args.work_dir,
    )
    _write_text(args.output, _json(report))
    return 0 if report["status"] == "pass" else 1


def cmd_transform(args: argparse.Namespace) -> int:
    game = _game_for_path(args.map)
    ir = _read_build_ir(args.map)
    if args.operation == "translate":
        ir.translate(args.x, args.y, args.z)
    elif args.operation == "rotate":
        ir.rotate_quarter_turns(args.turns, args.pivot_x, args.pivot_y)
    transformed = ir.to_native_disk_map()
    errors = [
        d for d in (validate_map(transformed) if game == "blood" else transformed.to_build_ir().validate())
        if d.severity == "error"
    ]
    if errors:
        raise BloodMapError(f"transformation produced {len(errors)} validation errors; first: {errors[0].message}")
    (write_map if game == "blood" else write_duke_map)(transformed, args.output)
    # Reparse is part of the command's contract.
    reparsed = read_map(args.output) if game == "blood" else read_duke_map(args.output)
    reparsed_diagnostics = validate_map(reparsed) if game == "blood" else reparsed.to_build_ir().validate()
    if any(d.severity == "error" for d in reparsed_diagnostics):
        raise BloodMapError("written transformation failed reparse validation")
    print(f"WROTE {args.output}: {args.operation}, reparsed and validated")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="llmapper", description="Lossless Blood and Duke3D Build MAP tooling")
    sub = parser.add_subparsers(dest="command", required=True)

    p = sub.add_parser("corpus", help="inventory every file in a map directory")
    p.add_argument("directory"); p.add_argument("-o", "--output"); p.set_defaults(func=cmd_corpus)
    p = sub.add_parser("duke-mechanisms", help="derive a semantic mechanism corpus from classic Duke3D MAPs")
    p.add_argument("directory")
    p.add_argument("-o", "--output", help="write JSON; defaults to stdout")
    p.set_defaults(func=cmd_duke_mechanisms)
    p = sub.add_parser("dump", help="write canonical Level IR JSON")
    p.add_argument("map"); p.add_argument("-o", "--output"); p.set_defaults(func=cmd_dump)
    p = sub.add_parser("dump-build", help="write game-neutral BuildIR JSON for Blood or Duke3D")
    p.add_argument("map"); p.add_argument("-o", "--output"); p.set_defaults(func=cmd_dump_build_ir)
    p = sub.add_parser("build-build", help="build a native MAP from game-neutral BuildIR JSON")
    p.add_argument("json"); p.add_argument("-o", "--output", required=True); p.set_defaults(func=cmd_build_build_ir)
    p = sub.add_parser("build", help="build a MAP from Level IR JSON")
    p.add_argument("json"); p.add_argument("-o", "--output", required=True); p.set_defaults(func=cmd_build)
    p = sub.add_parser("validate", help="validate Build/Blood structure")
    p.add_argument("map"); p.add_argument("--json", action="store_true"); p.set_defaults(func=cmd_validate)
    p = sub.add_parser("roundtrip", help="test byte-exact parse/write")
    p.add_argument("map"); p.add_argument("-o", "--output"); p.set_defaults(func=cmd_roundtrip)
    p = sub.add_parser("roundtrip-all", help="test parsing, disk/IR roundtrips, and validation")
    p.add_argument("directory"); p.add_argument("--json", action="store_true"); p.set_defaults(func=cmd_roundtrip_all)
    p = sub.add_parser("compare-e3l1", help="differentially analyze Duke E3L1 and Blood DNE3L1")
    p.add_argument("--duke", default="maps/duke3d/E3L1.MAP")
    p.add_argument("--blood", default="maps/blood/DNE3L1.MAP")
    p.add_argument("-o", "--output")
    p.set_defaults(func=cmd_compare_pair)
    p = sub.add_parser("convert", help="convert Blood/Duke3D through BuildIR with an explicit fidelity policy")
    p.add_argument("map")
    p.add_argument("--to", choices=("blood", "duke", "duke3d"), required=True)
    p.add_argument("--policy", choices=("strict", "semantic", "geometry-only"), default="geometry-only")
    p.add_argument("--report", help="write the required conversion fidelity report")
    p.add_argument("-o", "--output", required=True)
    p.set_defaults(func=cmd_convert)
    p = sub.add_parser(
        "convert-e3l11",
        help="convert Duke3D E3L11 to a playable Blood approximation with native mechanisms",
    )
    p.add_argument("map", nargs="?", default="maps/duke3d/E3L11.MAP")
    p.add_argument("--duke-art", default="reference/duke3d")
    p.add_argument("--blood-art", default="reference/blood")
    p.add_argument("--blood-maps", default="maps/blood")
    p.add_argument("--report", help="write the detailed fidelity and unsupported-feature report")
    p.add_argument("-o", "--output", required=True)
    p.set_defaults(func=cmd_convert_e3l11)
    p = sub.add_parser("diff", help="locate the first structural byte difference")
    p.add_argument("a"); p.add_argument("b"); p.set_defaults(func=cmd_diff)
    p = sub.add_parser("inspect", help="show a concise map or object observation")
    p.add_argument("map"); p.add_argument("--sector", type=int); p.add_argument("--wall", type=int); p.add_argument("--sprite", type=int); p.set_defaults(func=cmd_inspect)
    p = sub.add_parser("channels", help="derive the Blood TX/RX graph")
    p.add_argument("map"); p.add_argument("--channel", type=int); p.set_defaults(func=cmd_channels)
    p = sub.add_parser("render", help="render a deterministic top-down SVG")
    p.add_argument("map"); p.add_argument("-o", "--output", required=True); p.add_argument("--no-labels", action="store_true")
    p.add_argument("--sector", type=int); p.add_argument("--wall", type=int); p.add_argument("--sprite", type=int); p.set_defaults(func=cmd_render)
    p = sub.add_parser("stats", help="generate corpus geometry/gameplay statistics")
    p.add_argument("directory"); p.add_argument("-o", "--output"); p.set_defaults(func=cmd_stats)
    p = sub.add_parser("design-fingerprint", help="measure a level or region as grounded design characteristics")
    p.add_argument("map")
    p.add_argument("--sectors", help="optional comma-separated sector IDs/ranges")
    p.add_argument("-o", "--output", help="write JSON; defaults to stdout")
    p.set_defaults(func=cmd_design_fingerprint)
    p = sub.add_parser("design-index", help="index Blood and Duke3D maps by design fingerprint")
    p.add_argument("directory"); p.add_argument("-o", "--output", required=True); p.set_defaults(func=cmd_design_index)
    p = sub.add_parser("design-search", help="retrieve maps by multi-dimensional design similarity or evidence")
    p.add_argument("index")
    p.add_argument("--like", help="rank by fingerprint similarity to this MAP")
    p.add_argument("--game", choices=("blood", "duke3d"))
    p.add_argument("--mechanism", help="require a source mechanism kind")
    p.add_argument("--motif", choices=("arena", "branching", "compressed", "loop", "repeated-bays", "vertical"), help="require a soft structural motif heuristic")
    p.add_argument("--min-enemies", type=int)
    p.add_argument("--limit", type=int, default=10)
    p.add_argument("-o", "--output", help="write JSON; defaults to stdout")
    p.set_defaults(func=cmd_design_search)
    p = sub.add_parser("extract", help="extract selected sectors into a self-describing fragment")
    p.add_argument("map"); p.add_argument("--sectors", required=True, help="comma-separated IDs/ranges, e.g. 1,4-7")
    p.add_argument("-o", "--output", required=True); p.set_defaults(func=cmd_extract)
    p = sub.add_parser(
        "extract-closed",
        help="extract a room plus sectors required by its gameplay dependencies",
    )
    p.add_argument("map")
    p.add_argument("--sectors", required=True, help="comma-separated IDs/ranges")
    p.add_argument("--max-sectors", type=int, default=256)
    p.add_argument("--report", help="write closure/dependency report JSON")
    p.add_argument("-o", "--output", required=True)
    p.set_defaults(func=cmd_extract_closed)
    p = sub.add_parser("observe", help="emit an LLM-friendly LevelIR semantic observation")
    p.add_argument("map")
    p.add_argument("--sectors", help="optional detailed sector IDs/ranges; omission emits the level index")
    p.add_argument("-o", "--output", help="write JSON observation; defaults to stdout")
    p.set_defaults(func=cmd_observe)
    p = sub.add_parser("apply-fragment", help="apply a fragment back to the exact same source map")
    p.add_argument("map"); p.add_argument("fragment"); p.add_argument("-o", "--output", required=True)
    p.set_defaults(func=cmd_apply_fragment)
    p = sub.add_parser("compose", help="insert a fragment with deterministic allocation")
    p.add_argument("map", help="destination MAP")
    p.add_argument("fragment", help="LevelFragment JSON")
    p.add_argument("-o", "--output", required=True)
    p.add_argument("--report", help="write allocation/dependency report JSON")
    p.add_argument("--x", type=int, default=0); p.add_argument("--y", type=int, default=0); p.add_argument("--z", type=int, default=0)
    p.add_argument("--turns", type=int, default=0); p.add_argument("--pivot-x", type=int, default=0); p.add_argument("--pivot-y", type=int, default=0)
    p.add_argument("--channel-policy", choices=("error", "remap"), default="error")
    p.set_defaults(func=cmd_compose)
    p = sub.add_parser("connect", help="connect reversed coincident one-sided walls")
    p.add_argument("map"); p.add_argument("--wall-a", type=int, required=True); p.add_argument("--wall-b", type=int, required=True)
    p.add_argument("-o", "--output", required=True); p.set_defaults(func=cmd_connect)
    p = sub.add_parser("pathway", help="generate a corridor/stair strip between two room walls")
    p.add_argument("map")
    p.add_argument("--wall-a", type=int, required=True)
    p.add_argument("--wall-b", type=int, required=True)
    p.add_argument(
        "--via", action="append", default=[], metavar="X,Y",
        help="optional centerline waypoint; repeat to route around geometry",
    )
    p.add_argument("--sectors", type=int, help="explicit number of generated pathway sectors")
    p.add_argument("--max-step-height", type=int, default=2048)
    p.add_argument("--min-opening", type=int, default=8192)
    p.add_argument("--clear-blocking", action="store_true")
    p.add_argument("--allow-overlap", action="store_true")
    p.add_argument("--report")
    p.add_argument("-o", "--output", required=True)
    p.set_defaults(func=cmd_pathway)
    p = sub.add_parser("recipe", help="build an allocation-aware LevelIR composition recipe")
    p.add_argument("recipe", help="composition recipe JSON")
    p.add_argument("--source-dir", required=True, help="directory containing referenced MAP files")
    p.add_argument("--report", help="write full closure/composition report JSON")
    p.add_argument("-o", "--output", required=True)
    p.set_defaults(func=cmd_recipe)
    p = sub.add_parser(
        "design-first-room",
        help="build the scratch-authored two-switch introductory puzzle room",
    )
    p.add_argument("--report", help="write construction, clearance, and channel report JSON")
    p.add_argument("-o", "--output", required=True)
    p.set_defaults(func=cmd_design_first_room)
    p = sub.add_parser("attach", help="align, insert, and portal-connect an extracted room")
    p.add_argument("map", help="destination MAP")
    p.add_argument("fragment", help="LevelFragment JSON")
    p.add_argument("--destination-wall", type=int, required=True)
    p.add_argument("--fragment-wall", type=int, required=True)
    p.add_argument("--z", type=int, default=0, help="vertical offset applied to the fragment")
    p.add_argument("--turns", type=int, choices=range(4), help="force a quarter-turn count; default chooses automatically")
    p.add_argument("--channel-policy", choices=("error", "remap"), default="error")
    blocking = p.add_mutually_exclusive_group()
    blocking.add_argument("--clear-blocking", action="store_true", help="clear movement-blocking flags on the portal walls")
    blocking.add_argument("--allow-blocked", action="store_true", help="allow an intentionally blocked or vertically closed portal")
    p.add_argument(
        "--allow-overlap", action="store_true",
        help="allow intentional stacked/intersecting XY geometry and report conflicts",
    )
    p.add_argument("--report", help="write placement/allocation/dependency report JSON")
    p.add_argument("-o", "--output", required=True)
    p.set_defaults(func=cmd_attach)
    p = sub.add_parser("oracle-nblood", help="run a bounded external NBlood MAP-load smoke test")
    p.add_argument("map", help="candidate MAP")
    p.add_argument("--baseline", help="known-good MAP checked in the same environment")
    p.add_argument("--nblood", required=True, help="path to NBlood executable")
    p.add_argument("--game-dir", required=True, help="path to local Blood/NBlood game data")
    p.add_argument("--seconds", type=float, default=5.0, help="required healthy runtime, 1..60")
    p.add_argument("--work-dir", help="preserve per-probe logs under this ignored directory")
    p.add_argument("-o", "--output", help="write JSON report; defaults to stdout")
    p.set_defaults(func=cmd_oracle_nblood)
    p = sub.add_parser("oracle-eduke32", help="run a bounded external EDuke32 MAP-load smoke test")
    p.add_argument("map", help="candidate Duke3D v7 MAP")
    p.add_argument("--baseline", help="known-good Duke3D MAP checked in the same environment")
    p.add_argument("--eduke32", required=True, help="path to EDuke32 executable")
    p.add_argument("--game-dir", required=True, help="path to local Duke3D game data")
    p.add_argument("--startup-timeout", type=float, default=30.0)
    p.add_argument("--seconds", type=float, default=3.0, help="healthy runtime after board load, 1..60")
    p.add_argument("--work-dir", help="preserve per-probe logs under this ignored directory")
    p.add_argument("-o", "--output", help="write JSON report; defaults to stdout")
    p.set_defaults(func=cmd_oracle_eduke32)
    p = sub.add_parser(
        "oracle-nblood-behavior",
        help="compare a synthetic trigger/Z-motion scenario before and after composition",
    )
    p.add_argument("--nblood", required=True, help="path to NBlood executable")
    p.add_argument("--game-dir", required=True, help="path to local Blood/NBlood game data")
    p.add_argument("--startup-timeout", type=float, default=15.0)
    p.add_argument("--settle-seconds", type=float, default=2.0)
    p.add_argument("--work-dir", help="preserve generated MAPs and screenshots under this ignored directory")
    p.add_argument("-o", "--output", help="write JSON report; defaults to stdout")
    p.set_defaults(func=cmd_oracle_nblood_behavior)
    p = sub.add_parser(
        "oracle-nblood-action",
        help="press Use once in a MAP and require a stable visible state change",
    )
    p.add_argument("map", help="candidate MAP positioned in front of the intended interaction")
    p.add_argument("--nblood", required=True, help="path to NBlood executable")
    p.add_argument("--game-dir", required=True, help="path to local Blood/NBlood game data")
    p.add_argument("--startup-timeout", type=float, default=15.0)
    p.add_argument("--settle-seconds", type=float, default=2.0)
    p.add_argument("--work-dir", help="preserve logs and screenshots under this ignored directory")
    p.add_argument("-o", "--output", help="write JSON report; defaults to stdout")
    p.set_defaults(func=cmd_oracle_nblood_action)

    p = sub.add_parser("transform", help="apply a safe IR transformation")
    p.add_argument("map"); p.add_argument("-o", "--output", required=True)
    ops = p.add_subparsers(dest="operation", required=True)
    q = ops.add_parser("translate"); q.add_argument("--x", type=int, required=True); q.add_argument("--y", type=int, required=True); q.add_argument("--z", type=int, default=0)
    q = ops.add_parser("rotate"); q.add_argument("--turns", type=int, required=True); q.add_argument("--pivot-x", type=int, default=0); q.add_argument("--pivot-y", type=int, default=0)
    p.set_defaults(func=cmd_transform)
    return parser


def main(argv: list[str] | None = None) -> int:
    try:
        args = build_parser().parse_args(argv)
        return int(args.func(args))
    except (BloodMapError, CompositionError, ConstructionError, ConversionError, DukeMapError, E3L11ConversionError, FragmentError, ObservationError, OracleError, RecipeError, OSError, ValueError, KeyError, json.JSONDecodeError) as exc:
        print(f"bloodmap: error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
