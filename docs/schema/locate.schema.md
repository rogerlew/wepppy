# `locate` Routine Contract
> Contract for the WEPP frost-layer locator routine (`locate`) used in the `frostn -> winter -> wshdrv` execution path.

## Normative Status

- This document is normative for `locate` boundary behavior and output invariants.
- Requirement keywords `MUST`, `MUST NOT`, `SHOULD`, and `MAY` are interpreted per RFC 2119.

## Scope

- Applies to the `locate(vardp, layern, flyern, tpbtfg)` routine behavior.
- Covers layer/fine-layer resolution, boundary handling, and guard semantics for numeric safety.
- Does not define full frost physics validity for upstream depth-state generation.

## Inputs and Units

### Inputs

- `vardp` (real): target depth provided by caller.
- `tpbtfg` (integer flag):
  - `0`: start-point semantics
  - `1`: end-point semantics at layer boundaries
- Profile/context arrays (implicit/common): `nsl(iplane)`, `nfine(layer)`, `dg(layer,iplane)`.

### Unit expectations

- `vardp` callers in frost/winter paths are expected to pass depth in meters.
- `locate` internally scales by `*1000` to millimeter domain for layer arithmetic.

## Output Invariants

On return, `locate` MUST ensure:

- `layern >= 1`
- `flyern >= 1`
- if profile metadata is valid (`nsl(iplane) >= 1`), then `layern <= nsl(iplane)`
- if `nfine(layern) > 0`, then `flyern <= nfine(layern)`

## Boundary and Error Semantics

### Minimum depth behavior

- If scaled depth `< 10 mm`, routine MUST return `layern=1`, `flyern=1`.

### Out-of-profile layer behavior

- If computed `layern < 1`, routine MUST clamp to `layern=1`, `flyern=1` and return.
- If computed `layern > nsl(iplane)`, routine MUST saturate to bottom valid layer (`layern=nsl(iplane)`) and return with:
  - `flyern=nfine(layern)` when `nfine(layern) > 0`
  - `flyern=1` when `nfine(layern) <= 0`

### Denominator protection

- If `nfine(layern) <= 0`, routine MUST return `flyern=1` (no divide).
- If computed fine-layer thickness denominator `fthick` is near-zero (`|fthick| < 1e-12`), routine MUST return `flyern=1` (no divide).

### Endpoint (`tpbtfg=1`) behavior

- Boundary decrement behavior MUST NOT produce `flyern < 1`.
- If endpoint logic decrements below valid range, routine MUST clamp `flyern` to `1`.

## Observability and Debug Signals

When observability is enabled (`wepp_observe.on`), guard-triggered conditions SHOULD emit:

- `LOC_GUARD_NSL`
- `LOC_GUARD_LYR`
- `LOC_GUARD_NFN`
- `LOC_GUARD_FTK`

Prior diagnostic tag family (`LOC_BAD_*`) MAY be used in observe-only lanes to isolate pre-guard trigger conditions.

## Contract Interpretation

- `locate` guards are a containment contract for runtime safety.
- Repeated guard activation SHOULD be treated as an upstream state-quality signal, not as proof of physically ideal behavior.
- Frequent `LOC_GUARD_LYR` events require follow-up in caller-side depth-generation logic (`frostn/winter` depth path).

## Compatibility and Change Management

- This contract is additive and backward-compatible at runfile interface level (no runfile key/format changes).
- Any change to `locate` clamp/fallback semantics MUST update this file in the same change set.
- If behavior is promoted to a broader runtime/API guarantee, a pointer or promotion into `docs/schemas/` MUST be added.

## Validation Requirements

At minimum, changes affecting `locate` MUST validate:

1. Baseline failing repro no longer traps (if applicable).
2. Guarded runs complete with success marker.
3. Existing instability regressions remain passing.
4. Guard-hit observability is captured and reviewed for residual risk.

## Implementation References

- `wepp-forest/src/locate.for` (routine implementation)
- `wepp-forest/src/frostn.for` (primary caller path)
- `wepp-forest/src/winter.for` (frost driver path)
- `wepp-forest/src/wepp_observe.for` (observability tags)
- Incident package: `wepp-forest/docs/ablation/20260419_operational-berry_pw0_sigfpe-locate-frostn/`
