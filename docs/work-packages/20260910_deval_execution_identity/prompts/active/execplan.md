# Restore reliable Compose DEVAL access to existing run data

This living ExecPlan follows `docs/prompt_templates/codex_exec_plans.md`.

## Purpose

Existing and newly generated WEPPcloud projects must render DEVAL without manual
permission repair. The accepted scope is the user's September 9 PDT request for
a durable production fix after repeated permission regressions. Execution must
cover worker-owned mode-0600 inputs, preserve report contents and authorization,
and prove fresh output through the deployed worker and renderer.

## Progress

- [x] Confirmed job 2ae73acb-08a7-4894-98c3-f22559cfc336 failed on populated,
  valid soils.parquet, mode 0600, owner 1002:130; renderer 1000:993 plus group130.
- [x] Recovered that job by a one-file chmod and retry; this is mitigation only.
- [x] Confirmed deployed soils writer already publishes 0644; old files remain.
- [x] Selected worker effective UID/GID for Docker exec; independent review agrees.
- [x] Implemented regression, existing deployment check, and operator guidance.
- [x] Validated owner-only legacy data and regenerated data with fresh renders.
- [x] Completed 52 focused tests and independent correctness and QA review.
- [x] Full broad suite passed: 8,194 passed, 77 skipped in 854.71 seconds.
- [x] Applied bounded source correction on both shared-queue production hosts;
  actual queued job and authenticated report readback passed.
- [ ] Commit/push and fast-forward production source checkouts.
- [x] Removed the isolated canary copy after recording reviewed evidence.

## Surprises & Discoveries

The previous group-sharing repair cannot grant access to owner-only files. The
subsequent soils writer repair fixes future publication but cannot correct old
files. Effective wepp1 Compose builds workers with APP_UID=1002/APP_GID=130 and
leaves the renderer image at 1000:993. Loading R/Arrow/rmarkdown as 1002:130 in
the deployed renderer succeeds.

## Decision Log

The unchanged canonical obligation is Common Orchestration Responsibilities in
`docs/schemas/weppcloudr-render-execution-contract.md`: real shared-filesystem
worker-to-renderer execution must succeed. Classify restoration of access to
valid worker-owned inputs as conformance repair, not a report or auth change.
Do not add recursive chmod, periodic retries, or run-specific permission fixes.
Selected Docker exec identity on September 10 UTC: four production Python lines,
trusted process-derived values, no settings or permissions repair. The user
explicitly rejected overcomplication. Do not add a deployment mode or expand to
legacy direct Plumber service migration: that separate path has old output
ownership concerns and is not used by the affected WEPPcloud report workflow.
The existing deployment preflight gains a real owner-only data sharing check.
Security delta is low: use the same authority already creating/reading the run;
no user-supplied identity, root escalation, or route authorization change.

## Context and Orientation

`wepppy/rq/weppcloudr_backends.py` constructs Docker exec; the R adapter is
`weppcloudR/render-compose-request.R`. `wepppy/rq/weppcloudr_rq.py` validates paths,
locks/fences publication, and records logs. `docker/validate-weppcloudr-runtime-contract.sh`
is the existing deployment preflight called by `scripts/deploy-production.sh`.
Tests live in `tests/rq/test_weppcloudr_backends.py` and `tests/scripts/`.
Prior packages 20260821_weppcloudr_execution_backend_refactor and
20260909_deval_soils_permissions are immutable precedent. Preserve unrelated dirty
work in PROJECT_TRACKER.md and the directory-lock package.

## Plan of Work

First prove the proposed effective execution identity can read an owner-only
input and complete R rendering under actual mounts. Then make the smallest
transport/config correction and regression test. Extend the existing deployment
preflight to exercise data sharing, not merely parse R scripts. Update canonical
operator guidance with the identity and acceptance requirements. Review and test
before applying the fix to production. Use the production operator runbook and
avoid restarting unrelated workers or touching unrelated runs.

## Validation and Acceptance

Run `wctl run-pytest tests/rq/test_weppcloudr_backends.py tests/rq/test_weppcloudr_rq.py`;
run affected deployment tests and `wctl run-pytest tests --maxfail=1`. Run docs lint
on changed Markdown. Real acceptance requires a fresh render with a valid
worker-owned 0600 parquet, generated output readback, and ordinary queued RQ
execution on wepp1. An isolated fixture can reproduce permissions without
downgrading users' live files. Cover absent export, existing output, empty inputs
where supported, and existing hostile-path rejection tests. Missing required
model input remains an application error, not a permissions recovery case.

## Idempotence and Recovery

Keep timestamped source backups for any bounded production hotfix. Restore only
the exact changed source if verification fails; keep the last valid report.
No data/schema mutation is intended. Canary copies preserve source bytes; compare
hashes on input and validate nonempty output. Record test logs and UTC times.

## Outcomes & Retrospective

The runtime correction passed on both production hosts, including unchanged
0600 input, regenerated soils with DataFrame parity, absent export creation,
queued replacement of an existing report, and authenticated Flask artifact
readback. No workers were restarted or queues modified beyond the canary job.
Source backups remain available in each patched worker. Full-suite validation
passed; source publication remains open. No image or Compose configuration changed;
ordinary restart retains the patched layer, and the supported deploy script
rebuilds the fixed source before recreating locally built containers.

## Signals

Health is successful fresh rendering of owner-only inputs without chmod.
Danger is errno13, new library/cache write failure, changed input bytes, invalid
output, or changed route authorization. Use recurrence-triggered observation;
future identity/image changes must rerun the real boundary check. Retire canary
material after successful deployment evidence is recorded.
