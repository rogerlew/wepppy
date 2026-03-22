# RUSLE NoDb + Run-Page UI Integration

**Status**: Completed (2026-03-21)

## Overview
This package implemented Milestones 6-7 from `wepppy/nodb/mods/rusle/specification.md`: full `Rusle` NoDb orchestration, RQ-backed build execution, run-header mod toggles, run-page UI controls, preflight/task integration, stale invalidation wiring, and closure artifacts.

## Objectives
- Ship a `Rusle` NoDb controller that composes existing LS/K/C integrations and writes final `A = R * K * LS * C * P` artifacts.
- Expose `rusle` as a disturbed-gated optional mod in the run-header Mods menu and dynamic run-page sections.
- Keep enabling/disabling `rusle` registration-only (no automatic build), with build execution strictly through RQ.
- Enforce locked v1 user contracts:
  - default `c_mode = observed_rap`
  - `scenario_sbs` remains independent of Disturbed runtime burn toggles
  - `scenario_sbs` without SBS map uses unburned parameters and does not emit synthetic `sbs_4class.tif`
  - RAP year options sourced from the RAP implementation surface used by `rap.py`
  - no user-facing POLARIS section
- Ensure `rusle` auto-checks POLARIS alignment requirements and passes explicit payloads when acquisition is needed.
- Integrate dedicated `TaskEnum` + preflight checklist entry (`🔱`) and stale invalidation on climate/SBS changes.

## Included Scope
- New `Rusle` NoDb facade under `wepppy/nodb/mods/rusle/`.
- New RQ worker + rq-engine `build-rusle` route.
- Run-page control section/controller wiring and mod-toggle reveal behavior.
- Preflight TaskEnum/checklist/TOC integration and stale invalidation.
- Focused tests across nodb, rq-engine, WEPPcloud routes/templates/controllers, and preflight services.
- Review, QA, and validation artifacts under this package.

## Deliverables
- `wepppy/nodb/mods/rusle/rusle.py` (new controller).
- Rusle run-page control section + controller JS + mod toggle wiring.
- `build-rusle` rq-engine endpoint and `build_rusle_rq` worker task.
- Preflight checklist + TaskEnum + TOC/selector mappings.
- Test additions/updates across `tests/nodb`, `tests/microservices`, `tests/weppcloud`, and `services/preflight2`.
- `artifacts/milestone4_review.md`
- `artifacts/milestone5_qa_review.md`
- `artifacts/final_validation_summary.md`

## Success Criteria
- [x] Full Rusle build runs asynchronously through RQ and produces final `A` output.
- [x] Mode-specific artifacts are primary outputs; build writes only selected-mode `K`/`C` outputs.
- [x] `rusle` UI appears after WEPP and follows standard status + stacktrace behavior.
- [x] Disturbed-gated mod eligibility and dynamic reveal/hide behavior work end-to-end.
- [x] POLARIS auto-acquisition contract implemented with explicit payload and drift/missing handling.
- [x] Preflight `rusle` task (`🔱`) integrated and stale invalidation works for climate/SBS changes.
- [x] Review and QA artifacts contain no unresolved high/medium findings.
- [x] Required validation gates pass before closeout.

## Closeout Notes
- Final full-suite validation: `wctl run-pytest tests --maxfail=1` passed (`2443 passed, 34 skipped`).
- Route-contract freeze artifacts were synchronized to include the new agent-facing `build-rusle` endpoint.
- Package tracker and ExecPlan were closed and archived; root trackers/spec were synchronized.

## References
- `wepppy/nodb/mods/rusle/specification.md`
- `docs/ui-docs/control-ui-styling/preflight_behavior.md`
- `docs/prompt_templates/codex_exec_plans.md`
