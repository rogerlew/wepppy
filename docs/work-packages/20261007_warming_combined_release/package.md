# Warming championship combined release validation

**Status**: Closed (2026-10-07 22:14 UTC), research comparison complete  
**Timezone**: UTC

## Overview

Test whether daily totalwatsed streamflow from the combined `wepp_261007`
release at 10 cm initial random roughness is negligibly different from
`wepp_260803` at 10 cm. Include `wepp_260803` at 17 cm as the alternative
roughness intervention. Agreement is a hypothesis, not a required conclusion.

## Scope and objectives

Run all three cases afresh on forest using the frozen warming-championship
inputs from the 6 October experiment, covering 1980–2003. Preserve initial
states, climate, geometry and baseflow settings. Produce native totalwatsed
outputs, NSE, original KGE (2009), squared Pearson correlation, bias and daily
departures for both totalwatsed and routed channel discharge; inspect comparison
figures manually. Assess outlet discharge at daily and 600-second resolution,
including event peak magnitude and timing. Separately compare sampled
outlet flow with the channel volume ledger. Daily totalwatsed is hillslope
surface runoff plus lateral flow plus postprocessed baseflow; it is not routed
channel discharge and cannot independently validate channel conservation.

The baseline is always `wepp_260803` at 10 cm. Change only management records
whose rrinit is exactly 0.10 m in the 17 cm case. Do not change production,
defaults, model source or previously closed packages.

## Complexity budget

Reuse the retained offline runner, management reader, native wepppyo3
interchange, totalwatsed3, NumPy, pandas and matplotlib. No new dependencies,
services or execution infrastructure. First test the exact vendored binaries
with existing frozen inputs; do not construct a surrogate build.

## Generated artefact validation gate

Record binary and sidecar hashes, source identities, parsed rrinit inventory,
relative-path input and output manifests, terminal success and fresh PASS/WAT
conversion with zero rejected records. Require exactly 8,766 unique aligned
dates, finite nonnegative streamflow and identical watershed areas. Read back
the saved comparison data used in figures. The direct boundary is the real
binary consuming staged native model input and native interchange consuming
its fresh output. This is an offline model-input replay, not a NoDb clone or a
production workflow/deployment test. Keep full raw evidence on forest and
compact evidence in this package.

## Success criteria

- [x] Three verified fresh same-build hillslope and watershed runs.
- [x] Input isolation, binary identity, date/unit/component checks pass.
- [x] Tested metrics and comparison figures, including small-event departures.
- [x] Manual assessment and explicit hypothesis disposition.
- [x] Outlet diagnostics reported separately without overstating closure.

The provisional screening criterion, declared before executing models, is
absolute total-yield bias ≤0.1% and daily NSE, KGE and R² ≥0.999 for the new
10 cm case. This is a study-specific screen, not a universal scientific
equivalence standard or user-ratified tolerance. Report worst daily and event
departures regardless of aggregate pass/fail. No fitting, lag adjustment,
warm-up exclusion or deletion of inconvenient days is permitted.

## Security and parameterisation

Security impact: none; no dedicated security review required. Only fixed
scientific binaries and isolated research paths are used; no credentials or
external services change. No production parameterisation change and no ADR
required: 17 cm is an explicitly requested experimental perturbation, not a
new default. Roger is the decision owner; Codex implements and reviews this
bounded validation.

## Dependencies and unresolved risks

The recut has watershed SHA256
`ad5ef3e31be7e6da2517567fb211fe350cb7ff0ea9320282368182cb6157127b`
and hillslope SHA256
`cba2927f489a324774180164f1b8065118fb3a1fa6b64737710b46b0f96036df`,
source `669ff4106a4158e49dc79e038026e4d63a489923`, vendoring `918b3ca0a`.
The earlier same-name cut is excluded. Channel repair follow-ups HV-02 and
HV-05 remain open; this package does not assume they are resolved.

Related immutable packages are `20261006_warming_rrinit` and
`20261006_warming_rrinit_legacy`. Raw work will be retained at
`/workdir/warming-combined-release-20261007` on forest. No temporary production
mitigations are introduced. The observation window is the full 24-year model
record; site-specific model agreement is not validation against observations.

## Deliverables

The [results](results.md), [methods](methods.md), [validation review](validation-review.md),
completed execution plan, runner, tested metric/plot scripts, input/output
evidence, paired data and six figures are retained within this package.

## Closure

All 2,596 executions pass; native conversion rejects no records; 18,168 raw
output hashes, consumed inputs, historical legacy reproduction and seven-file
observer parity pass. Six metric/date tests and independent daily metric
recalculation pass. All six figures were manually inspected.

The yield-preservation hypothesis is supported, but routed-flow negligibility
is not: daily outlet KGE is 0.970290 and sampled volume bias is −0.598043%.
The October 1994 sampled-integral/ledger deficit is still 18.08%. This closes
the requested comparison, not HV-02/HV-05, release approval or physical
conservation validation. No production changes were made.
