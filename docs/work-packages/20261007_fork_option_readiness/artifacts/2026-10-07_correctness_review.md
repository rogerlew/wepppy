# FORK-UI-01 Correctness and QA Review

Reviewer: `/root/fork_contract_correctness`, independent `reviewer` role.
Date: 2026-10-07 UTC. Context: working implementation after `b80235d8f`.
Authority: `docs/ui-docs/contracts/fork-console-contract.md`, with the shared
contracts listed in the accepted decision. Review was read-only.

## Outcome and scope

Approved with no high/medium findings. The reviewer verified checkpoint
ancestry and reviewed route, template, client, test quality, and compatibility.
Correctness/QA owns valid states and user-facing behavior; separate final
security review owns containment evidence.

One minor coverage gap was identified: restored-job tracking and disabled
controls had separate tests. The existing restored-job case now combines both
with stale true bootstrap values. The reviewer confirmed that change and the
metadata descriptor-cleanup follow-up are sound, with no new findings.

## Valid-state and error evidence

| State | Result and evidence |
| --- | --- |
| No Omni/SBS metadata | Disabled unchecked options; non-Omni completed fork ready |
| Empty Omni collections/controller | Disabled until configured or retained work exists |
| Configured scenarios, contrasts, pairs | Enabled without executing child models |
| Retained named child directory | Enabled, including legacy metadata absence |
| Source, derived, absolute, linked SBS map | Existing usable map remains eligible |
| Legacy JSON without nodb.version | Metadata inspected without source writes/migration |
| Nonregular/malformed metadata | Explicit failure; not hidden as absent |
| Missing core files, uncompleted/mismatched jobs, auth failure | Existing refusal paths retained |
| Unsafe/populated Omni readiness state | Direct real-filesystem refusal tests retained |
| Old tracked job with unavailable options | Original job restored and reconciled normally |

The 118 passing focused tests include actual Jinja rendering and direct
filesystem inspection. Shared checkbox macros preserve existing presentation,
native disabling, labels, and help associations. Client tests prove both
bootstrap and payload behavior, not just markup strings.

## Artifact evidence and claim limits

The changed consumer is readiness, not a copy/model writer. The read-only wepp1
replay uses actual incident destinations and the web identity; all three pass
the candidate and fail the deployed predicate. Core controller identities match
their destination, and their bytes remain unchanged. See the validation artifact
for job IDs and hashes. UI is locally validated; predicate is environment
validated; production endpoint/UI is not deployed. No model-output correctness
claim is made. Full repository test result is recorded separately when complete.
