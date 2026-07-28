# WATAR/Ash Controller Contract Tests

**Stable ID**: DOM-01
**Status**: Ready (2026-07-28 UTC)
**Timezone**: UTC

## Overview

Execute the first one-controller contract test pass against WATAR/Ash. Write
tests that exercise actual rendered fields and the existing browser, route,
persistence, RQ, and reload seams; patch only confirmed mismatches.

This package proves the controller-by-controller method. It does not build a
registry or enforcement platform.

## Objectives

- Identify the intended contract for each risk-bearing WATAR control.
- Test actual rendered `id`, submitted `name`, tokens, defaults, and selection.
- Trace submitted values through parsing, persisted state, RQ use when
  applicable, and reload.
- Reproduce the historical WATAR `id`/`name` mismatch with a regression test.
- Make the smallest backward-compatible patch for each confirmed mismatch.
- Record whether small reusable test helpers would reduce repeated assertions.

## Scope

### Included

- `wepppy/weppcloud/controllers_js/ash.js`.
- `wepppy/weppcloud/templates/controls/ash_pure.htm`.
- `wepppy/weppcloud/routes/nodb_api/watar_bp.py`.
- The directly used `Ash` NoDb and ash/WEPP RQ boundaries.
- Existing focused JavaScript, route, NoDb, microservice, and RQ tests.
- Actual-template render tests and concise intent/field matrices.

### Explicitly Out of Scope

- Ash science, formulas, defaults, units, thresholds, or model redesign.
- General shared-helper audits.
- New registries, manifests, indexes, diff engines, CI workflows, attestations,
  or dependency graphs.
- Unrelated controller cleanup or refactoring.

## Success Criteria

- [ ] The historical rendered-id/submitted-name mismatch is represented by a
  test that fails when reintroduced.
- [ ] Every field whose value can change a submitted payload, persisted/reloaded
  state, queued work, or visible workflow state has actual-render coverage for
  name, token, selected/default state, and relevant absence/disabled behavior;
  reviewed exclusions and their reasons are recorded.
- [ ] Persisted values have focused parser/save/reload evidence.
- [ ] RQ tests are added only for values or lifecycle behavior that cross the
  worker boundary.
- [ ] Every production change is preceded by a focused failing regression when
  practical and is limited to the confirmed mismatch.
- [ ] Existing applicable frontend and Python suites pass.
- [ ] One independent correctness review closes any production patch.

## Test Tooling Rule

Start with direct assertions. Extract a helper only when at least two tests
repeat the same logic and the helper is smaller and clearer than those
assertions. Tooling remains test-only and stateless.

## Dependencies

- GOV-00A must publish the concise one-controller test convention.
- Shared SHR packages and GOV-01 are not prerequisites.
- Parent:
  `docs/work-packages/20260716_pure_ui_contract_standardization_c/`

## Security and Parameterization

- **Initial security impact**: `none` for test and documentation additions.
- Re-triage before any production patch. A selector/name compatibility repair
  that preserves route authorization, upload handling, and queue behavior is
  low; attack-surface changes are high and require a dedicated review.
- **Parameterization change**: `no`; any such change leaves this package and
  requires an ADR.

## Estimate and Deliverables

- **Estimate**: one focused controller iteration, not a multi-week platform.
- Actual-render and downstream regression tests, minimal confirmed repairs,
  validation results, one correctness review when production changes, and a
  short tooling/value retrospective.
