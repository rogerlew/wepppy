# Forest restart and Thomas Fire M1 rerun

## Purpose and scope

Execute the user's authorized forest stack restart and a fresh nervous-mesquite M1
assessment, then verify the Kf-backed report and preserved inputs. This is live
operational acceptance of implemented behavior, not a model revision or deployment
to production. Maintain this plan according to docs/prompt_templates/codex_exec_plans.md.

## Progress

- [x] Confirm forest, installed development wctl preset, existing M1 acceptance, and idle queues.
- [x] (2026-09-17 03:29Z) Preserve and verify 524 files in a unique run archive.
- [x] (2026-09-17 03:30Z) Restart stack; web/preflight HTTP 200, healthy databases/download, fresh workers.
- [x] (2026-09-17 03:32Z) Fresh M1 completed; browser curves, labels, exports and reload passed.
- [x] (2026-09-17 03:33Z) Independent numerical, publication, runtime fingerprint and preservation checks passed.

## Context and compatibility

Work from /workdir/wepppy. The run is /wc1/runs/ne/nervous-mesquite and its UI is
https://wc.bearhive.duckdns.org/weppcloud/runs/nervous-mesquite/config/.
Existing accepted attempt is 0ea9c1f5b0964b22ba7f1b457c1a6c9f.
Kf means fine-earth soil erodibility; the approved source is NRCS-derived STATSGO.
Only a new module-owned attempt and normal lifecycle state may be written.
Do not rebuild soils, rainfall, terrain, SBS, or dNBR. Keep prior attempts immutable.
Regression proof compares protected file hashes and independently checks new tables.

## Milestones and concrete steps

First reuse protect_run.py and validate_live.py from the closed
20260916_postfire_kf_report_revisions package in this package's artifacts directory.
Run protect_run.py before, archive every inventoried protected and module file plus
module state, and verify ZIP bytes before mutation. Preserve archive path and hash.

Next recheck default, batch, and fork-archive queues using read-only Redis queries.
Run wctl restart, record container startup/health and worker registrations, and test
public web/report endpoints. Do not run production deployment scripts or flush Redis.

Finally run node artifacts/browser_e2e.cjs nervous-mesquite config from this package.
It uses the existing dev-agent account, normal CAPTCHA login and browser run button.
Run wctl run-python on artifacts/validate_live.py nervous-mesquite and run
protect_run.py after. Retain JSON, CSV, screenshots and command logs in artifacts.

## Validation and acceptance

Require a fresh completed job and attempt, current schema-3 Kf-backed results,
independent agreement for event/design/inverse probabilities and all curve CSV rows,
15/30/60-minute curves, SI/English display, NOAA modeled/disaggregated labels,
downloads, source browsing, and stable accepted attempt after reload.
Protected science inputs and earlier attempt files must be unchanged.

## Idempotence and recovery

Never overwrite earlier evidence. If a browser check fails after submission, inspect
the recorded job and use resume mode instead of submitting duplicate work.
If preflight exits during Redis loading, verify Redis health then restart preflight.
Retain failed artifacts. Do not restore over the live project without diagnosis.

## Surprises & Discoveries

The installed rq-info --detailed option is unsupported; its wrapper also rebuilds
worker registry metadata. Subsequent queue checks use direct read-only queries.
The shared checkout contains unrelated D-Tale work, which remains untouched.
The generic endpoint discovery catalog omits post-fire operations and its schema
lookup fails. The first browser probe stopped before any submission. Its evidence
is retained under artifacts/browser/discovery-failure. The registered OpenAPI route
and existing browser controller were used for the successful normal UI submission.

## Decision Log

2026-09-16: Record new acceptance separately because closed work packages are immutable.
Restart the existing development stack without pulling, resetting, rebuilding,
or changing configuration; the user authorized restart and this named rerun only.

## Outcomes & Retrospective

Complete. Job 7583d48c-014f-46e8-9e55-cb09f948f68c finished on a restarted worker;
accepted attempt b9b523bda3f34ca684b7790145d4e43c is current after reload. All 8,082
saved probability rows and 416 curve CSV rows passed independent coefficient checks.
All prior attempt files and 387 protected scientific inputs were preserved;
climate.nodb changed only its serialization timestamp. No product code was changed.
The generic discovery-catalog gap is an operator ergonomics follow-up, not a failed
M1 execution. See ../../artifacts/acceptance.md for detailed acceptance evidence.

## Artifacts and dependencies

Reuse installed Playwright and existing Python/raster tooling; no new dependencies.
Artifacts live in this package; the baseline ZIP lives in the run's archives directory
so it is browsable and recoverable without embedding large binary inputs in Git.

Revision 2026-09-16: closed live verification with fresh job and preservation evidence;
retained the discovery failure and documented the explicit browser-path recovery.
