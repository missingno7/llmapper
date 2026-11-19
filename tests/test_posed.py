"""A mechanism's other end is built, not imagined, and what cannot be built is said.

The owner wants the critic to see a mechanism OFF and ON, "to tell that it
works the intended way"; every frame until then showed the map as saved.
`bloodmap.posed` builds the other pose as a copy. These hold its engine
transcriptions on synthetic maps: a z pair chosen by state, a switch's
second picture, a destroyed thing gone, a slide at both ends of its
travel -- and the refusal, for what has no picture (an engine channel).
"""

from __future__ import annotations

import copy
import unittest

from bloodmap import posed, wiring
from bloodmap.art import ArtTile
from bloodmap.format import XSECTOR_SCHEMA, XSPRITE_SCHEMA
from bloodmap.model import PackedExtra
from tests.helpers import corpus_disk, synthetic_two_sector_map

TOGGLE, ONE_WAY, GIB_OBJECT = 20, 21, 416
Z_MOTION, SLIDE = 600, 616


def _x(kind: str, **fields) -> PackedExtra:
    schema = {"XSECTOR": XSECTOR_SCHEMA, "XSPRITE": XSPRITE_SCHEMA}[kind]
    values = {name: 0 for name, _bits, _signed in schema}
    values.update(fields)
    return PackedExtra(kind, values)


def _map(*, state: int = 0, floor: int = 8192, secret: bool = True):
    """A pushed switch on 101; sector 1 is a z door from 8192 (off) to 4096 (on)."""
    disk = synthetic_two_sector_map()
    disk.sprites[0].fields.update(type=TOGGLE, picnum=100, x_repeat=64, y_repeat=64)
    disk.sprites[0].extra = _x("XSPRITE", tx_id=101, trigger_push=1, command=3,
                               trigger_on=1, trigger_off=1)
    disk.sprites[0].fields["extra"] = 1
    disk.sprites[1].extra = _x("XSPRITE")
    disk.sectors[1].fields.update(type=Z_MOTION, extra=1, floor_z=floor)
    disk.sectors[1].extra = _x("XSECTOR", rx_id=101, tx_id=2 if secret else 0, state=state,
                               trigger_on=1, trigger_off=1,
                               off_floor_z=8192, on_floor_z=4096,
                               off_ceiling_z=-8192, on_ceiling_z=-8192)
    return disk


def _snapshot(disk):
    return [(dict(item.fields), dict(item.extra.fields) if item.extra is not None else None)
            for group in (disk.sectors, disk.walls, disk.sprites) for item in group]


def _chain(disk, root="sprite 0"):
    return posed.chain_of(wiring.chains(disk), root)


class PosedTests(unittest.TestCase):
    def test_the_input_is_not_changed(self):
        disk = _map()
        saved = _snapshot(disk)
        other, _report = posed.posed(disk, _chain(disk))
        posed.rested(disk, _chain(disk))
        self.assertEqual(_snapshot(disk), saved)
        self.assertIsNot(other, disk)
        self.assertNotEqual(_snapshot(other), saved)

    def test_a_silent_senders_listeners_are_not_posed(self):
        """No trigger_on, trigger_off or link: it toggles and tells no one."""
        disk = _map()
        disk.sprites[0].extra.fields.update(trigger_on=0, trigger_off=0)
        other, report = posed.posed(disk, _chain(disk))
        self.assertEqual(other.sectors[1].fields["floor_z"], 8192)
        self.assertEqual(other.sprites[0].fields["picnum"], 101)
        self.assertIn("sector 1", [row["object"] for row in report["not_posed"]])

    def test_a_z_pair_is_chosen_by_state(self):
        """ZTranslateSector: off_floor_z at busy 0, on_floor_z at 65536."""
        disk = _map(state=0, floor=8192)
        other, report = posed.posed(disk, _chain(disk))
        self.assertEqual(other.sectors[1].fields["floor_z"], 4096)
        self.assertIn("sector 1", report["posed"])
        disk = _map(state=1, floor=4096)
        other, _report = posed.posed(disk, _chain(disk))
        self.assertEqual(other.sectors[1].fields["floor_z"], 8192)

    def test_rest_is_the_load_pose_not_the_saved_one(self):
        """A state-0 door saved at its ON height is found at OFF when the level loads."""
        disk = _map(state=0, floor=4096)
        rest, report = posed.rested(disk, _chain(disk))
        self.assertEqual(rest.sectors[1].fields["floor_z"], 8192)
        self.assertIn("sector 1", report["posed"])

    def test_a_switch_shows_its_other_picture(self):
        """view.cpp: a set state draws picanm.num + 1 tiles on, for view type 0."""
        disk = _map()
        other, report = posed.posed(disk, _chain(disk))
        self.assertEqual(other.sprites[0].fields["picnum"], 101)
        self.assertEqual(other.sprites[0].extra.fields["state"], 0,
                         "the observer reads no XSPRITE: the picture moves, not the state")
        tiles = {100: ArtTile(100, 32, 32, b"", picanm=2)}            # two more frames
        other, _report = posed.posed(disk, _chain(disk), tiles=tiles)
        self.assertEqual(other.sprites[0].fields["picnum"], 103)
        tiles = {100: ArtTile(100, 32, 32, b"", picanm=1 << 28)}      # view type 1
        other, report = posed.posed(disk, _chain(disk), tiles=tiles)
        self.assertEqual(other.sprites[0].fields["picnum"], 100)
        self.assertIn("sprite 0", [row["object"] for row in report["not_posed"]])

    def test_a_one_way_switch_flips_its_rest_state(self):
        disk = _map()
        disk.sprites[0].fields["type"] = ONE_WAY
        disk.sprites[0].extra.fields["state"] = 1
        disk.sprites[0].extra.fields["rest_state"] = 0
        _other, report = posed.posed(disk, _chain(disk))
        self.assertEqual(report["objects"][0]["state"], [1, 1])

    def test_a_destroyed_thing_is_gone(self):
        disk = _map()
        disk.sprites[0].fields["type"] = GIB_OBJECT
        disk.sprites[0].extra = _x("XSPRITE", tx_id=101, command=1)
        chain = _chain(disk)
        self.assertEqual(chain["cause"], ["destroyed"])
        other, report = posed.posed(disk, chain)
        self.assertTrue(other.sprites[0].fields["cstat"] & 32768)
        rest, _report = posed.rested(disk, chain)
        self.assertFalse(rest.sprites[0].fields["cstat"] & 32768)
        gone = [row for row in report["not_posed"] if row["object"] == "sprite 0"]
        self.assertTrue(gone and "not drawn" in gone[0]["why"][0])

    def test_an_engine_channel_is_reported_not_posed(self):
        disk = _map(secret=True)
        _other, report = posed.posed(disk, _chain(disk))
        refused = {row["object"]: row["why"] for row in report["not_posed"]}
        self.assertIn("engine channel 2", refused)
        self.assertIn("kChannelSecretFound", refused["engine channel 2"][0])

    def test_a_sender_that_misses_its_edge_sends_on_the_way_back(self):
        """E1M1's casket: trigger_off only, wait_time 6. Turned on, it says
        nothing; 0.6 s later it returns to rest and that change is reported."""
        disk = _map(secret=False)
        disk.sprites[0].extra.fields.update(trigger_on=0, trigger_off=1, wait_time=6)
        other, report = posed.posed(disk, _chain(disk))
        self.assertEqual(other.sectors[1].fields["floor_z"], 4096)
        door = next(row for row in report["objects"] if row["object"] == "sector 1")
        self.assertFalse([line for line in door["undecided"] if "trigger_on" in line])
        self.assertTrue(any("returns to state 0" in line for line in door["done"]))
        disk.sprites[0].extra.fields["wait_time"] = 0
        _other, report = posed.posed(disk, _chain(disk))
        door = next(row for row in report["objects"] if row["object"] == "sector 1")
        self.assertTrue(any("no trigger_on" in line for line in door["undecided"]))

    def test_a_command_that_sets_no_state_is_not_posed(self):
        disk = _map(secret=False)
        disk.sprites[0].extra.fields["command"] = 6                    # kCmdLock
        other, report = posed.posed(disk, _chain(disk))
        self.assertEqual(other.sectors[1].fields["floor_z"], 8192)
        self.assertIn("sector 1", [row["object"] for row in report["not_posed"]])

    def test_a_slide_is_posed_at_both_ends_of_its_travel(self):
        """trInit rebases a slide a whole travel back: drawn is busy 1, rest
        at state 0 is the drawn outline less the marker separation."""
        disk = _map(secret=False)
        sector = disk.sectors[1]
        sector.fields["type"] = SLIDE
        sector.extra.fields.update(marker_0=2, marker_1=3, off_floor_z=0, on_floor_z=0)
        for x in (1536, 1536 + 256):
            marker = copy.deepcopy(disk.sprites[1])
            marker.fields.update(x=x, y=512, type=3, status=10, angle=0, extra=-1)
            marker.extra = None
            disk.sprites.append(marker)
        chain = _chain(disk)
        own = range(4, 8)
        drawn = [(disk.walls[w].fields["x"], disk.walls[w].fields["y"]) for w in own]
        other, _report = posed.posed(disk, chain)
        rest, _report = posed.rested(disk, chain)
        self.assertEqual([(other.walls[w].fields["x"], other.walls[w].fields["y"])
                          for w in own], drawn)
        self.assertEqual([(rest.walls[w].fields["x"], rest.walls[w].fields["y"])
                          for w in own], [(x - 256, y) for x, y in drawn])


class CorpusTests(unittest.TestCase):
    def test_e1m5s_bar_switch_flips_and_its_bars_part(self):
        """E1M5 sprite 84: a pushed toggle whose door is three z sectors."""
        disk = corpus_disk("E1M5")
        other, report = posed.posed(disk, _chain(disk, "sprite 84"))
        self.assertEqual(other.sprites[84].fields["picnum"],
                         disk.sprites[84].fields["picnum"] + 1)
        self.assertEqual({"sector 167", "sector 168", "sector 169"} - set(report["posed"]), set())


if __name__ == "__main__":
    unittest.main()
