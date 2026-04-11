# PROJECT_TRACKER.md
> Kanban board for wepppy work packages and vision items

**Last Updated**: 2026-04-11  
**Active Packages**: 1  
**Quick Links**: [Work Packages Directory](docs/work-packages/) | [God-Tier Prompting Strategy](docs/god-tier-prompting-strategy.md)

## Purpose

This tracker provides a high-level view of active and planned work packages for both human and AI agents. When starting a session, agents should check this tracker to understand current initiatives and avoid duplicate work.

## How to Use This Tracker

**For Agents**:
- Check "In Progress" when starting work to see what's active
- Review "Backlog" to understand planned work
- Update package status when starting or completing work
- Add new packages to "Backlog" when scoping new initiatives
- Move packages between columns as they progress

**For Humans**:
- Get a quick snapshot of active development
- Understand what's coming next
- See what's been recently completed
- Identify opportunities to contribute

**Package Lifecycle**:
1. Start in **Backlog** (scoped but not started)
2. Move to **In Progress** when work begins
3. Move to **Done** when complete (leave for 30 days, then archive to History)

## Kanban Principles Applied

### 1. Visualize Work
This tracker makes all work visible at a glance, helping agents coordinate and avoiding duplicate effort.

### 2. Limit Work in Progress
**Target**: 2-4 active packages maximum to maintain focus and ensure packages complete rather than stall.

**Current WIP**: 1 package ✅ **Within target range**

If WIP exceeds 4, prioritize completing existing packages before starting new ones. This prevents context switching overhead and ensures clean handoffs.

### 3. Manage Flow
Monitor how long packages spend in each column:
- **Backlog → In Progress**: Should happen when capacity available and dependencies met
- **In Progress → Done**: Target 2-4 weeks for most packages; >6 weeks suggests scope issues

Blockers should be explicitly noted in package tracker.md and surfaced here if they affect multiple packages.

### 4. Make Process Policies Explicit
All policies are documented:
- Package structure: `docs/work-packages/README.md`
- Agent workflow: `AGENTS.md` (Creating a Work Package section)
- Prompt crafting: `docs/god-tier-prompting-strategy.md`
- Templates: `docs/prompt_templates/`

When agents encounter unclear policies, they should update the relevant documentation immediately.

### 5. Implement Feedback Loops
Feedback mechanisms:
- **Package tracker.md**: Decision logs and progress notes capture what's working/not working
- **Lessons learned**: Package closure notes document insights for future work
- **Agent collaboration**: Agents encouraged to suggest improvements when they stumble
- **This tracker**: Review periodically to identify patterns in blocked/stalled work

### 6. Improve Collaboratively, Evolve Experimentally
**Continuous improvement culture**:
- Agents have authority to correct/improve documentation when gaps are found
- Stumbling is a system failure, not agent failure
- Every agent should leave the system slightly better than they found it
- Experimental approaches are encouraged; document outcomes in tracker.md

**Feedback welcome**: If this tracker format doesn't work, propose improvements in a package tracker or directly update this file.

---

## 📋 Backlog

Work packages that are scoped but not yet started. Dependencies and prerequisites should be noted.

### Deprecate and Remove TauDEM Backend
**Proposed**: 2025-10-27  
**Size**: Medium (3-5 days)  
**Priority**: Medium  
**Description**: The `TauDEM` watershed delineation backend is deprecated and should be removed from the codebase to reduce complexity and maintenance overhead.

**Scope**:
- Remove all code paths related to `DelineationBackend.TauDEM` in `wepppy/nodb/core/watershed.py`.
- Delete any TauDEM-specific scripts, configuration, or workflow files.
- Ensure the `WBT` (WhiteboxTools) backend is the default and fully functional replacement for all use cases.

**Strategic Value**:
- Reduces technical debt and code complexity.
- Simplifies the watershed delineation logic and configuration.
- Lowers the maintenance burden for both developers and agents.
- Focuses testing and development efforts on the modern `WBT` backend.

**Dependencies**: Confirmation that the `WBT` backend fully covers all necessary functionality previously provided by `TauDEM`.

**Next Steps**: Create a work package to analyze the full impact of removal, verify WBT feature parity, and execute the removal.

---

### Jinja Template Lint Error Resolution
**Proposed**: 2025-10-27  
**Size**: Small (1-2 days)  
**Priority**: Low (cosmetic, doesn't affect functionality)  
**Description**: Resolve TypeScript/JavaScript linter false positives when parsing Jinja template syntax (`{{ ... | tojson }}`) inside `<script>` tags in `.htm` templates.

**Scope**:
- Move dynamic values from inline Jinja expressions to HTML data attributes
- Refactor JavaScript to read from data attributes instead of Jinja-injected constants
- Eliminate lint errors while maintaining template functionality
- Pattern applies to: `_base_report.htm`, potentially other report templates

**Strategic Value**: 
- Cleaner CI lint output
- Better developer experience (no false positive noise)
- More maintainable separation of template data and JavaScript logic
- Standard pattern for future template development

**Dependencies**: None

**Next Steps**: Create work package when bandwidth available; not blocking any current work

---

### Rename markdown-extract Repo to markdown-toolkit
**Proposed**: 2025-10-28  
**Size**: Small (1 hour)  
**Priority**: Low  
**Description**: Rename the `rogerlew/markdown-extract` repository to `rogerlew/markdown-toolkit` to reflect that it now includes three tools: `markdown-extract`, `markdown-edit`, and `markdown-doc`.

**Scope**:
- Rename GitHub repository via Settings → Rename
- Update README.md to reflect new name
- Update any documentation/references in wepppy that point to the old repo name
- GitHub automatically redirects old URLs, so existing links remain functional
- Update `tools/README.markdown-tools.md` references if needed

**Strategic Value**: 
- Accurate branding reflects toolkit nature (not just extraction)
- Clearer communication to users about available tools
- Better positioning for future tools (e.g., markdown-validate, markdown-toc)
- GitHub redirects preserve all existing links

**Dependencies**: None (safe operation, GitHub handles redirects)

**Next Steps**: Quick rename when convenient; very low risk

### Kubernetes Migration (Pending)
When resuming Kubernetes work:
- Duplicate static build stage for proxy image
- Use init containers for shared assets
- Eliminate shared volume mounts
- Configure Redis keyspace notifications in ConfigMap
- Set resource limits based on profiling

**Health Checks**:
- Endpoint: `/health`
- Returns 200 OK when ready
- Checks Redis connectivity
- Use for liveness/readiness probes

**Logging in Production**:
- Structured logs to stdout (captured by Docker/K8s)
- Per-run logs in working directory
- Centralized aggregation via Loki/ELK if needed
- Redis status messages ephemeral (72-hour retention)

---

## 🚧 In Progress

Currently active work packages. Limit to 2-4 packages to maintain focus.

**Current WIP Count**: 1 package

---

### markdown-doc Toolkit Integration
**Started**: 2025-10-25  
**Status**: Phase 3 Complete — Integration Active (Phase 4 pending telemetry + RFC decisions)  
**Size**: Large (Phases 1-3: 6 days; Phase 4: TBD)  
**Owner**: gpt-5-codex (Phase 1-3 implementation), GitHub Copilot (Claude 4.5 Sonnet - spec, testing, integration)  
**Link**: [docs/work-packages/20251025_markdown_doc_toolkit/](docs/work-packages/20251025_markdown_doc_toolkit/)  
**Description**: Comprehensive Rust CLI for documentation management with catalog generation, link validation, safe file moves, TOC maintenance, and reference finding. Phase 4 (search & indexing) pending go/no-go decision.

**Completed Deliverables** (Phases 1-3):
- ✅ `catalog` - Generate `DOC_CATALOG.md` with file list + TOCs
- ✅ `lint` - Validate links (broken-links, anchors, hierarchy, required-sections modes)
- ✅ `toc` - Generate/update table of contents with multiple styles
- ✅ `mv` - Move/rename files with automatic link updates across workspace
- ✅ `refs` - Find references to files/sections (file graph + forward/reverse links)
- ✅ `validate` - Config-driven checks with severity tuning
- ✅ wctl integration - 6 doc-* commands: doc-lint, doc-catalog, doc-toc, doc-mv, doc-refs, doc-bench
- ✅ CI/CD integration - docs-quality.yml workflow with SARIF upload, Rust checks, telemetry
- ✅ Comprehensive documentation - tools/README.markdown-tools.md, CI/CD strategy updates
- ✅ Telemetry collection active (started 2025-10-31, logs to telemetry/docs-quality.jsonl)

**Phase 4 Scope** (Pending Go/No-Go Decision 2025-11-18):
- 🔮 `search` - Full-text search with TF-IDF ranking (<500ms target)
- 🔮 Index builder with persistent caching (<5s rebuild target)
- 🔮 JSON output mode for programmatic consumption

**Current Status**:
- **RFC Decision Gate** (Due 2025-11-08): 4 decisions pending (link graph caching, CI bench cadence, release comms, Phase 4 scope validation)
- **Telemetry Collection** (Due 2025-11-18): Gathering baseline data (≥2 weeks from 2025-10-31) to validate Phase 4 justification
- **Integration Finalization** (Due 2025-11-08): Onboarding docs, release notes, RFC outcomes

**Strategic Value**: 
- **Delivered** (Phases 1-3): Reduces doc maintenance by ~70%, prevents broken links in CI, enables safe refactoring, improves link graph visibility
- **Potential** (Phase 4): Fast semantic search across 388+ docs, programmatic query support, reusable index for tooling integration

**Dependencies**: 
- Phase 4 blocked on: Telemetry data maturity (≥2 weeks), RFC decisions, Phase 4 open questions resolution

**Next Steps**:
1. **Immediate** (Nov 2-8): Resolve RFC decisions (4 decisions), finalize integration (onboarding docs, release notes)
2. **Phase 4 Gate** (Nov 18): Review telemetry data, resolve Phase 4 open questions (index storage, watch mode, UI integration, search patterns), make go/no-go decision
3. **If Phase 4 Greenlit**: Create Phase 4 work package structure, draft agent prompts, assign ownership, schedule M1 target (~Dec 6)

---

## ✅ Done

Recently completed work packages. Archived immediately upon completion.

### RQ Operator Experience Hardening (2026-04-11)
**Status**: ✅ **COMPLETE**  
**Link**: [docs/work-packages/20260411_rq_operator_experience_hardening/](docs/work-packages/20260411_rq_operator_experience_hardening/)  
**Summary**: Completed end-to-end operator hardening across auth bootstrap, revision coherence, freshness semantics, and smoke reliability. Shipped machine-safe bootstrap endpoint `POST /weppcloud/api/auth/rq-engine-operator-token` (scope-intersection enforcement, pre-revocation throttling, denylist revocation checks with explicit `503`+`Retry-After` outage contract, audit logging, short TTL/no-store response, CSRF exemption for bearer flow), added `run_state_domain` + phased `run_state_vector` semantics across run-scoped snapshot reads, enforced explicit freshness semantics (`updated_at`, `data_state`, `data_updated_at`) with revision-coherent/non-future behavior, and updated descriptor/schema contract fields and regression tests. Maintainer preflight gate passed (`251` microservice tests + parity guards), API-only operator acceptance evidence was rerun and captured with UTC/redacted logging, and independent `reviewer`/`qa_reviewer`/`security_reviewer` re-reviews closed with no unresolved medium/high findings. Follow-up acceptance remediation on 2026-04-11 closed the `build-climate` parser blocker (canonical `validation_error` payloads, no traceback leakage), aligned climate mode schema/defaults (including mode `5`/future-year semantics), and added batched run-endpoint discovery via `include_operation_docs=true`.

### RQ Controller State Contract Cutover (2026-04-11)
**Status**: ✅ **COMPLETE**  
**Link**: [docs/work-packages/20260410_rq_controller_state_contract_cutover/](docs/work-packages/20260410_rq_controller_state_contract_cutover/)  
**Summary**: Completed row-8 contract freeze/cutover reconciliation across schema/pointer docs, frozen inventory/checklist parity notes, and package lifecycle evidence. Required code gates passed, phased `reviewer` -> `qa_reviewer` -> `security_reviewer` reviews were dispositioned with no unresolved medium/high findings, and one explicit accepted residual/design risk (session-token scope bridge compatibility) was formally documented with owner and follow-up trigger. Post-close readiness hardening added a canonical end-to-end smoke runbook and reran a consolidated 248-test rq-engine smoke baseline plus guard checks.

### RQ Controller State Auth and Concurrency (2026-04-10)
**Status**: ✅ **COMPLETE**  
**Link**: [docs/work-packages/20260410_rq_controller_state_auth_concurrency/](docs/work-packages/20260410_rq_controller_state_auth_concurrency/)  
**Summary**: Hardened controller-state auth/concurrency semantics by shipping `rq:read` rollout parity, session-token write-precondition enforcement, and idempotency replay/mismatch parity with descriptor/OpenAPI metadata. All required code gates and independent `reviewer`/`qa_reviewer`/`security_reviewer` gates passed; security closeout recorded one accepted residual design risk and no unresolved medium/high defects.

### RQ Controller State Errors, Progress, and Outputs (2026-04-10)
**Status**: ✅ **COMPLETE**  
**Link**: [docs/work-packages/20260410_rq_controller_state_errors_progress_outputs/](docs/work-packages/20260410_rq_controller_state_errors_progress_outputs/)  
**Summary**: Implemented run-scoped endpoint error catalogs, async progress metadata integration, and `GET /api/runs/{runid}/{config}/outputs` with artifact trust/provenance metadata and retrieval handles. Required code gates and independent `reviewer`/`qa_reviewer`/`security_reviewer` gates passed with no unresolved medium/high findings.

### Lifecycle Corrections (2026-04-10)
**Status**: ✅ **COLUMNS RECONCILED**  
**Description**: The following work packages were still listed in `Backlog`/`In Progress` but package-level docs already recorded completion. They were moved to `Done` after subagent review + doc verification.

- [docs/work-packages/20260329_features_export_legacy_exports_cutover/](docs/work-packages/20260329_features_export_legacy_exports_cutover/) — Closed (2026-03-29)
- [docs/work-packages/20260329_features_export_live_run_matrix/](docs/work-packages/20260329_features_export_live_run_matrix/) — Completed (Phase 3 closed 2026-04-01)
- [docs/work-packages/20260329_features_export_artifact_readme_metadata/](docs/work-packages/20260329_features_export_artifact_readme_metadata/) — Closed (2026-03-29)
- [docs/work-packages/20260327_roads_point_source_inslope_non_channel/](docs/work-packages/20260327_roads_point_source_inslope_non_channel/) — Closed - Production Validation Verified (2026-03-28)
- [docs/work-packages/20260327_roads_point_source_outslope_rutted/](docs/work-packages/20260327_roads_point_source_outslope_rutted/) — Completed (2026-04-07)
- [docs/work-packages/20260327_roads_outslope_unrutted_mofe_replacement/](docs/work-packages/20260327_roads_outslope_unrutted_mofe_replacement/) — Complete (2026-04-08)
- [docs/work-packages/20260325_rusle_momm2025_r_mode/](docs/work-packages/20260325_rusle_momm2025_r_mode/) — Complete (2026-03-26)
- [docs/work-packages/20260403_roads_map_drilldown/](docs/work-packages/20260403_roads_map_drilldown/) — Handoff Ready (2026-04-04)
- [docs/work-packages/20260327_roads_peridot_trace_core/](docs/work-packages/20260327_roads_peridot_trace_core/) — Complete - Handoff Ready (2026-03-27)
- [docs/work-packages/20260323_roads_wepp_reports_regen/](docs/work-packages/20260323_roads_wepp_reports_regen/) — Completed (Milestones 1-10 closed, 2026-03-24)
- [docs/work-packages/20260124_sbs_map_refactor/](docs/work-packages/20260124_sbs_map_refactor/) — Closed (2026-01-24)
- [docs/work-packages/20251028_wojak_lives/](docs/work-packages/20251028_wojak_lives/) — Closed - Deferred Follow-On (2026-04-10 05:50 UTC)
- [docs/work-packages/20260331_wcag21aa_frontend_accessibility/](docs/work-packages/20260331_wcag21aa_frontend_accessibility/) — Closed (2026-04-10 05:50 UTC)
- [docs/work-packages/20260208_rq_engine_agent_usability/](docs/work-packages/20260208_rq_engine_agent_usability/) — Closed (2026-04-10 06:08 UTC)

---

### RQ Controller State Geospatial and Upload Metadata
**Completed**: 2026-04-10  
**Duration**: 1 focused session + remediation/re-review loop  
**Status**: ✅ **COMPLETE**  
**Owner**: Codex  
**Link**: [docs/work-packages/20260410_rq_controller_state_geospatial_uploads/](docs/work-packages/20260410_rq_controller_state_geospatial_uploads/)  
**Description**: Implemented run geospatial metadata and upload metadata contract hardening so agents can select first-step watershed defaults and validate upload payloads pre-submit.

**Outcome**:
- Added rq-engine endpoint:
  - `GET /api/runs/{runid}/{config}/geospatial-metadata`
- Hardened upload descriptor/schema/default metadata for:
  - `rq_engine_upload_dem`
  - `rq_engine_upload_cli`
  - `rq_engine_upload_sbs`
  - `rq_engine_upload_cover_transform`
- Aligned cross-surface parity for climate/soils mode constraints and watershed defaults.
- Added explicit runtime `max_bytes` upload enforcement + oversize regression tests for DEM/CLI/SBS/cover-transform handlers.
- Completed reviewer/QA/security re-reviews with no unresolved medium/high findings.
- Closed lifecycle docs, completed security artifact, and archived ExecPlan to `prompts/completed/` with outcome note.

**Validation Notes**:
- `wctl run-pytest tests/microservices/test_rq_engine_geospatial_upload_metadata_routes.py --maxfail=1` (`21 passed`)
- `wctl run-pytest tests/microservices/test_rq_engine_openapi_contract.py --maxfail=1` (`9 passed`)
- `python tools/check_endpoint_inventory.py` (pass)
- `python tools/check_route_contract_checklist.py` (pass)
- `wctl run-pytest tests/tools/test_endpoint_inventory_guard.py tests/tools/test_route_contract_checklist_guard.py --maxfail=1` (`2 passed`)

---

### RQ Controller State Schema and Defaults
**Completed**: 2026-04-10  
**Duration**: 1 focused session + review remediation loop  
**Status**: ✅ **COMPLETE**  
**Owner**: Codex  
**Link**: [docs/work-packages/20260410_rq_controller_state_schema_defaults/](docs/work-packages/20260410_rq_controller_state_schema_defaults/)  
**Description**: Implemented and closed run-scoped controller and endpoint schema/default metadata reads so agents can discover constraints and run-resolved defaults directly from rq-engine.

**Outcome**:
- Added rq-engine schema/default endpoints:
  - `GET /api/runs/{runid}/{config}/controllers`
  - `GET /api/runs/{runid}/{config}/controllers/{controller}/schema`
  - `GET /api/runs/{runid}/{config}/controllers/{controller}/hints`
  - `GET /api/runs/{runid}/{config}/controllers/{controller}/templates`
  - `GET /api/runs/{runid}/{config}/endpoints`
  - `GET /api/runs/{runid}/{config}/endpoints/{operation_id}/schema`
  - `GET /api/runs/{runid}/{config}/endpoints/{operation_id}/defaults`
- Added deterministic metadata assembly and route wiring in `schema_defaults_routes.py` + app registration.
- Resolved reviewer/QA/security findings, including:
  - climate default type parity (`climate_mode_code` integer defaulting)
  - operation schema/default parity with live handlers
  - disturbed-mod-aware `/upload-sbs` availability gating
- Package lifecycle closed:
  - tracker/package/security artifact updated
  - ExecPlan archived to `prompts/completed/` with outcome note
  - no unresolved medium/high QA or security findings

**Validation Notes**:
- `wctl run-pytest tests/microservices/test_rq_engine_schema_defaults_routes.py --maxfail=1` (`43 passed`)
- `wctl run-pytest tests/microservices/test_rq_engine_openapi_contract.py --maxfail=1` (`9 passed`)
- `python tools/check_endpoint_inventory.py` (pass)
- `python tools/check_route_contract_checklist.py` (pass)
- `wctl run-pytest tests/tools/test_endpoint_inventory_guard.py tests/tools/test_route_contract_checklist_guard.py --maxfail=1` (`2 passed`)

---

### RQ Controller State Orchestration Reads
**Completed**: 2026-04-10  
**Duration**: 1 focused session + review remediation loop  
**Status**: ✅ **COMPLETE**  
**Owner**: Codex  
**Link**: [docs/work-packages/20260410_rq_controller_state_orchestration_reads/](docs/work-packages/20260410_rq_controller_state_orchestration_reads/)  
**Description**: Implemented and closed run-scoped orchestration read APIs so agents can deterministically query pipeline/readiness state and choose next actions without UI heuristics.

**Outcome**:
- Added rq-engine orchestration endpoints:
  - `GET /api/runs/{runid}/{config}/pipeline`
  - `GET /api/runs/{runid}/{config}/readiness`
- Added route/openapi/guard/frozen-artifact parity updates for the two new agent-facing routes.
- Resolved independent reviewer/QA/security findings, including:
  - dedicated `RunConfigMismatchError` + narrow `404` mapping
  - UTC normalization for naive timestamps
  - deterministic empty-timeline `updated_at`
  - child-job status/ended-at folding to prevent premature completion in fan-out job trees
- Package lifecycle closed:
  - tracker/package/security artifact updated
  - ExecPlan archived to `prompts/completed/` with outcome note
  - no unresolved medium/high QA or security findings

**Validation Notes**:
- `wctl run-pytest tests/microservices/test_rq_engine_orchestration_read_routes.py --maxfail=1` (`25 passed`)
- `wctl run-pytest tests/microservices/test_rq_engine_openapi_contract.py --maxfail=1` (`9 passed`)
- `python tools/check_endpoint_inventory.py` (pass)
- `python tools/check_route_contract_checklist.py` (pass)
- `wctl run-pytest tests/tools/test_endpoint_inventory_guard.py tests/tools/test_route_contract_checklist_guard.py --maxfail=1` (`2 passed`)

---

### Roads NoDb Inslope End-to-End Implementation
**Completed**: 2026-04-10  
**Duration**: Multi-milestone package (implementation + closeout validation)  
**Status**: ✅ **CLOSED**  
**Owner**: Codex  
**Link**: [docs/work-packages/20260323_roads_nodb_inslope_e2e/](docs/work-packages/20260323_roads_nodb_inslope_e2e/)  
**Description**: Closed phase-1 Roads inslope integration package after explicit rollback validation and package handoff completion.

**Outcome**:
- Rollback validation captured for `mod disable` roundtrip (`roads.nodb` backup/restore hash parity), roads artifact isolation contract, and queue rollback hygiene (no active Roads job, no residual submit/runtime locks).
- Targeted rollback-related tests re-run and passing:
  - `tests/weppcloud/routes/test_project_bp.py` (`set_mod` subset)
  - `tests/rq/test_roads_rq.py`
  - `tests/nodb/mods/test_roads_controller.py` (`roads-scope resource` assertion)
- Package docs closed, rollback artifact added, and ExecPlan archived to `prompts/completed/`.

---

### Usersum Header ROLE Filter and Threshold Search Ceiling
**Completed**: 2026-04-09  
**Duration**: 1 focused session + follow-up fixes  
**Status**: ✅ **COMPLETE**  
**Owner**: Codex  
**Link**: [docs/work-packages/20260408_usersum_role_filter/](docs/work-packages/20260408_usersum_role_filter/)  
**Description**: Closed usersum role-filter package delivering header `ROLE` discovery filtering, threshold role-ceiling semantics, nav alignment, spec sync, and source/raw canonical-path security hardening.

**Outcome**:
- Header `ROLE` selector shipped with PowerUser/Admin/Root option contracts and selected-role persistence.
- Role filter semantics now use threshold ceilings with explicit unauthorized-ceiling handling (`403` API + page error path).
- Discovery/nav now honors selected role ceiling; doc pages self-report `min_role` under breadcrumbs.
- Security finding `SEC-01` closed by canonicalizing `/usersum/src` and `/usersum/raw` rel-path handling before manifest visibility checks.
- Package lifecycle closed: package/tracker updated, ExecPlan moved to `prompts/completed/` with outcome summary.

**Validation Notes**:
- `wctl run-pytest tests/weppcloud/routes/test_usersum_bp.py tests/weppcloud/test_usersum_template_wiring.py --maxfail=1` (`50 passed`)
- `wctl run-pytest tests/weppcloud/routes/test_usersum_bp.py tests/weppcloud/routes/test_usersum_docs_contracts.py tests/weppcloud/routes/test_usersum_docs_index.py tests/weppcloud/test_usersum_template_wiring.py --maxfail=1` (`58 passed`)
- `wctl doc-lint --path wepppy/weppcloud/routes/usersum/specification.md` (`1 file validated, 0 errors, 0 warnings`)

---

### RQ Controller State Contract Foundation
**Completed**: 2026-04-10  
**Duration**: 1 focused session  
**Status**: ✅ **COMPLETE**  
**Owner**: Codex  
**Link**: [docs/work-packages/20260410_rq_controller_state_foundation/](docs/work-packages/20260410_rq_controller_state_foundation/)  
**Description**: Closed the foundation contract package by reconciling identifier model semantics, descriptor invariants, and roadmap dependency clarity against frozen 2026-02-08 route artifacts.

**Outcome**:
- Updated foundation schema docs:
  - `docs/schemas/rq-controller-state-contract.md`
  - `docs/schemas/rq-engine-agent-api-contract.md`
- Dispositioned independent reviewer findings and recorded decisions/progress in:
  - `docs/work-packages/20260410_rq_controller_state_foundation/tracker.md`
  - `docs/work-packages/20260410_rq_controller_state_foundation/prompts/completed/rq_controller_state_foundation_execplan.md`
  - `docs/work-packages/20260410_rq_controller_state_foundation/prompts/completed/rq_controller_state_foundation_execplan_outcome.md`
- Closed package lifecycle documentation and readied direct follow-on packages:
  - `20260410_rq_controller_state_setup_discovery`
  - `20260410_rq_controller_state_orchestration_reads`
  - `20260410_rq_controller_state_schema_defaults`
- Lifecycle recorded: Backlog -> In Progress (2026-04-10 04:08 UTC) -> Done (2026-04-10 04:23 UTC).
- Security review artifact added:
  - `docs/work-packages/20260410_rq_controller_state_foundation/artifacts/2026-04-10_security_review.md`

**Validation Notes**:
- `wctl doc-lint --path docs/schemas/rq-controller-state-contract.md --path docs/schemas/rq-engine-agent-api-contract.md --path docs/work-packages/20260410_rq_controller_state_foundation/package.md --path docs/work-packages/20260410_rq_controller_state_foundation/tracker.md --path docs/work-packages/20260410_rq_controller_state_foundation/prompts/completed/rq_controller_state_foundation_execplan.md --path docs/work-packages/20260410_rq_controller_state_foundation/prompts/completed/rq_controller_state_foundation_execplan_outcome.md --path docs/work-packages/20260410_rq_controller_state_foundation/artifacts/2026-04-10_security_review.md --path PROJECT_TRACKER.md` (pass)

---

### RQ Controller State Setup Discovery
**Completed**: 2026-04-10  
**Duration**: 1 focused session  
**Status**: ✅ **COMPLETE**  
**Owner**: Codex  
**Link**: [docs/work-packages/20260410_rq_controller_state_setup_discovery/](docs/work-packages/20260410_rq_controller_state_setup_discovery/)  
**Description**: Implemented non-run-scoped setup-discovery endpoints and contract/test/documentation guardrails so agents can discover valid create configs and setup operation contracts without out-of-band docs.

**Outcome**:
- Added setup-discovery endpoints in rq-engine:
  - `GET /api/configs`
  - `GET /api/configs/{config}`
  - `GET /api/endpoints`
  - `GET /api/endpoints/{operation_id}/schema`
  - `GET /api/endpoints/{operation_id}/defaults`
  - `GET /api/endpoints/{operation_id}/errors`
- Added route/openapi coverage for auth matrix, strict payload contract checks, not-found taxonomy parity, and canonical handled-500 behavior.
- Updated frozen route artifacts and guard mappings for six new agent-facing setup routes.
- Closed medium/high reviewer + QA + security findings (metadata/runtime parity, error-contract boundaries, auth/test coverage).
- Package lifecycle closed with archived ExecPlan and required security artifact:
  - `docs/work-packages/20260410_rq_controller_state_setup_discovery/prompts/completed/rq_controller_state_setup_discovery_execplan.md`
  - `docs/work-packages/20260410_rq_controller_state_setup_discovery/prompts/completed/rq_controller_state_setup_discovery_execplan_outcome.md`
  - `docs/work-packages/20260410_rq_controller_state_setup_discovery/artifacts/2026-04-10_security_review.md`
- Lifecycle recorded: Backlog -> In Progress (2026-04-10 06:58 UTC) -> Done (2026-04-10 07:29 UTC).

**Validation Notes**:
- `wctl run-pytest tests/microservices/test_rq_engine_setup_discovery_routes.py --maxfail=1` (`28 passed`)
- `wctl run-pytest tests/microservices/test_rq_engine_openapi_contract.py --maxfail=1` (`9 passed`)
- `python tools/check_endpoint_inventory.py` (pass)
- `python tools/check_route_contract_checklist.py` (pass)
- `wctl run-pytest tests/tools/test_endpoint_inventory_guard.py tests/tools/test_route_contract_checklist_guard.py --maxfail=1` (`2 passed`)
- `wctl doc-lint --path docs/schemas/rq-controller-state-contract.md --path docs/schemas/rq-engine-agent-api-contract.md --path docs/work-packages/20260208_rq_engine_agent_usability/artifacts/endpoint_inventory_freeze_20260208.md --path docs/work-packages/20260208_rq_engine_agent_usability/artifacts/route_contract_checklist_20260208.md --path docs/work-packages/20260410_rq_controller_state_setup_discovery/package.md --path docs/work-packages/20260410_rq_controller_state_setup_discovery/tracker.md --path docs/work-packages/20260410_rq_controller_state_setup_discovery/prompts/completed/rq_controller_state_setup_discovery_execplan.md --path docs/work-packages/20260410_rq_controller_state_setup_discovery/prompts/completed/rq_controller_state_setup_discovery_execplan_outcome.md --path docs/work-packages/20260410_rq_controller_state_setup_discovery/artifacts/2026-04-10_security_review.md --path PROJECT_TRACKER.md` (pass)

---

### Run Sync Dashboard Source Token Integration
**Completed**: 2026-04-01  
**Duration**: 1 focused session  
**Status**: ✅ **COMPLETE**  
**Owner**: Codex  
**Link**: [docs/work-packages/20260401_run_sync_source_token_integration/](docs/work-packages/20260401_run_sync_source_token_integration/)  
**Description**: Integrated optional source run token support into Run Sync Dashboard and run-sync backend so private source runs can sync with bearer authentication.

**Outcome**:
- Added optional source token form field in:
  - `wepppy/weppcloud/routes/run_sync_dashboard/templates/rq-run-sync-dashboard.htm`
- Added dashboard payload wiring in:
  - `wepppy/weppcloud/controllers_js/run_sync_dashboard.js`
- Updated rq-engine enqueue payload handling in:
  - `wepppy/microservices/rq_engine/run_sync_routes.py`
  - optional `source_run_token` parsing and propagation to `run_sync_rq`.
- Updated worker auth behavior in:
  - `wepppy/rq/run_sync_rq.py`
  - `wepppy/rq/run_sync_rq.pyi`
  - worker now adds `Authorization: Bearer <token>` headers for `aria2c.spec` and aria2 requests when token is provided.
- Fixed and tested run-sync status serialization fallback arg indexes for `config` and `source_host`.
- Updated docs and queue graph artifacts:
  - `docs/run_migration_strategy.md`
  - `wepppy/rq/job-dependencies-catalog.md`
  - `wepppy/rq/job-dependency-graph.static.json`
  - `docs/standards/broad-exception-boundary-allowlist.md`
- Completed code/QA review artifacts with no open medium/high findings:
  - `docs/work-packages/20260401_run_sync_source_token_integration/artifacts/code_review_findings.md`
  - `docs/work-packages/20260401_run_sync_source_token_integration/artifacts/qa_review_findings.md`

**Validation Notes**:
- `wctl run-pytest tests/microservices/test_rq_engine_run_sync_routes.py tests/rq/test_run_sync_rq.py --maxfail=1` (`7 passed`)
- `wctl run-npm lint` (pass)
- `wctl check-rq-graph` (pass; artifacts refreshed)
- `python3 tools/check_broad_exceptions.py --enforce-changed --base-ref origin/master` (`PASS`)
- `wctl doc-lint --path docs/run_migration_strategy.md --path wepppy/rq/job-dependencies-catalog.md --path docs/standards/broad-exception-boundary-allowlist.md --path docs/work-packages/20260401_run_sync_source_token_integration --path PROJECT_TRACKER.md` (`7 files validated, 0 errors, 0 warnings`)

---

### Admin Run-Scoped Token Minting for Sync and Debug Workflows
**Completed**: 2026-04-01  
**Duration**: 1 focused session  
**Status**: ✅ **COMPLETE**  
**Owner**: Codex  
**Link**: [docs/work-packages/20260401_admin_run_token_minting/](docs/work-packages/20260401_admin_run_token_minting/)  
**Description**: Added an admin-only run-scoped token minting workflow (24-hour TTL) in PowerUser Actions for credentialed run sync and debugging.

**Outcome**:
- Added `POST /runs/<runid>/<config>/mint-run-token` in `wepppy/weppcloud/routes/user.py`:
  - requires auth + run authorization + `Admin`/`Root` role,
  - issues `token_class=service` JWT scoped to `runs=[runid]`,
  - fixed TTL `86400` seconds,
  - audiences `rq-engine` and `query-engine`,
  - returns canonical payload with `Cache-Control: no-store`.
- Added admin-only PowerUser "Mint Run Token" card in `wepppy/weppcloud/templates/controls/poweruser_panel.htm` with mint/copy/status/expiry UX using profile-token styling classes.
- Updated tests:
  - `tests/weppcloud/routes/test_user_profile_token.py`
  - `tests/weppcloud/routes/test_pure_controls_render.py`
- Updated docs:
  - `docs/dev-notes/auth-token.spec.md`
  - `wepppy/weppcloud/routes/usersum/weppcloud/getting-started.md`
- Completed code/QA review artifacts with medium/high findings resolved:
  - `docs/work-packages/20260401_admin_run_token_minting/artifacts/code_review_findings.md`
  - `docs/work-packages/20260401_admin_run_token_minting/artifacts/qa_review_findings.md`

**Validation Notes**:
- `wctl run-pytest tests/weppcloud/routes/test_user_profile_token.py tests/weppcloud/routes/test_pure_controls_render.py --maxfail=1` (`49 passed`)
- `wctl run-pytest tests/weppcloud/routes --maxfail=1` (`432 passed`)
- `wctl doc-lint --path docs/dev-notes/auth-token.spec.md --path wepppy/weppcloud/routes/usersum/weppcloud/getting-started.md --path docs/work-packages/20260401_admin_run_token_minting` (`5 files validated, 0 errors, 0 warnings`)
- `python3 tools/check_broad_exceptions.py --enforce-changed --base-ref origin/master` (`PASS`)

---

### Usersum Manifest-Driven Docs Engine (GitBook Layout + Vendor + PostgreSQL Search)
**Completed**: 2026-04-01  
**Duration**: 1 focused session  
**Status**: ✅ **COMPLETE**  
**Owner**: Codex  
**Link**: [docs/work-packages/20260401_usersum_docs_engine/](docs/work-packages/20260401_usersum_docs_engine/)  
**Description**: Converted usersum into a manifest-driven documentation engine with role-aware visibility, vendor sync support, GitBook-like navigation shell, and PostgreSQL FTS/`pg_trgm` search while retaining compatibility routes.

**Outcome**:
- Added machine-readable usersum contracts + generated index pipeline:
  - `docs_manifest.yaml`, `nav_tree.yaml`, `vendors.yaml`
  - `generated/docs_index.json`
  - tooling: `tools/usersum_docs_tool.py` (`validate`, `sync-vendors`, `build-index`)
- Added vendor sync for initial `weppcloud-wbt` scope and committed vendored docs under `/usersum/vendor/weppcloud-wbt/...`.
- Refactored usersum runtime to manifest/index-backed resolution with role-enforced visibility and canonical/doc vendor routes:
  - `GET /usersum/doc/<doc_id>`
  - `GET /usersum/vendor/<vendor_id>/<path:filename>`
  - compatibility routes preserved (`/usersum/view/*`, `/usersum/src/*`, `/usersum/raw/*`)
- Implemented GitBook-like shell features:
  - top header search (aligned with theme selector),
  - sticky collapsible nav tree,
  - breadcrumb links,
  - theme-aware sidebar/buttons/scrollbar and full-width usersum shell.
- Implemented PostgreSQL search backend integration (FTS + trigram) with explicit fallback behavior and site-prefix-safe route emission.
- Completed required code and QA review artifacts with all medium/high findings resolved:
  - `artifacts/code_review_findings.md`
  - `artifacts/qa_review_findings.md`

**Validation Notes**:
- `PYTHONPATH=/workdir/wepppy python3 tools/usersum_docs_tool.py validate` (pass)
- `PYTHONPATH=/workdir/wepppy python3 tools/usersum_docs_tool.py validate --require-vendor-files` (pass)
- `python3 tools/check_broad_exceptions.py --enforce-changed --base-ref origin/master` (pass)
- `wctl run-pytest tests/weppcloud/routes/test_usersum_bp.py tests/weppcloud/test_usersum_template_wiring.py tests/weppcloud/routes/test_usersum_docs_contracts.py tests/weppcloud/routes/test_usersum_docs_index.py --maxfail=1` (`28 passed`)
- `wctl run-pytest tests/weppcloud/routes/test_usersum_bp.py tests/weppcloud/test_usersum_template_wiring.py --maxfail=1` (`23 passed`)
- Baseline broad-suite gate during package execution:
  - `wctl run-pytest tests --maxfail=1` (`2971 passed, 36 skipped`)
- `wctl run-npm lint` (pass)
- `wctl run-npm test` (pass)

---

### Disturbed BD Override + Rosetta WC/FC Recompute
**Completed**: 2026-04-01  
**Duration**: 1 focused session  
**Status**: ✅ **COMPLETE**  
**Owner**: Codex  
**Link**: [docs/work-packages/20260401_disturbed_bd_rosetta_wc_fc/](docs/work-packages/20260401_disturbed_bd_rosetta_wc_fc/)  
**Description**: Added disturbed lookup `bd` override support and an opt-in WEPP advanced option that recomputes top-horizon `wp/fc` using Rosetta when numeric disturbed `bd` overrides are present.

**Outcome**:
- Added canonical disturbed lookup schema change (`bd` after `avke`) with blank defaults and additive upgrade coverage.
- Added persisted Soils flag `rosetta_wc_fc_from_disturbed_bd_override` plus WEPP advanced-options checkbox with exact requested label.
- Wired checkbox serialization/persistence through rq-engine WEPP run/prep routes.
- Implemented strict disturbed `bd` parsing/validation:
  - empty value = no override,
  - malformed non-numeric text = hard error,
  - numeric bounds = `0.6-2.2 g/cm^3`.
- Implemented top-horizon-only `bd` override + optional top-horizon Rosetta `wp/fc` recomputation in disturbed soil conversion.
- Completed mandatory `reviewer` and `qa_reviewer` passes and resolved all medium/high findings with artifact capture.

**Validation Notes**:
- `wctl run-pytest tests/nodb/mods/disturbed/test_lookup_contract.py tests/nodb/mods/disturbed/test_modify_soils_single_ofe.py tests/nodb/mods/disturbed/test_modify_soils_mofe.py tests/wepp/soils/utils/test_wepp_soil_util.py tests/microservices/test_rq_engine_wepp_routes.py tests/nodb/test_soils_gridded_root_creation.py tests/weppcloud/routes/test_pure_controls_render.py --maxfail=1` (`154 passed`)
- `wctl run-pytest tests/microservices/test_rq_engine_wepp_routes.py tests/microservices/test_rq_engine_soils_routes.py --maxfail=1` (`23 passed`)
- `wctl run-pytest tests --maxfail=1` (`2952 passed, 36 skipped`)
- `wctl run-npm lint` (pass)
- `wctl run-npm test -- wepp` (pass)
- `wctl check-test-stubs` (pass)
- `wctl run-stubtest wepppy.wepp.soils.utils.wepp_soil_util` (pass)
- `wctl run-stubtest wepppy.nodb.core.soils` (pass)

---

### Disturbed Panel Modal and Landsoil Lookup UX Contract
**Completed**: 2026-03-30  
**Duration**: 1 focused session  
**Status**: ✅ **COMPLETE**  
**Owner**: Codex  
**Link**: [docs/work-packages/20260330_disturbed_panel_modal/](docs/work-packages/20260330_disturbed_panel_modal/)  
**Description**: Added a dedicated Disturbed modal in the run-page/report More menu, relocated disturbed lookup actions out of PowerUser, and formalized the base/extended lookup workflow plus docs-link helper contract.

**Outcome**:
- Added new Disturbed modal template with requested sections:
  - landsoil lifecycle actions (reset base, load extended, delete extended),
  - table-resource selection radios (base/disturbed),
  - explicit modify actions (base, extended, sync base to extended),
  - Help link generated via usersum helper with `📄` affordance.
- Removed disturbed lookup action block and external disturbed-doc link from PowerUser panel.
- Added disturbed task routes:
  - `POST .../tasks/delete_extended_land_soil_lookup`
  - `POST .../tasks/sync_base_to_extended_land_soil_lookup`
- Extended disturbed controller wiring for delete/sync actions and lookup-variant UI state refresh.
- Added reusable Jinja helper `usersum_doc_link(...)` and published canonical developer contract doc at `docs/ui-docs/disturbed-panel-ui-contract.md`.

**Validation Notes**:
- `python3 wepppy/weppcloud/controllers_js/build_controllers_js.py`
- `wctl run-npm lint`
- `wctl run-npm test`
- `wctl run-pytest tests/weppcloud/routes/test_disturbed_bp.py tests/weppcloud/routes/test_pure_controls_render.py tests/weppcloud/test_jinja_filters.py --maxfail=1` (`65 passed`)
- `wctl run-pytest tests --maxfail=1` (`2858 passed, 35 skipped`)

---

### Features Export Profiles + Provenance Zip Packaging
**Completed**: 2026-03-28  
**Duration**: 1 focused session  
**Status**: ✅ **COMPLETE**  
**Owner**: Codex  
**Link**: [docs/work-packages/20260328_features_export_profiles_provenance_zip/](docs/work-packages/20260328_features_export_profiles_provenance_zip/)  
**Description**: Replaced legacy Features Export defaults with profile-driven UX and standardized all export downloads as zip bundles that include payload outputs plus replay/provenance files.

**Outcome**:
- Added built-in profiles (`post-wepp.yml`, `prep-details.yml`) and run-page profile controls (quick profile buttons + profile-text load).
- Added rq-engine profile resolve endpoint: `POST /api/runs/{runid}/{config}/export/features/profile/resolve`.
- Refactored service packaging so final artifacts are zip bundles containing payload members, `manifest.json`, `profile.yml`, built-in profile files, and `README.md`.
- Extended manifest payload with profile/provenance relpath fields and bumped features-export cache version marker for packaging contract change.

**Validation Notes**:
- `wctl run-pytest tests/nodb/mods/test_features_export_service.py tests/nodb/mods/test_features_export_manifest.py tests/microservices/test_rq_engine_features_export_routes.py tests/weppcloud/routes/test_pure_controls_render.py tests/weppcloud/routes/test_run_0_openet_admin_gate.py --maxfail=1` (`113 passed`)
- `wctl run-pytest tests/nodb/mods/test_features_export_exporters.py tests/nodb/mods/test_features_export_manifest.py --maxfail=1` (`21 passed`)
- `wctl run-npm test -- features_export` (`22 passed`)

---

### Features Export Service Compliance Refactor (4-Phase E2E)
**Completed**: 2026-03-28  
**Duration**: 1 focused session  
**Status**: ✅ **COMPLETE**  
**Owner**: Codex  
**Link**: [docs/work-packages/20260328_features_export_service_compliance_refactor/](docs/work-packages/20260328_features_export_service_compliance_refactor/)  
**Description**: Closed the QA follow-up four-phase service quality pass for `features_export` by extracting legacy/carrier collaborators, removing dead wrappers, adding missing strict-required branch tests, and validating end-to-end behavior.

**Outcome**:
- Added collaborators:
  - `wepppy/nodb/mods/features_export/legacy_source_materializer.py`
  - `wepppy/nodb/mods/features_export/carrier_layer_materializer.py`
- Refactored `service.py` to delegate legacy and carrier source materialization responsibilities to collaborators.
- Added `discover_layer_sources(..., skip_vector_relpath=...)` support to reuse strict required-source policy for legacy flows without duplicated logic.
- Removed dead wrappers and unused helper code in service (`_column_metadata_by_id`, `_identity_column_token`, legacy parquet helpers no longer needed after extraction).
- Added missing strict-required tests (`file_missing`, `unsupported_source_kind`, and carrier-path materialization error translation).
- Preserved run-path behavior and counts on baseline smoke run (`66` subcatchments, `27` channels).

**Validation Notes**:
- `wctl run-pytest tests/nodb/mods/test_features_export_service.py -k "required_source or discover_layer_sources or materialization_error or ensure_join_key" --maxfail=1` (`9 passed`)
- `wctl run-pytest tests/nodb/mods/test_features_export_planner.py tests/nodb/mods/test_features_export_service.py tests/nodb/mods/test_features_export_exporters.py tests/microservices/test_rq_engine_features_export_routes.py --maxfail=1` (`65 passed`)
- `wctl run-pytest tests/weppcloud/routes/test_pure_controls_render.py -k features_export --maxfail=1` (`4 passed`)
- `wctl run-pytest tests/weppcloud/routes/test_run_0_openet_admin_gate.py -k features_export --maxfail=1` (`10 passed`)
- `wctl run-npm test -- features_export` (`12 passed`)
- `python3 tools/check_broad_exceptions.py --enforce-changed --base-ref origin/master` (pass; net delta `-1`)

### Features Export Service Quality Refactor (Phased E2E)
**Completed**: 2026-03-28  
**Duration**: 2 focused sessions  
**Status**: ✅ **COMPLETE**  
**Owner**: Codex  
**Link**: [docs/work-packages/20260327_features_export_service_quality_refactor/](docs/work-packages/20260327_features_export_service_quality_refactor/)  
**Description**: Completed phased quality refactor of `wepppy/nodb/mods/features_export/service.py` with contract hardening, collaborator extraction, strict required-source enforcement, and full validation/evidence closure.

**Outcome**:
- Removed hidden identity-key fallback and enforced explicit `materialization_error` behavior when join-key contracts do not resolve.
- Enforced strict required-source handling on both legacy merge and carrier discovery paths (no warning-only degrade for required missing/unsupported sources).
- Extracted service collaborators:
  - `wepppy/nodb/mods/features_export/column_selection.py`
  - `wepppy/nodb/mods/features_export/cache_rehydration.py`
- Expanded service regression tests for required-source failure branches, join-key contracts, and malformed cache-entry fallback behavior.
- Updated `wepppy/nodb/mods/features_export/specification.md` to lock strict required-source and explicit identity-key contract semantics.
- Completed review artifacts with no unresolved medium/high findings.

**Validation Notes**:
- `wctl run-pytest tests/nodb/mods/test_features_export_planner.py tests/nodb/mods/test_features_export_service.py tests/nodb/mods/test_features_export_exporters.py tests/microservices/test_rq_engine_features_export_routes.py --maxfail=1` (`62 passed`)
- `wctl run-pytest tests/weppcloud/routes/test_pure_controls_render.py -k features_export --maxfail=1` (`4 passed`)
- `wctl run-pytest tests/weppcloud/routes/test_run_0_openet_admin_gate.py -k features_export --maxfail=1` (`10 passed`)
- `wctl run-npm test -- features_export` (`12 passed`)
- `python3 tools/check_broad_exceptions.py --enforce-changed --base-ref origin/master` (pass; net delta `-1`)
- `wctl doc-lint --path wepppy/nodb/mods/features_export/specification.md` (pass)
- `wctl doc-lint --path docs/work-packages/20260327_features_export_service_quality_refactor/package.md` (pass)
- `wctl doc-lint --path docs/work-packages/20260327_features_export_service_quality_refactor/tracker.md` (pass)
- `wctl doc-lint --path docs/work-packages/20260327_features_export_service_quality_refactor/prompts/completed/features_export_service_quality_refactor_execplan.md` (pass)

### Roads GeoJSON Attribute Discovery and Mapping UI
**Completed**: 2026-03-26  
**Duration**: 2 focused sessions  
**Status**: ✅ **COMPLETE**  
**Owner**: Codex  
**Link**: [docs/work-packages/20260326_roads_geojson_attribute_mapping/](docs/work-packages/20260326_roads_geojson_attribute_mapping/)  
**Description**: Added Roads GeoJSON attribute discovery with explicit mapping controls for `design`, `surface`, and `traffic`, plus user-configurable fallback values (`surface_default` and `traffic_default`) and end-to-end validation.

**Outcome**:
- Upload/config payloads now expose discovered top-level feature-property catalog metadata and persisted mapping state.
- Prepare-stage design eligibility now respects mapping-aware key resolution.
- Run-stage `surface`/`traffic` now use mapped-field resolution with explicit fallback values (`surface`: `gravel|paved`; `traffic`: `high|low|none`).
- Roads UI now supports mapping apply workflow and fallback value selection after upload.
- Regression coverage added/updated across NoDb controller, monotonic segment utility, roads routes, and Roads JS controller.
- Manual run-page E2E confirmed by user: UI mapping flow worked as expected and Roads WEPP run completed successfully.

**Validation Notes**:
- `wctl run-pytest tests/nodb/mods/test_roads_controller.py --maxfail=1`
- `wctl run-pytest tests/nodb/mods/test_roads_monotonic_segments.py --maxfail=1`
- `wctl run-pytest tests/weppcloud/routes/test_roads_bp.py --maxfail=1`
- `wctl run-pytest tests/weppcloud/routes/test_pure_controls_render.py --maxfail=1`
- `wctl run-npm test -- roads`
- `wctl run-npm lint`
- `wctl run-pytest tests --maxfail=1`

### Disturbed Lookup Hardening and Preservation
**Completed**: 2026-03-26 (reopen addendum)  
**Duration**: 2 focused sessions  
**Status**: ✅ **COMPLETE**  
**Owner**: Codex  
**Link**: [docs/work-packages/20260325_disturbed_lookup_hardening/](docs/work-packages/20260325_disturbed_lookup_hardening/)  
**Description**: Hardened disturbed lookup CSV persistence against user-edit loss, then reopened to add stale-page lockout/recovery UX and double-submit safeguards while preserving `?pup` compatibility.

**Outcome**:
- Hardened disturbed lookup writes with strict payload validation, duplicate-key rejection, and missing-row guardrails to block partial-table truncation.
- Hardened legacy schema upgrade/read behavior so `disturbed_class`/`texid` rows remain readable after upgrade.
- Prevented extended lookup export from clobbering editable lookup CSV (`disturbed_land_soil_lookup_extended.csv` now separate artifact).
- Updated disturbed CSV editor to dynamic header-driven columns for the full lookup schema.
- Added strict optimistic concurrency (`if_match_sha256`) for disturbed lookup writes and explicit stale/version-unavailable write-block contracts.
- Added stale-page safeguards in disturbed editor: polling-based stale detection, locked editing on stale state, and explicit `Load Current Table` / `Refresh Page` actions.
- Added in-flight save table lock to reduce duplicate-submission/user-confusion paths.
- Added route-side observability events for blocked/committed disturbed lookup writes.
- Completed reviewer + QA subagent passes with artifacts and no unresolved medium/high findings.

**Validation Notes**:
- `wctl run-pytest tests/weppcloud/routes/test_disturbed_bp.py --maxfail=1`
- `wctl run-pytest tests/nodb/mods/test_disturbed_lookup_persistence.py --maxfail=1`
- `wctl run-pytest tests/nodb/mods -k disturbed --maxfail=1`
- `wctl run-pytest tests --maxfail=1`
- `wctl run-stubtest wepppy.weppcloud.routes.nodb_api.disturbed_bp`
- `wctl check-test-stubs`
- `wctl run-npm lint`
- `wctl run-npm test`

### Peridot Watershed Parquet + Manifest Integration
**Completed**: 2026-03-21  
**Duration**: 1 focused session  
**Status**: ✅ **COMPLETE**  
**Owner**: Codex  
**Link**: [docs/work-packages/20260321_peridot_watershed_parquet_manifest/](docs/work-packages/20260321_peridot_watershed_parquet_manifest/)  
**Description**: Implemented direct Peridot watershed parquet outputs plus flag-aware `watershed/README.md` manifest generation, then switched WEPPpy to parquet-first ingestion with explicit legacy CSV fallback/migration behavior.

**Outcome**:
- Peridot now writes `watershed/hillslopes.parquet`, `watershed/channels.parquet`, and conditional `watershed/flowpaths.parquet` for both `abstract_watershed` and `wbt_abstract_watershed`.
- Peridot now writes `watershed/README.md` with execution flags, file manifest, tabular schema summary, and conditional notes.
- WEPPpy now consumes watershed parquet directly for new runs, logs explicit CSV fallback warnings for legacy runs, and keeps `migrate_watershed_outputs()` functional for old CSV-only projects.
- WEPPpy post-processing now refreshes README manifest/schema sections to reflect final canonical parquet outputs after derived-column normalization.
- Added Rust and pytest coverage for parquet generation, manifest conditionals, direct parquet path, legacy fallback, and migration edge cases.
- Completed real-run verification on `/wc1/runs/un/unassailable-sensuousness`, including slope sanity check against `wepp/runs/p*.slp`.

**Validation Notes**:
- `cargo test --test watershed_parquet_manifest -- --nocapture` passed (`3 passed`).
- `cargo test --test hillslope_slope_scalar -- --nocapture` passed (`1 passed`).
- `wctl run-pytest tests/topo/test_peridot_runner_wait.py` passed (`11 passed`).
- `wctl run-pytest tests/tools/test_migrations_parquet_backfill.py -k watershed` passed.

### RUSLE NoDb + Run-Page UI Integration
**Completed**: 2026-03-21  
**Duration**: 1 focused session  
**Status**: ✅ **COMPLETE**  
**Owner**: Codex  
**Link**: [docs/work-packages/20260321_rusle_nodb_ui/](docs/work-packages/20260321_rusle_nodb_ui/)  
**Description**: Completed RUSLE Milestones 6-7 with end-to-end NoDb orchestration, async RQ build route, run-header/run-page UI integration, preflight/task wiring, stale invalidation, and full review/QA/validation closeout.

**Outcome**:
- Added `Rusle` NoDb facade (`wepppy/nodb/mods/rusle/rusle.py`) and exports.
- Added async RQ/API flow (`build_rusle_rq`, `POST /api/runs/{runid}/{config}/build-rusle`).
- Added disturbed-gated mod toggle + dynamic run-page section rendering with Rusle controls after WEPP.
- Added preflight `TaskEnum.build_rusle` (`🔱`) checklist/TOC wiring and staleness invalidation on climate and SBS updates.
- Added focused tests across nodb, rq-engine, WEPPcloud routes/templates/controllers, and preflight checklist logic.
- Synchronized frozen route artifacts/checklists for the new agent-facing endpoint (`build-rusle`) and updated frozen-route count assertion.

**Validation Notes**:
- Required gates passed: `tests/nodb`, `tests/weppcloud`, npm lint/test, broad-exception enforcement, code-quality observability (observe-only), and full suite (`2443 passed, 34 skipped`).

### RUSLE C Modes Implementation (`observed_rap` + `scenario_sbs`)
**Completed**: 2026-03-21  
**Duration**: 1 focused session  
**Status**: ✅ **COMPLETE**  
**Owner**: Codex  
**Link**: [docs/work-packages/20260321_rusle_c_modes_implementation/](docs/work-packages/20260321_rusle_c_modes_implementation/)  
**Description**: Completed RUSLE `C` Milestone 5 by implementing the shared `C` engine, the locked `observed_rap` and `scenario_sbs` modes, auditable run-scoped artifacts, and dedicated review/QA/validation artifacts.

**Outcome**:
- Added new RUSLE `C` modules under `wepppy/nodb/mods/rusle/`: `c_formula.py`, `c_lookup.py`, `c_manifest.py`, `c_integration.py`.
- Added the runtime lookup substrate: `wepppy/nodb/mods/rusle/data/rusle_c_lookup.csv`.
- Updated `wepppy/nodb/mods/rusle/__init__.py` exports with the new `C` helpers and integration entrypoint.
- Implemented `observed_rap` with the exact locked contract:
  - `fg = clamp(100 - bare_ground_pct, 0, 100)`
  - `C = exp(-0.04 * fg)`
  - neutral canopy/roughness/biomass/consolidation terms
- Implemented `scenario_sbs` with:
  - DEM-aligned `disturbed_class.tif`
  - disturbed-family normalization (`young forest -> forest`)
  - burn-only application for `forest`, `shrub`, and `tall_grass`
  - explicit non-burnable policy enforcement and fail-fast missing-row behavior
- Added targeted tests: `test_rusle_c_formula.py`, `test_rusle_c_lookup.py`, `test_rusle_c_integration.py`.
- Captured package artifacts: `artifacts/milestone4_review.md`, `artifacts/milestone5_qa_review.md`, `artifacts/final_validation_summary.md`.

**Validation Notes**:
- Passed targeted `RUSLE C` suite (`19 passed`).
- Passed broad-exception changed-file enforcement and code-quality observability (observe-only).
- Passed full WEPPpy sanity gate (`2429 passed, 34 skipped`).

### RUSLE POLARIS K Implementation + NRCS Benchmark Harness
**Completed**: 2026-03-21  
**Duration**: 1 focused session  
**Status**: ✅ **COMPLETE**  
**Owner**: Codex  
**Link**: [docs/work-packages/20260321_rusle_k_polaris_implementation/](docs/work-packages/20260321_rusle_k_polaris_implementation/)  
**Description**: Completed RUSLE `K` Milestone 4 by implementing `polaris_nomograph` and `polaris_epic`, adding deterministic `gnatsgo/gssurgo` benchmark harness support, and shipping sanity comparison + review/QA artifacts.

**Outcome**:
- Added K implementation modules under `wepppy/nodb/mods/rusle/`: `k_nomograph.py`, `k_epic.py`, `k_reference.py`, `k_compare.py`, `k_manifest.py`, `k_integration.py`.
- Updated `wepppy/nodb/mods/rusle/__init__.py` exports with K integration and comparison entrypoints.
- Added targeted K tests: `test_rusle_k_nomograph.py`, `test_rusle_k_epic.py`, `test_rusle_k_reference_harness.py`, `test_rusle_k_compare.py`, `test_rusle_k_integration.py`.
- Implemented benchmark mode precedence contract: `gssurgo_kffact` -> `gnatsgo_kffact` -> `gssurgo_kwfact` -> `gnatsgo_kwfact`.
- Locked Milestone 0 contracts in manifest/docs: depth support (`0_5`,`5_15` with `5/10 cm` weights), EPIC OC conversion (`OM/1.724`), comparison thresholds defaults, and `cfvo` deferred scope.
- Captured package artifacts: `artifacts/milestone4_review.md`, `artifacts/milestone5_qa_review.md`, `artifacts/k_benchmark_comparison_summary.md`.

**Validation Notes**:
- Passed targeted K suite (`16 passed`).
- Passed broad-exception changed-file enforcement and code-quality observability (observe-only).
- Passed full WEPPpy sanity gate (`2410 passed, 34 skipped`).

### RUSLE Static R + WEPPpyo3 Hyetograph API Migration
**Completed**: 2026-03-21  
**Duration**: 2 focused sessions  
**Status**: ✅ **COMPLETE**  
**Owner**: Codex  
**Link**: [docs/work-packages/20260320_rusle_r_static_hyetograph_api/](docs/work-packages/20260320_rusle_r_static_hyetograph_api/)  
**Description**: Implemented static `R` (`cligen_static`) and shared hyetograph helpers in `wepppyo3.climate`, migrated WEPPpy climate callsites to canonical outputs, and delivered dedicated review + QA-review artifacts.

**Outcome**:
- Added new `wepppyo3.climate` API surface for non-breakpoint/breakpoint hyetograph reconstruction, peak-intensity windows, and static-`R` from CLI.
- Synced canonical py312 runtime release artifacts under `/home/workdir/wepppyo3/release/linux/py312/`.
- Migrated in-scope WEPPpy consumers (`cligen.py`, climate artifact export, interchange fallback, return-period staging) to use canonical `peak_intensity_*` + duration schema handling.
- Removed breakpoint sentinel intensity behavior and ensured exported artifacts include `dur`, nullable `tp/ip`, `storm_duration_*`, and `peak_intensity_10/15/30/60`.
- Added regression coverage in `tests/climate/test_cligen_peak_intensity_contract.py`, `tests/nodb/test_climate_artifact_export_service.py`, and `tests/wepp/interchange/test_utils_phase7.py`.
- Added deterministic breakpoint intensity assertions, static-`R` aggregation invariants, repeated non-breakpoint stability checks, and parquet coalescing-precedence coverage.
- Captured Milestone 4/5 review artifacts and final validation summary under package `artifacts/`.

**Validation Notes**:
- Passed: targeted migration tests, Rust tests, broad-exception changed-file enforcement, code-quality observability (observe-only), package/spec/tracker doc lint, and full WEPPpy sanity suite (`2392 passed, 34 skipped`).

**Deliverables**:
- ✅ New `wepppyo3` hyetograph + static-`R` API implementation and py312 release sync
- ✅ WEPPpy callsite migration + breakpoint artifact contract upgrades
- ✅ Review/QA/final-validation artifacts and completed ExecPlan

---

### RUSLE LS Factor Tooling in weppcloud-wbt
**Completed**: 2026-03-20  
**Duration**: 1 focused session  
**Status**: ✅ **COMPLETE**  
**Owner**: Codex  
**Link**: [docs/work-packages/20260320_rusle_ls_factor_wbt/](docs/work-packages/20260320_rusle_ls_factor_wbt/)  
**Description**: Implemented a purpose-built `RusleLsFactor` WhiteboxTools command using locked v1 `LS` science (`Desmet-Govers` `L`, `McCool/RUSLE` `S`, `DInf` default routing), plus end-to-end `wepppy` integration and manifest provenance.

**Outcome**:
- Added `whitebox-tools-app/src/tools/terrain_analysis/rusle_ls_factor.rs` and registered it in terrain-analysis exports + tool manager dispatch.
- Added wrapper methods in both binding files (`whitebox_tools.py`, `WBT/whitebox_tools.py`) and verified tool discoverability via `--listtools`.
- Added WEPPpy LS integration (`wepppy/nodb/mods/rusle/ls_integration.py`, `wepppy/nodb/mods/rusle/__init__.py`) and regression tests (`tests/nodb/mods/test_rusle_ls_integration.py`).
- Finalized LS spec edits for default 304.8 m cap, DEM assumptions, stop-mask routing semantics, and metadata contract.
- Validation passed: WBT build/check/tests + wrapper compile checks, targeted LS integration tests, and full WEPPpy suite (`2385 passed, 34 skipped`).
- Real-run acceptance on 5 `/wc1/runs/*` DEMs passed with breached-preprocess workflow, including LS identity (`< 2e-5` max absolute error), cap enforcement, and expected fail-fast rejection of unconditioned pit-containing DEMs.

**Deliverables**:
- ✅ New `RusleLsFactor` tool + registration + Python bindings
- ✅ WEPPpy LS integration entrypoint and tests
- ✅ Closed package artifacts (`package.md`, `tracker.md`, completed ExecPlan)

---

### Runtime Path Locks Redis Migration
**Completed**: 2026-03-17  
**Duration**: 1 focused session  
**Status**: ✅ **COMPLETE**  
**Owner**: Codex  
**Link**: [docs/work-packages/20260317_runtime_path_redis_locks/](docs/work-packages/20260317_runtime_path_redis_locks/)  
**Description**: Replaced host-local runtime-path lock files with Redis-backed distributed runtime locks and added command-bar runtime directory lock status/clear operations.

**Outcome**:
- Migrated runtime lock acquire/release/status/clear behavior to Redis in `wepppy/runtime_paths/thaw_freeze.py`, including compatibility-safe contention checks and token-safe clear behavior.
- Added command-bar routes and UI commands for runtime directory locks (`get directory_locks`, `clear directory_locks`) with canonical 503 error payload handling.
- Updated `NODIR_LOCKED` guidance to direct operators to `:clear directory_locks` or wait for TTL expiry.
- Added/updated tests in `tests/runtime_paths/test_mutations_thaw_freeze_contract.py` and `tests/weppcloud/routes/test_command_bar_mcp_token.py`.
- Incorporated pre-closure subagent code review + QA review findings before final validation.
- Validation passed: `tests/runtime_paths`, `tests/weppcloud/routes`, changed-file broad-exception guard, and full suite (`2333 passed, 34 skipped`).

**Deliverables**:
- ✅ Redis-backed runtime lock implementation and helper exports
- ✅ Runtime directory lock command-bar backend + frontend controls
- ✅ Regression coverage for clear/status flows and clear-token safety
- ✅ Closed work-package docs/tracker + completed ExecPlan

---

### Omni Contrast Hillslope Re-run Recovery (`delete_after_interchange`)
**Completed**: 2026-03-17  
**Duration**: 1 focused session  
**Status**: ✅ **COMPLETE**  
**Owner**: Codex  
**Link**: [docs/work-packages/20260317_omni_contrast_hillslope_rerun/](docs/work-packages/20260317_omni_contrast_hillslope_rerun/)  
**Description**: Added a contrast preflight in `run_omni_contrasts_rq` that reruns hillslopes (without prep and without interchange) for deduped scenarios referenced by queued contrast runs when `delete_after_interchange` has removed source hillslope outputs.

**Outcome**:
- Shipped new preflight helpers in `wepppy/rq/omni_rq.py` to collect deduped scenario keys, resolve scenario working directories, and rerun `Wepp.run_hillslopes()` before contrast enqueue fan-out, including scenario `cli/slp` relpaths back to base runs for existing Omni scenario workspaces.
- Kept existing skip/selection semantics intact by deriving rerun targets from finalized `run_ids`.
- Added regression coverage in `tests/rq/test_omni_rq.py` for delete-flag-enabled rerun + dedupe behavior and delete-flag-disabled no-rerun behavior.
- Synced boundary allowlist line anchors for `wepppy/rq/omni_rq.py` after helper insertion shifted line numbers.
- Validation passed: targeted tests, changed-file broad-exception guard, and full suite (`2323 passed, 34 skipped`).

**Deliverables**:
- ✅ `run_omni_contrasts_rq` rerun preflight for contrast scenarios under delete-after-interchange mode
- ✅ Focused regression tests for rerun gate/dedup/order behavior
- ✅ Package closure artifacts (`package.md`, `tracker.md`, completed ExecPlan, project tracker updates)

---

### POLARIS NoDb Runs Client for Project-Aligned Raster Layers
**Completed**: 2026-03-14  
**Duration**: 2 focused sessions  
**Status**: ✅ **COMPLETE**  
**Owner**: Codex  
**Link**: [docs/work-packages/20260313_polaris_nodb_runs_client/](docs/work-packages/20260313_polaris_nodb_runs_client/)  
**Description**: Added a run-scoped, config-driven POLARIS NoDb/mods client that fetches endpoint layers and aligns GeoTIFF outputs to project raster grid contracts.

**Outcome**:
- Shipped `wepppy/nodb/mods/polaris/*` with catalog-driven layer selection and default top-horizon `sand/clay/bd/om` acquisition.
- Added async endpoint/task flow: `POST /api/runs/{runid}/{config}/acquire-polaris` -> `fetch_and_align_polaris_rq`.
- Added run-local artifacts under `polaris/` (`*.tif`, `manifest.json`, generated `README.md`) with attribution/metadata.
- Added targeted unit + microservice tests including `acquire_and_align` idempotent skip and `force_refresh` behavior.
- Verified real-run integration on `/wc1/runs/in/insightful-peacock` with DEM grid parity checks.
- Full-suite sanity passed: `wctl run-pytest tests --maxfail=1` -> `2321 passed, 34 skipped`.

**Deliverables**:
- ✅ NoDb mod + config wiring (`[polaris]` section in `disturbed9002_wbt.cfg`)
- ✅ rq-engine route + RQ task + RedisPrep task enum wiring
- ✅ Route-freeze artifact updates (`endpoint_inventory_freeze_20260208.md`, `route_contract_checklist_20260208.md`)
- ✅ Work-package closure artifacts and completed ExecPlan

---

### Tenerife 2026 Data Ingestion
**Completed**: 2026-03-12  
**Duration**: 1 focused session after discovery setup  
**Status**: ✅ **COMPLETE**  
**Owner**: Codex  
**Link**: [docs/work-packages/20260312_tenerife_2026_data_ingestion/](docs/work-packages/20260312_tenerife_2026_data_ingestion/)  
**Description**: Integrated Jonay's 2026 Tenerife refresh by switching Tenerife to a dedicated climate station catalog, validating the new DEM keys, and making the Tenerife soil runtime inventory explicit.

**Outcome**:
- Added a dedicated Tenerife climate catalog (`tenerife_stations.db`, `tenerife_stations.csv`, `tenerife_par_files/`) plus a repeatable builder script.
- Switched the active Tenerife 25 m and 5 m configs off shared `ghcn_stations.db` and onto `tenerife_stations.db`.
- Verified live `wmesque2` retrieval for `tenerife/136_MDT25_TF` and `tenerife/MDT05_Tenerife`.
- Added Tenerife regression coverage for climate catalog loading, config wiring, and supported soil raster coverage.
- Retired the legacy Tenerife 250 m soil/config branch and template-generation artifacts while keeping `tf_soil_10.tif` as reference-only inventory.

---

### WEPPcloud CSRF Rollout with rq-engine API Compatibility
**Completed**: 2026-02-24
**Duration**: 1 day
**Status**: ✅ **COMPLETE**
**Owner**: Codex
**Link**: [docs/work-packages/20260224_weppcloud_csrf_rollout/](docs/work-packages/20260224_weppcloud_csrf_rollout/)
**Description**: Implemented global CSRF protection for WEPPcloud cookie-auth mutation routes while preserving bearer-token compatibility for rq-engine/browse/files third-party and agent clients.

**Outcome**: Browser mutation routes are CSRF-protected by default with template-driven token propagation, bootstrap forward-auth verify remains explicitly exempt, and rq-engine cookie-path session-token issuance now enforces same-origin while bearer flows remain unchanged.

**Deliverables**:
- ✅ Artifacts: route classification, exemption register, reviewer findings, code quality review, final validation summary
- ✅ Runtime changes: global CSRFProtect wiring, config toggles, base template CSRF propagation, OAuth disconnect migration, bootstrap exemption wiring
- ✅ Frontend hardening: CSRF bootstrap moved to `static/js/csrf_bootstrap.js` with dedicated Jest coverage
- ✅ Compatibility hardening: rq-engine session-token same-origin checks for cookie path only
- ✅ Proxy hardening: rq-engine forwarded-origin aliases now require explicit opt-in (`RQ_ENGINE_TRUST_FORWARDED_ORIGIN_HEADERS=true`)
- ✅ Validation gates executed: required pytest slices, npm `http` suite, npm `csrf_bootstrap` suite, code-quality observability, doc-lint
- ✅ `check_broad_exceptions --enforce-changed` PASS after allowlist line-position synchronization

---

### Residual Broad-Exception Closure Finish Line
**Completed**: 2026-02-24
**Duration**: 1 day
**Status**: ✅ **COMPLETE**
**Owner**: Codex
**Link**: [docs/work-packages/20260224_residual_broad_exception_finishline/](docs/work-packages/20260224_residual_broad_exception_finishline/)
**Description**: Closed Debt Project #1 residual broad-exception findings for `wepppy/query_engine/app/mcp/router.py` and `wepppy/weppcloud/app.py` with required sub-agent orchestration and validation gates.

**Outcome**: In-scope unresolved findings reached zero (`8 -> 0`) while preserving boundary behavior. Non-boundary query-engine parse catches were narrowed, true boundaries were retained and allowlist-synchronized, and required targeted/full pytest gates passed.

**Deliverables**:
- ✅ Required artifacts: baseline/postfix scanner JSON, baseline inventory, scope resolution matrix, final validation summary
- ✅ Required orchestration: baseline explorer, query-engine worker, weppcloud worker, reviewer, test_guardian
- ✅ Gate results: changed-file broad-exception enforcement PASS (`router.py` delta `-7`)
- ✅ Validation: targeted suites PASS (`36 passed`, `18 passed`), full-suite sanity PASS (`2107 passed, 29 skipped`)

---

### Redis Persistence Session Durability and RQ DB9 Deploy Flush
**Completed**: 2026-02-23
**Duration**: 1 day
**Status**: ✅ **COMPLETE**
**Owner**: Codex
**Link**: [docs/work-packages/20260224_redis_persistence_session_durability/](docs/work-packages/20260224_redis_persistence_session_durability/)
**Description**: Enabled durable Redis defaults in stacks with Redis and introduced explicit deploy-time RQ DB9 flush controls with docs/contract updates for session durability.

**Outcome**: Redis persistence is now durable by default in dev/prod stacks, RQ job resets are explicit and scoped to DB 9 via deploy controls, and session durability expectations/migration implications are documented.

**Deliverables**:
- ✅ Runtime durability defaults + env knobs (`redis-entrypoint`, compose dev/prod wiring)
- ✅ Explicit DB9 flush tooling (`scripts/redis_flush_rq_db.sh`) + deploy flags (`--no-flush-rq-db`, `--require-rq-redis`)
- ✅ Required artifacts: baseline/postfix runtime, deploy flush policy runbook, final validation summary
- ✅ Validation gates: compose renders PASS, targeted pytest PASS, broad-exception enforcement PASS, docs lint PASS
- ✅ Final explorer verification: no remaining high/medium issues

---

### Correlation ID Structured Logging End-to-End
**Completed**: 2026-02-23
**Duration**: 1 day
**Status**: ✅ **COMPLETE**
**Owner**: Codex
**Link**: [docs/work-packages/20260224_correlation_id_structured_logging/](docs/work-packages/20260224_correlation_id_structured_logging/)
**Description**: Implemented canonical `correlation_id` propagation across `weppcloud`, `rq_engine`, `query_engine`, and `rq` with `X-Correlation-ID` ingress/egress behavior, queue metadata continuity, and trace compatibility retention.

**Outcome**: Correlation ID is generated/accepted at ingress, returned in responses, propagated via enqueue/worker metadata, and mapped into query-engine `trace_id` without contract breakage. Final explorer review surfaced a Flask direct-enqueue gap that was fixed before closure.

**Deliverables**:
- ✅ Shared utility module: `wepppy/observability/correlation.py`
- ✅ Required artifacts: baseline inventory, final flow matrix, validation summary, sample log lines
- ✅ Required orchestration: baseline explorer, workers A-D, final explorer review
- ✅ Gate results: targeted suites PASS, broad-exception changed-file enforcement PASS, code-quality observability PASS
- ✅ Validation: `wctl run-pytest tests --maxfail=1` PASS (`2086 passed, 29 skipped`), `wctl check-rq-graph` PASS

---

### Top Modules Broad-Exception Closure
**Completed**: 2026-02-23  
**Duration**: 1 day  
**Status**: ✅ **COMPLETE**  
**Owner**: Codex  
**Link**: [docs/work-packages/20260224_top_modules_broad_exception_closure/](docs/work-packages/20260224_top_modules_broad_exception_closure/)  
**Description**: Closed broad-exception debt for the top remaining module trees, then completed Milestone 6 residual closure to eliminate the remaining global allowlist-aware findings.

**Outcome**: Initial package scope reached zero unresolved (`354 -> 0`), and Milestone 6 closed residual global unresolved findings to zero (`51 -> 0`). Global bare-exception remained zero and full-suite sanity passed after the Milestone 6 refactor pass.

**Deliverables**:
- ✅ Required artifacts: baseline/post scanner JSON, full module resolution matrix, final validation summary
- ✅ Required orchestration: baseline explorer, Workers A-E with ownership split, final explorer regression review
- ✅ Milestone 6 artifacts: `milestone_6_residual_baseline.json`, `milestone_6_resolution_matrix.md`, `milestone_6_postfix.json`, `milestone_6_final_validation_summary.md`
- ✅ Gate results: hard bare gate PASS, target/global unresolved gates PASS, changed-file enforcement PASS
- ✅ Validation: `wctl run-pytest tests --maxfail=1` PASS (`2066 passed, 29 skipped`)

---

### NoDb Broad-Exception Boundary Closure
**Completed**: 2026-02-23  
**Duration**: 1 day  
**Status**: ✅ **COMPLETE**  
**Owner**: Codex  
**Link**: [docs/work-packages/20260223_nodb_broad_exception_boundary_closure/](docs/work-packages/20260223_nodb_broad_exception_boundary_closure/)  
**Description**: Comprehensive broad-exception closure for `wepppy/nodb/**` with required sub-agent orchestration, tests-first characterization, narrowing/removal of non-boundary broad catches, and residual boundary allowlist synchronization.

**Outcome**: NoDb unresolved broad findings in allowlist-aware mode reached zero, NoDb `bare except` stayed zero, required NoDb/full-suite gates passed, and closure artifacts were published.

**Deliverables**:
- ✅ Required artifacts: baseline/final scanner JSON, full resolution matrix, final validation summary
- ✅ Required sub-agent orchestration: baseline explorer, workers A/B/C, final explorer review
- ✅ Gate results: hard bare gate PASS, allowlist-aware unresolved gate PASS, changed-file enforcement PASS
- ✅ Validation: `wctl run-pytest tests/nodb` PASS (`501 passed, 3 skipped`), `wctl run-pytest tests/nodir` PASS (`135 passed`), `wctl run-pytest tests --maxfail=1` PASS (`2066 passed, 29 skipped`)

---

### Bare Exception Zero Closure and Boundary Safety (Phase 2)
**Completed**: 2026-02-23  
**Duration**: 1 day (Phase 2 closure window)  
**Status**: ✅ **COMPLETE**  
**Owner**: Codex  
**Link**: [docs/work-packages/20260223_bare_exception_zero/](docs/work-packages/20260223_bare_exception_zero/)  
**Description**: Reopened and completed broad-exception boundary closure for `weppcloud/routes`, `rq_engine`, and `rq` after the original bare-exception closure.

**Outcome**: Target-module unresolved broad findings in allowlist-aware mode reached zero, global bare-exception count remained zero, and final full-suite validation passed on post-fix state.

**Deliverables**:
- ✅ Required Phase 2 artifacts: baseline/postfix scanner JSON, classification report, final validation summary
- ✅ Required sub-agent orchestration: baseline explorer, 3 subsystem workers, tests/contracts worker, final explorer review
- ✅ Gate results: hard bare gate PASS, target unresolved gate PASS, changed-file enforcement PASS
- ✅ Validation: `wctl run-pytest tests --maxfail=1` PASS (`2060 passed, 29 skipped`)

---

### Broad Exception Elimination and Boundary Contract Hardening
**Completed**: 2026-02-23  
**Duration**: 2 days  
**Status**: ✅ **COMPLETE**  
**Owner**: Codex  
**Link**: [docs/work-packages/20260222_broad_exception_elimination/](docs/work-packages/20260222_broad_exception_elimination/)  
**Description**: Phased elimination of broad exception handlers in runtime-critical production paths with subagent-driven refactoring/review/testing and contract-safe regression controls.

**Outcome**: Package completed through Milestone 7 with changed-file broad-catch guard activation, documented approved boundaries, and full-suite validation.

**Deliverables**:
- ✅ Broad-catch reduction from `1120` to `1103` (`bare-except`: `96` to `82`)
- ✅ Milestone artifacts for phases 0-6 plus final closeout summary
- ✅ Changed-file enforcement mode in `tools/check_broad_exceptions.py` (`--enforce-changed`, `--base-ref`)
- ✅ Checker regression coverage including `except*`/`TryStar` handling
- ✅ Required full gate: `wctl run-pytest tests --maxfail=1` (`2048 passed, 29 skipped`)
- ✅ Boundary allowlist with owner/rationale/expiry in package artifacts

---

### Cross-Service Auth Token Integration Hardening
**Completed**: 2026-02-19  
**Duration**: 1 day  
**Status**: ✅ **COMPLETE**  
**Owner**: Codex  
**Link**: [docs/work-packages/20260219_cross_service_auth_tokens/](docs/work-packages/20260219_cross_service_auth_tokens/)  
**Description**: Established one executable cross-service token contract across WEPPcloud, rq-engine, browse, and query-engine MCP with matrix-driven integration and lifecycle validation.

**Outcome**: Portability, renewal fallback, revocation propagation, rotation overlap/retirement, and grouped/composite runid cookie round-trip are now explicitly tested and mapped to compatibility matrix rows.

**Deliverables**:
- ✅ Integration harness in `tests/integration/` with shared Redis/JWT fixtures
- ✅ Matrix-driven portability tests (`MX-A*`)
- ✅ Lifecycle integration tests (`MX-L*`) including grouped cookie round-trip (`MX-L4`)
- ✅ Auth primitive unit-gap coverage (`exp/nbf/iat/leeway`, roles/run auth actor helpers)
- ✅ Synced package docs/artifacts (`tracker.md`, matrix, lifecycle results, ExecPlan closeout notes)

---

### Error Schema Standardization (RQ API Migration)
**Completed**: 2026-01-12  
**Duration**: 2 days  
**Status**: ✅ **COMPLETE**  
**Owner**: Codex  
**Link**: [docs/work-packages/20260111_error_schema_standardization/](docs/work-packages/20260111_error_schema_standardization/)  
**Description**: Standardized rq-engine and rq/api responses with canonical keys and status-code-first errors, removing legacy aliases.

**Outcome**: Contract published, legacy keys removed, job polling updated for 404 not_found, tests/docs aligned.

**Deliverables**:
- ✅ observed-error-schema-usages report
- ✅ rq-response contract documentation
- ✅ canonical error payloads with 4xx/5xx semantics
- ✅ jobstatus/jobinfo 404 polling updates
- ✅ updated tests and documentation

---

### VS Code Theme Integration
**Completed**: 2025-10-29  
**Duration**: 2 days  
**Status**: ✅ **COMPLETE**  
**Owner**: GitHub Copilot + gpt-5-codex (Codex)  
**Link**: [docs/work-packages/20251027_vscode_theme_integration/](docs/work-packages/20251027_vscode_theme_integration/)  
**Description**: Implemented configurable VS Code theme integration to satisfy stakeholder demands for "more style" while preserving zero-aesthetic development philosophy.

**Outcome**: Configurable theme mapping system delivered with 11 production themes, WCAG AA compliance validation, and stakeholder self-service color editing capability. System unblocks frontend modernization by addressing visual customization concerns without developer burden.

**Deliverables**:
- ✅ Configurable `theme-mapping.json` with semantic variable mappings
- ✅ Dynamic converter script with validation and reset capabilities
- ✅ 11 production themes (Light/Dark defaults + 9 VS Code themes)
- ✅ WCAG AA compliance validation for all shipped themes
- ✅ User persistence (localStorage + cookie fallback)
- ✅ Theme switcher UI integrated into settings panel
- ✅ Documentation: theme system guide, stakeholder editing guide, troubleshooting
- ✅ Build pipeline integration with automatic theme generation

---

### UI Style Guide Refresh
**Completed**: 2025-10-27  
**Duration**: 2 days  
**Status**: ✅ **COMPLETE**  
**Link**: [docs/work-packages/20251027_ui_style_guide_refresh/](docs/work-packages/20251027_ui_style_guide_refresh/)  
**Description**: Merged UI documentation into single agent-training guide with pattern catalog for rapid control construction.

**Outcome**: Comprehensive pattern catalog delivered with 8 copy-paste templates enabling <5 minute control creation. GPT-5-Codex completed review and validated technical accuracy. Work package handoff completed successfully.

**Deliverables**:
- ✅ Merged `ui-style-guide.md` (1151 lines)
- ✅ Pattern Catalog (8 templates)
- ✅ Quick Reference Tables, Troubleshooting, Testing Checklist
- ✅ "Zero-Aesthetic" design philosophy integration
- ✅ GPT-5-Codex technical validation complete

---

### Smoke Tests & Profile Harness
**Completed**: 2025-10-27  
**Duration**: Initial implementation phase complete  
**Status**: ✅ **SCOPE COMPLETE**  
**Link**: [docs/work-packages/20251023_smoke_tests/](docs/work-packages/20251023_smoke_tests/)  
**Description**: Established Playwright-based smoke harness with YAML profile support for health snapshots.

**Outcome**: Core infrastructure complete and functional. Test-support blueprint operational, smoke harness spec documented, initial profile authored. Scope achieved for immediate needs.

**Deliverables**:
- ✅ Playwright smoke harness setup
- ✅ YAML profile structure defined
- ✅ Test-support blueprint with `SMOKE_RUN_ROOT` support
- ✅ Initial quick profile drafted

**Note**: Future expansion (additional profiles, `wctl run-smoke` loader) can be addressed in separate work packages as needed.

---

### Frontend Integration & Smoke Automation
**Completed**: 2025-10-27  
**Duration**: ~4 weeks  
**Status**: ✅ **SCOPE COMPLETE**  
**Link**: [docs/work-packages/20251023_frontend_integration/](docs/work-packages/20251023_frontend_integration/)  
**Description**: Completed Pure template migrations, refactored bootstrap initialization, established repeatable smoke validation flow.

**Outcome**: All primary objectives achieved. Controllers migrated to Pure templates with StatusStream, bootstrap refactored to helper-driven patterns, URL construction standardized, 7 remaining polish issues fully documented for future refinement.

**Deliverables**:
- ✅ All controllers migrated to Pure templates with StatusStream
- ✅ Bootstrap refactored to helper-driven initialization
- ✅ Map race condition and preflight script issues resolved
- ✅ URL construction pattern (`url_for_run()`) fixed and documented
- ✅ Seven outstanding polish issues analyzed with implementation specs

**Note**: Seven polish items (legend styling, table standardization, TOC indicators, map layer wiring, inline help icons, hint deduplication) documented as future enhancements but not blocking production use.

---

### NoDb ACID Transaction Update
**Completed**: 2025-10-25  
**Duration**: 1 day (planning only)  
**Status**: ❌ **CANCELED - Unviable**  
**Link**: [docs/work-packages/20251024_nodb_acid_update/](docs/work-packages/20251024_nodb_acid_update/)  
**Description**: Proposed Redis-backed ACID transactions for NoDb controllers with intelligent event-driven cache invalidation.

**Outcome**: After architectural review, the proposed specification was deemed unviable. The approach introduced excessive complexity without sufficient benefit. NoDb's existing file-based state management with Redis locking remains the architectural pattern.

**Lessons Learned**:
- Redis transactions don't provide the durability guarantees needed for NoDb's file-first architecture
- Cache invalidation rules added complexity without addressing core concurrency patterns
- File-based state with explicit locking is simpler and more maintainable
- Future caching improvements should focus on read-through patterns, not transaction wrappers

---

### StatusStream Telemetry Cleanup
**Completed**: 2025-10-23  
**Duration**: 1 day  
**Link**: [docs/work-packages/20251023_statusstream_cleanup/](docs/work-packages/20251023_statusstream_cleanup/)  
**Description**: Replaced legacy WSClient shim with unified controlBase.attach_status_stream helper.

**Outcome**: Unified telemetry pipeline with no WSClient references; all controllers use StatusStream.

---

### Controller Modernization Documentation Backlog
**Completed**: 2025-10-23 
**Duration**: 1 week  
**Link**: [docs/work-packages/20251023_controller_modernization/](docs/work-packages/20251023_controller_modernization/)  
**Description**: Consolidated controller modernization documentation after WSClient removal and helper-first migration.

**Outcome**: Authoritative helper-first documentation established; archived per-controller plans grouped within work package.

---

## 🔮 Vision / Long-Term Initiatives

High-level initiatives that haven't been broken down into concrete work packages yet. These represent strategic directions or large efforts requiring planning.

### [Vision Item Template]
**Proposed**: YYYY-MM-DD  
**Sponsor**: [Team or person championing this]  
**Strategic Value**: [Why this matters long-term]  
**Dependencies**: [What needs to happen first]  
**Next Steps**: [What scoping work is needed before creating packages]

### Kubernetes Migration
**Proposed**: 2024-Q3  
**Sponsor**: DevOps  
**Strategic Value**: Enable horizontal scaling, improve deployment automation, support multi-tenant scenarios  
**Dependencies**: Static build process finalization, Redis keyspace configuration  
**Next Steps**: Create scoping package to enumerate migration steps, identify risks, and break into implementable chunks

---

### WEPP Model Validation Framework
**Proposed**: 2025-Q2  
**Sponsor**: Research team  
**Strategic Value**: Systematic validation against field data, improved model confidence, publication-ready metrics  
**Dependencies**: Standardized output formats, validation dataset curation  
**Next Steps**: Gather requirements from hydrologists, survey existing validation approaches, prototype validation metrics

---

## 📊 Metrics

### Cycle Time
Track how long packages take from start to completion:
- **Target**: 2-4 weeks for most packages
- **Current average**: [Calculate from recent completions]

### Work in Progress
- **Current**: 3 packages
- **Target**: 2-4 packages
- **Status**: ✅ **Within target**

### Throughput
Packages completed per month:
- **October 2025**: 7 packages completed/closed (6 completed successfully, 1 canceled as unviable); 1 package advanced to Phase 3 complete (markdown-doc toolkit); 3 packages started (UI Style Guide Refresh, VS Code Theme Integration, markdown-doc toolkit)

### Lead Time
Time from package creation to completion:
- Track in package tracker.md timeline sections

---

## 📝 Notes

### When to Update This Tracker

**Agents should update this tracker when**:
- Starting a new work package (add to Backlog or In Progress)
- Moving a package between columns (Backlog → In Progress → Done)
- Significant progress on an active package (update "Recent Progress")
- Blocking issues that affect package status
- Package completion (move to Done, add outcome summary)

**Frequency**: Check and update during each work session that touches work packages.

### Archive Policy

Completed packages are moved from "Done" to "History" section immediately upon completion. This keeps the tracker focused on active work while preserving completion history for reference.

### Questions or Issues

If this tracker format isn't working or you have suggestions:
1. Create a work package for "PROJECT_TRACKER improvements"
2. Document specific pain points and proposed solutions
3. Experiment with changes and gather feedback

---

## 📚 History

### October 2025
- ✅ VS Code Theme Integration (completed 2025-10-29) - Configurable mapping system with 11 production themes, WCAG AA compliance
- ✅ UI Style Guide Refresh (completed 2025-10-27) - Pattern catalog with 8 templates enabling <5min control creation
- ✅ Smoke Tests & Profile Harness (completed 2025-10-27) - Playwright harness setup with YAML profile support
- ✅ Frontend Integration & Smoke Automation (completed 2025-10-27) - Pure migration complete, 7 polish items documented
- ✅ StatusStream Telemetry Cleanup (completed 2025-10-23) - Unified telemetry pipeline, WSClient removed
- ❌ NoDb ACID Transaction Update (canceled 2025-10-25) - Unviable architecture, file-first approach retained
- ✅ Controller Modernization Documentation Backlog (completed 2025-10-23) - Helper-first docs established

### February 2026
- ✅ NED1 VRT Alignment Audit + Correction (completed 2026-02-05) - Audit script + corrected VRT + USGS report delivered

### [Month YYYY]
- [Package name] (completed YYYY-MM-DD) - [One line outcome]

---

## 🔧 Tracker Maintenance

**Last reviewed**: 2026-04-10  
**Next review**: 2026-05-10 (monthly)

**Review checklist**:
- [ ] Move stale Done items to History
- [x] Update WIP count and check against limits
- [x] Review In Progress packages for stalls (>6 weeks)
- [x] Verify Backlog priorities still align with current goals
- [x] Reconcile stale lifecycle state transitions in tracker columns
- [ ] Update metrics section with recent data
