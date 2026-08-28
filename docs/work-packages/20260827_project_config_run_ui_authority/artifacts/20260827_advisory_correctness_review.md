# WP12D Advisory Correctness Contract Review

**Status**: Superseded. This review covered unratified amendment
`PC-24/WP12D-20260827-1`, which the operator replaced with the `.cfg`-owned
locale model in amendment 2. It provides chronology only and grants no current
readiness.

## Metadata

- **Package**: `docs/work-packages/20260827_project_config_run_ui_authority/`
- **Reviewers**: independent `contract_correctness_review` agent
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
| ACOR-01 | High | Locale query key/grammar, both links, and pre-description behavior were ambiguous. | Resolved in the exact query and link rules. |
| ACOR-02 | High | Curated config/card membership was incomplete and Canada could be mislabeled. | Resolved by the five-row matrix, Canada no-match, and no-new-launch-form rule. |
| ACOR-03 | High | RHEM cannot pass geographic composition resolution. | Resolved with a single-non-Builder validation branch and invalid-composition failures. |
| ACOR-04 | Medium | A disabled outside-authority dataset could hide authorized recovery choices. | Resolved by rendering all stored-authorized datasets plus exactly one disabled current dataset. |
| ACOR-05 | Medium | Evidence did not directly prove exact-current positives and different-unsupported negatives. | Resolved by per-domain direct build/rejection evidence with no-mutation assertions. |
| ACOR-06 | Medium | Route and state coverage were open-ended. | Resolved in the exact surface/source matrix and hostile/legacy state matrix. |

## Advisory Verdict

The draft's behavior is internally consistent after disposition. The binding
correctness gate remains pending operator ratification, canonical amendments,
and an independent review of that exact diff.
