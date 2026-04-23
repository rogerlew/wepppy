# Watershed Centroid Persistence Hardening for Climate Build Reliability

**Status**: Open (2026-04-22)
**Timezone**: UTC

## Overview
`build_climate_rq` can fail with `TypeError: cannot unpack non-iterable NoneType object` when `watershed.centroid` is unexpectedly `None` even though watershed abstraction artifacts (`watershed/hillslopes.parquet`, `watershed/channels.parquet`, `structure.json`) exist. This package hardens the run-state contract so centroid state is either repaired deterministically or surfaced as an explicit, typed failure.

The package targets the failure mode observed on `immodest-quick/disturbed9002`, where watershed jobs were marked finished but persisted `watershed.nodb` lacked centroid/summary fields.

## Objectives
- Eliminate `None` centroid unpack crashes in climate paths by replacing nullable reads with repair-or-typed-failure semantics.
- Add watershed centroid self-heal from existing abstraction artifacts when persisted `watershed.nodb` state is incomplete.
- Prevent stale NoDb overwrites from silently clobbering newer persisted watershed state.
- Add post-abstraction durability verification in RQ orchestration so incomplete state fails early and clearly.
- Add regression coverage for stale-write and centroid-self-heal scenarios.

## Scope
This package covers NoDb watershed state durability, centroid access contracts, climate-call-site hardening, and associated queue-path validation.

### Included
- Add `Watershed.require_centroid()` (or equivalent) that:
  - returns persisted centroid when available,
  - repairs centroid from abstraction artifacts when possible,
  - raises typed state error when repair is impossible.
- Update centroid consumers in climate and climate-station services to use repair-or-fail contract.
- Add optimistic stale-write guard in NoDb persistence boundary (`NoDbBase.dump` / equivalent write boundary) to prevent older instance overwrite.
- Add post-`abstract_watershed_rq` persistence verification (reload + centroid assertion), with one bounded repair attempt.
- Add/adjust tests for:
  - centroid missing + artifacts present (self-heal path),
  - centroid missing + artifacts absent (typed failure),
  - stale writer overwrite prevention.
- Update documentation for watershed/climate run-state contract behavior and failure handling.

### Explicitly Out of Scope
- Peridot geometry or delineation algorithm changes.
- Broad climate model behavior changes unrelated to centroid availability.
- Historical bulk backfill of old runs (separate operational package if needed).
- Auth/security feature development.

## Stakeholders
- **Primary**: WEPPcloud operators triaging failed climate builds.
- **Reviewers**: NoDb/RQ maintainers, climate/watershed maintainers.
- **Security Reviewer**: Not required for this package scope.
- **Informed**: WEPPcloud users affected by climate build reliability.

## Success Criteria
- [ ] Climate build paths no longer raise raw `TypeError` on nullable centroid unpack.
- [ ] When abstraction artifacts exist, missing centroid is repaired and persisted before climate coordinates are consumed.
- [ ] When artifacts are unavailable/corrupt, code raises explicit typed state error with run/context diagnostics.
- [ ] Stale NoDb state writes are rejected (and covered by regression tests).
- [ ] `abstract_watershed_rq` validates centroid durability after abstraction and fails loudly if state remains incomplete.
- [ ] Relevant unit/integration tests pass with new coverage for the observed failure mode.
- [ ] Work-package docs and root tracker reflect final behavior contract and validation evidence.

## Dependencies

### Prerequisites
- Existing watershed abstraction outputs (`watershed/hillslopes.parquet`, `watershed/channels.parquet`) remain canonical centroid derivation inputs.
- Existing `post_abstract_watershed()` behavior remains available to compute centroid and summary values.

### Blocks
- Follow-on operator automation for auto-requeue/recovery should wait until this package closes.

## Related Packages
- **Related**: [20260321_peridot_watershed_parquet_manifest](../20260321_peridot_watershed_parquet_manifest/package.md)
- **Related**: [20260411_rq_operator_experience_hardening](../20260411_rq_operator_experience_hardening/package.md)
- **Related**: [20260317_runtime_path_redis_locks](../20260317_runtime_path_redis_locks/package.md)
- **Follow-up**: Optional operational package for historical-run repair tooling.

## Timeline Estimate
- **Expected duration**: 2-5 focused sessions.
- **Complexity**: High.
- **Risk level**: Medium-High (run-state durability and queue orchestration behavior).

## Security Impact and Review Gate
- **Security impact triage**: `none`
- **Dedicated security review required**: `no`
- **Triage rationale**: The package changes persistence/durability and error contracts for internal run state; it does not introduce new auth/session/secrets/input attack surfaces.
- **Security review artifact**: `N/A`

## Compatibility and Regression Plan
This package is backward-compatible at the external API level. It hardens internal behavior and error semantics without removing user-visible keys/columns.

Compatibility strategy:
- Keep watershed/climate data contracts additive and non-destructive.
- Preserve existing successful run behavior when centroid is already persisted.
- Use typed errors for unrecoverable state to improve operator diagnostics.

Regression strategy:
- Add explicit tests for centroid self-heal and hard-fail branches.
- Add stale-write rejection coverage at NoDb persistence boundary.
- Validate post-abstraction state durability behavior in RQ path tests.
- Validate climate path behavior transitions from raw `TypeError` to contract-compliant failure/repair.

## References
- `/home/workdir/wepppy/wepppy/nodb/core/watershed.py` - watershed persistence and peridot post-abstraction state writes.
- `/home/workdir/wepppy/wepppy/nodb/core/watershed_mixins.py` - centroid accessor location and abstraction orchestration methods.
- `/home/workdir/wepppy/wepppy/topo/peridot/peridot_runner.py` - `post_abstract_watershed` centroid derivation.
- `/home/workdir/wepppy/wepppy/nodb/base.py` - NoDb hydration/dump boundaries.
- `/home/workdir/wepppy/wepppy/rq/project_rq.py` - `abstract_watershed_rq` and `build_climate_rq` orchestration.
- `/home/workdir/wepppy/wepppy/nodb/core/climate.py` - climate build centroid call sites.
- `/home/workdir/wepppy/wepppy/nodb/core/climate_station_catalog_service.py` - station-selection centroid call sites.
- `/home/workdir/wepppy/docs/schemas/rq-response-contract.md` - queue error contract guidance.
- `/home/workdir/wepppy/docs/prompt_templates/codex_exec_plans.md` - ExecPlan process standard.

## Deliverables
- New/updated watershed centroid contract API (repair-or-fail behavior).
- Climate and station-service call-site hardening to new centroid contract.
- NoDb stale-write guard and regression tests.
- RQ post-abstraction durability check and regression coverage.
- Updated package docs, tracker entries, and root project tracker registration.

## Follow-up Work
- Optional run-repair CLI/script for existing historical runs with partial watershed.nodb state.
- Optional operator policy for automatic one-time centroid repair before climate requeue.

## Closure Notes

**Closed**: YYYY-MM-DD

**Summary**: TBD

**Lessons Learned**: TBD

**Archive Status**: TBD
