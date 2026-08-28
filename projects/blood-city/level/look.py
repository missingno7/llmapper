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
    "pilot": {
        "spur_street": (55.5, 26, 55.5, 16, LEVEL, "the rail spur, facing the yard"),
        "yard": (51.5, 19.5, 55.5, 19.5, LEVEL, "in the works yard, facing the spur"),
        "canteen_in": (51.6, 13.2, 50.2, 13.2, LEVEL, "inside the canteen, facing the counter"),
        "grate_stand": (49.4, 21.5, 50.5, 21.5, LEVEL, "the grate and its kerb, from the dock"),
        "sewer_junction": (114.0, 12.0, 118.0, 12.0, LEVEL, "the sewer junction (parked)"),
    },
    "fresh1": {
        "quay_start": (33.5, 53.0, 35.5, 45.0, LEVEL, "the player's first frame: quay, facing the avenue"),
        "avenue_vista": (35.0, 30.0, 35.0, 14.0, LEVEL, "mid-avenue, the Aldermack vista north"),
        "avenue_up": (35.0, 30.0, 35.0, 14.0, UP, "the same, looking up the canyon"),
        "plaza_centre": (22.5, 45.0, 33.0, 45.0, LEVEL, "market plaza, facing east past the monument"),
        "yard_approach": (55.5, 19.5, 50.0, 19.5, LEVEL, "approaching the yard off the spur"),
        "cellar": (41.0, 12.8, 42.6, 13.8, LEVEL, "the works cellar, facing the pit"),
    },
    "fresh2": {
        "canteen_door": (51.9, 16.4, 51.9, 13.5, LEVEL, "the canteen door from the yard"),
        "dock": (50.0, 18.0, 48.5, 18.0, LEVEL, "the loading dock alcove"),
        "west_lane": (1.5, 25.0, 1.5, 40.0, LEVEL, "the west lane, south along the tenements"),
        "cemetery_gate": (18.0, 28.0, 24.0, 28.0, LEVEL, "the lychgate from the west street"),
        "sewer_trunk": (115.0, 21.5, 121.0, 21.5, LEVEL, "the sewer trunk, facing the grate shaft"),
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
    "overhaul": {
        "shop_window": (30.2, 1.9, 30.2, 3.4, LEVEL, "the glazed shopfront from Theatre Row"),
        "shop_window_close": (30.2, 2.6, 30.2, 3.4, LEVEL, "up against the glass"),
        "saloon_door": (6.6, 16.2, 6.6, 14.6, LEVEL, "the saloon door, at its new height"),
        "saloon_in": (9.4, 12.4, 6.6, 9.8, LEVEL, "the saloon and its wall braziers"),
        "nave": (29.4, 28.6, 29.4, 24.2, LEVEL, "the nave, braziers on the aisle walls"),
        "street_lamp": (35.0, 30.0, 35.0, 14.0, LEVEL, "the avenue and its lamps"),
        "sewer_wet": (117.5, 7.0, 117.5, 12.0, LEVEL, "the wet channel, where the water dressing is"),
    },
    "signs": {
        "aldermack_sign": (28.2, 12.8, 28.2, 10.9, LEVEL, "the Aldermack's name over its portal"),
        "saloon_sign": (8.6, 10.5, 10.1, 10.5, LEVEL, "WHISKEY on the saloon's east wall"),
        "pawn_sign": (29.6, 4.9, 28.7, 4.9, LEVEL, "PAWN inside the shop"),
        "nave_sign": (29.4, 27.0, 29.4, 30.5, LEVEL, "ST GALLOWS across the nave's south wall"),
        "sewer_sign": (110.5, 15.0, 110.5, 12.2, LEVEL, "OUTFALL in the pump chamber"),
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
        "station_foot": (116.5, 5.0, 115.0, 5.0, LEVEL, "the shaft foot, down in the sewer"),
    },
    "lamp_pools": {
        "yard_lamp": (51.0, 19.0, 50.0, 19.0, LEVEL, "close to the works-yard lamp pool"),
        "forecourt_lamp": (30.0, 13.0, 31.0, 13.0, LEVEL, "close to the forecourt lamp pool"),
        "quay_lamp": (36.0, 52.0, 37.0, 52.0, LEVEL, "close to the quay-gate lamp pool"),
    },
    "sewer": {
        "north_walk": (110.0, 6.5, 114.0, 7.5, LEVEL, "the north walk beside its channel"),
        "pump_room": (103.0, 15.0, 100.0, 14.0, LEVEL, "the pumping chamber"),
        "flooded": (114.0, 34.5, 114.5, 38.0, LEVEL, "into the flooded branch"),
        "east_leg": (124.0, 20.0, 124.0, 16.0, LEVEL, "the east leg of the ring"),
        "annex": (124.5, 17.0, 128.0, 17.5, LEVEL, "the eastern annex"),
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
        "stash": (109.0, 21.5, 112.0, 22.5, LEVEL, "the secret stash off the sewer trunk"),
        "canteen_side": (49.5, 16.0, 50.5, 13.5, LEVEL, "the canteen's second door from the yard"),
        "pit_bottom": (114.0, 17.0, 116.5, 15.5, LEVEL, "the cellar pit landing, parked side"),
        "well_sq": (14.0, 27.0, 17.0, 25.5, LEVEL, "the well square in Old Crossing"),
    },
    "fresh4": {
        "pool_yard": (54.0, 19.5, 50.0, 19.5, LEVEL, "the works yard west: lamps, dock, stair mouth"),
        "pool_quay": (35.0, 51.0, 32.5, 52.5, LEVEL, "the quay gate pool"),
        "pool_forecourt": (32.0, 14.2, 30.5, 13.0, LEVEL, "the forecourt pool and kiosk"),
        "sewer_wet": (117.0, 21.5, 113.0, 21.5, LEVEL, "the wet trunk, west toward the junction"),
        "market_plaza_w": (33.0, 45.0, 20.0, 45.0, LEVEL, "the plaza, west past the monument"),
    },
    "fresh3": {
        "theatre_row": (17.5, 18.0, 24.0, 16.5, LEVEL, "Theatre Row street, east toward the forecourt"),
        "forecourt": (29.5, 14.0, 31.5, 12.5, LEVEL, "the Aldermack forecourt"),
        "north_lane": (36.5, 1.5, 42.0, 3.0, LEVEL, "the north lane, east to the spur"),
        "market_st": (25.0, 37.5, 33.0, 40.0, LEVEL, "market street, east"),
        "quay_up": (33.5, 53.0, 33.5, 45.0, UP, "the quay, looking up at the block tops"),
    },
}


def sector_at(level, x: int, y: int) -> int | None:
    for sector_id in range(len(level.sectors)):
        # `_contains` handles outer loops and carved holes.  The old observer
        # helper accepted a camera inside a street's carved lamp/building hole
        # and then handed it to the renderer as the host sector, producing an
        # invalid frame exactly where close light-pool review is needed.
        if _contains(level, sector_id, x, y):
            return sector_id
    return None


def poses_for(level, name: str) -> list[Viewpoint]:
    out = []
    for view_id, (px, py, tx, ty, horiz, note) in POSE_SETS[name].items():
        x, y = int(px * PU), int(py * PU)
        sector = sector_at(level, x, y)
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
    args = parser.parse_args(argv)

    map_path = (pathlib.Path(f"maps/blood/{args.ref}.MAP") if args.ref
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
        map_path=map_path, output_dir=out_dir,
        resource_dir=pathlib.Path("reference/blood"), viewpoints=views,
        width=640, height=480, screenshots=[v.view_id for v in views],
        brightness=0, rff=None))
    print(f"{len(views)} frames -> {out_dir}")
    for view in views:
        print(f"  {view.view_id}: sector {view.sector} z {view.z} -- {view.note}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
