# ADR-0155: Increase Linux WEPP watershed capacity

Status: Accepted
Date: 2026-11-21

## Context

The `diagonal-intersection` watershed has 47,582 hillslopes and 22,081
channels. WEPP 261118 rejected the hillslope count, then consumed subsequent
run-file lines while asking for a valid count. The job ended when the shifted
input sequence treated a channel output path as an existing hillslope pass file.
The channel count also exceeds the 261118 capacity.

## Decision

Offer `wepp_261121` and its matching `wepp_261121_hill` build as an explicit
Linux executable selection. The watershed build supports 50,000 hillslopes
and 25,000 channels, up from 45,000 and 15,000. The combined element capacity
is 75,025, including room for 25 impoundments. The two watershed plant and
management type dimensions are each 25,000. Existing executable selections and
preset defaults retain their current mappings.

## Rationale and alternatives

The selected bounds accommodate the reported watershed at its existing
delineation. Coarsening the channel network would change the modeled watershed.
The matched release keeps the pass-file producer and consumer on the same
build. The hillslope-only binary keeps its dedicated dimensions.

## Decision provenance

The WEPPcloud operator chose the limits and release tag in the November 21,
2026 task conversation (Pacific Standard Time). Codex implemented the change.

## Evidence and rollback

The failed watershed task is recorded in the
[RQ job tree](https://wepp.cloud/rq-engine/api/jobinfo/a8a04dd2-b704-4ecc-bfef-841d1ba198bb).
See the [binary release log](../binary-lifecycle.md#vendored-wepp-release-log)
for build identity and validation. A bounds-checked input test exercised all
75,025 element slots. A one-year fixture with 77 hillslopes and 31 channels
completed with six output files identical to 261118. It measured 7.34 GiB peak
resident RAM for 261121 compared with 2.75 GiB for 261118. The expanded static
arrays reserve 35.75 GiB of virtual address space per watershed process.
A full simulation near the new limits remains unverified.

Keeping the prior executable available lets operators return to it for
watersheds that fit its limits.
