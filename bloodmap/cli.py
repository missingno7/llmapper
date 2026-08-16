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
from .spatial import SpatialAnalysisError, analyze_spatial
from .contents import explain_mechanisms, inventory_map, multiplayer_layout
from .sight import SightError, depth_samples, line_of_sight, spawn_sight_report
from .player_space import (
    PlayerSpaceError, compare_transition, conversion_player_scale_report,
    focus_observation, inspect_connection, inspect_doom_space, inspect_space,
    material_player_scale, mine_build_spatial_corpus, mine_doom_spatial_corpus,
    player_profile, present_space,
)
from .experience import probe_progression, probe_route, probe_transition, probe_visibility
from .workspace import (
    append_decision, append_episode, append_evidence, initialize_project,
    make_level_slice, source_identity, store_level_slice,
)
from .e3l11 import E3L11ConversionError, PlayableConversionError, convert_playable_duke_to_blood
from .duke_semantics import analyze_duke_mechanisms
from .doom import DoomError, encode_wad, read_wad, wad_map, write_wad, doom_corpus_report
from .doom_convert import DoomConversionError, convert_doom_to_blood
from .doom_semantics import analyze_doom_mechanisms
from .format import BloodMapError, SIGNATURE, encode_map, locate_offset, read_map, write_map
from .fragment import (
    FragmentError, LevelFragment, apply_fragment_in_place,
    extract_behavior_closed_fragment, extract_fragment,
)
from .model import LevelIR
from .oracle import (
    OracleError, run_eduke32_oracle, run_gzdoom_oracle, run_nblood_action_oracle,
    run_nblood_behavior_oracle, run_nblood_oracle,
)
from .recipe import RecipeError, build_composition_recipe
from .semantics import ObservationError
from .materials import (
    MaterialsError, attach_appearance, contact_sheet_html, default_palette_path,
    dump_json, export_classification_batch, families_from_evidence,
    finalize_catalog, import_annotations, load_json, mine_blood_map, mine_doom_map,
    mine_duke_map, new_catalog, palette_vocabulary, query_materials, rank_candidates,
    retrieve_palette, select_authoring_kit, similar_palettes, summarize_catalog,
    write_review_packet,
)
from .art import read_art_directory, read_palette


def _json(value: Any) -> str:
    return json.dumps(value, indent=2, sort_keys=True) + "\n"


def _write_text(path: str | None, value: str) -> None:
    if path:
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        Path(path).write_text(value, encoding="utf-8", newline="\n")
    else:
        sys.stdout.write(value)


def _map_files(directory: Path, pattern: str | None = None) -> list[Path]:
    from fnmatch import fnmatch
    files = sorted(path for path in directory.iterdir() if path.is_file() and path.suffix.lower() == ".map")
    if pattern:
        files = [path for path in files if fnmatch(path.name, pattern)]
    return files


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


def cmd_doom_corpus(args: argparse.Namespace) -> int:
    from .doom import validate_doom_map

    wad = read_wad(args.wad)
    report = doom_corpus_report(wad, path=args.wad)
    rebuilt = encode_wad(wad)
    original = Path(args.wad).read_bytes()
    report["roundtrip_count"] = sum(1 for level in wad.maps if level.supported)
    report["wad_byte_exact"] = rebuilt == original
    report["validation_count"] = sum(
        1 for level in wad.maps
        if level.supported and not any(item["severity"] == "error" for item in validate_doom_map(level))
    )
    _write_text(args.output, _json(report))
    return 0 if report["supported_count"] == report["parse_count"] else 1


def cmd_doom_mechanisms(args: argparse.Namespace) -> int:
    wad = read_wad(args.wad)
    maps = []
    for level in wad.maps:
        if args.map and level.name != args.map.upper():
            continue
        maps.append(analyze_doom_mechanisms(level))
    _write_text(args.output, _json({
        "$schema": "llmapper.doom-mechanism-corpus",
        "schema_version": 1,
        "wad": str(args.wad),
        "maps": maps,
    }))
    return 0


def cmd_convert_doom(args: argparse.Namespace) -> int:
    wad = read_wad(args.wad)
    level = wad_map(wad, args.map)
    blood, report = convert_doom_to_blood(level)
    write_map(blood.to_disk_map(), args.output)
    if args.report:
        _write_text(args.report, _json(report))
    else:
        sys.stdout.write(_json({
            "output": args.output,
            "source": report["source"],
            "converted_counts": report["converted_counts"],
            "mechanisms_translated": report["mechanisms_translated"],
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
    disk, report = convert_playable_duke_to_blood(
        source,
        duke_art=args.duke_art,
        blood_art=args.blood_art,
        blood_maps=args.blood_maps,
        style_map=args.style_map,
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
    print(f"WROTE {args.output}: Duke playable -> Blood approximation, reparsed and validated")
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


def _load_optional_art(game: str, art: str | None, palette: str | None):
    if not art:
        return None, None, None
    tiles = read_art_directory(art)
    palette_path = Path(palette) if palette else default_palette_path(art, game)
    if palette_path is None:
        raise MaterialsError(f"no palette found for {game}; pass --palette")
    return tiles, read_palette(palette_path), str(palette_path)


def cmd_materials_mine(args: argparse.Namespace) -> int:
    catalog = new_catalog()
    if args.catalog and Path(args.catalog).exists() and args.merge:
        catalog = load_json(args.catalog)
    if args.maps:
        game = args.game
        tiles, palette, _palette_path = _load_optional_art(game, args.art, args.palette)
        if tiles and palette:
            attach_appearance(catalog, game, tiles, palette, source=args.art)
        for path in _map_files(Path(args.maps), args.glob):
            if game == "blood":
                mine_blood_map(catalog, read_map(path), map_name=path.name)
            elif game == "duke3d":
                mine_duke_map(catalog, read_duke_map(path), map_name=path.name)
            else:
                raise MaterialsError("--maps requires --game blood or duke3d")
    if args.wad:
        from .doom import read_wad
        wad = read_wad(args.wad)
        for level in wad.maps:
            if level.supported:
                mine_doom_map(catalog, level, map_name=level.name)
    finalize_catalog(catalog)
    if args.summary_only:
        _write_text(args.output, _json(summarize_catalog(catalog)))
    else:
        dump_json(args.output, catalog) if args.output else sys.stdout.write(_json(catalog))
    return 0


def cmd_materials_export_batch(args: argparse.Namespace) -> int:
    catalog = load_json(args.catalog)
    tiles = palettes = None
    if args.art:
        game = args.game
        loaded, palette, _path = _load_optional_art(game, args.art, args.palette)
        tiles = {game: loaded}
        palettes = {game: palette}
    batch = export_classification_batch(
        catalog, tiles=tiles, palettes=palettes, limit=args.limit, include_previews=not args.no_previews,
    )
    _write_text(args.output, _json(batch))
    return 0


def cmd_materials_import(args: argparse.Namespace) -> int:
    catalog = load_json(args.catalog)
    payload = load_json(args.input)
    import_annotations(catalog, payload)
    catalog["families"] = families_from_evidence(catalog)
    dump_json(args.output or args.catalog, catalog)
    _write_text(None, _json({
        "summary": summarize_catalog(catalog),
        "contradictions": catalog.get("contradictions") or [],
    }))
    return 0


def cmd_materials_audit(args: argparse.Namespace) -> int:
    catalog = load_json(args.catalog)
    tiles = palettes = None
    if args.art:
        loaded, palette, _path = _load_optional_art(args.game, args.art, args.palette)
        tiles = {args.game: loaded}
        palettes = {args.game: palette}
    html = contact_sheet_html(catalog, tiles=tiles, palettes=palettes, cluster_id=args.cluster)
    Path(args.output).parent.mkdir(parents=True, exist_ok=True)
    Path(args.output).write_text(html, encoding="utf-8", newline="\n")
    return 0


def cmd_materials_query(args: argparse.Namespace) -> int:
    catalog = load_json(args.catalog)
    require = json.loads(args.require) if args.require else None
    if require is not None and not isinstance(require, dict):
        raise MaterialsError("--require must be a JSON object of facet:value")
    if args.like and args.like not in catalog["assets"]:
        raise MaterialsError(f"unknown asset {args.like}")
    if not args.like and not require:
        raise MaterialsError("materials-query needs --like and/or --require")
    ranked = query_materials(catalog, like=args.like, require=require, limit=args.limit)
    palettes = retrieve_palette(catalog, like=args.like, map_name=args.map) if args.like else []
    _write_text(args.output, _json({
        "source": args.like,
        "require": require,
        "candidates": ranked,
        "palettes": palettes[: args.limit],
        "annotation": (catalog.get("annotations") or {}).get(args.like) if args.like else None,
    }))
    return 0


def cmd_materials_kit(args: argparse.Namespace) -> int:
    catalog = load_json(args.catalog)
    roles = json.loads(args.roles)
    if not isinstance(roles, dict):
        raise MaterialsError("--roles must be a JSON object of role -> facet:value")
    kit = select_authoring_kit(catalog, roles, limit=args.limit)
    _write_text(args.output, _json(kit))
    return 0


def cmd_materials_packet(args: argparse.Namespace) -> int:
    catalog = load_json(args.catalog)
    tiles, palette, _path = _load_optional_art(args.game, args.art, args.palette)
    ids = args.assets.split(",") if args.assets else None
    index = write_review_packet(
        catalog,
        maps_directory=args.maps,
        art_tiles=tiles,
        palette=palette,
        output_directory=args.output,
        asset_ids=ids,
    )
    _write_text(None, _json(index))
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


def cmd_analyze_space(args: argparse.Namespace) -> int:
    """Emit non-authoritative multi-view spatial evidence for either game."""
    game, build = _read_design_build(args.map)
    analysis = analyze_spatial(build, _parse_id_set(args.sectors) if args.sectors else None)
    analysis["map"] = str(args.map)
    analysis["detected_game"] = game
    _write_text(args.output, _json(analysis))
    return 0


def _load_spatial_corpus(path: str | None) -> dict[str, Any] | None:
    if not path:
        return None
    return json.loads(Path(path).read_text(encoding="utf-8"))


def _emit_player_space(payload: dict[str, Any], args: argparse.Namespace) -> int:
    if args.question:
        payload = focus_observation(payload, args.question)
    elif not args.full:
        payload = present_space(payload)
    _write_text(args.output, _json(payload))
    return 0


def cmd_player_profile(args: argparse.Namespace) -> int:
    if args.game:
        _write_text(args.output, _json(player_profile(args.game).to_dict()))
        return 0
    _write_text(args.output, _json({
        game: player_profile(game).to_dict()
        for game in ("blood", "duke3d", "doom")
    }))
    return 0


def cmd_contents(args: argparse.Namespace) -> int:
    if _game_for_path(args.map) != "blood":
        raise BloodMapError("contents currently classifies Blood object types only")
    disk = read_map(args.map)
    payload: dict[str, Any] = inventory_map(disk)
    payload["map"] = str(args.map)
    if args.mechanisms:
        payload["mechanisms"] = explain_mechanisms(disk)
    if args.multiplayer:
        payload["multiplayer"] = multiplayer_layout(disk)
    _write_text(args.output, _json(payload))
    return 0


def cmd_sightline(args: argparse.Namespace) -> int:
    _game, build = _read_design_build(args.map)
    if args.spawns:
        payload = spawn_sight_report(build, include_sp_start=not args.multiplayer_only)
    elif args.from_x is None or args.from_y is None or args.to_x is None or args.to_y is None:
        raise SightError("sightline requires --spawns or --from-x/--from-y/--to-x/--to-y")
    else:
        payload = line_of_sight(build, args.from_x, args.from_y, args.to_x, args.to_y)
        if args.depth:
            payload["depth"] = depth_samples(build, args.from_x, args.from_y)
    payload["map"] = str(args.map)
    _write_text(args.output, _json(payload))
    return 0


def cmd_inspect_space(args: argparse.Namespace) -> int:
    corpus = _load_spatial_corpus(args.corpus)
    sectors = _parse_id_set(args.sectors) if args.sectors else None
    if Path(args.map).suffix.lower() == ".wad":
        if not args.wad_map:
            raise PlayerSpaceError("inspect-space on a WAD requires --wad-map")
        payload = inspect_doom_space(wad_map(read_wad(args.map), args.wad_map), sectors, corpus=corpus)
    else:
        _game, build = _read_design_build(args.map)
        payload = inspect_space(build, sectors, corpus=corpus)
    payload["map"] = str(args.map)
    return _emit_player_space(payload, args)


def cmd_inspect_connection(args: argparse.Namespace) -> int:
    _game, build = _read_design_build(args.map)
    payload = inspect_connection(
        build, wall_id=args.wall, left=args.left, right=args.right,
        corpus=_load_spatial_corpus(args.corpus),
    )
    payload["map"] = str(args.map)
    return _emit_player_space(payload, args)


def cmd_compare_space(args: argparse.Namespace) -> int:
    _game, build = _read_design_build(args.map)
    payload = compare_transition(
        build, _parse_id_set(args.source), _parse_id_set(args.destination),
        corpus=_load_spatial_corpus(args.corpus),
    )
    payload["map"] = str(args.map)
    return _emit_player_space(payload, args)


def cmd_spatial_corpus(args: argparse.Namespace) -> int:
    if not args.wad and not args.maps:
        raise PlayerSpaceError("spatial-corpus requires --maps or --wad")
    if args.wad:
        wad = read_wad(args.wad)
        levels = [level for level in wad.maps if level.supported]
        if args.wad_map:
            levels = [wad_map(wad, args.wad_map)]
        payload = mine_doom_spatial_corpus(levels)
        payload["wad"] = str(args.wad)
    else:
        directory = Path(args.maps)
        loaded: list[tuple[str, Any]] = []
        for path in _map_files(directory, args.glob):
            _game, build = _read_design_build(path)
            loaded.append((path.name, build))
        payload = mine_build_spatial_corpus(loaded)
        payload["directory"] = str(directory)
    if args.summaries_only:
        for key in (
            "opening_width_player_widths", "traversable_opening_width_player_widths",
            "clear_height_player_heights",
            "footprint_player_areas", "step_player_heights", "aabb_width_player_widths",
        ):
            payload.pop(key, None)
    _write_text(args.output, _json(payload))
    return 0


def cmd_player_scale_report(args: argparse.Namespace) -> int:
    _write_text(args.output, _json(conversion_player_scale_report()))
    return 0


def cmd_material_scale(args: argparse.Namespace) -> int:
    catalog = json.loads(Path(args.catalog).read_text(encoding="utf-8"))
    asset = (catalog.get("assets") or {}).get(args.asset)
    if asset is None:
        raise PlayerSpaceError(f"asset {args.asset} is not in the catalog")
    payload = material_player_scale(asset, game=args.game or asset.get("game"))
    payload["asset"] = args.asset
    _write_text(args.output, _json(payload))
    return 0


def _optional_json(value: str | None) -> dict[str, Any] | None:
    if value is None:
        return None
    parsed = json.loads(value)
    if not isinstance(parsed, dict):
        raise ValueError("JSON option must be an object")
    return parsed


def cmd_probe_route(args: argparse.Namespace) -> int:
    _game, build = _read_design_build(args.map)
    result = probe_route(
        build, args.from_sector, args.to_sector,
        world_state=_optional_json(args.world_state), player_knowledge=_optional_json(args.knowledge),
    )
    result["map"] = str(args.map)
    _write_text(args.output, _json(result))
    return 0


def cmd_probe_transition(args: argparse.Namespace) -> int:
    _game, build = _read_design_build(args.map)
    result = probe_transition(build, args.from_sector, args.to_sector, world_state=_optional_json(args.world_state))
    result["map"] = str(args.map)
    _write_text(args.output, _json(result))
    return 0


def cmd_probe_visibility(args: argparse.Namespace) -> int:
    _game, build = _read_design_build(args.map)
    result = probe_visibility(build, args.from_sector, args.target_sector, world_state=_optional_json(args.world_state))
    result["map"] = str(args.map)
    _write_text(args.output, _json(result))
    return 0


def cmd_probe_progression(args: argparse.Namespace) -> int:
    _game, build = _read_design_build(args.map)
    result = probe_progression(build, world_state=_optional_json(args.world_state))
    result["map"] = str(args.map)
    _write_text(args.output, _json(result))
    return 0


def cmd_project_init(args: argparse.Namespace) -> int:
    brief = Path(args.brief_file).read_text(encoding="utf-8") if args.brief_file else args.brief
    _write_text(args.output, _json(initialize_project(args.directory, name=args.name, brief=brief or "")))
    return 0


def cmd_project_evidence(args: argparse.Namespace) -> int:
    entry = append_evidence(args.project, {
        "id": args.id, "concept": args.concept, "status": args.status, "claim": args.claim,
        "evidence": json.loads(args.evidence), "unknowns": args.unknown,
    })
    _write_text(args.output, _json(entry))
    return 0


def cmd_project_decision(args: argparse.Namespace) -> int:
    entry = append_decision(
        args.project, intent=args.intent, decision=args.decision, expected=args.expected,
        evidence=json.loads(args.evidence), status=args.status,
    )
    _write_text(args.output, _json(entry))
    return 0


def cmd_project_episode(args: argparse.Namespace) -> int:
    entry = append_episode(
        args.project, intent=args.intent, expected=args.expected,
        observed=json.loads(args.observed), correction=args.correction,
    )
    _write_text(args.output, _json(entry))
    return 0


def cmd_project_slice(args: argparse.Namespace) -> int:
    game, build = _read_design_build(args.map)
    sample = make_level_slice(
        build, _parse_id_set(args.sectors), source=source_identity(args.map, game=game),
    )
    result = store_level_slice(args.project, sample, sample_id=args.id)
    _write_text(args.output, _json(result))
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
            entry: dict[str, Any] = {
                "map": path.name, "path": str(path), "game": game,
                "fingerprint": fingerprint, "status": "ok",
            }
            if args.include_spatial:
                spatial = analyze_spatial(build)
                entry["spatial_index"] = {
                    "sectors": spatial["views"]["geometry"]["sectors"],
                    "hypotheses": spatial["hypotheses"],
                    "mechanism_groups": spatial["views"]["mechanism"]["groups"],
                    "provenance": spatial["provenance"],
                }
            entries.append(entry)
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
        base = {"map": entry["map"], "path": entry["path"], "game": entry["game"], "evidence": fingerprint["evidence"], "interpretations": fingerprint["interpretations"]}
        if match_basis is not None:
            base["motif"] = args.motif
            base["match_basis"] = match_basis
        if query is not None:
            base["distance"] = _fingerprint_distance(query, fingerprint)
        if args.region_kind:
            spatial_index = entry.get("spatial_index")
            if spatial_index is None:
                continue
            for hypothesis in spatial_index["hypotheses"]:
                if hypothesis["kind"] == args.region_kind:
                    results.append({**base, "region": hypothesis})
        else:
            results.append(base)
    results.sort(key=lambda item: (item.get("distance", 0), item["map"], item.get("region", {}).get("id", "")))
    _write_text(args.output, _json({
        "$schema": "bloodmap.design-search",
        "schema_version": 1,
        "query": {"like": args.like, "game": args.game, "mechanism": args.mechanism, "motif": args.motif, "region_kind": args.region_kind, "min_enemies": args.min_enemies},
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


def cmd_oracle_gzdoom(args: argparse.Namespace) -> int:
    report = run_gzdoom_oracle(
        args.iwad, gzdoom=args.gzdoom, map_name=args.map, pwad=args.file,
        grace_seconds=args.seconds, work_dir=args.work_dir,
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
    parser = argparse.ArgumentParser(prog="llmapper", description="Lossless Blood, Duke3D, and classic Doom map tooling")
    sub = parser.add_subparsers(dest="command", required=True)

    p = sub.add_parser("corpus", help="inventory every file in a map directory")
    p.add_argument("directory"); p.add_argument("-o", "--output"); p.set_defaults(func=cmd_corpus)
    p = sub.add_parser("duke-mechanisms", help="derive a semantic mechanism corpus from classic Duke3D MAPs")
    p.add_argument("directory")
    p.add_argument("-o", "--output", help="write JSON; defaults to stdout")
    p.set_defaults(func=cmd_duke_mechanisms)
    p = sub.add_parser("doom-corpus", help="inventory classic Doom/Doom II maps in a WAD")
    p.add_argument("wad")
    p.add_argument("-o", "--output")
    p.set_defaults(func=cmd_doom_corpus)
    p = sub.add_parser("doom-mechanisms", help="inventory vanilla Doom linedef/sector mechanisms")
    p.add_argument("wad")
    p.add_argument("--map", help="restrict to one map marker, e.g. E1M1")
    p.add_argument("-o", "--output")
    p.set_defaults(func=cmd_doom_mechanisms)
    p = sub.add_parser("convert-doom", help="convert a classic Doom map to a Blood MAP")
    p.add_argument("wad")
    p.add_argument("--map", required=True, help="map marker, e.g. E1M1 or MAP01")
    p.add_argument("--report", help="write the Doom→Blood fidelity report")
    p.add_argument("-o", "--output", required=True)
    p.set_defaults(func=cmd_convert_doom)
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
    p = sub.add_parser("compare-e3l1", help="differentially analyze a Duke/Blood map pair (E3L1 defaults)")
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
        help="convert a classic Duke3D map to a playable Blood approximation (E3L11 regression alias)",
    )
    p.add_argument("map", nargs="?", default="maps/duke3d/E3L11.MAP")
    p.add_argument("--duke-art", default="reference/duke3d")
    p.add_argument("--blood-art", default="reference/blood")
    p.add_argument("--blood-maps", default="maps/blood")
    p.add_argument("--style-map", help="Blood MAP whose tiles, palettes, shades, visibility, and sky become the visual vocabulary")
    p.add_argument("--report", help="write the detailed fidelity and unsupported-feature report")
    p.add_argument("-o", "--output", required=True)
    p.set_defaults(func=cmd_convert_e3l11)
    p = sub.add_parser(
        "convert-playable",
        help="convert a classic Duke3D map to a playable Blood approximation with native mechanisms",
    )
    p.add_argument("map", nargs="?", default="maps/duke3d/E3L11.MAP")
    p.add_argument("--duke-art", default="reference/duke3d")
    p.add_argument("--blood-art", default="reference/blood")
    p.add_argument("--blood-maps", default="maps/blood")
    p.add_argument("--style-map", help="Blood MAP whose tiles, palettes, shades, visibility, and sky become the visual vocabulary")
    p.add_argument("--report", help="write the detailed fidelity and unsupported-feature report")
    p.add_argument("-o", "--output", required=True)
    p.set_defaults(func=cmd_convert_e3l11)
    p = sub.add_parser("diff", help="locate the first structural byte difference")
    p.add_argument("a"); p.add_argument("b"); p.set_defaults(func=cmd_diff)
    p = sub.add_parser("inspect", help="show a concise map or object observation")
    p.add_argument("map"); p.add_argument("--sector", type=int); p.add_argument("--wall", type=int); p.add_argument("--sprite", type=int); p.set_defaults(func=cmd_inspect)
    p = sub.add_parser("contents", help="classify Blood starts, pickups, types, and channel inventory")
    p.add_argument("map")
    p.add_argument("--mechanisms", action="store_true", help="include static XSECTOR/XWALL/XSPRITE mechanism listing")
    p.add_argument("--multiplayer", action="store_true", help="include spawn/resource distances and 2D sight")
    p.add_argument("-o", "--output")
    p.set_defaults(func=cmd_contents)
    p = sub.add_parser("sightline", help="2D geometric line-of-sight against occluding Build walls")
    p.add_argument("map")
    p.add_argument("--spawns", action="store_true", help="pairwise sight among player-start sprites")
    p.add_argument("--multiplayer-only", action="store_true", help="with --spawns, ignore the single-player start sprite")
    p.add_argument("--from-x", type=float); p.add_argument("--from-y", type=float)
    p.add_argument("--to-x", type=float); p.add_argument("--to-y", type=float)
    p.add_argument("--depth", action="store_true", help="also emit a depth rose from the from-point")
    p.add_argument("-o", "--output")
    p.set_defaults(func=cmd_sightline)
    p = sub.add_parser("channels", help="derive the Blood TX/RX graph")
    p.add_argument("map"); p.add_argument("--channel", type=int); p.set_defaults(func=cmd_channels)
    p = sub.add_parser("render", help="render a deterministic top-down SVG")
    p.add_argument("map"); p.add_argument("-o", "--output", required=True); p.add_argument("--no-labels", action="store_true")
    p.add_argument("--sector", type=int); p.add_argument("--wall", type=int); p.add_argument("--sprite", type=int); p.set_defaults(func=cmd_render)
    p = sub.add_parser("stats", help="generate corpus geometry/gameplay statistics")
    p.add_argument("directory"); p.add_argument("-o", "--output"); p.set_defaults(func=cmd_stats)
    p = sub.add_parser("materials-mine", help="build a deterministic texture evidence catalog from maps and optional ART")
    p.add_argument("--maps", help="directory of Blood or Duke MAP files")
    p.add_argument("--glob", help="optional filename glob, e.g. E*.MAP for original Blood campaign maps")
    p.add_argument("--game", choices=("blood", "duke3d"), default="blood")
    p.add_argument("--wad", help="optional Doom IWAD/PWAD for named-texture usage")
    p.add_argument("--art", help="optional TILES*.ART directory")
    p.add_argument("--palette", help="768-byte palette; defaults to xmapedit import PAL for Blood")
    p.add_argument("--catalog", help="existing catalog to merge into when --merge is set")
    p.add_argument("--merge", action="store_true")
    p.add_argument("--summary-only", action="store_true")
    p.add_argument("-o", "--output", required=True)
    p.set_defaults(func=cmd_materials_mine)
    p = sub.add_parser("materials-export-batch", help="export an unlabeled classification batch for offline multimodal review")
    p.add_argument("catalog")
    p.add_argument("--game", choices=("blood", "duke3d"), default="blood")
    p.add_argument("--art"); p.add_argument("--palette")
    p.add_argument("--limit", type=int, default=80)
    p.add_argument("--no-previews", action="store_true")
    p.add_argument("-o", "--output", required=True)
    p.set_defaults(func=cmd_materials_export_batch)
    p = sub.add_parser("materials-import", help="import a proposed ontology and INTERPRETED annotations")
    p.add_argument("catalog")
    p.add_argument("input")
    p.add_argument("-o", "--output")
    p.set_defaults(func=cmd_materials_import)
    p = sub.add_parser("materials-audit", help="write an HTML contact sheet of unlabeled clusters and annotations")
    p.add_argument("catalog")
    p.add_argument("-o", "--output", required=True)
    p.add_argument("--game", choices=("blood", "duke3d"), default="blood")
    p.add_argument("--art"); p.add_argument("--palette"); p.add_argument("--cluster")
    p.set_defaults(func=cmd_materials_audit)
    p = sub.add_parser("materials-query", help="rank related assets by usage signature then appearance")
    p.add_argument("catalog")
    p.add_argument("--like", help="source asset id, e.g. blood:tile:180")
    p.add_argument("--require", help="JSON object of imported facet:value filters")
    p.add_argument("--map", help="restrict palettes to one map name")
    p.add_argument("--limit", type=int, default=8)
    p.add_argument("-o", "--output")
    p.set_defaults(func=cmd_materials_query)
    p = sub.add_parser("materials-kit", help="select corpus-backed assets for named authoring roles using imported facets")
    p.add_argument("catalog")
    p.add_argument("--roles", required=True, help="JSON object of role -> {facet: value}")
    p.add_argument("--limit", type=int, default=3)
    p.add_argument("-o", "--output")
    p.set_defaults(func=cmd_materials_kit)
    p = sub.add_parser("materials-packet", help="write isolated previews and cropped map-context SVGs for review")
    p.add_argument("catalog")
    p.add_argument("--maps", required=True)
    p.add_argument("--art")
    p.add_argument("--palette")
    p.add_argument("--game", choices=("blood", "duke3d"), default="blood")
    p.add_argument("--assets", help="optional comma-separated asset ids")
    p.add_argument("-o", "--output", required=True)
    p.set_defaults(func=cmd_materials_packet)
    p = sub.add_parser("design-fingerprint", help="measure a level or region as grounded design characteristics")
    p.add_argument("map")
    p.add_argument("--sectors", help="optional comma-separated sector IDs/ranges")
    p.add_argument("-o", "--output", help="write JSON; defaults to stdout")
    p.set_defaults(func=cmd_design_fingerprint)
    p = sub.add_parser("analyze-space", help="derive independent geometry, traversal, vertical, mechanism, progression, and material views")
    p.add_argument("map")
    p.add_argument("--sectors", help="optional comma-separated sector IDs/ranges")
    p.add_argument("-o", "--output", help="write JSON; defaults to stdout")
    p.set_defaults(func=cmd_analyze_space)
    p = sub.add_parser("player-profile", help="show source-backed player collision and movement profiles")
    p.add_argument("--game", choices=("blood", "duke3d", "duke", "doom"))
    p.add_argument("-o", "--output")
    p.set_defaults(func=cmd_player_profile)
    p = sub.add_parser("inspect-space", help="compact player-relative observation of a selected space")
    p.add_argument("map")
    p.add_argument("--sectors", help="optional comma-separated sector IDs/ranges")
    p.add_argument("--wad-map", help="Doom map marker when MAP is a WAD")
    p.add_argument("--corpus", help="optional player-relative spatial corpus JSON")
    p.add_argument("--question", choices=("traverse", "scale", "enclosure", "shape", "opening", "transition"))
    p.add_argument("--full", action="store_true", help="emit layered raw/normalized/corpus evidence")
    p.add_argument("-o", "--output")
    p.set_defaults(func=cmd_inspect_space)
    p = sub.add_parser("inspect-connection", help="player-relative observation of a portal opening")
    p.add_argument("map")
    p.add_argument("--wall", type=int, help="portal wall ID")
    p.add_argument("--left", type=int, help="left sector ID; requires --right")
    p.add_argument("--right", type=int, help="right sector ID; requires --left")
    p.add_argument("--corpus")
    p.add_argument("--question", choices=("traverse", "scale", "enclosure", "shape", "opening", "transition"))
    p.add_argument("--full", action="store_true")
    p.add_argument("-o", "--output")
    p.set_defaults(func=cmd_inspect_connection)
    p = sub.add_parser("compare-space", help="player-relative transition between two selections")
    p.add_argument("map")
    p.add_argument("--from", dest="source", required=True, help="source sector IDs/ranges")
    p.add_argument("--to", dest="destination", required=True, help="destination sector IDs/ranges")
    p.add_argument("--corpus")
    p.add_argument("--question", choices=("traverse", "scale", "enclosure", "shape", "opening", "transition"))
    p.add_argument("--full", action="store_true")
    p.add_argument("-o", "--output")
    p.set_defaults(func=cmd_compare_space)
    p = sub.add_parser("spatial-corpus", help="mine player-relative spatial distributions from original maps")
    p.add_argument("--maps", help="directory of Blood or Duke MAP files")
    p.add_argument("--glob", help="optional filename glob, e.g. E*.MAP")
    p.add_argument("--wad", help="optional Doom IWAD/PWAD")
    p.add_argument("--wad-map", help="restrict Doom mining to one map marker")
    p.add_argument("--summaries-only", action="store_true", help="omit raw sample arrays")
    p.add_argument("-o", "--output", required=True)
    p.set_defaults(func=cmd_spatial_corpus)
    p = sub.add_parser("player-scale-report", help="compare conversion XY/Z scales with player-body ratios")
    p.add_argument("-o", "--output")
    p.set_defaults(func=cmd_player_scale_report)
    p = sub.add_parser("material-scale", help="player-relative world coverage for a materials catalog asset")
    p.add_argument("catalog")
    p.add_argument("--asset", required=True)
    p.add_argument("--game", choices=("blood", "duke3d", "duke", "doom"))
    p.add_argument("-o", "--output")
    p.set_defaults(func=cmd_material_scale)
    p = sub.add_parser("probe-route", help="run a bounded Level-0 route/access probe")
    p.add_argument("map"); p.add_argument("--from-sector", type=int, required=True); p.add_argument("--to-sector", type=int, required=True)
    p.add_argument("--world-state", help="inline JSON world state, e.g. {\"opened_portals\":[\"portal:12\"]}")
    p.add_argument("--knowledge", help="inline JSON player knowledge")
    p.add_argument("-o", "--output"); p.set_defaults(func=cmd_probe_route)
    p = sub.add_parser("probe-transition", help="compare a bounded adjacent Level-0 experience transition")
    p.add_argument("map"); p.add_argument("--from-sector", type=int, required=True); p.add_argument("--to-sector", type=int, required=True)
    p.add_argument("--world-state", help="inline JSON world state")
    p.add_argument("-o", "--output"); p.set_defaults(func=cmd_probe_transition)
    p = sub.add_parser("probe-visibility", help="probe direct-portal visibility along a bounded Level-0 route")
    p.add_argument("map"); p.add_argument("--from-sector", type=int, required=True); p.add_argument("--target-sector", type=int, required=True)
    p.add_argument("--world-state", help="inline JSON world state")
    p.add_argument("-o", "--output"); p.set_defaults(func=cmd_probe_visibility)
    p = sub.add_parser("probe-progression", help="summarize static accessibility and state-change candidates")
    p.add_argument("map"); p.add_argument("--world-state", help="inline JSON world state")
    p.add_argument("-o", "--output"); p.set_defaults(func=cmd_probe_progression)
    p = sub.add_parser("project-init", help="create a non-destructive persistent level-design workspace")
    p.add_argument("directory"); p.add_argument("--name", required=True); p.add_argument("--brief", default="")
    p.add_argument("--brief-file", help="read the initial brief from UTF-8 text")
    p.add_argument("-o", "--output"); p.set_defaults(func=cmd_project_init)
    p = sub.add_parser("project-evidence", help="append an evidence-backed semantic claim to a project ledger")
    p.add_argument("project"); p.add_argument("--concept", required=True); p.add_argument("--claim", required=True)
    p.add_argument("--status", choices=("verified", "heuristic", "disputed", "superseded", "rejected"), default="heuristic")
    p.add_argument("--evidence", default="[]", help="inline JSON evidence list"); p.add_argument("--unknown", action="append", default=[]); p.add_argument("--id")
    p.add_argument("-o", "--output"); p.set_defaults(func=cmd_project_evidence)
    p = sub.add_parser("project-decision", help="append a design intent/decision/expected-result record")
    p.add_argument("project"); p.add_argument("--intent", required=True); p.add_argument("--decision", required=True); p.add_argument("--expected", required=True)
    p.add_argument("--evidence", default="[]", help="inline JSON evidence list"); p.add_argument("--status", default="proposed")
    p.add_argument("-o", "--output"); p.set_defaults(func=cmd_project_decision)
    p = sub.add_parser("project-episode", help="append an observed design episode and optional correction")
    p.add_argument("project"); p.add_argument("--intent", required=True); p.add_argument("--expected", required=True); p.add_argument("--observed", required=True, help="inline JSON probe/observation result")
    p.add_argument("--correction"); p.add_argument("-o", "--output"); p.set_defaults(func=cmd_project_episode)
    p = sub.add_parser("project-slice", help="store a contextual source-backed LevelSlice precedent")
    p.add_argument("project"); p.add_argument("map"); p.add_argument("--sectors", required=True); p.add_argument("--id")
    p.add_argument("-o", "--output"); p.set_defaults(func=cmd_project_slice)
    p = sub.add_parser("design-index", help="index Blood and Duke3D maps by design fingerprint")
    p.add_argument("directory")
    p.add_argument("--include-spatial", action="store_true", help="also index overlapping spatial hypotheses and mechanism memberships")
    p.add_argument("-o", "--output", required=True); p.set_defaults(func=cmd_design_index)
    p = sub.add_parser("design-search", help="retrieve maps by multi-dimensional design similarity or evidence")
    p.add_argument("index")
    p.add_argument("--like", help="rank by fingerprint similarity to this MAP")
    p.add_argument("--game", choices=("blood", "duke3d"))
    p.add_argument("--mechanism", help="require a source mechanism kind")
    p.add_argument("--motif", choices=("arena", "branching", "compressed", "loop", "repeated-bays", "vertical"), help="require a soft structural motif heuristic")
    p.add_argument("--region-kind", choices=("perceptual_space", "navigation_region", "material_region", "mechanism_region", "vertical_layer"), help="return overlapping hypothesis selections from an --include-spatial index")
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
    p = sub.add_parser("oracle-gzdoom", help="run a bounded GZDoom map-load smoke test")
    p.add_argument("--iwad", required=True)
    p.add_argument("--gzdoom", required=True)
    p.add_argument("--map", required=True, help="map marker, e.g. E1M1")
    p.add_argument("--file", help="optional PWAD")
    p.add_argument("--seconds", type=float, default=4.0)
    p.add_argument("--work-dir")
    p.add_argument("-o", "--output")
    p.set_defaults(func=cmd_oracle_gzdoom)

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
    except (BloodMapError, CompositionError, ConstructionError, ConversionError, DoomConversionError, DoomError, DukeMapError, E3L11ConversionError, PlayableConversionError, FragmentError, MaterialsError, ObservationError, OracleError, RecipeError, OSError, ValueError, KeyError, json.JSONDecodeError) as exc:
        print(f"bloodmap: error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
