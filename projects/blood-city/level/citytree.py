"""Stand anywhere in Gravesend's tree and look: the command line over `bloodmap.leveltree`.

    python projects/blood-city/level/citytree.py stats
    python projects/blood-city/level/citytree.py zoom theatre_row --depth 2 --cost
    python projects/blood-city/level/citytree.py find saloon

The tree kit itself (`nest`, `sub`, `plan`, `find`, `zoom`, `summary` ...) is the
library's; the level's modules reach it by this name.
"""

from __future__ import annotations

import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[3]))
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

from bloodmap.leveltree import *  # noqa: E402,F401,F403
from bloodmap.leveltree import _parent_world, _refuse_connect  # noqa: E402,F401


# ---------------------------------------------------------------------------
# the command line: stand anywhere in the city and look
# ---------------------------------------------------------------------------

def _program(with_costs=False):
    """The city, and -- if asked -- what each of its nodes costs.

    The cemetery gates are raw connections added after `build()` returns,
    so a program compiled without them has unpaired portals; measuring cost
    means compiling, so they go back in here.
    """
    import build_skeleton
    if not with_costs:
        return build_skeleton.build()[0], None
    # The FULL build, not just the tree: sprites are placed by the passes in
    # `main`, so a node measured from `program.compile()` alone reported 0p
    # on every node while the map carried hundreds -- and no venue could be
    # budgeted for the one of the three budgets that will bind first.
    build_skeleton.main()
    program, compiled = build_skeleton.LAST_BUILD
    return program, measure(compiled)


def main(argv=None) -> int:
    import argparse
    import json

    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("command",
                        choices=("stats", "tree", "zoom", "find", "at",
                                 "contains", "path", "summary"))
    parser.add_argument("argument", nargs="?", default="gravesend")
    parser.add_argument("--depth", type=int, default=1)
    parser.add_argument("--cost", action="store_true",
                        help="measure sectors, walls and sprites per node")
    args = parser.parse_args(argv)

    program, costs = _program(with_costs=args.cost)

    if args.command == "stats":
        print(json.dumps(stats(program), indent=1))
    elif args.command == "tree":
        print(program.tree())
    elif args.command == "zoom":
        print(zoom(one(program, args.argument), depth=args.depth, costs=costs))
    elif args.command == "summary":
        print(json.dumps(summary(one(program, args.argument), costs=costs),
                         indent=1, default=str))
    elif args.command == "find":
        for node in find(program, args.argument):
            print(node.path())
    elif args.command == "at":
        x, y = (int(v) for v in args.argument.split(","))
        for node in at(program, x, y):
            print(node.path())
    elif args.command == "contains":
        for room in contains(program, args.argument):
            print(room.path())
    elif args.command == "path":
        print("/".join(path_to(one(program, args.argument))))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
