"""Superseded: the ledger is a query over the fact store now.

`residue-ledger.json` used to be composed from per-layer evidence files. It is
now a QUERY RESULT over the project's `facts/`, where `claims`,
`candidate`, `selection`, `conflict` and `residue` are predicates like any
other (`RESEARCH-OVERLAPPING-LAYERS-2026-09-02.md` section 3).

This file stays as a signpost rather than being deleted, because a stale
second source of the same numbers is exactly the failure the fact store
exists to stop.

    python -m tools.decompile_stages.build_facts projects/<map>-decompiled   # store
    python -m tools.decompile_stages.query projects/<map>-decompiled         # numbers
"""

from __future__ import annotations


def main() -> int:
    print(__doc__.strip())
    print("\nRunning query for you.\n")
    from . import query

    return query.main()


if __name__ == "__main__":
    raise SystemExit(main())
