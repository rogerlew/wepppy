# Run catalog projection tracker

**Updated**: 2026-09-30 UTC
**Status**: Specification complete; implementation and deployment pending.

## Task board

- [x] Profile wepp1; retain filesystem/SQL timing evidence.
- [x] Establish standalone requirement and operator-endorsed architecture.
- [x] Author complete schema, failure/concurrency protocol, operating limits,
  implementation sequence, and forest → forest1 → wepp1 rollout specification.
- [x] Create ADR, execution package, active ExecPlan, and review gates.
- [ ] M0: independent contract reviews, finding disposition, approved ancestor.
- [ ] M1: additive migration/repository/extractor and real SQL/file parity tests.
- [ ] M2: portable observer and complete producer/process wiring.
- [ ] M3: refresh/reconciliation, scheduler, CLI, metrics, capacity evidence.
- [ ] M4: database readers, compatible payloads, freshness UI and browser tests.
- [ ] M5a: forest acceptance and healthy observation.
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
or independently ratified. No new branch/commit or production mutation was made.

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

## Review and checkpoint status

[Contract decision](artifacts/2026-09-30_contract_decision.md),
[correctness review](artifacts/2026-09-30_correctness_review.md), and
[security review](artifacts/2026-09-30_security_review.md) describe pending gates.
Contract ancestor SHA: **not created**. Implementation SHA: **none**.
Do not treat the architecture endorsement as a completed independent review.

## Next handoff

Begin M0 review of the specification/ADR/shared amendments; resolve detailed
policy questions through that checkpoint before changing runtime. Then follow
the ExecPlan milestone order. Update this tracker and the active plan together.
