"""Build the fact store, query it, then rebuild every stage's review pack.

Three steps and the order matters. `build_facts` runs every reader and
stores what it emits; `query` answers every number from those files and
writes the panels the packs read; then each stage runs, so its pack shows the
fact panel of the WHOLE store rather than of its own layer. Running a stage
alone is still valid -- its pack is then one build behind.

    BLOODMAP_CORPUS=... BLOODMAP_ART=... \
        python -m tools.decompile_stages.run_all projects/e3m1-decompiled
"""

from __future__ import annotations

import pathlib
import subprocess
import sys

from ._common import project

HERE = pathlib.Path(__file__).resolve().parent
REPO = HERE.parent.parent
PACKAGE = "tools.decompile_stages"

STAGES = (
    "stage1_space_tree",
    "stage2_surfaces",
    "stage3_joins",
    "stage4_overlays",
    "stage6_edges",
    "stage7_plan",
    "stage5_mechanisms",
    "stage8_intent",
)


def run(name: str, quiet: bool = False) -> None:
    if not (HERE / f"{name}.py").exists():
        print(f"  (skipping {name}: not written yet)")
        return
    result = subprocess.run([sys.executable, "-m", f"{PACKAGE}.{name}",
                             str(project())], cwd=str(REPO),
                            capture_output=quiet, text=True)
    if result.returncode:
        if quiet:
            print(result.stdout or "", result.stderr or "")
        raise SystemExit(f"{name} failed")


def main() -> int:
    project()
    print("building the fact store")
    run("build_facts")
    print("querying it")
    run("query")
    print("rebuilding every stage's evidence and review pack")
    for stage in STAGES:
        run(stage)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
