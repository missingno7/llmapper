"""A project as the tools know it: where its map is, where it is looked at from, and where its own reports go.

The owner, 2026-11-26: "The long-term product is llmapper itself, not Gravesend.
Gravesend is one of its projects ... it should not be an implicit dependency of
another level."

Until that day the tools that look at a level, hand it to blind readers and
rank its views had Gravesend's paths typed into them, and a second level (the
Duke E4L1 remake) wrote its own look, review and status rather than use them.

A project is a directory under `projects/` with a `project.json`. The file says
what the directory is (`kind`: a ``level`` that is built and played, an
``analysis`` of somebody else's map, a ``fixture`` built to test the library,
a ``pilot`` kept for its evidence) and,
for a level, the few paths a tool cannot guess. Everything else is where
`CONVENTION` says it is, so the smallest level's descriptor is three lines:

    {"$schema": "bloodmap.level-project", "schema_version": 1,
     "name": "The Cold Store", "kind": "level", "map": "level/coldstore.MAP"}

``map``        the built map every tool reads
``played``     the copy the owner plays, when that is another file
``build``      the script that writes the map
``level``      the directory of its modules (`level`)
``poses``      a Python file whose `POSE_SETS` names where the level is looked at from (`level/poses.py`),
               or a JSON file of absolute poses for a map that is edited by hand
``plan_unit``  what one unit of a pose is in Build units (1024)
``ground_z``   the floor a pose stands on unless it names another (0)
``reports``    what the build and the tools write about it (`reports`)
``critique``   its critique rounds, a directory a place (`reports/critique`)
``showcase``   its showcase rounds (`reports/showcase`); ``showcase_places`` the places they are of
``tests``      its own regression tests (`tests`)
``status_script``  a status of its own that knows its places; `tools.project status` runs it instead of its own

What the game is like belongs to no project: studies, findings and the catalog
are under `knowledge/`, and a project only points at them.
"""

from __future__ import annotations

import json
import os
import runpy
from dataclasses import dataclass
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
HOME = ROOT / "projects"
SCHEMA = "bloodmap.level-project"
KINDS = ("level", "analysis", "fixture", "pilot")
#: where a thing is when the descriptor does not say
CONVENTION = {"level": "level", "poses": "level/poses.py", "reports": "reports", "critique": "reports/critique",
              "showcase": "reports/showcase", "showcase_places": "level/showcase-places.json", "tests": "tests",
              "status": "reports/STATUS.md"}
#: the variable that names the project a tool works on when it is not told
ENV = "LLMAPPER_PROJECT"


class ProjectError(ValueError):
    pass


@dataclass(frozen=True)
class Project:
    """One directory under `projects/`, by what its `project.json` says."""

    root: Path
    data: dict[str, Any]

    @property
    def key(self) -> str:
        """The name tools take: the directory's."""
        return self.root.name

    @property
    def title(self) -> str:
        return str(self.data.get("name", self.key))

    @property
    def kind(self) -> str:
        return str(self.data.get("kind", "pilot"))

    @property
    def game(self) -> str:
        return str(self.data.get("game", "blood"))

    @property
    def live(self) -> bool:
        return self.data.get("status", "live") == "live"

    def path(self, what: str) -> Path | None:
        """Where `what` is: the descriptor's word, else the convention's; None if neither says."""
        said = self.data.get(what, CONVENTION.get(what))
        return (self.root / str(said)) if said else None

    def need(self, what: str) -> Path:
        """`path`, for a tool that cannot go on without it."""
        found = self.path(what)
        if found is None:
            raise ProjectError(f"{self.key}: project.json does not say where its {what} is")
        return found

    @property
    def map(self) -> Path:
        return self.need("map")

    @property
    def level(self) -> Path:
        return self.need("level")

    @property
    def plan_unit(self) -> int:
        return int(self.data.get("plan_unit", 1024))

    @property
    def ground_z(self) -> int:
        return int(self.data.get("ground_z", 0))

    def pose_sets(self) -> dict[str, dict[str, tuple]]:
        """The project's named poses: `{set: {view: (x, y, toward x, toward y, horiz, note[, floor z])}}`, in plan units."""
        path = self.need("poses")
        if not path.exists():
            raise ProjectError(f"{self.key}: no poses at {path}")
        if path.suffix == ".json":
            # a hand-edited map's poses: {set: [{"id": .., "x": .., "y": .., "angle": .., "sector": ..}, ...]}
            raw = json.loads(path.read_text(encoding="utf-8"))
            return {name: {row["id"]: row for row in rows} if isinstance(rows, list) else rows for name, rows in raw.items()}
        found = runpy.run_path(str(path)).get("POSE_SETS")
        if not isinstance(found, dict):
            raise ProjectError(f"{path} does not define POSE_SETS")
        return found

    def rounds(self, slug: str) -> Path:
        """Where one place's critique rounds are kept."""
        return self.need("critique") / slug


def read(directory: Path) -> Project:
    path = Path(directory) / "project.json"
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except OSError as exc:
        raise ProjectError(f"no project at {directory}: it has no project.json") from exc
    except json.JSONDecodeError as exc:
        raise ProjectError(f"{path} is not JSON: {exc}") from exc
    if data.get("$schema") != SCHEMA:
        raise ProjectError(f"{path} is not a {SCHEMA} document")
    if data.get("kind", "pilot") not in KINDS:
        raise ProjectError(f"{path}: kind is one of {', '.join(KINDS)}")
    return Project(Path(directory).resolve(), data)


def projects(kind: str | None = None) -> list[Project]:
    """Every project that says what it is, by name; of one kind if asked."""
    found = [read(path.parent) for path in sorted(HOME.glob("*/project.json"))]
    return [p for p in found if kind is None or p.kind == kind]


def named(name: str | os.PathLike | None = None) -> Project:
    """The project a tool was told to work on: by its directory's name, by a path, or by `LLMAPPER_PROJECT`.

    There is no default level. A tool that was not told refuses, and says which levels there are.
    """
    said = str(name) if name else os.environ.get(ENV, "")
    if not said:
        levels = ", ".join(p.key for p in projects("level")) or "none yet"
        raise ProjectError(f"which project? name one (a directory under projects/) or set {ENV}; levels here: {levels}")
    for candidate in (HOME / said, Path(said)):
        if (candidate / "project.json").exists():
            return read(candidate)
    raise ProjectError(f"no project {said!r} (levels here: {', '.join(p.key for p in projects('level'))})")
