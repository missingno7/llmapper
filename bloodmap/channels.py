"""Two kinds of channel, and no more.

A lamp under a shadow gives less light; a thing cannot open and close at once.
Those are the only two behaviours a compiler needs, so there are exactly two
kinds of channel and no priority scheme between them:

* **ADDITIVE** -- every writer contributes a delta and the deltas sum. Light
  is the only one. The sun is a directional source occluded by masses, a lamp
  is a point source, a flicker wave and a Link-driven wave are amplitudes, a
  pool is a local gain; all of them are deltas into one shade, and summing
  them is both the physically right answer and the one that needs no
  arbitration at all.
* **EXCLUSIVE** -- one owner. Floor z, a sector's type and mechanism state, a
  surface's frame, a holder role. A second writer raises **by name**, because
  "opens and closes at once" is one channel with two writers and there is
  nothing to resolve.

That is the whole table. No priorities, no solver.

Why shade had to be additive
============================

Four things already wrote `floor_shade` -- the sun field, `flicker_lit_
sectors`, LightBomb's own pass, and any Link-driven wave a mechanism declares
-- and nothing said who owned it. That is exactly the collision P13 found
between `glass.glaze` and `texture_frame.frame_map`, where two passes wrote
the same fields and **pass order decided per record**: fifteen panes kept one
number and nine got the other, and nobody chose. It was invisible until
somebody diffed.

Making shade exclusive and letting the sun win would have dropped every
Link-driven light in the city, and P8 counted 146 of those in the campaign.
So shade is additive and **LightBomb is its single summing owner**: nothing
writes `floor_shade` directly any more, everything contributes a delta.

What yields, and what does not
==============================

`bloodmap.arbiter` already ranks claims FUNCTION / MEDIATION / PRESENTATION
and settled the curtain's rx/tx collision with it. Generalised to channels:
on an EXCLUSIVE conflict a PRESENTATION claim yields and is listed with its
reason; FUNCTION against FUNCTION is an error. A dropped PRESENTATION facet is
**expected absence** for the read-back -- it compares against the sentence as
arbitrated -- and never a gate failure, and the review sheet lists every one
so an owner can promote it.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Iterable, Sequence

from .arbiter import FUNCTION, PRESENTATION, RANK, Claim

ADDITIVE = "additive"
EXCLUSIVE = "exclusive"

#: The whole table. A channel not named here is not a channel, and asking to
#: write one raises rather than defaulting to a kind.
CHANNELS: dict[str, str] = {
    "shade": ADDITIVE,
    "floor_z": EXCLUSIVE,
    "ceiling_z": EXCLUSIVE,
    "sector_type": EXCLUSIVE,
    "mechanism_state": EXCLUSIVE,
    "frame": EXCLUSIVE,
    "holder_role": EXCLUSIVE,
}


class ChannelError(ValueError):
    """A channel written twice, or a channel nobody declared."""


@dataclass(frozen=True)
class Write:
    """One writer's contribution to one channel on one region."""

    region: str
    channel: str
    owner: str
    #: A number for an additive channel; anything for an exclusive one.
    value: Any = 0
    intent: str = FUNCTION
    detail: str = ""

    def __post_init__(self) -> None:
        if self.channel not in CHANNELS:
            raise ChannelError(
                f"{self.channel!r} is not a channel. The table has exactly "
                f"two kinds and {sorted(CHANNELS)} in them; a channel nobody "
                f"declared is a question for a person, not a default")
        if self.intent not in RANK:
            raise ChannelError(f"{self.intent!r} is not a claim kind")


@dataclass
class RegionLedger:
    """Who wrote what to which region channel, and what came of it.

    The region-scoped twin of P13's `RecordOwner`, which does this for wall
    records. Additive channels accumulate; exclusive channels admit one owner
    and a second raises unless it yields.
    """

    writes: list[Write] = field(default_factory=list)
    dropped: list[dict[str, Any]] = field(default_factory=list)

    def write(self, region: str, channel: str, owner: str, value: Any = 0, *,
              intent: str = FUNCTION, detail: str = "") -> None:
        entry = Write(str(region), str(channel), str(owner), value, intent,
                      detail)
        if CHANNELS[entry.channel] == ADDITIVE:
            self.writes.append(entry)
            return
        held = [w for w in self.writes
                if w.region == entry.region and w.channel == entry.channel]
        if not held:
            self.writes.append(entry)
            return
        incumbent = held[0]
        if incumbent.owner == entry.owner:
            self.writes.remove(incumbent)
            self.writes.append(entry)
            return
        loser = self._yields(incumbent, entry)
        if loser is None:
            raise ChannelError(
                f"{entry.region} channel {entry.channel!r}: "
                f"{incumbent.owner!r} and {entry.owner!r} both claim it and "
                f"both are {FUNCTION} claims. One channel, one owner -- "
                f"'opens and closes at once' has nothing to resolve")
        winner = entry if loser is incumbent else incumbent
        if loser is incumbent:
            self.writes.remove(incumbent)
            self.writes.append(entry)
        self.dropped.append({
            "region": entry.region, "channel": entry.channel,
            "dropped": loser.owner, "kept": winner.owner,
            "why": (f"channel {entry.channel} on {entry.region} is owned by "
                    f"{winner.owner}; {loser.owner} is a {loser.intent} claim "
                    f"and yields"),
            "detail": loser.detail})

    @staticmethod
    def _yields(a: Write, b: Write) -> Write | None:
        """Which of two claims on one exclusive channel gives way."""
        if RANK[a.intent] == RANK[b.intent]:
            return None if a.intent == FUNCTION else b
        return a if RANK[a.intent] > RANK[b.intent] else b

    def total(self, region: str, channel: str) -> Any:
        """An additive channel's sum, or an exclusive channel's owner value."""
        if CHANNELS[channel] == ADDITIVE:
            return sum(int(w.value) for w in self.writes
                       if w.region == str(region) and w.channel == channel)
        held = [w for w in self.writes
                if w.region == str(region) and w.channel == channel]
        return held[0].value if held else None

    def owner_of(self, region: str, channel: str) -> str | None:
        held = [w for w in self.writes
                if w.region == str(region) and w.channel == channel]
        return held[0].owner if held else None

    def contributors(self, region: str, channel: str) -> list[str]:
        return [w.owner for w in self.writes
                if w.region == str(region) and w.channel == channel]

    def report(self) -> dict[str, Any]:
        by_channel: dict[str, int] = {}
        for entry in self.writes:
            by_channel[entry.channel] = by_channel.get(entry.channel, 0) + 1
        return {
            "writes": len(self.writes),
            "by_channel": dict(sorted(by_channel.items())),
            "dropped": [dict(row) for row in self.dropped],
            "dropped_count": len(self.dropped),
        }

    def dropped_facets(self) -> list[str]:
        """The review sheet's list: every facet that yielded, by name."""
        return [f"{row['dropped']}: {row['why']}" for row in self.dropped]


def claims_from(ledger: RegionLedger) -> list[Claim]:
    """The ledger's exclusive writes as arbiter claims, for reporting."""
    return [Claim(owner=w.owner, target=w.region, slot=w.channel,
                  intent=w.intent, detail=w.detail)
            for w in ledger.writes if CHANNELS[w.channel] == EXCLUSIVE]


# ---------------------------------------------------------------------------
# the order the passes run in
# ---------------------------------------------------------------------------

#: Fixed, and asserted rather than documented. Each step depends on the one
#: before it in a way that is not obvious from reading either:
#:
#: 1. planes and islands exist before anything can be declared on them;
#: 2. inserts and mechanisms are declared BEFORE the light field, because
#:    from that moment they are excluded from cutting (overlay Rule 2) and a
#:    field that ran first would already have cut a curtain;
#: 3. the field runs before the joins, because it creates the pieces whose
#:    shared edges the joins then decide;
#: 4. the joins run before the frames, because a join says whether an edge is
#:    a frame boundary and the frames need that answer;
#: 5. frames last.
PASSES = ("planes", "declare", "light", "joins", "frames")


class OrderError(ValueError):
    """A pass ran out of order."""


@dataclass
class Compilation:
    """Which passes have run, so one out of order raises rather than drifts.

    The reason this is a class and not a comment: every ordering bug this
    project has had -- `glaze` against `frame_map`, the facade pass against
    the run carry, the sun against a mover -- was invisible because the passes
    simply ran and the last one won. An order that raises cannot do that.
    """

    done: list[str] = field(default_factory=list)
    ledger: RegionLedger = field(default_factory=RegionLedger)

    def enter(self, pass_name: str) -> None:
        if pass_name not in PASSES:
            raise OrderError(f"{pass_name!r} is not one of {PASSES}")
        wanted = PASSES.index(pass_name)
        for earlier in PASSES[:wanted]:
            if earlier not in self.done:
                raise OrderError(
                    f"{pass_name!r} ran before {earlier!r}. The order is "
                    f"{' -> '.join(PASSES)}, and it is fixed because "
                    f"{_why_before(earlier, pass_name)}")
        if pass_name in self.done:
            raise OrderError(f"{pass_name!r} has already run")
        self.done.append(pass_name)

    @property
    def complete(self) -> bool:
        return list(self.done) == list(PASSES)

    def require_complete(self) -> None:
        """The order assertion is also a COMPLETENESS assertion.

        Running the passes in the right order is worth nothing if one of them
        never ran. Slice 2h's frame gate found 191 misaligned walls and the
        cause was that `frame_map` had never been called: a gate downstream of
        a missing pass reports the symptom, and only the compiler can report
        the absence. So a build that stops early raises **naming the first
        pass it never entered**.
        """
        for name in PASSES:
            if name not in self.done:
                raise OrderError(
                    f"the {name!r} pass never ran. The order is "
                    f"{' -> '.join(PASSES)} and all five are compulsory -- a "
                    f"pass that simply does not run is invisible to every "
                    f"gate downstream of it, which is how 191 walls came to "
                    f"be misaligned with a clean frame report")


def _why_before(earlier: str, later: str) -> str:
    reasons = {
        ("declare", "light"):
            "a mechanism must be declared before the field runs, or the "
            "field cuts a curtain that nothing had yet marked uncuttable",
        ("light", "joins"):
            "the field creates the pieces whose shared edges the joins decide",
        ("joins", "frames"):
            "a join says whether an edge is a frame boundary, and the frames "
            "need that answer",
        ("planes", "declare"):
            "there is nothing to declare an insert on until the planes exist",
    }
    return reasons.get((earlier, later),
                       f"{later} depends on what {earlier} produces")
