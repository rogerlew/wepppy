# Current VPAT Manifest

This file tracks the mutable staging package for the next buyer-facing WEPPcloud VPAT / ACR issue.

## Snapshot

| Field | Current value |
| --- | --- |
| Status | Staging package in progress |
| Intended final artifact | `VPAT 2.5Rev INT` |
| Official template version | April 2025 |
| Current worksheet source | `docs/ui-docs/acr-draft-int.md` |
| Current strategy source | `docs/ui-docs/accessiblity.md` |
| Current manual pass source | `docs/ui-docs/manual-at-pass-20260331.md` |
| Evaluated repository snapshot | `bb0fbb1cb` |
| Draft package date | March 31, 2026 |
| Deployment posture | Refresh before the next production deployment if any tracked conformance trigger changes |
| Archive rule | Issue to `issued/YYYY-MM-DD_<shortsha>/` only when the production-bound snapshot is frozen |
| Latest issued package | `docs/ui-docs/vpats/issued/2026-03-31_bb0fbb1cb/` |

## Current Decisions

- Conformance baseline remains the AA-validated theme set.
- Sensory-preference themes remain user-visible in federal-buyer deployments as supplemental user-choice themes outside the conformance set.
- The manual-evidence boundary for the current issue is the documented local browser / operating system / assistive-technology matrix rather than a separate spoken screen-reader matrix.

## Next Transfer Step

- Convert `docs/ui-docs/acr-draft-int.md` into the official ITI template once the production-bound snapshot and evaluator details are frozen.
