# Creation failure diagnostics tracker

## Progress

- [x] Locate the route and matching Portland failure in Forest logs.
- [x] Establish that the current contract permits log-only diagnostics.
- [x] Identify missing correlation ID in ordinary text log output.
- [x] Complete two independent contract reviews and resolve their findings.
- [x] Commit the reviewed checkpoint with operator authority: `bf063ed56`.
- [x] Implement bounded public diagnostics and text-log correlation.
- [x] Run focused and live regression checks.
- [x] Complete broad regression suite and prepare final scoped implementation commit.
- [x] Complete independent correctness, QA, and security review.

## Decisions

2026-09-09 UTC: classify actionable public diagnostics as an intended contract
amendment, because the existing shared contract explicitly permits log-only
details. The operator's request authorizes the behavior change. A scoped
checkpoint commit was requested separately under the repository standard, then
explicitly authorized and committed as `bf063ed56`. Existing unrelated
working-tree edits remain excluded from both commits.

## Findings and limits

Ron raises `Exception: unknown mod portland`. The runtime cannot initialize
that required module. Repairing its installation/registration is separate from
making the failure understandable. A cleanup `Directory not empty` exception
also occurred and is recorded as an independent follow-up, not the cause of
the initialization failure.

## Validation

Implementation evidence (2026-09-09 UTC): new regression failed on the original
Portland response before patching. Final focused project/Builder suites:
132 passed (113 project, 19 Builder). Broad-exception changed-file enforcement
passes with no unsuppressed increase. Code-quality telemetry ran to `/tmp`
without overwriting the operator's existing report files; the existing creation
function remains large because lifecycle refactoring is outside this patch.

Real browser login used the existing dev-agent credentials and solved the login
CAP challenge. Clicking the actual Portland create form returned HTTP 500,
`run_initialization_failed`, a module-specific explanation and repair guidance.
After reloading the changed service, ID `ffb1fc4ed5c7479f99df36747fe47469` matched
the original traceback, the secondary cleanup traceback, and the response
summary's status/code. Temporary smoke runs `hard-fought-plush` and
`intensional-shallot` were removed with the canonical cleanup helper after
releasing their open handles by restarting development rq-engine. No user run
was removed. The observed cleanup issue is existing lifecycle debt.

Real HTTP missing-config checks returned 400 `validation_error` for both
aliases, with IDs `eeaaa8f14b0b45859f093db5eb4c3988` and
`4202e4c66d52431f8de2f12c4e2ff9a7`.

First broad sweep stopped after 908 passes on a shared-helper compatibility
regression: Builder used the existing two-argument release helper. Restoring an
optional error ID preserved that call contract; both route suites then passed.
Correctness and security reviewers confirmed the fix. The broad rerun passed:
8,110 passed, 72 skipped, 3,110 warnings in 806.80 seconds. Existing warnings
were retained; no new warning suppression was introduced.
Correctness COR-03 and both low QA suggestions are resolved with independent
confirmation; security has zero unresolved findings and its validation
conditions are satisfied. Package closed locally on 2026-09-09.

### Initial checkpoint evidence

2026-09-09 20:38 UTC: unmocked `Ron(wd, 'portland.cfg')` in a temporary
directory inside the running rq-engine container raised
`Exception: unknown mod portland`; the registry did not contain `portland`.
The temporary directory was cleaned successfully. This reproduces the source
failure without changing a user run. It does not validate a changed HTTP response.

The package's three documents and both amended canonical contracts pass
`wctl doc-lint` with zero errors or warnings. No implementation edits or pytest
executions yet. Two independent contract reviews passed after the bounded
request-derived module identifier rule and configuration-repair guidance were
clarified; COR-01 and SEC-C01 are resolved with reviewer confirmation.

The initial checkpoint passed both independent reviews. Baseline focused suite:
67 passed. The final `PROJECT_TRACKER.md` pointer is staged independently of its
preexisting unrelated edits.
