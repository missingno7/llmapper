# Dense-town patterns — TEDE1M2 and E3M2

Owner-approved sources (2026-08-27 screening), both mis-read by the v1
classifier and re-detected after the fixes it forced (indoor-link merging,
directed reachability; see city-norms-v2). Records in
[city-norms-v2.json](city-norms-v2.json); owner-check plots at
[plots/tede1m2-city-plan.png](plots/tede1m2-city-plan.png) and
[plots/e3m2-city-plan.png](plots/e3m2-city-plan.png).

## TEDE1M2 — the dense core at the engine ceiling

1,014 sectors / 7,361 walls: DukCity3's territory, from the Blood side.

- **Re-detection**: the v1 classifier saw only the square; with components
  merged through short indoor links (13 merges) the network reads 58 street
  sectors — the square, its fountain (an orange sub-block obstacle), and
  the west and south streets, 39 doorways along them. The northeast quarter
  still reads as interiors: its lanes appear to be covered (roofed arcade
  class), which is the recorded limit of the 3-hop merge — flagged for the
  owner to check against their reading.
- **The dense-core street class**: width median **3584**, p10 1024 —
  narrower than anything in the v1 corpus (mains 5120–7168). A new,
  attested class between alley and street: the *lane*, ~3072–3584, is how
  a dense town core differs from E3M1's frontier pattern (one wide street,
  detached buildings). Enterability rides it: **0.38 substantial interiors
  per 10240** — the corpus maximum, edging E3M1's 0.37.
- **Winding**: 1 walk-around loop in 58 sectors — the dense core is a web
  of lanes and dead-ends around one square, not a loop grid. Loop-count
  urbanism is the Duke model; density urbanism is this.
- **Budget at the limit**: 7.3 walls/sector; the town core chunk spends
  5,390 walls over 759 sectors — one attributed chunk carrying 73% of the
  map. Dense cores do not decompose into 700–1100-wall districts; they are
  one continuous spend. Gravesend keeps its district decomposition (the
  E3M1 model) and borrows only the lane class and the enterability rate.

## E3M2 — the walled town and its rail corridor

- **The E2M6 form at town scale**: the whole town is **4 sky sectors**
  (1300M area) with its buildings as holes — the same
  one-region-with-carved-masses pattern Gravesend's districts use, at 567
  sectors / 4,272 walls. The v1 classifier caught only the rail corridor;
  directed reachability (the town is entered over its wall, by drops)
  found the town.
- **The densest enterability in the corpus**: **77 doorways, 2.04/10240**,
  3 of 3 blocks fronted. Interiors are small (0.11 substantial/10240) —
  many doors into shallow rooms: siege-town urbanism, every building a
  fighting position.
- **The rail corridor as urban element**: the corridor the v1 classifier
  found (w_med 9216 with the track bed) cuts the map as its own walkable
  spine with 20 doorways of its own — a district seam that is also a
  circulation route. Gravesend already has the grammar for this: the rail
  spur along Foundry Ward is exactly this element; E3M2 licenses extending
  it *through* the fabric (Phase 2+ option: the spur continues past the
  works into a cutting, reading as the seam between Foundry Ward and
  whatever grows east).

## What moves into the Gravesend contracts

- A **lane width class (3072)** joins the resolution table as attested
  vocabulary for dense quarters (Old Crossing may adopt it in Phase 3
  without a contract exception).
- Doorway-rate band widens to 0.23–2.04, interiors band to 0.11–0.38
  (see city-norms-v2-diff).
- The loop contract stays Duke-derived (6–9) — the Blood towns say the
  floor is soft, recorded rather than acted on.
