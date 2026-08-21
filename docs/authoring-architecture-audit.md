# Authoring architecture audit

What compiles a generated level today, which of it is real source, and what was
added so a level reads as an editable program.

## The paths that exist

There are two generation families in the repository, and only one of them is
authoring.

**1. `LevelBuilder` — direct native construction.**

```text
bloodmap/designs.py  build_first_puzzle_room()
bloodmap/e3l11.py    convert_e3l11()
    -> LevelBuilder.add_sector([(0, 0), (6144, 0), ...])
    -> builder.connect(wall_id_a, wall_id_b)
    -> LevelIR -> MAP
```

The author names sectors by the object `add_sector` returns and joins them by
**wall index**. `bloodmap/composition.py:generate_pathway` works at the same
level: it takes two wall ids on an already-compiled `LevelIR` and splices new
sectors in. This is post-compile surgery, not a source representation.

**2. `PlanarLayout` — planar authored source.**

```text
experiments/sp_progression_v1.py, sp_progression_v2.py
experiments/bb2_reconstruction_v3.py, bb6_reconstruction_v1.py
projects/reasoned-authoring-v1/level/candidate_v0..v5.py
    -> PlanarLayout.add_region / add_connection / add_partition / place_on_wall
    -> layout.compile()  (edge splitting, portal pairing, conservation)
    -> LevelIR -> MAP
```

This **is** a real compilable representation. Wall indices are output. Design
identity lives on region and connection ids. Editing the Python changes the
geometry. Every monastery iteration is authored this way.

## The decompiler's Python was presentation, not source

`bloodmap.decompiler.emit_python_source` produces exactly the shape the brief
warns about:

```python
_DOCUMENT = {... the entire exact LevelIR ...}
_SOURCE = LevelSource.from_dict(_DOCUMENT)

def build_space_001():
    node = _SOURCE.node('assembly:001/space:001')
    node['compiled_children'] = [...]
    return node
```

For E2M3 that file is **138,008 lines and 8.4 MB**, and 136,616 of those lines -- 99.0% of the file -- are the one `_DOCUMENT` literal. `build_space_001()` looks a
node up in the literal; editing it changes nothing, and the MAP is compiled from
`exact_level_ir` alone. It is a viewer. It also *increases* the context an agent
needs rather than reducing it, which is the opposite of the reason to decompile.

## What was missing, and what was added

`PlanarLayout` is a real compiler and a flat one. Every region is a top-level
entry in one dict, every point is absolute, every connection restates two
endpoints, every sprite is in one global list. Changing one room means reading
the file; moving one room means editing every number in it.

`bloodmap/levelprog.py` adds the layer above it — a tree of named parts, each
holding its own geometry in its own coordinates, its own surfaces, structures and
details. It lowers to `PlanarLayout` and stops; it is not a new IR. See
[level programs](level-programs.md).

Three supporting changes were needed in the compiler below it:

* `PlanarLayout.declare_special` was honoured by region validation but not by
  split-point collection, so a declared overlap still failed on a proper
  crossing. Declared pairs are now skipped in both.
* `PlanarLayout` emits the corpus sky panorama (`bits=4`, 16 offsets) when any
  region declares a parallax ceiling. `new_level` hardcoded a single panel,
  which maps 360 degrees onto one 64-pixel column of the sky tile — every
  outdoor level this project generated had a black sky as a result.
* `bloodmap.vocabulary.arc_through` gives an arc by its two endpoints and a
  bulge, which is the form an outline is actually written in.

## Measured effect on locality

E2M3, the same level, through both emitters:

| | `emit_python_source` | `emit_level_program` |
| --- | --- | --- |
| lines | 138,008 | 5,606 |
| bytes | 8.4 MB | 257 KB |
| top-level functions | 278 (all lookups) | 150 (all builders) |
| largest function | none: 99% of the file is one literal | 319 lines |
| median function | — | 24 lines |
| lines to read one room | the whole file | 24–319 |
| editing a function changes the MAP | no | yes |

`build_level` is 56 lines and names the areas. `build_main_complex` is 138 lines
and is a table of contents. `build_large_interior` is 319 lines and is the whole
of that space: 27 sectors, their surfaces, their sprites, in coordinates local to
it.

## What the authoring model cannot express

Measured, not guessed, and recorded rather than repaired:

* **133 of 14,079 campaign sectors (0.95%)**, in 27 of 43 maps, have outer loops
  `validate_loop` refuses — 87 with repeated vertices, 25 self-intersecting, 20
  zero-area, 1 unreadable. E2M3 has one. They go to `NATIVE_ESCAPES`.
* **XY overlap between independent sectors.** Build has no exclusivity rule and
  originals use it; E2M3 needs 11 `declare_stack` declarations.
* **Same-direction shared edges.** Two sectors traversing one edge the same way
  round rather than reversed: 15 edges in the 43-map corpus, in 6 maps, 4 of
  them in E2M3. Portal pairing is defined on exact *reversed* coincidence, so
  these have no pairing to make.
* **Mechanisms.** Doors, switches, keys and channels have no vocabulary in the
  level-program layer and go through `Room.raw` with a note.

E2M3's emitted program builds 339 of its 340 rooms and lowers to 339 regions and
443 placements. Recompiling from there stops on the same-direction class above,
which is the honest coverage figure: the tree and the lowering are complete, the
round trip is not.

## The middle of the hierarchy

This section used to say the middle layer was missing: `decompile_level` defines
an assembly as a connected component of the portal graph, a normal level is one
component, and 327 of E2M3's 340 sectors landed in a single assembly, so the
layer between "the level" and "one perceptual space" was a list of 123 calls.

It is now a grouping. `tools/propose_areas.py` combines position, elevation
band, material family, sky exposure, opening width and one thing geometry cannot
supply -- whether two spaces are actually seen together -- and
`tools/emit_level_program.py --areas` turns the proposal into real nested
assemblies with their own frames:

| | before | after |
| --- | --- | --- |
| `build_main_complex` | 138 lines, 123 calls | 41 lines, 25 calls |
| sectors in the largest four areas | -- | 270 of 340 |
| what a zone states about itself | -- | elevation, sky fraction, dominant surfaces, centre |

Co-visibility is what made the four principal areas cohere: without it the same
code at the same thresholds breaks the level into 26 fragments whose largest
four cover 202 sectors, and only eight of the 25 groups come out the same either
way. The evidence is in
[area-evidence.md](../projects/e2m3-decompiled/references/area-evidence.md), and
the observation path that supplies it is
[structured visual observation](visual-observation.md).

## The remaining limitation

Zones are called `zone_01` through `zone_25` and nothing here proposes better.
Naming them is interpretation, and interpretation goes in
`references/names.json` with a confidence on each -- which today holds eight
reviewed names for a level with 136 spaces. The grouping is now good enough that
naming a zone would be a *reviewable* act rather than a guess, and that review
has not been done.
