# Resumed scientific acceptance — October 26

Status: **local scientific, artifact and report acceptance passed at 21:38:50 UTC**. Operator selected
`wepp_261021` to address the earlier SOURCES3 date mismatch. Production async
remains disabled. [Production preflight](20261026_production_preflight.md) records
separate identity, mount, publication, lock and capacity evidence.

## Isolation and compatibility

Preserved failed case `/wc1/runs/qc/qcat-mill-creek-20261023`. Created independent
copy `/wc1/runs/qc/qcat-mill-creek-20261026`, excluding model runs/outputs, reports,
Roads outputs, archives, catalog/admission state, run logs, manifest and prior
validation artifacts. Canonical fork helpers rebased 14 NoDb files and cleared
inherited job markers. Scientific settings retain 184 years and 1,908 hillslopes;
only the selected WEPP executable changes. No existing project schema migration.
Copy hashes and release metadata reside in `qcat-validation-copy.json` in the new
case. Real local PostgreSQL ownership is the dedicated dev-agent account.

`tools/check_wepp_binary_provenance.sh wepp_runner/bin/wepp_261021
wepp_runner/bin/wepp_261021_hill` passed. Watershed executable SHA256:
`e2c83b1a691fad3ffe29acf1588dadbecfeec9b027391df8b7fddcf4908d2971`.
Release metadata requires regeneration of both hillslope and watershed products;
the fresh pipeline does both. No old model output is accepted as new evidence.

Process-local async configuration uses namespace
`qcat-mill-creek-acceptance-20261026`, root `/wc1/runs` with sharded layout, and
external coordination `/wc1/query-catalog-validation/20261026/mill-creek-locks`.
Real Redis/RQ queues `qcat-mill-creek-model-20261026` and
`qcat-mill-creek-catalog-20261026` isolate acceptance from shared consumers.
Worker identity is the existing local uid1000/gid993 on NFS, with eight model
CPUs. This local workflow does not alone prove full production identity parity.

## Submission and strict recovery

Actual run-wepp FastAPI route: unauthenticated 401; scoped authenticated request
200 in **0.950684 seconds**, selecting `wepp_261021`. Root job:
`cfddc361-6e18-497f-becf-66d8fe496cbd`. Submission receipt is retained as
`qcat-validation-submission.json`. Model worker started **17:29:04 UTC**;
preparation jobs are executing through normal dependency wiring.

The initial copy omitted exclusion of generated `wepp/reports`. Its inherited
zero-byte `hillslope_watbal_summary.attempts/.../native.parquet` correctly failed
strict catalog schema verification. Failed refresh
`query_catalog_refresh_5d02a036-ca8b-4e16-8efa-d17e0efcaa40` retained its receipt.
Moved only the new clone's generated reports to
`/wc1/query-catalog-validation/20261026/inherited-wepp-reports`; the original failed
case remains intact. Updated the copy manifest to record the quarantine.

Normal retry `query_catalog_refresh_c77f7fc2-4cd5-4a00-a9ff-cd53ca8bd823` completed
at **17:25:27 UTC**, published a readable catalog and acknowledged receipt
`a9755b80-de90-4cbd-b636-2c3d9838f544`. Pending count became zero; the single model
job remained queued. No duplicate model submission or relaxed validator.

## Evidence and pending validation

Local operator logs: `/tmp/qcat-261021-provenance.log`,
`/tmp/qcat-20261026-copy.log`, `/tmp/qcat-20261026-prepare.log`,
`/tmp/qcat-20261026-submit.log`, `/tmp/qcat-20261026-recover.log`, and
`/tmp/qcat-20261026-worker.log`. Harness scripts use matching
`/tmp/qcat_20261026_*.py` names. Worker executes a real file inside the web
container so spawned model processes can import its entry point. It retains job
results for one day without changing model timeouts or scientific settings.

Harness sources and SHA256 manifest are retained under
`/wc1/query-catalog-validation/20261026/harness`. A running scoped supervisor
observes `qcat-validation-pipeline.json`, requires every recorded job to finish,
then runs raw daily checks on three hillslopes, strict all-hillslope water-balance
reports, final artifact queries and authenticated report/download checks. It
never resubmits or repairs jobs. Durable state is
`/wc1/query-catalog-validation/20261026/acceptance-supervisor.json`; diagnostic log
is `/tmp/qcat-20261026-supervisor.log`. A failure is retained and stops validation.
Its success label covers only these local checks, not production rollout or
interactive browser login. One climate input was independently checked: 184
years, 365 days in year 100, 366 in year 104, no February 29 in year 100.

Independent harness review found four gaps before completion: missing child jobs
were skipped, empty raw samples could pass, three samples did not prove complete
daily coverage for every hillslope/OFE, and host-only timeouts could leave a
container validator running. The revised harness rejects missing jobs, requires
watershed/interchange/finalizer identities, rejects empty raw samples and checks
OFE identities against generated slope inputs. An additional projected Parquet
scan checks every profile for all 67,205 unique Gregorian daily keys, rejecting
nulls, gaps, duplicates and unexpected identities with bounded bitmap memory.
Container-side timeout now terminates the owned validator process group before
the outer command deadline. Syntax checks passed; a negative missing-child probe
was rejected. Independent recheck confirmed closure of all harness findings; actual completion checks remain pending.

Follow-up review also identified the watershed `pw0.slp` matching the hillslope
glob and a possible partial checkpoint read. Numeric hillslope filtering now
excludes `pw0.slp` (verified against the old case: exactly 1,908 selected).
Supervisor retries incomplete JSON for at most 30 seconds, then fails rather
than accepting malformed evidence. The running model was not interrupted.
Effective `Wepp.delete_after_interchange=False` preserves the raw validation
samples even though the climate fallback setting is true.

Remaining: all hillslopes and watershed completion, raw daily calendar/uniqueness,
interchange and finalizer products, catalog convergence, strict water-balance and
loss reports, authorized report/download semantic readback, and full workflow
production parity. Job success alone will not satisfy these gates.

Early raw-output check at 17:36 UTC: new `H1.wat.dat` has **67,205 unique daily
records across all 184 years**, with complete Gregorian day counts in every year
(including years 100 and 104). This first-hillslope check passes where the old
case duplicated dates. It does not establish watershed or full-run completion.
Retained result: `/wc1/query-catalog-validation/20261026/early-H1-raw-dates.json`.

Independent correctness reviewer confirmed all six harness findings closed at 17:41 UTC; all 11 retained/live script hashes match. This reviews validation logic only and does not mark the running model accepted.

## Terminal acceptance and remaining rollout scope

At 2026-10-26 21:38:50 UTC, all 18 recorded jobs were finished and all five
supervisor checks passed. All 1,908 hillslope/OFE profiles contain exactly
67,205 unique Gregorian days over 184 years (128,227,140 daily rows). Watershed,
interchange, strict water-balance and loss reports, authenticated report/CSV
consumers and exact-byte live downloads passed; pending receipts were zero.
Compact machine evidence is retained in [terminal acceptance](20261026_terminal_acceptance/acceptance-supervisor.json)
and its adjacent JSON files. The real authorized Flask session was seeded by the
validation harness; interactive login/CAPTCHA was not exercised.

This supersedes the chronological pending statements above. Local identity was
uid1000/gid993, so it does not replace production identity/mount/queue parity.
The operator subsequently requested completion of remaining rollout gates.
Production lock latency, complete inventory/reconciliation capacity and explicit
fleet namespace parity are being measured before enabling async production.
