# CAP Runtime and Deployment Hardening Operations Review

**Reviewer**: independent operations/security control agent
**Date**: 2026-08-25 UTC
**Review boundary**: production operations, containment, rollback, and shared
state safety
**Implementation or host mutation by reviewer**: none

## Verdict

**REJECT pending disposition and durable closure of OPS-H1 through OPS-H8.**

No Critical finding was identified. Eight High findings and two Medium
findings are open. The scope-reduced path that can become approvable is:

1. add a guarded CAP-only mode to the canonical Compose deployment script;
2. make CAP's exact secret and named-volume permission contract idempotent;
3. validate that contract before replacing the running CAP container;
4. recreate and validate CAP only on wepp1; and
5. leave wepp1 workers and every service on wepp2/wepp3 untouched.

The current plan must not authorize a production rollout. In particular, the
existing full mode runs `docker compose down`, which stops the entire wepp1
stack, and the current rollback wording can restore the same invalid metadata
that caused the incident.

## Evidence Reviewed

- `docker/AGENTS.md`
- all 722 lines of `scripts/deploy-production.sh`
- `docker/docker-compose.prod.yml`
- `docker/docker-compose.prod.wepp1.yml`
- `docker/docker-compose.prod.worker.yml`
- `docker/docker-compose.prod.wepp3.yml`
- `services/cap/Dockerfile`
- `services/cap/server.js`
- `docker/validate-aux-image-contract.sh`
- `tests/docker/unit/test_rq_worker_startup_contract.py`
- `docker/README.md`
- `docker/secrets/README.md`
- `docs/infrastructure/secrets.md`
- this package's `package.md`, `tracker.md`, and active ExecPlan

Confirmed implementation facts:

- CAP runs as numeric identity `10001:10001`.
- Compose mounts `cap_secret` from `docker/secrets/cap_secret` and mounts the
  `cap-data` named volume at `/var/lib/cap`.
- The same `cap_secret` is consumed by `cap`, `weppcloud`, and `rq-engine`.
- Full deployment builds CAP when present, runs `docker compose down`, then
  starts the whole effective topology with `up -d`.
- Targeted web deployment recreates only `weppcloud` and `rq-engine`; it does
  not exercise CAP.
- Full deployment currently verifies WEPPcloud health only. Existing deploy
  tests primarily assert script text and do not execute service-selection or
  failure/rollback behavior.
- Full deployment normally ends with `docker system prune -a -f`, which can
  remove an unused pre-deploy CAP image needed for rollback.

## Severity-Ranked Findings

| ID | Severity | Finding | Required disposition |
| --- | --- | --- | --- |
| OPS-H1 | High | The repair has no CAP-only canonical deployment mode; using current full mode stops the entire wepp1 stack and its workers. | Add and behaviorally test guarded `--targeted-cap`; use it for wepp1. |
| OPS-H2 | High | Secret migration is underspecified even though `cap_secret` has three runtime consumers and ACLs may disappear on secret replacement. | Ratify a least-privilege, rotation-safe access contract and test all consumers without reading the value. |
| OPS-H3 | High | Rollback can restore known-bad permissions and does not durably preserve the prior image against pruning. | Make canonical permissions forward-only and preserve an exact host-local rescue image/config until observation closes. |
| OPS-H4 | High | Migration order, CAP quiescence, partial-failure handling, and outage bounds are not executable. | Specify and rehearse an exact stop/migrate/probe/recreate/recover state machine. |
| OPS-H5 | High | `BUILD_SERVICES` is not the set recreated by full deployment, so the planned acceptance logic can miss or misclassify services. | Track selected/recreated services separately and validate stable runtime state for that exact set. |
| OPS-H6 | High | Forest1 failure injection can corrupt or strand the live token ledger or leave permissions broken if cleanup fails. | Use isolated fixtures first, exact restoration receipts, and a canonical-state recovery path independent of the injected failure. |
| OPS-H7 | High | Existing deploy tests are static text assertions and cannot prove containment, ordering, idempotence, or non-impact to workers. | Add executable command-fake tests plus an unmocked isolated Compose boundary suite. |
| OPS-H8 | High | The package promises users are not exposed to an unhealthy recreated service, but in-place Compose recreation has a real availability gap and no redundant CAP cutover. | Narrow the promise to preserved browser/session state plus a measured bounded login-only interruption, or explicitly add HA outside this package. |
| OPS-M1 | Medium | CAP public-health URL derivation is not an explicit interface and can target the wrong path when `HEALTHCHECK_URL` is customized. | Add `CAP_HEALTHCHECK_URL` with fail-closed derivation only from an unambiguous host URL. |
| OPS-M2 | Medium | The plan does not require before/after service identity receipts for the non-selected stack. | Record and compare non-CAP container IDs/state and RQ state during forest1 and wepp1 targeted rollouts. |

## Detailed Findings and Closure Evidence

### OPS-H1: Production rollout would unnecessarily stop workers and the full stack

The active ExecPlan says to use `scripts/deploy-production.sh` for forest1 and
production but does not define a CAP-only selector. Today a non-targeted full
deployment executes `wctl ... down`, then `up -d`. On wepp1 that affects web,
Redis, PostgreSQL, Caddy, schedulers, both local RQ workers, and auxiliary
services. CAP repair does not require any of those services to be recreated.

Required action:

- Add a guarded `--targeted-cap` option accepted only when the effective
  topology contains `cap`, `weppcloud`, and `rq-engine` and is the full-stack
  family.
- Set its build scope to `cap` only. It must reject `--flush-rq-db`, skip
  static-asset builds, skip stack `down`, skip dependency recreation, and skip
  broad Docker prune.
- Recreate only CAP with the equivalent of
  `docker compose up -d --no-deps --force-recreate cap` after permission
  migration and runtime preflight pass.
- Refuse the option on worker-only and wepp3 topologies. Do not run the CAP
  repair deployment on wepp2 or wepp3.
- Preserve the future full-deploy CAP migration and acceptance gates, but use
  targeted CAP mode for the production activation of this package.

Closure evidence:

- Executable tests show targeted CAP emits no `down`, Redis flush, static
  build, worker build/recreate, or broad-prune command.
- Forest1 and wepp1 before/after receipts show unchanged container IDs for
  `rq-worker`, `rq-worker-batch`, Redis, PostgreSQL, Caddy, WEPPcloud,
  rq-engine, scheduler, and every other non-CAP service.
- The rollout log identifies `hostname`, `pwd`, Git SHA, effective Compose
  files, selected service `cap`, and no commands issued to wepp2/wepp3.

### OPS-H2: Secret ownership cannot be changed as if CAP were the only consumer

`cap_secret` is mounted into CAP, WEPPcloud, and rq-engine. On wepp1 the Python
image runs as UID `1002`, while CAP runs as UID `10001`. Changing secret
ownership to `10001`, making it group/world-readable, or validating only CAP
can break server-side CAPTCHA verification in web/rq-engine or widen secret
exposure. A named-user ACL applied once is also not durable when an operator
rotates the secret by replacing its inode. The current `chmod 600` guidance can
mask an ACL and silently reproduce the failure.

Required action:

- Keep the secret owned by the deployment/application identity and grant only
  UID `10001` read access through a named-user ACL, unless an alternative is
  proven to preserve least privilege for all three consumers.
- Resolve and validate the exact effective secret path before mutation. Reject
  missing files, symlinks, non-regular files, unexpected resolved paths, and
  group/world access. Never read or hash the secret value for this check.
- Check `getfacl` semantics, not numeric mode alone. Document that secret
  rotation must reapply the CAP ACL atomically before replacing the live file,
  and make deployment preflight fail before CAP replacement when it is absent.
- Prove CAP UID `10001` can read the mount and that WEPPcloud/rq-engine retain
  their access, without printing file content, environment dumps, or rendered
  Compose environment values.
- Update `docker/secrets/README.md` and `docs/infrastructure/secrets.md` so
  generic `chmod 600 docker/secrets/*` does not invalidate the CAP exception.

Closure evidence:

- Fresh secret, correctly ACLed secret, chmod-masked ACL, replaced-inode
  secret, symlink, and over-broad access states are constructed separately.
- Valid states pass all three consumer checks; invalid states stop before CAP
  recreation with path/metadata-only diagnostics.

### OPS-H3: Rollback would restore the incident and may lose the rescue image

The ExecPlan says to restore prior permission metadata after migration failure.
For the legacy and incident states, that metadata is precisely the broken
root-owned volume or unreadable secret. Restoring it is not recovery. The plan
also refers to the previous image without preserving its exact image ID. A
full deployment retags the new build and later runs `docker system prune -a
-f`; an unused prior image may no longer exist when rollback is needed.

Required action:

- Treat the canonical secret ACL and `10001:10001` CAP data ownership as a
  forward-only compatibility migration. Application rollback must not revert
  them to known-bad metadata.
- Before building or recreating CAP, record its exact running image ID, config
  digest/inspection receipt, restart count, Git SHA, and named-volume identity.
- Preserve an exact host-local rescue image/config independently of the moving
  `latest` tag. Suppress broad prune for the rollout and retain the rescue
  material through the 14-day observation window. If a rebuild changes the
  image, use a verified local tag plus prune suppression or a checksummed local
  `docker save` artifact; no registry is needed or permitted for wepp.cloud.
- Define the exact canonical rollback invocation through the new targeted CAP
  mode with `--skip-build`, an immutable local image selector, and the same
  permission preflight. Define how the prior deploy script/config is reached
  if the new script itself fails.
- Never run `down -v`, `docker volume rm`, `docker system prune --volumes`, or
  ledger reinitialization as rollback.

Closure evidence:

- Forest1 rollback succeeds with network access unavailable, restores the
  exact prior image, preserves the named volume and non-secret ledger integrity
  marker, retains canonical permissions, and returns public CAP health.
- A second forward run is a no-op for permissions and succeeds.

### OPS-H4: The migration lacks a failure-atomic execution state machine

The plan requires idempotence but does not decide when CAP is stopped, how a
potentially active token ledger is fenced, which checks occur before outage,
or what state is left after a partial ownership change. Computing a ledger
integrity marker while CAP can write is not valid evidence. Running recursive
ownership changes while the service writes also makes failure analysis
ambiguous.

Required action:

- Before any stop: verify host/topology, exact secret path/type/ACL tooling,
  exact CAP volume mount/type/name, available rescue image, current health, and
  non-CAP service baseline.
- Apply or verify the secret ACL before outage because it does not require
  ledger mutation. Abort without stopping CAP if this fails.
- Stop only CAP, wait for confirmed stopped state, then capture a non-secret
  checksum and metadata receipt for the closed ledger.
- Run a root helper with no secret mount, no network, and only the resolved CAP
  named volume writable. Validate expected node types and stay on that volume's
  filesystem; reject symlinks, unexpected mounts, devices, or sockets. Change
  only the minimum CAP-owned directory/files to `10001:10001`.
- Probe the real secret and volume mounts as UID/GID `10001:10001`, including a
  create/remove write probe and existing-ledger writability, before replacing
  the old CAP container. The probe must not dump content.
- Recreate CAP only, then run bounded state/health/challenge checks. On failure,
  restore service using the rescue image while retaining canonical resource
  permissions. Define a maximum login unavailability budget and an explicit
  rollback trigger.

Closure evidence:

- Forest1 receipts cover failure before stop, failure after CAP stop, partial
  migration, failed new-image health, rescue restart, and rerun. Each terminal
  state is either old CAP healthy or new CAP healthy; no test ends with a
  restart loop or unresolved cleanup.

### OPS-H5: Build selection and recreation selection are different contracts

`BUILD_SERVICES` contains only images built by the script. In full mode the
script runs `down` and `up -d`, so the recreation set is the entire effective
Compose topology, not `BUILD_SERVICES`. A validation loop built from the build
array would repeat the original false-success defect. Conversely, requiring
every Compose service to be running can misclassify scaled-to-zero or
intentionally one-shot/profiled services.

Required action:

- Maintain distinct `BUILD_SERVICES`, `SELECTED_SERVICES`, and
  `EXPECTED_RUNTIME_SERVICES` concepts.
- For targeted CAP, all three sets are exactly `cap`. For targeted web they
  remain `weppcloud`/`rq-engine` as appropriate. For full and worker modes,
  derive expected runtime services from the effective selected Compose model,
  with explicit handling for scaled-to-zero/profiled services.
- After startup, require each expected runtime service to exist and be
  running, not restarting or exited. Sample state and restart counts at least
  twice across a bounded stability interval so a fast crash is not reported as
  success.
- Require public CAP health only when CAP was selected/recreated. Retain
  existing WEPPcloud and targeted rq-engine endpoint gates. Emit only bounded,
  redacted service logs on failure.
- Exit nonzero before the prune/completion banner on any state or health
  failure.

Closure evidence:

- Executable topology tests cover forest1/full, wepp1/full, targeted web,
  targeted CAP, wepp2 worker, and wepp3 single-worker selections.
- Deliberate CAP restart-loop and late crash both fail the deploy even while
  WEPPcloud health is 200. Worker-only modes never evaluate CAP.

### OPS-H6: Forest1 failure injection and restoration are not contained

The ExecPlan proposes deliberate unreadable-secret and root-owned-volume tests
but does not separate synthetic fixtures from Forest1's live CAP resources.
It also says to restore exact prior permissions, which may be invalid. A shell
trap alone is not durable recovery evidence if its process, SSH session, or
host exits unexpectedly.

Required action:

- First run all permission and migration injections against a unique,
  disposable Compose project, synthetic secret, and isolated named volume on
  forest1. Never inject against production wepp1 resources.
- Copy only a non-secret representative ledger fixture into the isolated
  volume. Do not copy artifacts off-host or record ledger contents.
- Prove cleanup and recovery in a separate operator step that does not depend
  on the injected process's trap. Record exact disposable project and volume
  names; validate them before removal.
- Exercise the canonical targeted CAP path against Forest1's real CAP only
  after isolated failures pass. Start from and return to canonical permissions;
  do not deliberately strand the real service in a broken state.
- If a full-deploy acceptance rehearsal is retained, run it only on forest1 in
  a declared maintenance window after RQ idle/drain checks. It is not the
  production rollout mechanism for this package.

Closure evidence:

- The evidence packet contains UTC timestamps, host identity, exact command
  scope, image IDs, container IDs, volume identity, ownership/ACL metadata,
  integrity markers, HTTP statuses, and cleanup verification.
- No secret value, token-ledger content, environment dump, bearer token, or
  unrestricted `docker inspect` output appears in the artifact.

### OPS-H7: Static source assertions do not prove deploy behavior

`tests/docker/unit/test_rq_worker_startup_contract.py` currently verifies
deployment features by searching the script for literal strings. Those tests
can pass when ordering, argument parsing, topology selection, error handling,
or command scope is wrong. `docker/validate-aux-image-contract.sh` uses tmpfs
and an environment secret, so it does not reproduce either production mount
failure.

Required action:

- Add executable shell tests with fake `wctl`, Docker, curl, git, and timing
  commands that run the real deploy script and assert ordered commands, exit
  status, selected services, and forbidden commands for every topology/mode.
- Add an unmocked isolated Compose test with a file-backed secret and named
  volume for absent, empty, populated root-owned, canonical, chmod-masked ACL,
  symlink/malformed, partial-migration, and rerun states.
- Assert ledger preservation by a non-secret fixture checksum/semantic marker
  taken while CAP is stopped. Exercise challenge and redeem/write behavior,
  not `/cap/health` alone.
- Retain simple source assertions only as supplementary contract checks.

Closure evidence:

- Tests fail against the incident-era script/config and pass against the
  repair.
- Test cleanup uses explicit unique resource names and proves no test project,
  container, network, or volume remains.

### OPS-H8: The no-exposure promise exceeds the current architecture

The package overview says deployment will fail before users are exposed when a
recreated service cannot become healthy. Docker Compose in-place recreation is
not an atomic blue/green cutover: CAP is unavailable between old-container stop
and new-container readiness, and a post-start crash is visible until rollback.
The package does not introduce redundant CAP instances or a concurrency-safe
shared token store, so zero login interruption cannot be promised honestly.

Required action:

- Amend the contract to guarantee no logout, cookie clearing, site-data
  clearing, session rotation, or loss of the CAP ledger.
- State and measure a bounded CAPTCHA/login-only interruption during CAP
  recreation, with a rollback threshold. Existing authenticated sessions and
  non-login application paths must remain available because only CAP changes.
- If zero login interruption is mandatory, stop and create a separate HA CAP
  design package; do not smuggle replication/shared-store changes into this
  incident repair.

Closure evidence:

- Forest1 records old-CAP stop to new-CAP health duration and successful
  challenge/redeem immediately after readiness.
- Production records the same bounded interval plus retained authenticated
  sessions and successful Safari/Chrome local login. OAuth remains a general
  auth smoke, not evidence for CAP itself.

### OPS-M1: Make CAP health URL selection explicit

Add `CAP_HEALTHCHECK_URL`. Derive it only when the configured WEPPcloud URL ends
in the canonical `/weppcloud/health` suffix or when `EXTERNAL_HOST` is an
unambiguous host/base URL. Otherwise fail before recreation and require the
override. Log the URL but never credentials or query strings.

### OPS-M2: Prove non-selected services stayed untouched

For targeted CAP rehearsal and rollout, capture the Compose service-to-
container-ID/state map before and after. Require exact identity retention for
all non-CAP containers and no increase in worker restart counts. Capture
`wctl rq-info --detailed` read-only before and after to demonstrate that the
CAP operation did not interrupt or purge queue state. A naturally occurring
unrelated restart is a stop-and-investigate condition, not evidence that the
CAP selector may be broader.

## Required Forest1 Rehearsal Sequence

1. Verify `hostname`, `pwd`, clean/reviewed Git SHA, installed production
   `wctl` preset, effective Compose files, and all current service states.
2. Establish isolated synthetic secret/volume fixtures and prove the recovery
   procedure before failure injection.
3. Run absent, empty, populated legacy, canonical rerun, chmod-masked ACL,
   unexpected resource, partial migration, unhealthy CAP, and rescue rollback
   cases in the isolated project.
4. Confirm exact cleanup from a separate operator shell/process.
5. Capture Forest1 real-stack non-CAP container IDs, RQ state, CAP image ID,
   restart count, volume identity, ACL/ownership metadata, and ledger integrity
   marker without content.
6. Run canonical targeted CAP deployment. Require preflight before CAP stop,
   canonical permission migration, runtime mount probe, CAP-only recreation,
   stable state, public health, and challenge/redeem.
7. Verify every non-CAP container ID and worker restart count is unchanged.
8. Rehearse exact rescue-image rollback and a second forward/idempotent run.
9. If testing full-deploy acceptance, do so as a separate forest1 maintenance
   exercise with idle/drained workers; do not conflate it with the CAP-only
   production activation.

## Required wepp1 Rollout and Rollback Sequence

Production approval requires all review High/Critical findings closed and an
immutable implementation revision already proven on forest1.

1. Verify host identity, repository state, exact revision, effective topology,
   CAP current health/restart count, secret metadata, named-volume identity,
   and non-CAP container IDs. Do not read secret or ledger contents.
2. Preserve the exact current CAP image/config as the rescue target and keep
   broad prune disabled through the observation window.
3. Run only the targeted CAP mode. Do not run the script on wepp2/wepp3 and do
   not stop/recreate any wepp1 worker or dependency.
4. Require preflight to pass before CAP stop. Measure stop-to-health duration.
5. Require two-sample stable CAP state/restart count, public `/cap/health` 200,
   challenge/redeem success, absence of both EACCES signatures, retained
   existing authenticated sessions, and successful local login.
6. Require all non-CAP container IDs and worker restart counts unchanged and RQ
   state consistent with normal workload progression.
7. Roll back immediately on permission/preflight ambiguity, CAP restart or
   late crash, failed public health/challenge/redeem, ledger integrity mismatch,
   unexpected non-CAP container change, or interruption beyond the ratified
   availability budget.
8. Rollback restores the exact rescue image/config through targeted CAP mode
   while retaining canonical ACL/ownership and the existing named volume.
9. Retain evidence and rescue material for the 14-day observation window; any
   recurrence of either EACCES signature or CAP restart growth reopens review.

## Approval Conditions

This review changes to **approve** only after:

- OPS-H1 through OPS-H8 have explicit dispositions in the active ExecPlan and
  tracker;
- implementation and test evidence close each required action;
- forest1 forward, failure, recovery, rollback, and idempotent retry evidence
  is complete;
- correctness/UX, QA, and security review gates independently approve; and
- the exact wepp1 targeted rollout and rollback commands are reviewed before
  execution.

The package should remain blocked from production rollout until those
conditions are met.
