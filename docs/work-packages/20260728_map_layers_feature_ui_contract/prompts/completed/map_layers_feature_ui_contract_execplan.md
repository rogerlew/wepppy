# Execute DOM-04B Map Layers and Feature UI Contract Audit

This ExecPlan is a living document. Maintain it under
`docs/prompt_templates/codex_exec_plans.md`.

## Purpose / Big Picture

This package proves that the actual Map template and the Map helper modules
agree on layer defaults, legend hosts, scale behavior, and accessible feature
presentation. It is a direct regression pass, not a Map redesign.

## Progress

- [x] (2026-07-28 UTC) Scoped DOM-04B and recorded its rendered/helper matrix.
- [x] Added actual-render state evidence; focused Python (72 passed), lint, and
  Map Jest (38 passed) conform.
- [x] Closed with no production patch; full frontend results recorded below.

## Surprises & Discoveries

- Observation: Existing Map Jest covers interactive helper behavior, but it
  builds its own DOM and cannot prove template-generated defaults.

## Decision Log

- Decision: Add one actual-render default-state test and retain existing helper
  tests rather than extract a helper.
  Rationale: The repeated direct checks are short and readable.
  Date/Author: 2026-07-28 / Codex

## Outcomes & Retrospective

DOM-04B closed without a production repair. One actual-render test protects
the template-generated SBS toggle/default colormap/legend contract; existing
Map Jest tests protect layer ordering, SBS presentation, scale, and accessible
feature UI. No helper was extracted and no route/resource boundary changed.
Focused Python (72 tests), lint, focused Map Jest (38 tests), and the full
frontend suite (88 suites, 662 tests) passed.

## Context and Orientation

`map_pure_gl.htm` renders SBS and subcatchment controls. `map_gl_layer_control.js`,
`map_gl_scale_control.js`, and `map_gl_feature_ui.js` own their presentation;
`map_gl_shared.js` supplies shared utility behavior. DOM-04A already owns Map
orchestration. No DOM-04B action persists data or reaches RQ.

## Plan of Work

Add actual Jinja render assertions for the SBS toggle, default colormap option,
and legend hosts. Run the existing Map Jest suite, which covers layer ordering,
scale units, legends, and feature-modal accessibility. Make no production
change unless a new direct regression proves a mismatch.

## Concrete Steps

From `/home/workdir/wepppy`, run:

    wctl run-pytest tests/weppcloud/routes/test_pure_controls_render.py --maxfail=1
    wctl run-npm lint
    wctl run-npm test -- map_gl
    wctl run-npm test
    wctl doc-lint --path docs/work-packages/20260728_map_layers_feature_ui_contract

## Validation and Acceptance

Focused Python must prove actual markup. Map Jest must prove helper behavior.
The full frontend suite must pass after JavaScript test changes. Controller
build, RQ graph validation, and production/security review are not required
unless production source changes.

## Idempotence and Recovery

Tests and docs are repeatable. Narrow any mismatch repair to the demonstrated
template/helper seam; do not change remote resource or route behavior.
