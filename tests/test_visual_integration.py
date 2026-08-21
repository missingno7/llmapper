"""Observation tests that need the built observer, and optionally Blood data.

These skip themselves rather than fail when the fork has not been built or the
commercial ART is absent, so the unit suite stays runnable anywhere.  Build the
observer with::

    mingw32-make -C xmapedit/src_blood/observe
"""

from __future__ import annotations

import json
import shutil
import tempfile
import unittest
from pathlib import Path

from bloodmap.format import write_map
from bloodmap.levelprog import LevelProgram, Style
from bloodmap.visual import (
    ObservationRequest,
    SourceMap,
    Viewpoint,
    default_binary,
    join_view,
    run_observation,
)

U = 384
PH = 0x1600

ROOT = Path(__file__).resolve().parent.parent
RESOURCE_DIR = ROOT / "reference" / "blood"
E2M3 = ROOT / "maps" / "blood" / "E2M3.MAP"
BLOOD_RFF = RESOURCE_DIR / "BLOOD.RFF"
#: The palette NBlood displays, shipped loose alongside the archive.
REFERENCE_PAL = RESOURCE_DIR / "xmapedit" / "palettes" / "import" / "BLOOD.PAL"

HAVE_BINARY = default_binary().exists()
HAVE_ART = (RESOURCE_DIR / "tiles000.art").exists()


def fixture_program() -> LevelProgram:
    """Two rooms and a stair, with tiles that exist in every Blood install."""
    program = LevelProgram(
        "obsfix", name="obsfix",
        style=Style(wall_picnum=5, floor_picnum=294, ceiling_picnum=454,
                    floor_z=8192, clear_height=8 * PH,
                    wall_shade=16, floor_shade=18, ceiling_shade=14),
    )
    house = program.assembly("house")
    hall = house.rect_room("hall", size=(12 * U, 10 * U))
    side = house.rect_room("side", size=(8 * U, 8 * U))
    side.place_against("west", hall.face("east", at=0.5, width=8 * U))
    program.connect(hall.face("east", at=0.5, width=8 * U),
                    side.face("west", at=0.5, width=8 * U),
                    connection_id="connection:hall_side")
    program.set_start(hall)
    return program


@unittest.skipUnless(HAVE_BINARY, "xmapedit-observe is not built")
@unittest.skipUnless(HAVE_ART, "no Blood ART under reference/blood")
class ObserverTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = Path(tempfile.mkdtemp(prefix="llmapper-obs-"))
        cls.program = fixture_program()
        cls.compiled = cls.program.compile().compile()
        cls.level = cls.compiled.level
        cls.map_path = cls.tmp / "fixture.MAP"
        write_map(cls.level.to_disk_map(), cls.map_path)
        cls.source_map = SourceMap.from_level_program(cls.program, cls.compiled)
        cls.hall_sector = min(cls.source_map.allocations["obsfix/house/hall"].sectors)

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.tmp, ignore_errors=True)

    def _request(self, views, out="out", **kwargs):
        return ObservationRequest(
            map_path=str(self.map_path), output_dir=str(self.tmp / out),
            resource_dir=str(RESOURCE_DIR), viewpoints=tuple(views), **kwargs,
        )

    def _centre_pose(self, view_id="centre", **kwargs):
        from bloodmap.viewplan import eye_z, interior_point

        point = interior_point(self.level, self.hall_sector)
        return Viewpoint(view_id, point[0], point[1],
                         eye_z(self.level, self.hall_sector),
                         sector=self.hall_sector, node="obsfix/house/hall", **kwargs)

    def test_many_views_come_back_from_one_batch(self):
        views = [self._centre_pose(f"a{i}", angle=i * 256) for i in range(8)]
        manifest = run_observation(self._request(views))
        self.assertEqual(len(manifest.views), 8)
        self.assertEqual(sorted(manifest.view_ids), sorted(v.view_id for v in views))

    def test_visible_native_ids_are_valid_for_this_map(self):
        manifest = run_observation(self._request([self._centre_pose()]))
        view = manifest.view("centre")
        self.assertEqual(view["status"], "ok")
        self.assertTrue(view["surfaces"])
        for surface in view["surfaces"]:
            self.assertLess(surface["sector"], len(self.level.sectors))
            if "wall" in surface:
                self.assertLess(surface["wall"], len(self.level.walls))
            if "sprite" in surface:
                self.assertLess(surface["sprite"], len(self.level.sprites))

    def test_semantic_join_resolves_through_the_allocations(self):
        manifest = run_observation(self._request([self._centre_pose()]))
        join = join_view(manifest.view("centre"), self.source_map, level=self.level)
        nodes = {record["node"] for record in join["visible"]}
        self.assertIn("obsfix/house/hall", nodes)
        self.assertFalse([n for n in nodes if n.startswith("unmapped:")])

    def test_an_invalid_pose_is_refused_with_a_reason_not_corrected(self):
        floor = int(self.level.sectors[self.hall_sector]["fields"]["floor_z"])
        bad = Viewpoint("sunk", 0, 0, floor + 4096, sector=self.hall_sector)
        outside = Viewpoint("nowhere", 1 << 20, 1 << 20, 0)
        manifest = run_observation(self._request([bad, outside, self._centre_pose()]))
        self.assertEqual(manifest.view("sunk")["status"], "invalid_pose")
        self.assertEqual(manifest.view("nowhere")["status"], "invalid_pose")
        self.assertTrue(manifest.view("sunk")["reason"])
        self.assertEqual(manifest.view("centre")["status"], "ok")

    def test_screenshots_can_be_switched_off_entirely(self):
        request = self._request([self._centre_pose()], out="json-only", screenshots=False)
        manifest = run_observation(request)
        self.assertIsNone(manifest.view("centre")["screenshot"])
        self.assertFalse((Path(request.output_dir) / "frames").exists())

    def test_a_requested_frame_uses_the_same_pose(self):
        request = self._request([self._centre_pose()], out="with-frame").with_screenshots(["centre"])
        manifest = run_observation(request)
        view = manifest.view("centre")
        self.assertEqual(view["screenshot"], "frames/centre.png")
        frame = Path(request.output_dir) / view["screenshot"]
        self.assertTrue(frame.exists())
        self.assertEqual(frame.read_bytes()[:8], bytes([137, 80, 78, 71, 13, 10, 26, 10]))
        wire = next(v for v in request.to_dict()["views"] if v["id"] == "centre")
        for key in ("x", "y", "z", "angle", "horiz"):
            self.assertEqual(view["camera"][key], wire[key])

    def test_identical_requests_produce_identical_manifests(self):
        views = [self._centre_pose(f"a{i}", angle=i * 512) for i in range(4)]
        first = run_observation(self._request(views))
        second = run_observation(self._request(views))

        def stable(manifest):
            # render_ms is wall clock, and the only thing in a manifest that is.
            return [{k: v for k, v in view.items() if k != "render_ms"}
                    for view in manifest.data["views"]]

        self.assertEqual(json.dumps(stable(first)), json.dumps(stable(second)))

    def test_the_summary_carries_no_raw_buffers(self):
        from bloodmap.visual import compact_summary

        manifest = run_observation(self._request([self._centre_pose()]))
        view = manifest.view("centre")
        join = join_view(view, self.source_map, level=self.level)
        text = compact_summary(view, join)
        self.assertLess(len(text), 2000)
        self.assertNotIn("pixels_by_kind", text)

    def test_occlusion_is_measured_not_assumed(self):
        """Facing the side room, the hall wall behind the camera paints nothing."""
        manifest = run_observation(self._request([
            self._centre_pose("east", angle=0), self._centre_pose("west", angle=1024),
        ]))
        east = manifest.view("east")
        west = manifest.view("west")
        self.assertNotEqual(
            {s.get("wall") for s in east["surfaces"] if "wall" in s},
            {s.get("wall") for s in west["surfaces"] if "wall" in s},
        )

    def test_the_limitations_are_always_stated(self):
        manifest = run_observation(self._request([self._centre_pose()]))
        joined = " ".join(manifest.limitations).lower()
        self.assertIn("static world state", joined)
        self.assertIn("editor renderer", joined)


def _png_chunks(path: Path):
    import struct

    data = path.read_bytes()
    offset = 8
    while offset < len(data):
        length, = struct.unpack(">I", data[offset:offset + 4])
        yield data[offset + 4:offset + 8], data[offset + 8:offset + 8 + length]
        offset += 12 + length


def _rff_resource(archive: Path, kind: bytes, name: bytes) -> bytes:
    """Read one resource, directory decryption and payload decryption included."""
    import struct

    data = bytearray(archive.read_bytes())
    version, = struct.unpack_from("<H", data, 4)
    directory, count = struct.unpack_from("<II", data, 8)
    key = (directory + (version & 0xFF) * directory) & 0xFFFF
    for index in range(count * 48):
        data[directory + index] ^= (key >> 1) & 0xFF
        key = (key + 1) & 0xFFFF
    for index in range(count):
        entry = data[directory + index * 48: directory + (index + 1) * 48]
        if bytes(entry[33:36]) != kind or not bytes(entry[36:44]).startswith(name):
            continue
        offset, size = struct.unpack_from("<II", entry, 16)
        payload = bytearray(data[offset:offset + size])
        if entry[32] & 0x10:
            for k in range(min(256, size)):
                payload[k] ^= (k >> 1) & 0xFF
        return bytes(payload)
    raise AssertionError(f"{kind!r}/{name!r} is not in {archive}")


@unittest.skipUnless(BLOOD_RFF.exists(), "BLOOD.RFF is absent")
class ResourceEncryptionTests(unittest.TestCase):
    """Why bit 0x10 means encrypted, checked against the data rather than asserted.

    This is the fact the observer's colour depends on, and it is worth a test
    because the wrong reading of it produces a frame that still looks like
    Blood.
    """

    def test_shade_zero_of_the_normal_plu_is_the_identity_map(self):
        plu = _rff_resource(BLOOD_RFF, b"PLU", b"NORMAL")
        self.assertEqual(len(plu), 64 * 256)
        self.assertEqual(plu[:256], bytes(range(256)))

    @unittest.skipUnless(REFERENCE_PAL.exists(), "the reference palette is absent")
    def test_the_decrypted_palette_is_the_one_the_game_displays(self):
        self.assertEqual(_rff_resource(BLOOD_RFF, b"PAL", b"BLOOD"),
                         REFERENCE_PAL.read_bytes())


@unittest.skipUnless(HAVE_BINARY, "xmapedit-observe is not built")
@unittest.skipUnless(E2M3.exists() and HAVE_ART, "E2M3.MAP or Blood ART is absent")
class OriginalMapTests(unittest.TestCase):
    def test_an_original_loads_and_renders_from_its_own_start(self):
        with tempfile.TemporaryDirectory() as tmp:
            request = ObservationRequest(
                map_path=str(E2M3), output_dir=str(Path(tmp) / "out"),
                resource_dir=str(RESOURCE_DIR),
                viewpoints=(Viewpoint("start", 55455, 40619, -11264, angle=1025, sector=310),),
            )
            manifest = run_observation(request)
            self.assertEqual(manifest.data["map"]["sectors"], 340)
            self.assertEqual(manifest.data["map"]["walls"], 2808)
            self.assertTrue(manifest.data["renderer"]["palette_authentic"])
            view = manifest.view("start")
            self.assertEqual(view["status"], "ok")
            self.assertGreater(view["frame"]["painted"], 0)

    @unittest.skipUnless(REFERENCE_PAL.exists(), "the reference palette is absent")
    def test_a_rendered_frame_uses_the_palette_the_game_displays(self):
        """Full eight-bit Blood colour, not the engine's six-bit VGA copy."""
        with tempfile.TemporaryDirectory() as tmp:
            request = ObservationRequest(
                map_path=str(E2M3), output_dir=str(Path(tmp) / "out"),
                resource_dir=str(RESOURCE_DIR),
                viewpoints=(Viewpoint("start", 55455, 40619, -11264,
                                      angle=1025, sector=310),),
            ).with_screenshots(["start"])
            manifest = run_observation(request)
            frame = Path(request.output_dir) / manifest.view("start")["screenshot"]
            palette = next(payload for tag, payload in _png_chunks(frame) if tag == b"PLTE")
            self.assertEqual(palette, REFERENCE_PAL.read_bytes())

    def test_frames_default_to_a_size_worth_looking_at(self):
        """320x200 is Mode 13h to this engine, and too coarse to read a room."""
        import struct

        with tempfile.TemporaryDirectory() as tmp:
            request = ObservationRequest(
                map_path=str(E2M3), output_dir=str(Path(tmp) / "out"),
                resource_dir=str(RESOURCE_DIR),
                viewpoints=(Viewpoint("start", 55455, 40619, -11264,
                                      angle=1025, sector=310),),
            ).with_screenshots(["start"])
            self.assertEqual((request.width, request.height), (640, 480))
            manifest = run_observation(request)
            frame = Path(request.output_dir) / manifest.view("start")["screenshot"]
            header = next(payload for tag, payload in _png_chunks(frame) if tag == b"IHDR")
            width, height = struct.unpack(">II", header[:8])
            self.assertEqual((width, height), (640, 480))
            self.assertEqual(manifest.view("start")["frame"]["pixels"], 640 * 480)


if __name__ == "__main__":
    unittest.main()
