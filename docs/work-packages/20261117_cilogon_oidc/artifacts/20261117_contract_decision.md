# Account contract decision checkpoint

**Starting implementation revision**: `3950b57520c029c75df67565238b94543a31b03a`.  
**Branch/worktree**: `work/cilogon-oidc-scaffold`, `/home/workdir/wepppy-cilogon-oidc`.  
**Status**: Documentation reviewed; all security/correctness findings closed on independent readback; OPEN-P1 unresolved; not a committed implementation checkpoint.

## Operator authority and normative delta

Operator: “we could just make cilogon accounts independent regardless of email but allow google, github to prove ownership and the same account.” The operator accepted the assistant's explanation of distinct CILogon projects and safe shared-account recovery. They approved the exact login-page wording with “that will work.” Earlier instructions require new-local email verification before access, existing local login preservation, responsive normal User Profile, verification card/send action, and a prompt after OAuth login to unverified local credentials.

The current request explicitly authorizes work-package/contract updates, review dispatch, and finding disposition. No code implementation, production deployment/migration, or new credential activation occurs in this task. Email-first password selection remains a recommendation, not an accepted user decision.

## Applicable current contracts

- `docs/schemas/weppcloud-account-email-verification-contract.md`: provider identity/account classes, exact UI copy, lifecycle, recovery, provenance, migration, acceptance.
- `docs/schemas/weppcloud-session-contract.md`: no new-local session/token bypass; grandfathering; CILogon account separation; reset versus verify effects.
- `docs/schemas/weppcloud-csrf-contract.md`: verification send/completion POST boundaries.
- `docs/schemas/safe-traceback-contract.md`: secret-source and signed-link diagnostics.
- Existing UI presentation and user-facing language standards remain applicable without normative changes.

## Rationale and compatibility

Independent CILogon users avoid uncertain federated-email ownership assumptions. Shared Google/GitHub verified-email matching preserves one account with local credentials. Proposed additive contact/class/provenance fields keep unique shared-login email instead of weakening uniqueness. Preserve user IDs, roles, run foreign keys, local hashes, and ORCID links; cross-account recovery and NULL-email consumers require explicit migration tests. No new infrastructure.

Security impact is high. Expected failure states and concrete acceptance matrices live in the canonical account contract. Discrepancy classification: intended new behavior, not a repair claim for every existing provider. Historical finding SEC-01 is removed from scope by the independent CILogon policy, not accepted as an unconditional-email trust risk.

## Checkpoint gate

Reviewers must evaluate current documents, then the primary agent records dispositions and requests only unresolved product choices. Commit the accepted checkpoint and review artifacts as a standalone ancestor before any implementation. This artifact is not proof of such a commit or implementation readiness. Deployment remains deferred.

## Review disposition

See [round-2 findings and closure](20261117_contract_review_round2.md). Both reviewers accepted the corrections; no unresolved documentation findings remain. OPEN-P1 requires the operator’s new-local password-selection choice. The reviewed product direction and exact login wording do not imply approval of that recommendation.


Approval update: operator explicitly approved email-first signup with password selection after the verification link and requested proceeding. OPEN-P1 is resolved. Implementation and its required standalone checkpoint commit are authorized; production deployment/migration remain deferred. Historical pending-choice statements above describe the preceding review state.

## Consumer compatibility checkpoint

Inspection confirmed profile/run token minting and Bootstrap required nonempty shared email and rq-engine dereferenced NULL owner email. The approved separate-account requirement entails preserving ID-authorized workflows without substituting contact email. The canonical account contract, token specification, and Bootstrap specification now describe optional email claims and signed positive user-ID Bootstrap resolution with legacy email-token compatibility. Independent correctness and security reviewers accepted this bounded amendment with no findings on 2026-11-17. Required tests: invalid IDs fail closed, active account/current access enforced, legacy email tokens retained, NULL owner email handled. This checkpoint authorizes consumer implementation only, not deployment.
