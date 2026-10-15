# M7 validation follow-up security review

## Findings and current verdict

**Security gate: pass for source integration.** One medium finding in the new
diagnostics export was corrected and directly verified. No unresolved medium
or high finding remains in the reviewed changes. Storage and CI controls pass
source and live boundary inspection. This approval does not claim the full
Forest suite, full isolation run, or hosted workflow has passed; M7 functional
closeout remains subject to those results.

| ID | Severity | Surface | Disposition |
| --- | --- | --- | --- |
| SEC-V01 | Residual | Persistent public-repository runner | Existing `remote-ci` jobs already execute pull-request code on runner-02. A test container does not isolate malicious workflow edits from the runner host. This change preserves that existing trust model; it does not establish a safe sandbox for hostile PRs. |
| SEC-V02 | Accepted operational tradeoff | PostgreSQL storage | The operator explicitly approved the prepared SSD RAID0 move after being told its device-failure resilience differs from RAID6. Durability settings, original data and RAID6 backup retention remain required. |
| SEC-V03 | Medium | Diagnostics export | Resolved. Direct `upload-artifact` traversal followed test-created symlinks and could publish a host file that the test container could not read. The workflow now archives the `.pytest_cache` entry without dereferencing links and uploads only the regular archive in `RUNNER_TEMP`. Nested-link and cache-root-link probes preserve valid logs and archive no external file contents. |

## Scope and triage

- Reviewer: independent `validation_security` agent, 2026-10-15 UTC.
- Context: working changes against WEPPpy `88cc1fafa` on the existing branch.
- Impact: **high**, because CI execution and deployment storage wiring change.
- Source: `docker/docker-compose.dev.yml`, `docker/docker-compose.test.yml`,
  `.github/forest_workflows/stubtest.yml`, its generated workflow,
  `scripts/build_forest_workflows.py`, and `wepppy/nodb/core/wepp.pyi`.
- Operational evidence and limits: [validation follow-up](20261015_validation_followup.md).
  Unrelated infrastructure documentation and generated docs index are excluded.
- Independent [correctness review](20261015_validation_correctness_review.md):
  pass with validation conditions; initial LFS/provenance findings resolved.
  Reviewed its direct runner results and the final workflow/generator changes
  after that disposition. No separate QA artifact is claimed.
- Trust assumptions: repository maintainers control deployment configuration;
  runner-02 retains its existing general CI admission policy; runner-01 remains
  exclusively eligible for the dedicated image-builder workload. The standard
  PostgreSQL and Redis images retain the repository's existing version choices.

## Surface checks

**CI, credentials and subprocess execution.** The canonical workflow spec opts
out of Forest bootstrap, so it neither copies the host's `docker/.env` and
secrets nor performs Forest Redis cleanup. Checkout does not persist credentials;
the job token is restricted to `contents: read`. The executor reports an actual
anonymous pull of the digest-pinned common image on runner-02; no registry token
is needed. Builder labels and caches are unchanged. Unique run/attempt/job
Compose project names bound creation and `down --volumes --remove-orphans`
cleanup. Commands contain no PR title, branch-name or other untrusted text
interpolation. Existing host-side `wctl` installation remains part of the
runner trust boundary.

**Diagnostics export.** The long job first requires a successful baseline
suite, then retains isolation logs. Host-side `tar -cf` archives the
`.pytest_cache` entry from the checkout root without `-h`; it never changes
directory through a potentially hostile cache symlink. Only the resulting
`RUNNER_TEMP/test-isolation.tar` is uploaded, with seven-day retention. The
uploader does not traverse the test-controlled directory. Logs originate from
the test-only runtime; production secrets and host environment are not injected.

**Filesystem and network.** Only the checkout is mounted in the test process;
there is no host Docker socket, credential mount, production dataset mount,
published port or host network. The test process runs as the configured
non-root user with all capabilities dropped and no new privileges. Its Compose
network is internal. PostgreSQL and Redis are disposable per-job services using
test-only configuration. These controls constrain ordinary test execution;
they do not protect the host from a workflow that deliberately replaces them.

**Storage integrity and recovery.** The dev default remains the original bind
mount. Forest explicitly selects the separate `forest-postgres-ssd` volume,
avoiding the preexisting `postgres-data` volume. The executor reports a stopped
copy with zero byte/ownership/mode differences and matching user-table counts.
The reviewer independently read the actual PostgreSQL mount, durability
settings and default-only tablespaces after migration. The original data is
retained. After new writes, rollback must copy the current stopped database
back; the old retained directory is not a current recovery source.

**Other surfaces.** No web authentication, session, CSRF, authorization,
catalog transport, queue wiring or NoDb locking contract changes. The two stub
annotation corrections do not change runtime behavior. Tests retain the
catalog's existing 50 ms latency limit and synchronous database writes. This
follow-up creates no new run artifact or archive member; ordinary application
data remains under its existing authorization and observability contracts.

## Direct evidence retained by reviewer

- `git diff --check`: passed.
- `.venv/bin/python scripts/build_forest_workflows.py --check`: passed; existing
  README profile-table marker absence was reported without workflow drift.
  System `python3` lacks PyYAML; the existing virtualenv supplied the dependency.
- Docker inspect: actual data mount is
  `/var/lib/docker/volumes/docker_forest-postgres-ssd/_data`.
- Live SQL: `fsync=on`, `synchronous_commit=on`,
  `wal_sync_method=fdatasync`; only `pg_default` and `pg_global` tablespaces.
- Logical backup: 2,388,063-byte `before.sql`, mode `0600`, within owner-only
  mode `0700` directory `/home/roger/.local/state/wepppy/m7-postgres-20261015`;
  PostgreSQL cluster-dump completion marker present. Database contents and
  credentials were neither printed nor copied into the repository.
- Direct runner-02 inspection of `m7-validation-weppcloud-1`: UID:GID
  `1000:993`, `Privileged=false`, `CapDrop=[ALL]`,
  `SecurityOpt=[no-new-privileges:true]`, only the validation checkout mounted,
  and no port bindings. Compose network reports `Internal=true`.
- Inside that container, `/var/run/docker.sock` and `/run/secrets` are absent.
  A TCP connection to an external address returned `ENETUNREACH` (101), while
  the intended internal Redis service returned `+PONG`. These direct negative
  and valid-state probes establish the configured network boundary without
  claiming resistance to a hostile workflow that changes the configuration.
- Reviewed direct runner logs: all eight stubtest modules passed,
  test-stub completeness passed, all 648 tracked LFS files verified, and 77
  PostgreSQL/catalog/NoDb tests passed in 25.74 seconds. These are focused
  executor results independently read from the retained logs, not a hosted-CI
  or broad-suite pass.
- Confirmed the original export flaw in runner-02's installed
  `actions/upload-artifact/v4/dist/upload/index.js`: the archive writer
  resolves symlinks to their targets at line 3784. The corrected command was
  exercised with a nested diagnostic symlink and a symlink replacing the
  `.pytest_cache` root. Both archives retained links without external bytes;
  an ordinary diagnostic file retained its exact contents. Only synthetic,
  nonsecret probe files were used, and the temporary probes were removed.

The full Forest suite, full runner isolation and hosted workflow outcomes
remain pending at this sign-off. Do not equate an isolation-checker exit code
with a passing broad suite or randomized coverage when its optional plugin is
absent. Functional acceptance remains separate from this security approval.

## Residual risk and sign-off

The preexisting persistent runner can retain effects of earlier PR jobs and
has host-side Docker access and tailnet reachability. This review does not
claim to remediate that repository-wide operating model. The image builder
remains excluded, and this change introduces no package-write token or shared
builder cache. Routine image/Action updates remain operator maintenance.

Storage's approved RAID0 tradeoff is bounded by preserved backups and rollback
data; `fsync=on` does not replace backup or device redundancy. No new security
risk acceptance beyond the explicit storage approval is inferred.

Final security sign-off: independent `validation_security`, 2026-10-15 UTC,
**approved for source integration** after final exact-diff review and closure
of SEC-V03. No outstanding medium/high finding or new risk waiver is required.
