# I-CREWS security review

## Metadata and triage

- Date: 2026-11-19.
- Independent reviewer: `icrews_contract_access`.
- Candidate branch: `task/i-crews-interface`.
- Security impact: high. The legacy creation handler must enforce ownership of the Idaho boundary and mode.
- Review scope: create request merging, named-preset selection, allowed overrides, allocation order, saved run identity and static map overlay.
- Related evidence: [Contract decision](20261119_contract_decision.md), [correctness review](20261119_correctness_review.md) and [validation](20261119_validation.md).

## Findings and disposition

| Finding | Evidence and disposition |
| --- | --- |
| Legacy configuration selection could bypass the new ownership check. | The final check uses the same pathlib basename behavior as the config loader. Tests reject slash and dot variants, inline arguments and unowned boundary settings in both creation modes, before allocation. The reviewer approved the fix. |
| The corrected MOFE source changes the inherited backend and executable. | Both reviewers rechecked `ac1e41236`. The WBT-MOFE source shares the same allowed override set and requires no access policy change. |

## Surface checks

- Access uses existing role, auth, CAPTCHA, and creation controls. The card
  exposes each form only when its preset is visible to the current user.
- Both creation modes validate canonical I-CREWS IDs and source-approved
  overrides before allocation. The legacy mode serializes only validated
  overrides for the two named presets. Normal unit overrides and an ordinary
  legacy preset remain covered.
- The static overlay uses the packaged Census polygon and the application
  static URL. The run footer and overlay opt-in use the saved preset identity.
- The work adds no endpoint, queue edge, credential, third-party fetch, or service
  dependency. Snapshot persistence and creation reservations use existing
  storage and idempotency paths.

## Verdict

Independent source review passed with zero unresolved medium or high
findings. The tests exercise valid and rejected requests through the actual
handler and resolver. External CAPTCHA verification and deployment use
the existing service paths.
