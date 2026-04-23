# MOFE `.mofe.man` Synthesis Process-Pool Migration

**Status**: Closed (2026-04-23)
**Timezone**: UTC

## Overview
`Landuse._build_multiple_ofe()` currently synthesizes `landuse/hill_<topaz_id>.mofe.man` files in a fully sequential loop. On disturbed multi-OFE workloads this path is now a dominant runtime slice, especially after MOFE map assignment and pair-count aggregation were accelerated. This package migrates `.mofe.man` synthesis to the canonical NoDb `createProcessPoolExecutor` pattern while preserving current output contracts and explicit failure behavior.

## Objectives
- Refactor `.mofe.man` synthesis in `wepppy/nodb/core/landuse.py` to use canonical `createProcessPoolExecutor` orchestration.
- Preserve behavioral parity for management file content, segment ordering, disturbed overrides, RAP canopy overrides, and output paths.
- Enforce explicit failure contracts (no silent error swallowing, no silent mismatch fallback).
- Add targeted regression tests for spawn/fork retry, bounded sequential fallback on `BrokenProcessPool`, and non-pool exception propagation.
- Produce benchmark/parity artifacts on local representative runs with per-run timings, mean/stddev, and percent delta.
- Close with mandatory code review, QA review, and security review artifacts.

## Scope
This package is limited to MOFE management synthesis concurrency in WEPPpy NoDb landuse build flows.

### Included
- Process-pool migration for `.mofe.man` synthesis under `Landuse._build_multiple_ofe()`.
- Canonical spawn-first -> fork retry -> sequential fallback semantics via `createProcessPoolExecutor`.
- Targeted tests for behavior parity and failure contracts.
- Benchmark/parity scripts and artifacts under this package.
- Code review, QA review, and security review artifacts with finding disposition.
- Package lifecycle documentation updates (`tracker.md`, ExecPlan sections, `PROJECT_TRACKER.md`).

### Explicitly Out of Scope
- Additional wepppyo3/Rust changes unrelated to `.mofe.man` synthesis.
- MOFE map labeling logic (already migrated).
- Landuse area pair-count logic (already migrated).
- Any migration into `wepp_interchange`; this package is WEPPpy NoDb-landuse scoped.

## Stakeholders
- **Primary**: WEPPpy NoDb landuse maintainers and disturbed-model operators.
- **Reviewers**: NoDb core maintainers, disturbed module maintainers, test maintainers.
- **Security Reviewer**: Required (queue/subprocess + run-tree write path changes).
- **Informed**: Runtime performance triage contributors.

## Success Criteria
- [x] `.mofe.man` synthesis path uses canonical `createProcessPoolExecutor` orchestration in production code.
- [x] Spawn-first, fork-retry, and bounded sequential fallback behaviors are explicitly covered by tests.
- [x] Non-`BrokenProcessPool` worker/setup failures remain explicit raised errors.
- [x] Generated `.mofe.man` outputs are parity-matched against baseline behavior on benchmark targets.
- [x] Benchmark artifacts include per-run timings, aggregate mean/stddev, and percent delta.
- [x] Code review, QA review, and security review artifacts exist with no unresolved medium/high findings.

## Dependencies

### Prerequisites
- [20260423_mofe_map_wepppyo3](../20260423_mofe_map_wepppyo3/package.md) (MOFE map assignment baseline).
- [20260423_mofe_landuse_pair_counts_wepppyo3](../20260423_mofe_landuse_pair_counts_wepppyo3/package.md) (landuse area-count baseline).
- Existing process-pool contract helper: `wepppy/nodb/base.py::createProcessPoolExecutor`.

### Blocks
- Follow-on multi-OFE optimization lanes that depend on reduced `.mofe.man` synthesis time.

## Related Packages
- **Depends on**: [20260423_mofe_map_wepppyo3](../20260423_mofe_map_wepppyo3/package.md)
- **Depends on**: [20260423_mofe_landuse_pair_counts_wepppyo3](../20260423_mofe_landuse_pair_counts_wepppyo3/package.md)
- **Related**: [20260422_segmented_multiple_ofe_wepppyo3_pool](../20260422_segmented_multiple_ofe_wepppyo3_pool/package.md)
- **Follow-up**: additional multi-OFE build-flow optimization packages after synthesis concurrency is stabilized.

## Timeline Estimate
- **Expected duration**: 2-4 focused sessions.
- **Complexity**: Medium-High.
- **Risk level**: Medium-High (concurrency + file-output parity contracts).

## Security Impact and Review Gate
- **Security impact triage**: `high`
- **Dedicated security review required**: `yes`
- **Triage rationale**: Introduces/refactors subprocess concurrency and concurrent run-tree file writes, which are explicitly high-impact surfaces under package policy.
- **Security review artifact**: `docs/work-packages/20260423_mofe_man_synthesis_process_pool/artifacts/2026-04-23_security_review.md`

## Benchmark Dataset Targets
Benchmark/parity anchors for this package:
- `https://wc.bearhive.duckdns.org/weppcloud/runs/moth-eaten-blackhead/disturbed9002-wbt-mofe/`
- `https://wc.bearhive.duckdns.org/weppcloud/runs/objectionable-sublimate/disturbed9002_wbt/`
- `https://wc.bearhive.duckdns.org/weppcloud/runs/cochlear-beriberi/disturbed9002-mofe/`
- `https://wc.bearhive.duckdns.org/weppcloud/runs/ordained-incentive/disturbed9002-wbt-mofe/`
- `https://wc.bearhive.duckdns.org/weppcloud/runs/uninsured-deformation/disturbed9002-wbt-mofe/`

Expected local roots:
- `/wc1/runs/mo/moth-eaten-blackhead`
- `/wc1/runs/ob/objectionable-sublimate`
- `/wc1/runs/co/cochlear-beriberi`
- `/wc1/runs/or/ordained-incentive`
- `/wc1/runs/un/uninsured-deformation`

## References
- `wepppy/nodb/core/landuse.py` - `_build_multiple_ofe`, `.mofe.man` synthesis path.
- `wepppy/nodb/base.py` - canonical `createProcessPoolExecutor` helper contract.
- `wepppy/nodb/core/watershed_mixins.py` - canonical MOFE pool orchestration pattern.
- `wepppy/nodb/core/wepp.py` - canonical multi-OFE prep pool orchestration pattern.
- `wepppy/nodb/mods/disturbed/disturbed.py` - canonical disturbed MOFE pool retry/fallback pattern.
- `tests/nodb/test_landuse_mofe_disturbed_scalar_lookup.py` - existing `_build_multiple_ofe` regression coverage.

## Deliverables
- Updated WEPPpy implementation for concurrent `.mofe.man` synthesis.
- Added/updated targeted tests for parity and failure contracts.
- Benchmark/parity raw + summary artifacts.
- Review artifacts:
  - `artifacts/2026-04-23_code_review.md`
  - `artifacts/2026-04-23_qa_review.md`
  - `artifacts/2026-04-23_security_review.md`
- Updated lifecycle docs and archived ExecPlan on completion.

## Follow-up Work
- Broader offload of per-hillslope segment-plan construction if runtime reduction remains required; this package parallelized the final `.mofe.man` synthesis/write phase only.
- Revisit MOFE synthesis pool economics if workload shape or start-method policy changes; the required benchmark matrix on this host remained slower under the spawn-first process-pool contract.

## Closure Notes

- **Closed**: 2026-04-23
- **Summary**: Implemented canonical spawn-first `createProcessPoolExecutor` orchestration for `.mofe.man` synthesis in `wepppy/nodb/core/landuse.py::_build_multiple_ofe()` with `BrokenProcessPool` fork retry, bounded sequential fallback, deterministic `hill_<topaz_id>.mofe.man` outputs, explicit non-pool error propagation, and bounded batched worker fan-out (`max_workers <= 4`). Added targeted regression coverage for success, spawn-failure retry, double-pool-failure sequential fallback, non-pool exception propagation, and deterministic parity fixtures. Captured required benchmark/parity artifacts on isolated temp copies of the five benchmark runs; parity matched on all runs and review artifacts closed with no unresolved medium/high findings.
- **Validation highlights**:
  - `env REDIS_HOST=localhost REDIS_PASSWORD_FILE=/workdir/wepppy/docker/secrets/redis_password .venv/bin/pytest tests/nodb/test_landuse_mofe_process_pool.py tests/nodb/test_landuse_mofe_disturbed_scalar_lookup.py tests/nodb/test_landuse_coverage_area_source.py --maxfail=1 -q` -> `10 passed`.
  - Benchmark/parity artifacts regenerated at `2026-04-23T18:30:33+00:00` under `artifacts/`.
  - Broad-exception enforcement remained clean for changed `landuse.py`, while repo-wide changed-file enforcement was blocked by unrelated dirty worktree edits in `wepppy/rq/project_rq.py`.
- **Lessons Learned**: On the required five-run matrix, spawn-first process-pool execution remained slower than forced sequential baseline (`+34.05%` to `+443.51%`), even after bounding workers and batching hillslope tasks. The package therefore closes on contract migration, parity preservation, and explicit evidence capture rather than a measured speedup claim.
- **Archive Status**: Active ExecPlan archived to `prompts/completed/mofe_man_synthesis_process_pool_execplan.md` with companion outcome note.
