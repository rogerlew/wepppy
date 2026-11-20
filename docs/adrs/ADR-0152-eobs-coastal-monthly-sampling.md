# ADR-0152: Masked bilinear sampling for coastal E-OBS climate data

Status: Accepted, implementation conformance pending
Date: 2026-11-20

## Context

Legacy v19.0e rainfall and temperature grids contain scaled missing data values, but their metadata still declares the unscaled sentinel. The existing cubic sampler incorporates those values near the coast. At Es Fangar this produced about 59–60 mm/day of apparent rainfall in January and July and a failed CLIGEN build.

## Decision

Preserve existing cubic interpolation on a complete valid neighborhood, including the existing dry-month treatment when cubic rainfall undershoots zero. At a covered location with an incomplete cubic neighborhood, renormalize bilinear weights over the valid immediate pixel-center neighbors. Do not borrow data for a missing containing pixel. Mask both historical encodings, the declared NoData value, and physically impossible source rainfall or temperature. Reject nonfinite results and temperatures below absolute zero. Keep unit conversions as they are. Correct the mask and fill handling for future preprocessing. The [sampling contract](../schemas/eobs-monthly-sampling-contract.md) specifies the exact scope, boundary behavior, and errors.

## Decision provenance

The operator selected the bilinear rule in the WEPPcloud incident conversation on 2026-11-20 UTC. The participants were the WEPPcloud operator and Codex. Codex prepared the candidate rule and implements the approved decision.

## Rationale and alternatives

Renormalized bilinear weights use available nearby observations without crossing an unavailable containing cell. Using only the containing cell gives a discontinuous surface at pixel boundaries. Replacing cubic everywhere would change valid inland estimates and broaden the scientific change beyond this incident.

## Evidence and rollback

The [coastal probe](../work-packages/20261120_eu_run_recovery/artifacts/20261120_incident_readback.md#e-obs-coastal-interpolation) produced 10,957 daily records, retained inland cubic sampling, and rejected an offshore control. Candidate validation must also exercise the actual metquery and CLIGEN request path. Older aggregates can contain partially contaminated values that look physically plausible, especially for temperature. Repairing those historical rasters requires rebuilding and validating the source products. Revert the sampler and preprocessing code if covered inland locations with valid cubic estimates lose parity or coastal output includes missing-data values. Keep existing rasters and generated evidence available for comparison. Reverting the sampler reintroduces the confirmed coastal failure.
