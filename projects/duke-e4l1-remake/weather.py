"""Declare the quarry's Blood-native lightning and thunder without rebuilding the map."""

from types import SimpleNamespace
from bloodmap import wiring
from bloodmap.model import record_extra

EXPOSED = (104, 105, 133, 134, 135, 136, 205, 206, 415, 416, 417,
           418, 419, 420, 421, 422, 451, 452, 453)


def declare(disk, *, channel=None):
    """Use E1M5's pulsed XSECTOR shade wave and sound-generator conventions."""
    # This adapter holds fields for existing native objects; it never compiles
    # or lays out geometry. Circuit remains responsible for channel allocation.
    layout = SimpleNamespace(
        regions={str(i): SimpleNamespace(sector_behavior=dict(record_extra(s) or {}))
                 for i, s in enumerate(disk.sectors)},
        placements=[SimpleNamespace(placement_id=f"existing-{i}", behavior=dict(record_extra(s) or {}))
                    for i, s in enumerate(disk.sprites)],
        wired_walls={i: dict(record_extra(w) or {}) for i, w in enumerate(disk.walls)},
    )
    layout.placements.extend([
        SimpleNamespace(placement_id="storm-clock", behavior={}),
        SimpleNamespace(placement_id="storm-thunder", behavior={}),
    ])
    circuit = wiring.Circuit(layout)
    storm = circuit.wire(
        "quarry:storm",
        "The level-started weather clock briefly illuminates the exposed quarry and sounds distant lightning strikes.",
        channel=channel,
    )
    storm.when(wiring.placement("storm-clock"), wiring.LEVEL_START,
               command=1, on=True, state=0, busy_time=80, data_1=20)
    for sector in EXPOSED:
        storm.then(wiring.region(str(sector)), amplitude=-17, shade_frequency=5,
                   shade_phase=0, shade_wave=8, shade_always=0,
                   shade_floor=1, shade_ceiling=1, shade_walls=1,
                   wait_time_a=20, retrigger_a=1, busy_time_b=2)
    storm.then(wiring.placement("storm-thunder"), data_2=255, wait_time=15)
    circuit.apply()
    return circuit, layout
