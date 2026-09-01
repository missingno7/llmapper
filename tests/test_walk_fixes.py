"""The three defects the owner found by walking the zoo, and their oracles.

Each is fixtured against the isolated tutorial rather than an embedded
campaign case, per the owner's rule: a tutorial demonstrates one mechanism
with nothing else in the way, so what you read there is the mechanism and not
the level around it.
"""

import unittest
from pathlib import Path

VANILLA = Path("maps/blood/mechanism/Vanilla")
SINGLES = Path("maps/blood/mechanism")


def _map(path: Path):
    from bloodmap.format import read_map

    if not path.exists():
        raise unittest.SkipTest(f"{path} is not present")
    return read_map(path)


def _zoo():
    return _map(Path("projects/pattern-zoo/level/pattern-zoo.MAP"))


def _extra(item):
    payload = getattr(item, "extra", None)
    if payload is None:
        return {}
    fields = payload.fields if hasattr(payload, "fields") else {}
    return {k: v for k, v in fields.items()
            if v not in (0, -1, False) and k != "reference"}


class ACrackIsAThingNotASwitch(unittest.TestCase):
    """`#SPR408.MAP`, the canonical single, read to the field."""

    def setUp(self):
        self.disk = _map(SINGLES / "#SPR408.MAP")

    def test_the_crack_is_a_thing_that_reports_impact(self):
        # spr0: type 408, tile 1127, cstat 722, THING statnum 4, and the
        # trigger is Impact -- damage landing -- not Vector, which is a
        # hitscan crossing. That one field is why the zoo's did nothing.
        sprite = self.disk.sprites[0]
        self.assertEqual(int(sprite.fields["type"]), 408)
        self.assertEqual(int(sprite.fields["picnum"]), 1127)
        self.assertEqual(int(sprite.fields["cstat"]), 722)
        self.assertEqual(int(sprite.fields["status"]), 4)
        extra = _extra(sprite)
        self.assertEqual(int(extra["tx_id"]), 100)
        self.assertEqual(int(extra["command"]), 1)
        self.assertTrue(extra["trigger_impact"])
        self.assertNotIn("trigger_vector", extra)

    def test_a_cascade_of_exploders_makes_it_blow(self):
        # Three type-459 puffs on the crack's own channel, staggered. The
        # zoo omitted them entirely, so its wall would have vanished in
        # silence even once the trigger was right.
        puffs = [s for s in self.disk.sprites if int(s.fields["type"]) == 459]
        self.assertEqual(len(puffs), 3)
        for puff in puffs:
            self.assertEqual(int(puff.fields["picnum"]), 908)
            self.assertEqual(int(puff.fields["status"]), 11)
            self.assertEqual(int(_extra(puff)["rx_id"]), 100)
        self.assertEqual(sorted(int(_extra(p).get("wait_time", 0))
                                for p in puffs), [1, 1, 2])

    def test_the_sectors_collapse_on_the_same_channel(self):
        live = [i for i, s in enumerate(self.disk.sectors)
                if int(s.fields["type"]) == 600]
        self.assertEqual(live, [2, 3])
        for sector_id in live:
            self.assertEqual(int(_extra(self.disk.sectors[sector_id])["rx_id"]),
                             100)

    def test_our_record_matches_the_oracle(self):
        from bloodmap.motion import crack_thing, exploder, thing_transmitter

        sprite = self.disk.sprites[0]
        built = crack_thing()
        for field in ("type", "picnum", "cstat", "status"):
            self.assertEqual(built[field], int(sprite.fields[field]), field)
        wiring = thing_transmitter(channel=100)
        self.assertEqual(wiring, _extra(sprite))
        puff = exploder(channel=100, wait=2)
        self.assertEqual(puff["behavior"], _extra(self.disk.sprites[2]))

    def test_the_second_oracle_differs_and_we_prefer_the_single(self):
        # ENVIRONMENT-EXPLODEWALL builds the same thing four fields apart:
        # cstat 464 rather than 722, no Once, exploders with no trigger_on
        # and a wider stagger. Recorded so the difference is a known fact
        # rather than a surprise the next time someone reads it.
        other = _map(VANILLA / "ENVIRONMENT-EXPLODEWALL.map")
        crack = other.sprites[4]
        self.assertEqual(int(crack.fields["type"]), 408)
        self.assertEqual(int(crack.fields["cstat"]), 464)
        self.assertEqual(int(crack.fields["status"]), 4)
        self.assertTrue(_extra(crack)["trigger_impact"])
        self.assertNotIn("trigger_once", _extra(crack))

    def test_the_gate_catches_a_switch_wired_crack(self):
        from bloodmap.motion import thing_faults

        disk = _map(SINGLES / "#SPR408.MAP")
        self.assertEqual(thing_faults(disk), [])
        #: exactly what the zoo shipped: a hitscan trigger on a thing
        extra = disk.sprites[0].extra.fields
        extra["trigger_impact"] = 0
        extra["trigger_vector"] = 1
        faults = thing_faults(disk)
        self.assertTrue(faults)
        self.assertIn("hitscan crossing", " ".join(faults))

    def test_the_zoo_now_carries_the_full_record(self):
        from bloodmap.motion import thing_faults

        zoo = _zoo()
        self.assertEqual(thing_faults(zoo), [])
        cracks = [s for s in zoo.sprites if int(s.fields["type"]) == 408]
        puffs = [s for s in zoo.sprites if int(s.fields["type"]) == 459]
        self.assertEqual(len(cracks), 1)
        self.assertEqual(len(puffs), 3)
        self.assertEqual(int(cracks[0].fields["cstat"]), 722)
        self.assertEqual(int(cracks[0].fields["status"]), 4)


class AKeyPickupWearsTheKeyItGrants(unittest.TestCase):
    """Readability, mined over the campaign: 95 pickups, zero exceptions."""

    def test_the_world_tile_is_derived_from_the_item_type(self):
        from bloodmap.keys import KEY_ITEM_TYPE, world_picnum

        for key, kind in KEY_ITEM_TYPE.items():
            self.assertEqual(world_picnum(key), 2452 + kind)

    def test_a_campaign_pickup_and_its_lock_agree(self):
        # The oracle pair: E1M1 grants the skull key and the pickup wears the
        # skull key's tile.
        from bloodmap.keys import KEY_ITEM_TYPE, pickup_art_faults

        campaign = Path("maps/blood/campaign/E1M1.MAP")
        disk = _map(campaign)
        self.assertEqual(pickup_art_faults(disk), [])
        found = {int(s.fields["type"]): int(s.fields["picnum"])
                 for s in disk.sprites
                 if int(s.fields["type"]) in KEY_ITEM_TYPE.values()}
        self.assertTrue(found, "E1M1 has no key pickup")

    def test_the_check_catches_a_mismatch(self):
        from bloodmap.keys import pickup_art_faults

        zoo = _zoo()
        self.assertEqual(pickup_art_faults(zoo), [])
        #: reintroduce the exact defect the owner walked into: the moon key
        #: wearing the skull key's art
        for sprite in zoo.sprites:
            if int(sprite.fields["type"]) == 105:
                sprite.fields["picnum"] = 2552
                break
        faults = pickup_art_faults(zoo)
        self.assertTrue(faults)
        self.assertIn("should be 2557", faults[0])


class ASecretIsCreditedWithANumber(unittest.TestCase):
    """`OTHERSECTORSFX-SECRETS.map`, and the two system channels."""

    def setUp(self):
        self.disk = _map(VANILLA / "OTHERSECTORSFX-SECRETS.map")

    def test_the_credit_carries_a_numeric_command(self):
        # kChannelSecretFound is 2 and kCmdNumberic is 64: command 64 means
        # secret 0, 65 means secret 1. The zoo sent command 1, which is
        # kCmdOn -- a verb where the counter wants a number.
        s2, s3 = _extra(self.disk.sectors[2]), _extra(self.disk.sectors[3])
        for extra, command in ((s2, 64), (s3, 65)):
            self.assertEqual(int(extra["tx_id"]), 2)
            self.assertEqual(int(extra["command"]), command)
            self.assertTrue(extra["trigger_enter"])
            self.assertTrue(extra["trigger_once"])
            self.assertTrue(extra["dude_lockout"])

    def test_the_level_declares_its_total(self):
        # Sprite 0 listens on level start and transmits the count on channel
        # 1. Every campaign map checked does the same.
        extra = _extra(self.disk.sprites[0])
        self.assertEqual(int(extra["tx_id"]), 1)
        self.assertEqual(int(extra["rx_id"]), 7)
        self.assertEqual(int(extra["command"]), 66)

    def test_our_records_match_the_oracle(self):
        from bloodmap.motion import secret_credit, secret_total

        self.assertEqual(secret_credit(0), _extra(self.disk.sectors[2]))
        self.assertEqual(secret_credit(1), _extra(self.disk.sectors[3]))
        self.assertEqual(secret_total(2), _extra(self.disk.sprites[0]))

    def test_the_gate_catches_a_verb_and_a_missing_total(self):
        from bloodmap.motion import secret_faults

        self.assertEqual(secret_faults(self.disk), [])
        disk = _map(VANILLA / "OTHERSECTORSFX-SECRETS.map")
        disk.sectors[2].extra.fields["command"] = 1
        disk.sprites[0].extra.fields["tx_id"] = 0
        faults = secret_faults(disk)
        self.assertTrue(any("is a verb" in f for f in faults))
        self.assertTrue(any("nothing sets the level total" in f
                            for f in faults))

    def test_the_zoo_credits_its_one_secret_properly(self):
        from bloodmap.motion import secret_faults

        self.assertEqual(secret_faults(_zoo()), [])


class ACurtainIsCalibratedForItsClosedSpan(unittest.TestCase):
    """DOOR-CURTAINS, measured: the repeat belongs to the OFF pose."""

    def test_the_tutorial_wears_its_fabric_at_natural_scale_when_closed(self):
        # s3 and s53 carry x_repeat 16 over a 1024 CLOSED span on tile 146,
        # which is 32 wide: length / x_repeat == 2 * tile_width exactly.
        import math

        from bloodmap.motion_sim import blood_poses
        from bloodmap.texture_align import NATURAL_TEXEL_SCALE, texel_scale

        disk = _map(VANILLA / "DOOR-CURTAINS.map")
        for sector_id in (3, 53):
            closed, _open = blood_poses(disk, sector_id)
            start = int(disk.sectors[sector_id].fields["wall_ptr"])
            count = int(disk.sectors[sector_id].fields["wall_count"])
            for index in range(count):
                fields = disk.walls[start + index].fields
                if int(fields["picnum"]) != 146:
                    continue
                a, b = closed[index], closed[(index + 1) % count]
                span = math.hypot(b[0] - a[0], b[1] - a[1])
                self.assertAlmostEqual(
                    texel_scale(span, 32, int(fields["x_repeat"])),
                    NATURAL_TEXEL_SCALE, delta=0.01,
                    msg=f"s{sector_id} wall {start + index}")

    def test_the_drawn_span_is_NOT_the_one_to_calibrate_against(self):
        # The same walls at the drawn (ON) pose are eight times denser. Sizing
        # the texture to what the file shows is what left ours 48x stretched.
        import math

        from bloodmap.motion_sim import blood_poses
        from bloodmap.texture_align import texel_scale

        disk = _map(VANILLA / "DOOR-CURTAINS.map")
        _closed, drawn = blood_poses(disk, 3)
        start = int(disk.sectors[3].fields["wall_ptr"])
        count = int(disk.sectors[3].fields["wall_count"])
        #: the fin's two SIDES, which are what stretch
        sides = [i for i in range(count)
                 if int(disk.walls[start + i].fields["picnum"]) == 146
                 and int(disk.walls[start + i].fields["x_repeat"]) > 1]
        self.assertEqual(len(sides), 2)
        for index in sides:
            fields = disk.walls[start + index].fields
            a, b = drawn[index], drawn[(index + 1) % count]
            span = math.hypot(b[0] - a[0], b[1] - a[1])
            self.assertLess(texel_scale(span, 32, int(fields["x_repeat"])),
                            1.0, f"wall {start + index}")

    def test_our_curtain_hangs_naturally_closed_and_gathers_open(self):
        import math

        from bloodmap.motion_sim import blood_poses
        from bloodmap.texture_align import NATURAL_TEXEL_SCALE, texel_scale

        from bloodmap.motion import flagged_walls

        zoo = _zoo()
        #: the ONE-leaf curtain specifically, because the assertion is about
        #: that dialect. The pair is exact too now -- it read 1.67 while its
        #: leaves were travelling outward past their own jambs, and 2.0 once
        #: the flags were the way DOOR-CURTAINSD s2 has them.
        sector_id = next(
            i for i, s in enumerate(zoo.sectors)
            if int(s.fields["type"]) == 614
            and len(flagged_walls(zoo, i)) == 1
            and any(int(zoo.walls[w].fields["picnum"]) == 146
                    for w in range(int(s.fields["wall_ptr"]),
                                   int(s.fields["wall_ptr"])
                                   + int(s.fields["wall_count"]))))
        closed, drawn = blood_poses(zoo, sector_id)
        start = int(zoo.sectors[sector_id].fields["wall_ptr"])
        count = int(zoo.sectors[sector_id].fields["wall_count"])
        checked = 0
        for index in range(count):
            fields = zoo.walls[start + index].fields
            if int(fields["picnum"]) != 146:
                continue
            repeat = int(fields["x_repeat"])
            a, b = closed[index], closed[(index + 1) % count]
            shut = math.hypot(b[0] - a[0], b[1] - a[1])
            c, d = drawn[index], drawn[(index + 1) % count]
            open_span = math.hypot(d[0] - c[0], d[1] - c[1])
            self.assertAlmostEqual(texel_scale(shut, 32, repeat),
                                   NATURAL_TEXEL_SCALE, delta=0.05)
            self.assertLessEqual(texel_scale(open_span, 32, repeat),
                                 NATURAL_TEXEL_SCALE)
            checked += 1
        self.assertEqual(checked, 3)

    def test_only_the_fabric_wears_the_fabric(self):
        # The tutorial's s3 is eight walls and exactly three carry tile 146;
        # painting the whole region with cloth put curtain on the door frame.
        disk = _map(VANILLA / "DOOR-CURTAINS.map")
        start = int(disk.sectors[3].fields["wall_ptr"])
        tiles = [int(disk.walls[start + i].fields["picnum"]) for i in range(8)]
        self.assertEqual(sum(1 for t in tiles if t == 146), 3)


if __name__ == "__main__":
    unittest.main()


class TheCurtainsConformanceActuallyRuns(unittest.TestCase):
    """The repeat law, gated -- and the gate proved able to fail.

    `measure_curtain` was written for the opposed-cap model and routed on the
    payload shape that model produces. When the constructor was rebuilt to
    the tutorial's fin, the shape changed and the check silently stopped
    running: the zoo reported thirteen of thirteen conforming because the
    curtain was never asked. It is routed on the fabric TILE now, which does
    not change when the topology does.
    """

    def test_the_zoo_curtain_conforms(self):
        from bloodmap.conformance import measure_curtain

        zoo = _zoo()
        sector = self._curtain(zoo)
        found = measure_curtain(zoo, sector, declared=[sector])
        self.assertEqual([d.relation for d in found.deviations], [])
        self.assertEqual(found.measured["leaves"], 1)
        #: and the two-leaf exhibit beside it conforms too
        pair = self._curtain(zoo, leaves=2)
        paired = measure_curtain(zoo, pair, declared=[pair])
        self.assertEqual([d.relation for d in paired.deviations], [])
        self.assertEqual(paired.measured["leaves"], 2)
        self.assertEqual(found.measured["motion_set"], [sector])
        #: and the fabric is where a body can see it
        self.assertGreaterEqual(found.measured["fabric_visible"], 1)

    def _curtain(self, disk, leaves=1):
        """The zoo's curtain with `leaves` leaves.

        There are two now -- a one-leaf CURTAIN and a two-leaf CURTAIN PAIR --
        so "the first 614 sector wearing 146" stopped meaning anything. These
        tests are about the one-leaf dialect and say so.
        """
        from bloodmap.motion import flagged_walls

        for index, sector in enumerate(disk.sectors):
            if int(sector.fields["type"]) != 614:
                continue
            start = int(sector.fields["wall_ptr"])
            count = int(sector.fields["wall_count"])
            if not any(int(disk.walls[i].fields["picnum"]) == 146
                       for i in range(start, start + count)):
                continue
            if len(flagged_walls(disk, index)) == leaves:
                return index
        self.fail(f"the zoo has no {leaves}-leaf curtain")

    def test_a_fabric_sized_to_the_DRAWN_span_is_caught(self):
        # The exact defect the owner walked into: the repeat authored for the
        # gathered bundle the file is saved at, which came out at 48 times
        # natural stretch when the curtain was drawn across.
        from bloodmap.conformance import measure_curtain

        zoo = _zoo()
        sector = self._curtain(zoo)
        start = int(zoo.sectors[sector].fields["wall_ptr"])
        count = int(zoo.sectors[sector].fields["wall_count"])
        for index in range(start, start + count):
            if int(zoo.walls[index].fields["picnum"]) == 146:
                zoo.walls[index].fields["x_repeat"] = 1
        found = measure_curtain(zoo, sector)
        self.assertTrue(found.deviations)
        self.assertIn("closed-span texel scale",
                      [d.relation for d in found.deviations])

    def test_a_curtain_that_deforms_something_undeclared_is_caught(self):
        # The relation is "the motion set is what the construct DECLARED".
        # Declaring nothing is not a defect -- three of the four originals
        # legitimately move a neighbour -- but declaring one thing and
        # moving two is.
        from bloodmap.conformance import measure_curtain

        zoo = _zoo()
        sector = self._curtain(zoo)
        found = measure_curtain(zoo, sector, declared=[sector, 999])
        self.assertIn("members", [d.relation for d in found.deviations])

    def test_the_sweep_actually_reaches_the_curtain(self):
        # The regression that hid all of the above: a construct that dodges
        # its own check by changing shape.
        import importlib.util
        from pathlib import Path

        spec = importlib.util.spec_from_file_location(
            "_zoo_sweep", Path("projects/pattern-zoo/sweep.py"))
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        zoo = _zoo()
        sector = self._curtain(zoo)
        checks = module._for_sector(zoo, sector, "curtain")
        self.assertIn("measure_curtain", [c.__name__ for c in checks])
