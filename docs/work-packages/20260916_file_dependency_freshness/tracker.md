# File dependency freshness tracker

**Phase:** M1 execution. **Updated:** 2026-09-17 UTC.
**Security impact:** High; dedicated security and correctness reviews required
at execution checkpoints. M1 reviews retained; first-wave M2 contract reviews in progress.

## Completed

- [x] Record owner's scaffold request and incident evidence.
- [x] Initial seed scan across NoDb, reports, runtime paths, RQ and services.
- [x] Define content/metadata/identity distinctions and operation/state matrix.
- [x] Scaffold phased ExecPlan with explicit rebuild/restart/end-to-end gates.

## Ready for execution

- [x] M1 seed inventory reviews and deterministic hard-link/SBS/NoDb baseline probes.
- [ ] M1 remaining exhaustive consumer tracing and final dispositions.
- [ ] M2: canonical contracts, compatibility/performance decisions, reviews and checkpoint.
- [ ] M3: bounded post-fire fix, then confirmed consumer groups.
- [ ] M4: full applicable gates, security/correctness reviews and benchmarks.
- [ ] M5: rebuilt/restarted development stack, actual UI/RQ/WEPP and archive tests.
- [ ] M6: all dispositions, durable docs and implementation closeout.

## Decisions and risks

Owner authorized execution after the original scaffold. No implementation, model rerun, stack
restart or production deployment occurred. Broad discovery is required;
mechanical removal of ctime is rejected because race/integrity checks may need it.
A stat-keyed hash cache can still hide changes; audit the cache and consumer,
not just whether a hash appears in a manifest. Avoid repeated large-file hashing
on report polls. Old signatures without hashes need explicit compatible handling.

No temporary bypasses, new infrastructure or cache clears are planned. A future
execution request should proceed milestone by milestone with existing authority,
subject to the repository contract checkpoint and operational boundaries.

## Evidence and next action

[Seed inventory](artifacts/seed_inventory.md), [operation matrix](artifacts/operation_matrix.md),
[ExecPlan](prompts/active/file_dependency_freshness_execplan.md).
Next: finish M1 evidence and the reviewed M2 checkpoint. Scaffold validation consists
of scoped doc lint, spelling preview and authored diff checks, not runtime tests.

## Execution evidence

Baseline `adb4f9b004459fc578460a95f30ac01ae1421f36`; source search scope,
independent inventories and probes are under artifacts/. Ordinary post-fire
file content is the first reviewed implementation wave. NoDb hydration race,
report/raster caches, soil SQLite metadata and CLI/parquet readiness remain
explicit open findings. Do not mark the package complete after one wave.
