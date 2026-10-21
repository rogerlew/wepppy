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
