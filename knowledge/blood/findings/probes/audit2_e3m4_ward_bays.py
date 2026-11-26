"""List E3M4's four-walled axis-aligned sectors of 1,152 x 1,024 (the ward bays) and 384 x 1,024 (the dividers), with sprites per bay."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[4]))
import os
import sys
from collections import Counter

from bloodmap.corpus import corpus_map_path
from bloodmap.format import read_map
from bloodmap.model import record_fields

disk = read_map(corpus_map_path("E3M4"))
sprites = Counter(int(record_fields(s)["sector"]) for s in disk.sprites)


def box(index):
    f = record_fields(disk.sectors[index])
    start, count = int(f["wall_ptr"]), int(f["wall_count"])
    if count != 4:
        return None
    xs = [int(record_fields(disk.walls[w])["x"]) for w in range(start, start + count)]
    ys = [int(record_fields(disk.walls[w])["y"]) for w in range(start, start + count)]
    if len(set(xs)) != 2 or len(set(ys)) != 2:
        return None
    return tuple(sorted((max(xs) - min(xs), max(ys) - min(ys))))


sizes = {i: box(i) for i in range(len(disk.sectors))}
bays = [i for i, s in sizes.items() if s == (1024, 1152)]
dividers = [i for i, s in sizes.items() if s == (384, 1024)]
print("bays", len(bays), bays)
print("sprites per bay", sorted(Counter(sprites[i] for i in bays).items()))
print("dividers", len(dividers), dividers)
