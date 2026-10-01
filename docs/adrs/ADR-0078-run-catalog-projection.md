# ADR-0078: Portable projects with a PostgreSQL runs catalog

Status: accepted for implementation by operator execution request;
independent contract reviews passed. Operating limits still require measured
host acceptance, not an assumption of capacity.
Date: 2026-09-30; predeployment implementation validated 2026-10-01 UTC.
Forest deployment remains on hold.

## Context and decision

Measurement clarification (implementation review): the unchanged 50 ms added-p95
target uses the producer's actual previous behavior. NoDb retains its timestamp
SQL commit; TTL/READONLY do not have that baseline. Counterbalanced complete
mutations, observer samples and legacy-helper characterization distinguish
incremental work from phase-dependent storage latency. No durability setting
or operating limit changes.

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
- Participants in the original decision: requesting operator and Codex.
  Independent contract reviewers on 2026-09-30: Dirac (correctness) and Ohm
  (security/operations); findings and post-fix verdicts are retained in the
  [disposition record](../work-packages/20260930_run_catalog_projection/artifacts/2026-09-30_contract_review_disposition.md).
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
| Production healthy observation | >=48 hours and a full reconciliation cycle; fixed nonproduction waits waived | Exercise sustained production workload and offline repair; idle single-operator hosts cannot establish representative traffic |
| Post-wepp1 retirement observation | 7 further healthy days | Preserve explicit read rollback while collecting production evidence |

Targets also include p95 <=1 second/p99 <=2.5 seconds for catalog/map requests
on the 805-run scope, and healthy added notification p95 <=50 ms. These are
release acceptance targets, not a claim the initial settings meet them. Forest
capacity testing must validate or revise the values before promotion, retaining
the measured workload, queue impact, NFS cost, and recovery time. Source outages
are visible exceptions to healthy-infrastructure guarantees, not hidden success.

Operator amendment, 2026-10-01 UTC: forest and forest1 each have one human
operator. Proceed to forest1 without a fixed 48-hour nonproduction wait; retain
controlled correctness and worker/database/browser checks and mark unobserved
elapsed recovery as unmeasured. Representative scale belongs on the first host
with that dataset, before wepp1 cutover if unavailable earlier. This changes
rollout evidence requirements, not reconciliation intervals or freshness limits.

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

## Contract review refinements

Readiness depends on available Ron/READONLY metadata, not job completion or
delivery of a finalizer notification. This preserves the existing reader's
ability to list a partially initialized project and allows reconciliation to
recover lost final events without a new durable lifecycle marker. Optional TTL
failure clears the stored expiration, retains its observation time, and does
not hide otherwise usable initial metadata. The expiration CHECK is null-safe.

Source resolution has a pure, descriptor-bound containment seam; grouped input
repair is not part of catalog reads. Every eligible batch consumer must support
the sweep before activation, even if older writers could otherwise be tolerated
through reconciliation. Public RQ details for this multi-user maintenance job
have a narrowly scoped redaction rule. Startup checks static configuration;
live source/DB/sweep readiness gates promotion rather than process construction.
These refinements close design contradictions without changing file authority,
adding infrastructure, widening runtime permissions, or claiming runtime proof.

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
