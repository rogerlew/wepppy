# Incident Report: Production Compose Partial-Build Deployment Failures

**Date:** 2026-08-25
**Environment:** WEPPcloud production (`wepp1`, `wepp2`, `wepp3`,
`https://wepp.cloud`)
**Status:** User-facing failures contained; durable deployment repair pending
**Severity:** High

## Summary

On 2026-08-25, the ordinary no-flag production command
`scripts/deploy-production.sh` deployed repository HEAD to the `wepp.cloud`
Docker Compose hosts. On the full `wepp1` topology, the script built a manually
curated subset of images, stopped the entire Compose stack, and recreated every
default service. It then treated the WEPPcloud web health endpoint as sufficient
proof of deployment success.

Two user-visible failures followed from that inconsistent contract:

1. CAP was rebuilt with its hardened non-root UID `10001`, but its bind-mounted
   secret and populated named volume retained permissions for earlier runtime
   identities. CAP restart-looped, so the login CAPTCHA did not become
   interactive in Safari or Chrome.
2. The RQ worker image was rebuilt with the new WEPPcloudR Docker execution
   backend, but `weppcloudr` was omitted from the full-mode build list. Compose
   recreated WEPPcloudR from an April image that lacked
   `/srv/weppcloudr/render-compose-request.R`. DEVAL rendering therefore failed
   immediately with exit code 2.

The failures had one root cause: full deployment did not make the set of images
built, services recreated, runtime migrations applied, and services validated
the same explicit set.

## User Impact

- Local password login and registration CAPTCHA interactions were unavailable
  while CAP restart-looped. The regression was confirmed in both Safari and
  Chrome.
- OAuth login was not dependent on the interactive CAPTCHA, but the incident
  put authentication-adjacent production state at risk and required explicit
  verification after containment.
- The DEVAL "Deval in the Details" report for run
  `satisfactory-buttermilk/disturbed9002` failed. RQ job
  `130f51de-57cb-4ba2-977a-17f81971a802` displayed only a generic render
  failure to the user.
- Existing authenticated sessions, RQ workers, and already running model jobs
  were preserved during the targeted containment actions. Users were not
  required to log out, clear cookies, or clear site data.

## Detection

CAP was detected from a user report that the login CAPTCHA was not clickable.
Production inspection showed:

    docker-cap-1: Restarting (1)
    EACCES: permission denied, open '/run/secrets/cap_secret'

After CAP could start, it also logged:

    EACCES: permission denied, open '/var/lib/cap/tokensList.json'

The DEVAL failure was detected from the user-visible failed render page. The RQ
record reported a selected Docker backend exit code 2. The job's captured
stdout contained the actual cause:

    Fatal error: cannot open file '/srv/weppcloudr/render-compose-request.R': No such file or directory

## Timeline

All timestamps are UTC on 2026-08-25. Times marked approximate are reconstructed
from container creation/start metadata.

- **~12:23:** Plain full deployment recreated the wepp1 Compose stack from
  repository revision `075910aff816d6d28e8f1ec4e0c985b9dd6d51eb`. The script
  reported success after WEPPcloud health passed.
- **15:39:** CAP restart loop and unreadable `cap_secret` were confirmed.
- **15:42:** CAP was restarted after least-privilege UID `10001` secret access
  and CAP data-volume ownership were repaired. The container remained stable
  with restart count zero.
- **15:45:** The operator confirmed the CAPTCHA was interactive and login
  worked in the previously failing production environment.
- **16:18:37:** DEVAL job
  `130f51de-57cb-4ba2-977a-17f81971a802` started and failed in less than one
  second because the running WEPPcloudR image lacked the new Compose render
  entrypoint.
- **16:25:** WEPPcloudR was rebuilt from production HEAD and only the
  `weppcloudr` container was recreated on wepp1. The required renderer scripts
  were present in the rebuilt image.
- **16:38:** WEPPcloudR was cleanly rebuilt and only `weppcloudr` recreated on
  wepp2. Both worker containers remained running; the renderer became healthy
  and its scripts parsed successfully.

## Root Cause

### Full deployment used incompatible service sets

The full wepp1 topology selected this manual build set:

    BUILD_SERVICES=(weppcloud rq-worker cap status preflight)

The same execution later ran full-stack operations equivalent to:

    docker compose down
    docker compose up -d

`down` and default `up` operated on the complete default Compose application,
not only `BUILD_SERVICES`. Locally built services such as `weppcloudr` could
therefore be recreated from a stale `:latest` image.

The script had no first-class distinction among:

- build targets,
- services intentionally recreated,
- services expected to remain running,
- runtime migrations required by a candidate image, and
- readiness/functional checks required before declaring success.

### Cross-image compatibility was not enforced

Revision `80e621164` introduced the WEPPcloudR execution backend. New worker
code invokes `/srv/weppcloudr/render-compose-request.R`, and the same revision
adds that file to `weppcloudR/Dockerfile`. Deploying the worker without rebuilding
WEPPcloudR created an unsupported mixed version.

No manifest, preflight, or integration check asserted that the worker-side
render protocol and renderer entrypoints were compatible. The existing unit
tests exercised Python and R components but did not execute the production
full-deployment sequence against real Compose images.

### CAP runtime migration was omitted

The CAP image was hardened to run as UID/GID `10001:10001`. Image-layer
ownership of `/var/lib/cap` did not migrate an existing named volume mounted
over that directory, and the mode-0600 host secret did not grant the new UID
read access. Secret ACLs are also inode-specific, so secret replacement can
reintroduce the problem unless the rotation/install path reapplies the access
contract.

The deployment built and activated the new image without a pre-start migration
or a production-style secret/volume contract test.

### Deployment validation was too shallow

Full mode checked `/weppcloud/health` only. It did not reject a restarting CAP
container, did not check CAP persistence readiness, did not validate
WEPPcloudR's required entrypoints, and did not exercise a DEVAL render. The
deployment could therefore print success while two recreated services were
incompatible or unusable.

## Contributing Factors

- Targeted web mode was rehearsed on forest1, but the production operation used
  plain full mode. The exact path shipped to production was not integrated-
  tested on forest1.
- Deployment tests primarily searched the shell script for expected strings;
  they did not execute its modes, command ordering, failure branches, or
  cleanup/rollback behavior.
- A manually maintained full build list could drift from Compose whenever a
  locally built service or cross-image contract changed.
- `:latest` tags concealed image age and compatibility. The wepp1 renderer
  recreated during deployment was built on 2026-04-18.
- Full deployment success was inferred from the web frontend rather than from
  every recreated service and user-critical workflow.
- The rehearsal and rollout plan focused on session migration and did not
  inventory unrelated services that plain full mode would rebuild or recreate.

## Containment and Recovery

### CAP

- Granted only CAP UID `10001` read access to the canonical host secret using a
  POSIX ACL; the secret was not made group/world readable.
- Preserved the existing token ledger and migrated the exact CAP named volume
  to UID/GID `10001:10001`.
- Restarted only CAP and verified secret readability, ledger writability,
  public health, and successful login. No browser data remediation was needed.

These host-local changes contain wepp1 but do not replace the required durable
install/rotation and legacy-volume migration contract.

### WEPPcloudR

- Verified no DEVAL job was active before replacement.
- Rebuilt WEPPcloudR from the checked-out production revision.
- Recreated only `weppcloudr` on wepp1 and wepp2; workers and web/session
  services remained running.
- Verified both renderer entrypoints exist and parse. On wepp2, the renderer
  reached Compose health `healthy`.

The failed DEVAL job remains historical evidence and must not be represented as
successful. A new/retried render requires a distinct successful RQ result and
artifact validation.

## What Changed on 2026-08-24

The deployment changes immediately preceding the incident added
`--targeted-web`, conditional stack shutdown/startup, rq-engine health polling,
and targeted prune behavior in commits `20d306ba5`, `c4f509634`, and
`5ef67d8d4`. These branches did not directly change plain full mode's manual
build list; that list originated earlier.

However, the deployment work added more mode-specific service bookkeeping
without correcting the fundamental full-mode build/recreate mismatch. Forest1
validated targeted web mode, then production used the unrehearsed plain full
mode. The operator/agent declared the rollout ready without proving all
services affected by the actual command. That process failure activated both
latent defects.

## Corrective Action Plan

The durable work is tracked in
`docs/work-packages/20260825_cap_runtime_deploy_hardening/`. Although the
directory retains its original incident-specific slug, the package scope now
covers the complete Compose deployment consistency failure.

Required corrections are:

1. Make full mode build every locally buildable service it will recreate.
2. Maintain distinct, executable contracts for build targets, recreated
   services, expected-running services, migrations, and acceptance checks.
3. Add cross-image WEPPcloudR protocol/entrypoint validation and an end-to-end
   DEVAL canary.
4. Add durable CAP secret rotation, legacy-volume migration, persistence
   readiness, and functional canary coverage.
5. Make targeted modes mutate and validate only their declared services.
6. Fail deployment if any recreated service is restarting, exited, unhealthy,
   incompatible, or functionally unusable.
7. Rehearse the exact no-flag full command on forest1
   (`wc-prod.bearhive.duckdns.org`) before production.
8. Require independent correctness, operations, QA, and security re-review
   after implementation and forest1 evidence.

## Forest1 Integrated-Test Gate

Forest1 is the production-like acceptance environment. Before another plain
full production deployment, the package must record all of the following:

- Baseline revision, rendered Compose service/build inventory, image IDs,
  container IDs, health/restart state, RQ state, and user-critical endpoints.
- A real no-flag `scripts/deploy-production.sh` execution from the candidate
  revision, not a targeted substitute.
- Proof that every locally built service recreated by full mode was built from
  the candidate context and that no stale image was activated.
- CAP production-style fresh, populated legacy, rotated-secret, malformed, and
  rollback tests using isolated disposable resources.
- Interactive CAPTCHA plus local login in Safari and Chrome, OAuth login, and
  existing-session continuity without logout or site-data clearing.
- A real RQ-driven DEVAL render that invokes the Compose backend, finishes, and
  publishes a validated report artifact and receipt.
- Targeted web and targeted CAP rehearsals proving non-selected container IDs
  and workers remain unchanged.
- Failure-injection and automatic/manual recovery evidence, followed by an
  independent cleanup verification process.
- A second no-flag full deploy proving idempotence and stable service/image
  identity contracts.

Production rollout remains blocked until this integrated gate and independent
re-review pass.

## Hardening Hypothesis and Signals

**Hypothesis:** If every deployment mode derives and validates explicit build,
recreate, migration, and acceptance sets from the effective Compose topology,
then stale mixed images and missing runtime migrations will fail before the
script reports success. Any later CAP/WEPPcloudR recurrence will create a new
incident that cites and reassesses this hardening rather than depending on an
elapsed-time follow-up.

**Health signals:**

- Zero recurrence of both CAP EACCES signatures.
- Zero deployments activating an image older than or incompatible with the
  candidate revision.
- Zero DEVAL failures caused by missing renderer protocol files.
- Every recreated service stable and every required functional canary passing
  before deployment success.

**Danger signals:**

- A manually curated full-build list can omit a Compose build service.
- Full and targeted modes share implicit mutable arrays with different meaning.
- A health endpoint can pass while persistence or a cross-service operation
  fails.
- Forest1 evidence covers a different command/mode from production.
- A rollback restores known-bad permissions or prunes the rescue image.

**Observation model:** stateless and recurrence-triggered. Capture one bounded
pre/post-rollout signal snapshot. After closure, any danger signal creates a
new incident/work package linked to this record; no scheduled telemetry state
or remembered calendar follow-up is required.

## Lessons Learned

- A deployment command is a product interface. Its ordinary no-flag behavior
  must be the best-tested path, not a composition of exceptions.
- Building a subset and recreating a superset is unsafe even when both commands
  individually succeed.
- Cross-image contracts require integrated deployment evidence; component tests
  cannot prove compatible image selection.
- Health is service-specific and may require persistence or workflow readiness,
  not merely an HTTP listener.
- Rehearsal must use the exact production command and topology. A targeted-mode
  rehearsal does not authorize a full-mode production rollout.
- User recovery must remain operator-owned. Logout, cookie clearing, and site-
  data clearing are not acceptable substitutes for compatible deployment.

## References

- `scripts/deploy-production.sh`
- `docker/docker-compose.prod.yml`
- `docker/AGENTS.md`
- `services/cap/Dockerfile`
- `weppcloudR/Dockerfile`
- `weppcloudR/render-compose-request.R`
- `wepppy/rq/weppcloudr_backends.py`
- `docs/work-packages/20260825_cap_runtime_deploy_hardening/package.md`
- `docs/standards/hardening-lifecycle-standard.md`
> **Forest1 rehearsal update (2026-08-25 21:38 UTC):** The durable repair at
> `e11985f02` passed two exact full deployments, targeted-mode isolation, CAP
> hostile-state and rescue checks, stale-renderer rejection, and a real
> RQ-driven DEVAL publication. See
> `docs/work-packages/20260825_cap_runtime_deploy_hardening/artifacts/2026-08-25_forest1_integrated_rehearsal.md`.
