# M7 validation follow-up

Status: approved storage move complete; runner validation in progress. No
threshold waiver. The full Forest regression suite is running.

## Scope and evidence

Resolve the run-catalog marker latency failure and provide a capable stubtest
runner. Keep the catalog contract's 50 ms added-p95 threshold and PostgreSQL
durability settings unchanged. Recurring WMesque sync remains disabled.

Forest source: `88cc1fafa`. PostgreSQL 16 data is a 108 MB bind mount from
`.docker-data/postgres` on `/home`, an ext4 rotational RAID6 filesystem.
Docker's data root is `/var/lib/docker`, on the root SSD filesystem.

- Original M7 baseline: READONLY added p95 123.88 ms; broad suite stopped at
  10,664 passed, 126 skipped, one failure.
- First follow-up READONLY run: added p95 46.84 ms, narrowly passing.
- All four latency checks together: three passed, TTL failed.
- Instrumented unchanged marker tests: READONLY added p95 36.49 ms and TTL
  49.33 ms. SQL execute p95 was 1.75/1.74 ms; commit p95 was 30.44/42.09 ms,
  with maxima 61.28/80.18 ms. The diagnostic wrapped the test engine's
  `do_execute` and `do_commit`; it did not alter SQL or settings.
- Independent 100-sample 8 KiB file append/flush/fdatasync probe: RAID6 p95
  89.47 ms, maximum 181.32 ms; root SSD p95 0.55 ms, maximum 0.66 ms.
- `synchronous_commit=on`, `fsync=on`, `wal_sync_method=fdatasync`.
- Later unchanged full run-catalog PostgreSQL module: 24 passed in 41.74 s.
  This variable outcome does not resolve the earlier reproducible failures.

These observations identify durable commit/storage latency as the leading
cause. A storage move followed by the same tests is required to confirm the fix.
Raw mutation and SQL-phase samples are retained in
[`20261015_latency_samples.json`](20261015_latency_samples.json).
No async notifier, retry, durability relaxation, or benchmark exclusion is
proposed. The canonical authority remains
`docs/schemas/run-catalog-projection-contract.md`, promotion targets and matched
performance baselines.

## Approved Forest storage move

Use the existing production precedent of a Docker named PostgreSQL data volume
for Forest. Add an optional dev Compose data-source override, defaulting to the
current bind mount; configure only Forest to use `forest-postgres-ssd`. Docker stores
this volume on the measured SSD filesystem. No database version, identity,
schema, network, or durability changes are involved.

Operator explicitly approved this proposal on 2026-10-15. Execution sequence:

1. Record current database identities, relation counts and service health;
   create a restricted logical backup. Check active RQ work and quiesce database
   consumers before the brief database outage; do not flush queues.
2. Stop PostgreSQL cleanly through wctl. Copy the complete stopped data directory
   into the new named volume, retaining ownership, modes and the original bind
   directory. Verify copied bytes and metadata before starting it.
3. Configure Forest's non-secret override and recreate PostgreSQL through wctl.
   Verify the actual mount, PostgreSQL health, database/relation readback and
   unchanged durability settings, then restore consumers.
4. Run the unchanged four latency tests and full suite. Validate application
   health and database reads after recreation. Retain metrics and gate results.

Rollback before resuming writes: stop PostgreSQL, restore the original mount
configuration and recreate. After writes resume, stop cleanly and copy the
current volume back before returning to the bind mount; the retained old copy
alone is then stale and must not be promoted. Do not delete either copy during
this task. SSD RAID0 has different device-failure resilience from RAID6; retain
the existing RAID6-backed PostgreSQL backup path.

Root `AGENTS.md` requires explicit operator approval for mount changes. Existing
Forest restart authorization did not by itself authorize this storage change;
the subsequent explicit approval supplies it.

### Execution receipt

- No active or queued RQ work; workers idle before quiescing database consumers.
- Restricted logical backup (2,388,063 bytes) completed in
  `/home/roger/.local/state/wepppy/m7-postgres-20261015/before.sql` on RAID6;
  directory mode 0700, file mode 0600. No backup contents are committed.
- PostgreSQL stopped cleanly. Copied bytes and owner/group/mode metadata matched
  before startup. The original bind directory is retained.
- Actual data mount is `docker_forest-postgres-ssd` under `/var/lib/docker`.
  The existing unrelated `docker_postgres-data` volume was not modified.
- Database identities and exact user-table row counts match before/after.
  Only default tablespaces exist; no external tablespace was omitted.
- `fsync=on`, `synchronous_commit=on`, `wal_sync_method=fdatasync` preserved.
- Consumers and daily RAID6 backup service resumed; public Forest health is OK.
- Four unchanged latency tests pass: NoDb added p95 2.89 ms, READONLY 5.81 ms,
  TTL 4.73 ms; timestamp adapter p95 2.05 ms versus legacy 26.34 ms.
  Database-refusal save completed in 4.01 ms. Raw samples are retained.

## Stubtest

GitHub currently registers runner-01 with `ghcr-builder` and runner-02 with
`remote-ci`; neither has `homelab`, which the generated Stubtest workflow
requires. Preserve the dedicated builder boundary from
`.github/workflows/AGENTS.md`. Do not change labels merely to make a job start.

Runner-02 has Docker but had no WEPPpy runtime or dev checkout. Operator confirmed
its tailnet access; noninteractive SSH succeeded. The current common image pulled
anonymously by immutable digest; no registry credential was introduced. Direct
runner stubtest passes all eight modules with corrected source mounted.

The canonical workflow now selects `remote-ci`, bypasses Forest's host bootstrap,
materializes and verifies LFS assets, and uses an isolated test Compose stack.
The short stubtest/completeness job has a 30-minute limit; the retained full
isolation gate follows it in a separate 360-minute job with two file workers.
That job first checks the baseline suite explicitly: the isolation tool alone
can treat consistently failing tests as non-isolation issues. Diagnostics are
archived without dereferencing symlinks before host-side upload. Neither job mounts
host credentials or the Docker socket, exposes ports, or shares builder caches.
The test network is internal. Existing public-PR runner trust remains unchanged.

Local `wctl run-stubtest` uncovered undefined `Optional` in two WEPP property
annotations. Replace these with the surrounding stub's `float | None` spelling.
The generated mirror predates these properties and was not involved in the
failure. Local rerun passes all eight default modules. `wctl check-test-stubs`
passes. Documentation lint passes for all three changed Markdown files.

The workflow also places `wctl check-test-isolation` under a 20-minute job
timeout. Its defaults perform five full-suite iterations followed by per-file
executions. Local invocation reported no randomization plugin; it was interrupted
after scope inspection, without claiming a pass. Runner restoration must address
this workload/timeout mismatch explicitly, retaining isolation validation rather
than silently removing it from acceptance. No test fixture or isolation behavior
was changed in this follow-up.

Runner qualification: 648 tracked LFS assets pass materialization and fsck;
77 PostgreSQL/catalog/NoDb tests pass in 25.74 seconds. Two workflow-generator
regressions pass. Generator freshness, changed-file exception enforcement,
Markdown lint and diff whitespace checks pass. Full Forest and full isolation
results remain pending; no random-order coverage is claimed.

### Hosted workflow checkpoint

Source integration `db903ce0e` started run `38762839809` on runner-02, proving
label matching. Its checkout downloaded all LFS objects (`git lfs fsck` passed)
but left 648 pointer files; materialization verification correctly blocked the
job before runtime startup. The follow-up explicitly runs `git lfs checkout`
before verification. Cleanup now requires successful wctl installation, so an
earlier preflight failure does not produce an unrelated missing-command error.
The direct full-isolation qualification was stopped and its disposable stack
removed when hosted acceptance started; no isolation pass is claimed.
