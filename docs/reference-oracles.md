# Local reference oracles

The project can use a local `reference/` tree for source cross-checks, format
probes, and independent runtime verification. The entire tree is ignored by Git
because it may contain commercial Blood data and nested upstream repositories.

The expected local layout is:

```text
reference/
  blood/       legally obtained game data and local executables
  xmapedit/    https://github.com/NoOneBlood/xmapedit.git
  NBlood/      https://github.com/NBlood/NBlood.git
```

Clone the open-source references locally when needed:

```text
git clone https://github.com/NoOneBlood/xmapedit.git reference/xmapedit
git clone https://github.com/NBlood/NBlood.git reference/NBlood
```

These inputs are evidence, not runtime dependencies. The Python package must keep
working without `reference/`, and ordinary tests use synthetic fixtures or the
separately ignored `maps/` corpus. When a verification claim depends on an
upstream checkout, record its commit in `reports/verification.md` so the result is
reproducible.

Never copy game resources, generated screenshots, executables, or nested Git
metadata into tracked paths. Only derived facts, focused tests, and documentation
belong in the repository.
