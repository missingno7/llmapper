# Level programs

A level is a tree of named parts, each holding its own geometry, surfaces,
structures, details and connections, in its own coordinates.

```text
level          LevelProgram
  area         Assembly
    room       Room
      structure  staircase() / recess()
        detail   wall_detail() / floor_detail() / ceiling_detail()
```

`bloodmap.levelprog` is that tree. It is **not** a new IR: it lowers to
`PlanarLayout`, which lowers to `LevelIR`, which writes a MAP. Native sector,
wall and sprite ids stay exactly where they were, as compiler output.

```text
build_level()                       hierarchical Python you edit
    -> LevelProgram.compile()       resolves frames and inherited style
        -> PlanarLayout             flat regions, absolute coordinates
            -> LevelIR              exact native truth
                -> MAP
```

## What it is for

Three properties, and each is testable.

**Locality.** `build_lobby()` contains the lobby: its outline, its materials, its
niche, its lamps, and the faces it offers to neighbours. `room.summary()`
returns all of it. Reading one room does not require reading the level.

**Local coordinates.** A room's outline is written around its own origin. Frames
compose down the tree and the compiler resolves them once. Moving a parent moves
every child without changing a number in any child's source, and because a frame
is a translation on Build's integer grid that move is exact — no rounding
residual anywhere.

**Inspectable inheritance.** A parent supplies a `Style` and a child states only
what differs. `room.style_provenance()` returns every resolved value *and the
node that set it*:

```python
>>> wing.style_provenance()["wall_picnum"]
{'value': 5, 'from': 'fixture/manor'}
>>> wing.style.stated()
{'floor_picnum': 294, 'clear_height': 33792}
```

Inheritance that cannot be traced is just a hidden default, so every value
carries its origin.

## Faces instead of coordinates

A room names stretches of its own boundary, and two parts are joined by naming
faces rather than endpoints:

```python
wing.place_against("east", lobby.face("west", at=0.5, width=8 * U))
level.connect(lobby.face("west", at=0.5, width=8 * U),
              wing.face("east", at=0.5, width=8 * U))
```

`rect_room` names `north`, `east`, `south` and `west` automatically — in screen
space, so north is minimum y and a clockwise outer loop keeps the interior on the
left. `hole_face(index, name)` names the inward face of a carved hole, which is
where a building's only door meets the ground outside it.

`place_against` computes the frame that makes the two faces coincide. It is the
single thing that removes coordinate arithmetic from the source, and it is exact:
the shared edge comes out as an exact reversed coincidence, which is what
`PlanarLayout` pairs portals on.

## Structures and details belong to their owner

```python
stairs = lobby.staircase("stairs:grand", "east", at=0.5, width=6 * U,
                         total_rise=-rise, step_rise=-4096, tread=2 * U,
                         arrive_at=gallery.region_id, shade_ramp=(18, 10))
stairs.decorate(wall_detail("sconce", SCONCE, 0.9, face="flank", at=0.5))
```

The sconce is the stair's, not the level's. Adding or removing it touches one
call and changes one sprite; nothing else in the compiled MAP moves. The
constructors are `bloodmap.vocabulary`'s, so their corpus support travels with
them — see [the authoring vocabulary](authoring-loop.md).

## Shared semantics after lowering

Some reusable semantics operate on the lowered `PlanarLayout` because they need
the final connections or placements.  They are still source-level declarations,
not post-MAP tweaks: rooms declare light sources through `Room.light_source()`
or `emits_light=True`; the compiler applies LightBomb.  Door rooms declare their
native motion through `doors.z_motion_door()` in `region_kwargs`; a project then
runs `aperture.frame_z_doors()` before its final `layout.compile()` so the
compiler owns the reveal geometry and art-aligned leaf.  See the [shared
authoring toolkit](authoring-toolkit.md) for the complete routing rule.

## The escape hatch

`Room.raw(note, apply)` runs arbitrary work against the lowered `PlanarLayout`,
with a note that shows up in `room.summary()["raw_escapes"]`. It exists so an
unusual structure falls back to native work *with a label on it*, rather than
forcing a bad generic abstraction into the vocabulary. The nested authoring test
uses it for its exit switch, because the language has no mechanism vocabulary
yet and inventing one to avoid a single raw call would be the worse trade.

## Decompiling into a program

`tools.emit_level_program` turns an original MAP into one of these programs.

```bash
python -m tools.emit_level_program maps/blood/E2M3.MAP \
    --art-dir reference/blood \
    --names projects/e2m3-decompiled/references/names.json \
    --escape-until-compiles \
    -o projects/e2m3-decompiled/source/E2M3.py
```

The contrast with `bloodmap.decompiler.emit_python_source` is the point:

| | `emit_python_source` | `emit_level_program` |
| --- | --- | --- |
| E2M3 output | 138,008 lines, 8.4 MB | 5,606 lines, 257 KB |
| geometry | one embedded `LevelIR` literal | distributed to the part that owns it |
| coordinates | absolute | local to each part |
| editing a room | changes nothing | changes that room |
| sprites | one global list | under the room they stand in |

Neither is authoritative. `E2M3.MAP` is, and `provenance.json` says so.

Two things the emitter records rather than repairs:

* **`NATIVE_ESCAPES`** — sectors the authoring model cannot express, with the
  compiler's own words. Across the campaign, 133 of 14,079 sectors (0.95%) have
  outlines `validate_loop` refuses: zero-area loops, repeated vertices,
  self-touching outlines. Repairing them silently would invent evidence about
  what the designer drew.
* **`declare_stack`** — sector pairs the original overlaps in XY on purpose.
  Build has no XY exclusivity rule and originals rely on that; `PlanarLayout`
  requires the overlap to be declared, because in authored work an undeclared
  one is a bug. E2M3 needs 11 declarations.

E2M3's program builds all 339 non-escaped rooms and lowers cleanly to 339
`PlanarLayout` regions and 443 placements. Recompiling it from there stops on a
third class: two sectors traversing one shared edge in the *same* direction
rather than reversed. There are 15 such edges in the whole 43-map corpus, in 6
maps; E2M3 has 4. They are not repaired here, for the same reason as the
others.

## Limits

* Frames translate; they do not rotate. A rotated structure is written rotated.
* Mechanisms — doors, switches, keys, channels — have no vocabulary here yet and
  go through `raw`.
* `connect` needs the two faces to be collinear and overlapping. It reports what
  it got when they are not, but it will not move a room to make them fit.
* A face is a resource: two structures cannot grow from the same stretch of one.
