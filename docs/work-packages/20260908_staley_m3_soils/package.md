# Staley M3 SSURGO Soil Thickness

**Status**: Closed — offline implementation and paired experiment complete, 2026-09-09.
**Started**: 2026-09-09 02:17 UTC (2026-09-08 Pacific)
**Timezone**: UTC

## Overview

Determine whether project SSURGO horizons can supply Staley M3's cumulative
soil-layer thickness predictor, implement a reproducible derivation, and
compare its effects against the original STATSGO THICK variable. The result
must define source readiness, interval and component aggregation, bedrock
handling, units, and explicit missing-data behavior before production M3 use.

## Objectives and Scope

- Audit real project soil data and preserve minimal, reproducible soil fixtures.
- Resolve cumulative-thickness semantics and draft a parameterization ADR.
- Implement and test an offline derivation and assessment artifact builder
  using owned components, without changing existing WEPP soil behavior.
- Compare SSURGO and original STATSGO on the existing 10 m terrain panel,
  isolating soil effects on M3 probabilities and inverse rainfall thresholds.
- Produce an evidence-based source recommendation and production integration
  contract, including SI/English display conversion and unavailable reasons.

No NoDb/UI/RQ wiring, deployment, live soil rebuilds, automatic STATSGO fallback,
or changes to generated WEPP profiles are included. Do not fix the unrelated
`SurgoSpatializer.SolThk` output as a shortcut: the package derives M3 thickness
from raw intervals independently. Terrain formulas and resolution decisions
remain those of the completed terrain work. This is new derivation/evaluation,
not a GPL implementation extraction or a claim of calibrated predictive skill.

## Stakeholders and Execution

The requesting user owns scientific source/availability decisions; the executing
agent implements and evaluates the derivation. Independent reviewers assess
correctness and data-boundary changes. The
[archived start prompt](prompts/completed/start_here.md),
[completed ExecPlan](prompts/completed/staley_m3_soils_execplan.md), and
[tracker](tracker.md) preserve execution history.

## Success Criteria

- Original THICK semantics and SSURGO interval/component rules are documented
  with primary-source evidence and a parameterization ADR.
- Minimal soil fixtures, provenance, hashes, and repeatable extraction commands
  make the study independent of mutable live runs.
- The offline builder produces thickness, coverage, reason codes, and catchment
  S inputs with tested unit conversions and no silently fabricated depths.
- A paired soil-source study uses fixed 10 m terrain/catchments and reports
  coverage, thickness, probability, and threshold differences separately.
- A decision report recommends an explicit source policy, retains STATSGO, or
  explains insufficiency with a concrete next step. Insufficient evidence does
  not establish source acceptance or complete the scientific determination.
- Required tests and independent reviews pass; durable findings and contracts
  are promoted into module docs. Production wiring remains explicitly deferred.

## Parameterization ADR Gate

Parameterization changes: **yes**. ADR required: **yes**, drafted before
implementation in `docs/adrs/` using the next available identifier. Capture
venue, user decision ownership, actual implementer, formula/unit deltas,
alternatives, missing-data rules, evidence, and limits. The conversation
authorizes investigating SSURGO; it has not approved a particular coverage
cutoff, bedrock rule, weighting scheme, or default thickness.

## Security Impact and Review Gate

Security impact: **high**, following repository defaults for planned offline
file/SQLite readers and any source acquisition boundary. Dedicated security and
independent correctness artifacts are required before implementation closeout,
using the repository templates. No new public endpoint or worker subprocess
boundary is in scope. Use read-only project access and bounded acquisition in
an isolated workspace; do not serialize secrets or entire project state into
fixtures. Close medium/high findings before completion.

## Dependencies and References

- [Canonical postfire specification](../../../wepppy/nodb/mods/postfire_debris_flow/specification.md).
- [SSURGO feasibility assessment](../../../wepppy/nodb/mods/postfire_debris_flow/docs/ssurgo_m3_feasibility.md).
- [Completed terrain package](../20260908_staley_m3_wbt_terrain/package.md) and
  [terrain decision](../20260908_staley_m3_wbt_terrain/artifacts/resolution_decision.md).
- [Terrain ADR](../../adrs/ADR-0052-staley-m3-upstream-terrain.md).
- Existing Soils and SSURGO code named in the ExecPlan; no new dependency is
  assumed. Evaluate any proposed dependency under the repository standard.

## Deliverables and Follow-up

The offline helper, frozen source fixtures, paired soil-source experiment,
ADR-0053 and independent reviews are delivered. The recommendation is to retain
original STATSGO pending scientific source approval; no SSURGO production
coverage cutoff or material policy is approved. See the
[decision report](artifacts/soil_decision.md) and
[canonical offline contract](../../../wepppy/nodb/mods/postfire_debris_flow/docs/m3_soil_thickness.md).
Future production integration requires its own contract-first work.
