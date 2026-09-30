# Writer attribution and pre-fix reproduction

Environment: forest; starting revision `bbace6023575d29ca00a26f1ad2a7776e957fc8a`.
Classification: conformance repair under unchanged NoDb Persistence and
Concurrency Contract, “Long-running collect-then-finalize pattern.”
No parameterization, schema, queue edge, or result-contract change is intended.

## Reproduction

Command: `wctl run-pytest tests/nodb/test_batch_climate_rap_contention.py -k daymet_multiple_same_size -vv --tb=short`.
Before implementation: **2 failed** with actual `NoDbStaleWriteError` from the
normal serializer. The real observed/Multiple mode router reaches both stages.
The injected atomic rewrite changes `_test_unrelated` from `BASE` to `KEEP`,
preserving payload size and advancing mtime exactly one second.

- Daymet: expected `(mtime=1790795551.579526, size=750)`, observed
  `(mtime=1790795552.579526, size=750)`; stack ends at
  `Climate._build_climate_observed_daymet` → `locked` → `dump`.
- PRISM: expected `(mtime=1790795552.4665437, size=774)`, observed
  `(mtime=1790795553.4665437, size=774)`; stack ends at
  `run_prism_revision` → `locked` → `dump`.

The known competing writer in these tests is `_same_size_rewrite`, running in
the collector (Daymet) or worker thread (PRISM). This establishes a deficient
mutation boundary; it does **not** identify the Kubernetes incident writer.

## Pre-fix source inventory

- Initial batch copy rewrites copied NoDb `wd` through ordinary file writes,
  before build. Workspace reset/copy is outside the climate directory lock.
- `_clear_batch_leaf_nodb_state` clears cache and controller locks on startup.
  Duplicate startup can interfere with an active controller writer.
- `resync_base_project_attributes` reads and directly truncates/rewrites the
  leaf NoDb document without either controller or directory-root locking.
  It is an explicit bypass capable of rewriting during a competing build.
- `_build_climate_at_mutation_boundary` clears only the climate cache and
  obtains a current controller inside the climate directory-root lock.
- Daymet's old builder retains a loaded mutation base through acquisition,
  CLIGEN generation, monthly calculation and its lock-exit dump.
- Observed/ObservedPRISM PRISM revision takes the legacy long lock. Only
  GridMetPRISM previously entered `run_prism_revision_build`.
- Numerical helpers, station lookup, Daymet acquisition and PRISM worker
  functions publish files; they do not independently dump `climate.nodb`.
- Climate router input/station resolution, scaling and quality-warning updates
  have their existing controller writes. Completion timestamps use RedisPrep;
  catalog update does not replace the climate controller.

## Lock identity and remaining evidence

Batch builds use scope `effective_root_path`. The scope token is the normalized
resolved `<wd>/climate` path; the lock key uses its SHA-1 prefix. Equal resolved
paths yield the same key; different mount path spellings can yield different
keys even for the same underlying NFS directory. Source inspection cannot prove
that all cluster workers resolve to the same path or share Redis configuration.

Directory-root ownership excludes a second cooperating build callback, but does
not cover the startup and resynchronization writers listed above. Thus an
exclusive build callback is not proof of exclusive leaf mutation.

No cluster inspection has run: forest has no `kubectl` executable, and the
approved cluster access host/command has been requested. Exact incident writer,
duplicate-job attribution and cross-node lock identity remain open acceptance
gates. Do not claim them proved from injected local rewrites.

## Implemented correction and compatibility

The correction reuses `_derived_build.finalize` and `publish_files`, fresh
hydration, relevant-input rejection, and allowlisted derived outputs. Batch
lexical/effective directory-root ownership now starts before reset, copy, cache
cleanup and resynchronization; startup preserves live Climate controller tokens.
Climate resynchronization rehydrates under the controller lock and atomically
commits only base attributes. No incident writer is inferred from these fixes.

Full Daymet builds defer obsolete-file replacement until their successful stage
commit; direct builder calls preserve sidecars/subclimate fields. Observed PRISM
enters the existing bounded finalizer and consumes fresh Daymet. Each stage
commits once. PRISM failure retains committed Daymet but leaves Multiple climate
incomplete and blocked from downstream preparation/completion. Numerical calls,
scientific parameters, queue edges and stale-write rejection are unchanged.
