# RedisPrep atomic ordered snapshots

Status: Open, 2026-10-31. Remediation ID: RPS-01. Timezone: UTC.

## Purpose and scope

Repair incomplete/backward snapshot publication and incoherent recovery in
RedisPrep and confirmed direct consumers. Source inspection confirms unsafe
mechanisms; no production corruption incident is asserted. The operator's exact
request is retained in `artifacts/operator-prompt.md`.

Complexity budget: one bounded snapshot/recovery protocol using existing Redis
and filesystem coordination; no service, database, dependency, deployment, queue
rewiring, auth/identity/privilege change or scientific parameter change. Preserve
WAM-01, MRS-01 and NFMS-01. No branch change. Operator authorized checkpoint commits, then implementation commit and push.

## Authority and execution

Canonical amendment: [snapshot contract](../../schemas/redisprep-snapshot-contract.md).
Execute [active plan](prompts/active/implementation_execplan.md), with live state
in [tracker](tracker.md). The checkpoint is an intended behavior change because
existing NoDbBase authority does not cover this independent helper. Two read-only
reviews and a standalone ancestor commit are required before implementation.

## Security and parameterization

Security impact: high (shared filesystem publication and restore/path handling).
Dedicated security review required before implementation handoff; contract review
is not final implementation approval. No parameterization change; ADR not required.

## Generated artifact acceptance

`redisprep.dump` must parse as complete old/new JSON, restore through the normal
RedisPrep reader and yield coherent receipts/timestamps to submission/preflight
consumers. Preserve the RQ database during metadata-loss tests. Exercise real
archive/restore and browse under representative identities; no model run needed
unless scientific execution changes. Current claim: locally verified implementation; production rollout remains held.

## Hardening and precedent

Reuse atomic-write lessons from NoDbBase, destination reset protections from fork,
and NFS/local record-lock lessons from catalog lifecycle coordination. WAM-01,
MRS-01 and NFMS-01 are preservation baselines, not authority to edit closed plans.

Hypothesis: serializing capture through replacement plus conditional atomic
recovery eliminates the reproducible failure class without altering successful
workflow meaning. Health: complete ordered artifacts, coherent consumer state.
Danger: stale receipts, resurrected timestamps, partial restore, new valid-state
rejections, lock-order deadlocks and excessive setter latency. Use recurrence-
triggered observation: any recurrence opens a new assessment against retained
artifact evidence. Rollout evidence remains separate; no temporary calluses.

## Exit criteria

- [x] Accepted contract ancestor exists before production/test implementation.
- [x] Confirmed writers repaired; consumer/state matrix dispositions evidenced.
- [x] Deterministic real Redis/process/filesystem failures and restore pass.
- [x] Required broad/static/docs checks executed; split-run results and reviews retained.
- [x] Identity/mount evidence or exact rollout blockers retained.
- [x] Operator/developer recovery guidance, plan and tracker current.
