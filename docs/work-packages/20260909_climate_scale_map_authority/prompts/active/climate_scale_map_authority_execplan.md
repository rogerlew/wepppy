# Repair immutable climate scale maps on wepp1

This living ExecPlan follows `docs/prompt_templates/codex_exec_plans.md`.

## Purpose and context

Restore Marta's Portland MOFE climate configurations and prevent another browser
submission from replacing a configured raster path with a scalar string. The
source boundary is `wepppy/nodb/core/climate_input_parser.py`; its parser writes
form values under a NoDb lock. `climate.py` currently reads the persisted map,
and `templates/controls/climate_pure.htm` renders a named read-only field that
`controllers_js/forms.js` includes in payloads. The canonical run filesystem
on wepp1 is `/geodata/wc1/runs/<prefix>/<runid>` on host, `/wc1/runs/...` in containers.

## Progress

- [x] Inspect deployed parser/template and identify owner account/family.
- [x] Inventory 14 owner runs: four corrupt, nine correct, one absent; verify failed RQ jobs.
- [x] Ratify/commit contract checkpoint `acf04419c` after two independent reviews.
- [x] Fix property/parser and omit display-only submission; focused Python/Jest tests pass.
- [x] Real worker raster/CLI/WEPP-prep canary passed; four live records repaired with backups.
- [x] Disk/cache inventory and repeated-repair no-op verified.
- [ ] Activate matching code in request handlers and RQ workers.
- [x] Complete broad checks (8,145 passed), independent reviews, and outcome record.
- [ ] Recheck/re-repair after new live submissions and matching code activation.

## Surprises & Discoveries

- The recent display patch is deployed, but server-side map assignment remains.
- The API document previously told callers to submit the map; its amendment
  was ratified before implementation.
- RQ workers replay build payloads, so request-handler-only deployment leaves
  an old worker capable of restoring the poison value.
- The first broad suite exposed a route-test dummy missing the real map property;
  the fixture was corrected and all 21 climate route tests passed.

## Decision Log

- Preserve existing configuration precedence; do not reinterpret Daymet and
  Gridmet selection or scalar/monthly values during incident repair.
- Ignore the obsolete payload field, including `"1.1"`, while resolving and
  persisting the configured map within the existing parse transaction.

## Milestones and concrete steps

1. Inventory through the WEPPcloud database and raw run JSON; record only
   relevant owner/run/config/map/job metadata, without credentials. Confirm
   expected config resolution and inspect generation/failure evidence.
2. Obtain two independent read-only contract reviews, disposition findings,
   and commit the contract checkpoint. Then make the map property derive its
   value from configuration, synchronize the persisted field during successful
   parses, and disable submission of the existing display field.
3. Run focused parser/property/template/persistence tests, npm lint/tests for
   frontend effects, and `wctl run-pytest tests --maxfail=1`. Exercise the actual
   parser with poisoned payload and confirm generated spatial-scaling input
   uses the configured raster. Apply live changes only with reviewed restart
   scope, backups, identity checks, and active-job checks.
4. Repair confirmed run fields under NoDb locks with fresh state; verify disk,
   fresh reads, cache coherence, and unchanged unrelated/generated artifacts.
   Record whether each failed climate job requires an operator-approved rebuild.

## Acceptance and recovery

An old form carrying `precip_scale_factor_map="1.1"` must not alter the configured
map. Correct values survive parse, atomic dump, and reload. No configured map
means `None`; invalid configuration still fails explicitly. Live inventory
must show the expected Daymet raster on every targeted repaired run. Backups
permit field-scoped rollback after rechecking locks; never restore entire stale
snapshots over subsequent user work. Repeated repair is a no-op for correct fields.

## Outcomes & Retrospective

Four corrupt wepp1 maps were repaired at 2026-09-09 22:19 UTC; all 13 existing
climate files now agree with configuration. Sampled generated files are unchanged.
Spatial builds for seductive-sabra, warming-championship, and asteroid-hindrance
need rebuilding before the next model run. Under-fecundity retained its current
no-scaling mode and later successful climate build. Broad checks passed. New user submissions at 22:32 UTC again carried the poison
map, with newly selected scalar modes that must be preserved. Permanent activation
and repeat repair after active jobs drain are pending. See `artifacts/20260909_live_evidence.md`
and `artifacts/20260909_implementation_reviews.md`.

Plan created 2026-09-09 after confirming the deployed assignment path.

2026-09-09 update: recorded contract checkpoint, implementation, reviewed live
repair, canary, replay deployment dependency, and explicit rebuild disposition.

2026-09-09 follow-up: full suite and real RQ replay regression passed; recorded
new live submissions and the outstanding production job/deployment gate.

2026-09-09 22:52 UTC: canceled two active climate jobs as requested (warming
climate had already completed). Repaired the two stopped runs again, preserving
new scalar settings. Warming model activity blocks its repeat repair; permanent
code activation is still pending. Evidence: live evidence cancellation section.

22:55 UTC: under-fecundity and warming-championship map repairs completed on
explicit follow-up, preserving scalar settings. The under climate job was stopped;
verified non-writing warming model jobs continued. Code activation remains pending.
