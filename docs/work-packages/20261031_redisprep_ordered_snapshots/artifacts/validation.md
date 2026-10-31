# RPS-01 implementation validation

2026-10-31 UTC. Contract ancestors: `88b5c174f`, `ea95e1298`; implementation
is an uncommitted worktree. See `source-manifest.sha256` for delivered source.
No deployment, production jobs, dependency additions or branch changes.

## Executed checks

| Check | Result | Evidence |
| --- | --- | --- |
| Snapshot suite, disposable real Redis, NFS | 52 passed, 15.19s | nfs-tests.log |
| Fork/archive/submission/WEPPcloudR consumers | 183 passed, 42.72s | consumer-tests.log |
| WAM/MRS/NFMS preservation | 199 passed, 37.19s | prior-repair-tests.log |
| Snapshot/batch/read-only/catalog/postfire focus | 162 passed, 39.44s (49 snapshot tests at that point) | terminal run 71679 |
| RedisPrep stubtest | Pass | stubtest.log |
| Shared test stub hygiene | Pass | stub-check.log |
| Broad continuation, current files | 8,619 passed, 295 skipped, 1,893s | broad-continuation.log |
| Documentation lint | 13 package files and targeted contract/operator/AGENTS docs pass | doc-lint.log |
| Changed broad exception gate | Pass, net zero | broad-exceptions.log |
| Code quality observability | Recorded, nonblocking | code-quality-summary.md |
| Correctness/security/QA independent review | Approved local delivery; no remaining medium/high findings | dated review artifacts |

Wrapper commands are retained where emitted in logs. Focused consumer command:
`wctl run-pytest tests/rq/test_project_rq_fork.py tests/rq/test_project_rq_archive.py tests/rq/test_submission_recovery.py tests/weppcloud/routes/test_weppcloudr_proxy_security.py --maxfail=1`.

The initial consumer run found omitted post-extraction retirement of copied
nested catalog identities (162 passed, one failed). The existing invalidation
was restored while retaining the new pre-destructive fence. Final 183 pass;
independent correctness reviewer approved this correction. Initial failure log
is retained as `consumer-tests-initial-failure.log`.

## Broad suite provenance

`wctl run-pytest tests --maxfail=1` collected 12,931 items and stopped after
3,958 passed, 125 skipped and one failure in 1,805.52s. It began before final
postfire mock assertions were edited, so its loaded test still expected the old
pipeline API. The corrected module passes in the focused current-file run.
This is not a final-revision complete suite pass. A current-file continuation
from that module is recorded in `broad-continuation-files.txt` and
`broad-continuation.log`: **8,619 passed, 295 skipped, 5,762 warnings in
1,893.00s**. No continuation failures. Counts overlap the starting module and
must not be summed as unique coverage. The broad command skips snapshot
integration tests without a disposable Redis socket; the separate 52-case NFS
run supplies that evidence.

## Artifact and consumer evidence

The 52-test suite uses real Redis/processes and actual JSON artifacts. It covers
ordered capture with observed kernel contention; concurrent setters/readers;
short writes and pre/postpublication faults; killed writers/loaders/restores;
WATCH conflicts; atomic loaded restoration; retained RQ job duplicate rejection;
missing RQ job semantics; actual Omni and WEPPcloudR consumers; archive roundtrip,
mode preservation, failure fencing and nested hash collision; two real batch
leaf initialization boundaries. Tests never flush shared Redis or erase RQ state.

## Runtime identity and performance

`access_probe.py`/`access.jsonl` record web, rq-worker, fork/archive-worker and
browse service access to one actual NFS snapshot. All ran UID1000/GID993;
owner/group and mode0640 survived writes, receipt/timestamps survived readback.
Browse used the actual service identity and JSON reader, not authenticated HTTP.
NFSv4.2 has local_lock=none; workspace is ext4. This is one NFS client.

`benchmark.py` compares starting revision `967627f4c` to the candidate using
64 fields/1,887 bytes, 100 samples, 1,000 wrapper churn.

| Mount | Setter median/p95 baseline ms | Candidate ms | Startup median/p95 baseline ms | Candidate ms |
| --- | --- | --- | --- | --- |
| NFS | 2.509 / 3.136 | 9.942 / 12.374 | 0.165 / 0.228 | 1.810 / 3.080 |
| ext4 | 0.748 / 0.878 | 4.520 / 4.936 | 0.122 / 0.153 | 1.050 / 1.214 |

Both implementations had zero net descriptor growth. This is an explicit
durability/coordination cost, not a throughput benchmark. Raw JSON retained.

## Limits and rollout hold

No production-equivalent cross-host NFS/local-server lock, bind-mount alias,
other runtime identity, ACL/xattr variation or authenticated browse proof. Those
remain required before deployment. Basename collisions and profile skeletonize
support remain unresolved preexisting boundaries, not silently migrated. An
already-partial legacy hash marked loaded cannot be distinguished from a later
legitimate deletion; the operator accepted explicit reconciliation. No
production corruption incident or class-wide namespace isolation is claimed.

## Reproduction and cleanup

For the NFS suite, run through `wctl exec weppcloud` with
`RQ212_TEST_REDIS_SOCKET=/workdir/wepppy/.pytest_cache/rps-redis/server.sock`
and `/opt/venv/bin/pytest tests/nodb/test_redis_prep_snapshots.py --basetemp=/wc1/runs/rps-validation-xkfrIZeK/final-tests --maxfail=1`.
That socket is an explicitly disposable installed host redis-server (port0, no
AOF/save, fixture guard key), not shared application Redis. The original server
and unique scratch are cleaned at handoff; recreate isolated scratch/server to
repeat. Benchmark/access scripts accept paths; never substitute an active run.

Cleanup completed: disposable Redis shut down without saving; exact owned NFS,
local benchmark and socket scratch directories removed. Retained evidence only.

Final source manifest verification and `git diff --check` passed. Spelling preview
found only “pre-existing” in the retained checkpoint decision; no implementation
prose correction was needed. Independent review approvals remain unchanged.
