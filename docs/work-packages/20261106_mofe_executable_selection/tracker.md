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
