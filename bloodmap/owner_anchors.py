"""The owner's tile readings, as a first-class input.

`knowledge/blood/design/owner-anchors-v1.json` is 97 tiles the owner named by
hand. It has been sitting beside the mining pipeline being read by people and
not by code, which meant every module that needed a tile's meaning typed its
own list and drifted.

This is the typed access to it. Nothing here mines, derives or averages: the
file is **OWNER provenance** and is reproduced, never rewritten.

Two things in the reading guide are rules rather than notes, and both are
executable here.

**Binding.** The owner's principle: every tile-to-meaning rule has
exceptions, and how many depends on how distinctive the tile looks. A
mannequin (2377) binds its meaning almost always; a generic wall (456) is
material that occasionally plays an object role. So a **strong**-binding tile
may contribute naming evidence and a **weak**-binding one never may -- it is
material, and a name resting on it is a name resting on wallpaper. Tiles the
owner left unset are untested and are treated as weak for naming, because an
untested claim is not evidence.

**Wiring.** A wiring tile is an engine marker invisible in game. It never
counts as a visible object, which is the same rule
`blood_types.sprite_visibility` applies from the other direction; the two are
cross-checked by a test rather than kept in step by hand.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path
from typing import Any, Iterable, Mapping

SCHEMA = "llmapper.blood-owner-anchors"
SCHEMA_VERSION = "1"

#: Where the owner's file lives, relative to the repository root.
ANCHOR_PATH = Path("knowledge") / "blood" / "design" / "owner-anchors-v1.json"

#: First-glance readings. A tile can legitimately turn up as another kind.
KINDS = frozenset({"sprite", "wall", "surface", "maskwall"})
#: The owner's two graded readings. Anything else is a malformed entry.
BINDINGS = frozenset({"strong", "weak"})

#: Provenance every consumer stamps on what it takes from here.
PROVENANCE = "OWNER"


class OwnerAnchorError(ValueError):
    """The owner's file says something this cannot read."""


@dataclass(frozen=True)
class OwnerAnchor:
    """One tile the owner named."""

    picnum: int
    kind: str
    label_en: str
    label_cs: str = ""
    notes: str = ""
    binding: str | None = None
    wiring: bool = False
    translucent: bool = False
    cross_refs: tuple[str, ...] = ()
    state_pair: Mapping[str, int] = field(default_factory=dict)
    dual_role: str = ""

    @property
    def may_name(self) -> bool:
        """May this tile contribute evidence to *naming* something?

        Only a strong binding may. A weak or untested one is material: it
        describes what a surface is made of, not what the thing is.
        """
        return self.binding == "strong"

    def describe(self) -> str:
        """The label as a report should print it, with its source attached."""
        return f"{self.label_en} (owner)"

    def provenance(self, used_for: str = "") -> dict[str, Any]:
        """Where a claim taken from this anchor came from.

        Stamped per use, so a wrong name leads back to the tile and the
        binding it was allowed on rather than to a module that once typed a
        number into a list.
        """
        out = {
            "source": PROVENANCE,
            "anchor": self.picnum,
            "label": self.label_en,
            "binding": self.binding or "untested",
            "may_name": self.may_name,
            "file": str(ANCHOR_PATH).replace("\\", "/"),
        }
        if used_for:
            out["used_for"] = used_for
        return out

    def to_dict(self) -> dict[str, Any]:
        out: dict[str, Any] = {
            "picnum": self.picnum, "kind": self.kind,
            "label_en": self.label_en, "label_cs": self.label_cs,
            "binding": self.binding, "wiring": self.wiring,
            "translucent": self.translucent,
        }
        if self.notes:
            out["notes"] = self.notes
        if self.cross_refs:
            out["cross_refs"] = list(self.cross_refs)
        if self.state_pair:
            out["state_pair"] = dict(self.state_pair)
        if self.dual_role:
            out["dual_role"] = self.dual_role
        return out


@dataclass(frozen=True)
class OwnerAnchors:
    """The whole file, indexed the ways callers actually ask."""

    anchors: tuple[OwnerAnchor, ...]
    provenance: Mapping[str, Any] = field(default_factory=dict)
    reading_guide: Mapping[str, str] = field(default_factory=dict)

    def __post_init__(self) -> None:
        #: Built once here rather than memoized on the method: the dataclass
        #: carries mappings, so it is not hashable and lru_cache cannot key
        #: on `self`.
        object.__setattr__(self, "_index",
                           {item.picnum: item for item in self.anchors})

    def __len__(self) -> int:
        return len(self.anchors)

    def __iter__(self):
        return iter(self.anchors)

    def get(self, picnum: int) -> OwnerAnchor | None:
        return self._index.get(int(picnum))

    def __contains__(self, picnum: object) -> bool:
        try:
            return int(picnum) in self._index  # type: ignore[arg-type]
        except (TypeError, ValueError):
            return False

    def by_kind(self, kind: str) -> tuple[OwnerAnchor, ...]:
        if kind not in KINDS:
            raise OwnerAnchorError(f"no such anchor kind {kind!r}; {sorted(KINDS)}")
        return tuple(item for item in self.anchors if item.kind == kind)

    def by_binding(self, binding: str) -> tuple[OwnerAnchor, ...]:
        if binding not in BINDINGS:
            raise OwnerAnchorError(
                f"no such binding {binding!r}; {sorted(BINDINGS)}")
        return tuple(item for item in self.anchors if item.binding == binding)

    def wiring_picnums(self) -> frozenset[int]:
        """Tiles that are engine markers and never a visible object."""
        return frozenset(item.picnum for item in self.anchors if item.wiring)

    def state_pairs(self) -> dict[int, dict[str, int]]:
        """intact/broken and bare/overgrown pairs, by tile."""
        return {item.picnum: dict(item.state_pair)
                for item in self.anchors if item.state_pair}

    def naming_picnums(self) -> frozenset[int]:
        """Tiles a name may rest on: strong binding and nothing else."""
        return frozenset(item.picnum for item in self.anchors if item.may_name)

    def label(self, picnum: int, default: str = "") -> str:
        anchor = self.get(picnum)
        return anchor.describe() if anchor is not None else default

    def may_name(self, picnum: int) -> bool:
        anchor = self.get(picnum)
        return bool(anchor and anchor.may_name)

    def naming_evidence(self, picnums: Iterable[int], *,
                        used_for: str = "") -> list[dict[str, Any]]:
        """The subset of these tiles a name is allowed to rest on.

        Weak and untested tiles are dropped rather than downweighted. The
        owner's rule is about what the evidence *is*, not how much of it
        there is: a generic wall texture appearing on a moved face says the
        face is made of that, and nothing about what the mechanism is for.
        """
        out = []
        for picnum in picnums:
            anchor = self.get(picnum)
            if anchor is not None and anchor.may_name:
                out.append(anchor.provenance(used_for))
        return out

    def to_dict(self) -> dict[str, Any]:
        return {
            "$schema": SCHEMA, "schema_version": SCHEMA_VERSION,
            "count": len(self.anchors),
            "provenance": dict(self.provenance),
            "anchors": [item.to_dict() for item in self.anchors],
        }


def _entry(raw: Mapping[str, Any], index: int) -> OwnerAnchor:
    where = f"anchors[{index}]"
    for required in ("picnum", "kind", "label_en"):
        if required not in raw:
            raise OwnerAnchorError(f"{where} has no {required!r}")
    try:
        picnum = int(raw["picnum"])
    except (TypeError, ValueError) as exc:
        raise OwnerAnchorError(f"{where} picnum is not a number") from exc
    if picnum < 0:
        raise OwnerAnchorError(f"{where} picnum {picnum} is negative")
    kind = str(raw["kind"])
    if kind not in KINDS:
        raise OwnerAnchorError(f"{where} kind {kind!r} is not one of {sorted(KINDS)}")
    binding = raw.get("binding")
    if binding is not None and binding not in BINDINGS:
        raise OwnerAnchorError(
            f"{where} binding {binding!r} is not one of {sorted(BINDINGS)}")
    pair = raw.get("state_pair") or {}
    if not isinstance(pair, Mapping):
        raise OwnerAnchorError(f"{where} state_pair is not a mapping")
    for name, other in pair.items():
        try:
            int(other)
        except (TypeError, ValueError) as exc:
            raise OwnerAnchorError(
                f"{where} state_pair[{name!r}] is not a tile number") from exc
    refs = raw.get("cross_refs") or ()
    if isinstance(refs, str):
        raise OwnerAnchorError(f"{where} cross_refs is a string, not a list")
    return OwnerAnchor(
        picnum=picnum, kind=kind,
        label_en=str(raw["label_en"]), label_cs=str(raw.get("label_cs") or ""),
        notes=str(raw.get("notes") or ""), binding=binding,
        wiring=bool(raw.get("wiring")),
        translucent=bool(raw.get("translucent")),
        cross_refs=tuple(str(item) for item in refs),
        state_pair={str(k): int(v) for k, v in pair.items()},
        dual_role=str(raw.get("dual_role") or ""),
    )


def parse_owner_anchors(document: Mapping[str, Any]) -> OwnerAnchors:
    """Validate the owner's document and index it.

    Malformed entries raise here, so a bad edit fails a test rather than a
    mining run three modules away.
    """
    if document.get("$schema") != SCHEMA:
        raise OwnerAnchorError(
            f"expected $schema {SCHEMA!r}, got {document.get('$schema')!r}")
    raw = document.get("anchors")
    if not isinstance(raw, list) or not raw:
        raise OwnerAnchorError("the document carries no anchors")
    anchors = tuple(_entry(item, index) for index, item in enumerate(raw))
    seen: set[int] = set()
    for anchor in anchors:
        if anchor.picnum in seen:
            raise OwnerAnchorError(f"tile {anchor.picnum} is named twice")
        seen.add(anchor.picnum)
    #: A state pair has to point at a tile that exists in the file, or the
    #: pairing is a dangling claim.
    for anchor in anchors:
        for name, other in anchor.state_pair.items():
            if other not in seen:
                raise OwnerAnchorError(
                    f"tile {anchor.picnum} pairs {name!r} with {other}, "
                    "which the file does not name")
    return OwnerAnchors(
        anchors=anchors,
        provenance=dict(document.get("provenance") or {}),
        reading_guide=dict(document.get("reading_guide") or {}),
    )


def _repository_root() -> Path:
    return Path(__file__).resolve().parents[1]


@lru_cache(maxsize=4)
def load_owner_anchors(path: str | Path | None = None) -> OwnerAnchors:
    """Read and validate the owner's anchors. Cached; the file is static."""
    target = Path(path) if path is not None else _repository_root() / ANCHOR_PATH
    if not target.is_file():
        raise OwnerAnchorError(f"the owner's anchors are not at {target}")
    #: The labels carry Czech originals, so the encoding is not optional.
    document = json.loads(target.read_text(encoding="utf-8"))
    return parse_owner_anchors(document)


def owner_label(picnum: int, default: str = "") -> str:
    """Convenience for a report line: `"grate/lattice (owner)"`."""
    try:
        return load_owner_anchors().label(picnum, default)
    except OwnerAnchorError:
        return default
