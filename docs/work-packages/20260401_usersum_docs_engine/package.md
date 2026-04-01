# Usersum Manifest-Driven Docs Engine (GitBook Layout + Vendor + PostgreSQL Search)

**Status**: Closed (2026-04-01)

## Overview
This package upgrades Usersum from filesystem-driven markdown browsing into a manifest-driven documentation engine with role-aware visibility, vendor import support, GitBook-like navigation UX, and PostgreSQL-backed ranked search. The objective is to make Usersum production-grade for both end users and operators while preserving compatibility with existing usersum links and command-bar integrations.

## Objectives
- Deliver machine-readable docs contracts (`docs_manifest.yaml`, `nav_tree.yaml`, `vendors.yaml`) with strict validation.
- Implement vendor sync/build tooling and generated runtime index artifact (`generated/docs_index.json`).
- Move usersum runtime browse/view/search to manifest-index-backed behavior.
- Implement GitBook-like shell features:
  - top-right header search,
  - sticky/collapsible navigation tree,
  - breadcrumb links above content.
- Implement PostgreSQL FTS + `pg_trgm` search backend for `/usersum/api/search` and `/usersum/search`.
- Keep compatibility routes functional while introducing canonical manifest identity routes.
- Complete required code review and QA review as package closure gates.

## Scope
This package covers usersum schema/config files, tooling scripts, route/runtime refactors, template/layout changes, PostgreSQL integration for search/indexing, tests, and package-level review artifacts.

### Included
- Usersum manifest/nav/vendor schema files and validation tooling.
- Vendor sync workflow for initial `weppcloud-wbt` docs.
- Generated usersum docs index artifact and loader.
- Route/runtime refactor to manifest-index-backed document resolution.
- GitBook-like usersum layout/navigation implementation.
- PostgreSQL search/index implementation with `pg_trgm`/FTS query contract.
- Canonical and compatibility usersum route wiring.
- Regression tests for schemas, runtime, routes, search, and layout contracts.
- Code review and QA review artifacts with remediation.

### Explicitly Out of Scope
- Replacement of usersum markdown rendering engine (`cmarkgfm`) in this package.
- Full MCP tool implementation (API surface remains preparatory for MCP).
- Broad migration of non-usersum docs systems outside usersum scope.

## Stakeholders
- **Primary**: WEPPcloud users and operators relying on in-app documentation.
- **Reviewers**: WEPPcloud routes/templates maintainers, docs/tooling maintainers, platform/PostgreSQL maintainers.
- **Informed**: NoDb/module maintainers referencing usersum docs and link helpers.

## Success Criteria
- [x] Milestones 1-6 from `wepppy/weppcloud/routes/usersum/specification.md` are implemented end-to-end.
- [x] Usersum docs are opt-in via manifest and role-classified using `min_role`.
- [x] Initial vendor scope is synced and published:
  - `docs/hydroenforcement/culvert-web-app-hydroenforcement.md`
  - `whitebox-tools-app/src/tools/hydro_analysis/hillslopes_topaz.spec.md`
- [x] Usersum UI exposes fixed header search, sticky collapsible nav tree, and breadcrumbs.
- [x] `/usersum/api/search` supports PostgreSQL-ranked search contract and role/category filtering semantics.
- [x] Existing compatibility endpoints continue to function.
- [x] Focused usersum/backend/frontend tests pass, plus pre-handoff broad pytest gate.
- [x] Independent code review and QA review are completed with no unresolved medium/high findings.

## Dependencies

### Prerequisites
- Existing usersum blueprint and templates in `wepppy/weppcloud/routes/usersum/`.
- WEPPcloud PostgreSQL connectivity via app configuration (`SQLALCHEMY_DATABASE_URI`/`DATABASE_URL`).
- Access to companion repo path `/workdir/weppcloud-wbt` for vendor sync.

### Blocks
- Future MCP docs tooling work depends on stable usersum API/search contracts from this package.

## Related Packages
- **Related**: [20251025_markdown_doc_toolkit](../20251025_markdown_doc_toolkit/package.md)
- **Follow-up**: Potential package for MCP docs capabilities using stabilized usersum search/get contracts.

## Timeline Estimate
- **Expected duration**: 2-4 focused sessions
- **Complexity**: High
- **Risk level**: High (cross-cutting route/runtime/search/layout/database changes)

## References
- `wepppy/weppcloud/routes/usersum/specification.md` - canonical target contract.
- `wepppy/weppcloud/routes/usersum/usersum.py` - current route implementation.
- `tests/weppcloud/routes/test_usersum_bp.py` - usersum route regressions.
- `tests/weppcloud/test_usersum_template_wiring.py` - usersum shell/template wiring.
- `/workdir/weppcloud-wbt/docs/hydroenforcement/culvert-web-app-hydroenforcement.md` - vendor source 1.
- `/workdir/weppcloud-wbt/whitebox-tools-app/src/tools/hydro_analysis/hillslopes_topaz.spec.md` - vendor source 2.

## Deliverables
- Manifest/nav/vendor schema files and validation tool(s).
- Vendor sync/build tooling and generated docs index artifact.
- Usersum runtime/layout/search implementation updates.
- Expanded usersum regression tests.
- Work-package artifacts:
  - `artifacts/code_review_findings.md`
  - `artifacts/qa_review_findings.md`
- Completed ExecPlan moved to `prompts/completed/`.

## Outcome Summary
- Added manifest/nav/vendor contracts and strict validator tooling:
  - `wepppy/weppcloud/routes/usersum/docs_manifest.yaml`
  - `wepppy/weppcloud/routes/usersum/nav_tree.yaml`
  - `wepppy/weppcloud/routes/usersum/vendors.yaml`
  - `wepppy/weppcloud/usersum_docs/docs_contracts.py`
  - `tools/usersum_docs_tool.py`
- Added generated runtime index + vendor sync path:
  - `wepppy/weppcloud/routes/usersum/generated/docs_index.json`
  - `wepppy/weppcloud/usersum_docs/docs_index.py`
  - `wepppy/weppcloud/routes/usersum/vendor/weppcloud-wbt/...`
- Refactored usersum runtime to manifest/index-backed doc routing and role-aware visibility:
  - canonical `GET /usersum/doc/<doc_id>`
  - scoped vendor `GET /usersum/vendor/<vendor_id>/<path:filename>`
  - compatibility routes retained (`/usersum/view/*`, `/usersum/src/*`, `/usersum/raw/*`)
- Implemented GitBook-like shell patterns:
  - sticky/collapsible left nav tree
  - breadcrumb trail above doc body
  - top-right header search integrated with theme selector and theme tokens
  - full-width usersum shell with theme-aware sidebar/background/scrollbar/button styling
- Implemented PostgreSQL-backed search path (`FTS + pg_trgm`) with explicit fallback behavior:
  - `wepppy/weppcloud/usersum_docs/pg_search.py`
  - usersum search API/page returns breadcrumb and role metadata
- Added/updated regression coverage:
  - `tests/weppcloud/routes/test_usersum_bp.py`
  - `tests/weppcloud/test_usersum_template_wiring.py`
  - `tests/weppcloud/routes/test_usersum_docs_contracts.py`
  - `tests/weppcloud/routes/test_usersum_docs_index.py`
- Completed required review artifacts:
  - `artifacts/code_review_findings.md`
  - `artifacts/qa_review_findings.md`

## Follow-up Work
- Optional scheduler/RQ job orchestration for periodic usersum index refresh if runtime load path needs decoupling from request handling.
- Optional search relevance tuning package once production query telemetry is available.
