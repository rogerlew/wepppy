# EU ESDAC Soil Quality Taxonomy and Invariant Contract

**Status**: Phase 2 working contract, proposed for Phase 3 implementation
**Evidence**: [Phase 1 fixture](../../../../tests/eu/soils/fixtures/eu_disturbed_soil_phase1.json)
**Related ADR**: [ADR-0043](../../../adrs/ADR-0043-eu-esdac-soil-quality-contract.md)

## Scope

This contract classifies the ESDAC-to-WEPP soil path at the first boundary
where a location becomes unusable or loses provenance. It does not change the
builder, add fallbacks, or repair historical `.sol` files. Phase 3 will add
the validation boundary after this contract is approved.

## Evidence Classification

| Case | Observed evidence | Phase 2 quality | Primary reason |
| --- | --- | --- | --- |
| `pilot-0001-control` | Complete source payload; depths `1200 -> 1500` | `valid` | None |
| `pilot-0021-missing-landuse-metadata` | Physical payload and depths valid; `usedom=0` | `degraded` | `source.usedom.no_information` |
| `pilot-0007-depth-order` | Generated depths `1200 -> 600` | `rejected` | `output.horizon_depth_order` |
| `pilot-0014-zero-stu` | Subsoil texture and density all zero; depths `1200 -> 400` | `rejected` | `source.stu.mandatory_profile_empty` |
| `pilot-0050-hydrogrids-out-of-bounds` | All Ksat slices unavailable; builder raises `RDIOutOfBoundsException` | `rejected` | `source.hydrogrids.provider_unavailable` |
| `pilot-0057-missing-depth-source` | Missing depth classes; builder raises `TypeError` | `rejected` | `source.depth_class.unreadable` |
| `pilot-0354-missing-rat-value` | Missing categorical value; builder raises `KeyError` | `rejected` | `source.categorical.lookup_failed` |

The `usedom=0` case is deliberately separated from physical invalidity. The
current builder uses the nonforest albedo/initial-saturation branch when land
use is unknown, so the proposed result is degraded with a warning rather than
rejected when all physical and structural checks pass.

## Invariants

### Source categorical values

- Required categorical reads must return a supported raster code and legend
  value. Read failures, missing RAT entries, and unsupported CEC classes are
  rejected with the source field and location in the reason context.
- `cec_top` and `cec_sub` must resolve to `H`, `M`, or `L` before horizon
  construction.
- Missing `textdepchg` or `il` classes must not silently become an
  undocumented depth fallback. A successfully read but explicitly supported
  legacy class may be degraded; an unreadable provider response is rejected.
- Missing `usedom` is degraded only when all physical and output invariants
  pass. It must be visible in the result metadata.

### STU physical values

- Clay, sand, and silt must be finite percentages in `[0, 100]` for both
  horizons. Their sum must be within one percentage point of 100 to allow the
  source's integer percentage quantization.
- An individual zero texture component is allowed; an all-zero clay/sand/silt
  triad is a missing mandatory profile and is rejected.
- Bulk density must be finite and strictly positive. No empirical upper or
  lower density cutoff is introduced in Phase 2.
- Gravel must be finite in `[0, 100]`; zero gravel is valid and is not a
  failure by itself.
- Organic matter must be finite and nonnegative. Zero organic matter alone is
  not rejected until a separate scientific decision establishes whether the
  downstream erodibility result is acceptable.

### Derived horizons and water properties

- Every derived numeric value written to a WEPP horizon must be finite.
- Cumulative horizon depths must be finite and strictly positive. If two
  horizons are emitted, `h1.depth > h0.depth` is required.
- Water contents must satisfy the existing WEPP contract
  `0 <= wilting_point <= field_capacity <= 1`, consistent with
  [ADR-0012](../../../adrs/ADR-0012-ssurgo-fc-wp-sanitization.md).

### SoilHydroGrids Ksat

- A provider exception or an all-missing Ksat profile is rejected; the
  existing `0.001` representation is not an acceptable silent substitute.
- A partially missing profile is degraded only when the remaining values are
  finite, the location is recorded, and the resulting `.sol` remains valid.
- Ksat values used in output must be finite and positive. Zero or negative
  values are rejected as unrepresentable model conductivity; no new minimum
  positive threshold is introduced here.

### Serialization

- Rejected cases must not write a usable-looking `.sol` file.
- Every emitted horizon row must contain finite values and positive,
  strictly increasing cumulative depths.
- The result must retain longitude, latitude, optional TopoAZ identity, source
  field, raw value or exception class, and a stable reason code.

## Result Contract

```text
valid
  No invariant violations; output may be used without a quality warning.

degraded
  Output remains contract-valid, but one or more optional/source-completeness
  warnings are attached with provenance. Degraded output is never a silent
  fallback.

rejected
  A mandatory source, derived value, horizon structure, Ksat profile, or
  serialization invariant failed. No model input is accepted for execution.
```

Reason codes should be stable, field-qualified strings such as
`source.stu.mandatory_profile_empty`, `source.hydrogrids.provider_unavailable`,
`horizon.depth_order`, and `output.nonfinite_value`. Diagnostics should carry
the original exception class separately from the normalized reason code.

## Parameterization Boundary

The one-percentage texture balance tolerance, treatment of partial Ksat
profiles, and treatment of supported depth-class fallbacks affect generated
model inputs. They are recorded in ADR-0043 and must be approved before Phase
3 production implementation. Phase 2 introduces no runtime behavior.

The 50,000-cell search remains a discovery-scale decision separate from these
invariants; the 1,000-cell pilot is sufficient to establish the fixture-backed
contract, but not to claim population-wide validity.
