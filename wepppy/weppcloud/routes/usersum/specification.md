# Usersum Documentation Engine Specification

Status: Draft  
Scope: WEPPcloud in-app documentation at `/weppcloud/usersum/`  
Primary module: `wepppy/weppcloud/routes/usersum/`

## Objectives

- Make documentation discoverable and navigable for end users inside WEPPcloud.
- Keep documentation integrated with WEPPcloud routes/templates and command bar workflows.
- Standardize document audience classification using four roles:
  - `user`
  - `operator`
  - `developer`
  - `internal`
- Provide a GitBook-like docs shell with:
  - persistent header search
  - sticky hierarchical navigation tree with collapsible sections
  - breadcrumb context above document content
- Define a production-ready search path using PostgreSQL full-text search (FTS) + `pg_trgm`.
- Add first-class support for vendored docs from companion repositories under scoped usersum routes.
- Preserve compatibility with existing usersum endpoints and command-bar integrations.

## Role Model

Role labels describe intended audience and default visibility behavior.

### Role assignment contract (decision)

- Roles are **mutually exclusive** at the document level.
- Each document has one canonical classification field: `min_role`.
- Visibility uses role hierarchy:
  - `user` < `operator` < `developer` < `internal`
- A caller may view a document when caller role rank >= document `min_role`.
- Optional `audience_tags` may be stored for discovery UX, but do not grant access and do not replace `min_role`.

### `user`

- Purpose: End-user guidance and product workflows.
- Examples: Control usage, parameter explanations, common troubleshooting.
- Default visibility: Public in usersum UI and default search.

### `operator`

- Purpose: Deployment, operations, incident response, and support runbooks.
- Examples: Queue diagnostics, deployment checks, service restart procedures.
- Default visibility: Visible in usersum when operator scope is enabled (or authenticated role permits).

### `developer`

- Purpose: Contributor and extension documentation for code-level work.
- Examples: API contracts, architecture notes, implementation patterns.
- Default visibility: Visible to contributor/developer scope; excluded from default end-user search.

### `internal`

- Purpose: Restricted/internal-only references, drafts, or sensitive process notes.
- Examples: Internal playbooks, security-sensitive notes not intended for public exposure.
- Default visibility: Excluded from default usersum navigation and search results unless explicitly authorized.

## Existing Implementation Specification (Current State)

This section describes behavior currently implemented in code.

## Content Roots

Usersum index currently enumerates markdown files from:

- `wepppy/weppcloud/routes/usersum/db`
- `wepppy/weppcloud/routes/usersum/input-file-specifications`
- `wepppy/weppcloud/routes/usersum/weppcloud`
- `wepppy/weppcloud/routes/usersum/path`

Index listing is generated dynamically from `*.md` files in each root.

## Rendering Model

- Markdown rendering: `cmarkgfm.github_flavored_markdown_to_html`.
- Template shell: `templates/usersum/layout.j2`.
- Header partial: `templates/usersum/header.htm`.
- Document view template: `templates/usersum/view.htm`.
- Index template: `templates/usersum/index.htm`.
- Current page title: `WEPPcloud UserSummary Documentation`.

Notes:

- `layout.j2` extends `base_pure.htm` and inherits shared WEPPcloud theme bootstrap/runtime (including `theme.js`).
- Usersum header uses WEPPcloud branding and includes shared theme picker (`header/_theme_switcher.htm`).
- Child templates (`index.htm`, `view.htm`) render into `layout.j2` via `body_content` block for consistent shell/header behavior.
- In-page heading anchors (`id` on `h1..h6`) are injected server-side at render time using `usersum_anchor_slug(...)`.
- In-repo markdown links are rewritten to usersum routes (`/usersum/view/...` or `/usersum/src/...`) while preserving query/fragment components.
- No role-based content filtering is currently applied.

## `usersum_doc_link` Helper Contract (Current State)

Helper location:

- `wepppy/weppcloud/_jinja_filters.py`

Current signature:

```jinja2
usersum_doc_link(category, filename, label, classes='wc-link wc-link--file', section=None)
```

Current behavior:

- `category == 'src'` routes to `usersum.view_src_markdown`.
- Otherwise routes to `usersum.view_markdown` with `<category>/<filename>`.
- Optional `section` is normalized with `usersum_anchor_from_section(...)` and appended as a URL fragment.
- Link output includes:
  - `target="_blank"`
  - `rel="noopener"`
  - `data-open-tab-pref`

Guidance:

- Use category routes (`db`, `input-file-specifications`, `weppcloud`, `path`) for documents already under usersum content roots.
- Use `category='src'` for in-repo markdown outside usersum roots (for example module READMEs).
- Prefer human-readable heading text for `section` (for example `"PowerUser Panel"`), not hand-built slug strings.
- If an explicit heading id already exists, `section` may include it with or without `#`.

Examples:

```jinja2
{{ usersum_doc_link('weppcloud', 'wepp-model.md', 'WEPP Model overview') }}
{{ usersum_doc_link('src', 'wepppy/nodb/mods/roads/README.md', 'Roads documentation') }}
{{ usersum_doc_link('src', 'wepppy/nodb/mods/baer/README.sbs_map.md', 'SBS map preparation guidance', section='Preparing SBS Map for wepp.cloud') }}
```

## Anchor Contract (Current State)

- Rendered markdown headings (`h1..h6`) are assigned deterministic ids when missing.
- Slug normalization behavior (`usersum_anchor_slug`):
  - HTML tags stripped
  - whitespace collapsed
  - lowercase
  - non-word/non-hyphen characters removed
  - spaces converted to hyphen
  - repeated hyphens collapsed
- Duplicate heading ids are disambiguated with numeric suffixes (`-1`, `-2`, ...).
- `usersum_doc_link(..., section=...)` uses the same normalization path, so helper-generated fragments match rendered heading ids.

## Document Footer Contract (Current State)

Each rendered usersum doc page includes a source footer in `templates/usersum/view.htm`:

- Scoped path label:
  - `view:<category>/<filename>` for category-routed docs
  - `src:<repo-relative-path>` for source-routed docs
- GitHub link:
  - built from `_GITHUB_BLOB_BASE_URL` + URL-encoded repo-relative markdown path
  - current base: `https://github.com/rogerlew/wepppy/blob/master`
- Raw markdown link:
  - `.md` footer link points to `/usersum/raw/<repo-relative-path>`
  - response content-type is `text/markdown`

Guidance:

- Do not hardcode GitHub/blob/raw links in usersum content for in-repo docs; rely on the footer contract.
- Keep markdown references inside docs as normal `.md` links; usersum rewrites them to routed links at render time.

## Template and Theme Regression Coverage (Current State)

- Coverage file: `tests/weppcloud/test_usersum_template_wiring.py`.
- Current assertions include:
  - `layout.j2` extends `base_pure.htm`.
  - usersum header include is present in layout.
  - markdown stylesheet wiring is present.
  - header includes WEPPcloud brand link and theme switcher include.
  - `/usersum/` render smoke test verifies header + theme selector + `theme.js` wiring.

Additional coverage:

- `tests/weppcloud/routes/test_usersum_bp.py`
  - markdown link rewriting for category and source docs
  - footer scoped path labels + GitHub/raw links
  - canonical/legacy src route behavior
  - heading anchor id injection
  - raw markdown endpoint behavior
- `tests/weppcloud/test_jinja_filters.py`
  - `usersum_doc_link` route generation
  - `section` fragment normalization for both category and source routes

## HTTP Endpoints

### `GET /usersum/`

- Returns usersum index HTML page with grouped links to markdown documents in configured roots.

### `GET /usersum/view/<category>/<path:filename>`

- Renders markdown file from an allowed category root.
- Allowed `category` values:
  - `db`
  - `input-file-specifications`
  - `weppcloud`
  - `path`
- 404 behavior:
  - Unknown category
  - File missing
  - Path traversal attempt outside category root

### `GET /usersum/src/<path:rel_path>`

- Renders arbitrary in-repo markdown file by repo-relative path.
- Constraints:
  - Must resolve to an existing file.
  - Must end with `.md`.
  - Must remain under repository root.
- Important capability:
  - This endpoint can render markdown outside usersum content roots, as long as it is an in-repo `.md` file.
- Current security posture:
  - No role-based access controls are applied at this endpoint in current implementation.

### `GET /usersum/src//<path:rel_path>`

- Legacy compatibility endpoint.
- Behavior: permanent redirect (`308`) to canonical `/usersum/src/<path:rel_path>`.

### `GET /usersum/raw/<path:rel_path>`

- Returns raw markdown bytes for a repo-relative markdown file.
- Uses the same in-repo path validation constraints as `/usersum/src/<path:rel_path>`.
- Response content type: `text/markdown`.

### `GET /usersum/api/parameter?name=<parameter>[&extended=1]`

- Lookup endpoint used by command bar and hover previews.
- Source corpus: parsed parameter docs under `usersum/db/*.md`.
- Response:
  - `200` with `{"lines": [...]}` for matches
  - `404` with `{"error": {"message": ...}}` when not found
  - `400` when `name` is missing

### `GET /usersum/api/keyword?q=<term>`
### `GET /usersum/api/keyword?keyword=<term>`

- Keyword search endpoint over parsed parameter catalog.
- Matching mode: case-insensitive substring over prebuilt `search_blob`.
- Result cap: 25 entries.
- Response:
  - `200` with `{"lines": [...]}` (including no-match text line)
  - `400` when keyword is missing/blank

## Current Search/Indexing Behavior

- In-memory parsing from markdown parameter files only.
- Cache: `@lru_cache(maxsize=1)` for catalog build.
- No incremental invalidation; process restart required to pick up file changes after first load.
- No cross-document full-text search for the broader docs corpus.
- No typo tolerance, stemming controls, faceting, relevance tuning, or pagination.

## Existing Integrations

- Command bar `usersum` command calls:
  - `/usersum/api/parameter`
  - `/usersum/api/keyword`
- Hover previews for `data-usersum="<parameter>"` call `/usersum/api/parameter`.
- UI links currently point to usersum from multiple pages (for example, header and power-user panel).
- Control descriptions and UI text can deep-link usersum docs through `usersum_doc_link(...)`, including optional section anchors.

## Gaps (Current State vs Target)

- No formal document metadata model (`role`, `tags`, lifecycle, visibility flags).
- No global documentation index across selected repo docs.
- No ranked full-text search.
- No canonical search API for UI + MCP clients.
- No explicit authorization policy tied to role labels.

## Information Architecture Contracts (Target)

Usersum moves from implicit filesystem discovery to explicit manifest-driven docs.

### Required machine-readable artifacts

- `docs_manifest.yaml`
  - Canonical allowlist of tracked docs and their metadata (`min_role`, category, status, nav binding).
- `nav_tree.yaml`
  - Canonical hierarchical tree used by sidebar navigation and breadcrumb derivation.
- `vendors.yaml`
  - Canonical vendor-source mapping and sync configuration for companion repositories.
- `generated/docs_index.json` (generated, committed)
  - Resolved runtime index joining manifest + nav + vendor metadata for fast load and deterministic behavior.

### `docs_manifest.yaml` schema (v1)

```yaml
version: 1
docs:
  - doc_id: usersum.weppcloud.mods_overview
    source: local            # local | vendor
    rel_path: wepppy/weppcloud/routes/usersum/weppcloud/mods-overview.md
    title: Mods Overview
    min_role: user           # user | operator | developer | internal
    category: weppcloud
    audience_tags: [user, developer]
    status: active           # active | deprecated | draft
    nav_key: weppcloud.mods.overview
  - doc_id: vendor.weppcloud_wbt.culvert_web_app_hydroenforcement
    source: vendor
    vendor_id: weppcloud-wbt
    rel_path: wepppy/weppcloud/routes/usersum/vendor/weppcloud-wbt/docs/hydroenforcement/culvert-web-app-hydroenforcement.md
    title: Culvert Web App Hydroenforcement
    min_role: operator
    category: vendor-weppcloud-wbt
    audience_tags: [operator]
    status: active
    nav_key: vendor.weppcloud_wbt.hydroenforcement.culvert_web_app
  - doc_id: vendor.weppcloud_wbt.hillslopes_topaz_spec
    source: vendor
    vendor_id: weppcloud-wbt
    rel_path: wepppy/weppcloud/routes/usersum/vendor/weppcloud-wbt/whitebox-tools-app/src/tools/hydro_analysis/hillslopes_topaz.spec.md
    title: Hillslopes Topaz Specification
    min_role: operator
    category: vendor-weppcloud-wbt
    audience_tags: [operator, developer]
    status: active
    nav_key: vendor.weppcloud_wbt.hydro_analysis.hillslopes_topaz_spec
```

Contract:

- `doc_id` is globally unique and stable.
- `rel_path` is repo-relative and markdown-only.
- `min_role` is required and mutually exclusive.
- `nav_key` must resolve to exactly one `nav_tree` node with `doc_id`.
- Docs not present in manifest are not published in usersum navigation/search.

### `nav_tree.yaml` schema (v1)

```yaml
version: 1
roots:
  - key: weppcloud
    title: WEPPcloud Guides
    collapsible: false
    children:
      - key: weppcloud.mods
        title: Mods
        collapsible: true
        children:
          - key: weppcloud.mods.overview
            doc_id: usersum.weppcloud.mods_overview
  - key: vendor.weppcloud_wbt
    title: WEPPcloud WBT
    collapsible: true
    children:
      - key: vendor.weppcloud_wbt.hydroenforcement
        title: Hydroenforcement
        collapsible: true
        children:
          - key: vendor.weppcloud_wbt.hydroenforcement.culvert_web_app
            doc_id: vendor.weppcloud_wbt.culvert_web_app_hydroenforcement
      - key: vendor.weppcloud_wbt.hydro_analysis
        title: Hydro Analysis
        collapsible: true
        children:
          - key: vendor.weppcloud_wbt.hydro_analysis.hillslopes_topaz_spec
            doc_id: vendor.weppcloud_wbt.hillslopes_topaz_spec
```

Contract:

- Tree nodes are one of:
  - section node: `key`, `title`, `children[]`, optional `collapsible`
  - leaf node: `key`, `doc_id`
- Keys are unique across the full tree.
- Leaf `doc_id` values must exist in `docs_manifest.yaml`.
- Breadcrumbs are derived from ancestor titles in `nav_tree`.

### `vendors.yaml` schema (v1)

```yaml
version: 1
vendors:
  - vendor_id: weppcloud-wbt
    source_repo_path: /workdir/weppcloud-wbt
    source_ref: main
    include_globs:
      - "docs/hydroenforcement/culvert-web-app-hydroenforcement.md"
      - "whitebox-tools-app/src/tools/hydro_analysis/hillslopes_topaz.spec.md"
    exclude_globs: ["**/node_modules/**"]
    target_root: wepppy/weppcloud/routes/usersum/vendor/weppcloud-wbt
    route_prefix: /usersum/vendor/weppcloud-wbt
```

Contract:

- `vendor_id` is stable and unique.
- `target_root` is generated content under usersum.
- `route_prefix` is reserved namespace for vendor docs.

## Target Specification: PostgreSQL FTS + `pg_trgm`

PostgreSQL FTS + `pg_trgm` is the preferred next implementation step because PostgreSQL already exists in the stack, reducing operational complexity and new-service risk.

## Dependencies

- PostgreSQL extension: `pg_trgm` (required).
- Optional extension: `unaccent` (recommended for better matching).

## Layout and Navigation UX Contract (Target)

Usersum adopts a GitBook-like shell optimized for dense documentation.

- Header:
  - fixed top header across usersum routes
  - search input anchored top-right
  - keyboard hint affordance (for example `Ctrl/Cmd + K`) is allowed
- Navigation pane:
  - left sidebar is static/sticky relative to viewport and does not scroll with document content
  - tree is manifest/nav-driven (not raw directory listing)
  - section nodes are collapsible
  - active document path auto-expands ancestors
- Content pane:
  - breadcrumbs rendered above document title/body
  - only content pane scrolls for long docs
  - current heading anchors remain supported

### Breadcrumb contract

- Breadcrumb items derive from `nav_tree.yaml` ancestor titles, ending at the active document.
- Breadcrumb links must target usersum routes (not raw filesystem paths).
- If a doc is reachable from multiple branches, one canonical breadcrumb path is selected in `generated/docs_index.json`.

## Document Metadata Contract

Each indexed document must have:

- `doc_id` (stable unique key)
- `rel_path` (repo-relative markdown path)
- `title`
- `min_role` (`user` | `operator` | `developer` | `internal`)
- `category` (navigation grouping)
- `audience_tags` (string array, optional discovery labels)
- `source` (`local` | `vendor`)
- `vendor_id` (nullable for local docs)
- `nav_key` (tree node binding key)
- `status` (`active` | `deprecated` | `draft`, optional but recommended)
- `body_markdown`
- `body_text` (normalized plain text)
- `updated_at`
- `content_hash` (for change detection)

## Suggested Schema

```sql
CREATE EXTENSION IF NOT EXISTS pg_trgm;

CREATE TABLE usersum_docs (
  doc_id TEXT PRIMARY KEY,
  rel_path TEXT NOT NULL UNIQUE,
  title TEXT NOT NULL,
  title_norm TEXT NOT NULL,
  headings_text TEXT NOT NULL DEFAULT '',
  min_role TEXT NOT NULL CHECK (min_role IN ('user', 'operator', 'developer', 'internal')),
  category TEXT NOT NULL,
  audience_tags TEXT[] NOT NULL DEFAULT '{}',
  source TEXT NOT NULL CHECK (source IN ('local', 'vendor')),
  vendor_id TEXT NULL,
  nav_key TEXT NOT NULL,
  status TEXT NOT NULL DEFAULT 'active',
  body_markdown TEXT NOT NULL,
  body_text TEXT NOT NULL,
  search_tsv tsvector NOT NULL,
  deleted_at TIMESTAMPTZ NULL,
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  content_hash TEXT NOT NULL
);

CREATE INDEX usersum_docs_search_tsv_gin ON usersum_docs USING GIN (search_tsv);
CREATE INDEX usersum_docs_title_trgm_gin ON usersum_docs USING GIN (title_norm gin_trgm_ops);
CREATE INDEX usersum_docs_headings_trgm_gin ON usersum_docs USING GIN (headings_text gin_trgm_ops);
CREATE INDEX usersum_docs_min_role_idx ON usersum_docs (min_role);
CREATE INDEX usersum_docs_category_idx ON usersum_docs (category);
CREATE INDEX usersum_docs_status_idx ON usersum_docs (status);
CREATE INDEX usersum_docs_vendor_idx ON usersum_docs (vendor_id);
```

## Ingestion and Indexing

- Source selection is manifest-driven (explicit allowlist), not blind indexing of all repo markdown.
- Ingestion pipeline:
  1. Read `docs_manifest.yaml` rows (`doc_id`, `rel_path`, `min_role`, category, `audience_tags`, `status`, `source`, `vendor_id`, `nav_key`, title override).
  2. Read `nav_tree.yaml` and validate `nav_key` + `doc_id` bindings.
  3. Read `vendors.yaml` and validate vendor references used by manifest rows.
  4. Resolve source markdown from local or vendored roots.
  5. Normalize markdown to plain text and headings.
  6. Build `search_tsv` using weighted fields (title > headings > body).
  7. Upsert changed documents using `content_hash`.
  8. Mark documents absent from current manifest/file scan as tombstoned (`status='deleted'`, `deleted_at=now()`).
  9. Emit `generated/docs_index.json` for runtime load (includes nav ancestry and breadcrumb path per doc).
- Generated artifact policy:
  - `generated/docs_index.json` is committed and treated as build output derived from manifest + nav + source content.
  - Runtime reads the generated artifact; it does not infer tree/roles directly from arbitrary filesystem state.
- Deletion semantics:
  - Tombstoned documents are excluded from all UI/API search and navigation results.
  - Hard-delete is allowed only in explicit maintenance jobs after retention window.
- Reindex modes:
  - full rebuild
  - incremental rebuild (changed files only)
- Failure handling:
  - Rebuild writes to staging table and swaps atomically only on success.
  - Failed rebuild must not replace last known-good index.

## Indexing Schedule and Startup Behavior (Target)

Indexing must not block WEPPcloud container readiness.

- Startup contract:
  - Web app startup does not wait for index build completion.
  - If no fresh index exists, usersum search returns a degraded-but-explicit response (`503` with retry guidance) while docs browse pages remain available.
- Background execution:
  - Index jobs run through RQ as asynchronous tasks.
  - Use a dedicated low-concurrency queue (for example `usersum-index`) to isolate indexing from user-facing job classes.
- Trigger model:
  - On deploy/startup: enqueue one deferred incremental sync (after health checks and initial service stabilization window).
  - Periodic incremental sync: scheduler-driven (short interval, for example every 5-15 minutes).
  - Periodic full rebuild: scheduler-driven (off-peak window, for example nightly).
  - Manual rebuild: explicit admin/operator trigger for controlled maintenance.
- Concurrency controls:
  - Single-flight lock around index writes (PostgreSQL advisory lock or equivalent).
  - If a run is already active, subsequent triggers are skipped/coalesced.
- Safety controls:
  - Reindex jobs use bounded timeout and structured progress logging.
  - Failed runs leave prior index active; no partial index is published.
  - Rebuild publish step is atomic.

## Search Query Strategy

Combine lexical relevance (FTS) with typo-tolerant similarity (`pg_trgm`).

Required strategy:

- Query parser:
  - `tsq = websearch_to_tsquery('english', :q)`
- Lexical rank:
  - `fts_rank = ts_rank_cd(search_tsv, tsq, 32)`
- Trigram signals:
  - `title_sim = similarity(title_norm, :q_norm)`
  - `headings_sim = similarity(headings_text, :q_norm)`
  - `trgm_rank = GREATEST(title_sim, headings_sim)`
- Match predicate:
  - `search_tsv @@ tsq`
  - OR `title_sim >= 0.35`
  - OR `headings_sim >= 0.30`
- Unified score:
  - `score = (fts_rank * 0.85) + (trgm_rank * 0.15)`
- Ordering contract:
  - first `lexical_hit DESC` where `lexical_hit = (search_tsv @@ tsq)`
  - then `score DESC`
  - then `fts_rank DESC`
  - then `updated_at DESC`
  - then `doc_id ASC`

Use `ts_headline(...)` to generate snippets for results.

## Authorization and Role Enforcement (Target)

Authorization is server-enforced. Client-provided `role` filters are never trusted directly.

### Effective role mapping

- Anonymous caller:
  - max role: `user`
- Authenticated caller (default):
  - max role: `user`
- Authenticated caller with operator privilege:
  - max role: `operator`
- Authenticated caller with developer privilege:
  - max role: `developer`
- Authenticated caller with internal-docs privilege:
  - max role: `internal`

Exact privilege checks must be wired to WEPPcloud auth roles/claims in implementation.

### Enforcement rules

- `GET /usersum/api/search`:
  - server computes effective visibility using role hierarchy and each doc's `min_role`
  - optional `role` query filter narrows scope; requested scopes above caller max role return `403`
  - if no `role` param is provided, default query scope is `['user']`
- `GET /usersum/` and `GET /usersum/view/...`:
  - navigation and direct doc views must enforce `min_role` visibility for target documents
- `GET /usersum/src/<path:rel_path>`:
  - production mode must require both:
    - path exists in docs manifest
    - caller has sufficient role for document `min_role`
  - disallowed documents return `404` (do not leak existence)

### `src` route policy

- Canonical endpoint: `GET /usersum/src/<path:rel_path>` (single slash).
- Compatibility endpoint: `GET /usersum/src//<path:rel_path>` performs permanent redirect to canonical path.
- Dev-only escape hatch (disabled by default):
  - optional config gate for broad repo markdown rendering during development only.

## API Additions (Target)

### `GET /usersum/api/search`

Query params:

- `q` (required)
- `role` (optional, repeated or comma-separated; requested scopes must not exceed caller max role)
- `category` (optional filter)
- `limit` (default 20, max 100)
- `offset` (default 0)

Response:

- `200`:
  - `results[]` with `doc_id`, `title`, `rel_path`, `min_role`, `category`, `snippet`, `score`, `breadcrumb[]`
  - `total`, `limit`, `offset`
- `400` for missing/invalid query args.
- `403` when caller requests unauthorized role scope.

### `GET /usersum/search`

- HTML search page using same backend query contract.
- Supports role/category filters and pagination.

### `GET /usersum/vendor/<vendor_id>/<path:filename>`

- Renders vendored markdown under the configured vendor namespace.
- Path must resolve under vendor `target_root` configured in `vendors.yaml`.
- Document must exist in `docs_manifest.yaml` and pass `min_role` visibility checks.
- Unknown vendor, missing file, manifest mismatch, or unauthorized access returns `404`.

### `GET /usersum/doc/<doc_id>` (recommended canonical route)

- Resolves and renders docs by stable manifest identity (`doc_id`).
- Supports canonical link generation for breadcrumbs/search results.
- Existing category/path routes may remain as compatibility aliases during migration.

## Compatibility Requirements

- Keep existing endpoints functional:
  - `/usersum/`
  - `/usersum/view/...`
  - `/usersum/src/...` (canonical)
  - `/usersum/src//...` (compatibility redirect)
  - `/usersum/raw/...`
  - `/usersum/api/parameter`
  - `/usersum/api/keyword`
- Existing command bar `usersum` behaviors remain valid.
- Role metadata rollout must be additive and backward-compatible.
- During migration, `/usersum/view/<category>/<path:filename>` and `/usersum/src/<path:rel_path>` may remain compatibility surfaces mapped to canonical manifest docs.

## Vendor Documentation Sync and Authoring Policy (Target)

### Sync model

- Vendor docs are synchronized by a dedicated build/sync script (for example `tools/usersum_sync_vendors.py`).
- Sync process:
  1. Read `vendors.yaml`.
  2. Pull/copy allowlisted markdown from each vendor source.
  3. Write generated files to `wepppy/weppcloud/routes/usersum/vendor/<vendor_id>/`.
  4. Regenerate `generated/docs_index.json`.
  5. Emit sync metadata (source ref/commit) for review traceability.
- Generated vendor docs are committed to `wepppy` for deterministic deploy/runtime behavior.

### Authoring policy

- Do not directly author generated vendor markdown under `usersum/vendor/**`.
- Canonical edits occur in the source vendor repository (for example `/workdir/weppcloud-wbt`), then synced into `wepppy`.
- CI/presubmit must detect unsynced drift between generated content and sync script output.
- Exceptions (emergency hotfix edits in vendored copy) require follow-up backport to source repo and immediate re-sync.

### Initial vendor scope (confirmed)

- `/workdir/weppcloud-wbt/docs/hydroenforcement/culvert-web-app-hydroenforcement.md`
  - publish with `min_role: operator`
- `/workdir/weppcloud-wbt/whitebox-tools-app/src/tools/hydro_analysis/hillslopes_topaz.spec.md`
  - publish with `min_role: operator`

## Role-Aware Visibility Rules (Target)

Default behavior for unauthenticated/general users:

- Include: `user`
- Exclude by default: `operator`, `developer`, `internal`

Authenticated or privileged contexts may opt in additional scopes only when server-side authorization allows it.

Visibility check uses role hierarchy against each document `min_role`.

## MCP-Oriented Capability (Target)

Expose docs search/retrieval via MCP-friendly surface after API stabilization:

- `docs.search(query, role[], category?, limit?, offset?)`
- `docs.get(doc_id | rel_path)`
- `docs.related(doc_id, limit?)` (optional phase 2)

This supports agent workflows without requiring full HTML page scraping.

## Phased Delivery Plan (Specification-Level)

1. Define and validate schemas for `docs_manifest.yaml`, `nav_tree.yaml`, and `vendors.yaml` (with strict validation tooling).
2. Implement vendor sync/build pipeline and generated index artifact (`generated/docs_index.json`).
3. Switch usersum runtime to manifest/nav-index-backed resolution for browse/view/search.
4. Implement GitBook-like shell: fixed header search, sticky collapsible nav tree, breadcrumbs.
5. Wire PostgreSQL FTS + `pg_trgm` search backend against manifest-curated corpus.
6. Keep compatibility routes active until canonical `doc_id`/vendor routes are fully adopted.

## Non-Goals (This Spec)

- Replacing usersum with a separate external docs site generator.
- Indexing all markdown in repo without curation.
- Introducing OpenSearch/Meilisearch in initial implementation phase.

## Acceptance Criteria

- Users can search and open curated docs from `/weppcloud/usersum/`.
- Usersum pages provide:
  - header search in top-right
  - sticky/collapsible tree navigation pane
  - breadcrumb links above content
- Search returns relevant results with typo tolerance and snippets.
- Document roles are enforced in search/navigation visibility.
- Existing command-bar parameter lookup continues to work unchanged.
- New search endpoints are stable enough to back a future MCP tool.
- Vendor docs from configured companion repositories are available under scoped routes (for example `/usersum/vendor/weppcloud-wbt/...`) and respect the same role/nav/search contracts.
- Vendored content drift is enforceable by sync tooling and CI checks.
- `GET /usersum/api/search` p95 latency <= 250 ms and p99 <= 500 ms on production-like hardware at target corpus size.
- `GET /usersum/api/search` monthly availability >= 99.9% and 5xx error rate < 0.5%.
- Incremental index freshness SLO <= 5 minutes from indexed content change to searchable availability.
- Full rebuild SLO <= 30 minutes for target corpus size and produces zero stale/tombstoned leaks.
- Relevance quality gate on maintained query set:
  - top-3 contains at least one relevant result >= 90%
  - top-10 contains at least one relevant result >= 98%
