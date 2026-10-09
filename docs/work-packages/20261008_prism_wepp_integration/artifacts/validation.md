# Validation ledger

All commands used the configured forest dev stack through `wctl` unless noted.
Regression coverage completed through the original run and its continuations.
The full suite found a single-input capability-catalog defect after 4,964 passes;
the append-only correction and targeted checks passed. A later unrelated Redis
authentication failure in an OpenET test did not reproduce in the passing tail.
This is not a claim that one uninterrupted full-suite invocation passed.

| Check | Result |
| --- | --- |
| Reader-floor compatibility | 75 passed |
| Initial catalog/router/year-bounds/bulk focus | 88 passed, 1 failed; partial-controller compatibility fixed and year-bound module passed in subsequent 134-test run |
| Native PRN/CLIGEN/CLI adapter | 2 passed |
| Compatibility, year bounds, canonical archive/restore and publication | 134 passed |
| Independent adapter/publication review run | 7 passed |
| Independent graph/schema/archive review run | 201 passed |
| Same-cell scaling, postcommit diagnostic failure and contention regressions | 45 passed |
| Explicit mode 16 revision failure/readiness and postcommit status | 2 passed |
| RQ missing observed-year rejection, including mode 16 | 2 passed |
| Climate JavaScript focused suite | 19 passed |
| Full frontend lint/test | Lint passed; 113 suites, 925 tests passed |
| Core climate, bulk-client and new adapter stubtest | All passed |
| Test-stub hygiene | Passed |
| Broad exception enforcement against origin/master, scoped to PRISM-touched production paths | Passed; net broad-handler delta 0 |
| Documentation lint | Changed package/contract/ADR/design/user docs passed |
| Full Python suite: `wctl run-pytest tests --maxfail=1` | 4,964 passed, 51 skipped, 1 failed in 34m44s; missing single-input reader structure corrected |
| Builder/capability suite after correction | 94 passed |
| Single-input creation and explicit-refresh regressions | 14 passed |
| Aggregate reader authority after final revision metadata | 75 passed |
| Remaining full-suite modules, including the corrected failed module | 5,219 passed, 75 skipped, 1 unrelated Redis-auth failure in 8m52s |
| Final tail, including the Redis-auth failed module | 301 passed in 1m48s; all remaining collected modules covered |

Tests overlap; counts must not be summed as unique coverage. The full suite was
collected before the last review fixes and scaling/status/readiness/route
regressions; current affected paths are covered by the explicit subsequent
targeted runs and independent graph/schema/archive tests. No queue edges
changed, so no RQ graph regeneration was needed. Both live WEPP trees were
inspected through `wepppy.rq.job_info` and every job finished.

## Observe-only quality and review

Independent [correctness review](correctness-review.md) closed all four findings
and reports no unresolved high/medium issue. See [forest acceptance](forest-results.md)
for actual identities, mounts, cache, CLI consumption, model output and source
portability evidence. CLIGEN convergence under the existing silent-pass setting
is a retained material limitation.

The quality tool normally compares committed `base...HEAD` paths only. For the
retained [working-change report](code-quality-summary.md), its in-memory Git
argument was changed to compare `base` against the working tree; no tool source
was edited. New Python files were marked intent-to-add so they were included.
Radon was unavailable, so Python cyclomatic complexity was not measured.
The new builder's 101-line function is yellow: keeping collection, guarded
publication and retained-outcome handling together makes the transaction
boundary explicit. Existing climate/catalog/controller additions are bounded;
no broad refactor was introduced to improve telemetry alone.

## Failed probes and recovery

- An initial year-bound test exposed a partial controller lacking `_climate_mode`;
  the existing-compatible `getattr` check fixed it, and the focused suite passed.
- The old expected current CONUS graph tuple needed the additive PRISM ID; stored
  historical graph expectations remain unchanged.
- Host frontend bundle generation lacked Jinja2. The configured container build
  succeeded; full frontend lint/tests passed.
- Two browser attempts stopped at a collapsed seed field before enqueue. Opening
  its closed ancestor sections allowed the real submission; no job was duplicated.
- Initial bulk stubtest rejected an annotation note in an untyped constructor.
  Moving the public attribute annotation to class scope resolved it without a
  runtime behavior change; the final check passed.
- A targeted command named a nonexistent schema test filename and collected no
  tests. The correct schema-defaults module passed in the independent 201-test run.
- The full suite found the omitted single-input reader structure. Correction
  checkpoint `5b97490e7` and aggregate reader floor `6781de988` precede successful
  variant publication. Both representations and explicit refresh passed targeted
  regression and exact committed-reader reopening.
- The first continuation stopped after 36 passes on an outdated current-CONUS
  preset inventory. Current preset/registry expectations were extended to PRISM;
  frozen historical fixtures were preserved. The same remaining 389 modules were
  restarted, retaining that failed probe separately.
- The next continuation stopped in
  `test_openet_signed_token_live_membership_admission`: expected 403, received 503
  because submission-lock Redis authentication failed before climate logic.
  The complete 33-test feature-access module and the rest of the 301-test tail
  passed in isolation, without changing that test or the admission code.
- Spelling normalization was previewed. Suggested changes to `afterward` and
  `pre-test` were editorial and not applied automatically.

The initial workspace-wide broad-exception check passed. A later check observed
concurrent non-PRISM RQ notification edits and reported a per-file increase at
`wepppy/rq/wepp_rq_stage_finalize.py:169`. Readback against origin/master shows
the existing boundary handler unchanged: three inserted narrow-handler lines
shifted its location relative to the line-based allowlist. The workspace check
remains flagged; the explicit PRISM-path enforcement passed. Those concurrently
edited files were untouched and are not certified by this review. Unrelated
paper/calibration work and its tracker entries were preserved.

Host logs are `/tmp/prism-*.log`; durable scientific/runtime evidence is retained
in this package and the target run's archives. Credentials and environment
secrets are excluded.
