# Build and vendor WEPP 261021

## Purpose

Release the validated Gregorian repair on the existing default branch, retaining
ASCII PASS v3 and current capabilities. Scope is faithful correction, wired into
production execution; acceptance requires newly built executable evidence.
No production deployment or default-selection change is requested.

## Progress

- [x] Confirm default branch and existing 261010 changelog entry.
- [x] Apply the validated ASCII repair and bounded tests on the default checkout.
- [x] Record source identity, build both profiles sequentially, and run native gates.
- [x] Vendor paired binaries and sidecars; provenance, host/container smokes and 8 runner tests pass.
- [x] Complete broad sanity with installed release files held fixed (segmented coverage and limits retained).
- [x] Update native changelog, release log, and handoff evidence.

## Context and plan

Use `/workdir/wepp-forest-release-20261009`, already on remote-default branch
`wepp_260430_negmeltfix_comparator` at `917265bb5`. Do not switch branches.
Apply `../wepppy/docs/work-packages/20261021_gregorian_calendar_repair/artifacts/ascii-release-backport.patch`.
The separate `/workdir/wepp-forest` checkout is HBP development and is not the
release lineage. Copy the reviewed calendar tests, adapting the filename assertion
to fixed-form wshpas. Retain the shared calendar module unchanged.
Build with `TARGET_TAG=261021 COMPILER=/usr/bin/gfortran tools/build_wepp_dated_release.sh`.
Run both native host smokes, committed-input hillslope watchlist, artifact policy,
and full maintained pytest suite. Do not vendor if required gates fail.
Record exact source commit, hashes and PASS v3 capabilities in adjacent sidecars.
Vendor into `/workdir/wepppy/wepp_runner/bin`, then run provenance, both host
smokes and `wctl run-pytest tests/wepp_runner/test_run_hillslope_retries.py tests/wepp/test_wepp_runner_outputs.py`.
Run broader required sanity; distinguish unrelated failures from release gates.

## Compatibility and recovery

Keep existing names, defaults, schemas, capacities and banner. Gregorian fixes
require regenerating all contributing hillslope PASS and watershed outputs with
the paired release. Existing v3 interchange remains compatible; HBP padding
changes are not part of this ASCII release. Preserve historical binaries.
Stage and validate the new four files before installation; failures before
vendoring leave installed binaries untouched. Never replace project artifacts.

## Surprises & Discoveries

The native `make all` target is deliberately disabled to prevent profile
include races. Used the canonical dated-release script, which cleans and builds
watershed then hillslope sequentially. Profile include copies were restored
after validation; frozen release artifacts retain the validated binaries.

The primary source checkout is a non-default HBP branch; the existing default
checkout is clean and already documents 261010. Use its committed-input gates.

The initial broad WEPPpy sweep (1,134 passed, 28 skipped) overlapped a sidecar
metadata copy and Builder observed temporarily empty JSON. Installed sidecars
validate after the write. Rerun with release files held fixed, excluding only
the already-passed disturbed matrix. Use atomic replacement for future sidecar
updates; do not classify this self-induced race as an unrelated test failure.
The stable rerun passed Builder and 2,350 tests before an intentional interrupt
in slow Rosetta inference. Complete the 230 soil-artifact tests as four disjoint
shards and rerun the remainder excluding that module and the already-passed
99-case disturbed matrix. Retain node assignments to account for all tests.

The remainder exposed live-inventory expectations pinned to 260803/261010.
Update those assertions for 261021 and exercise old-project selection without
config migration. Preserve mocked-inventory tests. Resume at the affected module
and exclude only modules already completed successfully; retain coverage logs.

## Decision Log

2026-10-21: Release from the default ASCII v3 line to preserve 261010 behavior
and integration compatibility. User requested build, vendoring and changelog.

## Outcomes & Retrospective

Built and vendored both 261021 binaries and sidecars from committed default-branch
source `a87925df9ffe6ebb928e126395dd159d484285fa`. Native tests: 232 passed;
watchlist: 12/12; both host/container smokes and provenance pass. Fresh 400-year
execution has 146,097 aligned days. Executables match the earlier validated
200-year repair after excluding debug sections/build IDs. Required post-vendor
runner tests: 8 passed; Builder/live-selection tests: 39 passed.

WEPPpy coverage across disjoint final segments: 11,052 passed, 122 skipped
(121 test skips plus one collection skip). Inventory assertions were updated
for the intentionally added release. A combined-suite Redis authentication
failure is test-order dependent: the full 52-test feature-access module passes
alone. Browser tests require a process-local override to the already installed
cache; the configured container path is wrong. No auth or application-config
changes were made, and no single-process full-green claim is made.

Native release artifacts are committed locally as `6a6621e4d`; its checkout is
clean. WEPPpy vendoring/docs/tests remain in the working tree for review.
The original 261010 binaries/changelog entry remain intact. No default switch,
push or production deployment. Existing project outputs require paired
regeneration; valid climate can remain. Atomic sidecar replacement is documented
in `docs/binary-lifecycle.md` after observing a concurrent metadata-read race.
For future broad validation use the existing `wctl run-pytest-sharded` command;
this run retained explicit module/node assignments for reproducibility.

Revision: closed after release gates, generated-output validation, inventory
regressions, and complete segmented coverage; retained all failed/interrupted
attempts and bounded limitations rather than hiding them.
