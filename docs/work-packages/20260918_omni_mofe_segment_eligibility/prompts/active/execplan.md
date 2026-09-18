# Repair Omni treatment selection for MOFE segments

This living plan follows `docs/prompt_templates/codex_exec_plans.md`.

## Purpose / Big Picture

An eligible forest or burned segment must receive its requested Omni treatment
even if its hillslope's dominant class is ineligible. A MOFE hillslope contains
several overland flow elements, each with its own management assignment.

## Progress

- [x] (2026-09-18) Confirm scalar prefilter in all three treatment branches.
- [ ] Commit reviewed contract checkpoint.
- [ ] Implement segment-based candidate selection and failing regressions.
- [ ] Validate generated/prepared inputs, focused and broad tests, independent review.
- [ ] Close package with retained evidence and outstanding audit dispositions.

## Surprises & Discoveries

The prior audit never paired manual scenario outputs; its 20% and rank claims
must not be treated as proof. Existing Treatments already loops over OFEs.

## Decision Log

2026-09-18: Fix the outer gate for all three treatment branches because they
share the same demonstrated failure. Keep existing segment treatment semantics,
single-OFE behavior and hillslope masks. The user authorized segment eligibility.

## Outcomes & Retrospective

Pending implementation. No production deployment or result parity claim yet.

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
