# Initial Contract Reviews

## Correctness Review

**Reviewer**: `/root/contract_review_correctness`  
**Verdict**: Reject pending remediation

The reviewer found medium gaps in user-reachable failure semantics, separate
input/state coverage, single-OFE invalid-value compatibility, and all-file area
evidence, plus a low ADR timestamp gap. The reviewer confirmed the shared-width
area formula and checkpoint ancestry state.

## Governance Review

**Reviewer**: `/root/contract_review_governance`  
**Verdict**: Reject pending remediation

The reviewer found high gaps in request/state matrices and canonical RQ failure
behavior; medium gaps in file-boundary security triage, ADR provenance and
rollback triggers, and exact Forest deployment/recovery; plus a low project-
tracker state mismatch.

## Disposition

All findings were accepted. The checkpoint now defines exact unchanged alias
and parsing behavior, separate request and persisted/filesystem state matrices,
expected versus exceptional async failure outcomes, the valid single-OFE and
invalid-state compatibility delta, every-file Forest artifact proof at `1e-9`
tolerance, high security triage with a dedicated review, exact decision time and
rollback triggers, and bounded Forest service recreation/rollback commands.
The package entry is moved to In Progress. Post-fix confirmation is required
before the standalone checkpoint commit.

## Post-Fix Confirmations

- `/root/contract_review_correctness`: **PASS / APPROVE** after the exact
  alias-null/all-empty/scalar-empty fallback matrix was added. All original
  findings are closed; implementation conformance remains pending.
- `/root/contract_review_governance`: **APPROVE** after exact non-finite
  behavior, ADR compatibility, high security triage, and guarded additive
  Forest rollback were aligned. All original findings are closed.
