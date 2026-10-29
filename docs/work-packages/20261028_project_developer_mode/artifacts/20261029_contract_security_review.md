# Independent contract/package security review

Reviewer: `/root/contract_security` (security reviewer agent), 2026-10-29 UTC.
Scope: DM-01, amended SA-01/ADR-0088/feature governance/registry specification and this package/ExecPlan, with read-only source inspection against base `cebb4b4283e408fd270126811f4dbbd1a8dfd8e2`. No runtime approval or edits.

## Findings

| ID | Severity | Finding and evidence | Required disposition |
| --- | --- | --- | --- |
| SEC-DM-01 | Medium | Restore deletes live state and extracts archived Ron (`project_rq_archive.py:432,459`), allowing mode reset without a disable endpoint. | Resolve operator policy. Smallest option: reject downgrade before destructive writes under lifecycle fence. Preservation instead requires durable crash/retry safety; a worker-local boolean is insufficient. |
| SEC-DM-02 | Medium | Failed/canceled/planned fork recovery permits replacing an existing destination (`fork_archive_routes.py:1097,1238`). Recopying a normal source can erase target activation. | Apply an explicit destination-permanence policy and direct regression before destructive replacement. Ordinary new clones still inherit source mode. |

## Initial reviewer verdict (superseded below)

Hold for lifecycle dispositions; both can share one operator decision. Exact Dev activation, ordinary authorization afterward, non-Dev clone inheritance, native defaults, strict booleans, CSRF/readonly and unrelated-panel privilege containment are coherent. The specified activation endpoint/payload resolved the earlier API deferral. Require restore denial/preservation, unchanged-files, concurrency and failure/retry evidence. No runtime security approval is implied.

## Post-fix confirmation

2026-10-29 UTC — Reviewer confirms both findings are faithfully retained and explicitly open for operator choice. Contract/plan now name existing failed-fork recovery as well as archive restoration. Reject-before-destructive-work is a recommendation, not an approved decision. No additional security design findings identified; checkpoint and runtime gates remain held. See primary [dispositions](20261029_review_disposition.md).

## Final design confirmation — 2026-10-29 UTC

Security reviewer confirmed SEC-DM-01 and SEC-DM-02 closed at design level under the explicit operator contract amendment. This changes the intended invariant rather than implicitly waiving risk. Exact Dev authorization still governs dedicated activation; existing lifecycle authorization and incoming state remain authoritative. No additional design findings. Runtime security review remains pending.
