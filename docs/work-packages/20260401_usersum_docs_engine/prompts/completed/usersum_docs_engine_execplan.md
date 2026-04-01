# Usersum Docs Engine: Manifest/Nav/Vendor + GitBook Layout + PostgreSQL Search

> Outcome Summary (2026-04-01): Completed milestones 1-6, shipped manifest/nav/vendor contracts + tooling, manifest-index-backed usersum runtime, GitBook-like shell updates, PostgreSQL search backend integration, and final QA/code-review remediations.

This ExecPlan is a living document. The sections `Progress`, `Surprises & Discoveries`, `Decision Log`, and `Outcomes & Retrospective` must be kept up to date as work proceeds.

This plan follows `docs/prompt_templates/codex_exec_plans.md`.

## Purpose / Big Picture

After this package, usersum documentation is no longer an implicit directory listing. Docs are explicitly curated and role-classified by manifest, rendered in a GitBook-like UX with sticky tree navigation and breadcrumbs, and searchable through a PostgreSQL-ranked API designed for future MCP use. Companion repo docs can be vendored into scoped usersum routes through a sync tool, with clear source-of-truth policy.

## Progress

- [x] (2026-04-01 16:45Z) Reviewed usersum spec, current usersum implementation, and work-package/ExecPlan requirements.
- [x] (2026-04-01 16:55Z) Created package scaffold (`package.md`, `tracker.md`, prompts/artifacts directories).
- [x] (2026-04-01 17:00Z) Authored active ExecPlan and aligned milestones to spec milestones 1-6.
- [x] (2026-04-01 18:40Z) Milestone 1 complete: implemented schema contracts and strict validation tooling.
- [x] (2026-04-01 18:55Z) Milestone 2 complete: implemented vendor sync/build pipeline and generated docs index artifact.
- [x] (2026-04-01 19:25Z) Milestone 3 complete: refactored usersum runtime to manifest-index-backed doc resolution and role visibility.
- [x] (2026-04-01 19:45Z) Milestone 4 complete: implemented GitBook-like usersum shell (header search, sticky collapsible nav tree, breadcrumbs).
- [x] (2026-04-01 20:10Z) Milestone 5 complete: implemented PostgreSQL FTS + `pg_trgm` backend and integrated usersum search endpoints.
- [x] (2026-04-01 20:40Z) Milestone 6 complete: finalized compatibility routes, validation gates, and authored code + QA review artifacts.
- [x] (2026-04-01 17:40Z) Follow-up QA pass resolved theme/layout/prefix routing issues raised after first implementation pass.

## Surprises & Discoveries

- Observation: Usersum route tests currently cover link rewriting, source-footer, and route compatibility but do not yet exercise manifest/nav-driven contracts.
  Evidence: `tests/weppcloud/routes/test_usersum_bp.py`.

- Observation: Usersum currently uses in-memory parsing and simple substring scoring; no database contract is wired yet.
  Evidence: `wepppy/weppcloud/routes/usersum/usersum.py`.

- Observation: Canonical usersum links that ignored site prefix (`/weppcloud`) failed in prefixed production deployment while legacy prefixed links still worked.
  Evidence: QA report + production URL behavior (`/usersum/doc/...` failed while `/weppcloud/usersum/view/...` succeeded).

- Observation: PostgreSQL backend instance recreation per request reset sync signature caching and increased avoidable sync churn.
  Evidence: `PostgresUsersumSearchBackend._last_synced_signature` lifecycle in request path before caching fix.

## Decision Log

- Decision: Execute all six milestones in one work package with explicit closure gates for code review and QA review artifacts.
  Rationale: Direct user request and existing work-package conventions.
  Date/Author: 2026-04-01 / Codex.

- Decision: Keep compatibility routes (`/usersum/view/...`, `/usersum/src/...`) while introducing canonical manifest-driven routing.
  Rationale: Root/usersum compatibility requirements and low-regression rollout strategy.
  Date/Author: 2026-04-01 / Codex.

- Decision: Use `url_for_run(...)` for usersum-generated links (nav, breadcrumbs, search results, header links, markdown rewrites) rather than raw route path strings.
  Rationale: Guarantees site-prefix-safe links under `/weppcloud` and proxy-prefix deployments.
  Date/Author: 2026-04-01 / Codex.

- Decision: Cache PostgreSQL search backend instances by DB URL.
  Rationale: Preserves incremental sync signature state and avoids unnecessary repeated sync operations on every request.
  Date/Author: 2026-04-01 / Codex.

## Outcomes & Retrospective

Package completed on 2026-04-01 with all milestone objectives delivered. Usersum now operates as a manifest-driven docs engine with strict contracts, generated index artifacts, vendor sync support, canonical doc identity routes, role-aware visibility enforcement, GitBook-like layout shell, and PostgreSQL-backed ranked search with explicit fallback behavior.

Post-implementation QA surfaced deployment-prefix and UX-theme gaps (canonical link prefix handling, header/search alignment, hardcoded sidebar/button styles, escaped snippet previews). These issues were resolved in the same package before closure. No unresolved medium/high findings remained after code review and QA review remediation.

Key lesson: when adding canonical route metadata into generated artifacts, runtime link emission must still defer final URL assembly to deployment-aware helpers (`url_for_run`) to avoid prefix drift between local and reverse-proxied environments.

## Context and Orientation

Current usersum implementation lives primarily in `wepppy/weppcloud/routes/usersum/usersum.py` and templates under `wepppy/weppcloud/routes/usersum/templates/usersum/`. It currently discovers docs from category roots, supports markdown render and link rewriting, and exposes parameter and keyword APIs. It now has a preliminary in-memory `/usersum/api/search`, but not the full manifest/nav/vendor and PostgreSQL search architecture defined in the updated usersum specification.

This package introduces explicit docs contracts:
- `docs_manifest.yaml`: authoritative opt-in docs metadata and role classification (`min_role`).
- `nav_tree.yaml`: authoritative navigation tree and breadcrumb lineage.
- `vendors.yaml`: authoritative vendor source configuration.
- `generated/docs_index.json`: generated runtime index from the above contracts plus source markdown inspection.

The package also introduces vendor ingestion for companion repo docs under `/usersum/vendor/<vendor_id>/...` and canonical doc identity routing under `/usersum/doc/<doc_id>`, while keeping older routes functional.

## Plan of Work

Milestone 1 adds schema files and strict validation tooling. Tooling will validate shape, uniqueness, references, and path safety constraints and will fail closed on invalid artifacts.

Milestone 2 adds vendor sync/build tooling and generated index artifact generation. It will copy approved vendor markdown files into usersum vendor roots, then generate `generated/docs_index.json`.

Milestone 3 refactors runtime loading so usersum browse/view/search resolve from generated index + manifest semantics rather than implicit directory traversal. Role visibility checks will enforce `min_role` hierarchy.

Milestone 4 updates templates/layout to a GitBook-like shell: fixed top header search, sticky collapsible tree nav, and breadcrumbs on doc pages.

Milestone 5 adds PostgreSQL-backed search with FTS + `pg_trgm`, including schema bootstrap, upsert/index sync path, ranked query, and explicit degraded behavior when search backend is unavailable.

Milestone 6 hardens compatibility routes and executes full validation plus mandatory review artifacts; medium/high findings will be fixed before closing.

## Concrete Steps

From `/workdir/wepppy`:

1. Create and validate usersum schema files and tooling:

    python3 tools/usersum_docs_tool.py validate

2. Sync initial vendor docs and regenerate runtime index:

    python3 tools/usersum_docs_tool.py sync-vendors --write
    python3 tools/usersum_docs_tool.py build-index --write

3. Run focused usersum route/template/tool tests:

    wctl run-pytest tests/weppcloud/routes/test_usersum_bp.py tests/weppcloud/test_usersum_template_wiring.py --maxfail=1

4. Run broader checks before closure:

    wctl run-pytest tests --maxfail=1
    wctl doc-lint --path docs/work-packages/20260401_usersum_docs_engine
    wctl doc-lint --path wepppy/weppcloud/routes/usersum/specification.md

5. Produce review artifacts:

    docs/work-packages/20260401_usersum_docs_engine/artifacts/code_review_findings.md
    docs/work-packages/20260401_usersum_docs_engine/artifacts/qa_review_findings.md

## Validation and Acceptance

Acceptance is met when:
- schema tooling validates manifest/nav/vendor files with strict checks;
- vendor sync imports the two approved `weppcloud-wbt` docs into usersum vendor root;
- generated usersum index is committed and used by runtime browse/view/search behavior;
- usersum shell shows fixed header search, sticky collapsible nav tree, and breadcrumbs;
- PostgreSQL search path supports FTS + trigram ranking and respects role/category filters;
- compatibility routes continue working with manifest-driven backing;
- tests and documentation lint pass;
- review artifacts exist with no unresolved medium/high findings.

## Idempotence and Recovery

Schema validation and index generation are idempotent. Vendor sync is deterministic and can be safely rerun. Compatibility routes remain in place during migration to avoid breaking existing links. If PostgreSQL indexing/search is unavailable, runtime must return explicit degraded responses instead of silently serving stale/misleading results.

## Artifacts and Notes

- Package brief: `docs/work-packages/20260401_usersum_docs_engine/package.md`
- Tracker: `docs/work-packages/20260401_usersum_docs_engine/tracker.md`
- Review artifacts:
  - `docs/work-packages/20260401_usersum_docs_engine/artifacts/code_review_findings.md`
  - `docs/work-packages/20260401_usersum_docs_engine/artifacts/qa_review_findings.md`

## Interfaces and Dependencies

Expected artifacts and interfaces at completion:
- `wepppy/weppcloud/routes/usersum/docs_manifest.yaml`
- `wepppy/weppcloud/routes/usersum/nav_tree.yaml`
- `wepppy/weppcloud/routes/usersum/vendors.yaml`
- `wepppy/weppcloud/routes/usersum/generated/docs_index.json`
- Tooling:
  - `tools/usersum_docs_tool.py` with `validate`, `sync-vendors`, and `build-index` subcommands.
- Runtime route additions:
  - `GET /usersum/doc/<doc_id>`
  - `GET /usersum/vendor/<vendor_id>/<path:filename>`
- Search backend:
  - PostgreSQL bootstrap/upsert/query path for usersum docs search.

---
Revision Note (2026-04-01, Codex): Initial active ExecPlan authored during package kickoff.
Revision Note (2026-04-01, Codex): Updated with completed milestone status, discoveries, decisions, and closure outcomes.
