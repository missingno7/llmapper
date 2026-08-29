"""Hierarchical level programs: a level as source code, not a sector graph.

``PlanarLayout`` is already a real compiler -- editing its Python changes the
geometry -- but it is *flat*.  Every region is a top-level entry in one
dictionary, every point is an absolute Build coordinate, every connection
restates two absolute endpoints, and every sprite lives in one global list.  To
change one room you read the whole file, and to move one room you edit every
number in it.

This module adds the layer above it: a tree of named parts, each holding its own
geometry, surfaces, structures, details and connections, in *its own*
coordinates.

    level
      -> assemblies / areas
        -> rooms / spaces
          -> structures
            -> details

Three properties are the point of the whole thing.

**Locality.**  ``build_lobby()`` contains the lobby: its outline, its materials,
its alcoves, its lamps, and the faces it offers to its neighbours.  Reading it
does not require reading the level.

**Local coordinates.**  A room's outline is written around its own origin, so a
room is the same source wherever it sits.  Frames compose down the tree and the
compiler resolves them once; the absolute Build coordinates every layer below
still needs are output, never input.

**Inspectable inheritance.**  A parent supplies a :class:`Style` -- surfaces,
shading, ceiling height -- and a child overrides only what differs.  Every
resolved value carries the node that set it, so ``room.style_provenance()``
answers "why is this wall this tile" without reading any ancestor.

What this module is *not*: it is not a new IR.  It compiles to ``PlanarLayout``
and stops.  Native sector, wall and sprite ids stay exactly where they were, as
compiler output and provenance, and :meth:`Room.raw` is the documented escape
hatch for the structure the model cannot express.
"""

from __future__ import annotations

from dataclasses import dataclass, field, replace
from typing import Any, Callable, Iterable, Sequence

from .planar_geom import Point, area2
from .planar_layout import PlanarLayout, PlanarLayoutError
from .vocabulary import Anchor, Decoration, Structure, recess, sprite_repeats, staircase

SCHEMA = "llmapper.level-program"
SCHEMA_VERSION = 1

PLAYER_WIDTH = 384

from .player_space import PLAYER_PROFILES

#: One standing human, from the player profile. Never hardcode this: it was
#: 0x1600 in a dozen modules, which is `POSTURE.eyeAboveZ` -- an offset from
#: the sprite's centre, not a body -- and every height in the project was
#: denominated in a unit 3x too small.
PLAYER_HEIGHT = PLAYER_PROFILES["blood"].standing_height

#: Screen-space compass for a rectangular room.  Build's y grows downward, so
#: the minimum-y edge is north, and a clockwise outer loop runs north, east,
#: south, west with the interior always on the left.
RECT_FACES = ("north", "east", "south", "west")


class LevelProgramError(PlanarLayoutError):
    """A level program cannot be expressed as valid planar source."""


# ---------------------------------------------------------------------------
# Frames: a node's coordinates inside its parent
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class Frame:
    """Where a node's local coordinates sit in its parent's.

    Translation and quarter-turns, and nothing else.

    The original rule here was translation only, on the grounds that rotation
    buys expressiveness at the cost of a rounding residual on every vertex. That
    reasoning is right, and it is right only about *arbitrary* angles. A
    quarter-turn is ``(x, y) -> (-y, x)``: integer in, integer out, no sine
    table, no residual, and exact under composition because the four turns form
    a group. So the sharpened rule is:

    * **k x 90 degrees belongs in the frame.** It is exact, it composes, and it
      lets an assembly be stamped in any cardinal orientation with "this room is
      the same source wherever it sits" still literally true.
    * **Any other angle does not.** Nesting non-cardinal rotations is where
      residual accumulates, one half-unit per vertex per level of nesting. Those
      are a one-time *outline stamp* instead -- see `vocabulary.stamp`, which
      composes in floating point and rounds once, before the planar overlay, so
      both sides of a shared edge come from the same integer points.

    `turns` counts anticlockwise quarter-turns in Build's coordinate space and
    is applied *before* the translation, so a frame reads as "turn this, then
    put it there".

    Rotation is not only geometry. A sector's slope direction and any
    first-wall-relative texture alignment reference the sector's first wall, so
    they follow an outline that is rotated as a whole with its winding intact.
    Sprite angles do not follow -- they are absolute -- so anything applying a
    frame to a sprite must also call `apply_angle`.
    """

    dx: int = 0
    dy: int = 0
    dz: int = 0
    #: Anticlockwise quarter-turns, taken modulo 4.
    turns: int = 0

    def __post_init__(self) -> None:
        object.__setattr__(self, "turns", int(self.turns) % 4)

    def turn(self, point: Sequence[float]) -> Point:
        """The quarter-turn alone, about the local origin. Exact."""
        x, y = int(point[0]), int(point[1])
        for _ in range(self.turns):
            x, y = -y, x
        return (x, y)

    def unturn(self, point: Sequence[float]) -> Point:
        """The inverse quarter-turn. Exact, and exactly undoes `turn`."""
        x, y = int(point[0]), int(point[1])
        for _ in range((4 - self.turns) % 4):
            x, y = -y, x
        return (x, y)

    def apply(self, point: Sequence[float]) -> Point:
        x, y = self.turn(point)
        return (x + self.dx, y + self.dy)

    def apply_z(self, z: int) -> int:
        return int(z) + self.dz

    def apply_angle(self, angle: int) -> int:
        """Rotate a Build angle by this frame's turns.

        2048 is a full turn, so a quarter is 512. Sprites carry absolute angles
        and are the one thing a rotated outline does not bring with it.
        """
        return (int(angle) + 512 * self.turns) % 2048

    def compose(self, child: "Frame") -> "Frame":
        """This frame applied to a child's.

        The child's translation happens in the child's own turned space, so it
        has to be turned by *this* frame before being added. Turns simply add:
        that is what makes the composition exact.
        """
        cdx, cdy = self.turn((child.dx, child.dy))
        return Frame(self.dx + cdx, self.dy + cdy,
                     self.dz + child.dz, self.turns + child.turns)

    def to_dict(self) -> dict[str, int]:
        return {"dx": self.dx, "dy": self.dy, "dz": self.dz, "turns": self.turns}


# ---------------------------------------------------------------------------
# Style: inheritable, inspectable surface vocabulary
# ---------------------------------------------------------------------------

STYLE_FIELDS = (
    "wall_picnum", "floor_picnum", "ceiling_picnum",
    "wall_shade", "floor_shade", "ceiling_shade",
    "parallax_ceiling", "clear_height", "floor_z", "layer",
)


@dataclass(frozen=True)
class Style:
    """Surface and lighting vocabulary that flows down the tree.

    Only the fields a node actually states are stored; everything else stays
    ``None`` and is answered by an ancestor.  :meth:`resolve` returns the value
    *and the node that supplied it*, so inheritance never becomes the kind of
    hidden default that makes source unreadable.
    """

    wall_picnum: int | None = None
    floor_picnum: int | None = None
    ceiling_picnum: int | None = None
    wall_shade: int | None = None
    floor_shade: int | None = None
    ceiling_shade: int | None = None
    parallax_ceiling: bool | None = None
    clear_height: int | None = None
    floor_z: int | None = None
    #: Which planar arrangement this part belongs to. Inherited like everything
    #: else here, because a layer is a property of a *place* -- the whole first
    #: floor of a building is on the upper layer -- and stating it once on the
    #: assembly is the only way that stays true as rooms are added. See
    #: `bloodmap.layers`.
    layer: str | None = None

    def override(self, **values: Any) -> "Style":
        unknown = set(values) - set(STYLE_FIELDS)
        if unknown:
            raise LevelProgramError(f"unknown style fields: {sorted(unknown)}")
        return replace(self, **values)

    def stated(self) -> dict[str, Any]:
        return {
            name: getattr(self, name)
            for name in STYLE_FIELDS if getattr(self, name) is not None
        }


def resolve_style(chain: Sequence[tuple[str, Style]]) -> dict[str, tuple[Any, str]]:
    """Flatten a root-to-node style chain into value-and-origin pairs."""
    result: dict[str, tuple[Any, str]] = {}
    for node_id, style in chain:
        for name, value in style.stated().items():
            result[name] = (value, node_id)
    return result


# ---------------------------------------------------------------------------
# Faces: how one part offers itself to another
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class FaceRef:
    """A named stretch of one room's boundary, in that room's own terms.

    ``at`` is a fraction along the face and ``width`` a length in world units;
    together they name a sub-segment without the author computing either
    endpoint.  Resolution to absolute coordinates happens once, at compile time.
    """

    room: "Room"
    name: str
    at: float = 0.5
    width: float | None = None

    def anchor(self) -> Anchor:
        return self.room.face_anchor(self.name, at=self.at, width=self.width)

    def describe(self) -> str:
        return f"{self.room.path()}.{self.name}@{self.at}"


# ---------------------------------------------------------------------------
# Declarations: what a node owns, resolved at compile time
# ---------------------------------------------------------------------------

@dataclass
class DetailDecl:
    """One decoration, owned by the part it decorates rather than by the level."""

    detail_id: str
    picnum: int
    player_heights: float
    where: str = "wall"
    face: str | None = None
    at: float = 0.5
    height_player_heights: float = 0.65
    local: tuple[float, float] = (0.5, 0.5)
    cstat: int = 16
    shade: int = -8
    aspect: float = 1.0
    offset_player_widths: float = 0.10
    fields: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class LightSourceDecl:
    """An authored light source at a room-relative point.

    The declaration is deliberately independent of sprite appearance: a flame
    may have a visual detail, while a window or furnace opening can emit light
    without one.  In both cases the source is explicit in the level program.
    """

    light_id: str
    local: tuple[float, float] = (0.5, 0.5)
    height_player_heights: float = 0.65


@dataclass
class StructureDecl:
    """A staircase or recess declared against one of the owning room's faces."""

    structure_id: str
    kind: str
    face: str
    at: float
    width: float | None
    options: dict[str, Any]
    details: list[DetailDecl] = field(default_factory=list)
    arrive_at: str | None = None
    connection: dict[str, Any] = field(default_factory=dict)

    def decorate(self, *details: DetailDecl) -> "StructureDecl":
        """Details attach to the structure, not to a global sprite list."""
        self.details.extend(details)
        return self


@dataclass
class ConnectionDecl:
    connection_id: str
    left: FaceRef
    right: FaceRef
    options: dict[str, Any] = field(default_factory=dict)


@dataclass
class RawDecl:
    """The escape hatch: arbitrary work against the compiled PlanarLayout."""

    note: str
    apply: Callable[[PlanarLayout, "Room"], None]


# ---------------------------------------------------------------------------
# Nodes
# ---------------------------------------------------------------------------

class Node:
    """Common tree behaviour: identity, frames, style chain, navigation."""

    def __init__(self, node_id: str, *, frame: Frame | None = None,
                 style: Style | None = None, note: str = "") -> None:
        self.node_id = str(node_id)
        self.frame = frame or Frame()
        self.style = style or Style()
        self.note = note
        self.parent: "Assembly | None" = None
        self.children: list["Node"] = []

    # -- tree -------------------------------------------------------------
    def path(self) -> str:
        parts = [self.node_id]
        current = self.parent
        while current is not None:
            parts.append(current.node_id)
            current = current.parent
        return "/".join(reversed(parts))

    def ancestors(self) -> list["Node"]:
        result: list[Node] = []
        current = self.parent
        while current is not None:
            result.append(current)
            current = current.parent
        return list(reversed(result))

    def world_frame(self) -> Frame:
        frame = Frame()
        for node in [*self.ancestors(), self]:
            frame = frame.compose(node.frame)
        return frame

    def style_chain(self) -> list[tuple[str, Style]]:
        return [(node.path(), node.style) for node in [*self.ancestors(), self]]

    def style_provenance(self) -> dict[str, dict[str, Any]]:
        """Every resolved style value and the node that stated it."""
        return {
            name: {"value": value, "from": origin}
            for name, (value, origin) in sorted(resolve_style(self.style_chain()).items())
        }

    def effective_style(self) -> dict[str, Any]:
        return {name: value for name, (value, _origin) in resolve_style(self.style_chain()).items()}

    def rooms(self) -> list["Room"]:
        result: list[Room] = []
        for child in self.children:
            if isinstance(child, Room):
                result.append(child)
            result.extend(child.rooms())
        return result

    def tree(self, indent: int = 0) -> str:
        """A navigable outline of this subtree, for orienting before editing."""
        head = f"{'  ' * indent}{self.node_id} ({self.__class__.__name__.lower()})"
        if self.note:
            head += f" -- {self.note}"
        lines = [head]
        for child in self.children:
            lines.append(child.tree(indent + 1))
        return "\n".join(lines)


class Assembly(Node):
    """A named group: an area, a building, a floor.

    An assembly owns no geometry of its own.  What it owns is a frame its
    children sit in, a style they inherit, and the connections between them.
    """

    def __init__(self, node_id: str, *, frame: Frame | None = None,
                 style: Style | None = None, note: str = "") -> None:
        super().__init__(node_id, frame=frame, style=style, note=note)
        self.connections: list[ConnectionDecl] = []

    def add(self, *nodes: Node) -> "Assembly":
        for node in nodes:
            if node.parent is not None:
                raise LevelProgramError(f"{node.node_id} already belongs to {node.parent.node_id}")
            node.parent = self
            self.children.append(node)
        return self

    def room(self, node_id: str, outline: Iterable[Sequence[float]], **kwargs: Any) -> "Room":
        """Create a child room that inherits this assembly's frame and style."""
        room = Room(node_id, outline, **kwargs)
        self.add(room)
        return room

    def rect_room(self, node_id: str, *, origin: Sequence[float] = (0, 0),
                  size: Sequence[float], **kwargs: Any) -> "Room":
        """A rectangular room named by its origin and size rather than four corners."""
        width, depth = int(size[0]), int(size[1])
        if width <= 0 or depth <= 0:
            raise LevelProgramError(f"{node_id}: room size must be positive")
        outline = [(0, 0), (width, 0), (width, depth), (0, depth)]
        kwargs.setdefault("faces", dict(zip(RECT_FACES, range(4))))
        kwargs["frame"] = Frame(int(origin[0]), int(origin[1]),
                                int(kwargs.pop("elevation", 0)))
        return self.room(node_id, outline, **kwargs)

    def assembly(self, node_id: str, **kwargs: Any) -> "Assembly":
        child = Assembly(node_id, **kwargs)
        self.add(child)
        return child

    def connect(self, left: FaceRef, right: FaceRef, *, connection_id: str | None = None,
                **options: Any) -> ConnectionDecl:
        """Join two named faces.  Neither side states a coordinate."""
        identifier = connection_id or f"connection:{left.describe()}->{right.describe()}"
        declaration = ConnectionDecl(identifier, left, right, options)
        self.connections.append(declaration)
        return declaration

    def all_connections(self) -> list[ConnectionDecl]:
        result = list(self.connections)
        for child in self.children:
            if isinstance(child, Assembly):
                result.extend(child.all_connections())
        return result


class Room(Node):
    """One space: its outline, its surfaces, its structures, its details.

    Everything about the room is reachable from the room.  That is the whole
    design goal -- an agent asked to change the lobby edits ``build_lobby`` and
    nothing else, and an agent reading ``build_lobby`` sees the lobby.
    """

    def __init__(self, node_id: str, outline: Iterable[Sequence[float]], *,
                 frame: Frame | None = None, style: Style | None = None,
                 faces: dict[str, int] | None = None, role: str = "gameplay",
                 note: str = "", intent: dict[str, Any] | None = None,
                 region_kwargs: dict[str, Any] | None = None) -> None:
        super().__init__(node_id, frame=frame, style=style, note=note)
        points = [(int(x), int(y)) for x, y in outline]
        if len(points) < 3:
            raise LevelProgramError(f"{node_id}: an outline needs at least three points")
        if area2(tuple(points)) < 0:
            points.reverse()
        self.outline = points
        # A room that does not name its faces gets the compass ones its own
        # outline offers. `rect_room` has always done this; a room with a shape
        # had to be handed a face map, and handing it the rectangle's map -- four
        # names against the first four indices -- silently named a chamfer
        # "south" and put a door on the diagonal.
        self.faces = dict(faces) if faces else _compass_edges(points)
        self.role = role
        self.intent = dict(intent or {})
        self.region_kwargs = dict(region_kwargs or {})
        self.structures: list[StructureDecl] = []
        self.details: list[DetailDecl] = []
        self.light_sources: list[LightSourceDecl] = []
        self.holes: list[list[Point]] = []
        self._hole_faces: dict[str, tuple[int, int]] = {}
        self.raw_declarations: list[RawDecl] = []

    # -- identity ---------------------------------------------------------
    @property
    def region_id(self) -> str:
        return f"region:{self.path()}"

    # -- geometry ---------------------------------------------------------
    def world_outline(self) -> list[Point]:
        frame = self.world_frame()
        return [frame.apply(point) for point in self.outline]

    def local_edge(self, name: str) -> tuple[Point, Point]:
        if name in self._hole_faces:
            hole_index, index = self._hole_faces[name]
            hole = self.holes[hole_index]
            return (hole[index], hole[(index + 1) % len(hole)])
        if name not in self.faces:
            raise LevelProgramError(
                f"{self.path()} has no face {name!r}; it offers {sorted(self.faces)}"
            )
        index = int(self.faces[name])
        return (self.outline[index], self.outline[(index + 1) % len(self.outline)])

    def face(self, name: str, *, at: float = 0.5, width: float | None = None) -> FaceRef:
        """Name a stretch of this room's boundary without computing a coordinate."""
        self.local_edge(name)  # fail here rather than at compile time
        return FaceRef(self, name, at, width)

    def face_anchor(self, name: str, *, at: float = 0.5, width: float | None = None) -> Anchor:
        frame = self.world_frame()
        start, end = (frame.apply(point) for point in self.local_edge(name))
        length = ((end[0] - start[0]) ** 2 + (end[1] - start[1]) ** 2) ** 0.5
        if length == 0:
            raise LevelProgramError(f"{self.path()}.{name} has zero length")
        span = float(length if width is None else width)
        if span > length + 1e-6:
            raise LevelProgramError(
                f"{self.path()}.{name} is {length:.0f} units long; a {span:.0f}-unit "
                "stretch does not fit on it"
            )
        ux, uy = (end[0] - start[0]) / length, (end[1] - start[1]) / length
        centre = length * float(at)
        begin = max(0.0, min(length - span, centre - span / 2.0))
        return Anchor(
            self.region_id,
            (int(round(start[0] + ux * begin)), int(round(start[1] + uy * begin))),
            (int(round(start[0] + ux * (begin + span))), int(round(start[1] + uy * (begin + span)))),
        )

    def place_against(self, my_face: str, other: FaceRef, *, slide: float = 0.0) -> "Room":
        """Move this room so one of its faces lies along another room's face.

        This is what replaces coordinate arithmetic in the source.  The author
        says *the nave's west wall meets the porch's east wall*, and the frame
        that makes it true is computed once.
        """
        target = other.anchor()
        local_start, local_end = self.local_edge(my_face)
        parent_frame = Frame()
        for node in self.ancestors():
            parent_frame = parent_frame.compose(node.frame)

        # Solve for this node's translation so that its face lands on the
        # target. Written out rather than differenced, because with quarter
        # turns in play the old shortcut -- world minus current, plus the
        # existing offset -- silently assumed both this frame and its parents
        # were unrotated.
        #
        #   world(p) = parent.turn(self.turn(p) + d) + parent.translation
        #
        # so, wanting world(local_start) == target.b:
        #
        #   d = parent.unturn(target.b - parent.translation) - self.turn(p)
        #
        # An exact-reversed coincidence: my face starts where theirs ends.
        want_x, want_y = target.b
        back = parent_frame.unturn((want_x - parent_frame.dx,
                                    want_y - parent_frame.dy))
        mine = self.frame.turn(local_start)
        dx, dy = back[0] - mine[0], back[1] - mine[1]
        if slide:
            length = ((local_end[0] - local_start[0]) ** 2
                      + (local_end[1] - local_start[1]) ** 2) ** 0.5
            if length:
                ux, uy = (local_end[0] - local_start[0]) / length, (local_end[1] - local_start[1]) / length
                dx += int(round(ux * slide))
                dy += int(round(uy * slide))
        self.frame = Frame(int(dx), int(dy), self.frame.dz, self.frame.turns)
        return self

    def hole_face(self, hole_index: int, name: str, *, at: float = 0.5,
                  width: float | None = None) -> FaceRef:
        """Name a stretch of one of this room's holes.

        A carved hole is the inward face of a solid mass, and it is where a
        building's only door meets the ground outside it.  Naming it the same
        way an outer face is named keeps that connection free of coordinates.
        """
        if not 0 <= hole_index < len(self.holes):
            raise LevelProgramError(
                f"{self.path()} has {len(self.holes)} hole(s); there is no hole {hole_index}"
            )
        key = f"hole{hole_index}:{name}"
        if key not in self.faces:
            edges = _compass_edges(self.holes[hole_index])
            if name not in edges:
                raise LevelProgramError(
                    f"{self.path()} hole {hole_index} has no {name!r} face; it offers "
                    f"{sorted(edges)}"
                )
            self._hole_faces[key] = (hole_index, edges[name])
            self.faces[key] = -1  # marks a hole face; resolved via _hole_faces
        return FaceRef(self, key, at, width)

    def carve(self, footprint: Iterable[Sequence[float]]) -> "Room":
        """Cut a hole in this room, in this room's own coordinates."""
        points = [(int(x), int(y)) for x, y in footprint]
        if area2(tuple(points)) > 0:
            points.reverse()
        self.holes.append(points)
        return self

    # -- surfaces ---------------------------------------------------------
    def surfaces(self, **overrides: Any) -> "Room":
        """State only what differs from the parent's style."""
        self.style = self.style.override(**overrides)
        return self

    # -- children ---------------------------------------------------------
    def staircase(self, structure_id: str, face: str, *, at: float = 0.5,
                  width: float | None = None, arrive_at: str | None = None,
                  connection: dict[str, Any] | None = None,
                  **options: Any) -> StructureDecl:
        """A stair growing out of one of this room's faces."""
        declaration = StructureDecl(
            structure_id, "staircase", face, at, width, options,
            arrive_at=arrive_at, connection=dict(connection or {}),
        )
        self.structures.append(declaration)
        return declaration

    def recess(self, structure_id: str, face: str, *, at: float = 0.5,
               width: float | None = None, **options: Any) -> StructureDecl:
        """A niche cut into one of this room's faces."""
        declaration = StructureDecl(structure_id, "recess", face, at, width, options)
        self.structures.append(declaration)
        return declaration

    def decorate(self, *details: DetailDecl) -> "Room":
        """Details belong to the room, not to a global sprite list."""
        self.details.extend(details)
        return self

    def light_source(self, light_id: str, *, local: Sequence[float] = (0.5, 0.5),
                     height_player_heights: float = 0.65) -> "Room":
        """Declare a source that will illuminate this room at compile time.

        Sources are named in the room that owns them rather than inferred from
        a decorative tile.  Put a visible lamp beside this declaration when the
        source ought to be visible; use it alone for an invisible source such as
        moonlight entering through an opening.
        """
        if any(item.light_id == light_id for item in self.light_sources):
            raise LevelProgramError(f"{self.path()} already has light {light_id!r}")
        self.light_sources.append(LightSourceDecl(
            str(light_id), (float(local[0]), float(local[1])),
            float(height_player_heights),
        ))
        return self

    def raw(self, note: str, apply: Callable[[PlanarLayout, "Room"], None]) -> "Room":
        """Escape hatch: do something to the compiled layout this model cannot say.

        Keeping this explicit is the point.  An unusual original structure
        should fall back to native work with a note attached, rather than force
        a bad generic abstraction into the vocabulary.
        """
        self.raw_declarations.append(RawDecl(note, apply))
        return self

    # -- reading ----------------------------------------------------------
    def summary(self) -> dict[str, Any]:
        """Everything about this room, without reading the level."""
        frame = self.world_frame()
        style = self.style_provenance()
        return {
            "path": self.path(),
            "region_id": self.region_id,
            "role": self.role,
            "note": self.note,
            "frame": self.frame.to_dict(),
            "world_frame": frame.to_dict(),
            "local_outline": [list(point) for point in self.outline],
            "faces": sorted(self.faces),
            "footprint_player_areas": round(
                abs(area2(tuple(self.outline))) / 2.0 / (PLAYER_WIDTH ** 2), 2
            ),
            "surfaces": style,
            "structures": [
                {"id": item.structure_id, "kind": item.kind, "face": item.face,
                 "details": [detail.detail_id for detail in item.details]}
                for item in self.structures
            ],
            "details": [item.detail_id for item in self.details],
            "light_sources": [item.light_id for item in self.light_sources],
            "holes": len(self.holes),
            "raw_escapes": [item.note for item in self.raw_declarations],
        }


def wall_detail(detail_id: str, picnum: int, player_heights: float, *, face: str,
                at: float = 0.5, height: float = 0.65, **fields: Any) -> DetailDecl:
    return DetailDecl(
        detail_id, picnum, player_heights, where="wall", face=face, at=at,
        height_player_heights=height, fields=fields,
    )


def floor_detail(detail_id: str, picnum: int, player_heights: float, *,
                 local: Sequence[float] = (0.5, 0.5), **fields: Any) -> DetailDecl:
    return DetailDecl(
        detail_id, picnum, player_heights, where="floor",
        local=(float(local[0]), float(local[1])), fields=fields,
    )


def native_detail(detail_id: str, picnum: int, *, x_repeat: int, y_repeat: int,
                  local: Sequence[float] = (0.5, 0.5), **fields: Any) -> DetailDecl:
    """A detail that states its Build repeats directly rather than a target height.

    Authoring wants "make this two player heights tall".  Decompiling wants the
    repeats the original actually used, because changing them would be inventing
    evidence.  Both are the same declaration with a different way of sizing it.
    """
    return DetailDecl(
        detail_id, picnum, 0.0, where="floor",
        local=(float(local[0]), float(local[1])),
        fields={"x_repeat": int(x_repeat), "y_repeat": int(y_repeat), **fields},
    )


def ceiling_detail(detail_id: str, picnum: int, player_heights: float, *,
                   local: Sequence[float] = (0.5, 0.5), height: float = 0.2,
                   **fields: Any) -> DetailDecl:
    return DetailDecl(
        detail_id, picnum, player_heights, where="ceiling",
        local=(float(local[0]), float(local[1])), height_player_heights=height,
        fields=fields,
    )


# ---------------------------------------------------------------------------
# The program itself
# ---------------------------------------------------------------------------

class LevelProgram(Assembly):
    """The root of a level, and the only object that knows how to compile."""

    def __init__(self, node_id: str = "level", *, name: str = "", visibility: int = 800,
                 style: Style | None = None, art_sizes: dict[int, tuple[int, int]] | None = None,
                 note: str = "") -> None:
        super().__init__(node_id, style=style, note=note)
        self.name = name or node_id
        self.visibility = int(visibility)
        self.art_sizes = dict(art_sizes or {})
        self.start: tuple[Room, tuple[float, float], int] | None = None
        self.stacks: list[tuple[str, str, str]] = []
        self.layer_bands: list[dict[str, Any]] = []

    def declare_layer(self, layer_id: str, *, ceiling_z: int, floor_z: int,
                      note: str = "") -> "LevelProgram":
        """Name a height band, so parts of this level may stand over each other.

        Declaring layers is what lets two assemblies occupy the same ground --
        a cellar under a yard -- and what makes them prove the engine can still
        tell them apart. A program that declares none behaves as before: any XY
        overlap is refused. See `bloodmap.layers`.
        """
        self.layer_bands.append({
            "layer_id": layer_id, "ceiling_z": int(ceiling_z),
            "floor_z": int(floor_z), "note": note,
        })
        return self

    def declare_stack(self, left: Room, right: Room, *, kind: str = "stack") -> "LevelProgram":
        """Declare that two rooms deliberately share XY footprint.

        ``PlanarLayout`` refuses undeclared XY overlap because in authored work
        it is nearly always a mistake.  Build itself allows it -- sectors are
        independent polygons resolved by portal connectivity -- and original
        maps use it, so a decompiled program says so explicitly rather than
        having the rule relaxed for everyone.
        """
        self.stacks.append((left.region_id, right.region_id, kind))
        return self

    def set_start(self, room: Room, *, local: Sequence[float] = (0.5, 0.5),
                  angle: int = 0) -> "LevelProgram":
        self.start = (room, (float(local[0]), float(local[1])), int(angle))
        return self

    # -- compilation ------------------------------------------------------
    def compile(self) -> PlanarLayout:
        """Lower the tree into flat planar source.  Absolute coordinates appear here."""
        layout = PlanarLayout(name=self.name, visibility=self.visibility)
        for band in self.layer_bands:
            layout.declare_layer(
                band["layer_id"], ceiling_z=band["ceiling_z"],
                floor_z=band["floor_z"], note=band["note"])
        rooms = self.rooms()
        if not rooms:
            raise LevelProgramError("a level program needs at least one room")

        for room in rooms:
            style = room.effective_style()
            missing = [
                name for name in ("wall_picnum", "floor_picnum", "ceiling_picnum",
                                  "floor_z", "clear_height")
                if style.get(name) is None
            ]
            if missing:
                raise LevelProgramError(
                    f"{room.path()} has no value for {missing}; state it on the room or "
                    "on one of its ancestors"
                )
            floor_z = room.world_frame().apply_z(int(style["floor_z"]))
            fields: dict[str, Any] = {
                "wall_picnum": int(style["wall_picnum"]),
                "floor_picnum": int(style["floor_picnum"]),
                "ceiling_picnum": int(style["ceiling_picnum"]),
                "floor_z": floor_z,
                "ceiling_z": floor_z - int(style["clear_height"]),
                "role": room.role,
            }
            for name in ("wall_shade", "floor_shade", "ceiling_shade"):
                if style.get(name) is not None:
                    fields[name] = int(style[name])
            if style.get("layer") is not None:
                fields["layer"] = str(style["layer"])
            if style.get("parallax_ceiling"):
                fields["parallax_ceiling"] = True
            if room.intent:
                fields["intent"] = dict(room.intent)
            fields.update(room.region_kwargs)
            frame = room.world_frame()
            layout.add_region(
                room.region_id, room.world_outline(),
                holes=[[frame.apply(point) for point in hole] for hole in room.holes],
                **fields,
            )

        for left, right, kind in self.stacks:
            layout.declare_special(left, right, kind)

        built: dict[str, Structure] = {}
        for room in rooms:
            for declaration in room.structures:
                built[declaration.structure_id] = self._build_structure(layout, room, declaration)

        for declaration in self.all_connections():
            left, right = declaration.left.anchor(), declaration.right.anchor()
            options = dict(declaration.options)
            options.setdefault("min_width", max(256, int(min(left.width, right.width))))
            layout.add_connection(
                declaration.connection_id, left.region_id, right.region_id,
                a1=left.a, a2=left.b, **options,
            )

        for room in rooms:
            self._place_details(layout, room.region_id, room, room.details)
            for declaration in room.raw_declarations:
                declaration.apply(layout, room)
            style = room.effective_style()
            floor_z = room.world_frame().apply_z(int(style["floor_z"]))
            for source in room.light_sources:
                x, y = _interior_point(room, source.local)
                layout.add_light_source(
                    f"light:{room.path()}:{source.light_id}", room.region_id,
                    x=x, y=y,
                    z=floor_z - int(round(source.height_player_heights * PLAYER_HEIGHT)),
                )

        if self.start is not None:
            room, local, angle = self.start
            x, y = _interior_point(room, local)
            style = room.effective_style()
            floor_z = room.world_frame().apply_z(int(style["floor_z"]))
            layout.set_player_start(room.region_id, x=x, y=y, z=floor_z, angle=angle)
        return layout

    def _build_structure(self, layout: PlanarLayout, room: Room,
                         declaration: StructureDecl) -> Structure:
        anchor = room.face_anchor(
            declaration.face, at=declaration.at, width=declaration.width,
        )
        style = room.effective_style()
        options = dict(declaration.options)
        surface = {
            name: int(style[name])
            for name in ("wall_picnum", "floor_picnum", "ceiling_picnum")
            if style.get(name) is not None
        }
        for name in ("wall_shade", "floor_shade", "ceiling_shade"):
            if style.get(name) is not None:
                surface.setdefault(name, int(style[name]))
        # A structure is part of the room that grew it, so its regions belong to
        # the room's layer. Without this every step of a staircase landed in the
        # default layer and the level was refused for standing somewhere it had
        # never been told about.
        if style.get("layer") is not None:
            surface.setdefault("layer", str(style["layer"]))
        surface.update({key: options.pop(key) for key in list(options)
                        if key in {"wall_picnum", "floor_picnum", "ceiling_picnum",
                                   "wall_shade", "floor_shade", "ceiling_shade"}})
        room_floor = room.world_frame().apply_z(int(style["floor_z"]))
        if declaration.kind == "staircase":
            options.setdefault("clear_height", int(style["clear_height"]))
            options.setdefault("base_floor_z", room_floor)
            structure = staircase(layout, declaration.structure_id, base=anchor, **options, **surface)
            if declaration.arrive_at:
                structure.arrive_at(declaration.arrive_at, **declaration.connection)
        elif declaration.kind == "recess":
            structure = recess(layout, declaration.structure_id, anchor=anchor, **options, **surface)
        else:
            raise LevelProgramError(f"unknown structure kind {declaration.kind!r}")
        for detail in declaration.details:
            self._place_structure_detail(layout, structure, detail)
        return structure

    def _place_structure_detail(self, layout: PlanarLayout, structure: Structure,
                                detail: DetailDecl) -> None:
        decoration = Decoration(
            decoration_id=detail.detail_id, picnum=detail.picnum,
            player_heights=detail.player_heights,
            where="flank" if detail.where == "wall" else "tread",
            cstat=detail.cstat, shade=detail.shade, aspect=detail.aspect,
            t=detail.at, height_player_heights=detail.height_player_heights,
            extra=dict(detail.fields),
        )
        structure.decorate(decoration, art_sizes=self.art_sizes)

    def _place_details(self, layout: PlanarLayout, region_id: str, room: Room,
                       details: Sequence[DetailDecl]) -> None:
        for detail in details:
            sized = (
                {} if {"x_repeat", "y_repeat"} <= set(detail.fields)
                else sprite_repeats(detail.picnum, detail.player_heights, self.art_sizes,
                                    aspect=detail.aspect)
            )
            fields = {
                "type": 0, "picnum": int(detail.picnum), "cstat": int(detail.cstat),
                "shade": int(detail.shade), **sized, **detail.fields,
            }
            placement_id = f"placement:{room.path()}:{detail.detail_id}"
            if detail.where == "wall":
                if detail.face is None:
                    raise LevelProgramError(
                        f"{room.path()}:{detail.detail_id} is a wall detail with no face"
                    )
                anchor = room.face_anchor(detail.face)
                layout.place_on_wall(
                    placement_id, region_id, a1=anchor.a, a2=anchor.b, t=detail.at,
                    height_player_heights=detail.height_player_heights,
                    offset_player_widths=detail.offset_player_widths, **fields,
                )
            elif detail.where == "floor":
                layout.place_on_floor(
                    placement_id, region_id, local=detail.local,
                    height_player_heights=detail.height_player_heights - 0.65, **fields,
                )
            elif detail.where == "ceiling":
                layout.place_on_ceiling(
                    placement_id, region_id, local=detail.local,
                    height_player_heights=detail.height_player_heights, **fields,
                )
            else:
                raise LevelProgramError(f"unknown detail placement {detail.where!r}")

    # -- reading ----------------------------------------------------------
    def outline_document(self) -> dict[str, Any]:
        """A navigable map of the program, for finding the part to edit."""
        return {
            "$schema": SCHEMA,
            "schema_version": SCHEMA_VERSION,
            "name": self.name,
            "tree": self.tree(),
            "rooms": [room.summary() for room in self.rooms()],
            "connections": [
                {"id": item.connection_id, "from": item.left.describe(),
                 "to": item.right.describe()}
                for item in self.all_connections()
            ],
            "reading_guide": [
                "a room's summary is complete: geometry, surfaces, structures and details",
                "surfaces carry the node that stated each value, so inheritance is checkable",
                "native sector and wall ids are compiler output and appear nowhere here",
            ],
        }


def _compass_edges(points: Sequence[Point]) -> dict[str, int]:
    """Compass names for the axis-aligned edges that sit on the loop's extremes."""
    count = len(points)
    min_x = min(point[0] for point in points)
    max_x = max(point[0] for point in points)
    min_y = min(point[1] for point in points)
    max_y = max(point[1] for point in points)
    result: dict[str, int] = {}
    for index in range(count):
        ax, ay = points[index]
        bx, by = points[(index + 1) % count]
        if ay == by and ay in (min_y, max_y):
            name = "north" if ay == min_y else "south"
        elif ax == bx and ax in (min_x, max_x):
            name = "west" if ax == min_x else "east"
        else:
            continue
        length = abs(bx - ax) + abs(by - ay)
        current = result.get(name)
        if current is None:
            result[name] = index
            continue
        cx, cy = points[current]
        dx, dy = points[(current + 1) % count]
        if length > abs(dx - cx) + abs(dy - cy):
            result[name] = index
    return result


def _interior_point(room: Room, local: Sequence[float]) -> Point:
    """A point inside the room at fractional local coordinates of its bounds."""
    frame = room.world_frame()
    points = [frame.apply(point) for point in room.outline]
    min_x = min(point[0] for point in points)
    max_x = max(point[0] for point in points)
    min_y = min(point[1] for point in points)
    max_y = max(point[1] for point in points)
    return (
        int(round(min_x + (max_x - min_x) * float(local[0]))),
        int(round(min_y + (max_y - min_y) * float(local[1]))),
    )
