# Usersum Header ROLE Filter and Threshold Search Ceiling
> Outcome Summary (2026-04-09): Package closed after delivering header ROLE discovery filtering, threshold role-ceiling search semantics, nav discovery role-ceiling alignment, doc role self-report, specification sync, and security remediation for non-canonical source/raw path bypass (`SEC-01`) with expanded regression coverage.


This ExecPlan is a living document. The sections `Progress`, `Surprises & Discoveries`, `Decision Log`, and `Outcomes & Retrospective` must be kept up to date as work proceeds.

This plan follows `docs/prompt_templates/codex_exec_plans.md`.

## Purpose / Big Picture

After this change, authenticated users with WEPPcloud roles `PowerUser`, `Admin`, or `Root` can choose a usersum `ROLE` discovery ceiling directly in the shared usersum header, immediately to the left of `SEARCH`, with styling that matches the shared `THEMES` selector. Search behavior will match the updated usersum contract: role filters operate as threshold ceilings (`<=`) instead of exact `min_role` equality, and unauthorized requested ceilings return explicit `403`/error-path behavior without bypassing existing document visibility rules.

This is observable by opening `/usersum/` or `/usersum/search` as test users with different WEPPcloud roles, selecting `ROLE`, and verifying result visibility, preserved selection, and error behavior.

## Progress

- [x] (2026-04-08 19:25Z) Read required onboarding/process/spec docs and scoped implementation/test touchpoints.
- [x] (2026-04-08 19:35Z) Created work-package scaffold and activated this ExecPlan.
- [x] (2026-04-08 20:18Z) Implemented backend role-resolution and threshold search semantics.
- [x] (2026-04-08 20:18Z) Implemented shared header role selector and search-page role persistence wiring.
- [x] (2026-04-08 20:18Z) Added/updated required route/template tests.
- [x] (2026-04-08 20:27Z) Ran required validation command successfully (`46 passed`).
- [x] (2026-04-08 20:34Z) Completed explicit QA review pass, recorded findings, and verified no open medium/high issues.
- [x] (2026-04-08 21:04Z) Applied follow-up layout tweak: doc pages now self-report role under breadcrumb; reran targeted usersum tests (`49 passed`).
- [x] (2026-04-08 21:20Z) Applied follow-up UX fix: header role select now submits on change (with `submit()` fallback for older browsers); reran targeted usersum tests (`49 passed`).
- [x] (2026-04-08 22:15Z) Fixed role-selector discovery mismatch by applying selected role ceiling to shell/nav visibility; reran targeted usersum tests (`50 passed`) and verified behavior with `dev-agent@example.com` role set.
- [x] (2026-04-08 22:33Z) Synced `wepppy/weppcloud/routes/usersum/specification.md` to implemented role/nav/search behavior and ran docs lint (`0 errors`, `0 warnings`).
- [x] (2026-04-08 23:35Z) Closed `SEC-01` by enforcing canonical source/raw path handling before manifest visibility checks; added traversal-variant regressions and reran expanded usersum suite (`58 passed`).

## Surprises & Discoveries

- Observation: Prior usersum search behavior was exact `min_role` filtering, so `role=operator` did not include `user` docs as required by threshold semantics.
  Evidence: New regression `tests/weppcloud/routes/test_usersum_bp.py::test_usersum_api_search_role_threshold_includes_lower_roles` now enforces threshold inclusion and would fail under prior exact-match behavior.
- Observation: Prior caller role mapping did not explicitly account for `Root`, so root users were not guaranteed to map to the `internal` usersum ceiling.
  Evidence: New regression `tests/weppcloud/routes/test_usersum_bp.py::test_usersum_api_search_root_ceiling_mapping` validates `role=internal` access for root users.
- Observation: Header `ROLE` defaulted and submitted correctly, but shell nav rendering still used caller max visibility, which made the selector appear ineffective for privileged users.
  Evidence: Follow-up regression `tests/weppcloud/routes/test_usersum_bp.py::test_usersum_shell_nav_respects_selected_role_ceiling` now verifies role-ceiling nav filtering.
- Observation: Source/raw route visibility checks previously keyed off raw path tokens before canonicalization, enabling `..` variants to bypass restricted manifest role checks.
  Evidence: Manual repro showed `src_bypass/raw_bypass` returning `200` for a developer-only doc pre-fix; post-fix both return `404`.

## Decision Log

- Decision: Execute this package end-to-end in one session with continuous tracker/ExecPlan updates and a mandatory QA second pass before handoff.
  Rationale: User requested complete implementation + tests + QA review in one pass.
  Date/Author: 2026-04-08 / Codex.
- Decision: Keep repeated/comma-separated `role` parsing for compatibility, and interpret it as one ceiling by selecting the highest requested usersum role rank.
  Rationale: This is the smallest contract-aligned change from prior parsing behavior while moving to threshold semantics.
  Date/Author: 2026-04-08 / Codex.
- Decision: Reject non-canonical `/usersum/src` and `/usersum/raw` request paths and perform visibility checks only against canonical repo-relative markdown paths.
  Rationale: Removes traversal-variant bypass behavior and ensures one stable authorization key for manifested docs.
  Date/Author: 2026-04-08 / Codex.

## Outcomes & Retrospective

- Implemented usersum backend contract updates in `wepppy/weppcloud/routes/usersum/usersum.py`:
  - explicit role-token extraction for authenticated callers,
  - corrected caller visibility mapping (`PowerUser -> operator`, `Admin -> developer`, `Root -> internal`),
  - threshold role-ceiling semantics via role scopes up to requested ceiling,
  - explicit authorization error for requested ceilings above caller max role,
  - default omitted role behavior preserved at `user`.
- Implemented usersum header/search template updates:
  - conditional `ROLE` selector in `header.htm` shown only to authenticated PowerUser/Admin/Root users,
  - option sets constrained to required usersum roles by WEPPcloud role,
  - role selector styled with the same classes as shared theme selector,
  - `/usersum/search` refinement form now preserves selected role value.
- Added/updated regression coverage in:
  - `tests/weppcloud/routes/test_usersum_bp.py`
  - `tests/weppcloud/test_usersum_template_wiring.py`
- Follow-up refinement: usersum doc pages now show `Role: <min_role>` directly under breadcrumb.
- Follow-up UX fix: usersum header role select now uses change-triggered submit to execute existing search flow immediately.
- Follow-up discovery fix: usersum shell navigation now applies the selected header role ceiling (discovery-only) so privileged users no longer see all docs when lower ceilings are selected.
- Follow-up doc sync: `wepppy/weppcloud/routes/usersum/specification.md` now reflects implemented role resolution, selector behavior, threshold semantics, and shell discovery filtering.
- Security remediation: `/usersum/src` and `/usersum/raw` now canonicalize and reject non-canonical rel-path variants before manifest visibility checks; regression tests cover canonical-allowed vs non-canonical-denied behavior for restricted docs.
- Validation:
  - `wctl run-pytest tests/weppcloud/routes/test_usersum_bp.py tests/weppcloud/test_usersum_template_wiring.py --maxfail=1` -> `50 passed` after follow-up nav-ceiling fix.
  - `wctl run-pytest tests/weppcloud/routes/test_usersum_bp.py tests/weppcloud/routes/test_usersum_docs_contracts.py tests/weppcloud/routes/test_usersum_docs_index.py tests/weppcloud/test_usersum_template_wiring.py --maxfail=1` -> `58 passed` after security remediation.
  - In-container role verification run with `dev-agent@example.com` confirmed API and shell/nav behavior by selected role ceiling.
  - Manual source/raw bypass repro now returns `404` for non-canonical variants targeting restricted docs.
  - `wctl doc-lint --path wepppy/weppcloud/routes/usersum/specification.md` -> `✅ 1 files validated, 0 errors, 0 warnings`.
- QA review:
  - Second-pass correctness/regression/contract review completed with no open medium/high findings; follow-up discovery mismatch finding resolved.

## Context and Orientation

Key implementation surface:

- Backend route/search/role logic:
  - `wepppy/weppcloud/routes/usersum/usersum.py`
- Usersum templates:
  - `wepppy/weppcloud/routes/usersum/templates/usersum/header.htm`
  - `wepppy/weppcloud/routes/usersum/templates/usersum/layout.j2`
  - `wepppy/weppcloud/routes/usersum/templates/usersum/search.htm`
- Regression tests:
  - `tests/weppcloud/routes/test_usersum_bp.py`
  - `tests/weppcloud/test_usersum_template_wiring.py`

Current behavior gaps versus spec:

- Role filter is exact-match set semantics rather than threshold ceiling semantics.
- `Root` mapping is not explicit in usersum role resolution.
- Header has theme selector + search only; no conditional `ROLE` selector.
- Search-page refinement form currently omits selected role and drops it on submit.

## Plan of Work

Milestone 1 (Backend semantics):

Update usersum role handling in `usersum.py` so callers resolve to correct usersum max-role ceilings, including explicit `Root` mapping. Replace exact role matching with threshold ceiling semantics by deriving an effective allowed role set up to the requested ceiling, intersected with caller maximum visibility, and preserving explicit `403` for requested ceilings above caller max. Keep omitted-role default as `user`.

Milestone 2 (Header and search-page UX wiring):

Add a conditional header `ROLE` selector in `header.htm`, positioned left of `SEARCH`, and assign the same field/select classes used by the shared theme selector so styling matches. Ensure selected role value is preserved in both header submits and search-page refinement submits.

Milestone 3 (Tests + QA review):

Add/adjust route tests for threshold semantics, unauthorized ceilings, and PowerUser/Admin/Root behavior. Add/adjust template tests for selector visibility and role option sets. Run required pytest targets. Then perform an explicit QA review pass (correctness/regressions/contracts/missing tests), log findings in tracker/ExecPlan, and fix any issues before handoff.

## Concrete Steps

Run commands from `/workdir/wepppy`.

1. Implement backend/template changes in usersum files.
2. Update usersum route and template tests.
3. Run required validation:
   - `wctl run-pytest tests/weppcloud/routes/test_usersum_bp.py tests/weppcloud/test_usersum_template_wiring.py --maxfail=1`
4. If specification changes are made, run:
   - `wctl doc-lint --path wepppy/weppcloud/routes/usersum/specification.md`
5. Perform QA second pass and record findings/disposition in:
   - `docs/work-packages/20260408_usersum_role_filter/tracker.md`

## Validation and Acceptance

Acceptance is complete when:

- Header `ROLE` selector shows only for authenticated `PowerUser`/`Admin`/`Root` users.
- Option sets exactly match:
  - PowerUser: `user`, `operator`
  - Admin: `user`, `operator`, `developer`
  - Root: `user`, `operator`, `developer`, `internal`
- Role filter semantics are threshold-based for both API and search page.
- Requests above caller ceiling produce `403` in `/usersum/api/search` and page error-path rendering in `/usersum/search`.
- Omitted `role` continues to use `user` ceiling behavior.
- Selected role persists across usersum search refinements.
- Required targeted tests pass.
- QA review findings are recorded and resolved/dispositioned.

## Idempotence and Recovery

Changes are additive and safe to rerun. If tests fail, iterate on affected files and rerun targeted suites until green. Maintain generated usersum index artifacts as read-only in this package unless explicitly requested.

## Artifacts and Notes

- Work package: `docs/work-packages/20260408_usersum_role_filter/`
- Completed plan: `docs/work-packages/20260408_usersum_role_filter/prompts/completed/usersum_role_filter_execplan.md`
- Tracker: `docs/work-packages/20260408_usersum_role_filter/tracker.md`

## Interfaces and Dependencies

Primary interfaces touched:

- Usersum caller-role resolution and search argument parsing in `usersum.py`.
- Search backend invocation role filters for in-memory and PostgreSQL paths.
- Shared usersum header control rendering contract.
- Search-page form query-param preservation behavior.

No new external dependencies are introduced.

---
Revision Note (2026-04-08 / Codex): Initial active ExecPlan authored at package kickoff.
Revision Note (2026-04-08 / Codex): Updated after implementation/testing/QA completion with final decisions, outcomes, and validation evidence.
Revision Note (2026-04-08 / Codex): Updated for post-handoff follow-up fix: role-ceiling nav discovery filtering and dev-agent verification evidence.
Revision Note (2026-04-08 / Codex): Updated for security trial remediation: closed source/raw non-canonical path bypass (`SEC-01`) and recorded expanded validation evidence.
