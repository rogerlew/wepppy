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

### 4. Restrictions need reasons

If a feature is internal, hidden, role-gated, deprecated, or publication-embargoed, the reason should be documented. Restrictions should not depend on memory, assumptions, or informal ownership claims.

### 5. Publication priority may be legitimate, but it must be time-limited

Grant-funded teams may need a reasonable head start to analyze, write, and submit work based on major new functionality. That priority window must have a review date or expiration date. It should not become an indefinite veto over shared infrastructure.

### 6. Runtime state and decision rationale are different things

The feature/config registry defines the current executable state of WEPPcloud. Architecture Decision Records, issue threads, meeting notes, or work-package documents should capture why significant release decisions were made.

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

When substantial development, interpretation, troubleshooting, or model-design support is provided by WEPPcloud developers or project scientists, authorship or acknowledgement should be discussed early.

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
