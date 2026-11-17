# Current Roads project harness assessment

Status: implemented and validated, 2026-11-17. The initial assessment below
preceded the new current-policy helper. Both current unrutted controls now pass
using that checked-in helper; see `candidate_validation.md` and its retained
receipts. Current RUPC-02 authority is reconciled in
`docs/schemas/roads-validation-suite-contract.md`.

## Initial stale expectations

`tests/roads/test_roads_project.py` still selects all four designs using
`validate_project(..., exclude_infeasible_unrutted=True)` for the unrutted case,
and expects two full-upload failures. Its reader `verify_negative` pins the old
`failed_non_positive_top_ofe` result for hillslopes 271/272. Those are historical
controls, not the current placement policy.

The historical `collect_evidence` also hardcodes 30 m unrutted fill/buffer and
infers only three/four-OFE roles from OFE count. A two-OFE road/fill profile and a
three-OFE road/fill/downstream-landuse profile cannot safely use that inference.
Changing only the expected failure count would leave these contradictions.

## Smallest faithful reconciliation

Keep the existing historical verification functions and published reports intact.
Parameterize the existing current additive test over the three additive designs.
Add one focused current-unrutted validation helper and two explicitly named tests;
the helper can reuse `inventory`, `digest`, and `inspect_outputs` but must not call
the historical unrutted `collect_evidence` path. Keep normal controller
upload/prepare/run calls and durable reload/artifact readback.

Use a separate opt-in `ROADS_UNRUTTED_VALIDATION_SOURCE` fixture so that selecting
the existing `ROADS_VALIDATION_SOURCE` does not silently substitute a different
site. Pin the proven misty source upload SHA-256:
`fa32c9ad8d43789acaca5b19f324c89871510913c10fae0fd29a939c6e4eec1f`.
Retain all 55 features, with explicit DESIGN=outslope_unrutted. Declare source
inventory, exact edited upload hash, feature count, no exclusions, binary identity,
and synthetic input provenance before execution.

The proven positive control uses fill length 5 m at 10%, buffer length 30 m at
10%; it completed 24 profiles. The oversized negative uses fill length 30 m with
the other values unchanged; it completed 15 profiles and retained five
`failed_road_fill_exceeds_hillslope` failures. These are fixture values, not new
model defaults or measured-site claims.

For success, require the top-placement marker, current-result admission,
prepared/emitted positive dimensions, OFE role agreement, source membership,
production segment summary and independent daily water/area reconciliation. For
failure, require failed status, absent current receipt, finite retained H/road/fill
dimensions proving the fit rejection, preserved diagnostic records, and the same
five failed profile identities as baseline. Always verify source and copied
baseline inventories after either outcome, including raised exceptions.

Do not import work-package scripts into the long-lived test suite. They are
execution evidence; promote only the small current-policy helper and its explicit
fixture contract into `tests/roads/`. Update the suite README with the two source
settings and explain that historical `--verify-negative` verifies historical
artifacts. No report refresh or scientific reranking is authorized by this repair.

## Evidence and implementation gate

`baseline_project_receipt.json` records the observed five controls, native binaries,
and artifact hashes. `scripts/project_parity.py` retains the fresh-copy recipe.
The root integrator coordinates any suite change and a focused run against stable
candidate source; no runtime launch was made for the initial assessment. The final candidate
validation subsequently exercised the checked-in helper and confirmed six
top-placed strips with nonempty source membership in the positive fixture.

## Implementation disposition

The proposal was implemented in `tests/roads/unrutted_project.py` and the opt-in
project tests. Both current-policy controls passed on the frozen candidate;
`candidate_validation.md` records the native and durable artifact comparisons.
The assessment above retains the pre-implementation findings and rationale.
