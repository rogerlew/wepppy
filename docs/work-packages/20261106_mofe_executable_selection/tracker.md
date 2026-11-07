# MOFE executable selection tracker

- Confirmed on wepp1: five installed MOFE releases; incident run is flattened,
  TOPAZ/MOFE, without capability axes or graph; selector returns zero choices.
- Operator approved backend-independent executable compatibility on 2026-11-06.
- Canonical amendment prepared; two independent checkpoint reviews approved
  after disposition. See `artifacts/20261106_contract_reviews.md`.
- Operator authorized commit, push, scoped tests, and wepp1 hotfix; implementation follows this checkpoint.
- Next: obtain checkpoint commit authority, commit the
  checkpoint, then implement and validate all shared consumers.

## Decision log

Executable capabilities are independent of delineation backend. Preserve
separate Builder geometry authorization and stored model-authority pairs.
Canonical decision: `docs/schemas/wepp-executable-selection-contract.md`,
"Backend-independent executable compatibility (2026-11-06)".

## Implementation validation

Checkpoint ancestor: `ffc15f1da`. Shared selector and schema geometry separation
implemented. Independent reviewer approved after direct runtime-state and real
TOPAZ parser/save/reload regressions were added. Scoped tests requested by the
operator replace the broad sweep for this hotfix. Production candidate preflight
passed under web container uid 1002/gid 130 against the incident run without
mutating its state. Full model output regeneration is outside this hotfix check.

Scoped validation: 305 passed; independent review approved. Hotfix pending.
