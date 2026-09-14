# Isolated integration increment validation

Contract ancestor: `89d673c38`; implementation is not production-wired.
Shared SSURGO/STATSGO builders are unchanged. No acquisition, source refresh,
live soil build, production publication or deployment occurred.

## Completed gates

- Before implementation: `wctl run-pytest tests/soils tests/nodb/test_soils_ssurgo_cache.py --maxfail=1`
  — 50 passed, 5 skipped.
- Current focused gate: production-soils, integration, offline soil-thickness
  and rainfall test modules through `wctl run-pytest ... --maxfail=1`
  — 153 passed in 28.27 seconds. This includes actual WBT execution and real
  SQLite WAL/rollback transactions, not mocked terrain or database contents.
- `wctl check-test-stubs` — passed.
- `python3 tools/check_broad_exceptions.py --enforce-changed --base-ref origin/master`
  — all nine changed production modules passed; no broad catches added.
- Package and module `wctl doc-lint` — 15 and 20 files, zero errors/warnings.
- `git diff --check` — passed; tracker spelling-normalization preview unchanged.

## Full sweep

`wctl run-pytest tests --maxfail=1` — 8,498 passed, 103 skipped, 3,118 warnings
in 961.15 seconds. It collected tests before the last review-driven additions;
the focused gate above covers those additions. The final M1 domain-equality
correction was followed by another integration run: 55 passed in 26.62 seconds.
The final nonuniform test refinement passed all five common-support cases
(50 unrelated integration cases deselected) in 11.26 seconds.
No frontend/queue wiring changed;
package-wide frontend and live RQ gates remain closeout work, not claimed here.

## Remaining acceptance

Authentic THICK reprojection, generated SSURGO/STATSGO `.sol` and `wepp/runs/*`
parity, actual large-grid M3 terrain, shared rainfall/results dispatch,
publication/freshness, and live RQ/browser/archive round trips remain required.
Prepared collection lineage and original THICK are absent for the development
basin. Bounded acquisition was requested separately and has not been authorized
or performed. A source-free unavailable result cannot close this package.
