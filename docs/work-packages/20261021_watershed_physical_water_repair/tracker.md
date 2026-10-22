# Watershed physical water repair tracker

## Status

Active execution, explicitly requested 2026-10-21. Audit checkpoint: `e85d582ed`.
Three narrow source corrections are validated. An MC-preserving consistency audit
has identified the publication/transfer boundary and a separate interior-state
execution defect. Full watershed closure and release readiness remain open.
Security impact low; no dedicated security review required for this scope.

## Task board

- [x] Commit predecessor audit and scaffold repair scope.
- [x] M1: portable failing controls and independent science/QA reviews.
- [x] M2a: total-area initial groundwater correction and full-period controls.
- [x] M2b: complete bounded hourly allocation and native observation parity.
- [x] M2c source cells: flat overlap correction and fine-grid/duration controls.
- [ ] M2c solver interface: reconcile source volume with actual MC quadrature.
- [ ] M2d: signed channel-local exchange and deferred baseflow assembly.
- [x] Additional MC control: preserve nonzero interior state at dry boundaries;
  eight focused tests pass, including MC4/MC5 and all-zero controls.
- [x] Actual two-channel trace identifies conflicting rate/daily-volume transfers.
- [ ] M3: consistent combined source/storage-increment/export accounting.
- [ ] M4: full routing acceptance, final review and release-readiness handoff.

## Decisions

Preserve the closed audit and 261021 release. Ash, dated release/vendoring,
deployment and original-project mutation remain excluded. Native default branch
is the repair baseline; unrelated HBP work is untouched.

The operator rejected geometric-volume authority and authorized preserving MC
dynamics. ADR-0101, section **MC continuity decision (operator authorized)**,
supersedes the earlier physical-volume recommendation. Assess MC using its
implemented increments, coefficient/grid transitions and accepted transfers;
geometric equality is not an acceptance gate.

The interior-state correction changes only recurrence eligibility. It does not
change Manning relations, coefficient formulas, storage definitions or clipping.
A seeded admissible profile proves this defect; it does not establish its frequency
in field projects. The publication mismatch remains a separate open repair.

## Validation

Narrow candidate v4: 361 passed, four strict expected failures; 12 watchlist cases,
both smoke checks and 29 paired replay date/transfer validations passed.
Native hourly observations cover 44 years for one/two/three OFEs, with zero
unallocated remainders and unchanged scientific outputs.

MC guard candidate: 165 targeted checks pass, four channel-local expected failures
remain. Both profiles built; 29 fresh paired runs completed, including 400 years.
Full suite: 369 passed, four expected failures; 12 watchlist cases and both smokes pass. All 29 replay date/transfer validations pass. See `artifacts/repair-handoff.md`.

MC diagnostics: 16 single-channel controls, eight actual two-channel controls,
independent probe parity, corrupted-record rejection and full-node observations.
See `artifacts/mc-continuity-findings.md`, scientific review and QA review.

## Next boundary

Reconcile interval/point source integration, signed exchange and deferred baseflow,
then make accepted outlet flux and daily publication/downstream transfer agree.
Do not normalize the outlet or invent geometric storage from a residual. Retain
explicit coefficient/grid/clipping terms and full-period dates. No full routing
acceptance is asserted while these boundaries remain unresolved.

## Active follow-on experiment

Checkpoint commits: native `22133f0c9`, WEPPpy `8fa7a8d9b`, not pushed.
The isolated MC publication candidate uses the accepted outlet integral and
independent geometric diagnostics, including q0 in peak metadata. Test source
carry, MC recurrence parity, actual cascade transfer and downstream effects
before any promotion. See `mc-interface-repair-design-review.md`.

Publication-only experiment: all 24 controlled cases agree with accepted outlet
flux within final binary32 rounding; all 29 fresh paired replays pass dates and
transfer checks. Combined `mc-interface-candidate-v2` is built and replaying.
Its full first-day MC4/5 baseflow tests route 100 m³ once and preserve next-day
boundary carry. Twenty-four source controls preserve side impoundment, positive
side-hill, zero/negative net and below-threshold comparators. The earlier candidate
is rejected for duplicate first-day baseflow; see scientific review. Signed-loss
availability and threshold-cascade review remain open.

Both reviews now support scoped source promotion, conditional on final gates.
All 29 combined replay validations pass. Signed-coupling controls demonstrate
a mismatch even with positive MC coefficients; that boundary remains open.
See `artifacts/mc-interface-checkpoint.md` for the current source/acceptance
distinction, observational clipping totals and required coupling contract.

**Promotion blocked:** explicit v2 binary times out in the required 100-year
upstream-scheme test after 900 s at year 16/day 81. Full suite: 409 passed, one failed; final
interface: 55 passed, watchlist: 12 passed and both smokes passed do not override this failure.
Current native changes remain uncommitted candidates. State-aware MC reference
handling is under isolated investigation; see the current validation receipt.


## MC4 reference continuation

The v2 timeout is retained as a failed gate. Reviewed v5 carries the previous
valid MC4 reference only for degenerate boundary estimates with live interior,
and preserves exact repeated states through bitwise fixed-point copying.
Independent 26-pair raw-array and 26-check lifecycle reviews pass. Both profiles
build and all 29 paired replay validations pass. Exact failed gate passes all 100 years in 580.64 s within the unchanged 900 s timeout; full
native suite passes 490 tests and the expanded reference suite passes 92 tests; signed soil/routing coupling remains open.
See `artifacts/mc-reference-state-review.md` and `mc-reference-qa-review.md`.

2026-10-21 — Native source/interface/reference checkpoint committed locally as
`e6dc19008ce83378508299b0e1efe4cf3844b198`; native worktree clean. No push,
release or vendoring. The package remains active for signed soil/routing coupling.


## Actual-soil coupling controls

Eight full two-year wet/dry × early/late × daily/hourly runs pass full calendar,
receiving-channel isolation and observer parity checks. Actual dry-day demand
is 37.8908/38.8419 m³, with material raw-to-export clipping; signed-coupling
closure remains open. Read-only tracing also confirms upstream runoff depth
contaminates the next channel's soil-plane slot when WSHIRS is skipped. A
bounded initialization repair is under review; no alias repair is promoted yet.
See `artifacts/actual-soil-coupling-control-review.md` and
`artifacts/mc-coupled-soil-qa-review.md`.


The alias candidate is isolated under `channel-plane-init-candidate-v1` and in
uncommitted native WSHDRV working source. Both profiles build; full native suite,
29 paired replays and independent causal controls are running. ADR-0101 records
the working-flux lifetime and rejects forwarding inherited runoff as a repair.


Channel-plane candidate: full native suite **520 passed**, two existing warnings,
618.33 s; final trace reaches year100/day365/channel31 within the existing
900-second gate. All 29 paired validations (including 400 years), 12 watchlist
cases, both profile smokes and system ELF loaders pass. Independent causal
review covers 96 runs and 1,800 exact observer file pairs. Final portable
regressions and source checkpoint are pending. Signed soil/routing acceptance
remains open.


Final channel-plane portable target: **7 passed in 115.93 s**. All 527 collected
native tests are covered (520 full suite plus seven added afterward). Independent
science and QA reviews approve this bounded initialization. The source checkpoint
is ready; signed withdrawal/soil-credit acceptance remains unresolved. See
`artifacts/channel-plane-initialization-checkpoint.md`.


2026-10-21 — Validated channel working-flux repair committed locally at native
`d354e3c998f81955f9d9e5ca7d01ca56e1a9f04b`. Native worktree clean. No push,
release, vendoring or deployment. Signed withdrawal/soil credit remains open;
retain the package as active.
