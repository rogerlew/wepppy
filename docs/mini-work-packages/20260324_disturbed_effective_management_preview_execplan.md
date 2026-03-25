# ExecPlan: On-Demand Disturbed-Effective Management Preview Links (No Persistence)

Status: Completed
Last Updated: 2026-03-24
Primary Areas: `wepppy/weppcloud/routes/nodb_api/wepp_bp.py`, `wepppy/weppcloud/routes/nodb_api/landuse_bp.py`, `wepppy/weppcloud/templates/reports/landuse.htm`, `wepppy/weppcloud/templates/reports/hill.htm`, `wepppy/weppcloud/templates/reports/wepp/prep_details.htm`, `wepppy/nodb/core/management_overrides.py`, `wepppy/nodb/core/wepp_prep_service.py`, `tests/weppcloud/routes/test_wepp_bp.py`, `tests/weppcloud/routes/test_landuse_bp.py`

This ExecPlan is a living document. The sections `Progress`, `Surprises & Discoveries`, `Decision Log`, and `Outcomes & Retrospective` must be kept up to date as work proceeds.

This document must be maintained in accordance with `docs/prompt_templates/codex_exec_plans.md`.

## Purpose / Big Picture

Users currently click `view/management/<key>` and see a management definition that is easy to misread as the final disturbed-effective result. In disturbed workflows, effective parameters (for example, `xmxlai`, `rdmax`, and other disturbed lookup overrides) are applied during WEPP preparation logic and depend on disturbed class plus texture.

After this change, disturbed-enabled runs expose explicit links for on-demand disturbed-effective previews by texture (`Clay`, `Loam`, `Sand`, `Silt`). Each preview is built in memory and returned directly as text. No files are written to project paths, run paths, or `/tmp`.

## Progress

- [x] (2026-03-24 22:40Z) Authored initial mini-work-package ExecPlan with subagent implementation and review gates.
- [x] (2026-03-24 22:44Z) Began end-to-end execution with explicit `worker` delegation for implementation + tests.
- [x] (2026-03-24 22:56Z) Implemented backend in-memory disturbed-effective preview endpoint and extracted disturbed normalization/scalar helper logic reused by WEPP prep service and preview route.
- [x] (2026-03-24 22:57Z) Added disturbed-aware preview links in landuse/hill/prep_details templates with disturbed-only route context flags.
- [x] (2026-03-24 22:57Z) Added/extended route and template tests, including explicit no-persistence coverage for preview requests.
- [x] (2026-03-24 22:58Z) Ran targeted validation command: `wctl run-pytest tests/weppcloud/routes/test_wepp_bp.py tests/weppcloud/routes/test_landuse_bp.py --maxfail=1` (47 passed).
- [x] (2026-03-24 23:02Z) Ran optional broader confidence pass: `wctl run-pytest tests/weppcloud/routes --maxfail=1` (330 passed).
- [x] (2026-03-24 23:02Z) Ran docs lint: `wctl doc-lint --path docs/mini-work-packages/20260324_disturbed_effective_management_preview_execplan.md` (1 file validated, 0 errors, 0 warnings).
- [x] (2026-03-24 23:03Z) Completed correctness review gate (`reviewer`): no high/medium correctness findings requiring code changes.
- [x] (2026-03-24 23:03Z) Completed QA/maintainability review gate (`qa_reviewer`): no maintainability findings requiring code changes.
- [x] (2026-03-24 23:41Z) Investigated user-reported `xmxlai` mismatch on live endpoint (`.../view/management_effective/71/clay/`) and identified preview scalar gating with `cancov_override` as cause.
- [x] (2026-03-24 23:44Z) Patched preview route to expose lookup-effective `rdmax/xmxlai` values in preview output even when `cancov_override` exists, and added regression test coverage.
- [x] (2026-03-24 23:44Z) Re-ran targeted validation command post-fix: `wctl run-pytest tests/weppcloud/routes/test_wepp_bp.py tests/weppcloud/routes/test_landuse_bp.py --maxfail=1` (48 passed).
- [x] (2026-03-24 23:51Z) Re-ran broader routes confidence sweep post-fix: `wctl run-pytest tests/weppcloud/routes --maxfail=1` (331 passed).
- [x] (2026-03-24 23:58Z) Applied final UX polish to tighten Key/Description spacing in `reports/landuse.htm` by updating `ui-foundation.css` landuse table column layout.

## Surprises & Discoveries

- Observation: existing `view/management/<key>` route returns `Landuse` management object repr directly, without disturbed-effective texture specialization.
  Evidence: `wepppy/weppcloud/routes/nodb_api/wepp_bp.py` route `view_management` calls `landuse.managements[str(key)].get_management()` and returns `repr(man)`.

- Observation: disturbed overrides are applied in WEPP prep stages, not in current management-view route.
  Evidence: `wepppy/nodb/core/wepp_prep_service.py` applies `rdmax`, `xmxlai`, and `apply_disturbed_management_overrides(...)` before writing `wepp/runs/p*.man`.

- Observation: user requirement forbids persistence for preview artifacts.
  Evidence: requirement from requester on 2026-03-24: "preferable no file at all."

- Observation: WEPP prep had inline disturbed-class normalization and scalar replacement branching duplicated in multiple call paths.
  Evidence: `wepppy/nodb/core/wepp_prep_service.py` inline `"mulch"/"thinning"` normalization and `rdmax/xmxlai` gating logic before helper extraction.

- Observation: conditional link rendering is safest via explicit context booleans instead of implicit object probing in templates.
  Evidence: `reports/hill.htm` and `reports/wepp/prep_details.htm` are rendered from `wepp_bp` routes where disturbed status is sourced from `ron.mods`, while `reports/landuse.htm` uses `landuse.mods`.

- Observation: no-persistence checks were easiest to validate at route-test level by preventing write-mode file opens and asserting no run-dir drift before/after request.
  Evidence: `tests/weppcloud/routes/test_wepp_bp.py::test_view_management_effective_does_not_persist_preview_artifacts` patches `open`/`tempfile.mkstemp` and compares `Path(run_dir).rglob("*")` snapshots.

- Observation: preview scalar gating by `cancov_override` hid disturbed lookup values for real runs where users expected lookup-effective preview output.
  Evidence: run `reconciled-condenser`, key `71`, clay lookup has `xmxlai=5.1`, while preview returned `3.6` before post-feedback route fix.

## Decision Log

- Decision: implement preview generation in memory only and return plain text response directly.
  Rationale: satisfies no-persistence requirement and avoids permission/cleanup risks.
  Date/Author: 2026-03-24 / Codex

- Decision: expose explicit disturbed-effective links per texture and keep existing base `view/management/<key>` link.
  Rationale: preserves legacy/non-disturbed behavior while removing ambiguity for disturbed workflows.
  Date/Author: 2026-03-24 / Codex

- Decision: require two independent review passes (`reviewer`, then `qa_reviewer`) after coding and test execution.
  Rationale: user explicitly requested subagent code and QA review workflow.
  Date/Author: 2026-03-24 / Codex

- Decision: return 400 JSON contract errors for invalid texture and missing disturbed mod in the new preview endpoint.
  Rationale: these are request/context validation failures, not server faults; `error_factory(..., status_code=400)` preserves canonical payload shape.
  Date/Author: 2026-03-24 / Codex

- Decision: preview route applies lookup `rdmax/xmxlai` replacements regardless of `cancov_override`.
  Rationale: users expect the preview to surface disturbed lookup-effective scalar values; suppressing these when `cancov_override` exists produced misleading output (`xmxlai=3.6` vs expected `5.1`).
  Date/Author: 2026-03-24 / Codex

## Outcomes & Retrospective

Completed outcomes:

- Added new endpoint `/runs/<runid>/<config>/view/management_effective/<key>/<texture>` in `wepp_bp` that:
  - normalizes texture labels (`Clay`, `Loam`, `Sand`, `Silt`) to canonical lookup textures (`clay loam`, `loam`, `sand loam`, `silt loam`),
  - requires disturbed context via `Disturbed.tryGetInstance(wd)` and returns a contract error when missing,
  - applies disturbed scalar/extended overrides to an in-memory management object only,
  - returns `repr(management)` as `text/plain`.
- Extracted shared disturbed helper logic into `management_overrides.py` and reused it in `wepp_prep_service.py` plus preview route logic to reduce drift for:
  - mulch/thinning disturbed class normalization,
  - `rdmax` / `xmxlai` gating with `cancov_override`.
- Post-feedback refinement: preview route now intentionally surfaces lookup-effective scalar replacements (`rdmax`, `xmxlai`) even when `cancov_override` exists on the management summary.
- Added disturbed-aware links (shown only when disturbed context is present) in:
  - `reports/landuse.htm`
  - `reports/hill.htm`
  - `reports/wepp/prep_details.htm`
  with links `(Clay | Loam | Sand | Silt)` targeting the new preview endpoint.
- Added/updated tests covering:
  - per-texture disturbed-effective responses,
  - invalid texture contract errors,
  - missing disturbed mod errors,
  - no-persistence behavior (no write-mode I/O and no run-path artifact drift),
  - disturbed preview context + conditional link rendering.
- Applied final report UX tightening for disturbed texture links in Landuse summary:
  - fixed table layout for `wc-landuse-report__table`,
  - narrower key/actions columns and compact coverage column sizing,
  - key-cell wrapping support and slightly reduced disturbed-link text size.

Validation evidence:

- `wctl run-pytest tests/weppcloud/routes/test_wepp_bp.py tests/weppcloud/routes/test_landuse_bp.py --maxfail=1` -> 48 passed (post-fix).
- `wctl run-pytest tests/weppcloud/routes --maxfail=1` -> 331 passed (post-fix).
- `wctl doc-lint --path docs/mini-work-packages/20260324_disturbed_effective_management_preview_execplan.md` -> 1 file validated, 0 errors, 0 warnings.

Review gate outcomes:

- `worker` implementation pass completed and integrated.
- `reviewer` correctness gate: no high/medium findings requiring fixes.
- `qa_reviewer` maintainability gate: no required findings.

## Context and Orientation

Current behavior has two distinct concepts:

1. Base management view:
   - Route: `wepppy/weppcloud/routes/nodb_api/wepp_bp.py::view_management`
   - Behavior: returns a representation of the management object tied to a landuse key.

2. Disturbed-effective management during WEPP prep:
   - File: `wepppy/nodb/core/wepp_prep_service.py`
   - Behavior: derives disturbed replacements using texture + disturbed class, applies `rdmax`, conditionally applies `xmxlai`, and applies additional disturbed override fields before writing `wepp/runs/p*.man`.

We need a third, explicit read-only capability: render disturbed-effective management variants for canonical textures without triggering prep or run steps and without writing files.

Terms used in this plan:

- "Disturbed-effective preview": the management representation after applying disturbed lookup replacements for one requested texture.
- "Canonical textures": `clay loam`, `loam`, `sand loam`, `silt loam`, surfaced as labels `Clay`, `Loam`, `Sand`, `Silt`.
- "No persistence": no writes to run directories, source tree, or temporary files.

## Subagent Execution Topology

Implementation and review must run with explicit delegation:

1. Code worker pass:
   - Spawn `worker` subagent to implement backend route/helper and tests.
   - Spawn a second `worker` only if needed for template-link updates with disjoint write scope.

2. Correctness review gate:
   - Spawn `reviewer` subagent against full diff.
   - Resolve all high/medium findings before proceeding.

3. QA/maintainability review gate:
   - Spawn `qa_reviewer` subagent against post-fix diff.
   - Resolve all required findings.

4. Optional validation hardening:
   - Spawn `test_guardian` if pytest scope needs stabilization, fixture hardening, or marker/stub fixes.

No merge/handoff until both review gates have completed and outcomes are documented in this plan.

## Plan of Work

### Milestone 1: Backend in-memory disturbed-effective preview endpoint

Add a new WEPP route for effective preview by key and texture, for example:

- `/runs/<runid>/<config>/view/management_effective/<key>/<texture>`

Behavior requirements:

- Resolve run `wd` with existing route helpers.
- Load `Landuse` and fetch `man_summary` for `key`.
- Require disturbed context (`Disturbed.tryGetInstance(wd)` with explicit error when missing).
- Clone management object in memory and apply disturbed replacements for the requested canonical texture.
- Return plain-text representation (`repr(management)`) directly in response.
- Do not write any files.

Normalize preview behavior to mirror prep logic where feasible:

- disturbed class normalization for mulch/thinning variants,
- preview scalar behavior that exposes lookup-effective `rdmax` / `xmxlai` values (including when `cancov_override` exists),
- `rdmax` and additional disturbed override application via existing helper pathways.

### Milestone 2: Disturbed-aware preview links in UI reports

Add explicit preview links where management key links already exist:

- `wepppy/weppcloud/templates/reports/landuse.htm`
- `wepppy/weppcloud/templates/reports/hill.htm`
- `wepppy/weppcloud/templates/reports/wepp/prep_details.htm`

Target pattern:

- existing base link remains: `<key>`
- disturbed-aware suffix appears when disturbed mod is present:
  - `(Clay | Loam | Sand | Silt)` with each item linked to the new preview endpoint.

Do not alter non-disturbed runs; links should only render when disturbed context is available.

### Milestone 3: Tests and no-persistence verification

Add/extend route and template tests to verify:

- endpoint returns disturbed-effective content for each texture label,
- endpoint rejects invalid texture labels with contract-compliant error response,
- endpoint handles missing disturbed mod clearly,
- response generation is in-memory only (no created/modified preview files in run/project paths),
- report templates render the additional links only in disturbed context.

### Milestone 4: Validation and review gates

Run targeted tests, execute both review gates, resolve findings, and document outcomes.

## Concrete Steps

Run from `/workdir/wepppy`.

1. Implement backend endpoint and helper extraction/reuse:

    Edit `wepppy/weppcloud/routes/nodb_api/wepp_bp.py`.
    Edit `wepppy/nodb/core/management_overrides.py` only if helper reuse is needed to avoid logic drift.
    Edit `wepppy/nodb/core/wepp_prep_service.py` only for safe helper extraction (behavior-preserving).

2. Add disturbed-aware links in templates:

    Edit `wepppy/weppcloud/templates/reports/landuse.htm`.
    Edit `wepppy/weppcloud/templates/reports/hill.htm`.
    Edit `wepppy/weppcloud/templates/reports/wepp/prep_details.htm`.
    Edit route context providers if additional booleans are needed (`landuse_bp.py`, related report routes).

3. Add/update tests:

    Edit `tests/weppcloud/routes/test_wepp_bp.py`.
    Edit `tests/weppcloud/routes/test_landuse_bp.py`.
    Add a focused template/render test module if coverage is cleaner there.

4. Run targeted validations:

    wctl run-pytest tests/weppcloud/routes/test_wepp_bp.py tests/weppcloud/routes/test_landuse_bp.py --maxfail=1

5. Run review gates via subagents:

    First: `reviewer` on full diff.
    Second: `qa_reviewer` on post-fix diff.
    Resolve findings and rerun impacted tests.

6. Optional broader confidence pass:

    wctl run-pytest tests/weppcloud/routes --maxfail=1

7. Lint docs updates:

    wctl doc-lint --path docs/mini-work-packages/20260324_disturbed_effective_management_preview_execplan.md

## Validation and Acceptance

Acceptance criteria:

1. Feature behavior:
   - Disturbed-enabled report pages expose texture-specific management preview links next to the base key link.
   - Clicking each texture link returns a plain-text management preview that reflects disturbed replacement behavior for that texture.

2. No persistence:
   - Preview requests do not create/modify files in run directories or source tree.
   - Implementation does not rely on `/tmp` files for preview generation.

3. Compatibility:
   - Existing base `view/management/<key>` route remains functional and unchanged for legacy workflows.
   - Non-disturbed runs do not display broken/irrelevant preview links.

4. Quality gates:
   - Targeted pytest scope passes.
   - `reviewer` and `qa_reviewer` findings are resolved or explicitly accepted with rationale in this plan.

## Idempotence and Recovery

All route/template/test edits in this plan are idempotent and safe to re-apply.

If implementation diverges:

- keep existing base `view/management/<key>` route untouched,
- disable only the new effective-preview links while preserving existing pages,
- rerun targeted route tests before restoring new links.

Because no persistent artifacts are written by design, there is no filesystem cleanup step for feature operation.

## Artifacts and Notes

Capture concise evidence during implementation:

- Response samples for each texture endpoint (`Clay`, `Loam`, `Sand`, `Silt`).
- Before/after file listings (or explicit assertions) proving no preview artifacts are created.
- Reviewer and QA reviewer findings with resolution notes.
- Final targeted pytest transcript.

## Interfaces and Dependencies

Primary interfaces affected:

- WEPP route surface for management viewing (`wepp_bp`).
- Report templates that currently link to base management views.
- Disturbed replacement logic paths currently centered in WEPP prep service.

Dependency expectations:

- Reuse existing NoDb controller interfaces (`Landuse`, `Disturbed`) and existing management mutation methods (`set_rdmax`, `set_xmxlai`, disturbed override helper).
- Do not introduce new external dependencies.

## E2E Operator Prompt (Copy/Paste)

Use this prompt to run implementation end-to-end with subagent coding and QA reviews:

Implement `docs/mini-work-packages/20260324_disturbed_effective_management_preview_execplan.md` end-to-end.

Requirements:

- Follow the ExecPlan exactly and keep it updated as a living document.
- Use subagents explicitly:
  - `worker` for implementation,
  - `reviewer` for correctness review gate,
  - `qa_reviewer` for QA/maintainability review gate.
- Do not stop after planning; complete implementation, tests, reviews, and fixes in one run unless blocked.
- Enforce no-persistence preview behavior: build disturbed-effective management previews in memory only and return response directly (no writes to run/project paths and no `/tmp` preview files).
- Run the validation commands listed in the plan and report concrete results.
- At handoff, include:
  - changed files,
  - review findings and resolutions,
  - test command outcomes,
  - any residual risks.

## Revision Notes

- 2026-03-24 23:03Z: Finalized living sections to completed state with concrete validation evidence, review gate outcomes, and no-persistence test notes.
- 2026-03-24 23:47Z: Added post-feedback xmxlai fix details, regression-test evidence, and updated milestone/outcome language to reflect lookup-effective preview scalar behavior.
- 2026-03-24 23:51Z: Refreshed validation evidence after post-feedback fix with a full `tests/weppcloud/routes` rerun (`331 passed`).
- 2026-03-24 23:58Z: Recorded final closeout UI refinement for Key/Description spacing and confirmed package remains in `Status: Completed`.
