# Repair shared MOFE Disturbed soil source selection

This ExecPlan is a living document. The sections `Progress`, `Surprises &
Discoveries`, `Decision Log`, and `Outcomes & Retrospective` must remain current.
Maintain it according to `docs/prompt_templates/codex_exec_plans.md`.

## Purpose / Big Picture

Users must be able to run ordinary Disturbed and Omni treatment scenarios through
one shared multiple-overland-flow-element (MOFE) soil producer. After this repair,
a second invocation will rebuild each ordered segment from its retained original
single-OFE soil, apply the current segment management class, and publish a valid
combined soil instead of feeding an already-combined MOFE soil back into the
synthesizer.

The observable proof is a focused regression that performs an initial Disturbed
MOFE build, changes segment treatment assignments, invokes the same producer
again, and parses both the combined and prepared WEPP soil inputs. The full test
suite is explicitly excluded by operator direction.

## Progress

- [x] (2026-11-16 00:38 UTC) Diagnose the production failure and confirm the
  ordinary base artifacts are correctly parameterized by segment.
- [x] (2026-11-16 00:38 UTC) Scaffold the work package and record the conformance
  scope.
- [x] (2026-11-16 00:55 UTC) Implement stable source selection in the shared
  producer, including ESDAC quality-key consistency.
- [x] (2026-11-16 00:55 UTC) Add direct unmocked generated-artifact regression
  coverage for repeated mixed-class generation and preparation.
- [x] (2026-11-16 00:55 UTC) Run focused tests and changed-file checks; scoped
  documentation lint is recorded at package closure.
- [x] (2026-11-16 00:55 UTC) Complete correctness review and close the local
  code-delivery package.

## Surprises & Discoveries

- Observation: the validation added on November 2 exposed an older caller defect
  instead of introducing the malformed state.
  Evidence: `SoilMultipleOfeSynth.write()` rejects a stack member whose declared
  OFE count is not one, while the failing caller selects `hill_*.mofe.sol` from
  the current published mapping.
- Observation: `innovative-tailor` retains two useful assignment views.
  Evidence: `domsoil_d` contains generated `hill_*.mofe` keys and
  `ssurgo_domsoil_d` contains the original soil keys.
- Observation: ESDAC quality coverage also consumes the selected source key.
  Evidence: resolving the source once before validation keeps quality identity
  and component generation consistent on repeated builds.

## Decision Log

- Decision: classify this as a conformance fix to unchanged MOFE identity and
  Disturbed lookup contracts.
  Rationale: the contracts already require one source per final OFE and
  per-segment class/texture resolution; no scientific behavior is changing.
  Date/Author: 2026-11-16 / Codex.
- Decision: repair `Disturbed.modify_mofe_soils()` rather than add an Omni branch.
  Rationale: both ordinary and Omni flows already call this producer, and one
  implementation prevents lookup drift.
  Date/Author: 2026-11-16 / Operator and Codex.
- Decision: do not run the full suite.
  Rationale: explicit operator direction; focused direct-artifact evidence is the
  relevant acceptance gate.
  Date/Author: 2026-11-16 / Operator.

## Outcomes & Retrospective

The shared producer now distinguishes clean source assignments from its own
published MOFE outputs and recovers the retained single-OFE source only for the
latter. Existing segment ordering, class/texture lookup, writer behavior,
transaction rollback, and public interfaces remain unchanged. A real-writer
regression proves that repeated mixed-class generation produces three
single-OFE components, a valid combined soil, and an equivalent prepared input.

Focused validation passed: the final affected-boundary run reported 34 passes,
an earlier adjacent run reported 134 passes, broad-exception enforcement passed,
and no full-suite run was attempted. The highest supported claim is locally
validated code delivery; deployment and production-run recovery are outside
this package.

## Context and Orientation

`wepppy/nodb/mods/disturbed/disturbed.py` owns
`Disturbed.modify_mofe_soils()`. The method currently reads each hillslope soil
key from `Soils.domsoil_d`, produces class-specific single-OFE component files,
and combines them with `SoilMultipleOfeSynth`. On a clean soil build,
`domsoil_d` points at an original single-OFE soil and the logic is correct. After
publication, the method replaces each value with a generated key such as
`hill_101.mofe`. A later treatment or Omni call therefore selects the combined
output as its source.

`Soils.ssurgo_domsoil_d` is the existing retained assignment used for source soil
metrics. Supported builders populate it before the Disturbed completion hook,
and the incident run retains original source keys there. `Soils.soils` retains
the corresponding original `SoilSummary` objects when generated MOFE summaries
are added.

`Landuse.domlc_mofe_d` is the ordered mapping from hillslope and segment ID to a
management key. The existing producer sorts numeric segment IDs, obtains each
management's `disturbed_class`, combines it with the source texture for lookup,
and writes components in that order. Preserve that logic.

## Plan of Work

First, add a narrow helper in `disturbed.py` that resolves the stable source soil
key for one hillslope. Prefer the retained source assignment when it exists and
references a known `SoilSummary`. Preserve the current assignment for a clean
first build. If the current assignment is generated MOFE state and no usable
retained source exists, fail before writing with actionable rebuild guidance.

Second, route the existing `modify_mofe_soils()` planning loop through that
helper. Do not copy or branch the segment lookup for Omni. Keep output keys,
lookup policy, transaction rollback, and final publication unchanged.

Third, extend focused tests. Unit tests must cover clean state, populated legacy
published state, and malformed published state. A direct integration test must
use real soil writers to build a mixed-class MOFE, invoke the same producer again
after changing assignments, prepare the WEPP input, and parse expected OFE count,
order, and parameters.

Finally, update `wepppy/nodb/mods/disturbed/README.md`, complete the work-package
evidence and correctness review, and run only scoped tests and documentation
checks.

## Concrete Steps

Work from `/workdir/wepppy`.

Inspect the patch after each milestone:

    git diff -- wepppy/nodb/mods/disturbed/disturbed.py \
      tests/nodb/mods/disturbed docs/work-packages/20261115_omni_mofe_disturbed_soil_repair

Run focused tests:

    wctl run-pytest tests/nodb/mods/disturbed/test_modify_soils_mofe.py
    wctl run-pytest tests/nodb/mods/disturbed/test_treatment_soil_artifacts.py
    wctl run-pytest tests/nodb/mods/test_treatments_build.py \
      tests/nodb/test_mofe_scenario_artifacts.py

Run changed-file checks and documentation lint:

    python3 tools/check_broad_exceptions.py --enforce-changed --base-ref origin/master
    wctl doc-lint --path docs/work-packages/20261115_omni_mofe_disturbed_soil_repair
    wctl doc-lint --path wepppy/nodb/mods/disturbed/README.md

Do not run `wctl run-pytest tests --maxfail=1`.

## Validation and Acceptance

Acceptance requires the new regression to fail against the pre-change source with
the exact one-OFE stack-member exception and pass after the repair. Parsed
combined and prepared soil files must have the same OFE count and ordered
class-specific parameter values as `landuse.domlc_mofe_d`. Repeating the producer
must use retained original sources and must not compound a multiplier-based
replacement.

Existing focused Disturbed and Treatments tests must pass. Documentation lint
must pass for changed documents. No completion claim may exceed locally validated;
deployment and `innovative-tailor` recovery remain separate.

## Idempotence and Recovery

The implementation must be safe to retry because the source resolver never
selects a generated MOFE output as a component source. The existing disturbed
soil transaction remains responsible for filesystem and in-memory rollback.
Tests use disposable directories. Do not mutate production artifacts during
candidate validation.

## Artifacts and Notes

Retain concise test output and semantic readback results under the work package's
`artifacts/` directory only when they add evidence beyond the test source. The
correctness review records the final evidence matrix.

## Interfaces and Dependencies

Keep the public `Disturbed.modify_mofe_soils() -> None` interface unchanged. Add
only a private resolver with explicit string keys and clear error behavior. Reuse
`Soils.domsoil_d`, `Soils.ssurgo_domsoil_d`, `Soils.soils`, `WeppSoilUtil`, and
`SoilMultipleOfeSynth`; introduce no external dependency or new service.

Plan revision note: created 2026-11-16 to execute the operator-authorized shared
producer conformance repair with focused validation only. Completed 2026-11-16
after adding ESDAC-consistent source resolution, direct artifact evidence, and a
bounded correctness review.
