"""Every stage, then the shared ledger, then every stage again.

Twice on purpose. A stage's review pack shows the fact panel of the SHARED
ledger, and the shared ledger is only complete once every stage has written
its claims -- so the first pass produces the claims, `ledger.py` merges them,
and the second pass rebuilds the packs against the merged result. Running a
stage alone is still valid; its pack is then one merge behind and says so.

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
    print("pass 1: every stage writes its claims")
    for stage in STAGES:
        run(stage, quiet=True)
    print("merging the shared ledger")
    run("ledger.py")
    print("pass 2: every stage rebuilds its pack against the merged ledger")
    for stage in STAGES:
        run(stage)
    print("merging the shared ledger again")
    run("ledger.py")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
