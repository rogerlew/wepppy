# Attribute resolution defects and bounded repair plan

## Reproduction and consequence

`reproduce_resolution_inputs.py` calls the real Roads resolver and fill derivation without constructing/persisting a NoDb project. The retained JSON binds production source SHA256 `7aa5cd95f17b493e1f3543b607b2d67b717edced1fb8c574c5c516ebb2fa74df`.

- Invalid WIDTH_M=999, SOIL_TEXTURE=peat and RFG_PCT=bad consume defaults 4 m, loam and 20%, but all three `resolution_sources` claim `segment_property`. Valid sandy-loam aliases and numeric zero retain attribute provenance correctly.
- RFG_PCT=NaN becomes 100%; fill slope NaN becomes 150%; fill length NaN survives resolution then becomes 100 m in `_derive_fill_profile_from_inputs`. Positive infinity takes the same upper-bound path. These are unsupported numeric values converted into materially different inputs, not a legacy-model discrepancy.
- Finite out-of-range values currently have explicit established behavior: RFG120 clamps100; fill length999 resolves999 then clamps100; fill slope999 clamps150. Preserve these behaviors in this repair.
- Invalid fill text correctly falls back and records `roads_default`. Surface/traffic invalid-category resolution already correctly reports fallback. Required unrutted geometry checks finite values explicitly and rejects invalid fields; preserve that distinct required-field contract.

The same generic float reader is used by `_derive_buffer_profile_from_feature_or_defaults`, active for channel-associated rutted contributors. Its length/slope tests also omit finite checks, so NaN/positive infinity reaches clamp maxima rather than the ordinary invalid-attribute derivation. Include this confirmed shared consumer in the bounded repair; do not globally change `_coerce_float`.

This is production behavior: `query_segment_detail` returns resolution sources, and both additive and unrutted contributor paths call `_resolve_segment_run_inputs`. Soil and slope builders consume its values. Rutted summaries also count fill defaults by source label. The issue is neither research-only nor proof that retained valid-input histories are wrong.

## Canonical intent and compatibility

Roads `specification.md`, “Routing Eligibility Rules” / fill contract, requires configured defaults and counts when consumed; the later non-channel routed contributor text explicitly says fill attributes missing/invalid use configurable defaults. Current adjudication requires valid input/output accounting, and artifact observability treats provenance as user-facing records. Nonfinite values are invalid numeric attributes; handling them like unparsable values restores this behavior. Reporting the actual fallback source restores metadata truth without changing any numeric result for finite inputs.

No formula, threshold, default, unit, alias or finite out-of-range policy changes are proposed. Preserve existing JSON keys and source-label vocabulary. No saved-state migration. Legacy artifacts remain historical; newly resolved details and newly generated inputs gain accurate source labels and finite fallback values. Do not reinterpret old histories as newly generated evidence.

## Proposed minimal repair and regression plan

Track actual attribute validity for texture/RFG/width source labels. Add finite checks to the four numeric attribute resolution branches and the active buffer-profile fallback branches; existing invalid/missing fallback handles them. Keep required unrutted fields rejecting nonfinite values. Keep `_coerce_float` unchanged because a shared reader policy is unnecessary.

Use focused real resolver tests covering missing, malformed text, NaN, both infinities, valid zero, alias, finite bounds and finite out-of-range behavior. Read actual generated soil and slope artifacts after fallback. Verify buffer fallback derivation and required-unrutted rejection separately. Existing valid fixture source/input identity and source-publication expectations must be refreshed or explicitly marked stale where applicable; do not silently bless published results.

Independent correctness classification precedes implementation. This artifact proposes conformance work; it is not the human configuration-view approval gate.

## Commands and retained failed attempt

Successful reproduction: `wctl exec -T weppcloud python docs/work-packages/20261029_roads_parameterization_program/artifacts/reproduce_resolution_inputs.py` (exit 0). Output: `revised-input-resolution-reproduction.json`.

An initial `wctl exec -T wepppy ...` attempt failed before execution because service `wepppy` was not running; the running service is `weppcloud`. A local virtualenv pure-call attempt completed but logged Redis connection failures on import; it is not service-parity evidence. No service was started and no project/native run was executed.

## Implemented conformance correction

Independent classification accepted the bounded repair. `roads.py` now tracks actual texture/RFG/width fallback sources and handles nonfinite optional numeric attributes through the existing fallback branches, including the active buffer peer. `_coerce_float`, defaults, finite bounds and required-unrutted validation are unchanged. Repaired source SHA256: `7506718831d8a8b11ca0877cd75aa82596d0aeb900cf04505f29df864bd77a4d`.

Tests-first execution retained five failures and three passes before the patch (`revised-input-resolution-before.log`). After repair, the complete Roads controller test module passed: **59 passed**, two dependency deprecation warnings (`revised-input-resolution-after.log`). New tests parse actual generated three-OFE slope and soil files, covering width/fill/buffer fallback geometry and emitted road/fill/buffer RFG, plus finite clipping/aliases and mandatory unrutted rejection. This establishes prepared-input propagation, not native/browser/deployment parity. The separate disposable full-project sensitivity validation owns those broader boundaries.

The running-service pure reproduction was repeated into `revised-input-resolution-repaired.json`, preserving the original reproduction separately. Developer/operator clarification is in Roads specification “Attribute Discovery and Mapping Contract”; user guidance is in Roads ENDUSER “Upload Mapping: What The Controls Mean”. Both passed scoped `wctl doc-lint`. No ADR is required for this reviewed unchanged-policy conformance repair; no formula/default/finite threshold changes occur.
