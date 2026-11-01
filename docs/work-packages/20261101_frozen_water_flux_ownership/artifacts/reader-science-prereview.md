# Flux reader and ownership contract: scientific prereview

The corrected ownership contract is scientifically sound: coarse ice includes the dry frozen-support contribution; reader-double reconstruction, native-REAL arithmetic and the conditional zeroing allowance are separate. ET method-specific residue equations, initialized shared-return operands and conditional SWU decisions are appropriate. The prepared-v2 patches only add observations at supported locations and do not introduce an uninitialized SWU-local read. This is design review, not execution approval.

Four reader corrections remain before freeze:

1. FRZW negativity is not physical ice negativity. Hourly flags must evaluate absolute ice FRZW+THETDR*FROZEN and absolute liquid ST+THETDR*(DG-FROZEN). Negative coordinate values may be retained separately; they must not be mislabeled as negative physical components.
2. Daily uptake and growth comparisons need the same W/K geometry/reference checks as hourly intervals. A change in dry reference, layer support, frozen support or ice coordinate can invalidate an ST-only physical interpretation. Retain flags rather than silently treating these as closed flux comparisons.
3. Retain negative or inconsistent interception and negative inferred root uptake flags. Canopy/root reconstruction should not promote unsupported PLAINT/PINTLV states into an unqualified accepted sink. No-call decision and stock checks must remain explicit.
4. Require daily uptake PRE to occur after that day/OFE's hour-24 AFTER. Existing local UP order alone does not establish the join to the final hourly state.

The signed ET, capacity, drainage, lateral, surface and supported SWU equations otherwise match the reviewed source. Outside-allowance results should remain visible even if observer structural/parity acceptance succeeds; the comparison allowance is not evidence of exact native conservation. Exact freeze review remains pending the corrected reader, malformed controls and runner.

## Reviewed bindings

- `ownership-contract.md`: `ea9b7c9f38937170514743abc6b2d16758d85f8c3099e070fae9ed4bcb8106fe`.
- `read_flux.py`: `8d52ad946701bd18d8089bc290a3f572984bc6bb4978d09d4c4f16e7e33699e3`.
- `source-bindings.json`: `d373b146b12af3bf973516ea8aca94fd89a1fab6c5edb4dd141d0827db49e90a`.

Writers clear. No native execution or prior-root writes.
