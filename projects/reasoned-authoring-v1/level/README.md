# Working level sources

This directory contains current working candidates, not a frozen historical pilot.
In particular, live v5 is a later expanded monastery (133 sectors in its stored MAP),
whereas the historical v5 packet describes 38 sectors. v6/v7 are later work too.
Do not attach old reviews to these sources after recompilation.

The six original source/MAP pairs, evidence bindings and successful historical
rebuild check are in `../archive/architectural-v0-v5/`.
Current v5 and v7 failed compilation during the 2026-09-09 audit with nine sweep
findings concerning one type-617 mechanism. No repair is claimed here.

The loop that evaluated them (`bloodmap.authoring_loop`, `experiments/monastery_pilot.py`) was
retired on 2026-11-26. To re-evaluate a candidate, use a worktree of commit 7847923, the last
whose library has it; the sources and stored MAPs here are evidence and are not rebuilt.
