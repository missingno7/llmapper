"""The city as a tree you can stand anywhere in.

Gravesend's level program was 201 nodes at maximum depth **2**: the root,
38 assemblies, 162 rooms, and nothing below.  A district assembly held one
room called `streets`; the venues standing on that street were its
*siblings*, so "what is in Theatre Row" had no answer.  Inside a venue it
was flatter still -- `theatre_venues` was 42 sibling rooms in which three
separate venues were told apart by a name prefix, `saloon_main` against
`aldermack_dressing`.  That prefix is this project's own documented failure
mode in new clothes: an authored label standing in for structure.

`levelprog.Assembly.assembly()` has always supported nesting.  This module
is the wiring, plus the three things the library does not offer:

* **`nest`** -- reparent a node and keep it exactly where it is.  A frame
  is relative to the parent, so moving a node between parents moves the
  geometry unless the frame is rewritten.  Here it is rewritten, and the
  move is rejected if the world frame comes out different.
* **`summary`** -- an assembly introducing itself the way `Room.summary`
  does: what it is, what it contains by kind and count, how it connects,
  what style it inherits and from where, what it costs.
* **navigation** -- `find`, `at`, `contains`, `path_to`, `zoom`: look at
  any part of the city from any distance without loading all of it.

Two library limits are worked around here and filed as grammar requests
(#13, #14): `Assembly.add` is typed against assemblies, so a `Room` cannot
own one; and `all_connections` recurses only through `Assembly` children,
so a connection declared on an assembly nested under a room is dropped in
silence.  The rule this module follows -- and enforces, by removing the
method -- is therefore: **containment is the tree; a connection is
declared on the nearest assembly ancestor, which is the node that owns
both of its sides anyway.**
"""

from __future__ import annotations

import collections
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[3]))
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

from bloodmap.levelprog import Assembly, Frame, Room


class TreeError(ValueError):
    """A reorganisation that would move the city rather than describe it."""


# ---------------------------------------------------------------------------
# building the tree
# ---------------------------------------------------------------------------

def _parent_world(node) -> Frame:
    frame = Frame()
    for ancestor in node.ancestors():
        frame = frame.compose(ancestor.frame)
    return frame


def descendants(node) -> list:
    out = []
    for child in node.children:
        out.append(child)
        out.extend(descendants(child))
    return out


def nest(parent, node, *, keep_world: bool = True):
    """Move `node` under `parent`, leaving the compiled geometry alone.

    This is the safety property of the whole overhaul: restructuring is a
    representation change, so the map must not move.  A node's frame is
    stated in its parent's coordinates, so a node that changes parent has
    to change frame by exactly the difference, or every vertex under it
    slides by the new parent's offset.
    """
    if parent is node or parent in descendants(node):
        raise TreeError(f"{node.node_id} cannot be nested inside itself")
    before = node.world_frame() if keep_world else None
    if node.parent is not None:
        node.parent.children.remove(node)
    node.parent = parent
    parent.children.append(node)
    if before is None:
        return node
    outer = _parent_world(node)
    if (outer.turns - before.turns) % 4 and node.frame.turns == 0:
        raise TreeError(
            f"{node.node_id}: {parent.node_id} is turned relative to its old "
            "parent, and nest() rewrites translations only")
    node.frame = Frame(before.dx - outer.dx, before.dy - outer.dy,
                       before.dz - outer.dz, node.frame.turns)
    after = node.world_frame()
    if (after.dx, after.dy, after.dz, after.turns) != (
            before.dx, before.dy, before.dz, before.turns):
        raise TreeError(
            f"{node.node_id}: reparenting under {parent.node_id} moved it from "
            f"{before.to_dict()} to {after.to_dict()}")
    return node


def absolute(parent) -> Frame:
    """A frame that lets a child go on stating WORLD coordinates.

    Most of this city was written when every assembly hung off the root, so
    its rooms state absolute rects.  Nesting one of those under a parent
    that carries an offset would move it by that offset.  Giving the child
    the parent's inverse keeps the source honest -- the rects still mean
    what they say -- without rewriting every table into local coordinates.
    """
    world = parent.world_frame()
    if world.turns:
        raise TreeError(
            f"{parent.node_id} is turned; a child stating world coordinates "
            "under it would need its outline turned, not its frame")
    return Frame(-world.dx, -world.dy, -world.dz)


def sub(parent, node_id: str, **kwargs) -> Assembly:
    """A new assembly under any node -- including a `Room`.

    A room owning its own fixtures is the point of the overhaul, and
    `Assembly.add` will not do it, so this attaches directly.  Under a room
    the new assembly cannot declare connections (see the module note), so
    the method is replaced by one that says why.
    """
    child = Assembly(node_id, **kwargs)
    child.parent = parent
    parent.children.append(child)
    if isinstance(parent, Room) or getattr(parent, "_under_room", False):
        child._under_room = True
        child.connect = _refuse_connect(child)      # type: ignore[assignment]
    return child


def _refuse_connect(node):
    def refuse(*_args, **_kwargs):
        raise TreeError(
            f"{node.path()} sits under a room, and LevelProgram.all_connections "
            "recurses only through assemblies, so a connection declared here "
            "would be dropped in silence.  Declare it on the nearest assembly "
            "ancestor -- citytree.owner(node) -- which owns both sides anyway.")
    return refuse


def owner(node) -> Assembly:
    """The nearest ancestor that may legally declare a connection."""
    current = node
    while current is not None:
        if (isinstance(current, Assembly)
                and not getattr(current, "_under_room", False)):
            return current
        current = current.parent
    raise TreeError(f"{node.node_id} has no assembly ancestor")


def make_room(parent, node_id: str, outline, **kwargs) -> Room:
    """A room under any node -- an assembly, or another room.

    `Assembly.room` is the same thing with an assembly-only parent check.
    A fixture belongs to the room it furnishes, so that check has to go.
    """
    room = Room(node_id, outline, **kwargs)
    room.parent = parent
    parent.children.append(room)
    return room


def common(a, b) -> Assembly:
    """The nearest assembly that owns both of these, and may join them.

    Which node declares a connection is not a style question: a connection
    stated below the fork is invisible to the side it did not come from,
    and one stated at the root tells a reader nothing about what it joins.
    The lowest common ancestor is the honest answer, and computing it means
    no call site has to know how deep the two ends happen to sit.
    """
    left = [node for node in (*a.ancestors(), a)]
    right = {id(node) for node in (*b.ancestors(), b)}
    for node in reversed(left):
        if not isinstance(node, Assembly) or getattr(node, "_under_room", False):
            continue
        if id(node) in right:
            return node
    return owner(a)


def join(a, b, *, connection_id: str, at_a=None, at_b=None, **options):
    """Join two rooms' faces, declared on the node that owns both.

    `at_a`/`at_b` are (face, kwargs) pairs; passing plain face names is the
    common case.
    """
    face_a = a.face(at_a) if isinstance(at_a, str) else at_a
    face_b = b.face(at_b) if isinstance(at_b, str) else at_b
    return common(a, b).connect(face_a, face_b,
                                connection_id=connection_id, **options)


# ---------------------------------------------------------------------------
# reading the tree
# ---------------------------------------------------------------------------

def walk(node, depth: int = 0):
    yield node, depth
    for child in node.children:
        yield from walk(child, depth + 1)


def stats(root) -> dict:
    nodes = list(walk(root))
    hist = collections.Counter(depth for _n, depth in nodes)
    return {
        "nodes": len(nodes),
        "max_depth": max(hist),
        "depth_histogram": dict(sorted(hist.items())),
        "assemblies": sum(1 for n, _d in nodes if isinstance(n, Assembly)),
        "rooms": sum(1 for n, _d in nodes if isinstance(n, Room)),
        "singleton_assemblies": sum(
            1 for n, _d in nodes
            if isinstance(n, Assembly) and len(n.children) == 1),
        "top_level": len(root.children),
    }


def bounds(node):
    """The world bounding box of every room at or under this node."""
    xs: list[int] = []
    ys: list[int] = []
    rooms = ([node] if isinstance(node, Room) else []) + node.rooms()
    for room in rooms:
        for x, y in room.world_outline():
            xs.append(int(x))
            ys.append(int(y))
    if not xs:
        return None
    return (min(xs), min(ys), max(xs), max(ys))


def rooms_under(node) -> list:
    return ([node] if isinstance(node, Room) else []) + node.rooms()


def summary(node, *, costs: dict | None = None) -> dict:
    """What I am, what I contain, how I connect, what I inherit, what I cost.

    Readable without reading the children: contents are counted by kind and
    named one level down, never dumped.
    """
    kinds = collections.Counter(
        child.__class__.__name__.lower() for child in node.children)
    roles = collections.Counter(room.role for room in rooms_under(node))
    style = node.style_provenance()
    own = {name: spec["value"] for name, spec in style.items()
           if spec["from"] == node.path()}
    inherited = {name: f'{spec["value"]} <- {spec["from"]}'
                 for name, spec in style.items() if spec["from"] != node.path()}
    inside = {room.path() for room in rooms_under(node)}
    outward = [item.connection_id
               for item in getattr(node, "connections", [])
               if not {item.left.room.path(), item.right.room.path()} <= inside]
    out = {
        "path": node.path(),
        "kind": node.__class__.__name__.lower(),
        "note": node.note,
        "frame": node.frame.to_dict(),
        "contains": dict(kinds),
        "rooms_total": len(rooms_under(node)),
        "roles": dict(roles),
        "children": [
            {"id": child.node_id, "kind": child.__class__.__name__.lower(),
             "rooms": len(rooms_under(child)), "note": child.note}
            for child in node.children
        ],
        "connections_internal": len(getattr(node, "connections", [])) - len(outward),
        "connections_outward": outward,
        "style_own": own,
        "style_inherited": inherited,
        "world_bounds": bounds(node),
    }
    if isinstance(node, Room):
        out["room"] = node.summary()
    if costs is not None:
        out["cost"] = cost_of(node, costs)
    return out


# ---------------------------------------------------------------------------
# cost
# ---------------------------------------------------------------------------

def measure(compiled) -> dict:
    """Per-region sector/wall/sprite counts, from the compiled artifact.

    Cost is a property of what was built, not of what was declared, so it
    is measured once against the compiled level and attributed back up.

    **This is the cost of the tree's own geometry.**  Sprites and the door
    reveal frames are added by later passes in `build_skeleton.main`, so a
    node measured straight from `program.compile()` reports zero sprites
    and a wall count below the finished map's.  Pass a layout that has been
    through those passes to get the full figure.
    """
    allocations = getattr(compiled, "allocations", None)
    if allocations is None:
        raise TreeError("measure() takes the object returned by layout.compile()")
    level = compiled.level
    by_sector: dict[int, str] = {}
    out: dict[str, dict] = {}
    for region_id, allocation in allocations.items():
        sector_id = int(allocation.sector_id)
        by_sector[sector_id] = region_id
        # A compiled level holds raw Build records as dicts keyed `fields`,
        # not as attributes; reading them with getattr returns the default
        # and every node reports zero walls, which is worse than an error.
        fields = level.sectors[sector_id]["fields"]
        out[region_id] = {"sectors": 1, "walls": int(fields["wall_count"]),
                          "sprites": 0}
    for sprite in level.sprites:
        region_id = by_sector.get(int(sprite["fields"]["sector"]))
        if region_id in out:
            out[region_id]["sprites"] += 1
    return out


def cost_of(node, costs: dict) -> dict:
    total = {"sectors": 0, "walls": 0, "sprites": 0}
    for room in rooms_under(node):
        row = costs.get(room.region_id)
        if row is None:
            continue
        for key in total:
            total[key] += row[key]
    return total


# ---------------------------------------------------------------------------
# navigation
# ---------------------------------------------------------------------------

def find(root, name: str) -> list:
    """Every node whose id or path mentions `name`, nearest the root first."""
    hits = [(depth, node) for node, depth in walk(root)
            if name == node.node_id or name in node.path()]
    hits.sort(key=lambda row: (row[0], row[1].path()))
    return [node for _depth, node in hits]


def one(root, name: str):
    """The single node called `name`, or an error naming the alternatives."""
    hits = [node for node, _d in walk(root) if node.node_id == name]
    if len(hits) == 1:
        return hits[0]
    if not hits:
        near = [node.path() for node in find(root, name)][:6]
        raise TreeError(f"no node called {name!r}"
                        + (f"; nearest: {near}" if near else ""))
    raise TreeError(f"{len(hits)} nodes called {name!r}: "
                    f"{[node.path() for node in hits]}")


def at(root, x: int, y: int) -> list:
    """Every node whose contents cover this point, deepest first."""
    hits = []
    for node, depth in walk(root):
        box = bounds(node)
        if box and box[0] <= x <= box[2] and box[1] <= y <= box[3]:
            hits.append((depth, node))
    hits.sort(key=lambda row: -row[0])
    return [node for _depth, node in hits]


def contains(node, role: str) -> list:
    """Every room under this node in the given role."""
    return [room for room in rooms_under(node) if room.role == role]


def path_to(node) -> list[str]:
    return [ancestor.node_id for ancestor in node.ancestors()] + [node.node_id]


def zoom(node, *, depth: int = 1, costs: dict | None = None) -> str:
    """This node's summary with its children `depth` levels down.

    The point of the whole tree: read a district without reading a venue,
    read a venue without reading a fixture.
    """
    head = summary(node, costs=costs)
    lines = [f"{head['path']}  [{head['kind']}]"]
    if head["note"]:
        lines.append(f"    {head['note']}")
    lines.append(f"    contains {head['contains']} | rooms {head['rooms_total']} "
                 f"| roles {head['roles']}")
    if head["style_own"]:
        lines.append(f"    states {head['style_own']}")
    if head["style_inherited"]:
        lines.append(f"    inherits {len(head['style_inherited'])} values, e.g. "
                     + next(iter(head["style_inherited"].items()))[1])
    if head["connections_outward"]:
        lines.append(f"    joins outward: {len(head['connections_outward'])}")
    if costs is not None:
        spend = head["cost"]
        lines.append(f"    cost {spend['sectors']} sectors "
                     f"{spend['walls']} walls {spend['sprites']} sprites")

    def render(current, level, prefix):
        for child in current.children:
            mark = "+" if isinstance(child, Assembly) else "-"
            row = f"{prefix}{mark} {child.node_id}"
            if costs is not None:
                spend = cost_of(child, costs)
                row += (f"  [{len(rooms_under(child))}r {spend['sectors']}s "
                        f"{spend['walls']}w {spend['sprites']}p]")
            else:
                row += f"  [{len(rooms_under(child))}r]"
            if child.note:
                row += f"  {child.note[:52]}"
            lines.append(row)
            if level < depth:
                render(child, level + 1, prefix + "    ")

    render(node, 1, "    ")
    return "\n".join(lines)


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
    program, _stacks, gates, *_rest = build_skeleton.build()
    if not with_costs:
        return program, None
    layout = program.compile()
    for gate_id, region_a, region_b, a1, a2 in gates:
        layout.add_connection(gate_id, region_a, region_b, a1=a1, a2=a2,
                              min_width=1024)
    return program, measure(layout.compile())


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
