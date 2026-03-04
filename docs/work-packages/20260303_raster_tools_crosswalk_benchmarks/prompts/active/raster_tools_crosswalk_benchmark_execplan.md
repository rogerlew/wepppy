# Raster Tools Cross-Walk and Benchmark Evaluation ExecPlan

This ExecPlan is a living document. The sections `Progress`, `Surprises & Discoveries`, `Decision Log`, and `Outcomes & Retrospective` must be kept up to date as work proceeds.

This plan must be maintained in accordance with `docs/prompt_templates/codex_exec_plans.md`.

## Purpose / Big Picture

Stakeholders asked whether WEPPpy should incorporate `/workdir/raster_tools`. This plan turns that request into a concrete evaluation pipeline: first build a capability cross-walk between `raster_tools` and the current WEPPpy geospatial stack, then run reproducible benchmarks only for workflows that are truly comparable.

At completion, maintainers should be able to answer three questions with evidence: (1) where `raster_tools` overlaps current tooling, (2) where it adds unique value or creates gaps, and (3) whether measured performance and integration cost justify adoption.

## Progress

- [x] (2026-03-03 22:30Z) Created work-package scaffold at `docs/work-packages/20260303_raster_tools_crosswalk_benchmarks/`.
- [x] (2026-03-03 22:31Z) Authored package brief (`package.md`) and tracker (`tracker.md`).
- [x] (2026-03-03 22:35Z) Authored this active ExecPlan with phased cross-walk then benchmark execution steps.
- [x] (2026-03-03 22:36Z) Added package entry to `PROJECT_TRACKER.md` backlog.
- [x] (2026-03-03 22:41Z) Ran documentation lint for package docs and `PROJECT_TRACKER.md` with zero errors/warnings.
- [x] (2026-03-04 04:08Z) Milestone 1 complete: published `artifacts/capability_inventory.md` and `artifacts/wepppy_geospatial_usage_map.md` with source-grounded evidence and unknown/non-comparable notes.
- [x] (2026-03-04 04:10Z) Milestone 2 complete: published `artifacts/capability_crosswalk_matrix.md` and shortlist-gated `artifacts/benchmark_plan.md` from overlap rows (`direct|partial`) with `high|medium` priority.
- [x] (2026-03-04 04:22Z) Milestone 3 complete: expanded `artifacts/benchmark_plan.md` with harness implementation notes, environment setup, and per-case parity contracts; added runnable harness script at `notes/benchmark_harness_bw01_bw02.py`.
- [x] (2026-03-04 04:22Z) Milestone 4 draft complete: executed BW-01 and BW-02 benchmark cases, captured raw timings in `notes/raw/benchmark_runs_bw01_bw02.json`, and published `artifacts/benchmark_results.md` with parity outcomes and deferred-case disclosures.
- [x] (2026-03-04 04:22Z) Milestone 5 draft complete: published `artifacts/adoption_recommendation.md` with explicit `defer` recommendation and follow-up package proposal.
- [x] (2026-03-04 04:42Z) QA correction pass: tightened parity/comparability contracts in benchmark plan + harness (true p95, grid-equivalence preconditions), reran BW-01/BW-02, and updated recommendation inputs to mark both executed cases as non-comparable.
- [x] (2026-03-04 04:47Z) Milestone 4 hardening pass: fixed nodata-aware BW-02 footprint metric, added explicit `parity_status` (`pass|fail|non_comparable`), and emitted timestamped run evidence (`benchmark_runs_bw01_bw02_20260304T044701Z.json`).
- [x] (2026-03-04 05:11Z) Supplemental curiosity zonal comparison documented: captured `raster_tools.zonal_stats` raw timings and synchronized benchmark/recommendation artifacts with explicit out-of-shortlist caveats.
- [x] (2026-03-04 05:36Z) Claims-vs-code addendum documented: published source-grounded audit artifact with USDA PDF link and synchronized recommendation/tracker references.

## Surprises & Discoveries

- Observation: All comparison repositories requested by stakeholders are already present under `/workdir/`, so there is no external clone/setup blocker for initial discovery.
  Evidence: local directory checks confirmed presence of `/workdir/raster_tools`, `/workdir/weppcloud-wbt`, `/workdir/peridot`, `/workdir/wepppyo3`, and `/workdir/oxidized-rasterstats`.

- Observation: `raster_tools` is large and likely multi-surface (library + scripts), so direct benchmarking without a cross-walk would waste time on non-equivalent operations.
  Evidence: initial clone footprint and file count indicate broad geospatial utility coverage rather than one narrow WEPPpy-aligned API.

- Observation: A substantial part of WEPPcloud geospatial code in this package surface is endpoint orchestration and rendering consumers, not raster compute backends.
  Evidence: `weppcloud/controllers_js/channel_delineation.js`, `weppcloud/controllers_js/channel_gl.js`, and `weppcloud/static/js/gl-dashboard/map/*` mostly call API routes and render GeoTIFF/GeoJSON outputs rather than execute heavy raster algorithms.

- Observation: No direct production `WEPPpy -> zonal_stats/rasterstats` call path was surfaced in the Milestone 1/2 repo scans.
  Evidence: `rg -n "zonal_stats|rasterstats|point_query" wepppy -g '*.py'` returned no matches during matrix construction, so zonal stats remains comparator context rather than shortlisted benchmark workload.

- Observation: Host Python is PEP-668 externally managed, so direct `pip install` of `raster_tools` dependencies failed for system environment.
  Evidence: `python -m pip install -r /home/workdir/raster_tools/requirements/default.txt` returned `error: externally-managed-environment`; benchmark setup required a dedicated venv at `/tmp/raster-tools-bench-venv`.

- Observation: `raster_tools` benchmark runs emitted repeated stderr (`Error in sys.excepthook: Original exception was:`) while still returning success and writing output files.
  Evidence: stderr samples captured in `notes/raw/benchmark_runs_bw01_bw02.json` for BW-01/BW-02 candidate variants.

- Observation: Even after parity guard tightening, BW-01/BW-02 outputs remained grid-mismatched between current and candidate paths, so executed runs are non-comparable.
  Evidence: `notes/raw/benchmark_runs_bw01_bw02.json` reports `comparable=false` for both cases with `same_geotransform=false` and shape mismatches.

- Observation: BW-02 footprint proxy originally over-counted nodata because nodata is non-zero in these fixtures.
  Evidence: nodata-aware fix changed BW-02 valid-footprint counts to `732,422` vs `742,073` in `notes/raw/benchmark_runs_bw01_bw02.json` (previous naive `arr!=0` approach counted full raster size).

- Observation: Supplemental zonal timing showed `raster_tools.zonal_stats` substantially slower than both zonal comparators on both fixtures, but semantics remain non-equivalent and grouped-row outputs differ from per-feature expectations.
  Evidence: `notes/raw/zonal_benchmark_raster_tools.json` (`run_id=20260304T051038Z`) and `notes/raw/zonal_benchmark_wepppyo3_oxidized_rasterstats.json` (`run_id=20260304T050046Z`).

- Observation: External communication language ("AI" and broad performance claims) overstates what is directly evidenced in source and package benchmarks.
  Evidence: `artifacts/claims_vs_code_reality.md` links the USDA PDF (`https://research.fs.usda.gov/download/treesearch/80116.pdf`) to concrete code/benchmark references and required evidence gaps.

## Decision Log

- Decision: Cross-walk first, benchmark second.
  Rationale: Only overlapping operations should be benchmarked; otherwise comparisons are noisy and non-actionable.
  Date/Author: 2026-03-03 / Codex.

- Decision: Keep this package evaluation-only.
  Rationale: Stakeholder ask is to assess incorporation, not to integrate immediately. Implementation should be a follow-up package if approved.
  Date/Author: 2026-03-03 / Codex.

- Decision: Use WEPPpy workload mapping as the anchor for comparison.
  Rationale: Tool-level feature lists are insufficient unless tied to real WEPPpy workflows and call-sites.
  Date/Author: 2026-03-03 / Codex.

- Decision: Mark uncertain tool-family matches as `unknown`/`partial` in Milestone 1 inventory instead of inferring parity from adjacent crates/modules.
  Rationale: Cross-walk and benchmark selection require conservative, evidence-backed equivalence; over-claiming overlap would bias shortlist quality.
  Date/Author: 2026-03-04 / Codex.

- Decision: Gate shortlist entries strictly to matrix rows marked `high|medium`.
  Rationale: Enforces semantic overlap discipline and prevents benchmark effort on excluded/non-comparable workflows.
  Date/Author: 2026-03-04 / Codex.

- Decision: Run candidate benchmarks in a dedicated venv while keeping current-stack runs on system Python.
  Rationale: This was the only viable way to satisfy dependency requirements in the host environment without breaking system-managed packages.
  Date/Author: 2026-03-04 / Codex.

- Decision: Publish a draft closeout recommendation of `defer` instead of `selective adoption`.
  Rationale: Executed cases showed slower candidate runtime and incomplete parity coverage across deferred shortlisted cases.
  Date/Author: 2026-03-04 / Codex.

- Decision: Require strict grid-equivalence preconditions for parity (`same projection + shape + geotransform`) and mark mismatches as `non-comparable`.
  Rationale: This prevents false parity passes for semantically non-equivalent outputs and aligns benchmark interpretation with package constraints.
  Date/Author: 2026-03-04 / Codex.

- Decision: Encode parity with explicit `parity_status` and retain `pass` as nullable for non-comparable outcomes.
  Rationale: Avoids conflating failed parity with non-comparable outcomes in downstream interpretation.
  Date/Author: 2026-03-04 / Codex.

- Decision: Treat zonal curiosity timing as supplemental evidence only (not milestone shortlist evidence).
  Rationale: Milestone 2 shortlist is overlap-gated and zonal semantics across these surfaces are non-identical.
  Date/Author: 2026-03-04 / Codex.

- Decision: Treat external marketing claims as non-authoritative unless backed by source and parity-evaluable benchmark evidence.
  Rationale: Recommendation quality depends on auditable implementation and reproducible measurements, not narrative copy.
  Date/Author: 2026-03-04 / Codex.

## Outcomes & Retrospective

Milestones 1 through 5 are now drafted end-to-end for this package.

Completed artifacts:

- `artifacts/capability_inventory.md`
- `artifacts/wepppy_geospatial_usage_map.md`
- `artifacts/capability_crosswalk_matrix.md`
- `artifacts/benchmark_plan.md`
- `artifacts/benchmark_results.md`
- `artifacts/adoption_recommendation.md`
- `artifacts/claims_vs_code_reality.md`

Result quality is explicitly partial: BW-01/BW-02 executed but non-comparable under strict grid-equivalence guards; BW-03/BW-04/BW-05 are deferred and called out as residual gaps. Recommendation in this draft is `defer`.

Post-closeout supplemental zonal timing evidence was added for stakeholder curiosity (`wepppyo3` vs `oxidized-rasterstats` vs `raster_tools`). Those results are recorded as directional-only telemetry and do not change milestone acceptance outcomes or recommendation status.

An additional claims-vs-code addendum was published after stakeholders provided external communication material. It documents which claims are supported by source evidence in this package and which require further controlled validation.

## Context and Orientation

This package compares candidate and current geospatial toolchains used by WEPPpy.

A "capability cross-walk" in this package means a matrix that maps each workflow-relevant operation family to each toolchain, with notes on parity, gap, and integration complexity.

An "operation family" means a concrete workload category such as raster IO/metadata, reprojection, clipping/masking, zonal statistics, raster math/reclassification, terrain derivatives, vector-raster conversion, and batch execution model.

A "parity check" means validating that benchmarked outputs are functionally equivalent to existing WEPPpy expectations, allowing explicit numeric tolerance when exact binary identity is unrealistic.

Repositories and surfaces in scope:

- Candidate:
  - `/workdir/raster_tools`
- Current stack comparators:
  - `/workdir/weppcloud-wbt`
  - `/workdir/peridot`
  - `/workdir/wepppyo3`
  - `/workdir/oxidized-rasterstats`
  - GDAL usage from WEPPpy code paths
- WEPPpy integration context:
  - `/workdir/wepppy/wepppy/`
  - `/workdir/wepppy/tools/`
  - `/workdir/wepppy/tests/`

Primary package artifact targets:

- `docs/work-packages/20260303_raster_tools_crosswalk_benchmarks/artifacts/capability_inventory.md`
- `docs/work-packages/20260303_raster_tools_crosswalk_benchmarks/artifacts/wepppy_geospatial_usage_map.md`
- `docs/work-packages/20260303_raster_tools_crosswalk_benchmarks/artifacts/capability_crosswalk_matrix.md`
- `docs/work-packages/20260303_raster_tools_crosswalk_benchmarks/artifacts/benchmark_plan.md`
- `docs/work-packages/20260303_raster_tools_crosswalk_benchmarks/artifacts/benchmark_results.md`
- `docs/work-packages/20260303_raster_tools_crosswalk_benchmarks/artifacts/adoption_recommendation.md`
- `docs/work-packages/20260303_raster_tools_crosswalk_benchmarks/artifacts/claims_vs_code_reality.md`

## Plan of Work

Milestone 1 (inventory) creates two grounded documents: one for what each candidate/current toolchain can do and one for where WEPPpy currently uses geospatial operations. This milestone must include source-path references so conclusions are auditable.

Milestone 2 (cross-walk) merges those inventories into one operation-family matrix. For each row, it records current WEPPpy owner, equivalent `raster_tools` support status (`direct`, `partial`, `none`), integration notes, and benchmark priority (`high`, `medium`, `low`, `exclude`).

Milestone 3 (benchmark plan/harness) converts high-priority overlap rows into executable benchmark cases. Each case defines dataset, command/API path for both current and candidate tooling, parity assertion, and repetition strategy.

Milestone 4 (benchmark execution) runs the benchmark suite on one stable host with environment metadata captured. Results are reported as median/p95 wall-clock plus parity outcomes and failure reasons.

Milestone 5 (recommendation) synthesizes cross-walk and benchmark evidence into a decision memo with explicit adoption options: defer, selective adoption, or broad adoption candidate for a future implementation package.

## Concrete Steps

Run commands from `/workdir/wepppy` unless noted.

1. Build raw capability inventory notes for all toolchains.

    mkdir -p docs/work-packages/20260303_raster_tools_crosswalk_benchmarks/notes/raw

    rg --files /workdir/raster_tools > docs/work-packages/20260303_raster_tools_crosswalk_benchmarks/notes/raw/raster_tools_files.txt
    rg --files /workdir/weppcloud-wbt > docs/work-packages/20260303_raster_tools_crosswalk_benchmarks/notes/raw/weppcloud_wbt_files.txt
    rg --files /workdir/peridot > docs/work-packages/20260303_raster_tools_crosswalk_benchmarks/notes/raw/peridot_files.txt
    rg --files /workdir/wepppyo3 > docs/work-packages/20260303_raster_tools_crosswalk_benchmarks/notes/raw/wepppyo3_files.txt
    rg --files /workdir/oxidized-rasterstats > docs/work-packages/20260303_raster_tools_crosswalk_benchmarks/notes/raw/oxidized_rasterstats_files.txt

2. Build WEPPpy geospatial usage map from code search.

    rg -n "gdal|rasterio|whitebox|wbt|peridot|rasterstats|wepppyo3|warp|reproject|zonal|raster" wepppy tools tests > docs/work-packages/20260303_raster_tools_crosswalk_benchmarks/notes/raw/wepppy_geospatial_refs.txt

    Summarize findings into `artifacts/wepppy_geospatial_usage_map.md` with operation family, owning module, and current toolchain.

3. Publish toolchain capability inventory.

    Summarize each repository by operation family, interface shape (CLI/API/library), and dependency model.

    Write output to `artifacts/capability_inventory.md` with explicit source references to repo files.

4. Build cross-walk matrix and benchmark shortlist.

    Create `artifacts/capability_crosswalk_matrix.md` with at least these columns:
    - operation family
    - current WEPPpy path
    - current tool owner
    - raster_tools support status
    - parity risk notes
    - benchmark priority

    Create initial shortlist inside `artifacts/benchmark_plan.md` from overlap rows only (`raster_tools` status `direct|partial`) with `benchmark priority=high|medium`.

5. Define benchmark harness commands and parity checks.

    For each shortlisted case, define:
    - dataset path and size
    - command or API call for current stack
    - command or API call for `raster_tools`
    - number of warmup and measured runs
    - parity assertion and tolerance

6. Execute benchmarks and publish results.

    Store raw runs in `notes/` and summarize in `artifacts/benchmark_results.md`.

    Include host metadata (CPU, RAM, Python/Rust versions, GDAL version, date/time).

7. Publish recommendation memo.

    Write `artifacts/adoption_recommendation.md` with:
    - evidence summary
    - integration cost/risk summary
    - explicit recommendation: `defer`, `selective adoption`, or `broad adoption candidate`
    - follow-up work-package proposal if adoption is recommended

8. Keep package docs synchronized throughout.

    Update:
    - this ExecPlan (`Progress`, `Surprises & Discoveries`, `Decision Log`, `Outcomes & Retrospective`)
    - `tracker.md` task board and progress notes
    - `package.md` success criteria and closure notes (when complete)
    - `PROJECT_TRACKER.md` board position when status changes

## Validation and Acceptance

This evaluation package is complete when all conditions below are true.

- Capability inventory and WEPPpy usage map are published and traceable to source paths.
- Cross-walk matrix clearly shows overlap/gaps and benchmark priorities.
- Benchmark plan is reproducible and ties every case to a cross-walk row.
- Benchmark results include repeated measurements and parity outcomes.
- Recommendation memo provides an explicit decision path with risks and assumptions.
- Documentation lint passes for package docs and project tracker.

Validation commands:

    wctl doc-lint --path docs/work-packages/20260303_raster_tools_crosswalk_benchmarks
    wctl doc-lint --path PROJECT_TRACKER.md

## Idempotence and Recovery

All discovery and documentation steps are additive and can be rerun. Raw note files under `notes/raw/` can be overwritten to refresh inventory snapshots.

If benchmark commands fail due to environment mismatch, capture the failure details in `artifacts/benchmark_results.md` and continue with remaining cases. Do not silently exclude failed cases; mark them as `not runnable` with cause and recommended remediation.

If parity checks fail, record the exact mismatch and tolerance context before changing any benchmark assumptions.

## Artifacts and Notes

Required outputs:

- `artifacts/capability_inventory.md`
- `artifacts/wepppy_geospatial_usage_map.md`
- `artifacts/capability_crosswalk_matrix.md`
- `artifacts/benchmark_plan.md`
- `artifacts/benchmark_results.md`
- `artifacts/adoption_recommendation.md`

Supporting evidence may be stored in:

- `notes/raw/*.txt`
- `notes/*.md`

Each milestone should leave a short command/result evidence note in tracker progress logs.

## Interfaces and Dependencies

This package is evaluation-only and does not change production interfaces.

Evaluation interfaces to document for each toolchain:

- Invocation model: CLI, Python API, Rust API, or mixed.
- Input/output formats: raster formats, vector formats, metadata requirements.
- Dependency model: GDAL/system libraries, Python packages, Rust build/runtime requirements.
- Error model: explicit failure modes relevant to automation.
- Parallelism model: single-process, multithreaded, distributed, or batch wrappers.

Benchmark comparisons must use equivalent workflow semantics. If exact equivalent does not exist, mark the row as non-comparable and do not treat it as a performance loss/win.

No fallback wrappers should be introduced in this package. Missing dependencies or unsupported operations must fail explicitly and be recorded as findings.

---
Revision Note (2026-03-03, Codex): Initial ExecPlan authored during work-package setup.
Revision Note (2026-03-04, Codex): Updated living sections after Milestone 1 completion (progress, discoveries, decisions, outcomes) and recorded conservative evidence policy for cross-walk parity claims.
Revision Note (2026-03-04, Codex): Recorded Milestone 2 completion, added shortlist gating decision, and documented the zonal-stats call-path discovery affecting benchmark scope.
Revision Note (2026-03-04, Codex): Added Milestone 3 harness implementation details, Milestone 4 draft benchmark execution outcomes (including deferred cases), and Milestone 5 draft recommendation memo (`defer`).
Revision Note (2026-03-04, Codex): Applied Milestone 3/4 QA corrections for strict parity comparability (grid-equivalence preconditions), reran BW-01/BW-02, and updated outcomes to non-comparable where contracts were not met.
Revision Note (2026-03-04, Codex): Applied Milestone 4 metric hardening (nodata-aware BW-02 footprint, explicit parity_status tri-state, timestamped raw benchmark outputs) and synchronized recommendation language to directional-only timing evidence.
Revision Note (2026-03-04, Codex): Recorded supplemental zonal curiosity benchmark evidence (`notes/raw/zonal_benchmark_raster_tools.json`) and synchronized artifacts while preserving shortlist/milestone scope boundaries.
Revision Note (2026-03-04, Codex): Added claims-vs-code addendum (`artifacts/claims_vs_code_reality.md`) with USDA PDF source link and source-grounded claim audit references.
