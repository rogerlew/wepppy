# I-CREWS interface tracker

## Status

Implemented and locally validated on 2026-11-19. The
[ExecPlan](prompts/completed/implementation_execplan.md) records the scope and
[validation](artifacts/20261119_validation.md) records the gate results and
limits of local verification.

## Tasks

- [x] Review the source presets, Idaho asset, card copy and attribution.
- [x] Ratify the launch contract in `9867163fb` and corrected WBT-MOFE
  lineage in `ac1e41236`.
- [x] Install the two presets, add the card and enable the Idaho outline
  and funding credit on both direct run pages.
- [x] Verify both creation modes, WBT variants and prepared MOFE inputs.
- [x] Complete independent correctness and security review.
- [ ] Rerun the repository suite after the baseline SSURGO fixture is fixed.

## Decisions

Both configs default to WBT. The MOFE source is
`disturbed9002-wbt-mofe.cfg` and retains its five-element maximum,
`wepp_261118` and RAP time series. Both configs use `intersects`, the same
Census polygon, center `[45.6, -114.15]` and zoom `5`. The card and two runs
use public Preview access, normal creation controls and the Idaho EPSCoR
acknowledgment and disclaimer. See the
[canonical contract](../../ui-docs/contracts/i-crews-interface-contract.md).

## Evidence

- [Contract and correction](artifacts/20261119_contract_decision.md).
- [Validation](artifacts/20261119_validation.md).
- [Correctness review](artifacts/20261119_correctness_review.md).
- [Security review](artifacts/20261119_security_review.md).
