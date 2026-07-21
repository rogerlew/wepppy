# PATH-CE v2: Jackson Model Resync, Parquet-Native Pipeline, Full UI + Reports

**Status**: Open (2026-07-20)
**Timezone**: UTC

## Overview

The vendored PATH Cost-Effective mod (`wepppy/nodb/mods/path_ce/`) is a stale port of Jackson Nakae's optimization model: it substitutes NTU for the outlet sediment discharge constraint, lacks contrast-group aggregation, has a divergent fallback-model constraint, and ships no threshold sweep or reports. Jackson's current codebase (`/workdir/PATH-cost-effective` @ `4e3b4a6`) adds all of these plus a Quarto HTML/PDF report pipeline, but consumes landscape-prefixed CSV exports. This package resyncs the vendored model to Jackson's current code, makes it consume wepppy's parquet artifacts directly (no CSV interchange, no backward compatibility with the existing vendored PATH-CE), reworks the UI to expose the full parameter contract, and links the generated reports from the run page.

Full delta analysis: [artifacts/2026-07-20_delta_assessment.md](artifacts/2026-07-20_delta_assessment.md).

## Objectives

- Vendored solver/data-prep/threshold-sweep match Jackson's `4e3b4a6` behavior (faithful extraction), reading `omni/*.parquet`, `watershed/hillslopes.parquet`, and `omni/contrast_id_definitions.psv` directly.
- RQ orchestration validates that user-provisioned Omni scenario and contrast artifacts satisfy PATH preconditions (contrasts are structurally required for the Sddc constraint; missing artifacts produce actionable errors), runs the model, runs the threshold sweep, and renders the HTML report into `<wd>/path/`. No Omni auto-provisioning.
- Run-page UI exposes every model parameter: both thresholds, slope range, burn-severity filter, and the per-treatment vectors (label, unit cost, quantity, fixed cost); results panel links the generated reports and download CSVs.
- Generated HTML report is viewable in-browser through a safe inline-serving path.
- Parameterization ADR records the NTU→Sddc constraint change, cost/unit contract, and default treatment vectors.

## Scope

### Included
- `wepppy/nodb/mods/path_ce/`: replace solver, data loader, presets; add threshold-sweep module and report-render service; keep `PathCostEffective` controller as config/status/results shell with expanded config schema.
- `wepppy/rq/path_ce_rq.py`: remove Omni auto-provisioning; precondition validation, sweep + render stages, status streaming.
- Vendored report assets: HTML QMD, `static/` JS/CSS, payload-JSON adaptation, output staging under `<wd>/path/report/`.
- Docker image: Quarto CLI + missing Python deps (plotly; highspy optional).
- Browse microservice: restricted inline-HTML serving for the report subtree (CSP/sandbox headers).
- `path_ce_bp.py`, `path_cost_effective_pure.htm`, `path_ce.js`: full parameter surface + report links.
- Tests (solver parity fixtures, data-prep goldens, route/UI contract), mod README, ADR.

### Explicitly Out of Scope
- Backward compatibility with the pre-v2 vendored PATH-CE config/artifacts (explicitly waived by Roger).
- Omni scenario/contrast provisioning — the user runs Omni before configuring PATH-CE (D3); PATH only validates.
- PDF report (D2): TinyTeX/typst toolchain deferred to a follow-up package.
- Threshold-sweep parallelization/optimization (D5): explicit follow-up work package.
- Generic untrusted-QMD sandbox service (`docs/dev-notes/qmd-reports-feature.spec.md`) — PATH QMDs are first-party; the sidecar remains a future option.
- Upstream fixes in Jackson's repo (unit findings are reported to him; we adapt at the vendoring seam).

## Implementation Fidelity and Evidence

- **Fidelity target**: `faithful extraction`
- **Authoritative source path(s)**: `/workdir/PATH-cost-effective` @ commit `4e3b4a6` — `PATH_CE.py`, `PATH_data_prep.py`, `PATH_plot.py`, `PATH_CE_Report_Universal.qmd`, `PATH_CE_Report_PDF.qmd`, `static/`
- **Cutover proof required**: end-to-end RQ run on a disturbed test watershed producing solver artifacts + rendered HTML report reachable from the run page (executional evidence, not fixture-only).
- **Acceptance evidence type**: `generated-output`

## Stakeholders

- **Primary**: Roger Lew (owner), Jackson Nakae (model author, upstream)
- **Executor**: Claude Code (explicitly assigned by Roger for this package; Codex MCP delegation at executor's discretion)
- **Reviewers**: Roger Lew
- **Security Reviewer**: required (inline HTML serving surface)
- **Informed**: PATH stakeholders via Roger

## Success Criteria

- [ ] Solver parity: vendored model reproduces Jackson's reference outputs on a shared fixture (selection sets, costs, final Sddc within tolerance).
- [ ] Pipeline consumes only wepppy-produced parquet/psv/geojson artifacts; no CSV staging step exists.
- [ ] RQ job validates Omni preconditions (actionable errors when artifacts missing) and runs model + sweep + report render with status streaming and failure states surfaced in UI.
- [ ] UI exposes all parameters listed in Objectives and round-trips them through config GET/POST.
- [ ] HTML report renders in-browser from the run page; download CSVs linked.
- [ ] ADR merged for solver-constraint and cost-unit contract changes.
- [ ] Security review artifact closed with no unresolved medium/high findings.
- [ ] `wctl run-pytest` targeted suites + `wctl run-npm lint && wctl run-npm test` pass.

## Parameterization ADR Gate

- **Parameterization change present**: `yes` (water-quality constraint NTU→Sddc; treatment cost/quantity/fixed-cost contract; threshold units; severity code map extension)
- **ADR required**: `yes`
- **ADR link(s)**: `docs/adrs/ADR-0023-path-ce-v2-parameterization.md` (Proposed; finalize at closure)
- **Decision provenance captured**: yes (D1–D5 ratification 2026-07-20; recorded in ADR-0023)

## Dependencies

- Omni scenario + contrast artifacts (user-provisioned; PATH validates and consumes).
- Docker image rebuild for Quarto/plotly (deploy coordination).
- D1–D5 ratified by Roger 2026-07-20 (see `tracker.md` Decisions). Remaining external item: confirm the upstream $/acre-vs-hectare cost basis with Jackson (D4 verification; ADR records our resolution either way).

## Security Impact Triage

`high` — adds a public route serving generated HTML inline from run directories (stored-XSS surface if not constrained), plus report-render execution in the worker. Dedicated security review artifact required: `artifacts/<date>_security_review.md` before closure. Mitigations planned: serve only the `path/report/` subtree, no path traversal beyond it, CSP sandbox / `Content-Security-Policy` headers, no session-credentialed fetches needed by report assets.

## Related

- Prior vendoring notes: `wepppy/nodb/mods/path_ce/integration_plan.md`, `implementation_plan.md` (superseded by this package)
- Quarto sandbox stub: `docs/dev-notes/qmd-reports-feature.spec.md`
- Upstream: https://github.com/jackson-nakae/PATH-cost-effective
