"""Where Blood does each thing: every type, sector effect and taught lesson, with the maps that show it.

An agent about to build a conveyor needs three answers before it writes a
line: what a conveyor is in the engine's terms, where the campaign has one it
can go and look at, and which tutorial teaches it. The repository knew all
three and could be asked for none of them: `blood_types` names the types, the
mechanism curriculum reads the 136 tutorial maps, `effects` reads every
moving sector -- and a search for "conveyor", "lift" or "614" came back empty.

This is the index that joins them. One entry per thing, all the same shape:

``sector:614``         a sector, wall or sprite TYPE the campaign uses
``effect:conveyor``    something a sector does through its XSECTOR fields
``channel:4``          one of the engine's reserved channels, and who uses it
``lesson:DOOR-SLIDING``  one tutorial map of the mechanism curriculum

Each carries how often and in how many maps, a handful of instances spread
across the campaign (so two agents do not both copy E1M1), what the mechanism
reader made of the moving ones, the lessons that use it, and the library code
that cites those lessons. `tools/catalog.py` builds it into
``knowledge/blood/design/mechanism-examples-v1.json`` and answers from it.

Nothing here is a claim about behaviour. A type's name is the engine's own; an
effect is defined by which fields are set, and says so; a lesson is a file. To
learn what a thing DOES, follow an example with ``catalog mechanisms`` or read
the lesson.
"""

from __future__ import annotations

import ast
import re
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Iterable, Mapping

from .blood_types import RESERVED_CHANNELS, classify
from .effects import read_map_mechanisms
from .format import XSECTOR_SCHEMA
from .model import record_extra, record_fields
from .sector_geom import wall_owners

SCHEMA = "llmapper.mechanism-examples"
SCHEMA_VERSION = 1

#: Instances kept per entry. Enough to find one worth looking at, few enough
#: that an entry is a dozen lines.
EXAMPLES_PER_ENTRY = 8

#: Something a sector does through its extension, defined by the fields that
#: are set and by nothing else. ``all``: every one non-zero; ``any``: at least
#: one; ``none``: none of them. The names are XSECTOR's own and a test holds
#: them to the schema, because a table like this with one misspelt field
#: reports that the campaign never does the thing.
EFFECTS: dict[str, dict[str, Any]] = {
    "conveyor": {
        "all": ("pan_floor", "drag"),
        "says": "the floor pans and drag is set: what stands on it is carried",
        "words": ("belt", "moving floor", "travelator")},
    "panning floor": {
        "all": ("pan_floor",), "none": ("drag",),
        "says": "the floor's texture pans and drag is not set",
        "words": ("flow", "scrolling floor")},
    "panning ceiling": {
        "all": ("pan_ceiling",),
        "says": "the ceiling's texture pans",
        "words": ("scrolling ceiling",)},
    "underwater": {
        "all": ("underwater",),
        "says": "the sector is flagged underwater",
        "words": ("water", "swim", "submerged")},
    "depth": {
        "all": ("depth",),
        "says": "the floor has a sinking depth: a body stands in it, not on it",
        "words": ("water", "wade", "mud", "shallow")},
    "damage": {
        "all": ("damage_type",),
        "says": "the sector hurts what is in it; damage_type says how",
        "words": ("lava", "acid", "hurt", "burn")},
    "crush": {
        "all": ("crush",),
        "says": "crush is set: the moving sector does not stop for a body",
        "words": ("crusher", "press", "piston")},
    "wind": {
        "any": ("wind_velocity", "wind_always"),
        "says": "the sector pushes what is in it; wind_angle says which way",
        "words": ("blow", "current", "push")},
    "bob": {
        "any": ("bob_z_range", "bob_floor", "bob_ceiling"),
        "says": "the floor or ceiling bobs up and down",
        "words": ("float", "raft", "boat", "swell")},
    "shade wave": {
        "all": ("amplitude",),
        "says": "the sector's shade animates; shade_wave says with which wave",
        "words": ("flicker", "pulse", "strobe", "light", "glow")},
    "keyed": {
        "all": ("key",),
        "says": "the sector demands a key",
        "words": ("key", "lock")},
    "locked": {
        "all": ("locked",),
        "says": "the sector starts locked and something must unlock it",
        "words": ("lock",)},
    "enter trigger": {
        "all": ("trigger_enter",),
        "says": "walking into the sector sets it off",
        "words": ("touchplate", "tripwire", "step on")},
    "exit trigger": {
        "all": ("trigger_exit",),
        "says": "walking out of the sector sets it off",
        "words": ("leave",)},
    "push trigger": {
        "all": ("trigger_push",),
        "says": "pressing Use while standing in the sector sets it off",
        "words": ("use", "press")},
    "wall push trigger": {
        "all": ("trigger_wall_push",),
        "says": "pressing Use against one of the sector's walls sets it off",
        "words": ("use", "door", "shove")},
    "shot trigger": {
        "all": ("trigger_vector",),
        "says": "a shot into the sector sets it off",
        "words": ("shoot", "bullet")},
}

#: Words a mapper says that the engine's names do not contain. Each is tried
#: alongside the word itself.
SYNONYMS: dict[str, tuple[str, ...]] = {
    "elevator": ("lift", "zmotion"),
    "lift": ("zmotion",),
    "platform": ("lift", "zmotion"),
    "teleporter": ("teleport", "warp"),
    "teleport": ("warp",),
    "belt": ("conveyor",),
    "crusher": ("crush", "piston"),
    "swing": ("swinging", "rotate"),
    "rotating": ("rotate",),
    "sliding": ("slide",),
    "breakable": ("gib", "explode"),
    "destructible": ("gib", "explode"),
    "enemy": ("dude",),
    "monster": ("dude",),
    "pickup": ("item",),
    "button": ("switch",),
    "lever": ("switch",),
    "light": ("lighting", "shade"),
    "water": ("underwater", "depth"),
    "secret": ("secrets",),
    "ror": ("stack", "stacks3dspaces"),
    "stairs": ("steps", "escalator"),
}


def _words_of_name(name: str) -> list[str]:
    """`kSectorSlideMarked` -> sector, slide, marked; `DOOR-SLIDING` -> door, sliding."""
    text = re.sub(r"^k(?=[A-Z])", "", name)
    parts = re.findall(r"[A-Z]+(?![a-z])|[A-Z][a-z]+|[a-z]+|\d+", text)
    return [part.lower() for part in parts if not part.isdigit()]


def _set(extra: Mapping[str, Any], names: Iterable[str]) -> list[bool]:
    return [bool(extra.get(name)) for name in names]


def effects_of(extra: Mapping[str, Any] | None) -> list[str]:
    """Which of `EFFECTS` a sector's extension fields amount to."""
    if not extra:
        return []
    found = []
    for name, rule in EFFECTS.items():
        if not all(_set(extra, rule.get("all", ()))):
            continue
        if rule.get("any") and not any(_set(extra, rule["any"])):
            continue
        if any(_set(extra, rule.get("none", ()))):
            continue
        found.append(name)
    return found


def observe(name: str, disk: Any) -> dict[str, Any]:
    """Everything one map contributes: typed objects, sector effects, readings.

    An instance is ``(sector, id)``: the sector to go and stand in, and the
    object's own index. For a sector the two are the same number. `disk` is a
    `DiskMap`: the mechanism reader behind `readings` reads no other shape.
    """
    types: dict[str, list[tuple[int, int]]] = defaultdict(list)
    effects: dict[str, list[tuple[int, int]]] = defaultdict(list)
    sends: dict[str, list[tuple[int, int]]] = defaultdict(list)
    hears: dict[str, list[tuple[int, int]]] = defaultdict(list)

    def wiring(record: Any, sector: int, index: int) -> None:
        extra = record_extra(record)
        if not extra:
            return
        for field, into in (("tx_id", sends), ("rx_id", hears)):
            channel = int(extra.get(field, 0) or 0)
            if channel in RESERVED_CHANNELS:
                into[f"channel:{channel}"].append((sector, index))

    for index, sector in enumerate(disk.sectors):
        type_id = int(record_fields(sector)["type"])
        if type_id:
            types[f"sector:{type_id}"].append((index, index))
        for effect in effects_of(record_extra(sector)):
            effects[effect].append((index, index))
        wiring(sector, index, index)
    owners = wall_owners(disk)
    for index, wall in enumerate(disk.walls):
        type_id = int(record_fields(wall)["type"])
        if type_id:
            types[f"wall:{type_id}"].append((owners.get(index, -1), index))
        wiring(wall, owners.get(index, -1), index)
    for index, sprite in enumerate(disk.sprites):
        fields = record_fields(sprite)
        type_id = int(fields["type"])
        if type_id:
            types[f"sprite:{type_id}"].append((int(fields["sector"]), index))
        wiring(sprite, int(fields["sector"]), index)
    readings = {}
    for item in read_map_mechanisms(disk, map_name=name)["mechanisms"]:
        readings[int(item["sector_id"])] = {
            "is": item["design_object"],
            "worked_by": item["primitive"].get("interaction") or "nothing a player does",
        }
    return {"map": name, "types": dict(types), "effects": dict(effects),
            "sends": dict(sends), "hears": dict(hears), "readings": readings}


def _spread(per_map: list[tuple[str, list[tuple[int, int]]]]) -> list[dict[str, Any]]:
    """A few instances, one map at a time, so they do not all come from the first."""
    picked: list[dict[str, Any]] = []
    depth = 0
    while len(picked) < EXAMPLES_PER_ENTRY:
        took = False
        for name, instances in per_map:
            if depth < len(instances) and len(picked) < EXAMPLES_PER_ENTRY:
                sector, index = instances[depth]
                picked.append({"map": name, "sector": sector, "id": index})
                took = True
        if not took:
            break
        depth += 1
    return picked


def cited_lessons(package: str | Path) -> dict[str, list[str]]:
    """Lesson name -> the library functions and classes whose docstring cites it.

    A constructor built to a tutorial says so where it is defined ("built to
    `maps/blood/mechanism/Vanilla/MACHINERY-LIFT.map`"). That sentence is the
    link from a lesson to the code that builds or reads the thing, and it is
    read here rather than kept in a second table.
    """
    found: dict[str, list[str]] = defaultdict(list)
    pattern = re.compile(r"([A-Z0-9#]+(?:-[A-Z0-9]+)+)\.map")
    for path in sorted(Path(package).glob("*.py")):
        if path.stem == "examples":
            continue                     # its own docstring names one, as an example
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in tree.body:
            if not isinstance(node, (ast.FunctionDef, ast.ClassDef)):
                continue
            doc = ast.get_docstring(node) or ""
            for lesson in sorted(set(pattern.findall(doc))):
                found[lesson].append(f"bloodmap.{path.stem}.{node.name}")
    return dict(found)


def build(observations: Iterable[dict[str, Any]], *,
          curriculum: Mapping[str, Any] | None = None,
          cited: Mapping[str, list[str]] | None = None) -> dict[str, Any]:
    """Join the campaign's observations, the curriculum and the code's citations."""
    observations = list(observations)
    cited = cited or {}
    type_instances: dict[str, list[tuple[str, list[tuple[int, int]]]]] = defaultdict(list)
    effect_instances: dict[str, list[tuple[str, list[tuple[int, int]]]]] = defaultdict(list)
    readings: dict[str, Counter] = defaultdict(Counter)
    worked: dict[str, Counter] = defaultdict(Counter)
    for seen in observations:
        for key, instances in seen["types"].items():
            type_instances[key].append((seen["map"], instances))
            if key.startswith("sector:"):
                for sector, _index in instances:
                    reading = seen["readings"].get(sector)
                    if reading:
                        readings[key][reading["is"]] += 1
                        worked[key][reading["worked_by"]] += 1
        for key, instances in seen["effects"].items():
            effect_instances[key].append((seen["map"], instances))

    #: the manual's first-tier lessons lead, so the one named is one to read
    lessons_by_type: dict[str, list[tuple[int, str]]] = defaultdict(list)
    entries: dict[str, dict[str, Any]] = {}
    for lesson in (curriculum or {}).get("maps", []):
        name = Path(lesson["map"]).stem
        used = sorted({f"sector:{c['type']}" for c in lesson["constructs"] if c["type"]})
        slots = sorted({slot for c in lesson["constructs"] for slot in c["slots"]})
        for key in used:
            lessons_by_type[key].append((int(lesson.get("tier") or 9), name))
        entries[f"lesson:{name}"] = {
            "kind": "lesson", "name": name, "tier": lesson.get("tier"),
            "words": _words_of_name(name),
            "says": "; ".join(c["sentence"] for c in lesson["constructs"][:3])
                    or "no moving sector: read the map for what it shows",
            "size": {"sectors": lesson["sectors"], "walls": lesson["walls"],
                     "sprites": lesson["sprites"]},
            "types": used, "slots": slots,
            "sectors": [int(c["sector"]) for c in lesson["constructs"]][:6],
            "sprite_roles": lesson.get("sprite_roles", {}),
            "cited_by": sorted(cited.get(name, [])),
        }

    for key, per_map in sorted(type_instances.items()):
        kind, _colon, number = key.partition(":")
        named = classify(kind, int(number))
        name = named.get("name") or f"type {number}"
        entry = {
            "kind": f"{kind} type", "name": name,
            "category": named.get("category"),
            "known": bool(named.get("known")),
            "words": _words_of_name(name) + [str(named.get("category") or "")],
            "count": sum(len(instances) for _name, instances in per_map),
            "maps": len(per_map),
            "examples": _spread(per_map),
            "lessons": [name for _tier, name in sorted(lessons_by_type.get(key, []))][:8],
        }
        if readings.get(key):
            entry["read_as"] = dict(readings[key].most_common())
            entry["worked_by"] = dict(worked[key].most_common())
        entries[key] = entry

    for name, rule in EFFECTS.items():
        per_map = effect_instances.get(name, [])
        wanted = {name.split()[0]} | set(rule.get("words", ()))
        entries[f"effect:{name}"] = {
            "kind": "effect", "name": name, "says": rule["says"],
            "fields": {k: list(rule[k]) for k in ("all", "any", "none") if rule.get(k)},
            "words": sorted(set(name.split()) | set(rule.get("words", ()))),
            "count": sum(len(instances) for _name, instances in per_map),
            "maps": len(per_map),
            "examples": _spread(per_map),
            "lessons": sorted(
                key.split(":", 1)[1] for key, entry in entries.items()
                if entry["kind"] == "lesson"
                and wanted & set(entry["words"]))[:12],
        }

    for channel, named in sorted(RESERVED_CHANNELS.items()):
        key = f"channel:{channel}"
        senders = [(seen["map"], seen["sends"][key]) for seen in observations
                   if seen["sends"].get(key)]
        hearers = [(seen["map"], seen["hears"][key]) for seen in observations
                   if seen["hears"].get(key)]
        if not senders and not hearers:
            continue
        sent = sum(len(instances) for _name, instances in senders)
        heard = sum(len(instances) for _name, instances in hearers)
        entries[key] = {
            "kind": "channel", "name": named["name"],
            "says": f"{sent} objects send on it and {heard} listen to it"
                    + (f"; {named['notes']}" if named.get("notes") else ""),
            "words": _words_of_name(named["name"]),
            "count": sent + heard,
            "maps": len({name for name, _i in senders} | {name for name, _i in hearers}),
            "examples": _spread(senders or hearers),
            "examples_are": "senders" if senders else "listeners",
            "lessons": [],
        }

    return {
        "$schema": SCHEMA, "schema_version": SCHEMA_VERSION,
        "maps": [seen["map"] for seen in observations],
        "reading_guide": [
            "an example is a place to go and look: map, the sector to stand "
            "in, and the object's own index",
            "examples are taken one map at a time, in map order, so they are "
            "spread across the campaign and are not a ranking",
            "read_as and worked_by are `bloodmap.effects`' reading of the "
            "moving sectors of that type; a name from where a thing sits, "
            "never from its type",
            "an effect is defined by the XSECTOR fields listed under `fields` "
            "and by nothing else",
            "cited_by is library code whose docstring names the lesson",
            "a channel entry counts who sends on and who listens to one of "
            "the engine's reserved channels; its examples are the senders",
        ],
        "entries": entries,
    }


def _matches(word: str, haystack: str) -> bool:
    return any(candidate in haystack
               for candidate in (word, *SYNONYMS.get(word, ())))


def search(index: Mapping[str, Any], words: Iterable[str]) -> list[tuple[str, dict[str, Any]]]:
    """Entries answering to every word, the most useful first.

    Lessons the manual treats first lead, then effects, then types by how
    often the campaign uses them. A word also tries its `SYNONYMS`. When
    nothing answers to every word, the entries answering to the most of them
    are returned instead.
    """
    wanted = [word.lower() for word in words]
    hits, partial = [], []
    for key, entry in index["entries"].items():
        haystack = " ".join([key.lower(), entry["name"].lower(),
                             " ".join(entry.get("words", [])),
                             str(entry.get("says", "")).lower()])
        matched = sum(1 for word in wanted if _matches(word, haystack))
        if matched == len(wanted):
            hits.append((key, entry))
        elif matched:
            partial.append((matched, key, entry))
    if not hits and partial:
        # Nothing answers to all of "lift elevator platform": an agent that
        # offers three words for one thing should get the thing, so fall back
        # to whatever answers to most of them.
        best = max(matched for matched, _key, _entry in partial)
        hits = [(key, entry) for matched, key, entry in partial if matched == best]

    def rank(item: tuple[str, dict[str, Any]]) -> tuple[int, int, str]:
        key, entry = item
        if key.split(":", 1)[1].lower() in wanted or entry["name"].lower() in wanted:
            return (-1, 0, key)          # asked for by its own number or name
        if entry["kind"] == "lesson":
            return (0, int(entry.get("tier") or 9), key)
        if entry["kind"] in ("effect", "channel"):
            return (1, -int(entry["count"]), key)
        return (2, -int(entry["count"]), key)

    return sorted(hits, key=rank)


def resolve(index: Mapping[str, Any], what: str) -> str | None:
    """The entry a person means by `sector:614`, `kSectorSlide`, `DOOR-SLIDING` or `conveyor`."""
    entries = index["entries"]
    if what in entries:
        return what
    if what.isdigit():
        return None                      # a bare number is a tile, not a type
    lowered = what.lower()
    for key, entry in entries.items():
        if key.lower() == lowered or entry["name"].lower() == lowered:
            return key
    for prefix in ("lesson:", "effect:", "channel:"):
        for key in entries:
            if key.lower() == prefix + lowered:
                return key
    return None


def xsector_field_names() -> frozenset[str]:
    return frozenset(name for name, _bits, _signed in XSECTOR_SCHEMA)
