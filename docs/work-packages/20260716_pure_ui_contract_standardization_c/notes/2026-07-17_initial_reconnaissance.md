# Initial Pure UI Contract Reconnaissance

**Date**: 2026-07-17 UTC
**Mode**: Read-only
**Contributors**: primary agent plus two dispatched reconnaissance agents

## Confirmed Inventory Evidence

- `run_page_bootstrap.js.j2::createBootstrapEntries` contains 33 production
  controller registrations.
- `build_controllers_js.py::_collect_controller_modules()` currently selects 56
  bundled modules, including helpers, infrastructure, standalone controllers,
  GL adjuncts, and the 33 run-page domain entries. Bundle membership alone is
  therefore not the domain-contract population.
- `runs0_pure.htm` contains 26 main control-panel includes plus the power-user,
  disturbed, unitizer, and team supporting modal/panel includes.
- Batch Runner is a separate Pure UI surface under its own route templates and
  is not represented by the runs0 bootstrap population.
- Route-local archive dashboard, fork console, and run-sync dashboard templates
  are also outside the narrow global-template search and require explicit
  contract rows or exclusion rationales.
- The 33 bootstrap entries have dedicated controller source and Jest coverage,
  but most tests construct their own DOM fixtures. They do not prove that Jinja
  macros render the same ids, names, values, and hooks.
- `tests/weppcloud/routes/test_pure_controls_render.py` covers only a small subset
  of the 26 main panels. Its focused Ash assertion is the seam that the prior
  hand-authored `ash.test.js` fixture could not cover.
- `build_controllers_js.py` deliberately prefers GL implementations over several
  retained legacy controller files. Documentation and test selection can still
  point to a legacy suite, so production bundle membership must be confirmed for
  every row.

## Confirmed Documentation Drift

- `docs/ui-docs/controller-contract.md` is a useful shared lifecycle contract,
  not a per-controller payload/persistence contract.
- `docs/ui-docs/control-ui-styling/control-inventory.md` is dated 2025-10-22,
  contains open/TBD items, and omits newer controls even though the nearby
  `AGENTS.md` calls it complete and authoritative.
- Controller-specific snapshots are spread through
  `wepppy/weppcloud/controllers_js/README.md`, its `AGENTS.md`, domain READMEs,
  and archived modernization plans with inconsistent shapes.
- The Ash domain README and AGENTS file link to a missing current
  `docs/ui-docs/ash-control-plan.md`; the detailed form contract exists only in
  an archived 2025 work package.
- `_pure_macros.html` often defaults a submitted name from the DOM id. The
  standard must require separate id/name columns and rendered evidence rather
  than assume equality.

## Adopted Governance Recommendations

- Keep `docs/ui-docs/controller-contract.md` for shared invariants.
- Create `docs/ui-docs/contracts/README.md` as the normative schema, maintenance
  policy, and published coverage index.
- Create one controller contract per high-risk domain; allow a coherent family
  only when it shares one form/route lifecycle and test surface.
- Retain the old control inventory as historical discovery material and demote
  it from normative authority after the replacement index exists.
- Separate observed behavior, normative behavior, and confirmed discrepancy so
  an existing defect is not accidentally standardized.
- Require two independent reviewers: semantic end-to-end tracing and
  regression/QA/compatibility evidence.

## Reproduction Commands

```bash
rg -n 'add\("' wepppy/weppcloud/routes/run_0/templates/run_page_bootstrap.js.j2
rg -n "include 'controls/" wepppy/weppcloud/routes/run_0/templates/runs0_pure.htm
.venv/bin/python -c 'from wepppy.weppcloud.controllers_js.build_controllers_js import _collect_controller_modules; print("\n".join(_collect_controller_modules()))'
rg --files wepppy/weppcloud/controllers_js/__tests__
rg -n 'ash-control-plan|controller-contract|control-inventory' docs wepppy
rg -l 'controls/_pure_macros.html' wepppy/weppcloud
rg --files wepppy/weppcloud/routes | rg 'templates/.*(pure|console|dashboard)'
```

The final Milestone 1 inventory must use deterministic extraction and reconcile
configuration gates; these reconnaissance counts are a baseline, not the final
coverage claim.
