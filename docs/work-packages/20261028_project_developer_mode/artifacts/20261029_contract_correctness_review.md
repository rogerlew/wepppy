# Independent contract/package correctness review

Reviewer: `/root/contract_correctness` (reviewer agent), 2026-10-29 UTC.
Scope: DM-01, SA-01, ADR-0088 and this package/ExecPlan, with read-only source inspection against base `cebb4b4283e408fd270126811f4dbbd1a8dfd8e2`. No implementation reviewed or changed.

## Findings

| ID | Severity | Finding and evidence | Required disposition |
| --- | --- | --- | --- |
| C1 | Medium | Permanent mode is unresolved for older archives. `project_rq_archive.py:431` deletes current state then restores archived Ron. | Operator chooses preserve or reject; amend contract/checkpoint/plan before acceptance. |
| C2 | Medium | Copy/archive can capture Ron=false, then elevated Wepp values after concurrent activation. `project_rq_fork.py:1460` and `project_rq_archive.py:291` copy files separately. | Require consistent mode/value publication and controlled real-boundary race tests; reuse lifecycle serialization or monotonic reconciliation. |
| C3 | Low | Activation may leave browser maximum attributes stale, preventing immediate use. | Specify current-page policy refresh while preserving unsaved edits. |

## Initial reviewer verdict (superseded below)

No other blocking design findings. Normal-mode defaults, strict activation role, role-independent subsequent submission, native compatibility and artifact acceptance are coherent. Clone variants and production-equivalent native/worker execution remain runtime gates. Design checkpoint held for C1; C2/C3 changes require confirmation. This is not runtime correctness approval.

## Post-fix confirmation

2026-10-29 UTC — Reviewer re-read revised DM-01, ExecPlan and artifacts. C2 and C3 are closed at design level; controlled clone/archive interleavings and immediate current-page refresh are specified. C1 remains open for operator policy. Reviewer confirms the findings and dispositions are faithful. Runtime validation remains pending. See primary [dispositions](20261029_review_disposition.md).

## Final design confirmation — 2026-10-29 UTC

Correctness reviewer confirmed C1 closed under the explicit operator lifecycle exception; C2/C3 remain closed. Incoming archive/source state wins without sticky state, mode-based rejection or an additional Dev check. Same-incarnation reconciliation respects replacement. No remaining blocking correctness findings or operator decisions. Editorial permanence wording in SA-01/ADR-0088 was also corrected. Runtime validation remains pending.
