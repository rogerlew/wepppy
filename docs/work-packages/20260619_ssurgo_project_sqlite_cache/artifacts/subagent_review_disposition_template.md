# Subagent Review Disposition Template

Use this template for both required subagent review artifacts:

- `artifacts/code_review_findings.md`
- `artifacts/qa_review_findings.md`

For the mandatory security review, use `docs/prompt_templates/security_review_template.md` and write `artifacts/security_review.md`. Security findings still need explicit disposition and no unresolved medium/high findings before package closure.

## Review Metadata

- **Reviewer role**: `reviewer | qa_reviewer`
- **Review date**: YYYY-MM-DD HH:MM UTC
- **Reviewed scope**: List files, tests, and docs reviewed.
- **Validation observed**: List commands/results the reviewer saw, or state `not run`.

## Findings

### Finding 1: Short Title

- **Severity**: critical | high | medium | low | note
- **Status**: accepted-fixed | accepted-pending | rejected | deferred
- **Location**: `path/to/file.py:line`
- **Issue**: Concise description of the defect, risk, or missing test.
- **Recommended action**: Concrete proposed fix.
- **Disposition**: What the implementation agent did, or why the finding was rejected/deferred.
- **Verification**: Command, test, or inspection proving the disposition.

## Summary

- **Unresolved critical/high findings**: none | list
- **Unresolved medium findings**: none | list
- **Residual risk accepted by package owner**: none | describe
