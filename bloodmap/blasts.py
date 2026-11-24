"""Chains of blasts: the exploders of one wire in the order their waits set them off, and what each of them can hurt.

A chain in Blood is one channel with many `kTrapExploder` (459) on it, each
holding its own `wait_time` in tenths of a second (`SetSpriteState` posts the
OFF that blows it after the wait, triggers.cpp): nothing is passed from blast
to blast. Beside them on the channel stand what else the moment has: an
earthquake (19), a voice (711), one-way switches (21) that wait as long as the
chain lasts and send on.

What a blast hurts (actor.cpp, the `kStatExplosion` loop): an exploder's is
`explodeInfo[1]`, radius 150, which is 2,400 units across and 38,400 up and
down (`CheckProximity` compares x and y >> 4 and z >> 8), and only what it can
see. Inside that it takes 20 to 30 health once and then, for each of some
fifteen frames, 900 * 0x40000 / (0x40000 + distance squared) sixteenths of one
more: two blasts beside a man kill him, and out of reach it does nothing.
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from math import hypot
from typing import Any, Iterable

from .model import record_extra, record_fields

EXPLODER = 459
#: an exploder's reach over the plan, and up and down
REACH, REACH_Z = 2400, 38400
#: what else a blast chain's channel is found to carry
QUAKE, VOICE, RELAYS, GIBS = 19, 711, (20, 21), (416, 417)


@dataclass(frozen=True)
class Blast:
    sprite: int
    sector: int
    x: int
    y: int
    z: int
    wait: int                                             # tenths of a second after the wire fires


@dataclass(frozen=True)
class Chain:
    channel: int
    blasts: tuple[Blast, ...]                             # in the order they go off
    others: tuple[tuple[int, int], ...]                   # (sprite, type) of what else listens

    @property
    def lasts(self) -> float:
        """Seconds from the first blast to the last."""
        return (self.blasts[-1].wait - self.blasts[0].wait) / 10

    @property
    def steps(self) -> tuple[int, ...]:
        """The different moments, in tenths."""
        return tuple(sorted({b.wait for b in self.blasts}))

    @property
    def rise(self) -> int:
        """How far it goes up (z) from its first blast to its last."""
        return self.blasts[0].z - self.blasts[-1].z

    @property
    def run(self) -> float:
        """How far over the plan its path goes, moment to moment."""
        middles = []
        for wait in self.steps:
            here = [b for b in self.blasts if b.wait == wait]
            middles.append((sum(b.x for b in here) / len(here), sum(b.y for b in here) / len(here)))
        return sum(hypot(b[0] - a[0], b[1] - a[1]) for a, b in zip(middles, middles[1:]))


def chains(disk: Any, *, at_least: int = 2) -> list[Chain]:
    """Every channel that sets off exploders at more than one moment, the longest first."""
    blasts, others = defaultdict(list), defaultdict(list)
    for index, sprite in enumerate(disk.sprites):
        extra = record_extra(sprite)
        if not extra or not extra["rx_id"]:
            continue
        f = record_fields(sprite)
        if f["type"] == EXPLODER:
            # the engine makes a wait of 0 one (actInit)
            blasts[extra["rx_id"]].append(Blast(index, int(f["sector"]), int(f["x"]), int(f["y"]), int(f["z"]),
                                                max(1, int(extra["wait_time"]))))
        else:
            others[extra["rx_id"]].append((index, int(f["type"])))
    out = [Chain(channel, tuple(sorted(rows, key=lambda b: (b.wait, b.sprite))), tuple(others[channel]))
           for channel, rows in blasts.items()]
    return sorted((c for c in out if len(c.steps) >= at_least), key=lambda c: (-len(c.steps), c.channel))


def hurts(blast_at: tuple[int, int, int], body_at: tuple[int, int, int]) -> bool:
    """Whether a blast there reaches a body whose sprite is there, if it can see it (the engine's own test)."""
    dx, dy = abs(blast_at[0] - body_at[0]) >> 4, abs(blast_at[1] - body_at[1]) >> 4
    if abs(blast_at[2] - body_at[2]) >> 8 >= REACH_Z >> 8 or max(dx, dy) >= REACH >> 4:
        return False
    # approxDist (common_game.h:868)
    return max(dx, dy) + (3 * min(dx, dy) >> 3) < REACH >> 4


def harmless(blasts: Iterable[tuple[int, int, int]], bodies: Iterable[tuple[int, int, int]]) -> bool:
    """Whether none of the blasts reaches any of the places a body may be."""
    bodies = list(bodies)
    return not any(hurts(b, body) for b in blasts for body in bodies)
