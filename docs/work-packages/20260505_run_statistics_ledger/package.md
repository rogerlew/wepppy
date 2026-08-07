# Run Statistics Ledger

**Status**: Open (2026-05-05)  
**Timezone**: UTC

## Overview

This package replaces the current WEPPcloud usage-statistics summaries with a durable run-statistics ledger. The immediate need came from the `/interfaces/` statistics text on wepp1, where the reported counts were derived from active run directories, a hard-coded post-2024 cutoff, hillslope file counts, and WATAR artifact globs rather than completed execution events.

The goal is to make project counts by configuration, WEPP hillslope run counts, and WATAR ash run counts defensible after TTL deletion and after repeated runs inside the same project.

## Objectives

- Restore `compile_dot_logs_rq` operationally by replacing per-run legacy file
  enumeration with canonical Parquet footer counts.

- Define a durable PostgreSQL-backed statistics event ledger so completed execution counts survive 90-day rolling TTL deletion.
- Count repeated WEPP hillslope runs and repeated WATAR ash runs as execution events, not as current output-file counts.
- Keep active project counts by configuration tied to active, non-deleted projects while preserving historical execution totals.
- Backfill the best available historical metadata from dot access logs and legacy artifacts without inventing unknown execution counts.
- Preserve existing public stats artifacts and routes during migration until consumers are explicitly moved.

## Scope

### Included

- A normative statistics contract in [spec.md](spec.md).
- A PostgreSQL event ledger schema and writer path for run-statistics events.
- Runtime event hooks for completed WEPP hillslope runs, completed WATAR ash runs, and project deletion.
- Idempotent backfill from dot access logs and existing legacy artifacts.
- Derived rollup outputs for project counts by config and execution counts.
- Endpoint inventory for `wepppy/weppcloud/routes/stats.py`, with migration limited to `/stats`, `/stats/<key>`, `/access-by-year`, and `/access-by-month` consuming PostgreSQL-backed rollups.
- Regression coverage for repeated runs, TTL deletion, dot-file backfill, and WATAR artifact matching.

### Explicitly Out of Scope

- Re-enabling interface-page statistics before the new rollups are implemented and validated.
- Reconstructing exact repeated-run history from periods before a runtime ledger existed; those counts must remain marked as unknown or artifact-inferred.
- Changing run-scoped WEPP, WATAR, CSV, or parquet output schemas.
- Adding new external dependencies unless the dependency-evaluation standard is completed first.
- Redis as the source-of-truth event ledger (Redis may be added later as a cache or precomputed-summary layer).

## Stakeholders

- **Primary**: WEPPcloud operators and maintainers who report usage and capacity metrics.
- **Reviewers**: WEPPcloud route/RQ maintainers, NoDb/WEPP runtime maintainers, and WATAR ash maintainers.
- **Security Reviewer**: Required for SURF-19A because generated values feed public routes and the landing map.
- **Informed**: Users who consume `/stats`, landing-map data, or historical usage summaries.

## Success Criteria

- [ ] `compile_dot_logs` performs no per-run `.slp`, ash CSV, or raw ash-output
  enumeration and obtains current inventory from canonical Parquet footers.

- [ ] `compile_dot_logs` or its successor produces active project counts by config from active projects only.
- [ ] Completed WEPP hillslope runs are appended once per successful `WeppRunService.run_hillslopes()` invocation and repeated runs are summed.
- [ ] Completed WATAR ash runs are appended once per successful `Ash.run_ash()` invocation and count runnable ash hillslopes, not `*ash.csv` files.
- [ ] TTL deletion removes projects from active project counts without decrementing historical execution totals.
- [ ] Backfill creates deterministic, idempotent events from dot files and legacy artifacts, with unknown pre-ledger repeated runs explicitly labeled.
- [ ] Existing `/stats` compatibility keys remain available until a separate consumer migration removes them.
- [ ] Targeted regression tests cover the exact failures that prompted this package.

## Dependencies

### Prerequisites

- Existing dot access logs under `/wc1/runs/*/.<runid>` and `/geodata/weppcloud_runs/.<runid>`.
- Existing maintenance job `compile_dot_logs_rq` in `wepppy/rq/project_rq_delete.py`.
- Existing WEPP hillslope runtime path in `wepppy/nodb/core/wepp_run_service.py`.
- Existing WATAR ash runtime path in `wepppy/nodb/mods/ash_transport/ash.py`.

### Blocks

- Any future public UI claim about total WEPPcloud project, hillslope, or WATAR usage counts.
- Cleanup or replacement of legacy `runs_counter.json` semantics.

## Related Packages

- **Related**: [WEPPcloud app/routes/controllers subsystem](../../../wepppy/weppcloud/AGENTS.md)
- **Related**: [NoDb controller contracts](../../../wepppy/nodb/AGENTS.md)

## Timeline Estimate

- **Expected duration**: 2-4 focused sessions.
- **Complexity**: Medium-High.
- **Risk level**: Medium. The implementation is additive, but it crosses runtime, maintenance, and stats-output paths.

## Security Impact and Review Gate

- **Security impact triage**: `high` for bounded SURF-19A; future ledger milestones re-triage separately.
- **Dedicated security review required**: `yes`
- **Triage rationale**: SURF-19A changes values consumed by public statistics routes and the landing map while preserving route shapes, auth, and exposure.
- **Security review artifact**: `artifacts/2026-08-07_checkpoint_ops_security_review.md`

## Hardening and Callus Softening

- **Failure signature(s)**: wepp1 job `7aa39c98-de7c-4298-8d5f-35e3784775e4` raised `JobTimeoutException: Task exceeded maximum timeout value (36000 seconds)` while enumerating `wepp/runs/*.slp`, after running from 02:10:26 through 12:10:26 UTC on 2026-08-07.
- **Scope boundary**: Replace the two per-run count globs and contain invalid global publication without refactoring dot-log discovery, TTL, Ron, Watershed, routes, or the future ledger.
- **Hypothesis**: Footer-only counts eliminate unbounded per-hillslope NAS metadata work and complete within the existing timeout while preserving last-known-good outputs under systemic failure.
- **Related prior hardening efforts**: ADR-0039/DOM-14A uses measured production evidence and bounded recovery; SURF-19A removes the unbounded work rather than increasing its timeout.
- **Health signals**: zero legacy per-run count scans; representative compile completes; canonical read/warning counters are logged; expected projects remain in locations and project counts.
- **Danger signals**: repeat timeout, systemic guard trip, implausible count collapse, widespread warnings, partial publication, or location/project loss caused only by missing counts.
- **Observation window**: 14 days after production rollout.
- **Temporary calluses introduced**: systemic publication guard and stable legacy keys during migration.
- **Publication support**: a nonblocking output-directory file lock prevents
  overlapping compilers; generation-unique candidates and backups restore the
  complete prior set on promotion failure. A durable journal supports
  next-invocation recovery after interruption, and failure cleanup removes
  unpublished access-data candidates.
- **Sunset owner and due date**: Roger Lew / WEPPcloud operator records a
  keep-reduce-remove decision 14 calendar days after SURF-19A activation.
- **Systemic-guard sunset criteria**: Keep the guard if it trips, any correlated
  canonical-read failure occurs, or output totals are not yet stable. Reduce or
  remove it only through a reviewed follow-up with 14 clean days, representative
  canary evidence, and equivalent last-good publication protection.
- **Legacy-key sunset criteria**: Keep keys until every direct file and `/stats`
  consumer is inventoried and migrated. Remove only in a separately approved
  consumer-migration package with route/output regressions.
- **Callus softening hypothesis**: After consumers move to the richer rollup,
  legacy counter keys and stale UI copy can be removed; the systemic guard may
  be simplified only if the ledger publication path provides equivalent
  fail-closed behavior.

## References

- [Canonical Parquet inventory decision](artifacts/2026-08-07_canonical_parquet_inventory_contract_decision.md) - Incident bridge and approved compatibility delta.
- [ADR-0040](../../adrs/ADR-0040-canonical-parquet-counts-for-run-inventory.md) - Count-source and missing-artifact decision.

- [spec.md](spec.md) - Normative statistics contract, data model, backfill plan, compatibility plan, and regression plan.
- [prompts/active/run_statistics_ledger_execplan.md](prompts/active/run_statistics_ledger_execplan.md) - Active implementation plan.
- `wepppy/weppcloud/_scripts/compile_dot_logs.py` - Current access-log compiler and legacy counter generator.
- `wepppy/nodb/core/wepp_run_service.py` - WEPP hillslope execution path.
- `wepppy/nodb/mods/ash_transport/ash.py` - WATAR ash execution path.
- `wepppy/rq/project_rq_delete.py` - TTL delete and maintenance-job paths.
- `wepppy/weppcloud/routes/stats.py` - Existing public stats routes.
- `wepppy/weppcloud/routes/__init__.py` - `stats_bp` registration and route export.

## Deliverables

- [ ] PostgreSQL ledger table, writer module, and writer tests.
- [ ] Runtime hooks for WEPP hillslope, WATAR ash, and TTL deletion events.
- [ ] Backfill command integrated with maintenance tooling.
- [ ] Endpoint migration for `wepppy/weppcloud/routes/stats.py` plus compatibility keys.
- [ ] Tests and validation notes recorded in this package tracker.

## Follow-up Work

- Re-enable or redesign public-facing statistics text only after the new rollup is production-validated.
- Retire legacy `runs_counter.json` compatibility keys after every consumer migrates.
