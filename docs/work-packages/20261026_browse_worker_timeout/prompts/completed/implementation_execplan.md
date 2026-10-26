# Restore honest browse/download filesystem access

Maintained under docs/prompt_templates/codex_exec_plans.md. The original timeout
package now includes Roger's explicit reversal of generic Roads admission.

## Purpose and context

Users must inspect/download existing files even when model results are stale,
incomplete or invalid. Security/PII restrictions remain. Generic browse code in
wepppy/microservices/browse and direct D-Tale file viewing gained Roads gates in
e4d28c9ad. Those edits have no later changes in the affected implementation files.
The current large-project manifest times out; its historical collector is fast.
The original explicit 120-second wepp1 timeout remains in scope, without deployment.

## Progress

- [x] Read production evidence and run bounded HTTP load probes; no 500 reproduced.
- [x] Record operator-authorized contract reversal and canonical amendments.
- [x] Obtain contract reviews and commit standalone contract checkpoint 8b56c3d94.
- [x] Restore generic file paths; 333 targeted regressions pass, large project readback passes.
- [x] Run targeted and broad checks, large-project readback, review and close.
- [x] Commit implementation; deployment remains separate.

## Surprises & Discoveries

Friday's two-second 500 lacks retained logs. Monday's collector adds realpath per
file: first 1,000 checks cost 1.514 seconds; historical 155,573-entry collector
cost 2.679 seconds. Container-local logs disappear on recreation. A raw retired
NoDir archive exclusion may also violate the new directory-transparency rule.

## Decision Log

Roger rejected generic lifecycle filtering on 2026-10-26. Only security and PII
may guard physical access. Preserve model report/query/producer admission and
D-Tale byte consistency; remove the generic file-layer mechanism. This is an
explicit reversal, not an optimization that preserves semantic hiding.

## Plan of Work and milestones

First checkpoint amended contracts after independent reviews. Then reverse the
Roads-only browse/D-Tale edits and remove their unused helper; retain auth and
path validation. Update affected tests to actual-directory semantics, covering
unreceipted files, an active producer lock, aliases and denied paths. Render the
timeout Compose configuration and run wctl targeted tests, then the required
broad sanity suite. Retain exact results and limitations before package closure.

## Concrete Steps and acceptance

Work in /workdir/wepppy. Use wctl run-pytest for tests/microservices/test_browse*,
D-Tale freshness/security suites and tests/wepp/interchange/test_roads_lifecycle.py.
Run wctl run-pytest tests --maxfail=1 and scoped wctl doc-lint. Compare actual
manifest entries and bytes with real files; validate large-project collection
without deploying application changes or mutating the project. Existing security
negative cases must still pass. No HTTP success may be inferred from metadata.

## Idempotence, recovery, interfaces and dependencies

Changes use existing services/libraries only. Restore prior source deliberately,
never overwrite unrelated work. Revert this package's commits if needed; no run
files or production services are changed. Roger owns later deployment. Capture
logging and original-500 limits as follow-ups, not claimed fixes.

## Outcomes & Retrospective

Completed locally on 2026-10-26. Contract checkpoint 8b56c3d94 precedes
implementation. Focused suite: 333 passed; full regression coverage completed
in segments after correcting one obsolete filename-ban expectation. Exact
commands, results and environment are in execution_evidence.md. Independent
correctness/security findings resolved. Production rollout and the historical
500 root cause remain separate. Logs must survive container recreation in a
follow-up; this package does not implement persistent logging.
