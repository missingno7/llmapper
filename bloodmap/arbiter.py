"""Resolve collisions over Blood's single-slot resources, by decision.

Blood gives each object exactly one extra record: one XSECTOR per sector, one
XWALL per wall, one XSPRITE per sprite. An XSECTOR holds ONE rx, ONE tx, ONE
state machine, ONE shade wave, one wind, one panning, one bob, one z pair and
one type. So compositions collide -- the door that wants to dim the room it
opens into is asking that room for a shade wave it may already have spent, and
the room can only say yes once.

The owner's rule for this is that the answer is never refusal. "The door is
impossible because the neighbour cannot take the light change" is not an
outcome; a DECISION is, and it gets reported. Four moves, and the curriculum
demonstrates the first three natively:

* **split** a sector to mint a fresh carrier. The lightpools pattern
  blood-city already uses, and what the manual tells you to do when a shade
  wave and a mechanism want the same sector.
* **relay** through a `kGenTrigger` sprite (type 700), which receives on one
  channel and transmits on another with its own busy and wait. It is how the
  tutorials get a second transmitter out of a sector that has spent its one
  tx -- MACHINERY-LIFT sprite 127 does exactly this.
* **reroute** onto a free channel when the collision is only that two things
  chose the same number.
* **degrade** the secondary effect, under a fixed hierarchy: mechanism
  function outranks mediation, mediation outranks presentation. The primary
  NEVER blocks on the secondary -- a door that cannot dim its room is still a
  door.

Every decision is a reported finding, per the authoring-loop law: the build
says what it did and why, and nothing is silently dropped.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Iterable

#: What outranks what when something has to give.
FUNCTION, MEDIATION, PRESENTATION = "function", "mediation", "presentation"
RANK = {FUNCTION: 0, MEDIATION: 1, PRESENTATION: 2}

#: The single-slot resources of an XSECTOR, and the fields that spend each.
SECTOR_SLOTS = {
    "rx": ("rx_id",),
    "tx": ("tx_id", "command"),
    "state": ("state", "busy"),
    "type": ("type",),
    "shade wave": ("amplitude", "wave", "shade_floor", "shade_ceiling",
                   "shade_walls", "phase", "freq"),
    "wind": ("wind_vel", "wind_ang", "wind_always"),
    "panning": ("pan_vel", "pan_angle", "pan_always", "pan_floor",
                "pan_ceiling"),
    "bob": ("bob_speed", "bob_z_range", "bob_always", "bob_floor",
            "bob_ceiling"),
    "z pair": ("off_floor_z", "on_floor_z", "off_ceiling_z", "on_ceiling_z"),
    "key": ("key", "locked"),
}


class ArbitrationError(ValueError):
    """A claim the arbiter cannot even read."""


@dataclass(frozen=True)
class Claim:
    """One effect wanting one slot on one object."""

    owner: str
    target: str
    slot: str
    intent: str = FUNCTION
    detail: str = ""

    def __post_init__(self) -> None:
        if self.intent not in RANK:
            raise ArbitrationError(
                f"{self.intent!r} is not one of {tuple(RANK)}")


@dataclass
class Decision:
    """What the arbiter did about one collision, and why."""

    target: str
    slot: str
    kept: str
    move: str
    displaced: list[str] = field(default_factory=list)
    why: str = ""

    def line(self) -> str:
        who = ", ".join(self.displaced)
        return (f"{self.target} {self.slot}: kept {self.kept}, "
                f"{self.move} for {who} -- {self.why}")

    def as_json(self) -> dict[str, Any]:
        return {"target": self.target, "slot": self.slot, "kept": self.kept,
                "move": self.move, "displaced": self.displaced,
                "why": self.why}


def slots_of(fields: dict[str, Any]) -> set[str]:
    """Which single-slot resources a set of XSECTOR fields spends."""
    out = set()
    for slot, keys in SECTOR_SLOTS.items():
        if any(fields.get(key) not in (None, 0, False) for key in keys):
            out.add(slot)
    return out


def collisions(claims: Iterable[Claim]) -> dict[tuple[str, str], list[Claim]]:
    """Group claims by the slot they contend for, keeping only contested ones."""
    grouped: dict[tuple[str, str], list[Claim]] = {}
    for claim in claims:
        grouped.setdefault((claim.target, claim.slot), []).append(claim)
    return {key: group for key, group in sorted(grouped.items())
            if len(group) > 1}


#: Which move fits which slot. A channel collision reroutes; a second
#: transmitter relays; anything carried by the sector's own record needs a new
#: carrier, which means splitting.
MOVES = {
    "rx": "reroute", "tx": "relay",
    "shade wave": "split", "wind": "split", "panning": "split",
    "bob": "split", "state": "split", "type": "split", "z pair": "split",
    "key": "reroute",
}


def arbitrate(claims: Iterable[Claim]) -> tuple[list[Decision], list[Claim]]:
    """Decide every collision. Returns the decisions and the surviving claims.

    The winner is the highest-ranked intent, ties going to the first claim
    made, because the thing built first is the thing the rest was composed
    around. Losers are not dropped: each gets a MOVE that keeps it, and only
    a presentation claim with nowhere to go is degraded -- which is the one
    case where losing is acceptable, since the primary must never block on
    the secondary.
    """
    claims = list(claims)
    decisions: list[Decision] = []
    contested = collisions(claims)
    survivors = [c for c in claims
                 if (c.target, c.slot) not in contested]
    for (target, slot), group in contested.items():
        ranked = sorted(range(len(group)),
                        key=lambda i: (RANK[group[i].intent], i))
        winner = group[ranked[0]]
        losers = [group[i] for i in ranked[1:]]
        move = MOVES.get(slot, "split")
        if all(loser.intent == PRESENTATION for loser in losers) \
                and move == "split" and slot in ("state", "type", "z pair"):
            #: Nothing can mint a second state machine for a sector that is
            #: already a mechanism, so presentation gives way here and says so.
            move = "degrade"
        decisions.append(Decision(
            target=target, slot=slot, kept=winner.owner, move=move,
            displaced=[loser.owner for loser in losers],
            why=_why(move, slot, winner, losers)))
        survivors.append(winner)
        if move != "degrade":
            survivors.extend(losers)
    return decisions, survivors


def _why(move: str, slot: str, winner: Claim, losers: list[Claim]) -> str:
    if move == "relay":
        return (f"a sector has one tx; {losers[0].owner} goes through a "
                f"kGenTrigger relay, as MACHINERY-LIFT sprite 127 does")
    if move == "reroute":
        return (f"the collision is only the channel number; "
                f"{losers[0].owner} moves to a free one")
    if move == "split":
        return (f"a sector has one {slot}; {losers[0].owner} gets a carrier "
                f"of its own, which is the lightpools pattern")
    return (f"a sector has one {slot} and it cannot be minted; "
            f"{losers[0].owner} is {winner.intent}-ranked below "
            f"{winner.owner} and gives way")


def report(decisions: list[Decision]) -> dict[str, Any]:
    """The build output's arbitration section."""
    return {
        "$schema": "llmapper.arbitration", "schema_version": 1,
        "decisions": [decision.as_json() for decision in decisions],
        "lines": [decision.line() for decision in decisions],
        "degraded": [d.displaced for d in decisions if d.move == "degrade"],
    }


#: How many spent slots make a sector worth naming. Four: MACHINERY-LIFT's
#: locked lifts carry type, rx, key and a z pair, and that is the ceiling the
#: tutorials actually reach.
PRESSURE = 4


def audit_map(disk: Any) -> list[str]:
    """Sectors in a finished map carrying more than they can.

    A read-back check rather than a build-time one: it cannot see intent, so
    it reports PRESSURE -- how close a sector is to spending everything it
    has -- and names the sectors where one more effect would need a decision.
    """
    from .curriculum import _extra

    out = []
    for index, sector in enumerate(disk.sectors):
        extra = dict(_extra(sector))
        if int(sector.fields["type"]):
            extra["type"] = int(sector.fields["type"])
        spent = slots_of(extra)
        #: Four is where the curriculum's own sectors top out -- a locked
        #: lift is type, rx, key and z pair and has nothing left. One more
        #: effect on a sector like this needs a decision, not a field.
        if len(spent) >= PRESSURE:
            out.append(f"sector {index} has spent {len(spent)} of its slots "
                       f"({', '.join(sorted(spent))})")
    return out
