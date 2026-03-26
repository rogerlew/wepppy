# Disturbed Lookup Hardening and Preservation

This ExecPlan is a living document. The sections `Progress`, `Surprises & Discoveries`, `Decision Log`, and `Outcomes & Retrospective` must be kept up to date as work proceeds.

This plan follows `docs/prompt_templates/codex_exec_plans.md`.

## Purpose / Big Picture

After this change, users can edit disturbed lookup rows in the UI and keep those values intact across save, subsequent build workflows, and disturbed prep operations. The disturbed editor will reject malformed saves instead of silently truncating lookup data, and extended lookup generation will no longer overwrite the editable base CSV.

## Progress

- [x] (2026-03-25 14:35Z) Created work-package scaffold and activated this ExecPlan.
- [x] (2026-03-25 14:36Z) Captured scope and compatibility requirement to keep `?pup` behavior.
- [x] (2026-03-25 18:18Z) Implemented disturbed lookup persistence hardening in module and route layers.
- [x] (2026-03-25 18:29Z) Added/updated regression tests for malformed save rejection, persistence retention across build paths, extended export non-clobber, and scope-safe editor URL behavior.
- [x] (2026-03-25 18:31Z) Executed targeted validations.
- [x] (2026-03-25 18:33Z) Ran subagent code review (`reviewer`), resolved medium/high findings, and saved artifact.
- [x] (2026-03-25 18:35Z) Ran subagent QA review (`qa_reviewer`), resolved medium/high findings, and saved artifact.
- [x] (2026-03-25 18:37Z) Finalized docs/tracker/retrospective and closed package tasks.

## Surprises & Discoveries

- Observation: Disturbed lookup migration currently runs from `land_soil_replacements_d` reads and can rewrite lookup files as a side effect.
  Evidence: `wepppy/nodb/mods/disturbed/disturbed.py` property implementation around migration checks.

- Observation: Disturbed editor save currently performs positional zip writes and can silently blank trailing columns when row payload width is short.
  Evidence: `write_disturbed_land_soil_lookup` maps `zip(fieldnames, row)` with no width validation.

## Decision Log

- Decision: Keep `?pup` compatibility and avoid global scope contract rewrites.
  Rationale: User explicitly requested to keep `?pup`; broad scope-system rewrites are out of package scope.
  Date/Author: 2026-03-25 / Codex.

- Decision: Harden save semantics to fail loudly on malformed payloads and preserve existing values during merge.
  Rationale: Prevent silent data loss and preserve user modifications.
  Date/Author: 2026-03-25 / Codex.

- Decision: Keep disturbed CSV download on existing browse/download route rather than introducing a new Flask download endpoint.
  Rationale: Preserve deployment proxy compatibility (`/download/*` path handling) while retaining `?pup` behavior.
  Date/Author: 2026-03-25 / Codex.

- Decision: Use full-table replacement semantics with a missing-row guard instead of merge-by-key writes.
  Rationale: Avoid stale-row/key-edit regressions while still preventing accidental partial-payload truncation.
  Date/Author: 2026-03-25 / Codex.

## Outcomes & Retrospective

Completed on 2026-03-25.

Delivered outcomes:
- Hardened disturbed lookup writes with strict row-width validation, duplicate-key checks, sparse-mapping rejection, and missing-row guardrails.
- Hardened schema upgrade behavior to keep legacy `disturbed_class`/`texid` rows readable after upgrades.
- Ensured extended lookup generation writes to `disturbed_land_soil_lookup_extended.csv` and does not overwrite editable lookup source.
- Updated editor columns to dynamic CSV-header-driven configuration (supports current 18-column schema without truncation assumptions).
- Preserved `?pup` compatibility and browse-proxy-safe CSV load path.
- Completed reviewer + QA subagent passes with no unresolved medium/high findings.

Validation summary:
- `wctl run-pytest tests/weppcloud/routes/test_disturbed_bp.py --maxfail=1`
- `wctl run-pytest tests/nodb/mods/test_disturbed_lookup_persistence.py --maxfail=1`
- `wctl run-pytest tests/nodb/mods -k disturbed --maxfail=1`
- `wctl run-pytest tests --maxfail=1`
- `wctl run-stubtest wepppy.weppcloud.routes.nodb_api.disturbed_bp`
- `wctl check-test-stubs`
- `wctl run-npm lint`
- `wctl run-npm test`

## Context and Orientation

Disturbed lookup data is persisted at `disturbed/disturbed_land_soil_lookup.csv` under the run root. The UI editor (`controls/edit_csv.htm`) downloads this CSV and posts edited rows to `/tasks/modify_disturbed`. Build flows (`build_landuse`, `build_soils`, and disturbed pmet prep) read disturbed lookup replacements through `Disturbed.land_soil_replacements_d`; this path currently includes migration/rewrite logic.

Primary files:

- `wepppy/nodb/mods/disturbed/disturbed.py`
- `wepppy/weppcloud/routes/nodb_api/disturbed_bp.py`
- `wepppy/weppcloud/templates/controls/edit_csv.htm`
- `tests/weppcloud/routes/test_disturbed_bp.py`
- `tests/nodb/mods/*` (new focused disturbed lookup regression tests)

## Plan of Work

Milestone 1 hardens persistence primitives in disturbed module code. Replace positional writer behavior with validated full-table write semantics, atomic writes, and backup-safe schema upgrade behavior that is additive and non-destructive for user-modified values.

Milestone 2 updates disturbed route/editor integration to reject malformed save payloads and ensure read/write URL scope alignment while retaining `?pup` compatibility.

Milestone 3 adds regression coverage for core failure modes and retention guarantees across build-triggered lookup reads.

Milestone 4 runs targeted validations and records outcomes.

Milestone 5 runs independent `reviewer` subagent code review; all medium/high findings are resolved before proceeding.

Milestone 6 runs independent `qa_reviewer` subagent QA review; all medium/high findings are resolved before closure.

Milestone 7 finalizes package docs and records outcomes.

## Concrete Steps

Run from `/workdir/wepppy`:

1. Implement disturbed module hardening in `wepppy/nodb/mods/disturbed/disturbed.py`.
2. Implement route/editor hardening in `wepppy/weppcloud/routes/nodb_api/disturbed_bp.py` and `wepppy/weppcloud/templates/controls/edit_csv.htm`.
3. Add/update regression tests in disturbed route and nodb test suites.
4. Run targeted tests:

    wctl run-pytest tests/weppcloud/routes/test_disturbed_bp.py --maxfail=1
    wctl run-pytest tests/nodb/mods -k disturbed --maxfail=1

5. Run subagent code review and save artifact to:

    docs/work-packages/20260325_disturbed_lookup_hardening/artifacts/code_review_findings.md

6. Run subagent QA review and save artifact to:

    docs/work-packages/20260325_disturbed_lookup_hardening/artifacts/qa_review_findings.md

7. Resolve medium/high findings and rerun targeted validation suites.

## Validation and Acceptance

Acceptance criteria:

- Malformed or empty save payloads return an explicit error and do not modify lookup CSV.
- Valid user-edited rows persist after lookup reads used by disturbed build/prep flows.
- Extended lookup generation writes to a separate artifact and does not overwrite editable lookup CSV.
- Disturbed editor read URL and save URL resolve to consistent scope behavior with `?pup` compatibility retained.
- Targeted regression tests pass.

## Idempotence and Recovery

Schema-upgrade logic must be additive and idempotent. If a write step fails, original CSV remains available via pre-write backup and atomic replace semantics.

## Artifacts and Notes

- Subagent code review findings: `docs/work-packages/20260325_disturbed_lookup_hardening/artifacts/code_review_findings.md`
- Subagent QA review findings: `docs/work-packages/20260325_disturbed_lookup_hardening/artifacts/qa_review_findings.md`

## Interfaces and Dependencies

- Disturbed lookup writer continues to support list-row payloads emitted by the existing UI.
- Route save contract remains POST JSON and returns canonical WEPPcloud success/error payloads.
- `?pup` compatibility is preserved; no removal of existing pup query semantics in this package.
