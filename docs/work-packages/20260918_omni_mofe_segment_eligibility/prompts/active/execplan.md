# Repair Omni treatment selection for MOFE segments

This living plan follows `docs/prompt_templates/codex_exec_plans.md`.

## Purpose / Big Picture

An eligible forest or burned segment must receive its requested Omni treatment
even if its hillslope's dominant class is ineligible. A MOFE hillslope contains
several overland flow elements, each with its own management assignment.

## Progress

- [x] (2026-09-18) Confirm scalar prefilter in all three treatment branches.
- [x] Commit reviewed contract checkpoint (`df504d8f6`).
- [x] Implement segment-based candidate selection and failing regressions.
- [x] (2026-09-18) Restart local Forest and dispatch six saved scenarios;
  job `8c88742d-defd-4b3e-ac33-a3efd622dd42`, awaiting completion notification.
- [ ] Validate generated/prepared inputs, focused and broad tests, independent review.
- [ ] Close package with retained evidence and outstanding audit dispositions.
- [x] Fix user-reported channel selection in Modify Landuse under the unchanged
  selected-hillslope contract; frontend/render gates and independent review pass.
- [x] Complete full six-scenario generated/prepared management and soil readback:
  455 hillslopes per scenario, zero failures.
- [x] Verify user's manual low-severity 260803 rerun: all artifact checks pass;
  current manual/Omni numeric summaries agree. Compare 447 unchanged-input
  hillslopes against dcc52a6 to assess executable-associated sediment differences.
- [x] (2026-09-18 19:42 UTC) Disposition low/prescribed-fire failures as
  model-output overflow plus Rust map-reader panic; full-model acceptance blocked.
- [x] (2026-09-18 20:03 UTC) User-authorized stop of remaining jobs, artifact
  preservation, and all-six rerun with `wepp_260803`; replacement job
  `ef226e0f-a5f7-4daf-bee6-9db5f420c7aa`, awaiting results.
- [x] Verify all six 260803 leaves and finalizers finished, no plot overflow,
  and generated/prepared management covers match all six mixed hillslopes in
  prescribed fire and both thinning treatments.
- [x] Compare new Omni outputs to verified manual summaries with the user's
  acknowledged mixed-binary caveat; fire runoff passes 20%, sediment fails,
  and full cross-workflow ordering differs around thinning.

## Surprises & Discoveries

The prior audit never paired manual scenario outputs; its 20% and rank claims
must not be treated as proof. Existing Treatments already loops over OFEs.

Forest low/prescribed-fire outputs contain asterisk overflow fields; the Rust
soil-loss map reader panics on them. Low also has overflow in its loss report,
so merely relaxing map parsing is not a scientifically valid recovery.

## Decision Log

2026-09-18: Fix the outer gate for all three treatment branches because they
share the same demonstrated failure. Keep existing segment treatment semantics,
single-OFE behavior and hillslope masks. The user authorized segment eligibility.

2026-09-18: Preserve failed-run evidence and block numerical acceptance rather
than retry unchanged inputs or suppress invalid cells. Numerical/model diagnosis
and contextual Rust reader errors are separately scoped remediation; see
`artifacts/forest_failure_disposition.md` for exact jobs and reproduction leads.

2026-09-18: User selected `wepp_260803` for the replacement six-scenario batch.
Change only the local project binary, preserve old artifacts and treatment
settings, and invalidate reuse. Baseline outputs are not rerun by this request.

User subsequently requested the mixed-binary comparison without rerunning manual
projects. Retain it as a descriptive comparison, not causal attribution or a
matched-parameter acceptance gate; see `artifacts/manual_comparison_260803.md`.

## Outcomes & Retrospective

Implementation and 72 focused regressions pass; independent review passed.
Broad suite was interrupted by the requested stack restart and remains pending.
Local Forest actual-project validation has two output-parsing failures and is
not accepted; their cause/disposition is retained in the failure artifact.
The subsequent 260803 batch completed all six scenarios and mixed-segment
management acceptance passes. Comprehensive soil/manifests audit and broad
regressions remain pending; no matched-binary manual comparison is claimed.
No production deployment or result parity claim yet.

## Context and Orientation

`wepppy/nodb/mods/omni/omni_mode_build_services.py` chooses candidate hillslopes.
`wepppy/nodb/mods/treatments/treatments.py` applies each treatment to eligible
segments and rebuilds managements/soils. `tests/nodb/mods/` covers both components;
`tests/nodb/test_mofe_scenario_artifacts.py` parses real combined/prepared inputs.

## Plan of Work

First commit the approved contract after two independent reviews. Then add a
small candidate predicate using segment assignments in MOFE mode. Keep scalar
rules in single-OFE mode and existing application logic. Test all treatment
branches and mixed segments; do not change cover values or soil lookup tables.
Finally run focused and broad checks, review, and record limitations.

## Concrete Steps

From `/home/workdir/wepppy`, run `wctl run-pytest
tests/nodb/mods/test_omni_mode_build_services.py
tests/nodb/mods/test_treatments_build.py tests/nodb/test_mofe_scenario_artifacts.py`.
Run `wctl run-pytest tests --maxfail=1`, changed-file broad-exception enforcement,
and `wctl doc-lint --path` for touched Markdown. Record failures honestly.

## Validation and Acceptance

Mixed hillslopes must reach the real segment application loop. Parse generated
combined managements and prepared WEPP managements to prove eligible segments
changed while ineligible neighbors did not. Existing scalar/filter cases pass.
This establishes code/input correction, not refreshed production model outputs.
Actual-project Forest acceptance remains a separate required release gate;
record it as pending until executed, even when local implementation passes.

## Idempotence and Recovery

Tests use temporary projects. Revert the focused code commit to undo the change;
historical scenarios require an explicit supported rebuild to acquire new inputs.

## Artifacts and Notes

Retain contract review, validation results and review dispositions in `artifacts/`.

## Interfaces and Dependencies

Reuse existing NoDb controllers and management parsers; no new dependency,
persisted field, API, numerical parameter, or queue edge is required.
