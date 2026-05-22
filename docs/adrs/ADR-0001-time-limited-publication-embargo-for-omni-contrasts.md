# ADR: Time-Limited Publication Embargo for OMNI Contrasts

Status: Accepted  
Date: 2026-05-22  
Review Date: 2027-02-22  
Embargo Until: 2027-05-22  

## Context

OMNI Scenarios and OMNI Contrasts support multi-scenario WEPPcloud workflows, but they serve different purposes.

OMNI Scenarios provide basic scenario orchestration. This functionality is needed to run and manage watershed scenario sets efficiently. It supports funded project workflows and normal WEPPcloud operations.

OMNI Contrasts are more interpretive. They expose comparative analysis over scenarios and can support publishable treatment-effect, management-priority, and scenario-comparison claims. Because of that, external use of OMNI Contrasts creates greater publication-priority, interpretation, and credit concerns than basic scenario orchestration.

A stakeholder concern was raised that newly developed grant-supported functionality can become available to external users before the originating project team has had a reasonable opportunity to test, interpret, and publish with it. The concern is not that WEPPcloud should be closed, but that major new analytic functionality should not unintentionally allow outside users to publish before the team that funded and developed the work.

At the same time, WEPPcloud functionality matures through use. Indefinite withholding would be harmful to the platform and inconsistent with WEPPcloud’s role as shared research infrastructure. A time-limited publication-priority window is a reasonable compromise.

## Decision

OMNI Scenarios will remain available as `preview` functionality.

OMNI Contrasts will be classified as `internal` with:

- `internal_reason: publication_embargo`
- `embargo_until: 2027-05-22`
- `min_role: dev`

This creates a 12-month publication-priority window for the originating project team while preserving OMNI Scenarios as usable scenario-orchestration infrastructure.

During the embargo period, OMNI Contrasts should not be shown or exposed as a general public WEPPcloud capability. Access is limited to Dev-authorized users.

## PATH CE Dependency Rule

OMNI Contrasts are a dependency for PATH CE.

If PATH CE is moved from `beta`, `internal`, or otherwise restricted status to any maturity state greater than `internal`, then OMNI Contrasts must also be moved from `internal`, unless PATH CE is refactored so that it no longer depends on OMNI Contrasts.

In practical terms:

- PATH CE cannot be made publicly visible or broadly usable while depending on an internal-only OMNI Contrasts feature.
- If PATH CE becomes `experimental`, `preview`, or `stable`, then OMNI Contrasts must be promoted to a compatible maturity state or the dependency must be removed.
- This follows the WEPPcloud registry policy that visible functionality must be usable.

## Rationale

This decision separates infrastructure from interpretation.

OMNI Scenarios are needed for normal multi-scenario workflows. Keeping them available allows funded watershed work and platform testing to continue.

OMNI Contrasts produce higher-level comparative outputs that are more likely to support publishable claims. A time-limited embargo protects the originating team’s reasonable opportunity to publish without creating an indefinite veto over shared infrastructure.

The 12-month window is intended to be long enough to support manuscript preparation and submission, but short enough to avoid immobilizing grant-funded platform functionality.

This also creates an explicit release-governance record. Future maintainers should not have to infer from git history why OMNI Contrasts were hidden or restricted.

## Alternatives Considered

### Make OMNI Contrasts immediately public as preview

Rejected for now. This would maximize testing and feedback, but it would not address the publication-priority concern raised by project stakeholders.

### Keep all OMNI functionality internal

Rejected. OMNI Scenarios are basic orchestration infrastructure and are needed for funded WEPPcloud workflows. Hiding all OMNI functionality would unnecessarily impair normal project work.

### Hold OMNI Contrasts indefinitely

Rejected. Publication priority must be time-limited. An indefinite hold would create de facto ownership of shared infrastructure and would conflict with WEPPcloud’s role as a public-facing research platform.

### Use informal agreement instead of registry enforcement

Rejected. Informal memory is not sufficient for release governance. The feature registry should encode current runtime state, while this ADR records the decision rationale.

## Consequences

OMNI Contrasts will not be generally visible or usable during the embargo period.

Users who need ordinary multi-scenario orchestration can continue to use OMNI Scenarios.

The originating team has a documented 12-month priority window to test, analyze, and submit work using OMNI Contrasts.

Before or near the review date, the project should decide whether OMNI Contrasts should be:

- promoted to `preview`,
- kept internal with renewed justification,
- changed to `experimental`,
- refactored,
- or deprecated.

Any extension beyond the embargo date should require a new or updated ADR.

## Implementation Notes

The feature registry should contain an `omni_contrasts` entry with `maturity: internal`, `internal_reason: publication_embargo`, `embargo_until: 2027-05-22`, and `min_role: dev`.

OMNI Scenarios and OMNI Contrasts should be gated independently so that scenario orchestration remains available while contrast analysis is restricted.

PATH CE release status must be checked against the OMNI Contrasts dependency before PATH CE is promoted beyond internal/restricted access.
