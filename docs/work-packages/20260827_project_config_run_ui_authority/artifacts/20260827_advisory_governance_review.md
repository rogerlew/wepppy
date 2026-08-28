# WP12D Advisory Governance Contract Review

**Status**: Superseded. This review covered unratified amendment
`PC-24/WP12D-20260827-1`, which the operator replaced with the `.cfg`-owned
locale model in amendment 2. It provides chronology only and grants no current
readiness.

## Metadata

- **Package**: `docs/work-packages/20260827_project_config_run_ui_authority/`
- **Reviewer**: independent `contract_governance_review` agent
- **Date**: 2026-08-27
Initiative branch: feature/project-owned-config
Canonical branch: master
Promotion policy: merge only at the roadmap promotion gate
- **Context**: proposed amendment at starting/upstream revision
  `5e04e0da9a23dd676e171f1857e14fa38cc9dfbe`
- **Gate effect**: advisory only; this review does not count as a required
  independent review of the ratified canonical checkpoint diff

## Findings and Disposition

| ID | Severity | Finding | Disposition |
| --- | --- | --- | --- |
| AGOV-01 | High | The implementation source boundary permitted unnamed paired modules. | Resolved by enumerating every route module and requiring re-ratification for an unlisted file. |
| AGOV-02 | High | The canonical promotion map was described only as amendments "as required." | Resolved by naming the exact project-config, feature-registry, roadmap, controller-contract, and unchanged ADR treatment. |
| AGOV-03 | Medium | WP12C remains open and its evidence floor was not exact. | Resolved with candidate `b31eeb625`, audit correction `f6784420a`, reader floor `187a856d4`, and a non-substitution rule. |
| AGOV-04 | Medium | Branch/promotion declarations and affected PC requirements were incomplete. | Resolved across the decision, package, tracker, and active ExecPlan. |
| AGOV-05 | Medium | Dirty exclusions were categories rather than reproducible paths. | Resolved with the complete exact path list and path-stage requirement. |
| AGOV-06 | Medium | Mandatory registry-field compatibility and rollback were unspecified. | Resolved with schema-version-1, atomic deploy, old-reader, and Forest rollback behavior. |

## Advisory Verdict

The proposal is ready to be presented for exact operator ratification after
these dispositions. Binding governance approval remains pending review of the
ratified canonical checkpoint diff.
