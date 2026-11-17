# CILogon account security review gate

- **Security impact**: high (OIDC, local credentials, signed tokens, mail and secret configuration).
- **Reviewer**: independent `account_contract_security`, 2026-11-17.
- **Candidate**: task branch after accepted checkpoint `874de621c`.
- **Local verdict**: no unresolved medium/high source findings; see [independent implementation review](20261117_security_implementation_review.md) for threat boundaries, findings, evidence and residual risks.
- **Release verdict**: HOLD for the explicit environment/rollout gates in [validation](validation.md); no production activation authorized.

The original unassessed template is replaced by the actual review. Authentication/authorization, local credential eligibility, exact-address proof, callback validation, CSRF, token/session revocation, secret redaction, atomic writes, last-login protection, and legacy compatibility were reviewed. No filesystem upload, arbitrary execution, queue topology, new dependency, or privileged service is introduced. Existing Bootstrap project authorization remains enforced by stable ID with active-user/current-membership checks.

## Artifact observability

This feature produces account/link/verification records and private mail tokens, not hydrologic model outputs. Test, migration, mail-sink and browser receipts are retained in the package. Secrets, cookies and mailbox tokens must never be retained in browsable run artifacts. Production provider/mail/logging/secret-mount and PostgreSQL concurrency evidence remains pending; local fixtures do not prove that boundary.
