"""Check Gravesend's sound fields and causes after map serialization."""

from pathlib import Path
import sys
import unittest

from bloodmap import wiring
from bloodmap.format import read_map
from bloodmap.mechanism import CMD_ON
from bloodmap.motion import CMD_STATE
from bloodmap.model import record_extra, record_fields
from bloodmap.visual import HIDDEN_TYPES

LEVEL = Path("projects/blood-city/level")
CITY = LEVEL / "blood-city-current.MAP"


def _ambience():
    if str(LEVEL) not in sys.path:
        sys.path.insert(0, str(LEVEL))
    import ambience
    return ambience


class AmbientFieldsTests(unittest.TestCase):
    def test_context_supplies_campaign_envelope_and_allows_overrides(self):
        fields = _ambience().fields
        self.assertEqual(fields("mall")["behavior"], {
            "data_1": 150, "data_2": 350, "data_3": 65, "data_4": 50, "state": 1})
        self.assertEqual(fields("mall", volume=30)["behavior"]["data_4"], 30)
        with self.assertRaises(ValueError):
            fields("mall", near=1500)


@unittest.skipUnless(CITY.exists(), "the city is not built")
class DoorSoundTests(unittest.TestCase):
    """The owner: "These wooden zdoor sound 106 sounds like a moving stone"."""

    def test_a_rising_door_sounds_like_what_its_leaf_is(self):
        _ambience()
        import motion_sounds
        from bloodmap.mechanism import SECTOR_SOUND_PROFILES

        disk = read_map(CITY)
        marks = {record_fields(s)["sector"]: tuple((record_extra(s) or {}).get(f"data_{k}") for k in (1, 2, 3, 4))
                 for s in disk.sprites if record_fields(s)["type"] == 709}
        wooden = 0
        for index, sector in enumerate(disk.sectors):
            if record_fields(sector)["type"] != 600 or index not in marks:
                continue
            if 22 in motion_sounds._leaf_faces(disk, index):
                self.assertEqual(marks[index], SECTOR_SOUND_PROFILES["wood_z_door"], index)
                wooden += 1
        self.assertGreaterEqual(wooden, 10)


@unittest.skipUnless(CITY.exists(), "the city is not built")
class CitySoundTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.disk = read_map(CITY)
        cls.sprites = [(record_fields(sprite), record_extra(sprite) or {})
                       for sprite in cls.disk.sprites]
        cls.sectors = [record_extra(sector) or {} for sector in cls.disk.sectors]

    def test_ambience_uses_room_envelopes_and_both_outfalls_sound(self):
        ambience = _ambience()
        envelopes = set()
        outfalls = 0
        for fields, extra in self.sprites:
            if fields["type"] != 710:
                continue
            self.assertEqual(fields["status"], 12)
            self.assertEqual(fields["picnum"], 2521)
            self.assertTrue(fields["cstat"] & 32768)
            self.assertEqual(extra["state"], 1)
            self.assertLess(extra["data_1"], extra["data_2"])
            sound = extra["data_3"]
            envelopes.add((sound, extra["data_1"], extra["data_2"], extra["data_4"]))
            outfalls += sound == 56
        expected = {(sound, *ambience.ENVELOPES[context])
                    for context, sound in ambience.SOUNDS.items()}
        self.assertEqual(envelopes, expected | {(56, 150, 350, 50)})
        self.assertEqual(outfalls, 2)

    def test_metal_drain_covers_have_a_metal_break_sound(self):
        covers = [extra["data_4"] for fields, extra in self.sprites
                  if fields["type"] == 417 and fields["picnum"] == 219]
        self.assertEqual(covers, [314] * 4)

    def test_caleb_remarks_have_one_invisible_speaker_and_the_intended_cause(self):
        speakers = [(fields, extra) for fields, extra in self.sprites
                    if fields["type"] == 711 and extra["data_1"] >= 3000]
        self.assertCountEqual([extra["data_1"] for _, extra in speakers], [4509, 4537, 3034, 3101])
        self.assertIn(711, HIDDEN_TYPES)
        for fields, extra in speakers:
            sound = extra["data_1"]
            with self.subTest(sound=sound):
                self.assertTrue(fields["cstat"] & 32768)
                self.assertEqual((fields["picnum"], fields["status"]), (2519, 0))
                self.assertGreaterEqual(extra["rx_id"], wiring.USER_CHANNELS_FROM)
                senders = [(source["type"], data) for source, data in self.sprites
                           if data.get("tx_id") == extra["rx_id"]]
                senders += [(None, data) for data in self.sectors
                            if data.get("tx_id") == extra["rx_id"]]
                self.assertEqual(len(senders), 1)
                type_id, cause = senders[0]
                self.assertEqual(cause["command"], CMD_ON)
                if sound in (4509, 4537):
                    self.assertEqual(cause["trigger_once"], 1)
                if sound == 4509:
                    self.assertEqual(type_id, 21)
                    self.assertEqual(cause["rx_id"], wiring.LEVEL_START_CHANNEL)
                    self.assertEqual((cause["state"], cause["wait_time"], cause["rest_state"]), (0, 5, 0))
                    self.assertEqual((cause["trigger_on"], cause["trigger_off"]), (0, 1))
                elif sound == 4537:
                    self.assertEqual(type_id, 216)
                    self.assertEqual((cause["decoupled"], cause["trigger_off"]), (1, 1))
                elif sound == 3034:
                    self.assertEqual(type_id, 20)
                    self.assertEqual((cause["state"], cause["trigger_on"], cause["trigger_off"]),
                                     (1, 0, 1))
                    car, = [data for data in self.sectors if data.get("tx_id") == cause["rx_id"]]
                    self.assertEqual(car["command"], CMD_STATE)
                    self.assertTrue(car["drag"] and car["busy_time_b"])
                else:
                    # The show uses a latch which stays ON across curtain cycles.
                    self.assertEqual(type_id, 0)
                    self.assertEqual((cause["trigger_on"], cause["trigger_off"]), (1, 0))
                    self.assertEqual((cause["state"], cause["wait_time"], cause["rest_state"]), (0, 0, 0))
                    (stage,) = [data for data in self.sectors if data.get("tx_id") == cause["rx_id"]]
                    self.assertEqual((stage["command"], stage["trigger_on"], stage["trigger_off"]),
                                     (CMD_ON, 1, 0))
