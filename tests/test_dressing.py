"""Props stand on something, and the something is anchored to a record.

`anchors.find_bundles` recovers a bundle from GEOMETRY and never from
proximity: one outer neighbour, a floor raised out of its host by more than a
step, an elongated footprint, and at least one visible prop. A handful of
sprites dropped at coordinates has none of those and comes back as nothing --
which is the whole difference between dressing a room and scattering in one.
"""

from __future__ import annotations

import unittest

from bloodmap import city
from bloodmap.planar_layout import PlanarLayout

FLOOR = 8192
CEILING = FLOOR - 3 * 16960
ROOM = [(0, 0), (32768, 0), (32768, 16384), (0, 16384)]
ANCHOR = ((0, 0), (32768, 0))


def _room(*, with_plinth: bool):
    """A room, and either a plinth carrying two props or two loose props."""
    made = city.dressing(ANCHOR, [city.prop("urn"), city.prop("statue")],
                         inward=(0, 1), floor_z=FLOOR, ceiling_z=CEILING,
                         surface_id="plinth:nave")
    layout = PlanarLayout(name="dressing-fixture")
    layout.add_region("nave", ROOM,
                      holes=[made["hole"]] if with_plinth else [],
                      floor_z=FLOOR, ceiling_z=CEILING, floor_picnum=4,
                      ceiling_picnum=379, wall_picnum=401, role="interior",
                      declared_zero_exit=True)
    if with_plinth:
        spec = made["surface"]
        layout.add_region(spec.surface_id, spec.rings[0], floor_z=spec.floor_z,
                          ceiling_z=spec.ceiling_z,
                          floor_picnum=spec.floor_tile,
                          ceiling_picnum=spec.ceiling_tile,
                          wall_picnum=spec.wall_tile, role="interior",
                          declared_zero_exit=True)
        for number, edge in enumerate(_edges(spec.rings[0])):
            layout.add_connection(f"plinth:{number}", "nave",
                                  spec.surface_id, role="portal",
                                  a1=edge[0], a2=edge[1])
    layout.set_player_start("nave", x=16384, y=12288, z=FLOOR, angle=0)
    disk = layout.compile().level.to_disk_map()
    _place(disk, made["props"], on_plinth=with_plinth)
    return disk, made


def _edges(ring):
    return [(tuple(ring[index]), tuple(ring[(index + 1) % len(ring)]))
            for index in range(len(ring))]


def _place(disk, props, *, on_plinth):
    from bloodmap.format import SPRITE_FIELDS
    from bloodmap.model import DiskObject

    for prop in props:
        sector = 0
        if on_plinth:
            for index, item in enumerate(disk.sectors):
                if int(item.fields["wall_picnum"] if False
                       else item.fields["floor_picnum"]) == city.INTERIOR_FLOOR:
                    sector = index
                    break
        fields = {name: 0 for name, _code in SPRITE_FIELDS}
        fields.update({
            "x": prop["point"][0], "y": prop["point"][1],
            "z": int(disk.sectors[sector].fields["floor_z"]),
            "sector": sector, "picnum": prop["tile"], "shade": prop["shade"],
            "cstat": prop["cstat"], "x_repeat": 64, "y_repeat": 64,
            "owner": -1, "extra": -1, "clipdist": 32,
        })
        disk.sprites.append(DiskObject(fields=fields))


def _bundles(disk):
    """`find_bundles` reads a BuildIR: Blood's sprite type lives in the
    shared `lotag` slot there, and a `LevelIR` keeps it under `type`."""
    from bloodmap.anchors import find_bundles

    return find_bundles(disk.to_build_ir())


class ABundleComesBackAsOneBundle(unittest.TestCase):

    def test_a_dressed_room_gives_back_one_bundle_on_its_anchor(self):
        disk, made = _room(with_plinth=True)
        found = _bundles(disk)
        self.assertEqual(len(found), 1)
        bundle = found[0]
        self.assertEqual(bundle.kind, "raised-island")
        self.assertEqual(len(bundle.props), 2)
        #: the same anchor: the host is the room the anchor record belongs to
        self.assertEqual(int(disk.sectors[bundle.host].fields["floor_picnum"]),
                         4)
        self.assertEqual(bundle.measures["rise_units"], made["rise"])

    def test_the_same_props_dropped_at_coordinates_come_back_as_nothing(self):
        # THE FAIL-FIRST. The sprites are the same, at the same points, in the
        # same room; what is missing is the thing they stand on.
        disk, _made = _room(with_plinth=False)
        self.assertEqual(_bundles(disk), [])

    def test_the_props_are_named_and_visible_or_no_reader_counts_them(self):
        from bloodmap.read_intent import named_props

        disk, _made = _room(with_plinth=True)
        counted = named_props(disk.to_level_ir())
        self.assertEqual(sum(sum(row.values()) for row in counted.values()), 2)
        self.assertIn("urn", {name for row in counted.values() for name in row})

    def test_a_plinth_that_is_not_waist_high_is_refused(self):
        with self.assertRaises(city.DressingError) as caught:
            city.dressing(ANCHOR, [city.prop("urn")], inward=(0, 1),
                          floor_z=FLOOR, ceiling_z=CEILING,
                          surface_id="plinth:low", rise=2048)
        self.assertIn("waist height", str(caught.exception))

    def test_a_plinth_that_is_not_elongated_is_refused(self):
        with self.assertRaises(city.DressingError) as caught:
            city.dressing(((0, 0), (4096, 0)), [city.prop("urn")],
                          inward=(0, 1), floor_z=FLOOR, ceiling_z=CEILING,
                          surface_id="plinth:square", spread=0.5)
        self.assertIn("run you stand along", str(caught.exception))

    def test_a_tile_the_campaign_has_no_word_for_is_refused(self):
        with self.assertRaises(city.DressingError):
            city.prop("crate")

    def test_nothing_here_takes_a_coordinate(self):
        import inspect

        names = set(inspect.signature(city.dressing).parameters)
        self.assertIn("anchor", names)
        for banned in ("x", "y", "at", "point", "position"):
            self.assertNotIn(banned, names)


if __name__ == "__main__":
    unittest.main()
