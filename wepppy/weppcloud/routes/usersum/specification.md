# Usersum Documentation Engine Specification

Status: Implemented v1 (2026-04-01)  
Scope: WEPPcloud in-app documentation at `/weppcloud/usersum/`  
Primary module: `wepppy/weppcloud/routes/usersum/`

## Objectives

- Keep documentation discoverable and navigable inside WEPPcloud.
- Use explicit manifest-driven curation instead of implicit directory listing.
- Enforce role-aware visibility with a single canonical role gate per document (`min_role`).
- Provide GitBook-like layout behaviors:
  - header search on the right
  - sticky/collapsible left navigation tree
  - breadcrumbs above document body
- Support vendored companion-repo docs under scoped usersum routes.
- Provide ranked search with PostgreSQL FTS + `pg_trgm`, with explicit fallback behavior.
- Preserve compatibility with existing usersum and command-bar endpoints.

## Role Model

Usersum roles are mutually exclusive at the document level.

- Canonical field: `min_role`
- Hierarchy: `user` < `operator` < `developer` < `internal`
- Visibility rule: caller can see a doc when caller max role rank >= doc `min_role`
- `audience_tags` is discovery metadata only; it does not grant access.

Role resolution is implemented in `wepppy/weppcloud/routes/usersum/usersum.py::_caller_max_role()` and checks:

- anonymous -> `user`
- authenticated defaults -> `user`
- elevated signals via `current_user.roles` and attributes:
  - operator-ish: `is_operator`, `is_admin`, `can_operate`
  - developer-ish: `is_developer`, `can_develop`, `is_poweruser`
  - internal-ish: `is_internal_docs`, `is_internal`, `can_view_internal_docs`

## Machine-Readable Contracts

Usersum contract artifacts (authoritative):

- `wepppy/weppcloud/routes/usersum/docs_manifest.yaml`
- `wepppy/weppcloud/routes/usersum/nav_tree.yaml`
- `wepppy/weppcloud/routes/usersum/vendors.yaml`
- generated output:
  - `wepppy/weppcloud/routes/usersum/generated/docs_index.json`

Validation and indexing implementation:

- contract loader/validator:
  - `wepppy/weppcloud/usersum_docs/docs_contracts.py`
- index builder/loader:
  - `wepppy/weppcloud/usersum_docs/docs_index.py`
- runtime catalog loader:
  - `wepppy/weppcloud/usersum_docs/runtime_catalog.py`
- CLI tooling:
  - `tools/usersum_docs_tool.py`
    - `validate`
    - `sync-vendors`
    - `build-index`

Contract highlights:

- `doc_id` is globally unique and stable.
- `rel_path` is repo-relative markdown path.
- `source` is `local` or `vendor`.
- vendor docs require `vendor_id`; vendor alias route generation expects vendor docs under configured `target_root`.
- `nav_key` in manifest must map 1:1 to a nav leaf node.
- only manifest-tracked docs are published in usersum nav/search surfaces.

PostgreSQL bootstrap/migration discoverability:

- search backend implementation:
  - `wepppy/weppcloud/usersum_docs/pg_search.py`
- runtime wiring and fallback controls:
  - `wepppy/weppcloud/routes/usersum/usersum.py` (`_postgres_search_backend`, `_search_documents`)
- docs/tooling index sync path:
  - `tools/usersum_docs_tool.py` (`validate`, `sync-vendors`, `build-index`)
- scheduled maintenance job:
  - `wepppy/rq/project_rq.py::index_usersum_docs_rq()`
  - helper implementation: `wepppy/rq/project_rq_delete.py::index_usersum_docs_rq()`
- current model: runtime idempotent DDL bootstrap (`_exec_ddl`), not formal Alembic-managed usersum search migrations yet.

## Runtime Route Contract

Implemented routes in `wepppy/weppcloud/routes/usersum/usersum.py`:

- `GET /usersum/`
- `GET /usersum/doc/<doc_id>` (canonical identity route)
- `GET /usersum/view/<category>/<path:filename>` (compatibility alias)
- `GET /usersum/vendor/<vendor_id>/<path:filename>`
- `GET /usersum/src/<path:rel_path>`
- `GET /usersum/src//<path:rel_path>` -> `308` redirect to canonical single-slash route
- `GET /usersum/raw/<path:rel_path>`
- `GET /usersum/api/parameter`
- `GET /usersum/api/keyword`
- `GET /usersum/api/search`
- `GET /usersum/search`

Visibility and path guards:

- canonical/doc/vendor/category routes resolve through manifest/index and enforce `min_role`.
- compatibility routes return `404` for unknown docs or unauthorized role visibility.
- `/usersum/src/<rel_path>` can render in-repo markdown outside manifest unless
  `USERSUM_REQUIRE_MANIFEST_FOR_SRC` is enabled.
- `/usersum/raw/<rel_path>` enforces in-repo markdown constraints and role checks when path is manifest-tracked.

## Link Resolution and Prefix Safety

Usersum uses deployment-prefix-safe URL generation with `url_for_run(...)` (not raw static route strings) for rendered navigation and links.

Key behavior:

- nav links resolve from `doc_id` using `url_for_run("usersum.view_doc", doc_id=...)`.
- breadcrumbs resolve to canonical doc routes.
- search result links resolve to canonical doc routes.
- markdown in-doc `.md` links are rewritten:
  - if target path is manifest-tracked -> canonical `/usersum/doc/<doc_id>` route
  - otherwise -> `/usersum/src/<repo-relative-path>`

This keeps links valid under prefixed deployments such as `/weppcloud/...`.

## Layout and UI Contract

Usersum templates:

- shell: `wepppy/weppcloud/routes/usersum/templates/usersum/layout.j2`
- header: `wepppy/weppcloud/routes/usersum/templates/usersum/header.htm`
- index: `wepppy/weppcloud/routes/usersum/templates/usersum/index.htm`
- view: `wepppy/weppcloud/routes/usersum/templates/usersum/view.htm`
- search: `wepppy/weppcloud/routes/usersum/templates/usersum/search.htm`

Implemented UX behavior:

- header includes shared theme selector and usersum search controls.
- search label is uppercase `SEARCH` and sits above the search input for field consistency with `THEMES`.
- left sidebar is sticky and supports collapsible nav sections.
- breadcrumbs render above page content.
- usersum shell is full width.
- sidebar/background/buttons/scrollbar follow theme tokens.

## Search API Contract

### `GET /usersum/api/search`

Query parameters:

- `q` required
- `role` optional (repeated and/or comma-separated)
- `category` optional (repeated and/or comma-separated)
- `limit` optional, default `20`, max `100`
- `offset` optional, default `0`

Rules:

- invalid args -> `400`
- requested roles above caller max role -> `403`
- default role filter if omitted -> `["user"]`

Response payload:

- `results[]` items:
  - `doc_id`
  - `title`
  - `rel_path`
  - `min_role`
  - `category`
  - `snippet` (HTML fragment rendered via `cmarkgfm`)
  - `score`
  - `breadcrumb[]`
- paging metadata:
  - `total`
  - `limit`
  - `offset`
- optional `warning` when PostgreSQL backend is unavailable and in-memory fallback is used.

### `GET /usersum/search`

- server-rendered HTML search page that uses the same backend/search logic.
- currently exposes category filtering in UI; role filtering is supported by query parsing but not surfaced as a dedicated page control.

## PostgreSQL Search Backend Contract

Implementation file:

- `wepppy/weppcloud/usersum_docs/pg_search.py`

Runtime wiring:

- `wepppy/weppcloud/routes/usersum/usersum.py::_search_documents()`
- backend factory with caching:
  - `_cached_postgres_search_backend(db_url)`

### Driver and connection discovery

- Tries `psycopg` first, then `psycopg2`.
- DB URL source precedence:
  1. `current_app.config["SQLALCHEMY_DATABASE_URI"]`
  2. `DATABASE_URL` env var
- Backend is enabled only when URL starts with `postgresql`.

### Runtime DDL bootstrap (current migration mode)

Current v1 uses idempotent runtime DDL bootstrap, not Alembic-managed usersum table migrations.

Discoverability:

- DDL definition location:
  - `PostgresUsersumSearchBackend._exec_ddl()` in `wepppy/weppcloud/usersum_docs/pg_search.py`
- sync/upsert logic:
  - `PostgresUsersumSearchBackend.ensure_synced(...)`
- query/ranking logic:
  - `PostgresUsersumSearchBackend.search(...)`

Current managed relation:

- table: `usersum_docs_search` (default)
- extension: `pg_trgm` (`CREATE EXTENSION IF NOT EXISTS pg_trgm;`)

Current columns/indexes include:

- identity/content:
  - `doc_id`, `rel_path`, `title`, `title_norm`, `headings_text`, `body_text`, `content_hash`
- metadata:
  - `min_role`, `category`, `audience_tags`, `source`, `vendor_id`, `nav_key`, `status`
- search:
  - `search_tsv` (`GIN`)
  - trigram indexes on `title_norm` and `headings_text`
- lifecycle:
  - `deleted_at`, `updated_at`

Soft deletion behavior:

- docs absent from current manifest/index sync are marked with `deleted_at = now()`
- active docs clear `deleted_at` on upsert.

### Search ranking strategy

Implemented scoring/query behavior:

- lexical query:
  - `websearch_to_tsquery('english', :query)`
- lexical score:
  - `ts_rank_cd(search_tsv, tsq, 32)`
- trigram similarity:
  - `similarity(title_norm, q_norm)`
  - `similarity(headings_text, q_norm)`
- composite score:
  - `(fts_rank * 0.85) + (trgm_rank * 0.15)`
- match predicate:
  - lexical match OR title/headings trigram thresholds
- ordering:
  - lexical hit first, then score/rank/update/doc_id
- snippets:
  - `ts_headline(...)` with fallback text.

### Runtime fallback and strictness flags

Config flags:

- `USERSUM_SEARCH_DISABLE_POSTGRES`:
  - disable PG backend and force in-memory search.
- `USERSUM_SEARCH_STRICT_POSTGRES`:
  - if PG backend fails, return error instead of fallback.

Default behavior when PG backend fails:

- API/page falls back to in-memory search over runtime catalog and includes a warning message.

## PostgreSQL Migration Setup: Operator Quick Guide

Current setup is intentionally discoverable in-code and command-line tooling:

1. Validate docs contracts:

    `PYTHONPATH=/workdir/wepppy python3 tools/usersum_docs_tool.py validate`

2. Sync vendors and build index:

    `PYTHONPATH=/workdir/wepppy python3 tools/usersum_docs_tool.py sync-vendors --write`  
    `PYTHONPATH=/workdir/wepppy python3 tools/usersum_docs_tool.py build-index --write --require-vendor-files`

3. Trigger search use once (API/search page) to bootstrap DDL and sync content.

4. Verify relation exists in PostgreSQL:

    `\dt usersum_docs_search`  
    `\d+ usersum_docs_search`

5. Verify indexed content count:

    `SELECT count(*) FROM usersum_docs_search WHERE deleted_at IS NULL AND status = 'active';`

Future migration note:

- If/when usersum search schema is moved to formal Alembic migration, add migration files under
  `wepppy/weppcloud/migrations/versions/` and keep runtime DDL path idempotent until all environments are migrated.

## Scheduled Indexing (RQ Scheduler)

Usersum indexing is also available as scheduled maintenance RQ work:

- task name: `usersum_docs_index`
- scheduled function: `wepppy.rq.project_rq.index_usersum_docs_rq`
- schedule source: `docker/scheduled-tasks.yml`
- interval source: `USERSUM_INDEX_INTERVAL_SECONDS` from `docker/.env`
  - default fallback: `14400` seconds (4 hours)
  - dev example: set `1200` for 20-minute refresh
- queue/timeout defaults:
  - queue: `batch`
  - `job_timeout`: `3600`
  - `result_ttl`: `86400`

Scheduler runtime wiring:

- scheduler runner module: `wepppy.tools.scheduler`
- scheduler config env: `SCHEDULE_CONFIG=/workdir/wepppy/docker/scheduled-tasks.yml`
- compose services:
  - `docker/docker-compose.dev.yml` (`scheduler`)
  - `docker/docker-compose.dev.hpc.yml` (`scheduler`)
  - `docker/docker-compose.prod.yml` (`scheduler`)
- scheduler parses interval tokens in `scheduled-tasks.yml` (for example `${USERSUM_INDEX_INTERVAL_SECONDS:-14400}`) at runtime.

## Vendor Sync and Authoring Policy

Vendor docs are generated/synced content.

- source-of-truth edits happen in vendor repos (for example `/workdir/weppcloud-wbt`).
- vendored copies under `wepppy/weppcloud/routes/usersum/vendor/**` are not hand-authored by default.
- approved sync flow:
  - `tools/usersum_docs_tool.py sync-vendors --write`
  - `tools/usersum_docs_tool.py build-index --write`

Initial vendor scope:

- `/workdir/weppcloud-wbt/docs/hydroenforcement/culvert-web-app-hydroenforcement.md`
- `/workdir/weppcloud-wbt/whitebox-tools-app/src/tools/hydro_analysis/hillslopes_topaz.spec.md`

Both are published as `min_role: operator`.

## Compatibility Contract

Preserved routes and behaviors:

- `/usersum/view/...` compatibility surface remains available.
- `/usersum/src//...` legacy double-slash redirect remains available.
- command-bar endpoints remain unchanged:
  - `/usersum/api/parameter`
  - `/usersum/api/keyword`

## Validation and Regression Coverage

Primary tests:

- `tests/weppcloud/routes/test_usersum_bp.py`
- `tests/weppcloud/test_usersum_template_wiring.py`
- `tests/weppcloud/routes/test_usersum_docs_contracts.py`
- `tests/weppcloud/routes/test_usersum_docs_index.py`

Recommended validation commands:

- `PYTHONPATH=/workdir/wepppy python3 tools/usersum_docs_tool.py validate`
- `PYTHONPATH=/workdir/wepppy python3 tools/usersum_docs_tool.py validate --require-vendor-files`
- `wctl run-pytest tests/weppcloud/routes/test_usersum_bp.py tests/weppcloud/test_usersum_template_wiring.py tests/weppcloud/routes/test_usersum_docs_contracts.py tests/weppcloud/routes/test_usersum_docs_index.py --maxfail=1`
- `python3 tools/check_broad_exceptions.py --enforce-changed --base-ref origin/master`

## Known Follow-Ups

- Formal Alembic-managed usersum search migrations are not yet implemented; v1 uses runtime idempotent DDL bootstrap.
