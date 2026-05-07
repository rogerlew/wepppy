# RUSLE K CFVO Profile-Fragment Adjustment Integration

This ExecPlan is a living document. Keep `Progress`, `Surprises & Discoveries`, `Decision Log`, and `Outcomes & Retrospective` current while work proceeds.

This plan follows `docs/prompt_templates/codex_exec_plans.md` and is maintained under that standard.

## Purpose / Big Picture

Users can currently run RUSLE `K` with POLARIS-based estimators, but profile coarse-fragment handling (`cfvo`) is documented as deferred. After this change, the `K` pipeline can apply a conservative optional profile-fragment adjustment when run-scoped `cfvo` layers exist, and will report clearly when the adjustment was applied or skipped.

## Progress

- [x] (2026-05-07) Created package scaffold and active ExecPlan.
- [x] (2026-05-07) Implemented `cfvo` loading/normalization/adjustment in `k_integration.py`.
- [x] (2026-05-07) Extended nomograph helper to support explicit permeability-class override.
- [x] (2026-05-07) Added regression coverage for applied and unavailable `cfvo` behavior.
- [x] (2026-05-07) Updated `specification.md` and `README.md` contracts.
- [x] (2026-05-07) Ran targeted and broader validation commands; full suite stopped on unrelated baseline test.
- [x] (2026-05-07) Produced code review, QA review, and findings disposition artifacts.
- [x] (2026-05-07) Closed package docs and archived this ExecPlan.

## Surprises & Discoveries

- Observation: existing run-scoped `soils/cfvo_*_Q0.5.tif` layers can be
  aligned and reused for RUSLE without adding a new fetch subsystem.
  Evidence: targeted and broader RUSLE tests passed after adding alignment +
  adjustment path (`6 passed`, `27 passed`).

- Observation: broad suite currently has an unrelated baseline failure outside
  RUSLE scope.
  Evidence: `tests/wepp/test_wepp_baseflow_opts.py::test_post_instance_loaded_guards_legacy_baseflow_without_initialized_logger`.

## Decision Log

- Decision: keep `cfvo` optional and metadata-explicit rather than required input.
  Rationale: preserves compatibility while closing deferred scope.
  Date/Author: 2026-05-07 / Codex.

## Outcomes & Retrospective

- Core implementation outcome:
  - `cfvo_scope` moved from deferred to optional implemented contract.
  - run-scoped `cfvo` discovery/normalization and conservative permeability
    class adjustment now ship in `K` processing for `polaris_nomograph`.
  - manifest captures applied vs skipped status and source details.
- Independent reviews:
  - initial code/QA reviews reported one high and two medium findings.
  - all high/medium findings were fixed and re-reviewed to closure.
- Validation:
  - targeted CFVO/RUSLE suites passed (`10 passed`, `31 passed`).
  - broad `tests --maxfail=1` still reports an unrelated baseline NoDb failure
    outside changed scope.

## Context and Orientation

`wepppy/nodb/mods/rusle/k_integration.py` builds RUSLE `K` rasters from run-scoped POLARIS inputs (`sand`, `silt`, `clay`, `om`, `ksat`) and writes metadata into `rusle/manifest.json`. Today the manifest explicitly says `cfvo_scope: deferred`. `wepppy/nodb/mods/rusle/k_nomograph.py` currently infers permeability class from Ksat internally, which is where profile-fragment adjustment can be represented conservatively.

## Plan of Work

Implement `cfvo` as an optional ancillary layer pair (0-5 cm and 5-15 cm) when present in run scope. Normalize to volumetric percent consistently, aggregate near-surface support like other K inputs, derive conservative permeability-class penalties by `cfvo` bins, and apply those penalties through a permeability override path in nomograph K computation. Preserve unchanged behavior when `cfvo` layers are absent, and make all states explicit in manifest metadata.

## Concrete Steps

1. Edit `wepppy/nodb/mods/rusle/k_nomograph.py` to support an optional permeability-class override argument.
2. Edit `wepppy/nodb/mods/rusle/k_integration.py` to:
   - discover optional `cfvo` layers,
   - normalize/aggregate `cfvo`,
   - apply conservative adjustment,
   - emit `cfvo` metadata in `k.mode_contract`.
3. Update `tests/nodb/mods/test_rusle_k_integration.py` to cover `cfvo` unavailable/applied paths.
4. Update `wepppy/nodb/mods/rusle/specification.md` and `wepppy/nodb/mods/rusle/README.md`.
5. Run validation commands and record results in package artifacts.

## Validation and Acceptance

- `wctl run-pytest tests/nodb/mods/test_rusle_k_integration.py --maxfail=1`
- `wctl run-pytest tests/nodb/mods/test_rusle_k_nomograph.py tests/nodb/mods/test_rusle_k_epic.py tests/nodb/mods/test_rusle_k_compare.py tests/nodb/mods/test_rusle_k_reference_harness.py tests/nodb/mods/test_rusle_k_integration.py tests/nodb/mods/test_rusle_controller.py --maxfail=1`
- `wctl run-pytest tests --maxfail=1` (report unrelated baseline failures if present)
- `wctl doc-lint --path wepppy/nodb/mods/rusle/specification.md --path wepppy/nodb/mods/rusle/README.md --path docs/work-packages/20260507_rusle_k_cfvo_integration`

Acceptance is met when:
- `cfvo` is no longer marked deferred in manifest,
- runtime behavior is explicit for both applied and unavailable paths,
- tests pass for changed path,
- docs and review artifacts are complete.

## Idempotence and Recovery

Changes are additive and file-local. If a validation command fails, rerun after fixing. No destructive data migrations are included.

## Artifacts and Notes

- Planned artifacts:
  - `artifacts/20260507_code_review.md`
  - `artifacts/20260507_qa_review.md`
  - `artifacts/20260507_findings_disposition.md`

## Interfaces and Dependencies

- `run_rusle_k_factors(...)` remains the integration entrypoint.
- `compute_polaris_nomograph_k(...)` will accept an optional permeability class override while preserving current default behavior.
- Manifest schema extension is additive under `k.mode_contract`.
