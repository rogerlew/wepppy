# ADR-0150: Separate native soil input capacity from calculation layers

Date: 2026-11-18
Status: Accepted and implemented in Linux release `wepp_261118`.

## Context

The 200 mm split makes Zepol's ten SSURGO horizons eleven and triggers the Python
capacity guard. Historical native readers silently discard excess records. A
full October 2026 national inventory finds 22 raw horizons, at most twenty after
necessary current validity filters, and five actual selected map-unit profiles
with 21 generated records. Eleven is insufficient nationally. Increasing global
`mxnsl` also changes calculation/output storage, including fixed output offsets.

## Decision

Set separate native reader scratch capacity `mxhzin=23`; keep `mxnsl=10`, depth
clipping/extension, property aggregation and physical formulas unchanged. Keep
all supported source horizons; explicitly reject counts above 23. Declare
integer input capacity in both digest-bound release sidecars. Python writers
and final native invocation enforce the selected executable's capacity. Absent
capability declarations mean ten; malformed or mismatched pairs fail explicitly.
Preserve historical binaries, defaults, saved selections and uploaded-file
admission/preservation behavior. No global relaxation for historical binaries.

## Rationale and alternatives

Twenty-three covers every observed raw source horizon plus one property-copying
split, without relying on present validity exclusions. Twenty-one is the exact
current-writer minimum but couples native capacity to those exclusions. Eleven
addresses only the initial incident. Global mxnsl expansion changes unrelated
state/output layouts. Merging or dropping horizons changes source properties;
minimum conductivity is not introduced. Larger arbitrary limits lack a measured
requirement. Future releases beyond 23 fail clearly and require a new evaluation.

## Validation, risk and rollback

Native reader tests covered 21, 22, and 23 horizons, explicit rejection at 24,
and mixed OFEs. The Puaulu and Zepol cases completed native runs. Legacy controls
produced byte-identical outputs. The disposable copy of the original project
completed 100 years across 355 hillslopes and 144 channels.

Both Linux binaries were built from commit
`464a5e5e15e1fbcdd4e8232260ecf79ad2645200`, now on the WEPP-Forest default
branch, `wepp_260430_negmeltfix_comparator`. The sidecars declare capacity 23
for the matched watershed and hillslope roles. The release ledger records their
SHA-256 hashes.

Retain the prior executable pair and input/output provenance for rollback.
A project with more than ten input horizons requires a compatible pair or a
known-good project snapshot with compatible inputs. The launch guard rejects
an incompatible selection before the model can truncate a profile.

## Decision provenance

Venue: operator/Codex conversation, 2026-11-18 America/Los_Angeles.
Participants: operator and Codex. Decision owner: operator, who authorized the
agreed plan and its work-package execution. Implementer: Codex. Change summary:
new selected native release supports 23 input records; historical capacity ten
and calculation capacity ten remain unchanged. No deployment/default migration
is inferred from accepting this implementation decision.

## Default selection amendment

On 2026-11-18 America/Los_Angeles, the operator directed Codex in this
conversation to change `[wepp] bin` from `wepp_261029` to `wepp_261118` wherever
that value was already the checked-in WEPPpy config default. The operator owns
the decision and Codex implemented it. The five configs are
`disturbed-mofe.cfg`, `disturbed9002-10-mofe.cfg`, `disturbed9002-10m-wbt.cfg`,
`disturbed9002-wbt-mofe.cfg`, and `disturbed9002_wbt.cfg`.

This makes the validated 23-horizon reader available by default to users of
these presets. Scope the change to the five presets because they already
selected the prior release. Saved project selections remain authoritative.
Reverting the preset values restores their earlier defaults. The rollback
constraints above still apply to projects with more than ten input horizons.

## Evidence

[National inventory](../investigations/2026-11-18-ssurgo-input-capacity/assessment.md),
[eleven-horizon evaluation](../work-packages/20261118_native_soil_input_capacity/artifacts/evaluation.md),
and [implementation package](../work-packages/20261118_soil_input_capacity_23/package.md).

[Release ledger](../binary-lifecycle.md) and [project replay](../work-packages/20261118_soil_input_capacity_23/artifacts/project-replay.md).
