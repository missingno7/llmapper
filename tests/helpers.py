from __future__ import annotations

import copy
from pathlib import Path

from bloodmap.format import (
    SECTOR_FIELDS, SPRITE_FIELDS, WALL_FIELDS, XSECTOR_SCHEMA, XSPRITE_SCHEMA,
    encode_map, parse_map,
)
from bloodmap.model import DiskMap, DiskObject, ExtraHeader, PackedExtra
from bloodmap.patterns import (
    NAMED_POPULATIONS, corpus_map_path, corpus_root, is_structured_corpus,
    list_corpus_maps,
)


def blood_corpus_root() -> Path:
    """The local Blood corpus root: `BLOODMAP_CORPUS`, else `maps/blood`."""
    return corpus_root()


def campaign_directory() -> Path:
    """Where the original campaign `E*M*.MAP` files live.

    The corpus was reorganized into provenance directories on 2026-08-31; a
    flat `BLOODMAP_CORPUS` override still resolves to the root itself.
    """
    root = blood_corpus_root()
    return root / "campaign" if is_structured_corpus(root) else root


def corpus_map(filename: str) -> Path:
    """Resolve one named corpus map, wherever the layout puts it.

    Returns a non-existent path when the corpus is absent, so a caller's
    `exists()` skip guard still works. This lived here first; it is now
    `bloodmap.patterns.corpus_map_path`, because eight non-test callers
    needed the same answer and were each spelling a flat path by hand.
    """
    return corpus_map_path(filename, root=blood_corpus_root(), missing_ok=True)


def named_corpus_maps() -> list[Path]:
    """Campaign, BloodBath, curated and own-conversion maps, sorted.

    This is the set the native losslessness gate is expected to hold for. The
    bulk `community/` population is deliberately excluded: those maps have not
    passed the gate, and the fail-closed health report covers them instead.
    `NAMED_POPULATIONS` is the same set `corpus_map_path` searches by name,
    and for the same reason.
    """
    from bloodmap.patterns import is_editor_autosave

    root = blood_corpus_root()
    found: dict[str, Path] = {}
    for population in NAMED_POPULATIONS:
        for item in list_corpus_maps(root, population=population, attach_tiers=False):
            # XMapEdit autosaves land in the corpus whenever the owner opens
            # the editor; they are quarantined by the registry and are never
            # part of the losslessness gate (owner, 2026-09-02: ignore them).
            if is_editor_autosave(item.path):
                continue
            found.setdefault(item.name.upper(), item.path)
    return sorted(found.values())


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


def synthetic_two_sector_map() -> DiskMap:
    """Two portal-linked sectors with cross-boundary markers, owners, and triggers."""
    disk = synthetic_map()
    sector0 = disk.sectors[0]
    sector0.fields["extra"] = 1
    xsector_fields = {name: 0 for name, _bits, _signed in XSECTOR_SCHEMA}
    xsector_fields.update(reference=9, marker_0=1, marker_1=-1)
    sector0.extra = PackedExtra("XSECTOR", xsector_fields)

    sector1 = copy.deepcopy(sector0)
    sector1.fields.update(wall_ptr=4, extra=-1)
    sector1.extra = None
    disk.sectors = [sector0, sector1]

    points = [
        (0, 0), (1024, 0), (1024, 1024), (0, 1024),
        (1024, 0), (2048, 0), (2048, 1024), (1024, 1024),
    ]
    walls = []
    for index, (x, y) in enumerate(points):
        wall = {name: 0 for name, _codec in WALL_FIELDS}
        point2 = (index + 1) if index not in (3, 7) else (0 if index == 3 else 4)
        wall.update(x=x, y=y, point2=point2, next_wall=-1, next_sector=-1,
                    picnum=1, over_picnum=-1, extra=-1)
        walls.append(DiskObject(wall))
    walls[1].fields.update(next_wall=7, next_sector=1)
    walls[7].fields.update(next_wall=1, next_sector=0)
    disk.walls = walls

    sprite0 = disk.sprites[0]
    sprite0.fields.update(owner=1, index=0, sector=0, extra=1)
    sprite0.extra.fields.update(
        reference=12, tx_id=100, rx_id=0, target=1, burn_source=-1, dude_flag_4=1,
    )
    sprite1 = copy.deepcopy(sprite0)
    sprite1.fields.update(x=1536, sector=1, owner=-1, index=1, extra=2)
    sprite1.extra.fields.update(reference=1, tx_id=0, rx_id=100, target=-1, burn_source=-1)
    disk.sprites = [sprite0, sprite1]
    disk.header.update(num_sectors=2, num_walls=8, num_sprites=2)
    return parse_map(encode_map(disk))


def synthetic_multi_loop_map() -> DiskMap:
    """One sector with an outer loop and an oppositely wound inner loop."""
    disk = synthetic_map()
    disk.sectors[0].fields["wall_count"] = 8
    points = [
        (0, 0), (4096, 0), (4096, 4096), (0, 4096),
        (1024, 1024), (1024, 3072), (3072, 3072), (3072, 1024),
    ]
    walls = []
    for index, (x, y) in enumerate(points):
        wall = {name: 0 for name, _codec in WALL_FIELDS}
        point2 = (index + 1) if index not in (3, 7) else (0 if index == 3 else 4)
        wall.update(x=x, y=y, point2=point2, next_wall=-1, next_sector=-1,
                    picnum=1, over_picnum=-1, extra=-1)
        walls.append(DiskObject(wall))
    disk.walls = walls
    disk.header["num_walls"] = 8
    return parse_map(encode_map(disk))


def synthetic_separated_rooms_map() -> DiskMap:
    """Two adjacent rooms with no portal; the shared edge is solid on both sides."""
    disk = synthetic_two_sector_map()
    disk.walls[1].fields.update(next_wall=-1, next_sector=-1)
    disk.walls[7].fields.update(next_wall=-1, next_sector=-1)
    return parse_map(encode_map(disk))


def synthetic_masked_portal_map() -> DiskMap:
    """Two rooms joined by a masked see-through portal."""
    disk = synthetic_two_sector_map()
    disk.walls[1].fields["cstat"] = 16
    disk.walls[7].fields["cstat"] = 16
    return parse_map(encode_map(disk))
