# Tracker - Raster Tools Cross-Walk and Benchmark Evaluation

> Living document tracking progress, decisions, risks, and communication for this work package.

## Quick Status

**Started**: 2026-03-03  
**Current phase**: Draft closeout complete with supplemental zonal + claims-vs-code addenda captured  
**Last updated**: 2026-03-04  
**Next milestone**: Optional follow-up package for deferred benchmark coverage.
**Implementation plan**: `docs/work-packages/20260303_raster_tools_crosswalk_benchmarks/prompts/active/raster_tools_crosswalk_benchmark_execplan.md`

## Task Board

### Ready / Backlog
- [ ] None in this package (deferred benchmark completion is explicitly routed to a follow-up package).

### In Progress
- [ ] None.

### Blocked
- [ ] None.

### Done
- [x] Created package scaffold (`package.md`, `tracker.md`, `prompts/active`, `prompts/completed`, `artifacts`, `notes`) (2026-03-03).
- [x] Authored active ExecPlan for cross-walk-first then benchmark-second execution (2026-03-03).
- [x] Added package entry in `PROJECT_TRACKER.md` backlog (2026-03-03).
- [x] Ran documentation lint for package docs and `PROJECT_TRACKER.md` (2026-03-03).
- [x] Added end-to-end sub-agent execution prompt (`prompts/active/run_raster_tools_crosswalk_benchmark_e2e.prompt.md`) and registered active ExecPlan in root `AGENTS.md` (2026-03-03).
- [x] Milestone 1 complete: published `artifacts/capability_inventory.md` and `artifacts/wepppy_geospatial_usage_map.md` with source-path evidence and unknown/non-comparable notes (2026-03-04).
- [x] Refreshed raw evidence snapshots in `notes/raw/` for toolchain capability claims and WEPPpy call-path mapping (2026-03-04).
- [x] Milestone 2 complete: published `artifacts/capability_crosswalk_matrix.md` and overlap-gated shortlist in `artifacts/benchmark_plan.md` (2026-03-04).
- [x] Milestone 3 complete: expanded benchmark plan with harness commands, datasets, run counts, and parity assertions; added runnable harness script (2026-03-04).
- [x] Milestone 4 draft complete: executed BW-01/BW-02 benchmarks, captured raw run JSON, and published benchmark results with parity outcomes and deferred-case notes (2026-03-04).
- [x] Milestone 5 draft complete: published recommendation memo with explicit `defer` outcome and follow-up proposal (2026-03-04).
- [x] QA correction pass complete: tightened benchmark parity guards (`same projection + shape + geotransform`), fixed p95 computation in harness, reran BW-01/BW-02, and reclassified both executed cases as `non-comparable` (2026-03-04).
- [x] Benchmark metric hardening complete: BW-02 footprint made nodata-aware, parity encoded with explicit `parity_status`, and timestamped rerun evidence emitted (2026-03-04).
- [x] Supplemental zonal curiosity comparison documented: added reproducible `raster_tools.zonal_stats` raw timings and synchronized benchmark/recommendation artifacts with out-of-shortlist caveats (2026-03-04).
- [x] Claims-vs-code addendum documented: added source-grounded audit of USDA PDF claims versus package evidence and linked it from recommendation artifacts (2026-03-04).

## Timeline

- **2026-03-03** - Package created and scoped.
- **2026-03-03** - Active ExecPlan drafted for phased evaluation.
- **2026-03-03** - Project-level backlog entry added.
- **2026-03-04** - Milestone 1 artifacts published; package moved into Milestone 2 cross-walk drafting.
- **2026-03-04** - Milestone 2 cross-walk matrix and shortlist published; package moved into Milestone 3 harness planning.
- **2026-03-04** - Milestone 3 harness plan + script published.
- **2026-03-04** - Milestone 4 draft benchmark execution completed for BW-01/BW-02 with raw evidence.
- **2026-03-04** - Milestone 5 draft recommendation published (`defer`).
- **2026-03-04** - Milestone 3/4 QA correction pass applied; BW-01/BW-02 marked non-comparable under strict parity contract.
- **2026-03-04** - Milestone 4 metric hardening applied (nodata-aware BW-02 footprint + parity-status tri-state + timestamped run JSON).
- **2026-03-04** - Supplemental zonal curiosity run captured for `raster_tools` and compared against existing `wepppyo3`/`oxidized-rasterstats` zonal evidence (directional-only).
- **2026-03-04** - Claims-vs-code addendum published with USDA PDF source link and source-evidence-backed interpretation boundaries.

## Decisions

### 2026-03-03: Run cross-walk before benchmarks
**Context**: Stakeholder ask combines tooling evaluation and performance benchmarking.

**Options considered**:
1. Start benchmarks immediately across all tools.
2. Build capability cross-walk first, benchmark only overlapping workflows.

**Decision**: Build the cross-walk first and use it to define a benchmark shortlist.

**Impact**: Benchmark time is focused on decision-relevant comparisons and avoids noisy or non-comparable runs.

---

### 2026-03-03: Keep this package evaluation-only
**Context**: The immediate ask is to evaluate incorporation feasibility and value.

**Options considered**:
1. Combine evaluation and production integration in one package.
2. Keep this package limited to analysis and benchmark evidence.

**Decision**: Keep this package evaluation-only; implementation happens in a follow-up package if approved.

**Impact**: Scope stays bounded and stakeholders receive a clear recommendation artifact before code churn.

---

### 2026-03-04: Use conservative overlap labeling (`unknown`/`partial`) when evidence is indirect
**Context**: Some capability inferences were tempting from adjacent crates/workspaces (especially for `weppcloud-wbt` and broad WEPPpy utility surfaces).

**Options considered**:
1. Infer likely parity from neighboring modules and ecosystem expectations.
2. Mark only directly evidenced parity and label uncertain families `unknown`/`partial`.

**Decision**: Use conservative labeling (`unknown`/`partial`) until explicit call-site or API evidence confirms overlap.

**Impact**: Reduces risk of benchmarking non-equivalent operations and improves shortlist quality.

---

### 2026-03-04: Shortlist only `high|medium` cross-walk rows
**Context**: Milestone 2 required benchmark candidate selection from overlap evidence.

**Options considered**:
1. Include low-confidence/non-comparable rows to increase benchmark count.
2. Restrict shortlist to matrix rows explicitly marked `high|medium`.

**Decision**: Restrict shortlist to `high|medium` rows and explicitly list exclusions.

**Impact**: Keeps benchmark effort tied to evidence-backed overlap and parity-feasible workloads.

---

### 2026-03-04: Use dedicated venv for `raster_tools` benchmark execution
**Context**: Host Python environment is externally managed and blocked direct package install.

**Options considered**:
1. Override system package protections.
2. Create isolated benchmark venv for candidate runs.

**Decision**: Create isolated venv at `/tmp/raster-tools-bench-venv` and keep current-stack commands on system Python.

**Impact**: Enabled execution but introduced environment-normalization risk in runtime comparisons.

---

### 2026-03-04: Draft recommendation set to `defer`
**Context**: Draft benchmark run executed subset cases only and showed no candidate runtime gain.

**Options considered**:
1. Recommend selective adoption from partial evidence.
2. Recommend defer pending deferred-case completion and normalized environment rerun.

**Decision**: Recommend `defer` in this package draft.

**Impact**: Avoids premature integration commitment while preserving a clear follow-up path.

---

### 2026-03-04: Enforce strict parity comparability contract
**Context**: Review found executed cases could be interpreted as parity pass/fail despite grid mismatches.

**Options considered**:
1. Keep partial-equivalence proxy outcomes as-is.
2. Require strict grid equivalence (`same projection + shape + geotransform`) and mark mismatches non-comparable.

**Decision**: Enforce strict grid equivalence preconditions and treat mismatched outputs as `non-comparable`.

**Impact**: Prevents false parity conclusions and aligns benchmark interpretation with evaluation constraints.

---

### 2026-03-04: Encode parity status as tri-state
**Context**: Non-comparable outcomes were initially represented as boolean `pass=false`, which can be misread as parity failure.

**Options considered**:
1. Keep boolean `pass` only and rely on a separate `comparable` flag.
2. Add explicit `parity_status` (`pass|fail|non_comparable`) and keep `pass` nullable when non-comparable.

**Decision**: Add explicit `parity_status` and emit timestamped raw benchmark files for rerun traceability.

**Impact**: Improves evidence interpretation and prevents conflation of failure vs non-comparability.

---

### 2026-03-04: Record zonal curiosity evidence as supplemental only
**Context**: Stakeholder requested a curiosity comparison for zonal workloads after core milestone closeout.

**Options considered**:
1. Fold zonal timing into shortlist benchmark outcomes.
2. Record zonal timing as supplemental evidence outside shortlist scope.

**Decision**: Record zonal timing as supplemental-only evidence with explicit semantic caveats.

**Impact**: Preserves auditability for the extra run while keeping milestone acceptance criteria and recommendation basis unchanged.

---

### 2026-03-04: Treat external marketing claims as non-authoritative until source-backed
**Context**: Stakeholder provided USDA communication PDF language asserting broad AI framing and efficiency claims.

**Options considered**:
1. Treat communication copy as equivalent to implementation-level evidence.
2. Record a source-backed claims-vs-code addendum and keep recommendation anchored to audited evidence.

**Decision**: Publish a claims-vs-code addendum and keep recommendation logic tied to reproducible code and benchmark artifacts.

**Impact**: Reduces risk of adopting on narrative claims that exceed what is currently evidenced by source and parity benchmarks.

## Risks and Issues

| Risk | Severity | Likelihood | Mitigation | Status |
|------|----------|------------|------------|--------|
| Capability mapping misses hidden runtime use-cases | High | Medium | Build WEPPpy usage map from code search plus owner validation pass | Open |
| Benchmark results are skewed by non-equivalent workflows | High | Medium | Benchmark only cross-walk-confirmed overlap with parity checks | Open |
| Tool setup differences dominate timing results | Medium | High | Capture environment metadata and run repeated trials on one host | Open |
| Stakeholders over-interpret raw speed without operational cost | Medium | Medium | Include maintenance/integration complexity in final recommendation | Open |

## Verification Checklist

### Documentation and Planning
- [x] `wctl doc-lint --path docs/work-packages/20260303_raster_tools_crosswalk_benchmarks`
- [x] `wctl doc-lint --path PROJECT_TRACKER.md`
- [x] Milestone 1 artifacts include source references and unknown/non-comparable assumptions.

### Benchmark Evidence
- [x] Benchmark plan artifact includes command lines and dataset definitions.
- [x] Benchmark run logs include repeated trials and summary statistics.
- [x] Output parity checks are documented for executed benchmark workflows (BW-01/BW-02) with explicit non-comparable handling for grid mismatch.
- [x] Recommendation memo links to cross-walk and benchmark evidence.

## Progress Notes

### 2026-03-03: Package setup
**Agent/Contributor**: Codex

**Work completed**:
- Created work-package scaffold and baseline docs.
- Authored package brief and tracker.
- Authored active ExecPlan with milestone sequence and acceptance gates.
- Added package entry to root `PROJECT_TRACKER.md` backlog.

**Blockers encountered**:
- None.

**Next steps**:
1. Build capability inventory artifacts.
2. Build WEPPpy geospatial usage map.
3. Publish cross-walk matrix draft and shortlist benchmark workloads.

**Test results**:
- `wctl doc-lint --path docs/work-packages/20260303_raster_tools_crosswalk_benchmarks` -> pass (`3 files validated, 0 errors, 0 warnings`).
- `wctl doc-lint --path PROJECT_TRACKER.md` -> pass (`1 files validated, 0 errors, 0 warnings`).

### 2026-03-03: AGENTS + execution prompt installation
**Agent/Contributor**: Codex

**Work completed**:
- Updated root `AGENTS.md` to register the active work-package ExecPlan path.
- Added `prompts/active/run_raster_tools_crosswalk_benchmark_e2e.prompt.md` with required sub-agent sequence and milestone gates.

**Blockers encountered**:
- None.

**Next steps**:
1. Use the new `run_*_e2e` prompt to execute Milestone 1 artifact production end-to-end.

**Test results**:
- `wctl doc-lint --path AGENTS.md` -> pass (`1 files validated, 0 errors, 0 warnings`).
- `wctl doc-lint --path docs/work-packages/20260303_raster_tools_crosswalk_benchmarks/prompts/active/run_raster_tools_crosswalk_benchmark_e2e.prompt.md` -> pass (`1 files validated, 0 errors, 0 warnings`).

### 2026-03-04: Milestone 1 completion
**Agent/Contributor**: Codex

**Work completed**:
- Generated raw capability and usage evidence files under `notes/raw/`.
- Published `artifacts/capability_inventory.md` across candidate and comparator toolchains.
- Published `artifacts/wepppy_geospatial_usage_map.md` with NoDb/WEPPcloud workflow mapping and call-path evidence.
- Updated active ExecPlan living sections to record Milestone 1 completion and discoveries.

**Blockers encountered**:
- None external; all required comparison repositories were available locally.

**Next steps**:
1. Build `artifacts/capability_crosswalk_matrix.md` from Milestone 1 evidence.
2. Create benchmark shortlist tied to `high|medium` overlap rows in `artifacts/benchmark_plan.md`.
3. Validate Milestone 2 docs with `wctl doc-lint`.

**Test results**:
- `wctl doc-lint --path docs/work-packages/20260303_raster_tools_crosswalk_benchmarks` -> pass (`6 files validated, 0 errors, 0 warnings`).

### 2026-03-04: Milestone 2 completion
**Agent/Contributor**: Codex

**Work completed**:
- Published capability cross-walk matrix with operation-family status (`direct|partial|none|unknown`) and benchmark priorities.
- Derived benchmark shortlist exclusively from `high|medium` matrix rows.
- Documented excluded/non-comparable rows and reasons.

**Blockers encountered**:
- None.

**Next steps**:
1. Add case-level benchmark harness commands, datasets, run counts, and parity checks.
2. Execute shortlisted benchmark cases and capture raw outputs.
3. Publish benchmark results and recommendation memo.

**Test results**:
- `wctl doc-lint --path docs/work-packages/20260303_raster_tools_crosswalk_benchmarks` -> pass (`8 files validated, 0 errors, 0 warnings`).

### 2026-03-04: Milestones 3-5 draft completion
**Agent/Contributor**: Codex

**Work completed**:
- Created benchmark harness script and executed BW-01/BW-02 cases.
- Captured benchmark runtime/parity outputs and host metadata in `notes/raw/`.
- Published benchmark results artifact and recommendation memo (`defer`).
- Updated active ExecPlan living sections through Milestone 5 draft closeout.

**Blockers encountered**:
- Host Python package policy (`externally-managed-environment`) blocked direct dependency installation; mitigated with dedicated venv.

**Next steps**:
1. If desired, run deferred BW-03/BW-04/BW-05 in a normalized single-environment setup.
2. Investigate candidate stderr `sys.excepthook` noise during successful runs.

**Test results**:
- `python docs/work-packages/20260303_raster_tools_crosswalk_benchmarks/notes/benchmark_harness_bw01_bw02.py` -> pass (raw JSON written).

### 2026-03-04: Milestone 3/4 QA correction pass
**Agent/Contributor**: Codex

**Work completed**:
- Resolved review findings in Milestone 1 and Milestone 2 artifact traceability.
- Updated `benchmark_harness_bw01_bw02.py` to compute true p95 and enforce strict grid comparability preconditions.
- Updated benchmark plan parity contracts and reran BW-01/BW-02.
- Hardened BW-02 footprint metric to use nodata-aware valid-cell counts.
- Added explicit `parity_status` (`pass|fail|non_comparable`) and timestamped raw run output for rerun traceability.
- Updated benchmark results + recommendation memo to classify executed cases as `non-comparable` under strict parity contract.

**Blockers encountered**:
- None.

**Next steps**:
1. Execute deferred BW-03/BW-04/BW-05 cases in a normalized environment.
2. If adoption is reconsidered, first demonstrate at least one parity-comparable overlap case.

**Test results**:
- `python docs/work-packages/20260303_raster_tools_crosswalk_benchmarks/notes/benchmark_harness_bw01_bw02.py` -> pass (rerun JSON written).

### 2026-03-04: Supplemental zonal curiosity benchmark sync
**Agent/Contributor**: Codex

**Work completed**:
- Ran `raster_tools.zonal_stats` on `small` and `large_local` fixtures with `stats=['count','mode']` and `features_field='TopazID'`.
- Wrote raw run output to `notes/raw/zonal_benchmark_raster_tools.json`.
- Synchronized `artifacts/benchmark_results.md` and `artifacts/adoption_recommendation.md` with side-by-side zonal timing summary and non-equivalent semantics caveat.

**Blockers encountered**:
- None.

**Next steps**:
1. Keep zonal comparison as directional-only unless a production-equivalent WEPPpy zonal call path is added to shortlist scope.

**Test results**:
- `python docs/work-packages/20260303_raster_tools_crosswalk_benchmarks/notes/zonal_benchmark_wepppyo3_oxidized_rasterstats.py` -> pass (raw JSON written).
- `PYTHONPATH=/home/workdir/raster_tools /tmp/raster-tools-bench-venv/bin/python - <<'PY' ... raster_tools.zonal_stats ... PY` -> pass (`notes/raw/zonal_benchmark_raster_tools.json` written).

### 2026-03-04: Claims-vs-code addendum publication
**Agent/Contributor**: Codex

**Work completed**:
- Added `artifacts/claims_vs_code_reality.md` to document verifiable capabilities, unverified/contradicted claims, and required future evidence.
- Added source URL to USDA PDF (`https://research.fs.usda.gov/download/treesearch/80116.pdf`) and linked to raw audit evidence.
- Linked addendum from `artifacts/adoption_recommendation.md`.

**Blockers encountered**:
- None.

**Next steps**:
1. If needed, convert this addendum into a follow-up package acceptance gate for future adoption reconsideration.

**Test results**:
- `wctl doc-lint --path docs/work-packages/20260303_raster_tools_crosswalk_benchmarks` -> pass (`11 files validated, 0 errors, 0 warnings`).
- `wctl doc-lint --path PROJECT_TRACKER.md` -> pass (`1 files validated, 0 errors, 0 warnings`).

## Watch List

- **Dataset representativeness**: benchmark datasets must match WEPPpy-realistic workloads.
- **Contract drift risk**: recommendation should not assume unsupported APIs or hidden wrappers.
- **Boundary discipline**: avoid sliding from evaluation into integration work in this package.

## Communication Log

### 2026-03-03: Stakeholder request intake
**Participants**: User, Codex  
**Question/Topic**: Set up a work package to evaluate `/workdir/raster_tools` against current tooling and then benchmark performance.  
**Outcome**: Created a scoped evaluation package with active ExecPlan and backlog registration.
