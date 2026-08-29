"""Look at the fragment from standing eye height, and at BB4 the same way.

.. code-block:: bash

    python projects/vertical-fragment/level/look.py            # the fragment
    python projects/vertical-fragment/level/look.py --ref       # BB4, same settings

The acceptance asks for frames at each level and at the overlap boundaries,
against campaign instances *under identical conditions*. Identical conditions is
the whole point of doing it in one script: same observer, same 640x480, same
brightness, same eye height rule. A side-by-side taken any other way compares two
renderers as much as two levels.

Never launches the game. The XMapEdit observer renders from a pose.
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
from bloodmap.viewpoints import _contains, _sector_loops
from bloodmap.visual import ObservationRequest, Viewpoint, run_observation

import fragment

PROJECT = pathlib.Path(__file__).resolve().parents[1]
MAP = PROJECT / "level" / "MALTX.MAP"

#: Build's horizon. 100 is level; the observer takes Build's own units.
LEVEL, UP, DOWN = 100, 155, 45

#: How far below a floor the eye sits, by the same rule `viewplan.eye_z` uses:
#: nine tenths of a standing body, so a frame is taken from where a player's
#: head is rather than from the middle of the room.
EYE = int(fragment.PH * 0.9)

#: (x, y, look-at x, look-at y, horiz, band, note)
#:
#: **Every pose names its band**, and that is not bookkeeping. Once layers exist
#: a plan point is inside three sectors at once, and "the sector at (x, y)" has
#: no answer: the first version of this file put the malt loft's camera on the
#: mash floor beneath it and the cellar's camera in the yard above it, because it
#: asked in plan alone.
#:
#: That is the same fault `layers.check` refuses under `layer-owner-over-overlap`
#: -- found here on this project's own side of the boundary. A standing pose is
#: (x, y, **z**), the way `inside_z_p` asks it.
#:
#: "deck" is the sprite gantry: it stands in the yard's sector at the upper
#: band's height, which is the one case no sector's floor can answer for.
POSES = {
    # -- street ------------------------------------------------------------
    "yard": (5000, 9200, 5000, 6200, LEVEL, "street",
             "the yard from its south end, north between the two buildings"),
    "yard_up": (5000, 9200, 5000, 6200, UP, "street",
                "the same, looking up at the lofts and the sky over them"),
    "mash": (2000, 4600, 2000, 1200, LEVEL, "street",
             "the mash floor, north up the brewhouse"),
    "kiln_floor": (7900, 4600, 7900, 1200, LEVEL, "street",
                   "the kiln's drying floor"),
    "store": (4800, 11200, 7600, 11200, LEVEL, "street",
              "inside the store, east toward the stairhead wall"),

    # -- street facades: one door each, the lofts leave from the side --------
    "kiln_facade": (7550, 9200, 7550, 5400, LEVEL, "street",
                    "back in the yard, north at the kiln's south face: the "
                    "street door only -- the loft leaves from the west"),
    "kiln_facade_up": (7550, 9200, 7550, 5400, UP, "street",
                       "the same facade, up at the loft's solid south wall"),
    "brew_facade": (1800, 9200, 1800, 5400, UP, "street",
                    "the brewhouse's south face, street door only"),

    # -- the overlap boundaries -------------------------------------------
    "hatch_edge": (4864, 9000, 4864, 7800, DOWN, "street",
                   "beside the malt hatch, looking down through the yard floor "
                   "into the cellar: street over undercroft"),
    "hatch_near": (4864, 8700, 4864, 7600, DOWN, "street",
                   "closer on the same opening"),
    "under_hatch": (4864, 6900, 4864, 7800, UP, "undercroft",
                    "from the cellar, looking back up at the hole"),
    "roof_edge": (7000, 10600, 7000, 8000, DOWN, "upper",
                  "the store roof at its edge, down into the yard: "
                  "upper over street"),

    # -- upper -------------------------------------------------------------
    "loft": (2000, 4600, 2000, 1200, LEVEL, "upper",
             "the malt loft, over the mash floor and the same shape as it"),
    "loft_door": (2000, 1150, 6144, 1150, LEVEL, "upper",
                  "the malt loft's north end, east toward the alley"),
    "alley": (6144, 1150, 6144, 5000, LEVEL, "upper",
              "the alley landing, south down the close between the buildings"),
    "kiln_door": (7500, 1150, 6144, 1150, LEVEL, "upper",
                  "the kiln loft, west through its side wall into the alley"),
    "west_porch": (-512, 6400, 2000, 6400, LEVEL, "upper",
                   "the west porch, east onto the gantry between the lofts"),
    "east_porch": (10496, 6400, 5000, 6400, LEVEL, "upper",
                   "the east porch, west onto the gantry -- this is wall 7"),
    "brew_window": (1536, 5620, 1536, 8000, LEVEL, "upper",
                    "the malt loft's south window, looking out over the yard"),
    "kiln_balcony": (9600, 5620, 10496, 5620, LEVEL, "upper",
                     "the kiln balcony, east toward the porch on the yard's east wall"),
    "gantry": (5000, 6400, 9984, 6400, LEVEL, "deck",
               "standing on the sprite deck, mid-yard, east toward the kiln porch"),
    "gantry_down": (5000, 6400, 5000, 7200, DOWN, "deck",
                    "the same, looking down at the cobbles being crossed"),
    "leads": (7000, 11400, 7000, 8000, LEVEL, "upper",
              "the store roof, north off its open edge over the yard"),
    "leads_edge": (7000, 10400, 7000, 8600, DOWN, "upper",
                   "at the roof's open edge, down into the yard"),
    "kiln_loft": (7900, 4600, 7900, 1200, LEVEL, "upper",
                  "the kiln loft"),

    # -- the malt tower, against E3M1's own spiral --------------------------
    "tower_foot": (3555, 14404, 3400, 15200, UP, "tower_bottom",
                   "the foot of the malt tower, looking up the well"),
    "tower_mid": (3245, 15996, 3400, 15200, LEVEL, "tower_middle",
                  "mid-climb, round the newel"),
    "tower_head": (3241, 14405, 3400, 15200, DOWN, "tower_top",
                   "the top of the tower, looking back down"),

    # -- undercroft --------------------------------------------------------
    "vault": (2600, 7900, 7800, 7900, LEVEL, "undercroft",
              "the malt cellar, east along the vault"),
    "vault_stair": (7900, 8900, 4200, 12200, LEVEL, "undercroft",
                    "the cellar's south end, toward the passage out"),
    "cellar_stair": (4100, 12800, 8000, 12800, UP, "undercroft",
                     "the foot of the stair up into the store"),

    # -- the stairwell, which is the only place three bands are one object --
    "stairwell": (4600, 1000, 4600, 4600, DOWN, "upper",
                  "the head of the malt stair, down the run"),
    "stairfoot": (4600, 5100, 4600, 1000, UP, "street",
                  "from the bottom of the same stair, back up it"),
}

#: BB4's three bands, one sector each, picked from
#: `knowledge/blood/design/layers-v1.json`: ground floor 8192, middle -32768,
#: upper -65536. These are the campaign instances the fragment is measured
#: against, and they are rendered by the same call with the same settings.
REFERENCE_MAP = ROOT / "maps" / "blood" / "BB4.MAP"

#: E3M1's spiral, the prefab's precedent: sectors 15-40. Bottom, middle and top
#: of the run, rendered by the same call with the same settings so a side-by-side
#: against the malt tower compares two stairs rather than two renderers.
E3M1_SPIRAL = {"bottom": 39, "middle": 27, "top": 15}


#: Where each band's floor stands. The deck's host sector is the yard, so it
#: resolves on the street floor and takes its height separately.
BAND_FLOOR = {
    "street": fragment.STREET_FLOOR,
    "upper": fragment.UPPER_FLOOR,
    "undercroft": fragment.UNDERCROFT_FLOOR,
    "deck": fragment.STREET_FLOOR,
    # The tower passes through every band, so a pose in it is resolved against
    # the step it is standing on rather than against a storey.
    "tower_bottom": fragment.UNDERCROFT_FLOOR,
    "tower_middle": 8189,
    "tower_top": fragment.UPPER_FLOOR,
}


def sector_at(level, x: int, y: int, floor_z: int | None = None) -> int | None:
    """The sector at (x, y) standing on `floor_z`, not merely the one at (x, y).

    `_contains` handles carved holes. `floor_z` is what makes the answer unique
    once layers exist: three sectors can hold one plan point, and the one the
    camera is in is the one whose floor is the one it is standing on.
    """
    found = [s for s in range(len(level.sectors)) if _contains(level, s, x, y)]
    if not found:
        return None
    if floor_z is None:
        return found[0]
    return min(found, key=lambda s: abs(
        int(level.sectors[s]["fields"]["floor_z"]) - floor_z))


def fragment_poses(level) -> list[Viewpoint]:
    out: list[Viewpoint] = []
    for view_id, (px, py, tx, ty, horiz, band, note) in POSES.items():
        sector = sector_at(level, px, py, BAND_FLOOR[band])
        if sector is None:
            print(f"  ! {view_id}: no sector at ({px},{py}) -- skipped")
            continue
        # The gantry is the one camera whose host sector cannot say how high it
        # stands: it is a surface with no sector behind it.
        z = ((fragment.UPPER_FLOOR - EYE) if band == "deck"
             else eye_z(level, sector))
        if z is None:
            print(f"  ! {view_id}: sector {sector} has no standing height")
            continue
        out.append(Viewpoint(
            view_id=view_id, x=px, y=py, z=z,
            angle=int(angle_toward((px, py), (tx, ty))) & 2047,
            horiz=horiz, sector=sector, node=f"pose:{view_id}",
            purpose="acceptance", screenshot=True, note=note))
    return out


def band_sectors(level, wanted: dict[str, int]) -> dict[str, int]:
    """The largest sector standing on each named floor height."""
    from bloodmap.viewplan import sector_area

    out: dict[str, int] = {}
    for name, floor_z in wanted.items():
        candidates = [
            index for index in range(len(level.sectors))
            if int(level.sectors[index]["fields"]["floor_z"]) == floor_z
        ]
        if candidates:
            out[name] = max(candidates, key=lambda s: sector_area(level, s))
    return out


def spiral_reference_poses(level) -> list[Viewpoint]:
    """E3M1's own spiral from its foot, its middle and its head."""
    out: list[Viewpoint] = []
    horizons = {"bottom": UP, "middle": LEVEL, "top": DOWN}
    axis_x = sum(p[0] for s in E3M1_SPIRAL.values()
                 for p in _sector_loops(level, s)[0])
    axis_y = sum(p[1] for s in E3M1_SPIRAL.values()
                 for p in _sector_loops(level, s)[0])
    count = sum(len(_sector_loops(level, s)[0]) for s in E3M1_SPIRAL.values())
    axis = (axis_x // count, axis_y // count)
    for name, sector_id in E3M1_SPIRAL.items():
        point = interior_point(level, sector_id)
        z = eye_z(level, sector_id)
        if point is None or z is None:
            continue
        out.append(Viewpoint(
            view_id=f"e3m1_{name}", x=point[0], y=point[1], z=z,
            angle=int(angle_toward(point, axis)) & 2047, horiz=horizons[name],
            sector=sector_id, node=f"sector:{sector_id}", purpose="reference",
            screenshot=True,
            note=f"E3M1 spiral {name}, sector {sector_id}"))
    return out


def reference_poses(level) -> list[Viewpoint]:
    """One frame per BB4 band, aimed down the long axis of the room."""
    out: list[Viewpoint] = []
    bands = band_sectors(level, {"ground": 8192, "middle": -32768, "upper": -65536})
    for name, sector_id in bands.items():
        point = interior_point(level, sector_id)
        z = eye_z(level, sector_id)
        if point is None or z is None:
            continue
        outer = _sector_loops(level, sector_id)[0]
        far = max(outer, key=lambda p: (p[0] - point[0]) ** 2 + (p[1] - point[1]) ** 2)
        out.append(Viewpoint(
            view_id=f"bb4_{name}", x=point[0], y=point[1], z=z,
            angle=int(angle_toward(point, far)) & 2047, horiz=LEVEL,
            sector=sector_id, node=f"sector:{sector_id}", purpose="reference",
            screenshot=True,
            note=f"BB4 {name} band, sector {sector_id}, floor "
                 f"{level.sectors[sector_id]['fields']['floor_z']}"))
    return out


def sweep_poses(level, *, step: int = 1024, angles: int = 8,
                limit: int = 600) -> list[Viewpoint]:
    """Every place a player could stand, looking every way, on a grid.

    The renderer fault this exists to find is a property of the *view*, not of
    the map: two storeys with the same outline are fine until one pose holds
    both. Hand-picked poses will not find that -- the owner found it by walking
    in from the side -- so this stands on a grid in every sector and turns all
    the way round at each point.
    """
    out: list[Viewpoint] = []
    for sector_id in range(len(level.sectors)):
        z = eye_z(level, sector_id)
        if z is None:
            continue
        loops = _sector_loops(level, sector_id)
        if not loops:
            continue
        xs = [p[0] for p in loops[0]]
        ys = [p[1] for p in loops[0]]
        points = [(x, y)
                  for x in range(min(xs) + step // 2, max(xs), step)
                  for y in range(min(ys) + step // 2, max(ys), step)
                  if _contains(level, sector_id, x, y)]
        if not points:
            point = interior_point(level, sector_id)
            if point is None:
                continue
            points = [point]
        for px, py in points:
            for turn in range(angles):
                out.append(Viewpoint(
                    view_id=f"s{sector_id}_{px}_{py}_a{turn}",
                    x=px, y=py, z=z, angle=(turn * 2048) // angles,
                    horiz=LEVEL, sector=sector_id,
                    node=f"sweep:{sector_id}", purpose="sweep",
                    screenshot=False,
                    note=f"sector {sector_id} at ({px}, {py})"))
                if len(out) >= limit:
                    return out
    return out


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--ref", action="store_true",
                        help="render BB4's bands instead, under identical settings")
    parser.add_argument("--spiral", action="store_true",
                        help="render E3M1's own spiral, same settings")
    parser.add_argument("--sweep", action="store_true",
                        help="stand everywhere and look every way, to find the "
                             "views where two storeys the renderer cannot order "
                             "are both on screen")
    parser.add_argument("--step", type=int, default=1024)
    parser.add_argument("--angles", type=int, default=8)
    parser.add_argument("--limit", type=int, default=600)
    parser.add_argument("--tag", default=None)
    args = parser.parse_args(argv)

    map_path = (ROOT / "maps" / "blood" / "E3M1.MAP") if args.spiral else (
        REFERENCE_MAP if args.ref else MAP)
    level = read_map(map_path).to_level_ir()
    if args.spiral:
        views = spiral_reference_poses(level)
    elif args.sweep:
        views = sweep_poses(level, step=args.step, angles=args.angles,
                            limit=args.limit)
    elif args.ref:
        views = reference_poses(level)
    else:
        views = fragment_poses(level)
    if not views:
        print("no poses resolved")
        return 1

    out_dir = PROJECT / "reports" / "looks" / (
        args.tag or ("sweep" if args.sweep else "e3m1-spiral" if args.spiral
                     else "bb4" if args.ref else "maltx"))
    out_dir.mkdir(parents=True, exist_ok=True)
    run_observation(ObservationRequest(
        map_path=str(map_path), output_dir=str(out_dir),
        resource_dir=str(ROOT / "reference" / "blood"), viewpoints=tuple(views),
        width=640, height=480, screenshots=not args.sweep, brightness=0, rff=None))
    print(f"{len(views)} frames -> {out_dir}")
    if args.sweep:
        print("now: python -m tools.render_conflicts {} {}".format(
            map_path, out_dir / "observation.json"))
        return 0
    for view in views:
        print(f"  {view.view_id}: sector {view.sector} z {view.z} -- {view.note}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
