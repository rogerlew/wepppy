# Forest restart acceptance

Host: `forest`. Date: 2026-09-16 UTC. Contract ancestor: `9395f4722`.
The tested runtime is the implementation working tree on that ancestor; final
implementation commit is recorded in the tracker. This is development acceptance.

Inspected installed `wctl`, `docker/docker-compose.dev.yml`, Docker guidance and
`scripts/deploy-production.sh`. Forest uses the installed development Compose
preset; the production deployment script was not invoked. No push, volume removal,
queue cancellation or other host operation occurred.

## Before restart

All three queues had zero queued/started jobs at 23:07:46 UTC. The latest named
legacy acceptance was `e10dbaa5899047e1be37d074b3a8df07`. Canonical `archive_rq`
created `nervous-mesquite.20260916T230145Z.zip`; ZIP integrity, all 84 retained
module files and the exact module NoDb bytes matched the captured before-state.
Archive path/hash: [baseline_archive.json](baseline_archive.json).
Protected input inventory: [nervous_protected_before.json](nervous_protected_before.json).

## Commands and recovery

1. `wctl exec -T weppcloud python wepppy/weppcloud/controllers_js/build_controllers_js.py`
2. `wctl build preflight` and `wctl up -d --no-deps preflight`
3. `wctl restart` at approximately 23:08 UTC; all configured services restarted.
4. `wctl ps`, web login HTTP check and preflight `/health` check.
5. Redis became healthy, but preflight had exited when Redis returned `LOADING`
   during simultaneous restart. `wctl restart preflight` restored `/health` = `OK`.
   This was startup ordering, not a model failure; retained logs show the original
   exit and recovery. No data or Redis state was reset.

The small follow-up for startup reliability is to classify Redis `LOADING` as
retryable in preflight's existing startup loop. It is outside this source/report
change; no service redesign or implicit fix is claimed.

## Loaded runtime and real acceptance

The new workers accepted Kf schema-3 jobs after restart. The web served the new
curve, Kf labels, report CSV and source browse. Normal worker/service identities
and bind mounts were used; no root-only alternate scientific execution path.
Both job trees reached finished state. See [named run](nervous_mesquite_e2e.md)
and [generic fixture](generic_e2e.md). M3 read-only browser regression passed with
23 protected files unchanged and no mutation requests beyond ordinary recorder events.

Retained logs: `logs/stack-restart.log`, `logs/preflight-build.log`,
`logs/preflight-recovery.log`; final service/identity/job evidence is in `logs/`.
Exited build helpers and the pre-existing stopped `f-esri` orphan are not
application-service failures.
