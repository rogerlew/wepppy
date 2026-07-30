# Local Runtime Smoke

**Date**: 2026-07-30 UTC

**Environment**: Forest development stack at `wc.bearhive.duckdns.org`.

**Acceptance status**: operational smoke only; the contract-required
preference mutation/new-run canary remains blocked until final re-review.

## Profile and preferences

The web container initially had a mixed runtime after bind-mounted templates
changed without a process restart: the Profile template referenced
`user.preferences`, but the running Flask route map predated that endpoint.
The resulting `BuildError` matched the user-reported error ID.

After the repository-wide Python gate completed, only the local `weppcloud`
service was restarted. Route-map inspection then confirmed both
`user.profile` and `user.preferences`. Authenticated requests through the real
Redis session interface returned:

```text
/weppcloud/profile      200, User Preferences link present
/weppcloud/preferences  200, Stop with an error choice present
```

No session identifier or account credential was printed or retained.

## RQ worker synchronization

A project task enqueued after the web restart failed because the still-running
workers retained their earlier import state while reading changed bind-mounted
source. RQ masked the underlying import attempt as an invalid
`wepppy.rq.project_rq.fetch_dem_and_build_channels_rq` attribute.

`wctl rq-info --raw` showed both queues with zero executing jobs and every
worker idle. The local `rq-worker` and `rq-worker-batch` services were then
restarted together. Only the affected failed job was requeued. Its complete
tree reached:

```text
status=finished
progress=3/3 (100%)
fetch_dem_rq=finished
build_channels_rq=finished
```

This was local development recovery only. Forest and production were not
changed.

## Isolation gate tooling

The canonical wrapper was also found to invoke the isolation checker with the
container system Python, which lacks pytest. When invoked with the virtualenv,
the checker then hit a Pytest 9 compatibility error by reading an optional
`TestReport.wasxfail` attribute unconditionally. The wrapper now selects
`/opt/venv/bin/python`, and the recorder uses an optional attribute lookup.
Regression tests pass, and the SURF-14A package scope now completes two suite
runs plus every per-file run with:

```text
No isolation issues detected.
```
