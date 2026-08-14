from __future__ import annotations

import argparse
import json
from pathlib import Path

from bloodmap import build_first_puzzle_room, write_map


def main() -> int:
    parser = argparse.ArgumentParser(description="Build the first scratch-authored Blood puzzle room")
    parser.add_argument("-o", "--output", default="work/first-puzzle-room.MAP")
    parser.add_argument("--report", default="work/first-puzzle-room-report.json")
    args = parser.parse_args()

    result = build_first_puzzle_room()
    output, report = Path(args.output), Path(args.report)
    output.parent.mkdir(parents=True, exist_ok=True)
    report.parent.mkdir(parents=True, exist_ok=True)
    write_map(result.level.to_disk_map(), output)
    report.write_text(json.dumps(result.report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(
        f"WROTE {output}: {len(result.level.sectors)} sectors, "
        f"{len(result.level.walls)} walls, {len(result.level.sprites)} sprites"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
