"""Synthetic test fixtures for Design Probe tests.

These fixtures create small, controlled level layouts that test specific
probe semantics:
    - simple reachable path
    - locked path
    - key unlock
    - vertical clearance failure
    - lift-enabled path
    - teleporter/water transition
    - state-dependent revisit
    - branching/escape options
"""

from __future__ import annotations

from copy import deepcopy

from bloodmap.format import (
    SECTOR_FIELDS, SPRITE_FIELDS, WALL_FIELDS, XSECTOR_SCHEMA, XSPRITE_SCHEMA,
    encode_map, parse_map,
)
from bloodmap.model import DiskMap, DiskObject, ExtraHeader, PackedExtra


def _empty_sector_fields() -> dict[str, int]:
    return {name: 0 for name, _codec in SECTOR_FIELDS}


def _empty_wall_fields() -> dict[str, int]:
    return {name: 0 for name, _codec in WALL_FIELDS}


def _empty_sprite_fields() -> dict[str, int]:
    return {name: 0 for name, _codec in SPRITE_FIELDS}


def _make_sector_disk_object(
    wall_ptr: int, wall_count: int,
    ceiling_z: int = -8192, floor_z: int = 8192,
    extra: int = -1,
) -> DiskObject:
    sector = _empty_sector_fields()
    sector.update(
        wall_ptr=wall_ptr, wall_count=wall_count,
        ceiling_z=ceiling_z, floor_z=floor_z,
        extra=extra,
    )
    return DiskObject(sector)


def _make_wall_disk_object(
    x: int, y: int, point2: int,
    next_wall: int = -1, next_sector: int = -1,
    picnum: int = 1, cstat: int = 0,
) -> DiskObject:
    wall = _empty_wall_fields()
    wall.update(
        x=x, y=y, point2=point2,
        next_wall=next_wall, next_sector=next_sector,
        picnum=picnum, over_picnum=-1, cstat=cstat, extra=-1,
    )
    return DiskObject(wall)


def _make_header(
    num_sectors: int, num_walls: int, num_sprites: int,
    start_x: int = 512, start_y: int = 512, start_z: int = 0,
    start_angle: int = 0, start_sector: int = 0,
) -> dict[str, int]:
    return {
        "start_x": start_x, "start_y": start_y, "start_z": start_z,
        "start_angle": start_angle, "start_sector": start_sector,
        "sky_bits": 0, "visibility": 800, "matt_id": 0,
        "sky_type": 0, "revision": 1,
        "num_sectors": num_sectors, "num_walls": num_walls,
        "num_sprites": num_sprites,
    }


def _make_extra_header() -> ExtraHeader:
    return ExtraHeader(
        copyright=b"\0" * 64, xsprite_size=56, xwall_size=24, xsector_size=60,
        xmp_signature=b"\0" * 3, xmp_header_version=0, xmp_map_flags=0,
        xmp_board_width=0, xmp_board_height=0, xmp_palette=0,
        xmp_sky_repeat_count=0, xmp_sky_visibility=0, reserved=b"\0" * 37,
    )


def _make_xsprite_fields() -> dict[str, int]:
    xfields = {name: 0 for name, _bits, _signed in XSPRITE_SCHEMA}
    xfields.update(reference=0, target=-1, burn_source=-1)
    return xfields


def _make_xsprite_packed_extra() -> PackedExtra:
    return PackedExtra("XSPRITE", _make_xsprite_fields(), b"\0" * 4)


def _make_xsector_fields(reference: int = 9, marker_0: int = 1, marker_1: int = -1) -> dict[str, int]:
    xfields = {name: 0 for name, _bits, _signed in XSECTOR_SCHEMA}
    xfields.update(reference=reference, marker_0=marker_0, marker_1=marker_1)
    return xfields


# ---------------------------------------------------------------------------
# Fixture: simple reachable path
# ---------------------------------------------------------------------------

def fixture_simple_reachable() -> DiskMap:
    """Two portal-linked sectors with a simple reachable path."""
    sector0 = _make_sector_disk_object(wall_ptr=0, wall_count=4, extra=1)
    sector0.extra = PackedExtra("XSECTOR", _make_xsector_fields(reference=9, marker_0=1, marker_1=-1))

    sector1 = deepcopy(sector0)
    sector1.fields.update(wall_ptr=4, extra=-1)
    sector1.extra = None

    points = [
        (0, 0), (1024, 0), (1024, 1024), (0, 1024),
        (1024, 0), (2048, 0), (2048, 1024), (1024, 1024),
    ]
    walls = []
    for index, (x, y) in enumerate(points):
        point2 = (index + 1) if index not in (3, 7) else (0 if index == 3 else 4)
        wall = _make_wall_disk_object(x=x, y=y, point2=point2)
        walls.append(wall)
    walls[1].fields.update(next_wall=7, next_sector=1)
    walls[7].fields.update(next_wall=1, next_sector=0)

    sprite0 = DiskObject(_empty_sprite_fields())
    sprite0.fields.update(x=512, y=512, z=0, sector=0, owner=1, index=0, extra=1, picnum=1)
    sprite0.extra = _make_xsprite_packed_extra()
    sprite0.extra.fields.update(reference=12, tx_id=100, rx_id=0, target=1, burn_source=-1, dude_flag_4=1)

    sprite1 = deepcopy(sprite0)
    sprite1.fields.update(x=1536, sector=1, owner=-1, index=1, extra=2)
    sprite1.extra.fields.update(reference=1, tx_id=0, rx_id=100, target=-1, burn_source=-1)

    header = _make_header(num_sectors=2, num_walls=8, num_sprites=2)
    disk = DiskMap(
        version=0x0700, header=header, extra_header=_make_extra_header(),
        sky_offsets=[0], sectors=[sector0, sector1], walls=walls,
        sprites=[sprite0, sprite1], source_crc32=0, source_size=0,
    )
    return parse_map(encode_map(disk))


# ---------------------------------------------------------------------------
# Fixture: locked path
# ---------------------------------------------------------------------------

def fixture_locked_path() -> DiskMap:
    """Two sectors connected by a blocked portal (wall cstat blocking flag)."""
    sector0 = _make_sector_disk_object(wall_ptr=0, wall_count=4, extra=1)
    sector0.extra = PackedExtra("XSECTOR", _make_xsector_fields())
    sector1 = deepcopy(sector0)
    sector1.fields.update(wall_ptr=4, extra=-1)
    sector1.extra = None

    points = [
        (0, 0), (1024, 0), (1024, 1024), (0, 1024),
        (1024, 0), (2048, 0), (2048, 1024), (1024, 1024),
    ]
    walls = []
    for index, (x, y) in enumerate(points):
        point2 = (index + 1) if index not in (3, 7) else (0 if index == 3 else 4)
        wall = _make_wall_disk_object(x=x, y=y, point2=point2)
        walls.append(wall)
    # Connect portals but mark wall 1 as blocking
    walls[1].fields.update(next_wall=7, next_sector=1, cstat=1)
    walls[7].fields.update(next_wall=1, next_sector=0, cstat=1)

    sprite0 = DiskObject(_empty_sprite_fields())
    sprite0.fields.update(x=512, y=512, z=0, sector=0, owner=1, index=0, extra=1, picnum=1)
    sprite0.extra = _make_xsprite_packed_extra()

    header = _make_header(num_sectors=2, num_walls=8, num_sprites=1)
    disk = DiskMap(
        version=0x0700, header=header, extra_header=_make_extra_header(),
        sky_offsets=[0], sectors=[sector0, sector1], walls=walls,
        sprites=[sprite0], source_crc32=0, source_size=0,
    )
    return parse_map(encode_map(disk))


# ---------------------------------------------------------------------------
# Fixture: key unlock
# ---------------------------------------------------------------------------

def fixture_key_unlock() -> DiskMap:
    """Three sectors: start -> locked gate -> objective.

    The locked gate is initially blocked (cstat=1).
    When the world state declares the portal opened, the objective becomes reachable.
    """
    sector0 = _make_sector_disk_object(wall_ptr=0, wall_count=4, extra=1)
    sector0.extra = PackedExtra("XSECTOR", _make_xsector_fields())
    sector1 = deepcopy(sector0)
    sector1.fields.update(wall_ptr=4, extra=-1)
    sector1.extra = None
    sector2 = deepcopy(sector0)
    sector2.fields.update(wall_ptr=8, extra=-1)
    sector2.extra = None

    points = [
        (0, 0), (1024, 0), (1024, 1024), (0, 1024),
        (1024, 0), (2048, 0), (2048, 1024), (1024, 1024),
        (2048, 0), (3072, 0), (3072, 1024), (2048, 1024),
    ]
    walls = []
    for index, (x, y) in enumerate(points):
        point2 = (index + 1) if index not in (3, 7, 11) else (
            0 if index == 3 else (4 if index == 7 else 8)
        )
        wall = _make_wall_disk_object(x=x, y=y, point2=point2)
        walls.append(wall)
    # Sector 0 -> Sector 1: blocked gate
    walls[1].fields.update(next_wall=7, next_sector=1, cstat=1)
    walls[7].fields.update(next_wall=1, next_sector=0, cstat=1)
    # Sector 1 -> Sector 2: open passage
    walls[5].fields.update(next_wall=11, next_sector=2)
    walls[11].fields.update(next_wall=5, next_sector=1)

    sprite0 = DiskObject(_empty_sprite_fields())
    sprite0.fields.update(x=512, y=512, z=0, sector=0, owner=1, index=0, extra=1, picnum=1)
    sprite0.extra = _make_xsprite_packed_extra()

    header = _make_header(num_sectors=3, num_walls=12, num_sprites=1)
    disk = DiskMap(
        version=0x0700, header=header, extra_header=_make_extra_header(),
        sky_offsets=[0], sectors=[sector0, sector1, sector2], walls=walls,
        sprites=[sprite0], source_crc32=0, source_size=0,
    )
    return parse_map(encode_map(disk))


# ---------------------------------------------------------------------------
# Fixture: vertical clearance failure
# ---------------------------------------------------------------------------

def fixture_vertical_clearance_failure() -> DiskMap:
    """Two sectors connected by a portal with insufficient vertical clearance.

    The at-rest opening is below 4096 Build units, making the portal non-traversable.
    """
    sector0 = _make_sector_disk_object(wall_ptr=0, wall_count=4, ceiling_z=-8192, floor_z=8192, extra=1)
    sector0.extra = PackedExtra("XSECTOR", _make_xsector_fields())
    sector1 = _make_sector_disk_object(wall_ptr=4, wall_count=4, ceiling_z=-8192, floor_z=8192, extra=-1)

    points = [
        (0, 0), (1024, 0), (1024, 1024), (0, 1024),
        (1024, 0), (2048, 0), (2048, 1024), (1024, 1024),
    ]
    walls = []
    for index, (x, y) in enumerate(points):
        point2 = (index + 1) if index not in (3, 7) else (0 if index == 3 else 4)
        wall = _make_wall_disk_object(x=x, y=y, point2=point2)
        walls.append(wall)
    walls[1].fields.update(next_wall=7, next_sector=1)
    walls[7].fields.update(next_wall=1, next_sector=0)

    sprite0 = DiskObject(_empty_sprite_fields())
    sprite0.fields.update(x=512, y=512, z=0, sector=0, owner=1, index=0, extra=1, picnum=1)
    sprite0.extra = _make_xsprite_packed_extra()

    header = _make_header(num_sectors=2, num_walls=8, num_sprites=1)
    disk = DiskMap(
        version=0x0700, header=header, extra_header=_make_extra_header(),
        sky_offsets=[0], sectors=[sector0, sector1], walls=walls,
        sprites=[sprite0], source_crc32=0, source_size=0,
    )
    return parse_map(encode_map(disk))


# ---------------------------------------------------------------------------
# Fixture: lift-enabled path
# ---------------------------------------------------------------------------

def fixture_lift_enabled_path() -> DiskMap:
    """Two sectors with a large floor delta, requiring a lift to traverse.

    The floor delta is > 4096, making the portal non-traversable at rest.
    """
    sector0 = _make_sector_disk_object(wall_ptr=0, wall_count=4, ceiling_z=-16384, floor_z=0, extra=1)
    sector0.extra = PackedExtra("XSECTOR", _make_xsector_fields())
    sector1 = _make_sector_disk_object(wall_ptr=4, wall_count=4, ceiling_z=-16384, floor_z=8192, extra=-1)

    points = [
        (0, 0), (1024, 0), (1024, 1024), (0, 1024),
        (1024, 0), (2048, 0), (2048, 1024), (1024, 1024),
    ]
    walls = []
    for index, (x, y) in enumerate(points):
        point2 = (index + 1) if index not in (3, 7) else (0 if index == 3 else 4)
        wall = _make_wall_disk_object(x=x, y=y, point2=point2)
        walls.append(wall)
    walls[1].fields.update(next_wall=7, next_sector=1)
    walls[7].fields.update(next_wall=1, next_sector=0)

    sprite0 = DiskObject(_empty_sprite_fields())
    sprite0.fields.update(x=512, y=512, z=0, sector=0, owner=1, index=0, extra=1, picnum=1)
    sprite0.extra = _make_xsprite_packed_extra()

    header = _make_header(num_sectors=2, num_walls=8, num_sprites=1)
    disk = DiskMap(
        version=0x0700, header=header, extra_header=_make_extra_header(),
        sky_offsets=[0], sectors=[sector0, sector1], walls=walls,
        sprites=[sprite0], source_crc32=0, source_size=0,
    )
    return parse_map(encode_map(disk))


# ---------------------------------------------------------------------------
# Fixture: teleporter/water transition
# ---------------------------------------------------------------------------

def fixture_teleporter_transition() -> DiskMap:
    """Two sectors connected by a teleporter (Blood sector type 604).

    The sectors are not portal-linked; they are connected via teleporter markers.
    """
    sector0 = _make_sector_disk_object(wall_ptr=0, wall_count=4, ceiling_z=-8192, floor_z=8192, extra=1)
    sector0.extra = PackedExtra("XSECTOR", _make_xsector_fields())
    sector0.fields["type"] = 604  # Teleport marker
    sector1 = _make_sector_disk_object(wall_ptr=4, wall_count=4, ceiling_z=-8192, floor_z=8192, extra=-1)

    points = [
        (0, 0), (1024, 0), (1024, 1024), (0, 1024),
        (2048, 0), (3072, 0), (3072, 1024), (2048, 1024),
    ]
    walls = []
    for index, (x, y) in enumerate(points):
        point2 = (index + 1) if index not in (3, 7) else (0 if index == 3 else 4)
        wall = _make_wall_disk_object(x=x, y=y, point2=point2)
        walls.append(wall)

    # Teleporter marker sprite in sector 0
    sprite0 = DiskObject(_empty_sprite_fields())
    sprite0.fields.update(x=512, y=512, z=0, sector=0, owner=1, index=0, extra=1, picnum=1)
    sprite0.extra = _make_xsprite_packed_extra()

    header = _make_header(num_sectors=2, num_walls=8, num_sprites=1)
    disk = DiskMap(
        version=0x0700, header=header, extra_header=_make_extra_header(),
        sky_offsets=[0], sectors=[sector0, sector1], walls=walls,
        sprites=[sprite0], source_crc32=0, source_size=0,
    )
    return parse_map(encode_map(disk))


# ---------------------------------------------------------------------------
# Fixture: branching/escape options
# ---------------------------------------------------------------------------

def fixture_branching_escape() -> DiskMap:
    """Four sectors in a branching layout: start -> {A, B, C}.

    Tests escape options and branching analysis.
    """
    sector0 = _make_sector_disk_object(wall_ptr=0, wall_count=4, ceiling_z=-8192, floor_z=8192, extra=1)
    sector0.extra = PackedExtra("XSECTOR", _make_xsector_fields())
    sector1 = _make_sector_disk_object(wall_ptr=4, wall_count=4, extra=-1)
    sector2 = _make_sector_disk_object(wall_ptr=8, wall_count=4, extra=-1)
    sector3 = _make_sector_disk_object(wall_ptr=12, wall_count=4, extra=-1)

    points = [
        (0, 0), (1024, 0), (1024, 1024), (0, 1024),       # sector 0
        (1024, 0), (2048, 0), (2048, 1024), (1024, 1024),  # sector 1
        (1024, 1024), (2048, 1024), (2048, 2048), (1024, 2048),  # sector 2
        (0, 1024), (1024, 1024), (1024, 2048), (0, 2048),  # sector 3
    ]
    walls = []
    for index, (x, y) in enumerate(points):
        point2 = (index + 1) if index not in (3, 7, 11, 15) else (
            0 if index == 3 else (4 if index == 7 else (8 if index == 11 else 12))
        )
        wall = _make_wall_disk_object(x=x, y=y, point2=point2)
        walls.append(wall)
    # Sector 0 -> Sector 1
    walls[1].fields.update(next_wall=7, next_sector=1)
    walls[7].fields.update(next_wall=1, next_sector=0)
    # Sector 0 -> Sector 3
    walls[3].fields.update(next_wall=12, next_sector=3)
    walls[12].fields.update(next_wall=3, next_sector=0)
    # Sector 1 -> Sector 2
    walls[5].fields.update(next_wall=11, next_sector=2)
    walls[11].fields.update(next_wall=5, next_sector=1)

    sprite0 = DiskObject(_empty_sprite_fields())
    sprite0.fields.update(x=512, y=512, z=0, sector=0, owner=1, index=0, extra=1, picnum=1)
    sprite0.extra = _make_xsprite_packed_extra()

    header = _make_header(num_sectors=4, num_walls=16, num_sprites=1)
    disk = DiskMap(
        version=0x0700, header=header, extra_header=_make_extra_header(),
        sky_offsets=[0], sectors=[sector0, sector1, sector2, sector3], walls=walls,
        sprites=[sprite0], source_crc32=0, source_size=0,
    )
    return parse_map(encode_map(disk))
