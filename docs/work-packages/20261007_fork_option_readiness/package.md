# Fork Option Availability and Readiness

Status: Completed for code/local validation (2026-10-08 UTC).
Production deployment remains separate. Timezone: UTC.
Remediation ID: FORK-UI-01.

## Problem and scope

Mariana's three forks finished on 2026-10-07 between 00:06 and 00:12 UTC.
All selected skip Omni, but neither source used Omni. The worker correctly
skipped reset; readiness unconditionally demanded Omni artifacts and suppressed
the destination link. Manual retry repeated the same rejection.

The operator requested disabling Skip Omni without scenarios/contrasts,
disabling undisturbify without SBS, and fixing backend readiness. The proposed
durable rules are in
[the fork-console contract](../../ui-docs/contracts/fork-console-contract.md).
This package covers the console route/template/script, their tests, and docs.
It does not change fork execution, API acceptance, job wiring, model inputs,
auth, production files, or deployment.

## Complexity budget

Reuse bounded JSON metadata inspection, shared checkbox/help markup, current console
bootstrap, and descriptor-relative readiness checks. Add no dependency,
endpoint, queue, service, datastore, or retry policy. The first acceptance
condition is that an already-finished non-Omni fork passes readiness while
unsafe/inconsistent Omni state still fails.

## Evidence and acceptance

Retain incident job IDs and read-only runtime observations in the decision
artifact. Validate source capability semantics, rendered controls and submitted
booleans, real filesystem readiness, restored jobs, and the destination link.
The scope consumes copied controller/artifact state but changes no artifact
writer; generated model-output validation is not claimed. Replay the candidate
readiness check against the real destinations under the existing web identity
before claiming environment validation. No production deployment is authorized
by this package.

## Security and lifecycle

Security impact: high, because a filesystem readiness predicate is relaxed for
one legitimate absent state. Dedicated correctness and security reviews are
required; both must verify absent/empty/legacy valid cases and hostile-entry
containment. No new privilege or authorization rule is permitted.

Related historical packages: `20260729_fork_destination_readiness_hardening`,
`20260806_fork_skip_omni_reset`, and `20260810_fork_omni_empty_state_fix`.
These are immutable provenance, not current authority. The new contract
promotes the relevant current rules and explicitly resolves absent Omni state.

Health signal: affected completed forks expose their link; unavailable options
cannot be selected in the console. Danger signal: an incomplete or unsafe
destination receives a ready result. No temporary mitigation is introduced.
Production observation begins only after a separately authorized deployment;
reproduce these signals during its acceptance check and reopen investigation
for any recurrence. No parameterization or retry-threshold ADR change is needed.

## Exit criteria

- Accepted, independently reviewed contract checkpoint committed before code.
- UI, API compatibility, and direct filesystem regression gates pass.
- Focused and broad Python/frontend checks, docs lint, and required reviews pass.
- Local/environment/deployed claims remain separate in the tracker.

## Outcome

The checkpoint was accepted, independently reviewed, and committed as
`b80235d8f` before runtime edits. Both UI guards and the backend no-op readiness
fix are implemented. Final focused tests pass (118), the full Python suite
passes (10,418 passed / 126 skipped), and frontend tests pass (924). Lint,
bundle rebuild, broad-exception enforcement, and documentation checks pass.
Independent correctness/QA and security reviews have no unresolved findings.

Read-only evaluation on the three real wepp1 destinations passes the candidate
predicate and fails the deployed predicate under the existing web identity.
Core controller identities match their destination and byte hashes are unchanged.
No production files, jobs, services, or project data were modified. Actual
endpoint/UI recovery is a separately authorized deployment acceptance check.
