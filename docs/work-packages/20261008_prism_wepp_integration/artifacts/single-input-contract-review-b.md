# Single-input reader correction: independent review B

Reviewer: `/root/prism_contract_review_b`, 2026-10-08 UTC. Read-only review of
the Project Config contract's final PRISM amendment, the correction checkpoint,
the exact candidate JSON, current catalog and existing single-input graph,
Builder and refresh code. Base PRISM reader revision: `e25299022`; current HEAD
also contains unrelated paper commit `0e331f5e2`. No production files edited by
this review. The candidate variant was absent from the catalog when reviewed.

## Findings and verdict

**Pass for the bounded contract correction.** No unresolved high, medium or low
findings. The omitted reader identity blocks an existing valid Builder workflow;
appending the exact variant restores conformance without changing single-input
policy or relaxing unknown-graph validation. This is within the authorized CONUS
integration and preservation of existing workflows.

## Independent comparison

Computed SHA-256 over sorted-key compact JSON exactly matches
`545e2197c8a67a88da9c796246a2b0572427c8228bcb0e5d3ccd883f11b320a6`.
Recursive comparison against old single-input payload
`8c9fd249f34531e3254ecb0f57e2724f335ef3e5d23cd581ac256cc0168f091f`
found precisely these differences:

- `axes.climate_datasets`: add `observed_prism_800m` after GridMET.
- `relations.climate_station_methods`: add auto/distance/multi_factor for PRISM.
- `relations.climate_spatial_methods`: add single/multiple/interpolated for PRISM.
- `method_defaults.climate_station`: add PRISM default auto.
- `method_defaults.climate_spatial`: add PRISM default single.

An independently reconstructed old payload with only those five changes equals
the candidate object exactly. Every other axis, relation, default, schema,
locale and allowed model pair remains equal, including module exclusions and
single-user-defined landuse/soil methods.

Binary identities are intentionally outside the structural hash; unchanged
`wepppy/nodb/single_input_policy.py:58` still restricts the transformed graph to
`wepp_260803`, filters model tuples, and validates the result. The catalog append
does not itself authorize other binaries. Existing binary-policy tests remain
necessary supporting evidence.

Both `wepppy/nodb/config_builder/resolver.py:480` and
`wepppy/nodb/project_config_update.py:942` call the same single-input transform.
The latter is the supported explicit refresh path; the additive catalog record
must not silently modify historical stored graphs or disable that workflow.

## Rollout, rollback and remaining evidence

Approve appending this exact immutable payload/hash in a standalone reader
ancestor with its checkpoint and review disposition. Preserve all prior payloads
and identities. Record the actual reader revision after commit; resolving an
earlier `pending-reader-floor` provenance marker is not a structural mutation.

The correction's aggregate rollback floor must recognize ordinary PRISM
`2c2934682af720fac7d022aa22f830087a10f2f423e4cb329d2a23c88c6ef1d3`
and the new single-input variant. The original ordinary-only floor cannot safely
read a newly persisted single-input graph. Verify the committed reader against
real persisted ordinary and single-input Builder configurations without byte
changes, including both watershed representations, before claiming rollout
complete. Retain prior graph fixtures and strict rejection of uncataloged
self-consistent structures. Run the existing explicit-refresh coverage as well
as creation/readback coverage because both consume this transformation.

Resuming the broad suite at the failing module is proportionate to this exact
catalog addition when focused policy/Builder/refresh and historical-catalog
checks pass. Previously passed modules provide supporting evidence; they do not
replace those checks. This review does not claim the correction is implemented,
tested, deployed or ready for rollback until those records are retained.
