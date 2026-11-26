"""The finishing sequence takes a layout to a map in one order, measures what it did, and writes nothing a gate refuses."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from bloodmap import finish, switches, wiring
from bloodmap.format import encode_map, read_map
from bloodmap.levelprog import LevelProgram, Style
from bloodmap.light_stage import Rule
from bloodmap.player_space import PLAYER_PROFILES

BODY = PLAYER_PROFILES["blood"]
U, PH = BODY.body_width, BODY.standing_height


def two_rooms():
    """A hall and a store joined by an opening, a switch that ends the level, one wire."""
    level = LevelProgram("pair", name="pair", style=Style(wall_picnum=180, floor_picnum=292, ceiling_picnum=385, wall_shade=8,
                                                           floor_shade=12, ceiling_shade=10, floor_z=0, clear_height=2 * PH))
    hall = level.rect_room("hall", size=(12 * U, 10 * U))
    store = level.rect_room("store", size=(8 * U, 8 * U))
    # the whole of the store's west side opens on the hall: two rooms that share an edge are joined along all of it
    store.place_against("west", hall.face("east", at=0.5, width=8 * U))
    level.connect(hall.face("east", at=0.5, width=8 * U), store.face("west"))
    level.set_start(hall, local=(0.3, 0.5))
    layout = level.compile()
    circuit = wiring.Circuit(layout)
    (x0, y0), (x1, y1) = [store.world_frame().apply(p) for p in store.local_edge("east")]
    way_out = dict(switches.exit_switch())
    way_out.pop("behavior")
    layout.place_on_wall("exit_switch", store.region_id, a1=(x0, y0), a2=(x1, y1), t=0.5, status=0,
                         height_player_heights=way_out.pop("height_player_heights"), **way_out)
    circuit.wire("way-out", "pushing the switch in the store ends the level", engine="kChannelLevelExitNormal").when(
        wiring.placement("exit_switch"), "push", command=1)
    circuit.wire("spare", "a wire nothing declares an end of")
    return layout, circuit


def quiet(_line: str) -> None:
    pass


class Finish(unittest.TestCase):
    def test_a_layout_becomes_a_map_a_tags_file_and_a_manifest(self):
        layout, circuit = two_rooms()
        out = Path(tempfile.mkdtemp()) / "level" / "pair.MAP"
        made = finish.finish(layout, out, circuit=circuit, light=lambda region: Rule("ceiling", 795, 3072), say=quiet)
        self.assertTrue(made.ok, made.refused)
        self.assertEqual([s["name"] for s in made.manifest["stages"]], ["compile", "alignment", "gates", "light", "write"])
        self.assertEqual(encode_map(read_map(out)), encode_map(made.disk))
        self.assertTrue(out.with_suffix(".tags.json").exists())
        for measured in ("rules", "swept", "readback", "sprite_fit", "tile_contexts", "wires", "light_stage", "tidy", "size"):
            self.assertIn(measured, made.manifest)
        self.assertEqual(made.manifest["wires"]["idle"], ["spare"])
        self.assertTrue(made.manifest["wires"]["agrees"])
        self.assertEqual(made.manifest["size"]["sectors"], len(made.disk.sectors))
        finish.write_manifest(made, out.parent.parent / "reports" / "build-manifest.json")
        kept = json.loads((out.parent.parent / "reports" / "build-manifest.json").read_text("utf-8"))
        self.assertEqual(kept["size"], made.manifest["size"])

    def test_the_same_layout_finishes_to_the_same_bytes(self):
        first = finish.finish(*two_rooms()[:1], circuit=two_rooms()[1], say=quiet)
        again = [finish.finish(layout, circuit=circuit, say=quiet) for layout, circuit in (two_rooms(), two_rooms())]
        self.assertTrue(first.ok)
        self.assertEqual(encode_map(again[0].disk), encode_map(again[1].disk))

    def test_without_a_light_rule_the_layouts_shades_stand_and_nothing_is_cut(self):
        layout, circuit = two_rooms()
        made = finish.finish(layout, circuit=circuit, say=quiet)
        self.assertNotIn("light_stage", made.manifest)
        self.assertEqual([s["name"] for s in made.manifest["stages"]], ["compile", "alignment", "gates", "write"])
        self.assertEqual(len(made.disk.sectors), 2)

    def test_the_levels_own_passes_run_where_the_order_puts_them(self):
        seen = []
        layout, circuit = two_rooms()
        made = finish.finish(layout, circuit=circuit, say=quiet,
                             on_level=lambda compiled: seen.append("level") or {"rooms": len(compiled.allocations)},
                             on_disk=lambda disk, compiled: seen.append("disk") or {"walls": len(disk.walls)})
        self.assertEqual(seen, ["level", "disk"])
        self.assertEqual(made.manifest["level"], {"rooms": 2})
        self.assertEqual([s["name"] for s in made.manifest["stages"]], ["compile", "level", "alignment", "disk", "gates", "write"])

    def test_a_refused_map_is_not_written(self):
        layout, circuit = two_rooms()
        out = Path(tempfile.mkdtemp()) / "pair.MAP"
        real = finish.gates

        def refusing(*args, **kwargs):
            report = real(*args, **kwargs)
            report["refused"].append("a mechanism breaks geometry it drags: sector 1")
            return report

        with mock.patch.object(finish, "gates", refusing):
            made = finish.finish(layout, out, circuit=circuit, light=lambda region: Rule("ceiling", 795, 3072), say=quiet)
        self.assertFalse(made.ok)
        self.assertEqual(made.refused, ["a mechanism breaks geometry it drags: sector 1"])
        self.assertFalse(out.exists())
        self.assertNotIn("light_stage", made.manifest)

    def test_the_gates_can_be_asked_alone(self):
        layout, circuit = two_rooms()
        made = finish.finish(layout, circuit=circuit, say=quiet)
        report = finish.gates(made.disk, made.compiled, circuit=circuit)
        self.assertEqual(report["refused"], [])
        self.assertEqual(report["rules"]["by_severity"].get("error", 0), 0)
        self.assertEqual(report["sprite_fit"]["rates"]["sunk"], 0.0)


class WireTable(unittest.TestCase):
    def test_a_plan_numbers_its_wires_in_order_and_the_engines_take_none(self):
        circuit = wiring.Circuit.from_plan((("door", "the lever opens the door"), ("lamp", "the switch lights the lamp")),
                                           (("out", "the emblem ends the level", "kChannelLevelExitNormal"),))
        self.assertEqual([circuit.named("door").channel, circuit.named("lamp").channel], [100, 101])
        self.assertEqual(circuit.named("out").engine, "kChannelLevelExitNormal")
        with self.assertRaises(wiring.WireError):
            circuit.named("nothing")
        circuit.named("door").when(wiring.placement("lever"), "push")
        self.assertEqual(circuit.drop_idle(), ["lamp", "out"])
        self.assertEqual([wire.name for wire in circuit.wires], ["door"])


if __name__ == "__main__":
    unittest.main()
