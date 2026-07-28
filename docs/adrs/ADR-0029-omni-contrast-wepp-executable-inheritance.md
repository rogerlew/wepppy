# ADR-0029: Omni Contrast WEPP Executable Inheritance

Status: Accepted
Date: 2026-07-28

## Context

Omni contrast runs are child simulations of a configured parent WEPPcloud
project. The parent project's persisted `wepp.nodb` records both its selected
WEPP executable and pass-family contract.

The contrast wrapper retained a historical `wepp_dcc52a6` default after an
inheritance path was added to the clone service. Because the wrapper always
supplied that default, the clone service never inherited the parent selection.
The latent inheritance branch also referenced service state that did not exist
and would have produced a one-element tuple because of a trailing comma.

This mismatch caused HBP-enabled projects to combine `pass_family=hbp` with the
legacy `wepp_dcc52a6` executable. Release-sidecar validation correctly rejected
that incompatible pairing before the watershed run was built.

## Decision

Omni contrast child runs inherit `wepp_bin` from the parent project's persisted
`Wepp` instance by default. An internal caller may still provide an explicit
string override, which takes precedence for that contrast run.

The contrast wrapper therefore defaults its optional override to `None`. The
clone service resolves `None` by loading the parent `Wepp` instance at the
original run working directory and copying its `wepp_bin` string into the
contrast clone.

## Decision Provenance

Decision Venue: Codex API conversation, 2026-07-28 10:00 PDT
Participants Present: Roger Lew, Codex
Decision Owner(s): Roger Lew, WEPPpy maintainer
Implementer(s): Codex

## Change Summary

Old behavior: the normal Omni contrast orchestration path always selected
`wepp_dcc52a6`, regardless of the executable persisted in the parent
`wepp.nodb`.

New behavior: the normal path inherits the parent's persisted executable.
Explicit internal overrides remain supported.

## Rationale

A contrast is derived from the parent project and consumes hillslope pass files
created under the parent's executable and pass-family contract. Inheriting the
parent selection keeps watershed aggregation compatible with those artifacts
and preserves executable provenance across the comparison.

## Alternatives Considered

1. Add HBP sidecars to `wepp_dcc52a6` - rejected because the legacy executable
   does not implement the HBP release contract.
2. Change the hard-coded contrast default to the newest dated binary - rejected
   because that would drift again and would not preserve per-project provenance.
3. Force every contrast caller to pass an executable - rejected because the
   persisted parent `wepp.nodb` is already the authoritative project selection.

## Consequences

Existing projects now run new Omni contrasts with their own persisted WEPP
selection. Results may differ from historical contrasts that were silently
pinned to `wepp_dcc52a6`; their existing artifacts remain unchanged.

An explicit internal override can still produce a different executable choice,
so callers using that seam remain responsible for pass-family compatibility.
The existing binary-sidecar validation continues to fail incompatible pairings
explicitly.

## Evidence

- Production host: `wepp1`.
- Run: `mdobre-foursquare-fovea`.
- Failed job: `af8cae6d-5c72-4867-a78d-8a6ed73fa984`.
- Parent state: `wepp_bin=wepp_260727`, `pass_family=hbp`.
- Failure state: the contrast wrapper supplied `wepp_dcc52a6`, whose HBP release
  sidecar is intentionally absent.

## Risk and Rollback Notes

The behavioral risk is expected output drift for users who unknowingly relied
on the historical contrast-only pin. That pin was not represented in project
state and was incompatible with HBP parent runs. Rollback is the small wrapper
and clone-service change, but doing so would restore the confirmed provenance
defect.

## Implementation Notes

Regression coverage must execute the public `_run_contrast` seam without an
override and assert that the contrast clone receives the parent `Wepp.wepp_bin`
as a string.
