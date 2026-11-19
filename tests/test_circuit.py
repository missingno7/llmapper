"""A level says what its wiring is for, and the finished map is held to it.

The owner, 2026-11-19: "these mechanics things are like a programming
language of the level, same things are used for different purposes according
to what author wants." Until then a wire was a channel number typed into two
modules, and the city had one on channel 30, which is the engine's. These
hold the declared layer: a wire states its purpose, the circuit numbers it,
the engine's three limits are refused by name, and the built map is read
back with the same reader that reads the campaign.
"""

from __future__ import annotations

import unittest

from bloodmap import wiring
from bloodmap.planar_layout import PlanarLayout
from bloodmap.player_space import PLAYER_PROFILES
from bloodmap.switches import pressed_switch

U = 1024
PH = PLAYER_PROFILES["blood"].standing_height
FLOOR = 0
HALL, YARD, VAULT = "region:hall", "region:yard", "region:vault"


def _p(x, y):
    return (x * U, y * U)


def _r(x0, y0, x1, y1):
    return [_p(x0, y0), _p(x1, y0), _p(x1, y1), _p(x0, y1)]


def _layout() -> PlanarLayout:
    """A hall with a lever, a yard beyond it, and a vault off the yard."""
    layout = PlanarLayout(name="circuit", visibility=800)
    layout.add_region(HALL, _r(0, 3, 12, 7), role="start",
                      ceiling_z=FLOOR - 4 * PH, floor_z=FLOOR)
    layout.add_region(YARD, _r(12, -6, 30, 16), role="exterior",
                      ceiling_z=FLOOR - 12 * PH, floor_z=FLOOR)
    layout.add_region(VAULT, _r(30, 3, 36, 7), role="room",
                      ceiling_z=FLOOR - 4 * PH, floor_z=FLOOR)
    layout.add_connection("c:hall_yard", HALL, YARD, a1=_p(12, 3), a2=_p(12, 7),
                          min_width=1024)
    layout.add_connection("c:yard_vault", YARD, VAULT, a1=_p(30, 3), a2=_p(30, 7),
                          min_width=1024)
    start = _p(6, 5)
    layout.set_player_start(HALL, x=start[0], y=start[1], z=FLOOR - 1024, angle=0)
    layout.add_sprite("sp_start", HALL, x=start[0], y=start[1], z=FLOOR - 1024,
                      type=1, picnum=2528, behavior={"state": 1})
    spec = dict(pressed_switch(tx_id=0))
    height = spec.pop("height_player_heights")
    layout.place_on_wall("lever", HALL, a1=_p(0, 7), a2=_p(0, 3), t=0.5,
                         height_player_heights=height, offset_player_widths=0.06,
                         status=0, **spec)
    return layout


def _built(layout, circuit):
    circuit.apply()
    compiled = layout.compile()
    return compiled, compiled.level.to_disk_map()


class DeclareTests(unittest.TestCase):
    def test_a_wire_is_numbered_by_the_circuit_and_written_to_both_ends(self):
        layout = _layout()
        circuit = wiring.Circuit(layout)
        circuit.wire("vault", "pulling the hall lever works the vault") \
            .when(wiring.placement("lever"), "push") \
            .then(wiring.region(VAULT))
        (line,) = circuit.apply()
        self.assertEqual(line["channel"], 100)
        self.assertEqual(line["when"], ["push on placement lever"])
        self.assertEqual(layout.regions[VAULT].sector_behavior["rx_id"], 100)
        lever = next(p for p in layout.placements if p.placement_id == "lever")
        self.assertEqual((lever.behavior["tx_id"], lever.behavior["trigger_push"]),
                         (100, 1))

    def test_numbering_goes_round_channels_typed_by_hand(self):
        layout = _layout()
        layout.regions[YARD].sector_behavior["rx_id"] = 100
        circuit = wiring.Circuit(layout)
        circuit.wire("vault", "the lever works the vault") \
            .when(wiring.placement("lever"), "push").then(wiring.region(VAULT))
        self.assertEqual(circuit.apply()[0]["channel"], 101)

    def test_a_wire_must_say_what_it_is_for(self):
        with self.assertRaisesRegex(wiring.WireError, "does not say what it is for"):
            wiring.Circuit(_layout()).wire("vault", "  ")

    def test_a_level_wire_may_not_sit_on_an_engine_channel(self):
        """Channel 30 is kChannelPlayer0. The city's foundry was on it."""
        circuit = wiring.Circuit(_layout())
        circuit.wire("moment", "walking in sets it off", channel=30) \
            .when(wiring.region(YARD), "enter").then(wiring.region(VAULT))
        with self.assertRaisesRegex(wiring.WireError, "below 100 is the engine's"):
            circuit.apply()

    def test_an_object_has_one_rx_and_the_error_says_what_to_do(self):
        circuit = wiring.Circuit(_layout())
        circuit.wire("a", "the lever works the vault") \
            .when(wiring.placement("lever"), "push").then(wiring.region(VAULT))
        circuit.wire("b", "walking into the yard works the vault too") \
            .when(wiring.region(YARD), "enter").then(wiring.region(VAULT))
        with self.assertRaisesRegex(wiring.WireError, "one rx_id. Put both on one wire"):
            circuit.apply()

    def test_two_senders_on_one_wire_is_how_two_things_work_one(self):
        layout = _layout()
        circuit = wiring.Circuit(layout)
        circuit.wire("vault", "the lever or walking into the yard works the vault") \
            .when(wiring.placement("lever"), "push") \
            .when(wiring.region(YARD), "enter", once=True) \
            .then(wiring.region(VAULT))
        circuit.apply()
        self.assertEqual(layout.regions[YARD].sector_behavior["tx_id"], 100)
        self.assertEqual(layout.regions[YARD].sector_behavior["trigger_once"], 1)

    def test_a_field_the_object_already_has_differently_is_refused(self):
        layout = _layout()
        lever = next(p for p in layout.placements if p.placement_id == "lever")
        lever.behavior["command"] = 1
        circuit = wiring.Circuit(layout)
        circuit.wire("vault", "the lever works the vault") \
            .when(wiring.placement("lever"), "push", command=3) \
            .then(wiring.region(VAULT))
        with self.assertRaisesRegex(wiring.WireError, "already has command=1"):
            circuit.apply()

    def test_the_engine_is_an_end_of_a_wire_and_only_one_end(self):
        layout = _layout()
        circuit = wiring.Circuit(layout)
        circuit.wire("secret", "finding the vault is a secret",
                     engine="kChannelSecretFound") \
            .when(wiring.region(VAULT), "enter", command=64, once=True)
        circuit.apply()
        self.assertEqual(layout.regions[VAULT].sector_behavior["tx_id"], 2)
        wrong = wiring.Circuit(_layout())
        wrong.wire("secret", "x", engine="kChannelSecretFound") \
            .when(wiring.region(VAULT), "enter").then(wiring.region(YARD))
        with self.assertRaisesRegex(wiring.WireError, "nothing in the level may answer"):
            wrong.apply()

    def test_a_wire_whose_sender_reports_nothing_is_refused(self):
        with self.assertRaisesRegex(wiring.WireError, "sends nothing"):
            wiring.Circuit(_layout()).wire("a", "x").when(
                wiring.region(YARD), "enter", on=False)

    def test_a_secret_the_layout_emits_is_one_the_engine_counts(self):
        """`secret=True` wrote tx 2, command 64, enter and once, and no
        trigger_on. All 153 of the campaign's secret sectors report ON."""
        layout = _layout()
        layout.regions[VAULT].secret = True
        circuit = wiring.Circuit(layout)
        compiled, disk = _built(layout, circuit)
        self.assertEqual(circuit.read_back(compiled, disk)["silent"], [])
        (chain,) = [c for c in wiring.chains(disk) if c["cause"] == ["enter"]]
        self.assertFalse(chain["silent"])
        self.assertEqual(chain["steps"][0]["to_type"], "kChannelSecretFound")

    def test_a_circuit_can_be_declared_before_its_layout_exists(self):
        """A level is a program before it is a layout, and a wire's ends are
        names: the city declares them where each thing is built."""
        circuit = wiring.Circuit()
        circuit.wire("vault", "the lever works the vault")             .when(wiring.placement("lever"), "push").then(wiring.region(VAULT))
        with self.assertRaisesRegex(wiring.WireError, "has no layout"):
            circuit.apply()
        layout = _layout()
        circuit.bind(layout).apply()
        self.assertEqual(layout.regions[VAULT].sector_behavior["rx_id"], 100)

    def test_a_relay_passes_on_what_it_answers_and_is_read_back_as_one(self):
        """The curtain answers the push and passes its travel to the stage
        light: it is nobody's cause, and it is an end of two wires."""
        layout = _layout()
        circuit = wiring.Circuit(layout)
        circuit.wire("yard", "the lever works the yard")             .when(wiring.placement("lever"), "push").then(wiring.region(YARD))
        circuit.wire("vault", "the vault follows the yard")             .when(wiring.region(YARD), wiring.RELAY, command=wiring.CMD_LINK, on=False)             .then(wiring.region(VAULT))
        compiled, disk = _built(layout, circuit)
        said = circuit.read_back(compiled, disk)
        self.assertEqual([row["faults"] for row in said["wires"]], [[], []])
        self.assertEqual(layout.regions[YARD].sector_behavior["command"], wiring.CMD_LINK)

    def test_a_cause_is_something_that_can_be_done(self):
        with self.assertRaisesRegex(wiring.WireError, "not something that can be done"):
            wiring.Circuit(_layout()).wire("a", "x").when(wiring.region(YARD), "opened")
        with self.assertRaisesRegex(wiring.WireError, "only a sprite can be killed"):
            wiring.Circuit(_layout()).wire("b", "x").when(wiring.region(YARD), "killed")


class ReadBackTests(unittest.TestCase):
    def _circuit(self, layout):
        circuit = wiring.Circuit(layout)
        circuit.wire("vault", "pulling the hall lever works the vault and the yard") \
            .when(wiring.placement("lever"), "push") \
            .then(wiring.region(VAULT)).then(wiring.region(YARD))
        circuit.wire("secret", "finding the vault is a secret",
                     engine="kChannelSecretFound") \
            .when(wiring.region(VAULT), "enter", command=64, once=True)
        return circuit

    def test_the_built_map_is_read_with_the_campaigns_reader_and_agrees(self):
        layout = _layout()
        circuit = self._circuit(layout)
        compiled, disk = _built(layout, circuit)
        said = circuit.read_back(compiled, disk)
        self.assertEqual([row["faults"] for row in said["wires"]], [[], []])
        self.assertTrue(said["agrees"])
        self.assertEqual(said["undeclared"], [])
        vault = said["wires"][0]
        self.assertEqual(len(vault["senders"]), 1)
        self.assertEqual(len(vault["answers"]), 2)
        # and the reader describes it the way its author did
        chain = next(c for c in wiring.chains(disk) if c["root"] == vault["senders"][0])
        self.assertEqual(wiring.shape(chain)["cause"], "push")
        self.assertIn("the engine (kChannelSecretFound)",
                      [wiring.shape(c)["answers"] for c in wiring.chains(disk)
                       if c["cause"] == ["enter"]][0])

    def test_a_wire_typed_by_hand_is_listed_as_nobodys(self):
        layout = _layout()
        layout.regions[YARD].sector_behavior.update(
            {"tx_id": 400, "trigger_enter": 1, "trigger_on": 1})
        layout.regions[HALL].sector_behavior["rx_id"] = 400
        circuit = wiring.Circuit(layout)
        compiled, disk = _built(layout, circuit)
        (row,) = circuit.read_back(compiled, disk)["undeclared"]
        self.assertEqual(row["channel"], 400)
        self.assertEqual((len(row["senders"]), len(row["listeners"])), (1, 1))

    def test_a_fault_names_the_object_that_is_not_as_declared(self):
        layout = _layout()
        circuit = self._circuit(layout)
        compiled, disk = _built(layout, circuit)
        sector = compiled.allocations[YARD].sector_id
        disk.sectors[sector].extra.fields["rx_id"] = 0        # the wire is cut
        said = circuit.read_back(compiled, disk)
        self.assertFalse(said["agrees"])
        self.assertTrue(any("region region:yard does not listen" in fault
                            for fault in said["wires"][0]["faults"]))


if __name__ == "__main__":
    unittest.main()
