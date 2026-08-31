"""Conditional traversability: which ways are gated, and what opens them.

The synthetic map below is the specification the task named: one keyed door
and one crack, and exactly two conditional crossings with the right causes.
An unwired mechanism has to yield none, which is not a formality -- before
that clause existed, E1M3's eight type-0 sectors carrying stale XSECTOR z
endpoints produced 60 conditional edges opened by nobody.
"""

import unittest

from bloodmap.conditional import (
    Action, ConditionalError, Held, build_graph, conditional_edges,
    frontier, passable, rest_state, route_edges, transmitters,
    what_becomes_reachable,
)
from bloodmap.effects import STEP_UP
from bloodmap.doors import PLAYER_HEIGHT

try:
    from bloodmap.patterns import list_corpus_maps
    CORPUS = bool(list_corpus_maps(population="blood-campaign"))
except Exception:
    CORPUS = False


# ---------------------------------------------------------------------------
# A map small enough to reason about by hand
# ---------------------------------------------------------------------------

class Extra:
    def __init__(self, fields):
        self.fields = fields


class Item:
    def __init__(self, fields, extra=None):
        self.fields = fields
        self.extra = Extra(extra) if extra is not None else None


def wall(x, y, next_sector=-1, point2=0, extra=None):
    return Item({"x": x, "y": y, "next_sector": next_sector, "next_wall": -1,
                 "point2": point2, "picnum": 0, "over_picnum": 0, "shade": 0,
                 "pal": 0, "x_repeat": 8, "y_repeat": 8, "cstat": 0,
                 "type": 0, "hitag": 0, "x_panning": 0, "y_panning": 0},
                extra)


def sprite_fields(type_id, picnum, *, sector, x=0, y=0, status=0):
    return {"type": type_id, "picnum": picnum, "sector": sector, "cstat": 0,
            "x": x, "y": y, "z": 0, "angle": 0, "pal": 0, "shade": 0,
            "x_repeat": 8, "y_repeat": 8, "status": status, "hitag": 0,
            "owner": -1, "index": 0, "clipdist": 32, "detail": 0, "flags": 0,
            "initial_type": type_id, "x_offset": 0, "y_offset": 0,
            "y_velocity": 0, "extra": -1}


def motion_sector(wall_ptr, *, floor_z, ceiling_z, off_ceiling, on_ceiling,
                  rx_id=0, key=0, state=0, walls=4, **triggers):
    extra = {"rx_id": rx_id, "tx_id": 0, "key": key, "state": state,
             "busy_time_a": 10, "off_floor_z": floor_z, "on_floor_z": floor_z,
             "off_ceiling_z": off_ceiling, "on_ceiling_z": on_ceiling,
             **triggers}
    return Item({"type": 600, "floor_z": floor_z, "ceiling_z": ceiling_z,
                 "wall_ptr": wall_ptr, "wall_count": walls,
                 "floor_picnum": 0, "ceiling_picnum": 0}, extra)


def plain_sector(wall_ptr, *, floor_z=0, ceiling_z=-40000, walls=4):
    return Item({"type": 0, "floor_z": floor_z, "ceiling_z": ceiling_z,
                 "wall_ptr": wall_ptr, "wall_count": walls,
                 "floor_picnum": 0, "ceiling_picnum": 0}, None)


class Disk:
    """Four rooms in a row: start, keyed door, middle, cracked door, end."""

    def __init__(self, sectors, walls, sprites):
        self.sectors, self.walls, self.sprites = sectors, walls, sprites
        self.header = {"start_x": 0, "start_y": 0, "start_z": 0,
                       "start_angle": 0, "start_sector": 0}


def synthetic(*, key_on_door=6, crack_channel=120, unwire_the_door=False,
              also_a_switch=False):
    """start(0) -- door(1) -- middle(2) -- cracked(3) -- end(4).

    Both mechanisms are shut at rest: ceiling flush with the floor. The door
    is worked by pushing its wall and needs a key; the cracked one listens on
    a channel a crack transmits on.
    """
    sectors, walls, sprites = [], [], []

    def room(index, neighbours):
        start = len(walls)
        for offset, neighbour in enumerate(neighbours):
            walls.append(wall(index * 1000 + offset * 10, 0,
                              next_sector=neighbour,
                              point2=start + (offset + 1) % len(neighbours)))
        return start

    ptr0 = room(0, [-1, -1, -1, 1])
    ptr1 = room(1, [0, -1, -1, 2])
    ptr2 = room(2, [1, -1, -1, 3])
    ptr3 = room(3, [2, -1, -1, 4])
    ptr4 = room(4, [3, -1, -1, -1])

    sectors.append(plain_sector(ptr0))
    sectors.append(motion_sector(
        ptr1, floor_z=0, ceiling_z=0, off_ceiling=0, on_ceiling=-40000,
        key=key_on_door,
        **({} if unwire_the_door else {"trigger_wall_push": 1})))
    sectors.append(plain_sector(ptr2))
    sectors.append(motion_sector(
        ptr3, floor_z=0, ceiling_z=0, off_ceiling=0, on_ceiling=-40000,
        rx_id=crack_channel, trigger_once=1))
    sectors.append(plain_sector(ptr4))

    #: The crack, in the middle room, transmitting on the door's channel.
    sprites.append(Item(sprite_fields(408, 1127, sector=2, x=2000),
                        {"tx_id": crack_channel, "command": 1}))
    #: The key, in the start room.
    sprites.append(Item(sprite_fields(105, 2552, sector=0, x=100, status=3), None))
    if also_a_switch:
        #: A second way to the same door, and an ordinary one. Now the crack
        #: is not the only route, so the change it makes is not one-way.
        sprites.append(Item(sprite_fields(20, 1070, sector=2, x=2500),
                            {"tx_id": crack_channel}))
    return Disk(sectors, walls, sprites)


class SyntheticMapTest(unittest.TestCase):
    """The specification: one keyed door, one crack, two conditional edges."""

    def test_one_keyed_door_and_one_crack_yield_exactly_two_routes(self):
        edges, summary = conditional_edges(synthetic())
        self.assertEqual(summary["z_motion_mechanisms"], 2)
        self.assertEqual(summary["inert_no_cause"], 0)
        routes = route_edges(edges)
        self.assertEqual(len(routes), 2)
        self.assertEqual([route["mechanism"] for route in routes], [1, 3])
        self.assertEqual([route["joins"] for route in routes], [[0, 2], [2, 4]])
        self.assertEqual(routes[0]["requires_key_name"], "moon")
        self.assertFalse(routes[0]["irreversible"])
        self.assertIsNone(routes[1]["requires_key"])
        self.assertTrue(routes[1]["irreversible"])
        self.assertEqual([cause["type_id"] for cause in routes[1]["causes"]], [408])

    def test_each_route_is_two_rooms_joined_by_four_directed_crossings(self):
        # A door sector has a portal on each side, and climbing and falling
        # are not the same crossing, so one route is four edges underneath.
        edges, _ = conditional_edges(synthetic())
        conditional = [edge for edge in edges if edge.verdict == "conditional"]
        self.assertEqual(len(conditional), 8)
        self.assertEqual({edge.mechanism for edge in conditional}, {1, 3})

    def test_the_keyed_door_carries_its_key_and_its_push(self):
        edges, _ = conditional_edges(synthetic())
        door = [e for e in edges if e.mechanism == 1 and e.verdict == "conditional"]
        self.assertTrue(door)
        for edge in door:
            self.assertEqual(edge.requires_key, 6)
            self.assertEqual([cause.trigger for cause in edge.causes], ["push"])
            self.assertFalse(edge.irreversible)

    def test_the_cracked_door_carries_the_crack_and_is_irreversible(self):
        edges, _ = conditional_edges(synthetic())
        cracked = [e for e in edges if e.mechanism == 3 and e.verdict == "conditional"]
        self.assertTrue(cracked)
        for edge in cracked:
            self.assertEqual(edge.requires_key, 0)
            self.assertTrue(edge.irreversible)
            self.assertEqual([cause.type_id for cause in edge.causes], [408])
            self.assertEqual([cause.trigger for cause in edge.causes], ["shot"])
            self.assertEqual([cause.channel for cause in edge.causes], [120])

    def test_an_unwired_mechanism_yields_no_conditional_edge(self):
        # Nothing reaches it: no channel, no pushable wall, no trigger on
        # entry. Its state can never change, so it gates nothing.
        edges, summary = conditional_edges(synthetic(unwire_the_door=True))
        self.assertEqual(summary["inert_no_cause"], 1)
        self.assertEqual({edge.mechanism for edge in edges}, {3})
        self.assertEqual([route["mechanism"] for route in route_edges(edges)], [3])

    def test_a_channel_nobody_transmits_on_leaves_the_door_inert(self):
        edges, summary = conditional_edges(
            synthetic(crack_channel=0, unwire_the_door=True))
        self.assertEqual(summary["inert_no_cause"], 2)
        self.assertEqual(edges, [])


    def test_a_barrier_with_an_ordinary_second_cause_is_not_irreversible(self):
        # Irreversible means every way to it is one-way. A door a crack opens
        # and a switch also opens comes back, so calling it irreversible on
        # the strength of the crack alone overstates what the map says.
        edges, _ = conditional_edges(synthetic(also_a_switch=True))
        cracked = [e for e in edges
                   if e.mechanism == 3 and e.verdict == "conditional"]
        self.assertTrue(cracked)
        self.assertEqual({len(edge.causes) for edge in cracked}, {2})
        self.assertFalse(any(edge.irreversible for edge in cracked))
        route = [r for r in route_edges(edges) if r["mechanism"] == 3][0]
        self.assertFalse(route["irreversible"])

    def test_a_route_is_irreversible_only_when_all_of_it_is(self):
        edges, _ = conditional_edges(synthetic())
        route = [r for r in route_edges(edges) if r["mechanism"] == 3][0]
        self.assertTrue(route["irreversible"])
        mixed = [e for e in edges if e.mechanism == 3]
        mixed[0].irreversible = False
        self.assertFalse(route_edges(mixed)[0]["irreversible"])


class ActionTest(unittest.TestCase):
    def test_shooting_the_crack_opens_the_way_and_says_why(self):
        # From a state where the middle room has already been reached: the
        # crack is behind the keyed door, so with nothing held it opens a way
        # nobody can get to.
        disk = synthetic()
        graph = build_graph(disk)
        report = what_becomes_reachable(
            disk, Action(kind="destroy", index=0, channel=120),
            already=Held(keys=frozenset({6}), operated=frozenset({1})),
            graph=graph)
        self.assertIn(4, report["newly_reachable"])
        chain = report["why"][0]
        self.assertEqual(chain["trigger"]["type_id"], 408)
        self.assertEqual(chain["channel"]["id"], 120)
        self.assertEqual(chain["mechanism"]["sector"], 3)
        self.assertTrue(chain["irreversible"])

    def test_the_keyed_door_stays_shut_without_the_key(self):
        disk = synthetic()
        graph = build_graph(disk)
        opened = what_becomes_reachable(
            disk, Action(kind="operate", index=1), graph=graph)
        self.assertEqual(opened["newly_reachable"], [])

    def test_the_keyed_door_opens_once_the_key_is_held(self):
        disk = synthetic()
        graph = build_graph(disk)
        opened = what_becomes_reachable(
            disk, Action(kind="operate", index=1),
            already=Held(keys=frozenset({6})), graph=graph)
        self.assertIn(2, opened["newly_reachable"])

    def test_the_chain_names_a_system_channel_where_there_is_one(self):
        disk = synthetic(crack_channel=4)
        report = what_becomes_reachable(
            disk, Action(kind="destroy", index=0, channel=4))
        self.assertEqual(report["why"][0]["channel"]["name"], "level_exit_normal")

    def test_a_channel_driven_mechanism_is_not_offered_as_hand_worked(self):
        # The crack's door listens on a channel, so the thing to do is shoot
        # the crack -- not walk up to the door and operate it. Offering both
        # invents an action the map does not contain.
        disk = synthetic()
        graph = build_graph(disk)
        held = Held(keys=frozenset({6}), operated=frozenset({1}))
        offered = graph.available_actions(held, graph.reachable(held))
        self.assertIn("destroy", {action.kind for action in offered})
        self.assertNotIn(3, {action.index for action in offered
                             if action.kind == "operate"})

    def test_a_hand_worked_mechanism_is_offered_only_from_beside_it(self):
        disk = synthetic()
        graph = build_graph(disk)
        offered = graph.available_actions(Held(), graph.reachable(Held()))
        operate = [action for action in offered if action.kind == "operate"]
        self.assertEqual([action.index for action in operate], [1])
        self.assertEqual(operate[0].where, 0)

    def test_the_frontier_reaches_the_end_room_in_order(self):
        disk = synthetic()
        walk = frontier(disk)
        self.assertEqual(walk["at_rest_reachable"], 1)
        self.assertEqual(walk["finally_reachable"], 5)
        self.assertGreater(len(walk["rounds"]), 1)


class CrossingTest(unittest.TestCase):
    """Climbing is capped and falling is not, so a crossing is directed."""

    def record(self, **over):
        base = {"off_floor_z": 0, "on_floor_z": 0, "off_ceiling_z": -40000,
                "on_ceiling_z": -40000, "state": 0, "floor_z": 0,
                "ceiling_z": -40000}
        base.update(over)
        return base

    def test_a_flush_gap_admits_nobody(self):
        record = self.record(off_ceiling_z=0)
        self.assertFalse(passable(record, "off", 0, leaving=True))

    def test_a_body_steps_up_no_further_than_the_engine_allows(self):
        record = self.record()
        self.assertTrue(passable(record, "off", -STEP_UP, leaving=True))
        self.assertFalse(passable(record, "off", -STEP_UP - 1, leaving=True))

    def test_a_body_falls_as_far_as_it_likes(self):
        # Blood's z grows downward, so a larger number is further down.
        record = self.record()
        self.assertTrue(passable(record, "off", 1_000_000, leaving=True))

    def test_the_two_directions_of_one_crossing_can_differ(self):
        record = self.record()
        drop = 100_000
        self.assertTrue(passable(record, "off", drop, leaving=True))
        self.assertFalse(passable(record, "off", drop, leaving=False))


class RestStateTest(unittest.TestCase):
    def test_the_state_field_decides_when_it_is_set(self):
        self.assertEqual(rest_state({
            "state": 1, "floor_z": 0, "ceiling_z": 0,
            "on_floor_z": 0, "on_ceiling_z": 0,
            "off_floor_z": 0, "off_ceiling_z": 0}), "on")

    def test_a_sector_built_in_its_on_pose_reads_as_on(self):
        self.assertEqual(rest_state({
            "state": 0, "floor_z": 10, "ceiling_z": -50,
            "on_floor_z": 10, "on_ceiling_z": -50,
            "off_floor_z": 10, "off_ceiling_z": 0}), "on")

    def test_otherwise_it_is_off(self):
        self.assertEqual(rest_state({
            "state": 0, "floor_z": 10, "ceiling_z": 10,
            "on_floor_z": 10, "on_ceiling_z": -50,
            "off_floor_z": 10, "off_ceiling_z": 10}), "off")


class TransmitterTest(unittest.TestCase):
    def test_sectors_transmit_too(self):
        # A `trigger_enter` room that opens a door elsewhere has no sprite
        # and no wall; reading only sprites loses it entirely.
        disk = synthetic()
        disk.sectors[2].extra = Extra({"tx_id": 77, "trigger_enter": 1})
        wires = transmitters(disk)
        self.assertIn(77, wires)
        self.assertEqual(wires[77][0].kind, "sector")
        self.assertEqual(wires[77][0].trigger, "touch")


@unittest.skipUnless(CORPUS, "the Blood corpus is not present")
class CampaignTest(unittest.TestCase):
    def _map(self, name):
        from bloodmap.format import read_map
        return read_map([item for item in list_corpus_maps(population="blood-campaign")
                         if item.path.stem == name][0].path)

    def test_the_e1m4_crack_opens_two_flush_sectors(self):
        # Verified against the raw XSECTOR and against the editor renderer,
        # which refuses to place a viewpoint in sector 276 for want of
        # standing clearance.
        disk = self._map("E1M4")
        report = what_becomes_reachable(
            disk, Action(kind="destroy", index=373, channel=119))
        mechanisms = {edge["mechanism"] for edge in report["crossings_opened"]}
        self.assertTrue({276, 277} <= mechanisms)
        self.assertTrue(all(edge["irreversible"]
                            for edge in report["crossings_opened"]))

    def test_the_e1m4_moon_door_needs_the_moon_key(self):
        disk = self._map("E1M4")
        graph = build_graph(disk)
        shut = [edge for edge in graph.edges if edge.mechanism == 295]
        self.assertTrue(shut)
        self.assertTrue(all(edge.requires_key == 6 for edge in shut))

    def test_the_e1m3_lift_reads_as_carrying_a_body_between_levels(self):
        disk = self._map("E1M3")
        graph = build_graph(disk)
        lift = [edge for edge in graph.edges if edge.mechanism == 241]
        self.assertTrue(lift)
        self.assertEqual({edge.delta["reads_as"] for edge in lift},
                         {"carries a body between levels"})

    def test_rotate_and_slide_are_scoped_out_rather_than_answered(self):
        disk = self._map("E1M1")
        _, summary = conditional_edges(disk)
        self.assertGreater(summary["scoped_out_rotate_slide"], 0)


if __name__ == "__main__":
    unittest.main()
