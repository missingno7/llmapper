"""Check the frozen pilot's source, MAP, packet and image bindings.

This verifies preservation, not compilation with the current compiler or quality.
The manifest pins the compiler revision used for historical reconstruction.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "projects/reasoned-authoring-v1/archive/architectural-v0-v5/manifest.json"


def check_archive(manifest_path: Path = MANIFEST, root: Path = ROOT) -> list[str]:
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    faults = []
    if not manifest["iterations"]:
        faults.append("empty archive")
    identities = set()
    for entry in manifest["iterations"]:
        label = entry["id"]
        if label in identities:
            faults.append(f"duplicate iteration: {label}")
        identities.add(label)
        available = {}
        for role in ("source", "map", "packet", "review"):
            record = entry[role]
            path = (root / record["path"]).resolve()
            if not path.is_relative_to(root.resolve()):
                faults.append(f"{label}: {role} escapes archive root")
                continue
            if not path.is_file():
                faults.append(f"{label}: missing {role}: {record['path']}")
                continue
            payload = path.read_bytes()
            if hashlib.sha256(payload).hexdigest() != record["sha256"]:
                faults.append(f"{label}: {role} hash mismatch")
            available[role] = payload
        if "packet" not in available:
            continue
        packet = json.loads(available["packet"])
        if packet["identity"]["iteration_id"] != entry["iteration_id"]:
            faults.append(f"{label}: packet iteration mismatch")
        if "map" in available and hashlib.sha256(available["map"]).hexdigest() != packet["identity"]["map_sha256"]:
            faults.append(f"{label}: MAP does not match packet identity")
        views = packet.get("render", {}).get("captures", {}).get("views", [])
        indexed = {v["viewpoint_id"]: v for v in views}
        if len(indexed) != len(views) or len({v["id"] for v in entry["views"]}) != len(entry["views"]):
            faults.append(f"{label}: duplicate frame identity")
        if set(indexed) != {v["id"] for v in entry["views"]}:
            faults.append(f"{label}: frame inventory differs from packet")
        for view in entry["views"]:
            captured = indexed.get(view["id"], {})
            if view.get("path") is None:
                if captured.get("image") or captured.get("status") == "pass" or view.get("status") != captured.get("status"):
                    faults.append(f"{label}: unbound successful frame: {view['id']}")
                continue
            path = (root / view["path"]).resolve()
            if not path.is_relative_to(root.resolve()) or not path.is_file():
                faults.append(f"{label}: missing frame {view['id']}")
                continue
            recorded = indexed.get(view["id"], {}).get("image_sha256")
            actual = hashlib.sha256(path.read_bytes()).hexdigest()
            if actual != view["sha256"] or actual != recorded:
                faults.append(f"{label}: frame hash mismatch: {view['id']}")
    return faults


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, default=MANIFEST)
    args = parser.parse_args()
    try:
        faults = check_archive(args.manifest)
    except (OSError, ValueError, KeyError, TypeError) as error:
        print(f"Archive unavailable or malformed: {error}")
        return 1
    for fault in faults:
        print(f"FAIL: {fault}")
    if not faults:
        print("Archive bindings verified; runtime and map quality are not evaluated.")
    return int(bool(faults))


if __name__ == "__main__":
    raise SystemExit(main())
