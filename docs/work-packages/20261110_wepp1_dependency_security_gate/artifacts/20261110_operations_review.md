# M0 operations review - Dependency security gate

**Review time**: 2026-11-11 05:11 UTC  
**Reviewer**: independent wepp1 operator agent  
**Source**: `2041fb8e267de3a1572d9fb4f4a62e725b75cc91`, local dirty worktree  
**Environment**: local `forest`, `/workdir/wepppy`; no SSH or production action  
**Verdict**: design recommendation with prerequisites; not owner approval,
implementation acceptance, or production qualification.

## Confirmed control flow

`scripts/deploy-production.sh` derives build and recreation sets from rendered
Compose, refreshes them after pull, and serializes deployment with a local lock.
The future gate must inspect that resolved set and immutable local image IDs,
not assume the common image is always named `wepppy:latest` or selected through
the `weppcloud` service.

The insertion point is after the build/targeted-selection block (currently
lines 941-984), before Step 3 (line 998). Prefer placement before CAP's
`--secret-only` preparer at line 995 so a scan failure also avoids that unrelated
runtime preparation. This precedes all normal-path stop/down/recreate commands,
including worker/fork-archive warm shutdown and the later full-stack cutover.
The CAP recovery trap does not recreate CAP before `CAP_ACTIVATION_STARTED` is
set, which happens later at activation. Preserve this ordering and trap behavior.

| Deployment path | Gate implication |
| --- | --- |
| Full stack | Gate each selected common-image identity; preserve dependent fcgiwrap build ordering and separate CAP/WEPPcloudR validations. |
| Targeted web | Builds common image through `weppcloud`, recreates `weppcloud` and `rq-engine`; gate applies. |
| Targeted CAP | Builds/recreates only CAP; common-image gate must not block this unrelated repair. |
| Targeted batch overlay | `build_source_overlay.py` creates an image from an immutable baseline and retags the resolved batch image; assess the actual selected image rather than skipping on the flag alone. |
| Targeted batch rollback | Verifies a retained image ID; its policy treatment must be explicit and cannot become an implicit stale-evidence bypass. |
| Worker/fork-archive presets | Discover the common image through rendered Compose; these paths need no `weppcloud` service. Scope applicability must be explicit before enabling across presets. |

The existing `--skip-build` path rejects locally built services selected for
recreation. Do not weaken that check to accommodate scanning. The development
baseline is not equivalent to wepp1's build identity: the wepp1 overlay declares
APP_UID 1002 and APP_GID 130, while local tests currently use the dev image.

## Findings and required acceptance evidence

1. **High integration risk: retry wrappers can mask failures.** Both
   `run_wctl_with_retry` and `capture_wctl_with_retry` assign `exit_code=$?`
   after a failed `if` statement without an `else`. A harmless local Bash
   reproduction, `if false; then :; fi; rc=$?`, yielded zero. Call the new
   evidence/policy interface directly with explicit failure propagation. Record
   the existing wrapper defect separately or repair its confirmed consumers
   under the failure-class standard; do not route the gate through it unchanged.

2. **Medium design gap: image selection and rollback.** A mode-only condition
   could skip the batch-derived common image or gate unrelated CAP. Finalize
   selection by rendered image/build definitions and candidate identities, with
   explicit retained rollback treatment. Recheck the selected tag-to-ID mapping
   immediately before activation, and verify running containers consume that ID.
   The deployment lock prevents cooperating deploys, but does not prove an
   external tag writer cannot change it during a long scan.

3. **Medium qualification gap: protected evidence and resource capacity.**
   `DEPLOY_STATE_DIR` defaults to `/var/tmp`, not a private directory. Create a
   dedicated 0700 child and 0600 evidence files. Prove actual operator ownership,
   free space for image archives/database/reports, failed-run cleanup, and
   retention behavior before activation. Do not prune rollback images or unrelated
   evidence. The proposed 90/365-day retention and 24-hour freshness are pending
   owner decisions and storage validation, not operationally approved limits.

4. **Medium qualification gap: failure preserves service availability.** Extend
   `tests/scripts/test_deploy_production_execution.py` using its existing fake
   command ledger. Require nonzero exit with no stop/down/up command, no CAP
   activation, and no RQ suspension for missing tool/database, schema mismatch,
   image mismatch, stale evidence, and blocking findings. Exercise full, web,
   worker, batch-derived, rollback, and excluded CAP paths. Also retain the
   unmocked scanner/disposable-image trial; fake control flow alone cannot prove
   scanner filesystem, permissions, coverage, or database behavior.

## Recommendation and remaining authority

The proposed shared CI/deploy policy interface and archive-only scanner boundary
fit the existing host-local Compose workflow. Keep the current pull/build,
static assets, RQ fence, CAP rescue, health, and targeted scope contracts. A
failed scan should return before any cutover work and report the private receipt
location without dumping rendered environment or secrets.

Before M0 acceptance, retain green mandatory pre-change gates, completed scanner
qualification, independent correctness/security review, and owner ratification
of concrete thresholds, exceptions, retention, and rollback behavior. No policy
exception or deployment authorization is granted by this review. M3/M4 require
implementation-specific re-review and production-equivalent identity/mount
evidence; M5 remains separately authorized.

Only source inspection and the harmless Bash status reproduction were performed
for this review. No full test, scanner, deployed runtime, or production recovery
result is claimed here.

## M1/M3 follow-up - Manual retention and Compose boundary

**Review time**: 2026-11-11 07:32 UTC. M0 checkpoint
`d4b175436b69ad4ba1038f96f3289f14b15f0091` now records owner ratification.
The earlier pending-policy statements above describe the original review and
are superseded on authority by ADR-0140 and the ratified scope/policy artifact.
This follow-up inspected local files only; it did not connect to a runner or
production host, transfer evidence, or validate retention over time.

### Manual CI evidence transfer is not yet an established path

The current `stubtest.yml` source uses `forest_bootstrap: false`, read-only
repository permissions, checkout without persisted credentials, and the
`remote-ci` self-hosted runner label. Its unique Compose project isolates test
containers and removes volumes/images after the job. Neither that file nor
`docs/dev-notes/test-isolation.md` establishes that the runner host is disposable,
that its scratch directory is protected from later untrusted jobs, or that the
operator can retrieve files before runner cleanup. Container isolation alone
does not establish these properties.

The existing exhaustive `test-isolation.yml` workflow archives diagnostics in
`RUNNER_TEMP`, uploads them through `actions/upload-artifact`, retains them for
seven days, and tears down the test runtime. That public-repository artifact
route does not satisfy the ratified private raw-report policy. The shared
Forest bootstrap is also unsuitable: it can copy the host's `docker/.env` and
must not be inherited by the isolated dependency-security workflow.

The selected private store is present locally: `.local/` and
`.local/dependency-security/` have mode 0700 and owner `roger`; the evidence area
is gitignored. This establishes a destination, not a CI transport or 90/365-day
retention guarantee. Searches of existing workflow sources, operation docs, and
the private deployment repository found no documented protected manual
runner-to-store handoff contract.

**Explicit external prerequisite:** establish the operator's existing
authenticated access to the selected isolated runner and its collection window
before the job scratch/host is destroyed or reused. No concrete working remote
retrieval path is proven by the inspected files. If that access already exists,
the bounded manual handoff is an operator pull of the job's closed, hashed
evidence bundle into the approved private area, followed by source/destination
hash and image/lock identity readback before acceptance and before cleanup.
The runner receives no private-store credentials. A completed CI job or a
candidate-written transfer marker cannot substitute for that readback.

Do not invent an SSH endpoint, add a transfer service, mount the private store
into PR jobs, leave evidence in shared runner scratch indefinitely, or upload
raw reports to public Actions to work around this gap. A timed collection
window without confirmed operator access would still lose evidence on timeout
or cancellation. M3 must retain the actual manual transfer receipt, and missing
receipt must leave candidate acceptance blocked. This is a delivery prerequisite,
not a proposal to change production deployment topology.

### Compose activation and identity remain authoritative

The owner reaffirmed that production remains host-local Docker Compose through
the installed `wctl` preset and `scripts/deploy-production.sh`. The private
repository holds manually transferred evidence/approvals only; it is not a new
GitOps, registry, Kubernetes, image-promotion, or activation path for wepp1.

An image built in isolated CI cannot authorize a different host-local build
merely because the source revision and lock hashes match. Gate the exact
wepp1 candidate ID after its normal build using the approved policy and fresh
evidence. Keep manual archival and retained approval hashes outside
candidate-controlled inputs. Before activation, verify the resolved Compose
tag still names the scanned image; after activation, read the consuming
containers' image IDs. Preserve the reviewed pre-Step-3 ordering, targeted CAP
exclusion, batch-derived and rollback coverage, RQ fences, CAP recovery,
static assets, and health checks described above.

Current database freshness beyond the ratified 24-hour window and unresolved
native coverage remain blocking evidence gaps. This follow-up grants no
exception and no activation acceptance. M5 remains separately authorized.

## M1 follow-up - In-image Docker CLI applicability

**Review time**: 2026-11-11 08:20 UTC. Read-only source review; no daemon or
production command was executed. Subject is `/usr/local/bin/docker` in baseline
image `sha256:1819856096bf838cdf32fe52b035d13971e6aaa3aad4652b63759926fae23d74`,
reported as Docker 26.1.4 with Go 1.21.11. The retained module-level Grype
inventory has 73 standard-library advisory rows; this review grants **zero**
not-affected dispositions. The supplemental SBOM still lacks Docker symbols and
architecture, as recorded in the scanner evaluation.

### Confirmed consumer and input boundaries

The only application Python Docker subprocess site found is
`wepppy/rq/weppcloudr_backends.py`, `DockerExecBackend.render` (line 182).
Its command is an argument array, without a shell:

    docker exec --user <worker-euid>:<worker-egid> -i <container-name> \
      Rscript /srv/weppcloudr/render-compose-request.R

The worker uses PATH lookup (`shutil.which("docker")`), not an absolute binary
path. Candidate validation must read back the resolved executable and hash;
the Dockerfile's copy to `/usr/local/bin/docker` alone does not prove every
process resolves it. `docker/Dockerfile` installs only the CLI from the downloaded
archive; no daemon is started by this consumer.

| Input | Source and treatment |
| --- | --- |
| Container name | Application configuration or `WEPPCLOUDR_CONTAINER`, default `weppcloudr`; no request-body assignment found. Backend rejects empty names and path components. This is trusted operator configuration, not a general Docker-name validator. |
| Exec UID/GID | Effective worker process identity, never a request field; required for legacy owner-only files. |
| Command/script | Fixed `Rscript` and image-owned `/srv/weppcloudr/render-compose-request.R`; no caller-selected executable. |
| JSON stdin | Run ID/config, canonical active path, cache flag, fencing generation. Run selection and `no-cache` are user influenced; paths are confined to approved roots and the run root by the RQ task. These values are transported as data, not Docker flags. |
| Timeout | Deployment configuration/task option; subprocess captures stdout/stderr and maps nonzero/timeout into backend errors. |
| CLI environment | Inherited process environment; the subprocess supplies no clean `env`, `-H`, or `--context` override. |

The route `/runs/<runid>/<config>/report/deval_details` at
`wepppy/weppcloud/routes/weppcloudr.py:749` uses CAP, run authorization, and
lifecycle checks before queue admission. `_enqueue_deval_job` takes backend,
container and timeout from application configuration, while run data comes from
`RunContext`. `render_deval_details_rq` validates the request and paths before
calling the backend. These controls narrow caller influence; they do not prove
the absence of vulnerable Go parsing or transport code.

The current backend/task files match the clean baseline checkout byte-for-byte:
backend SHA-256 `bc315d790ca421f265c0cbcdf26fd3a8b8ac07d812697aa84f989337ca5c9b85`;
task SHA-256 `3ad6849d76e41867d4cef8610b52e1bfd9eadcf9b3eed84f790b7983ab1bf228`.
This maps the baseline source consumer; it is not a live process trace or an
exhaustive inspection of dynamically loaded/vendor executable behavior.

### Daemon access and unresolved reachability

`docker/docker-compose.prod.wepp1.yml:166,173` explicitly mounts
`/var/run/docker.sock` into both worker services; the base production and worker
presets also declare this socket. Thus socket access cannot be dismissed as
absent by policy. YAML does not prove live mount ownership, supplementary groups,
permissions, selected context, daemon version, or successful access by UID
1002/GID 130. No live values were read in this review.

No `DOCKER_HOST`, `DOCKER_CONTEXT`, or TLS/API override declaration was found in
the searched tracked runtime source/configuration. Environment files are still
inherited, and Docker also reads its client configuration. Official
[Docker CLI documentation](https://docs.docker.com/reference/cli/docker/)
describes context/host/TLS/configuration and proxy environment controls.
Consequently the Unix socket is the intended declared endpoint, not verified
proof that every live invocation avoids TCP/TLS/proxy handling. Even Unix-socket
execution exchanges Docker API responses and exec streams. A fixed argv or
trusted daemon does not justify bulk dismissal of HTTP, JSON, TLS, archive, or
other standard-library advisories without advisory-specific preconditions and
binary evidence. The missing symbols prevent symbol-absence claims here.

Host-side `wctl`, `scripts/deploy-production.sh`, source-overlay tooling and
Docker validation scripts operate the host Docker client. Their command inventory
does not establish in-image CLI use. In particular,
`docker/validate-weppcloudr-runtime-contract.sh` uses host `docker run` for its
protocol and owner-only-file probes: those checks do not exercise the candidate
CLI's daemon negotiation or `exec -i` transport.

### Bounded update and acceptance constraints

Evaluate a checksum/provenance-pinned CLI replacement within the existing common
Dockerfile download/copy boundary. Preserve Docker Compose, the host daemon and
Compose plugin, worker identities, socket/mount policy, renderer protocol and
existing output behavior. Removing the CLI/socket, switching execution backend,
or upgrading the host engine would require separately scoped operator authority.

Select the candidate only after comparing its supported API range with actual
target-daemon versions and reviewing the embedded Go/module versions against
all retained rows. Docker documents API negotiation as best-effort compatibility,
with version-dependent minimums; version equality is not required, but a newer
CLI alone is not proof of compatibility.
[Docker Engine API reference](https://docs.docker.com/reference/api/engine/).

Required nonproduction acceptance is an actual invocation of the candidate
in-image binary against a disposable/approved daemon and renderer: negotiated
API readback, JSON stdin/exec output, normal fresh report generation, nonzero
renderer exit, unavailable container/daemon, timeout behavior, and worker-created
0600 inputs in a 0700 directory under production-equivalent identity/mounts.
Retain report readback and existing focused/full gates. The current mocked
`tests/rq/test_weppcloudr_backends.py` identity test and host-driven runtime
validator support but cannot replace this CLI boundary evidence.

If no bounded CLI candidate clears compatibility and advisory evidence, retain
an explicit Docker CLI/embedded-Go follow-up with owner and unresolved rows.
Do not force a host-engine migration or mark the rows not affected merely to
complete this package. Fresh scanning and independent security disposition remain
required; no risk acceptance or deployment permission is granted here.

## M3 scoped review - Candidate test-image wiring

**Review time**: 2026-11-11 08:36 UTC. **Verdict**: no blocking finding in this
narrow wiring; locally validated test extension, not full M3/M4 acceptance.

`docker/Dockerfile.test` now accepts `WEPPCLOUD_TEST_BASE_IMAGE`, and
`docker/docker-compose.test.yml` passes the explicit override. Both retain the
previous `7619a9fc...` common-image digest as their default. Independent Compose
configuration readback confirmed the unchanged default and a supplied local-tag
override, with unchanged test mounts, internal network and privilege controls.
The accompanying Docker README correctly keeps production on host-local Compose
through the installed `wctl` preset and canonical deploy script. No production
Compose or deploy-script diff was present in this scoped review.

Readback of private `evidence/crypto-batch-20261111/` receipts establishes:

- `test-image-build-receipt.json`: exit zero, 90.73 seconds, explicit candidate
  tag `wepppy-security-crypto-batch:20261111`.
- `test-image-ancestry.json`: all 22 common-image layers are the initial layers
  of the 27-layer test extension; candidate tag remained stable. Common image
  `sha256:f0f3fbb48f4afe636eb8bfcc491d7fa28514543cc1fe4bc628bce8fda373da48`
  extends to test image
  `sha256:c52f34545097d7a46c88b381eeaefcd1852192474646b320cd6c94036f643d38`.
- `extension-runtime-identity.json`: the running test container uses that exact
  test image and UID/GID `1000:993`.
- `test-extension-crypto-auth.json`: parsed JSON exactly equals the common
  candidate's result, including all 308 Python package versions, native
  readback, and real-library crypto/auth cases. Its separate execution receipt
  uses the exact extension image, UID/GID `1002:130`, read-only filesystem,
  dropped capabilities and no network; exit zero.
- Independent comparison of `common-dpkg.txt` and `extension-dpkg.txt` confirms
  the retained delta: 90 browser-support packages added, zero existing common
  packages changed or removed. This closes the concern that browser installation
  might silently upgrade the common image's OS dependencies in this build.
- `extension-focused.log`: 51 passed, 13 warnings, pytest duration 9.17 seconds;
  wrapper receipt exits zero with 17.9 seconds elapsed.

Identity receipts are bound by SHA-256:
ancestry `b9086da9506f42647df0c5e32ef33c485eaf06d40393d0d6827386b8988ab1ca`;
runtime `2438af4d2b3d973b80794d14fcccf62dcd3ba113f98c9d6faa43a1f4de607aba`;
crypto readback `2f00d61ae04c3566f2aeac67c00afc0ecab79999597b64f4b72cb9078bc90026`;
dpkg delta `fa37c0d2a878dec9ba8cb521edd77afe44b3e85257d241617917976426162cd4`.

The npm source/generated workflow diff adds lint and its source-file trigger;
it changes no runner, credential or deployment boundary. The parent retains a
passing workflow-generation check. This review does not establish private CI
evidence transfer, production gate wiring, full regression acceptance or
advisory clearance. The isolated test runtime identity differs from wepp1;
the separate UID/GID probe does not substitute for a production-equivalent
end-to-end workflow with real mounts and orchestration. New candidate builds
must repeat ancestry, installed-version and runtime-ID readback.
