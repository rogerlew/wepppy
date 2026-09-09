# Observable named-preset creation failures

This living plan follows `docs/prompt_templates/codex_exec_plans.md`.

## Purpose / Big Picture

Users of `/weppcloud/create/` must learn why a recognized creation failure
occurred, with a useful next action. Every failed response must have a reference
that is searchable in ordinary server logs. Scope is both aliases of the
named-preset create route, not Builder, batch, fork, or upload creation.

## Progress

- [x] Reproduce Portland's `unknown mod portland` with real Ron in rq-engine.
- [x] Prepare canonical diagnostics amendment and independent initial reviews.
- [x] Obtain operator commit authority and all-failure coverage instruction.
- [ ] Review expanded coverage and commit the checkpoint before implementation.
- [ ] Add failure regressions, implement safe diagnostics and complete correlation.
- [ ] Run focused/broad tests and real HTTP creation checks.
- [ ] Complete correctness, QA, security review and commit the scoped fix.

## Surprises & Discoveries

The response contract allowed log-only diagnostics. The route also attached IDs
only as LogRecord metadata, which the deployed text formatter omitted. Legacy
`nodb:mods` overrides can generate the same unknown-module error as an unavailable
shipped preset; guidance must cover both configuration and installation repair.

## Decision Log

2026-09-09 UTC: operator authorized actionable creation errors, then explicitly
authorized committing and observing all create failures. Preserve error status,
codes, auth, publication, and cleanup behavior. Add canonical handling only for
previously uncaught application exceptions. Full raw diagnostics stay in logs;
public disclosure uses the narrow canonical classifications.

## Outcomes & Retrospective

Diagnosis and initial reviews are complete. Implementation and runtime
conformance remain pending. No production deployment is included.

## Context and Orientation

`wepppy/microservices/rq_engine/project_routes.py` exposes `/create/` and is
registered a second time under `/api`. Ron initializes project controllers.
`responses.py` creates JSON error envelopes. Route tests live in
`tests/microservices/test_rq_engine_project_routes.py`. Canonical behavior is in
`docs/schemas/rq-response-contract.md` creation diagnostics/coverage sections
and `docs/schemas/project-creation-policy.md`. The package decision and review
artifacts describe the accepted delta and starting revision.

## Plan of Work

Commit the reviewed contract checkpoint alone. Add route regressions for safe
known causes, hostile/unknown exceptions, both aliases, all failed response
correlation, and unexpected errors. Implement bounded cause classification,
stage-specific infrastructure details, formatted exception IDs, and an outer
route error boundary. Keep optional TTL/README behavior and lifecycle intact.
Update operator/user diagnostics notes and record evidence in the tracker.

## Concrete Steps

From `/home/workdir/wepppy`, run
`wctl run-pytest tests/microservices/test_rq_engine_project_routes.py`, then
`wctl run-pytest tests --maxfail=1`. Use `wctl doc-lint --path` for changed docs.
After focused tests, restart only development rq-engine if necessary to load
the source change and exercise real HTTP using the existing dev-agent identity.
Print no credentials; retain response/log IDs and safe diagnostics as evidence.

## Validation and Acceptance

Portland failure must name `portland`, explain it is unavailable, and give
configuration/installation guidance. Missing files, denied permissions, full
storage and unavailable dependencies/services have distinct safe reasons.
Unknown exceptions never disclose raw strings. Every failed response must have
its ID in formatted log text; exception logs must retain the original traceback
even when cleanup fails. Existing successful, authenticated/CAPTCHA, legacy and
project-owned creation tests must remain green. Real Ron and HTTP evidence
complement mocked failure injection; do not claim exhaustive controller states.

## Idempotence and Recovery

Do not change run cleanup, queue wiring, parameters, or retry behavior. Real
failure checks may leave artifacts if existing cleanup fails; record that
separately and remove only identified test-owned leftovers when safe. Exclude
all unrelated working-tree changes from commits. Roll back only this package's
code change if the development smoke reveals a regression.

## Artifacts and Notes

Initial real-container evidence: `portland module registered: False` followed
by `initialization exception: Exception unknown mod portland` (20:38 UTC).

## Interfaces and Dependencies

Use standard-library exception/errno classifications and existing Redis,
SQLAlchemy, FastAPI and canonical response helpers. No new dependency, public
endpoint, or data schema is needed.

2026-09-09: created after the operator expanded the task to every create failure.
