"""Look at the city: named poses rendered through the XMapEdit observer.

The refinement loop's first step, made cheap.  Poses are written in plan
units and aimed at a target point, so they read like directions ("stand on
the quay, face the avenue") and survive a street-width change.  Reference
frames from the campaign are rendered by the same call with the same
settings, which is the only way a side-by-side means anything.

    python projects/blood-city/level/look.py --set pilot
    python projects/blood-city/level/look.py --set fresh1 --tag i1
    python projects/blood-city/level/look.py --ref E3M1 --sectors 12,119 -o ref-e3m1

Never launches the game: the observer renders from a pose (owner rule).
"""

from __future__ import annotations

import argparse
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

from bloodmap.format import read_map
from bloodmap.corpus import corpus_map_path
from bloodmap.viewplan import angle_toward, eye_z, interior_point
from bloodmap.visual import ObservationRequest, Viewpoint, run_observation
from bloodmap.viewpoints import _contains, _sector_loops

PROJECT = pathlib.Path(__file__).resolve().parents[1]
CURRENT = PROJECT / "level" / "blood-city-current.MAP"
PU = 1024

#: Level horizon; the observer's horiz is Build's, 100 is level.
LEVEL, UP, DOWN = 100, 160, 40

#: Named poses in plan units: (x, y, look-at x, look-at y, horiz, note).
#: Fixed sets stay stable across iterations so before/after pairs line up;
#: fresh sets are added per iteration and never reused.
POSE_SETS = {
    #: The opening moment.  The monument is not a single object -- it is the
    #: first thing the player sees -- so its acceptance is the frame from the
    #: spawn at standing eye height, with the plaza behind it, the market
    #: hall's frontage and the avenue running north.
    "opening": {
        "spawn": (33.5, 53.0, 26.0, 45.0, LEVEL,
                  "the player's first frame: the spawn, facing the monument"),
        "spawn_wide": (33.5, 53.0, 30.0, 44.0, LEVEL,
                       "the same, the plaza and the avenue beyond"),
        "monument_read": (29.0, 49.0, 26.0, 45.0, LEVEL,
                          "half way to it, where the name should read"),
        "monument_close": (26.0, 48.5, 26.0, 45.0, LEVEL,
                           "at the foot of the steps"),
        "monument_side": (23.0, 47.5, 26.0, 45.0, LEVEL,
                          "from the plaza's west side"),
    },
    #: the owner, 2026-11-18: "Ship in a harbour is just a wooden rectangle,
    #: water should end with sky"
    #: the owner, 2026-11-18: "I would add these stained window glass
    #: decorative sprites also inside ... to have a feeling that you are
    #: really inside that church"
    "church_in": {
        "nave_north": (28.75, 29.5, 28.75, 23.0, LEVEL, "up the nave to the chancel"),
        "nave_east": (28.0, 27.0, 30.0, 27.4, UP, "the nave's east wall and clerestory"),
        "nave_west": (29.6, 26.5, 27.5, 27.0, UP, "the nave's west side over the aisle"),
        "apse": (29.4, 24.5, 29.4, 22.0, LEVEL, "the apse and its three lights"),
        "narthex": (30.9, 28.6, 32.3, 28.6, LEVEL, "the narthex's street wall"),
    },
    "crypt": {
        "antechamber": (30.3, 25.4, 31.2, 26.3, LEVEL, "the antechamber: the slab in its east wall"),
        "from_lift": (31.0, 26.5, 29.4, 29.0, LEVEL, "the crypt from where the slab lands", 61440),
        "sarcophagus": (28.2, 28.0, 29.6, 28.8, LEVEL, "the sarcophagus from the west aisle", 61440),
        "lid": (29.5, 29.6, 29.5, 28.0, DOWN, "down onto the lid from its foot", 61440),
        "plaques": (30.9, 27.2, 27.5, 29.0, LEVEL, "the west wall: plaques and cobwebs", 61440),
        "back": (27.8, 29.8, 31.2, 26.8, LEVEL, "the crypt from its far corner", 61440),
        "fuse": (30.9, 26.6, 31.0, 30.0, LEVEL, "down the east aisle: the barrels", 61440),
    },
    #: the owner, 2026-11-18: "We should have more windows in buildings
    #: around the city"
    "windows": {
        "theatre_out": (22.5, 1.6, 22.5, 4.0, LEVEL, "the auditorium's window from the street"),
        "theatre_in": (22.5, 5.6, 22.5, 3.0, LEVEL, "the same window from inside the auditorium"),
        "saloon_out": (1.6, 7.0, 4.0, 7.0, LEVEL, "the saloon back room's barred window from the street"),
        "saloon_in": (5.4, 7.0, 3.0, 7.0, LEVEL, "the same bars from inside"),
        "market_out": (1.8, 42.75, 3.5, 42.75, LEVEL, "the supermarket's window from the street"),
        "market_in": (5.2, 42.75, 3.0, 42.75, LEVEL, "the same window from inside"),
    },
    #: Gravesend Station, behind the north wall (floors: street 8192, hall
    #: and platform -12288)
    "railway": {
        "street_door": (16.9, 2.6, 14.4, -0.8, LEVEL, "the station's door and name from the street"),
        "hall": (17.6, -8.6, 9.5, -12.5, LEVEL, "the booking hall from the stair head", -12288),
        "office": (10.4, -12.0, 7.0, -12.3, LEVEL, "the booking window and its clerk", -12288),
        "gates": (13.0, -9.2, 13.0, -16.0, LEVEL, "through the gates to the carriage", -12288),
        "carriage": (20.5, -15.4, 13.5, -16.6, LEVEL, "the carriage along the platform", -12288),
        "locomotive": (21.0, -14.9, 26.5, -17.4, LEVEL, "the locomotive from the platform's east end", -12288),
        "car_door": (15.9, -14.8, 14.8, -16.6, LEVEL, "the carriage's door from the platform", -12288),
        "balcony": (27.6, -14.0, 25.4, -17.4, LEVEL, "the engine from the signal box's balcony", -32768),
        "signal_box": (27.6, -13.2, 27.6, -11.4, LEVEL, "the signal box and its lever", -32768),
        "signal_stair": (22.6, -13.4, 26.6, -13.0, LEVEL, "the stair up to the signal box", -12288),
        "waiting": (18.6, -10.8, 21.8, -13.2, LEVEL, "the waiting room", -12288),
        "tunnel_gate": (26.5, -21.8, 31.0, -20.6, LEVEL, "the gate in the tunnel's mouth", 2048),
        "goods": (38.6, -20.2, 43.0, -22.5, LEVEL, "the goods store", 2048),
        "nose": (28.6, -14.8, 25.0, -17.4, LEVEL, "the locomotive from ahead of it", -12288),
        "far_track": (7.0, -15.3, 14.0, -22.0, LEVEL, "the tracks from the platform's west end", -12288),
        "from_track": (4.5, -21.5, 14.0, -18.0, LEVEL, "the train from down on the track", 2048),
        "inside": (10.6, -17.0, 19.5, -17.2, LEVEL, "inside the carriage", -12288),
    },
    #: ONE THING PER VIEW, for `tools.critique things`: a reader who is
    #: told nothing names what each shows, and the name is held against
    #: what it was built to be (knowledge/blood/studies/station/things.json)
    "railway_things": {
        "t_engine_side": (21.0, -14.9, 26.5, -17.4, LEVEL, "thing", -12288),
        "t_engine_nose": (28.6, -14.8, 25.0, -17.4, LEVEL, "thing", -12288),
        "t_car_door": (15.9, -14.8, 14.8, -16.6, LEVEL, "thing", -12288),
        "t_car_side": (12.6, -14.9, 12.4, -16.6, LEVEL, "thing", -12288),
        "t_car_inside": (10.6, -17.0, 19.5, -17.2, LEVEL, "thing", -12288),
        "t_track": (4.5, -21.5, 14.0, -18.0, LEVEL, "thing", 2048),
        "t_tunnel": (33.0, -20.5, 37.5, -20.5, LEVEL, "thing", 2048),
        "t_bench": (11.0, -13.4, 11.0, -11.7, LEVEL, "thing", -12288),
        "t_waiting": (18.6, -10.8, 21.8, -13.2, LEVEL, "thing", -12288),
        "t_gate": (26.5, -21.8, 31.0, -20.6, LEVEL, "thing", 2048),
        "t_goods": (38.6, -20.2, 43.0, -22.5, LEVEL, "thing", 2048),
        "t_balcony": (24.0, -15.6, 28.0, -14.3, LEVEL, "thing", -12288),
        "t_ticket": (10.4, -12.0, 7.0, -12.3, LEVEL, "thing", -12288),
        "t_gates": (11.2, -12.6, 10.4, -14.6, LEVEL, "thing", -12288),
        "t_hall": (17.6, -8.6, 9.5, -12.5, LEVEL, "thing", -12288),
    },
    "saloon": {
        "bar": (9.4, 12.4, 6.5, 9.5, LEVEL, "the saloon from its south-east corner: the bar"),
        "along": (4.6, 10.6, 9.5, 10.2, LEVEL, "along the stools"),
    },
    "house": {
        "to_stage": (25.4, 7.5, 19.5, 7.5, LEVEL, "the auditorium toward the stage"),
        "up": (24.5, 9.5, 20.0, 6.0, UP, "the height of the house"),
    },
    "sea_ends": {
        "east_end": (46.0, 55.0, 52.0, 58.0, LEVEL, "the quay's east end: the headland"),
        "west_end": (10.0, 55.0, 4.5, 58.0, LEVEL, "the quay's west end: the headland"),
        "out": (30.0, 55.2, 41.0, 66.0, LEVEL, "out to the skerry"),
        "piles": (22.0, 55.2, 26.0, 60.0, LEVEL, "the jetty from the quay"),
        "jetty_end": (25.5, 60.5, 22.0, 57.0, LEVEL, "back along the jetty to the ship and the town"),
    },
    #: the owner's walk of 2026-11-19 (second): the jetty, the ship's
    #: crates, the flanks over the rock, the hall's back door
    "walk_1119": {
        "jetty": (25.5, 54.6, 25.5, 60.0, DOWN, "along the jetty from the quay"),
        "crates": (18.6, 58.4, 20.6, 58.4, LEVEL, "the crates on the ship's deck", 1024),
        "window_in": (8.0, 44.0, 14.0, 42.5, LEVEL, "the hall's display windows from inside"),
        "window_side": (7.0, 43.0, 7.0, 40.0, LEVEL, "the hall's side gallery from inside"),
        "mall_niche": (45.0, 45.0, 45.0, 41.0, LEVEL, "a shop unit's back wall"),
        "flank_east": (44.0, 55.0, 52.0, 59.0, LEVEL, "the building over the east headland"),
        "flank_west": (12.0, 55.0, 4.0, 59.0, LEVEL, "the building over the west headland"),
        "back_door": (7.6, 52.6, 7.0, 50.0, LEVEL, "the market hall's back door"),
        "back_door_side": (10.5, 51.2, 7.0, 50.0, LEVEL, "the back door along its wall"),
        "wheels_far": (25.0, -21.0, 25.4, -17.6, LEVEL, "the locomotive's far side", 2048),
        "rail": (24.0, -15.6, 28.0, -14.3, LEVEL, "the balcony's railing", -12288),
    },
    "harbour": {
        "ship_from_quay": (15.0, 55.0, 19.0, 58.5, LEVEL,
                           "from the boards, the ship's stern quarter"),
        "ship_bow": (27.0, 55.0, 22.0, 58.5, LEVEL,
                     "from the boards east of it, the bow"),
        "horizon_south": (34.0, 55.0, 34.0, 70.0, LEVEL,
                          "from the boards, straight out to sea"),
        "horizon_east": (40.0, 55.0, 53.0, 60.0, LEVEL,
                         "from the boards, where the east wall was"),
        "from_water": (26.0, 59.0, 20.0, 58.5, LEVEL,
                       "standing in the slip, the hull over you"),
        "quay_from_sea": (30.0, 63.0, 30.0, 54.0, LEVEL,
                          "from the water, back at the town"),
    },
    #: the owner, 2026-11-18: "some of the lower walls around city have
    #: building textures and the things that should probably be buildings
    #: have wall textures"
    "edges": {
        "avenue_end": (35.0, 8.0, 35.0, -2.0, LEVEL, "the avenue's north end wall"),
        "row_end": (8.0, 16.5, -2.0, 16.5, LEVEL, "Theatre Row's west end wall"),
        "west_lane": (1.5, 26.0, 1.5, 4.0, LEVEL, "the west perimeter lane"),
        "north_lane": (16.0, 1.5, 30.0, 1.5, LEVEL, "the north perimeter lane"),
        "east_lane": (57.0, 30.0, 57.0, 6.0, LEVEL, "the east perimeter lane"),
        "market_east_end": (50.0, 38.5, 60.0, 38.5, LEVEL, "market street's east end"),
    },
    #: the owner, 2026-11-18: "In the shops shelves aren't sometimes aligned
    #: with textures ... pawn shop could be rethinked a bit"
    "shelves": {
        "unit_b_close": (45.0, 43.0, 45.0, 41.0, LEVEL, "the apothecary's shelf, square on"),
        "unit_c_close": (48.0, 43.0, 48.0, 41.0, LEVEL, "the ironmonger's shelf, square on"),
        "unit_e_close": (45.0, 47.0, 45.0, 49.0, LEVEL, "the bookseller's shelf, square on"),
        "saloon_shelf": (7.6, 10.9, 10.2, 9.4, LEVEL, "along the bar to the east wall"),
        "pawn_west": (31.0, 4.9, 27.2, 4.9, LEVEL, "the pawn shop, to its west wall"),
        "pawn_east": (28.5, 4.9, 32.5, 4.9, LEVEL, "the pawn shop, to its east wall"),
        "pawn_north": (30.0, 5.6, 30.0, 3.0, LEVEL, "the pawn shop, to its window"),
        "pawn_south": (30.0, 4.2, 30.0, 7.0, LEVEL, "the pawn shop, to its back"),
    },
    #: the owner, 2026-11-18: "Pump station interior is a bit small, we can
    #: make it as a big technical building with conveyor belts and heavy
    #: machinery"
    "machines": {
        "from_gallery": (47.3, 6.6, 42.0, 8.0, LEVEL, "entering the hall from the gallery"),
        "consoles": (41.8, 8.2, 40.0, 7.2, LEVEL, "the console alcove in the west wall"),
        "belt": (46.9, 11.0, 42.0, 9.5, LEVEL, "along the belt from the south-east corner"),
        "tanks": (43.5, 8.3, 42.0, 5.5, LEVEL, "the settling basin in the north bay"),
        "north_wall": (46.8, 13.6, 42.0, 5.0, UP, "the whole hall from the south bay"),
        "east_wall": (40.5, 4.0, 47.0, 13.0, LEVEL, "the hall's length from the north bay"),
    },
    "pilot": {
        "spur_street": (55.5, 26, 55.5, 16, LEVEL, "the rail spur, facing the yard"),
        "yard": (51.5, 19.5, 55.5, 19.5, LEVEL, "in the works yard, facing the spur"),
        "canteen_in": (51.6, 13.2, 50.2, 13.2, LEVEL, "inside the canteen, facing the counter"),
        "grate_stand": (49.4, 21.5, 50.5, 21.5, LEVEL, "the grate and its kerb, from the dock"),
        "sewer_junction": (42.0, 12.0, 46.0, 12.0, LEVEL, "the sewer junction under Foundry Ward"),
    },
    "fresh1": {
        "quay_start": (33.5, 53.0, 35.5, 45.0, LEVEL, "the player's first frame: quay, facing the avenue"),
        "avenue_vista": (35.0, 30.0, 35.0, 14.0, LEVEL, "mid-avenue, the Aldermack vista north"),
        "avenue_up": (35.0, 30.0, 35.0, 14.0, UP, "the same, looking up the canyon"),
        "plaza_centre": (22.5, 45.0, 33.0, 45.0, LEVEL, "market plaza, facing east past the monument"),
        "yard_approach": (55.5, 19.5, 50.0, 19.5, LEVEL, "approaching the yard off the spur"),
        "cellar": (41.0, 12.8, 42.6, 13.8, LEVEL, "the works cellar, facing the pit"),
    },
    #: Wave 1: what the street anatomy and the green actually changed. Walk
    #: order -- the west street's carriageway, the kerb that makes it one,
    #: then in through the lychgate to the green.
    "wave1": {
        "west_street_road": (18.0, 22.0, 18.0, 34.0, LEVEL,
                             "the west street: the carriageway running south "
                             "between its pavements"),
        "west_street_kerb": (17.0, 26.0, 19.0, 26.0, LEVEL,
                             "across the kerb -- the 2048 step E3M1 measures"),
        "spur_road": (56.5, 42.0, 56.5, 52.0, LEVEL,
                      "the spur south carriageway"),
        "lychgate": (18.0, 28.0, 24.0, 28.0, LEVEL,
                     "the lychgate from the west street"),
        "green_in": (22.0, 28.0, 28.0, 28.0, LEVEL,
                     "inside the green: turf, not tarmac"),
        "green_path": (23.9, 33.0, 23.9, 24.0, LEVEL,
                       "on the dirt path, looking north along it -- the "
                       "planting stands either side"),
        "green_stones": (22.5, 30.0, 25.5, 27.0, LEVEL,
                         "across the turf toward the mausolea, where the "
                         "headstones and bushes are"),
    },
    #: Wave 1b's additions: the shop glass and the Aldermack's curtain.
    "wave1c": {
        "auditorium": (22.5, 9.5, 22.5, 6.0, LEVEL,
                       "the Aldermack house, facing the stage: the curtain "
                       "hangs across the proscenium"),
        "curtain_close": (22.5, 8.0, 22.5, 6.5, LEVEL,
                          "at the curtain -- the fabric should read at "
                          "natural scale, drawn across"),
        "stage_side": (21.0, 8.2, 24.5, 6.8, LEVEL,
                       "along the proscenium from the house's west side"),
    },
    "fresh2": {
        "canteen_door": (51.9, 16.4, 51.9, 13.5, LEVEL, "the canteen door from the yard"),
        "dock": (50.0, 18.0, 48.5, 18.0, LEVEL, "the loading dock alcove"),
        "west_lane": (1.5, 25.0, 1.5, 40.0, LEVEL, "the west lane, south along the tenements"),
        "cemetery_gate": (18.0, 28.0, 24.0, 28.0, LEVEL, "the lychgate from the west street"),
        "sewer_trunk": (43.0, 21.5, 49.0, 21.5, LEVEL, "the sewer trunk, facing the grate shaft"),
    },
    "market": {
        "plaza_fountain": (24.0, 45.0, 21.0, 45.0, LEVEL, "the plaza, west to the fountain"),
        "fountain_edge": (22.8, 45.0, 20.5, 45.6, LEVEL, "at the basin rim"),
        "stalls": (19.0, 44.0, 16.5, 45.5, LEVEL, "the stall run on the plaza's west edge"),
        "quay_boards": (30.0, 52.5, 34.0, 54.5, LEVEL, "the quay, onto the boards"),
        "river": (20.0, 55.0, 20.5, 60.0, LEVEL, "from the boards south over the river"),
        "start_look": (33.5, 53.0, 31.0, 50.5, LEVEL, "the start, looking into the plaza"),
        "hall_door": (16.5, 45.7, 14.0, 45.7, LEVEL, "the market hall door from the plaza"),
        "hall_in": (13.5, 45.5, 10.2, 44.3, LEVEL, "inside the hall, toward unit A"),
    },
    "theatre": {
        "saloon_door": (6.6, 16.2, 6.6, 14.6, LEVEL, "the saloon door from Theatre Row"),
        "saloon_in": (9.4, 12.4, 6.6, 9.8, LEVEL, "inside the saloon, over the tables to the counter"),
        "saloon_counter": (7.0, 11.0, 6.5, 9.6, LEVEL, "at the bar"),
        "parlor_mouth": (13.8, 16.2, 13.8, 14.6, LEVEL, "the parlor's one-bay mouth"),
        "parlor_deep": (13.8, 12.6, 13.8, 9.2, LEVEL, "the gallery, north into the range"),
        "foyer_in": (28.2, 9.5, 28.2, 7.4, LEVEL, "the foyer and its box office"),
        "aldermack_front": (28.2, 12.6, 28.2, 10.9, LEVEL, "the Aldermack door off the forecourt"),
        "auditorium": (22.5, 10.4, 22.5, 5.6, LEVEL, "the house, facing the stage"),
        "stage_up": (22.5, 8.4, 22.5, 5.2, UP, "the stage and the wall above it"),
        "lobby_avenue": (33.4, 8.7, 32.3, 8.7, LEVEL, "the avenue lobby, the complex's second front"),
        "pawn_front": (33.4, 5.1, 32.3, 5.1, LEVEL, "the pawn shop off the avenue"),
        "pawn_in": (28.9, 4.6, 31.6, 4.6, LEVEL, "inside the pawn shop, down the pedestal run"),
    },
    "diag": {
        "pawn_west": (31.6, 4.6, 28.9, 4.6, LEVEL, "the shop looking back west"),
        "pawn_north": (31.0, 5.7, 31.0, 3.8, LEVEL, "the shop across its short axis"),
        "pawn_door_close": (31.6, 5.0, 32.3, 5.0, LEVEL, "hard up against the shop door"),
    },
    "church": {
        "nave": (29.4, 28.6, 29.4, 24.2, LEVEL, "the nave, north to the chancel"),
        "nave_up": (29.4, 28.6, 29.4, 24.2, UP, "the same, up into the roof"),
        "chancel": (29.4, 24.6, 29.4, 22.7, LEVEL, "the chancel and its altar"),
        "aisle": (27.6, 29.4, 27.6, 25.6, LEVEL, "the west aisle"),
        "narthex": (31.2, 29.3, 31.2, 27.5, LEVEL, "the narthex and the font"),
        "tower_up": (31.0, 23.3, 31.0, 22.8, UP, "up the bell tower"),
        "portal_avenue": (34.2, 29.2, 32.2, 29.2, LEVEL, "the avenue portal"),
        "portal_cemetery": (24.4, 29.2, 26.4, 29.2, LEVEL, "the cemetery door"),
    },
    #: Inside St Gallow's after it got roofs over it (2026-11-17): every room,
    #: looking both ways, and out through the tower door from inside.
    "church_inside": {
        "belfry_in": (33.0, 23.6, 32.5, 22.9, LEVEL, "in the belfry, toward the inner door"),
        "belfry_out": (33.0, 23.0, 33.0, 24.3, LEVEL, "in the belfry, back at the tower door"),
        "belfry_up": (33.0, 23.2, 33.0, 22.9, UP, "up the belfry"),
        "tower_room": (31.6, 23.3, 30.8, 23.3, LEVEL, "the room behind the tower, west to the chancel"),
        "tower_room_back": (31.0, 23.3, 32.6, 23.3, LEVEL, "the same room, back at the inner door"),
        "chancel_south": (29.4, 23.0, 29.4, 29.0, LEVEL, "from the chancel down the nave"),
        "nave_north": (29.4, 29.8, 29.4, 24.2, LEVEL, "the nave from its south end"),
        "nave_roof": (29.0, 29.9, 29.0, 24.2, UP, "up into the nave's pitched ceiling"),
        "aisle_north": (27.6, 30.0, 27.6, 25.0, LEVEL, "the west aisle"),
        "narthex_north": (31.4, 29.3, 31.4, 27.4, LEVEL, "the narthex"),
        "narthex_east": (31.0, 28.7, 32.2, 28.7, LEVEL, "the narthex wall where the avenue portal was"),
        "vestry": (31.4, 25.2, 31.4, 24.7, LEVEL, "the vestry"),
    },
    "overhaul": {
        "shop_window": (30.2, 1.9, 30.2, 3.4, LEVEL, "the glazed shopfront from Theatre Row"),
        "shop_window_close": (30.2, 2.6, 30.2, 3.4, LEVEL, "up against the glass"),
        "saloon_door": (6.6, 16.2, 6.6, 14.6, LEVEL, "the saloon door, at its new height"),
        "saloon_in": (9.4, 12.4, 6.6, 9.8, LEVEL, "the saloon and its wall braziers"),
        "nave": (29.4, 28.6, 29.4, 24.2, LEVEL, "the nave, braziers on the aisle walls"),
        "street_lamp": (35.0, 30.0, 35.0, 14.0, LEVEL, "the avenue and its lamps"),
        "sewer_wet": (45.5, 7.0, 45.5, 12.0, LEVEL, "the wet channel, where the water dressing is"),
    },
    "signs": {
        "aldermack_sign": (28.2, 12.8, 28.2, 10.9, LEVEL, "the Aldermack's name over its portal"),
        "saloon_sign": (8.6, 10.5, 10.1, 10.5, LEVEL, "WHISKEY on the saloon's east wall"),
        "pawn_sign": (29.6, 4.9, 28.7, 4.9, LEVEL, "PAWN inside the shop"),
        "nave_sign": (29.4, 27.0, 29.4, 30.5, LEVEL, "ST GALLOWS across the nave's south wall"),
        "sewer_sign": (38.5, 15.0, 38.5, 12.2, LEVEL, "OUTFALL in the pump chamber"),
    },
    "mall": {
        "concourse": (42.0, 46.0, 48.0, 46.0, LEVEL, "down the arcade concourse"),
        "concourse_up": (42.0, 46.0, 46.5, 46.0, UP, "the concourse height"),
        "shopfront": (44.4, 45.6, 44.4, 44.2, LEVEL, "unit A behind its glass"),
        "unit_in": (46.5, 43.5, 46.5, 42.3, LEVEL, "inside a unit, over its counter"),
        "service_door": (50.0, 46.1, 51.6, 46.1, LEVEL, "the keyed service door and its placard"),
        "entry": (38.3, 46.1, 40.4, 46.1, LEVEL, "the arcade entrance from the street"),
    },
    "station": {
        "station_door": (54.5, 6.5, 52.8, 6.5, LEVEL, "the pumping station door on the spur"),
        "station_hall": (51.5, 6.6, 50.2, 6.6, LEVEL, "inside the station, facing the stair"),
        "station_stair": (49.5, 6.6, 47.8, 6.6, DOWN, "down the stair run"),
        "station_cellar": (44.5, 5.0, 45.6, 5.0, LEVEL, "the cellar and its pit"),
        "station_foot": (44.5, 5.0, 43.8, 5.0, LEVEL, "the spiral foot, down in the sewer"),
    },
    "lamp_pools": {
        "yard_lamp": (51.0, 19.0, 50.0, 19.0, LEVEL, "close to the works-yard lamp pool"),
        "forecourt_lamp": (30.0, 13.0, 31.0, 13.0, LEVEL, "close to the forecourt lamp pool"),
        "quay_lamp": (36.0, 52.0, 37.0, 52.0, LEVEL, "close to the quay-gate lamp pool"),
    },
    "sewer": {
        "north_walk": (38.0, 6.5, 42.0, 7.5, LEVEL, "the north walk beside its channel"),
        "pump_room": (31.0, 15.0, 28.0, 14.0, LEVEL, "the pumping chamber"),
        "flooded": (42.0, 34.5, 42.5, 38.0, LEVEL, "into the flooded branch"),
        "east_leg": (52.0, 20.0, 52.0, 16.0, LEVEL, "the east leg of the ring"),
        "annex": (52.5, 17.0, 56.0, 17.5, LEVEL, "the eastern annex"),
    },
    "entrances": {
        "canteen_face": (51.9, 17.2, 51.9, 15.0, LEVEL, "square on the canteen entrance"),
        "hall_face": (16.8, 45.75, 15.0, 45.75, LEVEL, "square on the market hall entrance"),
        "lychgate_face": (18.5, 28.0, 20.5, 28.0, LEVEL, "square on the lychgate"),
        "stair_mouth": (50.5, 19.5, 48.6, 19.5, LEVEL, "the works stair mouth on the yard"),
    },
    "fresh5": {
        "cemetery_in": (24.0, 26.0, 27.0, 24.5, LEVEL, "inside the cemetery ground, toward the church"),
        "lychgate_out": (21.0, 28.0, 18.0, 29.5, LEVEL, "standing in the lychgate, out to the west street"),
        "stash": (37.0, 21.5, 40.0, 22.5, LEVEL, "the secret stash off the sewer trunk"),
        "canteen_side": (49.5, 16.0, 50.5, 13.5, LEVEL, "the canteen's second door from the yard"),
        "pit_bottom": (42.0, 17.0, 44.5, 15.5, LEVEL, "the cellar pit landing under the works"),
        "well_sq": (14.0, 27.0, 17.0, 25.5, LEVEL, "the well square in Old Crossing"),
    },
    "fresh4": {
        "pool_yard": (54.0, 19.5, 50.0, 19.5, LEVEL, "the works yard west: lamps, dock, stair mouth"),
        "pool_quay": (35.0, 51.0, 32.5, 52.5, LEVEL, "the quay gate pool"),
        "pool_forecourt": (32.0, 14.2, 30.5, 13.0, LEVEL, "the forecourt pool and kiosk"),
        "sewer_wet": (45.0, 21.5, 41.0, 21.5, LEVEL, "the wet trunk, west toward the junction"),
        "market_plaza_w": (33.0, 45.0, 20.0, 45.0, LEVEL, "the plaza, west past the monument"),
    },
    #: St Gallow's from where a player meets it.  Fixed 2026-11-17 for the
    #: skyline experiment (experiments/church-skyline): every pose stands in
    #: open street, so none of them moves when the church's massing does.
    #: `avenue_front` stood at x 38.0 until 2026-11-17, which is now exactly
    #: the kerb of the avenue's east carriageway: a camera on a sector
    #: boundary is in neither sector and the observer writes no frame.  It
    #: moved 0.3 east, onto the pavement.
    "skyline": {
        "avenue_south": (35.5, 33.5, 33.5, 23.3, LEVEL,
                         "walking north up the avenue toward the church"),
        "avenue_south_up": (35.5, 33.5, 33.5, 23.3, UP,
                            "the same step, eyes raised to the roofline"),
        "avenue_north": (35.8, 17.2, 33.5, 23.3, LEVEL,
                         "coming south across the Row junction"),
        "avenue_front": (38.3, 26.5, 32.0, 26.5, LEVEL,
                         "across the avenue, square on the church's long side"),
        "avenue_front_up": (38.3, 26.5, 32.0, 26.5, UP,
                            "the same, looking up its face"),
        "portal": (36.5, 28.7, 32.0, 28.7, LEVEL,
                   "facing the avenue portal from the far kerb"),
        "tower_door": (35.2, 27.2, 33.3, 24.2, LEVEL,
                       "walking up the avenue: the door in the tower's foot"),
        "tower_door_close": (33.4, 25.6, 33.4, 24.0, LEVEL,
                             "on the pavement, square on the tower door"),
        "tower_foot": (36.5, 21.5, 33.5, 23.3, UP,
                       "at the junction, looking up where the tower stands"),
        "row_corner": (30.0, 18.0, 33.5, 23.0, LEVEL,
                       "on Theatre Row, looking past the church's north end"),
        "forecourt": (30.5, 13.5, 33.5, 23.3, LEVEL,
                      "from the Aldermack forecourt: the vista church-patterns asks for"),
        "vista_far": (35.5, 45.0, 35.5, 20.0, LEVEL,
                      "from the market end, the whole avenue north"),
        "spawn_north": (33.5, 53.0, 34.5, 23.0, LEVEL,
                        "the spawn, turned to face up the avenue"),
        "cemetery_side": (23.9, 30.0, 26.6, 26.0, UP,
                          "inside the cemetery, up at the church's west face"),
    },
    #: Shop glass and the street's own floor (owner, 2026-11-17: "the glass
    #: should sit in an aperture/frame so glass texture scaling won't be
    #: colliding with facade texture"; "roads and sidewalk attempts ... look
    #: poor").  Each pane square-on and at a rake from the street, and once
    #: from inside its shop; then the ground, eyes lowered.
    "shopfronts": {
        "pawn_front": (29.7, 1.6, 29.7, 3.1, LEVEL,
                       "Theatre Row, square on the pawn shop's display"),
        "pawn_rake": (25.5, 2.0, 29.5, 3.1, LEVEL,
                      "the same pane at a rake, with the facade either side"),
        "pawn_inside": (29.7, 5.6, 29.7, 3.5, LEVEL,
                        "inside the pawn shop, looking out through the glass"),
        "super_east": (18.2, 43.3, 15.4, 43.3, LEVEL,
                       "square on the market hall's long east pane"),
        "super_east_rake": (17.2, 50.5, 15.4, 44.0, LEVEL,
                            "both east panes at a rake"),
        "super_north": (7.2, 38.2, 7.2, 41.0, LEVEL,
                        "square on the market hall's north pane"),
        "super_north_rake": (13.0, 39.6, 8.0, 41.0, LEVEL,
                             "the north pane at a rake"),
        "super_inside": (11.5, 43.3, 13.8, 43.3, LEVEL,
                         "inside the market hall, looking out east"),
        "super_south_pane": (16.8, 50.4, 15.3, 48.6, LEVEL,
                             "the market hall's short east pane, close, at a rake"),
        "super_north_far": (12.6, 38.7, 7.5, 41.0, LEVEL,
                            "the north pane at a rake, from the street's middle"),
        "pawn_close": (28.2, 2.4, 29.6, 3.2, LEVEL,
                       "close on a mullion: the reveal and the sash pocket"),
        "hall_band": (7.6, 46.2, 13.8, 42.6, UP,
                      "on the market hall's floor, eyes raised to the band "
                      "over its east windows"),
        "hall_stock_band": (8.0, 44.0, 8.0, 49.2, UP,
                            "the same, toward the stockroom opening"),
        "mall_north": (42.4, 46.4, 42.4, 44.5, LEVEL,
                       "in the arcade, square on a unit's window"),
        "mall_rake": (40.4, 46.0, 42.6, 44.5, LEVEL,
                      "the same at a rake along the concourse"),
    },
    #: Where the long views end (survey finding 2: "every vista ends in
    #: black").  Each main street looked along toward the city's edge, from
    #: far and from near, standing on the pavement side of the kerb.
    "vistas": {
        "avenue_north_far": (35.0, 34.0, 35.4, 0.0, LEVEL,
                             "up the avenue from the market street: its far end"),
        "avenue_north_mid": (35.0, 14.0, 35.4, 0.0, LEVEL,
                             "up the avenue from below Theatre Row"),
        "avenue_north_near": (35.0, 5.5, 35.6, 0.0, LEVEL,
                              "the avenue's last stretch"),
        "row_west_far": (33.0, 16.4, 0.0, 17.6, LEVEL,
                         "down Theatre Row from the avenue: its west end"),
        "row_west_near": (9.0, 16.4, 0.0, 17.8, LEVEL,
                          "Theatre Row's last stretch"),
        "market_west_far": (33.0, 36.4, 0.0, 37.3, LEVEL,
                            "down the market street westward"),
        "market_west_near": (8.0, 36.4, 0.0, 37.4, LEVEL,
                             "the market street's west end"),
        "market_east_far": (39.0, 36.4, 58.0, 37.3, LEVEL,
                            "down the market street eastward"),
        "market_east_near": (51.0, 36.4, 58.0, 37.4, LEVEL,
                             "the market street's east end"),
    },
    #: Inside the pawnbroker's, toward the back of the shop where the pledge
    #: room is (2026-11-18: "more complex interiors").
    #: What the goods stand on (experiments/fixtures). An arcade unit is seen
    #: from the concourse, over its counter, so that is where these stand.
    "fixtures": {
        "saloon_in": (9.4, 12.4, 6.6, 9.8, LEVEL, "the saloon, over the tables to the bar"),
        "saloon_counter": (7.0, 11.0, 6.5, 9.6, LEVEL, "at the bar"),
        "saloon_shelf": (7.6, 10.9, 10.2, 9.4, LEVEL, "along the bar to the east wall"),
        "unit_b": (45.0, 44.3, 45.0, 41.0, LEVEL, "the apothecary from the concourse"),
        "unit_c": (48.0, 44.3, 48.0, 41.0, LEVEL, "the ironmonger from the concourse"),
        "unit_e": (45.0, 45.7, 45.0, 49.0, LEVEL, "the bookseller from the concourse"),
        "unit_f": (48.0, 45.7, 48.0, 49.0, LEVEL, "the grocer from the concourse"),
        "unit_b_rake": (45.6, 43.3, 44.6, 41.0, LEVEL, "the apothecary, close and at a rake"),
        "pawn_front": (33.4, 5.1, 32.3, 5.1, LEVEL, "control: the pawn shop off the avenue"),
        "saloon_door": (6.6, 16.2, 6.6, 14.6, LEVEL, "control: the saloon door"),
    },
    #: Does everything fit where it was put (experiments/sprite-fit)?
    "fit": {
        "saloon_in": (9.4, 12.4, 6.6, 9.8, LEVEL, "the saloon, over the tables"),
        "unit_a": (42.7, 44.3, 41.8, 41.0, LEVEL, "the draper"),
        "unit_c": (48.0, 44.3, 48.0, 41.0, LEVEL, "the ironmonger"),
        "unit_d": (42.7, 45.7, 41.8, 49.0, LEVEL, "the clockmaker"),
        "unit_e": (45.0, 45.7, 45.0, 49.0, LEVEL, "the bookseller"),
        "pawn_west": (31.0, 4.9, 27.2, 4.9, LEVEL, "the pawn shop, to its west wall"),
        "pawn_window": (30.0, 5.4, 29.2, 3.5, LEVEL, "the pawn shop's display from inside"),
        "row": (22.5, 17.0, 30.0, 16.4, LEVEL, "Theatre Row, east"),
        "avenue": (35.8, 20.0, 35.8, 33.0, LEVEL, "the avenue, south"),
        "market": (30.0, 47.5, 38.0, 46.3, LEVEL, "the market street"),
        "crossing_west": (12.0, 21.5, 20.0, 23.4, LEVEL, "the old crossing"),
        "yard": (52.5, 18.5, 50.3, 19.4, LEVEL, "the foundry yard, to the stair mouth"),
    },
    "pawn_inside": {
        "pawn_to_back": (30.75, 4.1, 30.75, 7.0, LEVEL,
                         "in the shop, square on its back wall"),
        "pawn_back_rake": (29.2, 4.3, 30.9, 6.4, LEVEL,
                           "the back wall at a rake"),
        "pawn_back_close": (30.75, 5.5, 30.75, 7.0, LEVEL,
                            "close on the back wall"),
        "pawn_length": (27.7, 4.9, 32.0, 5.2, LEVEL,
                        "down the length of the shop"),
    },
    "ground": {
        "avenue_road": (35.5, 40.0, 35.5, 28.0, DOWN,
                        "on the avenue, eyes lowered: carriageway and kerb"),
        "avenue_road_level": (35.5, 40.0, 35.5, 28.0, LEVEL,
                              "the same, level"),
        "row_road": (22.0, 1.8, 34.0, 1.8, DOWN,
                     "along Theatre Row, eyes lowered"),
        "row_road_level": (22.0, 1.8, 34.0, 1.8, LEVEL, "the same, level"),
        "market_road": (17.5, 52.0, 17.5, 40.0, DOWN,
                        "beside the market hall, eyes lowered"),
        "market_road_level": (17.5, 52.0, 17.5, 40.0, LEVEL, "the same, level"),
        "west_road": (2.0, 30.0, 2.0, 18.0, LEVEL, "the west street"),
        "kerb_close": (35.2, 30.0, 37.4, 31.2, DOWN,
                       "on the avenue's pavement, close on the kerb's face"),
        "kerb_along": (35.6, 34.0, 36.0, 24.0, DOWN,
                       "along the avenue's kerb and centre strip"),
        "sill_close": (16.4, 43.0, 15.3, 42.4, DOWN,
                       "close on the market hall's stall riser and sill"),
        "west_street_on_road": (18.0, 36.0, 18.0, 30.0, LEVEL,
                             "on the west street's carriageway"),
        "crossing": (35.2, 37.2, 28.0, 37.0, LEVEL,
                     "at a crossing: how two roads meet"),
        "foundry_road": (55.5, 30.0, 55.5, 18.0, LEVEL, "the rail spur's street"),
    },
    #: What a LOW SKY hides (owner, 2026-11-17: "when you put parallax sky low
    #: it is covering view like a normal ceiling").  Each of these looks past
    #: or over something low at something tall that ought to show above it.
    "over": {
        "yard_out_east": (22.5, 30.5, 40.0, 26.0, LEVEL,
                          "in the churchyard, looking east: the church, and the "
                          "avenue's far tenements over its roof"),
        "yard_out_east_up": (22.5, 30.5, 40.0, 26.0, UP,
                             "the same, eyes raised"),
        "yard_out_south": (23.9, 30.0, 24.0, 40.0, UP,
                           "in the churchyard, looking south over its own wall "
                           "at the market blocks"),
        "yard_to_tower": (22.5, 33.0, 33.5, 23.3, UP,
                          "from the churchyard's far corner toward the tower"),
        "avenue_over_wall": (36.5, 33.6, 26.0, 33.6, UP,
                             "on the avenue, looking west over the churchyard "
                             "wall: the west street's blocks beyond"),
        "row_over_church": (29.0, 17.0, 31.0, 30.0, UP,
                            "on Theatre Row, looking south over the church's "
                            "north end: its nave and tower behind"),
        "avenue_over_church": (37.5, 27.0, 26.0, 27.0, UP,
                               "across the avenue, over the low range: the nave "
                               "should stand behind it"),
    },
    "fresh3": {
        "theatre_row": (17.5, 18.0, 24.0, 16.5, LEVEL, "Theatre Row street, east toward the forecourt"),
        "forecourt": (29.5, 14.0, 31.5, 12.5, LEVEL, "the Aldermack forecourt"),
        "north_lane": (36.5, 1.5, 42.0, 3.0, LEVEL, "the north lane, east to the spur"),
        "market_st": (25.0, 37.5, 33.0, 40.0, LEVEL, "market street, east"),
        "quay_up": (33.5, 53.0, 33.5, 45.0, UP, "the quay, looking up at the block tops"),
    },
}


#: Street level, in Build z.  `resolution.GRADE`, restated so this module
#: still renders a campaign reference map without the city's own imports.
GRADE_Z = 8192


#: What the GAME never draws. The owner, 2026-11-18, on frames of E1M1's
#: crypt full of numbered red flags and of ours with orange streaks in the
#: wall: "When you are viewing the level look you should be hiding these
#: control things which are normally invisible like player starts, stack
#: markers, sounds, etc."
#:
#: The engine's own list, not a guess: player starts and every marker
#: (types 1-19: the starts are taken into the start zones and deleted,
#: links and stacks get the invisible bit in warp.cpp:113-133, statnum 10
#: is culled at load); generators and sound sprites (700-712:
#: `InitGenerator`, triggers.cpp:2362); the exploder (459: actor.cpp:2507);
#: and anything launched only outside single player (blood.cpp:700).
HIDDEN_TYPES = set(range(1, 20)) | set(range(700, 713)) | {459}
HIDDEN_STATUS = {10}
#: WHO AND WHAT IS IN A ROOM IS NOT THE ROOM. The owner, 2026-11-18: "you
#: also should be able to check how it looks like without enemies and
#: pickups for example to get rid of visual noise." A cultist in the
#: middle of a frame is what a reader looks at, and a reader praised or
#: blamed a hall for the zombie standing in it. `as_played(..., empty=True)`
#: also hides the dudes (200-254), the weapons (40-51), the ammunition
#: (60-81) and the items and keys (100-149): nblood's kDudeBase..kDudeMax,
#: kItemWeaponBase, kItemAmmoBase and kItemBase ranges. Bodies, barrels,
#: lamps and every other decoration (type 0) stay: they ARE the room.
EMPTY_TYPES = (set(range(200, 255)) | set(range(40, 52))
               | set(range(60, 82)) | set(range(100, 150)))


def as_played(map_path, out_dir, empty: bool = False) -> pathlib.Path:
    """A copy of the map with the game's invisible things made invisible.

    A frame is evidence of what a player sees. A reviewer shown a start
    flag or a charge takes it for part of the room -- one read the
    exploders in the crypt wall as "orange sparks coming out of a crack".
    """
    from bloodmap.format import write_map

    disk = read_map(map_path)
    hidden = emptied = 0
    for sprite in disk.sprites:
        f = sprite.fields
        extra = getattr(getattr(sprite, "extra", None), "fields", None) or {}
        if empty and int(f.get("type", 0)) in EMPTY_TYPES:
            if not int(f["cstat"]) & 32768:
                f["cstat"] = int(f["cstat"]) | 32768
                emptied += 1
            continue
        if (int(f.get("type", 0)) in HIDDEN_TYPES
                or int(f.get("status", 0)) in HIDDEN_STATUS
                or int(extra.get("launch_single", 0))):
            if not int(f["cstat"]) & 32768:
                f["cstat"] = int(f["cstat"]) | 32768
                hidden += 1
    out = pathlib.Path(out_dir) / ("as-empty.MAP" if empty
                                   else "as-played.MAP")
    out.parent.mkdir(parents=True, exist_ok=True)
    write_map(disk, out)
    print(f"as played: {hidden} control sprites hidden"
          + (f"; emptied of {emptied} enemies and pickups" if empty else ""))
    return out


def sector_at(level, x: int, y: int, near: int | None = None) -> int | None:
    """The sector at a point -- the one a person would be standing in.

    `_contains` handles outer loops and carved holes.  (The old observer
    helper accepted a camera inside a street's carved lamp/building hole and
    handed it to the renderer as the host sector.)

    Space is stacked now: a sewer runs under the avenue and a roof stands
    over the church, so a point in plan can lie in several sectors.  This
    used to return the first, and the day the church got its roof every
    interior pose rendered the rooftop instead.  The answer is the sector
    whose floor is nearest the street's: a pose is written for a person on
    the ground.  A pose meant for the sewer still needs a layer named on it.
    """
    hits = [sector_id for sector_id in range(len(level.sectors))
            if _contains(level, sector_id, x, y)]
    if not hits:
        return None

    def floor(sector_id):
        sector = level.sectors[sector_id]
        fields = sector["fields"] if isinstance(sector, dict) else sector.fields
        return int(fields["floor_z"])
    want = GRADE_Z if near is None else near
    return min(hits, key=lambda sector_id: abs(floor(sector_id) - want))


def poses_for(level, name: str) -> list[Viewpoint]:
    out = []
    for view_id, pose in POSE_SETS[name].items():
        #: an optional seventh item names the floor the pose stands on, for
        #: a place under or over the street (the crypt, the sewer)
        px, py, tx, ty, horiz, note = pose[:6]
        x, y = int(px * PU), int(py * PU)
        sector = sector_at(level, x, y, pose[6] if len(pose) > 6 else None)
        if sector is None:
            print(f"  ! {view_id}: no sector at ({x},{y}) -- pose skipped")
            continue
        z = eye_z(level, sector)
        if z is None:
            print(f"  ! {view_id}: no eye height in sector {sector}")
            continue
        out.append(Viewpoint(
            view_id=view_id, x=x, y=y, z=z,
            angle=int(angle_toward((x, y), (int(tx * PU), int(ty * PU)))) & 2047,
            horiz=horiz, sector=sector, node=f"pose:{view_id}",
            purpose="loop", screenshot=True, note=note))
    return out


def reference_poses(level, sectors: list[int]) -> list[Viewpoint]:
    out = []
    for sector_id in sectors:
        point = interior_point(level, sector_id)
        z = eye_z(level, sector_id)
        if point is None or z is None:
            continue
        outer = _sector_loops(level, sector_id)[0]
        far = max(outer, key=lambda p: (p[0] - point[0]) ** 2 + (p[1] - point[1]) ** 2)
        out.append(Viewpoint(
            view_id=f"sector_{sector_id}", x=point[0], y=point[1], z=z,
            angle=int(angle_toward(point, far)) & 2047, horiz=LEVEL,
            sector=sector_id, node=f"sector:{sector_id}", purpose="reference",
            screenshot=True, note=f"reference sector {sector_id}"))
    return out


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--set", dest="pose_set", action="append", default=[])
    parser.add_argument("--map", default=str(CURRENT))
    parser.add_argument("--ref", default=None, help="campaign map name, e.g. E3M1")
    parser.add_argument("--sectors", default="", help="reference sector ids")
    parser.add_argument("--tag", default="latest")
    parser.add_argument("-o", "--out", default=None)
    parser.add_argument("--empty", action="store_true",
                        help="hide enemies and pickups too: the place alone")
    args = parser.parse_args(argv)

    map_path = (corpus_map_path(args.ref) if args.ref
                else pathlib.Path(args.map))
    level = read_map(map_path).to_level_ir()
    if args.ref:
        views = reference_poses(level, [int(s) for s in args.sectors.split(",") if s])
    else:
        views = []
        for name in (args.pose_set or ["pilot"]):
            views += poses_for(level, name)
    if not views:
        print("no poses resolved")
        return 1
    out_dir = pathlib.Path(args.out or (PROJECT / "reports" / "looks" / args.tag))
    out_dir.mkdir(parents=True, exist_ok=True)
    manifest = run_observation(ObservationRequest(
        map_path=as_played(map_path, out_dir, empty=args.empty),
        output_dir=out_dir,
        resource_dir=pathlib.Path("reference/blood"), viewpoints=views,
        width=640, height=480, screenshots=[v.view_id for v in views],
        brightness=0, rff=None))
    # The run keeps the MAP it looked at: the path is overwritten by the next
    # build, and a frame whose map is gone is not evidence of anything.
    import shutil
    shutil.copyfile(map_path, out_dir / "observed.MAP")
    print(f"{len(views)} frames -> {out_dir}")
    for view in views:
        print(f"  {view.view_id}: sector {view.sector} z {view.z} -- {view.note}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
