# Return-period Omni comparisons tracker

Updated: 2026-10-10; closed after full sanity.

## Status

Closed (code/local validation; not deployed). Independent contract, correctness, and
security reviews approved after documented fixes.
Starting revision: `8b32a5c8c7d7eba52e947c8619b1dff2d8435e77`.
Contract ancestors: `c5358daa7`, reviewed artifact-path clarification `946ec76fb`.
Operator explicitly authorized committing and proceeding before these commits.

## Decisions

The initiating request authorizes unchecked completed-scenario selection,
scenario/date/value rows, and concatenated CSV. Durable contract and rationale:
`docs/ui-docs/contracts/return-period-omni-scenarios-contract.md`.
Current project remains included; simple mode only; no stored schema mutation.

## Outcome

Implemented in `d252ff056`, corrected in `99981ce36` against contract ancestor
`d89ace269`. Full Python sanity: 10,554 passed, 126 skipped. Final correction:
91 focused tests plus 2 staging tests, 933 frontend tests, and actual-project-copy
CSV validation. Initial Chromium smoke passes. No further implementation work.
Known unrelated lint and tooling limitations are retained in validation.md.
Completed plan: `prompts/completed/return_period_omni_execplan.md`.

## Notes

2026-10-10 17:26 UTC: active template and separate CSV path identified.
Discovery must distinguish completion from report readiness. No code changed.
Independent reviews resolved completion, containment, and CSV-label findings;
comparison cache bypass added to prevent method/interval cache reuse.
Documentation lint passed; standalone ancestor commit authority is outstanding.

2026-10-10 17:52 UTC: authority granted; checkpoints committed before source
changes. Implemented and reviewed; explicit-calendar dates, per-metric interval
sets, filtered-empty groups, and preserved empty-report metadata are covered.
Configuration screenshot recaptured and visually checked after reviewer note.

2026-10-10 correction: operator rejected READONLY discovery after actual
`eighty-five-synthetic/undisturbed` false negative. Reviewed ancestor `d89ace269`
replaces marker-based eligibility with output evidence and normal selected-child
staging; optional Outlet form guard fixes the separate deck.gl warning.
