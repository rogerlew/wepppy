# ADR-0080: Separate public inspection and scoped feature actions

Status: Operator-directed policy amendment prepared; technical checkpoint pending

Date: 2026-10-01

Review Date: 2027-04-01, alongside the policy review in ADR-0079

## Context

The [ratified policy](../../wepppy/weppcloud/routes/usersum/weppcloud/feature-maturity-and-release-governance.md) describes PowerUser onboarding and internal collaborator access that the current runtime cannot represent. The [assessment](../dev-notes/feature-maturity-governance-implementation-assessment.md) found missing onboarding/group records, inconsistent role checks and broader-than-feature-scoped grouped data access. The maintainer clarified the intended public-read behavior, staffing constraints and initial restricted audiences.

## Decision

FA-01, the [feature access contract](../schemas/feature-access-governance-contract.md), separates public-project inspection from feature actions. Limited-access feature state/results are inspectable without granting restricted actions; ordinary anonymous creation and functionality remain unchanged. No global writer gate or anonymous creator credential is introduced; the current Omni Contrasts embargo restriction remains an explicit exception because its public release has not been authorized.

One authorized maintainer administers scoped groups with recorded person, group, effective scope, reason, actor and timestamps. This replaces dual-reviewer requirements, including two attestations by one person. Group changes retain history. Internal onboarding acknowledgment remains separate from the single administrative decision.

OpenET and Batch actions use separate feature groups, each initially containing only the requesting maintainer. Human Culvert workflow access also uses a group; the currently authorized long-lived Culvert service integration and its distinct seven-day batch-scoped browse credential retain their existing verified scope path. Group-only actions have no broad technical-role bypass.

PowerUser initial onboarding uses the two policy questions and a versioned acknowledgment with automatic approval. PowerUser suspension, reapplication and permanent revocation are deferred. Existing role administration remains; no new sanctions or durable suspension guarantee is introduced.

Maturity remains conservative: the multi-OFE override may make Stable/Preview configurations Preview, but may not promote Experimental configurations or erase Internal/Deprecated status. No numerical parameterization is changed.

## Decision provenance

The decision venue is the 2026-10-01 user-agent conversation. The authorizing principal is the requesting project maintainer; Codex records the documentation. The maintainer explicitly selected single-person group administration, account-only initial OpenET/Batch membership enforced through groups, conservative maturity and the PowerUser lifecycle exclusions, and requested the reconciled amendment and implementation plan.

The maintainer has not explicitly answered the embargoed-public-results question. Preserving ADR-0001's existing restriction is continuity, not an inference of consent to release results. The operator subsequently identified `rogerlew@gmail.com` on every deployment and `/workdir/Culvert_web_app` on wepp2, and clarified that read-only applies only to limited features for users lacking access. The broader anonymous creator/writer proposal was rejected as outside scope. Account IDs are resolved per deployment; existing credential expiry remains enforced.

## Rationale and alternatives

Public inspection supports understanding and reproduction without granting API/compute privileges. A shared visibility/action gate cannot express that difference. Hard-coded account IDs would make later access changes brittle; initial one-member feature groups provide the requested audience through the normal mechanism.

Two-reviewer access administration was rejected because the project lacks the staffing. Broad Dev/Admin assignment was rejected because it grants unrelated powers. JWT group claims alone were rejected because their validity could outlast membership removal. A new authorization service, queue or identity provider is unnecessary; the existing database and authentication stack can represent the bounded change.

Self-service before grouped-data reconciliation was rejected because PowerUser currently admits broader Batch/Culvert reads. Automatic embargo release was not authorized. PowerUser sanctions and reinstatement were explicitly deferred rather than becoming prerequisites for useful onboarding.

## Consequences and compatibility

Runtime conformance is pending. Group-only OpenET/Batch/Culvert human admission intentionally replaces coarse role admission; preserve legacy Dev/Root entitlement for the other registered internal features and unrelated operational powers. Current Culvert service integrations must pass compatibility checks before enforcement changes. New inspect-only restricted-feature views must not create their feature state or jobs; ordinary anonymous behavior remains unchanged. Group changes and their audit events must commit atomically.

The [work package](../work-packages/20261001_feature_access_governance/package.md) includes additive database migration, exact endpoint/state inventory, contract reviews, live workflow acceptance and rollout/rollback gates. The current documentation preparation does not authorize deployment or claim that the pre-implementation ancestor checkpoint is complete.

## Review and recovery

Review the implementation evidence at each milestone and the policy on 2027-04-01. Resolve any later public-embargo decision by updating both the policy and ADR-0001. Preserve audit records through rollback; disable new admissions rather than restoring a broad-role bypass. No existing credential is rotated or revoked by this ADR.
