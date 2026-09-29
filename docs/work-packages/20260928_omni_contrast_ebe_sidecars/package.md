# Omni Contrast EBE Sidecar Integrity

**Status**: Implemented; production verification delegated  
**Timezone**: UTC

## Overview

Omni contrasts created before the July 6, 2026 sidecar-preservation repair could omit `wepp/runs/chan.inp` when channel diagnostics were disabled. The WEPP watershed executable also uses that file to select event-by-event (EBE) outlet channels, so an EBE-enabled run could complete successfully while producing a header-only `ebe_pw0.txt` and zero-row `ebe_pw0.parquet`. This package makes that dependency executable, audits all inherited run sidecars, and repairs the affected `strategic-eloquence` contrasts on `wepp1` with semantic artifact readback.

## Scope

Included work is limited to Omni contrast run assembly, its focused regression tests and documentation, and regeneration of the 69 affected contrast runs for `strategic-eloquence`. No WEPP equations, parameters, schemas, queue topology, authentication, or parent/scenario outputs change.

## Failure Signature

- `ebe_pw0.txt` is exactly the 537-byte header and `ebe_pw0.parquet` has zero rows.
- `loss_pw0.out.parquet` nevertheless reports positive average annual outlet discharge.
- `wepp/runs/chan.inp` is absent from the contrast while the parent file selects outlet element `2784`.

## Durable Contract

The unchanged contract is in `wepppy/nodb/mods/omni/README.md`, “Execution Flow”: contrast clones preserve inherited base run sidecars, and disabled diagnostic switches do not remove them. This is a conformance and regression-hardening package, not an intended behavior change.

## Deliverables and Acceptance

- EBE-enabled contrasts ensure a readable `chan.inp` exists before WEPP executes, independent of the `chan_out` diagnostic flag.
- Contrast cloning has regression coverage proving regular parent run sidecars are inherited while `pw0.run` and `pw0.err` remain contrast-owned.
- Focused and broad applicable quality gates pass.
- Fresh `strategic-eloquence` contrast artifacts on `wepp1` have nonzero EBE rows for all contrasts, with direct Parquet metadata readback and successful run evidence.

The final production criterion remains pending. On 2026-09-29 the operator
directed Jackson to rerun `strategic-eloquence`; the previously queued Codex
repair jobs were canceled before any started to prevent duplicate execution.

## Security and Compatibility

Security impact is `none`: no request, authorization, secret, or execution-boundary change. Compatibility is additive hardening of an existing invariant. Existing sidecar contents remain authoritative and are not regenerated when present.

## Hardening Signals

Health signals are a present `chan.inp`, successful WEPP completion, and nonzero EBE rows where outlet discharge is positive. Danger signals are a header-only EBE file, zero-row EBE with positive outlet discharge, missing/broken inherited sidecars, or drift in contrast count. No temporary fallback or callus is introduced.
