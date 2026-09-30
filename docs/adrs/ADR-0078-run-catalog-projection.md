# ADR-0078: Portable projects with a PostgreSQL runs catalog

Status: architecture endorsed; detailed operating limits proposed for contract review.
Date: 2026-09-30. Implementation and deployment pending.

## Context and decision

The [production profile](../investigations/2026-09-30-user-runs-performance.md)
measured 169.56 seconds to build an 805-run catalog, dominated by project
filesystem access. Keep files authoritative and standalone projects independent
of PostgreSQL. Add one rebuildable `run_catalog` table beside existing `run`
registration/access records. Replace NoDb's existing web-app timestamp coupling
with an explicitly installed, storage-neutral post-commit observer.

Use bounded SQL invalidation, serialized current-source refresh, and scheduled
reconciliation on existing infrastructure. Catalog reads use PostgreSQL only
after explicit cutover. No automatic NFS fallback. Roll out forest, forest1
test production, then wepp1; each stage has its own evidence and promotion gate.
The [specification](../schemas/run-catalog-projection-contract.md) owns exact
schema, protocols, user behavior, and release sequence.

## Decision provenance

- Venue: Codex conversation, September 30, 2026, America/Los_Angeles; artifact
  authoring recorded in UTC in the work-package tracker.
- Participants: requesting operator and Codex; no independent reviewers yet.
- Decision owner: requesting operator for portable-project requirement,
  architecture endorsement, and forest → forest1 → wepp1 sequence.
- Specification author: Codex. Runtime implementer: not yet assigned.
- Operator instruction: author the full specification with implementation and
  rollout sequence. This is not evidence of deployment execution or acceptance
  of unreviewed numerical limits below.

## Operational parameters proposed for review

There are no changes to scientific formulas, TTL duration, or GC rules.
New synchronization and presentation parameters are recorded explicitly rather
than becoming undocumented implementation defaults.

| Parameter | Initial value | Rationale |
| --- | --- | --- |
| Sweep dispatch cadence | 15 seconds | Headroom for 60-second notified-update objective |
| Dispatch row limit | 50 attempts | Bound I/O and scheduler occupancy |
| Source-reader concurrency | 2 per deployment | Begin conservatively under measured NFS latency |
| New-work submission window | 45 seconds | Yield queue capacity between bounded sweeps |
| Reconciliation reservation | At least 25% of attempts when due | Prevent writes starving offline-change discovery |
| Transient retry delay | 60 seconds | Avoid immediate repeated I/O on unavailable sources |
| Full reconciliation due interval | 12 hours | Headroom for <=24-hour revisit/recovery target |
| Stale observation threshold | 24 hours | Align visible warning/TTL suppression with repair objective |
| Adapter connection / pool wait | 1 second / 250 ms | Bound save-path connection pressure |
| Adapter SQL lock / statement timeouts | 250 ms / 1 second | Avoid mirror work monopolizing a file-save lock |
| Adapter inline retries | 0 | Committed files remain authoritative; reconciliation repairs misses |
| Per-stage healthy observation | >=48 hours and a full reconciliation cycle | Exercise sustained workload and offline repair before promotion |
| Post-wepp1 retirement observation | 7 further healthy days | Preserve explicit read rollback while collecting production evidence |

Targets also include p95 <=1 second/p99 <=2.5 seconds for catalog/map requests
on the 805-run scope, and healthy added notification p95 <=50 ms. These are
release acceptance targets, not a claim the initial settings meet them. Forest
capacity testing must validate or revise the values before promotion, retaining
the measured workload, queue impact, NFS cost, and recovery time. Source outages
are visible exceptions to healthy-infrastructure guarantees, not hidden success.

## Alternatives and consequences

Adding fields directly to `run` is feasible but mixes disposable projections
with registration/ACL identity. PostgreSQL as the project authority would break
standalone portability. SQL in property setters misses actual commit/failure
boundaries and non-NoDb sources. Synchronous refresh on every save repeats NFS
cost under writer locks. Callback-only synchronization loses crash/offline edits.
An outbox, watcher, or new service is deferred unless measured bounded repair
misses the acceptance condition; the crash gap is explicitly acknowledged.

The chosen design is eventually consistent, can briefly omit new unindexed
projects, and can display labeled last-good metadata after transient failures.
Known-dirty/old TTL observations are suppressed. These are explicit contract
deltas, not incidental fallbacks; correctness/security review must examine them.
Missing/invalid Ron retains current omission behavior. Readonly and deletion
authority remain in their existing mutation paths.

## Risk, validation, and rollback

Risks include missed producers, NFS queue pressure during backfill, metadata
lag, stale TTL display after a lost signal, deserialization incompatibility,
registration races, and wrong-database companion workers. The specification
requires real file/SQL/process/browser evidence and host/database identity checks.

Switch reads explicitly to legacy mode for rollback, retaining schema and
healthy writers. Stop overloaded sweeps without erasing dirty state. Use the
canonical deploy path for application rollback; never replay SQL into projects
or drop tables to recover. Any adjustment to these workflow defaults updates
this ADR and the specification before promotion.
