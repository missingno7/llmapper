"""Read-only repository measurements for the 2026-09-09 audit."""
from pathlib import Path
from collections import Counter
import ast
import hashlib
import importlib.util
import json
import sys
import time

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from bloodmap.format import read_map, encode_map
from bloodmap.analysis import validate_map

def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

result = {"scope": "Current working tree; no engine runs; counts do not measure quality", "inventory": {}, "artifacts": [], "source_compile": []}
for directory in ("bloodmap", "tests", "tools", "experiments", "projects"):
    files = list((ROOT / directory).rglob("*.py"))
    result["inventory"][directory] = {"python_files": len(files), "lines": sum(len(p.read_bytes().splitlines()) for p in files)}
result["inventory"]["static_test_methods"] = sum(
    1 for p in (ROOT / "tests").glob("test_*.py")
    for n in ast.walk(ast.parse(p.read_text(encoding="utf-8-sig")))
    if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)) and n.name.startswith("test_")
)
paths = sorted((ROOT / "projects/reasoned-authoring-v1/level").glob("candidate-v*.MAP"))
paths += [ROOT / "projects/blood-city/level" / n for n in ("blood-city-current.MAP", "slice2-streets.MAP")]
for path in paths:
    disk = read_map(path)
    types = Counter(int(s.type) for s in disk.sprites)
    entry = {"path": str(path.relative_to(ROOT)), "sha256": digest(path), "bytes": path.stat().st_size,
             "counts": {"sectors": len(disk.sectors), "walls": len(disk.walls), "sprites": len(disk.sprites)},
             "dude_types_200_to_299": {str(k): v for k,v in sorted(types.items()) if 200 <= k < 300},
             "native_roundtrip_exact": encode_map(disk) == path.read_bytes(),
             "native_errors": [{"code": x.code, "location": x.location, "message": x.message} for x in validate_map(disk) if x.severity == "error"]}
    if path.name.startswith("candidate-"):
        version = path.stem.split("-")[-1]
        packet_path = ROOT / "projects/reasoned-authoring-v1/reports" / version / "iteration.json"
        if packet_path.exists():
            packet = json.loads(packet_path.read_text(encoding="utf-8"))
            entry["packet"] = {"bytes": packet_path.stat().st_size, "identity": packet["identity"],
                               "artifact_hash_matches": packet["identity"]["map_sha256"] == entry["sha256"],
                               "gate_status_counts": dict(Counter(g["status"] for g in packet["hard_gates"]))}
        else:
            entry["packet"] = None
    result["artifacts"].append(entry)

for version in ("v0", "v5", "v7"):
    path = ROOT / "projects/reasoned-authoring-v1/level" / f"candidate_{version}.py"
    name = f"audit_candidate_{version}"
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    started = time.monotonic()
    row = {"version": version, "source_sha256": digest(path)}
    try:
        spec.loader.exec_module(module)
        factory = module.candidate().factory if hasattr(module, "candidate") else module.make_layout
        compiled = factory().compile()
        payload = encode_map(compiled.level.to_disk_map())
        second = encode_map(factory().compile().level.to_disk_map())
        row.update(status="compiled", deterministic=payload == second, sha256=hashlib.sha256(payload).hexdigest(),
                   matches_stored_map=payload == path.with_name(f"candidate-{version}.MAP").read_bytes())
    except Exception as error:
        row.update(status="failed", error_type=type(error).__name__, error=str(error))
    row["seconds"] = round(time.monotonic() - started, 3)
    result["source_compile"].append(row)
    print(version, row["status"], row.get("error", "")[:180], flush=True)

out = ROOT / "work/audit-2026-09-09/measurements.json"
out.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
print(out)
