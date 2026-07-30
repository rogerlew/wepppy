# Local Runtime Smoke

**Date**: 2026-07-30 UTC

**Environment**: Forest development stack at `wc.bearhive.duckdns.org`.

**Acceptance status**: operational smoke only; the contract-required two-user
presentation/action canary remains blocked until amendment review.

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

## Full-stack reload and live preference findings

A later browser-created project proved the account row was `si` while its
persisted Unitizer remained English. Rq-engine had not been restarted with the
first web/worker recovery and was still executing pre-feature creation code.
The operator ran a complete `wctl down` followed by `wctl up -d`; a subsequent
new project inherited SI under the then-current creation-time implementation.
The operator later clarified that this is the wrong lifetime: SI/English must
alter that user's presentation without mutating project Unitizer state. This
is retained as negative/superseded evidence, not acceptance.

Two WBT jobs then established a separate lifetime defect in the
original contract:

- a run created with persisted `warn` finished on eight edge hillslopes after
  the initiating user selected `error`; and
- `depleted-hyperlink`, created with persisted `error`, failed on seven edge
  hillslopes after the initiating user selected `warn`.

The second root was `4b81f2cb-0b6f-4743-a152-5e7f9b658541`. After it was
terminal, the exact run's persisted boundary policy was repaired through the
canonical Watershed setter from `error` to the user's current `warn` so the
operator can retry. No job was requeued automatically. These observations
drive the pending initiating-user snapshot amendment; they are not evidence
that the general route fix is implemented. The later operator decision also
requires job policy to remain nonpersistent project state.

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
