# Shared level-authoring toolkit

This is the entry point for a human or an LLM making a new Blood level.  It
answers two questions before code is written: **where does this decision live?**
and **which existing tool owns it?**

The goal is not to force every map into one style.  It is to make intent,
reusable implementation, campaign evidence, and observed result traceable to
one another, so a correction made in one project becomes available to all of
them.

## The source-of-truth path

```text
map intent + named parts
  -> LevelProgram                     local coordinates, inherited style, intent
  -> PlanarLayout                     regions, connections, declarations
  -> shared constructors              apertures, stairs, lights, switches, props
  -> LevelIR / MAP                    native Build fields, generated output
  -> static checks + observer frames  evidence about the generated result
  -> project reports + knowledge       durable, retrievable conclusion
```

`LevelProgram` is the normal editable source.  `PlanarLayout` is its exact
planar lowering.  Native sectors, walls and sprites are output; do not treat a
compiled MAP or a list of numeric ids as the thing to hand-edit.  Use
`Room.raw(note, apply)` only for a genuinely unmodelled native mechanism, with
the reason recorded in the room summary and a grammar request if it recurs.

Campaign data describes a convention; it does not turn a level into a score
maximisation problem.  A deliberate exception belongs in the map's intent and
its visual review, not in an unexplained magic number.

## Tool routing

| Need | Shared owner | Use it for | Evidence / acceptance |
| --- | --- | --- | --- |
| Named editable rooms and local coordinates | `bloodmap.levelprog`, `Frame`, `Style` | assemblies, room faces, inherited surfaces, source-level light declarations | `room.summary()`, style provenance, `PlanarLayout.compile()` |
| Planar geometry and portals | `bloodmap.planar_layout`, `planar_geom`, `geometry_audit` | regions, connections, partitions, intentional overlap | conservation, portal pairing, geometry audit |
| Reusable architectural forms | `bloodmap.vocabulary`, `prefab`, `furniture`, `slope`, `roomoverroom` | stairs, recesses, arcs, alcoves, breakables, slopes, linked volumes | player clearance and structure-specific checks |
| Openings and moving doors | `bloodmap.aperture`, `doors`, `switches`, `keys` | named leaves/reveals, Z motion, direct/remote use, locks and signifiers | door affordance audit and close observer views |
| Surface vocabulary | `bloodmap.surfaces`, `materials`, `texture_align`, `style` | field/opening materials, inherited finishes, tile phase and panning | ART size checks, rendered continuity |
| Light and atmosphere | `bloodmap.lightbomb`, `lighting`, `LightSourceDecl` / `emits_light=True` | semantic sources (including justified source strength and optional bulb height), automatic bounced light, deliberate shade overrides, flicker | lighting report, representative rendered views |
| Props, signs and readable detail | `decoration`, `vocabulary`, `lettering`, `item_display`, `placement` | corpus-sized sprites, mounting, labels, usable placement | attachment and reach checks |
| Gameplay and progression | `mechanism`, `mechanisms`, `progression`, `reachability`, `player_space`, `sight`, `exposure` | channels, gates, routes, clearance, visibility and risk | individual hard gates, never one aggregate score |
| Campaign retrieval and inference | `art`, `patterns`, `contents`, `structures`, `sp_understand`, `understanding`, `knowledge/blood/design` | find an attested family, a tile's dimensions, a spatial precedent, or a convention | cite the mine/catalog and distinguish derived fact from interpretation |
| Build review and iteration memory | `rules`, `visual`, `viewplan`, `viewpoints`, `authoring_loop`, `workspace` | native validation, reproducible observer frames, source-to-view join, decisions and episodes | MAP hash, report, named frames, evidence links |

The repository also contains conversion, decompilation, Doom/Duke, analysis and
oracle modules.  They are supporting routes, not a reason to bypass the source
path above: use `decompiler`/`conversion` to recover or translate a level, then
bring the result back to an editable program; use `oracle` only as explicit
engine evidence.

### Complete module index

The table is the decision guide; this index makes every maintained `bloodmap`
module discoverable without making the table unreadable.

| Group | Modules |
| --- | --- |
| Core map model and emission | `format`, `model`, `build_ir`, `construction`, `layout`, `planar_geom`, `planar_layout`, `rules`, `rules_blood`, `blood_types` |
| Editable authoring and structures | `levelprog`, `assembly`, `vocabulary`, `aperture`, `doors`, `switches`, `keys`, `mechanism`, `mechanisms`, `prefab`, `furniture`, `slope`, `roomoverroom`, `composition`, `fragment` |
| Materials, light and placed objects | `art`, `assets`, `materials`, `surfaces`, `style`, `texture_align`, `lightbomb`, `lighting`, `decoration`, `lettering`, `item_display`, `placement` |
| Understanding and campaign retrieval | `analysis`, `contents`, `design`, `design_contract`, `patterns`, `structures`, `sp_understand`, `understanding`, `semantics`, `state_model`, `player_space`, `spatial`, `morphology`, `sector_map` |
| Checks, probes and visual evidence | `geometry_audit`, `progression`, `reachability`, `sight`, `exposure`, `experience`, `probes`, `probe_schema`, `viewplan`, `viewpoints`, `visual`, `oracle`, `authoring_loop`, `workspace` |
| Import, conversion and comparative work | `decompiler`, `conversion`, `doom`, `doom_convert`, `doom_geometry`, `doom_semantics`, `duke`, `duke_motion`, `duke_semantics`, `differential`, `counterfactual`, `recipe` |
| Worked or specialised implementations | `designs`, `e3l11`, `doom_fixtures` |

`__init__` is the curated public import surface and `cli`/`__main__` are the
command-line routes.  Start from a group in the table, then read the named
module's docstring and existing tests before adding a new abstraction.

## Cross-map authoring rules

1. **Search for the noun before inventing a helper.**  Before adding a
   project-local `door`, `light`, `stair`, `window`, `prop`, or `switch`
   function, search `bloodmap/` and this guide.  Adopt the shared constructor,
   improve it with a regression test if it lacks a needed parameter, or record
   a grammar request with the concrete case.  Do not silently fork a primitive.
2. **Declare causes, generate consequences.**  A flame, lamp, window or furnace
   declares a light source (and only a larger fixture declares a non-default
   intensity); LightBomb generates the base shades.  A room states
   its material exception; style inheritance supplies the ordinary finish.  A
   door declares its leaf, motion and interaction; the compiler supplies the
   frame and native fields.
3. **Keep an override where the decision is made.**  Explicit shade, texture,
   route, or mechanism values are valid when intentional.  Generated passes
   must preserve them and reports must say how much was generated versus
   protected.
   A surface that is deliberately generated from a declared source may opt in
   with region intent (for example a lamp pool's `generated_surfaces: [floor]`);
   that is a source-driven declaration, not a hidden shade override.
4. **Keep behaviour, interaction, condition, feedback and signifier separate.**
   A type-600 sector is not by itself a usable or readable door.  The same
   separation applies to every mechanism.
5. **Validate cheaply before rendering, then render the question.**  Compile,
   run native/geometry/affordance checks, and capture named observer poses that
   actually show the proposed change.  A valid MAP is not proof of a good frame;
   a pretty frame is not proof of working behaviour.
6. **Preserve knowledge as evidence, not folklore.**  Put a reusable discovery
   in a shared constructor plus a test; put a campaign observation in
   `knowledge/blood/design` or a linked report; put a map-specific choice in
   the project's source and refinement log.  Never leave the only explanation
   in an old generated MAP or chat history.
7. **Never let ordinary wall sprites share a painted plane.**  Mount routine
   wall detail through the project's safe wall-mount helper, which reserves a
   body-width run on the physical wall even when logical regions later compile
   into one sector.  Direct wall placement is only for an explicitly authored
   layered composition.  Audit the emitted MAP for co-located visible sprites
   and render the affected room; Build can reverse coplanar sprite painter
   order as the view angle changes.
8. **Make each ROR half agree with the room it opens into.**  For a lower ROR
   entry, the lower sector's ceiling is the receiving room's ceiling plane;
   derive both from one named stack plane and verify equality in the emitted
   map.  A deliberate threshold step is allowed only at a normal portal with
   enough clearance, never inside the stacked-volume hand-off.

## Door standard

For an ordinary rising door, declare type 600 and use
`bloodmap.doors.z_motion_door(floor_z, open_ceiling_z, ...)`.  Its default
five-tenth open and close times prevent the native zero-time state jump.  Choose
`interaction="direct"`, `"remote"`, or `"both"` deliberately; the dual form
retains use triggers as well as its RX channel.

Run `bloodmap.aperture.frame_z_doors(...)` on declared rectangular Z-doors
before the final layout compilation, or call `framed_door(...)` directly for an
unusual opening.  The helper adds reveal frames on both sides, snaps the leaf to
whole art repeats, and synchronises the motion endpoint to that leaf height.
This prevents a shut zero-height sector from painting its door tile across a
tall façade.  See [door affordances](door-affordances.md) and
[aperture grammar](../bloodmap/aperture.py).

## Minimum delivery record

Every generated map should leave these discoverable:

- source module(s) and the generated MAP;
- a build manifest with semantic light sources, source strengths, and
  generated/protected lighting counts;
- the relevant static reports (geometry, doors, progression or placement);
- named observer frames for the changed visual claim;
- a short refinement-log entry that links the evidence to the next decision.

That record makes a later LLM able to change one room without having to
rediscover why a door has a frame, why a lamp has no hand-tuned shade, or why a
particular raw native escape exists.
