# Roads native worker hotfix, 2026-10-27

## Cause and authority

Production Roads passed `wbt=True` but its native tracer rejected the keyword.
The paired wepppyo3 commit `71ec98a` existed locally while GitHub main remained
at `47e51b8`. The production Dockerfile clones GitHub; its interchange startup
check does not validate the Roads tracer. Both commits and the standing
push-after-commit rule (`dfad984`) are now published on wepppyo3 main.

The operator requested hotfixes on wepp1/wepp2 workers and explicitly authorized
atomic updates with active jobs. No worker restart, queue change, or project
mutation was performed. This record is separate from the closed October 26
implementation package and the project-page rendering repair.

## Applied change

Changed only `roads_flowpath_rust.so` in
`/opt/vendor/wepppyo3/release/linux/py312/wepppyo3/roads_flowpath/`.
Verified the previous checksum before each replacement, copied the old file to
a timestamped backup, preserved owner/group/mode, fsynced the staged replacement,
then used `os.replace` within the same directory. No worker process had the old
Roads module mapped before replacement.

- Previous SHA256: `58d0433a52d99630d607f6e5be198b8bcf2e3fb0d93cb395e29027c2e4968e45`
- Installed SHA256: `5d1f7be2e8176af5d762936b8c5cbe290450c2c2cbe134055d296f8fbd730a34`

| Host | Container | UTC replacement/backup suffix |
| --- | --- | --- |
| wepp1 | docker-rq-worker-1 | 20261027T172559Z |
| wepp1 | docker-rq-worker-batch-1 | 20261027T172600Z |
| wepp2 | docker-rq-worker-1 | 20261027T172607Z |
| wepp2 | docker-rq-worker-batch-1 | 20261027T172609Z |

Backups are alongside the module as `roads_flowpath_rust.so.bak.<suffix>`.
Scripts staged on each host: `/tmp/roads-hotfix-apply.py` and
`/tmp/roads-hotfix-verify.py`. Applied with targeted `docker exec -u 0`; validation
used each container's configured runtime user through ordinary `docker exec`.

## Validation and limits

In every container, the normal installed import exposes `wbt`, has the expected
checksum, and successfully traces the actual clogging-starch rasters. Segment
000001 reaches channel 204; segments 000020 through 000023 reach channel 154.
All 20 production-data checks passed. Container start times remained unchanged.
The active watershed job `60cc1de8-5c7c-4b29-a291-3ea157985c89` and log compilation
job `c9b8314e-369c-41c7-8bea-6c8262ec22b5` were not interrupted.

No full Roads job was resubmitted, so this establishes repair of the native
tracing failure, not completion of regenerated model outputs. Other services
were outside the requested worker hotfix scope.

The hotfix persists across container restart, but recreating from the old image
would remove it. The next canonical `scripts/deploy-production.sh` rebuild must
consume the now-published wepppyo3 main before recreating workers. Verify the
installed checksum and `wbt` signature after that rebuild. Retain the backup
until the rebuilt image passes those checks; rollback of this library alone
would reintroduce the caller mismatch.

Tooling friction: `wctl rq-info --detailed` failed because installed RQ rejects
`--detailed`. Activity was instead inspected through Redis started-registry
membership and RQ worker/job metadata without clearing or requeueing jobs.
