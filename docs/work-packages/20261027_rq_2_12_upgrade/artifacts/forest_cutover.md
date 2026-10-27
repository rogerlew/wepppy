# Forest runtime cutover

Executed 2026-10-27 19:36–19:39 UTC. Host forest, Docker default local Unix
socket, installed wctl development preset, Compose project docker.
Implementation revision `b5cac8166` descends from accepted checkpoint `b1054fac7`.
Dashboard sibling source revision `91f62b9` descends from `860ce63b` and matches
`docker/patches/rq-dashboard-rq212.patch`.

## Rebuild and preservation

Canonical `wctl docker compose build weppcloud` rebuilt all Python dependencies;
`wctl docker compose build rq-dashboard` rebuilt its separate Python runtime.
The first main build revealed unrelated floating dependency drift. Four exact
baseline pins removed it before final rebuild. Installed distribution comparison
in `installed-dependency-delta.json` proves only RQ1.16.2→2.12.0 and new
croniter6.0.0 differ in the main environment. Redis remains6.2.0.

Main image: `sha256:88a982e44d316824f493c99d0c3a9a3db3e4800feef86ff2c65693677039162b`.
Dashboard image: `sha256:019fbdf6ba5c5027149115e30818a8542b6bf33c78be43bc8e77fe841beb2087`.
Original main image retained as `wepppy-rq212-rollback:20261027`; original
dashboard as `rq-dashboard-rq212-rollback:20261027`. No image pruning occurred.

Before warm stop, all11 registered workers were idle and every observed raw
started registry was empty. Stopped exactly the16 shared-image services plus
dashboard with `wctl docker compose stop --timeout 216000` and the explicit
service list retained in `cutover-stop.log`. No unrelated workhorse was killed.
After stop, raw started and intermediate registries were empty and no worker
remained registered (`cutover-drain.json`). Preserved retained jobs, queues and
project data; never flushed Redis or deleted a volume.

A quiescent32,508,492-byte Redis replication snapshot was captured with the
existing secret-file authentication boundary. It is private recovery data, not
a repository artifact: `.pytest_cache/rq212-private/precutover.rdb`, parent mode700,
file mode600. The Redis-container temporary snapshot is also mode600. Never
publish it or restore it over newer accepted work. `cutover-snapshot.log` contains
only command/transfer status, not credentials or payload. This snapshot is not
an authorization or proof for in-place downgrade; isolated original-state
rollback evidence remains the narrower certified procedure.

Recreated the same17 services using `wctl docker compose up -d --no-deps
--force-recreate` with the identical explicit list (`cutover-recreate.log`). Redis,
PostgreSQL, Caddy, status/preflight, CAP, WEPPcloudR and unrelated containers were
not recreated. The preexisting stopped f-esri orphan was left untouched.

## Runtime readback

`runtime_readback.py` captured `forest_runtime.json`: all17 relevant containers
import exactly RQ2.12.0 from their installed runtimes, with image IDs, source
mounts, configured/actual identity, groups, umask, hostname and process birth.
Normal Python services retain UID1000/GID993, shape-converter retains its
configured10001:10001 identity, and dashboard retains root. Umask0022 throughout.
No Compose identity, permission or mount configuration changed.

`wctl rq-info --detail` succeeded with11 fresh workers:6 default,4 batch,
1 fork-archive (`rebuilt-rq-info.log`). `/health` on the web service returned
JSON `"OK"`; rq-engine `/health` returned `{status: ok, scope: rq-engine}`.
An initial web probe incorrectly used `/weppcloud/health` directly on port8000
and returned404; the documented direct-service `/health` endpoint succeeded.

Health and versions are not artifact acceptance. Actual API/model/readback,
cancellation ownership and archive/restore evidence are retained separately.
The required `wctl run-pytest tests --maxfail=1` runs against the rebuilt service.
The preliminary overlay broad run was deliberately interrupted before cutover:
2547passed,48skipped,3subtests; this is partial evidence, not a full-suite pass.
Production was not upgraded and native webhooks were not enabled.
