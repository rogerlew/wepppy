# PROJECT_TRACKER.md
> Kanban board for wepppy work packages and vision items

**Last Updated**: 2026-02-22  
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

**Current WIP**: 2 packages ✅ **Within target**

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

### NoDir Archives for High-Fanout Project Trees
**Proposed**: 2026-02-14  
**Size**: Large (2-4 weeks)  
**Priority**: High  
**Status**: Discovery / Scoping  
**Package**: [docs/work-packages/20260214_nodir_archives/](docs/work-packages/20260214_nodir_archives/)  
**Description**: Reduce inode and metadata `stat()` pressure on NAS-backed NFS by archiving `landuse/`, `soils/`, `climate/`, and `watershed/` as `.nodir` (zip container) while preserving directory-like semantics in browse and internal code.

**Scope**:
- Define the NoDir contract (`docs/schemas/nodir-contract-spec.md`) and enforce deterministic precedence rules (`<root>/` vs `<root>.nodir`).
- Teach browse + files/download endpoints to “enter” archive-backed trees without extracting.
- Provide a crawler/migrator to archive existing run trees under `/wc1/runs`.

**Strategic Value**:
- Removes the inode ceiling as a scaling constraint for larger watersheds (10k+ hillslopes).
- Reduces browse latency driven by metadata round-trips on small-file trees.

**Dependencies**:
- Agreement on NoDir contract details (naming, URL semantics, security invariants).

**Next Steps**:
1. Freeze archive boundary semantics for browse/files/download (`.../watershed.nodir/...`).
2. Inventory all call sites that assume real directories for the targeted roots.

---

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

**Current WIP Count**: 2 packages ✅

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

## ✅ Done

Recently completed work packages. Archived immediately upon completion.

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

**Last reviewed**: 2025-10-26  
**Next review**: 2025-11-26 (monthly)

**Review checklist**:
- [ ] Move stale Done items to History
- [ ] Update WIP count and check against limits
- [ ] Review In Progress packages for stalls (>6 weeks)
- [ ] Verify Backlog priorities still align with current goals
- [ ] Check Vision items for readiness to become packages
- [ ] Update metrics section with recent data
