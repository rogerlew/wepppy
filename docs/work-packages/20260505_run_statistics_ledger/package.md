# Run Statistics Ledger

**Status**: Open (2026-05-05)  
**Timezone**: UTC

## Overview

This package replaces the current WEPPcloud usage-statistics summaries with a durable run-statistics ledger. The immediate need came from the `/interfaces/` statistics text on wepp1, where the reported counts were derived from active run directories, a hard-coded post-2024 cutoff, hillslope file counts, and WATAR artifact globs rather than completed execution events.

The goal is to make project counts by configuration, WEPP hillslope run counts, and WATAR ash run counts defensible after TTL deletion and after repeated runs inside the same project.

## Objectives

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
- **Security Reviewer**: Optional unless scope expands into public route behavior or additional data exposure.
- **Informed**: Users who consume `/stats`, landing-map data, or historical usage summaries.

## Success Criteria

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

- **Security impact triage**: `low`
- **Dedicated security review required**: `no`
- **Triage rationale**: The base package writes internal aggregate statistics and runtime events. The ledger must avoid email, IP address, owner id, or other personally identifying fields. A dedicated security artifact becomes required if implementation changes public route access, exposes raw ledger events, changes auth/session behavior, or adds new external egress.
- **Security review artifact**: `N/A`

## Hardening and Callus Softening

- **Failure signature(s)**: Interface text reported `2469 projects and 1,043,759 hillslopes (0 WATAR hillslopes) ran since January 1, 2024` on wepp1. Investigation showed the date was a hard-coded exclusive cutoff, hillslopes were current `.slp` file counts, and WATAR was a legacy artifact glob rather than a runtime count.
- **Related prior hardening efforts**: None.
- **Health signals**: Project totals by config match active non-deleted projects; repeated hillslope/WATAR runs increase execution totals; deleted projects disappear from active counts but historical events remain.
- **Danger signals**: Runtime hooks slow model execution, the database writer path adds queue instability, ledger rows contain PII, backfill fabricates repeated-run counts, or compatibility outputs silently change meaning without docs.
- **Observation window**: 14 days after production rollout.
- **Temporary calluses introduced**: Keep legacy `runs_counter.json` keys during migration.
- **Callus softening hypothesis**: After consumers move to the richer rollup, legacy counter keys and any stale UI copy can be removed under a separate cleanup package.

## References

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
