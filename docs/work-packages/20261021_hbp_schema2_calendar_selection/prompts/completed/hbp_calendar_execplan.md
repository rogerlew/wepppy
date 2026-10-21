# Deliver binary PASS records on the requested routing date

This living ExecPlan follows `docs/prompt_templates/codex_exec_plans.md`.

## Purpose / Big Picture

Fix the confirmed schema-2 binary PASS date-selection defect in the native
`/workdir/wepp-forest` development implementation. Its writer emits 366 slots
per year; watershed routing requests actual simulated days. Sequential slot
consumption currently substitutes synthetic day 366 for the following January 1.
Correct delivery must select the matching year/day, including the final day.
This is an authorized behavioral bug fix, not modernization or a scaffold.

Roger authorized this correction on 2026-10-21 after the observation-only
investigation closed. That package remains immutable. `wepp_261010` uses ASCII
PASS components version 3 and is outside this binary-reader fix. Jackson's
separate 100-year issue is deferred. Do not release, vendor, deploy, mutate live
projects, change calendar policy, or change hydrologic equations.

## Progress

- [x] 2026-10-21: Confirm authority, source path, existing baseline and failure.
- [x] 2026-10-21: M1 contract and failing date-selection regression retained.
- [x] 2026-10-21: M2 exact-date lookup and production wiring; schema1/2 and
  legacy-centurial dated regressions pass.
- [x] 2026-10-21: M3 both native targets/host smoke and fresh reader suite pass;
  two 44-year controlled cases and the 28-hillslope, 43-year project pass
  date readback, unchanged hillslope products and observation off/on parity.
  Broad-suite limitations are reproduced and retained, not hidden.
- [x] 2026-10-21: M4 correctness then source QA pass; final runtime review
  approves development closure. Evidence and discovery links updated.

## Surprises & Discoveries

Fresh isolated FPM validation exposes a preexisting WBK08 test calling an obsolete
geometry argument. The shared cached FPM executable instead segfaults on that
mismatch. A cached hourly-adapter failure disappears on fresh baseline/candidate
builds. These are retained as broad-suite limitations, not repaired in this task.
A newly generalized centurial fixture initially retained a hard-coded year index;
that test-only error was corrected and the failed attempt retained.

The reader already stores simulation-year, calendar-year and Julian-day keys.
Production bridge calls only a sequential-slot API. Existing direct-reader tests
exercise first days and malformed payloads, not multiyear routing selection.

## Decision Log

2026-10-21: Accept the development correction after full-period generated-output
readback and independent final review. Keep broad-suite baseline failures visible;
do not expand this fix into unrelated storage-test repair or calendar-policy
changes. No release/vendoring/deployment or ASCII century investigation occurred.

2026-10-21: Preserve writer bytes and the established legacy-centurial calendar.
Add paired optional requested year/day arguments to the reader API; dated loads
select the exact directory key, while undated calls retain sequential inspection
compatibility. Wire the production bridge with the watershed's current year/day.
Reject absent dates or a partial request explicitly; never substitute another day.
Use binary search on validated ordered simulation-year/day keys, with calendar
verification, rather than a repeated linear scan of long stochastic trajectories.

Compatibility/regression plan: no on-disk schema or user-visible column changes.
Schema 1 and 2 read compatibility, undated iteration and existing corruption
rejections remain covered. Scientific watershed output changes after the first
padding boundary are expected; same-build hillslope/HBP outputs must stay exact.
Candidate observations off/on must remain exact. Corrected loaded volumes must
match independent date-keyed HBP readback for every simulated day and flux.
This is temporal selection, not a parameterization/formula/default change; no
parameterization ADR is required. Security impact: none, existing offline reader.

## Outcomes & Retrospective

Implemented and wired the requested-date reader. Both controlled cases and the
43-year real project pass date-keyed readback through the final day. All 196 real
hillslope products remain identical to baseline; all 388 ordinary real files are
identical between corrected off/on runs. The first controlled EBE divergence is
exactly the repaired date, 1982-01-01. Independent correctness and QA pass.

Native pytest has 193 passes and one missing external fixture failure. Full FPM
is limited by preexisting WBK08 test/API drift and stale cached hourly executables;
fresh baseline/candidate comparisons and the fresh reader suite establish the
bounded disposition. No physical-domain closure, release or deployment claim.
Jackson's ASCII century issue remains separate. Retained commands, hashes and
review are in `artifacts/validation.md`, `provenance.json` and `correctness_review.md`.

## Context and Orientation

`fpm-src/hillslope_binary_pass_reader.f90` validates/hydrates HBP shards and
loads watershed arrays. `src/hbp_mode2_bridge.f90` bridges those arrays to legacy
COMMON state; `src/wshred.for` owns the read call during routing. The normative
contract is `docs/contracts/watershed-hillslope-pass-reader-contract.md` in the
native repository. Extend `fpm-test/ps05_mode2_direct_reader_tests.f90` for the
reader regression, retaining existing writer helpers and format contracts.

The prior investigation retained unchanged and instrumented binaries, complete
inputs, probes, controls and traces at
`/wc1/holdouts/watershed-channel-routing-closure-20261021` and
`/workdir/watershed-channel-routing-closure-20261021`. Preserve those and unrelated
dirty files in both repos. Build/replay new attempts under
`/workdir/hbp-schema2-calendar-selection-20261021` with source/input/binary hashes.

## Plan of Work

M1 documents exact-date selection and tests a generated multiyear shard with
uniquely identifiable fluxes around ordinary/leap boundaries, final-day lookup,
invalid requests and unchanged schema-1 behavior. Show the regression fails
before the behavior fix (a compatibility API skeleton may compile the red test).

M2 adds paired optional date arguments, bounded key lookup and explicit missing
key errors. Move cursor only after successful selection/loading. Pass actual
routing date from wshred through the bridge without changing COMMON layouts.
Update the bridge's source contract if missing. Preserve observation probes.

M3 builds isolated watershed/hillslope targets with the same gfortran/link flags
as the retained baseline. Run native FPM and pytest, Fortitude and smoke checks.
Replay at least single/60-40 and the retained real project over full periods.
Use existing retained harnesses with new destinations. Date-keyed readback must
have zero violations; fresh same-build HBP files must equal baseline byte for
byte. Capture changed downstream results explicitly, not as parity failures.
Candidate off/on must match all ordinary files. Broaden topology replays if
needed for new routing failures. Full-domain physical closure remains unproven.

M4 applies the mandatory native `.f90` correctness reviewer followed by QA,
resolves implementation blockers, records exact checks/limitations, moves the
completed plan and updates package/tracker/root discovery links.

## Concrete Steps

From `/workdir/wepp-forest`, use `fpm test --target ps05_mode2_direct_reader`,
`fpm test`, `pytest`, and `fortitude check` on touched free-form sources/tests.
In isolated source `src/`, build with
`make FC=/usr/bin/gfortran LDFLAGS='-mcmodel=medium -no-pie -lz' wepp` and the
same command for `wepp_hill`. Run canonical `tools/smoke_wepp_binary_host.sh`
on both binaries. Retain logs rather than relying on exit status alone.

From `/workdir/wepppy`, lint this package with `wctl doc-lint --path
 docs/work-packages/20261021_hbp_schema2_calendar_selection`, run
`tools/check_agents_size.sh AGENTS.md`, and scoped `git diff --check`.

## Validation and Acceptance

A rebuilt production call path must deliver requested-day surface, lateral,
tile, groundwater and sediment values through ordinary/leap transitions without
calendar lag. Missing dates fail explicitly; existing schema1/sequential behavior
passes. Generated project artifacts and off/on comparisons are required in
addition to unit tests. Release/deployment and the ASCII century investigation
remain separate work.

## Idempotence and Recovery

Use new attempt directories. Preserve failed runs and baseline receipts. Do not
clean shared source checkouts or overwrite release binaries. If the correction
fails, retain evidence and revise only this behavior group. No branch switching.

## Interfaces and Dependencies

Reuse the native directory index, observation hooks and independent installed
wepppyo3 HBP parser. Add no dependencies, services, persisted fields or file types.

## Revision Notes

2026-10-21: Initial execution plan records explicit authorization and acceptance.

2026-10-21: Completed M1–M4 with exact artifact receipts and explicit broad-suite
limitations. Closed the development fix; no release promotion.
