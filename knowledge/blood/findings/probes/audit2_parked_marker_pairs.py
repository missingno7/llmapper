"""Count the vanilla tutorial movers whose marker pair stands at the poses or is parked elsewhere (bloodmap.motion.marker_convention), and the slides whose two markers differ in angle."""
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[4]))
from bloodmap.corpus import corpus_root
from bloodmap.format import read_map
from bloodmap.model import record_extra, record_fields
from bloodmap.motion import marker_convention

root = corpus_root() / "mechanism"          # the taught course: the folder and its Vanilla/ subfolder, not Modern/
paths = sorted(p for d in (root, root / "Vanilla") for p in d.iterdir() if p.suffix.lower() == ".map")
conv, by_type, turned = Counter(), Counter(), Counter()
for path in paths:
    disk = read_map(path)
    for i, sector in enumerate(disk.sectors):
        kind = record_fields(sector)["type"]
        try:
            value = marker_convention(disk, i)
        except Exception:
            value = "unreadable"
        if value is None:
            continue
        conv[value] += 1
        by_type[(kind, value)] += 1
        if kind in (614, 616):
            x = record_extra(sector)
            a, b = x.get("marker_0", -1), x.get("marker_1", -1)
            if 0 <= a < len(disk.sprites) and 0 <= b < len(disk.sprites):
                same = record_fields(disk.sprites[a])["angle"] == record_fields(disk.sprites[b])["angle"]
                turned["same angle" if same else "angles differ"] += 1
print(len(paths), "maps;", dict(conv), sorted(by_type.items()), dict(turned))
