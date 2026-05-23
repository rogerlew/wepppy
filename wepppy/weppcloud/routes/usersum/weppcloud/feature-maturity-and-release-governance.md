# Feature Maturity and Release Governance

Status: Draft  
Applies to: WEPPcloud user-facing features, run-page modules, launchable configs, and major analysis workflows  
Related implementation: `wepppy/weppcloud/feature_registry/`

## Purpose

WEPPcloud is both a public modeling platform and an active research/development environment. New functionality is often created through grants, workshops, stakeholder requests, operational needs, and collaborator feedback.

This creates a recurring tension:

- features must be used to mature,
- but immature features can be misunderstood, misapplied, or published without appropriate caveats.

This policy defines simple governance rules for feature maturity, release state, publication priority, and documentation. The goal is not to slow development. The goal is to make release decisions explicit, auditable, and fair.

## Scope

This policy applies to:

- launchable WEPPcloud interface configs,
- run-page features and controls,
- major analysis workflows,
- experimental model components,
- preview features exposed for broader testing,
- internal features restricted for compute, API, beta, or publication reasons.

This policy does not replace scientific judgment, grant management, authorship discussions, institutional policy, or legal/compliance review. It provides a shared project-level release framework.

## Core Principles

### 1. Models are not oracles

WEPPcloud outputs are model-based estimates. They depend on input data, assumptions, model structure, parameterization, and domain applicability. A feature being available does not mean every result is correct, validated everywhere, or appropriate for every decision.

### 2. Use matures the system

Important defects and limitations are often discovered only when users apply WEPPcloud to diverse watersheds, climates, soils, burn severities, treatments, and management contexts. Functionality that is never exercised does not mature.

### 3. Availability is not the same as maturity

A feature may be technically reachable, known to some users, or available in limited workflows without being stable, broadly supported, or publication-ready. Maturity status must be explicit.

### 4. Restrictions need reasons and should be transparent

If a feature is internal, hidden, role-gated, deprecated, or publication-embargoed, the reason should be documented. Restrictions should not depend on memory, assumptions, or informal ownership claims. Restrictions and their reasons should be visible to users.

### 5. Publication priority may be legitimate, but it must be time-limited

Grant-funded teams may need a reasonable head start to analyze, write, and submit work based on major new functionality. That priority window must have a review date or expiration date. It should not become an indefinite veto over shared infrastructure.

### 6. Runtime state and decision rationale are different things

The feature/config registry defines the current executable state of WEPPcloud. Architecture Decision Records, issue threads, meeting notes, or work-package documents should capture why significant release decisions were made.

### 7. Sponsor authority must be bounded and universal

Sponsors may legitimately influence funded scope, delivery priority, and time-limited publication-priority windows.

Sponsors must not control scientific truth claims, maturity labeling, known-limitation disclosure, or incident-risk communication.

Governance boundaries must be universal across sponsors. Sponsor identity, size, or funding level must not create ad hoc exception pathways.

## Conflicting Points of View

### Public-service and model-maturation view

WEPPcloud is a public-facing research and decision-support system. Broad use helps identify defects, transferability limits, confusing workflows, and scientific edge cases. Restricting features too aggressively can prevent the feedback needed to make them reliable.

From this view, overly cautious release control can harm the platform by delaying testing, weakening stakeholder value, and trapping useful infrastructure behind internal timelines.

**Rationale:**  
WEPPcloud improves when real users exercise real workflows across diverse landscapes.

### Scientific-quality and reputation view

Premature exposure can also cause harm. Users may treat experimental outputs as stable, apply models outside their domain of applicability, or publish results without understanding limitations. When that happens, reputational damage may attach to WEPPcloud as a whole.

From this view, release governance is needed so experimental or poorly validated features are not mistaken for supported scientific products.

**Rationale:**  
Users need clear signals about what is stable, what is preview, and what is experimental.

### Publication-priority and credit view

Some features are built with grant funding intended to support specific research deliverables. If a major new feature is exposed broadly before the originating team has had a reasonable chance to publish, external users may publish first or receive disproportionate credit.

From this view, limited publication-priority windows are appropriate for major grant-funded functionality.

**Rationale:**  
Developers and project teams should not lose reasonable publication opportunity because they made infrastructure usable.

### Anti-embargo and infrastructure-stewardship view

Publication priority cannot become an indefinite release block. WEPPcloud is shared infrastructure with public-service, stakeholder, and grant-deliverable purposes. A feature should not remain restricted for years solely because a manuscript has not appeared.

From this view, access should be governed by maturity, documented risk, operational constraints, and time-limited review dates.

**Rationale:**  
Slow publication should not permanently immobilize shared research infrastructure.

### Operations and supportability view

Some restrictions have little to do with scientific maturity. A feature may be internal because it is expensive to run, depends on fragile APIs, requires manual oversight, creates excessive storage, or is not supportable for ordinary users.

From this view, operational restrictions are valid but should be labeled honestly.

**Rationale:**  
Compute, storage, API, and support limits are legitimate release criteria, but they are not the same as scientific immaturity.

## Maturity Labels

WEPPcloud uses the following maturity labels.

### Stable

The feature is supported as a normal WEPPcloud workflow.

Stable means:

- the workflow is documented,
- expected behavior is reasonably well understood,
- ordinary users may use it without special permission,
- outputs may be used in analysis or publication with normal citation and caveats,
- known limitations are documented where practical.

Stable does not mean perfect, universally validated, or free from model uncertainty.

### Preview

The feature is available for broader use, but users should treat it as still maturing.

Preview means:

- the workflow is believed to be useful and scientifically plausible,
- broader testing and feedback are desired,
- documentation may still be evolving,
- validation coverage or edge-case behavior may be incomplete,
- publication-scale use should include version, maturity status, and appropriate caveats.

Preview features may be public or login-gated depending on risk and support burden.

### Experimental

The feature is scientifically or technically unresolved.

Experimental means:

- the approach, implementation, interpretation, or domain applicability is still being evaluated,
- outputs may change substantially,
- users should not treat the feature as supported,
- publication, management, or regulatory use should occur only with direct development-team involvement.

Experimental features may be visible to selected users, collaborators, or testers when feedback is needed.

### Deprecated

The feature should generally not be used for new work.

Deprecated means:

- the feature has been replaced, superseded, or is known to have significant limitations,
- it may remain available for reproducibility, legacy runs, or transition,
- documentation should point users toward the replacement when one exists.

Deprecated features should be clearly labeled.

### Internal

The feature is not generally available.

Internal means:

- access is restricted to development or project-authorized roles,
- the feature must have an explicit internal reason,
- the feature should not be presented as a public WEPPcloud capability.

Allowed internal reasons include:

- `compute`: too expensive or operationally risky for general use,
- `api_constrained`: depends on credentials, fragile services, or restricted APIs,
- `beta`: restricted testing before broader exposure,
- `publication_embargo`: time-limited priority window for the originating team.

Internal features require explicit review or expiration when the reason is temporary.

## Release Policies

### Policy 1: The registry is the runtime authority

The feature/config registry is the authoritative source for user-facing maturity labels, visibility, role gating, backend requirements, and release state.

Routes and templates should not duplicate maturity or visibility rules.

### Policy 2: Visible means usable

If a feature is shown to a user, the user should be able to use it.

If a config is shown to a user, the user should be able to launch it.

The normal exception is a read-only existing project/run state, where controls may be shown but disabled with a clear reason.

WEPPcloud should avoid tease-only controls.

### Policy 3: Use the least optimistic accurate maturity label

Maintainers should choose the least optimistic maturity label supported by current evidence.

Do not classify a feature as stable if material questions remain about:

- regional transferability,
- validation coverage,
- interpretation,
- output correctness,
- operational support,
- backend reliability,
- or user-facing documentation.

### Policy 4: Preview is for responsible broader use

Preview is appropriate when a feature is useful enough for broader feedback but not mature enough to call stable.

Preview features should have:

- visible maturity labeling,
- basic documentation,
- version/provenance support where practical,
- known limitations or caveats,
- a path toward stable, experimental, deprecated, or internal status.

Preview is not a guarantee of correctness.

### Policy 5: Experimental is for unresolved work

Experimental features should not be represented as supported public workflows.

Experimental features should be used for:

- testing,
- model exploration,
- collaborator feedback,
- comparison of candidate methods,
- discovery of failure modes.

Experimental outputs should not be used for publication-scale, regulatory, or operational decision-making without direct consultation with the development team.

### Policy 6: Internal restrictions must state a reason

Internal features must identify why they are internal.

Valid reasons include compute limits, API constraints, beta testing, or publication embargo.

Internal status should not be used as a vague substitute for ownership, discomfort, or indefinite uncertainty.

### Policy 7: Publication embargoes must be time-limited

A publication embargo may be used when a major new feature was developed for a grant-funded research effort and the originating team needs a reasonable head start to prepare and submit work.

Publication embargoes must include an `embargo_until` date.

Normal expectations:

- small feature or analysis note: 3–6 months,
- substantial workflow or model feature: 6–12 months,
- complex multi-party validation or agency-dependent work: up to 18 months with documented rationale.

Embargoes longer than 18 months require explicit renewal and justification.

A publication embargo is a priority window, not permanent ownership of infrastructure.

### Policy 8: Embargoes should not block necessary infrastructure

If a feature is required to operate funded workflows, stakeholder scenarios, or routine platform infrastructure, the project should consider separating:

- the basic operational capability,
- the publishable analysis layer,
- advanced interpretation tools,
- and experimental outputs.

For example, scenario orchestration may be released as preview while more interpretive contrast analysis remains internal under a time-limited publication embargo.

### Policy 9: Known-bad or questionable functionality must be labeled

If a feature is known to produce questionable results in a domain, configuration, or model family, that limitation should be documented.

Possible actions include:

- downgrade from stable to preview or experimental,
- add known-limitation text,
- add warning text to docs or UI,
- deprecate the feature,
- restrict the feature while problems are investigated.

Silently leaving known-problem functionality presented as stable should be avoided.

### Policy 10: Public availability does not imply public domain

A publicly accessible WEPPcloud feature is not automatically public domain, publication-ready, scientifically endorsed, or free of citation obligations.

Documentation should distinguish:

- access,
- license,
- maturity,
- citation expectations,
- authorship/collaboration norms,
- scientific limitations.

### Policy 11: Role gating is not a substitute for documentation

Role gates can protect users and infrastructure, but they do not explain the decision.

Major release decisions should be documented in an ADR, issue, work package, or other durable project record.

The registry answers: “What does the system enforce now?”  
The ADR answers: “Why did we choose this?”

### Policy 12: Review dates matter

Temporary statuses should have review dates when practical.

Review is especially important for:

- publication embargoes,
- beta/internal features,
- deprecated but still visible features,
- experimental features with active users,
- features restricted due to operational constraints.

A review does not guarantee release. It requires reassessment.

### Policy 13: Sponsor authority is scoped

Sponsors may request:

- funding priorities and milestone sequencing,
- time-limited publication embargo windows with explicit `embargo_until`,
- scoped collaborator access for funded workflows during a valid embargo window.

Sponsors may not require:

- suppression of known limitations, warnings, or maturity downgrades,
- stable labeling when evidence does not support stability,
- indefinite infrastructure control after delivery,
- undocumented governance exceptions.

### Policy 14: Separate technical-science authority from release/business authority

Technical-science authority governs:

- maturity labels,
- known-limitation statements,
- warning/deprecation decisions,
- interpretation and scientific-risk messaging.

Release/business authority governs:

- visibility state (public/internal),
- role and access gates,
- operational enablement constraints,
- embargo administration and review cadence.

Sponsor input is expected in both domains, but sponsor preference is not a unilateral veto over technical-science authority.

### Policy 15: Sponsor conflicts require documented escalation

When sponsor preference conflicts with technical-science assessment, maintainers must run a documented escalation that records:

- the disputed decision,
- participants in the decision meeting,
- evidence considered,
- final authority path and rationale,
- resulting registry/ADR updates and review date.

Escalation outcomes must be durable and auditable (ADR, issue, or work package), and must preserve universal sponsor-neutral governance.

## Access Governance

### Principle

Access must be fair, transparent, scoped, and auditable.

WEPPcloud should not treat “internal” as a vague social category. A person is not internal merely because they are known to the group, have a university affiliation, have attended meetings, or have used WEPPcloud before.

Access should be based on documented role, project relationship, operational need, testing purpose, or approved collaboration scope.

### Access state vs. person status

`internal` is a feature/config release state.

It does not mean there is a permanent class of “internal people” who automatically receive access to all restricted functionality.

A user may be authorized for one internal feature and not another.

### Access levels

WEPPcloud recognizes the following access levels for governance purposes.

#### User

A normal WEPPcloud user.

Users may access public stable and preview functionality, subject to normal account, quota, and operational limits.

#### PowerUser

A PowerUser is an approved advanced user who may access elevated workflows that are not appropriate for all users but are not necessarily internal research features.

PowerUser access may be appropriate for:

- agency or partner users with recurring operational workflows,
- trained users who understand WEPPcloud assumptions and limitations,
- users running larger or more complex jobs,
- users participating in structured testing of preview workflows,
- users who need access to features with higher compute or support burden.

PowerUser status does not grant access to publication-embargoed internal features unless separately approved.

#### Internal Feature Access

Internal Feature Access is scoped access to one or more internal features/configs.

This is not the same as general PowerUser status.

Internal Feature Access may be appropriate for:

- core maintainers implementing or debugging the feature,
- project team members responsible for the funded work,
- named collaborators approved for a documented purpose,
- trusted testers approved for a specific feature,
- users required to access a dependency of another approved workflow.

Internal Feature Access must be feature-scoped, reasoned, and reviewable.

#### Dev / Admin / Root

Dev, Admin, and Root are operational trust levels.

They are for users who need broad technical access to develop, maintain, debug, deploy, or administer WEPPcloud.

These roles should not be used merely to give a collaborator access to one internal feature.

If a user needs one restricted feature but does not need broad development/admin access, the policy preference is feature-scoped internal access.

## PowerUser Onboarding Procedure

PowerUser access is intended for trained users who need elevated WEPPcloud workflows that are not appropriate for all users, but who do not require feature-specific internal review.

PowerUser onboarding should minimize stored personal information.

The application should not collect affiliation, project description, publication intent, or research details unless separately required for a specific workflow. The normal stored record should be limited to:

- authenticated user id,
- request timestamp,
- training version accepted,
- approval status,
- approver or automated rule, if applicable,
- approval/review timestamp.

### PowerUser Training Text

Before requesting PowerUser access, the user must acknowledge concise onboarding text not exceeding 200 words.

Suggested text:

> PowerUser workflows may expose advanced WEPPcloud features, larger jobs, or less commonly used model configurations. WEPPcloud outputs are model-based estimates, not measurements or guarantees. Results depend on input data, assumptions, parameterization, model structure, and watershed/domain suitability. You are responsible for reviewing outputs, checking whether assumptions are appropriate for your use case, and documenting versions, inputs, and limitations when results are shared or published. Preview or experimental functionality may change, produce unexpected results, or require additional interpretation. Elevated access may be limited, reviewed, or removed to protect system reliability, storage, compute capacity, or scientific integrity. PowerUser access does not provide access to internal, publication-embargoed, or restricted features unless that access is separately granted.

### PowerUser Request

The request should ask only:

- “Do you need PowerUser access?” yes/no
- “I have read and understand the PowerUser training statement.” yes/no

### PowerUser Approval

PowerUser access may be approved automatically or manually.

Approval may be denied or deferred when:

- user does not respond yes to both questions.

PowerUser status does not grant access to internal or publication-embargoed features.

## Internal Collaborator Pathway

Internal access should not be limited to existing project insiders. External researchers, agency partners, students, consultants, and unaffiliated collaborators may receive scoped access to internal WEPPcloud features when there is a documented purpose and human review.

The purpose of this pathway is to provide fair access without treating internal features as generally public or publication-ready.

### Internal Collaborator

An Internal Collaborator is a named user approved for scoped access to one or more internal WEPPcloud features, configs, runs, or workflows.

Internal Collaborator status is not global membership in the WEPPcloud team. It does not grant Dev, Admin, Root, or access to unrelated internal features.

A person may be an Internal Collaborator for one feature and an ordinary user for another.

### Access Principles

Internal Collaborator access should be:

- **scoped** to the approved feature, config, project, or workflow;
- **purpose-based**, not based on social proximity;
- **time-limited or reviewable**;
- **minimally invasive**, avoiding unnecessary personal information;
- **auditable**, so future maintainers can understand why access was granted.

Access should not be denied merely because a requester is external, new to the group, unaffiliated, or not part of the originating project.

Access may be denied, deferred, or narrowed when the requested use conflicts with feature maturity, publication embargo, compute/storage burden, support burden, data constraints, or scientific risk.

### Internal Access Request

Internal access requires human review. A web form may collect the request, but approval should be made by an authorized maintainer, project lead, or governance group.

The stored request record should minimize PII. Normally it should include only:

- authenticated user id or email;
- requested feature/config/workflow;
- request date;
- access reason code;
- short purpose statement;
- sponsor or project contact, if applicable;
- decision: approved, denied, deferred, or narrowed;
- approving person or group;
- access scope;
- review or expiration date;
- accepted onboarding/training version.

The project should avoid collecting detailed research plans, CVs, demographic information, sensitive data descriptions, or unnecessary affiliation history unless required by a grant, DUA, IRB, agency agreement, security review, or other compliance obligation.

### Access Reason Codes

Use simple reason codes where possible:

- `originating_project_team`
- `dependent_project`
- `sponsored_collaborator`
- `trusted_tester`
- `agency_partner`
- `maintenance_or_debugging`
- `publication_embargo_exception`
- `other_documented_reason`

### Approval Criteria

Internal Collaborator access may be approved when:

- the request has a clear research, testing, agency, operational, maintenance, or dependent-project purpose;
- the requested use is compatible with the feature maturity state;
- the user accepts the relevant onboarding text;
- the access can be scoped narrowly enough to avoid unnecessary exposure;
- compute, storage, support, and scientific-risk burdens are acceptable;
- any active publication embargo or originating-team priority window is respected.

PowerUser status alone does not grant access to internal or publication-embargoed features.

### Publication-Embargoed Features

For features marked `internal_reason: publication_embargo`, access should normally be limited to:

- core maintainers needed for implementation, testing, or operations;
- members of the originating project team;
- approved users working on dependent workflows;
- sponsored collaborators explicitly approved for the embargoed feature.

A publication embargo governs access to the feature during the embargo period. It should not be framed as a retroactive right to approve, block, or censor publications.

If access is granted during an embargo, the access record should state the approved purpose and whether outputs are intended for development, testing, validation, internal analysis, agency review, or publication-scale use.

### Consultation Expectations

Internal access may include consultation expectations, especially for experimental, preview, anomalous, or publication-embargoed functionality.

These expectations are intended to reduce avoidable misinterpretation of immature workflows. They are not a blanket publication veto.

Suggested consultation expectation:

> If results from internal WEPPcloud functionality appear anomalous, scientifically important, or likely to be published or used in management decisions, the user should notify the WEPPcloud project contact before public release so the team has an opportunity to identify known issues, versioning concerns, or interpretation problems.

Failure to follow agreed consultation expectations may affect future access, but WEPPcloud should generally rely on documentation, citation expectations, scholarly norms, and future access decisions rather than attempting to control publication after results have been generated.

### Internal Collaborator Onboarding

Before access is granted, the user should accept concise onboarding text.

Suggested text:

> Internal WEPPcloud access may include experimental, preview, restricted, or publication-embargoed functionality. Access is granted only for the approved feature, purpose, and time period. Outputs may be incomplete, unstable, or unsuitable for publication or management decisions without additional review. You are responsible for documenting versions, inputs, assumptions, limitations, and maturity status. If results appear anomalous or scientifically important, notify the WEPPcloud project contact before public release when practical. Internal access does not imply authorship rights, publication approval, or access to unrelated features. Authorship and acknowledgment should be discussed early when WEPPcloud personnel provide substantial intellectual, scientific, technical, or interpretive contributions.

### Authorship and Acknowledgment

Internal access does not create an automatic coauthorship requirement.

Authorship should be based on substantive intellectual, scientific, technical, or interpretive contribution.

Acknowledgment or citation may be appropriate when WEPPcloud personnel provide support, when a feature is grant-funded, or when model development materially enabled the work.

Expectations should be discussed early when a user intends to publish with internal, experimental, or preview functionality.

### Expiration and Review

Internal Collaborator access should have a review or expiration date.

Access should be reviewed when:

- the approved purpose ends;
- the feature changes maturity;
- an embargo expires;
- the user’s project relationship changes;
- a dependent workflow is promoted, replaced, or removed;
- access is no longer needed;
- compute, storage, support, or scientific-risk conditions change.

Expired access should be removed, renewed with rationale, or converted to a different access level.

### Relationship to Registry

The registry defines feature maturity and runtime visibility. The current registry supports maturity states, internal reasons, embargo dates, and role gates. Future implementation should support feature-scoped internal access when policy requires narrower access than broad Dev/Admin roles provide.

## Access Records

Internal Feature Access decisions must produce an auditable record.

The record should include:

- request date,
- requester,
- requested feature/config,
- maturity state at time of request,
- internal reason,
- approving person or group,
- rationale for approval or denial,
- access scope,
- expiration or review date,
- publication/citation expectations,
- related ADR, issue, grant, or work package when relevant.

Access records may live in the repository, a database, an admin interface, or another durable project system. The important requirement is that they are retrievable and reviewable.

The project should be able to answer:

- who has access,
- what they have access to,
- why access was granted,
- who approved it,
- when access should be reviewed,
- whether publication restrictions or expectations apply.

## Expiration and Review

Internal Feature Access should have a review date or expiration date unless there is a documented reason for continuing access.

Review is required when:

- a publication embargo expires,
- a feature changes maturity state,
- a project ends,
- a user changes role,
- a dependent workflow is promoted,
- a known limitation or risk changes,
- access is no longer needed.

Expired access should be removed, renewed with rationale, or converted to a different access level.

## Fairness Standard

Similarly situated users should receive similar access.

Different outcomes should be explainable by documented differences in:

- feature maturity,
- project relationship,
- access purpose,
- publication embargo,
- compute/storage burden,
- operational risk,
- support burden,
- security or data constraints,
- prior misuse or unresolved compliance concern.

Access decisions should not be based on favoritism, personal preference, informal proximity, sponsor identity, or publication competition alone.

## Implementation Requirement

Implementation should follow this policy.

The current registry may use coarse role gates as an MVP enforcement mechanism, but the governance target is:

- PowerUser access can be requested through a web-facing application,
- Internal Feature Access requires human review,
- internal approvals are feature-scoped where practical,
- approvals and denials create auditable records,
- publication-embargoed access is explicitly documented,
- broad Dev/Admin roles are not used as a substitute for narrow collaborator access.

If the current user model cannot represent a fair policy decision, the user model should be extended rather than weakening the policy.
## Decision Records

Significant release decisions should be recorded using an Architecture Decision Record or equivalent repo-tracked document.

An ADR is recommended when:

- a feature is moved to or from internal status,
- a publication embargo is created or extended,
- a feature is promoted to stable,
- a feature is deprecated,
- a known scientific limitation changes maturity state,
- a release decision is likely to be questioned later,
- stakeholders make a visibility decision in a meeting.

An ADR should be short. It should normally include:

- title,
- date,
- status,
- decision,
- rationale,
- alternatives considered,
- expected review or expiration date,
- related grant/project/work package if relevant,
- implementation references or commit links if available.

The ADR should not need to be perfect. Its purpose is to preserve decision context.

## Recommended Release Workflow

### 1. Identify the feature or config

Define the feature/config key and the user-facing label.

### 2. Choose an initial maturity state

Use the least optimistic accurate label:

- internal,
- experimental,
- preview,
- stable,
- deprecated.

### 3. Identify restrictions

If the feature is internal, document the internal reason.

If the reason is publication embargo, include an embargo end date.

If the feature depends on backend capability, API access, compute limits, or role level, encode that in the registry.

### 4. Add or update documentation

At minimum, public or preview features should have enough documentation for users to understand:

- what the feature does,
- what the output means,
- major assumptions,
- major limitations,
- citation or versioning expectations where relevant.

### 5. Record the decision if significant

Create or update an ADR when the decision has stakeholder, publication, operational, or reputational significance.

### 6. Review after use

Real use should inform future maturity changes.

A feature may move:

- from internal to experimental,
- from experimental to preview,
- from preview to stable,
- from any state to deprecated,
- from stable back to preview or experimental if problems are found.

## Promotion Guidelines

### Experimental to Preview

A feature may move from experimental to preview when:

- the basic workflow works,
- outputs are interpretable,
- known severe defects are resolved or clearly documented,
- broader user feedback would be useful,
- the team is comfortable with caveated external use.

### Preview to Stable

A feature may move from preview to stable when:

- normal users can operate it successfully,
- documentation is adequate,
- known limitations are documented,
- outputs have been checked against expected behavior,
- support burden is acceptable,
- the feature is not materially unresolved scientifically or operationally.

### Any State to Deprecated

A feature should be deprecated when:

- a better workflow replaces it,
- results are known to be misleading,
- the backend is no longer supportable,
- the model assumptions are no longer defensible,
- maintenance cost exceeds value.

## Publication and Citation Expectations

Users publishing with WEPPcloud outputs should report enough information to make their work interpretable and reproducible.

Where practical, publications should identify:

- WEPPcloud feature/config used,
- maturity state at time of use,
- model/version/provenance information,
- parameterization assumptions,
- input datasets,
- known limitations relevant to the study area,
- whether the feature was preview, experimental, or stable.

Preview or experimental features should be cited and caveated as such.

WEPPcloud may restrict access to internal or publication-embargoed features before use. Once results are independently generated, the project should generally rely on scholarly norms, citation expectations, documentation, and future access decisions rather than attempting to control publication.

When substantial development, interpretation, troubleshooting, or model-design support is provided by WEPPcloud developers or project scientists, authorship or acknowledgment should be discussed early.

## Resource and Operations Expectations

WEPPcloud is shared infrastructure.

The project may impose operational limits to preserve reliability, including:

- storage cleanup,
- project retention rules,
- quotas,
- archival policies,
- compute limits,
- role-gated expensive workflows,
- temporary disabling of unstable services.

Operational restrictions should be documented separately from scientific maturity.

## Practical Examples

### Scenario orchestration

A workflow that efficiently manages multiple model scenarios may be classified as preview or stable if it is needed for normal funded work and does not itself make a new scientific claim.

### Contrast analysis

A workflow that produces interpretive comparisons or treatment-prioritization outputs may warrant preview, experimental, or internal status depending on validation, documentation, and publication-priority concerns.

### Model-fitting workflow

A fitting/calibration feature may be experimental if implementation, interpretation, or performance is unresolved. It may be preview when broader testing is appropriate but publication-scale use still requires caveats.

### Known regional limitation

If a model parameterization performs poorly or unpredictably in a region or vegetation/soil domain, the issue should be documented as a domain limitation. The correct response may be warning text, maturity downgrade, targeted validation, or deprecation of a configuration for that domain.

## Policy Maintenance

This policy should be updated when the project’s release process changes.

Small wording improvements may be made through normal commits.

Substantive changes should be discussed with relevant project stakeholders and recorded in an ADR when appropriate.

## Summary

WEPPcloud feature release should be governed by explicit maturity status, documented restrictions, time-limited priority windows, and auditable decisions.

The registry defines what the system currently enforces.

ADRs and related project records explain why those decisions were made.
