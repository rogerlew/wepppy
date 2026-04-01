# Tracker - Usersum Manifest-Driven Docs Engine

> Living document tracking progress, decisions, risks, and communication for this work package.

## Quick Status

**Started**: 2026-04-01  
**Completed**: 2026-04-01  
**Current phase**: Closed  
**Last updated**: 2026-04-01  
**Next milestone**: None (package complete).

## Task Board

### Ready / Backlog
- [ ] None.

### In Progress
- [ ] None.

### Blocked
- [ ] None.

### Done
- [x] Milestone 1: Implemented schema contracts and strict validation tooling.
- [x] Milestone 2: Implemented vendor sync/build pipeline and generated docs index artifact.
- [x] Milestone 3: Refactored usersum runtime to manifest-index-backed resolution and role-aware visibility.
- [x] Milestone 4: Implemented GitBook-like usersum shell (header search, sticky collapsible nav, breadcrumbs).
- [x] Milestone 5: Implemented PostgreSQL FTS + `pg_trgm` search backend and wired `/usersum/api/search` + `/usersum/search`.
- [x] Milestone 6: Hardened compatibility routes, added regression coverage, completed code + QA review artifacts, and closed package docs.

## Timeline

- **2026-04-01** - Package created and scoped.
- **2026-04-01** - Active ExecPlan drafted for milestones 1-6.
- **2026-04-01** - Implemented milestones 1-6, validated, and closed package.

## Decisions Log

### 2026-04-01: Execute as single full work-package with mandatory review gates
**Context**: User requested full end-to-end execution and explicitly requested code + QA review as part of the package.

**Options considered**:
1. Partial implementation with follow-up package.
2. End-to-end package execution with milestone-driven plan and closure gates.

**Decision**: Option 2.

**Impact**: Work package included all milestones plus review artifacts and closure validation.

### 2026-04-01: Keep compatibility routes while shifting canonical routing to `doc_id`
**Context**: Existing usersum links and route contracts are already in active use.

**Decision**: Keep `/usersum/view/*`, `/usersum/src/*`, and `/usersum/raw/*` compatibility routes while introducing canonical `/usersum/doc/<doc_id>` and `/usersum/vendor/<vendor_id>/<path:filename>`.

**Impact**: Reduced migration risk while enabling manifest-driven routing.

## Risks and Issues

| Risk | Severity | Likelihood | Mitigation | Status |
|------|----------|------------|------------|--------|
| Runtime regressions while switching to manifest-index-backed resolution | High | Medium | Compatibility routes retained and covered by route regression tests | Closed |
| PostgreSQL search availability in local/test environments | Medium | Medium | Explicit fallback/strict modes + deterministic API behavior | Closed |
| Vendor drift between source repo and vendored copy | Medium | High | Sync tooling + contract validation + committed generated artifacts | Closed |
| Nav/manifest mismatches causing broken links/breadcrumbs | Medium | Medium | Strict validation and index-generation tests | Closed |

## Verification Checklist

### Code Quality
- [x] `wctl run-pytest tests/weppcloud/routes/test_usersum_bp.py tests/weppcloud/test_usersum_template_wiring.py --maxfail=1`
- [x] Targeted usersum tooling/schema tests
- [x] `wctl doc-lint --path wepppy/weppcloud/routes/usersum/specification.md`
- [x] `wctl doc-lint --path docs/work-packages/20260401_usersum_docs_engine`

### Testing
- [x] Regression tests for manifest/nav/vendor schema validation.
- [x] Regression tests for usersum runtime doc resolution + compatibility routes.
- [x] Regression tests for usersum search API/page behavior.
- [x] Regression tests for vendor route/doc behavior.

### Review Gates
- [x] Code review artifact authored at `artifacts/code_review_findings.md`.
- [x] QA review artifact authored at `artifacts/qa_review_findings.md`.
- [x] Medium/high findings resolved and documented with validation reruns.

## Progress Notes

### 2026-04-01: Execution and closure
**Agent/Contributor**: Codex

**Work completed**:
- Implemented all milestone scope from specification milestones 1-6.
- Added usersum contracts/tooling/runtime/search/template updates and regression tests.
- Addressed QA follow-up UI/route issues:
  - full-width usersum shell/header,
  - search placement + alignment with theme selector,
  - theme-aware usersum button/sidebar/scrollbar styling,
  - prefix-safe usersum links via `url_for_run`,
  - unescaped search snippets.
- Authored review artifacts and closed package docs.

**Blockers encountered**:
- One interrupted broad-suite rerun; resolved by rerunning focused regression gates for final changed scope.

**Test results**:
- `wctl run-pytest tests/weppcloud/routes/test_usersum_bp.py tests/weppcloud/test_usersum_template_wiring.py tests/weppcloud/routes/test_usersum_docs_contracts.py tests/weppcloud/routes/test_usersum_docs_index.py --maxfail=1` -> pass.
- `wctl run-pytest tests/weppcloud/routes/test_usersum_bp.py tests/weppcloud/test_usersum_template_wiring.py --maxfail=1` -> pass.
- `PYTHONPATH=/workdir/wepppy python3 tools/usersum_docs_tool.py validate` -> pass.
- `PYTHONPATH=/workdir/wepppy python3 tools/usersum_docs_tool.py validate --require-vendor-files` -> pass.
- `python3 tools/check_broad_exceptions.py --enforce-changed --base-ref origin/master` -> pass.
- Baseline broad suite during package execution: `wctl run-pytest tests --maxfail=1` -> `2971 passed, 36 skipped`.

## Watch List

- Preserve source-of-truth policy for vendor docs: author upstream, sync into usersum vendor tree.
- Keep canonical usersum links site-prefix aware for `/weppcloud` and proxy-prefix deployments.

## Communication Log

### 2026-04-01: Full package execution
**Participants**: User, Codex  
**Question/Topic**: Execute usersum milestones 1-6 as a full work-package with code and QA review artifacts.  
**Outcome**: Completed and closed.
