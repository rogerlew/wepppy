# WP-09 Execution Prompt: End-to-End Integration and Performance Validation

Use this prompt verbatim in a new Codex/Copilot session to execute WP-09.

---

Execute WP-09 end-to-end for Geneva and close the package.

Authoritative docs:
- `/workdir/wepppy/wepppy/nodb/mods/geneva/implementation-plan.md`
- `/workdir/wepppy/wepppy/nodb/mods/geneva/specification.md`
- `/workdir/wepppy/wepppy/nodb/mods/geneva/work-packages/wp-08_routes_tasks_rq_wiring_query_report_api.md`
- `/workdir/wepppy/wepppy/nodb/mods/geneva/work-packages/wp-09_end_to_end_integration_and_performance_validation.md`

Scope (must complete):
1. Implement/extend WP-09 validation harnesses to cover end-to-end scenario matrix:
   - no-burn vs burn-severity inputs,
   - CLIGEN-only vs dual-source (NOAA+CLIGEN),
   - mixed available/unavailable matrix cells and `completed_with_gaps` lifecycle.
2. Add/extend runtime/performance profiling for representative panel/watershed sizes and record explicit baselines/evidence.
3. Add collapsed-vs-uncollapsed end-to-end sensitivity checks:
   - default `allow_cross_hsg_merge=false`: runoff depth `<= 2%`, runoff volume `<= 2%`, peak discharge `<= 5%`.
   - `allow_cross_hsg_merge=true`: runoff depth `<= 2%`.
4. Validate watershed-size warning thresholds (`warning`, `severe`, `extreme`) and ensure warnings propagate through results/query/report surfaces.
5. Keep scope bounded to WP-09 validation/performance readiness; do not broaden into WP-10 release closeout.
6. Complete code review, QA review, and security review; resolve all fix-now findings.
7. Update WP-09 evidence and implementation-plan row to `done` only after all required gates and manual checks pass.

Required gates (`/workdir/wepppy`):
- `cd /workdir/wepppy && wctl run-pytest tests/nodb/mods/geneva --maxfail=1`
- `cd /workdir/wepppy && wctl run-pytest tests/nodb --maxfail=1`
- `cd /workdir/wepppy && wctl run-pytest tests --maxfail=1`
- `cd /workdir/wepppy && wctl doc-lint --path wepppy/nodb/mods/geneva`
- `cd /workdir/wepppy && python3 tools/check_broad_exceptions.py --enforce-changed --base-ref origin/master`
- `cd /workdir/wepppy && wctl check-rq-graph` (required only if queue wiring changes)

If `wepppyo3` is touched:
- `cd /workdir/wepppyo3 && cargo test -p geneva_core`
- `cd /workdir/wepppyo3 && cargo test -p cli_revision`
- `cd /workdir/wepppyo3 && cargo fmt --check`
- `cd /workdir/wepppyo3 && cargo clippy --all-targets -- -D warnings`

UI gates (only if frontend/templates/js touched):
- `cd /workdir/wepppy && wctl run-npm lint`
- `cd /workdir/wepppy && wctl run-npm test`

Mandatory review workflow:
- Code review
- QA review
- Security review
- Resolve fix-now findings before closeout

Evidence updates required:
- `/workdir/wepppy/wepppy/nodb/mods/geneva/work-packages/wp-09_end_to_end_integration_and_performance_validation.md`
- `/workdir/wepppy/wepppy/nodb/mods/geneva/implementation-plan.md` (WP-09 row state/gates/evidence link)

Manual integration evidence required:
- Run the full Geneva flow on at least two real run directories, including one noisy `hydgrpdcd` run.
- Record performance/profiling evidence with workload definition, command, and observed runtime.
- Record warning-threshold evidence and query/report consistency observations.

Constraints:
- Do not modify `wepppy/weppcloud/routes/usersum/generated/docs_index.json`.
- Ignore unrelated dirty files outside Geneva/WP-09 scope.
- Do not broaden scope into WP-10.

---
