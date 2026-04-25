Execute the active work package end-to-end:

- Package: `/home/workdir/wepppy/docs/work-packages/20260424_landuse_disturbed_mofe_pipeline_optimization/`
- Active ExecPlan: `/home/workdir/wepppy/docs/work-packages/20260424_landuse_disturbed_mofe_pipeline_optimization/prompts/active/landuse_disturbed_mofe_pipeline_optimization_execplan.md`

Required scope:
1. Implement Lane 1 (highest priority): consolidate duplicate heavy `build_managements()` work across the LANDUSE_DOMLC_COMPLETE chain while preserving trigger/event contracts.
2. Implement Lane 2: reduce remap/MOFE hot-loop INFO logging to compact summaries + DEBUG detail; preserve warning/error diagnostics.
3. Implement Lane 3 (guarded): add MOFE pair-count reuse only when same-cycle inputs are unchanged, with explicit invalidation semantics.
4. Add/extend targeted tests for all touched lane behavior:
   - event/build-pass contract preservation
   - disturbed routing/remap parity
   - logging contract behavior
   - pair-count cache guard hit/miss/parity behavior
5. Run lane-level parity and benchmark comparisons on isolated temp dirs (no source run mutation).
6. Complete code/QA/security review artifacts with finding dispositions.

Execution constraints:
- Preserve explicit failure contracts; do not introduce silent fallback wrappers.
- Do not mutate source run artifacts under `/wc1/runs/ap/apprehensive-caw/`.
- Sequence lanes in priority order and stop progression if parity fails.

Artifacts to produce under package `artifacts/`:
- Existing investigation artifacts (preserve):
  - `apprehensive_caw_timing_raw.json`
  - `apprehensive_caw_timing_profile.md`
  - `landuse_disturbed_pipeline_optimization_candidates.md`
- New execution artifacts:
  - `lane_benchmark_raw.json`
  - `lane_benchmark_summary.md`
  - `lane_parity_raw.json`
  - `lane_parity_notes.md`
  - `2026-04-24_code_review.md`
  - `2026-04-24_qa_review.md`
  - `2026-04-24_security_review.md`

Package-doc updates required:
- Update active ExecPlan living sections (`Progress`, `Surprises & Discoveries`, `Decision Log`, `Outcomes & Retrospective`) during execution.
- Update `tracker.md` with UTC timestamps for lane progress, decisions, and verification outcomes.
- Update `package.md` closure notes on successful completion.
- Archive active ExecPlan into `prompts/completed/` with outcome note when package closes.
- Update `PROJECT_TRACKER.md` lifecycle/status entries.

Validation expectations:
- Targeted pytest suites for touched landuse/disturbed modules pass.
- Benchmark summary includes per-run timings, mean/stddev, and percent delta.
- Parity artifacts confirm no required-output drift for required benchmark runs.
- Code/QA/security review artifacts close with no unresolved medium/high findings.

Finish with a concise closure summary:
- changed files
- behavior delta
- tests run/results
- benchmark results
- review findings/disposition
- residual risks/follow-ups
