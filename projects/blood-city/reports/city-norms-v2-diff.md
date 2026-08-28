# city-norms v2 — what moved, and what it does to the Gravesend contracts

v2 = [city-norms-v2.json](../references/city-norms-v2.json): the v1 six
sources plus the owner-approved DWE3M10, TEDE1M2, E3M2, read through the
improved classifier (indoor-link merging, directed reachability, fronted
blocks). v1 stays on disk unchanged. Two things moved numbers at once — new
sources and better detection — so v1-source rows that shifted are from the
classifier, not the city.

## Classifier changes (the rules the screening bought)

1. **Indoor-link merging**: sky components joined through ≤3 interior
   sectors are one network (TEDE1M2's square+streets; 13 merges there,
   2–14 elsewhere).
2. **Directed reachability screen**: drops pass downward, mechanisms count
   as open; a component unreachable from the start is a *scene*, not a
   street (E2M1's backdrop; E3M2's town is entered by drops and was being
   discarded until the model went directed).
3. **Fronted blocks**: an obstacle you can circle is not a block unless
   something opens onto it — `blocks_fronted` joins the census; raw counts
   remain for massing-stage conformance. (The wilderness set's loops all
   score fronted 0.) Known limit: doors on edge-frontage masses don't
   attribute to any enclosed block, so frontage towns read fronted 0 —
   attribution needs the doorway-to-mass mapping, not just raster labels.

## Contract movements

| contract | v1 band | v2 band | Gravesend plan | verdict |
|---|---|---|---|---|
| main street widths | 5120–7168 | unchanged; **new attested lane mode 3072–3584** (TEDE1M2 core) | avenue 7168 / row 6144 / street 5120 | **green, unchanged**; `lane`-class streets now available to dense quarters without exception |
| doorways /10240 | 0.23–1.17 | **0.23–2.04** (E3M2 top) | ~0.35 | green, more headroom |
| substantial interiors /10240 | 0.13–0.37 | **0.11–0.38** (E3M2 low, TEDE1M2 high) | 0.145 | green |
| street loops | 6–9 (DukCity-derived) | DukCity unchanged; Blood towns measure 1–8 → **the floor is soft** | 9 | green; floor softness recorded, not acted on |
| canyon (avenue) | 1.7–2.1 (DukCity-derived) | DukCity unchanged; Blood towns 0.31–1.2 (E3M1's median moved 1.68→1.2 under merging — more open ground joined its network) | 1.71 | green; explicitly a Duke-derived target held for the avenue only |
| per-district walls ≈700–1100 | E3M1 chunks 79–1007 | **TEDE1M2's core is one 5,390-wall chunk over 759 sectors** — dense cores don't decompose | districts 300–1100 | green; the district decomposition is a choice the E3M1 model supports and the TEDE1M2 model would overturn — Gravesend keeps districts |
| walls/sector density | 6.5–10 | new points 7.3 / 7.5 / 8.0 — band tightens around ~7–8 | skeleton 7.1 | green |

**No Gravesend L1 contract shifts out of band → no plan-layer change**;
`plan_review.py` re-run green (16/16) and the conformance diff re-run clean
against the unchanged skeleton. The additions land as vocabulary (the lane
class, the promenade contract, the backdrop/weave patterns, the rail-seam
option) for Phases 2–4.

## New-source headline rows (v2)

| map | street sectors | w median | d/10240 | int/10240 | note |
|---|---|---|---|---|---|
| DWE3M10 | 59 (1 loop) | 5632 | 1.76 | 0.20 | promenade; single-sided frontage 23:14; water is sectors, boats are geometry |
| TEDE1M2 | 58 (13 merges) | 3584 | 1.83 | 0.38 | dense core; 7,361 walls at the ceiling; one 5,390-wall chunk |
| E3M2 | 4 giant sectors (E2M6 form) | 9216 | **2.04** | 0.11 | 77 doorways — corpus max; rail corridor as district seam |

## Post-v2 correction (urban semantics pass, same day)

E3M2's headline "77 doorways, 2.04/10240 -- corpus max" needs an asterisk:
the per-sector semantics pass (references/urban-semantics.md) shows 75 of
those 77 are mouths of narrow **gate passages through the town wall**, not
building doors, and E3M2's buildings are entered from the rampart circulation
above (roof/upper network), not from the street. The v2 doorway band's top
end therefore describes gate-mouth counting, not enterability; the
per-building share band (0.13-0.40, cross-game) is the corrected enterability
metric and is queued as a candidate L1 contract row.
