"""Step MoveDude's vertical order (actor.cpp:4596-4631, landing :4815-4847) for a standing jump's apex and the fall-damage thresholds."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[4]))
G = 58254            # kDudeGravity, actor.h:185
FLOOR = 100 << 4     # kFallDamageFloor, actor.h:187
JUMP = -0xbaaaa      # normalJumpZ, player.cpp:134
BODY = 16960


def apex() -> int:
    """Highest rise of a standing jump: z += zvel>>8, then z += (2g)>>8 and zvel += g, every tick in the air."""
    z, v, low = 0, JUMP, 0
    while v <= 0 or z <= 0:
        z += v >> 8
        z += (G * 4 // 2) >> 8
        v += G
        low = min(low, z)
    return -low


def landing_damage(drop: int) -> int:
    """Raw damage (before the player's damage factor) of falling `drop` from rest onto a flat floor.

    Gravity is skipped on the tick whose zvel move already reaches the floor (actor.cpp:4625, bottom >= floorZ);
    otherwise it is added and the landing is tested with the new z (:4815-4827). Damage is mulscale30(zvel, zvel)
    (actFloorBounceVector returns zvel itself on a flat floor, :2694-2698) less kFallDamageFloor (:4845).
    """
    z, v = 0, 0
    while True:
        z += v >> 8
        if z >= drop:
            break
        z += (G * 2) >> 8
        v += G
        if z >= drop:
            break
    return ((v * v) >> 30) - FLOOR


if __name__ == "__main__":
    print("apex", apex())
    last = first = kill = None
    for h in range(1, 200000):
        d = landing_damage(h)
        if d <= 0:
            last = h
        elif first is None:
            first = h
        if d >= FLOOR:
            kill = h
            break
    print(f"last painless {last} ({last / BODY:.2f} bodies); first that hurts {first} ({first / BODY:.2f}); "
          f"raw damage reaches 1600 (100 hit points) at {kill} ({kill / BODY:.2f})")
