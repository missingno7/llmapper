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
        self.assertEqual(made.manifest["wires"]["idle"], [])
        self.assertTrue(made.manifest["wires"]["agrees"])
        self.assertEqual(made.manifest["size"]["sectors"], len(made.disk.sectors))
        finish.write_manifest(made, out.parent.parent / "reports" / "build-manifest.json")
        kept = json.loads((out.parent.parent / "reports" / "build-manifest.json").read_text("utf-8"))
        self.assertEqual(kept["size"], made.manifest["size"])

    def test_the_same_layout_finishes_to_the_same_bytes(self):
        again = [finish.finish(layout, circuit=circuit, say=quiet) for layout, circuit in (two_rooms(), two_rooms())]
        self.assertTrue(again[0].ok, again[0].refused)
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

    def test_a_wire_with_no_end_is_a_mistake_unless_it_is_a_row_of_a_plan(self):
        layout, circuit = two_rooms()
        circuit.wire("spare", "a wire nothing declares an end of")
        with self.assertRaises(wiring.WireError):
            finish.finish(layout, circuit=circuit, say=quiet)
        layout, _circuit = two_rooms()
        planned = wiring.Circuit.from_plan((("later", "a door that is not built yet"),),
                                           (("way-out", "the switch ends the level", "kChannelLevelExitNormal"),))
        planned.named("way-out").when(wiring.placement("exit_switch"), "push", command=1)
        made = finish.finish(layout, circuit=planned.bind(layout), say=quiet)
        self.assertTrue(made.ok, made.refused)
        self.assertEqual(made.manifest["wires"]["idle"], ["later"])

    def test_a_rule_error_or_wiring_that_differs_refuses_the_map(self):
        from types import SimpleNamespace

        layout, circuit = two_rooms()
        out = Path(tempfile.mkdtemp()) / "pair.MAP"
        bad = SimpleNamespace(severity="error", code="made-up-rule", location="sector[0]", message="for the test")
        with mock.patch("bloodmap.rules.evaluate", lambda disk: [bad]):
            made = finish.finish(layout, out, circuit=circuit, say=quiet)
        self.assertEqual(made.refused, ["rule made-up-rule at sector[0]: for the test"])
        self.assertFalse(out.exists())
        layout, circuit = two_rooms()
        with mock.patch.object(type(circuit), "read_back", lambda self, compiled, disk: {
                "agrees": False, "wires": [{"name": "way-out", "faults": ["no sender on the map"]}], "undeclared": [], "silent": []}):
            made = finish.finish(layout, out, circuit=circuit, say=quiet)
        self.assertEqual(made.refused, ["wire way-out: no sender on the map"])
        self.assertFalse(out.exists())

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


class Session(unittest.TestCase):
    """A level with passes of its own drives the stages one by one, and its passes go between them."""

    def drive(self, layout, circuit, *, between=None, before_merge=None):
        rule = lambda region: Rule("ceiling", 795, 3072)  # noqa: E731
        made = finish.Finish(layout, circuit=circuit, say=quiet)
        made.wire()
        made.compile(lit=True)
        if between is not None:
            between(made)
        made.align()
        made.to_disk()
        self.assertTrue(made.hold(map_name="pair.MAP"), made.refused)
        self.assertTrue(made.cut_overlays())
        self.assertTrue(made.light(rule, before_merge=before_merge))
        made.tidy()
        return made

    def test_driven_stage_by_stage_it_makes_the_map_finish_makes(self):
        layout, circuit = two_rooms()
        whole = finish.finish(layout, circuit=circuit, light=lambda region: Rule("ceiling", 795, 3072), say=quiet)
        layout, circuit = two_rooms()
        driven = self.drive(layout, circuit)
        self.assertEqual(encode_map(driven.disk), encode_map(whole.disk))
        self.assertEqual(driven.tags(), {})

    def test_a_record_the_level_claims_before_align_is_not_reframed(self):
        layout, circuit = two_rooms()
        claimed = {}

        def glaze(made):
            # a level's own pass (a pane of glass) claims a wall's texture fields before the frames are laid
            wall = made.compiled.level.walls[0]
            wall["fields"]["x_panning"] = 7
            made.records.claim(0, "insert:glass")
            claimed["wall"] = wall

        made = self.drive(layout, circuit, between=glaze)
        self.assertEqual(int(made.disk.walls[0].fields["x_panning"]), 7)
        self.assertEqual(made.records.owner_of(0), "insert:glass")

    def test_the_level_works_on_the_lit_map_before_its_pieces_join(self):
        layout, circuit = two_rooms()
        seen = []
        made = self.drive(layout, circuit, before_merge=lambda disk, compiled: seen.append(len(disk.sectors)) or "evened")
        self.assertEqual(len(seen), 1)
        self.assertEqual(made.manifest["light_stage"]["before_merge"], "evened")

    def test_a_refused_session_writes_nothing(self):
        layout, circuit = two_rooms()
        made = finish.Finish(layout, circuit=circuit, say=quiet)
        made.compile(lit=False)
        made.align()
        made.to_disk()
        self.assertTrue(made.hold())
        made.refused.append("a test says no")
        for stage in (made.cut_overlays, made.tidy, lambda: made.write(Path(tempfile.mkdtemp()) / "no.MAP")):
            with self.assertRaises(finish.FinishError):
                stage()

    def test_the_stages_keep_their_order(self):
        layout, circuit = two_rooms()
        made = finish.Finish(layout, circuit=circuit, say=quiet)
        with self.assertRaises(finish.FinishError):
            made.align()                                # before compile
        made.compile(lit=False)
        made.to_disk()
        with self.assertRaises(finish.FinishError):
            made.align()                                # after to_disk: nothing it did would reach the map
        out = Path(tempfile.mkdtemp()) / "ungated.MAP"
        for stage in (made.cut_overlays, made.tidy, lambda: made.write(out)):
            with self.assertRaises(finish.FinishError):
                stage()                                 # nothing is cut, tidied or written that was not held
        self.assertFalse(out.exists())
        self.assertTrue(made.hold())
        made.tidy()
        made.write(out)
        self.assertTrue(out.exists())


if __name__ == "__main__":
    unittest.main()
