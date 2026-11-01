# Independent scientific prereview: SIFT basis repair

Disposition: approved for the bounded implementation and declared validation.
The published source definitions support conversion of COFRAG volume fraction
using fine-earth BD to native dry fragment mass fraction. Reusing the existing
mineral2.65g/cm3 helper preserves the previously reviewed additive-volume
convention; it is not a new lithology or porous-fragment model.

Missing None/-9 inputs remain unavailable rather than fabricated; valid zero
rock stays zero when both source operands are available. The explicit contract
requires density availability even at zero rock. Invalid available operands
must fail the shared domain checks. Preserve the stated unavailable-input
precedence when testing mixed missing/invalid pairs; do not introduce a hidden
fallback. Raw source values, historical artifacts, formatting,200mm boundaries,
open-water behavior and native caps remain separately governed.

The required emitted-soil and complete native-consumer observations are essential:
a correct inverse formula alone cannot prove what native caps, density changes
and computational remapping subsequently consume. Report the cap and conversion
residual where applicable rather than require an impossible exact volume round
trip. No retention or frozen-water formula change follows from this repair.
The absent deployed BC dataset and estimated/modal source attributes continue
to limit field and deployment claims. No scientific blocker in the proposed
contract; implementation and generated-artifact acceptance remain pending.

## Reviewed bindings

- `docs/adrs/ADR-0126-sift-rock-volume-to-mass.md` SHA256 `601f1ea168f55be720fbd14641c4e237f66f97c285ebd5e24c410392bd61d486`.
- `docs/schemas/rock-fragment-representation-contract.md` SHA256 `59c5a68327a8bab16b4b7dd72fc10bd8c545e36d8e12192659f6dadef09b8062`.
- `docs/work-packages/20261101_sift_rock_frozen_water/artifacts/contract-decision.md` SHA256 `a71e39d77bd2c799dcc80a04cc726ff21f825224b8020b86d30cbc2bb442d856`.

## Compatibility clarification prereview

Approved the revised contract checkpoint: missing None/-9 in either operand
takes precedence over an invalid other operand. Canned open-water output is
selected before mineral validity/conversion, preserving its distinct existing
meaning; it does not certify invalid mineral data as scientifically valid.
Actual writer controls for missing/invalid mineral values on water rows are
appropriate. This clarification leaves the mineral conversion and scientific
limits above unchanged. Earlier bindings remain historical.

Revised reviewed SHA256 bindings:

- `docs/adrs/ADR-0126-sift-rock-volume-to-mass.md`: `079483d074590620894593d9cb86ee0422d23e454572906aaea76f2cfc2efc63`.
- `docs/schemas/rock-fragment-representation-contract.md`: `3dd30b9b0363f5cde5d99f1742b321f039691260865b096cde91efcad0df925f`.
- `docs/work-packages/20261101_sift_rock_frozen_water/artifacts/contract-decision.md`: `216d19897d3caccbfe86761f1ecc087040276ff7d7901552cb7a7dd2e0dd6200`.

## Builder-boundary amendment prereview

Approved the narrowly scoped preimplementation amendment. The actual baseline
writer failure receipt identifies the undeclared prettytable import. A standard-
library comment renderer preserving original column names and values changes
no soil physics; exact comment whitespace need not be a numeric contract.

Source inspection confirms the mineral header omits SAT: its seven tokens
contrast with the canonical parser's eight-field header (wepp_soil_util.py:327).
Adding SAT0.75 at the declared position is a necessary explicit initial-condition
choice, supported by the established ISRIC and SSURGO defaults and existing SIFT
water header. It is a modeling convention, not a measured BC moisture state or
a sediment-calibrated value. This amendment must not be described as solely a
mass-conversion edit; retain its distinct parser-failure evidence and native
initialization readback. No other coefficient change is approved here.

Prior reviews remain historical; revised reviewed SHA256 bindings:

- `docs/adrs/ADR-0126-sift-rock-volume-to-mass.md`: `70b22a720ca124b187267e8fa67052edc3b160dd00f78f5d82d2b39f4987d255`.
- `docs/schemas/rock-fragment-representation-contract.md`: `731ca654db3d629c1c88ea3e30097258f4189d276e9a1ab7b07d1b2a0457b15f`.
- `docs/work-packages/20261101_sift_rock_frozen_water/artifacts/contract-decision.md`: `b83f7b5a3217b98e85c03145a36a11ed3dac6933ffd03f8975e35ababdde0e27`.
