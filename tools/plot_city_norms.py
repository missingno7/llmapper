"""Draw what mine_city_norms decided, so a person can call it wrong.

One plan per source map: every wall in light gray, the detected street
component filled, walk-around blocks hatched, doorways from street marked.
The classifier's mistakes (a landscape picked as a street, a courtyard read
as a block) are invisible in the JSON and obvious here.

    python -m tools.plot_city_norms -o projects/blood-city/references/plots
"""

from __future__ import annotations

import argparse
import pathlib

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

from tools.mine_city_norms import (
    STRUCTURE_SOURCES, StreetRaster, load_source, street_component,
    indoor_components, doorways, CELL,
)


def plot_map(name: str, game: str, path: str, out_dir: pathlib.Path) -> None:
    geom = load_source(name, game, path)
    street = street_component(geom)
    raster = StreetRaster(geom, street)
    blocks = raster.enclosed_components()
    _parts, membership = indoor_components(geom, street)
    doors = doorways(geom, street, membership)

    fig, ax = plt.subplots(figsize=(14, 14))
    extent = (raster.x0, raster.x0 + raster.nx * CELL,
              raster.y0 + raster.ny * CELL, raster.y0)
    street_img = np.where(raster.mask, 1.0, np.nan)
    ax.imshow(street_img, extent=extent, cmap="Blues", vmin=0, vmax=2,
              alpha=0.5, interpolation="nearest")
    block_img = np.full(raster.labels.shape, np.nan)
    for block in blocks:
        block_img[raster.labels == block["label"]] = 1.0
    ax.imshow(block_img, extent=extent, cmap="Oranges", vmin=0, vmax=2,
              alpha=0.6, interpolation="nearest")

    for wall_id in range(len(geom.walls)):
        (x1, y1), (x2, y2) = geom.wall_segment(wall_id)
        red = int(geom.walls[wall_id].fields["next_sector"]) >= 0
        ax.plot([x1, x2], [y1, y2], color="0.75" if red else "0.35",
                linewidth=0.3 if red else 0.5)

    for door in doors:
        (x1, y1), (x2, y2) = geom.wall_segment(door["wall"])
        ax.plot([(x1 + x2) / 2], [(y1 + y2) / 2], marker="o", markersize=4,
                color="crimson")

    ax.set_title(f"{name}: street (blue), blocks (orange), doorways (red)  "
                 f"street={len(street)} blocks={len(blocks)} doors={len(doors)}")
    ax.set_aspect("equal")
    ax.invert_yaxis()  # Build y grows south; plans read north-up
    fig.tight_layout()
    out = out_dir / f"{name.lower()}-city-plan.png"
    fig.savefig(out, dpi=110)
    plt.close(fig)
    print(f"wrote {out}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("-o", "--output", default="projects/blood-city/references/plots")
    parser.add_argument("--maps", nargs="*")
    args = parser.parse_args(argv)
    out_dir = pathlib.Path(args.output)
    out_dir.mkdir(parents=True, exist_ok=True)
    for name, game, path in STRUCTURE_SOURCES:
        if args.maps and name not in args.maps:
            continue
        plot_map(name, game, path, out_dir)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
