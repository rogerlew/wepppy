# Execute: Geneva Storm Shape Control

Execute the active work package end-to-end:

- Package: `/workdir/wepppy/docs/work-packages/20260428_geneva_storm_shape_control/`
- WEPPpy repo: `/workdir/wepppy`
- Rust native-kernel repo: `/workdir/wepppyo3`

Required outcome: Geneva users can select `Storm Shape` as Uniform, NEH-4 B, Type I, Type IA, Type II, or Type III, and that selected shape is honored in UI payloads, Python validation/orchestration, Rust hyetograph generation, generated run artifacts, query/report payloads, and Geneva documentation.

Read first:

1. `/workdir/wepppy/AGENTS.md`
2. `/workdir/wepppy/docs/prompt_templates/codex_exec_plans.md`
3. `/workdir/wepppy/docs/work-packages/20260428_geneva_storm_shape_control/package.md`
4. `/workdir/wepppy/docs/work-packages/20260428_geneva_storm_shape_control/tracker.md`
5. `/workdir/wepppy/docs/work-packages/20260428_geneva_storm_shape_control/artifacts/2026-04-28_current_status_assessment.md`
6. `/workdir/wepppy/docs/work-packages/20260428_geneva_storm_shape_control/artifacts/2026-04-28_type_i_ia_ii_iii_hyetograph_research.md`
7. `/workdir/wepppy/docs/work-packages/20260428_geneva_storm_shape_control/artifacts/2026-04-28_type_hyetograph_spec_qa_validation.md`
8. `/workdir/wepppy/wepppy/nodb/mods/geneva/specification.md`, especially section 11.6
9. `/workdir/wepppy/wepppy/nodb/mods/geneva/culvert-cn-comparison.md`

Before coding, create and maintain an active ExecPlan:

- Path: `/workdir/wepppy/docs/work-packages/20260428_geneva_storm_shape_control/prompts/active/geneva_storm_shape_control_execplan.md`
- The ExecPlan must follow `/workdir/wepppy/docs/prompt_templates/codex_exec_plans.md`.
- Keep `Progress`, `Surprises & Discoveries`, `Decision Log`, and `Outcomes & Retrospective` current.
- Update `tracker.md` at every handoff and after every validation run.

Implementation constraints:

- Do not start Type I/IA/II/III runtime implementation until these checked-in artifacts exist under `/workdir/wepppyo3/geneva_core/resources/`:
  - `nrcs_legacy_24h_distributions.wintr20_raw.txt`
  - `nrcs_legacy_24h_distributions.csv`
  - `nrcs_legacy_24h_distributions.metadata.json`
- The metadata must include WinTR-20 version, generation date, raw-output filename/SHA-256, export mode, source time increment, decimal precision, rounding policy, post-processing steps, normalized CSV SHA-256, row count, and monotonic endpoint checks.
- Type II embedded-duration ratios from NEH Chapter 4 Figure 4-31 must pass within absolute fraction tolerance `<= 0.003`; regenerate or export a finer source table before relaxing tolerance.
- Type I/IA/II/III short-duration hyetographs must use embedded-window extraction from the 24-hour cumulative curve, not full-curve compression.
- Keep `Storm Shape` as a closed enum. Do not add custom/user-uploaded distributions in this package.
- Preserve missing-value compatibility by defaulting `distribution_type` to `neh4_type_b` unless the user explicitly approves a default change.
- Existing completed artifacts that claimed Type B but were produced by the old uniform Python path must not be silently relabeled as equivalent to newly generated Type B outputs.

Primary implementation scope:

- WEPPcloud UI/control payloads:
  - `/workdir/wepppy/wepppy/weppcloud/templates/controls/geneva_pure.htm`
  - `/workdir/wepppy/wepppy/weppcloud/controllers_js/geneva.js`
- Python Geneva schemas/services/reports:
  - `/workdir/wepppy/wepppy/nodb/mods/geneva/schemas/run_batch_schema.py`
  - `/workdir/wepppy/wepppy/nodb/mods/geneva/schemas/query_schema.py`
  - `/workdir/wepppy/wepppy/nodb/mods/geneva/collaborators/frequency_panel_service.py`
  - `/workdir/wepppy/wepppy/nodb/mods/geneva/collaborators/batch_run_service.py`
  - `/workdir/wepppy/wepppy/nodb/mods/geneva/collaborators/report_payload_service.py`
- Rust Geneva core:
  - `/workdir/wepppyo3/geneva_core/src/hyetograph.rs`
  - `/workdir/wepppyo3/geneva_core/src/frequency_panel.rs`
- Documentation:
  - `/workdir/wepppy/wepppy/nodb/mods/geneva/specification.md`
  - `/workdir/wepppy/wepppy/nodb/mods/geneva/culvert-cn-comparison.md`
  - package tracker, ExecPlan, and validation artifacts

Expected implementation sequence:

1. Create the active ExecPlan and record the start in `tracker.md` and `PROJECT_TRACKER.md`.
2. Check both worktrees with `git status --short --untracked-files=all`; do not stage unrelated changes.
3. Generate and validate the WinTR-20 raw/normalized/metadata artifacts in `/workdir/wepppyo3/geneva_core/resources/`.
4. Implement Rust source loading, embedded-window extraction, Uniform/NEH-4 B/Type I/IA/II/III dispatch, metadata, and tests.
5. Update Python schemas and batch execution so selected storm shape is validated, passed to Rust, persisted, and reported.
6. Add the Geneva UI `Storm Shape` selector and JavaScript payload tests.
7. Update reports and docs so assumptions, generated artifacts, and stale-artifact policy are consistent.
8. Dispatch the required `reviewer` sub-agent for code review and the required `qa_reviewer` sub-agent for QA review; record both review artifacts and dispose every Medium/High finding.
9. Run validation, update package lifecycle docs, and provide a concise closure summary.

Validation commands:

- From `/workdir/wepppy`:
  - `wctl run-npm test -- geneva`
  - `wctl run-npm lint`
  - `python3 wepppy/weppcloud/controllers_js/build_controllers_js.py`
  - `wctl run-pytest tests/nodb/mods/geneva tests/weppcloud/routes/test_geneva_bp.py tests/weppcloud/routes/test_geneva_wp08_routes.py tests/rq/test_geneva_rq.py tests/microservices/test_rq_engine_geneva_routes.py --maxfail=1`
  - `wctl doc-lint --path PROJECT_TRACKER.md --path docs/work-packages/20260428_geneva_storm_shape_control --path wepppy/nodb/mods/geneva/specification.md --path wepppy/nodb/mods/geneva/culvert-cn-comparison.md`
  - `git diff --check`
- From `/workdir/wepppyo3`:
  - `cargo test -p geneva_core`
  - `git diff --check`

Finish with:

- Changed files grouped by repository.
- Behavior delta, including how to verify selected storm shape in artifacts/reports.
- Validation commands and results.
- Review-gate outcomes and any accepted residual risks.
- Exact source/provenance artifact paths and hashes for Type I/IA/II/III.
