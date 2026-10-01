# Run catalog: integration and staged operations

The [canonical contract](../schemas/run-catalog-projection-contract.md) governs
this feature. Candidate implementation passed isolated validation. **Do not deploy or
activate from this document alone.** The operator now authorizes forest steps
1–5 through gated read cutover; host promotion remains pending observation.
Host order is forest → forest1 application → wepp1.

## What users see after explicit cutover

Runs table/map metadata comes from PostgreSQL rather than walking projects.
Files remain authoritative. Changes normally appear within 60 seconds of a
notified save, not immediately. Last-good rows remain visible with “metadata
updating”; pending and unavailable projects are counted separately in an
accessible status message. Missing/invalid Ron omits that project. Unknown or
stale TTL never displays a guessed deletion date. A database failure is an
explicit request error, not a silent return to a slow filesystem scan.

Sharing, Admin/Root alias rules, sorting, project actions, file access and TTL
policy do not change. Catalog counts are scoped to the authorized selection.

## Developer integration

`wepppy.nodb.persistence_events` is the portable, primitive-only observer seam.
No observer means no deployment import or I/O. Call
`initialize_project_commits()` at an explicit deployment process boundary;
the library default remains disabled. Successful NoDb replacement notifies even
if later ancillary work fails. Observer failures cannot undo saved files and
produce bounded logs with PID/source/time and process failure count.

The deployment adapter validates modes/secrets/driver without connecting at
startup. It reuses fork-safe pools, preserves last-modified timestamps for all
NoDb controllers, and invalidates catalog metadata only for Ron or explicit
READONLY/TTL/lifecycle events. Registration seeding shares the ORM transaction.
Do not import Flask or SQLAlchemy into the portable seam, replay metadata event
values, add per-save jobs, or use the catalog as project persistence.

Other `_pups` retain their existing parent timestamp mirror without projecting
their Ron onto the parent. Supported Omni children have their own source
identity while preserving parent modification semantics. File-only/offline
maintenance remains supported and is repaired by reconciliation; initialize and
notify explicitly if its workflow needs the notification freshness target.

The existing broad `wepppy.nodb` convenience import already reaches Flask via
BatchRunner/helpers. This change does not expand or remove that preexisting
framework dependency. The seam itself has no web/database dependency; actual
standalone saves are tested with the deployment app, SQLAlchemy, database driver
and adapter unavailable. Do not confuse that with a claim that all existing
NoDb convenience exports can import without Flask installed.

## Safe defaults and commands

Deployed presets explicitly stage with:

```text
WEPPPY_PROJECT_COMMIT_MODE=postgres
WEPPCLOUD_RUN_CATALOG_WRITE_MODE=timestamp_only
WEPPCLOUD_RUN_CATALOG_READ_MODE=legacy
```

The `run_catalog_sweep` schedule remains disabled. These defaults preserve the
modification mirror before the new schema exists. A library/offline environment
defaults to disabled integration. Do not enable postgres reads with timestamp-only
writes. Catalog reads do not activate the scheduler.

After separately authorized candidate staging and additive migration:

```bash
wctl exec -T weppcloud python -m wepppy.weppcloud.run_catalog status --json
wctl exec -T weppcloud python -m wepppy.weppcloud.run_catalog seed --limit 50 --json
wctl exec -T weppcloud python -m wepppy.weppcloud.run_catalog seed --limit 50 --apply --json
wctl exec -T weppcloud python -m wepppy.weppcloud.run_catalog reconcile --limit 50 --apply --json
wctl exec -T weppcloud python -m wepppy.weppcloud.run_catalog compare --run-id 123 --json
wctl exec -T weppcloud python -m wepppy.weppcloud.run_catalog preflight --json
```

Replace `123` with an existing registered integer ID; no command accepts arbitrary
project paths. `refresh` requires `--run-id`; mutating commands default to dry-run.
Repeat bounded backfill until coverage is complete. Compare reports `match`,
`different`, or `inconclusive` plus unreadable sources; inconclusive is not parity.

Status includes SQL row counts/ages and the latest completed sweep's attempts,
failures, source-read time, SQL acquisition/publication time and total elapsed
time. These are last-sweep samples, not cumulative service counters. Use existing
logs for per-process notification counts and `project_commit_mirror_completed`
elapsed time. Protect operator output; it is not a public API.

## Mandatory stage run sheet

Maintain a sheet naming host/preset, candidate revision, modes, Alembic head,
all producer and eligible consumer identities, mounts/groups/umask, evidence
timestamps and operator disposition. Begin from the package's
[producer inventory](../work-packages/20260930_run_catalog_projection/artifacts/producer_inventory.md).
Machine `technical_ready=true` and exit zero are **not release authorization**;
`gate_status=operator_evidence_required` always remains explicit.

1. **Candidate staging:** inspect `docker/README.md` and
   `scripts/deploy-production.sh` under the installed target preset. Preserve
   canonical pull/build/static/Redis/health/active-job handling; no alternate
   registry, image or raw Compose workflow. Preserve legacy reads and
   timestamp-only writes. Inspect the candidate Alembic head before the existing
   `wctl exec -T weppcloud flask --app wepppy.weppcloud.app db upgrade`
   schema-install step. Never drop data.
2. **Before sweep admission:** verify every eligible batch consumer supports the
   callable, exact reserved IDs and public redaction, has job-origin SQL and
   approved source mounts. Configuration hashes are hints only. An incompatible
   companion blocks activation; deploying forest1 application does not update
   its forest companion automatically. Resolve additional-host authority first.
3. **Connection-bound proof:** in a dedicated origin-adapter SQL transaction,
   generate two distinct fresh signed-bigint nonces; acquire an exclusive
   `pg_try_advisory_xact_lock(bigint)` on the held nonce and retain that
   transaction. From each consumer's actual environment/credentials, run its
   adapter's separate connection through `service.probe_origin`, or CLI
   `preflight --held-nonce <held> --control-nonce <control> --json`. Require
   held-acquired false and control-acquired true while the origin lock is
   demonstrably retained. Always end probe transactions, including on failure.
   Errors, wrong/control results or coordinator loss mean HOLD. Record actual
   results, not matching URI strings or operator-supplied substitute DSNs.
4. **Shadow/backfill:** after consumer proof, enable catalog writes and the
   existing 15-second batch task explicitly while reads remain legacy. Classify
   every registration; unresolved transient errors block cutover. Retain an
   omission manifest for known missing/invalid Ron and semantic comparisons.
   Prove real web, RQ, maintenance, readonly and TTL mutations through file →
   SQL → authorized JSON/browser under production-equivalent identities/mounts.
5. **Read cutover:** require technical checks plus the retained initialization,
   scope, source/mount, comparison and omission witnesses. Explicitly select
   postgres reads; verify both browser views, not only job SUCCESS or SQL rows.
6. **Host promotion:** retain >=100 authenticated sequential requests per surface
   plus concurrent readers, browser/TTFB/payload/cache state,
   notification overhead, queue impact, full 24-hour reconciliation and >=48
   healthy hours. Forest1 additionally requires two no-argument canonical
   deployments and existing login/CAPTCHA/RQ/DEVAL/rollback checks. Only then
   promote to the next host. Tests are not a substitute for these elapsed windows.

Forest uses its actual single-account project scope and controlled traffic;
an unavailable 805-run dataset is not its acceptance gate. Keep isolated scale
evidence separate. Validate representative host scale at the first stage with
that dataset, before wepp1 read cutover if unavailable earlier. This avoids
inventing forest load evidence without waiving correctness, worker proof,
reconciliation or the 48-hour observation window.

Restart, candidate/configuration/mount changes or eligible membership changes
invalidate affected witnesses. Revalidate before resuming admission. Old
non-consuming writers need an explicit reconciliation/freshness disposition;
their historical missed last-modified timestamps are not reconstructed.

## Recovery and rollback

Keep the additive table and dirty work. First stop catalog admission and use
existing queue tooling to drain/cancel only catalog jobs before an incompatible
worker rollback. Reserved-ID cancellation requires Admin/Root; normal job
authorization is unchanged. Never clear unrelated queues. An aborted per-run SQL
transaction cannot publish; losing the separate coordinator cannot hard-cancel
blocked NFS reads or atomically fence another transaction's commit. Investigate
lost coordination before restarting admission.

Read rollback explicitly selects legacy mode and restores its old latency.
Retain reserved-job polling redaction for the complete lifetime of queued and
terminal catalog records—even after draining. Reverting that protection to the
old serializer while private failure records remain is not a safe rollback.
Retest anonymous single/batch/recursive polling after rollback. Keep source
files authoritative; never restore project files from catalog values.
