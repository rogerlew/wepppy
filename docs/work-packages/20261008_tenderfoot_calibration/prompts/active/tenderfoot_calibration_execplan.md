# Tenderfoot ET sensitivity trials

This living ExecPlan follows `docs/prompt_templates/codex_exec_plans.md`.

## Purpose

Determine whether lower vegetation transpiration demand materially improves the observed streamflow volume deficit in `cultivated-ubiquity` on openwepp.org. Run exactly two initial forks, with forest basal crop coefficient (`kcb`, the vegetation coefficient used by the evapotranspiration calculation) 0.80 and 0.65 versus baseline 0.95. These are exploratory values, not validated calibration choices. Preserve the baseline and all other model settings.

## Progress

- [x] 2026-10-08 23:35 UTC: retain baseline artifacts, verify observations and outlet normalization, compute flow and water-balance diagnostics.
- [x] 2026-10-08 23:35 UTC: authenticate with the user-provided PAT and retrieve setup/run discovery, readiness, fork/run schemas, defaults, and errors.
- [x] 2026-10-08 23:37 UTC: submit two fork requests and retain receipts/failure traces; both fail before destination creation.
- [x] 2026-10-08: reproduce absent-credential import failure and apply core WEPP's existing optional-import behavior to four RQ modules; independent static review has no blocking findings.
- [x] 2026-10-09 00:29 UTC: focused regressions, isolated import tests, stub checks, and docs checks pass; full-suite attempt records 10,284 passed, 126 skipped, and a persistent unchanged TTL/catalog timing-test failure.
- [ ] Deploy/verify the import repair through the established cluster workflow and successfully create isolated trial forks; full-suite timing gate remains unresolved outside the patch scope.
- [ ] Modify only forest `pmet_kcb` lookup entries using the existing editor contract; run and verify executable inputs.
- [ ] Retrieve fresh outputs, compare matched daily metrics and annual model balances, and document limitations and next experiment.

## Context and orientation

Source URL: `https://wc.openwepp.org/weppcloud/runs/cultivated-ubiquity/disturbed9002_wbt/`. The file server is `hpc`; source directory is `/tank/kubernetes/weppcloud/weppcloud-wc1/pvc-d4c5528b-3204-438b-909a-61af286d6fea/runs/cu/cultivated-ubiquity`. Remote work is confined to forked runs through existing service APIs; SSH reads inspect artifacts. The PAT is `~/open-wepp-org-weppcloud-pat.jwt`; read it privately into request headers, never print or persist its value.

Retained baseline and analysis script are in `papers/2026-weppcloud-scenarios-and-contrasts/data/tenderfoot-experimental/calibration/cultivated-ubiquity/`. The ignored raw snapshot is partial. `diagnose.py` verifies the 4,142 accepted dates and outlet flow against channel output, then generates metrics and a hydrograph. Winter gaps prohibit interpreting matched yearly sums as annual observed yield.

## Milestones and concrete steps

First preserve API receipts under the calibration evidence directory. Discover operations from `https://wc.openwepp.org/rq-engine/api` with the PAT, following `.codex/skills/rq-agent-operator/SKILL.md`. Fork with `undisturbify=false`, `skip_wepp_runs_output=true`, and `skip_omni_scenarios_contrasts=false` (this source has no Omni mod), after checking route availability. Poll job status/info until the fork's children finish. Record the returned destination ID; never infer success from parent status alone.

For each fork, use the existing Flask disturbed `api/disturbed/lookup_snapshot` and `tasks/modify_disturbed` routes. Preserve all rows and columns except `pmet_kcb` for `luse=forest`. Send the current lookup SHA as `if_match_sha256` and use the established browser CSRF mechanism. If authentication prevents this, stop the dependent mutation and report the precise missing contract rather than editing live files directly. Re-read the lookup to confirm the exact intended edit.

Read the fork's pipeline/readiness and run-specific run-wepp schema/defaults/errors. Submit `run-wepp` with the baseline soil choices explicitly preserved: `clip_soils=false`, `initial_sat=0.75`; discovery defaults incorrectly suggest clipping for this completed baseline and must not be blindly applied. Persist request and response. Poll with intervals that permit regular user updates. Inspect child job trees and generated outputs rather than treating the orchestration root as proof.

Verify all 322 entries in `wepp/runs/pmetpara.txt` carry the trial `kcb` and unchanged `rawp=0.8`. Compare prepared climate, soil, management, snow, and groundwater artifacts to baseline; explain harmless provenance differences and reject scientific input drift. Retrieve outlet `chanwb.parquet` and `totalwatsed3.parquet`, then compare on the original observation dates using the same area convention. Save daily NSE, correlation, volume bias, monthly flow means, and modeled annual P/ET/Q. Rebuild Observed results through its existing route if authenticated access permits; otherwise label inherited report artifacts stale and publish the independently computed comparison clearly.

## Validation and acceptance

Success means the two scientific sensitivity trials have known consumed inputs and fresh outputs, with a reviewable comparison and preserved baseline. It does not mean good model fit. Inspect hydrograph shape alongside volume error: the baseline's 2012 peak occurs 22 days early. Hold out years before any later claim of calibrated predictive skill. Run scoped Markdown lint and direct analysis checks; no application code changes or broad test suite are needed.

## Compatibility and recovery

This is an additive experiment: existing CSV keys, NoDb schemas, and defaults remain unchanged. The only intended trial input change is forest `pmet_kcb`. Preserve original lookup snapshots and use version-conditional edits. Record fork IDs before retries because fork is not idempotent. After ambiguous submission, inspect receipts/job state before repeating. Never delete baseline artifacts, change access settings, or reset unrelated work. Do not merge/promote selected model parameterization without its ADR.

## Surprises & Discoveries

The disturbed preparation path overrides the generic WEPP coefficient with lookup values. All baseline prepared entries are 0.95/0.8. Climate header station location/elevation differ from the watershed and the duration header says 100 years although daily rows cover 26 years; effects on model calculations remain unaudited. The baseline soil controller disables clipping although the endpoint's defaults suggest clipping.

Both fork jobs failed at import: `project_rq` imports `wepp_rq`, whose finalize module imports the Discord client, which opens missing `/workdir/weppcloud2/weppcloud2/discord_bot/.bot_token`. Destinations `overall-thruster` and `tacky-seeking` do not exist. This is a worker dependency/configuration failure, not a PAT or calibration failure.

The user clarified that Discord must not be a hard dependency. The smallest repair is to mirror existing core WEPP handling for missing/unreadable optional credentials in the four RQ import sites. A subprocess regression reproduced the failure before patching; the initial focused suite passes. This is an import-only repair, not a change to notification delivery or job-completion semantics.

## Decision Log

2026-10-08, Codex implementing the user's run-calibration request: use two isolated lower-kcb forks to test the dominant water-balance deficit; avoid simultaneous soil/snow/baseflow tuning so the effect is attributable. No final coefficient is selected. Keep observed normalization at the documented 22.8 km² literature area pending a boundary audit.

## Outcomes & Retrospective

Baseline diagnosis and authenticated API discovery are complete. Both fork submissions failed before parameter edits or model runs. See `trial_jobs.json` and the two retained job traces in the baseline evidence directory. Hash readback confirms baseline `wepp.nodb`, `soils.nodb`, `climate.nodb`, `pmetpara.txt`, and observations remain unchanged. Trials are blocked pending deployment and verification of the optional Discord import repair; no calibration improvement can be claimed.

Recovery amendment: deploy and validate the bounded optional-import repair rather than adding a Discord token. Production validation remains pending; no calibration improvement is claimed. See the conformance artifact for test results and review scope.

Local validation outcome: focused tests and independent review pass. The full suite stopped at an unchanged TTL/catalog p95 performance gate, which also failed alone; its threshold and implementation were left untouched. The import repair is not yet deployed, and fork trials remain blocked on the live worker version.

Revision: initial plan, 2026-10-08, to make the bounded experiment and artifact checks explicit before mutations.

Revision 2026-10-08 23:37 UTC: retain import-failure evidence, clarify the unused Omni flag, and record the external blocker without changing infrastructure or fabricating trial outcomes.
