# Probes

The small scripts that counted what a finding says, kept so that the count can be made again.
Each was written for one question on the day its finding was filed or audited; run one from the
repository's root (`python knowledge/blood/findings/probes/<name>.py`). They read the local
corpus through `bloodmap.corpus` and write nothing. They are evidence, not tools: when a count
is wanted often, it belongs in a miner under `tools/`.
