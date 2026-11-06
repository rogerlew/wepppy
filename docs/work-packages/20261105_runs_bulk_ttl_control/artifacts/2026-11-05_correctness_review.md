# Correctness and UX review: Runs bulk TTL control

## Metadata

Independent reviewer: `ttl_contract_correctness`; date: 2026-11-05.
Contract ancestor: `6cbd4404b`. Reviewed user.py, runs2.html, changed route tests,
inline-handler regressions and published run-ttl-deletion guide against the
catalog/TTL/projection contracts in the checkpoint.

## User outcome and valid states

Earliest expiration sorting includes overdue dates, nulls last both ways.
Selected runs receive independent protection requests with explicit partial
outcomes. Empty selections and readonly rows do not request mutations. Existing
batch exclusion is accepted. Missing/invalid responses and null TTL do not
confirm protection; queued/trash/purged results explain deletion cannot be undone.
Network, CSRF and authorization errors remain visible and retryable. Hostile
labels/errors render as text. Existing real TTL-file tests cover missing,
empty/legacy normalization without changing that persistence boundary.

## Findings and disposition

Medium: failed alias reload retained catalog arrays, allowing later search to
resurrect prior-scope rows. Fixed by clearing both arrays on scope reload and
covering failure followed by filtering. Reviewer independently reproduced the
pre-fix issue and confirmed the final correction with the 16-test suite.
Low: obsolete catalog request failures could replace a newer successful view.
Fixed by checking request generation in the error handler, with regression.
Both findings are resolved; reviewer reports no remaining high/medium/low issues.

## Evidence and limits

104 focused Python tests passed, including direct registered-route authorization,
CSRF and TTL-file persistence tests. Frontend handler tests execute the actual
inline script with mocked transport. The parent also exercised the actual
rendered template in Chromium: header target, checked-row requests, prefixed
URLs, CSRF header, success row, failed-row retry selection, and no page errors;
see `chromium-smoke.json`. HTTP responses in that smoke are mocked, not production.
No model-generated artifacts apply. Broader Python validation recorded separately.

## Final narrow-screen correction

Chromium at 375px found button overflow. Scoped table-panel minimum width and
action/text wrapping put the button at x=25, width=325. The reviewer confirmed
this preserves action order/semantics and affects no other toolbar or map panel.

## Disposition

Correctness/UX gate: PASS after fixes. Local implementation only; production
deployment and a live production user workflow are not claimed.
