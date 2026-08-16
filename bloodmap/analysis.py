from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import asdict, dataclass
from math import hypot
from pathlib import Path
from typing import Any

from .model import DiskMap, DiskObject, LevelIR


@dataclass(frozen=True)
class Diagnostic:
    severity: str
    code: str
    message: str
    location: str


def validate_map(disk: DiskMap) -> list[Diagnostic]:
    out: list[Diagnostic] = []

    def emit(severity: str, code: str, message: str, location: str) -> None:
        out.append(Diagnostic(severity, code, message, location))

    ns, nw, nsp = len(disk.sectors), len(disk.walls), len(disk.sprites)
    h = disk.header
    for label, count, maximum in (("sectors", ns, 1024), ("walls", nw, 8192), ("sprites", nsp, 4096)):
        if count > maximum:
            emit("error", "count-limit", f"{count} {label} exceeds the corpus-version limit {maximum}", "header")
    if h["start_sector"] < 0 or h["start_sector"] >= ns:
        emit("error", "start-sector", f"start sector {h['start_sector']} is outside 0..{ns-1}", "header")
    if not 0 <= h["start_angle"] < 2048:
        emit("error", "start-angle", f"start angle {h['start_angle']} is outside 0..2047", "header")

    wall_owner: list[int | None] = [None] * nw
    for si, sector in enumerate(disk.sectors):
        first, count = sector.wall_ptr, sector.wall_count
        if first < 0 or count <= 0 or first + count > nw:
            emit("error", "sector-wall-range", f"wall range [{first}, {first+count}) is invalid", f"sector[{si}]")
            continue
        if count < 3:
            emit("warning", "degenerate-sector", f"sector has only {count} walls; accepted by Build but geometrically degenerate", f"sector[{si}]")
        for wi in range(first, first + count):
            if wall_owner[wi] is not None:
                emit("error", "wall-multiple-sectors", f"also owned by sector {wall_owner[wi]}", f"wall[{wi}]")
            wall_owner[wi] = si
            p2 = disk.walls[wi].point2
            if not first <= p2 < first + count:
                emit("error", "point2-sector-range", f"point2 {p2} leaves owning sector range", f"wall[{wi}]")

        unseen = set(range(first, first + count))
        while unseen:
            start = min(unseen)
            current = start
            loop_seen: set[int] = set()
            while current not in loop_seen and current in unseen:
                loop_seen.add(current)
                unseen.remove(current)
                current = disk.walls[current].point2
            if current != start:
                emit("error", "wall-loop-open", f"wall chain from {start} closes at {current}, not {start}", f"sector[{si}]")

    for wi, owner in enumerate(wall_owner):
        if owner is None:
            emit("error", "wall-unowned", "wall is outside every sector wall range", f"wall[{wi}]")

    for wi, wall in enumerate(disk.walls):
        p2 = wall.point2
        if p2 < 0 or p2 >= nw:
            emit("error", "point2", f"point2 {p2} is outside 0..{nw-1}", f"wall[{wi}]")
        nwall, nsector = wall.next_wall, wall.next_sector
        if (nwall == -1) != (nsector == -1):
            emit("error", "portal-pair", f"next_wall={nwall}, next_sector={nsector} must both be -1 or valid", f"wall[{wi}]")
        if nwall != -1:
            if not 0 <= nwall < nw:
                emit("error", "next-wall", f"next wall {nwall} is outside 0..{nw-1}", f"wall[{wi}]")
            if not 0 <= nsector < ns:
                emit("error", "next-sector", f"next sector {nsector} is outside 0..{ns-1}", f"wall[{wi}]")
            if 0 <= nwall < nw:
                other = disk.walls[nwall]
                if other.next_wall != wi:
                    emit("warning", "portal-nonreciprocal-wall", f"wall {nwall} points back to {other.next_wall}; Build accepts this original-map portal trick", f"wall[{wi}]")
                expected_owner = wall_owner[wi]
                if other.next_sector != expected_owner:
                    emit("warning", "portal-nonreciprocal-sector", f"wall {nwall} points to sector {other.next_sector}, expected {expected_owner}", f"wall[{wi}]")
                if 0 <= nsector < ns and wall_owner[nwall] != nsector:
                    emit("warning", "portal-owner", f"next wall {nwall} belongs to sector {wall_owner[nwall]}, not {nsector}", f"wall[{wi}]")

    for spi, sprite in enumerate(disk.sprites):
        if sprite.sector < 0 or sprite.sector >= ns:
            emit("error", "sprite-sector", f"sector {sprite.sector} is outside 0..{ns-1}", f"sprite[{spi}]")
        # Sprite angle is a signed 16-bit disk field. Build angle consumers mask it
        # modulo 2048, and original maps intentionally contain negative values.

    for label, items, limit in (("sector", disk.sectors, 1024), ("wall", disk.walls, 8192), ("sprite", disk.sprites, 4096)):
        owners: dict[int, int] = {}
        for index, obj in enumerate(items):
            ref = obj.fields["extra"]
            if ref <= 0:
                if obj.extra is not None:
                    emit("error", "extra-without-reference", "extended record exists but extra <= 0", f"{label}[{index}]")
                continue
            if ref >= limit:
                emit("error", "extra-range", f"extra index {ref} is outside 1..{limit-1}", f"{label}[{index}]")
            if ref in owners:
                emit("error", "extra-duplicate", f"extra index {ref} also belongs to {label} {owners[ref]}", f"{label}[{index}]")
            owners[ref] = index
            if obj.extra is None:
                emit("error", "missing-extra", f"extra index {ref} has no inline extended record", f"{label}[{index}]")
            # The packed reference field is redundant. Both authoritative loaders
            # bind by inline order/Build `extra` and overwrite this value with the
            # current owner; original maps contain stale values after deletions.

    for si, sector in enumerate(disk.sectors):
        if sector.extra is None:
            continue
        for name in ("marker_0", "marker_1"):
            marker = sector.extra.fields[name]
            if marker != -1 and not 0 <= marker < nsp:
                emit("warning", "marker-reference", f"{name}={marker} is not -1 or a sprite index", f"sector[{si}].XSECTOR")

    return out


def geometry_view(disk: DiskMap) -> list[dict[str, Any]]:
    sprite_ids: dict[int, list[int]] = defaultdict(list)
    for i, sprite in enumerate(disk.sprites):
        sprite_ids[sprite.sector].append(i)
    result = []
    for si, sector in enumerate(disk.sectors):
        ids = list(range(sector.wall_ptr, sector.wall_ptr + sector.wall_count))
        points = [(disk.walls[i].x, disk.walls[i].y) for i in ids if 0 <= i < len(disk.walls)]
        neighbors: dict[int, list[int]] = defaultdict(list)
        for wi in ids:
            if 0 <= wi < len(disk.walls) and disk.walls[wi].next_sector >= 0:
                neighbors[disk.walls[wi].next_sector].append(wi)
        if points:
            xs, ys = zip(*points)
            bounds = {"min_x": min(xs), "min_y": min(ys), "max_x": max(xs), "max_y": max(ys)}
            # Polygon centroid for the first/simple loop; arithmetic mean is the robust fallback.
            twice_area = 0
            cx6, cy6 = 0, 0
            for wi in ids:
                if not 0 <= wi < len(disk.walls):
                    continue
                w = disk.walls[wi]
                if not 0 <= w.point2 < len(disk.walls):
                    continue
                q = disk.walls[w.point2]
                cross = w.x * q.y - q.x * w.y
                twice_area += cross
                cx6 += (w.x + q.x) * cross
                cy6 += (w.y + q.y) * cross
            if twice_area:
                centroid = {"x": cx6 / (3 * twice_area), "y": cy6 / (3 * twice_area)}
            else:
                centroid = {"x": sum(xs) / len(xs), "y": sum(ys) / len(ys)}
        else:
            bounds = None
            centroid = None
        result.append({
            "sector": si, "walls": ids, "neighbors": [
                {"sector": n, "portal_walls": ws} for n, ws in sorted(neighbors.items())
            ], "bounds": bounds, "centroid": centroid,
            "ceiling_z": sector.ceiling_z, "floor_z": sector.floor_z,
            "sprites": sprite_ids.get(si, []),
        })
    return result


def channel_graph(disk: DiskMap, channel: int | None = None) -> dict[str, Any]:
    transmitters: dict[int, list[dict[str, Any]]] = defaultdict(list)
    receivers: dict[int, list[dict[str, Any]]] = defaultdict(list)
    for kind, objects in (("sector", disk.sectors), ("wall", disk.walls), ("sprite", disk.sprites)):
        for index, obj in enumerate(objects):
            if obj.extra is None:
                continue
            f = obj.extra.fields
            base = {"kind": kind, "id": index}
            if f["tx_id"]:
                transmitters[f["tx_id"]].append({**base, "command": f["command"], "trigger_on": f["trigger_on"], "trigger_off": f["trigger_off"]})
            if f["rx_id"]:
                receivers[f["rx_id"]].append(base)
    ids = sorted(({channel} if channel is not None else set(transmitters) | set(receivers)))
    return {"channels": [
        {"channel": ch, "transmitters": transmitters.get(ch, []), "receivers": receivers.get(ch, [])}
        for ch in ids
    ]}


def corpus_statistics(maps: list[tuple[str, DiskMap]]) -> dict[str, Any]:
    sprite_types: Counter[int] = Counter()
    sector_types: Counter[int] = Counter()
    wall_types: Counter[int] = Counter()
    tiles: Counter[int] = Counter()
    commands: Counter[int] = Counter()
    keys: Counter[int] = Counter()
    channels: Counter[int] = Counter()
    trigger_combinations: Counter[str] = Counter()
    entries = []
    for name, disk in maps:
        xs = [w.x for w in disk.walls] + [s.x for s in disk.sprites]
        ys = [w.y for w in disk.walls] + [s.y for s in disk.sprites]
        entries.append({
            "filename": name, "sectors": len(disk.sectors), "walls": len(disk.walls),
            "sprites": len(disk.sprites),
            "portal_walls": sum(wall.next_sector >= 0 for wall in disk.walls),
            "extended": {
                "xsectors": sum(obj.extra is not None for obj in disk.sectors),
                "xwalls": sum(obj.extra is not None for obj in disk.walls),
                "xsprites": sum(obj.extra is not None for obj in disk.sprites),
            }, "bounds": {
                "min_x": min(xs), "min_y": min(ys), "max_x": max(xs), "max_y": max(ys),
            } if xs else None,
        })
        for obj, counter in ((disk.sectors, sector_types), (disk.walls, wall_types), (disk.sprites, sprite_types)):
            counter.update(item.fields["type"] for item in obj)
        for sector in disk.sectors:
            tiles.update((sector.ceiling_picnum, sector.floor_picnum))
        for wall in disk.walls:
            tiles.update((wall.picnum, wall.over_picnum))
        tiles.update(sprite.picnum for sprite in disk.sprites)
        for objects in (disk.sectors, disk.walls, disk.sprites):
            for obj in objects:
                if obj.extra is not None:
                    f = obj.extra.fields
                    commands[f["command"]] += 1
                    keys[f["key"]] += 1
                    channels.update(ch for ch in (f["tx_id"], f["rx_id"]) if ch)
                    active = sorted(name for name, value in f.items() if name.startswith("trigger_") and value)
                    trigger_combinations["+".join(active) if active else "none"] += 1

    def counts(counter: Counter[int]) -> list[dict[str, int]]:
        return [{"id": key, "count": count} for key, count in sorted(counter.items())]
    return {
        "maps": entries, "totals": {
            "maps": len(maps), "sectors": sum(x["sectors"] for x in entries),
            "walls": sum(x["walls"] for x in entries), "sprites": sum(x["sprites"] for x in entries),
        },
        "sprite_types": counts(sprite_types), "sector_types": counts(sector_types),
        "wall_types": counts(wall_types), "tile_ids": counts(tiles),
        "commands": counts(commands), "keys": counts(keys), "channels": counts(channels),
        "trigger_combinations": [
            {"flags": key, "count": count} for key, count in trigger_combinations.most_common()
        ],
    }


def render_svg(disk: DiskMap, *, labels: bool = True, selected: tuple[str, int] | None = None) -> str:
    if not disk.walls:
        return '<svg xmlns="http://www.w3.org/2000/svg" width="800" height="600"/>'
    min_x = min(w.x for w in disk.walls)
    max_x = max(w.x for w in disk.walls)
    min_y = min(w.y for w in disk.walls)
    max_y = max(w.y for w in disk.walls)
    width, height, margin = 1400, 1000, 30
    sx = (width - 2 * margin) / max(1, max_x - min_x)
    sy = (height - 2 * margin) / max(1, max_y - min_y)
    scale = min(sx, sy)

    def xy(x: int, y: int) -> tuple[float, float]:
        return margin + (x - min_x) * scale, height - margin - (y - min_y) * scale

    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">',
        '<rect width="100%" height="100%" fill="#111318"/>',
        '<g fill="none" stroke-linecap="round">',
    ]
    for wi, wall in enumerate(disk.walls):
        if not 0 <= wall.point2 < len(disk.walls):
            continue
        q = disk.walls[wall.point2]
        x1, y1 = xy(wall.x, wall.y)
        x2, y2 = xy(q.x, q.y)
        color = "#43a4db" if wall.next_sector >= 0 else "#d8dde6"
        stroke = 2.5 if selected == ("wall", wi) else 0.7
        parts.append(f'<line x1="{x1:.2f}" y1="{y1:.2f}" x2="{x2:.2f}" y2="{y2:.2f}" stroke="{color}" stroke-width="{stroke}"/>')
        if labels and selected == ("wall", wi):
            parts.append(f'<text x="{(x1+x2)/2:.2f}" y="{(y1+y2)/2-4:.2f}" fill="#ffcc66" font-family="monospace" font-size="10">W{wi}</text>')
    parts.append('</g><g font-family="monospace" font-size="9" text-anchor="middle">')
    geometry = geometry_view(disk)
    if labels:
        for item in geometry:
            if item["centroid"] is None:
                continue
            x, y = xy(round(item["centroid"]["x"]), round(item["centroid"]["y"]))
            color = "#ffcc66" if selected == ("sector", item["sector"]) else "#7bd88f"
            parts.append(f'<text x="{x:.2f}" y="{y:.2f}" fill="{color}">S{item["sector"]}</text>')
    for si, sprite in enumerate(disk.sprites):
        x, y = xy(sprite.x, sprite.y)
        color = "#ff5f5f" if selected == ("sprite", si) else "#e78cff"
        radius = 4 if selected == ("sprite", si) else 1.8
        parts.append(f'<circle cx="{x:.2f}" cy="{y:.2f}" r="{radius}" fill="{color}"/>')
        if labels and (selected == ("sprite", si)):
            parts.append(f'<text x="{x:.2f}" y="{y-6:.2f}" fill="{color}">P{si}</text>')
    px, py = xy(disk.header["start_x"], disk.header["start_y"])
    parts.append(f'<path d="M {px-5:.2f} {py:.2f} L {px+5:.2f} {py:.2f} M {px:.2f} {py-5:.2f} L {px:.2f} {py+5:.2f}" stroke="#ffd866" stroke-width="2"/>')
    parts.append('</g></svg>')
    return "\n".join(parts)
