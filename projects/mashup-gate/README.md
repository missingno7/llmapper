> Update 2026-09-09: the owner reports v1 looks good and works; see `owner-review.json`.
> The separate upper-route follow-up is described in [v2.md](v2.md). The historical v1 notes below are preserved.

# Gallery / gate mashup

A small native-fragment transfer experiment, built 2026-09-09. The deliverable is
`work/mashup-gate/v1-verified/mashup.MAP` from the repository root. It has four
sectors, 26 walls and 17 sprites. It is a mechanism prototype, not a finished level.

## What was combined

| Role | Source | Transferred context |
| --- | --- | --- |
| Entry gallery | E1M3 sector 287 | Irregular geometry, materials, lighting, actors and props |
| Push-wall gate | E1M4 sector 359 | Behavior closure also selects sector 361, containing wall 3111 |
| Goal | Newly authored | Small room with a native channel-4 exit switch |

E1M4 wall 3111 has an XWALL push trigger, sends command 3 through channel 129,
and controls the type-600 ceiling mover in sector 359. The door's sound sprite
travels with it. Neither donor has unresolved gameplay dependencies after closure.
The gallery's otherwise detached portals become sealed boundaries. One boundary
is reconnected to the donor antechamber; the far door portal leads to the goal.
No original map bytes or original-map pictures are committed.

The E1M1 sector-50/51 candidate was rejected for this bounded experiment because
its behavior closure exceeded 30 sectors. The E1M4 gate needs only two.

## Recipe and preservation

`experiments/mashup_gate.py` is the executable recipe. It pins both original MAP
hashes and refuses a different specimen. E1M3 is inserted without transformation.
The gate is attached to gallery-local wall 0 using donor-local wall 4, translated
by (-13312, -68352, -32768), without rotation. Its floor then matches the gallery.
Source-to-fragment and fragment-to-result allocations remain in `report.json`.

The gallery's sector and sprite records are preserved; only the chosen wall's
portal references change. The gate's behavior is preserved. The goal adds an exit
switch wearing tile 318. Channel allocation is collision-aware; a separate test
reserves channel 129 and verifies that the donor transmitter and receiver receive
the same new channel while the existing receiver stays unchanged.

Build from the repository root with local campaign maps and Blood ART available:

```text
python -m experiments.mashup_gate --output work/mashup-gate/my-new-run --render
python -m unittest tests.test_mashup_gate tests.test_conditional tests.test_composition tests.test_fragment -q
```

The output directory must be new. Omit `--render` for a static build without ART or
the observer. Original maps remain required. The output includes compiler/source
snapshots, source and artifact SHA-256 bindings, the analysis MAP, six rendered
views, observation JSON and renderer/ART input hashes when rendering is requested.
`probe-*` and `v1` under the local work directory are intermediate experiments;
`v1-verified` is the reviewed result.

## What the evidence establishes

- The MAP rebuilds byte-exact and reparses byte-exact. Native validation reports
  no errors or warnings; new-to-existing layout checks report no conflicts.
- Before activation, the explicit initial-state model reaches gallery 0 and
  antechamber 2. Pushing wall 18 sends channel 129 and makes door 1 and goal 3
  reachable. The exit switch is offered only in the next progression round.
- All three connections are 1024 units wide. The closed gate has zero opening;
  its open clearance is 26624 Z units, above the 16960 standing-height check.
- The helper checks report no switch-height, exit-tile or switch-placement faults.
- Three mashup tests pass, including broken/locked control and channel-collision
  cases. The related conditional/composition/fragment suite passes 83 tests.
  All 43 campaign maps pass native and IR byte roundtrips and validation.
- Six requested editor views render successfully. The closed approach hides the
  goal; the open approach reveals its exit emblem. These are endpoint geometry
  observations, not screenshots of a mechanism activated in the game.

## What this experiment exposed

`ConditionalGraph.available_actions` previously offered sprite switches and direct
mechanism operation but omitted XWALL push transmitters. Consequently it knew the
channel-door relationship yet offered no action to activate this transplanted gate.
It now exposes `use_wall`, with wall identity and owning sector. Unreachable,
locked, key-blocked, spent one-shot and disabled push controls are not offered.
This remains sector-level availability, not a use-distance or line-of-sight proof.

The donor is drawn open while XSECTOR state is zero. Directly describing that
geometry as the initial state produced misleading explanatory opening values.
The recipe therefore preserves the native MAP and separately writes
`initial-state-analysis.MAP` with the explicit off endpoints. Its hash is recorded
in the report. The activation explanation now consistently reads 0 -> 26624.
No general engine-state simulator was added.

## Remaining play check and limits

No NBlood process was launched. To verify runtime behavior, a player must approach
the gate from the gallery, press its face, cross during its original timing, then
operate the exit emblem in the goal room. Check closing/reopening, sound, collision
and exit transition. A proposed standing point is (8064, -33792), 256 units from
the push wall through the narrow antechamber; this still needs a runtime use test.

The two original cultists, pickups and decoration remain. Combat, resources and
first-time readability have not been tuned or player-tested. The generated goal
is intentionally simple. This experiment transfers Z motion and native trigger
closure; it does not yet transfer stacked rooms, room-over-room links or sprite
bridges. Those should form a separate matched mashup after this passage is tested.
