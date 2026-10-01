# Forest deployment run sheet

Operator authorized steps 1–5 through gated read cutover, not another host or
promotion. Forest's actual account/project scope replaces the unavailable
805-run host fixture; representative scale remains required before wepp1
cutover. Controlled requests replace organic traffic. The 48-hour observation
and complete reconciliation gates remain pending.

## Candidate and preparation

- Candidate: `3e6cbdcb9`; forest, installed development `wctl` preset.
- All registered workers were idle; default/batch/high/low queues empty.
- Four batch consumers shared local container hostname `92d5878256d7`;
  six default consumers and one fork/archive consumer were also local.
  No remote companion was registered at inventory time.
- Initial migration: `c91f6b2a4d7e`; candidate head: `d30c91a7b802`.
- Fresh backup: `/backups/weppcloud-pre-run-catalog-20261001T023136Z.dump`,
  705 KiB, `pg_restore --list` passed, permissions restricted to 0600.
  This verifies archive readability, not a completed restore rehearsal.
- Static build passed with repository virtualenv on PATH. Initial host-Python
  attempt lacked Jinja2; no dependency was installed or runtime changed to
  conceal that environment issue.
- Plain `flask db` cannot discover this app from the container workdir. Use
  `flask --app wepppy.weppcloud.app db`; operations guide corrected.
- Recreated web, rq-engine, default/batch/fork-archive workers and scheduler
  with staged defaults. No Redis queue flush or unrelated service restart.

## Shadow deployment

Migration completed at `d30c91a7b802`. Catalog writes are enabled in forest's
gitignored `docker/.env`; reads remain legacy. The `run_catalog` task is enabled
as a forest-local, uncommitted change in `docker/scheduled-tasks.yml`; do not
promote that activation setting to another host. Scheduler was restarted after
consumer proof. Other services were recreated to load write-mode settings.

After recreation, four local batch workers (PIDs 359–362, container
`030247b7d6fc`) were probed using each actual `/proc/<pid>/environ`, the adapter
and separate SQL transactions. All returned held-acquired false, control-acquired
true, matches-origin true while the coordinator transaction retained its lock.
Coordinator/probes ended explicitly. All ran UID 1000/GID 993/groups 993/umask
0022. Web/rq-engine/default/batch/fork-archive share approved `/wc1` and
`/wc1/geodata`→`/geodata` mounts and UID/GID. An earlier staging proof was
invalidated by recreation and repeated; it is not the activation witness.

Bounded backfill covered 463 registrations: 95 ready, 368 missing Ron/TTL,
zero pending/dirty/transient errors. All 463 individual source comparisons
matched with no inconclusive result. See the retained
[omission manifest](2026-10-01_forest_omissions.json). No registration or project
was deleted to improve these counts. The database also contains test accounts;
this does not imply ten active human users.

Actual Chromium login passed using the existing dev-agent credentials and
canonical CAPTCHA challenge helper. The principal account scope (alias 1)
returns 85 projects on each of catalog with Ron metadata, map-data and JSON
runs. Every legacy payload key/value matched the shadow SQL reader; SQL counts
141 unavailable registrations in that authorized scope. Legacy map rendered a
canvas. Credentials/session state are private temporary files, not artifacts.

Technical preflight passed with four compatible consumers and a completed
scheduled sweep. One earlier check correctly held while an overlapping compare
made the last sweep busy; the next scheduled completion cleared that condition.

Created owned smoke project `grating-implementation` through the real rq-engine
create endpoint, stored profile token and required random idempotency key.
No user project was used for mutation tests. Initial requests using the legacy
test-only preset or missing idempotency key were rejected without creation;
the supported `disturbed9002` request returned 303.

## Cutover and remaining gates

At approximately 02:45 UTC, forest's web process was recreated with postgres
reads; batch workers were not restarted, so their connection/mount witnesses
remain valid. Post-cutover technical preflight passed with 465 projected
registrations, 97 ready, 368 explained missing, no dirty/pending/transient
errors, four compatible consumers and healthy scheduled sweeps.

Actual authenticated HTTPS responses on all three surfaces exactly matched
every legacy field for the 85-project principal scope. Each surface passed
100 sequential requests plus four concurrent readers making five requests
each. Catalog p95/p99: 66.01/81.46 ms; map-data: 56.02/68.85 ms;
JSON runs: 57.86/60.15 ms. These measure full response retrieval through the
local host's public HTTPS address, warm processes; not remote WAN latency or
805-project performance. Table navigation reached network-idle in 1.31 s,
rendered rows, and the actual map showed basemap/labels and 63 mapped projects.
No page JavaScript errors occurred. See
[HTTP/browser evidence](2026-10-01_forest_http_browser.json).

Live SQL reader checks with project-path open/stat guards observed zero project
filesystem calls for both full and map payloads. The actual completed catalog
job tree and anonymous single/batch polling returned only the redacted envelope,
with no paths, results or exception details. Real RQ maintenance job
`41ef5035-25f5-4970-bfb1-5387ff60f9ee` finished successfully; source/SQL parity
for both witness projects passed afterward.

A post-cutover web rename to `Forest catalog cutover verified` appeared as a
current SQL-backed authenticated catalog row in 10.47 s and was visibly rendered
after browser reload. This completes the live file→SQL→HTTP→browser witness,
not merely an assertion on a finished job or database row.

Steps 1–5 are complete. Keep the two dev-agent projects as observation witnesses.
Rollback rehearsal, sustained model-load impact, database-blackhole budget,
complete elapsed reconciliation recovery and >=48 healthy hours remain host
acceptance gates. No background acceptance monitor was installed or launched;
the existing scheduler alone continues normal catalog maintenance. No other
host deployment or promotion occurred. Preserve polling redaction on rollback.

## Producer witnesses

On the new owned smoke run, actual authenticated HTTP mutations propagated
through persisted files and scheduled catalog publication: name 10.45 s,
READONLY true 15.96 s, READONLY false 13.05 s, TTL disabled 13.15 s and rolling
13.26 s. Each assertion required an advanced indexed revision, matching dirty
revision and the expected value. READONLY operations executed as real default-
queue jobs; markers and TTL are read back by the data-only extractor.

Real fork/archive worker jobs created `synaptic-left`, wrote a 56-member ZIP
with Ron (CRC validation passed), and restored that archive. Job IDs:
`6788ac70-0234-4d95-9397-0d9a6e07cd74`,
`47609693-1b13-4b73-b3a1-d1dba63e23d1`,
`05eac6e7-3ab9-4f54-9f9a-0b99e7c48232`. Both projects' actual Ron/TTL files
exist and source/SQL comparisons match. A real maintenance `run_paths` migration
on the smoke run succeeded and advanced its dirty revision. No scientific
model computation/output parity is claimed for these fresh metadata-only runs.

Remote import/sync and Omni-specific branches retain isolated regression
evidence, not a new live remote-host claim. No remote sync producer or companion
was observed active; no additional host was authorized or changed. These
branches share the initialized worker boundary but need workflow-specific
host witnesses during subsequent acceptance if exercised.
