"""Small source-blind BB6-inspired reconstruction.

Geometry is invented from the pattern-aware BB6 understanding prose. It does
not copy BB6 vertices. Twin outdoor yards, a lower central depression, two
covered masses, mixed spawn neighborhoods, and gated flag rooms.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from bloodmap.format import encode_map, write_map
from bloodmap.geometry_audit import (
    audit_geometry,
    authored_geometry_report,
    validate_authored_level,
)
from bloodmap.item_display import sprite_appearance
from bloodmap.planar_layout import CompiledLayout, PlanarLayout

U = 384
PH = 0x1600
OUT_FLOOR = 8192
OUT_CEIL = OUT_FLOOR - 20 * PH
IN_CEIL = OUT_FLOOR - 6 * PH
MUD_FLOOR = OUT_FLOOR + int(1.5 * PH)


def P(x: float, y: float) -> tuple[int, int]:
    return (int(round(x * U)), int(round(y * U)))


def _place(layout: PlanarLayout, placement_id: str, region: str, x: int, y: int, type_id: int, *, z: int, **overrides: Any) -> None:
    layout.add_sprite(placement_id, region, x=x, y=y, z=z, **sprite_appearance(type_id, **overrides))


def make_layout() -> PlanarLayout:
    layout = PlanarLayout(name="BB6-pattern-reconstruction-v1", visibility=800)
    outdoor = dict(
        ceiling_z=OUT_CEIL, floor_z=OUT_FLOOR,
        ceiling_picnum=2500, floor_picnum=270, wall_picnum=110,
        floor_shade=16, wall_shade=12, ceiling_shade=-16,
        parallax_ceiling=True,
    )
    indoor = dict(
        ceiling_z=IN_CEIL, floor_z=OUT_FLOOR,
        ceiling_picnum=416, floor_picnum=2448, wall_picnum=5,
        floor_shade=16, wall_shade=8, ceiling_shade=8,
    )

    north_yard = [
        P(0, 4), P(8, 0), P(40, 0), P(48, 4), P(48, 20), P(40, 24), P(8, 24), P(0, 20),
    ]
    layout.add_region("region:north_yard", north_yard, role="hunting_ground", **outdoor)

    mud = [P(8, 24), P(40, 24), P(40, 40), P(8, 40)]
    layout.add_region(
        "region:mud", mud, role="depression",
        ceiling_z=OUT_CEIL, floor_z=MUD_FLOOR,
        ceiling_picnum=2500, floor_picnum=270, wall_picnum=110,
        floor_shade=28, wall_shade=24, ceiling_shade=-8,
        parallax_ceiling=True,
    )
    layout.add_connection("connection:north_mud", "region:north_yard", "region:mud")

    south_yard = [
        P(8, 40), P(40, 40), P(48, 44), P(48, 60), P(40, 64), P(8, 64), P(0, 60), P(0, 44),
    ]
    layout.add_region("region:south_yard", south_yard, role="hunting_ground", **outdoor)
    layout.add_connection("connection:south_mud", "region:mud", "region:south_yard")

    north = layout.insert_building_shell(
        "region:north_yard",
        mass_id="north_fort",
        outer_footprint=[P(14, 6), P(34, 6), P(34, 18), P(14, 18)],
        inner_footprint=[P(16, 8), P(30, 8), P(30, 16), P(16, 16)],
        entrances=[{
            "id": "north_mouth",
            "outer_a": P(20, 18), "outer_b": P(28, 18),
            "inner_a": P(20, 16), "inner_b": P(28, 16),
        }],
        **indoor,
    )
    south = layout.insert_building_shell(
        "region:south_yard",
        mass_id="south_fort",
        outer_footprint=[P(14, 46), P(34, 46), P(34, 58), P(14, 58)],
        inner_footprint=[P(16, 48), P(30, 48), P(30, 56), P(16, 56)],
        entrances=[{
            "id": "south_mouth",
            "outer_a": P(20, 46), "outer_b": P(28, 46),
            "inner_a": P(20, 48), "inner_b": P(28, 48),
        }],
        **indoor,
    )

    layout.add_region(
        "region:north_flag_door",
        [P(30, 10), P(32, 10), P(32, 14), P(30, 14)],
        ceiling_z=OUT_FLOOR, floor_z=OUT_FLOOR, type=600,
        ceiling_picnum=104, floor_picnum=104, wall_picnum=104, role="doorway",
        sector_behavior={
            "rx_id": 200, "busy_time_a": 5, "busy_time_b": 5,
            "off_ceiling_z": OUT_FLOOR, "on_ceiling_z": IN_CEIL,
            "off_floor_z": OUT_FLOOR, "on_floor_z": OUT_FLOOR,
        },
    )
    layout.add_region(
        "region:north_flag",
        [P(32, 8), P(34, 8), P(34, 16), P(32, 16)],
        **indoor, role="gated_pocket",
    )
    layout.add_connection("connection:north_flag_a", north["interior"], "region:north_flag_door", role="doorway", gated=True)
    layout.add_connection("connection:north_flag_b", "region:north_flag_door", "region:north_flag", role="doorway", gated=True)
    layout.add_partition(
        "partition:north_flag_yard", "region:north_yard", "region:north_flag",
        role="solid_boundary", a1=P(34, 8), a2=P(34, 16),
    )

    layout.add_region(
        "region:south_flag_door",
        [P(30, 50), P(32, 50), P(32, 54), P(30, 54)],
        ceiling_z=OUT_FLOOR, floor_z=OUT_FLOOR, type=600,
        ceiling_picnum=104, floor_picnum=104, wall_picnum=104, role="doorway",
        sector_behavior={
            "rx_id": 201, "busy_time_a": 5, "busy_time_b": 5,
            "off_ceiling_z": OUT_FLOOR, "on_ceiling_z": IN_CEIL,
            "off_floor_z": OUT_FLOOR, "on_floor_z": OUT_FLOOR,
        },
    )
    layout.add_region(
        "region:south_flag",
        [P(32, 48), P(34, 48), P(34, 56), P(32, 56)],
        **indoor, role="gated_pocket",
    )
    layout.add_connection("connection:south_flag_a", south["interior"], "region:south_flag_door", role="doorway", gated=True)
    layout.add_connection("connection:south_flag_b", "region:south_flag_door", "region:south_flag", role="doorway", gated=True)
    layout.add_partition(
        "partition:south_flag_yard", "region:south_yard", "region:south_flag",
        role="solid_boundary", a1=P(34, 48), a2=P(34, 56),
    )

    layout.add_region(
        "region:north_porch",
        [P(20, -4), P(28, -4), P(28, 0), P(20, 0)],
        **{**outdoor, "floor_shade": 24, "wall_shade": 26},
        role="sky_porch",
    )
    layout.add_connection("connection:north_porch", "region:north_yard", "region:north_porch")
    layout.add_region(
        "region:south_porch",
        [P(20, 64), P(28, 64), P(28, 68), P(20, 68)],
        **{**outdoor, "floor_shade": 24, "wall_shade": 26},
        role="sky_porch",
    )
    layout.add_connection("connection:south_porch", "region:south_yard", "region:south_porch")

    layout.set_player_start("region:north_yard", x=P(8, 12)[0], y=P(8, 12)[1], z=OUT_FLOOR - 4096, angle=512)

    starts = [
        ("n0", "region:north_yard", P(8, 10), 0),
        ("n1", "region:north_yard", P(40, 10), 512),
        ("s0", "region:south_yard", P(8, 54), 1024),
        ("s1", "region:south_yard", P(40, 54), 1536),
        ("m0", "region:mud", P(16, 32), 0),
        ("m1", "region:mud", P(32, 32), 1024),
        ("p0", "region:north_porch", P(24, -2), 512),
        ("p1", "region:south_porch", P(24, 66), 1536),
    ]
    for name, region, pt, angle in starts:
        z = MUD_FLOOR - 1024 if region == "region:mud" else OUT_FLOOR - 1024
        _place(layout, f"start:{name}", region, pt[0], pt[1], 2, z=z, angle=angle)

    _place(layout, "flag_a", "region:north_flag", *P(33, 12), 145, z=OUT_FLOOR - 1024)
    _place(layout, "flag_b", "region:south_flag", *P(33, 52), 146, z=OUT_FLOOR - 1024)
    _place(layout, "cloak", "region:north_flag", *P(33, 14), 113, z=OUT_FLOOR - 1024)
    _place(layout, "tommy_n", north["interior"], *P(24, 12), 42, z=OUT_FLOOR - 1024)
    _place(layout, "tommy_s", south["interior"], *P(24, 52), 42, z=OUT_FLOOR - 1024)
    _place(layout, "tesla_n", north["interior"], *P(28, 12), 45, z=OUT_FLOOR - 1024)
    _place(layout, "tesla_s", south["interior"], *P(28, 52), 45, z=OUT_FLOOR - 1024)
    _place(layout, "armor_n", north["interior"], *P(18, 12), 140, z=OUT_FLOOR - 1024)
    _place(layout, "armor_s", south["interior"], *P(18, 52), 140, z=OUT_FLOOR - 1024)
    _place(layout, "health_mud", "region:mud", *P(24, 32), 107, z=MUD_FLOOR - 1024)

    layout.add_sprite(
        "sw_north", north["interior"], x=P(22, 10)[0], y=P(22, 10)[1], z=OUT_FLOOR - 4096,
        type=21, picnum=1070, cstat=464, x_repeat=40, y_repeat=40, angle=1024,
        behavior={"tx_id": 200, "command": 1, "trigger_on": 1, "trigger_push": 1, "data_1": 203},
    )
    layout.add_sprite(
        "sw_south", south["interior"], x=P(22, 54)[0], y=P(22, 54)[1], z=OUT_FLOOR - 4096,
        type=21, picnum=1070, cstat=464, x_repeat=40, y_repeat=40, angle=1024,
        behavior={"tx_id": 201, "command": 1, "trigger_on": 1, "trigger_push": 1, "data_1": 203},
    )
    return layout


def write_bb6_reconstruction_v1(
    map_path: str | Path = "work/BB6-pattern-reconstruction-v1.MAP",
    report_path: str | Path = "reports/BB6-pattern-reconstruction-v1-build.json",
) -> CompiledLayout:
    layout = make_layout()
    compiled = layout.compile()
    first = encode_map(compiled.level.to_disk_map())
    second = encode_map(make_layout().compile().level.to_disk_map())
    if first != second:
        raise RuntimeError("BB6 reconstruction v1 is not byte-identical across compiles")
    map_path = Path(map_path)
    map_path.parent.mkdir(parents=True, exist_ok=True)
    write_map(compiled.level.to_disk_map(), map_path)
    gated = {
        compiled.allocations[key].sector_id
        for key, region in compiled.layout.regions.items()
        if region.type in {600, 602} or region.role in {"doorway", "gated_pocket"}
    }
    diagnostics = validate_authored_level(
        compiled.level,
        intended_adjacency=[(item.region_a, item.region_b) for item in compiled.layout.connections.values()],
        gated_sectors=gated,
        declared_specials=compiled.declared_specials,
        allocations={key: value.sector_id for key, value in compiled.allocations.items()},
        connection_report=compiled.connection_report,
    )
    audit = audit_geometry(
        compiled.level,
        declared_specials=compiled.declared_specials,
        gated_sectors=gated,
    )
    report = {
        "map": str(map_path),
        "deterministic": True,
        "bytes": len(first),
        "conservation": compiled.conservation.to_dict(),
        "authored": authored_geometry_report(diagnostics),
        "audit_error_conflicts": audit["counts"]["error_conflicts"],
        "native_validation_errors": audit["native_validation_errors"],
        "traversal": audit["traversal"],
        "source_hidden": ["maps/blood/BB6.MAP"],
    }
    Path(report_path).write_text(
        __import__("json").dumps(report, indent=2, sort_keys=True) + "\n",
        encoding="utf-8", newline="\n",
    )
    return compiled


if __name__ == "__main__":
    compiled = write_bb6_reconstruction_v1()
    print(
        f"bb6-v1: {len(compiled.level.sectors)} sectors, {len(compiled.level.walls)} walls, "
        f"{len(compiled.level.sprites)} sprites, conserved={compiled.conservation.conserved}"
    )
