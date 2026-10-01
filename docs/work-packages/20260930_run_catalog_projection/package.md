# PostgreSQL run catalog projection

**Status**: Open — predeployment implementation complete; holding before forest deployment (2026-10-01 UTC)
**Timezone**: UTC

## Purpose and authority

Eliminate project filesystem work from authenticated run-list/map requests
while retaining standalone WEPPpy and project-file authority. Production
profiling found a 169.56-second catalog build for 805 registrations.

The durable requirements live in the
[catalog specification](../../schemas/run-catalog-projection-contract.md).
This package organizes execution, not a competing schema. Follow the
[active ExecPlan](prompts/active/run_catalog_projection_execplan.md) and
[tracker](tracker.md). Architecture and forest → forest1 → wepp1 order were
endorsed by the operator; independent technical reviews passed. Detailed operator
ratification and accepted checkpoints now precede runtime implementation.

## Scope and complexity budget

Include one additive `run_catalog` table, a portable notification interface,
deployment adapter, non-mutating extractor, bounded existing-queue sweeps,
operator CLI, three database-backed JSON read surfaces, freshness UI, and
staged rollout/rollback. Reuse PostgreSQL, existing dependencies, scheduler,
batch workers, Flask-Migrate, current authentication, and canonical deployment.

Exclude scientific state migration, ACL/TTL calculation changes, statistics
ledger work, new services/queues/brokers/outboxes/watchers, and additional host
deployments. A second progress table is unnecessary: use per-row SQL scheduling
timestamps. Test the simple bounded refresh before escalating; preserve real
capacity evidence and operational/recovery cost for any proposed expansion.

## Fidelity and generated artifact evidence

Target: faithful extraction, with only specified stale/freshness presentation
changes. Implemented is distinct from wired, environment-validated, and deployed.
The evidence chain is actual mutation intent → committed Ron/READONLY/TTL →
observer → SQL projection → authorized JSON → browser table/map. Read semantic
values at each stage; populated rows and RQ SUCCESS alone are insufficient.

Direct file and PostgreSQL boundaries are mandatory. Test representative
save/run/archive/restore behavior to prove portable project inputs/outputs remain
unchanged. Real forest, forest1, and wepp1 workflows under actual identities,
groups, mounts, umask, and orchestration are deployment gates. Current highest
claim: diagnosed; specification independently reviewed, no runtime implementation.

## Success criteria

- Database-only list/map requests perform zero project filesystem operations.
- Large-account latency and freshness/reconciliation gates in the spec pass.
- Standalone use imports no web/database dependencies through the new boundary.
- Every relevant producer and missed-notification recovery has direct evidence.
- No unauthorized metadata, unapproved ACL changes, lost saves, or source edits
  by projection reads; legacy values and known omissions are explained.
- All three stages pass in order, including full reconciliation, observation,
  canonical deployment checks, and rollback/re-enable.
- Contract reviews, implementation reviews, documentation, and legacy-reader
  retirement disposition are complete before package closeout.

## Security and correctness gates

Security impact: **high**, because authenticated metadata enumeration, source
path handling, worker database connections, and serialization boundaries change.
Dedicated [security review](artifacts/2026-09-30_security_review.md) and
[correctness review](artifacts/2026-09-30_correctness_review.md) are required.
Both independent contract reviews passed after findings disposition; see the
[closure record](artifacts/2026-09-30_contract_review_disposition.md). Runtime
review is tracked in the [implementation disposition](artifacts/2026-09-30_implementation_review.md);
deployment proof remains pending. Authoring is not self-approval.

Parameterization: no scientific changes. Workflow cadence, retry, stale-state
presentation and observation defaults are recorded in
[ADR-0078](../../adrs/ADR-0078-run-catalog-projection.md), with detailed numerical
choices authorized for implementation and still subject to host capacity validation.

## Incident lifecycle and delivery

Health signals: low request latency, no request NFS, complete reconciliation,
bounded update lag, source/SQL/UI parity, and stable model-job capacity.
Danger signals: stale-age growth, repeated projection failure, unexplained row
loss, missing writer initialization, or wrong-database notifications.

The temporary legacy-reader switch is owned by the package implementer/operator.
Sunset is separately reviewed after seven healthy days following wepp1 acceptance;
retaining it needs an explicit owner and date. Each stage requires at least
48 healthy hours plus a full reconciliation cycle. No deployment is performed
by this documentation task.

Stakeholders: operator, WEPPcloud users, standalone WEPPpy users, NoDb/worker
maintainers, independent correctness and security reviewers. No external
dependency or deployment permission is requested in this specification phase.
