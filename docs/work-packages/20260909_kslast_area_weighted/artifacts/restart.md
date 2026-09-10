# Local forest runtime restart

Executed the authorized `wctl down` and `wctl up -d` from the WEPPpy checkout,
using the installed development Compose preset. No volumes were deleted. The
second restart followed the reviewed numerical correction and final atomic
native refresh; model submission occurred only after that restart.

Before restart all default, batch and fork-archive queues had zero queued and
started jobs. The external full-run and native-pair backup is in baseline.md.
Compose services started; PostgreSQL/Redis/download readiness checks passed.

[restart.json](restart.json) records different old/new container IDs and running
states. [release_manifest.json](release_manifest.json) records Python and native
paths, user/group IDs, exact matching library SHA256, and successful real-raster
calls in fresh web, rq-engine, default-worker and batch-worker environments.
All selected `/workdir/wepppyo3/release/linux/py312` via normal runtime import
wiring, without a temporary PYTHONPATH override. No interchange library/pin or
production host changed.

Raw restart transcripts and complete Compose snapshots remain outside Git under
`/tmp/kslast-area-weighted-20260909/`.
