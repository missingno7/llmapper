from __future__ import annotations

from bloodmap.format import (
    SECTOR_FIELDS, SPRITE_FIELDS, WALL_FIELDS, XSPRITE_SCHEMA, encode_map, parse_map,
)
from bloodmap.model import DiskMap, DiskObject, ExtraHeader, PackedExtra


def synthetic_map() -> DiskMap:
    """Return a small valid v7 map built entirely from documented structures."""

    def empty(fields):
        return {name: 0 for name, _codec in fields}

    sector = empty(SECTOR_FIELDS)
    sector.update(wall_ptr=0, wall_count=4, ceiling_z=-8192, floor_z=8192, extra=-1)

    points = [(0, 0), (1024, 0), (1024, 1024), (0, 1024)]
    walls = []
    for index, (x, y) in enumerate(points):
        wall = empty(WALL_FIELDS)
        wall.update(x=x, y=y, point2=(index + 1) % 4, next_wall=-1, next_sector=-1,
                    picnum=1, over_picnum=-1, extra=-1)
        walls.append(DiskObject(wall))

    sprite = empty(SPRITE_FIELDS)
    sprite.update(x=512, y=512, z=0, sector=0, status=0, angle=0, owner=-1,
                  index=0, type=1, picnum=1, extra=1)
    xfields = {name: 0 for name, _bits, _signed in XSPRITE_SCHEMA}
    xfields.update(reference=0, target=-1, burn_source=-1)
    xsprite = PackedExtra("XSPRITE", xfields, b"\0" * 4)

    header = {
        "start_x": 512, "start_y": 512, "start_z": 0, "start_angle": 0,
        "start_sector": 0, "sky_bits": 0, "visibility": 800, "matt_id": 0,
        "sky_type": 0, "revision": 1, "num_sectors": 1, "num_walls": 4,
        "num_sprites": 1,
    }
    extra_header = ExtraHeader(
        copyright=b"\0" * 64, xsprite_size=56, xwall_size=24, xsector_size=60,
        xmp_signature=b"\0" * 3, xmp_header_version=0, xmp_map_flags=0,
        xmp_board_width=0, xmp_board_height=0, xmp_palette=0,
        xmp_sky_repeat_count=0, xmp_sky_visibility=0, reserved=b"\0" * 37,
    )
    disk = DiskMap(
        version=0x0700, header=header, extra_header=extra_header, sky_offsets=[0],
        sectors=[DiskObject(sector)], walls=walls,
        sprites=[DiskObject(sprite, xsprite)], source_crc32=0, source_size=0,
    )
    return parse_map(encode_map(disk))
