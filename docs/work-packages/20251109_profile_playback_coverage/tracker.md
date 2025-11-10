# Work Package Tracker: Profile Playback Code Coverage Mapping

## Task Board

### Phase 1 – Instrumentation (targets M1)
- [x] **T1.1** Coverage middleware skeleton in `wepppy/weppcloud/middleware/profile_coverage.py` (start/stop, context tagging, error handling).
- [x] **T1.2** App factory + blueprint wiring with env toggles (`ENABLE_PROFILE_COVERAGE`, `PROFILE_COVERAGE_DIR`, config loader for `coverage.profile-playback.ini`).
- [x] **T1.3** Slug propagation helpers (`wepppy/rq/utils.py`): attach `profile_trace_slug` to jobs/subprocess env.
- [ ] **T1.4** RQ worker bootstrap to honor slug + start coverage with `parallel=True`, `data_suffix=True`.
- [ ] **T1.5** Playback CLI (`tools/profile_playback_cli.py` + `wctl`) adds `--trace-code`, `X-Profile-Trace` header, and local artifact directory overrides.

### Phase 2 – Local Validation (wraps M1)
- [ ] **T2.1** Smoke run: execute a single profile with tracing enabled; archive resulting `{slug}.coverage`.
- [ ] **T2.2** Regression checklist ensuring tracing is entirely opt-in and doesn’t slow default runs (>5% variance).
- [ ] **T2.3** Author `docs/dev-notes/profile-coverage.md` quick-start (setup, toggles, troubleshooting).

### Phase 3 – Reporting Toolchain (targets M2)
- [ ] **T3.1** Static symbol inventory builder (`tools/profile_coverage/build_symbol_index.py`) with persisted JSON artifact.
- [ ] **T3.2** Per-profile report generator (`tools/profile_coverage/generate_reports.py`) → HTML + JSON (modules/classes/symbols, executed lines, coverage%).
- [ ] **T3.3** Cross-profile matrix builder (`tools/profile_coverage/build_matrix.py`) combining all JSON inputs into `profile→symbols`, `symbol→profiles`, and coverage gap list.
- [ ] **T3.4** Automated tests for the tooling modules (unit tests under `tests/profile_coverage/`).

### Phase 4 – CI/CD Integration (targets M3)
- [ ] **T4.1** Update playback workflow generator to set tracing env + fetch artifacts.
- [ ] **T4.2** Regenerate `.github/workflows/forest_workflow_*.yml` (nightly set) with tracing turned on behind feature flag.
- [ ] **T4.3** Add nightly aggregation job: download artifacts, run matrix builder, upload consolidated bundle.
- [ ] **T4.4** Performance sampling in CI comparing baseline vs. tracing (publish in job summary and store in `artifacts/perf-baseline.json`).

### Phase 5 – Stabilization & Adoption (targets M4)
- [ ] **T5.1** Update `AGENTS.md`, `tests/README.md`, and `docs/readme.md` with coverage instructions + FAQs.
- [ ] **T5.2** Add guardrails (`wctl check-profile-coverage`) to ensure symbol inventory + config stay in sync with source tree.
- [ ] **T5.3** Close loop with stakeholders (demo, collect feedback, decide on next feature requests), then mark work package complete.

## Decisions Log

| Date | Decision | Rationale | Stakeholders |
|---|---|---|---|
| 2025-11-09 | Use Flask middleware with `coverage.py` for server-side tracing. | Playback is a client/server interaction; only server-side tracing sees backend execution. | `@rogerlew`, `@GitHub-Copilot` |
| 2025-11-09 | Use `X-Profile-Trace` header to activate tracing. | Explicit opt-in per profile; avoids changing route logic. | `@GitHub-Copilot` |
| 2025-11-09 | Store raw `.coverage` files under `/workdir/wepppy-test-engine-data/coverage`. | Keeps artifacts outside repo tree and aligns with existing playback storage. | `@GitHub-Copilot` |
| 2025-11-10 | Propagate slugs via enqueue helpers + worker bootstrap instead of touching every endpoint. | Centralizes instrumentation and ensures RQ jobs + subprocesses inherit context. | `@GitHub-Copilot` |
| 2025-11-10 | Build static symbol inventory via AST scan. | Coverage data alone can’t list untouched classes/functions; inventory fills that gap. | `@GitHub-Copilot` |

## Risks & Blockers

| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| Performance overhead slows playback beyond CI budget. | Medium | High | Capture baseline timings, add tracing feature flag, run heaviest profiles nightly/others weekly until optimized. |
| Artifact volume exceeds GitHub retention/quota. | Low | Medium | Compress JSON/HTML bundles, prune branch coverage, enforce 14-day retention, and gate optional artifacts behind `UPLOAD_FULL_REPORTS`. |
| RQ/subprocess work misses slug propagation leading to partial data. | Medium | Medium | Centralize helper APIs, add unit tests that assert slug presence, fail fast if tracing enabled but slug missing. |
| Coverage inventory drifts from source tree. | Medium | Medium | Add CI check (`wctl check-profile-coverage`) to regenerate + diff inventory; document workflow in AGENTS. |
| Flaky profiles produce incomplete nightly coverage. | Medium | Medium | Run aggregator only after successful playback jobs; retry failed profiles or mark coverage matrix entries with job status metadata. |
