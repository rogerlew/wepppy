# Usersum Header ROLE Filter and Threshold Search Ceiling

**Status**: Closed (2026-04-09)

## Overview
This package adds a usersum `ROLE` discovery filter in the shared usersum header and aligns backend search/filter behavior with the updated usersum role-ceiling specification. The goal is to keep role-based discovery predictable for PowerUser/Admin/Root audiences while preserving strict authorization and min-role visibility gates.

## Objectives
- Add a conditional header `ROLE` select left of `SEARCH`, styled exactly like the shared `THEMES` select.
- Align usersum role resolution with updated WEPPcloud role mapping requirements, including correct `Root` handling.
- Change usersum search `role` semantics from exact role matching to threshold ceiling matching.
- Preserve selected role across usersum search requests, including refinement on `/usersum/search`.
- Add route and template regression coverage for all new role/UI/contract behaviors.
- Complete an explicit second-pass QA review and document findings/remediations.

## Scope
This package covers usersum route logic, usersum header/search templates, targeted usersum spec clarifications (only if needed), test updates, and work-package documentation/tracking artifacts.

### Included
- Usersum backend role-resolution and search role-filter contract updates.
- Shared usersum header role selector behavior and styling parity.
- Search-page role-preservation wiring.
- Route tests for threshold behavior, unauthorized ceilings, and role mapping.
- Template tests for conditional visibility and role option sets.
- Active ExecPlan and tracker maintenance during implementation and QA review.

### Explicitly Out of Scope
- Rebuilding/re-generating usersum manifest or index artifacts outside this feature scope.
- Non-usersum route/template changes.
- Broader usersum information architecture changes.

## Stakeholders
- **Primary**: WEPPcloud users and operators consuming usersum docs/search.
- **Reviewers**: WEPPcloud usersum route/template maintainers.
- **Informed**: Docs maintainers relying on usersum discoverability and role gating.

## Success Criteria
- [x] Header `ROLE` select renders only for authenticated `PowerUser`/`Admin`/`Root` callers.
- [x] Header `ROLE` select exposes exact required option subsets per WEPPcloud role.
- [x] `/usersum/api/search` and `/usersum/search` use threshold role-ceiling semantics.
- [x] Requested role ceilings above caller ceiling return `403` in API and error path in page route.
- [x] Default omitted role behavior remains `user` ceiling.
- [x] Selected role is preserved through usersum search flow and page refinements.
- [x] Required tests pass and QA review findings are fully dispositioned.

## Dependencies

### Prerequisites
- Existing usersum docs engine/package baseline: `docs/work-packages/20260401_usersum_docs_engine/`.
- Current usersum contracts/spec at `wepppy/weppcloud/routes/usersum/specification.md`.

### Blocks
- Follow-on usersum UX and role discoverability refinements depend on this package’s search/filter contract alignment.

## Related Packages
- **Depends on**: [20260401_usersum_docs_engine](../20260401_usersum_docs_engine/package.md)
- **Related**: [20260403_roads_map_drilldown](../20260403_roads_map_drilldown/package.md) (active ExecPlan governance process reference)

## Timeline Estimate
- **Expected duration**: 1 focused session
- **Complexity**: Medium
- **Risk level**: Medium

## References
- `wepppy/weppcloud/routes/usersum/specification.md` - canonical usersum role/search/header behavior contract.
- `wepppy/weppcloud/routes/usersum/usersum.py` - usersum route/search/role logic.
- `wepppy/weppcloud/routes/usersum/templates/usersum/header.htm` - shared usersum header controls.
- `wepppy/weppcloud/routes/usersum/templates/usersum/search.htm` - usersum search page form behavior.
- `tests/weppcloud/routes/test_usersum_bp.py` - usersum route regression coverage.
- `tests/weppcloud/test_usersum_template_wiring.py` - usersum shell/template wiring coverage.

## Deliverables
- Updated usersum backend role/search behavior and templates.
- Updated targeted usersum route/template test coverage.
- New work package docs:
  - `docs/work-packages/20260408_usersum_role_filter/package.md`
  - `docs/work-packages/20260408_usersum_role_filter/tracker.md`
  - `docs/work-packages/20260408_usersum_role_filter/prompts/completed/usersum_role_filter_execplan.md`

## Outcome Summary
- Implemented usersum role-ceiling discovery behavior end-to-end:
  - conditional header `ROLE` selector with required option sets for `PowerUser`/`Admin`/`Root`,
  - threshold role semantics for `/usersum/api/search` and `/usersum/search`,
  - selected role persistence during search refinement and change-submit behavior.
- Added follow-up UX and correctness refinements:
  - doc role self-report under breadcrumbs,
  - shell/nav discovery filtered by selected `ROLE`,
  - canonicalized source/raw rel-path checks to close non-canonical visibility bypass (`SEC-01`).
- Updated usersum docs contracts and spec for shipped behavior:
  - `wepppy/weppcloud/routes/usersum/specification.md`,
  - `wepppy/weppcloud/routes/usersum/docs_manifest.yaml`,
  - `wepppy/weppcloud/routes/usersum/nav_tree.yaml`,
  - `wepppy/weppcloud/routes/usersum/weppcloud/models/batch-runs/ENDUSER.md`.
- Validation and review closure:
  - targeted usersum route/template suite passed (`50 passed`),
  - expanded usersum suite after security remediation passed (`58 passed`),
  - usersum spec doc-lint passed (`0 errors`, `0 warnings`),
  - QA and security review gates closed with no unresolved medium/high findings.

## Follow-up Work
- Optional future package to add explicit telemetry/alerting for repeated denied non-canonical `/usersum/src` and `/usersum/raw` probes.
