# Blood design-pattern knowledge

Versioned hypotheses discovered from original Blood maps. Names are
**INTERPRETED**. Signatures and occurrence counts are **DERIVED**.

Do not treat generated reconstructions as evidence.

```text
python knowledge/blood/design/compile_catalog.py
```

requires local unsigned mines in `work/` (gitignored). The compiled
[`catalog-v1.json`](catalog-v1.json) is the retrieval surface.

| file | role |
| --- | --- |
| `compile_catalog.py` | pattern templates + occurrence attach |
| `catalog-v1.json` | versioned hypotheses with original-map occurrences |
| `door-families-v1.json` | compact campaign door-family / key-emblem retrieval hints |

Door implementation families and key-signifier co-occurrence live in
[`reports/blood-door-families.json`](../../../reports/blood-door-families.json)
and [`reports/blood-key-signifiers.json`](../../../reports/blood-key-signifiers.json).
They are retrieval, not prefabs.

See [docs/door-affordances.md](../../../docs/door-affordances.md).

SP mechanism compositions from E2M2 (fan-out TX/RX, single motion gates) were
searched on the 43-map campaign and stored in
[`reports/E2M2-mechanism-patterns.json`](../../../reports/E2M2-mechanism-patterns.json).
They are not catalog-v1 entries until `compile_catalog.py` grows a mechanism view.

See [docs/design-pattern-discovery.md](../../../docs/design-pattern-discovery.md).
