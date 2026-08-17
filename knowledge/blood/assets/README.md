# Blood contextual assets

Sprites and decorative tiles are not a second material ontology. They are
independent facets: native id, sit, scale, blocking, mechanism neighborhood,
key co-occurrence.

Campaign retrieval:

```text
python -c "from bloodmap.assets import mine_sprite_context, dump; ..."
```

Reports:

- `reports/blood-sprite-context.json` — families with independent shares
- `reports/blood-key-signifiers.json` — keyed vs unkeyed co-occurrence

Review packets (isolated bitmap + in-map usages) reuse the materials packet
pipeline when ART is present. Interpretation of “this is a fire-key sign” is
INTERPRETED even when co-occurrence is strong (2540–2545).
