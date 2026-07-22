# SSURGO Intelligent Fallback M4 Rollout

**Status**: Open (2026-07-22)
**Timezone**: UTC

## Overview

Implement ADR-0025: ordinary SSURGO conversion recovers the raw MUKEY where it
can, a locally buildable shallow-profile vector donor handles eligible residual
failures, and the current watershed-global donor remains last resort. The
implementation must be observable and backward-compatible, and must be proven
through the local RQ `build_soils` operation for `plastic-bundling`.

The preceding empirical study established the policy. This package implements
and propagates it; it does not reopen terrain, topology, or policy scoring.

## Objectives

- Faithfully implement ADR-0025 and `wepppy/soils/ssurgo/fallback.md`.
- Do no padded-map retrieval or added-MUKEY builds for an all-valid watershed.
- Preserve raw/final assignment contracts and add complete nullable provenance.
- Prove an affected hermetic fixture and an unaffected production-shaped path.
- Rebuild `plastic-bundling` through RQ with config `disturbed9002`, poll the
  job, and validate generated artifacts.
- Complete independent code, QA, and security reviews with a final disposition.

## Scope

### Included

- Conditional 2 km padded candidate raster creation from 2025 gNATSGO.
- Separate added-MUKEY candidate builds under the primary build's settings.
- Source recovery, vector selection, global escape hatch, selected-donor
  materialization, and additive NoDb/Parquet provenance.
- Regression, generated-output, RQ, and no-op performance coverage.
- Config-match validation for the existing RQ mutator before it changes state;
  this does not add a route, broaden authorization, or change queue wiring.
- Local Docker Compose restart if needed for the RQ proof; agents are
  explicitly authorized to restart the local container stack for this package.
- Code, QA, security review, and finding-disposition artifacts.

### Explicitly Out of Scope

- New source-data repair formulas, synthetic profiles, terrain scoring, or
  watershed/hillslope-topology scoring.
- New public RQ routes, authorization changes, or dependency wiring unless
  separately ratified.
- Production-host deployment, source-data mutation, or national adjacency index.

## Implementation Fidelity and Evidence

- **Fidelity target**: faithful extraction into `Soils._build_gridded()`.
- **Authoritative source paths**: ADR-0025,
  `wepppy/soils/ssurgo/fallback.md`, `wepppy/nodb/core/soils.py`, and
  `wepppy/rq/project_rq.py::build_soils_rq`.
- **Cutover proof required**: RQ-enqueued `build_soils_rq` completes for
  `plastic-bundling`; its rebuilt NoDb, Parquet, and soil artifacts pass the
  no-op/integrity assertions.
- **Acceptance evidence type**: both generated-output and fixture evidence.

## Success Criteria

- [ ] Recovered raw MUKEYs remain raw and have no substitution record.
- [ ] Eligible invalid fixtures choose the deterministic local vector donor;
  both valid primary and valid added candidates are eligible; only selected
  added donors appear in final output.
- [ ] Profile-free, no-comparable, and candidate build/raster failure cases use
  the existing global donor.
- [ ] Donor materialization failure is atomic: it leaves no partial `.sol` or
  dangling final assignment/provenance and uses the existing global donor.
- [ ] All-valid fixtures perform no padded work, persist
  `candidate_preparation=not_attempted`, and make no source open, crop,
  enumeration, or added-build call.
- [ ] Legacy NoDb/Parquet consumers are compatible with additive provenance.
- [ ] RQ `plastic-bundling` / `disturbed9002` build completes and demonstrates
  the expected all-valid no-op path.
- [ ] Independent code, QA, security reviews and disposition are complete with
  no open critical/high or undispositioned medium findings.

## Parameterization ADR Gate

- **Parameterization change present**: yes.
- **ADR required**: yes.
- **ADR link(s)**:
  [`ADR-0025`](../../adrs/ADR-0025-ssurgo-local-vector-profile-fallback.md).
- **Decision provenance captured**: yes, in ADR-0025.

## Data and Schema Compatibility Plan

Before persistence edits, complete
[`artifacts/2026-07-22_data_schema_compatibility.md`](artifacts/2026-07-22_data_schema_compatibility.md),
which records the nine additive `ssurgo_substitution_d` fields and their NoDb /
Parquet representations. Keep `raw_ssurgo_domsoil_d`, `domsoil_d`,
`ssurgo_domsoil_d`, and existing substitution keys unchanged. Old NoDb payloads
must hydrate new fields as null/empty. Tests must prove raw assignments are
unchanged, every final assignment has a `.sol`, NoDb/Parquet/final mappings
agree, and unused candidate soils are absent from final outputs.

## Dependencies

- ADR-0025 and fallback specification at `def1d3243` or descendant.
- `/wc1/geodata/ssurgo/gNATSGSO/2025/.vrt` mounted locally.
- `/wc1/runs/pl/plastic-bundling` with config `disturbed9002`.
- Local Docker Compose stack and RQ worker through `wctl`.

## Related Packages

- **Depends on**:
  [`20260721_ssurgo_intelligent_fallback_study`](../20260721_ssurgo_intelligent_fallback_study/package.md).
- **Related**:
  [`20260619_ssurgo_project_sqlite_cache`](../20260619_ssurgo_project_sqlite_cache/package.md).
- **Related**:
  [`20260622_ssurgo_reclaimed_soil_fallback`](../20260622_ssurgo_reclaimed_soil_fallback/package.md).

## Timeline Estimate

- **Expected duration**: 2-4 focused sessions.
- **Complexity**: High.
- **Risk level**: High.

## Security Impact and Review Gate

- **Security impact triage**: high.
- **Dedicated security review required**: yes.
- **Triage rationale**: an RQ worker changes run-scoped filesystem work and
  reads configured geodata; path, lock, source, and failure boundaries require
  independent review.
- **Security review artifact**: `artifacts/2026-07-22_security_review.md`.

## References

- `docs/adrs/ADR-0025-ssurgo-local-vector-profile-fallback.md`
- `wepppy/soils/ssurgo/fallback.md`
- `wepppy/nodb/core/soils.py`
- `wepppy/soils/ssurgo/fallback.py`
- `wepppy/rq/project_rq.py::build_soils_rq`
- `docs/schemas/rq-response-contract.md`
- `docs/work-packages/20260722_ssurgo_intelligent_fallback_rollout/artifacts/2026-07-22_data_schema_compatibility.md`

## Deliverables

- Wired fallback implementation, compatibility evidence, local RQ proof, and
  completed review/disposition artifacts.
