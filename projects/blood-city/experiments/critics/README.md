# Experiments on the critics

Two instruments that asked how far a blind reader can be trusted, run on
Gravesend's station in 2026-11: `critic_bench.py` (which model names a thing
rightly, against Blood's own things as controls, and which notices a planted
fault) and `critic_lab.py` (what the best view and prompt for a reader is).
Their answers are on the findings shelf (`python -m tools.findings find reader`)
and in `knowledge/blood/critic-bench/`. They are kept as they were run: both
name this level's poses and coordinates, which is why they are here and not in
`tools/`. The process they informed is `tools/critique.py`.
