# Probes

The small scripts that counted what a finding says, kept so that the count can be made again.
Each was written for one question on the day its finding was filed or audited, and opens with a
one-sentence docstring saying what it counts.

Run one as it stands, from the repository's root:

```bash
python knowledge/blood/findings/probes/<name>.py [arguments]
```

Each puts the repository root on `sys.path` itself (from its own location), so no `PYTHONPATH`
is needed. They read the local corpus through `bloodmap.corpus`, print what they count, and
write nothing; none depends on scratch under `work/`. A few take arguments:
`consolidation_probe_tile.py <tile>`, `consolidation_probe_shade.py <MAP>...`,
`consolidation_probe_raised.py [<MAP>...] [--island]` and
`lightstage_budget.py <MAP or path>...`; `audit2_diagonal_walls.py`, `audit2_facade_phase.py`,
`audit2_through_windows.py` and `consolidation_audit_mid_facade_phase.py` take optional map
names. `sewer-study_breach_shapes.json` is data, not a probe: the blast-hole pieces that
`audit2_blast_holes.py` reads.

They are evidence, not tools: when a count is wanted often, it belongs in a miner under `tools/`.
