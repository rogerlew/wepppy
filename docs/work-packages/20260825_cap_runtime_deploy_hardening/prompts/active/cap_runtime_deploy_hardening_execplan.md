# Make production Compose deployment and CAP runtime contracts durable

This ExecPlan is a living document. The sections `Progress`, `Surprises &
Discoveries`, `Decision Log`, and `Outcomes & Retrospective` must be maintained
as work proceeds. Maintain this document according to
`docs/prompt_templates/codex_exec_plans.md` and update the package tracker at
every handoff.

## Purpose / Big Picture

After this work, a full `wepp.cloud` Docker Compose deployment cannot build one
service set, recreate a larger set from stale images, and report success from a
single web health check. CAP will retain its
least-privilege non-root identity, supported existing token data will migrate
without loss; workers and WEPPcloudR will prove protocol compatibility; and
operators will verify every service the exact deployment command recreates.
Users will not need to log out, clear cookies, or clear site data.

## Progress

- [x] (2026-08-25 15:48Z) Captured incident evidence and restored wepp1 CAP.
- [x] (2026-08-25 15:48Z) Scaffolded package, tracker, and this ExecPlan.
- [x] (2026-08-25 16:10Z) Completed independent correctness, QA, operations,
  and security reviews; no Critical findings were reported.
- [x] (2026-08-25 16:12Z) Dispositioned every High finding and ratified the
  runtime permission, migration, readiness, CAP-only activation, and rollback
  design in `artifacts/2026-08-25_review_disposition.md`.
- [x] (2026-08-25 17:20Z) Reproduced unreadable-secret and legacy-volume
  failures at the production container boundary before accepting migration.
- [x] (2026-08-25 17:20Z) Added direct production-image CAP tests covering
  fresh, populated root-owned legacy, and malformed ledgers; the legacy state
  fails before migration and passes challenge/redeem/siteverify afterward.
- [x] (2026-08-25 17:20Z) Added executable full/targeted plan tests, derived
  build/recreate/acceptance sets, candidate image identity checks, and a
  WEPPcloudR entrypoint/syntax compatibility gate.
- [x] (2026-08-25 17:20Z) Implemented fixed-scope CAP migration, persistence
  readiness, atomic secret installation, CAP-only mode, functional canary, and
  rescue-image recovery.
- [x] (2026-08-25 17:20Z) Updated canonical deployment and secret/runtime
  documentation.
- [x] (2026-08-25 17:47Z) Passed 6,706-test broad validation, 23 focused
  deployment/helper tests, production CAP image matrix, WEPPcloudR protocol
  receipt, and deliberately stale renderer rejection.
- [x] (2026-08-25 18:05Z) Received PASS from renewed correctness, operations,
  QA, and security code gates: Critical 0, High 0.
- [x] (2026-08-25 21:38Z) Installed/verified the Forest1 `acl` prerequisite and
  exact UID `10001` secret ACL.
- [x] (2026-08-25 21:38Z) Completed two exact no-flag Forest1 full deployments,
  targeted CAP/web isolation, disposable hostile CAP and stale-renderer gates,
  automatic CAP rescue evidence, and a real RQ-driven DEVAL render.
- [x] (2026-08-25 22:00Z) Confirmed final-revision Safari/Chrome CAPTCHA,
  OAuth login, and multi-tab logout; local login is disabled/N/A on Forest1.
- [x] (2026-08-25 22:00Z) Flipped Forest1 to the owned-cookie writer through a
  canonical targeted-web deploy and proved a fresh CAP session receives only
  `__Host-weppcloud_session`.
- [ ] Roll out to wepp1, verify login UX, and start the observation window.

## Surprises & Discoveries

- Observation: a full production deployment recreated CAP because the full
  topology build set includes `cap`, even though the initiating session change
  did not concern CAPTCHA.
  Evidence: `configure_deploy_topology` in `scripts/deploy-production.sh` adds
  CAP to `BUILD_SERVICES`, and non-targeted startup runs the full Compose stack.
- Observation: deploy success only proved `/weppcloud/health`; it did not prove
  CAP health or even that CAP was stable.
  Evidence: wepp1 returned CAP 502 while the deploy completed and CAP was in
  `Restarting (1)` state.
- Observation: the non-root image's build-time `chown` does not affect a named
  volume mounted over `/var/lib/cap` at runtime.
  Evidence: the production named volume directory and `tokensList.json` were
  UID/GID `0:0` while the image ran as `10001:10001`.
- Observation: the current `/cap/health` is only liveness and returns 200 even
  when upstream CAP cannot read or write the populated ledger.
  Evidence: the independent QA reviewer reproduced this with a disposable
  root-owned named volume; `docker/validate-aux-image-contract.sh` still passed.
- Observation: secret ACLs are attached to an inode, so atomic secret rotation
  can remove access even after the current host is repaired.
  Evidence: correctness and operations reviews identified replacement as an
  untested supported state.
- Observation: full mode built `weppcloud`, `rq-worker`, CAP, status, and
  preflight, then recreated the complete default Compose stack.
  Evidence: wepp1 activated an April WEPPcloudR image while the new worker
  expected an entrypoint added by revision `80e621164`.
- Observation: forest1 exercised targeted web mode, while production used
  plain full mode.
  Evidence: the session rollout record did not contain an exact-command full
  deployment or DEVAL integrated canary before production.
- Observation: the development CAP service builds `services/cap/Dockerfile.dev`,
  while Forest1 and production build `services/cap/Dockerfile`.
  Evidence: `wctl build cap` locally produced `wepppy-cap-dev`; the unmocked
  production boundary therefore uses an explicit production-Dockerfile image.
- Observation: Compose configuration includes one-shot `*-build` helpers and
  the wepp1 override defines a scaled-zero fork/archive worker.
  Evidence: local `compose ps --all` reports `status-build` and
  `preflight-build` exited successfully; acceptance excludes these deliberate
  non-long-running services rather than false-failing them.
- Observation: the real Forest `wctl` transport removed single quotes embedded
  in a Python `-c` payload even though mocked argv tests preserved them.
  Evidence: Redis received `redis.call(get, ...)` and rejected the Lua before
  acquisition; Lua long-bracket string literals survived the exact transport.
- Observation: targeted web's no-cache image build can spend several minutes
  in an unbounded shallow clone of `weppcloud-wbt`.
  Evidence: the Forest build remained network-bound in `git clone` for about
  four minutes before completing; no cutover occurred during that interval.

## Decision Log

- Decision: retain CAP's `10001:10001` identity and migrate runtime resources
  instead of reverting to root.
  Rationale: least privilege is the intended security contract; the defect is
  the omitted runtime migration and acceptance coverage.
  Date/Author: 2026-08-25 / Codex with operator confirmation.
- Decision: derive validation from services actually recreated by the selected
  deploy mode.
  Rationale: full deploy must cover CAP, while targeted web mode intentionally
  leaves CAP and workers running.
  Date/Author: 2026-08-25 / Codex.
- Decision: preserve populated legacy token ledgers and existing browser/auth
  state.
  Rationale: operational remediation must not transfer recovery cost to users.
  Date/Author: 2026-08-25 / operator requirement.
- Decision: add guarded `--targeted-cap` and use it for this rollout.
  Rationale: CAP repair must not stop/recreate WEPPcloud, rq-engine, Caddy,
  Redis, or workers. Full deployment behavior remains separately tested.
  Date/Author: 2026-08-25 / review disposition.
- Decision: promise no browser/session remediation and a measured bounded
  login-only gap, not zero interruption.
  Rationale: the current Compose topology has one CAP instance; zero-gap
  activation would require an out-of-scope high-availability design.
  Date/Author: 2026-08-25 / operations review disposition.
- Decision: use pre-listen persistence validation and a fixed-scope privileged
  migration helper.
  Rationale: upstream CAP can swallow ledger failures and a free-form root
  helper would create an unacceptable host privilege boundary.
  Date/Author: 2026-08-25 / security review disposition.
- Decision: simplify full mode so every locally buildable service it recreates
  is built from the candidate context.
  Rationale: a hand-maintained partial list cannot safely accompany full
  `down`/`up`; build, recreate, and validation sets must be explicit and
  executable-testable.
  Date/Author: 2026-08-25 / incident review with operator.
- Decision: forest1 must execute the exact no-flag command intended for
  production and complete integrated auth plus DEVAL workflows.
  Rationale: targeted-mode rehearsal cannot establish full-mode safety.
  Date/Author: 2026-08-25 / operator requirement.
- Decision: derive one build target per distinct local image, then validate
  every recreated service using that image against the candidate image ID.
  Rationale: many WEPPcloud services intentionally share one image tag; building
  every service would race writes to that tag without improving coverage.
  Date/Author: 2026-08-25 / Codex.

## Outcomes & Retrospective

The implementation and Forest1 matrix are complete at `e11985f02` (with
evidence documentation at `8ddfc4692`).
The common architectural failure was closed by deriving build, recreation, and
acceptance sets from Compose; CAP now has explicit runtime ownership,
persistence, rotation, functional, and rescue contracts; and WEPPcloudR has an
executable worker/renderer protocol gate. Two exact full deployments, targeted
isolation checks, an RQ-driven DEVAL publication, and the operator-controlled
browser UX gate passed. Production now requires explicit activation
authorization, not another Forest repair or browser-data migration step.
Detailed receipts are in
`artifacts/2026-08-25_forest1_integrated_rehearsal.md`.

The durable deployment repair and Forest1 release gate are complete. The
package remains active through production activation and the observation
window.

## Context and Orientation

CAP is the proof-of-work CAPTCHA service used by WEPPcloud local login. Its
image is built by `services/cap/Dockerfile` and runs as numeric UID/GID
`10001:10001`. Production Compose in `docker/docker-compose.prod.yml` mounts a
host-backed secret at `/run/secrets/cap_secret` and a named volume at
`/var/lib/cap`. A bind-mounted secret retains host permissions; a named volume
mounted over an image directory hides the image-layer ownership. Therefore,
the Dockerfile's build-time ownership is insufficient for either resource.

`scripts/deploy-production.sh` is the canonical deployment entry point for
wepp1/wepp2/wepp3. It discovers the installed Compose topology. Full wepp1 mode
builds auxiliary services including CAP and starts the full stack. Targeted web
mode rebuilds and recreates only WEPPcloud and rq-engine. The implementation
must preserve this distinction and must not introduce registry or Kubernetes
deployment concepts, which belong to `openwepp.org` rather than `wepp.cloud`.

The production incident had two exact signatures:

    EACCES: permission denied, open '/run/secrets/cap_secret'
    EACCES: permission denied, open '/var/lib/cap/tokensList.json'
    Fatal error: cannot open file '/srv/weppcloudr/render-compose-request.R': No such file or directory

CAP restart-looped and the public proxy returned HTTP 502 for CAP health. The
login page itself returned HTTP 200, so users saw a CAPTCHA that never became
interactive. The temporary production containment granted only UID `10001`
read access to the secret and changed the CAP data volume to `10001:10001` while
preserving its ledger.

The same full deployment rebuilt worker code containing the Docker execution
backend but omitted `weppcloudr` from `BUILD_SERVICES`. Full Compose recreation
then started an April renderer image. The user-visible DEVAL job
`130f51de-57cb-4ba2-977a-17f81971a802` failed before rendering because the
worker's required entrypoint was absent. The authoritative timeline is
`docs/infrastructure/incident-2026-08-25-production-compose-partial-build.md`.

## Plan of Work

First, inventory the exact effective numeric identities of all three
`cap_secret` consumers on development, forest1, and wepp1 without reading
secret contents. Ratify the allowlist before mutation. Implement canonical
atomic secret installation/rotation for the fixed
`docker/secrets/cap_secret` path. Require the exact `docker/secrets` parent to
be a non-symlink directory owned by the deployment account with no group/other
write access, and require the secret to be a non-symlink regular file owned by
that account. Stage each replacement inode in the same directory, set owner
read/write with no base group/other access, and apply named-user read ACLs only
to allowlisted consumer UIDs distinct from the owner. Assert the exact
effective ACL before atomic rename and again after installation: owner `rw-`,
allowlisted named users `r--`, owning group `---`, mask `r--`, and other `---`.
POSIX ACL mask bits can make the numeric mode differ from `0600`, so assert
effective `getfacl` permissions rather than mode alone. Verify the
WEPPcloud/rq-engine UID and reject CAP UID `10001` if it maps to an unexpected
host account; permit only an absent mapping or a ratified locked `cap` account.
No live replacement inode may lack the CAP ACL. Reject simultaneous inline
`CAP_SECRET` and `CAP_SECRET_FILE`.

Implement legacy data migration as a one-shot root helper with networking
disabled and only the exact `cap-data` named volume mounted at a fixed path. It
accepts no free-form host path or UID, does not recursively traverse, and may
change only the volume root plus the expected regular `tokensList.json` entry.
Before mutation it rejects unexpected entries, symlinks, directories, special
files, zero-byte/invalid JSON, and JSON with the wrong top-level shape. It
records non-secret integrity and metadata receipts and is idempotent for fresh,
empty, populated legacy, and already migrated states.

Second, make CAP readiness real before constructing the upstream CAP object or
opening the listener. Validate the exact data root and optional ledger schema,
prove that UID `10001` can open an existing ledger for update without changing
it, then perform a create, fsync, and remove probe in the directory without
modifying the ledger. Both existing-file and directory-write proof are
required; one cannot substitute for the other. Keep opaque liveness separate
from readiness. Make deploy acceptance perform a complete challenge, redeem,
and siteverify canary. Prove continuity by minting an unconsumed verification
token before migration and accepting that exact token once after
migration/restart.

Third, add regression coverage before or alongside implementation. Construct
fresh/absent, empty, populated legacy root-owned, correctly owned, and malformed
states independently. For the populated case, record a non-secret checksum or
sentinel before migration and prove it remains after migration. Directly run
the CAP container or Compose service at the real mount boundary; mocks of
filesystem access do not satisfy this gate. Prove the original EACCES
conditions fail deployment explicitly and the valid states start and can
write/redeem.

Implement `docker/validate-cap-runtime-contract.sh` as the single mandatory
host-Docker harness for those production-style bind-secret and named-volume
states. Invoke it from local validation, from the CAP branch of
`docker/validate-aux-image-contract.sh`, and from every deploy mode that
recreates CAP. Do not duplicate the resource checks among those callers.
Missing Docker, named-volume, or ACL capability is a hard prerequisite failure,
not a skipped result.

Fourth, extend `scripts/deploy-production.sh` with separate build-target,
intentionally-recreated, and expected-running service sets and add guarded
`--targeted-cap`. Targeted CAP must build/validate the candidate against
disposable production-style mounts while the old CAP serves. Before candidate
validation or CAP stop, enforce and verify the canonical secret ACL contract,
including when the inode was replaced outside the rotation helper. Record and tag
the running image as a host-local rescue image and skip runtime pruning. Before
stopping CAP, validate the exact secret path and ACL, exact volume
identity/type, migration tooling, candidate image, rescue image/config, and
non-CAP service baseline. Stop only CAP and confirm it is stopped before taking
the closed-ledger integrity/metadata receipt. Run the fixed migration, then
probe the real mounts as `10001:10001`, including create/fsync/remove and
existing-ledger writability, while the stopped old CAP container still exists
as the immediate pre-replacement recovery path. Only after that probe passes
may the script recreate CAP. Require internal readiness, the functional
canary, external health, and stable restart-state samples. Define
`CAP_HEALTHCHECK_URL`; derive it only from an unambiguous host URL and otherwise
fail closed. Any activation failure must restore canonical forward-safe
permissions and the known-good image/config automatically, then prove the
restored CAP passes the same internal readiness, functional canary, and external
health gates before returning the original deployment failure. A recovery that
does not become healthy emits a distinct rescue-failure reason, retains the
rescue image, recorded image/config identity, and non-secret receipts, and
returns nonzero without pruning or printing the deployment success footer.
Every terminal branch that can recover automatically must leave either the old
or new CAP healthy; a failed automatic recovery must preserve the evidence and
exact instructions needed for manual recovery. Never restore the known-bad
permissions.

Full mode must validate all expected replacements, accounting for profiles and
scaled-zero services. Whenever full wepp1 mode intentionally recreates CAP, it
must apply the same CAP pre-stop resource/secret preflight, rescue-image
retention, post-start readiness/canary/health gate, and verified CAP-only
recovery as targeted CAP. Add an internal CAP readiness health check and make
Caddy's CAP dependency `service_healthy`, so a full-stack start cannot activate
its new public proxy before CAP readiness succeeds; follow it with external CAP
health. Full mode need not roll back unrelated services, but it may not exit
while leaving CAP broken. Targeted CAP intentionally leaves the existing Caddy
running and relies on the measured bounded gap plus automatic known-good
restore, not a zero-exposure claim. Targeted web retains only
WEPPcloud/rq-engine checks and must not claim or mutate CAP. Worker-only
wepp2/wepp3 modes remain CAP-free.
Diagnostics use fixed reason codes and service state, never environment dumps,
request bodies, secret values, or unrestricted logs.

For plain full mode, derive the build targets from every enabled service with a
local `build` definition in the effective production Compose configuration.
The script must not use a curated subset while later recreating the full
topology. Treat build targets, intentionally recreated services, expected
running services, migration gates, and acceptance gates as separate executable
contracts. Before activation, compare those contracts and fail if a locally
buildable service would be recreated from an unvalidated stale image.

Add a worker/WEPPcloudR compatibility gate. A candidate worker must not be
activated with a renderer that lacks the Docker execution protocol it invokes.
Validate the required renderer files, including
`/srv/weppcloudr/render-compose-request.R`, `render-request-v1.R`, and
`publish_fenced.py`; parse the R entrypoints; and run the existing protocol
fixture or canary against the candidate images. Full-mode acceptance must check
the state, health where defined, restart stability, and candidate image identity
of every service it recreated. A WEPPcloud-only HTTP check cannot declare a
full deployment successful.

Fifth, update the named canonical destinations:
`docs/ui-docs/cap-js-captcha-auth.md` for runtime/readiness,
`docs/infrastructure/secrets.md` and `docker/secrets/README.md` for secret UID
and rotation, and `docker/README.md` for production deployment and rollback.
Remove stale CAP mount claims. Explain diagnosis without printing secrets and
how rollback preserves the ledger.

Finally, run the integrated release gate on forest1 at
`https://wc-prod.bearhive.duckdns.org`. Capture the checked-out revision,
rendered Compose service/build inventory, image and container identities,
restart counts, RQ worker/job baseline, public endpoint status, and an existing
authenticated browser session. Use isolated disposable resources for CAP and
stale-WEPPcloudR failure injection; do not corrupt the live forest1 ledger.
Prove each injected defect prevents a success result and leaves or restores the
known-good service.

Execute the exact no-argument `scripts/deploy-production.sh` command intended
for production. Verify that every locally buildable recreated service uses the
candidate revision, every recreated service stabilizes, CAP completes its
functional canary, and the existing browser session remains authenticated.
Verify interactive CAPTCHA in Safari and Chrome, local login, OAuth login, and
multi-tab logout behavior. Submit a real RQ-driven DEVAL render through the run
page and require successful job completion, published output, and the expected
render receipt; a direct renderer invocation alone is insufficient. Exercise
targeted web and targeted CAP modes separately and prove non-selected container
identities remain unchanged. Rehearse rollback, then run the exact no-argument
full deploy a second time to prove idempotence. Record the measured login-only
CAP gap and give every disposable resource a unique name with independently
verified cleanup. The expanded full-deploy and WEPPcloudR scope requires fresh
correctness, operations, QA, and security review before production activation;
the existing reviews remain authoritative only for the CAP sub-scope.

## Concrete Steps

Work from `/home/workdir/wepppy` locally and `/workdir/wepppy` on Compose hosts.
Before editing, inspect `docker/AGENTS.md`, `services/cap/Dockerfile`, the CAP
sections of `docker/docker-compose.prod.yml`, and all of
`scripts/deploy-production.sh`. Use `apply_patch` for repository edits.

Discover precedents and affected tests with:

    rg -n "cap_secret|cap-data|/var/lib/cap|CAP_SECRET_FILE|deploy-production|render-compose-request" \
      docker services scripts tests docs -S

Run the narrow regression suite and mandatory host boundary gate with:

    npm --prefix services/cap test
    bash -n scripts/deploy-production.sh docker/prepare-cap-runtime.sh \
      docker/install-cap-secret.sh docker/validate-cap-runtime-contract.sh \
      docker/validate-weppcloudr-runtime-contract.sh
    wctl run-pytest tests/scripts tests/docker/unit/test_rq_worker_startup_contract.py -vv
    wctl run-pytest tests/rq/test_weppcloudr_backends.py tests/rq/test_weppcloudr_rq.py -vv
    docker build --no-cache -f services/cap/Dockerfile -t wepppy-cap-contract .
    docker build -f weppcloudR/Dockerfile -t weppcloudr-contract .
    docker/validate-cap-runtime-contract.sh wepppy-cap-contract
    docker/validate-weppcloudr-runtime-contract.sh weppcloudr-contract

The two runtime-contract commands run on the Docker host and may not skip. The
WEPPcloudR validator must prove the required files exist, parse the R scripts,
and exercise the worker/renderer request fixture. Then run:

    wctl run-pytest tests --maxfail=1
    python3 tools/check_broad_exceptions.py --enforce-changed --base-ref origin/master
    wctl doc-lint --path docs/work-packages/20260825_cap_runtime_deploy_hardening

Use `scripts/deploy-production.sh` for forest1 and production deployment. Any
bounded diagnostic `docker compose` action must be recorded as diagnostic or
failure injection and must not become an alternate deployment path.

## Validation and Acceptance

Acceptance requires direct evidence for each state. A fresh CAP volume starts
and creates writable state as UID/GID `10001:10001`. An empty volume starts. A
populated legacy root-owned ledger remains byte-for-byte or semantically intact
after migration and supports challenge/redeem. An unreadable secret and an
unexpected/malformed data resource produce an explicit nonzero preflight or
deploy result without printing the secret. A correctly migrated rerun is a
no-op and remains healthy.

A canonical data directory containing a root-owned mode-0600 ledger must fail
readiness before CAP listens; a successful adjacent-directory probe must not
mask that file-specific failure. The host-Docker contract also must prove that
its current false-green predecessor cannot pass these production mount states.

The executable deploy harness must prove full wepp1, targeted web, targeted
CAP, wepp2 worker, and wepp3 modes independently. It must assert command order,
failure branches, automatic restore, cleanup, success-footer placement, and
prune ordering. Both full wepp1 and targeted CAP must prove that a CAP activation
failure restores the recorded image/config, re-passes internal readiness, the
functional canary, and external health, and then returns nonzero without a
success footer. Targeted CAP may change only the CAP container, its exact named
volume metadata, the canonical secret ACL, and rescue-image tag. Missing Docker
or ACL capability is an actionable hard failure for the release gate, not a
skip.

The harness must also force automatic restoration itself to fail. That case
must return a distinct nonzero error, omit the success footer and pruning, and
retain the rescue tag, recorded image/config identity, and non-secret receipts
for manual recovery.

For full mode, the harness must prove that the set of enabled locally buildable
services is included in the build set before full recreation. Seed a stale
WEPPcloudR image that lacks `render-compose-request.R` and prove deployment
rejects it before printing success. Then prove the compatible candidate passes
the worker/renderer protocol gate. Assert candidate image identity and stable
state for every recreated service, not only WEPPcloud.

Forest1 acceptance includes two runs of the exact no-argument full deployment,
isolated CAP and stale-renderer failure detection, automatic known-good CAP
restoration, idempotent retry, rollback, the targeted-mode non-impact checks,
and a recorded login-only gap. It also requires interactive local and OAuth
authentication while retaining a pre-deploy session, plus an RQ-submitted DEVAL
render that publishes its output and receipt without the missing-entrypoint
signature. Production
acceptance includes readiness and liveness HTTP 200, functional canary,
interactive CAPTCHA in Safari and Chrome, successful local and OAuth login,
existing account session retention, no browser-data remediation, stable CAP
restart count, and no recurrence of either EACCES signature.

## Idempotence and Recovery

The migration must be safe to rerun and must not replace secret contents or
delete/reinitialize the token ledger. Capture permission metadata and a
non-secret ledger integrity marker after CAP is stopped. If migration fails,
stop before recreating CAP, establish the canonical forward-safe ACL and
`10001:10001` ownership on the exact validated resources, and restart the
previously working image through the canonical Compose/deploy configuration.
Never restore incident, legacy-root-owned, hostile, or partially migrated
metadata. Never use recursive ownership changes on host roots or unresolved
paths.

Failure-injection tests must operate only on explicit disposable resources and
use a cleanup trap as the first recovery layer. After the injection process
ends, a separate operator process must independently verify cleanup or enforce
canonical recovery; the trap is not sufficient evidence by itself. A failed
deploy must leave already-running unselected workers untouched.

## Artifacts and Notes

Store independent reviews and disposition evidence under
`docs/work-packages/20260825_cap_runtime_deploy_hardening/artifacts/`. Never put
secret values, environment dumps, bearer tokens, or unrestricted container
inspection output in artifacts. Record only ownership/mode metadata, service
state, HTTP status, bounded redacted logs, and non-secret integrity markers.

## Interfaces and Dependencies

Use existing Docker Compose, POSIX shell, `wctl`, curl, and host ACL/ownership
tools already present on supported Compose hosts. Do not add an external
dependency. The privileged volume helper receives no path or UID argument and
uses only its fixed CAP volume mount and compiled-in numeric identity. The
secret helper uses only the canonical repository-relative secret path and
ratified identities; it accepts neither a free-form path nor UID. Both return
nonzero on mismatch and emit no secret content.
`docker/validate-cap-runtime-contract.sh` owns the
production-style mount checks and is invoked by local, auxiliary-image, and
CAP-recreating deploy gates. Deployment validation must consume the separate
build, intentionally-recreated, and expected-running sets produced by
`configure_deploy_topology` rather than maintain an unrelated list.
`docker/validate-weppcloudr-runtime-contract.sh` owns renderer entrypoint,
syntax, and worker-protocol compatibility checks. Full mode derives its local
build targets from the effective Compose configuration and must demonstrate
that every locally buildable recreated service has a validated candidate image.

Revision note (2026-08-25 16:12 UTC): incorporated and dispositioned every High
finding from independent correctness, operations, QA, and security reviews;
ratified CAP-only failure-atomic activation, real persistence readiness,
rotation-safe least-privilege access, fixed-scope migration, executable tests,
and an honest bounded login-only availability contract.

Revision note (2026-08-25, QA disposition audit): made QA-01, QA-02, and QA-04
carry-through explicit by naming the shared mandatory host-Docker harness,
requiring existing-ledger write proof separately from directory write proof,
defining automatic-restore failure evidence, and removing the contradictory
instruction to restore the incident's known-bad permissions.

Revision note (2026-08-25, security disposition audit): completed SEC-01
through SEC-03 mapping by gating full-stack Caddy activation on CAP readiness,
specifying canonical secret-parent and host-UID checks plus exact POSIX ACL
semantics, forbidding free-form privileged-helper paths/UIDs, and retaining
only forward-safe metadata during recovery.

Revision note (2026-08-25, production incident expansion): incorporated the
stale-WEPPcloudR failure and the underlying full-mode build/recreate mismatch;
made two exact no-argument Forest1 deployments and an RQ-driven DEVAL render
release gates, and required renewed independent review for the expanded scope.
