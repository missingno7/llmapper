# Deterministic fragment composition

Composition appends a verified `LevelFragment` to an existing `LevelIR`. It is
deliberately allocation-oriented: it does not infer gameplay design, automatically
join geometry, or hide unresolved source relationships.

```python
result = destination.insert(
    fragment,
    dx=4096,
    dy=-2048,
    quarter_turns=1,
    channel_policy="remap",
)
composed = result.level
report = result.report()
```

## Allocation contract

Each insertion appends sectors, walls, and sprites and returns explicit
fragment-to-destination maps. XSECTOR, XWALL, and XSPRITE indices are assigned the
lowest free positive ID in their independent namespaces. Owner/reference, marker,
portal, and sprite links that are internal to the fragment are remapped through
those allocations.

The v7 limits (1,024 sectors, 8,192 walls, 4,096 sprites) are checked before any
result is returned.

## Channel policy

Blood channels are not ordinary array indices.

- Verified system/global channels retain their source-defined IDs.
- Undefined values below 100 are never guessed or automatically remapped. A
  collision fails closed.
- User channels 100–1023 remain unchanged when free.
- A user-channel collision either raises (`error`, the default) or receives the
  lowest free user channel (`remap`). TX and RX fields inside the fragment use the
  same deterministic map.

External fragment dependencies remain visible in `CompositionResult`; insertion
does not claim they were resolved merely because the output is structurally valid.

## Placement

Insertion supports integer X/Y/Z translation and quarter-turn rotation around an
explicit pivot. Only the same verified world-space coordinates and direction fields
used by whole-map transforms are touched.

## Explicit portal connection

```python
connected = composed.connect_portals(wall_a, wall_b)
```

Both walls must be one-sided, belong to different sectors, and have exactly
coincident reversed endpoints. The operation creates reciprocal `next_wall` and
`next_sector` links, then runs structural validation. It never searches for or
chooses connectors automatically.

## Automatic room attachment

`LevelIR.attach` combines placement, insertion, and portal connection. The caller
selects one one-sided wall in the destination and one fragment-local one-sided wall:

```python
result = destination.attach(
    room,
    destination_wall=120,
    fragment_wall=3,
    channel_policy="remap",
)
attached = result.level
```

The walls must have equal nonzero lengths. Unless a turn is forced, the operation
tries 0, 1, 2, and 3 quarter-turns and chooses the first exact reversed alignment.
It then calculates the required X/Y translation, applies an explicit Z offset,
inserts the room through the normal deterministic allocator, and connects the
allocated wall pair. Selecting different fragment walls gives different room
orientations and connections without hand-calculating coordinates.

Movement-blocking wall flags and vertically closed openings fail closed by default.
Callers may explicitly clear the blocking bit for a normal doorway or retain a
blocked/closed portal for a door mechanism. At-rest clearance is evaluated at both
portal endpoints with Blood's source-derived sloped-sector arithmetic. The report
records placement, allocation, channel mapping, portal IDs, endpoint clearance,
and the external portal dependency resolved by the new connection.

```text
python -m bloodmap attach destination.MAP room.json \
  --destination-wall 120 --fragment-wall 3 \
  --channel-policy remap --clear-blocking \
  --report work/attachment.json -o work/attached.MAP
```

Attachment requires exact equal-length walls. New-vs-existing segment crossings,
collinear overlaps, and polygon containment fail closed; intentional stacked XY
geometry requires an explicit override and remains visible in the report.

## Behavior-closed room extraction

`LevelIR.extract_closed()` starts from requested sectors and recursively includes
the sectors owning external trigger endpoints, markers, sprite owners, targets,
and burn sources. NBlood/XMAPEDIT source rules distinguish authored modern-patrol
targets and active burn sources from ordinary AI runtime indices. The latter are
preserved byte-for-byte but do not pull unrelated sectors into behavior closure.
Portal adjacency is not followed: detached portals are useful
room boundaries, whereas following them would usually absorb the whole map.
Game-valid TX/RX channels with no matching endpoint remain explicitly unresolved.
A maximum-sector bound prevents an unexpectedly global mechanism from silently
turning into a huge fragment.

## Generated pathways and stairs

`LevelIR.connect_pathway()` connects any two free walls already present in a
level. Endpoint lengths may differ and the rooms need not be coincident. The
operation generates a strip of inert quadrilateral sectors, interpolates doorway
width and ceiling/floor height, and creates reciprocal portals throughout.

```python
result = level.connect_pathway(
    wall_a=2477,
    wall_b=2482,
    via=[(-20000, 70000)],
    max_step_height=2048,
    min_opening=8192,
)
```

The automatic sector count is large enough to keep every floor transition within
the requested maximum. Callers may add centerline waypoints or request more
sectors. Zero-width sections, insufficient vertical opening, over-height risers,
self-crossing strips, and intersections/containment against existing geometry all
fail closed. This permits corridors, tapered adapters, and stairs while keeping
room placement and routing explicit.

## Composition recipes

The `recipe` command replays a `bloodmap.composition-recipe` JSON document. Each
donor is extracted with gameplay closure. An operation ID exposes its allocation
map to later operations, allowing references such as:

```json
{"operation": "gallery", "fragment_wall": 8}
```

This removes brittle post-insertion wall arithmetic. Plain `insert` operations
also receive the same layout collision gate when run through a recipe.

A recipe can move the player into an inserted or attached room without calculating
destination coordinates. `set_player_start` accepts a source operation, a
fragment-local sector, and an X/Y/Z/angle expressed in the donor's original
coordinate system. The recipe applies that operation's translation and rotation,
then rejects positions outside the allocated sector or its vertical span.

```json
{
  "op": "set_player_start",
  "id": "remixed_start",
  "source_operation": "opening_room",
  "fragment_sector": 0,
  "x": -20864,
  "y": 44544,
  "z": -45056,
  "angle": 1280
}
```

## CLI

```text
python -m bloodmap compose destination.MAP fragment.json \
  --x 4096 --y -2048 --channel-policy remap \
  --report work/composition.json -o work/composed.MAP

python -m bloodmap connect work/composed.MAP \
  --wall-a 120 --wall-b 845 -o work/connected.MAP

python -m bloodmap attach destination.MAP fragment.json \
  --destination-wall 120 --fragment-wall 3 \
  --report work/attachment.json -o work/attached.MAP

python -m bloodmap pathway work/separated.MAP \
  --wall-a 120 --wall-b 845 --via 4096,8192 \
  --report work/pathway.json -o work/connected.MAP

python -m bloodmap recipe recipes/e1m2-crossroads.json \
  --source-dir maps/blood --report work/mashup.json -o work/e1m2-crossroads.MAP

python -m bloodmap recipe recipes/e1m2-remix.json \
  --source-dir maps/blood --report work/remix.json -o work/e1m2-remix.MAP
```

A deterministic independent-engine oracle now verifies that a decoupled wall-push
trigger, user-channel dispatch, and sector Z motion retain exact before/after views
after fragment insertion. See `docs/reference-oracles.md`. This focused scenario
does not yet make composition complete for arbitrary production use; additional
marker-, sprite-, and progression-driven behavior gates remain.
