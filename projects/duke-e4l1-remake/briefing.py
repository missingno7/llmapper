"""Declare the briefing recorder's Use action, delayed explosions and one-shot collapse."""

from types import SimpleNamespace

from bloodmap.model import record_fields, record_extra
from bloodmap import wiring
from bloodmap.sector_geom import wall_owners


def declare(disk, *, wall_id=2318, moving=(390, 403, 405), exploders=(327, 328, 329),
            added=None, arm_wait=27, collapse_wait=30, use_channel=None):
    """Retain existing receiver channels; allocate the missing Use wire around them."""
    added = added or {}
    placements = [SimpleNamespace(placement_id=f"existing-{i}", behavior=dict(record_extra(s) or {}))
                  for i, s in enumerate(disk.sprites)]
    for name in ("briefing-arm-delay", "briefing-collapse-delay"):
        extra = dict(record_extra(disk.sprites[added[name]]) or {}) if name in added else {}
        placements.append(SimpleNamespace(placement_id=name, behavior=extra))
    layout = SimpleNamespace(
        regions={str(i): SimpleNamespace(sector_behavior=dict(record_extra(s) or {}))
                 for i, s in enumerate(disk.sectors)},
        placements=placements,
        wired_walls={i: dict(record_extra(w) or {}) for i, w in enumerate(disk.walls)},
    )
    owner = wall_owners(disk)[wall_id]
    wall = record_fields(disk.walls[wall_id])
    end = record_fields(disk.walls[wall["point2"]])
    a, b = (wall["x"], wall["y"]), (end["x"], end["y"])

    def write_wall(region_id, first, last, **fields):
        if str(region_id) != str(owner) or (first, last) != (a, b):
            raise ValueError("Briefing control wall identity changed")
        layout.wired_walls[wall_id].update(fields)

    layout.wire_wall = write_wall

    def shared_channel(objects):
        channels = {int((record_extra(obj) or {}).get("rx_id", 0)) for obj in objects}
        if len(channels) != 1:
            raise ValueError("Briefing receivers disagree; inspect the live map before rewiring")
        return next(iter(channels)) or None

    circuit = wiring.Circuit(layout)
    if use_channel is None:
        use_channel = int((record_extra(disk.walls[wall_id]) or {}).get("tx_id", 0)) or None
    use = circuit.wire("intake:briefing-use",
                       "Using the recording device once starts its two self-destruction delay relays.",
                       channel=use_channel)
    use.when(wiring.face(str(owner), a, b), "push", command=1, once=True,
             state=0, rest_state=0, trigger_off=0)
    use.then(wiring.placement("briefing-arm-delay"))
    use.then(wiring.placement("briefing-collapse-delay"))
    arm = circuit.wire("intake:briefing-explosions",
                       "After the MasterSwitch delay, arm the three retained exploders with their original converted fuses.",
                       channel=shared_channel(disk.sprites[i] for i in exploders))
    arm.when(wiring.placement("briefing-arm-delay"), wiring.RELAY, command=1,
             on=False, off=True, state=0, rest_state=0, wait_time=arm_wait)
    for i in exploders:
        arm.then(wiring.placement(f"existing-{i}"))
    collapse = circuit.wire("intake:briefing-collapse",
                            "At the first detonation, lower the existing recorder and desk fragments to their authored endpoints.",
                            channel=shared_channel(disk.sectors[i] for i in moving))
    collapse.when(wiring.placement("briefing-collapse-delay"), wiring.RELAY, command=1,
                  on=False, off=True, state=0, rest_state=0, wait_time=collapse_wait)
    for i in moving:
        collapse.then(wiring.region(str(i)))
    circuit.apply()
    return circuit, layout


def compiled(disk, added):
    """Bind declared names to native records for Circuit.read_back."""
    return SimpleNamespace(
        allocations={str(i): SimpleNamespace(sector_id=i) for i in range(len(disk.sectors))},
        placement_sprites={**{f"existing-{i}": i for i in range(len(disk.sprites))}, **added},
    )
