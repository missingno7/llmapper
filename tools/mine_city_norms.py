"""Mine what a Build-engine city is, before designing one.

Blood City (projects/blood-city) is a large urban level.  Nothing in the
existing knowledge registries describes *urban* structure -- street widths,
block sizes, how much of a facade is enterable -- because the campaign corpus
is mostly interiors.  This pass measures the three city precedents the project
names and writes the numbers the urban plan has to hit:

    python -m tools.mine_city_norms \\
        -o projects/blood-city/references/city-norms.json

Structure comes from all sources (E3M1, DWE3M1, DukCity1-4); art comes from
the Blood two only, because tile identity does not transfer between games --
the project already measured that between *episodes*.

Method notes, so a number here can be argued with instead of trusted:

* "Street" is the largest connected component of sky-ceiling sectors linked by
  red walls the player can walk through at grade (floor step <= max_step).
  Sky rooftops reached through interiors land in other components and are
  counted under verticality instead.
* Widths are measured by ray-casting from street boundary walls across a
  raster of the street region (cell 128 units), sampled every 256 units of
  boundary.  Slopes are read at their flat z; the city precedents keep their
  streets flat.
* Vertical build z is compared to plan xy through the engine's own 16:1 ratio
  (256 z per texel of a 64-texel/1024-unit wall), so a canyon ratio is
  dimensionless.
* Blocks are the enclosed holes of the street raster: a region you can walk
  all the way around.  Street loop count is exactly that hole count.
* Every threshold an "interpreted" number depends on is echoed into the
  output next to the number.
"""

from __future__ import annotations

import argparse
import json
import math
import pathlib
import statistics
from collections import Counter, defaultdict, deque
from typing import Any

import numpy as np

from bloodmap.doors import MOTION_TYPES as BLOOD_DOOR_SECTOR_TYPES
from bloodmap.duke import read_duke_map
from bloodmap.format import read_map
from bloodmap.patterns import corpus_map_path
from bloodmap.player_space import PLAYER_PROFILES
from tools.mine_mechanisms import observe as observe_channels
from tools.mine_stacks import observe as observe_stacks

SCHEMA = "llmapper.city-norms"
SCHEMA_VERSION = 1

#: 256 z units per texel of wall height, 16 xy units per texel of wall length.
Z_PER_XY = 16

CELL = 128
BOUNDARY_SAMPLE_STEP = 256
MAX_RAY = 65536

#: A raster hole smaller than this is a lamppost base or a fountain, not a
#: city block.  512x512 units is about two player heights on a side.
MIN_BLOCK_AREA = 512 * 512

#: An interior smaller than this is a niche or a closet, not an enterable
#: building.  1024x1024 units fits a small shop counter and room to turn.
MIN_INTERIOR_AREA = 1024 * 1024

#: EDuke32 sector lotags for doors (ceiling/floor/split/swing/slide families).
#: Interpreted from EDuke32 sector effector documentation; used only to keep a
#: closed-at-rest Duke door from being read as a solid wall.
DUKE_DOOR_LOTAGS = {20, 21, 22, 23, 25, 26, 27, 28, 29}

#: Blood sources name a map; the registry says where it lives, because the
#: corpus is provenance directories rather than one flat folder. Duke's is
#: still a flat directory, so it is still spelled out.
#:
#: `missing_ok` because this table is built at import time: without a local
#: corpus it must still yield a path that does not exist, exactly as the
#: hardcoded strings did, rather than stopping the import of every module
#: that reads this list.
STRUCTURE_SOURCES = [
    ("E3M1", "blood", corpus_map_path("E3M1", missing_ok=True)),
    ("DWE3M1", "blood", corpus_map_path("DWE3M1", missing_ok=True)),
    ("DukCity1", "duke3d", "maps/duke3d/DukCity1.map"),
    ("DukCity2", "duke3d", "maps/duke3d/DukCity2.map"),
    ("DukCity3", "duke3d", "maps/duke3d/DukCity3.map"),
    ("DukCity4", "duke3d", "maps/duke3d/DukCity4.map"),
    # Owner-approved 2026-08-27 (urban-source screening): the pier promenade,
    # the dense town at the engine ceiling, and the walled town with the rail
    # corridor.  Rejected in the same screening, with the rules now encoded
    # in street_component and blocks_fronted: DWE2M1 (open space, not
    # streets), E2M2 (lumber stacks, not buildings), and the wilderness set
    # (loops without enterability are landscape).
    ("DWE3M10", "blood", corpus_map_path("DWE3M10", missing_ok=True)),
    ("TEDE1M2", "blood", corpus_map_path("TEDE1M2", missing_ok=True)),
    ("E3M2", "blood", corpus_map_path("E3M2", missing_ok=True)),
]

#: Art admissibility measured 2026-08-27: TEDE1M2 uses 95% and DWE3M10 97%
#: campaign-vocabulary tiles (DWE3M1, already admitted, sits at 94%), so
#: both join the art set; their few foreign ids (TEDE1M2: 85,136,337,357,
#: 367,377,960; DWE3M10: 85,377,2182) are excluded from any art norm.
ART_SOURCE_NAMES = {"E3M1", "DWE3M1", "TEDE1M2", "DWE3M10"}


def _percentiles(values: list[float], digits: int = 1) -> dict[str, float]:
    if not values:
        return {"n": 0}
    ordered = sorted(values)
    return {
        "n": len(ordered),
        "min": round(ordered[0], digits),
        "p10": round(ordered[len(ordered) // 10], digits),
        "median": round(statistics.median(ordered), digits),
        "p90": round(ordered[len(ordered) * 9 // 10], digits),
        "max": round(ordered[-1], digits),
    }


# ---------------------------------------------------------------------------
# Map geometry model


class MapGeom:
    """Flat tables the urban measurements read, built once per map."""

    def __init__(self, name: str, game: str, disk: Any):
        self.name = name
        self.game = game
        self.disk = disk
        self.profile = PLAYER_PROFILES[game]
        self.sectors = disk.sectors
        self.walls = disk.walls
        self.sprites = disk.sprites
        self.wall_owner = self._wall_owners()
        self.sector_walls = [
            list(range(int(s.fields["wall_ptr"]),
                       int(s.fields["wall_ptr"]) + int(s.fields["wall_count"])))
            for s in self.sectors
        ]
        self.parallax = [bool(int(s.fields["ceiling_stat"]) & 1) for s in self.sectors]
        self.floor_z = [int(s.fields["floor_z"]) for s in self.sectors]
        self.ceiling_z = [int(s.fields["ceiling_z"]) for s in self.sectors]
        self.area = [self._sector_area(i) for i in range(len(self.sectors))]

    def _wall_owners(self) -> list[int]:
        owner = [0] * len(self.walls)
        for sector_id, sector in enumerate(self.sectors):
            start = int(sector.fields["wall_ptr"])
            for w in range(start, start + int(sector.fields["wall_count"])):
                owner[w] = sector_id
        return owner

    def wall_xy(self, wall_id: int) -> tuple[int, int]:
        f = self.walls[wall_id].fields
        return int(f["x"]), int(f["y"])

    def wall_segment(self, wall_id: int) -> tuple[tuple[int, int], tuple[int, int]]:
        return self.wall_xy(wall_id), self.wall_xy(int(self.walls[wall_id].fields["point2"]))

    def wall_length(self, wall_id: int) -> float:
        (x1, y1), (x2, y2) = self.wall_segment(wall_id)
        return math.hypot(x2 - x1, y2 - y1)

    def _sector_area(self, sector_id: int) -> float:
        total = 0.0
        for w in self.sector_walls[sector_id]:
            (x1, y1), (x2, y2) = self.wall_segment(w)
            total += x1 * y2 - x2 * y1
        return abs(total) / 2.0

    def gap(self, a: int, b: int) -> int:
        """Passable vertical window through the red wall between a and b (z units)."""
        return min(self.floor_z[a], self.floor_z[b]) - max(self.ceiling_z[a], self.ceiling_z[b])

    def rise(self, from_sector: int, to_sector: int) -> int:
        """Floor climb from one sector to the next, positive going up (z units)."""
        return self.floor_z[from_sector] - self.floor_z[to_sector]

    def is_door_sector(self, sector_id: int) -> bool:
        sector = self.sectors[sector_id]
        if self.game == "blood":
            return int(sector.fields.get("type", 0)) in BLOOD_DOOR_SECTOR_TYPES
        return (int(sector.fields["lotag"]) & 0x3FFF) in DUKE_DOOR_LOTAGS


def load_source(name: str, game: str, path: str) -> MapGeom:
    if game == "blood":
        disk = read_map(path)
    else:
        disk = read_duke_map(path)
    geom = MapGeom(name, game, disk)
    geom.source_path = str(path)
    return geom


# ---------------------------------------------------------------------------
# Street component


#: Two sky components joined by an indoor passage of at most this many
#: sectors count as one street network (TEDE1M2's streets join through
#: arcades and gate rooms; the single-component assumption fragmented it).
INDOOR_LINK_HOPS = 3


def _full_walk_adjacency(geom: MapGeom) -> dict[int, set[int]]:
    """Optimistic traversability for the reachability screen.

    A door or lift sector passes regardless of its resting gap and rise (a
    z-motion floor travels), and Blood link pairs (stacks, water, plain
    links) are edges: the point of the screen is "could the player ever be
    here", so mechanisms count as open.  A pessimistic model discarded
    E3M2's town as a scene because its approach runs through a lift.
    """
    pass_gap = geom.profile.crouch_height or int(geom.profile.standing_height * 0.75)
    adjacency: dict[int, set[int]] = defaultdict(set)
    for s in range(len(geom.sectors)):
        for w in geom.sector_walls[s]:
            o = int(geom.walls[w].fields["next_sector"])
            if o < 0:
                continue
            doored = geom.is_door_sector(o) or geom.is_door_sector(s)
            if (geom.gap(s, o) >= pass_gap or doored) \
                    and (doored or abs(geom.rise(s, o)) <= geom.profile.max_step):
                adjacency[s].add(o)
                adjacency[o].add(s)
    if geom.game == "blood":
        for row in observe_stacks(geom.name, geom.disk):
            upper, lower = row.get("upper_sector"), row.get("lower_sector")
            if row.get("paired") and upper is not None and lower is not None:
                adjacency[upper].add(lower)
                adjacency[lower].add(upper)
    return adjacency


def street_component(geom: MapGeom) -> set[int]:
    """The urban at-grade walkable street network of sky-ceiling sectors.

    Three screening rules, each bought by a mis-read (owner verification,
    2026-08-27):

    * Largest-by-area is the wrong pick: DWE3M1's biggest sky component is
      the landscape around the town.  The component with the most
      street-to-interior doorways wins; area breaks ties.  (Loops without
      doorways are landscape -- the wilderness set had loops galore and
      nothing to enter.)
    * Sky components joined through short indoor links (arcades, gates --
      at most INDOOR_LINK_HOPS interior sectors) are one network: TEDE1M2's
      square detected alone while its streets hung off arcades.
    * A component the player cannot reach on foot from the start is a
      *scene*, not a street: E2M1's window-backdrop street would otherwise
      screen as urbanism.  Unreachable components are recorded on the geom
      as ``scene_components`` for the backdrop-urbanism pattern.
    """
    max_step = geom.profile.max_step
    adjacency: dict[int, set[int]] = defaultdict(set)
    outdoor = [i for i in range(len(geom.sectors)) if geom.parallax[i]]
    outdoor_set = set(outdoor)
    for sector_id in outdoor:
        for w in geom.sector_walls[sector_id]:
            other = int(geom.walls[w].fields["next_sector"])
            if other < 0 or other not in outdoor_set:
                continue
            if abs(geom.rise(sector_id, other)) <= max_step:
                adjacency[sector_id].add(other)
                adjacency[other].add(sector_id)
    seen: set[int] = set()
    components: list[set[int]] = []
    for start in outdoor:
        if start in seen:
            continue
        component = {start}
        queue = deque([start])
        seen.add(start)
        while queue:
            current = queue.popleft()
            for other in adjacency[current]:
                if other not in seen:
                    seen.add(other)
                    component.add(other)
                    queue.append(other)
        components.append(component)
    if not components:
        return set()

    # Merge components joined through short indoor links.
    walk = _full_walk_adjacency(geom)
    comp_of = {s: i for i, c in enumerate(components) for s in c}
    parent = list(range(len(components)))

    def find(i):
        while parent[i] != i:
            parent[i] = parent[parent[i]]
            i = parent[i]
        return i

    for index, component in enumerate(components):
        frontier = {(s, 0) for s in component}
        visited = set(component)
        queue = deque(frontier)
        while queue:
            current, hops = queue.popleft()
            if hops >= INDOOR_LINK_HOPS:
                continue
            for other in walk[current]:
                if other in visited:
                    continue
                visited.add(other)
                if other in comp_of:
                    a, b = find(index), find(comp_of[other])
                    if a != b:
                        parent[b] = a
                elif other not in outdoor_set:
                    queue.append((other, hops + 1))
    merged: dict[int, set[int]] = defaultdict(set)
    for index, component in enumerate(components):
        merged[find(index)] |= component
    networks = sorted(merged.values(), key=lambda c: -sum(geom.area[s] for s in c))
    geom.street_networks_merged = len(components) - len(networks)

    # A network the player cannot reach on foot is a scene, not a street.
    header = geom.disk.header
    header_fields = header.fields if hasattr(header, "fields") else header
    start_sector = int(header_fields.get("start_sector", -1))
    # Reachability is directed: a drop of any height is passable downward
    # (E3M2's town is entered over its wall), a climb only within max_step.
    pass_gap = geom.profile.crouch_height or int(geom.profile.standing_height * 0.75)
    directed: dict[int, set[int]] = defaultdict(set)
    for s in range(len(geom.sectors)):
        for w in geom.sector_walls[s]:
            o = int(geom.walls[w].fields["next_sector"])
            if o < 0:
                continue
            doored = geom.is_door_sector(o) or geom.is_door_sector(s)
            if geom.gap(s, o) >= pass_gap or doored:
                if doored or geom.rise(s, o) <= geom.profile.max_step:
                    directed[s].add(o)
                if doored or geom.rise(o, s) <= geom.profile.max_step:
                    directed[o].add(s)
    if geom.game == "blood":
        for row in observe_stacks(geom.name, geom.disk):
            upper, lower = row.get("upper_sector"), row.get("lower_sector")
            if row.get("paired") and upper is not None and lower is not None:
                directed[upper].add(lower)
                directed[lower].add(upper)
    reachable: set[int] = set()
    if 0 <= start_sector < len(geom.sectors):
        reachable = {start_sector}
        queue = deque([start_sector])
        while queue:
            current = queue.popleft()
            for other in directed[current]:
                if other not in reachable:
                    reachable.add(other)
                    queue.append(other)
    candidates = [c for c in networks if not reachable or c & reachable]
    geom.scene_components = [c for c in networks if reachable and not c & reachable]
    if not candidates:
        candidates = networks
        geom.scene_note = "no network reachable from start; reachability check waived"

    def urban_score(component: set[int]) -> tuple[int, float]:
        _parts, membership = indoor_components(geom, component)
        return (len(doorways(geom, component, membership)),
                sum(geom.area[s] for s in component))

    return max(candidates[:10], key=urban_score)


# ---------------------------------------------------------------------------
# Raster


class StreetRaster:
    def __init__(self, geom: MapGeom, street: set[int]):
        xs: list[int] = []
        ys: list[int] = []
        for sector_id in street:
            for w in geom.sector_walls[sector_id]:
                x, y = geom.wall_xy(w)
                xs.append(x)
                ys.append(y)
        self.x0 = (min(xs) // CELL - 2) * CELL
        self.y0 = (min(ys) // CELL - 2) * CELL
        self.nx = (max(xs) - self.x0) // CELL + 4
        self.ny = (max(ys) - self.y0) // CELL + 4
        self.mask = np.zeros((self.ny, self.nx), dtype=bool)
        for sector_id in street:
            self._fill(geom, sector_id)

    def _fill(self, geom: MapGeom, sector_id: int) -> None:
        segments = [geom.wall_segment(w) for w in geom.sector_walls[sector_id]]
        bx0 = min(p[0][0] for p in segments)
        bx1 = max(p[0][0] for p in segments)
        by0 = min(p[0][1] for p in segments)
        by1 = max(p[0][1] for p in segments)
        c0 = max(0, (bx0 - self.x0) // CELL)
        c1 = min(self.nx - 1, (bx1 - self.x0) // CELL + 1)
        r0 = max(0, (by0 - self.y0) // CELL)
        r1 = min(self.ny - 1, (by1 - self.y0) // CELL + 1)
        if c1 < c0 or r1 < r0:
            return
        xc = self.x0 + (np.arange(c0, c1 + 1) + 0.5) * CELL
        yc = self.y0 + (np.arange(r0, r1 + 1) + 0.5) * CELL
        grid_x, grid_y = np.meshgrid(xc, yc)
        inside = np.zeros(grid_x.shape, dtype=bool)
        # Even-odd over every wall of the sector; the hole loops flip parity
        # back out, which is exactly what makes carved building masses count
        # as "not street" without any explicit loop bookkeeping.
        for (x1, y1), (x2, y2) in segments:
            if y1 == y2:
                continue
            crosses = (y1 <= grid_y) != (y2 <= grid_y)
            x_at = x1 + (grid_y - y1) * (x2 - x1) / (y2 - y1)
            inside ^= crosses & (grid_x < x_at)
        self.mask[r0:r1 + 1, c0:c1 + 1] |= inside

    def cell(self, x: float, y: float) -> tuple[int, int]:
        return int((y - self.y0) // CELL), int((x - self.x0) // CELL)

    def is_street(self, x: float, y: float) -> bool:
        r, c = self.cell(x, y)
        return 0 <= r < self.ny and 0 <= c < self.nx and bool(self.mask[r, c])

    def enclosed_components(self) -> list[dict[str, Any]]:
        """Enclosed non-street regions: the city blocks the street loops around."""
        labels = np.zeros(self.mask.shape, dtype=np.int32)
        current = 0
        components: list[dict[str, Any]] = []
        open_cells = ~self.mask
        for r in range(self.ny):
            for c in range(self.nx):
                if not open_cells[r, c] or labels[r, c]:
                    continue
                current += 1
                touches_border = False
                touches_street = False
                cells: list[tuple[int, int]] = []
                queue = deque([(r, c)])
                labels[r, c] = current
                while queue:
                    cr, cc = queue.popleft()
                    cells.append((cr, cc))
                    if cr in (0, self.ny - 1) or cc in (0, self.nx - 1):
                        touches_border = True
                    for dr, dc in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                        nr, nc = cr + dr, cc + dc
                        if not (0 <= nr < self.ny and 0 <= nc < self.nx):
                            continue
                        if self.mask[nr, nc]:
                            touches_street = True
                            continue
                        if not labels[nr, nc]:
                            labels[nr, nc] = current
                            queue.append((nr, nc))
                if touches_border or not touches_street:
                    continue
                rows = [cell[0] for cell in cells]
                cols = [cell[1] for cell in cells]
                components.append({
                    "label": current,
                    "area": len(cells) * CELL * CELL,
                    "bbox_units": [
                        (max(cols) - min(cols) + 1) * CELL,
                        (max(rows) - min(rows) + 1) * CELL,
                    ],
                    "centroid": [
                        self.x0 + (min(cols) + max(cols) + 1) / 2 * CELL,
                        self.y0 + (min(rows) + max(rows) + 1) / 2 * CELL,
                    ],
                })
        self.labels = labels
        return components

    def component_at(self, x: float, y: float) -> int:
        r, c = self.cell(x, y)
        if 0 <= r < self.ny and 0 <= c < self.nx:
            return int(self.labels[r, c])
        return 0


# ---------------------------------------------------------------------------
# Streets: widths and canyon sections


def boundary_walls(geom: MapGeom, street: set[int]) -> list[int]:
    out = []
    for sector_id in street:
        for w in geom.sector_walls[sector_id]:
            other = int(geom.walls[w].fields["next_sector"])
            if other < 0 or other not in street:
                out.append(w)
    return out


def street_sections(geom: MapGeom, street: set[int], raster: StreetRaster) -> list[dict[str, Any]]:
    """Width + facade-height samples along the street boundary."""
    samples: list[dict[str, Any]] = []
    for w in boundary_walls(geom, street):
        (x1, y1), (x2, y2) = geom.wall_segment(w)
        length = math.hypot(x2 - x1, y2 - y1)
        if length < CELL:
            continue
        sector_id = geom.wall_owner[w]
        other = int(geom.walls[w].fields["next_sector"])
        # Facade face height in z units, as drawn on the street side.
        if other < 0:
            face = geom.floor_z[sector_id] - geom.ceiling_z[sector_id]
            face_kind = "sky_bounded"
        else:
            rise = geom.rise(sector_id, other)
            if rise <= 0:
                continue  # drop-offs and sunken lots are not facades
            face = rise
            face_kind = "raised_mass"
        nx, ny = (y2 - y1) / length, -(x2 - x1) / length
        count = max(1, int(length // BOUNDARY_SAMPLE_STEP))
        for step in range(count):
            t = (step + 0.5) / count
            px, py = x1 + (x2 - x1) * t, y1 + (y2 - y1) * t
            direction = None
            for sign in (1.0, -1.0):
                if raster.is_street(px + nx * sign * CELL, py + ny * sign * CELL):
                    direction = sign
                    break
            if direction is None:
                continue
            distance = CELL
            while distance < MAX_RAY and raster.is_street(
                    px + nx * direction * distance, py + ny * direction * distance):
                distance += CELL
            if distance >= MAX_RAY:
                continue
            samples.append({
                "wall": w,
                "sector": sector_id,
                "width": distance,
                "face_z": face,
                "face_kind": face_kind,
                "canyon_ratio": round((face / Z_PER_XY) / distance, 3),
            })
    return samples


# ---------------------------------------------------------------------------
# Interiors and enterable share


def indoor_components(geom: MapGeom, street: set[int]) -> tuple[list[set[int]], dict[int, int]]:
    indoor = {
        i for i in range(len(geom.sectors))
        if i not in street
    }
    crouch = geom.profile.crouch_height or int(geom.profile.standing_height * 0.75)
    adjacency: dict[int, set[int]] = defaultdict(set)
    for sector_id in indoor:
        for w in geom.sector_walls[sector_id]:
            other = int(geom.walls[w].fields["next_sector"])
            if other < 0 or other not in indoor:
                continue
            if geom.gap(sector_id, other) >= crouch or geom.is_door_sector(other) \
                    or geom.is_door_sector(sector_id):
                adjacency[sector_id].add(other)
                adjacency[other].add(sector_id)
    seen: set[int] = set()
    components: list[set[int]] = []
    membership: dict[int, int] = {}
    for start in indoor:
        if start in seen:
            continue
        component = {start}
        seen.add(start)
        queue = deque([start])
        while queue:
            current = queue.popleft()
            for other in adjacency[current]:
                if other not in seen:
                    seen.add(other)
                    component.add(other)
                    queue.append(other)
        for member in component:
            membership[member] = len(components)
        components.append(component)
    return components, membership


def doorways(geom: MapGeom, street: set[int], membership: dict[int, int]) -> list[dict[str, Any]]:
    crouch = geom.profile.crouch_height or int(geom.profile.standing_height * 0.75)
    out = []
    for sector_id in street:
        for w in geom.sector_walls[sector_id]:
            other = int(geom.walls[w].fields["next_sector"])
            if other < 0 or other in street or geom.parallax[other]:
                continue
            width = geom.wall_length(w)
            if width < geom.profile.min_passage_width:
                continue
            gap = geom.gap(sector_id, other)
            doored = geom.is_door_sector(other)
            if gap < crouch and not doored:
                continue
            out.append({
                "wall": w,
                "street_sector": sector_id,
                "into_sector": other,
                "interior_component": membership.get(other),
                "width": round(width),
                "gap_z": gap,
                "via_door_sector": doored,
            })
    return out


# ---------------------------------------------------------------------------
# Facade articulation


def facade_metrics(geom: MapGeom, street: set[int], raster: StreetRaster) -> dict[str, Any]:
    walls = boundary_walls(geom, street)
    total_length = sum(geom.wall_length(w) for w in walls)
    if not total_length:
        return {}
    vertex_count = len(walls)
    masked_windows = 0
    red_openings = 0
    for w in walls:
        f = geom.walls[w].fields
        other = int(f["next_sector"])
        if other >= 0 and int(f.get("over_picnum", 0)) > 0 and int(f["cstat"]) & 16:
            masked_windows += 1
        elif other >= 0 and not geom.parallax[other] \
                and geom.gap(geom.wall_owner[w], other) > 0:
            red_openings += 1
    # Wall-aligned sprites standing in street sectors: signage, decals, lamps
    # bolted to facades.  cstat bits 4-5: 16 = wall aligned.
    wall_sprites = 0
    face_sprites = 0
    for sprite in geom.sprites:
        sector_id = int(sprite.fields["sector"])
        if sector_id not in street:
            continue
        alignment = int(sprite.fields["cstat"]) & 48
        if alignment == 16:
            wall_sprites += 1
        elif alignment == 0:
            face_sprites += 1
    per_kilounit = 1024.0 / total_length
    return {
        "facade_length_units": round(total_length),
        "boundary_walls": vertex_count,
        "walls_per_1024": round(vertex_count * per_kilounit, 2),
        "masked_windows": masked_windows,
        "masked_windows_per_1024": round(masked_windows * per_kilounit, 3),
        "red_wall_openings": red_openings,
        "red_wall_openings_per_1024": round(red_openings * per_kilounit, 3),
        "wall_sprites_in_street": wall_sprites,
        "wall_sprites_per_1024": round(wall_sprites * per_kilounit, 3),
        "face_sprites_in_street": face_sprites,
    }


# ---------------------------------------------------------------------------
# Verticality


def _near_street_mask(raster: StreetRaster, reach_units: int) -> np.ndarray:
    reach = max(1, reach_units // CELL)
    near = raster.mask.copy()
    for _ in range(reach):
        grown = near.copy()
        grown[1:, :] |= near[:-1, :]
        grown[:-1, :] |= near[1:, :]
        grown[:, 1:] |= near[:, :-1]
        grown[:, :-1] |= near[:, 1:]
        near = grown
    return near


def skyline(geom: MapGeom, street: set[int], grade: float,
            raster: StreetRaster) -> dict[str, Any]:
    """Roof heights above street grade, area-weighted.

    A building's visible height is the floor of its roof/ledge sector, not the
    street sector's sky ceiling -- an at-grade interior behind a facade leaves
    no trace in the canyon-ratio samples, but its roof sector does here.
    Restricted to masses within 2048 units of the street so canyon rims and
    remote areas stay out of the census.
    """
    near = _near_street_mask(raster, 2048)
    standing = geom.profile.standing_height
    heights: list[float] = []
    weights: list[float] = []
    for i in range(len(geom.sectors)):
        if i in street:
            continue
        points = [geom.wall_xy(w) for w in geom.sector_walls[i]]
        cx = sum(p[0] for p in points) / len(points)
        cy = sum(p[1] for p in points) / len(points)
        r, c = raster.cell(cx, cy)
        if not (0 <= r < raster.ny and 0 <= c < raster.nx and near[r, c]):
            continue
        rise = grade - geom.floor_z[i]
        if rise > standing:
            heights.append(rise / Z_PER_XY)
            weights.append(geom.area[i])
    if not heights:
        return {"roof_sectors": 0}
    order = sorted(range(len(heights)), key=lambda k: heights[k])
    total = sum(weights)
    cumulative = 0.0
    weighted_median = heights[order[-1]]
    for k in order:
        cumulative += weights[k]
        if cumulative >= total / 2:
            weighted_median = heights[k]
            break
    return {
        "roof_sectors": len(heights),
        "height_xy_units": _percentiles(heights, 0),
        "area_weighted_median_xy": round(weighted_median),
        "tallest_xy": round(max(heights)),
        "tallest_in_standing_heights": round(
            max(heights) * Z_PER_XY / geom.profile.standing_height, 1),
    }


def verticality(geom: MapGeom, street: set[int], raster: StreetRaster) -> dict[str, Any]:
    street_floors = [geom.floor_z[s] for s in street]
    grade = statistics.median(street_floors)
    standing = geom.profile.standing_height
    rooftops = []
    perched = []
    below = []
    for i in range(len(geom.sectors)):
        if i in street:
            continue
        rise = grade - geom.floor_z[i]
        if geom.parallax[i]:
            if rise > 2 * standing:
                rooftops.append(i)
            elif rise > standing and geom.area[i] < 1024 * 1024 * 4:
                perched.append(i)
        elif rise < -standing:
            below.append(i)
    stacks: list[dict[str, Any]] = []
    if geom.game == "blood":
        stacks = observe_stacks(geom.name, geom.disk)
    return {
        "skyline": skyline(geom, street, grade, raster),
        "street_grade_z_median": grade,
        "street_grade_z_spread": _percentiles([float(z) for z in street_floors], 0),
        "rooftop_sky_sectors": len(rooftops),
        "rooftop_area_share_of_street": round(
            sum(geom.area[i] for i in rooftops) / max(1.0, sum(geom.area[s] for s in street)), 3),
        "perched_outdoor_sectors": len(perched),
        "below_grade_sectors": len(below),
        "below_grade_area": round(sum(geom.area[i] for i in below)),
        "stack_pairs": [
            {k: row[k] for k in ("family", "paired", "congruent", "overlaps_in_plan",
                                 "upper_sector", "lower_sector")
             if k in row}
            for row in stacks
        ],
    }


# ---------------------------------------------------------------------------
# Districts (art: Blood sources only)


def street_zones(geom: MapGeom, street: set[int]) -> list[set[int]]:
    """Street sectors merged by floor material over adjacency: the seams the
    palette itself draws.  Derived clustering; the 'district' reading of a
    zone is interpretation.  Sorted largest-area first."""
    label = {
        s: (int(geom.sectors[s].fields["floor_picnum"]),
            int(geom.sectors[s].fields["floor_pal"]))
        for s in street
    }
    seen: set[int] = set()
    zones = []
    for start in street:
        if start in seen:
            continue
        zone = {start}
        seen.add(start)
        queue = deque([start])
        while queue:
            current = queue.popleft()
            for w in geom.sector_walls[current]:
                other = int(geom.walls[w].fields["next_sector"])
                if other in street and other not in seen and label[other] == label[start]:
                    seen.add(other)
                    zone.add(other)
                    queue.append(other)
        zones.append(zone)
    zones.sort(key=lambda z: -sum(geom.area[s] for s in z))
    return zones


def district_zones(geom: MapGeom, street: set[int]) -> list[dict[str, Any]]:
    out = []
    for zone in street_zones(geom, street):
        area = sum(geom.area[s] for s in zone)
        if area < MIN_BLOCK_AREA:
            continue
        sample = next(iter(zone))
        shades = [int(geom.sectors[s].fields["floor_shade"]) for s in zone]
        ceilings = [geom.floor_z[s] - geom.ceiling_z[s] for s in zone]
        facade_picnums = Counter()
        facade_shades = []
        for s in zone:
            for w in geom.sector_walls[s]:
                other = int(geom.walls[w].fields["next_sector"])
                if other < 0 or other not in street:
                    facade_picnums[int(geom.walls[w].fields["picnum"])] += 1
                    facade_shades.append(float(geom.walls[w].fields["shade"]))
        out.append({
            "sectors": len(zone),
            "sector_ids": sorted(zone)[:12],
            "area": round(area),
            "floor_picnum": int(geom.sectors[sample].fields["floor_picnum"]),
            "floor_pal": int(geom.sectors[sample].fields["floor_pal"]),
            "floor_shade": _percentiles([float(v) for v in shades], 0),
            "sky_height_z": _percentiles([float(v) for v in ceilings], 0),
            "facade_wall_picnums_top5": facade_picnums.most_common(5),
            "facade_wall_shade": _percentiles(facade_shades, 0),
        })
    return out


def budget_partition(geom: MapGeom, street: set[int]) -> list[dict[str, Any]]:
    """Sectors, walls, and sprites attributed to district-sized chunks.

    Every sector joins the nearest street zone by breadth-first search over
    red-wall adjacency, so an interior spends its budget in the district whose
    street it opens onto.  Walls count by owning sector, sprites by containing
    sector: the two totals reconcile with the map's own.
    """
    zones = street_zones(geom, street)
    assignment: dict[int, int] = {}
    queue: deque[int] = deque()
    for index, zone in enumerate(zones):
        for s in zone:
            assignment[s] = index
            queue.append(s)
    while queue:
        current = queue.popleft()
        for w in geom.sector_walls[current]:
            other = int(geom.walls[w].fields["next_sector"])
            if other >= 0 and other not in assignment:
                assignment[other] = assignment[current]
                queue.append(other)
    sprites_by_sector = Counter(int(s.fields["sector"]) for s in geom.sprites)
    chunks: dict[int, dict[str, int]] = defaultdict(lambda: {"sectors": 0, "walls": 0, "sprites": 0})
    unattributed = {"sectors": 0, "walls": 0, "sprites": 0}
    for sector_id in range(len(geom.sectors)):
        target = chunks[assignment[sector_id]] if sector_id in assignment else unattributed
        target["sectors"] += 1
        target["walls"] += len(geom.sector_walls[sector_id])
        target["sprites"] += sprites_by_sector.get(sector_id, 0)
    out = []
    for index, spend in sorted(chunks.items()):
        zone = zones[index]
        sample = next(iter(zone))
        record = {"zone": index,
                  "zone_floor_picnum": int(geom.sectors[sample].fields["floor_picnum"]),
                  "street_sectors": len(zone)}
        record.update(spend)
        out.append(record)
    out.sort(key=lambda r: -r["walls"])
    if any(unattributed.values()):
        out.append({"zone": None, "note": "not reachable from any street", **unattributed})
    return out


# ---------------------------------------------------------------------------
# Per-map orchestration


def analyze(geom: MapGeom) -> dict[str, Any]:
    street = street_component(geom)
    raster = StreetRaster(geom, street)
    blocks = raster.enclosed_components()
    real_blocks = [b for b in blocks if b["area"] >= MIN_BLOCK_AREA]
    sections = street_sections(geom, street, raster)
    interiors, membership = indoor_components(geom, street)
    doors = doorways(geom, street, membership)

    # Attribute each doorway to the raster block it opens out of: sample just
    # outside the street on the wall's far side.
    for door in doors:
        (x1, y1), (x2, y2) = geom.wall_segment(door["wall"])
        mx, my = (x1 + x2) / 2, (y1 + y2) / 2
        length = math.hypot(x2 - x1, y2 - y1) or 1.0
        nx, ny = (y2 - y1) / length, -(x2 - x1) / length
        block = 0
        for sign in (1.0, -1.0):
            candidate = raster.component_at(mx + nx * sign * CELL * 1.5,
                                            my + ny * sign * CELL * 1.5)
            if candidate:
                block = candidate
                break
        door["block_label"] = block or None

    interior_stats = []
    entered = set()
    for door in doors:
        component = door["interior_component"]
        if component is not None:
            entered.add(component)
    for index in sorted(entered):
        component = interiors[index]
        area = sum(geom.area[s] for s in component)
        interior_stats.append({
            "interior_component": index,
            "sectors": len(component),
            "area": round(area),
            "substantial": area >= MIN_INTERIOR_AREA,
        })

    block_labels = {b["label"] for b in real_blocks}
    entered_blocks = set()
    for door in doors:
        component = door["interior_component"]
        substantial = component is not None and sum(
            geom.area[s] for s in interiors[component]) >= MIN_INTERIOR_AREA
        if door["block_label"] in block_labels and substantial:
            entered_blocks.add(door["block_label"])

    # Rates, not counts: the block census collapses where the street network
    # does not enclose its buildings (Blood towns), so enterability is also
    # expressed per unit of street frontage.
    frontage = sum(geom.wall_length(w) for w in boundary_walls(geom, street))
    substantial_entered = sum(1 for i in interior_stats if i["substantial"])

    widths = [float(s["width"]) for s in sections]
    canyon = [s["canyon_ratio"] for s in sections if s["face_z"] > geom.profile.standing_height]
    street_area = sum(geom.area[s] for s in street)

    record: dict[str, Any] = {
        "map": geom.name,
        "game": geom.game,
        "budget": {
            "sectors": len(geom.sectors),
            "walls": len(geom.walls),
            "sprites": len(geom.sprites),
        },
        "street": {
            "sectors": len(street),
            "area": round(street_area),
            "area_share_of_map": round(street_area / max(1.0, sum(geom.area)), 3),
            "width_units": _percentiles(widths, 0),
            "width_player_widths": _percentiles(
                [w / geom.profile.body_width for w in widths], 1),
            "canyon_ratio": _percentiles([float(c) for c in canyon], 2),
            "samples": len(sections),
        },
        "street_detection": {
            "indoor_link_merged": getattr(geom, "street_networks_merged", 0),
            "scene_sky_components": [
                {"sectors": len(c), "area": round(sum(geom.area[s] for s in c)),
                 "sample": sorted(c)[:6]}
                for c in getattr(geom, "scene_components", [])
            ],
            "note": getattr(geom, "scene_note", None),
        },
        "blocks": {
            "enclosed_walkaround_blocks": len(real_blocks),
            "street_loop_count": len(real_blocks),
            #: The screening rule from the rejected wilderness set: an
            #: obstacle you can circle is not a block unless something opens
            #: onto it.  Raw counts stay (a massing-stage candidate has no
            #: doorways yet); screening reads the fronted numbers.
            "blocks_fronted": len({d["block_label"] for d in doors
                                   if d.get("block_label")}
                                  & {b["label"] for b in real_blocks}),
            "block_extent_units": _percentiles(
                [float(max(b["bbox_units"])) for b in real_blocks], 0),
            "block_area": _percentiles([float(b["area"]) for b in real_blocks], 0),
            "sub_block_obstacles": len(blocks) - len(real_blocks),
            "blocks_detail": real_blocks,
        },
        "enterability": {
            "doorways_from_street": len(doors),
            "interior_components_entered": len(entered),
            "substantial_interiors_entered": sum(1 for i in interior_stats if i["substantial"]),
            "blocks_total": len(real_blocks),
            "blocks_enterable": len(entered_blocks),
            "enterable_block_share": round(len(entered_blocks) / len(real_blocks), 3)
            if real_blocks else None,
            "doorways_per_10240_frontage": round(len(doors) / max(1.0, frontage) * 10240, 2),
            "substantial_interiors_per_10240_frontage": round(
                substantial_entered / max(1.0, frontage) * 10240, 2),
            "interior_area_per_entered_component": _percentiles(
                [float(i["area"]) for i in interior_stats], 0),
            "doorway_records": doors,
            "interior_records": interior_stats,
        },
        "facade": facade_metrics(geom, street, raster),
        "verticality": verticality(geom, street, raster),
        "budget_per_chunk": budget_partition(geom, street),
    }
    if geom.name in ART_SOURCE_NAMES:
        record["districts_art"] = district_zones(geom, street)
    if geom.game == "blood" and getattr(geom, "source_path", None):
        record["mechanisms"] = observe_channels(pathlib.Path(geom.source_path))
    return record


# ---------------------------------------------------------------------------


def summarize(records: list[dict[str, Any]]) -> dict[str, Any]:
    def pool(path: list[str], key: str) -> dict[str, Any]:
        per_map = {}
        for record in records:
            node: Any = record
            for part in path:
                node = node.get(part, {})
            if key in node:
                per_map[record["map"]] = node[key]
        return per_map

    return {
        "street_width_player_widths": pool(["street"], "width_player_widths"),
        "canyon_ratio": pool(["street"], "canyon_ratio"),
        "street_loops": pool(["blocks"], "street_loop_count"),
        "block_extent_units": pool(["blocks"], "block_extent_units"),
        "enterable_block_share": pool(["enterability"], "enterable_block_share"),
        "doorways_per_10240_frontage": pool(["enterability"], "doorways_per_10240_frontage"),
        "substantial_interiors_per_10240_frontage": pool(
            ["enterability"], "substantial_interiors_per_10240_frontage"),
        "skyline_height_xy": pool(["verticality", "skyline"], "height_xy_units"),
        "skyline_area_weighted_median_xy": pool(
            ["verticality", "skyline"], "area_weighted_median_xy"),
        "facade_walls_per_1024": pool(["facade"], "walls_per_1024"),
        "wall_sprites_per_1024": pool(["facade"], "wall_sprites_per_1024"),
        "budgets": {r["map"]: r["budget"] for r in records},
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("-o", "--output", default="projects/blood-city/references/city-norms.json")
    parser.add_argument("--maps", nargs="*", help="restrict to these map names")
    parser.add_argument("--input", action="append", default=[],
                        help="extra map as NAME=GAME=PATH (e.g. a compiled "
                             "candidate, so a plan can be read the way the "
                             "precedents were read)")
    args = parser.parse_args(argv)

    sources = [s for s in STRUCTURE_SOURCES
               if not args.maps or s[0] in args.maps]
    for item in args.input:
        name, game, path = item.split("=", 2)
        sources.append((name, game, path))

    records = []
    for name, game, path in sources:
        geom = load_source(name, game, path)
        records.append(analyze(geom))
        print(f"{name}: {records[-1]['budget']} street={records[-1]['street']['sectors']}")

    payload = {
        "$schema": SCHEMA,
        "schema_version": SCHEMA_VERSION,
        "scope": {
            "structure_sources": [n for n, _g, _p in STRUCTURE_SOURCES],
            "art_sources": sorted(ART_SOURCE_NAMES),
            "method": __doc__,
            "thresholds": {
                "cell": CELL,
                "min_block_area": MIN_BLOCK_AREA,
                "min_interior_area": MIN_INTERIOR_AREA,
                "z_per_xy": Z_PER_XY,
                "duke_door_lotags": sorted(DUKE_DOOR_LOTAGS),
            },
        },
        "per_map": records,
        "summary": summarize(records),
    }
    out = pathlib.Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(f"wrote {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
