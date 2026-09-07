# Forest GridMET admission acceptance

**Result: PASS, 2026-09-07 UTC.** No batch was submitted. Registry publication,
Kubernetes/openwepp.org deployment, and subsequent batch validation remain the
operator's separate phase.

## Revision, deployment, and identities

- Host: `forest` (`forest.bearhive.internal`).
- Runtime candidate: `ae5d107d44a77c6ff3d0288e97b86cac174a77a4`, committed and
  pushed to `origin/master` before activation.
- Contract ancestor: `1b4835ca73bc67c9c84ecbb26f596aab4078e234`.
- Previous runtime baseline: `583e6870c639999515035423f133e5925dae2da5`.
- Installed `/usr/local/bin/wctl` resolves to this repository's wrapper and
  selects `docker/docker-compose.dev.yml`. The tree was clean at deployment.
- Redis: existing healthy standalone 8.6.2, using canonical `RedisDB.LOCK`
  connection helpers. No Redis/stateful service was recreated.

| Service | Acceptance container | Final restored container |
| --- | --- | --- |
| `rq-worker` | `633c7b74ff98` | `5f35997d7704` |
| `rq-worker-batch` | `0f827e6565fb` | `7e32b08ff7f7` |

Fresh processes in both containers verified the full candidate SHA and identical
configuration. Only these two services were recreated, using:

```bash
wctl docker compose up -d --no-deps rq-worker rq-worker-batch
```

The seven admission lines in gitignored `docker/.env` were backed up to a
mode-0600 temporary file before line-scoped activation. All other environment
lines were preserved. Compose was rendered/validated before recreation, and
only filtered admission values were recorded. Effective final values:

```dotenv
GRIDMET_REDIS_ADMISSION_ENABLED=true
GRIDMET_REDIS_ADMISSION_LIMIT=4
GRIDMET_REDIS_ADMISSION_WAIT_TIMEOUT_SECONDS=900
GRIDMET_REDIS_ADMISSION_LEASE_SECONDS=300
GRIDMET_REDIS_ADMISSION_QUEUE_TTL_SECONDS=60
GRIDMET_REDIS_ADMISSION_POLL_INTERVAL_SECONDS=0.25
GRIDMET_REDIS_ADMISSION_KEY=wepppy:gridmet:admission:v1
```

## Cross-container probes

[Machine-readable evidence](2026-09-07_forest_evidence.json) contains exact keys,
Redis server timestamps, contender/process/container identities, acquisition
and release records, state-change samples, deployment configuration, rollback,
and final worker health. Samples are condensed only when occupancy is unchanged;
the probe summary used every original observation.

Every key starts
`wepppy:gridmet:admission:acceptance:ae5d107d44a7-20260907T170013Z-`.
Suffixes are `concurrency`, `killed-waiter`, `killed-holder`, and `public`.
The shared test policy was limit 2, wait 120 seconds, lease 30 seconds, queue TTL
9 seconds, and poll 0.05 seconds. The public probe used lease 300 seconds.

| Repetition | Contenders / survivors | Peak | Queued | FIFO sequences of survivors | Final queued / active |
| --- | --- | --- | --- | --- | --- |
| Ordinary | 6 / 6 | 2 | Yes | 1, 2, 3, 4, 5, 6 | 0 / 0 |
| Killed waiter | 6 / 5 | 2 | Yes | 1, 2, 4, 5, 6 | 0 / 0 |
| Killed holder | 6 / 5 | 2 | Yes | 2, 3, 4, 5, 6 | 0 / 0 |

All repetitions reported zero limit violations and matching acquisition/release
identities for survivors across both containers. One intentionally killed
process accounts for each missing completion in crash repetitions.

The waiter was killed only after observing two live holders and exactly one
queued ticket. Its ticket was reclaimed in **9.626 seconds**; both original
holders were still active. The holder was killed after its acquisition record
and visible queuing; its abandoned lease was reclaimed in **30.011 seconds**.
These measurements include the next observer poll and command overhead.

Commands used the reviewed probe through `wctl docker compose exec -T SERVICE
python tools/gridmet_admission_probe.py`. For ordinary contention, three
`worker` invocations ran in each service, with distinct `--worker-id` values
0 through 5 and `--hold-seconds 3`. The other container ran `observe
--duration-seconds 30 --require-peak --require-queued` with the same key.
Offline `summarize --contenders 6 --minimum-containers 2 --input FILE`
combined the observer and six worker files.

For waiter recovery, two holders used `--hold-seconds 25`, the queued victim
and three subsequent contenders used 2 seconds, and observation lasted 50
seconds. For holder recovery, six contenders used 4-second holds and 50-second
observation. Each kill targeted only the exact PID emitted by its probe:
`wctl docker compose exec -T SERVICE kill -KILL PID`. Survivor summaries used
`--contenders 5 --minimum-containers 2`. No wildcard deletion or Redis flush was
performed; normal release and expiry cleaned the test state.

## Actual public GridMET request

The default worker ran:

```bash
python tools/gridmet_admission_probe.py public --key "$PUBLIC_KEY" --lease-seconds 300 --timeout-seconds 180
```

The batch worker independently ran `observe --key "$PUBLIC_KEY"
--lease-seconds 300 --duration-seconds 30`, followed by a final `inspect` with
the same key/lease. `PUBLIC_KEY` is the exact prefix above plus `public`.

The real public precipitation client returned **366 valid rows for 2020** from
the existing GridMET endpoint. The other container observed `active=1` during
the request. The client exited successfully without timing out, and both its
own cleanup check and the independent final inspection reported zero queued
and active entries. Full query URLs and credentials are excluded from evidence.

## Rollback and final health

Actual rollback was exercised while every RQ worker was idle: set only the
enable line false, validate Compose, recreate the same two services, and check
fresh `GridMetAdmissionConfig.from_env()` results. Both returned `None`
(containers `cecf1bf2983a` and `24dcb26e20f4`). Then restore true, recreate the
same services, and verify the final identities and ratified configuration above.
Every fresh revision check still reported the exact runtime candidate SHA.

Final registry: six default, four batch, one unchanged fork/archive worker;
all **11 idle**. Canonical operational inspection before and after rollback
reported zero queued/active state, limit four, and no expired logical debris.
The namespace was unused/absent, which is a valid state. Forest remains enabled.

## Limits and closeout provenance

This proves the shared live-Redis-permit ceiling across independent containers,
cooperative HTTP integration, cleanup, expiry, and rollback. It does not fence
an already-running remote request after arbitrary suspension or partition.

The subsequent closeout commit changes documentation/evidence only; its runtime,
tools, tests, and Compose files are identical to the deployed candidate. No
Kubernetes or openwepp.org acceptance is claimed.
