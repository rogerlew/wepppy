# Phase 6 QA Review and Observation Plan

**Executed**: 2026-08-19 UTC
**Scope**: EU-specific runtime gate for Disturbed single-OFE and MOFE soil
artifacts, plus additive `Soils` provenance persistence.

## QA matrix

| Area | Check | Result |
| --- | --- | --- |
| Base quality | valid ESDAC profile | passed; disturbed artifact is published only after canonical reparse |
| Base quality | degraded ESDAC profile | passed; warning diagnostics remain accepted and visible |
| Base quality | rejected ESDAC profile | passed; no generic replacement is published |
| Carrier integrity | missing or malformed report | passed; typed report errors are raised |
| Carrier integrity | incomplete TopoAZ coverage | passed; preflight fails before generation |
| Carrier integrity | stale `soil_key` | passed; report mismatch is rejected before generation |
| Carrier integrity | inconsistent accepted/rejected counts | passed; report is rejected before runtime use |
| Carrier integrity | missing diagnostics or boolean schema version | passed; malformed report is rejected |
| Publication | single-OFE new and reused output | passed; both paths are validated |
| Publication | MOFE segment and synthesized output | passed; both use canonical validation |
| Publication | MOFE failure rollback | passed; preexisting files are restored and new files removed |
| Publication | MOFE controller-state rollback | passed; `domsoil_d`, soil summaries, and metrics are restored |
| Publication | single-OFE full key preflight | passed; stale later keys fail before any write |
| Publication | single-OFE batch rollback | passed; earlier files and NoDb state are restored on later failure |
| Compatibility | legacy NoDb payload without marker | passed; marker defaults to `None` |
| Compatibility | non-ESDAC identify builder | passed; marker remains absent |
| Static hygiene | stubs, broad exceptions, compile, diff check | passed, except the preexisting direct ESDAC stubtest blocker below |

## Commands and results

- `wctl run-pytest tests/nodb/mods/disturbed/test_esdac_runtime_gate.py
  tests/eu/soils/test_esdac_quality_contract.py
  tests/eu/soils/test_esdac_soil_build.py
  tests/nodb/test_soils_gridded_root_creation.py --maxfail=1`: **50 passed,
  2 warnings**.
- `wctl run-pytest tests/eu/soils tests/nodb/mods/disturbed
  tests/nodb/test_soils_gridded_root_creation.py --maxfail=1`: **139 passed,
  20 skipped, 2 warnings** before the final two parser/rollback regression
  additions; the final focused set covers those additions.
- `wctl check-test-stubs`: passed.
- `python3 tools/check_broad_exceptions.py --enforce-changed
  --base-ref origin/master`: passed, zero net delta.
- `python3 -m py_compile` on all changed production modules: passed.
- `git diff --check`: passed.
- `wctl doc-lint` on the package and ESDAC README: passed.

## Known environmental blockers

- Direct `wctl run-stubtest wepppy.eu.soils.esdac` remains blocked by the
  preexisting mypy errors in `wepppy/eu/soils/esdac/quality.py` at lines 211,
  308, 319, 321, 330, and 339. `wctl check-test-stubs` remains green.
- The final-tree `wctl run-pytest tests --maxfail=1` gate reached
  `170 passed, 13 skipped, 9 warnings` in 265.05s and stopped in the
  unrelated Docker canary because the installed Docker CLI rejects
  `docker compose -f` with `unknown shorthand flag: 'f'`. This was reproduced
  on the final tree; it must be rerun in an environment with the expected
  Compose CLI before repository-wide closeout.

## Observation window

Observe the next EU ESDAC runs for 14–30 days after deployment, or until at
least 20 EU disturbed runs have completed, whichever is later. The operator
should record:

- count of marked ESDAC runs entering Disturbed;
- accepted valid/degraded/rejected base profiles;
- `source.quality_report.*` and `disturbed.*` rejection codes;
- count of published single-OFE and MOFE artifacts;
- any rollback invocation or leftover temporary files;
- comparison against the Phase 0 baseline of 641 suspicious samples per 1,000
  pilot locations and 59 generated depth-order findings.

**Danger signals**: any generic replacement after a rejected base, any
artifact published without a successful canonical reparse, any missing
location report error after output publication, or any temporary `.sol`
leftover. A danger signal reopens Phase 6 review and pauses mitigation
softening.

**Owner**: EU soil maintainer / on-call operator. **Sunset**: close the
observation record after the window with run IDs and counts; no temporary
callus is retained by this implementation.
