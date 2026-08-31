# Project Config Production Cutover (WP12)

**Status**: Open (2026-08-31)
**Timezone**: UTC
**Initiative branch**: `feature/project-owned-config`
**Canonical branch**: `master`
**Promotion policy**: merge only at the roadmap promotion gate

## Overview

WP12 promotes the Forest-accepted project-owned configuration boundary to
`master`, deploys that exact canonical revision to production, observes the
rollout, and preserves a tested reader-compatible rollback path. It is the
first merge and production boundary in the project-owned-config roadmap.

## Objectives

- Repeat the ratified WP12D amendment 4 and amendment 5 scope comparisons at
  the final feature-branch revision.
- Merge only the accepted and explicitly dispositioned branch boundary into
  `master`.
- Deploy the resulting canonical revision with staged reader-before-writer
  feature enablement and verify production health, project creation, legacy
  reads, project-owned writes, and rollback compatibility.
- Hand WP13 the deployed and rollback revision inventory while retaining the
  shared `_defaults.toml` compatibility alias.

## Scope

### Included

- Final branch, requirement, validation, security, and changed-file audits.
- Canonical merge to `master` and production deployment through the documented
  production entry point.
- Staged feature-flag activation, health/danger observation, and rollback
  verification.
- Operator evidence, revision inventory, and WP13 handoff documentation.

### Explicitly Out of Scope

- Removing the shared `_defaults.toml` alias; WP13 owns that change.
- Migrating legacy projects or supporting prerelease Config Builder projects.
- Adding locales, datasets, climate modes, or modeling capabilities.
- Changing model parameterization, defaults, formulas, or thresholds.

## Implementation Fidelity and Evidence

- **Fidelity target**: faithful promotion of the Forest-accepted execution path
- **Authoritative source paths**: the revisions and evidence owned by WP11,
  WP12B, WP12C, and WP12D
- **Cutover proof required**: production reports the canonical merge revision;
  supported reader/writer flows execute with staged flags; rollback readers
  open project-owned `_defaults.cfg`
- **Acceptance evidence type**: generated-output and deployed-runtime evidence

## Stakeholders

- **Primary**: WEPPcloud operator and project owners
- **Reviewers**: project-owned-config correctness, governance, security, and
  deployment reviewers retained from prerequisite packages
- **Security Reviewer**: required for final auth, mutation, deployment, and
  rollback boundary review
- **Informed**: WP13 alias-retirement owner

## Success Criteria

- [ ] WP11, WP12B, WP12C, and WP12D evidence is accepted at the final revision.
- [ ] Amendment 4 and amendment 5 scope comparisons match or all additional
  paths receive an explicit accepted disposition.
- [ ] Complete automated gates pass at the final feature revision.
- [ ] The reviewed boundary is merged to `master` and the merge revision is
  recorded.
- [ ] Production deployment, staged flags, health observation, and rollback
  verification pass.
- [ ] The shared `_defaults.toml` alias remains present and WP13 receives the
  deployed/rollback inventory.

## Parameterization ADR Gate

- **Parameterization change present**: no
- **ADR required**: no
- **ADR link(s)**: N/A
- **Decision provenance captured**: yes; the roadmap and ratified WP12D
  amendments define the promotion boundary

## Dependencies

### Prerequisites

- WP11 Forest acceptance
- WP12B locale/view authority acceptance
- WP12C five-locale Builder acceptance
- WP12D run UI and capability-refresh acceptance

### Blocks

- WP13 shared `_defaults.toml` alias retirement

## Related Packages

- **Depends on**: `20260804_project_config_forest_acceptance`,
  `20260827_project_config_locale_authority`,
  `20260827_project_config_builder_locale_expansion`, and
  `20260827_project_config_run_ui_authority`
- **Follow-up**: WP13 defaults alias retirement

## Timeline Estimate

- **Expected duration**: one promotion and observation cycle
- **Complexity**: High
- **Risk level**: High

## Security Impact and Review Gate

- **Security impact triage**: high
- **Dedicated security review required**: yes
- **Triage rationale**: production deployment activates authenticated project
  creation and mutation paths and relies on rollback-safe reader behavior
- **Security review artifact**:
  `docs/work-packages/20260804_project_config_production_cutover/artifacts/20260831_security_review.md`

## Hardening and Callus Softening

This is a promotion package, not a new incident mitigation. Health signals are
successful authenticated and legacy reads, successful authorized project
mutations, healthy web/RQ workers, and no increase in canonical error codes.
Danger signals are authentication rejection for valid users, manifest/config
inconsistency, worker incompatibility, or inability of the selected rollback
reader to open `_defaults.cfg`. The observation window and exact evidence will
be recorded during production rollout. No temporary callus is authorized.

## References

- `docs/schemas/project-owned-config-implementation-roadmap.md`
- `docs/work-packages/20260804_project_config_forest_acceptance/`
- `docs/work-packages/20260827_project_config_locale_authority/`
- `docs/work-packages/20260827_project_config_builder_locale_expansion/`
- `docs/work-packages/20260827_project_config_run_ui_authority/`

## Deliverables

- Final scope and gate evidence
- Reviewed canonical merge revision
- Production deployment and observation record
- Rollback inventory and WP13 handoff

## Follow-up Work

- WP13 removes only the shared `_defaults.toml` alias after the required later
  release and rollback gates.
