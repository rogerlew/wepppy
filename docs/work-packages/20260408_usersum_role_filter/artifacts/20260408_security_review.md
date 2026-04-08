# Security Review - Usersum Header ROLE Filter and Threshold Search Ceiling

## Metadata

- **Package**: `docs/work-packages/20260408_usersum_role_filter/`
- **Reviewer**: Codex
- **Date**: 2026-04-08
- **Scope reviewed**:
  - `wepppy/weppcloud/routes/usersum/usersum.py`
  - `wepppy/weppcloud/routes/usersum/docs_manifest.yaml`
  - `wepppy/weppcloud/routes/usersum/templates/usersum/header.htm`
  - `wepppy/weppcloud/routes/usersum/templates/usersum/search.htm`
  - `wepppy/weppcloud/routes/usersum/templates/usersum/view.htm`
  - `tests/weppcloud/routes/test_usersum_bp.py`
  - `tests/weppcloud/routes/test_usersum_docs_contracts.py`
  - `tests/weppcloud/routes/test_usersum_docs_index.py`
  - `tests/weppcloud/test_usersum_template_wiring.py`
- **Commit/branch context**: `master @ 7deb193e8` + local uncommitted package files
- **Related artifacts**:
  - Code review: not provided in this package scope
  - QA review: tracked in `docs/work-packages/20260408_usersum_role_filter/tracker.md`

## Security Triage Decision

- **Security impact level**: `high`
- **Dedicated security review required**: `yes`
- **Triage rationale**: This package changes role-based discovery and authorization-adjacent routing behavior in public `usersum` docs/search endpoints.
- **Threat model assumptions**:
  - Anonymous users can reach `usersum` routes directly.
  - `min_role` in usersum manifest is an authorization boundary for restricted docs.
  - Source/raw markdown routes must not bypass role visibility rules for manifested docs.

## Findings

| ID | Severity | Surface | Description | Evidence | Required action | Status |
| --- | --- | --- | --- | --- | --- | --- |
| SEC-01 | High | Auth, input/path, file-serving routes (`/usersum/src`, `/usersum/raw`) | Role visibility checks in `view_src_markdown` and `raw_markdown` previously keyed off raw `rel_path` before normalization, enabling non-canonical `..` bypass for restricted manifested docs. | Pre-fix repro: `src_normal 404`, `src_bypass 200`, `raw_normal 404`, `raw_bypass 200` for `enduser-authoring-guide.md` (`min_role: developer` in `docs_manifest.yaml:219-224`). Fixed in `usersum.py` by canonicalizing and rejecting non-canonical variants before manifest lookup/visibility checks; post-fix repro returns `404` for both bypass paths. | Implemented: canonicalized source/raw `rel_path`, rejected non-canonical inputs, and added regressions in `tests/weppcloud/routes/test_usersum_bp.py` for canonical allowed vs non-canonical denied on restricted docs. | Resolved |

Risk acceptance authority: `Accepted-risk` requires security reviewer recommendation plus explicit package owner acknowledgment in Sign-off.

## Verdict

- **Gate status**: `pass`
- **Unresolved findings**:
  - High: 0
  - Medium: 0
  - Low: 0
- **Release recommendation**: ship.

## Surface Checks

### 1) Auth, Session, and Authorization

- [x] Entry points enforce expected authn/authz checks for `/usersum/doc`, `/usersum/view`, and `/usersum/vendor`.
- [x] Role-ceiling checks enforce `403` for requested search ceilings above caller max in `/usersum/api/search`.
- [x] Source/raw markdown route handling now canonicalizes rel-path inputs before visibility checks; non-canonical traversal variants are denied.
- [x] Error paths avoid token leakage in reviewed scope.

### 2) Secrets and Credential Handling

- [x] No new plaintext secrets were introduced in reviewed files.
- [x] No credential material appears in route responses for reviewed paths.

### 3) Input Validation and Output Safety

- [x] Path normalization for `/usersum/src` and `/usersum/raw` now occurs before manifest visibility checks.
- [x] Search integer query args (`limit`, `offset`) enforce bounds.
- [x] Search role/category parsing rejects invalid values.

### 4) File System and Run-Tree Boundaries

- [x] Markdown file serving no longer exposes restricted manifested docs through non-canonical variants.
- [x] Repository-root boundary checks prevent escape outside repo root after resolution.

### 5) Queue, Worker, and Subprocess Surfaces

- [x] Not in scope for this package; no queue/subprocess changes reviewed.

### 6) Agentic Tooling and MCP Surfaces

- [x] Not in scope for this package; no agent/MCP permission changes reviewed.

### 7) Network and External Integrations

- [x] Not in scope for this package; no new outbound calls reviewed.

### 8) CI/CD and Supply Chain

- [x] Not in scope for this package; no CI token/runner changes reviewed.

### 9) Data Integrity, Locking, and Concurrency

- [x] Not in scope for this package; no NoDb/RQ mutation path changes reviewed.

### 10) Logging, Monitoring, and Incident Readiness

- [x] Reviewed endpoints return explicit 4xx errors for invalid search inputs.
- [ ] No dedicated signal exists for attempted path-canonicalization bypass on source/raw routes.

## Validation Evidence

- Automated checks run:
  - `wctl run-pytest tests/weppcloud/routes/test_usersum_bp.py tests/weppcloud/routes/test_usersum_docs_contracts.py tests/weppcloud/routes/test_usersum_docs_index.py tests/weppcloud/test_usersum_template_wiring.py --maxfail=1`
  - Result: `58 passed, 3 warnings in 10.28s`.
- Manual exploit repro run:
  - Command: `/workdir/wepppy/.venv/bin/python` Flask test-client script targeting `enduser-authoring-guide.md`.
  - Pre-fix result:
    - `src_normal 404`
    - `src_bypass 200`
    - `raw_normal 404`
    - `raw_bypass 200`
  - Post-fix result:
    - `src_normal 404`
    - `src_bypass 404`
    - `raw_normal 404`
    - `raw_bypass 404`

## Residual Risk

- **Accepted residual risks**:
  - Low observability gap: no dedicated metric/log signal currently tracks non-canonical source/raw path denial attempts.
- **Follow-up packages/issues**:
  - Optional: add explicit telemetry for repeated denied non-canonical source/raw path probes.

## Sign-off

- **Security reviewer**: Codex, 2026-04-08
- **Package owner**: pending (acknowledgment not required for resolved findings)
