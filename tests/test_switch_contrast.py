"""What a switch commands, and the hidden-against-visible contrast.

`switch_role` is the whole experiment's guard: the feature set must stay
channel role and what is commanded, because a geometric feature would answer
a different question and look like an answer to this one. The tests pin the
feature list as much as the values.
"""

import unittest

from bloodmap.switches import (
    CONTRAST_FEATURES, INVISIBLE, SwitchError, contrast_hidden_switches,
    switch_role,
)

try:
    from bloodmap.patterns import list_corpus_maps
    CORPUS = bool(list_corpus_maps(population="blood-campaign"))
except Exception:
    CORPUS = False


class Extra:
    """`switches._extra` reads `item.extra.fields`, so the fake matches."""

    def __init__(self, fields):
        self.fields = fields


class Item:
    def __init__(self, fields, extra=None):
        self.fields = fields
        self.extra = Extra(extra) if extra is not None else None


class Disk:
    def __init__(self, sprites=(), sectors=()):
        self.sprites = list(sprites)
        self.sectors = list(sectors)


def switch(*, type_id=20, cstat=0, tx_id=0, rx_id=0, **extra):
    payload = {"tx_id": tx_id, "rx_id": rx_id, **extra}
    return Item({"type": type_id, "cstat": cstat, "picnum": 1070}, payload)


def sector(*, type_id=600, rx_id=0):
    return Item({"type": type_id}, {"rx_id": rx_id})


class SwitchRoleTest(unittest.TestCase):
    def test_a_non_switch_sprite_is_not_read(self):
        disk = Disk([Item({"type": 0, "cstat": 0, "picnum": 1}, {})])
        self.assertIsNone(switch_role(disk, 0))

    def test_the_invisible_bit_makes_a_switch_hidden(self):
        disk = Disk([switch(cstat=INVISIBLE)])
        self.assertTrue(switch_role(disk, 0)["hidden"])

    def test_a_drawn_switch_is_not_hidden(self):
        disk = Disk([switch(cstat=0)])
        self.assertFalse(switch_role(disk, 0)["hidden"])

    def test_it_finds_the_sectors_listening_on_its_channel(self):
        disk = Disk([switch(tx_id=42)],
                    [sector(rx_id=42), sector(rx_id=7), sector(rx_id=42)])
        role = switch_role(disk, 0)
        self.assertEqual(role["sectors_commanded"], 2)
        self.assertTrue(role["commands_motion"])
        self.assertTrue(role["commands_z_motion"])

    def test_a_channel_nothing_listens_to_commands_nothing(self):
        disk = Disk([switch(tx_id=42)], [sector(rx_id=7)])
        role = switch_role(disk, 0)
        self.assertEqual(role["sectors_commanded"], 0)
        self.assertTrue(role["commands_nothing_in_this_map"])

    def test_commanding_a_still_sector_is_not_commanding_motion(self):
        disk = Disk([switch(tx_id=42)], [sector(type_id=0, rx_id=42)])
        role = switch_role(disk, 0)
        self.assertEqual(role["sectors_commanded"], 1)
        self.assertFalse(role["commands_motion"])

    def test_the_level_exit_channels_are_recognised(self):
        self.assertTrue(switch_role(Disk([switch(tx_id=4)]), 0)["ends_the_level"])
        self.assertTrue(switch_role(Disk([switch(tx_id=5)]), 0)["ends_the_level"])
        self.assertFalse(switch_role(Disk([switch(tx_id=6)]), 0)["ends_the_level"])

    def test_a_switch_that_both_listens_and_transmits_relays(self):
        role = switch_role(Disk([switch(tx_id=9, rx_id=3)]), 0)
        self.assertTrue(role["relays"])

    def test_a_switch_wired_one_way_only_is_not_a_relay(self):
        # A relay is a switch something else can work. Transmitting alone is
        # every switch in the campaign bar a handful, so counting it as a
        # relay makes the feature say nothing.
        self.assertFalse(switch_role(Disk([switch(tx_id=9)]), 0)["relays"])
        self.assertFalse(switch_role(Disk([switch(rx_id=3)]), 0)["relays"])

    def test_a_switch_on_no_channel_commands_nothing(self):
        # Channel 0 is "not wired", not a channel. A sector with no rx_id is
        # listening to nothing, and matching the two would hand every silent
        # switch every silent sector in the map.
        disk = Disk([switch(tx_id=0)], [sector(rx_id=0), sector(rx_id=0)])
        role = switch_role(disk, 0)
        self.assertEqual(role["sectors_commanded"], 0)
        self.assertFalse(role["transmits"])
        self.assertFalse(role["commands_nothing_in_this_map"])

    def test_the_scored_features_are_exactly_these(self):
        # The rule of the experiment, pinned as an allow-list rather than a
        # sniff for geometric-looking words -- `commands_z_motion` is about
        # the axis the *commanded sector* moves on, not about where the
        # switch is, and a heuristic rejects it. Anything joining this list
        # has to be added here too, deliberately.
        self.assertEqual(set(CONTRAST_FEATURES), {
            # channel role
            "transmits", "listens", "relays", "ends_the_level",
            "reserved_channel",
            # what it commands
            "sectors_commanded", "commands_nothing_in_this_map",
            "commands_motion", "commands_z_motion",
            "commands_more_than_one_kind",
            # how it may be worked
            "one_way", "keyed", "once_only",
        })

    def test_nothing_about_where_the_switch_is_reaches_the_reading(self):
        # Two switches identical in role but placed differently cannot be
        # told apart, because position never enters `switch_role`.
        here = Item({"type": 20, "cstat": 0, "picnum": 1070, "x": 0, "y": 0},
                    {"tx_id": 9})
        there = Item({"type": 20, "cstat": 0, "picnum": 2290,
                      "x": 99999, "y": -4096}, {"tx_id": 9})
        left = switch_role(Disk([here], [sector(rx_id=9)]), 0)
        right = switch_role(Disk([there], [sector(rx_id=9)]), 0)
        self.assertEqual({k: left[k] for k in CONTRAST_FEATURES},
                         {k: right[k] for k in CONTRAST_FEATURES})


@unittest.skipUnless(CORPUS, "the Blood corpus is not present")
class ContrastTest(unittest.TestCase):
    def test_the_campaign_contrast_runs_and_keeps_both_sides(self):
        report = contrast_hidden_switches()
        self.assertGreater(report["counts"]["hidden"]["switches"], 0)
        self.assertGreater(report["counts"]["visible"]["switches"], 0)
        self.assertEqual(report["features_scored"], list(CONTRAST_FEATURES))

    def test_every_feature_is_scored_and_none_is_silently_dropped(self):
        report = contrast_hidden_switches()
        scored = {item["feature"] for item in
                  report["discriminating"] + report["rejected"]}
        self.assertEqual(scored, set(CONTRAST_FEATURES))

    def test_a_population_with_no_maps_is_refused(self):
        with self.assertRaises(Exception):
            contrast_hidden_switches(population="no-such-population")


if __name__ == "__main__":
    unittest.main()
