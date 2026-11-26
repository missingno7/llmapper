# Backdrop urbanism and the interior–outdoor weave — E2M1's two patterns

Owner reading (2026-08-27): E2M1's street-looking part is a scene glimpsed
through an opening — scenery the player sees but never walks — while the
playable level is interiors interwoven with outdoor pockets. Neither is
"urban structure"; both are named patterns Gravesend uses. Records via the
improved classifier's scene detection (city-norms-v2.json `street_detection`)
and a campaign-wide sweep.

The classifier rule this bought: **a street component the player cannot
reach on foot from the start is a scene, not a street** — implemented as a
directed-reachability screen (drops pass downward, mechanisms count as
open) in `tools/mine_city_norms.py`. The model is optimistic and still
under-reaches through unmodeled gating, so "scene" formally means
*unreachable in the optimistic model*; E2M1's backdrop is the confirmed
case.

## 1. Backdrop urbanism (budget-cheap city depth)

The E2M1 exemplar, measured (sector 163):

- **One sector, 12 walls, 60M sq units** (10240×11520 in plan) — a
  sky-ceilinged sunken court whose floor sits 20480 z (1.2 standing)
  below the parapets it is seen from.
- **Framing**: three red walls (~9.3k units of open span, gap 47104) onto
  two reachable parapet sectors — an open overlook, not masked glass. The
  drop in would be one-way, so the player never walks it; the far walls
  carry a single large tile (2490) as the painted distance.
- **Cost accounting**: 12 walls buy a city block's worth of implied space.
  Facade-phase arithmetic: at the mined facade rate (~0.45 walls/1024) the
  same visual depth as real streets would cost hundreds.
- **The campaign does this everywhere**: the sweep found **88
  scene components of ≥20M area in ≤6 sectors** across the campaign —
  nearly every map parks large visible-but-unwalkable space at 4–80 walls
  (extremes: E4M1's 1006M single 9-wall horizon; E2M6's 917M 80-wall
  panorama). This is a standard Blood construction, not an E2M1 quirk.

**Gravesend application (Phase 3, facades)**: windows and overlooks that
show streets continuing where no street exists — the "facade promises more
than exists" contract extended inward. Concrete slots: the Aldermack's
upper windows showing a lit street beyond the north lane; the quay's far
shore (see promenade-patterns.md); the works' east wall showing rail yards
beyond the spur. Budget: 10–30 walls each, charged to the district's
facade allowance.

## 2. The interior–outdoor weave

E2M1's playable side, measured within the reachability the model has
(partial — its gating under-reaches; numbers are floor values):

- **Alternation**: the walkable network merged across **14 short indoor
  links** — interior, court, interior — with the courts as one 8-sector,
  143M pocket chain rather than a street.
- **Threshold light**: outdoor pockets average floor shade **+4.2**
  against interior **+36.2** — a ~32-point step at every threshold, the
  inverse of the night-street venue law (venue-patterns.md: interiors
  darker than streets). In the weave, the *pocket* is the bright room.
- **Pockets are not streets**: no frontage rhythm, no doorway economics —
  each pocket is a room with sky, entered like a room.

**Gravesend application (Phase 4, the Aldermack)**: the landmark complex
braids its rooms through one or two interior courts with sky — the weave
gives the superblock's inside the same day-for-night contrast E2M1 runs,
and the court thresholds take the 30-point light step, opposite in sign to
the street-side venue mouths.
