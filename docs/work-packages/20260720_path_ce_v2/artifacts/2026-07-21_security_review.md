# Security Review - PATH-CE v2: Jackson Model Resync, Parquet-Native Pipeline, Full UI + Reports

> Linked from the package tracker; consolidates the security-relevant findings of the four
> Codex phase reviews and their dispositions.

## Metadata

- **Package**: `docs/work-packages/20260720_path_ce_v2/`
- **Reviewer**: Claude Code (author-side consolidation) over four independent Codex review passes (read-only MCP sessions; threads recorded in the phase-review artifacts)
- **Date**: 2026-07-21
- **Scope reviewed**: `wepppy/microservices/browse/report.py` (+ registration in `browse.py`), `wepppy/nodb/mods/path_ce/` (report_service, controller, preconditions, vendored model + QMD + static JS), `wepppy/rq/path_ce_rq.py`, `wepppy/weppcloud/routes/nodb_api/path_ce_bp.py`, `docker/Dockerfile{,.dev}` Quarto layer, `path_ce.js`/template
- **Commit/branch context**: uncommitted working tree on `master` (per-phase evidence in tracker timeline)
- **Related artifacts**:
  - Code reviews: `artifacts/2026-07-21_codex_phase{1,2,3,4}_review.md` (all findings dispositioned; none ignored)
  - Executional evidence: tracker timeline (RQ jobs `fa6a6bf4`, `240c0469`, `34a0efc4`, `dac5a67a`, `92ee701a`; live curls; headless Playwright through the served route)

## Security Triage Decision

- **Security impact level**: `high`
- **Dedicated security review required**: `yes`
- **Triage rationale**: the package adds a new public-facing surface that serves *generated* HTML inline from run directories (stored-XSS-adjacent), plus an in-worker subprocess render pipeline consuming run-derived data, plus config-driven RQ orchestration.
- **Threat model assumptions**:
  - Run directories are wepppy-managed; writers are the platform's workers and run owners (via uploads/API), not arbitrary principals. Content inside a run dir is *untrusted for serving* but its writers are authenticated.
  - The browse service's `authorize_run_request` contract (public runs readable without token; run-scoped tokens otherwise) is certified by its own suite and is the intended policy for report reads, matching `/download/`.
  - The vendored QMD/JS are first-party code (D1); the *data* they embed is run-derived and treated as untrusted in the browser.

## Findings

| ID | Severity | Surface | Description | Evidence | Required action | Status |
| --- | --- | --- | --- | --- | --- | --- |
| SEC-01 | High | Inline serving | Scripted SVG/XHTML in the report tree would have executed in the service origin (outside the sandbox CSP) | Phase 4 review F1 | Inline media-type allowlist; active types forced to attachment | Resolved (tests: scripted SVG/XHTML download-only) |
| SEC-02 | High | Inline serving | Symlinked `path/` or `path/report/` blessed a foreign tree as the containment root | Phase 4 F2 | Symlink-check the fixed subtree components before resolution | Resolved (tests: symlinked root + parent) |
| SEC-03 | Medium | Inline serving | TOCTOU between containment checks and file open; long partial-state window during report publication | Phase 4 F3 | `O_NOFOLLOW`+`fstat` buffered serving (leaf race closed); near-atomic rename-swap publication | Resolved (leaf) / Accepted-risk (directory-component swap in a microsecond window; wepppy-managed trees; full `openat`-walk serving judged disproportionate) |
| SEC-04 | Medium | CSP | `allow-popups` enabled an outbound navigation channel; missing `base-uri`/`form-action` hardening | Phase 4 F4 | Removed `allow-popups`; added `base-uri 'none'`, `form-action 'none'` | Resolved (live headers verified; report functionality re-verified headless) |
| SEC-05 | Medium | Script-context injection | Run-derived JSON embedded in `<script>` without `</script>`/U+2028/29 escaping | Phase 3 F6 | `_script_json()` + surface-spec escaping in the QMD | Resolved |
| SEC-06 | Medium | Render staging | Staged geojsons followed symlinks without containment or content validation into the future-public tree | Phase 3 F7 | `_copy_run_geojson`: symlink/containment/GeoJSON-content validation | Resolved (tests: symlink, traversal, content) |
| SEC-07 | Medium | Render subprocess | Quarto timeout killed only the parent, not the Jupyter kernel; staging leak on failure | Phase 3 F8 / Phase 4 disposition | Process-group kill; staging lifecycle fix with leak regression test | Resolved |
| SEC-08 | Low | Supply chain | Quarto `.deb` version-pinned but not integrity-pinned | Phase 3 F10 | `QUARTO_SHA256` verified via `sha256sum -c` in both Dockerfiles; image rebuilt | Resolved |
| SEC-09 | Low | Cache | `private, max-age=60` allowed authenticated report reuse across logout/visibility change | Phase 4 F5 | `private, no-store` | Resolved |
| SEC-10 | Low | Third-party disclosure | Report viewers make requests to folium-iframe CDN hosts + Google tile servers (request metadata; `Referrer-Policy: no-referrer` set; no run data in URLs) | Phase 3/4 reviews | Vendor folium assets to remove CDN dependence (follow-up); tile hosts inherent to the basemap | Accepted-risk (documented; CSP pins the exact hosts) |
| SEC-11 | Low | Platform convention | RQ jobs execute the latest persisted config (no enqueue-time binding); artifacts overwrite fixed paths; `error_factory` returns 200-with-error-body | Phase 2 F1/F3, Phase 4 F9 | Platform-wide contracts; PATH-CE adds an enqueue dedup guard and client-side error detection | Accepted-risk (platform-level initiative required to change; recorded in tracker Risks) |

Risk acceptance authority: Accepted-risk entries require package owner acknowledgment.
**Owner acknowledgment**: Roger Lew reviewed the security notes and acknowledged the three Accepted-risk rows (SEC-03 residual, SEC-10, SEC-11) on 2026-07-21, clearing the package for commit.

## Verdict

- **Gate status**: `pass`
- **Unresolved findings**: High: 0 · Medium: 0 (one accepted residual on SEC-03) · Low: 2 accepted-risk
- **Release recommendation**: **ship-with-conditions** — conditions: (1) owner acknowledgment of the three accepted-risk rows; (2) Roger's manual authenticated UI round-trip + in-browser report check; (3) prod image rebuild uses the sha-pinned Quarto layer already in `docker/Dockerfile`.

## Surface Checks (summary of non-trivial items; trivially-passing boxes omitted)

### Auth, Session, and Authorization
- Report routes call `authorize_run_request` with the identical flags as `/download/` (public-without-token allowed, run token classes, 401-redirect html-only) — parity by construction; the auth helper is certified by `tests/microservices/test_browse_auth_routes.py`. Denial propagation tested (403 exact, no redirect).
- The sandbox CSP (no `allow-same-origin`) puts served reports in an opaque origin: no cookie access, no credentialed same-origin API reach — the primary stored-XSS containment.
- Blueprint mutations retain the platform session/authz decorators; the run route adds a duplicate-run guard (RedisPrep job id + RQ status).

### Input Validation and Output Safety
- Config: strict normalization in the NoDb controller (finite numerics, enum severities, label↔scenario derivation enforcement — closes the silent treatment mis-pairing class found in Phases 1 and 2). The blueprint passes values through rather than coercing (Phase 4 F8/F9 fixes).
- Preconditions read artifacts defensively (malformed parquet → actionable report errors, not exceptions).
- Report HTML embeds run-derived JSON via script-safe serialization (SEC-05).

### File System and Run-Tree Boundaries
- Serving: subtree allowlist rooted at `<wd>/path/report/`, hidden/recorder-segment rejection, `..` rejection, component symlink walk incl. the subtree components, resolve containment, `O_NOFOLLOW` leaf open. Traversal/symlink probes verified live against the dev service.
- Render staging: geojson copies validated (symlink/containment/content); scratch dirs cleaned on all paths (leak regression test).
- Publication: rename-swap; dot-prefixed staging names are unservable by construction.

### Queue, Worker, and Subprocess Surfaces
- Quarto invocation: fixed argv (no shell, no user-controlled command composition), payload delivered via env-var file path written by the service itself, staging-scoped HOME/XDG, process-group kill on timeout, log-tail surfaced on failure.
- RQ wiring unchanged in shape (one task, same queue); nodir preflight ordered before cache invalidation per the NoDb standard.

### Network and External Integrations
- New outbound: Quarto deb fetch at image build (sha-pinned); viewer-side CDN/tile requests (SEC-10). The render itself needs no network (local plotly/deck.gl; sweep from artifacts).

### CI/CD and Supply Chain
- Quarto pinned by version + sha256 in both images. deck.gl/papaparse vendored from upstream's repo at reviewed versions; plotly.js staged from the installed Python package (version-matched by construction).

### Data Integrity, Locking, and Concurrency
- NoDb lock discipline preserved (`with self.locked()` on all mutations; deep-copied results). Single config snapshot threads through a run. Sweep cache keyed on config + frame SHA-256 with schema version.

## Validation Evidence

- Automated: container pytest sweeps (final Phase 4 state: 124 passed across path_ce/rq/bp/microservice/unitizer targets, incl. the real Quarto render integration test); `npm run lint` 0 errors + 647 jest tests; `tools/check_broad_exceptions.py --enforce-changed` PASS.
- Manual/executional: five dev-stack RQ jobs across the phases (happy/failure/cache/render paths); live curl header + traversal probes against the browse service; headless Playwright through the served route under the final CSP (fully functional; only sandbox-by-design `localStorage` denials).
- Outstanding manual: Roger's authenticated UI round-trip and in-browser report check (tracked in closeout).
