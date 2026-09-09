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
- [ ] Inventory actual corrupted runs and active jobs.
- [ ] Ratify/commit the map contract and API compatibility amendment after reviews.
- [ ] Fix property/parser and omit display-only form submission; add regression tests.
- [ ] Validate and apply bounded live remediation with backups.
- [ ] Complete broad checks, independent reviews, and outcome/rebuild record.

## Surprises & Discoveries

- The recent display patch is deployed, but server-side map assignment remains.
- A canonical API document currently tells callers to submit the map. This
  must be amended explicitly before removing its authority.

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

Pending. This plan governs only this incident, not the other active work packages.

Plan created 2026-09-09 after confirming the deployed assignment path.
