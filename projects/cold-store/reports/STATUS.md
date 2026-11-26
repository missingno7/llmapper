# The Cold Store: where it stands

Written by `python -m tools.project status cold-store` from the last build; never edited.

- map: `projects/cold-store/level/cold-store.MAP`: 12 sectors, 68 walls, 19 sprites (NBlood's limits: 4096, 16384, 16384)
- ends: sprite 13 (reached)
- looked at from: `start` (3), `hall` (4)
- critique: none yet

## Open: 1

### never-critiqued

- no blind reader has looked at any place of this level
  - do: python -m tools.critique --project cold-store prepare <slug> --poses <set> --kind <kind>
