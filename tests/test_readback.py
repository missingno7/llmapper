"""Every constructor builds, is read back, and is diffed against its sentence.

Roadmap Phase 11 item 3, generalized off the pattern zoo. The zoo proved the
loop for the things it exhibits; blood-city then built a curtain that failed
conformance and no gate said so, because the gates lived in the zoo's own
`sweep.py` and `selfread.py`. `bloodmap.readback` owns the comparison and
this is where every constructor is held to it.

Two shapes of test, and the third is the gate over both:

1. **build in a minimal PlanarLayout, read back, assert equality.** The
   layout is the smallest thing the constructor will compile in -- a room, a
   region behind, the connections the compiler needs -- so a difference is
   about the constructor and not about the level around it.
2. **build in a minimal levelprog TREE** for the two constructors blood-city
   places from the tree (`turnstiles.py`, `curtains.py`). The two dialects
   are the reason the city's curtain drifted from the zoo's: a tree placer
   that hand-adapts a spec can drift from the flat constructor, and only a
   read-back on both sides can see it.
3. **the registry test**: a public constructor with neither a read-back test
   nor a written reason fails, exactly the way the zoo's conformance test
   fails a constructor without an exhibit.

Fail-first, on real defects, in `ReadBackFailsFirst`:

* the city's curtain as committed at 8c42701 -- before the P1 rebuild --
  pulled out of git so the anchor outlives the fix. Its sentence says
  `members` is the fin alone and its fabric draws in the walkable band; the
  built map deforms the auditorium and draws nothing a body can see.
* a deliberately mis-wired copy of a current construct: a Link receiver with
  `shadeAlways` set (which `sectorfx.cpp:161-166` makes deaf to busy), and a
  door with an rx and no route to work it.
"""

from __future__ import annotations

import importlib
import subprocess
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

PLAYER = 16960


# ---------------------------------------------------------------------------
# the harness
# ---------------------------------------------------------------------------

#: Tile extents this file DECLARES for its own probes. Not mined ART: a
#: minimal layout has no art directory, and `PlanarLayout` needs an extent
#: only to seat a sprite on the floor. Declared here so the test says where
#: the number came from rather than borrowing a corpus it has not got.
#: picnum -> (tile pixel height, picanm y offset), which is what
#: `PlanarLayout.tile_extents` means.
PROBE_TILE_EXTENTS = {1044: (128, 0)}


def _layout(name="probe"):
    from bloodmap.planar_layout import PlanarLayout

    #: The room stops at y 3072 and every construct is built BEYOND it. A
    #: region wholly inside another is a containment `PlanarLayout` refuses
    #: -- neither side of that boundary can be a portal -- which is the
    #: "sub-rooms go in a back box" gotcha the roadmap records.
    layout = PlanarLayout(name=name,
                          tile_extents=dict(PROBE_TILE_EXTENTS))
    layout.add_region("room", [(0, 0), (8192, 0), (8192, 3072), (0, 3072)],
                      floor_z=0, ceiling_z=-33280, wall_picnum=200,
                      floor_picnum=201, ceiling_picnum=202,
                      declared_zero_exit=True)
    layout.set_player_start("room", x=1024, y=1024, z=0, angle=0)
    return layout


def _rect(x0, y0, x1, y1):
    return [(x0, y0), (x1, y0), (x1, y1), (x0, y1)]


def _built(layout):
    """Compile and hand back the disk map with its region -> sector table."""
    compiled = layout.compile()
    disk = compiled.level.to_disk_map()
    sectors = {name: allocation.sector_id
               for name, allocation in compiled.allocations.items()}
    return disk, sectors, compiled


def _assert_agrees(case, result):
    case.assertTrue(result.agrees, result.report())
    case.assertEqual(result.unmeasured, [], result.report())


# ---------------------------------------------------------------------------
# 1. bloodmap.mechanism
# ---------------------------------------------------------------------------

class CurtainReadBack(unittest.TestCase):
    """`mechanism.curtain`, both leaf counts, built and read back."""

    def _hang(self, layout, **overrides):
        from bloodmap.mechanism import curtain

        kwargs = dict(opening=(1024, 3072, 3072, 3328), axis="x", channel=200,
                      leaf_region="leaf", floor_z=0, ceiling_z=-33280,
                      frame_picnum=200, declared_zero_exit=True)
        kwargs.update(overrides)
        built = curtain(layout, "cur", **kwargs)
        layout.declare_motion("leaf", [])
        layout.add_connection("c0", "room", "leaf",
                              a1=(1024, 3072), a2=(3072, 3072), min_width=384)
        layout.add_region("back", _rect(1024, 3328, 3072, 5376),
                          floor_z=0, ceiling_z=-33280, declared_zero_exit=True,
                          wall_picnum=200, floor_picnum=201,
                          ceiling_picnum=202)
        layout.add_connection("c1", "leaf", "back",
                              a1=(1024, 3328), a2=(3072, 3328), min_width=384)
        return built

    def _sentence(self, sector, **overrides):
        from bloodmap.readback import sentence

        claims = dict(
            name="curtain", sector=sector, sectors=[sector], sector_type=614,
            members=[], wiring={"channel": 200, "rx_id": 200},
            drag={"closure": True},
            visibility={"tiles": [146], "walkable_band": True, "per_leaf": 1},
            state={"changes": True})
        claims.update(overrides)
        return sentence("curtain", **claims)

    def test_a_one_leaf_curtain_reads_back_as_what_it_declared(self):
        from bloodmap.readback import read_back

        layout = _layout()
        self._hang(layout)
        disk, sectors, _ = _built(layout)
        result = read_back(disk, [self._sentence(sectors["leaf"])],
                           map_name="one-leaf curtain")
        _assert_agrees(self, result)

    def test_a_two_leaf_curtain_reads_back_as_what_it_declared(self):
        from bloodmap.readback import read_back

        layout = _layout()
        self._hang(layout, leaves=2)
        disk, sectors, _ = _built(layout)
        #: One visible fabric wall PER LEAF, not per wall. DOOR-CURTAINSD s4
        #: has six fabric walls and two visible ones, so a rule demanding all
        #: of them rejects the tutorial (roadmap, "the curtain family").
        result = read_back(disk, [self._sentence(
            sectors["leaf"], visibility={"tiles": [146],
                                         "walkable_band": True,
                                         "per_leaf": 2})],
            map_name="two-leaf curtain")
        _assert_agrees(self, result)

    def test_you_are_told_to_push_the_curtain_and_not_to_find_a_switch(self):
        # The wall-level route, on a map this file builds -- no corpus. Our
        # own constructor puts the push XWALL on the fabric, which is a
        # ONE-SIDED wall beside a void slot, and `observe_motion_sector`
        # read the whole thing as `remote_rx`: "find a switch", of a
        # mechanism that has none. The engine operates the hit wall's own
        # XWALL without looking at `nextsector` (`player.cpp:1637-1641`),
        # and `SetWallState` (`triggers.cpp:112-128`) sends its txID.
        from bloodmap.doors import _wall_owners, observe_motion_sector

        layout = _layout()
        self._hang(layout)
        disk, sectors, _ = _built(layout)
        record = observe_motion_sector(disk, sectors["leaf"],
                                       owners=_wall_owners(disk))
        self.assertEqual(record["interaction"], "wall_push")
        pushers = [item for item in record["own_xwalls"]
                   if "trigger_push" in item["triggers"]]
        self.assertTrue(pushers)
        self.assertTrue(all(item["one_sided"] for item in pushers),
                        "the fabric of a void-slot curtain is one-sided; "
                        "that is why the portal-only reading missed it")
        self.assertEqual({item["tx_id"] for item in pushers},
                         {int(record["rx_id"])})

    def test_the_read_back_notices_a_curtain_that_declares_the_wrong_members(self):
        # The gate has to be able to fail. A sentence claiming the fin drags
        # a neighbour it does not is a difference in the same direction as
        # the city's real defect, and the reader must report it.
        from bloodmap.readback import read_back

        layout = _layout()
        self._hang(layout)
        disk, sectors, _ = _built(layout)
        result = read_back(disk,
                           [self._sentence(sectors["leaf"],
                                           members=[sectors["room"]])],
                           map_name="over-declared curtain")
        self.assertFalse(result.agrees)
        self.assertIn("members", [d.facet for d in result.differences])


class PlanarDoorReadBack(unittest.TestCase):
    """`mechanism.planar_door`: a lid sliding off a hole."""

    def _build(self):
        from bloodmap.mechanism import planar_door

        layout = _layout()
        built = planar_door(
            layout, "door", footprint=(1024, 3072, 3072, 5248), axis="y",
            split=5120, travel=-1920, channel=100,
            lid_region="lid", hole_region="hole", floor_z=0,
            ceiling_z=-33280,
            lid_kwargs={"declared_zero_exit": True},
            hole_kwargs={"declared_zero_exit": True})
        layout.add_connection("c0", "room", "lid",
                              a1=(1024, 3072), a2=(3072, 3072), min_width=384)
        return layout, built

    def test_a_planar_door_reads_back_as_the_pair_it_declared(self):
        from bloodmap.readback import read_back, sentence

        layout, built = self._build()
        disk, sectors, _ = _built(layout)
        motor = sectors[built["motor"]]
        members = sorted({sectors["lid"], sectors["hole"]})
        result = read_back(disk, [sentence(
            "planar_door", name="casket", sector=motor,
            sectors=members, sector_type=614, members=members,
            wiring={"channel": 100, "rx_id": 100},
            drag={"closure": True}, state={"changes": True})],
            map_name="planar door")
        _assert_agrees(self, result)

    def test_the_read_back_notices_a_planar_door_wired_to_the_wrong_channel(self):
        from bloodmap.readback import read_back, sentence

        layout, built = self._build()
        disk, sectors, _ = _built(layout)
        motor = sectors[built["motor"]]
        result = read_back(disk, [sentence(
            "planar_door", name="casket", sector=motor, sectors=[motor],
            sector_type=614, wiring={"channel": 999, "rx_id": 999})],
            map_name="mis-channelled planar door")
        self.assertFalse(result.agrees)
        self.assertIn("wiring.rx_id", [d.facet for d in result.differences])


class TurnstileReadBack(unittest.TestCase):
    """`mechanism.turnstile` and `turnstile_pair`: the rotors."""

    def _one(self, layout, region="rotor", centre=(4096, 4608)):
        from bloodmap.mechanism import turnstile

        cx, cy = centre
        half = 1024
        outline = _rect(cx - half, cy - half, cx + half, cy + half)
        built = turnstile(layout, region, outline, pivot=(cx, cy),
                          period=255, floor_z=0, ceiling_z=-4 * 128 * 16,
                          declared_zero_exit=True)
        return built

    def test_a_turnstile_reads_back_as_the_rotor_it_declared(self):
        from bloodmap.readback import read_back, sentence

        layout = _layout()
        self._one(layout)
        disk, sectors, _ = _built(layout)
        result = read_back(disk, [sentence(
            "turnstile", name="rotor", sector=sectors["rotor"],
            sectors=[sectors["rotor"]], sector_type=615, members=[],
            drag={"closure": True}, state={"changes": True})],
            map_name="turnstile")
        _assert_agrees(self, result)

    def test_a_counter_rotating_pair_reads_back_as_two_rotors(self):
        from bloodmap.mechanism import turnstile_pair
        from bloodmap.readback import read_back, sentence

        layout = _layout()
        turnstile_pair(
            layout, "gate",
            outlines=(_rect(1024, 3584, 3072, 5632),
                      _rect(4096, 3584, 6144, 5632)),
            pivots=((2048, 4608), (5120, 4608)),
            period=255, floor_z=0, ceiling_z=-4 * 128 * 16,
            declared_zero_exit=True)
        disk, sectors, _ = _built(layout)
        claims = [sentence("turnstile", name=name, sector=sectors[name],
                           sectors=[sectors[name]], sector_type=615,
                           members=[], drag={"closure": True},
                           state={"changes": True})
                  for name in sorted(sectors) if name.startswith("gate")]
        self.assertEqual(len(claims), 2)
        result = read_back(disk, claims, map_name="turnstile pair")
        _assert_agrees(self, result)


class SlidingGateReadBack(unittest.TestCase):
    """`mechanism.sliding_gate`: leaves that part across a threshold."""

    def test_a_sliding_gate_reads_back_as_the_sprite_payload_it_declared(self):
        from bloodmap.mechanism import sliding_gate
        from bloodmap.readback import read_back, sentence

        layout = _layout()
        sliding_gate(layout, "gate", _rect(1024, 3072, 5120, 4096),
                     threshold=((1536, 3584), (4608, 3584)),
                     travel=768, channel=300, floor_z=0,
                     ceiling_z=-4 * 128 * 16, declared_zero_exit=True)
        layout.add_connection("c0", "room", "gate",
                              a1=(1024, 3072), a2=(5120, 3072), min_width=384)
        disk, sectors, _ = _built(layout)
        result = read_back(disk, [sentence(
            "sliding_gate", name="gate", sector=sectors["gate"],
            sectors=[sectors["gate"]], sector_type=614, members=[],
            wiring={"channel": 300, "rx_id": 300},
            drag={"closure": True}, state={"changes": True})],
            map_name="sliding gate")
        _assert_agrees(self, result)


class LiftReadBack(unittest.TestCase):
    """`mechanism.lift`: a floor that travels in z."""

    def test_a_lift_reads_back_as_a_z_motion_that_changes_state(self):
        from bloodmap.mechanism import lift
        from bloodmap.readback import read_back, sentence

        layout = _layout()
        lift(layout, "lift", footprint=(1024, 3072, 3072, 5120),
             region="car", low_z=0, high_z=-PLAYER, ceiling_z=-33280,
             channel=400, route="remote", declared_zero_exit=True)
        layout.add_connection("c0", "room", "car",
                              a1=(1024, 3072), a2=(3072, 3072), min_width=384)
        disk, sectors, _ = _built(layout)
        result = read_back(disk, [sentence(
            "lift", name="lift", sector=sectors["car"],
            sectors=[sectors["car"]],
            wiring={"channel": 400, "rx_id": 400},
            state={"changes": True})], map_name="lift")
        _assert_agrees(self, result)
        row = result.measured[0]
        self.assertNotEqual(row["state_pair"]["headroom_change"], 0)


# ---------------------------------------------------------------------------
# 2. bloodmap.doors
# ---------------------------------------------------------------------------

class ZMotionDoorReadBack(unittest.TestCase):
    """`doors.z_motion_door`: the XSECTOR a ceiling door needs.

    It builds no geometry of its own -- it returns the behavior dict a region
    carries -- so the read-back stands a region on it and asks the reading
    stack what that region became.
    """

    def test_a_z_motion_door_reads_back_as_a_door_that_opens(self):
        from bloodmap.doors import z_motion_door
        from bloodmap.readback import read_back, sentence

        layout = _layout()
        behavior = z_motion_door(0, -PLAYER * 2, interaction="remote",
                                 rx_id=500)
        layout.add_region("door", _rect(1024, 3072, 3072, 3584),
                          floor_z=0, ceiling_z=0, type=600,
                          sector_behavior=behavior, declared_zero_exit=True,
                          wall_picnum=200, floor_picnum=201,
                          ceiling_picnum=202)
        layout.add_connection("c0", "room", "door",
                              a1=(1024, 3072), a2=(3072, 3072), min_width=384)
        layout.add_region("back", _rect(1024, 3584, 3072, 5632),
                          floor_z=0, ceiling_z=-33280, declared_zero_exit=True,
                          wall_picnum=200, floor_picnum=201,
                          ceiling_picnum=202)
        layout.add_connection("c1", "door", "back",
                              a1=(1024, 3584), a2=(3072, 3584), min_width=384)
        disk, sectors, _ = _built(layout)
        result = read_back(disk, [sentence(
            "z_motion_door", name="door", sector=sectors["door"],
            sectors=[sectors["door"]], sector_type=600,
            wiring={"channel": 500, "rx_id": 500},
            state={"changes": True})], map_name="z-motion door")
        _assert_agrees(self, result)

    def test_a_door_that_cannot_move_is_reported(self):
        # The zoo's original defect, in miniature: a type-600 sector whose z
        # pair is identical. Every field is legal and the mechanism is inert.
        from bloodmap.doors import z_motion_door
        from bloodmap.readback import read_back, sentence

        layout = _layout()
        behavior = z_motion_door(0, 0, interaction="remote", rx_id=500)
        layout.add_region("door", _rect(1024, 3072, 3072, 3584),
                          floor_z=0, ceiling_z=0, type=600,
                          sector_behavior=behavior, declared_zero_exit=True,
                          wall_picnum=200, floor_picnum=201,
                          ceiling_picnum=202)
        layout.add_connection("c0", "room", "door",
                              a1=(1024, 3072), a2=(3072, 3072), min_width=384)
        layout.add_region("back", _rect(1024, 3584, 3072, 5632),
                          floor_z=0, ceiling_z=-33280, declared_zero_exit=True,
                          wall_picnum=200, floor_picnum=201,
                          ceiling_picnum=202)
        layout.add_connection("c1", "door", "back",
                              a1=(1024, 3584), a2=(3072, 3584), min_width=384)
        disk, sectors, _ = _built(layout)
        result = read_back(disk, [sentence(
            "z_motion_door", name="door", sector=sectors["door"],
            sectors=[sectors["door"]], sector_type=600,
            state={"changes": True})], map_name="inert door")
        self.assertFalse(result.agrees)
        self.assertIn("state.changes", [d.facet for d in result.differences])


# ---------------------------------------------------------------------------
# 3. bloodmap.glass
# ---------------------------------------------------------------------------

class GlazeReadBack(unittest.TestCase):
    """`glass.glaze`: a two-sided wall turned into a breakable pane."""

    def test_a_glazed_span_reads_back_with_its_panes_drawn(self):
        from bloodmap.glass import GLASS_TILE, glaze, pane_faults
        from bloodmap.readback import read_back, sentence

        layout = _layout()
        layout.add_region("shop", _rect(1024, 3072, 3072, 5120),
                          floor_z=0, ceiling_z=-33280, declared_zero_exit=True,
                          wall_picnum=200, floor_picnum=201,
                          ceiling_picnum=202)
        layout.add_connection("c0", "room", "shop",
                              a1=(1024, 3072), a2=(3072, 3072), min_width=384)
        compiled = layout.compile()
        report = glaze(compiled.level, [(1000, 3040, 3100, 3100)])
        self.assertGreater(report["panes"], 0)
        disk = compiled.level.to_disk_map()
        self.assertEqual(pane_faults(disk), [])
        sectors = {name: a.sector_id
                   for name, a in compiled.allocations.items()}
        result = read_back(disk, [sentence(
            "glass", name="shopfront", sector=sectors["shop"],
            sectors=[sectors["shop"], sectors["room"]],
            visibility={"tiles": [GLASS_TILE]})], map_name="glazed span")
        _assert_agrees(self, result)


# ---------------------------------------------------------------------------
# 4. bloodmap.aperture
# ---------------------------------------------------------------------------

class ApertureReadBack(unittest.TestCase):
    """The opening grammar: a mouth, a frame around one, a whole frontage."""

    def test_a_pierced_opening_reads_back_with_its_jamb_drawn(self):
        from bloodmap.aperture import Aperture, Leaf, pierce
        from bloodmap.readback import read_back, sentence

        layout = _layout()
        #: The hall is exactly as wide as the mouth, so the whole shared
        #: stretch IS the opening. A feature narrower than the wall leaves
        #: the rest of that stretch coincident and unpaired -- the "needs a
        #: neck" gotcha -- and this probe is about the mouth, not the neck.
        layout.add_region("hall", _rect(1536, 3072, 2560, 5120),
                          floor_z=0, ceiling_z=-33280, declared_zero_exit=True,
                          wall_picnum=200, floor_picnum=201,
                          ceiling_picnum=202)
        #: A mouth is a leaf PLUS a mediation: the aperture grammar refuses
        #: an opening with bare facade above it, so the room's own wall
        #: continues over the head as a lintel.
        pierce(layout, Aperture("mouth", leaf=Leaf(width=2.0, height=1.6),
                                mediation="lintel"),
               "room", "hall", a1=(1536, 3072), a2=(2560, 3072))
        disk, sectors, _ = _built(layout)
        result = read_back(disk, [sentence(
            "aperture", name="mouth", sector=sectors["hall"],
            sectors=[sectors["hall"], sectors["room"]])],
            map_name="pierced opening")
        _assert_agrees(self, result)

    def test_a_maskwall_panel_reads_back_drawing_in_the_walkable_band(self):
        # The rendering law's positive case: a masked two-sided wall is the
        # one way a tile reaches the middle band of a portal
        # (engine.cpp:4938-4940, and render_slots' masked_middle row).
        from bloodmap.aperture import maskwall_panel
        from bloodmap.readback import read_back, sentence

        layout = _layout()
        layout.add_region("hall", _rect(1024, 3072, 3072, 5120),
                          floor_z=0, ceiling_z=-33280, declared_zero_exit=True,
                          wall_picnum=200, floor_picnum=201,
                          ceiling_picnum=202)
        layout.add_connection("c0", "room", "hall",
                              a1=(1024, 3072), a2=(3072, 3072), min_width=384)
        maskwall_panel(layout, "grate", "room", "hall",
                       a1=(1024, 3072), a2=(3072, 3072), picnum=903)
        disk, sectors, _ = _built(layout)
        result = read_back(disk, [sentence(
            "aperture", name="grate", sector=sectors["hall"],
            sectors=[sectors["hall"], sectors["room"]],
            visibility={"tiles": [903], "walkable_band": True})],
            map_name="maskwall panel")
        _assert_agrees(self, result)


# ---------------------------------------------------------------------------
# 5. the other dialect: the same constructs placed from a levelprog TREE
# ---------------------------------------------------------------------------

CITY_LEVEL = ROOT / "projects" / "blood-city" / "level"


def _city_module(name):
    """Import a blood-city level module; the directory is not a package."""
    import sys

    for path in (str(ROOT), str(CITY_LEVEL)):
        if path not in sys.path:
            sys.path.insert(0, path)
    return importlib.import_module(name)


def _tree(node_id="probe"):
    """The smallest level program a city placer will stand in."""
    from bloodmap.levelprog import LevelProgram, Style

    return LevelProgram(node_id, style=Style(
        wall_picnum=180, floor_picnum=292, ceiling_picnum=385,
        floor_z=0, clear_height=8 * PLAYER))


@unittest.skipUnless(CITY_LEVEL.is_dir(), "blood-city is not present")
class CityTreeReadBack(unittest.TestCase):
    """The two constructors blood-city places from the TREE, read back.

    The level is authored in two dialects -- the levelprog tree and flat
    `PlanarLayout` -- and the constructors are split by dialect. That split
    is what let the city's curtain drift from the zoo's: the tree placer
    consumes `curtain_spec` and lays the geometry itself, so a flat-side test
    proves nothing about it. These build the tree side and read the same
    sentence back.
    """

    def test_the_city_places_two_counter_rotating_rotors_from_the_tree(self):
        from bloodmap.readback import read_back, sentence

        turnstiles = _city_module("turnstiles")
        level = _tree()
        district = level.assembly("district")
        street = district.rect_room(
            "street", size=(24 * 1024, 8 * 1024),
            region_kwargs={"declared_zero_exit": True})
        level.set_start(street)
        built = turnstiles.pair(district, street, "probe",
                                centre_x=12 * 1024, y=4 * 1024, floor_z=0,
                                wall_picnum=180, floor_picnum=292,
                                ceiling_picnum=385)
        layout = level.compile()
        placed = turnstiles.populate(layout, built)
        self.assertEqual(placed["axes"], 2)
        self.assertEqual(placed["blades"], 8)
        compiled = layout.compile()
        disk = compiled.level.to_disk_map()
        claims = [sentence(
            "turnstile", name=rotor["name"],
            sector=compiled.allocations[rotor["region_id"]].sector_id,
            sectors=[compiled.allocations[rotor["region_id"]].sector_id],
            sector_type=615, members=[], drag={"closure": True},
            state={"changes": True}) for rotor in built]
        _assert_agrees(self, read_back(disk, claims,
                                       map_name="tree turnstiles"))

    def test_the_city_hangs_a_curtain_from_the_tree_that_reads_back_clean(self):
        # The mechanism the whole assignment is about. Its sentence is the
        # one the pre-P1 build failed: the fin deforms only itself, and its
        # fabric draws where a body can see it.
        from bloodmap.readback import read_back, sentence

        curtains = _city_module("curtains")
        level = _tree()
        district = level.assembly("district")
        house = district.rect_room(
            "house", size=(16 * 1024, 16 * 1024),
            region_kwargs={"declared_zero_exit": True})
        level.set_start(house)
        frame = house.world_frame()
        stage = (frame.dx + 4 * 1024, frame.dy + 2 * 1024,
                 frame.dx + 12 * 1024, frame.dy + 6 * 1024)
        built = curtains.hang(house, district, stage, grade=0,
                              clear=8 * PLAYER)
        layout = level.compile()
        furnished = curtains.furnish(layout, built,
                                     stage_region=house.region_id, grade=0)
        self.assertEqual(furnished["markers"], 2)
        self.assertEqual(furnished["flagged"], built["spec"]["leaves"])
        compiled = layout.compile()
        disk = compiled.level.to_disk_map()
        sector = compiled.allocations[built["room"].region_id].sector_id
        result = read_back(disk, [sentence(
            "curtain", name="stage_curtain", sector=sector, sectors=[sector],
            sector_type=614, members=[],
            wiring={"channel": curtains.CH_CURTAIN,
                    "rx_id": curtains.CH_CURTAIN},
            drag={"closure": True},
            visibility={"tiles": [146], "walkable_band": True, "per_leaf": 1},
            state={"changes": True})], map_name="tree curtain")
        _assert_agrees(self, result)


# ---------------------------------------------------------------------------
# 6. the registry: no constructor without a read-back test or a reason
# ---------------------------------------------------------------------------

#: The modules whose public constructors owe this file a read-back test.
#: A module missing here is a module the rule does not bind -- the failure
#: mode the zoo's own COVERED_MODULES comment records.
READBACK_MODULES = ("bloodmap.mechanism", "bloodmap.doors", "bloodmap.glass",
                    "bloodmap.aperture", "bloodmap.street")

#: constructor -> the test method in this file that builds it and reads it
#: back. Named rather than discovered, so deleting the test fails the gate
#: instead of silently shrinking it.
COVERED: dict[str, str] = {
    "bloodmap.mechanism.curtain":
        "CurtainReadBack.test_a_one_leaf_curtain_reads_back_as_what_it_declared",
    "bloodmap.mechanism.planar_door":
        "PlanarDoorReadBack.test_a_planar_door_reads_back_as_the_pair_it_declared",
    "bloodmap.mechanism.turnstile":
        "TurnstileReadBack.test_a_turnstile_reads_back_as_the_rotor_it_declared",
    "bloodmap.mechanism.turnstile_pair":
        "TurnstileReadBack.test_a_counter_rotating_pair_reads_back_as_two_rotors",
    "bloodmap.mechanism.sliding_gate":
        "SlidingGateReadBack."
        "test_a_sliding_gate_reads_back_as_the_sprite_payload_it_declared",
    "bloodmap.mechanism.lift":
        "LiftReadBack.test_a_lift_reads_back_as_a_z_motion_that_changes_state",
    "bloodmap.doors.z_motion_door":
        "ZMotionDoorReadBack.test_a_z_motion_door_reads_back_as_a_door_that_opens",
    "bloodmap.glass.glaze":
        "GlazeReadBack.test_a_glazed_span_reads_back_with_its_panes_drawn",
    "bloodmap.aperture.pierce":
        "ApertureReadBack.test_a_pierced_opening_reads_back_with_its_jamb_drawn",
    "bloodmap.aperture.maskwall_panel":
        "ApertureReadBack."
        "test_a_maskwall_panel_reads_back_drawing_in_the_walkable_band",
}

#: A constructor with no read-back test needs a written reason. "Honest skip"
#: means the reason says what the function does INSTEAD of building, and
#: where the thing it feeds is read back.
SKIP: dict[str, str] = {
    # --- pure-facts functions: they compute, they do not build -------------
    "bloodmap.mechanism.curtain_spec":
        "the facts behind `curtain`, which the curtain read-back exercises; "
        "the tree placer in blood-city consumes the same dict, and "
        "CityTreeReadBack reads that side back",
    "bloodmap.mechanism.turnstile_spec":
        "the facts behind `turnstile`, exercised through the turnstile "
        "read-back and through blood-city's tree placer",
    "bloodmap.mechanism.leaf_repeat_for":
        "a sizing rule: how many repeats a leaf's travel wants. Nothing is "
        "built, and the number it returns is read back inside the gate "
        "constructs that consume it",
    "bloodmap.mechanism.blade_offset":
        "a sizing rule for a blade's tile offset; consumed by `turnstile`, "
        "whose read-back measures the blades it produced",
    "bloodmap.mechanism.shade_wave":
        "returns the XSECTOR fields of a shade wave. It builds no geometry; "
        "the wave is read back where it is used -- the stage light the "
        "curtain drives, in blood-city",
    # --- doors: mining and validating, not building ------------------------
    "bloodmap.doors.z_motion_endpoints":
        "the endpoints half of `z_motion_door`, whose read-back stands a "
        "region on the behavior it returns",
    "bloodmap.doors.xsector_direct_use":
        "the XSECTOR fields for a door you walk up to and use; carried by a "
        "region, and read back through the z-motion door test's wiring facet",
    "bloodmap.doors.xsector_remote_rx":
        "the XSECTOR fields for a door worked from a channel; the same",
    "bloodmap.doors.observe_motion_sector":
        "a READING of a built map -- one of the readers `readback` calls, "
        "not a thing that can be read back",
    "bloodmap.doors.mine_map":
        "mining over original maps; produces evidence, builds nothing",
    "bloodmap.doors.mine_directory":
        "mining over a corpus directory; produces evidence, builds nothing",
    "bloodmap.doors.query_door_precedents":
        "a query over mined doors; produces evidence, builds nothing",
    "bloodmap.doors.mine_key_signifiers":
        "mining over mined occurrences; produces evidence, builds nothing",
    "bloodmap.doors.mine_scenic_candidates":
        "mining over one map; produces evidence, builds nothing",
    "bloodmap.doors.authored_gate_audit":
        "a validator over a compiled layout: it is a reader, and a reader "
        "cannot be its own read-back",
    "bloodmap.doors.gate_audit_markdown":
        "formats the validator's output for a human; no geometry at all",
    "bloodmap.doors.door_affordance_report":
        "a reading over a compiled layout's doors; a reader, not a builder",
    # --- glass -------------------------------------------------------------
    "bloodmap.glass.attach_xwall":
        "the record-writing half of `glaze`; the glazed-span read-back goes "
        "through `glaze`, which is the only supported way to reach it",
    "bloodmap.glass.holder":
        "declares a pane's two sides as a mediation -- a CLAIM about the "
        "construct rather than geometry, so there is nothing to read back",
    "bloodmap.glass.pane_faults":
        "a check over a built map; the glazed-span read-back asserts it is "
        "empty, which is the reader being used rather than read back",
    "bloodmap.glass.breaks_to":
        "answers what a cstat becomes after the break, for reading a map's "
        "post-break topology; a rule, not a construction",
    "bloodmap.glass.recess_spec":
        "returns the recess outline and its two z values for a caller to "
        "carve into the tree; nothing in either build carves it yet, so there "
        "is no built geometry to read back -- named here so the gap stays "
        "countable rather than absent",
    "bloodmap.glass.recess_faults":
        "a reader over a built map, fixtured against E6M1's own recesses; a "
        "reading is used, not read back",
    "bloodmap.glass.panes_without_a_recess":
        "the same reading at map scale: every glazed wall with a room on "
        "both sides, which is a pane set flush in stonework",
    # --- aperture ----------------------------------------------------------
    "bloodmap.aperture.facade_of":
        "reads a facade plane off an existing map; a reader",
    "bloodmap.aperture.audit":
        "checks an authored aperture against the grammar; a validator",
    "bloodmap.aperture.tile_span_z":
        "a helper: how much z one tile repeat covers",
    "bloodmap.aperture.snap_leaf":
        "a helper: rounds a leaf's height to whole tile repeats",
    "bloodmap.aperture.framed_door":
        "PENDING a read-back: it dresses an already-built z-door and needs "
        "ART tile extents to choose the reveal, which this suite has no "
        "corpus-free source for. Named here so the gap is countable",
    "bloodmap.aperture.frame_z_doors":
        "PENDING a read-back: a whole-map pass over every z-door, and it "
        "takes `art_sizes`, which needs the ART reference this suite cannot "
        "assume. Named here so the gap is countable",
    "bloodmap.aperture.facade_run":
        "PENDING a read-back: the frontage constructor's sign placement "
        "needs ART extents. Its geometry is covered by tests/test_aperture.py "
        "and by the zoo's FACADE exhibit; the read-back is still owed",
    # --- street: derives, never builds -------------------------------------
    "bloodmap.street.carriageway":
        "derives the roadway rectangle of a run. It returns geometry for a "
        "caller to lay; blood-city's street_anatomy is that caller and the "
        "city build's read-back covers what it lays",
    "bloodmap.street.sidewalk_for":
        "a sizing rule behind `carriageway`; returns a width",
    "bloodmap.street.kerb_junction":
        "declares the kerb as a mediation: a claim about the seam, with no "
        "geometry of its own",
    "bloodmap.street.lamp_slots":
        "derives standing positions along a run; the slots are placed by the "
        "caller, and it is the placement that is read back",
    "bloodmap.street.porch_slots":
        "derives porches from a street's doors; the same, one level up",
    "bloodmap.street.wants_porch":
        "the porch threshold rule behind `porch_slots`; returns a bool",
    "bloodmap.street.runs_from_plan":
        "reads a city plan's circulation graph into runs; a reader over a "
        "plan, and it builds nothing",
}


def public_constructors():
    """Every public callable in the covered modules, by dotted name."""
    found = []
    for name in READBACK_MODULES:
        module = importlib.import_module(name)
        for attribute in dir(module):
            if attribute.startswith("_"):
                continue
            value = getattr(module, attribute)
            if not callable(value) or isinstance(value, type):
                continue
            if getattr(value, "__module__", None) != name:
                continue
            found.append(f"{name}.{attribute}")
    return sorted(found)


class ReadBackRegistry(unittest.TestCase):
    """The rule that keeps this file current.

    Promote a constructor into one of the five modules and this fails until
    it has a read-back test or a written reason -- exactly the way
    `tests/test_pattern_zoo.ConformanceTest` fails a constructor that has no
    exhibit in the zoo.
    """

    def test_every_public_constructor_has_a_read_back_test_or_a_reason(self):
        missing = [name for name in public_constructors()
                   if name not in COVERED and name not in SKIP]
        self.assertEqual(missing, [], (
            "these public constructors are built by nothing that reads them "
            "back. Add a test to tests/test_readback.py and name it in "
            "COVERED, or add an entry to SKIP saying what the function does "
            "instead of building: " + ", ".join(missing)))

    def test_every_skip_gives_an_honest_reason(self):
        for name, reason in SKIP.items():
            self.assertGreater(len(reason), 30, name)

    def test_neither_table_names_something_that_does_not_exist(self):
        known = set(public_constructors())
        stale = sorted(name for name in set(SKIP) | set(COVERED)
                       if name not in known)
        self.assertEqual(stale, [], f"stale entries: {stale}")

    def test_no_constructor_is_both_covered_and_skipped(self):
        both = sorted(set(COVERED) & set(SKIP))
        self.assertEqual(both, [], f"covered and skipped: {both}")

    def test_every_named_read_back_test_exists(self):
        # A COVERED entry naming a method that has been renamed away is a
        # gate that has quietly stopped running.
        import sys

        module = sys.modules[__name__]
        for constructor, dotted in COVERED.items():
            case, method = dotted.split(".", 1)
            klass = getattr(module, case, None)
            self.assertIsNotNone(klass, f"{constructor}: no class {case}")
            self.assertTrue(hasattr(klass, method),
                            f"{constructor}: {case} has no {method}")


# ---------------------------------------------------------------------------
# 7. fail-first: the gate has to catch known defects
# ---------------------------------------------------------------------------

#: The city map as committed BEFORE P1 rebuilt the stage curtain. Pulled out
#: of git so the anchor outlives the fix, the same way the rendering rule's
#: fail-first fixture does.
PRE_P1_CITY = "8c42701:projects/blood-city/level/blood-city-current.MAP"


def _blob(spec):
    """A committed map, straight out of the object store."""
    try:
        return subprocess.run(["git", "cat-file", "blob", spec.split(":", 1)[0]
                               + ":" + spec.split(":", 1)[1]],
                              cwd=ROOT, capture_output=True, check=True).stdout
    except Exception:
        return None


class ReadBackFailsFirst(unittest.TestCase):
    """Written to fail on defects that are known, and known to be real."""

    def test_the_pre_p1_city_curtain_fails_its_own_sentence(self):
        from bloodmap.format import parse_map
        from bloodmap.readback import read_back, sentence

        blob = _blob(PRE_P1_CITY)
        if not blob:
            self.skipTest(f"{PRE_P1_CITY} is not reachable in this checkout")
        disk = parse_map(blob)
        #: Sector 37 of that build: type 614, wearing tile 146 on walls
        #: 276-278, every one of its eight walls paired into the auditorium.
        curtain = [index for index, sector in enumerate(disk.sectors)
                   if int(sector.fields["type"]) == 614
                   and any(int(disk.walls[w].fields["picnum"]) == 146
                           for w in range(
                               int(sector.fields["wall_ptr"]),
                               int(sector.fields["wall_ptr"])
                               + int(sector.fields["wall_count"])))]
        self.assertTrue(curtain, "the pre-P1 city has no fabric-wearing 614")
        sector = curtain[0]
        #: The sentence the constructor claimed: a fin that deforms only
        #: itself, whose fabric a body can see.
        claim = sentence("curtain", name="stage_curtain", sector=sector,
                         sectors=[sector], sector_type=614, members=[],
                         visibility={"tiles": [146], "walkable_band": True,
                                     "per_leaf": 1})
        result = read_back(disk, [claim], map_name=PRE_P1_CITY)
        self.assertFalse(result.agrees, result.report())
        facets = {d.facet for d in result.differences}
        #: Both halves of the defect, and the second is the one nobody could
        #: see: the fin dragged the house AND the fabric drew nowhere.
        self.assertIn("members", facets, result.report())
        self.assertTrue(
            any(f.startswith("visibility.146") for f in facets),
            result.report())

    def test_a_link_receiver_that_cannot_respond_is_a_difference(self):
        # `sectorfx.cpp:161-166` scales a shade wave's amplitude by busy only
        # when shadeAlways is 0. A receiver with shadeAlways set is deaf to
        # the Link that drives it: every field is legal and the light never
        # moves. The sentence says the mechanism changes state; the reading
        # says nothing measurable does.
        from bloodmap.readback import read_back, sentence

        layout = _layout()
        layout.add_region(
            "stage", _rect(1024, 3072, 3072, 5120), floor_z=0,
            ceiling_z=-33280, declared_zero_exit=True, wall_picnum=200,
            floor_picnum=201, ceiling_picnum=202,
            sector_behavior={"rx_id": 341, "amplitude": -24,
                             "shade_wave": 7, "shade_frequency": 5,
                             "shade_always": 1, "shade_floor": 1,
                             "shade_walls": 1})
        layout.add_connection("c0", "room", "stage",
                              a1=(1024, 3072), a2=(3072, 3072), min_width=384)
        disk, sectors, _ = _built(layout)
        result = read_back(disk, [sentence(
            "shade_link", name="stage_light", sector=sectors["stage"],
            sectors=[sectors["stage"]],
            wiring={"rx_id": 341}, state={"changes": True})],
            map_name="deaf link receiver")
        self.assertFalse(result.agrees, result.report())
        self.assertIn("state.changes", [d.facet for d in result.differences])

    def test_a_door_with_a_channel_and_no_route_is_a_difference(self):
        # The other half of the mis-wiring: a door that listens on a channel
        # nothing transmits on. `conditional.route_edges` finds no gated
        # route, so the sentence's `route` claim has nothing to satisfy it.
        from bloodmap.doors import z_motion_door
        from bloodmap.readback import read_back, sentence

        layout = _layout()
        layout.add_region("door", _rect(1024, 3072, 3072, 3584),
                          floor_z=0, ceiling_z=0, type=600,
                          sector_behavior=z_motion_door(0, -PLAYER * 2,
                                                        interaction="remote",
                                                        rx_id=777),
                          declared_zero_exit=True, wall_picnum=200,
                          floor_picnum=201, ceiling_picnum=202)
        layout.add_connection("c0", "room", "door",
                              a1=(1024, 3072), a2=(3072, 3072), min_width=384)
        layout.add_region("back", _rect(1024, 3584, 3072, 5632),
                          floor_z=0, ceiling_z=-33280, declared_zero_exit=True,
                          wall_picnum=200, floor_picnum=201,
                          ceiling_picnum=202)
        layout.add_connection("c1", "door", "back",
                              a1=(1024, 3584), a2=(3072, 3584), min_width=384)
        disk, sectors, _ = _built(layout)
        result = read_back(disk, [sentence(
            "z_motion_door", name="orphan", sector=sectors["door"],
            sectors=[sectors["door"]], sector_type=600,
            wiring={"rx_id": 777, "route": "switch"})],
            map_name="door with no route")
        self.assertFalse(result.agrees, result.report())
        self.assertIn("wiring.route", [d.facet for d in result.differences])


class DerivedSentences(unittest.TestCase):
    """`sentences_from_layout`: the declared side, read off the source.

    This is what both build scripts pass to `read_back`. It matters that it
    is DERIVED and not a second hand-written manifest: a manifest drifts from
    the source it describes, and then the gate is comparing two stale things.
    """

    def _curtain_layout(self):
        from bloodmap.mechanism import curtain

        layout = _layout()
        curtain(layout, "cur", opening=(1024, 3072, 3072, 3328), axis="x",
                channel=200, leaf_region="leaf", floor_z=0,
                ceiling_z=-33280, frame_picnum=200, declared_zero_exit=True)
        layout.declare_motion("leaf", [])
        layout.add_connection("c0", "room", "leaf",
                              a1=(1024, 3072), a2=(3072, 3072), min_width=384)
        layout.add_region("back", _rect(1024, 3328, 3072, 5376),
                          floor_z=0, ceiling_z=-33280, declared_zero_exit=True,
                          wall_picnum=200, floor_picnum=201,
                          ceiling_picnum=202)
        layout.add_connection("c1", "leaf", "back",
                              a1=(1024, 3328), a2=(3072, 3328), min_width=384)
        return layout

    def test_a_curtain_is_named_by_what_it_wears_not_by_its_region_id(self):
        # The zoo's sweep learned this the hard way: routing the curtain
        # check on a payload SHAPE stopped running the moment the
        # constructor was corrected, and the zoo reported 13/13 conforming
        # because the curtain was never asked. A tile does not change when
        # the topology does.
        from bloodmap.readback import sentences_from_layout

        layout = self._curtain_layout()
        compiled = layout.compile()
        claims = {c["name"]: c for c in sentences_from_layout(compiled,
                                                              layout=layout)}
        self.assertIn("leaf", claims)
        self.assertEqual(claims["leaf"]["construct"], "curtain")
        self.assertEqual(claims["leaf"]["visibility"]["tiles"], [146])
        self.assertTrue(claims["leaf"]["drag"]["closure"])

    def test_a_declared_motion_set_becomes_the_members_claim(self):
        from bloodmap.readback import sentences_from_layout

        layout = self._curtain_layout()
        compiled = layout.compile()
        claims = {c["name"]: c for c in sentences_from_layout(compiled,
                                                              layout=layout)}
        #: `declare_motion("leaf", [])` says the fin deforms only itself.
        self.assertEqual(claims["leaf"]["members"], [])

    def test_a_region_that_declared_nothing_makes_no_claim(self):
        # A claim nobody made must never become a difference, or the gate
        # starts inventing intent and every honest build fails it.
        from bloodmap.readback import sentences_from_layout

        layout = self._curtain_layout()
        compiled = layout.compile()
        names = {c["name"] for c in sentences_from_layout(compiled,
                                                          layout=layout)}
        self.assertNotIn("room", names)
        self.assertNotIn("back", names)

    def test_the_derived_gate_agrees_with_the_map_it_derived_from(self):
        from bloodmap.readback import read_back, sentences_from_layout

        layout = self._curtain_layout()
        compiled = layout.compile()
        disk = compiled.level.to_disk_map()
        result = read_back(disk,
                           sentences_from_layout(compiled, layout=layout),
                           map_name="derived")
        _assert_agrees(self, result)

    def test_a_layout_that_did_not_compile_here_is_refused_rather_than_guessed(self):
        from bloodmap.readback import SentenceError, sentences_from_layout

        class Bare:
            allocations: dict = {}
            layout = None

        with self.assertRaises(SentenceError):
            sentences_from_layout(Bare())


class LostTilesAsDifferences(unittest.TestCase):
    """The rendering rule's violations, restated in the diff's vocabulary."""

    def test_a_lost_tile_reads_as_a_visibility_difference(self):
        from bloodmap.readback import lost_tiles_as_differences

        class Violation:
            location = "map E1M1 tile 146"
            detail = "authored on 5 walls, drawn on no band"

        class Result:
            violations = [Violation()]

        found = lost_tiles_as_differences(Result())
        self.assertEqual(len(found), 1)
        self.assertEqual(found[0].facet, "visibility.drawn")
        self.assertIn("tile 146", str(found[0]))
        self.assertIn("wall-tile-is-drawn-somewhere", found[0].reader)

    def test_nothing_lost_is_no_differences(self):
        from bloodmap.readback import lost_tiles_as_differences

        class Result:
            violations = []

        self.assertEqual(lost_tiles_as_differences(Result()), [])


class SentenceShape(unittest.TestCase):
    """The declared side is a documented dict, and it refuses nonsense."""

    def test_an_unknown_claim_is_refused_rather_than_dropped(self):
        from bloodmap.readback import SentenceError, sentence

        with self.assertRaises(SentenceError):
            sentence("curtain", sector=1, visibilty={"tiles": [146]})

    def test_a_claim_not_made_is_never_a_difference(self):
        from bloodmap.readback import read_back, sentence

        layout = _layout()
        disk, sectors, _ = _built(layout)
        result = read_back(disk, [sentence("room", sector=sectors["room"])],
                           map_name="a sentence that claims nothing")
        self.assertTrue(result.agrees, result.report())

    def test_a_sentence_with_no_sector_reports_itself_unmeasured(self):
        # The standing warning: a detector that measures nothing must say so.
        from bloodmap.readback import read_back, sentence

        layout = _layout()
        disk, _sectors, _ = _built(layout)
        result = read_back(disk, [sentence("curtain", name="nowhere")],
                           map_name="unplaced sentence")
        self.assertTrue(result.agrees)
        self.assertEqual(len(result.unmeasured), 1, result.report())


if __name__ == "__main__":
    unittest.main()
