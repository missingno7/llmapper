"""Four frames of the built city, drawn from the map file and nothing else.

Not the observer: the standing rule for this run is that neither NBlood nor
XMapEdit is launched, so these are plan renders made offline from
`slice2-streets.MAP`. What they can show is exactly what the model claims --
the ground plane and the islands standing on it, every piece filled by the
shade the light field actually gave it, and each join drawn in the colour of
the rule that decided it. What they cannot show is a body's eye view, and
that is named rather than implied.

Each frame is written with the commit hash in its name so a picture can be
traced to the code that made it.
"""

from __future__ import annotations

import pathlib
import subprocess
import sys

HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parents[2]
for path in (str(ROOT), str(HERE)):
    if path not in sys.path:
        sys.path.insert(0, path)

import matplotlib                                                 # noqa: E402

matplotlib.use("Agg")
import matplotlib.pyplot as plt                                   # noqa: E402
from matplotlib.patches import Polygon as MplPolygon              # noqa: E402

from bloodmap.format import read_map                              # noqa: E402
from bloodmap.texture_frame import sector_index                   # noqa: E402
from build_graph_slice2 import (                                  # noqa: E402
    HORIZON_TILE, PAVE_TILE, ROAD_TILE, SEA_TILE, SHORE_TILE, geometry)

#: What each surface kind is drawn in. Shade modulates the fill, so a piece
#: three shadows deep is visibly darker than the same kind in full sun.
KIND_COLOUR = {
    ROAD_TILE: (0.55, 0.52, 0.50),
    PAVE_TILE: (0.72, 0.68, 0.62),
    SHORE_TILE: (0.82, 0.75, 0.55),
    SEA_TILE: (0.30, 0.45, 0.62),
    HORIZON_TILE: (0.60, 0.70, 0.82),
}
#: The join that decided each record, by the tile the table wrote on it.
RECORD_COLOUR = {6: "#c8452e", 400: "#8a5cc8", 28: "#2e8ac8"}

FRAMES = (
    ("street", "The west street from the road, with its kerbs",
     (18000, 22000, 30000, 36000)),
    ("junction", "Where the avenue crosses Theatre Row",
     (38000, 15000, 52000, 29000)),
    ("path", "The market plaza, and the path onto its island",
     (24000, 36000, 43000, 49000)),
    ("quay", "The quay: walk, shore, sea and the horizon beyond",
     (0, 55000, 73728, 81920)),
)


def _rings(disk, sector_id):
    fields = disk.sectors[sector_id].fields
    start = int(fields["wall_ptr"])
    count = int(fields["wall_count"])
    rings = []
    index = start
    while index < start + count:
        ring = []
        walk = index
        while True:
            face = disk.walls[walk].fields
            ring.append((int(face["x"]), int(face["y"])))
            walk = int(face["point2"])
            if walk == index:
                break
        rings.append(ring)
        index += len(ring)
    return rings


def render(map_path: pathlib.Path, out_dir: pathlib.Path, commit: str):
    disk = read_map(map_path)
    owners = sector_index(disk)
    out_dir.mkdir(parents=True, exist_ok=True)
    written = []
    for name, title, (x0, y0, x1, y1) in FRAMES:
        figure, axes = plt.subplots(figsize=(9, 9 * (y1 - y0) / (x1 - x0)))
        for index, sector in enumerate(disk.sectors):
            fields = sector.fields
            base = KIND_COLOUR.get(int(fields["floor_picnum"]),
                                   (0.4, 0.4, 0.4))
            #: Blood's shade grows darker upward, so a bigger number is less
            #: light. 8 is the city's lit base and 44 its deepest shadow.
            lit = max(0.35, 1.0 - (int(fields["floor_shade"]) - 2) / 90.0)
            colour = tuple(min(1.0, channel * lit) for channel in base)
            for ring in _rings(disk, index):
                axes.add_patch(MplPolygon(ring, closed=True, facecolor=colour,
                                          edgecolor="none", zorder=1))
        for wall_id, wall in enumerate(disk.walls):
            face = wall.fields
            nxt = disk.walls[int(face["point2"])].fields
            xs = (int(face["x"]), int(nxt["x"]))
            ys = (int(face["y"]), int(nxt["y"]))
            if int(face["next_sector"]) < 0:
                axes.plot(xs, ys, color="#1a1a1a", linewidth=1.1, zorder=3)
            else:
                colour = RECORD_COLOUR.get(int(face["picnum"]))
                if colour:
                    axes.plot(xs, ys, color=colour, linewidth=1.0, zorder=2)
        for sprite in disk.sprites:
            axes.plot(int(sprite.fields["x"]), int(sprite.fields["y"]),
                      marker="o", markersize=4, color="#ffd24d", zorder=4)
        axes.set_xlim(x0, x1)
        axes.set_ylim(y1, y0)
        axes.set_aspect("equal")
        axes.set_xticks([])
        axes.set_yticks([])
        axes.set_title(f"{title}\n{commit}", fontsize=9)
        target = out_dir / f"slice2i-{name}-{commit}.png"
        figure.savefig(target, dpi=130, bbox_inches="tight")
        plt.close(figure)
        written.append(target)
    return written


def main() -> int:
    commit = subprocess.run(["git", "rev-parse", "--short", "HEAD"],
                            cwd=ROOT, capture_output=True, text=True,
                            check=True).stdout.strip()
    geometry()
    for path in render(HERE / "slice2-streets.MAP",
                       ROOT / "projects/blood-city/renders", commit):
        print("wrote", path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
