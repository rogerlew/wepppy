# PROJECT_TRACKER.md
> Kanban board for wepppy work packages and vision items

**Last Updated**: 2026-03-09  
**Active Packages**: 3  
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

**Current WIP**: 3 packages ✅ **Within target**

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

### RQ-Engine Agent Usability and Documentation Hardening
**Proposed**: 2026-02-08  
**Size**: Medium (1-2 weeks)  
**Priority**: High  
**Status**: Scoped - Ready to Start  
**Package**: [docs/work-packages/20260208_rq_engine_agent_usability/](docs/work-packages/20260208_rq_engine_agent_usability/)  
**Description**: Establish rq-engine as the canonical agent API for Bootstrap and queue workflows, harden OpenAPI route metadata, and align docs/tests across developer and user audiences.

**Scope**:
- Converge agent-facing Bootstrap endpoints into `/rq-engine/api/*` ownership.
- Standardize OpenAPI metadata (`summary`, `description`, `operation_id`, schemas, examples, auth notes).
- Align token/scope documentation with enforced behavior (`bootstrap:enable`, `bootstrap:token:mint`, `bootstrap:read`, `bootstrap:checkout`).
- Expand regression coverage for auth failures, async enable lifecycle, lock contention, and canonical errors.

**Strategic Value**:
- Gives agents one discoverable API surface and reduces Flask/rq-engine contract drift.
- Improves automation reliability through explicit route contracts and examples.
- Makes Bootstrap workflows auditable, reproducible, and supportable for both users and tooling.

**Dependencies**:
- Existing rq response contract (`docs/schemas/rq-response-contract.md`)
- Bootstrap Phase 2 endpoint baseline in rq-engine
- Current token policy docs (`docs/dev-notes/auth-token.spec.md`)

**Next Steps**:
1. Freeze endpoint inventory and classify `agent-facing` vs `internal` routes.
2. Apply OpenAPI metadata pass on agent-critical modules.
3. Close test and docs drift gaps with targeted suites and artifacts.

---

### Wojak Lives: Interactive Agent Integration
**Proposed**: 2025-10-28  
**Approved**: 2025-10-28  
**Owner**: Codex  
**Size**: Medium (2-3 days, 14-20h)  
**Priority**: High  
**Status**: **Approved — Implementation Ready**  
**Package**: [docs/work-packages/20251028_wojak_lives/](docs/work-packages/20251028_wojak_lives/)  
**Description**: Establish minimal viable path for Wojak agent (zero-trust public-facing tier) integration with WEPPcloud command bar.

**Scope**:
- JWT authentication scoped to user + run context
- MCP modules for file access (`report_files`) and markdown editing (`report_editor`) using PyO3 bindings
- Flask route to spawn CAO sessions with JWT injection
- Command bar UI integration with WebSocket bridge for bi-directional chat
- Security validation (path traversal prevention, JWT verification)
- Manual smoke testing with root user (Roger)

**Strategic Value**:
- Enables interactive agent assistance for WEPP run exploration
- Demonstrates CAO integration with WEPPcloud UI
- Establishes security patterns for future agent tiers
- Leverages PyO3 markdown bindings for 50× performance improvement over subprocess calls

**Dependencies**: 
- CAO server running on localhost:9889
- PyO3 bindings installed in CAO venv (markdown_extract_py, markdown_edit_py, markdown_doc_py)
- Flask-JWT-Extended library
- Sample run directory with markdown reports for testing

**Codex Review Gate**: Pause after Phase 1 (Backend Foundation) if effort exceeds 12 hours for architecture validation before frontend work.

---

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

**Current WIP Count**: 3 packages ✅

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

### SBS Map Refactor (Rust Acceleration)
**Started**: 2026-01-24  
**Status**: Discovery/Benchmarking  
**Size**: Medium (multi-phase refactor)  
**Owner**: Codex  
**Link**: [docs/work-packages/20260124_sbs_map_refactor/](docs/work-packages/20260124_sbs_map_refactor/)  
**Description**: Replace slow Python raster scanning and per-pixel loops in `sbs_map.py` with Rust + GDAL implementations. Adds large-fixture regression tests and benchmarks on real SBS maps.

**Current Status**:
- Baseline large fixtures captured with expectations and gated regression tests.
- Benchmarks recorded for two SBS maps; Python path is minutes long for multiple methods.
- Rust summary + reclassification modules scoped but not implemented yet.

**Next Steps**:
1. Implement `wepppyo3.sbs_map.summarize_sbs_raster`.
2. Wire `sbs_map_sanity_check` to Rust summary (keep Python fallback).
3. Implement Rust reclassification + export helpers and update tests.

---

### AI Authority Doctrine + Operating Practices
**Started**: 2026-03-09  
**Status**: Draft 2 operationalization complete - review and closeout pending  
**Size**: High-leverage governance package (1-2 weeks iterative drafting)  
**Owner**: Codex  
**Link**: [docs/work-packages/20260309_ai_authority_doctrine/](docs/work-packages/20260309_ai_authority_doctrine/)  
**Description**: Establish a living doctrine for delegating authority to AI agents based on demonstrated competence, plus a separate operating standard for grants, evidence, oversight, revocation, and compliance-aware escalation.

**Current Status**:
- Draft 1 working drafts exist in `AI_AUTHORITY_DOCTRINE.md` and `AI_AUTHORITY_OPERATING_PRACTICES.md`.
- Doctrine and SOP now include a Draft 1 compliance crosswalk to the EU AI Act and NIST materials.
- Doctrine and SOP now include the first Draft 2 task-class execution matrix with evidence thresholds and escalation modes.
- Doctrine and SOP now define minimum-sufficient evidence and succession breadcrumb rules for low-friction governance.
- Doctrine and SOP now resolve record location as a hybrid model: durable governance meaning in repo-visible artifacts, execution detail in orchestration metadata.
- SOP now includes lightweight templates for authority grants, competence reviews, and revocation or tripwire events, designed for issue-first use on smaller work and package artifacts on broader work.
- First serial review findings have been patched: `T4` now has explicit break-glass handling, qualifying-gate criteria, safer production-investigation defaults, and stronger `T4` template fields.
- Second serial review found no remaining material contradiction and led only to a small template polish: an explicit rollback-or-containment field in the authority-grant template.
- Doctrine and SOP now name stable `governance_control_agent` and `ops_security_control_agent` roles, and the repo now includes matching `.codex` and CAO bindings without hardcoding model identities into governance docs.
- Doctrine now explicitly limits its claims to governable systems and distinguishes runaway from possible AI self-succession as a future continuity state rather than a present operating assumption.
- Package docs and active prompts now treat the package as Draft 2 complete and ready for closeout if accepted.

**Next Steps**:
1. Close the package if the patched doctrine set is accepted as operationally sufficient.
2. If runtime enforcement or policy tooling is desired, open a follow-on implementation package.

---

## ✅ Done

Recently completed work packages. Archived immediately upon completion.

### TerrainProcessor Runtime + Visualization Artifact Implementation
**Completed**: 2026-03-06  
**Duration**: 1 day initial + follow-up closeout  
**Status**: ✅ **COMPLETE**  
**Owner**: Codex  
**Link**: [docs/work-packages/20260305_terrain_processor_implementation/](docs/work-packages/20260305_terrain_processor_implementation/)  
**Description**: Completed full TerrainProcessor runtime + visualization backend delivery and follow-up Tasks 1-6 (BLC fidelity, real WBT integration tests, visualization guardrails/UI payloads, watershed API surface, and docs closeout).

**Outcome**:
- Runtime now supports breach-least-cost controls end-to-end (`blc_dist_m`, `blc_max_cost`, `blc_fill`).
- Added real WBT integration tests (`tests/topo/test_terrain_processor_wbt_integration.py`).
- Added visualization benchmark and UI payload artifacts (`visualization_benchmarks.json`, `visualization_ui_payload.json`) plus `visualization_max_pixels` guardrail.
- Added watershed terrain endpoints for config/run/result/manifest/resource access.
- Follow-up validation completed (`tests/topo --maxfail=1`, `tests/weppcloud --maxfail=1`, broad-exception gate pass, docs lint pass) and prompts archived to `prompts/completed/`.

### TerrainProcessor Pre-Implementation Foundations
**Completed**: 2026-03-05  
**Duration**: 1 day  
**Status**: ✅ **COMPLETE**  
**Owner**: Codex  
**Link**: [docs/work-packages/20260305_terrain_processor_preimplementation/](docs/work-packages/20260305_terrain_processor_preimplementation/)  
**Description**: Completed phased helper-first TerrainProcessor foundations with phase-scoped tests, review artifacts, concept synchronization, and package closeout.

**Outcome**:
- Added reusable helper module `wepppy/topo/wbt/terrain_processor_helpers.py` for phases 1-5 (flow-stack facade, bounded-breach helpers, culvert prep/burn adapter, multi-outlet parsing, provenance/invalidation scaffolding).
- Added targeted regression suite `tests/topo/test_terrain_processor_helpers.py` with 34 helper tests and review-driven edge-case/failure-contract coverage.
- Updated `wepppy/topo/wbt/terrain_processor.concept.md` with shipped-helper status and contract notes.
- Published phase review artifacts and final validation summary under `docs/work-packages/20260305_terrain_processor_preimplementation/artifacts/`.
- Archived prompts to `prompts/completed/` and closed package/tracker docs.

### OSM Roads Client with Persistent Server-Side Cache
**Completed**: 2026-03-05  
**Duration**: 1 day  
**Status**: ✅ **COMPLETE**  
**Owner**: Codex  
**Link**: [docs/work-packages/20260304_osm_roads_client_cache/](docs/work-packages/20260304_osm_roads_client_cache/)  
**Description**: Implemented a production-ready WEPPpy OSM roads client module with deterministic keying, hybrid persistent caching, lock-safe refresh, and TerrainProcessor-style consumer seam.

**Outcome**:
- Added `wepppy/topo/osm_roads/` module surface (`contracts`, `errors`, `cache`, `overpass`, `service`, runtime README).
- Implemented hybrid cache contract support (PostgreSQL metadata/advisory-lock backend + file payload storage) with bounded stale/expired fallback behavior.
- Added consumer seam `wepppy/topo/wbt/osm_roads_consumer.py::resolve_roads_source`.
- Added topo regression suites for contracts/cache/service concurrency, fallback policy, cleanup, and clip/reproject behavior.
- Executed required validation gates including `wctl run-pytest tests --maxfail=1` (pass), broad-exception enforcement (pass), and required doc-lint checks (pass).

### Browse Parquet Quick-Look Filter Builder
**Completed**: 2026-03-04  
**Duration**: 1 day  
**Status**: ✅ **COMPLETE** (functional milestones complete; broad-exception enforcement drift recorded for separate follow-up scope)  
**Owner**: Codex  
**Link**: [docs/work-packages/20260304_browse_parquet_quicklook_filters/](docs/work-packages/20260304_browse_parquet_quicklook_filters/)  
**Description**: Added bounded, shared parquet filter contract and integrated it across browse HTML preview, filtered parquet download, filtered CSV export, and D-Tale launch with a browse-side filter builder UI.

**Outcome**: Requester semantics are implemented and covered by regression tests:
- `download` returns filtered parquet when filter state is active.
- `Contains` is case-insensitive.
- `GreaterThan`/`LessThan` are numeric-only and exclude missing/`NaN` rows.
- UI operator uses select controls with nested group/condition builder and parquet-link `pqf` propagation.

**Deliverables**:
- ✅ Shared filter module: `wepppy/microservices/parquet_filters.py`
- ✅ Browse integrations: `flow.py`, `listing.py`, `_download.py`, `dtale.py`, `browse.py`
- ✅ D-Tale loader integration: `wepppy/webservices/dtale/dtale.py`
- ✅ UI integration: browse templates + `wepppy/weppcloud/static/js/parquet_filter_builder.js`
- ✅ Regression tests: `test_parquet_filters.py`, plus updates to `test_browse_routes.py`, `test_download.py`, `test_browse_dtale.py`
- ✅ Docs updates: browse README + `docs/schemas/weppcloud-browse-parquet-filter-contract.md`
- ✅ Validation artifact: `docs/work-packages/20260304_browse_parquet_quicklook_filters/artifacts/20260304_e2e_validation_results.md`

### Raster Tools Cross-Walk and Benchmark Evaluation
**Completed**: 2026-03-04
**Duration**: 1 day (evaluation closeout)
**Status**: ✅ **COMPLETE** (`defer`; BW-01/BW-02 executed but non-comparable under strict parity contract)
**Owner**: Codex
**Link**: [docs/work-packages/20260303_raster_tools_crosswalk_benchmarks/](docs/work-packages/20260303_raster_tools_crosswalk_benchmarks/)
**Description**: Evaluated whether `/workdir/raster_tools` should be incorporated into WEPPpy using capability cross-walk + benchmark evidence.

**Outcome**: Produced end-to-end evaluation artifacts and a `defer` recommendation. Deferred benchmark cases (`BW-03`/`BW-04`/`BW-05`) are explicitly routed to a follow-up package, and external PDF claim language is documented in a source-grounded claims-vs-code addendum.

**Deliverables**:
- ✅ Capability inventory + WEPPpy usage map
- ✅ Cross-walk matrix + overlap-only shortlist traceability
- ✅ Benchmark harness + raw run logs with strict comparability guards
- ✅ Results + recommendation memo + synchronized package tracker/ExecPlan docs
- ✅ Claims-vs-code addendum with USDA PDF source link and evidence boundaries

### NoDir Full Reversal (Abandonment Program)
**Completed**: 2026-02-27
**Duration**: 1 day (multi-phase closeout day)
**Status**: ✅ **COMPLETE**
**Owner**: Codex
**Link**: [docs/work-packages/20260227_nodir_full_reversal/](docs/work-packages/20260227_nodir_full_reversal/)
**Description**: Abandoned NoDir runtime/test/contract surfaces and returned active WEPPpy/WEPPcloud behavior to directory-only semantics with full closeout evidence.

**Outcome**: Phase 6 closeout completed with full validation gates, final rollback verification mapping all package success criteria, and mandatory subagent high/medium findings closure to zero unresolved.

**Deliverables**:
- ✅ Phase 6 closeout artifacts published (`phase6_closeout_scope.md`, `phase6_nodir_import_scan.txt`, `phase6_structural_assertions.md`, `phase6_validation_log.md`, `phase6_final_rollback_verification.md`, `phase6_subagent_review.md`, `phase6_findings_resolution.md`)
- ✅ Required gates: `wctl run-pytest tests --maxfail=1` PASS (`2069 passed, 29 skipped`), `check_broad_exceptions` PASS, `code_quality_observability` observe-only PASS, `wctl check-rq-graph` PASS, required `wctl doc-lint` paths PASS
- ✅ Package/tracker/project surfaces synchronized to completed state

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
- **Current**: 2 packages
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

**Last reviewed**: 2025-10-26  
**Next review**: 2025-11-26 (monthly)

**Review checklist**:
- [ ] Move stale Done items to History
- [ ] Update WIP count and check against limits
- [ ] Review In Progress packages for stalls (>6 weeks)
- [ ] Verify Backlog priorities still align with current goals
- [ ] Check Vision items for readiness to become packages
- [ ] Update metrics section with recent data
