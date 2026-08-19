#!/usr/bin/env python3
"""Render a bot run over the level geometry as an SVG.

Offline analysis only.  Shows where the bot actually went, where it stalled,
and which sectors it never entered, so a run can be read spatially instead
of only as a list of events.
"""
import argparse
import collections
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from bloodmap.format import read_map  # noqa: E402


def load_geometry(path):
    disk = read_map(path)
    walls, sectors = disk.walls, disk.sectors
    segments = []
    sector_walls = collections.defaultdict(list)
    for index, sector in enumerate(sectors):
        first = sector.fields["wall_ptr"]
        for offset in range(sector.fields["wall_count"]):
            wall_id = first + offset
            wall = walls[wall_id]
            nxt = walls[wall.fields["point2"]]
            solid = wall.fields["next_sector"] < 0
            segments.append((wall.fields["x"], wall.fields["y"],
                             nxt.fields["x"], nxt.fields["y"], solid, wall_id, index))
            sector_walls[index].append(wall_id)
    return disk, segments, sector_walls


def sector_centroid(disk, sector_walls, index):
    ids = sector_walls.get(index, [])
    if not ids:
        return None
    xs = [disk.walls[w].fields["x"] for w in ids]
    ys = [disk.walls[w].fields["y"] for w in ids]
    return sum(xs) / len(xs), sum(ys) / len(ys)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("map")
    parser.add_argument("trajectory")
    parser.add_argument("--telemetry")
    parser.add_argument("--output", required=True)
    parser.add_argument("--width", type=int, default=1600)
    parser.add_argument("--zoom", action="store_true",
                        help="frame the area the bot actually reached")
    parser.add_argument("--pad", type=int, default=6000)
    args = parser.parse_args()

    disk, segments, sector_walls = load_geometry(args.map)
    points = [json.loads(line) for line in
              Path(args.trajectory).read_text(encoding="utf-8", errors="replace").splitlines()
              if line.strip()]
    visited = {p.get("sector") for p in points if p.get("sector") is not None}

    xs = [c for s in segments for c in (s[0], s[2])]
    ys = [c for s in segments for c in (s[1], s[3])]
    min_x, max_x, min_y, max_y = min(xs), max(xs), min(ys), max(ys)
    if args.zoom and points:
        px = [p["x"] for p in points]
        py = [p["y"] for p in points]
        min_x, max_x = min(px) - args.pad, max(px) + args.pad
        min_y, max_y = min(py) - args.pad, max(py) + args.pad
    span_x, span_y = max(1, max_x - min_x), max(1, max_y - min_y)
    scale = args.width / span_x
    height = int(span_y * scale)

    def project(x, y):
        return (x - min_x) * scale, (y - min_y) * scale

    out = ['<svg xmlns="http://www.w3.org/2000/svg" width="%d" height="%d" '
           'viewBox="0 0 %d %d">' % (args.width, height, args.width, height)]
    out.append('<rect width="100%%" height="100%%" fill="#12141a"/>')

    # Geometry: reachable-but-unvisited sectors are highlighted.
    for x1, y1, x2, y2, solid, _wall_id, sector_id in segments:
        ax, ay = project(x1, y1)
        bx, by = project(x2, y2)
        if solid:
            colour, width = ("#4a5568", 1.4)
        else:
            colour, width = ("#2d3748", 0.7)
        if sector_id in visited:
            colour = "#7f8ea3" if solid else "#3d4a5c"
        out.append('<line x1="%.1f" y1="%.1f" x2="%.1f" y2="%.1f" stroke="%s" '
                   'stroke-width="%.1f"/>' % (ax, ay, bx, by, colour, width))

    # Label sectors the bot entered, in visit order.
    order, seen = [], set()
    for point in points:
        sector_id = point.get("sector")
        if sector_id is not None and sector_id not in seen:
            seen.add(sector_id)
            order.append(sector_id)
    for step, sector_id in enumerate(order):
        centre = sector_centroid(disk, sector_walls, sector_id)
        if not centre:
            continue
        cx, cy = project(*centre)
        out.append('<circle cx="%.1f" cy="%.1f" r="9" fill="#1a202c" stroke="#68d391" '
                   'stroke-width="1.5"/>' % (cx, cy))
        out.append('<text x="%.1f" y="%.1f" fill="#68d391" font-size="10" '
                   'font-family="monospace" text-anchor="middle">%d</text>'
                   % (cx, cy + 3.5, sector_id))
        out.append('<text x="%.1f" y="%.1f" fill="#f6ad55" font-size="8" '
                   'font-family="monospace" text-anchor="middle">#%d</text>'
                   % (cx, cy - 11, step))

    # Path, coloured from cold (start) to hot (end).
    total = max(1, len(points) - 1)
    for index in range(total):
        a, b = points[index], points[index + 1]
        ax, ay = project(a["x"], a["y"])
        bx, by = project(b["x"], b["y"])
        ratio = index / total
        colour = "#%02x%02x%02x" % (int(60 + 195 * ratio), int(180 - 90 * ratio),
                                    int(240 - 200 * ratio))
        out.append('<line x1="%.1f" y1="%.1f" x2="%.1f" y2="%.1f" stroke="%s" '
                   'stroke-width="1.6" opacity="0.85"/>' % (ax, ay, bx, by, colour))

    if points:
        sx, sy = project(points[0]["x"], points[0]["y"])
        ex, ey = project(points[-1]["x"], points[-1]["y"])
        out.append('<circle cx="%.1f" cy="%.1f" r="7" fill="none" stroke="#63b3ed" '
                   'stroke-width="2.5"/>' % (sx, sy))
        out.append('<circle cx="%.1f" cy="%.1f" r="7" fill="#f56565"/>' % (ex, ey))

    out.append('<text x="12" y="22" fill="#e2e8f0" font-size="15" font-family="monospace">'
               '%s &#183; %d/%d sectors entered &#183; blue=start red=end</text>'
               % (Path(args.map).stem, len(visited), len(disk.sectors)))
    out.append("</svg>")
    Path(args.output).write_text("\n".join(out), encoding="utf-8")
    print(json.dumps({"output": args.output, "visited": len(visited),
                      "total": len(disk.sectors), "order": order}))


if __name__ == "__main__":
    main()
