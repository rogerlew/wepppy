# Independent single-input reader correction review A

Reviewer: `prism_contract_review_a`; reviewed 2026-10-08T23:34:01Z.
Read-only scope: correction checkpoint, current Project Config PRISM amendment,
candidate structure, existing reader catalog, `single_input_capability_graph`,
the single-user-defined-inputs contract and failing Builder snapshot test.
No implementation edits made. Current checkout HEAD is `0e331f5e2`; relevant
PRISM contract/reader ancestors remain `d3b5958c5` and `e25299022`. The intervening
commit concerns unrelated user work and is not part of this correction.

## Findings

No high or medium contract finding. The omitted existing variant is a real
compatibility regression, not grounds to relax the structural validator.
`single_input_capability_graph` modifies landuse/soil upload relations, permitted
modules and native binary restrictions, then validates the resulting graph.
Adding PRISM to the base graph therefore produces a distinct, legitimately
expected variant that must be registered explicitly.

Independent canonical JSON SHA-256 calculation matches the proposed identity:
`545e2197c8a67a88da9c796246a2b0572427c8228bcb0e5d3ccd883f11b320a6`.
Deep comparison against prior single-input identity
`8c9fd249f34531e3254ecb0f57e2724f335ef3e5d23cd581ac256cc0168f091f`
finds exactly these additions:

- `observed_prism_800m` in the climate dataset axis;
- station methods `auto`, `distance`, `multi_factor` and default `auto`;
- spatial methods `single`, `multiple`, `interpolated` and default `single`.

No landuse/soil, module, model-pair, representation or existing method/default
value changes. Historical stored graphs remain valid and unchanged. The
current canonical amendment specifies both exact identities and requires the
additional reader floor before successful new-variant persistence. Keeping the
existing strict rejection until that floor is present prevents unsupported graph
publication; there is no permission to broaden validation or bypass the reader.

The user's CONUS integration and existing-workflow compatibility authorization
covers this bounded correction. It does not authorize new single-input behavior,
other-locale changes, module/binary expansion or retroactive mutation of stored
projects. The checkpoint accurately identifies the full-suite failure as a
conformance defect. Its starting-revision wording should distinguish the PRISM
reader baseline from current checkout HEAD when the additional commit is recorded.

## Verdict and required evidence

**Approved for the standalone append-only reader-floor correction.** Preserve
all existing structure payloads/identities, append the exact candidate, retain
review/checkpoint ancestry and advance the aggregate rollback floor. No
production conformance is claimed by this contract review.

Before closing the implementation finding, verify ordinary and single-input
Builder creation for both OFE representations; reopen both new structures with
the committed aggregate reader without changing stored bytes; retain old-graph
fixtures; and resume the required broad suite from the failed module. The
previous 4,964 passes and failed probe should remain documented. A targeted
variant fix does not require rerunning unchanged completed slow modules, but
neither targeted success nor the previous forest watershed run proves the
remaining broad suite passes.
