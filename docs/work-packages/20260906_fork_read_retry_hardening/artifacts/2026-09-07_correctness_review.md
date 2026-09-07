# Correctness and User-Experience Review — FORK-READ-01

## Metadata

Reviewer: independent `contract_correctness` reviewer agent, 2026-09-07 UTC.
Author recorded the returned review and dispositions. Implementation follows
checkpoint `2ad307aeb` on master. Scope: NoDb read context, initial WEPP prep,
child lineage/callback, production worker supervisor, and associated tests.
Canonical authority: FORK-READ-01 sections of NoDb persistence and RQ response
contracts and ADR-0049. Related: QA and security artifacts in this directory.

## User Outcome

A brief missing/stale initial controller read can recover without replaying
input generation. Persistent or unrelated errors fail explicitly. Failed fork
children identify their job in source status and preserve a failed destination
outcome while strict downstream stages remain blocked. Active siblings may
finish before polling presents terminal failure. Outputs are not implied ready.

## Valid-State Matrix

| State | Required behavior | Direct evidence |
| --- | --- | --- |
| Optional absent/disappearing | Immediate None without stale cache | `test_initial_retry_missing_disk_never_reuses_cache`, `test_optional_disappearance_at_signature_does_not_retry` |
| Required absent | Bounded retries, original ENOENT | Same missing-disk test, actual atomic-publication tests |
| Empty/malformed | Immediate decode/type failure | `test_initial_retry_malformed_payload_is_not_retried` |
| Populated cold/singleton/Redis | Correct state/signatures, no sleep | `test_initial_retry_healthy_and_legacy_payload_no_delay` |
| Legacy missing signature fields | Hydrate and establish signatures | Same healthy/legacy matrix |
| Foreign/stale/absent callback lineage | No mutation or source publication | `test_invalid_or_legacy_callback_cannot_publish` |
| Current failed child, active siblings | Immediate receipt; poll active then failed | `test_actual_rq_callback_records_failure_and_preserves_strict_tree` |
| Abrupt work-horse exit | Supervisor publishes guarded failure | `test_actual_work_horse_death_reports_fork_failure` |

## User-Reachable Error Policy

ENOENT/ESTALE after budget exhaustion remain exceptional filesystem errors.
Permissions, EIO and other errno values fail immediately. Empty/corrupt payloads
are invalid required state; parsing never retries. Optional ENOENT is expected
absence, not an error. Redis failure reporting is best-effort with logging and
preserves the original task error. These policies are authorized by the two
canonical FORK-READ-01 sections.

## Review Checks and Evidence

The checkpoint predates implementation. Read-state and callback matrices are
separate. Actual filesystem ENOENT/atomic publication and NoDb decode are
exercised; fault-injected ESTALE is explicitly not a NAS reproduction. Actual
Redis/RQ jobs and a forked production worker exercise atomic callback and
supervisor boundaries. Translation/mutation test failures prove the read scope
ends before those operations and no whole-job replay occurs.

Focused combined validation: 228 passed. The reviewer independently ran
33 NoDb subset tests. Actual Redis/RQ tests assert the live registered job tree
reports queued with active siblings, then failed with blocked descendants.

## Findings

| ID | Severity | Finding | Disposition |
| --- | --- | --- | --- |
| COR-01 | Medium | Optional disappearance during later signature stat retried/raised | Resolved: propagate optional policy through every signature, add interleaving tests |
| COR-02 | Medium | RQ skips callback on abrupt work-horse exit | Resolved: supervisor guarded reporting plus real forked-exit test |
| COR-03 | Medium | Supervisor status fetch could escape reporting boundary | Resolved: narrow RedisError catch plus injected-error regression preserving subsequent publication |

## Verdict

Pass for local implementation. Reviewer confirmed no remaining medium/high
findings. Production rollout remains on hold for production-equivalent full
workflow evidence; the local tests do not establish recovery on the production
NAS. This is not a claim of exhaustive model/input coverage.
