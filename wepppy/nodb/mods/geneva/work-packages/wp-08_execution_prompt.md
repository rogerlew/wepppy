# WP-08 Execution Prompt: Routes, Tasks, RQ Wiring, Query/Report API

Use this prompt verbatim in a new Codex/Copilot session to execute WP-08.

---

Execute WP-08 end-to-end for Geneva and close the package.

Authoritative docs:
- `/workdir/wepppy/wepppy/nodb/mods/geneva/implementation-plan.md`
- `/workdir/wepppy/wepppy/nodb/mods/geneva/specification.md`
- `/workdir/wepppy/wepppy/nodb/mods/geneva/work-packages/wp-07_cn_table_workflow_edit_csv_integration.md`
- `/workdir/wepppy/wepppy/nodb/mods/geneva/work-packages/wp-08_routes_tasks_rq_wiring_query_report_api.md`
- `/workdir/wepppy/docs/standards/nodb-facade-collaborator-pattern.md`
- `/workdir/wepppy/docs/schemas/rq-response-contract.md`
- `/workdir/wepppy/docs/schemas/weppcloud-csrf-contract.md`

Scope (must complete):
1. Implement remaining Geneva route family and contracts from spec section `Expected route family`:
   - `GET|POST /runs/<runid>/<config>/api/geneva/config`
   - `POST /runs/<runid>/<config>/tasks/geneva/prepare_hrus`
   - `POST /runs/<runid>/<config>/tasks/geneva/build_frequency_panel`
   - `POST /runs/<runid>/<config>/tasks/geneva/run_batch`
   - `GET /runs/<runid>/<config>/api/geneva/status`
   - `GET /runs/<runid>/<config>/api/geneva/results`
   - `GET /runs/<runid>/<config>/api/geneva/frequency_panel`
   - `GET /runs/<runid>/<config>/query/geneva/summary`
   - `GET /runs/<runid>/<config>/report/geneva/summary`
   - Preserve WP-07 CN-table endpoints and contracts.
2. Wire task endpoints to RQ with canonical submission envelopes (`job_id`, `status_url`) and canonical error envelopes.
3. Enforce run-scope auth and CSRF/session contract expectations at route/task boundaries.
4. Update queue dependency catalog and route wiring artifacts when queue wiring changes.
5. Add/extend tests for:
   - route payload schema and enum-ID conformance,
   - RQ submission/status/result contracts,
   - `completed_with_gaps` status lifecycle,
   - query/report payload shape parity,
   - WBT/US guard propagation at route level (NoDb-origin error propagation only).
6. Complete QA + security review workflow and resolve all fix-now findings.
7. Update WP-08 evidence and implementation-plan row to done only after all criteria pass.

Required gates:
- `cd /workdir/wepppy && wctl run-pytest tests/nodb/mods/geneva --maxfail=1`
- `cd /workdir/wepppy && wctl run-pytest tests/nodb --maxfail=1`
- `cd /workdir/wepppy && wctl run-pytest tests --maxfail=1`
- `cd /workdir/wepppy && wctl doc-lint --path wepppy/nodb/mods/geneva`
- `cd /workdir/wepppy && python3 tools/check_broad_exceptions.py --enforce-changed --base-ref origin/master`
- `cd /workdir/wepppy && wctl check-rq-graph` (required if queue wiring changes)

UI gates (required if frontend assets/templates/js are touched):
- `cd /workdir/wepppy && wctl run-npm lint`
- `cd /workdir/wepppy && wctl run-npm test`

Mandatory review workflow:
- Code review
- QA review
- Security review
- Resolve fix-now findings before closeout

Evidence updates required:
- `/workdir/wepppy/wepppy/nodb/mods/geneva/work-packages/wp-08_routes_tasks_rq_wiring_query_report_api.md`
- `/workdir/wepppy/wepppy/nodb/mods/geneva/implementation-plan.md` (WP-08 row state/gates/evidence link)

Constraints:
- Do not modify `wepppy/weppcloud/routes/usersum/generated/docs_index.json`.
- Ignore unrelated dirty files outside Geneva/WP-08 scope.
- Do not broaden scope into WP-09+.

---
