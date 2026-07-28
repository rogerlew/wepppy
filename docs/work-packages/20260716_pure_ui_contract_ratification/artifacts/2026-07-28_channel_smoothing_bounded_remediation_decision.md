# GOV-00A Bounded Channel Smoothing Remediation Decision

**Milestone**: GOV-00A-M1E
**Remediation**: REM-05
**Borrowed owner**: DOM-05
**Dated package**:
`docs/work-packages/20260728_channel_depression_smoothing_fix/`

## Decision

Register the operator-authorized Channel Delineation production defect as a
bounded remediation. REM-05 borrows only the depression-smoothing selector's
rendered name, canonical request token, existing worker mutation, persistence,
and reload boundary from DOM-05.

The exact accepted behavior is defined in the REM-05 contract decision. A
rendered valid selection must submit a non-null `wbt_fill_or_breach` token,
which the existing worker persists before channel construction and the page
hydrates after reload.

## Authority

On 2026-07-28 UTC the operator reported the wepp1 production defect, supplied
the null request payload, directed Codex to fix the contract and error, commit
and push all local commits, then pull and deploy WEPPcloud on wepp1. This
authorizes the finite contract, dual independent reviews, standalone checkpoint
ancestor, implementation, publication, and deployment.

GOV-00A-M1E becomes effective only when this registration, the REM-05 contract
decision, both checkpoint reviews, and their disposition are committed together
as a standalone documentation-only ancestor.

## Exclusions

REM-05 does not change algorithms, defaults, enum tokens, map behavior, uploads,
route parsing, queue wiring, NoDb schema, authorization, CSRF, or other DOM-05
fields. DOM-05 remains planned and unverified.

## Security and Compatibility

Security impact is high because DOM-05 crosses a browser-to-RQ mutation
boundary. The patch must use the existing canonical key and validation path,
add no new input or alias, and preserve every valid old run and token. Only the
incorrect browser-created null becomes the selected token.
