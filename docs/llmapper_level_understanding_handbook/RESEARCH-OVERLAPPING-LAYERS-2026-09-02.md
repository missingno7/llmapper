# Research: representing a level as overlapping graphs (2026-09-02)

Owner's question: a Blood map is many overlapping layers and links at
once (space, surfaces, joins, islands, light, mechanisms, keys, edges,
plan, intent), E3M1 already overlaps them heavily and a Death Wish map
is an order of magnitude denser. How do other fields represent this,
especially where a machine designs or recovers architecture, and what
should we take?

Supervisor's research over the published literature, with what each
model gets right, what it would cost us, and a design at the end.
Section 28 of `projects/blood-city/reports/street-model-decisions-2026-09-02.md`
stated the model (records, aspects, channels, links, one ledger); this
document grounds it and sharpens it.

## 1. Seven models from other fields

### 1.1 Multilayer / multiplex networks (network science)

A multilayer network is several graphs, the layers, over ONE shared set
of nodes, differing in their edges; multiplex when inter-layer edges
only connect a node to itself in another layer. Higher-order variants
(hypergraphs, simplicial complexes, incidence/bipartite forms, tensors)
exist for relations that are not pairwise.

- **Right:** exactly the owner's phrase, "differently overlapping
  graphs". The node set is fixed (our records); each aspect is a layer
  with its own edge kind; a mechanism's tx -> rx chain, a join, a
  stack link, a frame shared by a run of walls are edges of different
  layers over the same records. An n-ary thing (one trigger, five
  receivers, one condition) is a hyperedge, not five edges.
- **Cost:** the mathematics is for measurement (communities,
  centrality), not for authoring. Take the vocabulary and the
  invariant, not the toolkits.
- Sources: [Multilayer and multiplex networks: an introduction](https://pmc.ncbi.nlm.nih.gov/articles/PMC7500177/),
  [Multilayer networks: aspects, implementations](https://link.springer.com/article/10.1186/s41044-020-00046-0),
  [Representing higher-order networks: a survey](https://arxiv.org/pdf/2605.12509).

### 1.2 IFC / buildingSMART: objectified relationships (BIM)

The Industry Foundation Classes model every relationship between
building objects as an OBJECT of its own (`IfcRelationship`), with its
own attributes: `IfcRelAggregates` (whole/part, unordered),
`IfcRelNests` (ordered parts), `IfcRelConnects` (two objects touch),
`IfcRelVoidsElement` (an opening cut into a wall), `IfcRelFillsElement`
(a door or window filling that opening), `IfcRelDefinesByProperties`
(a property set attached to an object, directly or via its type).

- **Right:** this is our aperture grammar and join grammar already
  named by a standards body: a facade is a wall, an opening VOIDS it,
  an insert FILLS the opening, and both are relationships with
  evidence, not fields on the wall. A join between two surfaces is a
  `Connects` relationship with the join class as its attribute.
  Property sets by type (all curtain doors share defaults) then by
  occurrence (this one differs) is the campaign-defaults / curated-
  precedent split of section 22.
- **Cost:** IFC as a whole is enormous. Take the relationship taxonomy
  and the rule "a relation is a record with attributes", nothing else.
- Sources: [IfcRelationship](https://standards.buildingsmart.org/IFC/RELEASE/IFC4_3/HTML/lexical/IfcRelationship.htm),
  [IfcRelAggregates](https://ifc43-docs.standards.buildingsmart.org/IFC/RELEASE/IFC4x3/HTML/lexical/IfcRelAggregates.htm),
  [IfcRelDefinesByProperties](https://standards.buildingsmart.org/IFC/RELEASE/IFC4/ADD1/HTML/schema/ifckernel/lexical/ifcreldefinesbyproperties.htm).

### 1.3 ISO/IEC/IEEE 42010: viewpoints, views, correspondences

An architecture description is a set of VIEWS, each governed by a
VIEWPOINT that frames specific concerns; relations between elements of
different views are MODEL CORRESPONDENCES (n-ary), governed by
CORRESPONDENCE RULES; the standard requires that known inconsistencies
across views be RECORDED, with an analysis of consistency.

- **Right:** our aspects are views; the channel table (additive /
  exclusive) is the set of correspondence rules; the residue and
  conflict ledger is the record of known inconsistencies the standard
  demands. The important norm: an inconsistency is a recorded fact
  with an owner, not something the model hides by picking one side.
- **Cost:** none; it is a discipline, not software.
- Sources: [ISO/IEC/IEEE 42010 conceptual model](http://www.iso-architecture.org/ieee-1471/cm/),
  [Architecture frameworks](http://www.iso-architecture.org/ieee-1471/afs/),
  [Every architecture description needs a framework](https://www.researchgate.net/publication/224605964_Every_Architecture_Description_Needs_a_Framework_Expressing_Architecture_Frameworks_Using_ISOIEC_42010).

### 1.4 Fact stores and Datalog: program analysis and decompilation

CodeQL, Souffle-based analyses and modern decompilers keep an
EXTENSIONAL database of base facts extracted from the artifact and an
INTENSIONAL database of derived facts produced by rules, evaluated
bottom-up to a fixpoint; every derived fact carries provenance. The
2026 "superset decompilation" work (Manifold) goes one step further
for exactly our problem: rather than committing to one interpretation
early, it "retains ambiguous interpretations as parallel candidates
with provenance, deferring resolution until the final selection
phase", over a relation store that only grows.

- **Right:** this is the decompiler architecture we should have. The
  map's records are the EDB. Every reader is a rule set: it reads
  facts and emits facts (`surface(S, walls...)`, `frame(S, u0, scale)`,
  `join(W, class)`, `island(I, sectors, step)`, `shade_depth(sector, k)`,
  `sentence(M, kind, roles...)`), each with the facts it was derived
  from. Claims on record fields are facts too. Ambiguity (a wall that
  two surfaces could own; a shade edge at the sun's bearing that could
  also be a lamp's) is kept as candidates and resolved in a named pass
  with a stated criterion, never inside a reader. Our multi-view
  bundle already keeps disagreements as the deliverable; this makes
  that formal and cheap.
- **Cost:** low if done as Python predicate tables (lists of tuples
  per predicate, JSONL on disk); high if we adopt a Datalog engine.
  Do the former.
- Sources: [Superset decompilation](https://arxiv.org/pdf/2603.28002),
  [Towards fully declarative program analysis](https://arxiv.org/pdf/2112.12398),
  [Datalog and recursive query processing](https://www.researchgate.net/publication/267666768_Datalog_and_recursive_query_processing).

### 1.5 Mission graph and space graph (Dormans; Sturgeon)

Dormans splits an action-adventure level into a MISSION graph (the
tasks, locks and keys, in player order) and a SPACE graph (where they
happen), generates the mission with a generative graph grammar, then
rewrites it into a space graph and into geometry with a shape grammar;
the two stay consistent because one is produced from the other.
Sturgeon generates tile levels under learned and designed constraints
with a reachability template and, in MKIII, emits an example
playthrough together with the level as proof of completability.

- **Right:** a Blood map has both graphs and they are NOT the same
  tree: the collapsing house in E3M1 is one mission node whose records
  sit in three places of the space tree. Keep them as two graphs with
  an explicit correspondence. Decompilation recovers the mission graph
  from the link relations (tx/rx, keys, conditions, stacks) and the
  conditional topology; the playthrough as proof is what our bot and
  the NBlood oracle are for, later.
- **Cost:** none new; it names what `conditional.py` and the mechanism
  sentences already produce and says where to keep it.
- Sources: [Adventures in level design (Dormans 2010)](https://pcgworkshop.com/archive/dormans2010adventures.pdf),
  [Level design as model transformation](https://www.researchgate.net/publication/228747742_Level_design_as_model_transformation_A_strategy_for_automated_content_generation),
  [Sturgeon](https://ojs.aaai.org/index.php/AIIDE/article/view/21944),
  [Sturgeon-MKIII](https://dl.acm.org/doi/10.1145/3582437.3587205).

### 1.6 Programs for shapes: ShapeAssembly, ShapeMOD, DreamCoder, Szalinski, InverseCSG/CADFit, FacAID

A family of results on recovering EDITABLE PROGRAMS from geometry:
ShapeAssembly writes a shape as a hierarchical program of parts and
attachments with continuous parameters; ShapeMOD discovers MACROS
(reusable sub-programs) across a corpus of such programs and shows
inference gets more valid with them; DreamCoder alternates a wake
phase (infer programs) with a sleep phase (refactor the programs found
and abstract common components into a growing library); Szalinski uses
equality saturation to shrink flat CSG into small programs with map and
fold; InverseCSG and CADFit fit parametric operations incrementally
with geometric validation feedback; FacAID recovers a split grammar for
facades.

- **Right:** this is our writer/reader symmetry as a research
  programme, and it says how the vocabulary should grow: decompile
  several maps into programs (wake), then refactor the PROGRAMS to
  discover the macros they share (sleep), and measure that the next
  map's residue drops. Shrink the program, never the map (Szalinski).
  Fit one sentence, validate it by recompilation, then the next
  (CADFit) is the per-sentence version of our recompile-and-diff gate.
  Facades as split grammars is section 6d's facade-with-openings.
- **Cost:** the learned parts (VAEs, transformers) are not for us; the
  symbolic loop is, and it is cheap: a macro is a Python function two
  decompiled maps both needed.
- Sources: [ShapeAssembly](https://arxiv.org/abs/2009.08026),
  [ShapeMOD](https://arxiv.org/pdf/2104.06392),
  [DreamCoder](https://dl.acm.org/doi/10.1145/3453483.3454080),
  [Szalinski (equality saturation for CAD)](https://arxiv.org/abs/1909.12252),
  [InverseCSG](https://dl.acm.org/doi/abs/10.1145/3272127.3275006),
  [CADFit](https://arxiv.org/html/2605.01171v1),
  [FacAID](https://arxiv.org/html/2406.01829).

### 1.7 CGA shape grammar, CityGML, and floor-plan generators

CityEngine's CGA rules refine SHAPES that each carry a SCOPE, a local
oriented frame, so every rule works in its own coordinates; CityGML
gives every city object several representations at levels of detail
LoD0-3 and splits the model into a core plus thematic modules
(Building, Transportation, WaterBody, CityFurniture ...). Floor-plan
generators (Graph2Plan, House-GAN, HouseLLM/HouseTune 2024-25) all
work in two stages: a BUBBLE DIAGRAM graph (rooms as nodes, adjacency
and doors as edges) first, geometry second, with the language model
writing the graph, not the geometry.

- **Right:** scope = our Frame (section 6d); LoD = an explicit index we
  should put on every sentence (plan LoD0, massing LoD1, facades LoD2,
  inserts and dressing LoD3); thematic modules = aspects; and the
  two-stage plan-then-geometry is what `city_plan.py` and the
  envelope solver already do, confirmed as the shape every AI layout
  system converges on.
- **Cost:** none; adopt the LoD index and the naming.
- Sources: [CGA introduction](https://desktop.arcgis.com/en/cityengine/2017/cga/cityengine-cga-introduction.htm),
  [CityGML 3.0 conceptual model](https://docs.ogc.org/is/20-010/20-010.html),
  [House-GAN](https://arxiv.org/pdf/2003.06988),
  [Graph2Plan](https://www.researchgate.net/publication/343625455_Graph2Plan_learning_floorplan_generation_from_layout_graphs),
  [HouseTune](https://arxiv.org/pdf/2411.12279),
  [Layout generation for building design: a review](https://arxiv.org/html/2504.09694v1).

### 1.8 Entity-component systems (game engines)

An entity is an id; components are pure data, one per aspect; systems
run over every entity that has the components they need.

- **Right:** the runtime shape of the ledger. Record = entity, claim =
  component, reader or writer pass = system. Nothing is a subclass of
  anything; a sector under a sun shadow with a light wave and a key
  lock simply has four components.
- Sources: [Entity component system](https://en.wikipedia.org/wiki/Entity_component_system).

### What NOT to take

Knowledge-graph memory for LLM agents and GraphRAG are about retrieval
for chatbots, not about representing a designed artifact; GAN and
diffusion floor-plan generators produce pixels or boxes, not programs;
full IFC or full CityGML would drown the project in schema. The
literature converges on the symbolic parts above.

## 2. What it means for us: the design, sharpened

The section-28 model stands; the literature adds five sharpenings.

1. **The map is a fact store.** Base facts are the records' fields, as
   stored: `sector(i, floor_z, ...)`, `wall(j, ...)`, `xsector(i, ...)`,
   `sprite(k, ...)`. Readers are pure functions from facts to facts and
   never mutate anything. Derived facts carry provenance: the facts
   they came from and the reader that made them. The store only grows
   within a decompilation run; a later pass may SELECT among
   candidates but never delete a fact. JSONL per predicate, a Python
   dict of tuples in memory; no engine.
2. **Relations are records.** Join, void (opening), fill (insert),
   link (tx -> rx), stack, key, condition, attachment (a run of walls
   sharing a frame) are predicates with attributes and evidence, in
   the IFC sense. An aspect's tree is itself a set of `part_of`
   facts, so hierarchy is one relation among many and two hierarchies
   can coexist.
3. **Two graphs, one correspondence.** The space graph (`part_of`,
   `connects`) and the mission graph (`link`, `key`, `condition`,
   `sentence`) are kept apart, and `realises(sentence, records...)`
   is their correspondence. Decompilation reads the mission graph off
   the link relations; the playthrough proof is deferred to the bot.
4. **Claims are the ledger, per channel.** `claims(aspect, record,
   field, value_or_contribution, evidence)`. On an additive channel the
   contributions must sum to the record; on an exclusive channel there
   must be exactly one claim. Residue = fields without a claim;
   conflict = exclusive fields with two. Both are RECORDED facts with
   owners (42010), never resolved silently. Ambiguous readings are
   kept as `candidate(...)` facts and resolved by a named selection
   pass with a stated criterion (Manifold).
5. **The vocabulary grows by refactoring programs, and is measured.**
   After each decompiled map: refactor the programs found so far,
   promote what two maps both needed to a macro (a Python constructor
   in `bloodmap`), re-run every reader over every decompiled map, and
   record residue per map per layer. The language is done when a new
   map's residue under the existing readers is small; its tail names
   the next macro. Every sentence carries its LoD.

## 3. Concrete recommendations

Now, for P15 (E3M1):

- `residue-ledger.json` becomes a fact store: one JSONL file per
  predicate under `projects/e3m1-decompiled/facts/`, with `claims`,
  `candidate`, `conflict` and `residue` as predicates like any other,
  each row with provenance. The percentages the reports quote are
  queries over these files, computed by one script, not typed.
- Every reader is a function `facts -> facts` in `bloodmap` with no
  side effects; the E3M1 project only orchestrates and stores.
- Relations get their own predicates from layer 3 on: `join`, `void`,
  `fill`, `link`, `key`, `stack`, `attachment`; the space tree is
  `part_of` facts; a mechanism sentence is `sentence` plus
  `realises`.
- The review pack shows one aspect's facts at a time; the fact panel
  of a record lists its claims, candidates and unclaimed fields.

Later, when four maps are decompiled (milestone B):

- the sleep phase: a refactoring pass over the four programs that
  proposes macros, with the residue curve per map as its acceptance
  test; a macro that does not lower residue on at least two maps is
  not adopted;
- the mission graph gets its proof: the bot or the NBlood oracle plays
  the recovered mission graph and the reachability template of the
  conditional topology is checked against a real run (Sturgeon-MKIII).

What we do not build: a Datalog engine, a knowledge graph service, a
learned inference model, or a full IFC schema.
