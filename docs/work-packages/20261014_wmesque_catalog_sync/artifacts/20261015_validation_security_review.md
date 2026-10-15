# M7 validation follow-up security review

## Findings and current verdict

**Security gate: pass for source integration.** One medium finding in the new
diagnostics export was corrected and directly verified. No unresolved medium
or high finding remains in the reviewed changes. Storage and CI controls pass
source and live boundary inspection. Forest's recorded baseline suite passed;
the latest complete hosted baseline/isolation remains open. This source
approval does not close M7's remaining functional validation gates.

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
  Supplemental hosted-runtime review also covers `tests/integration/conftest.py`
  and the test Compose lock-directory override above `5325742bf`.
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

At the initial source sign-off, the full Forest suite, full runner isolation
and hosted workflow outcomes were pending. Do not equate an isolation-checker exit code
with a passing broad suite or randomized coverage when its optional plugin is
absent. Functional acceptance remains separate from this security approval.

## Hosted runtime follow-up

The hosted stubtest job in run `38763492543` passed all eight modules and
completeness after explicit LFS materialization. Its baseline job subsequently
exposed test-runtime assumptions about `/wc1` and deployment account data.
Reviewed the bounded corrections above `5325742bf`; no new security finding.

- The test Compose service sets the existing
  `WEPPCLOUD_RQ_LIFECYCLE_LOCK_DIR=/tmp/rq-lifecycle-locks` configuration. Locks
  stay in the disposable container, with unchanged locking code. No production
  setting, host mount, privilege or permission is added.
- The function-scoped integration fixture creates a real SQLite database under
  `tmp_path`, using the canonical account/feature schema. It seeds synthetic
  account 42 with the ordinary `User` role and replaces only the account-engine
  provider; the shared account-principal lookup and JWT/authorization code still
  execute. No administrator role or feature entitlement is granted.
- Legacy MCP identity lookup otherwise enters Flask's deployment database.
  Its fixture double maps only synthetic subject `"42"` to account 42 and
  returns `None` for other subjects. This is a test input boundary, not an
  authorization result replacement. It does not establish coverage of the real
  Flask `fs_uniquifier` query. The engine is disposed and pytest monkeypatch
  restores both providers after each test.
- Independently read `/tmp/m7-runner-auth-tests.log`: all ten integration
  tests pass in 1.13 seconds, including valid transport flows and existing
  revocation, retired-secret, cross-origin and token-class denials. No assertion
  or production authentication implementation changed. Broad hosted baseline
  and isolation acceptance remain pending.

## Clean-runner image and RQ fixture follow-up

Reviewed the working delta above `b1b522f2e` on 2026-10-15 UTC: new
`docker/Dockerfile.test`, test Compose build wiring, canonical/generated
workflow, `tests/rq/conftest.py` and the seven edited RQ test modules. **Approved
for source integration; no new security finding.** The actual clean-runner
failures justify these bounded prerequisites without broadening production
mounts, privileges, dependencies or execution paths.

- Dependency precedent is `docker/Dockerfile.dev:59`: Node 20 already supplies
  controller-test execution. The CI extension pins the official
  `node:20-bookworm-slim` image and accepted common runtime by SHA-256. The
  initial Node-only extension was subsequently expanded to install the existing
  locked browser-test dependencies, reviewed below. No credentials, image
  publication, or image-builder cache sharing is introduced.
- The existing Python controller builder runs inside the same container and
  generates the ordinary assets within the checkout. Cleanup adds `--rmi local`
  to the existing unique-project Compose teardown; no daemon-wide prune or
  production image deletion is introduced.
- Independently inspected the rebuilt runner container: UID:GID `1000:993`,
  no privileged mode, all capabilities dropped, no new privileges, checkout-only
  mount, no published ports, and an internal network. Node reports `v20.20.2`.
- Cache recorders are explicitly requested, function-scoped fixtures rather
  than global/autouse bypasses. Bootstrap tests assert the exact scoped request;
  cache-order tests retain their own boundaries. Temporary work roots keep
  directory creation/removal away from `/wc1`. Production cache invalidation,
  NoDir locks, fork cleanup, and queue wiring are unchanged. These orchestration
  fixtures do not claim to test the real filesystem cache implementation.
- Workflow regeneration and whitespace checks pass. Independently read the
  earlier Forest regression receipt: 10,872 passed, 126 skipped in 2,836.09
  seconds. That run predates these latest fixture/image changes. Subsequent
  direct runner results and their acceptance limits are recorded below.

### Browser and disposable account prerequisites

The remaining-group probe subsequently recorded 4,683 passes, two failures and
eight errors: missing browser/runtime inputs, a missing test-run context, and
an empty account schema. Reviewed the resulting source corrections; no new
medium/high security finding in the changed execution boundaries.

- The root build context supplies only the existing static-src package manifest
  and lockfile through explicit `COPY` operands. No checkout, `.env`, credential
  file or host path is copied wholesale. Node/npm come from the pinned official
  image; `npm ci` uses the unchanged lockfile. Playwright installs its matching
  Chromium and OS dependencies during image construction. `USER root` is limited
  to construction; final `USER roger` and Compose's explicit UID, capability
  drop, no-new-privileges, internal network and mount boundaries remain intact.
- Modules and browsers live under `/opt/wepppy-ci`, outside the source mount,
  with read/execute permissions rather than world-write permissions. The browser
  test now honors the explicit `PLAYWRIGHT_BROWSERS_PATH`; its default remains
  the existing checkout location. This does not alter production configuration.
- `tests/bootstrap_ci_database.py` replaces the initial `db.create_all()` step,
  which did not preserve the preferences migration's named constraints. It
  checks for existing tables in the default schema before any creation. One
  transaction creates current model tables except preferences, then invokes
  the canonical preferences migration through Alembic `Operations`. It never
  drops existing objects, stamps migration history, or changes account data.
  This initializes the disposable internal PostgreSQL service; it is not a
  deployment bootstrap or proof of the complete production migration chain.
- The CSRF unit test supplies its assumed valid run-context boundary but keeps
  real `CSRFProtect`, the missing-token request and its 400 assertion. It does
  not disable CSRF or alter the production route, decorators, or authorization.
- The build log reports 43 npm advisories for the existing lockfile (38 high,
  four moderate, one low). Package versions are unchanged. This inherited
  dependency telemetry is not a claim that advisories were remediated or a
  complete exploitability assessment. Test code already executes within the
  same isolated runtime; no production endpoint or new host authority exposes
  these packages. Dependency maintenance remains a separate existing concern.

Direct final prerequisite evidence:

- Independently read `/tmp/m7-final-remaining-runner.log`: the remaining runner
  group passed 4,693 tests and 12 subtests, with 83 skips and 1,581 warnings in
  335.95 seconds. All eight stubtest modules and stub completeness also passed.
  This is bounded direct runtime acceptance, not complete hosted baseline or
  isolation acceptance.
- `/tmp/m7-ci-final-focused.log`: all 19 preferences, catalog-reader/browser,
  and catalog-route tests passed with nine warnings in 22.89 seconds on a newly
  recreated disposable database. The real browser consumer and named database
  constraints were exercised without weakening their assertions.
- Independently inspected browser image `aa784e4fc3d8...` running as UID:GID
  `1000:993`: privileged mode remains false, all capabilities are dropped,
  no-new-privileges is set, only the checkout is mounted, no ports are published,
  and the network is internal. `/opt/wepppy-ci` and its browser directory are
  root-owned mode `0755`; the test process cannot rewrite those installed inputs.
- Independently ran the bootstrap again against that populated CI database:
  exit 1 with `RuntimeError: CI bootstrap requires an empty database`. Full
  logical schema/data dump SHA-256 was identical before and after:
  `b263b3f497dc4d3184d933fceda949d7f8553009771fa6caabec09c471e7c89d`.
  Only PostgreSQL's random restrict/unrestrict tokens were normalized; no data
  contents were printed or retained in repository artifacts. Rejection occurs
  before mutation. The guard's exact scope is default-schema tables, not every
  possible schema/object in an arbitrary database.

The final workflow delta adds `exec -T` to asset construction and database
bootstrap, preserving noninteractive execution without changing permissions or
coverage. Source integration remains approved; direct remaining-group acceptance
passes. Complete hosted baseline and isolation acceptance remain pending.

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
of SEC-V03, including the bounded hosted-runtime, image and RQ fixture follow-ups
above. No outstanding medium/high finding or new risk waiver is required.
