"""What would this map look like WITHOUT that?

A before/after pair says a build changed. It does not say which part of the
change did the work: a shopfront that gained a fascia, a name and a lit room
in one build is "better", and nobody knows whether the name mattered. The
owner asked for exactly this (2026-11-17): "check how it looks without
something ... what if we add this or remove this, what it will change".

So this takes a BUILT map and a list of small edits and writes a variant:
the same map with one thing unlit, repainted, flattened or removed. It works
on the finished file, not the source, so a variant costs a second rather
than a three-minute build, and it cannot be mistaken for a build: a variant
is evidence about what a feature contributes, never a level to ship.

An edit is ``{"on": kind, "where": {...}, "set": {...}}`` or
``{"on": "sprites", "where": {...}, "drop": true}``.

``where`` (all given keys must hold):
    ``id``            list of record numbers
    ``picnum`` / ``over_picnum`` / ``floor_picnum`` / ``ceiling_picnum``
                      list of tile numbers
    ``sector``        for walls: the owning sector; for sprites: its sector
    ``next_sector``   for walls: the sector on the other side
    ``rect``          [x0, y0, x1, y1]: a wall's midpoint, a sprite's
                      position, or any vertex of a sector lies inside
    ``intent``        a tag from the sidecar written by the build, see
                      `tag_sectors`

``set`` maps a field to a value, or to ``{"add": n}`` / ``{"copy": field}``.

.. code-block:: bash

    python -m tools.whatif built.MAP -o unlit.MAP --edits edits.json
"""

from __future__ import annotations

import argparse
import hashlib
import json
import pathlib
import sys
from typing import Any, Iterable

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))


class WhatIfError(ValueError):
    pass


def _owner(disk: Any) -> dict[int, int]:
    out = {}
    for index, sector in enumerate(disk.sectors):
        f = sector.fields
        for w in range(int(f["wall_ptr"]), int(f["wall_ptr"]) + int(f["wall_count"])):
            out[w] = index
    return out


def _matches(disk: Any, kind: str, index: int, fields: Any, where: dict,
             owner: dict[int, int], tags: dict[str, list[int]]) -> bool:
    for key, want in where.items():
        if key == "id":
            if index not in want:
                return False
        elif key in ("picnum", "over_picnum", "floor_picnum", "ceiling_picnum"):
            if int(fields.get(key, -1)) not in want:
                return False
        elif key == "sector":
            here = owner.get(index) if kind == "walls" else (
                index if kind == "sectors" else int(fields["sector"]))
            if here not in want:
                return False
        elif key == "next_sector":
            if int(fields.get("next_sector", -1)) not in want:
                return False
        elif key == "intent":
            wanted = set()
            for tag in ([want] if isinstance(want, str) else want):
                wanted |= set(tags.get(tag, ()))
            here = owner.get(index) if kind == "walls" else (
                index if kind == "sectors" else int(fields["sector"]))
            if here not in wanted:
                return False
        elif key == "rect":
            x0, y0, x1, y1 = want
            if kind == "sprites":
                points = [(int(fields["x"]), int(fields["y"]))]
            elif kind == "walls":
                nxt = disk.walls[int(fields["point2"])].fields
                points = [((int(fields["x"]) + int(nxt["x"])) / 2,
                           (int(fields["y"]) + int(nxt["y"])) / 2)]
            else:
                points = [(int(disk.walls[w].fields["x"]),
                           int(disk.walls[w].fields["y"]))
                          for w in range(int(fields["wall_ptr"]),
                                         int(fields["wall_ptr"])
                                         + int(fields["wall_count"]))]
            if not any(x0 <= x <= x1 and y0 <= y <= y1 for x, y in points):
                return False
        else:
            raise WhatIfError(f"unknown selector {key!r}")
    return True


def apply(disk: Any, edits: Iterable[dict], *,
          tags: dict[str, list[int]] | None = None) -> list[dict]:
    """Apply the edits in place. Returns what each one touched."""
    tags = tags or {}
    report = []
    for edit in edits:
        kind = edit.get("on")
        if kind not in ("sectors", "walls", "sprites"):
            raise WhatIfError(f"an edit is on sectors, walls or sprites, not {kind!r}")
        owner = _owner(disk)
        records = getattr(disk, kind)
        hit = [index for index, record in enumerate(records)
               if _matches(disk, kind, index, record.fields,
                           edit.get("where", {}), owner, tags)]
        if edit.get("drop"):
            if kind != "sprites":
                raise WhatIfError("only sprites can be dropped: a sector or a "
                                  "wall cannot be removed from a built map")
            keep = [record for index, record in enumerate(records)
                    if index not in set(hit)]
            disk.sprites[:] = keep
        else:
            for index in hit:
                fields = records[index].fields
                for field, value in edit.get("set", {}).items():
                    if field not in fields:
                        raise WhatIfError(f"{kind} have no field {field!r}")
                    if isinstance(value, dict) and "add" in value:
                        fields[field] = int(fields[field]) + int(value["add"])
                    elif isinstance(value, dict) and "copy" in value:
                        fields[field] = int(fields[value["copy"]])
                    else:
                        fields[field] = int(value)
        report.append({"edit": edit.get("name", ""), "on": kind,
                       "touched": len(hit),
                       "dropped": bool(edit.get("drop"))})
    return report


def variant(source: pathlib.Path, target: pathlib.Path, edits: list[dict], *,
            tags: dict[str, list[int]] | None = None) -> dict[str, Any]:
    """Write `target` as `source` with `edits` applied, and say what moved."""
    from bloodmap.format import read_map, write_map

    disk = read_map(source)
    touched = apply(disk, edits, tags=tags)
    if not any(row["touched"] for row in touched):
        raise WhatIfError("no edit touched anything: the variant would be "
                          "the map it was made from")
    write_map(disk, target)
    return {
        "source": str(source), "target": str(target),
        "source_sha256": hashlib.sha256(source.read_bytes()).hexdigest(),
        "target_sha256": hashlib.sha256(target.read_bytes()).hexdigest(),
        "edits": touched,
        "claims": {"is_a_build": False,
                   "is_evidence_of": "what the edited records contribute"},
    }


def load_tags(source: pathlib.Path) -> dict[str, list[int]]:
    """Sector tags written beside a built map by its build, if any."""
    sidecar = source.with_suffix(".tags.json")
    if sidecar.exists():
        return json.loads(sidecar.read_text("utf-8"))
    return {}


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("map")
    parser.add_argument("-o", "--out", required=True)
    parser.add_argument("--edits", required=True, help="JSON file: a list of edits")
    args = parser.parse_args(argv)
    source = pathlib.Path(args.map)
    edits = json.loads(pathlib.Path(args.edits).read_text("utf-8"))
    result = variant(source, pathlib.Path(args.out), edits,
                     tags=load_tags(source))
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
