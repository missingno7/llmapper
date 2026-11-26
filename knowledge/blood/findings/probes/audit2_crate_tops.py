"""Recount the campaign's raised crate tops (texture_frame.raised_solids on CRATE_FLOOR_TILES) and how many land the tile grid on their own corner."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[4]))
from bloodmap.corpus import campaign_maps  # noqa: E402
from bloodmap.format import read_map  # noqa: E402
from bloodmap import texture_frame as T  # noqa: E402
from bloodmap.texture_align import wall_art_sizes  # noqa: E402

sizes = wall_art_sizes()
total = whole = expanded = panned = relative = 0
for path in campaign_maps():
    level = read_map(path)
    for s in T.raised_solids(level):
        f = T._fields(level.sectors[s])
        size = sizes.get(int(f["floor_picnum"]))
        if not size or not size[0]:
            continue
        total += 1
        exp = bool(int(f["floor_stat"]) & T.FLOOR_EXPANDED)
        expanded += exp
        relative += bool(int(f["floor_stat"]) & 64)
        pan = (int(f["floor_x_panning"]), int(f["floor_y_panning"]))
        panned += any(pan)
        whole += T.surface_is_whole(T.sector_corner(level, s), size, expanded=exp, panning=pan)
print(f"raised crate tops {total}: corner-whole {whole} ({100 * whole / total:.0f}%), expanded {expanded} ({100 * expanded / total:.0f}%), "
      f"panned {panned} ({100 * panned / total:.0f}%), first-wall relative {relative} ({100 * relative / total:.0f}%)")
