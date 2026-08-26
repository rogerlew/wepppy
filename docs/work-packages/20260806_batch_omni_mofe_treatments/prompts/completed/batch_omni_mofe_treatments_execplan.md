# Propagate Batch OMNI treatments through multi-OFE WEPP inputs

This ExecPlan is a living document. The sections `Progress`, `Surprises &
Discoveries`, `Decision Log`, and `Outcomes & Retrospective` must be kept current
as work proceeds. Maintain this document in accordance with
`docs/prompt_templates/codex_exec_plans.md`.

## Purpose / Big Picture

After this change, a Batch Runner project configured for multiple overland flow
elements (multi-OFE) can run OMNI thinning and prescribed-fire scenarios whose
canopy and ground-cover treatments reach the actual WEPP management files.
Operators can verify this by comparing an undisturbed generated
`wepp/runs/p<id>.man` with its treated counterpart and observing treatment cover
values in the eligible OFE segments while unrelated segments remain unchanged.

## Progress

- [x] (2026-08-06 19:26 UTC) Confirmed the production failure boundary.
- [x] (2026-08-06 19:30 UTC) Scaffolded the work package and active ExecPlan.
- [x] (2026-08-06 19:45 UTC) Added regression coverage for multi-OFE mappings and generated
  management files before the fix.
- [x] (2026-08-06 19:43 UTC) Implemented segment-aware treatment propagation and rebuilt dependent
  multi-OFE artifacts.
- [x] (2026-08-06 19:48 UTC) Updated durable Batch Runner documentation.
- [x] (2026-08-06 20:05 UTC) Ran targeted, NoDb, and full repository validation gates.
- [x] (2026-08-06 20:05 UTC) Closed the package and archived this ExecPlan with outcomes.

## Surprises & Discoveries

- Observation: Treatment selection and scalar mutation succeed in production,
  but the multi-OFE representation remains undisturbed.
  Evidence: for production hillslope `1001`, thinning changes `domlc_d` from
  `42` to `124` or `128`, and prescribed fire changes it to `110`, while every
  `domlc_mofe_d` segment remains `42`.

- Observation: Multi-OFE WEPP preparation does not consume scalar `domlc_d`.
  Evidence: `wepppy/nodb/core/wepp.py` copies
  `landuse/hill_<topaz_id>.mofe.man` into `wepp/runs/p<wepp_id>.man`.

## Decision Log

- Decision: Treat each OFE from its own management class rather than copying the
  scalar hillslope treatment result across all OFEs.
  Rationale: Multi-OFE hillslopes can be heterogeneous; blanket replacement
  would silently destroy valid shrub, grass, or other unaffected segments.
  Date/Author: 2026-08-06 / Codex

- Decision: Keep treatment parameters unchanged.
  Rationale: This is propagation repair, not parameterization; an ADR is not
  required.
  Date/Author: 2026-08-06 / Codex

## Outcomes & Retrospective

The package achieved faithful, wired multi-OFE treatment propagation. Selected
OFE segments now receive thinning, prescribed-fire, or mulch management keys
according to their own land-cover class; unrelated segments remain unchanged.
The implementation rebuilds synthesized multi-OFE management and disturbed-soil
artifacts before WEPP preparation. Generated-output coverage proves the treated
management reaches `wepp/runs/p<wepp_id>.man`.

Validation completed with 33 focused tests passing, 1,559 NoDb tests passing
with 26 skipped, and the final full repository gate passing 5,895 tests with 61
skipped and 12 passing subtests. Production deployment and rebuilding the
affected run remain separate operator actions.

## Context and Orientation

An overland flow element (OFE) is one segment of a WEPP hillslope with its own
land cover, management, and soil properties. In single-OFE mode,
`Landuse.domlc_d` maps each hillslope to one management key. In multi-OFE mode,
`Landuse.domlc_mofe_d` additionally maps every segment within a hillslope to its
own management key, and `Landuse._build_multiple_ofe()` synthesizes one
`landuse/hill_<topaz_id>.mofe.man` file from those segments.

`wepppy/nodb/mods/omni/omni_mode_build_services.py` selects hillslopes for OMNI
treatments and calls `Treatments.build_treatments()`.
`wepppy/nodb/mods/treatments/treatments.py` currently changes only the scalar
`domlc_d`. `wepppy/nodb/core/wepp.py` takes the multi-OFE path and copies the
already-synthesized `hill_*.mofe.man`, so the scalar mutation never reaches WEPP.

The compatibility requirement is additive: single-OFE behavior remains
unchanged. For multi-OFE hillslopes selected by OMNI, apply the treatment to each
eligible segment according to that segment's current disturbed class; preserve
ineligible segments. Then regenerate the multi-OFE management and soil artifacts
before WEPP preparation.

## Plan of Work

First, extend the existing treatment unit tests with a heterogeneous multi-OFE
hillslope. The test must show that forest segments receive thinning or
prescribed-fire keys, non-forest segments remain unchanged, and the scalar
mapping retains its existing behavior.

Next, introduce the smallest segment-aware mutation seam in
`wepppy/nodb/mods/treatments/treatments.py`. Reuse existing treatment-specific
eligibility and mapping logic rather than duplicating treatment parameters.
Persist both scalar and multi-OFE dictionaries within the existing Landuse lock.
Regenerate the treatment-dependent soil and synthesized management artifacts
using existing Landuse and Soils APIs under their established directory-root
locks.

Then add generated-output evidence. Exercise the multi-OFE synthesis and WEPP
preparation path in a focused fixture and assert that the resulting
`wepp/runs/*.man` contains treated canopy and ground-cover values. Assert that
the undisturbed fixture remains different and that ineligible segments retain
their original management.

Finally, update `wepppy/nodb/README.batch-runner.md`, run targeted tests, broad
NoDb tests, full tests, code-quality checks, and Markdown lint. Record results in
this plan and the package tracker before closing the package.

## Concrete Steps

Work from `/home/workdir/wepppy`.

Run the focused tests during iteration:

    wctl run-pytest tests/nodb/mods/test_treatments_build.py tests/nodb/mods/test_omni_mode_build_services.py --maxfail=1

Run broader NoDb validation:

    wctl run-pytest tests/nodb --maxfail=1

Run required handoff gates:

    wctl run-pytest tests --maxfail=1
    python3 tools/check_broad_exceptions.py --enforce-changed --base-ref origin/master
    wctl doc-lint --path docs/work-packages/20260806_batch_omni_mofe_treatments
    wctl doc-lint --path wepppy/nodb/README.batch-runner.md

## Validation and Acceptance

The focused regression must fail before implementation because a selected
multi-OFE forest segment remains on its undisturbed management key. After the
fix it must pass and prove all of the following: eligible segments receive the
treatment management, ineligible segments are preserved, `domlc_mofe_d` is
persisted, synthesized `hill_*.mofe.man` is rebuilt, and the generated
`wepp/runs/*.man` exposes treatment canopy/ground cover.

Existing single-OFE tests must continue to pass. The full repository test suite
must complete without a new failure before package closure.

## Idempotence and Recovery

The code path must be safe to rerun: applying the same treatment mapping twice
must produce the same landuse keys and regenerated artifacts. Tests use temporary
directories and leave no run data behind. No production runs are modified by
this package. If full validation exposes unrelated failures, record them with
evidence and keep the package open until the change-specific gates are resolved.

## Artifacts and Notes

Production evidence collected read-only on 2026-08-06:

    thinning_40_75: domlc_d[1001] = 124
    thinning_40_75: domlc_mofe_d[1001] = {1: 42, 2: 42, 3: 42, 4: 42, 5: 42}
    thinning_65_93: domlc_d[1001] = 128
    prescribed_fire: domlc_d[1001] = 110
    all scenario wepp/runs/*.man checksum differences = 0

## Interfaces and Dependencies

Keep `Treatments.build_treatments()` as the public orchestration entry point.
Any new helper should be private and accept explicit mappings or segment ids so
it can be tested without filesystem-global state. Reuse `Landuse.managements`,
`Landuse.domlc_d`, `Landuse.domlc_mofe_d`, existing treatment mapping lookup,
and existing Landuse multi-OFE synthesis functions. Do not add dependencies or
change RQ wiring.

Revision note (2026-08-06 19:30 UTC): Initial plan created from the confirmed
production Batch Runner OMNI failure and the operator's request to implement the
repair end-to-end.

Revision note (2026-08-06 20:05 UTC): Recorded completed implementation,
generated-output proof, full validation results, and package closure.
