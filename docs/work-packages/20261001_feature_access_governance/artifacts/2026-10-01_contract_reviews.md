# FA-01 independent contract review and disposition

Scope update, 2026-10-01: the operator clarified that only limited features become read-only for callers lacking access; ordinary anonymous creation/functionality is unchanged. Earlier general writer/creator-proof requirements in this historical review are superseded. Current scope and deployed evidence are in [the M0 record](2026-10-01_milestone_zero.md). Final narrowed-checkpoint reviews are separate from the earlier review confirmations.


Reviewed baseline: `4cd85e2d506b54afd37bbe6f1df37cb62ae0a422`.

Review requested by the operator on 2026-10-01 after committing the prepared amendment. Review scope is documentation and plan readiness, not implementation acceptance. Both reviewers were read-only and independently inspected contracts and relevant source. Author dispositions below are not reviewer approval.

## Reviewers and initial verdicts

- Correctness: `/root/contract_correctness` (`reviewer`), 2026-10-01. Reviewed valid states, UI consistency, acknowledgment sequence and credential admission. Initial verdict: corrections required; explicit milestone-zero evidence gaps are not defects in a prepared plan.
- Security: `/root/contract_security` (`security_reviewer`), 2026-10-01. Reviewed human/service identity, group freshness, public inspection and preserved integration scope. Initial verdict: correct the private-session and principal-resolution contracts before proceeding to milestone zero; no implementation pass.

## Findings and author disposition

| ID | Severity / reviewers | Evidence at reviewed baseline | Disposition and regression obligation |
| --- | --- | --- | --- |
| FA-R1 | High (P1); correctness and security | Browse contract lines 35–43 checks live groups only for user tokens while allowing scoped sessions. `rq_engine/session_routes.py:_session_user_authorized_for_run` admits Admin/Root; `browse/auth.py:authorize_group_request` applies its role gate only to user tokens. Correctness also traced `routes/user.py:mint_run_token`, which issues human-delegated service credentials accepted by Batch base aliases. | Accepted. Canonical access, browse, token and API contracts now require live originating-human membership for user tokens, human sessions and trusted human-delegated service credentials. Resource checks remain additive; service class alone is not an exemption. Preserve public Batch reads, independent Culvert integration/browse credentials and existing accepted token classes. Inventory/tests include authorized human sessions/delegations, Admin/Root nonmembers and removed members with stale credentials. |
| FA-R2 | Medium (P2); security | Agent API contract line 39 broadly resolves user/session principals to account IDs, despite session IDs and optional human binding. `session_routes.py:_identity_from_claims` and bearer conversion can parse numeric service/MCP subjects as user IDs. | Accepted. Principal resolution is token-class aware; anonymous readers remain anonymous, sessions require verified human binding, and conversion cannot manufacture human authority. Trusted explicit delegation is distinguished from arbitrary subject/claim parsing. Freeze provenance mechanism at milestone zero; test numeric service subjects matching a member account and service-derived human-looking claims while preserving authorized integration outcomes. |
| FA-R3 | Medium (P2); correctness | Registry specification lines 26–30 says below `min_role` is unauthorized and shown configs are launchable, contradicting effective group entitlement and informational cards. | Accepted. UX policy now uses effective entitlement, separates card information from launch authorization, and permits explained disabled discovery. Validate an ordinary group member, a broad-role nonmember and an anonymous informational-card viewer. |
| FA-R4 | Medium (P2); correctness | Governance approval criteria lines 642–646 requires acknowledgment before approval, while internal onboarding and access contract allow membership before acknowledgment. | Accepted. Grant criteria identifies the statement; acknowledgment may follow the grant but precedes group-based protected actions. Preserve first-use acknowledgment without another maintainer decision. |

## Post-fix confirmation

Both reviewers independently read back the revised working tree on 2026-10-01 and confirmed closure. Correctness confirmed FA-R1, FA-R3 and FA-R4; security confirmed FA-R1 and FA-R2, including the human-delegated service extension. Both verdicts: prepared amendment/plan is ready to proceed into milestone zero, with zero unresolved high/medium findings from this review. Source/runtime files are unchanged. No live credential, database or browser validation was performed for this documentation review.

## Remaining gates

This review does not close milestone zero: exact route/artifact and valid-state matrix, verified deployed account/service identities, writer/anonymous-creator authority, conversion/delegation provenance, mixed-bundle policy and exact transport contracts remain to be frozen. Obtain review of that completed matrix and record a standalone accepted ancestor before runtime edits. Commit `4cd85e2d5` is the prepared amendment, not a retrospectively accepted runtime checkpoint.

The operator's earlier commit instruction was fulfilled by `4cd85e2d5`. This disposition records the subsequent review request; it does not claim implementation/deployment authority or operational access grants.

Review-disposition validation (2026-10-01): all 15 changed/new Markdown files passed `wctl doc-lint` with zero errors/warnings; relative link targets resolved and `git diff --check` passed. New review artifact spelling preview was unchanged. No runtime tests were rerun for this documentation-only change.
