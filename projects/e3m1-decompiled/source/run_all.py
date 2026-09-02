"""Build the fact store, query it, then rebuild every stage's review pack.

Three steps and the order matters. `build_facts.py` runs every reader and
stores what it emits; `query.py` answers every number from those files and
writes the panels the packs read; then each stage runs, so its pack shows the
fact panel of the WHOLE store rather than of its own layer. Running a stage
alone is still valid -- its pack is then one build behind.

    BLOODMAP_CORPUS=... BLOODMAP_ART=... PYTHONPATH=".;projects/e3m1-decompiled/source" \
        python projects/e3m1-decompiled/source/run_all.py
"""

from __future__ import annotations

import pathlib
import subprocess
import sys

HERE = pathlib.Path(__file__).resolve().parent
REPO = HERE.parent.parent.parent

STAGES = (
    "stage1_space_tree.py",
    "stage2_surfaces.py",
    "stage3_joins.py",
    "stage4_overlays.py",
    "stage6_edges.py",
    "stage7_plan.py",
    "stage5_mechanisms.py",
    "stage8_intent.py",
)


def run(name: str, quiet: bool = False) -> None:
    path = HERE / name
    if not path.exists():
        print(f"  (skipping {name}: not written yet)")
        return
    result = subprocess.run([sys.executable, str(path)], cwd=str(REPO),
                            capture_output=quiet, text=True)
    if result.returncode:
        if quiet:
            print(result.stdout or "", result.stderr or "")
        raise SystemExit(f"{name} failed")


def main() -> int:
    print("building the fact store")
    run("build_facts.py")
    print("querying it")
    run("query.py")
    print("rebuilding every stage's evidence and review pack")
    for stage in STAGES:
        run(stage)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
