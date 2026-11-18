# RUPC-02 implementation reviews

Scope: runtime diff after contract checkpoint `f46d59422009d5adb8641b1d2b7494cd5f9b788a`,
including placement, role generation, failure provenance, current-result admission,
archive restoration and result inspection. Reviews were independent and read-only.

## Correctness — `/root/contract_review_a`

Final verdict: pass, no remaining correctness blocker. Findings closed:

- Decimal exact fit could create a tiny third OFE that serialized to zero. Use
  decimal input-dimension subtraction, retain low/high-distance exact-fit tests,
  and validate native road/fill artifacts; no new physical length tolerance.
- Native failure and missing-PASS records dropped known placement. Preserve plan
  provenance on failures and explicit nulls for unavailable fields, including
  hillslope compensation. Controller regression forces native failure.
- Native two-OFE and short-downhill evidence was required beyond mocked writer
  tests. The reviewer independently verified retained hashes, slope dimensions,
  soil roles, management indices and 5,844 parsed daily records per shape.

## Security — `/root/contract_review_b`

Final verdict: pass, no unresolved medium/high findings. Findings closed:

- Historical policy restore initially bypassed ordinary generated-artifact
  validation. Validate receipt, Parquet bodies, manifest IDs and ledger before
  downgrading only the placement policy to historical. Corrupt old-policy restore
  regressions fail and revoke admission.
- Absent status used a different completion convention. Match existing default
  completed semantics so missing status cannot bypass placement provenance.
- Missing/relabeled design could bypass row marker checks. Bind row design to
  prepared primary/source membership; reject missing, rutted and remainder
  relabeling for unrutted sources. Reviewer probes confirmed both current read
  and restore rejection independently.

## Validation and limits

Final scoped suite: 199 passed, two existing dependency deprecation warnings.
Six affected modules; no full repository suite. Fresh final-candidate native
retries retain all eight old failure dispositions: three execute with top placement
at 30 m synthetic fill; five explicitly fail road/fill fit. The separate 5 m-fill
experiment completes 24 profiles, replacement PASS, watershed and 5,844 daily
report rows. Native exact-fit and 1 m downhill probes also pass. See the separate
native evidence manifest for hashes, runtime identity and consumer readback.

No source mutation, production deployment, or site calibration claim. Placement
assumes zero modeled upstream runon. Synthetic fill values are validation inputs.
