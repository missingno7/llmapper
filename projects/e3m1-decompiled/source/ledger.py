"""Superseded: the ledger is a query over the fact store now.

`residue-ledger.json` used to be composed from per-layer evidence files. It is
now a QUERY RESULT over `projects/e3m1-decompiled/facts/`, where `claims`,
`candidate`, `selection`, `conflict` and `residue` are predicates like any
other (`RESEARCH-OVERLAPPING-LAYERS-2026-09-02.md` section 3).

This file stays as a signpost rather than being deleted, because a stale
second source of the same numbers is exactly the failure the fact store
exists to stop.

    PYTHONPATH=. python projects/e3m1-decompiled/source/build_facts.py   # store
    PYTHONPATH=. python projects/e3m1-decompiled/source/query.py         # numbers
"""

from __future__ import annotations

import sys


def main() -> int:
    print(__doc__.strip())
    print("\nRunning query.py for you.\n")
    import query

    return query.main()


if __name__ == "__main__":
    raise SystemExit(main())
