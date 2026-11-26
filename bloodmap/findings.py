"""What building levels has taught us, one finding a file, each saying how it is known.

The owner, 2026-11-26: "When an agent discovers a new texture usage, construction
technique, engine behavior, mechanism, visual convention, validation method, or
useful precedent, that discovery should be recorded in the appropriate shared
system ... Preserve the distinction between verified engine behavior, observed
precedents, statistical tendencies, artistic interpretations, and unverified
hypotheses."

Until that day such things were written where they were met: in the docstring of
the level module that needed them, in a project's notes, or nowhere but one
agent's memory. A second level could not find them, and its agent learned them
again.

A FINDING is one thing worth knowing before building, small enough to act on:

``claim``     the thing itself, in a sentence or two
``standing``  how it is known (`STANDINGS`); the reader decides by this how far to trust it
``evidence``  where to check it: an engine file and line, a map and a sector, a
              count and the tool that made it, the day and the owner's words
``use``       what to do about it; ``code`` names the functions that already do it
``scope``     ``blood`` (the game), ``build`` (the engine family), ``duke``, or
              ``project:<name>`` for a decision that is one level's own
``learned``   in which project and on which day

`standing` is the point. A thing that worked in one level of ours is ``practice``
and says so: it is evidence about us, not about Blood, and no other level is
bound by it. Only ``engine``, ``precedent`` and ``tendency`` are about the game,
and each must cite what its kind is made of (`problems`). A finding found false
is kept as ``refuted`` with what is true ``instead``, so that it is not found
again.

One file a finding (`HOME`), so that two levels can file at once. The other
shelves are for what they hold: a tile in a slot is a tile context
(`bloodmap.tile_contexts`), a mechanism is the catalog's wiring, how Blood built
a kind of place is a study. A finding is for what none of them takes: how a
thing is built, what the engine does with it, what a check cannot see.
"""

from __future__ import annotations

import ast
import datetime
import json
import re
from pathlib import Path
from typing import Any, Iterable

ROOT = Path(__file__).resolve().parent.parent
HOME = ROOT / "knowledge" / "blood" / "findings"

#: how a finding is known, the firmest first; the sentence is what its evidence must be
STANDINGS = {
    "engine": "read in the engine's source or seen in a run of the engine: cites the file and line, or the run",
    "ruling": "the owner said so: cites the day, and the words where they are kept",
    "precedent": "a shipped map does it: cites the map and the sector, wall or sprite",
    "tendency": "counted over a population of maps: cites the count and what counted it",
    "practice": "done in a level of ours, and it held: evidence about us, not about the game",
    "hypothesis": "believed and not checked",
    "refuted": "was believed and is false: says what is true `instead`",
}
#: what a finding is about
TOPICS = ("engine", "renderer", "construction", "texture", "light", "mechanism", "sprite", "sound",
          "gameplay", "place", "validation", "workflow")
SCOPES = ("blood", "build", "duke")
FIELDS = ("id", "topic", "standing", "claim", "evidence", "use", "code", "scope", "learned", "words", "instead")

_SOURCE = re.compile(r"\.(cpp|c|h|hpp|con|pas|asm)\b|\brun\b|\bheadless\b|\bobserver\b", re.I)
_MAP = re.compile(r"\b[A-Z][A-Z0-9_]{2,11}\b[^.;]*?\b(s|sector|sectors|wall|walls|sprite|sprites|w|#)\s*\d+", re.I)
_DAY = re.compile(r"\b20\d\d-\d\d-\d\d\b")


class FindingError(ValueError):
    pass


def read(home: Path | None = None) -> list[dict[str, Any]]:
    """Every finding on file, by id."""
    out = []
    for path in sorted((home or HOME).glob("*.json")):
        try:
            row = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            raise FindingError(f"{path.name}: not JSON ({exc})") from exc
        row["_file"] = path.name
        out.append(row)
    return out


def _defined(module: Path) -> set[str]:
    """Every name a module defines: its functions, classes and assignments, and a class's own by `Class.name`."""
    try:
        tree = ast.parse(module.read_text(encoding="utf-8"))
    except (OSError, SyntaxError):
        return set()
    names: set[str] = set()

    def take(body, prefix=""):
        for node in body:
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                names.add(prefix + node.name)
                if isinstance(node, ast.ClassDef):
                    take(node.body, prefix + node.name + ".")
            elif isinstance(node, (ast.Assign, ast.AnnAssign)):
                for target in (node.targets if isinstance(node, ast.Assign) else [node.target]):
                    for leaf in ast.walk(target):
                        if isinstance(leaf, ast.Name):
                            names.add(prefix + leaf.id)
    take(tree.body)
    return names


def resolves(name: str, root: Path = ROOT) -> bool:
    """Whether `code` names something that is there: a file by its path, or `package.module.name` (`.Class.name`)."""
    if "/" in name or name.endswith((".py", ".md", ".json")):
        return (root / name.split(":")[0]).exists()
    parts = name.split(".")
    for cut in range(len(parts), 0, -1):
        module = root.joinpath(*parts[:cut]).with_suffix(".py")
        if module.exists():
            rest = ".".join(parts[cut:])
            return not rest or rest in _defined(module)
    return False


def problems(row: dict[str, Any], root: Path = ROOT) -> list[str]:
    """What is wrong with one finding: an empty list is a finding that may be filed."""
    said = []
    ident = str(row.get("id", ""))
    if not re.fullmatch(r"[a-z0-9]+(-[a-z0-9]+)*", ident) or len(ident) > 80:
        said.append("id is lower-case words joined by hyphens, eighty characters at most")
    if row.get("_file") not in (None, f"{ident}.json"):
        said.append(f"the file is named {row['_file']}, not {ident}.json")
    for key in row:
        if key not in FIELDS and not key.startswith("_"):
            said.append(f"unknown field {key!r}")
    if row.get("topic") not in TOPICS:
        said.append(f"topic is one of {', '.join(TOPICS)}")
    standing = row.get("standing")
    if standing not in STANDINGS:
        said.append(f"standing is one of {', '.join(STANDINGS)}")
    claim = str(row.get("claim", "")).strip()
    if not 20 <= len(claim) <= 700:
        said.append("claim is the thing itself in a sentence or two (20 to 700 characters)")
    evidence = row.get("evidence", [])
    if not isinstance(evidence, list) or any(not isinstance(e, str) or not e.strip() for e in evidence):
        said.append("evidence is a list of sentences")
        evidence = []
    whole = " ".join(evidence)
    if standing != "hypothesis" and not evidence:
        said.append("evidence is missing: only a hypothesis may stand on nothing")
    if standing == "engine" and not _SOURCE.search(whole):
        said.append("an engine finding cites a source file (`actor.cpp:2710`) or the run it was seen in")
    if standing == "precedent" and not _MAP.search(whole):
        said.append("a precedent cites a map and where in it (`E3M1 s79`)")
    if standing == "tendency" and not re.search(r"\d", whole):
        said.append("a tendency cites its count")
    if standing == "ruling" and not _DAY.search(whole):
        said.append("a ruling cites the day it was given (`2026-11-25`)")
    if standing == "refuted" and not str(row.get("instead", "")).strip():
        said.append("a refuted finding says what is true `instead`")
    scope = str(row.get("scope", ""))
    if scope not in SCOPES and not re.fullmatch(r"project:[a-z0-9-]+", scope):
        said.append(f"scope is one of {', '.join(SCOPES)}, or project:<name>")
    learned = row.get("learned", {})
    if not isinstance(learned, dict) or not learned.get("in") or not _DAY.fullmatch(str(learned.get("date", ""))):
        said.append("learned says in which project and on which day: {\"in\": ..., \"date\": \"YYYY-MM-DD\"}")
    for field in ("code", "words"):
        if not isinstance(row.get(field, []), list):
            said.append(f"{field} is a list")
    for name in row.get("code", []) if isinstance(row.get("code", []), list) else []:
        if not resolves(str(name), root):
            said.append(f"code names {name!r}, which is not there")
    return said


def check(home: Path | None = None, root: Path = ROOT) -> list[str]:
    """Everything wrong with the shelf, a line each."""
    return [f"{row.get('id') or row['_file']}: {said}" for row in read(home) for said in problems(row, root)]


def record(*, id: str, topic: str, standing: str, claim: str, evidence: Iterable[str], learned_in: str,
           use: str = "", code: Iterable[str] = (), scope: str = "blood", words: Iterable[str] = (), instead: str = "",
           date: str | None = None, home: Path | None = None, replace: bool = False) -> dict[str, Any]:
    """File one finding. It is refused if it is not well made, or if the id is taken and `replace` is not said."""
    home = home or HOME
    row = {"id": id, "topic": topic, "standing": standing, "claim": " ".join(claim.split()),
           "evidence": [" ".join(e.split()) for e in evidence], "use": " ".join(use.split()), "code": list(code),
           "scope": scope, "learned": {"in": learned_in, "date": date or datetime.date.today().isoformat()},
           "words": sorted({w.lower() for w in words})}
    if instead:
        row["instead"] = " ".join(instead.split())
    wrong = problems(row)
    if wrong:
        raise FindingError("; ".join(wrong))
    path = home / f"{id}.json"
    if path.exists() and not replace:
        raise FindingError(f"{id} is on file already: read it, and say --replace to rewrite it")
    home.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(row, indent=1, ensure_ascii=False) + "\n", encoding="utf-8", newline="\n")
    return row


def _text(row: dict[str, Any]) -> tuple[str, str]:
    """What is searched: the words a finding is found by first, then everything else it says."""
    first = " ".join([row.get("id", "").replace("-", " "), row.get("claim", ""), " ".join(row.get("words", [])), row.get("topic", "")])
    rest = " ".join([row.get("use", ""), " ".join(row.get("evidence", [])), " ".join(row.get("code", [])), row.get("instead", ""),
                     row.get("scope", ""), row.get("standing", "")])
    return first.lower(), rest.lower()


def find(words: Iterable[str], *, topic: str | None = None, standing: str | None = None, scope: str | None = None,
         home: Path | None = None) -> list[dict[str, Any]]:
    """The findings that answer to every word (a word matches where a word begins: `stair` finds `stairs`), the firmest first."""
    words = [w.lower() for w in words]
    order = list(STANDINGS)
    hits = []
    for row in read(home):
        if topic and row.get("topic") != topic or standing and row.get("standing") != standing:
            continue
        if scope and row.get("scope") != scope:
            continue
        first, rest = _text(row)
        marks = [(len(re.findall(rf"\b{re.escape(w)}", first)), len(re.findall(rf"\b{re.escape(w)}", rest))) for w in words]
        if any(a + b == 0 for a, b in marks):
            continue
        rank = order.index(row["standing"]) if row.get("standing") in order else len(order)
        hits.append((-sum(1 for a, _b in marks if a), rank, row["id"], row))
    return [row for *_key, row in sorted(hits, key=lambda h: h[:3])]


def line(row: dict[str, Any]) -> str:
    """One finding on one line, as a search shows it."""
    where = "" if row.get("scope") == "blood" else f" ({row.get('scope')})"
    return f"  [{row.get('standing')}] {row.get('id')}{where}: {row.get('claim')}"


def show(row: dict[str, Any]) -> str:
    """One finding in full."""
    out = [f"{row['id']}   [{row['standing']}: {STANDINGS.get(row['standing'], '?')}]",
           f"  about {row['topic']}, of {row['scope']}; learned in {row['learned']['in']}, {row['learned']['date']}", "",
           f"  {row['claim']}"]
    if row.get("instead"):
        out += ["", f"  INSTEAD  {row['instead']}"]
    if row.get("use"):
        out += ["", f"  USE  {row['use']}"]
    if row.get("code"):
        out += ["  CODE  " + ", ".join(row["code"])]
    out += ["", "  EVIDENCE"] + [f"    - {e}" for e in row.get("evidence", [])]
    return "\n".join(out)
