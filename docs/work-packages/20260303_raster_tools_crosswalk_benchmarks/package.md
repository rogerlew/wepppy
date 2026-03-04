# Raster Tools Cross-Walk and Benchmark Evaluation

**Status**: Draft Complete (`defer` recommendation) (2026-03-04)

## Overview
Non-technical stakeholders asked for an evaluation of incorporating `https://github.com/UM-RMRS/raster_tools`. This package treats that as a two-stage decision workflow: first produce a capability cross-walk against what WEPPpy already uses (`GDAL`, `/workdir/weppcloud-wbt`, `/workdir/peridot`, `/workdir/wepppyo3`, `/workdir/oxidized-rasterstats`), then run focused benchmarks only on meaningful overlap.

The goal is to produce an evidence-backed recommendation (adopt, selectively adopt, or defer) instead of a tool-list comparison.

## Objectives
- Build an explicit capability matrix for raster/geospatial operations across `raster_tools` and the current WEPPpy stack.
- Map current WEPPpy geospatial workloads to the concrete libraries/tools that execute them today.
- Identify true overlap, unique capabilities, and integration gaps.
- Design and run reproducible performance benchmarks for the overlapping operations.
- Deliver a decision memo with technical and operational tradeoffs for stakeholders.

## Scope

### Included
- Repository-level inventory of capabilities in:
  - `/workdir/raster_tools`
  - `/workdir/weppcloud-wbt`
  - `/workdir/peridot`
  - `/workdir/wepppyo3`
  - `/workdir/oxidized-rasterstats`
  - WEPPpy usage surfaces invoking `gdal`/raster workflows
- Cross-walk artifacts linking current WEPPpy workflows to candidate tooling.
- Benchmark plan and benchmark harness for selected overlapping operations.
- Benchmark execution and summarized findings with reproducible command logs.
- Work-package documentation and recommendation artifacts.

### Explicitly Out of Scope
- Immediate production integration of `raster_tools` into WEPPpy.
- Large refactors to replace current geospatial dependencies during this package.
- Infrastructure redesign unrelated to geospatial tool evaluation.

## Stakeholders
- **Primary**: Roger and WEPPpy maintainers
- **Reviewers**: Maintainers for WEPPpy, `wepppyo3`, and supporting geospatial tooling repos
- **Informed**: Non-technical stakeholders requesting incorporation assessment

## Success Criteria
- [x] Capability cross-walk matrix is published and traceable to source files/commands.
- [x] Current WEPPpy geospatial workflow inventory is published with tool ownership mapping.
- [x] Benchmark shortlist is justified from overlap analysis (not arbitrary tool tasks).
- [x] Benchmark harness and execution commands are reproducible on the same host.
- [x] Benchmark results include runtime metrics and output-parity checks with explicit non-comparable handling (executed subset BW-01/BW-02; deferred cases documented).
- [x] Final recommendation memo provides a clear go/no-go or selective-adoption path with risks.

## Dependencies

### Prerequisites
- Local repository checkouts available under `/workdir/` (confirmed).
- Working Python/Rust/geospatial runtime sufficient to execute each candidate tool path.
- Representative raster datasets available for meaningful comparison.

### Blocks
- Any decision to add `raster_tools` as an approved dependency in WEPPpy.
- Any roadmap commitment to replace existing raster tooling without cross-walk evidence.

## Related Packages
- **Related**: [20260124_sbs_map_refactor](../20260124_sbs_map_refactor/package.md)
- **Related**: [20260208_rq_engine_agent_usability](../20260208_rq_engine_agent_usability/package.md)
- **Follow-up**: Potential implementation package if selective `raster_tools` adoption is approved.

## Timeline Estimate
- **Expected duration**: 1-2 weeks
- **Complexity**: Medium
- **Risk level**: Medium (decision-quality risk if workflows or benchmarks are not representative)

## References
- `wepppy/nodb/mods/` - Core raster-heavy modules and call-sites.
- `tools/benchmarks/` - Existing benchmark harness patterns in-repo.
- `/workdir/raster_tools` - Candidate repository under evaluation.
- `/workdir/weppcloud-wbt` - Existing WBT tooling surface.
- `/workdir/peridot` - Existing geospatial helper/tooling surface.
- `/workdir/wepppyo3` - Rust acceleration and raster helpers.
- `/workdir/oxidized-rasterstats` - Existing stats-oriented raster tooling.

## Deliverables
- `artifacts/capability_inventory.md`
- `artifacts/wepppy_geospatial_usage_map.md`
- `artifacts/capability_crosswalk_matrix.md`
- `artifacts/benchmark_plan.md`
- `artifacts/benchmark_results.md`
- `artifacts/adoption_recommendation.md`
- `artifacts/claims_vs_code_reality.md`

## Follow-up Work
- Follow-up benchmark completion package for deferred cases (`BW-03`, `BW-04`, `BW-05`) in a normalized single runtime environment.
- Candidate stderr investigation package for `sys.excepthook` noise observed during successful `raster_tools` runs.
- Implementation package for prioritized adoption path only if recommendation is revisited after follow-up evidence.
