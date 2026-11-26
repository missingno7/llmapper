# Acceptance Tests and Reference Experiments

These are not all unit tests. Some are research acceptance criteria.

## A0. Corpus integration (Phase 0a)

Input:

```text
maps/blood/{campaign,curated,conversions,community,tiered,mechanism}
with multiplayer/ mode subdirs (layout in 07_...md; already reorganized
on disk by the owner)
```

Expected:

- population resolved from directory layout, fail-closed,
- `community` and `tiered` resolve to one population (tier as metadata),
- campaign enumeration returns exactly the original `E*M*.MAP` set,
- `DWE*`/`TEDE*` resolve to `community-curated`, `DNE*` to `own-conversion`
  (owner correction 2026-08-31; the old filename table calling them all
  `conversion` is wrong),
- `blood-bloodbath` enumeration returns only `campaign/multiplayer/BB1–BB9`;
  `DWBB*` and `DM*` resolve to `community-curated` with `mode=multiplayer`,
- the `reference` view = campaign + curated is queryable,
- community parse-gate report exists (per map: parses / roundtrips /
  version / failure reason), failures skipped and reported, never
  normalized.

Pass condition:

`pattern-mine --population blood-campaign` and the corpus gates run against
the new layout, and a health report states community-corpus coverage.

---

## A. Drawer anchor bootstrap

Input:

```text
known drawer-front tile
```

Expected:

- all original-map occurrences collected,
- neighborhood relations extracted,
- at least one recurring structural candidate found,
- structurally similar anchor-free examples searched,
- counterexamples shown,
- no direct `tile -> drawer unit` shortcut.

Pass condition:

The system learns a larger structure than the manually supplied label.

---

## B. Shelf vs crate

Expected analysis:

- positive shelf candidates,
- crate-pile comparison group,
- repeated horizontal support evidence,
- privileged-front/access evidence,
- containment/support relationships,
- ambiguous examples.

Pass condition:

Classification is relational, not texture-only or bounding-box-only.

---

## C. Authored object assembly vs random scattering

Create two synthetic test scenes only for validation, not evidence:

1. table with intentionally related chairs,
2. same assets randomly scattered.

Pass condition:

Assembly critic distinguishes them using relations and access/circulation, not
sprite count.

---

## D. Storefront facade

Select several original street-facing examples.

Expected:

- facade parent identified,
- bay/opening hierarchy,
- reveal/thin-sector role,
- repeated sill/header data,
- style continuity,
- rendered street view.

Pass condition:

The system can explain why the opening belongs to the facade.

---

## E. Door vs lift vs other Z-motion

Choose three original mechanisms with similar low-level motion.

Expected:

- common physical state-change representation,
- different spatial effects,
- semantic distinction supported by context.

Pass condition:

Low-level mechanism family does not force incorrect semantic label.

---

## F. Breakable barrier topology delta

Expected:

```text
intact -> blocked
destroyed -> traversable
irreversible
```

Pass condition:

Spatial view reports conditional connection and causal provenance.

---

## G. Multi-view contradiction

Find or construct a candidate where:

- geometry is valid,
- mechanism works,
- visual readability fails.

Pass condition:

Critics report only the relevant failure and repair scope remains local/assembly.

---

## H. Recursive abstraction

After learning a lower-level concept such as shelf or drawer unit:

- rerun discovery using learned concept nodes,
- identify at least one larger recurring assembly.

Pass condition:

The knowledge system can grow upward, not only accumulate flat labels.

---

## I. Corpus population separation

Run the same pattern query across:

- original campaign (`maps/blood/campaign/E*M*.MAP`),
- community corpus (`maps/blood/tiered/S` first).

Pass condition:

Reports can distinguish:

```text
original convention
```

from:

```text
community precedent
```

without merging distributions silently.

---

## J. Discovery frontier

After a corpus mining run, produce a ranked list of unknown candidates.

Pass condition:

At least one candidate was not manually named in advance and includes:

- recurrence,
- representative examples,
- uncertainty,
- proposed next experiment.

---

## K. Scoped repair

Introduce one local visual/architectural defect in a generated candidate.

Pass condition:

Repair:

- fixes the reported issue,
- does not change unrelated topology,
- does not change progression,
- reports semantic delta.
