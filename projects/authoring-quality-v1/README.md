# First controlled quality experiment

Status: protocol prepared 2026-09-09; no player preference result exists yet.
The independent audit is `reports/independent-audit-2026-09-09.md`.
Do not expand the discriminator or hierarchy framework before testing whether
its feedback helps an author produce a better playable map.

## Question and fixed brief

Does the rich authoring packet improve player preference compared with rendered
views plus hard validation, at equal authoring budget?
Build a compact Blood encounter: entry courtyard, one interior route and one
alternate route, a clearly signposted key and exit, one escalating combat sequence,
and a recognizable landmark visible before and after the detour. Target 3-5 minutes
of first-time play. Use the existing authoring APIs and the same asset set. Do not
add new general-purpose APIs during this experiment.

## Paired procedure

1. Prepare three identical starting specimens satisfying the brief's structural
   skeleton. Save source, compiler, assets and MAP hashes before treatment assignment.
   Neither the historical empty monastery nor the enemy-free city slice is a
   completed gameplay specimen; they are only construction controls.
2. For each specimen, make two isolated copies and randomly assign feedback A/B.
   A receives hard validation and the same fixed rendered viewpoints. B also
   receives the rich hierarchy, corpus and discrepancy packet. Both receive the
   same brief, source access, model/settings and 30-minute revision budget.
   Keep assignments outside the authoring contexts and player-facing filenames.
3. Allow one revision cycle per copy. Record wall time, model/tool budget when
   available, all edits and compile failures. Save a fresh run for every evaluation;
   never reuse a run ID or attach another MAP's review. Freeze all six MAPs before
   collecting preferences. Do not discard failed or unattractive outputs.
4. Have three independent players play each matched pair in counterbalanced order,
   with neutral randomized labels. Record completion, time, deaths, navigation
   stalls and forced resets. Ask which map they would replay and why before
   revealing either treatment. A runtime smoke test cannot replace these sessions.
   Do not launch NBlood automatically under the current local owner restriction.
5. Report all nine pairwise judgments, including ties, alongside completion and
   defects. This is a small decision pilot, not a significance claim. Prefer B for
   the next experiment only if it wins at least 6/9 judgments without introducing
   more progression blockers; otherwise inspect reasons and simplify feedback.
   Do not generalize this threshold into proof of universal superiority.

## Defect evidence and next decision

For every important issue record a MAP hash, location or viewpoint, observed
behavior, expected behavior, and whether current feedback identified it before
play. Distinguish missed defects from false alarms. After the primary ratings,
permit one targeted repair of the most frequent missed issue and repeat its
specific check. This tests whether feedback produces a useful action rather than
merely another score. Save both MAPs and evidence.

Only after that result, compare tree versus flat editing on a matched revision
(e.g. enlarge the courtyard while preserving portal and mechanism behavior).
Measure edit time, touched definitions, unintended changes and validation failures.
Do not use source line count alone as a productivity or quality measure.

## Records

Use `ratings.csv` for player observations. Keep a separate private assignment
record with pair, neutral label, treatment, source snapshot and MAP SHA-256;
reveal it only after ratings are frozen. Record exclusions and missing sessions.
No ratings have been filled in and no quality improvement is claimed.
