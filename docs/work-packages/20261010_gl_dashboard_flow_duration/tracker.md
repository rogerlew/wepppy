# Flow-duration panel tracker

Updated: 2026-10-10. Phase: implementation and forest integration validated;
full Python suite running. Starting revision: `189d10649`.
Checkpoint ancestor: `c63f2cc52`; production edits followed its independent
contract correctness/security approvals. Security impact: high, reviewed.

## Completed

- Accepted daily m³/s, independent scenario records, Weibull ranks, ties/zeros,
  missing/invalid rules, default two-year exclusion and familiar Year selection.
- Implemented source radios, linear/log x, stable Omni labels/colors/visibility,
  hover and keyboard/touch inspection. No CSV or seasonal controls.
- Verified owned daily files/catalog entries, translated outlet IDs and bounded
  shared topology, including standalone pup and composite Omni-child views.
- Forest stack restarted via installed development `wctl restart`; all 25 running
  services verified, all four configured health checks healthy.
- Direct-source oracle matched authenticated browser values for both sources,
  baseline and undisturbed (15,706 eligible days each); both child URL forms passed.
- Correctness, QA and security reviews passed; all six security findings resolved
  and temporary authentication artifacts removed.

## Remaining gate

Retain final full Python suite outcome, final review addenda and implementation
commit. See [active plan](prompts/active/flow_duration_execplan.md) and
[validation evidence](artifacts/20261010_validation.md).

## Validation

951 Jest tests passed; 32 targeted Python tests passed; two authenticated FDC
browser tests passed. Existing GL suite: 30 passed, 14 skipped, three failures
reproduced with pre-change `c63f2cc52` JavaScript (raster labels/comparison selector).
Frontend lint retains the unrelated climate.test.js:300 conditional-expect error.
Scoped documentation lint and broad-exception check pass. Larger-population
ranking/caching benchmarks are retained; they are synthetic loader measurements,
not end-to-end browser performance guarantees.

## Decisions and limits

[Requirements](notes/requirements.md), the canonical FDC contract and ADR-0085
retain operator decisions and rationale. Each scenario uses its own record for
performance; periods and N are disclosed. GL has no Unitizer integration; m³/s is
fixed. Roads output scope is explicitly unavailable. Rain-on-snow control and
explanation are omitted per the final operator decision; no verified classifier exists.
No model outputs, schemas, simulations or unrelated working-tree edits changed.
Source caches/ownership are page-session snapshots; reload after regeneration.
