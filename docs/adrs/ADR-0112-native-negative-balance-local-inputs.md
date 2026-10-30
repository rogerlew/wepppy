# ADR-0112: Retain local inputs in native signed water balances

Status: Accepted, 2026-10-30; explicit matched Linux release selection.
Date: 2026-10-29

## Context

The Roads parameterization study traced a native `wepp_261026` failure to a
negative-balance reset that omits net local rainfall. The observed change from
-22.576984 to -61.153371 mm discards 38.576386 mm before the hourly allocator.
The same failure class exists in the daily calculation. This is separate from
generated-soil normalization at 200 mm (ADR-0110).

## Decision

Implement the local-input correction in WEPP-forest and target a matched Linux
`wepp_261029` pair, retaining the canonical branch's portability changes and
`wepp_261026` as a historical control. Validate native regressions, the Disturbed
matrix and Cedar Creek semantics; author release notes with figures. Do not change
existing project defaults or deploy as part of this decision.

Removing the reset also exposes a later
hourly timing failure in the Roads reproducer. On 2026-10-30 the operator explicitly
authorized an ablation package to correct that failure and add a fixture. The
native `20261030-hourly-return-flow-timing` package is now a release prerequisite.
The accepted approximation attributes routed upstream surface-return water to its
existing hourly support, preserving the daily input sum and inventory guards.
No future-water borrowing or deferred-deficit forgiveness is authorized.

## Decision provenance

Decision Venue: this development conversation, 2026-10-29, America/Los_Angeles;
exact message time not retained.
Participants Present: requesting operator and Codex.
Decision Owner: requesting operator, explicitly directing the native work package,
261029 release, Disturbed/Cedar validation and illustrated notes.
Implementer: Codex.

The operator separately confirmed: keep the portability changes. This supersedes
the Roads charter's earlier exact-261026 freeze, without changing its scientific
acceptance criteria or consuming withheld validation soils.

## Change summary and rationale

Before: a negative sum of net local inputs and routed water is replaced by a
runoff-only expression. After: retain the complete sum.
The hourly inventory checks and daily positive-only allocation remain unchanged.
Daily channel subsurface water is added to the complete balance, so local inputs
remain available when the combined result becomes positive.

The accounting identity is independent of soil calibration. Restoring local
inputs is preferable to changing conductivity to evade the failure or weakening
the inventory check. The original trace reproduced all seven native outputs
byte-for-byte; calculation probes cover rainfall/interception, melt, irrigation,
channels, downstream elements and zero crossings.

## Alternatives considered

- Tune soil parameters around the stop: rejected because it hides a model defect.
- Clip negative balances or discard unmet withdrawals: rejected because it breaks
  conservation and masks insufficient water.
- Change the shared 200 mm normalization: unrelated to this arithmetic defect.
- Treat the initial patch as full signed-exchange repair: rejected; the later
  failure and the preexisting routing contract show that claim is unsupported.
- Revert portability changes: explicitly rejected by the operator.

## Consequences, risk and rollback

The change affects shared native code beyond Roads. Existing projects retain their
selected binary; adopting a new release requires regenerating matched hillslope
and watershed outputs, including PASS files. Preserve historical executables for
rollback. Do not label a passing numerical sediment screen as physical acceptance.
Native failure, unexplained water/sediment behavior or failed release gates blocks
promotion. Daily and hourly semantics must be assessed separately.

## Evidence and implementation

- [Roads program](../work-packages/20261029_roads_parameterization_program/package.md).
- [Original defect and portable reproducer](../work-packages/20261029_roads_parameterization_program/artifacts/native-water-accounting-decision.md).
- Native package: WEPP-forest
  `docs/work-packages/20261029-negative-fin-water-accounting/`.
- Native contract: `docs/contracts/physical-water-routing-contract.md`.
- Native tests: `tests/test_negative_fin_local_inputs.py` and
  `tests/test_physical_water.py`; final focused suite passes 262 checks; full native suite passes 663.
- Native illustrated report: `docs/release-notes/wepp_261029/`.

Acceptance evidence and exact release identities are retained in the
[release package](../work-packages/20261030_wepp_261029_release/package.md).

## Authorized timing and ET consumer ablation (2026-10-30)

The operator authorized the separate timing correction and permanent fixture.
The candidate attributes the routed portion of upstream surface return to the
hours in which that return exists, preserving the signed daily exchange and
retaining actual-stock failure for any unfunded remainder. This is proportional
source-time attribution, not a new transport/travel-time model. Independent AI scientific and implementation reviews accepted this bounded
approximation on 2026-10-30.

The full fixture exposed two confirmed shared ET consumers: EVAPPM re-added FIN
to already updated stock, and its final rooted-layer calculation replaced the
root integral with surface evaporation water. Separate source-block probes and
full replays support removing the duplicate adjustment and preserving the root
integral. Both daily and hourly callers use updated stock, so effects extend
beyond Roads. Timing-only replay produced 17 negative Ep records; the corrected
ET lanes produce none across 17,532 water records. Do not clip negative ET as a
substitute for correcting its input accounting.

ELEMENT PeakRO also overflowed its seven-character field. A widened-field attempt
was rejected by the production Rust parser. Preserve fixed widths and ordinary
three-decimal values; permit compact lower-precision printing only for formerly
unreadable overflowing values. Native and interchange acceptance must both pass.

Native work package: `docs/work-packages/20261030-hourly-return-flow-timing/`.
Full native, Roads, Disturbed and Cedar validations pass. The 96-case Roads
result is a frozen development screen, not withheld-soil or field acceptance.
The operator accepted the report and authorized independent review agents on
2026-10-30. Both science and implementation reviews found no release blockers.
Daily allocation applies only positive FIN; negative daily FIN remains
unallocated and must not be independently debited by EVAPPM. The wider daily
signed-exchange boundary remains open.

Release source: 631aed1d1c89ed8fa76c5dc3f2e4258a8f199504. The dated pair is
byte-identical to the candidate used for the complete scientific studies.
Cedar changes relative to 261026 are -0.41035% published volume and +0.13751%
sediment; screened event peak differences span -10.68% to +4.25%. Portability
alone changes sediment by +0.66654%, so these are not all accounting effects.
No project default, soil normalization or Roads parameterization default changes.
