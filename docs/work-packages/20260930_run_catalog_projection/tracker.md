# Run catalog projection tracker

**Updated**: 2026-10-01 UTC
**Status**: Forest steps 1–5 complete; PostgreSQL reads live; observation/promotion pending.

Implementation evidence and current findings:
[review disposition](artifacts/2026-09-30_implementation_review.md),
[producer inventory](artifacts/producer_inventory.md), and
[operator/developer guide](../../dev-notes/run-catalog-operations.md).
Clarification checkpoint: `bf6b0584f7d9a4831576559e9354ff4bb53fa8b6`.
Broad suite: 10,034 passed, 99 skipped, 12 subtests before final review fixes.
Final functional targeted validation: 487 passed, three performance cases
deselected and measured separately. Profiling identified commit-dominated,
phase-sensitive timing. Counterbalanced SQL/performance validation passed 24
tests; corrected matched READONLY evidence and the final eight-test reader suite
also passed. See [validation and retained risks](artifacts/2026-09-30_predeploy_validation.md).
Forest deployment evidence: [run sheet](artifacts/2026-10-01_forest_deployment.md).
No completed host soak, representative production-scale acceptance or promotion
is claimed.

## Task board

- [x] Profile wepp1; retain filesystem/SQL timing evidence.
- [x] Establish standalone requirement and operator-endorsed architecture.
- [x] Author complete schema, failure/concurrency protocol, operating limits,
  implementation sequence, and forest → forest1 → wepp1 rollout specification.
- [x] Create ADR, execution package, active ExecPlan, and review gates.
- [x] Independent correctness/security contract reviews and findings disposition.
- [x] Operator ratified the reviewed plan by authorizing execution on 2026-09-30 UTC.
- [x] M0: acceptance checkpoint `db8e6be126fb231f16dd5e76f322d2b03089c10c` precedes runtime edits.
- [x] M1 implementation: additive migration/repository/extractor and real SQL/file tests.
- [x] M2 implementation: portable observer and inventoried producer/process wiring.
- [x] M3 implementation: maintenance, scheduler, CLI, metrics and isolated timing/fairness evidence.
- [x] M4 implementation: SQL readers, compatible payloads, freshness UI and isolated browser/HTTP tests.
- [ ] M5 host evidence: production-equivalent initialization/mounts, queue capacity, network/browser timing and full producer/consumer witnesses.
- [ ] M5a: forest acceptance and healthy observation.
- [x] Forest candidate commit, migration, consumer proof, shadow/backfill and read cutover.
- [ ] M5b: forest1 test-production rehearsal and healthy observation.
- [ ] M5c: wepp1 shadow/backfill/cutover and healthy observation.
- [ ] Legacy reader retirement disposition and final review/closeout.

## Decisions — 2026-09-30 UTC

The operator requires portable projects without PostgreSQL and endorsed a
separate rebuildable catalog plus storage-neutral notifications/reconciliation.
The operator explicitly selected forest, then forest1, before wepp1. Exact
schema/protocol and proposed numeric limits are documented in the canonical
[specification](../../schemas/run-catalog-projection-contract.md) and
[ADR](../../adrs/ADR-0078-run-catalog-projection.md); they are not claimed deployed
or independently ratified. Specification commit: `62d4273d9`; the operator
subsequently requested contract review and findings disposition. No runtime or
production mutation was made.

## Discoveries and risks

NoDb already mirrors last-modified through a web-app import; replace it rather
than adding a second competing path. READONLY and TTL are outside generic Ron
dump coverage. Forest1 test production is not the forest1 companion batch worker.
Other hosts may share the target database/queue/storage: preflight must inventory
their producers and not claim notification freshness for old binaries.

Current source counters are 805 registered versus 615 returned in one wepp1
observation. Omission classification must be audited during backfill, not guessed.
The proposed scheduler cadence requires verification against existing jitter/
startup behavior; synchronous database mirrors require explicit failure budgets.

## Validation and evidence

Retained: [wepp1 investigation](../../investigations/2026-09-30-user-runs-performance.md).
Specification-session validation: all scoped documentation lint commands passed
with zero errors/warnings; eight new specification/package files have no broken
relative link targets; spelling preview reviewed and new prose normalized;
diff whitespace checks passed. Existing unrelated spelling suggestions were
left unchanged. No runtime tests or deployments are claimed.
Future artifacts: producer inventory; compatibility corpus; SQL/file fault and
race evidence; per-host preflight, comparison, latency, freshness, rollback,
full-cycle/observation run sheets; and final independent reviews.

Review-session validation: scoped documentation lint passed with zero errors or
warnings; relative link targets and `git diff --check` passed. Spelling preview
found only unrelated existing tracker suggestions, left unchanged. No runtime
tests were run because this change set only revises documentation.

## Review and checkpoint status

[Contract decision](artifacts/2026-09-30_contract_decision.md),
[correctness review](artifacts/2026-09-30_correctness_review.md), and
[security review](artifacts/2026-09-30_security_review.md) record independent
post-fix PASS verdicts. The [disposition record](artifacts/2026-09-30_contract_review_disposition.md)
closes all ten distinct findings (including one author finding and one duplicate
reported by both reviewers); none is risk-accepted. Runtime gates remain pending.
Contract ancestor SHA: `db8e6be126fb231f16dd5e76f322d2b03089c10c`.
Implementation SHA: `3e6cbdcb9`.
Do not treat the architecture endorsement as a completed independent review.

## Next handoff

Forest steps 1–5 are complete. Web reads are postgres; producers use catalog
writes; the existing scheduler admits 15-second sweeps. Forest-local schedule
activation remains an intentionally uncommitted configuration change; do not
ship it as a global default. The gitignored forest env retains mode settings.
Keep the two dev-agent smoke projects as deployment witnesses for observation.
Complete remaining host acceptance, rollback rehearsal and >=48 healthy hours
before promotion. Representative host-scale evidence belongs on the first
eligible stage, before wepp1 cutover if necessary. No other host was deployed.
