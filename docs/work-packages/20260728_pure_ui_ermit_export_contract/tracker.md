# Tracker - SURF-16 Pure UI ERMiT Export Contract

## Status

Closed 2026-07-28 UTC.

## Progress

- [x] Registered SURF-16 after SURF-12 and DOM-14A.
- [x] Ratified the concise launcher/token/job/download/retry contract.
- [x] Expanded direct rendered-template evidence.
- [x] Added real inline-client lifecycle and retry evidence.
- [x] Ran and retained route/session/RQ/worker evidence.
- [x] Repaired the regression-confirmed rejected-token retry mismatch.
- [x] Completed validation, proportional review, parent reconciliation, and
  close.

## Decisions

- Treat SHR-02 and SHR-03A as shared behavior encountered through this concrete
  consumer, not as prerequisite platform audits.
- Preserve all route paths, canonical response keys, scopes, queue wiring,
  artifact schemas, and public/private download policy.

## Mismatch and Repair

The first token request could reject and leave `tokenPromise` permanently
rejected. Clicking Retry then reused the same rejection without making another
token or submit request. The focused Jest regression failed with one token
attempt where two were required. Resetting `tokenPromise` at the start of
`startExport()` makes Retry a fresh attempt while retaining one token within
each attempt.

## Validation

- Focused rendered launcher/Flask routes: 161 passed.
- Focused inline client: 1 suite, 2 tests passed.
- Focused rq-engine export/session and worker: 63 passed.
- Frontend lint passed.
- Full frontend: 90 suites, 673 tests passed.
- Repository-wide Python stopped on the known unrelated GridMET
  `_FakeUnits.degC` fixture failure after 2,455 passed and 40 skipped.
- Independent review: pass; zero unresolved high, medium, or low findings.
- Final child/parent/project docs lint and `git diff --check`: passed.
