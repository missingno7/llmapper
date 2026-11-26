# City evidence status — 2026-09-09

> **Out of date since 2026-11-17.** This page was written on 2026-09-09, when the street slice was the
> line being worked. Everything since -- the church, market, shed, theatre, station, harbour, shopfronts,
> goods, the owner's second and third walks -- went into `level/build_skeleton.py`, which writes
> `level/blood-city-current.MAP`. On 2026-11-19 that build is **474 sectors, 3,187 walls, 816 sprites**,
> takes about a minute, and reproduces the committed map byte for byte. The slice below has not been
> rebuilt or re-audited since September. Where the city stands today is `reports/STATUS.md`, which the
> build generates; the data behind it is `reports/status.json`.

The current construction control is `level/slice2-streets.MAP`, emitted by
`level/build_graph_slice2.py` through `bloodmap.pipeline.compile_city`.
The independent audit rebuilt it byte-exact: 199 sectors, 1031 walls, 16 sprites,
SHA-256 `347ba9fbce3d2e074a3683c08bbaff845a2302ae3146d32c0f9a9993dd147eea`.
Readback matched all nine authored sentences. Nine links and five keys were
realized; 173 sectors were reachable at rest and 199 under `everything_worked`.
That state assumption is not a recorded player traversal. This slice has no dudes
and is not a completed gameplay-quality baseline.

`level/blood-city-current.MAP` is the separate older full-city artifact:
259 sectors, 1694 walls, 430 sprites, including 27 dudes;
SHA-256 `5a1aac2ed778d2918eb9ed3d689cc6e1608f25acad3f780992e71652f644f84f`.
Do not transfer its content or play claims onto the current slice.

The former whole-graph junction gap is superseded for this slice by the working
emitter/pipeline. Recent flat-plan renderings are construction views, not first-person
or play evidence. See `reports/archive/independent-audit-2026-09-09/city-probe.json` from the
repository root for the recorded check. No NBlood play session was run.
