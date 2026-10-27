# Independent inventory implementation review

## Findings

| ID | Severity | Evidence and impact | Required remediation | Status |
| --- | --- | --- | --- | --- |
| INV-IMPL-01 | Medium | Scheduler consumed a retained path with `resolve_scope(create=True)` before confirming managed containment. Replacing a discovered directory with a symlink could redirect standalone metadata initialization outside configured roots, or into another in-root scope. | Validate lexical configured-root membership and component nofollow before resolving helpers; check managed identity without creation before initialization. Exercise stream, dirty-index and retained-pending sources against external and internal symlink targets. | Fixed; seven new real filesystem/Redis cases passed in independent run. |
| INV-IMPL-02 | Medium | Removing a required root after a completed empty cycle still returned `completed`, zero failures and the old completion time. This regressed ADR-0104's next-tick unavailable-namespace behavior. Real reproduction: `inventory-root-loss-before-fix.log`. | Restore namespace/alias-aware availability checks outside the scheduler lease; invalidate completion and rediscover promptly after recovery without the daily delay. | Fixed; original reproduction and recovery/alias regressions pass in the final independent run. |

**Final disposition: PASS for the bounded implementation; no unresolved findings.**
Production capacity/role/rollout gates remain separate. No production operation
or implementation edit was performed by this reviewer.

## Scope and authority

Reviewer: `/root/inventory_security_review`, 2026-10-27 UTC. Reviewed
`wepppy/rq/_query_catalog_inventory.py`, `wepppy/rq/query_catalog_rq.py`,
`tests/rq/test_query_catalog_inventory.py`, affected existing RQ regressions and
the unchanged maintenance disclosure classifier. Contract checkpoint
`09ce55d1d` is an ancestor of HEAD; the inventory diff follows that checkpoint.
Security impact remains high because queue payloads and derived Redis locators
cross a worker/filesystem boundary. This artifact combines independent security
and correctness findings for this bounded slice; production gates remain separate.

## Checks established by inspection and focused tests

- Exact worker configuration now includes `inventory_protocol`; the filesystem
  receipt/incarnation protocol remains unchanged. Admission checks all live
  consumers, while execution checks both current configuration and the actual
  executing worker registration.
- Inventory task IDs use the existing canonical maintenance prefix/UUID helper,
  generic description and privacy metadata. Existing single/batch/recursive
  polling classifies before deserialization and exposes no locator, frontier,
  batch, result or traceback.
- The worker streams directory entries with finite checkpoints. Child dedup,
  frontier append, scope-stream append and directory exhaustion share one watched
  Redis transaction. Current job/cycle ownership and a generation watch fence
  old checkpoints; completed-directory removal follows published discoveries.
- Restart replays the unfinished directory prefix while retaining emitted
  children/scopes. A real killed-worker regression exercises retained progress,
  failed-job reconciliation/backoff and successor completion. This is retained
  Redis progress, not a persistent filesystem directory offset.
- Scheduler stream acknowledgment and its pending cursor commit atomically;
  transaction failure leaves discoveries unacknowledged. Lease renewal checks
  ownership and cannot revive an expired token. The inventory worker performs
  slow enumeration outside the scheduler lease.
- Missing required roots and traversal errors remain explicitly incomplete.
  Deleted non-root children can disappear without becoming phantom work. Nested
  project containers remain traversed while scientific output subtrees remain
  excluded. Actual boundary tests cover traversal/absolute locators and symlinks.
- Discovery writes only derived Redis coordination, never project metadata.
  Existing refresh code continues to own receipt/publication and READONLY gates.
  No new queue, service, dependency, credential, mount or privilege was added.

## Independent validation

Independent canonical-wrapper run against a confirmed disposable Unix-socket
Redis server (no production Redis, TCP listener or persistence):

```text
wctl exec -e BATCH_BOUNDARY_TEST_REDIS_SOCKET=/workdir/wepppy/.pytest_cache/inventory-test.sock \
  weppcloud /opt/venv/bin/python -m pytest \
  tests/rq/test_query_catalog_inventory.py tests/rq/test_query_catalog_disclosure.py \
  -q --maxfail=1
```

Result before the root-availability follow-up: **37 passed, no skips**, 13.02 s.
Log: [inventory-independent-tests.log](inventory-independent-tests.log).
An initial attempt without the disposable socket skipped the inventory tests
because `redis-server` is absent from the web container; that attempt is not
credited as integration evidence. Runs were serialized because the reusable
external-Redis fixture cleanup is not safe for overlapping test invocations.

The additional required-root-loss reproduction failed on the actual uncorrected
path, as expected; source and output are retained in
`inventory-root-loss-regression.py` and `inventory-root-loss-before-fix.log`.
That failure identified a product regression. The final run includes the exact
reproduction against the fixed source and passes; the normal test tree also
proves root restoration triggers a new full cycle immediately and refreshes a
new project without waiting 24 hours.

## Remaining release evidence

Full legacy/fleet discovery, worker-restart acceptance on representative storage,
oldest unreconciled age, checkpoint storage growth and shared-batch capacity
remain owning rollout gates. Fixed runtime bounds are not a measured SLO. The
existing read-only wepp3 legacy role must remain unchanged unless its actual
workflow demonstrates a separately authorized need.

## Final findings closure and source identity

The final independent run used the same confirmed disposable Redis and added
`tests/rq/test_query_catalog_rq.py` plus the original root-loss reproduction to
the command above: **66 passed, no skips**, 23.04 seconds. Retained result:
[inventory-independent-tests-final.log](inventory-independent-tests-final.log).

INV-IMPL-01 is closed by lexical configured-root/component validation before
resolving helpers, a noncreating managed-scope check, and validation again before
initialization. Stream, dirty-index and retained-cursor locators reject both
external and in-root symlink redirection without creating target metadata.

INV-IMPL-02 is closed by lightweight namespace/alias metadata probes before
acquiring the scheduler lease, clearing stale completion, and retaining a
rediscovery-required marker until a replacement cycle is actually admitted.
The exact failed reproduction now passes. A separate real regression renames
the same directory/project inodes to an explicitly configured alias and proves
retained stream/dirty locators reconcile and clean up correctly. Alias rebasing
is restricted to a missing original root with the same configured namespace and
layout; a symlink, permission failure or missing child is not silently redirected.
Unavailable alias diagnostics remain visible without treating an available
namespace as missing.

| Reviewed file | Final SHA256 |
| --- | --- |
| `_query_catalog_inventory.py` | `d39f056e243b7889b0dd50c2030c518b822f3d54e4263fb6f16a4b5e8cc86791` |
| `query_catalog_rq.py` | `839bafc4efa1b1f4161b3d7fec1b7f0a4c0c7e0b3652727f70bd6363404c0cac` |
| `test_query_catalog_inventory.py` | `33b817ae81aa8b599d2d0d5ec1eea1cfabae43dd7dc9255f634a52339330e3f1` |
| `test_query_catalog_rq.py` | `255e9d739c444cdb31b481b88e4092e0aaa2810e1219bf2d7b7aa3667ab2b52d` |

Cleanup: read back the `batch-boundary-test-server=disposable` marker, shut down
only the owned Unix-socket Redis with `shutdown nosave`, and verified its PID
2473841 no longer existed. No Compose/production Redis was used or stopped.
Doc lint passes. Security/correctness reviewer sign-off:
`/root/inventory_security_review`, 2026-10-27 UTC.
