# Dashboard RQ 2.12 compatibility

Validated on local forest: disposable candidate checks at 2026-10-27 19:25 UTC,
followed by installed-service HTTP acceptance after the parent cutover.

## Source and integration boundary

The sibling `/workdir/rq-dashboard` was clean at
`860ce63b45c4f70db53f21f6fc04a052c6fed90f`. No AGENTS.md exists there.
The only sibling edits are `rq_dashboard/web.py` and two regressions in
`tests/test_basic.py`. No branch change, commit or push was performed.

The parent retains the exact patch at
[`docker/patches/rq-dashboard-rq212.patch`](../../../../docker/patches/rq-dashboard-rq212.patch).
Patch SHA-256: `3d835ed362841af8ae3198c04a7bd1ac23cfc12d421bfae59d888b4cc29998c9`.
Patched web.py SHA-256:
`6b72ffffa2b8fb504a21132eac5aef8fbaded49d4b06df738c0cd8a060134c34`.
The canonical Compose dashboard mounts the sibling source at `/rq-dashboard`;
a dependency-image rebuild alone does not install these source changes.

Before a separately authorized deployment, apply the patch to the inspected
sibling checkout (or carry equivalent reviewed changes in that repository):

    git -C /workdir/rq-dashboard apply --check /workdir/wepppy/docker/patches/rq-dashboard-rq212.patch
    git -C /workdir/rq-dashboard apply /workdir/wepppy/docker/patches/rq-dashboard-rq212.patch

For an already patched checkout, verify without applying twice:

    git -C /workdir/rq-dashboard apply --reverse --check /workdir/wepppy/docker/patches/rq-dashboard-rq212.patch

The reverse check and `git diff --check` pass locally. Production was not changed.
No mount, identity, authentication, permission or webhook behavior changed.

## Confirmed failures and repairs

RQ 2.0 `Job.dependency_ids` returns encoded Redis job keys, while released
2.12 returns exact string job IDs. The previous unconditional decode crashed
actual dependent-job JSON retrieval with HTTP 500. The repaired route removes
only the known `rq:job:` prefix from old bytes and preserves new string IDs
exactly. It does not split or normalize user identifiers.

A missing job in the started registry reached `StartedJobRegistry.remove`,
which raises NotImplementedError in 2.12. The repair constructs the exact job
identity through public `parse_job_id` and removes its executions using the
public `remove_executions` API. Both APIs exist in 2.0 and 2.12; no hidden
missing-API fallback or broad exception handler is added. Other registry cleanup
paths retain their existing behavior.

Additional bounded source inspection covered registry listing, worker current-job
reporting, worker state, JSON job status and `serialize_date`. Listing uses the
public get_job_ids API; JSON encodes string enums correctly; Arrow normalizes
both naive and aware timestamps to UTC. No additional confirmed regression was
found in this bounded inspection. It does not certify every dashboard mutation.

## Direct evidence

The probe uses canonical `wctl run --rm --no-deps` for the actual rebuilt image
`sha256:019fbdf6ba5c5027149115e30818a8542b6bf33c78be43bc8e77fe841beb2087`, Python
3.12 and installed RQ 2.12.0. It mounts the existing disposable Redis Unix
socket only for this test container, checks the DB0 disposable marker, uses DB5
and uniquely named queue/jobs, and starts the actual Flask app on a loopback HTTP
server. No shared application Redis is used. Test jobs and executions are
removed individually; no flush occurs. The normal dashboard source mount,
root identity and application route configuration are retained. The old-version
comparison uses an isolated RQ 2.0 import overlay in the same candidate image;
it is API compatibility evidence, not a claim that the old Python 3.8 image was
rebuilt or accepted.

- [Before dependency repair](dashboard-before.log): actual HTTP 500,
  `AttributeError: str object has no attribute decode`.
- [Before orphan repair](dashboard-orphan-before.log): actual HTTP 500,
  `StartedJobRegistry.remove` NotImplementedError; one orphan member remained.
- [RQ 2.12 after repair](dashboard-after.log): dependent-job HTTP 200 with exact
  parent ID and active dependency; orphan cleanup HTTP 200 and zero started
  members.
- [RQ 2.0 compatibility](dashboard-rq20-after.log): the same two actual HTTP
  assertions pass using the old bytes/composite-member API.
- [Retained regression tests](dashboard-tests.log): two sibling unittest cases
  pass against actual RQ 2.12/Redis. No route or Redis API is mocked; the runner
  selects the disposable socket instead of the suite's default localhost Redis.

Reproducible [HTTP probe](dashboard_probe.py) and
[unittest runner](dashboard_test_runner.py) are retained. Exact canonical commands
are in the logs. The wider sibling suite was not run because its default fixture
empties the default queue; only the two targeted cases were redirected to the
owned disposable database. Installed dashboard readback subsequently passed as recorded below.

## Installed forest acceptance

After parent cutover, the running `wepppy-rq-dashboard` image is
`sha256:019fbdf6ba5c5027149115e30818a8542b6bf33c78be43bc8e77fe841beb2087`
and the mounted sibling source is committed at
`91f62b9c1d71918c9ecd173e2eea5e383d624687` (clean working tree). The parent
performed that sibling commit and service activation after this lane's earlier
no-commit handoff. Running RQ is exactly 2.12.0.

The read-only [installed probe](dashboard_installed_probe.py) queried the actual
running Gunicorn HTTP endpoint for the upgraded acceptance project's hillslope
and watershed jobs. Both job JSON responses and their normal HTML detail pages
returned HTTP 200. The exact completed-job IDs, retained prerequisite IDs and
`active` prerequisite-record labels matched the model graph; status remained
`finished`, and timestamps parsed as aware UTC. `active` here is the existing
dashboard label for a retained prerequisite record, not a claim it is executing.
The exact results, runtime UID/GID/groups and patched-source hash are retained in
[dashboard-installed.json](dashboard-installed.json). This step read existing
package-owned jobs only; it submitted, canceled and deleted no work. It exercised
the installed service's loopback HTTP boundary, not external proxy authentication.
