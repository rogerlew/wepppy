# NoDb Atomicity + RQ Graph Baseline + Observability Follow-Ups

This ExecPlan is a living document. The sections `Progress`, `Surprises & Discoveries`, `Decision Log`, and `Outcomes & Retrospective` must be kept up to date as work proceeds.

This document follows `docs/prompt_templates/codex_exec_plans.md`.

## Purpose / Big Picture

After this package, scoped rq-engine mutation flows should be safer under failure/concurrency stress (without avoidable partial persisted state), queue-graph checks should be trustworthy again, and lock/dump-efficiency regressions should be caught by explicit guardrails. A maintainer should be able to run the scoped regression commands and verify: stable response contracts, clean queue-graph baseline, and maintainable tests with reduced duplication.

## Progress

- [x] (2026-04-25 23:06 UTC) Package scaffold created and scope locked to follow-ups `1,2,3,4,6`.
- [x] (2026-04-26 00:36 UTC) Milestone 1 complete: scoped cross-controller failure-atomicity strategy implemented with closure review triad and no remaining High/Medium findings.
- [x] (2026-04-26 00:43 UTC) Milestone 2 complete: `wctl check-rq-graph` drift resolved by canonical artifact regeneration; triad review found no High/Medium issues.
- [x] (2026-04-26 01:08 UTC) Milestone 3 complete: WEPP/bootstrap post-enqueue hint persistence boundary hardening landed; closure triad reported no remaining High/Medium findings.
- [x] (2026-04-26 01:34 UTC) Milestone 4 complete: lock/dump-efficiency AST guard added; landuse grouped-update rollback gap remediated and re-reviewed clean.
- [x] (2026-04-26 01:50 UTC) Milestone 5 complete: scoped test maintainability cleanup landed (shared WEPP payload doubles + reduced brittle assertions) with closure triad and no remaining High/Medium findings.
- [x] (2026-04-26 01:50 UTC) Milestone 6 complete: package-wide scoped validation and closure gates passed; docs and tracker synchronized.

## Surprises & Discoveries

- Observation: `wctl check-rq-graph` currently reports drift in graph/catalog artifacts despite no queue-wiring edits in the prior package.
  Evidence: prior package closure notes and tracker timeline for `20260425_nodb_lock_dump_efficiency_refactor`.
- Observation: grouped lock preflight + later reacquire introduced a TOCTOU race where WEPP parse could persist before grouped lock conflict surfaced; required single-acquisition lock lifecycle across parse + grouped commit.
  Evidence: Milestone 1 closure re-review findings and final remediation notes in package tracker.

## Decision Log

- Decision: use a new package instead of reopening the closed prior package.
  Rationale: preserves closure auditability and keeps follow-up implementation evidence isolated.
  Date/Author: 2026-04-25 / Codex.

- Decision: run milestones in risk-first order (atomicity + boundary hardening before guard/cleanup).
  Rationale: correctness and contract safety should stabilize before maintainability refactors.
  Date/Author: 2026-04-25 / Codex.

- Decision: sanitize lock-conflict client payloads while preserving full lock details in server logs.
  Rationale: avoid exposing lock owner/token metadata in API error messages.
  Date/Author: 2026-04-26 / Codex.

- Decision: hold grouped soils/watershed locks across WEPP parse + grouped stage/commit instead of preflight unlock/reacquire.
  Rationale: remove TOCTOU window and ensure grouped lock conflicts fail before WEPP parse persistence.
  Date/Author: 2026-04-26 / Codex.

## Outcomes & Retrospective

- Achieved scoped atomicity/boundary hardening goals without expanding into legacy Flask routes.
- Added a repeatable observability guard test to detect grouped-helper regression patterns in scoped rq-engine routes/helpers.
- Maintained contract-safe behavior for enqueue success on post-enqueue hint persistence faults while redacting lock metadata from client-visible paths.
- Package-wide scoped validation and enforcement gates passed at closure:
  - `wctl run-pytest` scoped sweep: `228 passed`, `0 failed`
  - `wctl check-rq-graph`: clean
  - `check_broad_exceptions --enforce-changed`: PASS
- Residual risk accepted as Low: AST guard is structural and should continue to be paired with runtime behavioral suites.

## Context and Orientation

The prior package (`20260425_nodb_lock_dump_efficiency_refactor`) converted selected rq-engine flows from sequential setter writes to grouped single-lock helper flows. That reduced lock/dump churn but left follow-ups:

1. A scoped cross-controller failure-atomicity gap (controller-local atomicity exists, cross-controller atomicity does not).
2. `wctl check-rq-graph` drift in static graph/catalog artifacts.
3. Boundary-hardening/test gaps for post-enqueue WEPP hint persistence error classes and concurrency behavior.
4. Missing explicit observability guard for lock/dump-efficiency regression in scoped paths.
5. Test maintainability debt from duplicated dummy collaborators and brittle assertion patterns.

Primary files expected in scope:
- `wepppy/microservices/rq_engine/wepp_run_payload.py`
- `wepppy/microservices/rq_engine/wepp_routes.py`
- `wepppy/microservices/rq_engine/bootstrap_routes.py`
- `wepppy/nodb/core/wepp.py`
- `wepppy/nodb/core/soils.py`
- `wepppy/nodb/core/watershed.py`
- `wepppy/nodb/base.py`
- `wepppy/rq/job-dependency-graph.static.json`
- `wepppy/rq/job-dependencies-catalog.md`
- scoped tests under `tests/microservices/` and `tests/nodb/`

## Plan of Work

Milestone 1 will define and implement a bounded atomicity strategy for the specific multi-controller mutation flow that still risks partial persistence. The implementation must preserve route response contracts and produce explicit failure semantics.

Milestone 2 will investigate the queue-graph drift and correct the canonical artifacts or source of mismatch so `wctl check-rq-graph` becomes a reliable signal again.

Milestone 3 will harden post-enqueue hint persistence boundary behavior, especially non-`RuntimeError` and lock-contention paths, and lock in behavior with targeted tests.

Milestone 4 will add an observability/guard mechanism that detects lock/dump-efficiency regressions in scoped mutation paths.

Milestone 5 will reduce test maintenance friction in scoped suites by extracting shared collaborators and replacing unnecessarily brittle assertions while preserving behavioral coverage.

Milestone 6 will run package-wide validation and close docs (`package.md`, `tracker.md`, `PROJECT_TRACKER.md`) and archive this ExecPlan to `prompts/completed/`.

## Concrete Steps

From `/workdir/wepppy`:

1. Baseline discovery and design notes for atomicity + boundary behavior.
2. Implement Milestone 1 with targeted tests.
3. Resolve queue-graph drift and verify with:
   - `wctl check-rq-graph`
4. Implement Milestone 3 boundary hardening + targeted tests.
5. Add observability guard and guard tests.
6. Refactor scoped tests for maintainability and rerun affected suites.
7. Run closure validations:
   - `wctl run-pytest tests/microservices/test_rq_engine_wepp_routes.py tests/microservices/test_rq_engine_bootstrap_routes.py tests/nodb/test_wepp_run_payload_grouped_updates.py tests/nodb/test_wepp_job_hint_grouped_updates.py --maxfail=1`
   - additional targeted suites for any added guard tooling/tests
   - `wctl check-rq-graph`
   - `wctl doc-lint --path docs/work-packages/20260425_nodb_atomicity_observability_followups_a/package.md --path docs/work-packages/20260425_nodb_atomicity_observability_followups_a/tracker.md --path docs/work-packages/20260425_nodb_atomicity_observability_followups_a/prompts/active/nodb_atomicity_observability_followups_execplan.md --path PROJECT_TRACKER.md`

## Validation and Acceptance

Acceptance requires:
- scoped atomicity behavior is explicit and regression-tested;
- queue-graph baseline is clean (`wctl check-rq-graph` passes);
- post-enqueue hint persistence boundary behavior is contract-stable and tested for selected error/concurrency paths;
- observability guard exists and passes in CI/local targeted runs;
- maintainability cleanup lands without test regression;
- package docs and tracker capture findings, commands, and residual risks.

## Idempotence and Recovery

Each milestone should be additive and independently testable. If a milestone fails, revert only that milestone’s edits and keep prior validated milestones intact. Queue-graph artifact updates must be derived from canonical tooling output to remain reproducible.

## Artifacts and Notes

Record key command outputs and review findings in:
- `docs/work-packages/20260425_nodb_atomicity_observability_followups_a/tracker.md`
- optional evidence files under `docs/work-packages/20260425_nodb_atomicity_observability_followups_a/artifacts/`

## Interfaces and Dependencies

End-state expectations:
- Scoped atomicity helper interface(s) for selected multi-controller mutation flow, with explicit failure semantics.
- WEPP hint-persistence boundary logic with explicitly tested exception-class behavior.
- A repeatable guard mechanism (test or tool) that flags lock/dump-efficiency regression in scoped paths.
- Queue dependency graph artifacts aligned with canonical tooling (`wctl check-rq-graph` clean).
