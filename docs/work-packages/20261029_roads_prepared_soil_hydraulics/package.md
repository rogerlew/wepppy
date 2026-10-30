# Roads prepared-soil and hydraulic experiment

Status: complete, 2026-10-29. No production candidate accepted.

## Accepted scope and rationale

The operator authorized scaffolding and executing the proposed follow-up to the
Roads soil benchmark. Compare actual WEPPcloud landuse preparation, distinguish
road/fill/forest-buffer treatment, and isolate road-layer depth and conductivity
before erosion adjustments. Use `wepp_261026`, matched fswepp2 WEPP2010 controls,
multiple climates and a new held-out soil. Factor-ten agreement is the study
criterion; zero-reference results and material absolute errors remain explicit.

The previous benchmark used generated 7778 base soils. This study must exercise
the production soil conversion and preparation functions and verify the files
consumed by WEPP. No blanket output multiplier or climate-specific fitting.
A negative result is a valid scientific outcome. Production promotion requires
an accepted candidate, parameterization ADR, contract updates and actual isolated
Roads integration; execution of this study alone does not authorize deployment.

Compatibility: all study inputs, output schemas and scripts are additive and
isolated. Existing project data, runtime defaults and the prior study remain
unchanged. New results must preserve metric definitions and retain input/output
hashes, failed attempts and preparation lineage. No new dependency or service.

See [execution plan](prompts/completed/experiment_execplan.md) and [tracker](tracker.md).

## Scientific outcome

All 1,615 native runs completed and passed artifact revalidation. Roles treatment
meets the export band in 503/563 positive-reference comparisons but retains
material failures; no candidate is promoted. Equivalent horizon subdivision
changes sandy-loam export sharply, with an exact-release native source explanation.
See [results report](report.md) and [mechanism evidence](artifacts/mechanism.md).

Fresh repository validation: 12,083 passed, 298 skipped, no failures. See
[validation evidence](artifacts/validation.md).
