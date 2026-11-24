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
from bloodmap.sector_geom import outline_and_holes
from bloodmap.sector_geom import sector_at as _sector_at
from bloodmap.visual import (
    EMPTY_TYPES, HIDDEN_STATUS, HIDDEN_TYPES, HORIZ_DOWN, HORIZ_LEVEL,
    HORIZ_UP, ObservationRequest, Viewpoint, as_played, run_observation,
)

PROJECT = pathlib.Path(__file__).resolve().parents[1]
CURRENT = PROJECT / "level" / "blood-city-current.MAP"
PU = 1024

#: Level horizon; the observer's horiz is Build's, 100 is level.
LEVEL, UP, DOWN = HORIZ_LEVEL, HORIZ_UP, HORIZ_DOWN

#: Named poses in plan units: (x, y, look-at x, look-at y, horiz, note).
#: Fixed sets stay stable across iterations so before/after pairs line up;
#: fresh sets are added per iteration and never reused.
POSE_SETS = {
    "phantom": {
        "k_windows_west": (48.45, -11.00, 50.0, -14.75, LEVEL,
                           "the first windows and the open door from west of the pool", 118784),
        "l_windows_east": (55.0, -10.74, 52.0, -14.95, LEVEL,
                           "back along the occupied windows from the east", 118784),
        "m_empty_seat": (49.69, -11.75, 49.69, -15.2, LEVEL,
                         "the one empty seat, through the open door", 119552),
        "n_stationmaster": (54.25, -10.70, 54.96, -9.15, LEVEL,
                            "the stationmaster below the broken clock", 118784),
        "o_bricked_wall": (57.66, -10.96, 55.81, -10.88, LEVEL + 18,
                           "the half-built barrier and the bricking gang", 118784),
        "q_handle": (54.25, -13.3, 55.1, -12.8, LEVEL,
                     "the driver's handle in the cab", 119552),
        "p_before_departure": (49.3, -10.72, 55.0, -12.15, LEVEL,
                               "the platform and coach before the departure", 118784),
        "a_booking": (47.36, -8.15, 48.6, -12.6, LEVEL,
                      "off the pump stair, through the folding gates", 118784),
        "b_ticket_window": (47.32, -9.10, 44.4, -8.65, LEVEL,
                            "the clerk behind the booking grille", 118784),
        "c_platform": (47.38, -10.65, 52.3, -14.6, LEVEL,
                       "along the rust edge to the coach", 118784),
        "d_waiting": (53.65, -11.1, 53.6, -8.0, LEVEL,
                      "the old nameboard and the passengers who waited", 118784),
        "e_car": (48.95, -13.87, 54.2, -13.95, LEVEL,
                  "from the west end down the aisle", 119552),
        "r_bench": (49.9, -12.9, 48.9, -15.2, LEVEL,
                    "from the open door to the bench across", 119552),
        "s_cab": (52.7, -13.87, 57.5, -13.87, LEVEL,
                  "down the aisle into the driver's cab and out of his window", 119552),
        "t_pit": (46.9, -13.0, 50.2, -13.9, LEVEL,
                  "the end of the carriage from the rails", 125696),
        "u_flank": (46.6, -16.5, 52.5, -15.0, LEVEL,
                    "the carriage's far flank from the rails behind it", 125696),
        "f_tunnel": (63.2, -11.55, 65.7, -17.2, LEVEL,
                     "the return walk and the watchers", 121856),
        "i_car_broadside": (51.17, -10.72, 51.9, -15.2, LEVEL,
                            "the green windows across the platform edge", 118784),
        "j_office": (49.8, -9.31, 48.9, -7.25, LEVEL,
                     "the strike-through line diagram and the booking clock", 118784),
        "g_drowned": (46.0, -13.2, 41.6, -14.9, LEVEL,
                      "the drowned carriage from the siding", 127488),
        "v_drowned_side": (43.5, -11.7, 40.8, -14.7, LEVEL,
                           "the drowned carriage's side from the cavern's edge", 129280),
        "w_drowned_far": (37.0, -12.5, 40.3, -14.6, LEVEL,
                          "round the drowned carriage's far end", 129280),
        "h_recall": (66.2, -9.6, 67.2, -8.5, LEVEL,
                     "the bricking gang's recall station", 120832),
    },
    "phantom_fired": {
        "a_platform_after": (49.3, -10.72, 55.0, -12.15, LEVEL,
                             "the same platform after departure", 118784),
        "b_watcher_inside": (63.6, -13.9, 64.45, -18.0, LEVEL,
                              "a lit niche through the carriage window at the far berth", 119552),
        "c_far_berth": (61.4, -11.55, 64.1, -14.4, LEVEL,
                        "the coach from the far walk", 121856),
    },
    # the Aldermack as a visitor walks it (critique rounds number frames by name)
    "aldermack": {
        "a_forecourt": (27.30, 13.62, 28.05, 11.0, 143, "from the west side of the forecourt to the entrance"),
        "b_foyer": (28.2, 9.4, 28.05, 6.5, LEVEL, "the foyer and its ticket windows"),
        "d_vomitory": (25.18, 9.79, 22.5, 6.75, LEVEL, "from the vomitory toward the stage"),
        "e_stalls": (22.5, 12.24, 22.5, 6.75, LEVEL, "rear terrace above the lit steps"),
        "f_circle": (22.5, 14.2, 22.5, 5.2, LEVEL + 9, "dress circle looking over the parapet"),
        "g_back": (22.5, 8.6, 22.5, 14.0, LEVEL + 12, "from the pit rail back over the seats to the circle"),
        "c_to_house": (29.2, 9.1, 26.0, 9.25, LEVEL, "from the foyer to the way into the house"),
        "j_stage_way": (18.1, 6.55, 18.9, 5.3, LEVEL, "backstage, to the stair onto the stage"),
        "h_corridor": (17.65, 9.51, 17.97, 12.07, LEVEL, "backstage, past the prop crate to the dressing room"),
        "i_dressing": (17.94, 11.05, 18.15, 14.45, LEVEL, "the star's room from its door"),
    },
    "aldermack-house": {
        "vomitory": (25.18, 9.79, 22.5, 6.75, LEVEL, "from the vomitory toward the stage"),
        "stalls": (22.5, 12.24, 22.5, 6.75, LEVEL, "rear terrace above the lit steps"),
        "west_aisle": (20.48, 12.74, 22.5, 7.5, LEVEL - 15, "down the west stair past the terraces"),
        "circle": (22.5, 14.2, 22.5, 5.2, LEVEL + 9, "dress circle looking over the parapet"),
        "circle_edge": (22.5, 13.37, 22.5, 7.4, LEVEL - 24, "over the parapet to the stalls and stage"),
        "pit": (23.30, 8.04, 21.3, 8.08, LEVEL + 10, "the upright piano from the orchestra pit"),
        "conductor": (22.79, 8.31, 22.79, 6.75, LEVEL - 15, "the lever on the conductor's stand"),
        "wing": (20.2, 5.9, 22.5, 5.15, LEVEL, "west wing looking across the stage"),
        "shadow": (23.85, 6.12, 23.06, 4.25, LEVEL, "on the stage toward the performer and cloth"),
        "watchers": (24.06, 4.5, 24.75, 3.64, LEVEL, "the drape door in the east wing"),
        "dome": (22.5, 12.25, 22.5, 9.25, LEVEL + 104, "from the stalls up to the dome"),
        "box": (19.62, 12.1, 22.5, 7.0, LEVEL, "from the second west box toward the opening"),
        "box_cloth": (20.52, 12.34, 19.65, 12.12, LEVEL, "the sliding box curtain from the west stairs"),
    },
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
    #: the Weaver's Cellars, a spider lair off Graves Brook (the owner,
    #: 2026-11-22: "We can also add spider lair somewhere, similar to E2M8")
    "lair": {
        "way_in": (11.75, 19.6, 11.75, 16.0, LEVEL, "from Graves Brook up the passage", 63488),
        "hall": (11.4, 16.6, 12.0, 11.0, LEVEL, "the hall from the top of the passage", 61440),
        "north_brood": (12.0, 13.6, 12.0, 10.5, LEVEL, "the north alcove", 61440),
        "west_brood": (11.2, 15.8, 8.0, 14.0, LEVEL, "across to the west alcove", 61440),
        "east_brood": (13.4, 15.8, 16.5, 14.0, LEVEL, "across to the east alcove", 61440),
        "ceiling": (10.2, 15.4, 13.5, 12.0, UP, "up at the ceiling", 61440),
        "back": (15.0, 12.2, 10.0, 16.5, LEVEL, "from the far corner back to the way in", 61440),
    },
    #: the owner, 2026-11-18: "We should have more windows in buildings
    #: around the city"
    "windows": {
        "theatre_out": (22.5, 1.6, 22.5, 4.0, LEVEL, "the auditorium's window from the street"),
        "theatre_in": (22.5, 5.6, 22.5, 3.0, LEVEL, "the same window from inside the auditorium"),
        "saloon_out": (1.6, 7.0, 4.0, 7.0, LEVEL, "the saloon back room's barred window from the street"),
        "saloon_in": (5.4, 7.0, 3.0, 7.0, LEVEL, "the same bars from inside"),
        "market_out": (1.8, 41.5, 3.5, 41.5, LEVEL, "the supermarket's window from the street"),
        "market_in": (5.2, 41.5, 3.0, 41.5, LEVEL, "the same window from inside"),
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
    #: the meat market and its stalls, the Demeter (`meat_market`, `harbour_ship`, 2026-11-25)
    "meat_market": {
        "a_front": (20.0, 45.5, 13.5, 45.5, LEVEL, "the hall's front, a stall either side"),
        "b_butcher": (19.5, 51.5, 18.0, 48.5, LEVEL, "the butcher's stall"),
        "c_grocer": (20.2, 44.2, 18.0, 41.5, LEVEL, "the grocer's stall"),
        "d_aisle": (13.2, 45.5, 6.0, 45.5, LEVEL, "from the street door down the aisle of meat"),
        "e_hall": (7.0, 42.0, 13.0, 47.5, LEVEL, "from the nook across the hall to the gallery"),
        "f_stair": (5.0, 48.75, 12.0, 48.75, LEVEL, "the stair from the porters' lobby"),
        "g_gallery": (10.8, 48.6, 7.5, 45.0, LEVEL, "from the gallery to the steel door", -16384),
        "h_lever": (10.2, 48.75, 13.5, 48.75, LEVEL, "the gallery's lever", -16384),
        "i_cold": (4.75, 47.2, 4.75, 42.6, LEVEL, "the cold store from its far end", 4096),
        "j_armor": (5.7, 45.5, 4.2, 46.9, LEVEL, "the cold store's armor from its door", 4096),
    },
    "demeter": {
        "a_quay": (13.0, 55.0, 18.0, 59.0, LEVEL, "the ship from the quay's west"),
        "b_gangplank": (14.9, 54.8, 14.9, 58.0, LEVEL, "up the gangplank"),
        "c_forward": (15.3, 59.0, 24.0, 59.0, LEVEL, "the deck, forward", 1024),
        "d_house": (20.0, 60.2, 14.5, 59.0, LEVEL, "the deckhouse from the deck", 1024),
        "e_hold": (12.6, 60.3, 14.2, 57.5, LEVEL, "the hold from its stern", 13312),
        "f_panel": (13.8, 60.25, 12.2, 60.25, LEVEL, "the panel", 13312),
        "g_locker": (11.6, 60.2, 11.6, 57.6, LEVEL, "the locker", 13312),
        "h_name": (18.2, 55.2, 18.2, 58.0, LEVEL, "her name"),
        "i_jetty": (26.0, 60.5, 20.0, 58.0, LEVEL, "the bow from the jetty's end"),
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
    #: The works yard's three ways down, for the owner's rework of 2026-11-19
    #: ("entrances to the sewers basically next to each other, weird low door").
    "foundry_ways_down": {
        "yard_west": (54.0, 20.5, 48.5, 20.5, LEVEL, "the yard, facing its west face: stair mouth and dock"),
        "stair_mouth": (51.6, 19.5, 48.0, 19.5, LEVEL, "the works stair's mouth on the yard"),
        "dock_mouth": (51.6, 22.5, 48.0, 22.5, LEVEL, "the low room beside the stair"),
        "stair_down": (49.6, 19.5, 46.0, 19.5, LEVEL, "from the stair head, down the flight"),
        "grate_east": (53.6, 21.9, 50.6, 21.9, LEVEL, "the grate from the spur side"),
    },
    #: The owner's own standing point, 2026-11-20: X 51969 Y 17417 ANG 1553,
    #: "these low doors ... something what is not finished properly".
    "owner_low_door": {
        "low_door": (50.75, 17.01, 50.83, 14.0, LEVEL, "the owner's pose: the yard's north side"),
        "low_door_near": (50.75, 16.2, 50.75, 14.0, LEVEL, "the same, two steps closer"),
        "low_door_east": (52.7, 16.6, 52.7, 14.0, LEVEL, "its neighbour to the east"),
    },
    #: The canteen, for its rebuild as a rat-dog stand (owner, 2026-11-20).
    "canteen": {
        "canteen_front": (51.0, 18.5, 51.0, 14.5, LEVEL, "the canteen's whole yard face"),
        "canteen_face": (51.9, 17.2, 51.9, 15.0, LEVEL, "square on the canteen entrance"),
        "canteen_in": (51.6, 13.2, 50.2, 13.2, LEVEL, "inside the canteen, facing the counter"),
        "canteen_back": (52.5, 14.2, 49.5, 11.5, LEVEL, "inside, from the door corner to the back"),
        "canteen_hatch": (50.7, 16.6, 50.7, 15.0, LEVEL, "square on the RAT DOGS hatch from the yard"),
        "canteen_cook": (51.8, 12.5, 50.7, 14.8, LEVEL, "the hatch from inside, past the table"),
        "canteen_dine": (51.85, 14.5, 49.6, 12.4, LEVEL, "the dine-in from the door: tables, counter, kitchen wall"),
        "freezer_door": (50.5, 14.0, 50.5, 9.0, LEVEL, "the freezer door from the counter side"),
        "freezer_in": (51.4, 9.6, 48.6, 8.2, LEVEL, "inside the freezer, among the carcasses"),
        "canteen_north": (49.6, 10.6, 51.9, 14.2, LEVEL, "the dine-in from its north-west corner to the door"),
    },
    #: Gravesend Station's avenue front (2026-11-20): the avenue's vista, the
    #: front, and the way in to the platform.
    "terminus": {
        "terminus_far": (35.5, 45.0, 35.5, 0.0, LEVEL, "from the market end: the avenue to the station"),
        "terminus_mid": (35.5, 24.0, 35.5, 0.0, LEVEL, "mid-avenue: the station front ahead"),
        "terminus_front": (35.5, 8.0, 35.5, 0.0, UP, "before the front, eyes raised to the clock"),
        "terminus_door": (34.3, 1.5, 34.3, -4.0, LEVEL, "square on the west arch, from the forecourt's mouth"),
        "terminus_hall": (34.0, -5.0, 36.4, -8.5, LEVEL, "inside: the avenue hall and its stair"),
        "terminus_court": (38.6, -0.4, 34.0, -3.0, LEVEL, "across the forecourt to the west arch"),
        "terminus_stair": (36.3, -8.0, 36.3, -13.0, LEVEL, "up the stair to the concourse"),
        "terminus_concourse": (37.5, -13.4, 30.0, -15.4, LEVEL, "the concourse, to the platform", -12288),
        "terminus_platform": (30.4, -15.4, 22.0, -15.8, LEVEL, "out onto the platform's east end", -12288),
    },
    "underpass": {
        "underpass_in": (42.0, 19.0, 42.0, 24.5, LEVEL, "from the yard stair's foot, down the passage"),
        "underpass_bars": (42.0, 22.4, 42.0, 26.5, LEVEL, "the barred mouth of the unfinished metro"),
        "underpass_back": (42.0, 24.6, 42.0, 19.0, LEVEL, "from the passage's end, back to the stairs"),
        "avenue_mouth": (37.6, 19.0, 40.4, 19.0, LEVEL, "the underpass's mouth from the avenue"),
        "service_stair": (42.0, 19.6, 42.0, 15.5, LEVEL, "from the landing, down the service stair"),
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
        "aldermack_front": (27.30, 13.62, 28.05, 11.0, 143, "the Aldermack marquee and its forecourt entrances"),
        "auditorium": (22.5, 10.4, 22.5, 5.6, LEVEL, "the house, facing the stage"),
        "stage_up": (22.5, 8.4, 22.5, 5.2, UP, "the stage and the wall above it"),
        "lobby_avenue": (35.0, 8.66, 32.0, 8.6, 112, "the Aldermack's avenue entrance"),
        "pawn_front": (33.4, 5.1, 32.3, 5.1, LEVEL, "the pawn shop off the avenue"),
        "pawn_in": (28.9, 4.6, 31.6, 4.6, LEVEL, "inside the pawn shop, down the pedestal run"),
    },
    # The kiosk clips the frontage from the middle of the square.
    # These exterior poses follow the clear western approach to the porch.
    "aldermack-front": {
        "forecourt": (27.30, 13.62, 28.05, 11.0, 143, "from the west side of the forecourt to the marquee and bills"),
        "theatre_row": (26.55, 16.24, 28.50, 11.0, 135, "the lit blade from Theatre Row"),
        "porch": (28.2, 12.2, 27.95, 10.65, LEVEL, "the raised double entrance"),
        "box_office": (28.2, 10.2, 28.05, 6.5, LEVEL, "from the entrance to the ticket windows"),
        "cloakroom": (27.7, 8.5, 29.55, 6.8, LEVEL, "towards the cloak counter and broken mirror"),
        "house_route": (29.65, 8.95, 26.0, 9.25, LEVEL, "the carpet, queue rail and last patron"),
        "chandelier": (28.2, 9.7, 27.8, 7.85, UP, "the chandelier and the foyer's ceiling"),
        "avenue_front": (35.0, 8.66, 32.0, 8.6, 112, "the Aldermack's avenue entrance"),
        "avenue_lobby": (31.30, 8.9, 30.65, 7.55, 116, "the bills and gold lettering in the lobby"),
        "avenue_settee": (30.40, 7.80, 31.1, 9.35, LEVEL, "the framed bill and the waiting settee"),
    },
    "diag": {
        "pawn_west": (31.6, 4.6, 28.9, 4.6, LEVEL, "the shop looking back west"),
        "pawn_north": (31.0, 5.7, 31.0, 3.8, LEVEL, "the shop across its short axis"),
        "pawn_door_close": (31.6, 5.0, 32.3, 5.0, LEVEL, "hard up against the shop door"),
    },
    "church": {
        "nave": (29.4, 28.6, 29.4, 24.2, LEVEL, "the nave, north to the chancel"),
        "nave_up": (29.4, 28.6, 29.4, 24.2, UP, "the same, up into the roof"),
        "chancel": (29.4, 25.8, 29.4, 22.7, LEVEL, "the chancel and its altar, from the head of the nave (at 24.6 a candelabrum stood in front of the camera)"),
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
    # the owner's walk of 2026-11-23: the sampling chamber's water and its
    # way out, the race down to its fall, and the Aldermack's stage doors
    "walk-1123": {
        "chamber_fall": (51.25, 57.1, 49.75, 55.75, LEVEL, "the fall, from the inlet below it", 71680),
        "chamber_culvert": (54.0, 56.5, 60.1, 56.5, LEVEL, "the inlet, east to its culvert", 71680),
        "tail_culvert": (54.5, 60.0, 60.1, 60.1, LEVEL, "the tail, east to its culvert", 71680),
        "race_down": (49.0, 48.0, 49.75, 55.75, LEVEL, "down the race to the rack and the fall", 61440),
        "corridor": (17.9, 4.6, 18.6, 9.25, LEVEL, "the Aldermack's backstage corridor, south"),
        "corridor_doors": (17.4, 9.25, 19.2, 9.25, LEVEL, "the stage doors from the corridor"),
        "house_doors": (22.5, 9.25, 19.0, 9.25, LEVEL, "the stage doors from the house"),
    },
    "aldermack-backstage": {
        "from_parlor": (16.68, 7.5, 18.35, 6.92, LEVEL, "across the passage to the keeper's callboard"),
        "scenery_rack": (18.32, 6.9, 17.25, 5.75, LEVEL, "the flats, paint and stage service lamps"),
        "prop_store": (17.95, 4.86, 17.95, 3.63, LEVEL, "HUNT's trick table and balloon in the north recess"),
        "silence": (17.9, 8.2, 17.95, 4.6, LEVEL + 10, "up the corridor to the prop store's sign"),
        "stage_turn": (18.14, 5.52, 18.87, 5.91, LEVEL, "stage sign beside the reserved stair opening"),
        "fire_doors": (17.45, 9.28, 19.1, 9.25, LEVEL, "the paired stage doors across the corridor"),
        "fly_rail": (17.63, 8.12, 17.06, 8.79, DOWN, "the pin rail's lines and their sandbags"),
        "to_dressing": (17.65, 9.51, 17.97, 12.07, LEVEL, "past the prop crate and fire station to dressing"),
        "dressing_entry": (17.94, 11.05, 18.15, 14.45, LEVEL, "the star's portrait from the dressing room door"),
        "makeup": (17.68, 12.06, 18.96, 12.84, LEVEL, "the two stations under their bulb strips"),
        "star": (17.72, 13.25, 18.36, 14.36, LEVEL, "the star's curtained corner and the broken mirror"),
        "costumes": (18.16, 12.93, 17.08, 11.94, LEVEL, "the clothes rail, trunk and folding screen"),
        "behind_screen": (18.05, 13.56, 17.35, 13.12, LEVEL, "the star's empty costume behind the screen"),
    },
    #: what the owner flagged on 2026-11-24 after playing: wooden blocks before the provisions, the lift's upper landing
    "flagged": {
        "fa_prov_w": (17.6, 49.0, 14.0, 46.0, LEVEL, "the provisions front from the south east"),
        "fb_prov_n": (17.5, 40.5, 14.5, 45.0, LEVEL, "the provisions front from the north"),
        "fc_prov_sq": (21.0, 45.0, 13.0, 45.0, LEVEL, "square on the provisions from the plaza"),
        "fd_blocks": (19.5, 43.0, 16.5, 45.5, LEVEL - 10, "the blocks close to"),
        "fe_lift_up": (20.8, 42.75, 19.2, 42.3, LEVEL, "the lift's upper landing", 61440),
        "ff_lift_in": (19.55, 42.0, 19.3, 43.2, LEVEL, "at the lift's button", 59392),
        "fg_under_in": (42.0, 19.0, 42.0, 24.5, LEVEL, "the underpass from the yard's stair"),
        "fh_under_mid": (42.0, 22.4, 42.0, 26.5, LEVEL, "the underpass bars"),
        "fi_avenue": (37.6, 19.0, 40.4, 19.0, LEVEL, "the underpass's avenue mouth"),
        "fj_arcade": (40.2, 45.0, 50.0, 45.0, LEVEL, "the arcade from its west door"),
        "fk_market": (13.0, 45.5, 5.0, 44.0, LEVEL, "the market hall from its door"),
        "fl_plaza": (30.0, 49.5, 18.0, 40.0, LEVEL, "the plaza and what stands in it"),
    },
    #: the six keys where they lie (`gameplay.KEYS`)
    "keys": {
        "k_skull": (28.1, 29.4, 29.1, 28.2, LEVEL - 12, "the skull key on the sarcophagus", 61440),
        "k_flame": (43.75, 7.6, 43.75, 9.5, LEVEL - 14, "the flame key on the belt between the presses", 8192),
        "k_moon": (22.4, 7.4, 22.4, 5.4, LEVEL, "the moon key on the Aldermack's trap", -6160),
        "k_spider": (12.0, 13.2, 12.0, 11.2, LEVEL - 8, "the spider key before the nest", 61440),
        "k_dagger": (27.5, 65.2, 27.5, 66.6, LEVEL - 22, "the dagger key in the throat", 102400),
        "k_eye": (46.2, 46.9, 47.2, 47.6, LEVEL - 10, "the eye key in its shop", 8192),
    },
    #: the station as a lock: what its two fronts show whoever comes without the keys
    "gates": {
        "ga_start": (33.5, 53.0, 35.5, 45.0, LEVEL, "the player's first frame"),
        "gb_avenue": (35.5, 8.0, 35.5, -5.0, LEVEL, "up the avenue to the terminus"),
        "gc_front": (35.5, 1.5, 35.5, -5.0, LEVEL, "the terminus front from the street"),
        "gd_west": (13.2, 4.0, 13.2, -4.0, LEVEL, "the station's west front"),
        "ge_westdoor": (13.2, 0.8, 13.2, -8.0, LEVEL, "the west door, near"),
        "gf_close": (35.5, -1.2, 35.5, -5.0, LEVEL, "the pier between the terminus doors"),
    },
    #: the settling hall: what joins the sewer to the Cabal's mouth
    "hall": {
        "h_outfall": (33.0, 36.0, 33.0, 41.0, LEVEL, "down the outfall toward the hall", 63488),
        "h_gallery_e": (34.3, 42.75, 27.0, 46.0, LEVEL, "the gallery walk's east end, over the hall", 61440),
        "h_gallery_m": (26.0, 42.75, 27.5, 50.0, LEVEL, "the gallery's middle, over the tanks to the mouth", 61440),
        "h_gallery_w": (20.3, 42.75, 30.0, 47.0, LEVEL, "the gallery walk's west end", 61440),
        "h_stair": (34.0, 44.5, 33.9, 50.0, DOWN, "down the stair", 73728),
        "h_quay_e": (34.5, 49.5, 22.0, 48.0, LEVEL, "along the south quay from its east end", 102400),
        "h_quay_w": (20.5, 49.5, 34.0, 47.5, LEVEL, "along the south quay from its west end", 102400),
        "h_west": (20.5, 43.5, 30.0, 49.0, LEVEL, "down the west quay", 102400),
        "h_brink": (33.0, 40.7, 33.0, 49.0, LEVEL - 8, "the outfall's last metres: over the gallery and down the falls", 63488),
        "h_up": (31.5, 49.3, 33.3, 43.0, UP, "the falls and the stair from the quay", 102400),
        "h_walk": (31.5, 44.62, 21.0, 44.62, LEVEL, "the walk between two tanks", 102400),
        "h_vault": (26.4, 47.6, 24.0, 43.2, UP, "the vaults over the tanks", 106496),
        "h_back": (27.5, 49.5, 27.5, 42.0, LEVEL, "from the mouth back over the tanks", 102400),
    },
    #: the Cabal's chamber behind the settling hall (`cabal_rite`)
    "rite": {
        "a_mouth": (27.5, 48.4, 27.5, 51.5, LEVEL, "the mouth in the quay's south wall", 102400),
        "b_overlook": (27.5, 51.6, 27.5, 57.8, LEVEL - 18, "the chamber from the gallery inside the mouth", 102400),
        "c_gallery": (33.2, 55.6, 26.0, 59.0, LEVEL - 12, "across the chamber from the east gallery", 102400),
        "d_floor": (26.3, 54.2, 27.6, 58.6, LEVEL, "the sign and the well from the foot of the runner", 118784),
        "e_well": (29.6, 56.0, 27.5, 57.8, LEVEL - 14, "the well close to", 118784),
        "f_dais": (27.5, 60.2, 27.5, 64.0, LEVEL + 12, "the dais, the altar and the window", 118784),
        "g_back": (28.35, 63.5, 27.2, 57.0, LEVEL - 10, "back from beside the altar", 110592),
        "h_niche": (30.2, 53.6, 31.5, 52.3, LEVEL, "a niche of the gallery", 102400),
        "j_candles": (32.6, 59.9, 34.2, 60.4, LEVEL, "the niche of candles", 102400),
        "k_rose": (27.5, 62.9, 27.5, 68.5, LEVEL + 20, "the rose over the altar", 110592),
        "l_throat": (27.5, 65.75, 27.5, 69.0, LEVEL, "behind the glass, down the gullet to the heart", 102400),
        "m_heart": (27.5, 67.2, 27.5, 69.0, LEVEL, "the column and the eye", 102400),
        "i_box": (28.6, 57.8, 34.0, 57.8, LEVEL + 30, "a box over the gallery, from the floor", 118784),
    },
    "sewer-water": {
        "brook_inlet": (3.6, 19.65, 1.0, 19.5, LEVEL, "Graves Brook, west toward the feeder", 63488),
        "brook_walk": (6.0, 19.3, 15.0, 18.6, LEVEL, "Graves Brook, east along the north wall", 63488),
        "brook_drip": (24.1, 19.65, 23.33, 18.54, LEVEL, "Graves Brook, across to the north walk", 63488),
        "outfall": (33.0, 37.5, 33.0, 42.0, LEVEL, "the outfall running south into the gallery", 63488),
        "gallery": (34.1, 41.65, 31.5, 42.4, LEVEL, "the gallery channel toward the settling tank spillway", 63488),
        "tank_foot": (32.0, 45.7, 32.0, 42.75, LEVEL, "tank 1 facing the spillway", 106496),
    },
    "sewer": {
        #: the sewer floor, named: without it a pose stands on the street above
        #: (the set predates the stacked city, and rendered the street until 2026-11-20)
        "north_walk": (38.0, 6.5, 42.0, 7.5, LEVEL, "the north walk beside its channel", 61440),
        "pump_room": (31.0, 15.0, 28.0, 14.0, LEVEL, "the pumping chamber", 61440),
        "flooded": (42.0, 34.5, 42.5, 38.0, LEVEL, "into the flooded branch", 61440),
        "east_leg": (52.0, 20.0, 52.0, 16.0, LEVEL, "the east leg of the ring", 61440),
        "annex": (52.5, 17.0, 56.0, 17.5, LEVEL, "the eastern annex", 61440),
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


def sector_at(level, x: int, y: int, near: int | None = None) -> int | None:
    """The sector at a point -- the one a person would be standing in.

    `bloodmap.sector_geom.sector_at`, asked for the sector whose floor is
    nearest the street's: a pose here is written for a person on the ground,
    and the city is stacked (a sewer under the avenue, a roof over the
    church). A pose meant for another level names its z as `near`.
    """
    return _sector_at(level, x, y,
                      floor_near=GRADE_Z if near is None else near)


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
        outer, _holes = outline_and_holes(level, sector_id)
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
