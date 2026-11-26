# reports/

Corpus-wide reports: what a miner or an audit measured over the shipped maps. The files at
this level are still read: by a library module (`bloodmap.anchors`, `conditional`,
`contradictions`, `knowledge_index`, which indexes them for `python -m tools.catalog find`),
by a tool, by a test, or by a project; `tiles/` holds the tile pictures the catalog shows.

`archive/` is history: August and September reports that nothing reads any more, kept as
they were written. Nothing there describes the present; ask `tools.catalog` and
`tools.findings` instead. A level's own reports (status, critique rounds, its build
manifest) live in its project, under `projects/<name>/reports/`.
