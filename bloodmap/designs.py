from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .analysis import channel_graph
from .construction import LevelBuilder, portal_profiles
from .model import LevelIR


@dataclass
class DesignedLevel:
    level: LevelIR
    report: dict[str, Any]


def build_first_puzzle_room() -> DesignedLevel:
    """Build a scratch-authored two-switch, two-door introductory puzzle suite."""
    builder = LevelBuilder()

    main = builder.add_sector(
        [
            (0, 0), (6144, 0), (10240, 0), (16384, 0),
            (16384, 4608), (16384, 7680), (16384, 12288), (0, 12288),
        ],
        wall_picnum=180, floor_picnum=292, ceiling_picnum=385,
        wall_shade=12, floor_shade=20,
    )
    first_door = builder.add_sector(
        [(16384, 4608), (18432, 4608), (18432, 7680), (16384, 7680)],
        ceiling_z=8192, floor_z=8192, type=600,
        wall_picnum=104, floor_picnum=293, ceiling_picnum=293,
        wall_shade=-8, floor_shade=-8, ceiling_shade=-8,
    )
    switch_alcove = builder.add_sector(
        [
            (18432, 2048), (26624, 2048), (26624, 10240),
            (18432, 10240), (18432, 7680), (18432, 4608),
        ],
        wall_picnum=181, floor_picnum=294, ceiling_picnum=385,
        wall_shade=20, floor_shade=28,
    )
    reward_door = builder.add_sector(
        [(6144, -2048), (10240, -2048), (10240, 0), (6144, 0)],
        ceiling_z=8192, floor_z=8192, type=600,
        wall_picnum=104, floor_picnum=293, ceiling_picnum=293,
        wall_shade=-8, floor_shade=-8, ceiling_shade=-8,
    )
    reward_bay = builder.add_sector(
        [
            (2048, -10240), (14336, -10240), (14336, -2048),
            (10240, -2048), (6144, -2048), (2048, -2048),
        ],
        wall_picnum=184, floor_picnum=278, ceiling_picnum=385,
        wall_shade=4, floor_shade=12,
    )

    builder.connect(main.wall_ids[4], first_door.wall_ids[3])
    builder.connect(first_door.wall_ids[1], switch_alcove.wall_ids[4])
    builder.connect(main.wall_ids[1], reward_door.wall_ids[2])
    builder.connect(reward_door.wall_ids[0], reward_bay.wall_ids[3])

    for sector_id, channel in (
        (first_door.sector_id, 100),
        (reward_door.sector_id, 101),
    ):
        builder.set_behavior(
            "sector", sector_id,
            state=0, busy=0, rx_id=channel,
            busy_wave_a=0, busy_wave_b=0,
            busy_time_a=5, busy_time_b=5,
            rest_state=0, interruptable=0,
            off_ceiling_z=8192, on_ceiling_z=-24576,
            off_floor_z=8192, on_floor_z=8192,
        )

    first_switch = builder.add_sprite(
        sector=main.sector_id,
        x=16384, y=3072, z=-4096,
        type=21, picnum=1070, status=0, angle=1024,
        cstat=464, x_repeat=40, y_repeat=40, shade=-8,
    )
    builder.set_behavior(
        "sprite", first_switch,
        state=0, rest_state=0, tx_id=100, command=1,
        trigger_on=1, trigger_off=0, trigger_push=1,
        data_1=203,
    )

    second_switch = builder.add_sprite(
        sector=switch_alcove.sector_id,
        x=26624, y=6144, z=-4096,
        type=21, picnum=1070, status=0, angle=1024,
        cstat=464, x_repeat=40, y_repeat=40, shade=-8,
    )
    builder.set_behavior(
        "sprite", second_switch,
        state=0, rest_state=0, tx_id=101, command=1,
        trigger_on=1, trigger_off=0, trigger_push=1,
        data_1=203,
    )

    for x, y, angle in (
        (4096, 12288, 1536), (12288, 12288, 1536),
        (2048, 0, 512), (14336, 0, 512),
    ):
        builder.add_sprite(
            sector=main.sector_id, x=x, y=y, z=-4096,
            type=30, picnum=570, status=0, angle=angle,
            cstat=384, x_repeat=64, y_repeat=64, shade=-8,
        )

    reward = builder.add_sprite(
        sector=reward_bay.sector_id,
        x=8192, y=-6144, z=8192,
        type=41, picnum=559, status=3,
        cstat=128, x_repeat=48, y_repeat=48, shade=-8,
    )
    builder.set_behavior("sprite", reward)

    builder.set_player_start(
        sector=main.sector_id,
        # Grounded placement avoids a short settling fall after map load, which
        # otherwise makes the opening interaction nondeterministic. The 896-unit
        # offset is inside Blood's push range without intersecting the wall sprite.
        x=15488, y=3072, z=0, angle=0,
    )
    level = builder.build()
    profiles = portal_profiles(level, min_width=2048, min_opening=8192)
    if not profiles or not all(profile["walkable_when_open"] for profile in profiles):
        raise RuntimeError("first puzzle room contains a portal that is not walkable when open")

    report = {
        "$schema": "bloodmap.designed-level-report",
        "schema_version": 1,
        "name": "first-puzzle-room",
        "intent": "read switch A, enter its revealed alcove, use switch B, return and claim the reward",
        "spaces": {
            "main_chamber": main.sector_id,
            "first_door": first_door.sector_id,
            "switch_alcove": switch_alcove.sector_id,
            "reward_door": reward_door.sector_id,
            "reward_bay": reward_bay.sector_id,
        },
        "progression": [
            {"step": 1, "action": f"push sprite:{first_switch}", "sends": {"channel": 100, "command": 1}, "opens_sector": first_door.sector_id},
            {"step": 2, "action": f"cross sector:{first_door.sector_id} into the east alcove"},
            {"step": 3, "action": f"push sprite:{second_switch}", "sends": {"channel": 101, "command": 1}, "opens_sector": reward_door.sector_id},
            {"step": 4, "action": f"return through sector:{main.sector_id} and enter reward sector:{reward_bay.sector_id}"},
        ],
        "objects": {
            "first_switch": first_switch,
            "second_switch": second_switch,
            "reward": reward,
        },
        "player_start": dict(level.player_start),
        "portal_profiles": profiles,
        "channel_graph": channel_graph(level.to_disk_map()),
        "counts": {
            "sectors": len(level.sectors),
            "walls": len(level.walls),
            "sprites": len(level.sprites),
        },
    }
    return DesignedLevel(level, report)
