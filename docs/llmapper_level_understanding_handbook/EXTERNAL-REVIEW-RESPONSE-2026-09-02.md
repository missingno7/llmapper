# External review of f6247f5: what is adopted, where it goes, what is not (2026-09-02)

The owner had a second AI review the repository at commit f6247f5. Its
thesis: the project has sensors and miners enough; what it lacks is a
closed learning loop that discovers a recurring relation by itself,
verifies it, names it, stores it and delivers it back to the author.
The supervisor's verdict per point, checked against the code and the
decisions taken since (sections 20-29 of the street-model decisions
document, the research document on overlapping layers).

Verified on the way: there is no `verify-project` command; the pattern
zoo registry has no lifecycle status field; `plan_review.py` writes its
plot to `references/plots/` without creating the directory; the tests
reach the corpus in 158 places with 119 skip guards, so a clean
checkout without `maps/` is not guaranteed to skip cleanly.

| # | proposal | verdict | where it lands |
| --- | --- | --- | --- |
| 10 | one reproducible project gate, `verify-project`; clean checkouts skip cleanly | **adopt now** | P16, its own agent, this week |
| 5 | one Construct/Sentence schema for reading and writing | **already decided**, now concrete | fact store: P14b slice 3 item 1 and 5; P15 facts/ |
| 7 | conditional norms, never a global average | **already the rule**, made explicit | section 22 gets the sentence "every norm is conditioned on a context" |
| 6 | `design-context` delivering knowledge to the author; manifest records requested / retrieved / selected / ignored / precedents / readback | **adopt, after the fact store** | slice 4 of P14b: provenance facts `used_constructor`, `precedent`, `alternative_ignored`; then the command over facts |
| 2 | LLM interprets evidence packets, never coordinates | **adopt as a rule** | review pack and owner queue: a candidate arrives as a packet (recurs-in-maps, roles, relations, representatives, counterexamples, unknowns) |
| 1 | discovery frontier: invariant graphlet mining, counted per independent map, with counterexamples, Pareto front | **adopt, sequenced after readers** | milestone B, after P15 layer 4; runs over DERIVED facts, never raw sectors; acceptance = blind rediscovery |
| 3 | concept lifecycle state machine with propagating review actions | **adopt, small** | a `status` on registry entries and on facts; review-pack marks are the actions confirm / reject / split / merge |
| 4 | recursive learning: confirmed concepts become atoms | **already planned** | research document section 2.5 (sleep phase) and section 6d's aperture hierarchy |
| 8 | visual learning from grounded views | **later**, blocked | no observer runs in agent loops (editor never launched); parked with the eye-level renders |
| 9 | stateful / experiential patterns; bot not a witness yet | **agree**, later | parked with the bot |

## Why the frontier waits for the readers

The reviewer is right that `tools/mine_patterns.py` and `bloodmap.patterns`
only find what they were told to look for. But mining graphlets over
raw sectors, sprites and tiles is what produced this project's worst
misnamings (the embedding field misnamed 40% of mechanisms; two
contrasts came back empty because hidden switches are closet wiring).
A graphlet is only invariant if its nodes are the right nodes:
surfaces, openings, inserts, joins, islands, field depth, sentences.
Those are exactly the derived facts P15's readers produce. So the
frontier runs over the fact store, with the reviewer's invariances
(no sector numbers, no absolute position, no rotation, material role
instead of tile id, ratio instead of size) applied to fact tuples, and
counts INDEPENDENT MAPS, not occurrences. Its acceptance test is the
reviewer's: rediscover storefront bay, turnstile and parapet blind,
transfer to a held-out map, separate counterexamples; only then remove
the hint and look at what is new.

## What the fact store already gives the reviewer's points 3, 5 and 6

- Point 5's `ConstructDecl` is `sentence` + `realises` facts written by
  the compiler and read back by the readers; conformance is a diff of
  two fact stores.
- Point 6's manifest is provenance facts in the same store; the
  "13 of 31 modules, 1 of 20 knowledge files, doorswitch.py rewritten"
  finding becomes a query (`used_constructor` against the registry)
  instead of an audit.
- Point 3's lifecycle is a `status` column on facts and registry rows,
  and the review pack's marks are the transitions.

## P16 prompt: the reproducible project gate

```text
You are P16, "project gate", a new Opus agent on the llmapper repo
(D:\Games\DOS\llmapper), branch blood-city-arcade, in your own
worktree on a branch project-gate. Read
docs/llmapper_level_understanding_handbook/10_AGENT_EXECUTION_PROTOCOL.md
(the section "Irreplaceable local data" is binding) and
docs/llmapper_level_understanding_handbook/EXTERNAL-REVIEW-RESPONSE-2026-09-02.md.
Hard rules: no directory deletes ever, no junctions or symlinks, never
launch NBlood or xmapedit, BLOODMAP_CORPUS set to the ABSOLUTE path of
D:\Games\DOS\llmapper\maps\blood, commit by file name, never git add
-A, never commit maps/ or reference/, suite to a log file and the Ran
line verbatim, trailer Co-Authored-By: Claude Opus 5
<noreply@anthropic.com>. Do not touch bloodmap/overlay.py,
light_field.py, joins.py, surface.py, planar_layout.py, pipeline.py
or anything under projects/blood-city/level/ -- P14b owns those.

1. `python -m bloodmap verify-project projects/blood-city` builds the
   project's current map in a temporary directory under the
   scratchpad (never in the project tree), regenerates every report
   the project declares in project.json, compares each regenerated
   report with the committed one and REFUSES stale ones by name,
   runs conformance and readback, prints which layers were available
   (corpus present? which populations? NBlood oracle present?), and
   exits non-zero on any refusal. Fail-first: commit a report with
   one number changed and watch it refused. Every project under
   projects/ that has a project.json gets the same gate; those that
   cannot build yet report "no build entry" rather than passing.
2. `plan_review.py` and any other script that writes under
   references/ create their output directory; run each once from a
   clean temporary copy of the project.
3. Clean checkout: run the suite with BLOODMAP_CORPUS pointing at an
   EMPTY temporary directory and with maps/ absent from the checkout
   (a git worktree without the corpus, no junction). Every corpus
   test must SKIP with a reason naming the corpus, never error or
   fail; fix the guards in tests/helpers.py or the tests themselves,
   never by weakening an assertion. Report the Ran line of both runs
   (with corpus, without) verbatim.
4. A `status` field on projects/pattern-zoo/registry.py entries with
   the values candidate / supported / reviewed / authoring_capable /
   regression_protected / superseded, defaulting from what the
   registry already knows (a constructor with a conformance test is
   regression_protected; a SKIP entry is candidate); a test that every
   entry has one.

Stop and report: which reports were stale at HEAD and why; the two
Ran lines; the skip reasons added; the registry status census. Owner
questions to reports/owner-review-queue.md with a recommended default.
```
