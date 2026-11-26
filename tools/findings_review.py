"""The findings a level leans on, gathered for its owner to mark, with a frame of the Blood map spot each cites.

.. code-block:: bash

    python -m tools.findings_review blood-city -o work/review/site     # findings.json and frames/ for the review page

A finding is leaned on when the level's code uses what it names (`tools.library_usage`). Three kinds are put to the
owner: rulings ("is this what you said?"), what Blood does (precedents, tendencies and what we found false) and our own
habits. Engine facts read in the source are not: the owner cannot see them by playing. The owner's answers come back
through the page's store and are folded into the shelf by an agent (`tools.findings amend`).
"""
import collections
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(".").resolve()
sys.path.insert(0, str(ROOT))

from bloodmap import findings as F  # noqa: E402
from bloodmap.corpus import corpus_map_path  # noqa: E402

import argparse  # noqa: E402

from tools.library_usage import project_usage  # noqa: E402

_args = argparse.ArgumentParser(description=__doc__.split(chr(10))[0])
_args.add_argument("project")
_args.add_argument("-o", "--out", required=True, help="the review page's folder: findings.json and frames/ go here")
ARGS = _args.parse_args()
SITE = Path(ARGS.out).resolve()
FRAMES = SITE.parent / (SITE.name + "-frames")
usage = project_usage(ARGS.project)
rows = {r["id"]: r for r in F.read()}
used_names = {f"{m}.{n}" for m, names in usage["modules"].items() for n in names if n != "*"} | set(usage["modules"])

BATCH = {"ruling": "words", "precedent": "blood", "tendency": "blood", "refuted": "blood", "practice": "ours"}
SPOT = re.compile(r"\b([A-Z][A-Z0-9_]{2,11})\b[\s:,(]*(?:s|sector|sectors)\s*#?(\d+)")


def spots(row):
    out = []
    for text in [row["claim"], *row.get("evidence", [])]:
        for name, sector in SPOT.findall(text):
            try:
                path = corpus_map_path(name)
            except Exception:
                continue
            if path.exists() and (name, int(sector)) not in out:
                out.append((name, int(sector)))
    return out[:2]


cards = []
wanted = collections.defaultdict(set)
for ident in usage["findings"]:
    row = rows[ident]
    batch = BATCH.get(row["standing"])
    if batch is None:
        continue
    where = spots(row)
    for name, sector in where:
        wanted[name].add(sector)
    cards.append({
        "id": ident, "batch": batch, "standing": row["standing"], "topic": row["topic"], "scope": row["scope"],
        "claim": row["claim"], "instead": row.get("instead", ""), "use": row.get("use", ""),
        "evidence": row.get("evidence", []), "checked": (row.get("checked") or {}).get("how", ""),
        "learned": row["learned"], "gravesend": [c for c in row.get("code", []) if c in used_names
                                                 or c.startswith(f"projects/{usage['project']}/")],
        "spots": [{"map": m, "sector": s, "image": f"frames/{m}_s{s}.jpg"} for m, s in where],
    })

# draw each map's spots in one observer run
FRAMES.mkdir(parents=True, exist_ok=True)
(SITE / "frames").mkdir(parents=True, exist_ok=True)
from PIL import Image  # noqa: E402

PEOPLE = re.compile(r"(key|keys|pickup|pickups|item|items|foe|foes|enemy|enemies|dude|cultist|ammo|weapon)", re.I)
keep_people = {spot["map"] for card in cards for spot in card["spots"] if PEOPLE.search(card["claim"])}
for name, sectors in sorted(wanted.items()):
    out = FRAMES / name
    if not all((out / "frames" / f"sector_{s}.png").exists() for s in sectors):
        subprocess.run([sys.executable, "-m", "tools.look", "--ref", name, "--sectors",
                        ",".join(str(s) for s in sorted(sectors)), "-o", str(out)]
                       + ([] if name in keep_people else ["--empty"]),
                       check=False, capture_output=True, text=True)
    for s in sectors:
        png = out / "frames" / f"sector_{s}.png"
        if png.exists():
            Image.open(png).convert("RGB").save(SITE / "frames" / f"{name}_s{s}.jpg", quality=82)
for card in cards:
    card["spots"] = [spot for spot in card["spots"] if (SITE / spot["image"]).exists()]

order = {"words": 0, "blood": 1, "ours": 2}
cards.sort(key=lambda c: (order[c["batch"]], c["topic"], c["id"]))
(SITE / "findings.json").write_text(json.dumps(cards, ensure_ascii=False, indent=0), encoding="utf-8")
print(len(cards), collections.Counter(c["batch"] for c in cards),
      "with a frame:", sum(1 for c in cards if c["spots"]), "frames:", len(list((SITE / "frames").glob("*.jpg"))))
