# MC4 reference and interface checkpoint

Status: validated narrow source checkpoint, committed locally at native
`e6dc19008ce83378508299b0e1efe4cf3844b198`. This checkpoint preserves Muskingum-Cunge
and does not complete the signed soil/channel exchange repair.

## Changes and rationale

The source/publication corrections admit deferred groundwater once, recover
ordinary channel-local water without side-hill surface runoff, and publish the
accepted MC outlet integral including time zero. Positive side-impoundment
release remains on its established path; KW3 publication is unchanged.

The v2 required 100-year run timed out at year16/day81 after 900 seconds.
MC4 selected a zero propagation reference despite live retained interior flow.
Its resulting zero-K recurrence repeats an alternating profile over even-step
days. V5 carries the last valid reference only for a degenerate boundary estimate
with live retained interior. It preserves ordinary reference selection and
resets per-channel history at simulation initialization.

A second problem is repeated finite-precision fixed points at 60-second steps.
V5 copies an exact repeated full raw profile and accepted outlet only when
future forcing is bitwise unchanged. It retains subnormals and signed zero.
The numeric-equality v4 shortcut was rejected by a signed-zero counterexample.
No numerical cutoff, midnight reset, geometric storage authority or replacement
routing equation is introduced. MC5 is excluded from both new MC4 mechanisms.

## Evidence

Both candidate profiles build with system gfortran and use the system ELF loader.
All 29 paired replays pass complete date/finite/transfer validation, including
400 years and 146097 daily records. Twelve full-period hillslope watchlist cases
and both profile host smokes pass. The host smokes exercise hillslope p1;
watershed coverage comes from the paired replay and execution fixtures.

Sixteen continuity and eight two-channel cascade controls pass the strict
complete-recurrence parser. Both cascade transfer errors are exactly zero.
These diagnostic builds explicitly disable the fixed-point shortcut and record
that in provenance. Portable tests separately compare every raw state and export
byte with the shortcut disabled: 60 pairs across both lateral modes, followed
by six causal/no-history cases. Twenty-six lifecycle tests cover reset, readonly
eligibility, channel isolation and MC3/5 exclusion. The combined final portable
suite passes 92 tests. Independent scientific and QA reviews are retained.

The exact previously failed gate now passes: two tests, two existing tarfile
warnings, 580.64 seconds. Its original 900-second timeout is unchanged; the trace
reaches year100/day365/channel31. The full native gate passes 490 tests with two existing warnings in 592.55 seconds.
Its collection preceded expansion of 30 additional mode cases, covered by the
final 92-test targeted run; the final suite collects 520 tests, all covered. The v2 failure remains retained
as rejected candidate evidence.

## Limits and continuation

Rate publication and downstream transfer now describe the same accepted export.
This is necessary for auditing but does not prove physical watershed closure.
Signed loss can be skipped before water arrives or yield raw negative discharge
that is clipped from export after soil has already received its daily credit.
Clipping also occurs in zero-loss MC5 controls. These mechanisms remain visible
in the independent ledgers; they are not assigned to a geometric storage residual.

Eight actual WATBAL/WSHDRV/WSHCHR early/late wet/dry controls now complete both
water-balance modes and confirm material requested loss and clipping. They also
identify a separate plane/element runoff alias under review. See
[actual-soil control review](actual-soil-coupling-control-review.md). A subsequent repair must make soil credit equal accepted
routing withdrawal under an explicit temporal/spatial coupling contract.
Neither a late scalar adjustment nor a new physical storage authority is approved.

No release, vendoring, default switch, push or deployment is included. Preserve
261021 outputs as history and regenerate all contributing hillslope/PASS/watershed
outputs together for every candidate comparison. The durable decision is in
ADR-0101, section “MC4 retained-state reference and exact fixed points,” and the
native physical-water routing contract.
