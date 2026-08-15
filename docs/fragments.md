# Sector fragments and reference remapping

`LevelFragment` is the first composition-oriented layer above `LevelIR`. It is a
self-describing selection of sectors, their owned walls, contained sprites, and
embedded Blood extended records. It does not concatenate arrays and does not claim
to be a complete new map.

## Extraction contract

```python
fragment = level.extract([12, 13, 14])
restored = fragment.apply_to_source(level)
```

Extraction creates explicit source-to-fragment maps for sector, wall, sprite,
XSECTOR, XWALL, and XSPRITE IDs. Internal references are rewritten to fragment-local
IDs. Boundary portals and external sprite/marker ownership are detached to `-1`,
but their source values are retained as small `PreservedReference` records for exact
same-source reinsertion.

Every discovered relationship is classified as one of:

- `internal_reference`: geometry, membership, ownership, marker, extra, or trigger
  links wholly contained by the fragment;
- `external_geometry`: a portal crossing the selected sector boundary;
- `external_trigger`: TX/RX behavior involving source objects outside the fragment,
  including unresolved but game-valid one-sided channels;
- `external_marker`: an XSECTOR marker owned outside the fragment;
- `external_ownership`: sprite owner, target, or burn-source relationships outside
  the fragment;
- `system_global`: source-verified Blood engine channels.

Special channels are copied from NBlood's
[`source/blood/src/eventq.h`](https://github.com/NBlood/NBlood/blob/master/source/blood/src/eventq.h);
undefined channel values are not guessed to be global.

## CLI

```text
python -m bloodmap extract maps/blood/E1M1.MAP --sectors 12,13,20-24 -o work/fragment.json
python -m bloodmap apply-fragment maps/blood/E1M1.MAP work/fragment.json -o work/rebuilt.MAP
```

`apply-fragment` is intentionally restricted to the exact source identity and object
counts. It restores detached relationships, writes, reparses, and validates. This
proves extraction and remapping without pretending cross-map placement is solved.

## Composition boundary

Cross-map insertion now allocates object, extra-record, and user-channel identities.
Fragments can be translated, quarter-turned, inserted repeatedly, and attached to
an existing one-sided wall through an exact equal-length portal. Callers still
cannot silently opt out of dependency classification: relationships outside the
selected sectors remain visible in fragment JSON and composition reports until a
specific operation resolves them.

Automatic dependency closure, unequal-width corridor generation, whole-layout
overlap checks, and progression validation remain future gates.
