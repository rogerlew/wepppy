# Restore sentinel and existing NFS retained-log limitation

**Date:** 2026-10-27 19:49–19:54 UTC.
**Result:** missing output restored; full generated-content and report readback passes.

## Strong restore proof

The original archive test restored a populated tree. To exclude a no-op restore,
removed only disposable project `rq212-20261027-upgraded` file
`wepp/output/interchange/loss_pw0.out.parquet` after verifying its bytes matched
archive `rq212-20261027-upgraded.20261027T194322Z.zip`. The receipt proves the
file was absent after injection and still absent before the successful retry.

Initial job `711e653e-0c07-4f31-863c-78bad9ebe088` failed with EBUSY while removing
an already-retained `.nfs` log file; extraction had not begun. Failure and exact
traceback are in `acceptance_restore_repair_initial_failure.json` and its log.
After bounded process recovery, canonical restore job
`cb1c0901-5564-45a9-a649-5aeebe7135e5` finished. Before/ZIP/restored SHA256:
`1a41623beb5222c62aecd740edc6de07e6a7dc1db46a0c6f06e7308394ee3af7`.
Actual outlet CSV returned 200 and exactly matched retained pre-injection bytes.
`acceptance_restore_repair.json` retains the absence, recovery and report proof.

The final whole-artifact recheck opens all 25 Parquets, checks all 184 executable
input/diagnostic files, retrieves all three summary CSVs and compares all 417
files under `wepp/runs` and `wepp/output` with their original ZIP member hashes.
All pass; see `acceptance_final_repaired_manifest.json`,
`acceptance_upgraded_repaired_readback.json` and `acceptance_repaired_comparison.json`.

## Classification evidence

This is an existing file-handle lifecycle limitation, not inferred merely from
when the failure occurred. `git diff 9231f2427d33b64f971992ac969fd9420c49afd3 --`
for `wepppy/rq/project_rq_archive.py`, `wepppy/nodb/base.py` and
`wepppy/weppcloud/routes/nodb_api/wepp_bp.py` is empty. The unchanged restore
implementation removes run contents before extracting validated ZIP members.
The unchanged NoDb logger retains file handles in long-lived process caches;
its process-local `cleanup_run_instances` closes them, whereas the public
`clear_nodb_cache` route only clears Redis payloads.

A direct probe on the same NFS mount and UID 1000/GID 993 uses only Python
`logging.FileHandler`, with no RQ import or job: unlink an open log, observe the
NFS temporary file, attempt its unlink and receive errno 16, then close the
handler and observe automatic removal. Its temporary directory was removed.
Evidence and reproducer: `acceptance_nfs_mechanism.json` and
`acceptance_nfs_mechanism_harness.py`. This proves the mechanism independently of
RQ; it is not a claim that a second full 1.16.2 restore was executed.

## Exact ownership and safe recovery

Read-only container-local `/proc/*/fd` inspection found these handles for the
package-owned upgraded project:

| Service | PID | FD | File |
| --- | --- | --- | --- |
| weppcloud | 213 | 22 | `.nfs000000000019b67100000081` |
| weppcloud | 213 | 23 | `.nfs000000000019b8bc00000085` |
| weppcloud | 213 | 24 | `.nfs000000000019b8b600000082` |
| rq-engine | 7 | 21 | `.nfs000000000019b8be00000086` |
| rq-engine | 7 | 23 | `.nfs000000000019bb1000000087` |
| rq-engine | 7 | 24 | `.nfs000000000019b8b900000084` |
| rq-engine | 7 | 26 | `.nfs000000000019b8b600000082` |

Web worker 214 held current climate/unitizer/Ron logs. Browse, download and
query-engine had no handles for this project. Both web port 8000 and rq-engine
port 8042 had only LISTEN sockets and no established requests immediately before
recovery. Local Docker context and project were unchanged: forest/default Unix
socket, Compose project `docker`, development services.

The canonical deployment-tuning knowledgebase's graceful reload procedure was
adapted to the inspected layout: PID 1 is docker-init, actual Gunicorn master is
PID 7. At 19:51:06 UTC executed:

```bash
wctl docker compose exec -T weppcloud kill -HUP 7
wctl docker compose restart --timeout 60 rq-engine
```

Gunicorn children 211–214 exited gracefully and were replaced by
79975–79978. The weppcloud container and pytest exec PID 1011 survived; RQ worker
pools were untouched. All six stale NFS files disappeared after their owners
closed. The first immediate rq-engine health probe raced its startup and saw
connection refused; subsequent actual API restore/report succeeded and final
health returned 200 `{status: ok, scope: rq-engine}` with RQ 2.12.0.
Retained evidence: `acceptance_nfs_web_reload.log`,
`acceptance_nfs_process_after.log`, `acceptance_nfs_health_after.log`.

## Remaining operational limitation

No NFS lifecycle code was changed by this package. A later restore can create a
new retained log handle again when long-lived API processes have loaded the
project. Repeated restores may require the same inspected, graceful closure of
specific holding services. Never blindly unlink `.nfs` files or alter queue/lock
state as a substitute. This bounded recovery preserves jobs and container execs;
a general cross-process NoDb log-eviction change would be a separate task.
