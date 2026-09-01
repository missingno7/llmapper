"""A construct is a SUBGRAPH, not a sector.

The owner's ownership axis, made executable. Build fixes STORAGE ownership --
every wall lives in exactly one sector's array, and a boundary between two
sectors exists twice as a red-wall twin pair. FUNCTIONAL ownership, whose wall
it is for a mechanism's purposes, is not fixed at all: it depends on the
mechanism and on intent, and it crosses storage boundaries routinely.

The curriculum is emphatic about this. Ninety-four of the tutorials' swept
mechanisms deform more than their own sector, because `dragpoint` moves a
vertex for every wall incident on it and a flagged wall shared with a
neighbour drags the neighbour too. The curtain that stays inside its own
outline is the special case -- an isolation FIN, deliberately built -- not the
default. And the curtain's buttons are XWALLs on its fabric faces while its
receiver is the sector: one construct, three storage kinds.

So a construct declares MEMBERS with roles, and the gate compares the
declaration against what the geometry actually does:

* what a mechanism claims to move, against the motion-set closure;
* what two constructs each claim, against each other -- a vertex or a wall
  claimed by two mechanisms is a defect neither one can see alone.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Iterable

#: What a member does for the construct that owns it.
ROLES = (
    "payload",      # the thing that moves or changes
    "carrier",      # the sector whose XSECTOR holds the mechanism
    "button",       # a surface or sprite that commands it
    "frame",        # the standing geometry the payload runs in
    "seat",         # what the payload rests on or in
    "holder",       # what keeps a member in place
    "junction",     # where the construct meets another
    "seam",         # the isolation cut that keeps motion off the neighbours
    "clearance",    # space that must stay empty for the travel
    "effect",       # something downstream this construct drives
)

#: The three things a member can be, matching Build's three arrays.
KINDS = ("sector", "wall", "vertex", "sprite")


class OwnershipError(ValueError):
    """A declaration that contradicts the geometry or another construct."""


@dataclass(frozen=True)
class Member:
    """One claim: this construct owns this thing, for this purpose."""

    kind: str
    ref: Any
    role: str

    def __post_init__(self) -> None:
        if self.kind not in KINDS:
            raise OwnershipError(f"{self.kind!r} is not one of {KINDS}")
        if self.role not in ROLES:
            raise OwnershipError(f"{self.role!r} is not one of {ROLES}")

    def key(self) -> tuple:
        return (self.kind, self.ref)


@dataclass
class Construct:
    """One mechanism, as the subgraph it actually is."""

    name: str
    kind: str = ""
    members: list[Member] = field(default_factory=list)
    channel: int | None = None
    notes: list[str] = field(default_factory=list)

    def claim(self, kind: str, ref: Any, role: str) -> "Construct":
        self.members.append(Member(kind, ref, role))
        return self

    def of_role(self, role: str) -> list[Member]:
        return [m for m in self.members if m.role == role]

    def sectors(self, *roles: str) -> list[Any]:
        wanted = roles or ROLES
        return sorted({m.ref for m in self.members
                       if m.kind == "sector" and m.role in wanted},
                      key=str)

    def as_json(self) -> dict[str, Any]:
        return {"name": self.name, "kind": self.kind, "channel": self.channel,
                "members": [{"kind": m.kind, "ref": m.ref, "role": m.role}
                            for m in self.members],
                "notes": self.notes}


def conflicts(constructs: Iterable[Construct]) -> list[str]:
    """Two constructs claiming the same thing, where that cannot be shared.

    Sharing is not always wrong -- a junction is the role that says "this is
    where I meet somebody else", and a frame wall is legitimately the frame of
    the room on both sides. What cannot be shared is a PAYLOAD: two mechanisms
    moving one vertex tear the map between them, and neither one's own
    reading can see it.
    """
    owners: dict[tuple, list[tuple[str, str]]] = {}
    for construct in constructs:
        for member in construct.members:
            owners.setdefault(member.key(), []).append(
                (construct.name, member.role))
    out = []
    for key, claims in sorted(owners.items(), key=lambda item: str(item[0])):
        if len(claims) < 2:
            continue
        payloads = [name for name, role in claims if role == "payload"]
        if len(payloads) > 1:
            out.append(
                f"{key[0]} {key[1]} is the payload of {len(payloads)} "
                f"constructs at once ({', '.join(sorted(payloads))}); one "
                f"motion will tear it away from the other")
            continue
        if payloads and any(role in ("frame", "seat", "holder")
                            for _n, role in claims):
            standing = sorted(name for name, role in claims
                              if role in ("frame", "seat", "holder"))
            out.append(
                f"{key[0]} {key[1]} is {payloads[0]}'s payload and "
                f"{', '.join(standing)}'s standing geometry; it cannot both "
                f"move and hold still")
    return out


def check_declared_motion(disk: Any, construct: Construct,
                          carrier_sector: int) -> list[str]:
    """The computed motion set, against what the construct claimed.

    The motion-set closure -- flagged walls plus the vertex drag, both sides
    of every red-wall twin -- IS the functional ownership of a moving
    mechanism. A sector in it that the construct did not claim is a room
    being deformed by a mechanism that does not know it owns it, which is
    what the zoo's curtain was doing to its section.
    """
    from .motion import motion_set

    try:
        found = motion_set(disk, carrier_sector)
    except Exception as exc:
        return [f"{construct.name}: motion set unreadable ({exc})"]
    claimed = set(construct.sectors("payload", "carrier", "seam"))
    out = []
    for sector_id in found["sectors"]:
        if sector_id not in claimed:
            out.append(
                f"{construct.name}: the motion deforms sector {sector_id}, "
                f"which it never claimed -- either claim it as payload or "
                f"cut a seam so it stops there")
    for sector_id in sorted(claimed):
        if (isinstance(sector_id, int) and sector_id != carrier_sector
                and sector_id not in found["sectors"]):
            out.append(
                f"{construct.name}: claims to move sector {sector_id} and "
                f"does not; the flags say otherwise")
    return out
