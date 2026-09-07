# GridMET Redis Admission and Queue Visibility

**Status**: Open (2026-09-07)
**Timezone**: UTC

## Overview

GridMET downloads are bounded only inside an individual client process. In a
multi-worker deployment, each process applies its own limit, so aggregate
traffic can exceed the upstream service's practical capacity and produce
coordinated read timeouts. This package adds optional, Redis-coordinated
admission with visible FIFO queue state, wires every WEPPpy GridMET client into
that boundary, and proves the behavior across independent containers on the
`forest` development stack.

## Objectives

- Add a dedicated `wepppy.climates.gridmet.admission` module that coordinates
  waiting tickets and active leases atomically in Redis.
- Preserve present behavior when the `GRIDMET_REDIS_ADMISSION_*` environment
  contract is absent or explicitly disabled; disabled clients must not create
  a Redis client or perform Redis I/O.
- Apply one cluster-wide limit to both single-location JSON and gridded NetCDF
  HTTP attempts, including calls reached through GridMET, PRISM, Daymet, and
  supplemental-climate workflows.
- Make admission pressure diagnosable through bounded queue state and
  structured logs without claiming that queue position is a reliable ETA.
- Deploy the opt-in variables to `forest` and obtain agent-recorded evidence
  that independent Forest containers share and enforce the configured limit.

## Scope

### Included

- A standalone GridMET admission module, configuration parser, errors, permit
  context manager, queue/active snapshot interface, and atomic Redis scripts.
- FIFO waiting tickets, expiring active leases, queued-ticket liveness,
  ownership-safe renewal/release, bounded waiting, cancellation, and cleanup.
- Per-HTTP-attempt admission in the single-location and gridded download paths.
  Retry backoff occurs without an active permit and uses the remaining overall
  acquisition budget.
- Explicit propagation through all runtime callers, including the
  multiple-interpolated process pool without passing a live Redis connection
  through `ProcessPoolExecutor`.
- Configuration reference, operational diagnostics, rollback guidance, and
  propagation through `docker/docker-compose.dev.yml`. The committed default
  remains disabled.
- Forest's gitignored `docker/.env` activation and recreation of only the
  services necessary to exercise GridMET work.
- Unit, real-Redis, multiprocessing, client-wiring, Compose-render, and live
  Forest integration evidence.
- A parameterization ADR for the initial limit and timeout/lease values.
- Independent correctness, QA/code, and security reviews.

### Explicitly Out of Scope

- Running a batch workload on `forest` or `openwepp.org`.
- Building registry images or changing the Kubernetes deployment. The operator
  will perform the batch test only after this package is complete and the
  resulting WEPPpy revision is deployed separately to `openwepp.org`.
- Changing RQ queue topology, RQ job timeout defaults, NoDb locking, or batch
  success/failure semantics.
- Treating queue position as an ETA or promising a completion time from it.
- Adding Redis Streams, a new daemon, a dashboard, or an external dependency.
- Editing or validating production/worker-only Compose topologies, or enabling
  admission on `wepp.cloud`, `forest1`, or `openwepp.org`.

## Stakeholders

- **Primary**: Roger Lew and WEPPcloud operators
- **Implementer**: executing Forest agent
- **Reviewers**: independent correctness and QA/code reviewers
- **Security Reviewer**: independent agent reviewing Redis, worker, deployment,
  and external-request boundaries
- **Informed**: later `openwepp.org` deployment operator

## Success Criteria

- [ ] With all `GRIDMET_REDIS_ADMISSION_*` variables absent, public GridMET
  clients preserve their API/results and make no Redis connection or command.
- [ ] Enabled independent processes and containers use one Redis queue and
  never exceed the configured active limit under deterministic contention.
- [ ] Admission is FIFO for live tickets; abandoned queued tickets and active
  leases are reclaimed within documented bounds.
- [ ] Permit ownership prevents one client from renewing or releasing another
  client's permit, and Redis/server time avoids host clock skew.
- [ ] Each HTTP attempt holds a permit only while acquiring/streaming the
  response; validation and retry sleep do not consume capacity.
- [ ] All direct and indirect GridMET acquisition paths opt in when
  Forest configuration enables admission.
- [ ] Queue timeout, upstream timeout, permit loss, invalid configuration, and
  Redis unavailability are distinct, bounded, actionable failures.
- [ ] Forest has the ratified environment values, the affected containers show
  the same effective values, and a fresh process reads them as enabled.
- [ ] An agent executes the package's cross-container Forest probe using a
  unique test key and records raw/sanitized evidence that observed concurrency
  is at most the test limit and at least two, with queued state observed.
- [ ] An actual public GridMET client acquisition on Forest is observed entering
  and leaving Redis admission without leaked queue or active entries.
- [ ] Focused and full repository tests, development Compose rendering,
  documentation lint, correctness review, and security review pass with no
  unresolved medium/high findings.
- [ ] No batch is run and no claim is made about `openwepp.org` behavior.

## Parameterization ADR Gate

- **Parameterization change present**: `yes`
- **ADR required**: `yes`
- **ADR link(s)**: [ADR-0050](../../adrs/ADR-0050-gridmet-redis-admission.md)
- **Decision provenance captured**: `yes; Roger Lew authorized plan execution
  and Redis/explicit opt-in; Codex ratified the initial implementation values
  in ADR-0050, with Forest validation pending`
- **Canonical contract**: [GridMET Redis admission](../../schemas/gridmet-redis-admission-contract.md)

## Dependencies

### Prerequisites

- Existing Redis connectivity and secret-file handling through
  `wepppy.config.redis_settings` and `RedisDB.LOCK`.
- Existing GridMET retry and payload validation in
  `wepppy/climates/gridmet/acquisition.py` and
  `wepppy/climates/gridmet/client.py`.
- Access to the `forest` development Compose stack and authority to update its
  gitignored `docker/.env` and recreate affected worker containers.

### Blocks

- Registry image publication and Kubernetes deployment for the later
  `openwepp.org` batch test.

## Security Impact

- **Level**: `high`
- **Dedicated review required**: `yes`
- **Rationale**: this changes Redis keyspace/TTL behavior, worker concurrency,
  deployment wiring, and outbound external-request admission. Atomic ownership,
  failure containment, secret handling, and denial-of-service behavior require
  independent review.

## Contract Decisions

1. Admission is opt-in. `GridMetAdmissionConfig.from_env()` returns `None` when
   the enable variable is absent or false. No admission object, Redis client, or
   Redis operation is created in that state.
2. Enabling admission is fail-closed. Invalid configuration or unavailable
   Redis raises an explicit GridMET admission error; it never silently bypasses
   the limit.
3. Public client functions accept an optional, keyword-only, serializable
   admission configuration. They do not accept or pickle a live Redis client.
4. One shared pool coordinates point and gridded GridMET acquisition initially.
   Request kind is metadata for observation, not a separate capacity pool.
5. Queue ordering uses a Redis-generated sequence and Redis server time. Atomic
   scripts prune expired state and perform queue-to-active transitions.
6. Queue position and elapsed wait are observable, but no ETA is promised.
7. A permit covers a single outbound attempt, including streamed response
   consumption, and is released before validation-only work or retry backoff.
8. The existing multiple-interpolated local pool remains a per-build ceiling;
   Redis supplies the deployment-wide ceiling.

## Initial Forest Parameters

These values are ratified for implementation in
[ADR-0050](../../adrs/ADR-0050-gridmet-redis-admission.md); live acceptance remains
required before closeout.
If evidence requires a change, update the ADR, package, tracker, tests, and
operator documentation before deployment rather than editing only `docker/.env`.

```text
GRIDMET_REDIS_ADMISSION_ENABLED=true
GRIDMET_REDIS_ADMISSION_LIMIT=4
GRIDMET_REDIS_ADMISSION_WAIT_TIMEOUT_SECONDS=900
GRIDMET_REDIS_ADMISSION_LEASE_SECONDS=300
GRIDMET_REDIS_ADMISSION_QUEUE_TTL_SECONDS=60
GRIDMET_REDIS_ADMISSION_POLL_INTERVAL_SECONDS=0.25
GRIDMET_REDIS_ADMISSION_KEY=wepppy:gridmet:admission:v1
```

The key is operational state, not a secret. Redis credentials continue through
the existing secret-file contract and must never be copied into these values or
test artifacts.

## Related Work

- [Batch Climate and RAP NoDb Contention](../20260906_batch_climate_rap_contention/package.md)
- [Climate Spatial Mode Switching](../20260906_climate_spatial_mode_switching/package.md)

## Deliverables

- [ ] Canonical GridMET admission/configuration contract and parameterization ADR.
- [ ] Admission module and integrations.
- [ ] Automated tests and reusable Forest integration probe.
- [ ] Compose/configuration/runbook updates.
- [ ] Forest deployment and concurrency evidence artifact.
- [ ] Correctness, QA/code, security, and validation artifacts.
- [ ] Updated package tracker, ExecPlan, and `PROJECT_TRACKER.md` at closeout.

## Rollback

Set `GRIDMET_REDIS_ADMISSION_ENABLED=false` (or remove the complete variable
set) in Forest's gitignored `docker/.env`, recreate the same affected services,
and verify a fresh process resolves admission to `None`. Existing Redis queue
keys may then be inspected and deleted only after confirming no enabled client
still uses the namespace. Code rollback uses the preceding known-good commit.
Neither rollback path flushes a Redis database or alters RQ jobs.
