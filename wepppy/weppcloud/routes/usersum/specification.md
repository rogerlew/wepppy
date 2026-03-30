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
- Define a production-ready search path using PostgreSQL full-text search (FTS) + `pg_trgm`.
- Preserve compatibility with existing usersum endpoints and command-bar integrations.

## Role Model

Role labels describe intended audience and default visibility behavior.

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
- No role-based content filtering is currently applied.

## Template and Theme Regression Coverage (Current State)

- Coverage file: `tests/weppcloud/test_usersum_template_wiring.py`.
- Current assertions include:
  - `layout.j2` extends `base_pure.htm`.
  - usersum header include is present in layout.
  - markdown stylesheet wiring is present.
  - header includes WEPPcloud brand link and theme switcher include.
  - `/usersum/` render smoke test verifies header + theme selector + `theme.js` wiring.

## HTTP Endpoints

### `GET /usersum/`

- Returns usersum index HTML page with grouped links to markdown documents in configured roots.

### `GET /usersum/view/<category>/<path:filename>`

- Renders markdown file from an allowed category root.
- Allowed `category` values:
  - `db`
  - `input-file-specifications`
  - `weppcloud`
- 404 behavior:
  - Unknown category
  - File missing
  - Path traversal attempt outside category root

### `GET /usersum/src//<path:rel_path>`

- Renders arbitrary in-repo markdown file by repo-relative path.
- Constraints:
  - Must resolve to an existing file.
  - Must end with `.md`.
  - Must remain under repository root.
- Important capability:
  - This endpoint can render markdown outside usersum content roots, as long as it is an in-repo `.md` file.
- Current security posture:
  - No role-based access controls are applied at this endpoint in current implementation.

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

## Gaps (Current State vs Target)

- No formal document metadata model (`role`, `tags`, lifecycle, visibility flags).
- No global documentation index across selected repo docs.
- No ranked full-text search.
- No canonical search API for UI + MCP clients.
- No explicit authorization policy tied to role labels.

## Target Specification: PostgreSQL FTS + `pg_trgm`

PostgreSQL FTS + `pg_trgm` is the preferred next implementation step because PostgreSQL already exists in the stack, reducing operational complexity and new-service risk.

## Dependencies

- PostgreSQL extension: `pg_trgm` (required).
- Optional extension: `unaccent` (recommended for better matching).

## Document Metadata Contract

Each indexed document must have:

- `doc_id` (stable unique key)
- `rel_path` (repo-relative markdown path)
- `title`
- `role` (`user` | `operator` | `developer` | `internal`)
- `category` (navigation grouping)
- `tags` (string array)
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
  role TEXT NOT NULL CHECK (role IN ('user', 'operator', 'developer', 'internal')),
  category TEXT NOT NULL,
  tags TEXT[] NOT NULL DEFAULT '{}',
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
CREATE INDEX usersum_docs_role_idx ON usersum_docs (role);
CREATE INDEX usersum_docs_category_idx ON usersum_docs (category);
CREATE INDEX usersum_docs_status_idx ON usersum_docs (status);
```

## Ingestion and Indexing

- Source selection is manifest-driven (explicit allowlist), not blind indexing of all repo markdown.
- Ingestion pipeline:
  1. Read manifest rows (`rel_path`, role, category, tags, title override).
  2. Load markdown from repo.
  3. Normalize to plain text.
  4. Build `search_tsv` using weighted fields (title > headings > body).
  5. Upsert changed documents using `content_hash`.
  6. Mark documents absent from current manifest/file scan as tombstoned (`status='deleted'`, `deleted_at=now()`).
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
  - allowed roles: `['user']`
- Authenticated caller (default):
  - allowed roles: `['user']`
- Authenticated caller with operator privilege:
  - allowed roles: `['user', 'operator']`
- Authenticated caller with developer privilege:
  - allowed roles: `['user', 'operator', 'developer']`
- Authenticated caller with internal-docs privilege:
  - allowed roles: `['user', 'operator', 'developer', 'internal']`

Exact privilege checks must be wired to WEPPcloud auth roles/claims in implementation.

### Enforcement rules

- `GET /usersum/api/search`:
  - server computes `effective_roles = requested_roles ∩ allowed_roles`
  - if `requested_roles` includes any disallowed role, return `403`
  - if no `role` param is provided, default query role set is `['user']`
- `GET /usersum/` and `GET /usersum/view/...`:
  - navigation and direct doc views must enforce role visibility for target documents
- `GET /usersum/src/<path:rel_path>`:
  - production mode must require both:
    - path exists in docs manifest
    - caller has required role for that path
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
- `role` (optional, repeated or comma-separated; requested roles must be a subset of caller-allowed roles)
- `category` (optional filter)
- `limit` (default 20, max 100)
- `offset` (default 0)

Response:

- `200`:
  - `results[]` with `doc_id`, `title`, `rel_path`, `role`, `category`, `snippet`, `score`
  - `total`, `limit`, `offset`
- `400` for missing/invalid query args.
- `403` when caller requests unauthorized roles.

### `GET /usersum/search`

- HTML search page using same backend query contract.
- Supports role/category filters and pagination.

## Compatibility Requirements

- Keep existing endpoints functional:
  - `/usersum/`
  - `/usersum/view/...`
  - `/usersum/src/...` (canonical)
  - `/usersum/src//...` (compatibility redirect)
  - `/usersum/api/parameter`
  - `/usersum/api/keyword`
- Existing command bar `usersum` behaviors remain valid.
- Role metadata rollout must be additive and backward-compatible.

## Role-Aware Visibility Rules (Target)

Default behavior for unauthenticated/general users:

- Include: `user`
- Exclude by default: `operator`, `developer`, `internal`

Authenticated or privileged contexts may opt in additional roles only when server-side authorization allows it.

## MCP-Oriented Capability (Target)

Expose docs search/retrieval via MCP-friendly surface after API stabilization:

- `docs.search(query, role[], category?, limit?, offset?)`
- `docs.get(doc_id | rel_path)`
- `docs.related(doc_id, limit?)` (optional phase 2)

This supports agent workflows without requiring full HTML page scraping.

## Non-Goals (This Spec)

- Replacing usersum with a separate external docs site generator.
- Indexing all markdown in repo without curation.
- Introducing OpenSearch/Meilisearch in initial implementation phase.

## Acceptance Criteria

- Users can search and open curated docs from `/weppcloud/usersum/`.
- Search returns relevant results with typo tolerance and snippets.
- Document roles are enforced in search/navigation visibility.
- Existing command-bar parameter lookup continues to work unchanged.
- New search endpoints are stable enough to back a future MCP tool.
- `GET /usersum/api/search` p95 latency <= 250 ms and p99 <= 500 ms on production-like hardware at target corpus size.
- `GET /usersum/api/search` monthly availability >= 99.9% and 5xx error rate < 0.5%.
- Incremental index freshness SLO <= 5 minutes from indexed content change to searchable availability.
- Full rebuild SLO <= 30 minutes for target corpus size and produces zero stale/tombstoned leaks.
- Relevance quality gate on maintained query set:
  - top-3 contains at least one relevant result >= 90%
  - top-10 contains at least one relevant result >= 98%
