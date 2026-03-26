# Disturbed Lookup UI Safeguards Addendum

This ExecPlan is a living document. The sections `Progress`, `Surprises & Discoveries`, `Decision Log`, and `Outcomes & Retrospective` must be kept up to date as work proceeds.

This plan follows `docs/prompt_templates/codex_exec_plans.md`.

## Purpose / Big Picture

After this addendum, stale disturbed-lookup pages are identified in the editor UI, editing is locked when stale, users can load current data/refresh from explicit controls, and server-side optimistic concurrency blocks stale overwrites. The save action is hardened against double-submission behavior by in-flight locking on both save button state and table editability.

## Progress

- [x] (2026-03-26 00:25Z) Reopened package for stale-page and double-submit safeguards.
- [x] (2026-03-26 00:52Z) Added server-side snapshot/meta support and strict optimistic-concurrency save checks.
- [x] (2026-03-26 01:01Z) Updated editor UI for stale polling lockout, current-data reload, refresh action, and in-flight save lock behavior.
- [x] (2026-03-26 01:16Z) Expanded route/template regression coverage for lookup snapshot contract and optimistic-concurrency failure paths.
- [x] (2026-03-26 01:30Z) Added write-path observability logs for all blocked/committed save outcomes.
- [x] (2026-03-26 01:40Z) Completed validation gates (`routes`, disturbed module suites, stubtest, test-stub check, full `tests --maxfail=1`).
- [x] (2026-03-26 01:48Z) Completed code review + QA review subagent reviews and resolved reported high/medium findings.
- [x] (2026-03-26 01:52Z) Updated package docs/tracker/project tracker and re-closed package.

## Surprises & Discoveries

- Observation: Loading CSV and hash from separate endpoints can produce a transient baseline mismatch if writes happen between reads.
  Evidence: Prior editor flow downloaded CSV and fetched metadata independently.

## Decision Log

- Decision: Introduce a locked snapshot endpoint that returns CSV + hash together.
  Rationale: Remove baseline desynchronization window at editor load time.
  Date/Author: 2026-03-26 / Codex.

- Decision: Require `if_match_sha256` for disturbed lookup writes and return explicit `428`/`409` contracts when preconditions fail.
  Rationale: Eliminate stale overwrite paths from long-open tabs and old client states.
  Date/Author: 2026-03-26 / Codex.

- Decision: Keep `?pup` compatibility unchanged.
  Rationale: User explicitly requested compatibility retention.
  Date/Author: 2026-03-26 / Codex.

## Outcomes & Retrospective

Completed on 2026-03-26.

Delivered outcomes:
- Added optimistic-concurrency precondition enforcement (`if_match_sha256`) and stale/write-block contracts in disturbed save route.
- Added `lookup_snapshot` endpoint for atomic CSV+hash load baseline.
- Added stale polling/lockout UX with explicit "Load Current Table" and "Refresh Page" actions.
- Added in-flight table edit lock to reduce double-submit/user-confusion risk.
- Added write-path observability for blocked and committed save outcomes.
- Added/updated route tests for missing precondition, stale mismatch, unavailable hash, snapshot contract, and template wiring.

Residual risks:
- Browser-level E2E polling/race behavior is not covered by Playwright tests in this package.

## Context and Orientation

Disturbed lookup editor code is rendered from `wepppy/weppcloud/templates/controls/edit_csv.htm`. Route APIs are in `wepppy/weppcloud/routes/nodb_api/disturbed_bp.py`. Lookup persistence and hashing helpers live in `wepppy/nodb/mods/disturbed/disturbed.py`. Route regressions are in `tests/weppcloud/routes/test_disturbed_bp.py`.

## Plan of Work

The addendum implemented three layers:
1. Route contracts: add atomic snapshot endpoint and strict optimistic-concurrency write checks.
2. UI behavior: stale polling, lockout controls, baseline-hash-aware save payloads, and in-flight save locking.
3. Coverage and observability: route regression tests for new contracts and explicit structured logs on write block/commit outcomes.

## Concrete Steps

Run from `/workdir/wepppy`:

1. `wctl run-pytest tests/weppcloud/routes/test_disturbed_bp.py --maxfail=1`
2. `wctl run-pytest tests/nodb/mods/test_disturbed_lookup_persistence.py --maxfail=1`
3. `wctl run-pytest tests/nodb/mods -k disturbed --maxfail=1`
4. `wctl run-stubtest wepppy.weppcloud.routes.nodb_api.disturbed_bp`
5. `wctl check-test-stubs`
6. `wctl run-pytest tests --maxfail=1`

## Validation and Acceptance

Acceptance criteria for this addendum:
- Stale writes are blocked server-side when `if_match_sha256` mismatches current file hash.
- Save requests without `if_match_sha256` are rejected.
- UI marks stale state, locks editing, and offers explicit reload/refresh actions.
- Save action is guarded against in-flight duplicate submissions.
- All listed validation commands pass.

## Idempotence and Recovery

Lookup writes remain atomic (`os.replace` semantics in disturbed module). On stale precondition failure, lookup file remains unchanged and users can reload current table state. UI reload action is idempotent and can be repeated without side effects.

## Artifacts and Notes

- Code review findings: `docs/work-packages/20260325_disturbed_lookup_hardening/artifacts/code_review_findings.md`
- QA review findings: `docs/work-packages/20260325_disturbed_lookup_hardening/artifacts/qa_review_findings.md`

## Interfaces and Dependencies

- Route: `POST /runs/<runid>/<config>/tasks/modify_disturbed` now enforces `if_match_sha256` precondition for writes.
- Route: `GET /runs/<runid>/<config>/api/disturbed/lookup_snapshot` returns CSV text + hash fingerprint from one locked read.
- UI contract: editor sends `{rows, if_match_sha256}` and handles `409/428` write-block outcomes.
