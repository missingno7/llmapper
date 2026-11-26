# Independent technical and product-direction audit

**Decision: stop expanding the design infrastructure for now. Establish one reproducible authoring baseline, then test whether its feedback loop produces maps that people prefer to play.**

Audit date: 2026-09-09. Main repository HEAD: `99c904c`. This assessment concerns the current working tree and distinguishes it from historical reports. It uses repository code, tests, reports, preserved images, and git history; it is not a literature review. Three parallel inspections informed the audit; the conclusions below are independently synthesized and important findings were checked against code or small measurements.

No implementation, map, submodule, or existing report was edited. The pre-existing modified NBlood/xmapedit state, modified city plan report, and untracked `.claude/` were preserved. New files are this audit and its measurement artifacts. No game was launched and no human playtest was performed during the audit.

## 1. Executive verdict

The project is on a credible path toward **reliable Blood construction and inspectable architectural editing**. It has not demonstrated convergence toward **excellent, independently designed Blood levels**. The evidence currently fits an infrastructure-led, owner-corrected process: a map exposes a problem, a person or agent investigating that specific problem names it, and the repository grows a detector or constructor. That process can accumulate useful expertise. It does not establish that the next unfamiliar design will be good, or that the LLM will recognize its most important failures without the owner.

The strongest part is the connection between exact engine data, stable source identity, compilation, and observations tied back to actual map objects. Native preservation, planar geometry construction, hierarchical source, source-backed mechanism helpers, and renderer observations are worth keeping. The nested-authoring experiment is a particularly clean small result: changing one stair-width parameter increased its measured screen coverage from 5.5% to 8.1%, while unrelated nodes and another view stayed unchanged. That demonstrates controllable revision and a useful sensor, although it does not establish better navigation or enjoyment. [Nested observation experiment](D:/Games/DOS/llmapper/experiments/nested-authoring-observation.md:1)

The largest bottleneck is **judgement connected to player experience**. The project has many ways to establish what a map contains, whether selected declarations survived compilation, and how its statistics compare with a corpus. It has little controlled evidence about whether a player understands the space, anticipates a threat, enjoys a fight, remembers an objective, or wants to continue. The review seam delegates judgement to an external agent; reference validation does not make those judgements correct. [Review implementation](D:/Games/DOS/llmapper/bloodmap/authoring_loop.py:1986)

What worries me most is the combination of three problems: quality dimensions are often introduced after owner discovery; passing diagnostics becomes the practical definition of progress; and the flagship evidence is not consistently bound to its current source and MAP. These reinforce each other. A growing vocabulary can look like learning while the actual task remains dependent on the same human critic, and stale reports can obscure the difference.

I would retain the reliable construction core, sharply reduce the active surface area, and spend the next effort on three falsifiable experiments below. I would not commission another general IR, a wider cross-game abstraction, a bigger city, or another census to fill a percentile gap. The immediate product should be **small, complete, intentionally designed Blood maps with trustworthy before/after evidence**, not a comprehensive theory of Blood maps.

## 2. What is actually proven

“Proven” below means demonstrated within a named technical scope, not universally guaranteed. Historical reports are not treated as fresh measurements.

| Status | Claim supported by the evidence | Boundary |
|---|---|---|
| **PROVEN, bounded** | Native binary preservation and structural tooling work on substantial supported corpora and fixtures. The fresh suite exercised the local corpus; all ten candidate MAPs inspected in this audit round-tripped natively and had zero native validation errors. | This says nothing about rendering correctness across all states, reachability in play, or quality. |
| **PROVEN, current** | The current city slice compiles to exactly its stored MAP: 199 sectors, 1,031 walls, 16 sprites, SHA-256 `347ba9fb…147eea`. Its nine mechanism sentences read back without differences; nine links and five keys are realized. | These are construction and correspondence checks. The optimistic reachability result assumes mechanisms have worked. |
| **PROVEN, bounded** | Hierarchical source supports local edits, explicit ownership, exact translation frames, and traceable style inheritance; dedicated tests execute these contracts. | Complete arbitrary-map reconstruction and arbitrary geometric transformations are not implied. |
| **STRONG EVIDENCE** | The toolkit prevents important classes of corruption and bad mechanism implementation that native parsing alone misses. Current v5/v7 source is rejected by the motion-sweep gate although the stored MAPs pass native validation. | A stronger gate catching an old mistake is useful progress, not proof that the old map was good or the whole gameplay system is covered. |
| **STRONG EVIDENCE** | Visual inspection plus measurements can improve specific visible defects. The historical v2 chapel image is dominated by an oversized decoration; the saved v5 image removes it and has clearer articulation. | This is my judgement of particular saved frames, not a blinded level-quality finding; the v5 frame is not evidence about today's v5 MAP. |
| **PROMISING** | Shared constructors, corpus-conditioned material propagation, source-attributed rendering, and the city mission/read-back model can reduce author burden. | Their effect on independently authored maps has not been isolated from owner help, iteration time, or accumulated project-specific fixes. |
| **ASSUMED** | Matching corpus envelopes, lowering decompilation residue, or adding recognized structures generally improves a new level. | Each may improve a measurement while leaving the map bland, illegible, or tedious. |
| **ASSUMED** | The current bot can supply representative player-experience evidence. | The active bot is unfinished and differs from the bot behind older retail results; whole-world knowledge also limits claims about discoverability. |
| **NOT YET TESTED convincingly** | The LLM discovers missing evaluation dimensions, requests decisive evidence, repairs the actual experience, and transfers that ability to unfamiliar briefs without owner prompting. | No controlled multi-brief study or calibrated critic evaluation was found. |
| **NOT YET TESTED convincingly** | Players prefer the resulting maps for atmosphere, navigation, encounters, pacing, or replay value. | Existing authored populations and gameplay declarations establish content presence, not the experience they cause. |

Sources: [fresh measurements](D:/Games/DOS/llmapper/reports/archive/independent-audit-2026-09-09/measurements.json), [fresh city probe](D:/Games/DOS/llmapper/reports/archive/independent-audit-2026-09-09/city-probe.json), [historical verification](D:/Games/DOS/llmapper/reports/archive/verification.md:1), [LevelProgram contracts](D:/Games/DOS/llmapper/docs/level-programs.md:26), [saved v2 chapel](D:/Games/DOS/llmapper/projects/reasoned-authoring-v1/reports/v2/views/view_chapel_interior.png), [saved v5 chapel](D:/Games/DOS/llmapper/projects/reasoned-authoring-v1/reports/v5/views/view_chapel_interior.png).

### Nine different meanings of “good”

| Dimension | What the repository can establish | What remains unestablished |
|---|---|---|
| Binary correctness | Supported records parse, preserve bytes, encode deterministically. | Any design merit. |
| Structural validity | Portal pairing, conservation, certain collision/overlap errors, attachment and start checks. | All useful movements and dynamic states. |
| Semantic correctness | Selected mechanism fields, wiring, motion membership, and read-back agree with declarations. | Every mechanism actually works in context and every required action can be completed in the required order. |
| Similarity to Blood | Frequencies, conditional usage, signatures, feature deviations. | Authenticity as experienced by a player; appropriateness to a particular brief. |
| Architectural coherence | Ownership, dimensions, connections, detected spatial relationships, local visual evidence. | Whether the whole place makes perceptual, functional, or dramatic sense. |
| Visual quality | Exact tiles/flags plus static rendered visibility and selected pictures. | Composition, hierarchy, mood, legibility, and coherence judged across a route and states. |
| Gameplay quality | Populations, static access, some state/mechanism analysis and runtime probes. | Reliable completion, balanced resources, useful choices, fair combat. |
| Fun / pacing / encounter design | Authored intentions and scattered qualitative reviews. | A validated relationship between these intentions and actual player response. |
| Self-correction | Repeatable compile/probe/review interfaces and examples of targeted repair. | Reliable independent diagnosis, missing-dimension discovery, and beneficial revisions on new maps. |

### Fresh reproducibility findings

The current v5 packet claims **38 sectors / 295 walls / 60 sprites**, under hash `8fb5288e…b1eee9`. The MAP at its named path contains **133 / 913 / 360**, under `46780018…13fe2`. The v0–v4 saved MAPs still match their packet hashes. Git identifies the break: `7e19f84` changes v5 source and MAP without refreshing the packet/report; the original v5 group was added in `b0e0f3b`. This is a specific archive-integrity failure, not a reason to discard all pilot evidence. [v5 summary](D:/Games/DOS/llmapper/projects/reasoned-authoring-v1/reports/v5/summary.md:3), [measurement identities](D:/Games/DOS/llmapper/reports/archive/independent-audit-2026-09-09/measurements.json)

Current v5 and v7 source compilation each fails with **nine sweep diagnostics concerning one type-617 mechanism**, including self-crossing and intersection with standing geometry. These are nine findings, not nine independently broken mechanisms, despite the exception's wording. Current v0 compiles deterministically but differs from its historical MAP: two sprite Z values and one sprite's repeats changed, in addition to CRC metadata. Reproducibility therefore needs the compiler/toolchain revision as well as source. [Source probes](D:/Games/DOS/llmapper/reports/archive/independent-audit-2026-09-09/measurements.json)

The test named “every iteration” compiles only v0–v3. There are no corresponding v6/v7 iteration packets in the pilot report directory. The current v5–v7 MAPs contain 29 dude-type sprites each; the early v0–v4 MAPs contain none. It would be wrong to describe all current monastery work as enemy-free, or to describe its later population as tested encounter design. [Pilot tests](D:/Games/DOS/llmapper/tests/test_monastery_pilot.py:11), [artifact inventory](D:/Games/DOS/llmapper/reports/archive/independent-audit-2026-09-09/measurements.json)

Gravesend also has two tracks. The older full map contains **259 sectors / 1,694 walls / 430 sprites**, including 27 dude-type sprites. The current 199-sector slice is a smaller construction/mechanism specimen with no dude-type sprites. It now contains functioning declarations and read-back, so its introductory “ground” description understates it; it still is not the full city's gameplay demonstration. Its four recently committed “renders” are plan diagrams, not first-person views. Historical first-person city evidence exists elsewhere and must retain its own version. [Current slice source](D:/Games/DOS/llmapper/projects/blood-city/level/build_graph_slice2.py:1), [current read-back](D:/Games/DOS/llmapper/reports/archive/independent-audit-2026-09-09/city-probe.json), [recent street diagram](D:/Games/DOS/llmapper/projects/blood-city/renders/slice2i-street-b291984.png)

## 3. Critical weaknesses, ranked by impact on the goal

1. **There is no validated quality-improvement loop.** The project cannot currently tell whether a revised map is more enjoyable, clearer, or more intentionally designed except through uncalibrated judgement. Additional sensors do not solve this by accumulation. Establishing a small reliable external evaluation is the highest-value next step.

2. **The loop depends on the owner to expose missing questions.** The monastery missed scale, shape, and sprite size. The city repeated the pattern with kerb materials, wall shading, unsupported lamps, and inconsistent sky choices. Regression coverage after discovery is useful; it does not establish independent discovery before a player sees the fault. [Pilot failure analysis](D:/Games/DOS/llmapper/projects/reasoned-authoring-v1/reports/comparison.md:101), [city walk findings](D:/Games/DOS/llmapper/docs/history/llmapper_level_understanding_handbook/09_IMPLEMENTATION_ROADMAP.md:3876)

3. **Player action is not a routine, trusted part of candidate acceptance.** A graph with all mechanisms worked cannot establish an achievable sequence. A door moving cannot establish passage. Passage cannot establish legibility or a good fight. The Foundry packet explicitly leaves its drop, explosion timing, and gate choice fun-unvalidated. [Foundry acceptance](D:/Games/DOS/llmapper/projects/blood-city/reports/pilot-foundry-packet.md:42), [passage-oracle report](D:/Games/DOS/llmapper/reports/blood-passage-oracle.md:1)

4. **The evidence chain is not reliable enough for research comparisons.** The v5 mismatch, source rebuild failures, divergent city artifacts, old verification report, and interleaved roadmap history make it too easy to compare different things under the same name. This ranks below the missing outcome in product importance, but should be repaired first operationally because the next experiments depend on it.

5. **Corpus conformity is drifting into an authoring objective.** There are explicit warnings against this, yet practical tasks repeatedly chase orientation bins, alcove counts, lighting percentages, dead-end fractions, and resource ratios. The norms exemption queue even proposes that norms remain authoritative for every artifact called a level. A corpus observation has no such authority over a deliberate design. [Norm exemption proposal](D:/Games/DOS/llmapper/reports/owner-review-queue.md:37), [pilot metric tradeoff](D:/Games/DOS/llmapper/projects/reasoned-authoring-v1/reports/comparison.md:178)

6. **The active authoring surface is fragmented.** Tree source, flat layout source, city surface declarations, imperative mechanism helpers, native fragments, and post-lowering passes all have legitimate uses. As coequal routes for an LLM they create discovery and integration costs. The city itself documented four incorrect local reimplementations of existing helpers, including switches that could not be pushed. [City handoff](D:/Games/DOS/llmapper/projects/blood-city/reports/handoff.md:63)

7. **Generalization evidence is mostly about readers and primitives, not designers.** Cross-map recurrence, held-out primitive fits, and decompiling a second map are stronger than a single pilot. They do not measure whether an LLM composes those primitives into an effective unfamiliar level. The tested unit of transfer must become a design task and its revision outcome.

## 4. Feedback-loop diagnosis

| Link | What actually happens | Information lost or assumption introduced |
|---|---|---|
| Intent → source | Python factories, authored assemblies/regions, some mission facts, prose briefs. | Much of the desired player experience has no executable or observational acceptance condition. Architectural role names can exceed what geometry realizes. |
| Source → compilation | LevelProgram lowers to PlanarLayout, then LevelIR/MAP; city has a compiler-owned sequence of surface/lighting/join/frame passes. | Native mechanism fields and low-level stage details remain exposed; historical source output changes when shared defaults change. |
| MAP → validation | Native validation plus authored geometry, attachment, reachability, motion and selected mechanism checks. | Some checks are conditional on declarations and exceptions. They do not independently establish that all useful actions are possible. |
| MAP/game → observation | Static probes, decompiler hypotheses, ART/corpus measurements, editor rendering, optional runtime oracles. | Static geometry loses temporal experience. Chosen viewpoints omit unseen defects. Editor pixels omit some game effects and sprite behavior. |
| Observation → judgement | External reviewer attaches claims and actions with resolvable references. | Correct references do not establish correct inference, suitable priorities, completeness, or that the reviewer actually inspected the decisive frame. |
| Judgement → revision | Source edits followed by more checks and sometimes matched renders. | No systematic causal comparison establishes that the experienced problem improved rather than a proxy moved. Evaluators and maps sometimes change together. |
| Revision → next map | Knowledge files, constructors, rules, project memories. | Storage is not demonstrated learning. There is no measured reduction in human help or increase in quality on a fresh brief. |

Sources: [loop implementation](D:/Games/DOS/llmapper/bloodmap/authoring_loop.py:1452), [city compiler](D:/Games/DOS/llmapper/bloodmap/pipeline.py:187), [Experience Atlas limits](D:/Games/DOS/llmapper/docs/experience-atlas.md:26), [visual limitations](D:/Games/DOS/llmapper/docs/visual-observation.md:179).

**The weakest link is observation → justified judgement of the player's experience.** Observation coverage is the next bottleneck: the critic cannot discover what its evidence never represents.

### Independence is narrower than the documentation's slogan

The derived hierarchy reads compiled map data rather than trusting `role="courtyard"`. That is good. However, the overall packet also contains conformance checks: `_gated_sectors` accepts authored `doorway`/`gated_pocket` roles as well as native types; mandatory regions are declared by the author; `_required_reachability` explicitly opens every authored connection; some hierarchy discrepancy filters use authored transition roles. These are legitimate conditional checks, but should be presented as **“valid under these declared assumptions”**, alongside independent observations. [Gate inputs](D:/Games/DOS/llmapper/bloodmap/authoring_loop.py:234), [optimistic mandatory reachability](D:/Games/DOS/llmapper/bloodmap/authoring_loop.py:431)

The current city probe makes the distinction concrete: 173 sectors are reachable at rest and 199 under `everything_worked()`. Nine sentences, nine links, and five keys being realized does not prove a player can discover and execute a sequence that produces that state. [Mission check](D:/Games/DOS/llmapper/projects/blood-city/level/build_graph_slice2.py:1239)

### The pilot is valuable negative evidence

The original pilot deliberately excluded combat and wider gameplay behavior. It should be credited as an architectural feedback pilot, not penalized for failing a goal it never attempted. Its importance is that even within that narrower scope, the owner supplied missing dimensions after green checks. Three hierarchy rules also needed correction after disagreement with frames. The report says pre-correction output was not retained, so the rerun table cannot establish what the critic knew at the moment each design decision was made. [Pilot scope](D:/Games/DOS/llmapper/projects/reasoned-authoring-v1/design/brief.md:41), [comparison history](D:/Games/DOS/llmapper/projects/reasoned-authoring-v1/reports/comparison.md:101)

The v0→v1 gallery fix is plausible architecture, but it also directly crosses the grouping rule's shade threshold. Clearing the discrepancy therefore cannot independently validate the perceptual claim. Similarly, adding small structures that a detector calls overlooks is not equivalent to introducing a meaningful cross-height view or encounter. The report itself notes a courtyard classified as a landing. Those are reasons to preserve frames and player observations beside the metrics. [Gallery revision](D:/Games/DOS/llmapper/projects/reasoned-authoring-v1/reports/comparison.md:65), [structure revision](D:/Games/DOS/llmapper/projects/reasoned-authoring-v1/reports/comparison.md:153)

The recent city walk shows the same loop at a later stage: existing gates asked whether every join pair had a rule, but not whether every surface wearing a special material had the right context; lighting checked floors but missed wall bands; lamps and connected sky consistency were not covered. The response added useful absolute checks. It did not show that the system could anticipate these dimensions. [Walk analysis](D:/Games/DOS/llmapper/docs/history/llmapper_level_understanding_handbook/09_IMPLEMENTATION_ROADMAP.md:3876)

### Useful evidence versus attractive targets

Keep hard engine truths hard: valid records, usable trigger flags, actual motion dependencies, legal reference relationships, and demonstrated passage. Keep corpus facts conditional: which population, which unit, which surface role, which context, and how many independent maps. Keep authored intent and subjective judgement explicitly separate from both.

The worst targets are whole-map aggregates interpreted as experienced design: orientation-bin counts, loops per sector, “empty space” counts, material variety, overlook counts, pickup/dude ratios, percentage of animated sectors, and decompilation residue. Each can help locate a question. None determines the answer. Tight ratios can be satisfied with badly placed resources; extra loops can create confusing backtracking; more visual variety can destroy coherence; a deliberately empty pause can be good pacing.

There is a concrete mathematical limitation in `map_discriminator.py`. Its score is the 90th percentile of independent absolute deviations from each feature's median, scaled by IQR. It does **not** model relationships between features, despite the motivating claim about their combination. A probe using corpus pairs `(x,y)=(1,1)…(8,8)` gives the same score, 0.875, to `(1,1)` and the relation-breaking `(1,8)`; blandness is also identical. With 100 features, making one feature extreme leaves a zero score unchanged because it lies above the selected percentile. This is a marginal outlier summary, not a validated classifier of designed maps. [Implementation](D:/Games/DOS/llmapper/tools/map_discriminator.py:134), [counterexample probe](D:/Games/DOS/llmapper/reports/archive/independent-audit-2026-09-09/discriminator-probe.json)

Do not replace it with a more sophisticated classifier yet. Remove its status as a quality or authenticity gate. The first question is whether any of these statistics predicts independent human judgements. A learned classifier over roughly 43 repeatedly inspected campaign maps would also face substantial overfitting and leakage risks.

### Visual evidence and runtime evidence

The XMapEdit observer is one of the strongest investments: it cheaply identifies what the renderer painted and joins native objects to source owners. The documentation reports 163 E2M3 views rendered in 55 ms after initialization. Its static editor view is useful for composition; it cannot establish dynamic game appearance, attention, comprehension, sound, or gameplay. Painted coverage can exceed frame area because of overdraw, and sprites are not exact per-pixel ownership. [Observer design and limits](D:/Games/DOS/llmapper/docs/visual-observation.md:1)

The policy that JSON is the product and images optional is sensible for geometry measurement, but too restrictive as a product principle for visual judgement. A critic should normally receive a small, deliberately chosen sequence of actual pictures plus source references; detailed JSON should be available on demand. A collection of object IDs and coverage fractions cannot communicate why a room feels institutional, sacred, cluttered, or theatrically staged. The early pilot also had no upward views until v5. [View counts](D:/Games/DOS/llmapper/projects/reasoned-authoring-v1/reports/comparison.md:13)

Gravesend's refinement log records long-sightline frames disappearing and then shorter views being used. That is a historical observation-tool failure, not a fresh reproduction in this audit. It should be rechecked before using this path for street/vista evaluation; avoiding the failing poses is not equivalent to observing the vista. [Recorded frame loss](D:/Games/DOS/llmapper/projects/blood-city/reports/refinement-log.md:117)

Actual engine traces already have a foundation. The passage report correctly distinguishes a recorded crossing from ambiguous non-crossing and uses open/walled controls. Its rotor probes produce no trajectory because the bot refuses to enter: **no data**, not a bad door. Use that lesson to separate a recorder and bounded scripted input from an autonomous player. The near-term loop needs trusted actions and human recordings, not a fully general bot first. [Passage controls and limitations](D:/Games/DOS/llmapper/reports/blood-passage-oracle.md:59)

Older bot results are not evidence about today's bot. The August 21 retail audit reports 6.36% weighted raw sector coverage over 43 maps in `-nodudes` mode; the bot was reset afterward, and the legacy source explicitly records the snapshot. Current documentation contains both an older observation-bounded description and a later whole-world-reading description. Use the latter limitation when discussing discoverability, and pin the actual build before further runtime claims. [Historical retail audit](D:/Games/DOS/llmapper/NBlood/extras/llmapper-retail-depth-audit.md:1), [legacy boundary](D:/Games/DOS/llmapper/NBlood/source/blood/src/llmapper/bot_legacy/LEGACY_BOT.md:1), [current whole-world description](D:/Games/DOS/llmapper/docs/nblood-autonomous-playtest-bot.md:259)

## 5. Architecture and overengineering diagnosis

The problem is not simply too many modules. Inspection, source editing, native preservation, and compilation genuinely need different representations. The overengineering is that too many research representations and workflows are active prerequisites for making the next level.

| Subsystem | Classification for this goal | Decision |
|---|---|---|
| Blood DiskMap codec, validation, native field knowledge | Important enabling infrastructure | **Keep and stabilize.** Preserve exact engine truth and regression coverage. |
| LevelIR | Important enabling infrastructure | **Keep internal.** It is the compiler/native editing boundary, not the usual LLM design surface. |
| BuildIR | Important enabling infrastructure already depended upon | **Keep as an adapter for existing sensors.** Do not rewrite consumers merely to delete an abstraction. Freeze expansion driven by other games. |
| LevelProgram | Core to scalable authoring | **Preferred source for substantial new work.** Local frames, named faces, and style provenance directly help revision. Validate its advantage in experiment 3. |
| PlanarLayout | Core compiler infrastructure | **Keep one geometry compiler.** Make it the ordinary lowering target; retain direct use for small fixtures and the comparison baseline. |
| LevelBuilder, raw native construction | Enabling internals | **Keep for primitives and probes.** Stop presenting it as another preferred greenfield design route. |
| Fragments, closure, composition recipes | Useful research / specialized import | **Freeze broad expansion.** Keep behavior-safe import and precedent extraction. No demonstrated need to make fragment recombination the central design method. |
| Shared doors, switches, keys, motion, aperture helpers | Core to Blood authoring | **Keep and route authors to them.** Reduce duplicate project helpers and verify the emitted native behavior. |
| Materials, surfaces, ART dimensions, owner anchors | Core data plus enabling knowledge | **Simplify the author interface.** Offer a small contextual palette with images and dimensions; preserve provenance. Avoid a wider ontology before a transfer result. |
| Spatial/design/contents/sight/progression sensors | Important enabling infrastructure | **Keep as independent queries.** Consolidate duplicate implementations, not distinct meanings of space. |
| Structures, patterns, vocabulary mining | Useful research with selected core outputs | **Freeze general census growth.** Promote a constructor only when it makes a current design task easier and transfers. |
| Decompiler and emitted LevelSource | Inspection / reconstruction research | **Keep the exact reader and local inspection.** Remove complete decompilation from the generation critical path. |
| City surface model, joins, frames, overlays, compiler-owned pipeline | Important enabling work, currently specialized | **Keep the proven pass ownership and geometry fixes.** Freeze breadth; test whether the declarations serve another kind of map before expanding the city grammar. |
| City mission facts / read-back sentences | Promising core direction | **Reuse experimentally.** Do not migrate the entire repository to a new MechanismDecl schema first. |
| Experience Atlas / project memories / ledgers | Useful bounded probes; premature as a learning system | **Keep small records and query contracts; freeze elaboration.** Measure whether their retrieval improves the next map. |
| Duke/Doom semantics, conversion, cross-game normalization | Useful research, off the current critical path | **Freeze feature investment.** Retain tests and existing code; do not make unrelated conversion fidelity a prerequisite for Blood quality. |
| NBlood autonomous bot | Useful research; full autonomy premature for current need | **Freeze general planner growth.** Use or minimally expose a trusted recorder and bounded action driver first. |
| Quality-diversity search, discriminator-driven tuning, recursive knowledge-growth agenda | Premature | **Stop treating these as next steps.** Search amplifies the evaluator's blind spots. Reconsider after quality evaluation has predictive value. |
| Duplicate project helper vocabularies and superseded emitters | Duplicative / likely distraction | **Migrate or archive after pinning historical artifacts.** Delete only when no preserved experiment depends on them. |

### The abstraction level is partly right

The practical target is a hybrid: **hierarchical authored source for place and ownership; a small shared vocabulary for recurring structures and mechanics; arbitrary geometry/raw exceptions when intentional; compiled native detail below that boundary**. The LLM should mostly reason about a room's purpose, approach, silhouette, route, encounter, and relationships. It should not normally maintain reciprocal wall IDs, sprite extents, or packed trigger flags.

LevelProgram already supplies much of the missing middle for architecture. The reported E2M3 emitter comparison reduces a largely inert 138,008-line literal to 5,606 lines of builders, with individual room functions generally 24–319 lines. That is a genuine context and editability benefit. It is not full lossless re-authoring: 133 of 14,079 campaign sectors are outside the supported outline model, and E2M3 still has same-direction shared edges that prevent a complete compile. Freeze that coverage chase unless an experiment actually needs those cases. [Emitter comparison and limits](D:/Games/DOS/llmapper/docs/history/authoring-architecture-audit.md:85)

The project already has substantial native mechanism grammar. “It cannot author doors or switches” would be false. Door helpers expose interaction, key, timing and channel choices; switches have grounded constructors; the current city emits keys and links. What is missing is a coherent way to bind these to a **player-facing design hypothesis**: what should be noticed, what decision should follow, what alternatives remain, and what evidence would show that the beat worked. A generic function label such as “ambush” will not establish that. [Door constructor](D:/Games/DOS/llmapper/bloodmap/doors.py:91), [switch constructor](D:/Games/DOS/llmapper/bloodmap/switches.py:94), [city mission implementation](D:/Games/DOS/llmapper/projects/blood-city/level/build_graph_slice2.py:1239)

The roadmap already proposes one source language and MechanismDecl. Its diagnosis of duplicated dialect adapters is plausible; its demand to rewrite multiple projects before further synthesis is not yet justified. First express one mechanism-and-goal relationship in two unlike maps using the existing source and constructors. Add only the declaration required by that exercise. Keeping two independent readers can also be useful for detecting compiler mistakes: shared source/read-back schemas should not become a reason to share every assumption and thereby make both sides wrong together. [Existing proposal](D:/Games/DOS/llmapper/docs/history/llmapper_level_understanding_handbook/09_IMPLEMENTATION_ROADMAP.md:5219)

Some current restrictions matter. Translation-only frames and face-coincidence rules can make relocation convenient but angled composition awkward. Raw callbacks and post-lowering passes expose ordering and allocation assumptions. Conversely, source-defined exceptions are necessary: a crypt may be unusually low, a gallery may have many dead ends, and an intentional vista may lie outside a corpus envelope. Retain those choices without requiring a project-specific exception for every unusual aesthetic decision. [LevelProgram limits](D:/Games/DOS/llmapper/docs/level-programs.md:149)

### Generalization: some real progress, insufficient outcome evidence

There is real generalization evidence below the design level. The vocabulary uses held-out episode examples. Material research found that contextual neighbor propagation predicts surfaces better than map-wide modal tiles, while held-out tile identity transfers poorly between episodes. The large usage cluster covering 99.9% of wall surfaces would have made a cluster-based transfer test vacuous; the repository explicitly catches that. These are good research outcomes because they limit what should be promoted. [Vocabulary provenance](D:/Games/DOS/llmapper/bloodmap/vocabulary.py:33), [surface transfer results](D:/Games/DOS/llmapper/knowledge/blood/design/README.md:144)

The second-map decompilation exercise also did useful work: it exposed five map-specific assumptions and removed hardcoded findings from reusable readers. But identical stage code copied into three project directories is reuse with duplication, not evidence of better design. The sleep-phase macro counts are predicted reductions in residue; the report explicitly says no constructor was added in that exercise. [Sleep-phase results](D:/Games/DOS/llmapper/reports/archive/sleep-phase-2026-09-03.md:17)

The BB6 reconstruction is especially relevant counterevidence. It preserved some high-level relations and all eight DM starts' connectivity, while losing fortress-scale interiors, material/shade language, irregular architecture, and mechanism richness. Its own conclusion is that the result remains a diagram of relations. BB2's earlier morphology improvement also coexisted with disconnected circulation until a stronger authored gate was introduced. Those are two examples of the same gap between descriptive structure and design competence. [BB6 comparison](D:/Games/DOS/llmapper/reports/archive/BB6-semantic-roundtrip.md:16), [BB2 v3 comparison](D:/Games/DOS/llmapper/reports/archive/BB2-semantic-roundtrip-v3.md:14)

The recent E3M1 “round trip” reproduces 4,298 of 123,280 fields from claims, copies 118,982, and reports zero misreadings. This is useful validation of the claims it actually computes. It is not a generative reconstruction of 96% of the map, nor a measure of understanding in player terms. Likewise, the residue census explains that its earlier claimed-share ranking mostly ranked wall count and that layer 2 supplied 96% of claims. Do not choose the next feature by the largest residue bucket. [Claim round trip](D:/Games/DOS/llmapper/projects/e3m1-decompiled/round-trip/E3M1.md:3), [residue metric critique](D:/Games/DOS/llmapper/reports/archive/residue-curve-2026-09-03.md:48)

Owner anchors are valuable supervised knowledge. A tile name supplied by a person is an interpreted label; a measured occurrence is a corpus fact; a city identity is an authored choice; an engine source rule is implementation truth. They must remain separate even when one file or test uses all four. Current city norms also draw on mixed Blood/Duke precedents, so they cannot all be advertised as facts extracted from Blood. Recurrence across records within one map is weaker evidence than recurrence across independent maps; hand-correcting those maps makes them development data, not untouched holdouts. [City norm provenance](D:/Games/DOS/llmapper/projects/blood-city/references/city-norms.md:3), [owner anchor catalog role](D:/Games/DOS/llmapper/knowledge/blood/design/README.md:19)

The next unknown map is the correct test unit. A transferable rule must improve its authoring or diagnosis while retaining intentional counterexamples. A growing count of human-origin regression tests establishes memory of past failures, not independent design ability.

## 6. Missing capabilities and silent failure modes

These are dimensions where the existing machinery may expose relevant ingredients but does not reliably complain that the experience is bad. An external LLM could sometimes notice them in images or prose; that capability has not been calibrated.

| A bad level could still… | Why existing green checks would not settle it | Most useful evidence |
|---|---|---|
| Have an objectively reachable exit that nobody knows to seek. | Reachability is not goal comprehension or wayfinding. | First-time player route, pauses, wrong turns, retrospective goal explanation. |
| Show a switch without communicating what changed. | TX/RX correctness says nothing about causal readability or off-screen feedback. | Before/action/after game sequence with sound and state deltas. |
| Place the right number of enemies in tedious or unfair encounters. | Inventory and density do not measure threat timing, crossfire, escape, or counterplay. | Real combat traces, resource use, deaths and player explanation. |
| Exhaust ammunition before a required fight despite a normal pickup/dude ratio. | Pickup identity, amount, accessibility, ordering and weapon effectiveness matter. | Resource trajectories along plausible routes and difficulties. |
| Have technically varied rooms that are perceptually indistinguishable. | Tile variety and room segmentation do not establish memorable landmarks. | Blind location recognition and navigation after a delay. |
| Alternate rooms without dramatic build-up, relief, or escalation. | Static topology and proportions discard sequence and elapsed time. | A full first-play route, beat timing, and player preferences. |
| Be overdecorated, visually noisy, or consistently bland. | Counts and typicality do not establish focal hierarchy or taste. | Route-based images and blinded visual comparisons. |
| Make a secret either arbitrary or impossible to miss. | Correct secret wiring does not establish a fair clue/reward relationship. | Unprompted discovery rate, clue interpretation, and reward evaluation. |
| Turn a dramatic drop into a frustrating one-way commitment. | A legal transition does not measure anticipation, loss of agency, or acceptable risk. | First-time play and comparison with an alternative layout. |
| Work at rest and fail after revisiting, closing a door, or triggering events in a different order. | One static state or a single witness does not cover reachable state combinations. | Bounded alternate action sequences and state-aware replay. |
| Sound wrong or feel lifeless despite attractive screenshots. | Static editor output has no auditory experience or live effects. | Game capture with audio, timing and player commentary. |
| Satisfy the brief's nouns without realizing its intention. | “Church,” “ambush,” “landmark,” and “shortcut” can all be labels attached to weak implementations. | Critique without those labels, followed by comparison to the intended experience. |

An unknown unknown cannot be enumerated completely. The missing meta-capability is a disciplined way to say **“the map appears wrong on a dimension this packet does not represent”**, obtain a distinguishing observation, and revise without first inventing a global rule. That requires open-ended visual/player critique and an evidence-request channel, not just a longer checklist.

Measure human dependence rather than pretending it can immediately disappear: count owner interventions, time spent, which important problems the LLM found first, which needed an owner hint, and whether an accepted correction transfers to the next brief. A human ranking a final pair is evaluation; a human repeatedly supplying the next metric is part of the generation system. Report those contributions separately.

## 7. Recommended near-term workflow

1. **Choose a complete 3–5 minute map brief.** State a player goal, two or three intended beats, one distinctive spatial idea, an encounter/resource plan, an optional reward, and a finish. Use a compact written design hypothesis; no new IR is needed.

2. **Choose a few precedents by purpose.** Retrieve an approach, encounter space, mechanism, or material treatment with images and context. Record which relationship is being borrowed and why. Do not import a whole-map percentile recipe.

3. **Author through one normal route.** Prefer LevelProgram plus the shared constructors, lowering through PlanarLayout/LevelIR. Keep native geometry and exceptional behavior accessible through clearly scoped escapes. Use existing city mission facts only where they help the actual brief.

4. **Compile and check engine/structural truth.** Reparse, validate, inspect supported motion states and required behavior. Make conditional assumptions explicit. An unavailable runtime check must prevent a “runtime verified” label without pretending the whole candidate failed structurally.

5. **Create an immutable candidate packet.** Bind source, compiler and engine revision, corpus/knowledge versions, MAP hash, view/state requests, raw outputs, and review. Never overwrite an iteration. When the evaluator changes, preserve the original decision-time evidence and add a separate reevaluation.

6. **Observe the experience, not only named rooms.** Give the critic a small route-ordered contact sheet or sequence: spawn, first choice, landmark approach, encounter start, action feedback, return path, optional discovery, exit. Include ordinary upward views and a few independently selected views. Capture actual game states/audio where relevant. If geometry moves, preserve old valid poses and also sample the new route; do not silently nudge a failed camera.

7. **Require an evidence-based critique with an open question.** Rank three concrete problems by player impact. For each: name the observed symptom, competing explanations, a minimal discriminating query, and a source-local proposed change. Explicitly ask what the current metrics might be missing. Allow “uncertain” and intentional exceptions. Retrieve raw evidence on demand rather than dumping a 173–286 KB pilot packet into every decision.

8. **Revise one high-impact hypothesis at a time.** Preserve a control version. Verify the intended native/source delta, the same experience segment, and unrelated invariants. Then obtain a brief blinded preference or playability check. Stop after the fixed experiment budget, including if it failed; do not redefine success by adding a convenient metric.

9. **Transfer only what earned its cost.** Save a contextual example and measured result. Promote a new constructor or rule only after it works in another unlike map and has a meaningful counterexample. A local repair may remain local forever.

This uses most of the existing foundation. The principal additions are outcome evaluation, immutable experiment identity, better evidence presentation, and a minimal runtime recording path. It does not require a general combat simulator, a new renderer, or a fully autonomous player.

## 8. The next three experiments

Run these in order. Fix the tooling and evaluation protocol before each experiment; do not tune the evaluator on its outcomes and then claim those outcomes as validation. The numerical thresholds below are proposed decision rules for small engineering experiments, not statistically established constants. Record model/settings, prompts, attempts, tool calls, elapsed time, human interventions, and artifact hashes. Use the same generation budget in paired conditions and preserve failures.

### Experiment 1 — Does the current feedback machinery improve maps people want to play?

**Hypothesis.** With equal authoring resources, the richer current feedback packet produces better complete levels than a lean workflow using the same construction tools, structural validation, and ordinary screenshots.

**Setup.** Prepare three unfamiliar, modest Blood briefs: for example a compact industrial infiltration, a vertical interior with a return shortcut, and an outdoor approach leading to a contained finale. None should be another monastery or Gravesend district. For each brief run two independent attempts per condition: six matched pairs, twelve final maps, each designed for 3–5 minutes of play.

Both conditions use the same model, shared constructors, normal source representation, initial asset access, fixed budget, initial build plus two revision opportunities, standard rendered route views, and the same safety/runtime completion checks. The rich condition additionally receives the current structured design/corpus packet and can request existing targeted probes within its budget. The lean condition receives validation and images without corpus percentile recommendations or hierarchy-discrepancy priorities. Randomize condition order and keep context isolated.

Three experienced Blood players independently play the anonymized final pairs in counterbalanced order. They answer the primary question **“Which map would you choose to keep playing?”**, and record atmosphere/identity, navigation, fairness, pacing, major defects, completion and hints required. Keep disagreement; do not collapse all categories into a synthetic quality score. Keep initial versions for a secondary blinded before/after comparison if the primary result warrants it. The owner supplies no mid-generation hints.

**Existing infrastructure.** LevelProgram/PlanarLayout, native and authored gates, mechanism helpers, existing observations and render poses, source diffing, candidate packets. Use human play and an existing game recording path; an autonomous bot is unnecessary.

**Minimal new work.** An immutable run manifest, a short fixed critic prompt, blind labeling/order, a compact rating form, and recording of completion/hints. Build only a tiny recorder adapter if the existing game/demo path cannot capture the needed sessions.

**Success criterion.** The rich workflow wins at least five of the six map pairs by a majority of the three players, and every rich candidate can be completed without a developer hint by at least two players. Preference explanations must identify improvements in the actual experience, not just greater detail or conformity. Report budget use and any failed attempts alongside the result.

**Failure criterion.** No preference advantage, gains confined to metric compliance, or repeated blockers that the rich packet claimed resolved. Four wins out of six is suggestive but inconclusive; expand to fresh briefs before architecture investment rather than declaring victory.

**Decision.** If successful, keep the packet and investigate which evidence drove the gain. If unsuccessful, freeze metric/ontology expansion and use the lean path while prioritizing the failure channels exposed by players. If both arms are poor, treat source capability or basic LLM design ability as the bottleneck; do not assume additional feedback infrastructure alone will rescue it.

This is the central product test. Until it exists, “the machinery improves map quality” remains a hypothesis.

### Experiment 2 — Can the critic discover an important problem it was not told to look for?

**Hypothesis.** An LLM with targeted image and runtime evidence can identify high-impact defects outside the current detector vocabulary, request discriminating observations, and repair them without an owner naming the missing dimension.

**Setup.** Assemble twelve short, structurally valid playable segments from six unfamiliar contexts: six with plausible experience defects and six sound or deliberately unusual controls. Include naturally occurring flaws from experiment 1 as well as controlled variants. Examples are off-screen action feedback, ambiguous objective signaling, an unfair entry fight, an unreadable landmark, a frustrating return journey, and excessive visual competition. Controls should include justified low ceilings, sparse decoration, orthogonal geometry, or dead ends, so the critic cannot succeed by penalizing every corpus outlier.

Before the critic runs, independent human players privately record high-impact issues and intent-sensitive acceptable exceptions; treat consensus as an evaluation reference, not universal aesthetic truth. Withhold these descriptions, variant identity, and any revealing labels from the critic. Use fresh context and frozen tools. Compare a packet-only critic with the same critic given route-ordered first-person images, short game/action traces, and a bounded ability to request additional views or probes. Both must state uncertainty and rank only their most important findings.

After an initial critique, allow one source revision for each faulty segment. Reviewers blind to the diagnosis and condition compare the original and revision in play. Preserve source-label-only counterfactuals for a few cases: changing “grand reveal” to “service corridor” should not change observations of what was rendered, although it can legitimately change conformance to the declared intent.

**Existing infrastructure.** Renderer requests, source/native joins, static and progression probes, packet references, mechanism/action evidence, small fragments and authored fixtures.

**Minimal new work.** A withheld issue/control sheet, a short evidence-request protocol, matched observation bundles, and a record distinguishing LLM-first discovery from owner-assisted discovery. Do not implement new detectors during the experiment.

**Success criterion.** The richer critic identifies at least 75% of the human-consensus high-impact defects, falsely rejects no more than one of the six sound controls, and its requested evidence resolves at least two issues outside the existing explicit metric vocabulary. At least four of six revisions are preferred in blind play without a new major regression.

**Failure criterion.** It repeats existing diagnostics, invents problems in intentional controls, cannot select a discriminating observation, or repairs measured symptoms without improving play. Finding an issue only after the owner supplies its name counts as assisted, not autonomous discovery.

**Decision.** If pictures/traces materially improve diagnosis, prioritize evidence delivery and selective visual reasoning rather than more metrics. If decisive evidence is unavailable, build that narrow sensor or recording capability. If evidence is present but judgement remains poor, keep an explicit human critique stage and collect examples; do not present the rule collection as an autonomous critic. If diagnosis works but repairs fail, representation/control becomes the next bottleneck.

This separates missing evidence, weak judgement, and weak repair. Without that separation, every bad result tends to be interpreted as a request for another abstraction.

### Experiment 3 — Does hierarchical source earn its complexity on an unfamiliar revision?

**Hypothesis.** The preferred tree/shared-constructor workflow reduces the cost and failure rate of meaningful cross-cutting edits, including mechanism changes, compared with a lean PlanarLayout-based source, without reducing expressive freedom.

**Setup.** Build matched starting versions of three unlike small designs: a street-facing shop, a vertically connected interior, and an irregular exterior encounter. Match intended geometry, mechanisms and player experience as closely as practical, documenting any representation asymmetry. One version uses LevelProgram and current shared constructors; the other uses compact flat source with the same native helpers. Both receive exactly the same feedback channels established in the earlier experiments.

Give each representation two unseen revision tasks per design, six matched tasks total: one changes space/ownership, such as moving and widening a wing while preserving its attached details and connections; one changes a player goal or mechanism relationship, such as relocating a key and changing the return route without breaking interaction or feedback. Include a deliberate off-axis or corpus-unusual design that must survive. Randomize task order and isolate model context.

Measure successful completion within a fixed budget, tool/time/token cost, raw native fields edited, source touched outside the intended scope, runtime behavior, and unintended semantic changes. Compare stable source objects and behavior, not raw index churn after compilation. Use the same small player check to guard against a structurally “local” edit worsening the experience.

**Existing infrastructure.** Local frames, faces, ownership, constructors, PlanarLayout, city mission sentences/read-back, compile reports, native diffs, rendering and bounded runtime checks.

**Minimal new work.** Three matched source pairs and a task/evaluation harness. Try adapting an existing city mission declaration to the unlike interior before introducing any new schema. If a tiny helper is essential, keep it local and record its cost; do not begin a repository-wide migration.

**Success criterion.** The tree workflow succeeds on at least five of six tasks, yields at least a 30% reduction in median revision effort at comparable success, and preserves all required behavior without extra expert intervention or a perceptual quality penalty. The same mechanism declaration/helper must transfer to at least two unlike designs without map-name or sector-ID special cases.

**Failure criterion.** Equal or worse effort, frequent raw callbacks and stage-specific repairs, dialect-specific adapters proliferating, or expressive restrictions that force the design into formulaic geometry. A result where the tree wins spatial edits but not mechanism edits is a useful partial result, not a mandate for an entirely new IR.

**Decision.** If successful, standardize this path and retire duplicate author-facing routes incrementally. If only a small mission wrapper transfers, promote that wrapper. If unsuccessful, keep the smallest useful ownership/frame facilities and simplify the rest; do not complete the proposed universal declaration system on architectural faith.

## 9. Immediate work plan: NOW → NEXT → LATER → DO NOT DO YET

### NOW — restore a credible baseline, then stop polishing it

**Episode 1: bind evidence to artifacts.** Recover the original v5 MAP/source/toolchain from history as an immutable historical experiment, and give its later expansion a new identity. Pin or clearly label v0–v4's historical compiler rather than silently replacing their outputs. Register the full Gravesend map and current slice as different artifacts. Every visible report should identify the MAP hash, source revision and evaluator revision it actually describes. Preserve the original decision-time packet separately from any new reevaluation.

**Episode 2: make one chosen small candidate rebuild and play.** Decide whether to repair the v5/v7 sweep failure because that candidate will be used, or archive those versions as currently incompatible. Do not fix every historical experiment. Use the already reproducible city slice as a mechanism/construction control, not as evidence of a complete fun level. For the experiment map, verify its actual critical action sequence and exit in the game, with a human or bounded driver.

**Episode 3: make the audit/experiment profile honest.** Document the optional test dependencies and separate synthetic, corpus, artifact and runtime checks. Require the active benchmark's required assets explicitly rather than accepting skipped checks. Resolve missing decisive fixtures if that benchmark needs them; do not reconstruct a lost oracle from prose and call it the same ground truth. Correct the pilot test coverage claim and run artifact/source/packet binding checks on the active experiment set.

These are bounded completion tasks. Their exit condition is one reproducible baseline and a trustworthy comparison protocol, not a clean result for every old subsystem.

### NEXT — run the three experiments

Run experiment 1 first. Use its actual failures to populate experiment 2. Use experiment 3 to decide how much source-language consolidation earns investment. Keep owner intervention visible. Establish preference, diagnosis and revision baselines before approving more generic mining, another city phase, or a new IR.

### LATER — invest only where the experiments identify a bottleneck

If quality improves, broaden to longer routes, more varied encounter types, different difficulties and additional authors/players. Promote proven source helpers. Add narrow runtime state observations or visual understanding where missed defects demonstrate a need. Revisit learned contextual vocabulary and human preference examples after there is a dataset with genuine holdouts. Revisit autonomous play only if human/scripted recording has become the throughput bottleneck.

### DO NOT DO YET

Do not expand Duke/Doom conversion, pursue complete native-map decompilation, add a general combat simulator, implement broad recursive knowledge growth, run larger QD searches, fit a richer quality classifier, migrate every project to MechanismDecl, or finish the full Gravesend content plan to meet statistical targets. None currently has evidence of being the shortest path to a better next Blood map.

### Important unfinished work, classified

| Item | Classification | Reason / concrete action |
|---|---|---|
| Pilot v5 artifact/packet mismatch and unversioned continuation | **Finish now** | Recover the historical binding; separate later source/artifacts. This is necessary experimental hygiene. |
| Current v5/v7 motion-sweep compilation failure | **Finish now if selected; otherwise postpone** | Repair one active benchmark, or explicitly archive it. No green claim for a source that no longer builds. |
| Full city versus current slice, stale counts and circuit reports | **Finish now** | Identify artifact scope, regenerate only the active status, mark older reports historical. The modified plan report currently has a sewer-entry MISS despite older 16/16 claims. |
| Older whole-graph junction refusal and `build_streets_slice2.py` path | **Superseded on the current path; archive the duplicate** | The newer `build_graph_slice2`/`compile_city` rebuild succeeds exactly. Do not act on the old “STILL OPEN” paragraph without reproducing it. |
| Test dependency/profile ambiguity | **Finish now** | State optional Shapely/Matplotlib requirements for the overlap tooling and distinguish missing evaluation from success. |
| Lost casket/AGTST oracle assets | **Needs a different experiment before deciding** | Restore by verified backup if available; otherwise create new labeled controls only for required behavior. Do not spend the next phase reconstructing an entire lost bot curriculum. |
| Stack-linked casket construct expected failure | **Postpone** | A real incomplete reading, but not a prerequisite unless the next map requires this composition. |
| Three Doom semantic expected failures | **Postpone under frozen cross-game scope** | They concern another product direction. Retain explicit limitations and tests. |
| Turnstile passage proof | **Needs a different experiment before deciding** | The current autonomous driver cannot answer it. A controlled human/scripted crossing with positive/negative controls is the appropriate next proof if the map requires that door. |
| E2M3 complete emitted-program round trip / native escapes | **Postpone** | Useful reconstruction research; no evidence it is required to author excellent new maps. |
| Surface/Frame residue coverage and broad census expansion | **Needs a different experiment before deciding** | Residue reduction is not player improvement. Implement only what a tested edit/quality failure requires. |
| MechanismDecl and compulsory all-project source migration | **Needs a different experiment before deciding** | Experiment 3 should determine the smallest reusable declaration and its value. |
| City-local material, key, switch, wet-prop duplication | **Remove or merge incrementally** | The handoff already identifies the owners and defects. First preserve the old build; then remove parallel implementations rather than adding another routing document. |
| Four planned venues, skyline/detail expansion, density targets | **Postpone** | Complete a small good level before enlarging an unvalidated city. |
| Original decompiler Python literal as advertised editable source | **Superseded; remove from the author-facing workflow** | Keep as a historical inspection/export path if needed; advertise the real builder emitter instead. |
| Bigger QD/archive search and discriminator optimization | **Remove from the critical path** | The 64-candidate BB2 search tests feasibility under narrow perturbations, not quality search. |

Sources: [pilot test scope](D:/Games/DOS/llmapper/tests/test_monastery_pilot.py:11), [current compile probe](D:/Games/DOS/llmapper/reports/archive/independent-audit-2026-09-09/city-probe.json), [old junction refusal](D:/Games/DOS/llmapper/docs/history/llmapper_level_understanding_handbook/09_IMPLEMENTATION_ROADMAP.md:4875), [lost assets](D:/Games/DOS/llmapper/reports/archive/corpus-recovery-2026-09-01.md:1), [casket expected failure](D:/Games/DOS/llmapper/tests/test_attested_constructs.py:120), [Doom expected failures](D:/Games/DOS/llmapper/tests/test_doom_semantics.py:71), [passage blocker](D:/Games/DOS/llmapper/reports/blood-passage-oracle.md:109), [city duplication](D:/Games/DOS/llmapper/projects/blood-city/reports/handoff.md:63), [QD scope](D:/Games/DOS/llmapper/reports/archive/BB2-semantic-roundtrip-v3.md:88).

### Verification performed for this audit

- Read the main README/architecture/roadmap/authoring-loop documentation, construction and source representations, visual/experience documentation, historical verification, pilot reports/source/tests, BB2/BB6/SP evidence, city source and recent reports, decompilation/census/round-trip work, bot documentation/code boundaries, and recent git history. Searched implementation/tests/experiments for TODOs, stubs, skips and expected failures; important incompleteness is predominantly in reports, unsupported capability declarations and skipped fixtures rather than TODO markers.
- Counted **133 Python files / 79,614 lines** in `bloodmap`, **145 / 36,318** in tests, **72 / 19,695** in tools, **11 / 2,547** in experiments, and **119 / 47,935** in projects. These include generated/project code and are scope measurements, not a claim that a certain fraction is waste. Static AST inspection found 2,186 test methods; that is distinct from executed unittest entries.
- Ran `python -m unittest discover -s tests -v` with the default Python 3.10.11: **2,172 tests in 400.925 seconds; FAILED with one import error, 27 skips, four expected failures**. The import error is `test_sector_overlap` → `tools.build2d_core` → missing `shapely`. No failing assertions were reported among loaded tests. This is not a fully green suite. The bundled alternate runtime also lacks Shapely; nothing was installed or modified to hide the gap.
- Two historical-fixture tests initially skipped because child git commands encountered repository ownership protection, not because commit `8c42701` was absent. Re-ran their two test classes with process-local `safe.directory`: **11 tests passed**. Other skips include missing owner-created oracle maps and uncommitted fragments. The rerun does not retroactively make the full run green.
- Parsed and natively re-encoded eight monastery MAPs plus the full city and current slice; measured hashes, counts and native diagnostics; compared all available pilot packets to their artifacts. Compiled v0 twice, attempted v5/v7, and compiled the current city slice in memory without invoking its report-writing main function.
- Inspected the saved v2/v5 chapel pictures and the recent city street/church diagrams directly. Reviewed other visual evidence through its records and reports. No claim of personally playing the maps or inspecting every frame is made.
- Tested the discriminator function with two small synthetic feature-vector counterexamples. These establish mathematical limitations of the statistic, not a measured human quality difference.

Supporting artifacts: [measurements](D:/Games/DOS/llmapper/reports/archive/independent-audit-2026-09-09/measurements.json), [city probe](D:/Games/DOS/llmapper/reports/archive/independent-audit-2026-09-09/city-probe.json), [discriminator probe](D:/Games/DOS/llmapper/reports/archive/independent-audit-2026-09-09/discriminator-probe.json), [full unittest log](D:/Games/DOS/llmapper/reports/archive/independent-audit-2026-09-09/tests.txt), [historical-fixture rerun](D:/Games/DOS/llmapper/reports/archive/independent-audit-2026-09-09/git-fixture-tests.txt).

## 10. Final challenge: delete 50% of the conceptual machinery

I would keep five things:

1. **Blood engine truth:** the exact codec, LevelIR, native semantics, validators and narrowly calibrated runtime checks.
2. **One practical authoring path:** hierarchical Python ownership and local frames, a small shared construction vocabulary, PlanarLayout lowering, and a documented escape hatch.
3. **Evidence a designer can use:** selected structural/spatial queries, source-attributed rendered images, and actual game action/play traces.
4. **A compact precedent library:** architectural, material and mechanism examples with context, images, provenance and known limits.
5. **A disciplined revision experiment:** immutable candidate identities, explicit hypotheses, bounded repairs, blinded player comparison, and a record of human help.

I would remove from the active product model the cross-game conversion agenda, complete decompilation as a prerequisite, a broad persistent “experience” theory, recursive ontology growth, corpus conformity as an objective, quality-diversity search before a valid evaluator, the full autonomous-bot prerequisite, coequal source dialects, duplicated city vocabularies, and comprehensive reconstruction of original maps as a proxy for generation.

This is conceptual deletion, not indiscriminate removal of half the source files. Existing adapters and dependencies can remain as frozen internals; historical evidence must remain reproducible. I would collapse the user-facing task to: **author a place, compile it reliably, observe what a player experiences, make a justified change, and demonstrate that someone prefers the result.**

I would make that cut because the scarce capability is now design judgement and successful transfer to the next map. Keeping exact engine truth and local editability makes improvement possible. Keeping far more machinery than the experiments can justify makes it easier to postpone finding out whether that improvement is happening.
