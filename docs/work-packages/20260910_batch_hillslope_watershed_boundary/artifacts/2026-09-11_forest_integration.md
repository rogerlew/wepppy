# Forest deployment and integration evidence

## Source and deployment

Reviewed candidate: `0a1e2e1efdd816243883254cd99412b022983cd2`, pushed to
`origin/master` before deployment. Host: Forest; canonical installed development
Compose workflow: `wctl up -d --no-deps --force-recreate rq-worker-batch`.
Only the existing batch-worker container was recreated. No queue/service,
identity, native binary, mount or resource configuration changed.

Before deployment (05:59:35 UTC): four batch-only workers idle, queue count zero.
Old container: `ec38eeff58a4a674ed7602d77c08961b9248b87ab5b67b6f77e9c61bee746bb2`.
New container: `492189b6c9bb09324b77c623fd0f46fbfdbb45104eaeec1375d1bc616619425b`.
Existing local image: `sha256:6ac7e71030467a10e5d73dc18893cbd85c9202976d4b1b561a19dbb0d7ef2b75`.
Source bind: `/home/workdir/wepppy` to `/workdir/wepppy`; service UID/GID
`1000:993`. This is source-mounted Forest Compose deployment, not GHCR rollout.

## Bounded fixture and observations

Prepared with `wctl exec weppcloud /opt/venv/bin/python
.../artifacts/forest_boundary_fixture.py codex-boundary-20260911-0540`.
Workspace: `/wc1/batch/codex-boundary-20260911-0540`; leaf `leaf`.
The fixture uses real BatchRunner/NoDb controllers and synthetic polygon data.
Scientific directives are disabled; only explicit full-rerun reset is enabled.
The existing RQ `Queue('batch').enqueue_call(run_batch_rq, args=(batch_name,))`
submitted roots with canonical generated UUIDs and batch-name metadata.

[Sanitized observations](2026-09-11_forest_observations.json) retain both actual
RQ graphs, statuses, dependencies, timestamps, terminal metadata, receipt,
completion events, browser hashes, and final worker inventory. Live graph
inspection used `wepppy.rq.job_info.get_wepppy_rq_job_info` as well as real Job
and queued/started/deferred registry reads.

| Attempt | Root | Hillslopes | Watershed | Finalizer |
| --- | --- | --- | --- | --- |
| Injected failure | `b867c966-4457-44b8-9f50-0182138d6128` | `4cf2486e-ecd7-4416-b55d-8ca90bfb3730` failed | `2a964f83-2036-4a2c-8b3c-c4fec30444de` finished, result false | `1a9fb80e-0b67-4909-9c9a-ed9f1c9439dc` finished |
| Full rerun | `128bcb08-d721-4b5d-9d30-ea9556e0ab77` | `748aea79-973c-4ea1-bac7-0b72bc5db164` finished | `8f913e61-cdcf-4745-8b7e-67d9bdf6e2b1` finished, result true | `6250c7bf-5eb3-4676-84b7-9b0ea5795ca2` finished |

Failure injection added only `_base/boundary_failure.nodb` with intentionally
invalid JSON. Stage one failed while decoding the copied fixture input. The
second stage rejected the unsuccessful prerequisite, wrote failed metadata and
did not enter watershed work. The failure-tolerant finalizer released normally.
The initial temporary observer assumed enum-valued RQ status; live RQ returned
a string. Correcting that observer allowed inspection of the retained jobs;
no production change or retry was needed for this tooling error. Failure pub/sub
capture was interrupted; failure claims use retained RQ and file evidence.

The injected base file was removed after asserting its exact diagnostic content.
Failure metadata was downloaded and retained before the explicit full rerun
reset its leaf. Both attempts have no remaining queued/started/deferred IDs.
Normal partial retry is independently covered by isolated RQ tests; the fixture
preserves existing zero-enabled-task timestamp classification behavior.

For success, hillslopes ran at 06:01:03.922895–06:01:08.684889 UTC, PID **382**;
watershed ran at 06:01:08.721616–06:01:09.678337 UTC, PID **391**, both on host
`492189b6c9bb` and queue `batch`. RQ dependency IDs exactly match the preceding
stage. Terminal metadata names only the watershed job and reports whole-leaf
elapsed time 5.746675 seconds. The live subscription captured exactly **one**
leaf-completion trigger, followed by batch completion. Focused tests separately
assert the single terminal metadata-writer ownership.

## Browsing, retention and cleanup

A short-lived service JWT was minted through `wctl issue-auth-token`, scoped
only to this fixture base and leaf. Existing browse service directory listings
and `?download` responses returned HTTP **200**, named the files, and matched
the local bytes. Failure `run_metadata.json` SHA-256:
`5ced795cb25c14f057e2b584e86c28934681e2d3a607e35f9e595550654ae42f`.
Successful handoff SHA-256:
`5ac77cbc0ecb736d839b87171bf73c2b37511bdcd75ccf7177277fd963d7ca09`.
Receipt owner/group `1000:993`, mode **0600**, was readable through the actual
browse/download service. No public flag or authorization rule was changed.
Canonical archive/restore preservation is covered by the focused test gate.

At 06:01:39 UTC, the four replacement batch-only workers were idle, queue count
zero. No fixture jobs remain queued/started/deferred; terminal records and the
fixture tree remain inspectable. No unrelated job was deleted. The scoped JWT
was revoked through `wctl revoke-auth-token`; the disposable test Redis was
stopped with `shutdown nosave`. Temporary local probes and credentials were
removed after evidence capture. The worker retains its normal Compose setup.

This proves the deployed RQ/process/shared-tree boundary. It does not establish
scientific output parity, new-cgroup behavior, or 12 GiB memory headroom; those
remain the subsequent openwepp.org integration acceptance.
