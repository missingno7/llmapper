from __future__ import annotations

import argparse
import copy
import hashlib
import json
import sys
from pathlib import Path
from typing import Any

from .analysis import channel_graph, corpus_statistics, geometry_view, render_svg, validate_map
from .composition import CompositionError, connect_portals, insert_fragment
from .format import BloodMapError, encode_map, locate_offset, read_map, write_map
from .fragment import FragmentError, LevelFragment, apply_fragment_in_place, extract_fragment
from .model import LevelIR


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
            disk = read_map(path)
            version = f"0x{disk.version:04x}"
            versions[version] = versions.get(version, 0) + 1
            entry.update(
                detected_format="Blood MAP", map_version=version,
                sectors=len(disk.sectors), walls=len(disk.walls), sprites=len(disk.sprites),
                crc32=f"{disk.source_crc32:08x}", status="ok",
            )
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
    disk = read_map(args.map)
    diagnostics = validate_map(disk)
    errors = sum(x.severity == "error" for x in diagnostics)
    warnings = sum(x.severity == "warning" for x in diagnostics)
    if args.json:
        print(_json({"file": args.map, "errors": errors, "warnings": warnings,
                     "diagnostics": [x.__dict__ for x in diagnostics]}), end="")
    else:
        for item in diagnostics:
            print(f"{item.severity.upper():7} {item.code:26} {item.location}: {item.message}")
        print(f"{args.map}: {errors} error(s), {warnings} warning(s)")
    return 1 if errors else 0


def cmd_roundtrip(args: argparse.Namespace) -> int:
    path = Path(args.map)
    original = path.read_bytes()
    disk = read_map(path)
    rebuilt = encode_map(disk)
    if rebuilt == original:
        print(f"PASS {path}: byte-exact ({len(original)} bytes)")
        if args.output:
            Path(args.output).write_bytes(rebuilt)
        return 0
    limit = min(len(original), len(rebuilt))
    offset = next((i for i in range(limit) if original[i] != rebuilt[i]), limit)
    a = original[offset] if offset < len(original) else None
    b = rebuilt[offset] if offset < len(rebuilt) else None
    print(f"FAIL {path}: first mismatch at 0x{offset:08x}; original={a!r}, rebuilt={b!r}; {locate_offset(disk, offset)}")
    return 1


def cmd_roundtrip_all(args: argparse.Namespace) -> int:
    results = []
    failed = 0
    for path in _map_files(Path(args.directory)):
        try:
            original = path.read_bytes()
            disk = read_map(path)
            rebuilt = encode_map(disk)
            ir_rebuilt = encode_map(disk.to_level_ir().to_disk_map())
            diagnostics = validate_map(disk)
            errors = sum(x.severity == "error" for x in diagnostics)
            item = {
                "filename": path.name, "parse": True, "byte_exact": original == rebuilt,
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


def cmd_transform(args: argparse.Namespace) -> int:
    disk = read_map(args.map)
    ir = disk.to_level_ir()
    if args.operation == "translate":
        ir.translate(args.x, args.y, args.z)
    elif args.operation == "rotate":
        ir.rotate_quarter_turns(args.turns, args.pivot_x, args.pivot_y)
    transformed = ir.to_disk_map()
    errors = [d for d in validate_map(transformed) if d.severity == "error"]
    if errors:
        raise BloodMapError(f"transformation produced {len(errors)} validation errors; first: {errors[0].message}")
    write_map(transformed, args.output)
    # Reparse is part of the command's contract.
    reparsed = read_map(args.output)
    if any(d.severity == "error" for d in validate_map(reparsed)):
        raise BloodMapError("written transformation failed reparse validation")
    print(f"WROTE {args.output}: {args.operation}, reparsed and validated")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="bloodmap", description="Lossless Blood MAP tooling")
    sub = parser.add_subparsers(dest="command", required=True)

    p = sub.add_parser("corpus", help="inventory every file in a map directory")
    p.add_argument("directory"); p.add_argument("-o", "--output"); p.set_defaults(func=cmd_corpus)
    p = sub.add_parser("dump", help="write canonical Level IR JSON")
    p.add_argument("map"); p.add_argument("-o", "--output"); p.set_defaults(func=cmd_dump)
    p = sub.add_parser("build", help="build a MAP from Level IR JSON")
    p.add_argument("json"); p.add_argument("-o", "--output", required=True); p.set_defaults(func=cmd_build)
    p = sub.add_parser("validate", help="validate Build/Blood structure")
    p.add_argument("map"); p.add_argument("--json", action="store_true"); p.set_defaults(func=cmd_validate)
    p = sub.add_parser("roundtrip", help="test byte-exact parse/write")
    p.add_argument("map"); p.add_argument("-o", "--output"); p.set_defaults(func=cmd_roundtrip)
    p = sub.add_parser("roundtrip-all", help="test parsing, disk/IR roundtrips, and validation")
    p.add_argument("directory"); p.add_argument("--json", action="store_true"); p.set_defaults(func=cmd_roundtrip_all)
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
    p = sub.add_parser("extract", help="extract selected sectors into a self-describing fragment")
    p.add_argument("map"); p.add_argument("--sectors", required=True, help="comma-separated IDs/ranges, e.g. 1,4-7")
    p.add_argument("-o", "--output", required=True); p.set_defaults(func=cmd_extract)
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
    except (BloodMapError, CompositionError, FragmentError, OSError, ValueError, KeyError, json.JSONDecodeError) as exc:
        print(f"bloodmap: error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
