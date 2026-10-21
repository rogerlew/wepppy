# Tracker

2026-10-21: User authorized release build and vendoring. Canonical default
checkout is `/workdir/wepp-forest-release-20261009`, clean at `917265bb5`.
The 261010 changelog entry is present.

Applied the reviewed ASCII backport and committed it on the default branch as
`a87925df9ffe6ebb928e126395dd159d484285fa`. Focused calendar suite: 61 passed.
The HBP-only compatibility-preimage test is excluded from this ASCII port.
Release build is running with the system compiler.

Both dated binaries built successfully. Host smokes, provenance and artifact
policy pass. All seven production repair files exactly match the previously
validated ASCII backport. Full native/watchlist and fresh 400-year replay running.

Fresh release 400-year replay and date/precipitation audit pass: 146,097 days
through 400/366 across hill water balance, hill/master PASS and watershed EBE.
Committed-input watchlist: 12/12 pass. Native suite final watershed case remains
running. Broad WEPPpy sanity also running.

Native full suite: 232 passed in 397 seconds, including the new release on the
committed 100-year watershed regression. Installed both binaries plus sidecars
in WEPPpy; post-vendor provenance passes. Host/container smokes and targeted
runner tests are running.

All post-vendor gates pass (host/container smokes, provenance, 8 runner tests).
Initial broad sweep stopped after 1,134 passes/28 skips because Builder read
the sidecar during metadata copying. Rerunning with fixed installed files and
only the already-passed disturbed matrix excluded. Future metadata replacements
will be atomic; no production code workaround is introduced.

Stable rerun passed the previously failing Builder module and reached the
soil-artifact suite without failures. Documented atomic sidecar replacement and
fixed-file validation in `docs/binary-lifecycle.md` (Vendoring Enforcement).

Stable full rerun passed 2,350 tests/48 skips, including Builder, before an
intentional interrupt in slow Rosetta soil inference. Split its 230 collected
soil-artifact node IDs into four disjoint shards; rerun the remainder with
only that module and the already-passed 99-case disturbed matrix excluded.
Node assignments and commands are retained to account for complete coverage.

All four soil shards pass (58 + 58 + 57 + 57 = 230 tests). Remaining broad
suite continues without reported failures; release files remain fixed.

The remainder reached 4,872 passes/51 skips before a live Builder snapshot
expected the old two-release inventory. Updated the snapshot and live-policy
expectations for 261021, and parameterized existing old-project selection
coverage to exercise 261021 without config migration. Mocked inventories remain
unchanged. Resuming at the failing module, excluding fully completed modules;
coverage assignments and commands are retained.

Resumed explicit module list collected exactly 5,931 remaining tests. Coverage
accounting: 99 matrix + 230 soil + 4,913 completed prefix + 5,931 remaining =
11,173 tests (original 11,172 plus the new 261021 selection regression).
The corrected Builder snapshot and capability tests pass in the resumed run.

Resumed segment: 5,550 passed/72 reported skips before an OpenET authorization
test saw unauthenticated Redis in submission-lock admission. The complete
feature-access module passes independently (52 tests); retained as a test-order
limitation, with no auth changes. Final 29 modules/258 tests are running.

Complete: final browser-adjusted segment passes all 258 tests. Full segmented
coverage is 11,052 unique passes plus 121 test skips and one collection skip.
All required release gates pass. Test-order Redis and browser-path limitations
are retained; no authentication, application configuration, defaults or deployment
changes. Native changelog and WEPPpy release log include 261021; 261010 retained.

Native release artifacts/changelog committed locally as
`6a6621e4db9aff1cdf6fa9cd0cb02b00e82182eb`; native checkout is clean. Build source
remains `a87925df9ffe6ebb928e126395dd159d484285fa`. Final binary/sidecar hashes,
source-release equality and file modes verified unchanged after testing.
WEPPpy changes remain available for review in its working tree; no push.
