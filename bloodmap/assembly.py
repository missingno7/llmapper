"""A mechanism is several objects and the relations between them.

Everything else in this project decompiles a level into *shape*: regions, walls,
portals, a hierarchy of rooms. That is the right decomposition for architecture
and the wrong one for machinery, and the cost has been paid one fault at a time.

A sliding gate in Blood is six objects -- a sector, two markers, two leaves, and
whatever operates it -- bound by about a dozen facts. Half of those facts are not
properties of any single object but *relations between two*: a leaf's angle is
only correct relative to the wall it sits on, its width only relative to the
distance the markers are apart, its z only relative to the floor. Mining field
values one type at a time cannot see a relation, which is why
`tools.unattested_values` reported the gate clean while it was standing edge-on
in its own doorway, twice as wide as its own travel.

So this decompiles a level the other way: pick a root, close over everything
bound to it, name each member by the part it plays, and record the relations
between the parts as well as the fields of each. Do that across the campaign and
the result is a *template* -- what a working example of this mechanism looks
like, stated in terms that survive being moved to a different room at a different
size.

Closure follows three kinds of binding, which between them cover every mechanism
the campaign builds:

* **containment** -- a sprite standing in the sector;
* **reference** -- a sector naming a sprite by index, as `marker_0` does;
* **channel** -- an object transmitting on the channel this one receives.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from math import atan2, hypot, pi
from typing import Any, Iterable

#: cstat bits that make a sprite travel with (8192) or against (16384) a moving
#: sector. A sprite carrying one of these is part of the machine, not scenery.
CARRIED_WITH = 8192
CARRIED_AGAINST = 16384

MARKER_STATNUM = 10

#: Path markers live on their own list. `kMarkerPath` is type 15 on statnum 16,
#: and the loader's marker loop -- which walks kStatMarker only -- never sees
#: them, so they are bound by a different route and are not subject to the
#: `owner` rule. The campaign contains no path sector at all; every instance
#: comes from the XMapEdit samples.
PATH_MARKER_TYPE = 15
PATH_MARKER_STATNUM = 16


def _f(item: Any) -> dict[str, Any]:
    return item["fields"] if isinstance(item, dict) else item.fields


def _x(item: Any) -> dict[str, Any] | None:
    extra = item["blood"] if isinstance(item, dict) else item.extra
    if extra is None:
        return None
    return extra["fields"] if isinstance(extra, dict) else extra.fields


@dataclass
class Member:
    """One object in an assembly, and the part it plays."""

    role: str
    kind: str
    index: int
    fields: dict[str, int] = field(default_factory=dict)
    extra: dict[str, int] = field(default_factory=dict)
    relations: dict[str, Any] = field(default_factory=dict)


@dataclass
class Assembly:
    """One instance of a mechanism, as found in one map."""

    map_name: str
    root_kind: str
    root_index: int
    root_type: int
    members: list[Member] = field(default_factory=list)
    relations: dict[str, Any] = field(default_factory=dict)

    def by_role(self, role: str) -> list[Member]:
        return [m for m in self.members if m.role == role]

    def shape(self) -> tuple[tuple[str, int], ...]:
        """The multiset of roles, which is what makes two instances comparable."""
        counts: dict[str, int] = {}
        for member in self.members:
            counts[member.role] = counts.get(member.role, 0) + 1
        return tuple(sorted(counts.items()))


def _wall_direction(ax: int, ay: int, bx: int, by: int) -> int:
    return int(round(atan2(by - ay, bx - ax) / (2 * pi) * 2048)) & 2047


def _nearest_wall(disk: Any, sector_index: int, x: int, y: int):
    fields = _f(disk.sectors[sector_index])
    start, count = int(fields["wall_ptr"]), int(fields["wall_count"])
    best = None
    for wall in range(start, start + count):
        wf = _f(disk.walls[wall])
        ax, ay = int(wf["x"]), int(wf["y"])
        nxt = int(wf["point2"])
        bx, by = int(_f(disk.walls[nxt])["x"]), int(_f(disk.walls[nxt])["y"])
        dx, dy = bx - ax, by - ay
        length = dx * dx + dy * dy
        t = 0.0 if not length else max(0.0, min(1.0, ((x - ax) * dx + (y - ay) * dy) / length))
        distance = hypot(x - (ax + t * dx), y - (ay + t * dy))
        if best is None or distance < best[0]:
            best = (distance, ax, ay, bx, by)
    return best


def sprite_role(disk: Any, sprite: Any) -> str:
    """What part a sprite plays, from what the engine will do with it."""
    fields = _f(sprite)
    type_id = int(fields["type"])
    cstat = int(fields["cstat"])
    if type_id == PATH_MARKER_TYPE and int(fields["status"]) == PATH_MARKER_STATNUM:
        return "marker_path"
    if int(fields["status"]) == MARKER_STATNUM or type_id in (1, 2, 3, 4, 5, 6, 7):
        return {3: "marker_off", 4: "marker_on", 5: "marker_axis"}.get(type_id, "marker")
    # A sprite carried by a moving sector is part of the machine, but "carried"
    # alone is too coarse a part to be useful: across the campaign's slide gates
    # it groups fence leaves together with the exploder charges that happen to
    # ride a moving platform, and their modal fields then describe neither. What
    # the sprite *is* has to stay in the role.
    if cstat & (CARRIED_WITH | CARRIED_AGAINST):
        direction = "with" if cstat & CARRIED_WITH else "against"
        what = "panel" if type_id == 0 else f"thing_{type_id}"
        return f"carried_{direction}_{what}"
    if type_id in (20, 21, 22, 23):
        return "switch"
    if type_id:
        return f"thing_{type_id}"
    return "decoration"


def assembly_around(disk: Any, sector_index: int, *, map_name: str = "") -> Assembly:
    """Close over everything bound to this sector and name each part."""
    sector = disk.sectors[sector_index]
    sector_fields = _f(sector)
    sector_extra = _x(sector) or {}
    out = Assembly(
        map_name=map_name, root_kind="sector", root_index=sector_index,
        root_type=int(sector_fields["type"]),
        relations={
            "state_busy": (int(sector_extra.get("state", 0)),
                           int(sector_extra.get("busy", 0))),
            "height": abs(int(sector_fields["floor_z"]) - int(sector_fields["ceiling_z"])),
        },
    )
    out.members.append(Member(
        role="sector", kind="sector", index=sector_index,
        fields={"type": int(sector_fields["type"])},
        extra={k: int(v) for k, v in sector_extra.items() if k != "reference"},
    ))

    seen: set[tuple[str, int]] = {("sector", sector_index)}

    def add_sprite(index: int, role: str | None = None) -> Member | None:
        if ("sprite", index) in seen or not 0 <= index < len(disk.sprites):
            return None
        seen.add(("sprite", index))
        sprite = disk.sprites[index]
        fields = _f(sprite)
        extra = _x(sprite) or {}
        member = Member(
            role=role or sprite_role(disk, sprite), kind="sprite", index=index,
            fields={k: int(fields[k]) for k in
                    ("type", "picnum", "cstat", "angle", "x_repeat", "y_repeat", "status")},
            extra={k: int(v) for k, v in extra.items() if k != "reference"},
        )
        out.members.append(member)
        return member

    # containment
    for index, sprite in enumerate(disk.sprites):
        if int(_f(sprite)["sector"]) == sector_index:
            add_sprite(index)
    # reference
    for name in ("marker_0", "marker_1"):
        ref = int(sector_extra.get(name, -1))
        if ref > 0:
            member = add_sprite(ref)
            if member is not None and not member.role.startswith("marker"):
                member.role = "marker"
    # channel
    receives = int(sector_extra.get("rx_id", 0))
    if receives:
        for index, sprite in enumerate(disk.sprites):
            extra = _x(sprite)
            if extra and int(extra.get("tx_id", 0)) == receives:
                member = add_sprite(index, role=None)
                if member is None:
                    for existing in out.members:
                        if existing.kind == "sprite" and existing.index == index:
                            existing.relations["operates_root"] = True
                else:
                    member.relations["operates_root"] = True
                    if not member.role.startswith(("switch", "carried")):
                        member.role = "operator"

    _add_relations(disk, out, sector_index)
    return out


def _add_relations(disk: Any, out: Assembly, sector_index: int) -> None:
    """The facts that live between two members rather than inside one."""
    sector_fields = _f(disk.sectors[sector_index])
    floor_z = int(sector_fields["floor_z"])
    height = abs(floor_z - int(sector_fields["ceiling_z"]))

    markers = {m.role: m for m in out.members if m.role.startswith("marker")}
    travel = None
    if "marker_off" in markers and "marker_on" in markers:
        a = _f(disk.sprites[markers["marker_off"].index])
        b = _f(disk.sprites[markers["marker_on"].index])
        travel = hypot(int(b["x"]) - int(a["x"]), int(b["y"]) - int(a["y"]))
        out.relations["travel"] = round(travel)
        out.relations["marker_angles"] = (int(a["angle"]), int(b["angle"]))
    if "marker_axis" in markers:
        out.relations["pivot_angle"] = int(_f(disk.sprites[markers["marker_axis"].index])["angle"])

    for member in out.members:
        if member.kind != "sprite" or member.role.startswith("marker"):
            continue
        fields = _f(disk.sprites[member.index])
        if int(fields["sector"]) != sector_index:
            continue
        # An invisible sprite has no angle or drawn size that anyone sees, so
        # comparing either against the campaign says nothing. Ambient sound
        # generators are the case that showed it: they sit in most gates and
        # sludge pits, they are always cstat 32896, and their facing was being
        # reported as a deviation from a convention that cannot exist.
        if int(fields["cstat"]) & 32768:
            continue
        x, y = int(fields["x"]), int(fields["y"])
        near = _nearest_wall(disk, sector_index, x, y)
        if near is not None:
            member.relations["wall_distance"] = round(near[0])
            member.relations["angle_over_wall"] = (
                int(fields["angle"]) - _wall_direction(*near[1:])) & 2047
        if travel:
            member.relations["width_over_travel"] = round(
                (int(fields["x_repeat"]) / 4.0) / travel, 3)
        if height:
            member.relations["repeat_over_height"] = round(
                (int(fields["y_repeat"]) << 2) / height, 4)

    # what the operators send, given how the root rests
    commands = sorted({
        int(m.extra.get("command", 0)) for m in out.members
        if m.relations.get("operates_root")
    })
    if commands:
        out.relations["operator_commands"] = commands
