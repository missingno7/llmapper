"""The decompile stage program: one copy for every `projects/<map>-decompiled`.

Each module is runnable with the project as its argument:

    python -m tools.decompile_stages.run_all projects/e3m1-decompiled
    python -m tools.decompile_stages.query projects/e3m1-decompiled
    python -m tools.decompile_stages.stage3_joins projects/e3m1-decompiled

The map is the project's directory name (checked against its
`provenance.json`); nothing else differs between two maps.
"""
