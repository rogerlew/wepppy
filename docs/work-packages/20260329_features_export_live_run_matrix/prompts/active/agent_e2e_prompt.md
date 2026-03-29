# Agent Prompt: Execute Features Export Live-Run Matrix End-to-End

Use this prompt verbatim in a new Codex/Copilot session to execute the work package.

---

Execute the active work-package ExecPlan end-to-end:
`docs/work-packages/20260329_features_export_live_run_matrix/prompts/active/features_export_live_run_matrix_execplan.md`

Scope and constraints:
- Run against `runid=clogging-starch`, `config=disturbed9002-wbt-mofe`.
- Follow gate flow strictly:
  1. `Gate-1` sentinel suite (one successful case per format + core negative cases).
  2. `Gate-2` core matrix groups A-E only after Gate-1 passes.
  3. Expansion groups F-G (cache-hit replay, additional negative payload contract, units numeric oracles, UI regressions).
- Use the matrix and acceptance criteria in:
  - `docs/work-packages/20260329_features_export_live_run_matrix/package.md`
  - `docs/work-packages/20260329_features_export_live_run_matrix/tracker.md`
  - the active ExecPlan above

Required outcomes:
- Validate all format contracts (`geojson`, `geoparquet`, `parquet`, `csv`, `kmz`, `geopackage`, `geodatabase`) including artifact member/signature checks.
- Validate CRS (`wgs`, `utm`) behavior with file-level probes for spatial formats and no-op CRS behavior for tabular formats.
- Validate units (`project`, `si`, `english`) including deterministic numeric conversion checks/tolerances.
- Validate temporal behavior for atemporal + yearly + event combinations, year selection variants, and mixed long-layout rejection.
- Validate identity and data-integrity invariants:
  - canonical `topaz_id`, `wepp_id` columns,
  - no row with both identity values missing,
  - strict tabular identity completeness,
  - key-domain oracle reconciliation with source carrier domains.
- Validate cache replay contract by rerunning identical payloads and asserting `cache_hit`, `source_job_id`, stable artifact mapping.
- Fix UI copy typo from `Unitzer Selections` to `Unitizer Selections` and add regression coverage.
- Validate no page reload regression on temporal mode changes and export-button unlock behavior after successful export.

Execution requirements:
- Do not stop at planning. Implement, run, triage, patch, retest, and document to closure unless blocked.
- Record evidence under:
  `docs/work-packages/20260329_features_export_live_run_matrix/artifacts/`
  minimum files:
  - `matrix_results.jsonl`
  - `manual_sanity_notes.md`
  - `defect_log.md`
- Keep the living docs updated continuously:
  - ExecPlan `Progress`, `Surprises & Discoveries`, `Decision Log`, `Outcomes & Retrospective`
  - package `tracker.md`
- If you change contracts or case definitions, update `package.md` matrix tables accordingly.

Validation before handoff:
- `wctl run-pytest tests/nodb/mods/test_features_export_service.py --maxfail=1`
- `wctl run-pytest tests/microservices/test_rq_engine_features_export_routes.py --maxfail=1`
- `wctl run-pytest tests/weppcloud/routes/test_pure_controls_render.py --maxfail=1`
- `wctl run-npm test -- features_export`

Handoff format:
- Provide concise summary first:
  - pass/fail counts by matrix group
  - defects found/fixed
  - unresolved risks
- Then provide file list of changed code/tests/docs and artifact evidence paths.

---

