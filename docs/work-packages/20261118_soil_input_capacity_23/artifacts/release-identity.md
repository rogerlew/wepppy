# Release identity and validation provenance

The opt-in matched Linux pair is `wepp_261118` / `wepp_261118_hill`.
Both sidecars declare input capacity 23; calculation capacity remains ten.

| Role | SHA-256 |
| --- | --- |
| Watershed | `bd421e39dfe742ed500c69596ef91a6232254587001ec49b09b2ec0ca5ec9f32` |
| Hillslope | `9843f250b25f2f2dab342d2418cd9d5b5b43d9e685b6db1216031c1a0958fa81` |

Canonical native builder: `tools/build_wepp_dated_release.sh`,
`TARGET_TAG=261118`, source commit
`464a5e5e15e1fbcdd4e8232260ecf79ad2645200`, native default branch
`wepp_260430_negmeltfix_comparator`. The default branch was locally
fast-forwarded from `7d4cf4b5ab24bbc825515d54f25a035062b826bb`; no remote
push or production deployment occurred. Build outputs are retained in
`/workdir/wepp-forest-release-20261009/release/`. Matching copies and sidecars
are vendored under `wepp_runner/bin/` on the Python task branch.

Native full suite: 1824 passed on implementation commit `f90ba43ed`.
Final commit adds metadata tests, the retained watershed evaluator and docs;
production Fortran is unchanged. Additional metadata tests: 14 passed.
Reader matrix: 72 passed. Legacy reader state: 80/80 exact. Final pair host
smokes and ELF provenance passed; hillslope watchlist: 31 passed.
Twenty daily/hourly watershed executions completed; legacy control outputs
were byte-identical. See `native-watershed.json` and `native-reader-parity.json`.

External logs and complete generated files are retained at
`/workdir/soil-input-capacity-23-evidence/`, including `native/`,
`release-watershed/`, `vendor-provenance.log` and `vendor-smoke.log`.
The development replay uses the final pair. Its earlier raw soil-build probe
used the explicitly labeled diagnostic build from the same native implementation.
Neither validation identity substitutes for remote integration or deployment.
