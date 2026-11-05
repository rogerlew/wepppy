# Usersum Documentation Engine Specification

Status: Implemented v1.1 (2026-04-08)  
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

## Changelog table presentation

The WEPP Forest changelog keeps long compiler, version and commit metadata within
its cells. Values wrap rather than painting over neighboring columns. The table
retains a readable minimum width; on narrower viewports the document container
scrolls horizontally without widening the page. This restores the existing
readable-document layout for longer release labels; it does not change content,
navigation, access rules or link resolution. Other document tables are unaffected.

## Public Feature Catalog

Accepted 2026-10-27 at checkpoint `96f7df370`; implemented and locally validated (not deployed).
`GET /usersum/features/` renders a public Jinja page in the existing Usersum
shell. It lists every feature and interface configuration returned by the
validated registry loaders, in registry order, without filtering by login,
role, group, backend, maturity, or the Usersum role selector. Internal and
publication-embargo entries are included: open-source registry metadata is
public information, distinct from permission to execute a feature or read a
protected resource. Existing document visibility and feature authorization
remain unchanged. See the [registry specification](../../feature_registry/specification.md#public-metadata-catalog).

Separate feature and interface tables show label, stable id, maturity,
internal reason and embargo date when present, role/access policy, and backend.
Feature rows also show prerequisites; configuration rows show replacement ids
when present. Group-only policy must not be presented as role-granted access.
Configuration maturity uses effective runtime overrides, matching the existing
registry loader. This is a catalog of registered entries, not an inventory of
every unregistered application capability or project-owned Builder config.

The page links to the user guide's maturity definitions and explains that
listing does not grant access. The Usersum index links to the catalog outside
the curated document sections. No generated Markdown/index copy, search-index
entry, JavaScript dependency, run state, or account membership lookup is needed.
Shared shell navigation retains its existing document visibility behavior.

Registry text is autoescaped. Optional absent metadata displays an explicit
neutral value, and an empty registry produces an empty-state message. Invalid
registry data retains the loader's explicit failure contract; do not substitute
an empty or partial catalog on error. No caller-supplied filesystem path or
registry selector is accepted. Use application URL helpers for links so proxy
prefixes remain correct.

## Automatic ADR catalog

Status: implemented and verified on forest; contract checkpoint `0b804f1ff`.

The Help index exposes **Architecture Decision Records (ADRs)** as a standalone
dynamic link. In the sidebar, place the same link in **Start Here**, immediately
after **Quick Start** and before **Feature Maturity and Release Governance**,
using the standard navigation-link styling. This placement was explicitly
requested by the operator; no per-ADR manifest registration is required.
Sidebar placement amendment: approved direction, implementation pending. `/usersum/adrs/`
(trailing slash optional) lists every regular, non-symlink Markdown file directly
inside repository `docs/adrs/` whose filename matches
`ADR-[0-9]+-<nonempty-slug>.md`. README, templates, subdirectories and other files
are excluded. The root directory itself must resolve inside the repository and
must not be a symlink. No per-ADR manifest/nav entry, generated-index edit,
background job, database change or web-worker reload is needed when an ADR is
added, edited or removed from the source tree available to the web process.

Sort records by their explicit recorded Date, descending. Read the ISO date
immediately following a `Date:` label in the Markdown preamble before the first
section heading (H2 or deeper); support plain/bold labels and an inline label
following Status text. Use the first such field and its first ISO calendar date,
including when a suffix gives a timezone or an additional UTC date. Validate the
calendar date. Do not infer dates from status text, provenance prose, git history
or filesystem timestamps. Missing or invalid dates display **Date unavailable**
and sort after all dated records. Ties, including undated records, sort by numeric
ADR identifier descending and then filename descending. The page explains
**Newest recorded date first; undated records last**. Every matching file remains
included, including duplicate numeric IDs and proposed/superseded records.

Rationale: the operator requested reverse chronological order. Numeric ordering
is not equivalent: ADR-0028 GridMET is dated 2026-08-31, after ADR-0029 dated
2026-07-28. Explicit dates preserve the requested chronology without inventing
missing metadata. Existing ADR content is not rewritten by this feature.

Each entry shows its recorded date (or unavailable label), filename-derived ADR
identifier and first Markdown H1 title;
use the filename as the visible title if no H1 is present. Title text is escaped
by Jinja, not treated as HTML. A brief introduction explains that records describe
decisions at a point in time and readers should check each record's status.
Links open the complete document in the existing Help Markdown shell at
`/usersum/adrs/<filename>`, with Help → ADRs → document breadcrumbs and existing
GitHub/raw-source links. Preserve Markdown heading anchors and existing relative Markdown-link behavior.
For unregistered eligible ADR targets, links use the new ADR document route.
Manifest-tracked targets retain canonical routes and role checks; other Markdown
links retain existing routing. Non-Markdown assets retain existing renderer
behavior; this feature does not add generic relative PDF/image publication.

The ADR catalog and documents are public repository documentation, visible to
anonymous and authenticated readers independently of the role-discovery filter.
Dedicated ADR routes remain usable with `USERSUM_REQUIRE_MANIFEST_FOR_SRC` enabled;
the generic source route's strict-manifest behavior and all existing document
role gates remain unchanged. New ADRs are discovered on each request. They are
not automatically enrolled in full-text Help search in this bounded change.
This follows the existing Feature Catalog pattern and avoids stale manually
maintained lists or expanding the manifest/search schema.

Valid-state and failure behavior:

| State | Required behavior |
| --- | --- |
| Directory absent or empty | Successful catalog page with a clear no-records message; no invented entries or filesystem writes |
| Populated directory | Every eligible file appears exactly once in the stated order and renders through its detail link |
| Legacy ADR without date, status or H1 | Included; missing H1 uses filename; missing/invalid date sorts last; metadata omissions do not block reading |
| Added, edited or removed ADR | Next request reflects the source tree; removed document returns 404 |
| Duplicate numeric identifier | Both filenames remain visible, deterministically ordered |
| Nonmatching file, symlink, directory, traversal or encoded traversal | No listing entry and 404 on the dedicated document route; no outside-root read |
| Unreadable file or invalid UTF-8 | Explicit server error under normal error handling, never silently omitted or rendered as successful empty content |

Use the shared Help layout, ordinary links and heading structure without new
JavaScript or dependencies. Validation must use real temporary directories for
filesystem/discovery boundaries and real repository ADRs for complete route
rendering, including site-prefix URLs and cross-ADR links. Verify the empty,
legacy, populated, freshness and hostile-path states independently of role and
strict-manifest options. This feature does not authorize a production deployment
or project/run mutation. Initial rollout must load the new Python routes together with their
shared-template links. On bind-mounted development hosts, reload web workers and
verify the external Help index, catalog and document routes; template freshness
alone does not establish route registration.

## Role Model

Usersum roles are mutually exclusive at the document level.

- Canonical field: `min_role`
- Hierarchy: `user` < `operator` < `developer` < `internal`
- Visibility rule: caller can see a doc when caller max role rank >= doc `min_role`
- `audience_tags` is discovery metadata only; it does not grant access.
- Distinguish WEPPcloud user roles from usersum document roles:
  - WEPPcloud user roles and attributes determine what the caller is allowed to see.
  - usersum roles (`user`, `operator`, `developer`, `internal`) are the documentation visibility model and the values used by docs/search filters.

Role resolution is implemented in:

- `wepppy/weppcloud/routes/usersum/usersum.py::_caller_weppcloud_role_context()`
- `wepppy/weppcloud/routes/usersum/usersum.py::_caller_max_role()`

Current checks:

- anonymous -> `user`
- authenticated defaults -> `user`
- elevated signals are collected from normalized `current_user.roles` values and user attributes:
  - `is_root`, `is_admin`, `is_poweruser`
  - `is_operator`, `can_operate`
  - `is_developer`, `can_develop`
  - `is_internal_docs`, `is_internal`, `can_view_internal_docs`
- effective usersum ceiling mapping:
  - `Root` -> `internal`
  - `Admin` -> `developer`
  - `PowerUser` -> `operator`
  - otherwise -> `user`

### Header role selector policy

The header `ROLE` selector is a discovery filter, not an authorization override.

- It renders only for authenticated users with WEPPcloud roles `PowerUser`, `Admin`, or `Root`.
- Its option values come from the usersum role model, not from raw WEPPcloud role names.
- It exposes a curated subset of usersum roles based on the caller's WEPPcloud role:
  - `PowerUser` sees: `user`, `operator`
  - `Admin` sees: `user`, `operator`, `developer`
  - `Root` sees: `user`, `operator`, `developer`, `internal`
- It submits through the existing usersum search flow on change (`requestSubmit()` with `submit()` fallback).
- The selected role is preserved across `/usersum/search` refinement requests.
- The selected role ceiling is also applied to usersum shell discovery/nav rendering.
- The selector does not grant access to docs the caller could not otherwise view through the normal visibility gate.

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
- Curated nav/search documents are manifest-tracked. Standalone dynamic Feature
  Catalog and ADR catalog links are the explicit navigation exceptions; neither
  automatically adds entries to full-text search.

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
- `GET /usersum/features/` (public dynamic registry catalog; trailing slash optional)
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
  - otherwise, if the target is an eligible ADR under **Automatic ADR catalog**
    -> `/usersum/adrs/<filename>` (additive behavior; implementation pending)
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
- header includes a conditional `ROLE` selector to the left of `SEARCH` for authenticated `PowerUser`/`Admin`/`Root` callers.
- the `ROLE` selector uses the same select/input classes as the shared theme selector for visual consistency.
- left sidebar is sticky and supports collapsible nav sections.
- breadcrumbs render above page content.
- doc view pages self-report active doc role as `Role: <min_role>` directly under breadcrumbs.
- usersum shell is full width.
- sidebar/background/buttons/scrollbar follow theme tokens.

## Search API Contract

### `GET /usersum/api/search`

Query parameters:

- `q` required
- `role` optional usersum role ceiling (`user`, `operator`, `developer`, `internal`)
- `category` optional (repeated and/or comma-separated)
- `limit` optional, default `20`, max `100`
- `offset` optional, default `0`

Rules:

- invalid args -> `400`
- requested role ceiling above caller max role -> `403`
- default role ceiling if omitted -> `user`
- `role=X` should mean "show docs with `min_role` up to `X`", not "show only docs whose `min_role` exactly equals `X`"
- threshold matching should therefore include any doc where `doc.min_role <= requested_role_ceiling`
- repeated and/or comma-separated `role` values are accepted; effective requested ceiling is the highest valid requested usersum role.

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
- exposes category filtering in-page and uses the shared header `ROLE` control for role-ceiling filtering.
- preserves selected role during search refinement.
- for unauthorized requested role ceilings, renders the current page-level error path (instead of returning API JSON).

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

2. Build index (auto-syncs configured vendor docs first):

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
  - scheduled kwargs:
    - `write_index: false`
    - `require_vendor_files: false`
    - `sync_postgres: true`

Immutable-runtime note:

- Scheduled indexing is intended to be read-only on repository paths in production containers.
- The scheduler run updates PostgreSQL search state, but does not rewrite vendored markdown or `generated/docs_index.json` on disk.
- In this scheduled mode, vendor source sync is skipped; search sync uses repo-tracked usersum markdown as-is.

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
  - `tools/usersum_docs_tool.py build-index --write` (auto-syncs vendors first)
  - optional explicit sync preview/apply:
    - `tools/usersum_docs_tool.py sync-vendors`
    - `tools/usersum_docs_tool.py sync-vendors --write`

Initial vendor scope:

- `/workdir/weppcloud-wbt/docs/hydroenforcement/culvert-web-app-hydroenforcement.md`
- `/workdir/weppcloud-wbt/whitebox-tools-app/src/tools/hydro_analysis/hillslopes_topaz.spec.md`
- `/workdir/wepp-forest_260430_baseline/change-log.md`

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

## Water output interpretation publication

Implementation conformance: validated 2026-10-21 UTC (2026-10-20 documentation package), including published repository catalog and fresh-process user-role browser/search checks. Production deployment remains separate.

Publish **Understanding water balance and runoff** and **Water and PASS variables** as active user-role documents under Technical Reference. They explain local OFE versus whole-hillslope normalization, physical WAT runoff versus threshold-filtered PASS delivery, routed watershed outputs, date support, storage and producer/version limitations using the hillslope-water-aggregation contract and ADR-0099. Scientific formulas and output scope remain unchanged.

WEPP Results provides interpretation help independently of run-specific README existence, for single-storm and continuous results. The existing conditional README link is labeled **Output files, columns, and sample data**. Water reports and daily streamflow help identify their runoff source and link to interpretation. Existing prefix-safe URL helpers, access checks and baseline/Roads scopes remain in force. Missing or historical run artifacts never prevent access to general guidance and never imply current accounting conformance.

Generated interchange README text explains its per-file metadata/sample role, the distinct meanings of interchange schema version, model provenance and report accounting version, and points readers to user guidance. Previews remain bounded to three rows. Metadata descriptions must agree with the current scientific contract without changing column names, types or values. Regenerating documentation does not rewrite or certify historical data.

The rationale is to make scientific meaning discoverable before users combine fields in a spreadsheet; schemas and sample rows alone cannot communicate normalization and event filtering. Validate user-role nav/search, rendered contextual links, absent/present/legacy artifacts and actual generated metadata before claiming completion.

## Automatic deletion help (2026-11-04)

Implemented and locally validated after checkpoint `c62567f1c`; deployment separate. Preserve the existing
`usersum.weppcloud.run_ttl_deletion` identity and URL, but title the guide **Keep
your project from being automatically deleted** and place it under **Managing
projects**. Explain the inactivity period, exact **Disable automatic deletion**
steps, **Automatic deletion is disabled** confirmation, and re-enabling's fresh
90-day window before exceptions. Include natural search phrases about keeping
projects, stopping deletion and how long projects are saved. General help chrome
uses **WEPPcloud Help** and **Search help**, not internal Usersum terminology.
Contextual links from both project headers and every catalog state use **How to
keep your project**. Preserve document visibility and search architecture.

Explain that disabling automatic deletion cannot undo deletion that has already
started or restore deleted projects; avoid an indefinite storage guarantee.
