"""A mechanism is a chain laid over the level, and it is read as one.

The owner, 2026-11-19: "there is no such a thing as a simple door or lift
because you are giving connections of events and effects to sectors and
sprites." The index built that morning was keyed by sector type and let the
word "lift" resolve to one. These hold the layer that was missing: a chain
starts where the engine starts one, ends where the engine ends one, and is
named by its cause, its sender and what answers -- never by a type alone.
"""

from __future__ import annotations

import unittest

from bloodmap import wiring
from bloodmap.format import XSECTOR_SCHEMA, XSPRITE_SCHEMA
from bloodmap.model import PackedExtra
from tests.helpers import synthetic_two_sector_map

ZOMBIE, GIB_OBJECT, TOGGLE = 203, 416, 20


def _x(kind: str, **fields) -> PackedExtra:
    schema = {"XSECTOR": XSECTOR_SCHEMA, "XSPRITE": XSPRITE_SCHEMA}[kind]
    values = {name: 0 for name, _bits, _signed in schema}
    values.update(fields)
    return PackedExtra(kind, values)


def _map():
    """A pushed switch on 101; sector 1 listens there and tells the engine a secret was found."""
    disk = synthetic_two_sector_map()
    disk.sprites[0].fields["type"] = TOGGLE
    disk.sprites[0].extra = _x("XSPRITE", tx_id=101, trigger_push=1, trigger_on=1,
                               command=1, key=3)
    disk.sprites[0].fields["extra"] = 1
    disk.sectors[1].fields["type"] = 600
    disk.sectors[1].extra = _x("XSECTOR", rx_id=101, tx_id=2, trigger_on=1)
    disk.sectors[1].fields["extra"] = 1
    return disk


class ChainTests(unittest.TestCase):
    def test_a_chain_is_a_cause_a_sender_and_all_that_answers(self):
        (chain,) = wiring.chains(_map())
        self.assertEqual((chain["root"], chain["cause"], chain["key"]),
                         ("sprite 0", ["push"], 3))
        self.assertEqual([(step["from"], step["channel"], step["to"], step["to_type"])
                          for step in chain["steps"]],
                         [("sprite 0", 101, "sector 1", "kSectorZMotion"),
                          ("sector 1", 2, "engine", "kChannelSecretFound")])

    def test_a_listener_is_not_the_start_of_its_own_chain(self):
        """Sector 1 sends, but only when something tells it to."""
        self.assertEqual([chain["root"] for chain in wiring.chains(_map())], ["sprite 0"])

    def test_no_channel_is_not_a_cause(self):
        """`rx_id` 0 listens to nothing. It used to be read as "set off by
        channel 0", which made 354 of the campaign's chains start at a
        channel that does not exist."""
        disk = _map()
        disk.sprites[1].fields["type"] = TOGGLE
        disk.sprites[1].extra = _x("XSPRITE", tx_id=101)
        disk.sprites[1].fields["extra"] = 2
        causes = {chain["root"]: chain["cause"] for chain in wiring.chains(disk)}
        self.assertEqual(causes["sprite 1"], ["itself"])

    def test_a_dude_fires_when_killed_and_a_thing_when_destroyed(self):
        """Neither has a trigger flag: the engine triggers them itself
        (actor.cpp:3029 and :3513)."""
        for type_id, cause in ((ZOMBIE, "killed"), (GIB_OBJECT, "destroyed")):
            with self.subTest(type=type_id):
                disk = _map()
                disk.sprites[1].fields["type"] = type_id
                disk.sprites[1].extra = _x("XSPRITE", tx_id=101, rx_id=150, trigger_off=1)
                disk.sprites[1].fields["extra"] = 2
                causes = {chain["root"]: chain["cause"] for chain in wiring.chains(disk)}
                self.assertEqual(causes["sprite 1"], [cause])

    def test_the_level_starting_is_a_cause_and_a_levels_own_channel_is_not(self):
        disk = _map()
        disk.sprites[1].extra = _x("XSPRITE", tx_id=101, rx_id=7)
        disk.sprites[1].fields["extra"] = 2
        causes = {chain["root"]: chain["cause"] for chain in wiring.chains(disk)}
        self.assertEqual(causes["sprite 1"], ["channel 7 kChannelLevelStart"])
        disk.sprites[1].extra = _x("XSPRITE", tx_id=101, rx_id=100)
        self.assertNotIn("sprite 1", {chain["root"] for chain in wiring.chains(disk)})

    def test_a_sender_that_reports_no_change_never_fires(self):
        """`SetSpriteState`, `SetWallState` and `SetSectorState` send only
        under triggerOn or triggerOff. The layout's own secrets were emitted
        without either, so no secret it ever built was counted."""
        disk = _map()
        disk.sprites[0].extra = _x("XSPRITE", tx_id=101, trigger_push=1, command=1)
        (chain,) = wiring.chains(disk)
        self.assertTrue(chain["silent"])
        self.assertEqual([node["id"] for node in wiring.silent_senders(disk)], ["sprite 0"])
        disk.sprites[0].extra = _x("XSPRITE", tx_id=101, trigger_push=1, trigger_off=1)
        self.assertFalse(wiring.chains(disk)[0]["silent"])

    def test_a_cascade_stops_at_a_relay_that_reports_no_change(self):
        disk = _map()
        disk.sectors[1].extra = _x("XSECTOR", rx_id=101, tx_id=2)
        (chain,) = wiring.chains(disk)
        self.assertEqual(chain["dead_relays"], ["sector 1"])
        self.assertEqual([step["to"] for step in chain["steps"]], ["sector 1"])

    def test_a_link_drives_its_listeners_without_reporting_anything(self):
        disk = _map()
        disk.sprites[0].extra = _x("XSPRITE", tx_id=101, trigger_push=1,
                                   command=wiring.CMD_LINK)
        self.assertFalse(wiring.chains(disk)[0]["silent"])

    def test_a_relay_where_no_player_goes_is_named_as_one(self):
        """The owner: "there are usually switches outside of accessible level
        area to do cascade of events." 603 campaign chains pass through one."""
        disk = _map()
        (chain,) = wiring.chains(disk, reach={0: "reachable", 1: "logic_closet"})
        self.assertEqual(chain["closet_relays"], ["sector 1"])
        (chain,) = wiring.chains(disk, reach={0: "reachable", 1: "reachable"})
        self.assertEqual(chain["closet_relays"], [])
        self.assertEqual(wiring.chains(disk)[0]["closet_relays"], [])

    def test_only_keeps_the_chains_that_start_in_those_sectors(self):
        disk = _map()
        home = int(disk.sprites[0].fields["sector"])
        self.assertEqual(len(wiring.chains(disk, only={home})), 1)
        self.assertEqual(wiring.chains(disk, only={home + 5}), [])


class ShapeTests(unittest.TestCase):
    def test_a_shape_has_no_numbers_in_it(self):
        (chain,) = wiring.chains(_map())
        self.assertEqual(wiring.shape(chain), {
            "cause": "push", "sender": "kSwitchToggle",
            "answers": ["kSectorZMotion", "the engine (kChannelSecretFound)"]})

    def test_a_sector_on_the_wire_is_named_by_what_it_does_to_the_space(self):
        """The same type is a door on one wire and a lift on another, and
        only the reading of where it sits can say which."""
        (chain,) = wiring.chains(_map())
        for reading, said in (
                ("changes what fits through",
                 "kSectorZMotion that changes what fits through"),
                ("carries a body between levels",
                 "kSectorZMotion that carries a body between levels"),
                ("neither", "kSectorZMotion")):
            with self.subTest(reading=reading):
                answers = wiring.shape(chain, {1: {"is": reading}})["answers"]
                self.assertIn(said, answers)

    def test_an_untyped_sender_is_called_what_it_is(self):
        disk = _map()
        disk.sprites[0].fields["type"] = 0
        (chain,) = wiring.chains(disk)
        self.assertEqual(wiring.shape(chain)["sender"], "a plain sprite")


if __name__ == "__main__":
    unittest.main()
