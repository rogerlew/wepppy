# Implementation QA review

Reviewer: independent secondary QA agent, 2026-10-23 UTC. Scope: maintainability,
observability and test robustness of the new publication/recovery modules, their
tests, and retained acceptance evidence. Runtime files were reviewed without
editing; this artifact is the reviewer's only repository change.

## Finding and disposition

| Finding | Severity | Status |
| --- | --- | --- |
| Atomic replacement changed an existing catalog from mode `0640` to `0644` and discarded its POSIX access ACL; new-file creation also lost group-write permission under umask `0002`. The prior `write_text` publisher preserved these behaviors. A discarded named-user deny ACL could widen access. | Medium; blocks permission-preservation acceptance | Closed. Independent mode, owner, ACL and new-file umask/default-ACL checks pass; preservation failure leaves original bytes intact. |

The finding concerns the contract's existing-permissions invariant, not a new
permission policy. Independent probes used disposable files through `wctl exec`
under the existing web service identity. They reproduced `0640 -> 0644`, loss of
`system.posix_acl_access`, and new-file `0664 -> 0644` under umask `0002`.

The corrected publisher stages replacement bytes privately, preserves and verifies
original ownership, mode and extended attributes, and fails before replacement if
preservation is impossible. New files use the prior `0666 & umask` creation
semantics, including default-ACL and setgid-directory inheritance. Independent
rechecks confirm `0640 -> 0640`, exact access-ACL retention, and new-file parity
at `0664` under umask `0002`.

## Quality assessment

The division between filesystem authority and Redis admission is understandable.
`catalog_refresh.py` owns scope identity, locks, receipts and publication;
`query_catalog_rq.py` owns coalesced admission and resumable recovery. The design
reuses existing infrastructure and avoids a generic queue framework. Deliberate
error boundaries retain durable intent and do not conceal missing dependencies.

The new tests use actual Parquet schemas, filesystem replacement, process/thread
coordination, and disposable Redis. They verify artifact contents and retained
receipts instead of only asserting mock calls. Lost-reply and WATCH injection
still execute real Redis transactions. The worker-death test kills a real process
and uses actual RQ abandonment cleanup, with an explicitly advanced cutoff. The
receipt-free unit case models the gap; separate environment evidence supplies the
actual producer SIGKILL at that boundary. This distinction is recorded honestly.

## Non-blocking follow-ups

- The core module is 821 lines, and `reconcile_query_catalogs`
  spans 135 lines. Both are cohesive enough for this change, but the latter mixes
  discovery, candidate merging, admission and cursor publication. If extended,
  extract those phases into small private functions in the same module; retain
  the existing real-Redis regressions. No new framework is warranted.
- Parquet schema formatting is duplicated between `activate._read_parquet_schema`
  and `catalog_refresh._verify_required`. A shared pure formatter would reduce
  future native/PyArrow representation drift while preserving the distinct
  best-effort reader and strict error behavior.
- `test_guard_is_shared_by_processes_and_nested_scopes` uses a 0.2-second negative
  wait without a signal that the contender has attempted acquisition. Under load
  this can mask a missing lock. A separate attempt handshake or nonblocking
  acquisition result would make this test more deterministic. The retained
  cross-host and Roads tests provide additional evidence for the current guard.

## Validation and limits

Independent QA execution: `wctl run-pytest tests/query_engine/test_catalog_refresh.py
-k atomic_json --maxfail=1 -q` passed **8 tests**. These cover mode/ownership/ACL
preservation, failure refusal, and new-file parity under both `0002`/`0022` umasks
with and without actual Linux default ACLs. Direct before/after permission probes ran
in the web container. No production host, project or active model run was changed.

Other agents' supplied evidence is not counted as this reviewer's execution:
26 real-Redis tests with zero skips, 33 core tests before the permission additions,
reader/report tests, native heartbeat/parity, and authenticated browse/archive
readback. See [execution evidence](execution_evidence.md),
[correctness review](implementation_correctness_review.md), and
[security review](implementation_security_review.md) for exact scope and results.

Full repository regression and the isolated complete model/report workflow were
still running at review time. Deployment identity, companion configuration and
fleet capacity remain separate rollout gates. This review cannot establish
production readiness or incident resolution.

## Verdict

No unresolved blocking QA finding in the reviewed implementation. The permission
finding is closed; the follow-ups above are non-blocking. Final regression, complete
model/report acceptance and rollout gates remain owned by the execution lead.

Reviewed source SHA256: `catalog_refresh.py`
`1f19401a875246e621fdeea398cf4f42d6fb288eef591ad5d611c19b6fd3dcd5`;
`query_catalog_rq.py`
`b8b8e9a9cae212333d694e2e1f56df5fdd313a611f09bd5aea0d35f07d0bfa5c`.
