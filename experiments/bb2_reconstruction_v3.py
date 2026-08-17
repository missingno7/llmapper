"""Replayable source-blind BB2 reconstruction v3.

Geometry is invented from the understanding documents and the v2 semantic
delta. It does not copy BB2 vertices. Two clean compiles must be byte-identical.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from bloodmap.format import encode_map, write_map
from bloodmap.geometry_audit import (
    audit_geometry,
    audit_svg,
    authored_geometry_report,
    validate_authored_level,
)
from bloodmap.item_display import (
    UNDERWATER_FLOOR_PICNUM,
    WATER_CEILING_PICNUM,
    WATER_FLOOR_PICNUM,
    sprite_appearance,
)
from bloodmap.planar_layout import CompiledLayout, PlanarLayout

U = 384
PH = 0x1600  # Blood standing height
OUT_FLOOR = 8192
OUT_CEIL = OUT_FLOOR - 20 * PH
IN_CEIL = OUT_FLOOR - 6 * PH
UNDER_FLOOR = OUT_FLOOR + 8 * PH


def P(x: float, y: float) -> tuple[int, int]:
    return (int(round(x * U)), int(round(y * U)))


def _interior(points: list[tuple[int, int]]) -> tuple[int, int]:
    return (
        sum(x for x, _ in points) // len(points),
        sum(y for _, y in points) // len(points),
    )


def _place(
    layout: PlanarLayout,
    placement_id: str,
    region: str,
    x: int,
    y: int,
    type_id: int,
    *,
    z: int,
    **overrides: Any,
) -> None:
    layout.add_sprite(placement_id, region, x=x, y=y, z=z, **sprite_appearance(type_id, **overrides))


def make_layout(
    *,
    south_inset: int = 4,
    east_span: int = 14,
    chamfer: int = 4,
) -> PlanarLayout:
    layout = PlanarLayout(name="BB2-semantic-reconstruction-v3", visibility=800)

    courtyard = [
        P(0, chamfer), P(chamfer, 0), P(48 - chamfer, 0), P(48, chamfer),
        P(48, 40 - chamfer), P(48 - chamfer, 40), P(chamfer, 40), P(0, 40 - chamfer),
    ]
    layout.add_region(
        "region:main_exterior",
        courtyard,
        ceiling_z=OUT_CEIL, floor_z=OUT_FLOOR,
        ceiling_picnum=2500, floor_picnum=270, wall_picnum=110,
        floor_shade=20, wall_shade=12, ceiling_shade=-16,
        parallax_ceiling=True, role="hunting_ground",
    )

    south = [P(8, 40), P(40, 40), P(40 + south_inset, 54), P(36, 58), P(12, 58), P(8 - south_inset, 52)]
    layout.add_region(
        "region:south_yard",
        south,
        ceiling_z=OUT_CEIL, floor_z=OUT_FLOOR,
        ceiling_picnum=2500, floor_picnum=270, wall_picnum=110,
        floor_shade=20, wall_shade=12, ceiling_shade=-16,
        parallax_ceiling=True, role="hunting_ground",
    )
    layout.add_connection("connection:south_field", "region:main_exterior", "region:south_yard")

    east = [P(48, 8), P(48 + east_span, 4), P(70, 10), P(72, 22), P(64, 32), P(48, 30)]
    layout.add_region(
        "region:east_yard",
        east,
        ceiling_z=OUT_CEIL, floor_z=OUT_FLOOR,
        ceiling_picnum=2500, floor_picnum=270, wall_picnum=110,
        floor_shade=18, wall_shade=10, ceiling_shade=-16,
        parallax_ceiling=True, role="hunting_ground",
    )
    layout.add_connection("connection:east_field", "region:main_exterior", "region:east_yard")

    north = layout.insert_building_shell(
        "region:main_exterior",
        mass_id="north_building",
        outer_footprint=[P(12, 6), P(34, 6), P(34, 20), P(12, 20)],
        inner_footprint=[P(14, 8), P(30, 8), P(30, 18), P(14, 18)],
        entrances=[{
            "id": "north_mouth",
            "outer_a": P(20, 20), "outer_b": P(26, 20),
            "inner_a": P(20, 18), "inner_b": P(26, 18),
        }],
        ceiling_z=IN_CEIL, floor_z=OUT_FLOOR,
    )

    east_b = layout.insert_building_shell(
        "region:main_exterior",
        mass_id="east_building",
        outer_footprint=[P(36, 12), P(46, 12), P(46, 26), P(36, 26)],
        inner_footprint=[P(38, 14), P(42, 14), P(42, 24), P(38, 24)],
        entrances=[{
            "id": "east_mouth",
            "outer_a": P(36, 16), "outer_b": P(36, 22),
            "inner_a": P(38, 16), "inner_b": P(38, 22),
        }],
        ceiling_z=IN_CEIL, floor_z=OUT_FLOOR,
    )

    layout.add_region(
        "region:armor_door",
        [P(30, 11), P(32, 11), P(32, 15), P(30, 15)],
        ceiling_z=OUT_FLOOR, floor_z=OUT_FLOOR, type=600,
        ceiling_picnum=104, floor_picnum=104, wall_picnum=104, role="doorway",
        sector_behavior={
            "rx_id": 100, "busy_time_a": 5, "busy_time_b": 5,
            "off_ceiling_z": OUT_FLOOR, "on_ceiling_z": IN_CEIL,
            "off_floor_z": OUT_FLOOR, "on_floor_z": OUT_FLOOR,
        },
    )
    layout.add_region(
        "region:armor_vault",
        [P(32, 8), P(34, 8), P(34, 18), P(32, 18)],
        ceiling_z=IN_CEIL, floor_z=OUT_FLOOR,
        ceiling_picnum=416, floor_picnum=2448, wall_picnum=5, role="gated_pocket",
    )
    layout.add_connection("connection:north_vault_a", north["interior"], "region:armor_door", role="doorway", gated=True)
    layout.add_connection("connection:north_vault_b", "region:armor_door", "region:armor_vault", role="doorway", gated=True)
    layout.add_partition(
        "partition:armor_outer", "region:main_exterior", "region:armor_vault",
        role="solid_boundary", a1=P(34, 8), a2=P(34, 18),
    )

    layout.add_region(
        "region:cloak_door",
        [P(42, 17), P(44, 17), P(44, 21), P(42, 21)],
        ceiling_z=OUT_FLOOR, floor_z=OUT_FLOOR, type=600,
        ceiling_picnum=104, floor_picnum=104, wall_picnum=104, role="doorway",
        sector_behavior={
            "rx_id": 101, "busy_time_a": 5, "busy_time_b": 5,
            "off_ceiling_z": OUT_FLOOR, "on_ceiling_z": IN_CEIL,
            "off_floor_z": OUT_FLOOR, "on_floor_z": OUT_FLOOR,
        },
    )
    layout.add_region(
        "region:cloak_vault",
        [P(44, 14), P(46, 14), P(46, 24), P(44, 24)],
        ceiling_z=IN_CEIL, floor_z=OUT_FLOOR,
        ceiling_picnum=416, floor_picnum=2448, wall_picnum=5, role="gated_pocket",
    )
    layout.add_connection("connection:east_vault_a", east_b["interior"], "region:cloak_door", role="doorway", gated=True)
    layout.add_connection("connection:east_vault_b", "region:cloak_door", "region:cloak_vault", role="doorway", gated=True)
    layout.add_partition(
        "partition:cloak_vault_outer", "region:main_exterior", "region:cloak_vault",
        role="solid_boundary", a1=P(46, 14), a2=P(46, 24),
    )

    layout.add_region(
        "region:west_porch",
        [P(-16, 8), P(0, 8), P(0, 28), P(-16, 28)],
        ceiling_z=IN_CEIL, floor_z=OUT_FLOOR,
        ceiling_picnum=416, floor_picnum=2448, wall_picnum=5,
        floor_shade=16, wall_shade=8, role="covered_route",
    )
    layout.add_connection("connection:west_porch", "region:main_exterior", "region:west_porch")

    layout.add_region(
        "region:akimbo_door",
        [P(-14, 28), P(-8, 28), P(-8, 32), P(-14, 32)],
        ceiling_z=OUT_FLOOR, floor_z=OUT_FLOOR, type=600,
        ceiling_picnum=104, floor_picnum=104, wall_picnum=104, role="doorway",
        sector_behavior={
            "rx_id": 102, "busy_time_a": 5, "busy_time_b": 5,
            "off_ceiling_z": OUT_FLOOR, "on_ceiling_z": IN_CEIL,
            "off_floor_z": OUT_FLOOR, "on_floor_z": OUT_FLOOR,
        },
    )
    layout.add_region(
        "region:akimbo_nook",
        [P(-16, 32), P(-4, 32), P(-4, 40), P(-16, 40)],
        ceiling_z=IN_CEIL, floor_z=OUT_FLOOR,
        ceiling_picnum=416, floor_picnum=2448, wall_picnum=5, role="gated_pocket",
    )
    layout.add_connection("connection:akimbo_a", "region:west_porch", "region:akimbo_door", role="doorway", gated=True)
    layout.add_connection("connection:akimbo_b", "region:akimbo_door", "region:akimbo_nook", role="doorway", gated=True)

    pool = [P(20, 26), P(28, 26), P(30, 28), P(28, 34), P(20, 34), P(18, 30)]
    layout.carve_hole("region:main_exterior", pool)
    layout.add_region(
        "region:pool",
        pool,
        ceiling_z=OUT_CEIL, floor_z=OUT_FLOOR,
        ceiling_picnum=2500, floor_picnum=WATER_FLOOR_PICNUM, wall_picnum=110,
        floor_shade=8, wall_shade=12, ceiling_shade=-16,
        parallax_ceiling=True, role="water_surface",
    )
    layout.add_connection("connection:pool_rim", "region:main_exterior", "region:pool")
    layout.add_region(
        "region:underwater",
        pool,
        ceiling_z=OUT_FLOOR, floor_z=UNDER_FLOOR,
        ceiling_picnum=WATER_CEILING_PICNUM, floor_picnum=UNDERWATER_FLOOR_PICNUM, wall_picnum=110,
        special="water", layer="stack:pool", declared_zero_exit=True, role="underwater",
        sector_behavior={"underwater": 1},
    )
    layout.declare_special("region:pool", "region:underwater", "water")

    # Outdoor lift beside the south mouth.
    layout.add_region(
        "region:south_lift",
        [P(20, 58), P(28, 58), P(28, 62), P(20, 62)],
        ceiling_z=OUT_CEIL, floor_z=OUT_FLOOR, type=602,
        ceiling_picnum=2500, floor_picnum=270, wall_picnum=110,
        parallax_ceiling=True, role="lift",
        sector_behavior={
            "rx_id": 103, "busy_time_a": 8, "busy_time_b": 8,
            "off_ceiling_z": OUT_CEIL, "on_ceiling_z": OUT_CEIL,
            "off_floor_z": OUT_FLOOR, "on_floor_z": OUT_FLOOR + 6 * PH,
        },
    )
    layout.add_connection("connection:south_lift", "region:south_yard", "region:south_lift")

    layout.set_player_start("region:main_exterior", x=P(8, 12)[0], y=P(8, 12)[1], z=OUT_FLOOR - 4096, angle=512)

    # Starts: all on the open circulation graph, not behind closed doors.
    starts = [
        ("sp", "region:main_exterior", P(8, 12)[0], P(8, 12)[1], 1, 0),
        ("dm0", "region:south_yard", *_interior(south), 2, 1536),
        ("dm1", "region:east_yard", *_interior(east), 2, 1024),
        ("dm2", "region:west_porch", P(-8, 18)[0], P(-8, 18)[1], 2, 0),
        ("dm3", "region:main_exterior", P(8, 12)[0], P(8, 12)[1], 2, 512),
        ("dm4", "region:main_exterior", P(40, 32)[0], P(40, 32)[1], 2, 1536),
        ("dm5", north["interior"], P(22, 13)[0], P(22, 13)[1], 2, 0),
        ("dm6", east_b["interior"], P(41, 19)[0], P(41, 19)[1], 2, 1024),
        ("dm7", "region:south_yard", P(16, 50)[0], P(16, 50)[1], 2, 512),
    ]
    for name, region, x, y, type_id, angle in starts:
        _place(
            layout, f"start:{name}", region, x, y, type_id,
            z=OUT_FLOOR - 1024, angle=angle,
        )

    px, py = _interior(pool)
    _place(layout, "water:up", "region:pool", px, py, 9, z=OUT_FLOOR, behavior={"data_1": 7})
    _place(layout, "water:down", "region:underwater", px, py, 10, z=OUT_FLOOR + 2048, behavior={"data_1": 7})
    _place(layout, "tesla", "region:underwater", px + U, py, 45, z=UNDER_FLOOR - 1024)

    _place(layout, "flag_a", "region:south_yard", *P(24, 50), 145, z=OUT_FLOOR - 1024)
    _place(layout, "flag_b", north["interior"], *P(18, 12), 146, z=OUT_FLOOR - 1024)
    _place(layout, "armor", "region:armor_vault", *P(33, 13), 144, z=OUT_FLOOR - 1024)
    _place(layout, "cloak", "region:cloak_vault", *P(45, 19), 113, z=OUT_FLOOR - 1024)
    _place(layout, "akimbo", "region:akimbo_nook", *P(-10, 36), 117, z=OUT_FLOOR - 1024)

    layout.add_sprite("sw_armor", north["interior"], x=P(28, 13)[0], y=P(28, 13)[1], z=OUT_FLOOR - 4096, type=21, picnum=1070, cstat=464, x_repeat=40, y_repeat=40, angle=1024, behavior={"tx_id": 100, "command": 1, "trigger_on": 1, "trigger_push": 1, "data_1": 203})
    layout.add_sprite("sw_cloak", east_b["interior"], x=P(42, 22)[0], y=P(42, 22)[1], z=OUT_FLOOR - 4096, type=21, picnum=1070, cstat=464, x_repeat=40, y_repeat=40, angle=512, behavior={"tx_id": 101, "command": 1, "trigger_on": 1, "trigger_push": 1, "data_1": 203})
    layout.add_sprite("sw_akimbo", "region:west_porch", x=P(-6, 18)[0], y=P(-6, 18)[1], z=OUT_FLOOR - 4096, type=21, picnum=1070, cstat=464, x_repeat=40, y_repeat=40, angle=0, behavior={"tx_id": 102, "command": 1, "trigger_on": 1, "trigger_push": 1, "data_1": 203})

    weapons = [
        ("sawed", "region:south_yard", P(12, 48), 41),
        ("tommy", "region:east_yard", P(60, 18), 42),
        ("flare", "region:west_porch", P(-10, 16), 43),
        ("napalm", "region:main_exterior", P(8, 32), 46),
    ]
    for name, region, (x, y), type_id in weapons:
        _place(layout, f"weapon:{name}", region, x, y, type_id, z=OUT_FLOOR - 1024)
    ammo_spots = [
        ("region:main_exterior", P(16, 28), 68),
        ("region:main_exterior", P(36, 10), 72),
        ("region:south_yard", P(32, 52), 67),
        ("region:east_yard", P(66, 24), 69),
        ("region:west_porch", P(-12, 24), 76),
        (north["interior"], P(16, 14), 68),
        (east_b["interior"], P(40, 20), 73),
        ("region:south_yard", P(20, 54), 60),
    ]
    for index, (region, (x, y), type_id) in enumerate(ammo_spots):
        _place(layout, f"ammo:{index}", region, x, y, type_id, z=OUT_FLOOR - 1024)
    for index, (region, (x, y)) in enumerate((
        ("region:main_exterior", P(42, 8)),
        (north["interior"], P(26, 10)),
        ("region:west_porch", P(-8, 12)),
    )):
        _place(layout, f"health:{index}", region, x, y, 107, z=OUT_FLOOR - 1024)
    _place(layout, "armor_basic", "region:east_yard", *P(56, 12), 140, z=OUT_FLOOR - 1024)
    return layout


def build_bb2_reconstruction_v3() -> CompiledLayout:
    return make_layout().compile()


def write_bb2_reconstruction_v3(
    map_path: str | Path = "work/BB2-semantic-reconstruction-v3.MAP",
    report_path: str | Path = "reports/BB2-v3-build-report.json",
) -> CompiledLayout:
    compiled = build_bb2_reconstruction_v3()
    second = build_bb2_reconstruction_v3()
    first_bytes = encode_map(compiled.level.to_disk_map())
    if first_bytes != encode_map(second.level.to_disk_map()):
        raise RuntimeError("BB2 v3 compile is not byte-deterministic")
    Path(map_path).parent.mkdir(parents=True, exist_ok=True)
    write_map(compiled.level.to_disk_map(), map_path)
    diagnostics = validate_authored_level(
        compiled.level,
        intended_adjacency=[(item.region_a, item.region_b) for item in compiled.layout.connections.values()],
        gated_sectors={
            compiled.allocations[key].sector_id
            for key, region in compiled.layout.regions.items()
            if region.type == 600 or region.role in {"gated_pocket", "doorway"}
        },
        declared_zero_exit={
            compiled.allocations[key].sector_id
            for key, region in compiled.layout.regions.items()
            if region.declared_zero_exit
        },
        declared_specials=compiled.declared_specials,
        allocations={key: value.sector_id for key, value in compiled.allocations.items()},
        connection_report=compiled.connection_report,
    )
    gated = {
        compiled.allocations[key].sector_id
        for key, region in compiled.layout.regions.items()
        if region.type in {600, 602} or region.role in {"doorway", "gated_pocket"}
    }
    zero_exit = {
        compiled.allocations[key].sector_id
        for key, region in compiled.layout.regions.items()
        if region.declared_zero_exit or region.special in {"water", "stack", "helper"}
    }
    audit = audit_geometry(
        compiled.level,
        declared_specials=compiled.declared_specials,
        gated_sectors=gated,
        declared_zero_exit=zero_exit,
    )
    overlay = Path("reports/BB2-v3-geometry-audit.svg")
    overlay.write_text(audit_svg(compiled.level, audit), encoding="utf-8", newline="\n")
    report: dict[str, Any] = {
        "map": str(map_path),
        "deterministic": True,
        "bytes": len(first_bytes),
        "conservation": compiled.conservation.to_dict(),
        "connection_report": compiled.connection_report,
        "allocations": compiled.to_dict()["allocations"],
        "authored": authored_geometry_report(diagnostics),
        "audit_error_conflicts": audit["counts"]["error_conflicts"],
        "native_validation_errors": audit["native_validation_errors"],
        "traversal": audit["traversal"],
        "specials": compiled.to_dict()["declared_specials"],
        "allowed_gated_sectors": sorted(gated),
        "allowed_zero_exit_sectors": sorted(zero_exit),
        "overlay": str(overlay),
    }
    Path(report_path).parent.mkdir(parents=True, exist_ok=True)
    Path(report_path).write_text(
        __import__("json").dumps(report, indent=2, sort_keys=True) + "\n",
        encoding="utf-8", newline="\n",
    )
    return compiled


if __name__ == "__main__":
    compiled = write_bb2_reconstruction_v3()
    print(
        f"v3: {len(compiled.level.sectors)} sectors, {len(compiled.level.walls)} walls, "
        f"{len(compiled.level.sprites)} sprites, conserved={compiled.conservation.conserved}"
    )
