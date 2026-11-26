"""Third audit share: type 456 and stone gargoyles with Teslas over every corpus map."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[4]))
import sys
from bloodmap.format import read_map
from bloodmap import corpus
from bloodmap.model import record_fields as F
names = [c.path for c in corpus.list_corpus_maps()]
z, g207, g209, gt207, gt209, n = [], [], [], [], [], 0
for path in names:
    name = str(path)
    try:
        m = read_map(path)
    except Exception as e:
        continue
    n += 1
    ts = [F(s)["type"] for s in m.sprites]
    for k, t in enumerate(ts):
        if t == 456: z.append((name, k))
    s = set(ts)
    if 207 in s: g207.append(name); gt207 += [name] if 45 in s else []
    if s & {207, 209}: g209.append(name); gt209 += [name] if 45 in s else []
print("maps read", n)
print("type 456:", z)
print("stone gargoyle 207:", len(g207), "with Tesla:", len(gt207))
print("207 or statue 209:", len(g209), "with Tesla:", len(gt209))
