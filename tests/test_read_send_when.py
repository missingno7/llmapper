"""A transmitter that cannot send is not a link, and the reader now says so.

The owner's second walk of `slice2-streets.MAP` found nine switches sitting
above the roof of the shell, and measured the thing the reader had missed:
`trigger_on` and `trigger_off` are 0 on all nine, so by the engine none of
them can ever send. The reader called all nine links realised.

The engine rule, identical for all three record kinds
(`NBlood/source/blood/src/triggers.cpp` — SetSpriteState 100-106, SetWallState
121-127, SetSectorState 138-155):

    if (pX->txID)
        if (pX->command != kCmdLink && pX->triggerOn  &&  pX->state) evSend(...)
        if (pX->command != kCmdLink && pX->triggerOff && !pX->state) evSend(...)

Three clauses, and a `tx_id` alone satisfies only the first. `kCmdLink` is 5
(`eventq.h:88`): a linked record follows its partner and never transmits on
its own account.

So a source SENDS WHEN it has a channel, a command that is not `kCmdLink`,
and at least one of the two send-when bits. Anything else is a channel
written down and never used — which is a residue with a sector id, not a
mechanism.
"""

from __future__ import annotations

import unittest

CITY = "projects/blood-city/level/slice2-streets.MAP"


def _disk(path):
    from bloodmap.format import read_map

    return read_map(path)


def _corpus(name):
    from bloodmap.patterns import corpus_map_path

    try:
        return _disk(corpus_map_path(name))
    except Exception as error:  # pragma: no cover - corpus-dependent
        raise unittest.SkipTest(f"{name} is not readable here: {error}")


class TheSendWhenBits(unittest.TestCase):
    """`conditional.can_send` on its own, against the engine's three clauses."""

    def test_a_channel_alone_does_not_send(self):
        from bloodmap.conditional import can_send

        able, why = can_send({"tx_id": 400, "trigger_on": 0, "trigger_off": 0,
                              "command": 1})
        self.assertFalse(able)
        self.assertIn("trigger_on", why)
        self.assertIn("trigger_off", why)

    def test_either_bit_is_enough(self):
        from bloodmap.conditional import can_send

        for bit in ("trigger_on", "trigger_off"):
            able, why = can_send({"tx_id": 400, "command": 1, bit: 1})
            self.assertTrue(able, why)
            self.assertIn(bit, why)

    def test_no_channel_is_not_a_transmitter_at_all(self):
        from bloodmap.conditional import can_send

        able, why = can_send({"tx_id": 0, "trigger_on": 1})
        self.assertFalse(able)
        self.assertIn("no channel", why)

    def test_a_linked_record_follows_and_never_sends(self):
        """`command == kCmdLink` (5) fails the first clause of all three."""
        from bloodmap.conditional import KCMD_LINK, can_send

        self.assertEqual(KCMD_LINK, 5)
        able, why = can_send({"tx_id": 400, "trigger_on": 1,
                              "command": KCMD_LINK})
        self.assertFalse(able)
        self.assertIn("kCmdLink", why)


class TheCitysNineSwitchesNowSend(unittest.TestCase):
    """The fail-first, and the fix that answered it.

    The owner's second walk measured nine switches on `slice2-streets.MAP`
    with a channel each and `trigger_on` and `trigger_off` both 0 -- nine
    mechanisms the reader called realised and the engine would never have
    started. The reader learnt the engine's rule (`can_send`), and P14b
    rebuilt the map with the send-when bits set (queue item 39, W6).

    Both halves are pinned. The rule itself is guarded by `TheSendWhenBits`
    above, on values rather than on this map, so it survives the next rebuild;
    what is checked here is that the map the finding came from now passes, and
    that it passes for the stated reason and not by the rule going quiet.
    """

    @classmethod
    def setUpClass(cls):
        from bloodmap.curriculum import mine_map
        from bloodmap.read_mechanisms import read_mechanisms

        try:
            cls.disk = _disk(CITY)
        except Exception as error:  # pragma: no cover
            raise unittest.SkipTest(f"the city is not readable: {error}")
        cls.result = read_mechanisms(cls.disk.to_level_ir(), cls.disk,
                                     lessons=None, reading=mine_map(CITY))

    def test_no_transmitter_on_the_map_is_dead_any_more(self):
        dead = [index for index, sprite in enumerate(self.disk.sprites)
                if sprite.extra is not None
                and int(sprite.extra.fields.get("tx_id") or 0)
                and not int(sprite.extra.fields.get("trigger_on") or 0)
                and not int(sprite.extra.fields.get("trigger_off") or 0)]
        self.assertEqual(dead, [],
                         "these were sprites 0, 2, 4, 6, 8, 10, 11, 14 and 15")

    def test_all_nine_links_are_realised_and_say_why(self):
        links = self.result["links"]
        self.assertEqual(len(links), 9)
        for link in links:
            self.assertTrue(link["realised"], link)
            self.assertEqual(link["sources_that_can_send"], link["from"])
            for why in link["why_by_source"].values():
                self.assertIn("sends on channel", why)
                self.assertIn("trigger_on", why)

    def test_each_chain_is_one_sentence(self):
        chains = [row for row in self.result["sentences"]
                  if row["kind"] == "tx -> rx chain"]
        self.assertEqual(len(chains), 9)

    def test_no_switch_is_residue_any_more(self):
        reasons = {row["record"]: row["why"] for row in self.result["residue"]}
        self.assertEqual([record for record, why in reasons.items()
                          if "transmits on channel" in why], [])
class TheCampaignStillWorks(unittest.TestCase):
    """The guard: Blood's own chains are realised, or the rule is too strict."""

    def test_e3m1s_collapsing_house_is_still_a_realised_chain(self):
        from bloodmap.curriculum import mine_map
        from bloodmap.patterns import corpus_map_path
        from bloodmap.read_mechanisms import read_mechanisms

        disk = _corpus("E3M1")
        path = corpus_map_path("E3M1")
        result = read_mechanisms(disk.to_level_ir(), disk, lessons=None,
                                 reading=mine_map(path))
        realised = [row for row in result["links"] if row["realised"]]
        self.assertTrue(realised, "E3M1 wires its mechanisms and they work")
        biggest = max(realised, key=lambda row: len(row["to"]))
        self.assertGreaterEqual(len(biggest["to"]), 10,
                                "the collapsing house is one channel telling "
                                "many records at once")
        self.assertTrue(biggest["sources_that_can_send"])

    def test_a_map_may_carry_some_dead_channels_without_losing_the_rest(self):
        from bloodmap.curriculum import mine_map
        from bloodmap.patterns import corpus_map_path
        from bloodmap.read_mechanisms import read_mechanisms

        disk = _corpus("E1M2")
        result = read_mechanisms(disk.to_level_ir(), disk, lessons=None,
                                 reading=mine_map(corpus_map_path("E1M2")))
        realised = [row for row in result["links"] if row["realised"]]
        self.assertTrue(realised)
        self.assertTrue(any(row["kind"] == "tx -> rx chain"
                            for row in result["sentences"]))
