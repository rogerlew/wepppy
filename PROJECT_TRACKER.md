# PROJECT_TRACKER.md
> Kanban board for wepppy work packages and vision items

**Last Updated**: 2026-07-09
**Active Packages**: 12
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

**Current WIP**: 12 packages (above target range)

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

### SSURGO Reclaimed Soil Conversion and Fallback Transparency
**Proposed**: 2026-06-22
**Size**: Medium-High (2-4 focused sessions)
**Priority**: High
**Link**: [docs/work-packages/20260622_ssurgo_reclaimed_soil_fallback/](docs/work-packages/20260622_ssurgo_reclaimed_soil_fallback/)
**Description**: Fix reclaimed mined-land SSURGO profiles that collapse to zero WEPP layers when the first horizon is below the restrictive-layer threshold, and make invalid-dominant-MUKEY fallback preserve/report the raw raster-selected MUKEY instead of silently substituting a common valid soil.

**Scope**:
- Fix SSURGO-to-WEPP conversion so Fairpoint reclaimed MUKEYs `3294459`, `3294460`, and `3294461` build valid WEPP soil files.
- Add unit and integrated generated-output tests for those three MUKEYs.
- Preserve raw dominant MUKEYs and record substitution details when fallback still occurs.
- Keep NoDb and `soils.parquet` evolution additive/backward-compatible.
- Add a parameterization ADR and update durable SSURGO docs.
- Complete QA review with finding disposition before closure.

**Strategic Value**:
- Restores current SSURGO/gNATSGO behavior for reclaimed mined lands.
- Prevents old-looking substituted soils from hiding valid current Fairpoint map units.
- Gives operators and users provenance when WEPPcloud must substitute invalid soil data.

**Dependencies**: Builds on completed project-local SSURGO cache work in `20260619_ssurgo_project_sqlite_cache`.

**Next Steps**: Draft ADR-0008, add failing Fairpoint fixture tests, then implement the restrictive-layer fix and fallback provenance.

---

### SSURGO Project SQLite Cache
**Proposed**: 2026-06-19
**Size**: Medium (2-4 focused sessions)
**Priority**: High
**Link**: [docs/work-packages/20260619_ssurgo_project_sqlite_cache/](docs/work-packages/20260619_ssurgo_project_sqlite_cache/)
**Description**: Move SSURGO tabular cache persistence from shared module-level SQLite files to project-local SQLite databases created under `<wd>/soils/` during `build_soils`, with an Advanced Options checkbox to clear the run-scoped cache before rebuild.

**Scope**:
- Make `wepppy/soils/ssurgo/ssurgo.py` use in-memory SQLite by default unless a caller supplies an explicit cache path.
- Serialize cache behavior options and `clear_ssurgo_cache_on_rebuild` through `wepppy/nodb/core/soils.py`, while deriving absolute cache paths from the active run's `soils` directory.
- Wire the pure UI checkbox, build-soils route parsing, worker-visible NoDb state, and cache-clear behavior.
- Add targeted backend, RQ route, template, and controller regression tests.
- Update stale durable SSURGO cache documentation.
- Use fixed project cache files `ssurgo_tabular_cache.sqlite` and `statsgo_tabular_cache.sqlite`, and cover all current `Soils` constructor sites plus direct non-`Soils` callers.
- Complete dual subagent review with finding disposition before closure.

**Strategic Value**:
- Avoids stale shared SSURGO cache rows while preserving per-project rebuild efficiency.
- Makes cache clearing an explicit operator/user action scoped to the current run.
- Keeps old projects backward compatible by creating the cache when soils are rebuilt.

**Dependencies**: Work-package, tracker, active ExecPlan, and review disposition template are authored; implementation is pending.

**Next Steps**: Implement the cache path abstraction in `ssurgo.py`, then wire `Soils` serialization, RQ route parsing, UI control, and regression coverage.

---

### Run Statistics Ledger
**Proposed**: 2026-05-05
**Size**: Medium-High (2-4 focused sessions)
**Priority**: High
**Link**: [docs/work-packages/20260505_run_statistics_ledger/](docs/work-packages/20260505_run_statistics_ledger/)
**Description**: Replace WEPPcloud usage counters derived from active run-directory file counts with a durable PostgreSQL statistics ledger for project counts by config, repeated WEPP hillslope run counts, and WATAR ash run counts.

**Scope**:
- Add a PostgreSQL statistics event ledger so historical execution counts survive 90-day TTL deletion and concurrent writers are transaction-safe.
- Keep PostgreSQL as the source-of-truth ledger; Redis may be used only as an optional summary cache/materialization layer.
- Count repeated WEPP hillslope and WATAR ash executions from runtime events rather than `.slp` or `*ash.csv` file counts.
- Backfill project metadata from dot access logs and legacy artifact minimum counts without inventing unknown pre-ledger reruns.
- Preserve existing `/stats`, `/stats/<key>`, `/access-by-year`, and `/access-by-month` response shapes while richer summary artifacts are introduced.

**Strategic Value**:
- Prevents public/operator statistics from mixing active project inventory with historical execution counts.
- Makes WATAR reporting defensible by counting completed ash tasks, not legacy artifacts.
- Creates a documented source-quality model for runtime-observed, artifact-inferred, and unknown historical data.

**Dependencies**: Initial spec and active ExecPlan are created; implementation is pending.

**Next Steps**: Implement the ledger module and focused writer/backfill tests before wiring WEPP, WATAR, and TTL runtime hooks.

---

### totalwatsed3 Storage and Optional Terms Contract Hardening
**Proposed**: 2026-04-29
**Size**: Medium-High (2-4 focused sessions)
**Priority**: High
**Link**: [docs/work-packages/20260429_totalwatsed3_storage_optional_terms/](docs/work-packages/20260429_totalwatsed3_storage_optional_terms/)
**Description**: Define and implement additive optional storage/capacity and runoff-partition terms across WEPP-forest outputs and WEPPpy interchange/`totalwatsed3` so water-balance closure interpretation is explicit and backward-compatible.

**Scope**:
- Finalize optional-term contract (names, units, formulas, null semantics) in `totalwatsed` spec/docs.
- Harden WEPPpy hillslope parsers for legacy + enriched output layouts.
- Wire optional terms into `totalwatsed3` and closure-audit tooling with regression coverage.
- Regenerate and re-audit `uncapped-spectacular` artifact after rollout.

**Strategic Value**:
- Reduces repeated analyst/operator confusion around storage semantics (`TSW` vs `Total-Soil Water`).
- Preserves legacy compatibility while enabling richer closure diagnostics.
- Creates a durable, documented cross-repo contract for future WEPP output evolution.

**Dependencies**: Production validation was completed on wepp1 because the run directory is not mounted in the local workspace.

**Next Steps**: Create a follow-up investigation package if the large H2637/H2809 closure residuals need root-cause analysis beyond this schema/contract work.

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

**Current WIP Count**: 12 packages

---

### SSURGO FC/WP Sanitization
**Started**: 2026-07-05
**Status**: Sanitizer deployed and invalidation complete; invalid-soil logging follow-up complete locally
**Size**: Medium (single focused session)
**Owner**: Codex
**Priority**: High
**Link**: [docs/work-packages/20260705_ssurgo_fc_wp_sanitization/](docs/work-packages/20260705_ssurgo_fc_wp_sanitization/)
**Description**: Sanitize SSURGO-generated field-capacity and wilting-point values after NASA ROSES batch runs produced WEPP soil files containing `-9.9 nan`, enforce the same guard in `WeppSoilUtil`, document timestamp-based invalidation for affected production runids, and harden invalid-soil diagnostic logging for failed-worker mukeys.

**Current Focus**: Deploy the invalid-soil logging follow-up to wepp1, then rerun the NASA ROSES batch.

**Next Steps**: Deploy the logging follow-up, rerun the NASA ROSES batch, and verify affected runids rebuild soils before WEPP hillslopes.

---

### Batch Runner Durability
**Started**: 2026-06-30
**Status**: Implementation updated locally; production rollout pending
**Size**: Medium-High (2-4 focused sessions)
**Owner**: Codex
**Priority**: High
**Link**: [docs/work-packages/20260630_batch_runner_durability/](docs/work-packages/20260630_batch_runner_durability/)
**Description**: Make Run Batch restart-aware so a partially failed batch can be retried after operator correction without enqueueing every completed watershed leaf again, including leaves whose cloned climate config drifted from the corrected base project.

**Current Focus**: Local implementation, dual-agent review disposition, focused tests, RQ graph regeneration, docs, security review, and climate base-attribute resync hardening are complete. Remaining work is production preflight/rollout after active target-batch jobs finish or are explicitly canceled.

**Dependencies**: Production evidence captured from `wepp1`; implementation should not be rolled out while the target batch still has active queued/started jobs.

**Next Steps**: Run production preflight and deploy when requested; existing broad-exception boundary debt remains recorded as residual cleanup work.

---

### Dedicated Download Service for Critical Run Artifacts
**Started**: 2026-06-19
**Status**: Implementation complete locally; production rollout pending
**Size**: Medium-High (2-4 focused sessions)
**Owner**: Codex
**Priority**: High
**Link**: [docs/work-packages/20260619_dedicated_download_service/](docs/work-packages/20260619_dedicated_download_service/)
**Description**: Split critical completed-run archive downloads out of `browse` into a dedicated, range/resume-friendly, observable download service with independent process controls and Caddy routing.

**Current Focus**: Local service, tests, Docker/Caddy wiring, local full/range/resume smoke, QA review, and security review are complete with local findings dispositioned. Remaining work is wepp1 cutover plus production smoke/log evidence.

**Dependencies**: Builds on the June 2026 browse/D-Tale memory remediation work and the wepp1 browse/download slowdown incident record.

**Next Steps**: Start/restart the download service and Caddy on wepp1, smoke test a representative archive, and observe `download.complete` logs through the 14-day window.

---

### D-Tale Lazy Parquet Backend
**Started**: 2026-06-16
**Status**: Implementation complete locally; production observation pending
**Size**: Medium-High (1-3 focused sessions)
**Owner**: Codex
**Priority**: High
**Link**: [docs/work-packages/20260616_dtale_lazy_parquet_backend/](docs/work-packages/20260616_dtale_lazy_parquet_backend/)
**Description**: Patch the embedded D-Tale integration so Parquet launches use lazy, bounded row/column reads instead of eager full-table Arrow-to-pandas conversion.

**Current Focus**: Local implementation and validation are complete. Production rollout/observation is the remaining operational step if this is promoted.

**Dependencies**: Builds on the browse Arrow-to-pandas elimination package and the June 16 browse/D-Tale memory incident investigation.

**Next Steps**: Deploy and observe D-Tale worker RSS on production if requested; consider a follow-up for bounded lazy chart/export adapters.

---

### Browse Arrow-to-Pandas Elimination
**Started**: 2026-06-16
**Status**: Implementation complete locally; broad validation/security/RSS evidence in progress
**Size**: Medium-High (1-2 weeks)
**Owner**: Codex
**Priority**: High
**Link**: [docs/work-packages/20260616_browse_arrow_pandas_elimination/](docs/work-packages/20260616_browse_arrow_pandas_elimination/)
**Description**: Remove Arrow-to-pandas conversion from the `browse` service request paths so parquet preview/export/download behavior remains intact without long-lived Gunicorn workers retaining high RSS after large parquet operations.

**Scope**:
- Inventory and replace `table.to_pandas()` / `pd.read_parquet(...)` usage under `wepppy/microservices/browse`.
- Preserve route-level behavior for parquet preview, filtered preview, parquet download, filtered parquet download, CSV export, and D-Tale launch.
- Add worker RSS/request-duration observability and production-like validation evidence.
- Complete a dedicated security review because the package touches public browse/download route internals.

**Strategic Value**:
- Addresses a likely contributor to the June 16, 2026 `wepp1` browse high-RSS/download slowdown incident.
- Reduces reliance on targeted `browse` restarts as an operational mitigation.
- Creates safer foundations for future large-artifact browse/export workflows.

**Dependencies**: Existing browse parquet filter contract and route tests from `20260304_browse_parquet_quicklook_filters`; incident context in `docs/infrastructure/incident-2026-06-16-wepp1-browse-download-slowdown.md`.

**Next Steps**: Complete broad validation gates, security review sign-off, and production-like worker RSS evidence.

---

### RUSLE C Surface-Rock Partition Implementation
**Started**: 2026-05-27  
**Status**: Package scaffolded; implementation planning and review-disposition kickoff in progress  
**Size**: Medium-High (2-3 focused sessions)  
**Owner**: Codex  
**Link**: [docs/work-packages/20260527_rusle_c_surface_rock_partition/](docs/work-packages/20260527_rusle_c_surface_rock_partition/)  
**Description**: Implement `observed_rap` C-factor surface-rock partition (`rock_fraction_of_rap_bare`) across RUSLE UI, rq-engine payload contracts, and runtime C integration with explicit user verification guidance and manifest provenance.

**Current Status**:
- New work package, tracker, and active ExecPlan created under `docs/work-packages/20260527_rusle_c_surface_rock_partition/`.
- Scope is locked to `observed_rap` implementation across `rusle_pure.htm`, `controllers_js/rusle.js`, rq-engine route/schema defaults, and RUSLE C/controller paths.
- Parameterization governance is anchored to `docs/adrs/ADR-0003-rusle-observed-rap-surface-rock-partition.md`.
- Independent package/plan review findings were dispositioned; acceptance criteria now explicitly include boundary/error-path tests and `auto` fallback semantics.

**Next Steps**:
1. Implement runtime/UI/API wiring and focused regressions.
2. Run targeted Python/JS validation gates including schema-default route coverage.
3. Perform post-implementation independent review, then close package docs.

---

### Fork Copy Optimization for `wepp/runs` and `wepp/output`
**Started**: 2026-05-06  
**Status**: Package scaffolded; implementation in progress  
**Size**: Medium (1 focused session)  
**Owner**: Codex  
**Link**: [docs/work-packages/20260506_fork_skip_wepp_copy/](docs/work-packages/20260506_fork_skip_wepp_copy/)  
**Description**: Add a fork-console option to skip copying `wepp/runs` and `wepp/output` contents while still creating those directories in the target run, and ensure undisturbify keeps using the same copy optimization path.

**Current Status**:
- New work package, tracker, and active ExecPlan created under `docs/work-packages/20260506_fork_skip_wepp_copy/`.
- Implementation scope locked to fork UI, rq-engine route payload wiring, fork worker copy behavior, and focused regressions.

**Next Steps**:
1. Implement UI -> API -> worker flag wiring and rsync exclusion behavior.
2. Guarantee directory creation for skipped `wepp/runs` and `wepp/output` trees.
3. Run targeted tests and subagent review with disposition artifact.

---

### MOFE Flagged Hillslope Triage for Ablation Campaigns
**Started**: 2026-05-02  
**Status**: Package scaffolded and ExecPlan migrated; M1 pending implementation  
**Size**: Medium (2-4 focused sessions)  
**Owner**: Codex  
**Link**: [docs/work-packages/20260502_mofe_flagged_hillslope_triage/](docs/work-packages/20260502_mofe_flagged_hillslope_triage/)  
**Description**: Convert the MOFE flagged hillslope follow-up into a full work package, then execute deterministic D0-D5 triage, clustering cross-check, representative seed selection, and campaign matrix generation for ablation planning.

**Current Status**:
- Full package scaffold created with `package.md`, `tracker.md`, `prompts/active`, and `artifacts/`.
- Active ExecPlan now lives at `prompts/active/mofe_flagged_hillslope_triage_execplan.md`.
- Preconditions and autonomous-execution friction updates are documented; output home is package-local `artifacts/`.

**Next Steps**:
1. Implement `tools/build_mofe_triage_table.py` and generate `triage_table_runs.csv`, `triage_table_hillslopes.csv`, and `triage_table_hillslopes_all.csv`.
2. Execute M2-M6 outputs (taxonomy assignment, disagreement review, representative seeds, precedent crosswalk, campaign matrix).
3. Close out package docs and hand off ablation-incident recommendations.

---

### Hillslope MOFE Daily Closure Audit + Contract Definition
**Started**: 2026-04-30  
**Status**: Milestones 1-3 complete; full-physics closure rework implemented and validated in tool tests  
**Size**: Medium-High (2-4 focused sessions)  
**Owner**: Codex  
**Link**: [docs/work-packages/20260430_hillslope_mofe_daily_closure_audit/](docs/work-packages/20260430_hillslope_mofe_daily_closure_audit/)  
**Description**: Define a source-backed MOFE water-balance contract from `/workdir/wepp-forest` and implement a dedicated `hillslope_mofe_daily_closure_audit` tool with tests and run evidence, now explicitly reporting full-physics exported-term closure residuals plus implied unresolved terms.

**Current Status**:
- Contract milestone and required subagent gate are complete (`artifacts/20260430_contract_review_disposition.md`).
- Tool implementation now includes full-physics closure diagnostics (`RM + UpStrmQ + SubRIn` inputs; `QOFE + latqcc + Dp + ET + Tile + ΔStorage` outputs) and MOFE chain transfer checks.
- Regression test suite for the new tool passes (`tests/tools/test_hillslope_mofe_daily_closure_audit.py`).
- Remaining lifecycle work: evaluation artifact refresh and independent implementation-review disposition artifact.

**Next Steps**:
1. Re-run required closure-audit regression guard suites.
2. Refresh evaluation summary/artifacts under package `artifacts/`.
3. Complete and record implementation review disposition artifact.

---

### Watershed Centroid Persistence Hardening for Climate Build Reliability
**Started**: 2026-04-22  
**Status**: Implementation complete with targeted validation; global suite closure blocked by unrelated Geneva failure  
**Size**: Medium-High (2-5 focused sessions)  
**Owner**: Codex  
**Link**: [docs/work-packages/20260422_watershed_centroid_persistence_hardening/](docs/work-packages/20260422_watershed_centroid_persistence_hardening/)  
**Description**: Harden watershed centroid durability and climate-call-site contracts to prevent `build_climate_rq` failures when `watershed.nodb` persists with missing centroid state despite successful abstraction artifacts.

**Current Status**:
- Watershed centroid contract now supports repair-or-fail semantics with typed `WatershedCentroidStateError`.
- Climate/station centroid consumers now use `require_centroid()` instead of nullable unpack paths.
- NoDb stale-write rejection is active and covered by regression (`NoDbStaleWriteError`).
- `abstract_watershed_rq` now verifies persisted centroid durability, performs one bounded repair attempt, and fails typed if durability still fails.
- Targeted validation passed (`43 passed`) across nodb/rq/climate touched modules.
- Full-suite gate is currently blocked by unrelated existing failure in `tests/nodb/mods/geneva/test_geneva_wp09_end_to_end.py::test_wp09_watershed_warning_thresholds_propagate_to_results_query_report[...]` (`KeyError: 'severity'`).

**Next Steps**:
1. Fix unrelated Geneva worktree failure (`KeyError: 'severity'` in `test_geneva_wp09_end_to_end.py`).
2. Re-run `wctl run-pytest tests --maxfail=1` and close package after global gate clears.

---

### Jagged Hyperpigmentation Hillslope Ablation Queue (`H3507`, `H1271`)
**Started**: 2026-04-22  
**Status**: Observe-only + first hypothesis lanes complete; Windows comparator baseline established  
**Size**: Medium (2-3 focused sessions)  
**Owner**: Codex  
**Link**: [docs/work-packages/20260422_jagged_hyperpigmentation_hillslope_ablation_queue/](docs/work-packages/20260422_jagged_hyperpigmentation_hillslope_ablation_queue/)  
**Description**: Prepared next ablation campaign slice for run `jagged-hyperpigmentation/disturbed9002-10-mofe`, focused on anomalous `element.dat` signatures and sediment concentration in hillslopes `H3507` and `H1271`.

**Current Status**:
- Incident package initialized at `/workdir/wepp-forest/docs/ablation/20260422_jagged-hyperpigmentation_hillslope_elementdat-stars/`.
- Source artifacts staged from `wepp1:/geodata/wc1/runs/ja/jagged-hyperpigmentation`.
- Baseline local replays complete for `p1271` and `p3507`; source-vs-staged signature scans recorded (`C099`, `C100`).
- `blarhg` Windows comparator binary inventory captured (SHA256 `07d348d5f9ebff607b6f8e15bea8647410a080c8451b9017f74a9475f39c569d`, timestamp `2026-04-18T02:41:59Z`) as case `C101`.
- Observe-only and first hypothesis lanes completed (`C101-C106`), including Windows target replays and cross-lane signature census.
- Decision recorded: use `C:\src\wepppy-win-bootstrap\bin\wepppy-win-bootstrap.exe` as parity comparator baseline for this incident.

**Next Steps**:
1. Execute the next one-change hypothesis lane group using the pinned Windows comparator baseline.
2. Isolate minimal causal delta for source-only starred signatures.
3. Publish keep/rollback recommendation for next implementation package.

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

### AgFields Backend Readiness (2026-07-09)
**Status**: ✅ **COMPLETE**

**Link**: [docs/work-packages/20260709_ag_fields_backend_readiness/](docs/work-packages/20260709_ag_fields_backend_readiness/)

**Lifecycle**: Backlog -> In Progress -> Done (2026-07-09)

**Summary**: Repaired configured-WEPP-binary propagation and delivered the
AgFields backend contract for the successor runs-page UI: atomic controller
mutations, staleness/readiness state, deterministic plant and rotation handling,
three guarded RQ entrypoints, 13 authenticated rq-engine route shapes,
single-flight admission, bounded uploads, queue graph registration, regression
coverage, ADR-0015, and a passing dedicated security review. Focused AgFields
validation passed 52 tests; the full suite stopped after 2,070 passing tests at
an unrelated, independently reproducible batch-runner baseline failure. A real
WEPP binary end-to-end run remains follow-up because no seeded AgFields run was
available locally.

---

### Auth Cap.js CAPTCHA (2026-07-01)
**Status**: ✅ **COMPLETE**

**Link**: [docs/work-packages/20260701_auth_cap_captcha/](docs/work-packages/20260701_auth_cap_captcha/)

**Lifecycle**: Scoped -> Implemented -> Done (2026-07-01)

**Summary**: Added Cap.js to local password login and registration forms,
enforced server-side `cap_token` validation in Flask-Security forms, and
updated the Playwright smoke login helper to solve login-page Cap challenges
through the Cap challenge/redeem API. Focused validation passed:
`wctl run-pytest tests/weppcloud/test_auth_cap_captcha.py --maxfail=1`,
`wctl run-npm lint`, `wctl run-npm test`, JS syntax check, and doc lint for
changed docs.

---

### Browse Tree Theme Integration (2026-06-30)
**Status**: ✅ **COMPLETE**

**Link**: [docs/work-packages/20260630_browse_tree_theme/](docs/work-packages/20260630_browse_tree_theme/)

**Lifecycle**: Backlog -> In Progress -> Done (2026-06-30)

**Summary**: Applied WEPPcloud theme assets and persisted `wc-theme` bootstrapping
to browse directory tree and not-found views while preserving the Default
theme's exact odd/even/hover row backgrounds. Added generic theme-token
odd/even/hover row styling for named themes, moved the Parquet Data Filter
builder off inline hard-coded colors, and added Theme Lab targets for browse
tree rows plus the filter builder. Focused validation passed:
`tests/microservices/test_browse_routes.py` (18 passed),
`tests/weppcloud/routes/test_ui_showcase_bp.py` (6 passed), package/docs lint,
and `wctl run-playwright --suite theme-metrics` (1,430 measurements, 13 themes,
78 browse-tree measurements, 0 browse-tree failures, 91 filter-builder
measurements, 0 filter-builder failures, 13/13 themes with distinct browse-tree
row backgrounds).

### Browse Parquet Preview Theme Integration (2026-06-30)
**Status**: ✅ **COMPLETE**

**Link**: [docs/work-packages/20260630_browse_parquet_preview_theme/](docs/work-packages/20260630_browse_parquet_preview_theme/)

**Lifecycle**: Backlog -> In Progress -> Done (2026-06-30)

**Summary**: Consolidated parquet preview and active-filter feedback into a single fixed browse banner, moved the standalone browse table preview onto WEPPcloud theme assets and persisted `wc-theme` bootstrapping, and added Theme Lab contrast-target coverage for preview text, filter text/code, and actions. Focused validation passed: `tests/microservices/test_browse_routes.py` (16 passed), `tests/weppcloud/routes/test_ui_showcase_bp.py` (4 passed), package/docs lint, and `wctl run-playwright --suite theme-metrics` (1261 measurements, 13 themes, 91 browse-banner measurements, 0 browse-banner failures).

### UI Lab Light Landing Keyboard Access (2026-06-29)
**Status**: ✅ **COMPLETE**

**Link**: [docs/work-packages/20260629_ui_lab_light_keyboard_access/](docs/work-packages/20260629_ui_lab_light_keyboard_access/)

**Lifecycle**: Backlog -> In Progress -> Done (2026-06-29)

**Summary**: Fixed the UI Lab light landing route and keyboard traversal. The
`/weppcloud/landing/light/` variant now serves generated assets and run-location
data through narrow Flask aliases with no-store landing responses, the light
landing source exposes a skip link, explicit link tab stops, a body-start
first-Tab fallback, strong visible focus styling, a named map region, keyboard
map zoom/reset controls, a non-focusable map visual, and a hidden filter-panel
focus guard.
Added Playwright coverage in
`wepppy/weppcloud/static-src/tests/smoke/landing-keyboard.spec.js`, rebuilt and
installed the UI Lab bundle into `wepppy/weppcloud/static/ui-lab/`, and verified
the live local route at `wc.bearhive.duckdns.org` tabs link-by-link through the
early page controls with visible focus indicators and no map-stage focus.
Focused validation passed:
`npm --prefix weppcloud-ui-lab run lint`, `npm --prefix weppcloud-ui-lab run
build`, `npm --prefix weppcloud-ui-lab run export:landing`,
`wctl run-pytest tests/weppcloud/routes/test_landing_template.py --maxfail=1`,
`wctl run-playwright --suite full --grep "light landing keyboard" --workers 1`,
`wctl run-npm test`, direct ESLint on the new smoke spec, py_compile for
`weppcloud_site.py`, and work-package doc lint.

### Forest-Family Burn Gradient Assessment (2026-06-26)
**Status**: ✅ **COMPLETE**

**Link**: [docs/work-packages/20260626_forest_family_burn_gradient_assessment/](docs/work-packages/20260626_forest_family_burn_gradient_assessment/)

**Lifecycle**: Backlog -> Done (2026-06-26)

**Summary**: Expanded the disturbed matrix harness and regenerated
`tests/disturbed/analysis_results.md` for 80 hillslope simulations
(`4` soil textures x `5` vegetation types x `4` burn severities). The new
forest-family assessment compares evergreen, deciduous, and mixed unburned
baselines against the existing generic forest low/moderate/high burn
managements. All forest-family rows remained directionally correct for matched
runoff total, sediment-delivery total, and peakflow total, so no
low/moderate/high burned deciduous or mixed forest parameterization is indicated
by this matrix. Focused validation passed:
`wctl run-pytest tests/disturbed/test_disturbed_matrix.py -q` (`83 passed`,
`2 warnings`, `232.70s`).

### totalwatsed3 Interception-Flux Closure (2026-06-08)
**Status**: ✅ **COMPLETE**

**Link**: [docs/work-packages/20260607_totalwatsed3_interception_flux_closure/](docs/work-packages/20260607_totalwatsed3_interception_flux_closure/)

**Lifecycle**: Backlog -> Done (2026-06-08)

**Summary**: Closed the openWEPP WBVAL06 interception-audit gap by consuming
optional `hillslope_wat.Interception` as a first-class outflow in
`totalwatsed3` and its closure audit surface, with legacy-safe zero-default
semantics when the column is absent. Updated
`wepppy/wepp/interchange/totalwatsed3.py`,
`tools/totalwatsed3_daily_closure_audit.py`, and
`docs/dev-notes/totalwatsed-interchange.spec.md`; added focused regressions and
validated targeted tests (`8 passed`). Acceptance evidence on openWEPP
post-WBVAL06 WAT outputs shows year-index `2..6` annual residuals near
`~2e-07 mm` with interception versus `~14.7..18.9 mm` without interception.

### Indispensable Presenter Daymet Radiation Bounds Investigation (2026-06-06)
**Status**: ✅ **COMPLETE**

**Link**: [docs/work-packages/20260606_indispensable_presenter_daymet_radiation_bounds/](docs/work-packages/20260606_indispensable_presenter_daymet_radiation_bounds/)

**Lifecycle**: Backlog -> In Progress -> Done (2026-06-06)

**Summary**: Closed the observed-Daymet radiation source-boundary package for
`/wc1/runs/in/indispensable-presenter`. Execution proved genuine Daymet
over-TOA source rows at the WEPPpy producer boundary, added ADR-0006, and
implemented bounded normalization to baseline `sunmap.r3` before generated CLI
`rad` publication while preserving original source values and a per-build CSV
provenance artifact. The WBVAL03 blocker row `1990-02-18` now normalizes from
`486.398513 Ly/day` to publication-safe `453 Ly/day`; real-run validation
found 53 affected rows and post-normalization max excess `0.0`. Post-rebuild
verification found the exact-bound rule still allowed 22 integer CLI rounding
exceedances, so the producer now publishes the largest integer L/day value
below `sunmap.r3`. Focused validation passed (`20` + `29` tests). Follow-up is
to regenerate downstream openWEPP
WBVAL03 inputs from corrected WEPPpy climate artifacts.

### PFDF Removal and Native NOAA Atlas 14 Client (2026-05-29)
**Status**: ✅ **COMPLETE**

**Link**: [docs/work-packages/20260529_noaa_atlas14_pfdf_removal/](docs/work-packages/20260529_noaa_atlas14_pfdf_removal/)

**Lifecycle**: Backlog -> In Progress -> Done (2026-05-29)

**Summary**: Removed GPLv3 `pfdf` runtime dependency by introducing a WEPPpy-owned Atlas 14 client at `wepppy/climates/noaa/atlas14.py` based on NOAA PFDS public endpoint contracts (`cgi_readH5.py` and HDSC FAQ references). Cut over `ClimateArtifactExportService.download_noaa_atlas14_intensity` to the new client, preserved optional NOAA artifact and retry/no-coverage semantics, removed `pfdf` from `docker/requirements-uv.txt`, updated NOAA tests/docs, and added deterministic unit coverage (`tests/climates/noaa/test_atlas14_client.py`). Focused validation passed (`4 passed`, `12 passed`, NOAA live tests network-gated/`4 skipped`). Full-suite gate still stops on unrelated baseline failure in `tests/nodb/test_ron_fetch_dem_copernicus.py` (`Ron._cellsize` AttributeError).

### RUSLE K Conservative Second-Stage Gap Fill (2026-05-28)
**Status**: ✅ **COMPLETE**

**Link**: [docs/work-packages/20260527_rusle_k_second_stage_gap_fill/](docs/work-packages/20260527_rusle_k_second_stage_gap_fill/)

**Lifecycle**: Backlog -> In Progress -> Done (2026-05-28)

**Summary**: Implemented a conservative two-stage POLARIS nodata fill policy
for RUSLE `K` preprocessing in `k_integration.py`. Stage-1 remains unchanged
(`1-64` px, `<=10%`, search `6` px). New stage-2 fills residual medium interior
components (`65-4096` px, `<=5%`, search `12` px), preserving edge-connected
and oversized gaps as nodata. Manifest reporting now captures stage-specific
policy/outcomes while retaining stage-1-compatible top-level keys.
Added regression tests for stage-2 fill-applied and stage-2 fraction-guard skip
paths. Targeted validation passed (`12` + `11` tests), docs were updated, and
ADR-0005 captured parameterization governance.

### RUSLE `scenario_sbs` Surface-Rock Partition Integration (2026-05-27)
**Status**: ✅ **COMPLETE**

**Link**: [docs/work-packages/20260527_rusle_sbs_surface_rock_partition/](docs/work-packages/20260527_rusle_sbs_surface_rock_partition/)

**Lifecycle**: Backlog -> In Progress -> Done (2026-05-27)

**Summary**: Executed end-to-end RAP-independent SBS surface-rock integration for RUSLE `C` by introducing `rock_fraction_of_sbs_bare` across NoDb runtime/controller parsing, rq-engine payload/schema-default contracts, and WEPPcloud RUSLE UI controls. `scenario_sbs` now partitions lookup bare fraction before `C = exp(-0.04 * fg)` mapping, supports `auto` proxy precedence (`cosurffrags -> cfvo -> 0.0`) with lookup-bare normalization, and records manifest provenance (`requested`, `effective`, `source`). Added targeted regressions for runtime math/validation, API contract wiring, and JS payload behavior; targeted validation suites passed and review/disposition artifacts closed with no unresolved high/medium findings.

### SSURGO Corestrictions `kslast` Viability Assessment (2026-05-23)
**Status**: ✅ **COMPLETE**

**Link**: [docs/work-packages/20260522_ssurgo_corestrictions_kslast_viability/](docs/work-packages/20260522_ssurgo_corestrictions_kslast_viability/)

**Lifecycle**: Backlog -> In Progress -> Done (2026-05-23)

**Summary**: Completed M0-M5 assessment artifacts for SSURGO `corestrictions` viability against legacy `kslast` behavior, including national coverage aggregates, ecoregion-sampled coverage/reasonableness matrices, bounded candidate-rule comparisons, and recommendation memo. Final outcome is `retain legacy` with explicit follow-up gating for full run-fixture hydrologic validation. Restrictive-present shortfalls in some regions are documented as SDA extraction/runtime infrastructure constraints for this run, not evidence of missing underlying SSURGO records.

### WEPPcloud Feature and Config Registry Implementation (2026-05-22)
**Status**: ✅ **COMPLETE**

**Link**: [docs/work-packages/20260521_feature_registry/](docs/work-packages/20260521_feature_registry/)

**Lifecycle**: Backlog -> In Progress -> Done (2026-05-22)

**Summary**: Implemented dual registries under `wepppy/weppcloud/feature_registry/` (`feature_registry.yaml`, `config_registry.yaml`) with shared schema validation/runtime loaders. Migrated `project_bp.py` feature label/dependency/disable-guard metadata to registry authority, migrated `run_0_bp.py` mod UI definitions and header mod options to registry-backed metadata, and wired `weppcloud_site.interfaces` + `interfaces.htm` launch config values/maturity badges to config registry metadata. Added user-facing maturity definitions in usersum guide and landed targeted regressions (`test_feature_registry_runtime.py`, template rendering updates) with passing focused validation (`112 passed`).

### NoDb Atomic Write Replace Hardening (2026-05-20)
**Status**: ✅ **COMPLETE (waiver accepted for unrelated baseline test)**

**Link**: [docs/work-packages/20260519_nodb_atomic_write_hardening/](docs/work-packages/20260519_nodb_atomic_write_hardening/)

**Lifecycle**: Backlog -> In Progress -> Done (2026-05-20)

**Summary**: Closed atomic NoDb write hardening for the `omni.nodb` concurrent decode race by replacing truncate-in-place writes with temp-file + atomic `os.replace` persistence, preserving stale-writer contract behavior, mode semantics, and replace-failure retry safety. Added deterministic race/failure characterization coverage in `tests/nodb/test_base_boundary_characterization.py`, including explicit legacy deficiency demonstration (`JSONDecodeError` under truncate window) and NFS-oriented `ESTALE` post-commit fsync behavior. Iterative `reviewer` + `qa_reviewer` loops closed with zero unresolved High/Medium findings. Operator accepted waiver for unrelated baseline failure `tests/nodb/test_ron_fetch_dem_copernicus.py` (`Ron._cellsize` missing), which remains tracked outside this package scope.

### EBE `peak_runoff` Regression Ablation and Repair (2026-05-13)
**Status**: ✅ **COMPLETE (with residual follow-ups)**

**Link**: [docs/work-packages/20260513_ebe_pw0_peak_runoff_regression_ablation/](docs/work-packages/20260513_ebe_pw0_peak_runoff_regression_ablation/)

**Lifecycle**: Backlog -> In Progress -> Done (2026-05-13)

**Summary**: Completed ablation-first regression isolation for `ebe_pw0.peak_runoff` all-zero behavior in `off-the-rack-neoprene` (`wepp_260513`), proving first-loss boundary at producer raw `ebe_pw0.txt` and parser/interchange non-causality. Built and vendored candidate binaries (`wepp_260513`, `wepp_260513_hill`) with sidecars and provenance evidence, then verified live rerun semantics: `ebe_peak_zero_rows=0`, `chan_pos_ebe_zero=0`, and chan-vs-ebe deltas in expected small envelope. Package closed with explicit residual follow-ups for targeted regression-test hardening and broader three-cohort recertification.

### Deterministic Return Ordering for wepppyo3 Raster Characteristics APIs (2026-05-13)
**Status**: ✅ **COMPLETE**

**Link**: [docs/work-packages/20260512_wepppyo3_raster_characteristics_deterministic_order/](docs/work-packages/20260512_wepppyo3_raster_characteristics_deterministic_order/)

**Lifecycle**: Backlog -> In Progress -> Done (2026-05-13)

**Summary**: Hardened all public map-returning `wepppyo3.raster_characteristics` APIs to deterministic key order at the Rust API boundary by replacing unordered return maps with `BTreeMap`/nested `BTreeMap` where required. Added repeated-call deterministic-order + semantic-parity regression coverage in `tests/raster_characteristics/test_deterministic_ordering_contract.py` (including negative-path error-contract assertions), refreshed `release/linux/py312/wepppyo3/raster_characteristics/raster_characteristics_rust.so`, captured runtime import and SHA256 evidence (`a2dddb70c3c9670bad8c4103b64d455539896d5ea1be17a99d9c5adc88dccda6`), updated `wepppyo3` documentation (`README.md`, `docs/module-registry.md`, `docs/release-provenance.md`), passed targeted WEPPpy consumer suites (`9 passed` plus optional `85 passed`), and closed independent review with no unresolved high/medium findings.

### RUSLE K CFVO Profile-Fragment Adjustment Integration (2026-05-07)
**Status**: ✅ **COMPLETE**

**Link**: [docs/work-packages/20260507_rusle_k_cfvo_integration/](docs/work-packages/20260507_rusle_k_cfvo_integration/)

**Lifecycle**: Backlog -> In Progress -> Done (2026-05-07)

**Summary**: Closed the deferred `cfvo` path for RUSLE `K`. `k_integration` now supports optional run-scoped profile-fragment adjustment for `polaris_nomograph` by discovering aligned `cfvo` layers, aligning SoilGrids `soils/cfvo_*_Q0.5.tif` depth rasters when present, converting SoilGrids `cfvo` from per-mille to `vol%`, applying conservative permeability-class shifts (`<25`: 0, `25-<60`: +1, `>=60`: +2, clamped to class 6), and writing explicit applied/skipped metadata in `rusle/manifest.json`. Added regression coverage for applied, no-change, malformed-input optional skip, aligned-layer reuse, and invalid-mode no-side-effect behavior. Targeted validation passed (`10 passed`, then `31 passed`), doc lint passed, and full-suite gate still stops on unrelated NoDb baseline failure (`tests/nodb/test_base_boundary_characterization.py::test_dump_forces_mtime_advance_on_unchanged_signature_then_rejects_stale_writer`). Review and QA findings were fully dispositioned under `docs/work-packages/20260507_rusle_k_cfvo_integration/artifacts/`.

### RUSLE POLARIS K Conservative Small-Hole Fill (2026-05-07)
**Status**: ✅ **COMPLETE**

**Link**: [docs/work-packages/20260507_rusle_k_polaris_gap_fill/](docs/work-packages/20260507_rusle_k_polaris_gap_fill/)

**Lifecycle**: Backlog -> In Progress -> Done (2026-05-07)

**Summary**: Added conservative run-scoped interpolation for small interior POLARIS `NoData` defects before RUSLE `K` derivation in `wepppy/nodb/mods/rusle/k_integration.py`. The policy fills only interior holes up to `64` pixels with an inverse-distance kernel (`max_search_distance=6 px`, no smoothing), skips edge-connected gaps, and skips automated fill when candidate small-hole coverage exceeds `10%` of eligible cells. Manifest reporting now includes `k.gap_fill_policy` and per-property `k.gap_fill_summary` outcomes. Targeted K/RUSLE tests passed (`5 passed`, then `26 passed`); full suite `tests --maxfail=1` surfaced an unrelated baseline failure in `tests/nodb/test_base_boundary_characterization.py::test_dump_forces_monotonic_signature_after_second_same_size_rewrite`. QA and finding dispositions are recorded under `docs/work-packages/20260507_rusle_k_polaris_gap_fill/artifacts/`.

### RUSLE LS Full-Extent Routing + Conservative Small-Defect Fallback (2026-05-07)
**Status**: ✅ **COMPLETE**

**Link**: [docs/work-packages/20260507_rusle_ls_extent_fallback/](docs/work-packages/20260507_rusle_ls_extent_fallback/)

**Lifecycle**: Backlog -> In Progress -> Done (2026-05-07)

**Summary**: Removed the `wepppy`-generated outside-watershed LS blocking mask path so `RusleLsFactor` now runs over full DEM/map extent by default unless explicit stop masks are provided. Hardened `/workdir/weppcloud-wbt` `RusleLsFactor` DInf-derived SCA behavior with bounded conservative fallback for small interior no-flow defects (`BreachSingleCellPits`), retained fail-fast behavior for larger/unresolved defects, and added metadata fields documenting no-flow guard state and thresholds. Updated wrapper and spec documentation, with QA evidence recorded in `docs/work-packages/20260507_rusle_ls_extent_fallback/artifacts/20260507_qa_review.md`.

### Ablation Protocol Tooling Port (2026-05-02)
**Status**: ✅ **COMPLETE**

**Link**: [docs/work-packages/20260502_ablation_protocol_tooling/](docs/work-packages/20260502_ablation_protocol_tooling/)

**Lifecycle**: Backlog -> In Progress -> Done (2026-05-02)

**Summary**: Closed with a local port of `tools/ablation_protocol.py` and a targeted regression suite at `tests/tools/test_ablation_protocol.py`, aligned to the established `wepp-forest` behavior contract. Added local `docs/ablation/TEMPLATE_*` files plus `docs/ablation/README.md` so `init` works against the default root in this repo. Validation passed via `wctl run-pytest tests/tools/test_ablation_protocol.py` (`17 passed, 2 warnings`), and code-review disposition was captured in `docs/work-packages/20260502_ablation_protocol_tooling/artifacts/20260502_code_review.md`.

### Uncapped-Spectacular H2637 Ablation Campaign (2026-04-30)
**Status**: ✅ **COMPLETE**

**Link**: [docs/work-packages/20260430_uncapped_spectacular_h2637_ablation_campaign/](docs/work-packages/20260430_uncapped_spectacular_h2637_ablation_campaign/)

**Lifecycle**: Backlog -> In Progress -> Done (2026-04-30)

**Summary**: Completed end-to-end attribution campaign for `uncapped-spectacular` hillslope `H2637`, including required Windows comparator execution on `blarhg` with `C:\\src\\wepppy-win-bootstrap\\bin\\wepppy-win-bootstrap.exe`. Incident package `20260430_uncapped-spectacular_h2637_hillslope_closure-spike` was executed/finalized in `/workdir/wepp-forest/docs/ablation/` with lane matrix `C000` (production binary replay), `C010` (historical comparator), and `C020` (Windows comparator). Day-44 legacy closure spike was reproduced in source + `C000` and not reproduced in comparator lanes; day-45 remained near zero. Package artifacts now include `artifacts/evaluation_summary.md` and `artifacts/incident_snapshot/` with matrix, notes, summaries, and integrity records.

### Hillslope Daily Closure Audit Tool (MOFE + Single OFE) (2026-04-30)
**Status**: ✅ **COMPLETE**

**Link**: [docs/work-packages/20260430_hillslope_daily_closure_audit/](docs/work-packages/20260430_hillslope_daily_closure_audit/)

**Lifecycle**: Backlog -> In Progress -> Done (2026-04-30)

**Summary**: Closed with a new repeatable hillslope closure audit CLI (`tools/hillslope_daily_closure_audit.py`) that operates directly on interchange artifacts (`H.wat`, `H.pass`, optional `H.soil`/`H.element`) for one hillslope selected by `--wepp-id` or `--topaz-id`. The tool preserves MOFE accounting by using outlet-OFE-only `latqcc` and PASS `runvol` for runoff depth. Regression coverage (`tests/tools/test_hillslope_daily_closure_audit.py`) validates single-OFE closure arithmetic, MOFE outlet/runoff behavior, selector paths, and invalid selector rejection; existing watershed closure-audit tests remained green. Real-run artifacts were generated for six exemplars (`uninsured-deformation` H78/H43/H97 and `bovine-clipboard` H1/H2/H3), plus a topaz-selector verification run, with consolidated stats in `artifacts/evaluation_summary.{md,csv}`. Independent review findings were dispositioned in `artifacts/20260430_code_review_disposition.md`.

### WEPP Gregorian Leap-Year Contract and Centurial Tolerance (2026-04-30)
**Status**: ✅ **COMPLETE**

**Link**: [docs/work-packages/20260430_wepp_gregorian_leap_tolerance/](docs/work-packages/20260430_wepp_gregorian_leap_tolerance/)

**Lifecycle**: Backlog -> In Progress -> Done (2026-04-30)

**Summary**: Completed leap-year contract correction and compatibility preservation across WEPP source and vendored artifacts. Updated active runtime leap call sites in `/workdir/wepp-forest/src` (`stmget.for`, `wshpas.for`, `contin.for`, `wshdrv.for`) to Gregorian classification (`/4` except `/100` unless `/400`) while retaining non-400 centurial day-366 tolerance in day-count/loop branches. Rebuilt binaries, validated required `wepp-forest` gates (smoke for `wepp` and `wepp_hill`, hillslope watchlist `12/12`, ablation artifact policy, full `pytest -q` with `79 passed, 2 warnings`), and captured centurial controls (`year100/365` false warning removed, `year100/366` tolerated success, `year2000/366` leap success). Released/vendored `wepp_260430` and `wepp_260430_hill`, synced changelog copy into `wepppy`, and passed post-vendor provenance/smoke/focused regressions (`8 passed`).

### Geneva HRU Peak Runoff and Event Erosion Enablement (2026-04-30)
**Status**: ✅ **COMPLETE**

**Link**: [docs/work-packages/20260429_geneva_hru_peak_event_erosion/](docs/work-packages/20260429_geneva_hru_peak_event_erosion/)

**Lifecycle**: Backlog -> In Progress -> Done (2026-04-30)

**Summary**: Closed the Geneva HRU-local peak runoff substrate package end to end. Rust `geneva_core` `run_batch` now emits per-HRU `peak_runoff_m3_s` and `time_to_peak_minutes` using per-HRU incremental excess + HRU area through the existing Geneva unit-hydrograph convolution path (no watershed area-splitting). PyO3 bridge tests were updated, `cli_revision_rust` release artifacts were rebuilt/synced to both runtime locations, and matching SHA-256 provenance was recorded. WEPPpy now materializes `measure_id=hru_peak_runoff` (`unit=m3_s`) in `geneva/hru_event_measure_rows.parquet`, HRU-map measure validation accepts `hru_peak_runoff` while still rejecting watershed-only `peak_discharge`, and Geneva Interactive Summary HRU Choropleth controls now expose `HRU peak runoff`. Section 12.4/12.5 specification updates, validation summary, code review, QA review, and dedicated security review artifacts are complete. Required gates passed except known unrelated frontend lint baseline in `controllers_js/__tests__/landuse_map_inline.test.js`, which is documented in the package validation artifact.

### NOAA Atlas 14 Retry Backoff Hardening for Climate Artifact Export (2026-04-30)
**Status**: ✅ **COMPLETE**

**Link**: [docs/work-packages/20260429_noaa_atlas14_retry_backoff/](docs/work-packages/20260429_noaa_atlas14_retry_backoff/)

**Lifecycle**: Backlog -> In Progress -> Done (2026-04-30)

**Summary**: Completed bounded exponential retry/backoff hardening for optional NOAA Atlas 14 climate artifact export. `download_noaa_atlas14_intensity` now applies parameterized retries (`timeout=30s`, `attempts=3`, `base=1.0s`, `cap=8.0s`; env-overridable via `WEPPPY_NOAA_ATLAS14_*`) and logs attempt/backoff/exhaustion context while preserving non-fatal exhaustion behavior. `ValueError` no-coverage remains immediate non-retryable. Deterministic regressions cover transient failure then success, bounded retry exhaustion, no-coverage immediate return, timeout propagation, cap-hit backoff, and invalid-env fallback. Targeted validation passed: `wctl run-pytest tests/nodb/test_climate_artifact_export_service.py --maxfail=1` (`12 passed`).

### Uncapped-Spectacular totalwatsed3 Runoff Reconciliation (2026-04-29)
**Status**: ✅ **COMPLETE**

**Link**: [docs/work-packages/20260429_uncapped_spectacular_totalwatsed3_runoff_reconciliation/](docs/work-packages/20260429_uncapped_spectacular_totalwatsed3_runoff_reconciliation/)

**Lifecycle**: Backlog -> In Progress -> Done (2026-04-29)

**Summary**: Closed a production runoff-depth reconciliation package for `uncapped-spectacular`. Corrected `totalwatsed3` runoff derivation to use `runvol/Area*1000` (instead of `QOFE` depth basis), added regression coverage, and introduced a repeatable CLI audit (`tools/totalwatsed3_daily_closure_audit.py`) with unit tests. Performed a no-restart `wepp1` runtime hotfix and regenerated `/geodata/wc1/runs/un/uncapped-spectacular/wepp/output/interchange/totalwatsed3.parquet`; container uptime remained unchanged. Post-refresh verification confirmed `max(abs(Runoff - runvol/Area*1000)) = 0.0`, and closure-audit outputs were captured under both wepp1 run artifacts and package artifacts.

### Geneva Interactive Summary HRU Choropleth Series (2026-04-29)
**Status**: ✅ **COMPLETE**

**Link**: [docs/work-packages/20260428_geneva_hru_choropleth_series/](docs/work-packages/20260428_geneva_hru_choropleth_series/)

**Lifecycle**: Backlog -> In Progress -> Done (2026-04-29)

**Summary**: Closed WP01-WP04 end to end. WP01 finalized contracts and preserved watershed-only `peak_discharge`; WP02 added HRU event-measure artifact/query support and enforced map-scope validation; WP03 delivered Geneva deck.gl HRU choropleth UI with themed controls and runoff `winter` palette; WP04 executed validation/docs/release closure. Required scoped pytest, targeted Geneva JS tests, docs lint, and `git diff --check` passed. Known unrelated `wctl run-npm lint` baseline in `wepppy/weppcloud/controllers_js/__tests__/landuse_map_inline.test.js` was reproduced and documented as external to this series.

### Geneva Preflight Checklist Freshness Integration (2026-04-29)
**Status**: ✅ **COMPLETE**

**Link**: [docs/mini-work-packages/20260429_geneva_preflight_checklist_execplan.md](docs/mini-work-packages/20260429_geneva_preflight_checklist_execplan.md)

**Lifecycle**: Backlog -> In Progress -> Done (2026-04-29)

**Summary**: Closed the Geneva preflight checklist freshness package end to end. Added dedicated `TaskEnum.run_geneva` (`🐈`) ownership, stamped completion on successful Geneva batch runs, and wired Geneva into TOC emoji mapping (`#geneva`) plus preflight checklist payloads (`checklist.geneva`). `preflight2` now evaluates Geneva freshness against `build_landuse`, `build_soils`, `build_climate`, and conditionally `init_sbs_map` when `attrs:has_sbs == "true"`. Stale invalidators now clear `timestamps:run_geneva` at documented boundaries: Geneva config diffs, Geneva CN-table modify/reset, Geneva prepare/panel/workflow enqueue paths, SBS upload/remove/uniform/class edits, and climate/landuse/soils enqueue paths. Follow-up hardening stamped `TaskEnum.init_sbs_map` on Disturbed/BAER SBS mutation paths that set `attrs:has_sbs=true`, added Geneva-run legacy backfill for historical `has_sbs=true` runs missing `timestamps:init_sbs_map`, and completed a one-time Redis sweep backfilling `99` legacy SBS runs. Authenticated smoke on `onshore-xenophobia/disturbed9002_wbt` confirmed websocket `checklist.geneva=true` and Geneva TOC emoji metadata present in run-page bootstrap. Queue dependency artifacts were synchronized (`job-dependency-graph.static.json` + `job-dependencies-catalog.md`) and `wctl check-rq-graph` is green. Targeted validation gates passed; optional full-suite confidence gate still fails on unrelated existing `tests/nodb/test_base_boundary_characterization.py::test_dump_forces_monotonic_signature_after_second_same_size_rewrite`.

### WEPP Interchange Dependency Race Guard (2026-04-29)
**Status**: ✅ **COMPLETE**

**Link**: [docs/work-packages/20260428_wepp_interchange_dependency_race_guard/](docs/work-packages/20260428_wepp_interchange_dependency_race_guard/)

**Lifecycle**: Backlog -> In Progress -> Done (2026-04-29)

**Summary**: Closed the WEPP interchange race-hardening package end to end. Queue wiring now enforces deterministic ordering so `_post_watershed_interchange_rq` cannot start before `_build_hillslope_interchange_rq` in `enqueue_wepp_pipeline` and `enqueue_wepp_noprep_pipeline`, removing the known `H.wat.parquet.tmp` commit race window. Regression coverage was expanded in `tests/rq/test_wepp_rq_pipeline.py` to assert dependency identity across all helpers that enqueue `_post_watershed_interchange_rq`, including watershed-only paths that remain cleanup-only by design. Queue dependency artifacts (`wepppy/rq/job-dependency-graph.static.json`, `wepppy/rq/job-dependencies-catalog.md`) were synchronized and validated (`wctl check-rq-graph` up to date). Independent `reviewer` and `qa_reviewer` artifacts were completed, the one medium QA finding was resolved in-package, and the dedicated security review gate passed with no unresolved medium/high findings.

### Geneva Storm Shape Control (2026-04-28)
**Status**: ✅ **COMPLETE**

**Link**: [docs/work-packages/20260428_geneva_storm_shape_control/](docs/work-packages/20260428_geneva_storm_shape_control/)

**Lifecycle**: Backlog -> In Progress -> Done (2026-04-28)

**Summary**: Closed the Geneva storm-shape package end to end across `/workdir/wepppy` and `/workdir/wepppyo3`. Added closed-enum `Storm Shape` support (`uniform`, `neh4_type_b`, `type_i`, `type_ia`, `type_ii`, `type_iii`) through UI, controller payloads, Python schemas/services/reports, and Rust kernel hyetograph dispatch. Source gating requirements were satisfied first with checked-in raw WinTR-20 table payload, normalized CSV, and metadata under `geneva_core/resources/`, including Type II embedded-duration validation within `<= 0.003` absolute tolerance. Package closure also addressed reviewer/QA findings: kernel callable availability, panel/run-batch distribution consistency, non-divisible timestep rejection, stale-summary suppression, positive-depth contract alignment, and explicit legacy-uniform warning surfacing. Required validation commands passed except an unrelated pre-existing JS lint issue in `controllers_js/__tests__/landuse_map_inline.test.js`; reviewer, QA, and validation artifacts are recorded under the package `artifacts/` directory.

### wepppyo3 Native Substrate Repositioning (2026-04-28)
**Status**: ✅ **COMPLETE**

**Link**: [docs/work-packages/20260428_wepppyo3_repositioning/](docs/work-packages/20260428_wepppyo3_repositioning/)

**Lifecycle**: Backlog -> In Progress -> Done (2026-04-28)

**Summary**: Closed the docs-first `wepppyo3` repositioning package. `/workdir/wepppyo3/README.md` now positions the repo as WEPPpy's native kernel and interchange substrate, and new canonical docs define the module registry, architecture boundaries, release provenance, and claim discipline. WEPPpy architecture, package README, root README, and dependency-standard references now point to this posture instead of describing `wepppyo3` as a generic accelerator bundle. Validation passed with scoped WEPPpy doc-lint, `git diff --check` in both repos, `uk2us` preview for changed Markdown, and manual `wepppyo3` relative-link validation. Runtime behavior and release binaries were not changed; the ExecPlan is archived under `prompts/completed/`.

### RQ Scoped Stale NoDb Cache Guard Priority 2 (2026-04-28)
**Status**: ✅ **COMPLETE**

**Link**: [docs/work-packages/20260428_rq_scoped_stale_cache_guard_priority2/](docs/work-packages/20260428_rq_scoped_stale_cache_guard_priority2/)

**Lifecycle**: Backlog -> Done (2026-04-28)

**Summary**: Closed Priority 2 scoped stale-cache guard conformance across deferred RQ module families. Implemented exact pre-hydration guards for WEPP orchestration (`wepp.nodb`), SWAT build/run/interchange (`swat.nodb`), Omni scenario/contrast orchestration and contrast deletion (`omni.nodb`), PATH CE orchestration (`path_ce.nodb` + `omni.nodb`), Roads prepare/run (`roads.nodb`), Geneva prepare/panel/batch (`geneva.nodb`), and fork undisturbify destination-run mutations (`new_runid` scopes: `ron.nodb`, `disturbed.nodb`, `landuse.nodb`, `soils.nodb`). Targeted tests assert scoped `pup_relpath` values and guard-before-hydration ordering while preserving existing lock/archive/status/timestamp/enqueue/clone/delete/autocommit/runtime-lock behavior. All required focused pytest suites, package doc-lint, and `git diff --check` passed; ExecPlan archived under `prompts/completed/`.

### RQ Scoped Stale NoDb Cache Guard Follow-Ups (2026-04-28)
**Status**: ✅ **COMPLETE**

**Link**: [docs/work-packages/20260428_rq_scoped_stale_cache_guard_followups/](docs/work-packages/20260428_rq_scoped_stale_cache_guard_followups/)

**Lifecycle**: Backlog -> Done (2026-04-28)

**Summary**: Closed the scoped RQ stale-cache guard follow-up package. `wepppy/rq/project_rq.py` now clears exact scoped NoDb cache entries before mutable hydration for Priority 0 project-prep paths and simple Priority 1 mod paths (`rangeland_cover`, treatments landuse/soils, ash, debris flow, RAP TS, OpenET TS, POLARIS, RUSLE). Regression coverage asserts exact scopes, archive/root rejection before cache clear, guard-before-hydration ordering, and representative status/timestamp/enqueue behavior. Priority 2 WEPP/SWAT/Omni/PATH CE/Roads/Geneva/fork-undisturbify candidates were split/deferred with rationale because they need module-specific orchestration tests. Required targeted pytest, package doc-lint, and `git diff --check` passed; the ExecPlan is archived under `prompts/completed/`.

### `build_soils_rq` Stale NoDb Cache Guard (2026-04-28)
**Status**: ✅ **COMPLETE**

**Link**: [docs/work-packages/20260428_build_soils_rq_stale_cache_guard/](docs/work-packages/20260428_build_soils_rq_stale_cache_guard/)

**Lifecycle**: Backlog -> Done (2026-04-28)

**Summary**: Closed the scoped soils RQ stale-cache guard package. `build_soils_rq` now clears only `soils.nodb` cache inside the existing soils directory-root lock callback and immediately before `Soils.getInstance(wd).build()`. Targeted regression coverage asserts cache-clear ordering, scoped key usage, unchanged archive-root rejection before cache clear/hydration, and unchanged success-path status/timestamp order. Required targeted pytest suites, package doc-lint, and `git diff --check` passed; the ExecPlan is archived under `prompts/completed/`.

### RQ WEPP Subwta Precondition Contract Enforcement (2026-04-27)
**Status**: ✅ **COMPLETE**

**Link**: [docs/work-packages/20260427_rq_subwta_precondition_contract/](docs/work-packages/20260427_rq_subwta_precondition_contract/)

**Lifecycle**: Backlog -> In Progress -> Done (2026-04-27)

**Summary**: Closed strict RQ `subwta` precondition enforcement for `run-wepp` and `run-wepp-watershed`. Missing `watershed.subwta` now returns canonical HTTP `409` with `error.code="invalid_watershed_abstraction_state"` before payload mutation, batch/base acknowledgement, or enqueue. Regression coverage locks normal, batch, `_base`, and `checkbox_wepp_watershed=false` behavior for both run endpoints, while `prep-wepp-watershed` keeps its existing missing-`subwta` prep path. Canonical response docs and schema-default error metadata now include the strict contract and recovery notes; required reviewer/QA findings were dispositioned before closure. The ExecPlan is archived under `prompts/completed/`.

### WEPP Runner Traceability Hardening (Hillslope + Watershed) (2026-04-27)
**Status**: ✅ **COMPLETE**

**Link**: [docs/work-packages/20260427_wepp_runner_traceability_hardening/](docs/work-packages/20260427_wepp_runner_traceability_hardening/)

**Lifecycle**: Backlog -> In Progress -> Done (2026-04-27)

**Summary**: Closed the single-rollout traceability package for continuous `run_hillslope` and `run_watershed` only. `run_watershed` now emits startup context parity (`runs_dir`, `run_file`, `err_file`, `cmd`, `attempt=1/1`), both in-scope methods log cached binary identity fields (`binary_path`, SHA256, size, mtime, status/error fallback), and both start a Linux best-effort bounded D-state watchdog controlled by documented env vars. Watershed close-path I/O failures now emit classified `close_path_failure` diagnostics, including `classification=stale_file_handle` for the production NFS signature. Targeted tests cover startup parity, binary identity/fallback, watchdog emit/no-emit behavior, and close diagnostics. Post-closure operator addendum executed in-package: built/vendored `wepp_260427` + `wepp_260427_hill` (provenance recorded as `6bb872ca (dirty tree)`), preserved `-g/-fbacktrace` makefile traceability defaults, synced vendored changelog, and documented dirty-cycle guidance for `pmxelm.inc`/`pmxhil.inc`/`pmxpln.inc`/`pntype.inc`. The ExecPlan is archived under `prompts/completed/`.

### Peridot vs WEPPpy Python Abstraction Benchmark (2026-04-27)
**Status**: ✅ **COMPLETE**

**Link**: [docs/work-packages/20260426_peridot_python_abstraction_benchmark/](docs/work-packages/20260426_peridot_python_abstraction_benchmark/)

**Lifecycle**: Backlog -> In Progress -> Done (2026-04-27)

**Summary**: Closed as a valid comparator-failure benchmark attempt, then updated with a post-close rough benchmark addendum. The package rediscovered the legacy Python comparator as `WatershedAbstraction(topaz_wd, wat_dir)` and the NoDb wrapper path `_topaz_abstract_watershed()`, selected the in-repo `wepppy/_tests/feverish-lamp` TOPAZ fixture, and copied inputs into isolated scratch directories. Initial Python execution failed with a NumPy casting error in `wepppy/topo/watershed_abstraction/support.py::cummnorm_distance()`. The post-close remediation fixed that failure plus legacy channel GeoJSON serialization, then collected rough smoke numbers with exact parity explicitly out of scope: Python mean `2.368s`, Peridot mean `0.162s`, about `14.6x` faster for Peridot on this tiny fixture and command path. The ExecPlan is archived under `prompts/completed/`. Follow-up work remains scoped to fixture curation, parity cleanup, and binary provenance before publication-grade benchmark claims.

### Peridot Runtime Contract Hardening (2026-04-26)
**Status**: ✅ **COMPLETE**

**Link**: [docs/work-packages/20260426_peridot_runtime_contract_hardening/](docs/work-packages/20260426_peridot_runtime_contract_hardening/)

**Lifecycle**: Backlog -> Done (2026-04-26)

**Summary**: Closed cross-repo runtime/schema hardening for Peridot and WEPPpy. Peridot CLI entrypoints now propagate underlying abstraction `io::Result<()>` errors so `abstract_watershed` and `wbt_abstract_watershed` return non-zero on propagated write-stage failures. Peridot `field_flowpaths.csv` now uses unique headers with parent `topaz_id` and flowpath-record `flowpath_topaz_id`. WEPPpy post-processing normalizes new `flowpath_topaz_id` and historical pandas-mangled `topaz_id.1` schemas to canonical `field_flowpaths.parquet` while rejecting ambiguous mixed inputs. Canonical Peridot/WEPPpy docs and package validation artifacts were updated. Follow-up Peridot commit `e09f54c` closed the initially observed support/raster full-suite failures, and local `cargo test` is now clean.

### Peridot Documentation Repositioning and Adoption Visibility (2026-04-26)
**Status**: ✅ **COMPLETE**

**Link**: [docs/work-packages/20260426_peridot_documentation_repositioning/](docs/work-packages/20260426_peridot_documentation_repositioning/)

**Lifecycle**: Backlog -> In Progress -> Done (2026-04-26)

**Summary**: Closed cross-repo documentation repositioning for Peridot. `/home/workdir/peridot/README.md` now frames Peridot as an explicit graph abstraction shift rather than a simple TOPAZ/TOP2WEPP modernization, with replacement boundaries, canonical docs, and communication kit. New Peridot docs cover the watershed output contract, benchmark/claim discipline, prepwepp/TOPAZ migration, and operations validation. WEPPpy references now point to canonical Peridot docs and avoid unqualified speedup claims. Package artifacts record claim provenance, validation, and follow-up runtime/schema gaps.

### NoDb Atomicity + Observability Follow-Ups (RQ Engine) (2026-04-26)
**Status**: ✅ **COMPLETE**  
**Link**: [docs/work-packages/20260425_nodb_atomicity_observability_followups_a/](docs/work-packages/20260425_nodb_atomicity_observability_followups_a/)  
**Lifecycle**: Backlog -> In Progress -> Done (2026-04-26)  
**Summary**: Closed end-to-end across six milestones. Delivered scoped cross-controller grouped-update atomicity hardening, queue-graph baseline cleanup (`wctl check-rq-graph` clean with regenerated canonical artifacts), post-enqueue WEPP hint persistence boundary hardening (including lock-contention and non-`RuntimeError` fault paths with contract-safe behavior), lock/dump-efficiency observability guard coverage, and scoped test maintainability cleanup (shared WEPP payload doubles + less brittle assertions). Required `reviewer`/`qa_reviewer`/`security_reviewer` triad reviews were run after each milestone; all Medium/High findings were remediated before progression. Closure validation passed (`228 passed`, `0 failed`) and enforcement gates were clean (`wctl check-rq-graph`, `check_broad_exceptions --enforce-changed`). Post-close addendum documents and remediates a discovered `_wepp_bin` rollback regression in NoDb Redis cache signature handling (`ada260d79`).

### NoDb Lock/Dump Efficiency Refactor (RQ Engine) (2026-04-25)
**Status**: ✅ **COMPLETE**  
**Link**: [docs/work-packages/20260425_nodb_lock_dump_efficiency_refactor/](docs/work-packages/20260425_nodb_lock_dump_efficiency_refactor/)  
**Lifecycle**: Backlog -> In Progress -> Done (2026-04-25)  
**Summary**: Closed end-to-end with all scoped rq-engine lock/dump hotspots converted to grouped single-lock mutation flows: `wepp_run_payload.py`, `watershed_routes.py`, `landuse_routes.py`, `upload_batch_runner_routes.py`, `wepp_routes.py`, and `bootstrap_routes.py`, with required NoDb helper additions in `Soils`, `Watershed`, `Landuse`, `Disturbed`, `BatchRunner`, and `Wepp.persist_job_hint(...)`. Per-milestone `reviewer`/`qa_reviewer`/`security_reviewer` loops were executed and all Medium findings were remediated before progression; remaining findings are Low-only residual notes. Targeted validation passed across scoped suites (`198 passed`), and `wctl check-rq-graph` was executed with documented pre-existing drift while no queue-wiring files were changed in this package. ExecPlan was archived under `prompts/completed/`.

### Landuse/Disturbed MOFE Pipeline Optimization (`apprehensive-caw`) (2026-04-25)
**Status**: ✅ **COMPLETE**  
**Link**: [docs/work-packages/20260424_landuse_disturbed_mofe_pipeline_optimization/](docs/work-packages/20260424_landuse_disturbed_mofe_pipeline_optimization/)  
**Lifecycle**: Backlog -> In Progress -> Done (2026-04-25)  
**Summary**: Closed end-to-end with all three prioritized lanes implemented and validated. Lane 1 consolidated duplicate heavy `build_managements()` work in the DOMLC landuse/disturbed chain via explicit deferred-rebuild contract (`Landuse.build()` scoped deferral); Lane 2 compacted remap/MOFE hot-loop INFO logging to summary lines while preserving warning/error diagnostics and DEBUG detail; Lane 3 added guarded same-cycle MOFE pair-count reuse with explicit signature checks and invalidation (`build-cycle reset` + `signature drift`). Targeted lane regression suites passed (`42 passed`) across touched landuse/disturbed modules. Required benchmark/parity artifacts were regenerated using isolated temp directories with no source-run mutation under `/wc1/runs/ap/apprehensive-caw/`; parity status is `match` for all lanes and benchmark summary includes per-lane baseline/optimized mean/stddev and percent deltas. Code/QA/security review artifacts are closed with no unresolved medium/high findings, and the ExecPlan is archived under `prompts/completed/`.

### Controllers-GL Cache Hardening Rollout (2026-04-24)
**Status**: ✅ **COMPLETE**  
**Link**: [docs/work-packages/20260424_controllers_gl_cache_hardening/](docs/work-packages/20260424_controllers_gl_cache_hardening/)  
**Lifecycle**: Backlog -> In Progress -> Done (2026-04-24)  
**Summary**: Closed end-to-end with include-hygiene hardening for all WEPPcloud templates that load `controllers-gl.js`. Inventory/remediation covered 19 templates across `wepppy/weppcloud/templates/**` and `wepppy/weppcloud/routes/**`; every include now uses `static_url('js/controllers-gl.js')` and immediately loads `controllers_gl_stale_check.js` after it while preserving local script order and existing defer/non-defer behavior. Regression coverage was expanded in `tests/weppcloud/test_stale_controllers_gl_template_wiring.py` to assert inventory-wide invariants. Required validations passed (`46` pytest render tests, stale-check Jest suite `9/9`, targeted template wiring pytest `26` passed), and both package review gates (`artifacts/2026-04-24_code_review.md`, `artifacts/2026-04-24_qa_review.md`) closed with no unresolved medium/high findings.

### RQ Worker Startup and NoDb Redis Cache Hardening (Retroactive) (2026-04-24)
**Status**: ✅ **COMPLETE**  
**Link**: [docs/work-packages/20260424_rq_worker_nodb_cache_hardening/](docs/work-packages/20260424_rq_worker_nodb_cache_hardening/)  
**Lifecycle**: Retroactive capture -> Done (2026-04-24)  
**Summary**: Captures completed incident-response hardening for repeated `Redis NoDb cache client is unavailable` failures impacting landuse mapping jobs. Closed scope includes: safe reconnect semantics for NoDb lock/cache Redis clients, lock-token ownership enforcement before `dump()` persistence, removal of foreign-lock force-unlock fallback, worker startup gating via `docker/rq-worker-startup.sh` (readiness probe + configurable delay), compose hardening for prod and worker-only stacks (`RQ_REDIS_URL` fail-fast contract, `REDIS_URL` alignment, `weppcloudr` health dependency), and regression/doc updates. Two review rounds were executed with code/QA/security artifacts; all medium/high findings were dispositioned and targeted validation passed (`61` pytest tests, compose config checks, doc-lint clean). Lifecycle-standard alignment is now explicit in package docs (hypotheses/signals, Redis NoDb cache connection strategy, and callus sunset checkpoints), with a post-close observation window through **2026-05-24** and softening review checkpoint on **2026-05-25**.

### Landuse Legacy Flask State Route Removal (Post Gate 3) (2026-04-24)
**Status**: ✅ **COMPLETE**  
**Link**: [docs/work-packages/20260424_landuse_legacy_flask_state_route_removal/](docs/work-packages/20260424_landuse_legacy_flask_state_route_removal/)  
**Lifecycle**: Backlog -> In Progress -> Done (2026-04-24)  
**Summary**: Closed end-to-end with deprecated Flask landuse compatibility machine/state routes removed from `wepppy/weppcloud/routes/nodb_api/landuse_bp.py`, including `set_landuse_mode`, `set_landuse_db`, `modify_landuse_coverage`, `modify_landuse_mapping`, user-defined catalog mutators/read route, landuse-map snapshot/save/clear routes, and `modify_landuse`. WEPPcloud render routes stayed in WEPPcloud (`/report/landuse`, `/landuse-user-defined`, `/landuse-map`) and passed render-route validation. Production in-repo callers no longer target removed Flask endpoints; route/docs/schema ownership now reflects rq-engine-only machine/state APIs. Post-closure remediations include Finder metadata sidecar tolerance for `landuse-user-defined/upload`, shared page-shell title styling for the landuse catalog/map pages, stale system custom-map reference recovery, a root-cause clean-path fix so `build_landuse` preserves run-scoped `landuse/user-defined/` + `landuse/landuse_user_defined_mapping.json`, a `run_0` render-path recovery boundary so stale system map references do not make projects unloadable (`500`), a stale-write race closure so stale-system-map cleanup on unlocked reads is in-memory-only with explicit `run_0` stale-write retry coverage, custom-map description integrity remediation so changed assignments normalize management labels (for example key `43` surfaces as `Moderate Severity Fire`) instead of stale base-map descriptions, title-row parity updates so both landuse editor pages expose the run-home `runid` link left of `wc-control__title`, and map-description edit/save parity so `/landuse-map` description edits persist through save/reload/report paths. A final cross-package code/QA/security disposition pass closed additional actionable findings (mapping-selection allowlist hardening, unknown token-class denial, map-path redaction, and `landuse-map/save` `428`/header-body precondition contract parity). Required validation suite passed (`22 + 46 + 50 + 54 + 10` pytest results, plus `32` auth-route pytest, `20 + 3 + 2` Jest results, doc-lint clean), and dedicated security review closed with no unresolved medium/high findings.

### Landuse Phase 3 Hardening Parity Tests and Migration Gate (2026-04-24)
**Status**: ✅ **COMPLETE**  
**Link**: [docs/work-packages/20260424_landuse_phase3_hardening_parity_tests/](docs/work-packages/20260424_landuse_phase3_hardening_parity_tests/)  
**Lifecycle**: Backlog -> In Progress -> Done (2026-04-24)  
**Summary**: Closed end-to-end with Gate 3 pass criteria met. Baseline WEPPcloud hardening behavior is now explicitly frozen for all required matrix rows (path containment, archive/member policy, upload boundaries/conflicts, optimistic concurrency, invalid-row validation, and rollback). Deferred Phase 3 landuse surfaces now have rq-engine parity implementations and tests: user-defined catalog upload/list/delete/update-description, landuse map snapshot/save/clear-override, and `modify-landuse`. Browser transport for moved surfaces uses session-token bridge bearer flow (`requestWithSessionToken`) with no cookie-mutation fallback on rq-engine mutators, while render routes remain in WEPPcloud (`/report/landuse`, `/landuse-user-defined`, `/landuse-map`). Required validation suite passed (`24 + 39 + 54 + 10` pytest results, `20 + 3` Jest results, doc-lint clean), and dedicated security review closed with no unresolved medium/high findings.

### Landuse First-Class Agent Interface Migration (Phased rq-engine Cutover) (2026-04-24)
**Status**: ✅ **COMPLETE**  
**Link**: [docs/work-packages/20260423_landuse_first_class_agent_interface_migration/](docs/work-packages/20260423_landuse_first_class_agent_interface_migration/)  
**Lifecycle**: Backlog -> In Progress -> Done (2026-04-24)  
**Summary**: Closed with phased gate execution and no render-route migration. Gate 0 decisions were finalized before code changes (PUP/active-root strategy, token-class/scope policy, browser transport strategy). Phase 1 shipped first-class rq-engine replacements for `set-landuse-mode`, `set-landuse-db`, and `modify-landuse-coverage`, and WEPPcloud browser callers were cut over to `requestWithSessionToken`. Phase 2 shipped `GET /api/runs/{runid}/{config}/controllers/landuse/state` and endpoint-catalog/openapi parity for migrated landuse operations (including existing `modify-landuse-mapping` discoverability gap closure). Phase 3 map/catalog/file surfaces remained in WEPPcloud by explicit no-go gate policy. Legacy Flask compatibility/deprecation policy is documented with a no-delay removal posture and explicit sunset criteria. Required JS tests passed; required pytest suites passed under `.venv/bin/pytest` fallback due repeated `wctl run-pytest` exit `137` in this environment; contract/package docs lint passed.

### Landuse User-Defined Management Catalog + Mapping Editor (2026-04-24)
**Status**: ✅ **COMPLETE**  
**Link**: [docs/work-packages/20260423_landuse_user_defined_management_catalog_map/](docs/work-packages/20260423_landuse_user_defined_management_catalog_map/)  
**Summary**: Closed end-to-end with two new PowerUser workflows: `Landuse User-Defined` catalog and `Landuse Map` editor. Shipped run-scoped `.man`/`.zip` catalog ingest with hardened archive/member/size constraints, metadata CRUD, and all-or-nothing install behavior under `landuse/user-defined/`. Shipped mapping snapshot/save/clear APIs with optimistic concurrency (`X-If-Match-Sha256`) and atomic persistence to `landuse/landuse_user_defined_mapping.json`. `Landuse` NoDb now prefers configured run-local custom maps via `custom_mapping_relpath` and raises explicit typed errors for missing/invalid configured custom maps; `load_map()` now supports explicit JSON mapping paths for run-local resolution. Targeted validations passed (`86 passed` across touched suites), package doc lint passed (`5 files validated, 0 errors, 0 warnings`), and dedicated security review closed with no unresolved medium/high findings.

### Landuse Batched Mapping Submit UX (Single + Multi-OFE) (2026-04-24)
**Status**: ✅ **COMPLETE**  
**Link**: [docs/work-packages/20260423_landuse_batched_mapping_submit/](docs/work-packages/20260423_landuse_batched_mapping_submit/)  
**Summary**: Closed end-to-end with staged landuse mapping submit UX and batched backend processing. Landuse report mapping selects now stage edits locally with a dedicated secondary apply button and live staged-count messaging; one submit posts canonical `mappings[]` payload to `/rq-engine/api/runs/{runid}/{config}/modify-landuse-mapping`. rq-engine now validates + normalizes batch edits (including legacy `dom/newdom` compatibility), removes mapping `depends_on` chaining, and enqueues a single mapping job. `modify_landuse_mapping_rq` now applies normalized batches deterministically under one landuse maintenance-lock window with one completion trigger and pre-mutation validation/rollback safeguards. Post-review disposition closed actionable code/QA findings (lock-gate stale completion short-circuit, null-key validation, readonly/inflight UI guards, and stub parity). Targeted validations passed: microservice route tests (`19 passed`), RQ mutation-guard tests (`23 passed`), controller Jest suite (`20 passed`), and package doc-lint (`0 errors`).

### Landuse Multi-OFE Build Optimization (Lookup/Pass/IO/Logging) (2026-04-23)
**Status**: ✅ **COMPLETE**  
**Link**: [docs/work-packages/20260423_landuse_multi_ofe_build_optimization/](docs/work-packages/20260423_landuse_multi_ofe_build_optimization/)  
**Summary**: Closed end-to-end with multi-OFE landuse optimization in `wepppy/nodb/core/landuse.py`: SBS burn-remap management-summary reuse, duplicate-pass collapse in `Landuse.build()` multi-OFE path, explicit first-pass guard behavior (`domlc_mofe_d` cleared pre-build and MOFE pair-count work skipped when assignment map is missing/empty), and reduced high-volume info logging via compact summaries/debug placement. Added targeted regression coverage for SBS remap parity + lookup reuse, build/event contract preservation, first-pass no-op guard behavior, and logging behavior (`14 passed` across touched landuse suites). Required benchmark/parity artifacts were regenerated on isolated temp copies for all five required runs; contract parity status is `match` on all runs.

### MOFE `.mofe.man` Synthesis Process-Pool Migration (2026-04-23)
**Status**: ✅ **COMPLETE**  
**Link**: [docs/work-packages/20260423_mofe_man_synthesis_process_pool/](docs/work-packages/20260423_mofe_man_synthesis_process_pool/)  
**Summary**: Closed end-to-end with canonical `.mofe.man` synthesis orchestration in `wepppy/nodb/core/landuse.py::_build_multiple_ofe()`: spawn-first `createProcessPoolExecutor`, `BrokenProcessPool` fork retry, bounded sequential fallback, explicit non-pool exception raising, deterministic `hill_<topaz_id>.mofe.man` basename validation, and bounded batched worker fan-out (`max_workers <= 4`). Added targeted landuse tests for success/retry/fallback/non-pool-failure/parity behavior (`10 passed`) and regenerated required benchmark/parity artifacts on isolated temp copies of the five benchmark runs. Parity matched on all runs (`0` mismatches); benchmark deltas on this host remained positive (`+143.18%`, `+443.51%`, `+34.05%`, `+63.58%`, `+286.34%`), so the package closes on explicit contract/parity evidence rather than a speedup claim. Review artifacts closed with no unresolved medium/high findings; ExecPlan archived under `prompts/completed/`.

### Multi-OFE Landuse Pair-Count Optimization via wepppyo3 Raster Characteristics (2026-04-23)
**Status**: ✅ **COMPLETE**  
**Link**: [docs/work-packages/20260423_mofe_landuse_pair_counts_wepppyo3/](docs/work-packages/20260423_mofe_landuse_pair_counts_wepppyo3/)  
**Summary**: Closed end-to-end with new production API `wepppyo3.raster_characteristics.count_intersecting_raster_key_pairs` (explicit read/shape failure contracts), canonical release export update (`release/linux/py312`), and WEPPpy `Landuse.build_managements()` multi-OFE area path cut over from repeated pairwise `np.where` scans to Rust one-pass pair counts while preserving area/pct semantics and failure propagation. Validation passed in both repos (`cargo test -p raster_characteristics_rust`: `2 passed`; wepppyo3 raster-characteristics pytest: `5 passed`; targeted WEPPpy gates: `9 passed` across landuse/daymet/omni suites). Benchmark/parity artifacts were captured on the required five-run matrix in isolated temp dirs: parity `match` on all runs; timing deltas were `-88.67%`, `+144.42%`, `-96.34%`, `-95.41%`, `-67.56%` (the positive delta is the required non-MOFE run `objectionable-sublimate`, executed with documented synthetic isolated MOFE map + derived single-segment pairing due missing source MOFE inputs).

### MOFE Map Migration to wepppyo3 (Topaz Pre-Index + One-Pass Rank Assignment) (2026-04-23)
**Status**: ✅ **COMPLETE**  
**Link**: [docs/work-packages/20260423_mofe_map_wepppyo3/](docs/work-packages/20260423_mofe_map_wepppyo3/)  
**Summary**: Closed end-to-end with MOFE map assignment production behavior moved from WEPPpy Python loops to `wepppyo3.watershed_abstraction.assign_mofe_map` (new crate/module), keeping explicit fallback/repair contracts and contiguous-id guarantees. WEPPpy `_build_mofe_map` now delegates to the Rust path via strict loader `wepppy/topo/watershed_abstraction/mofe_map.py`; legacy Python assignment remains available only as parity oracle helper (`_build_mofe_map_labels_python_legacy`) and is not used as silent fallback. Validation artifacts captured on `/wc1/runs/po/pointy-toed-fluff` subset (`200` hillslopes, isolated temp dirs): parity `mismatch_count=0`; benchmark (6 alternating samples) old mean `65.949408s`, new mean `0.282354s`, `-99.57%`. Targeted gates passed in both repos (`cargo test -p watershed_abstraction_rust`, wepppyo3 pytest, WEPPpy targeted `wctl run-pytest`). Broad WEPPpy sweep (`wctl run-pytest tests --maxfail=1`) surfaced one unrelated existing failure in `tests/nodb/test_wepp_run_service.py::test_run_watershed_does_not_rewrite_wepp_50k_bin`.

### Segmented MOFE Migration to wepppyo3 + Process-Pool Refactor (2026-04-23)
**Status**: ✅ **COMPLETE**  
**Link**: [docs/work-packages/20260422_segmented_multiple_ofe_wepppyo3_pool/](docs/work-packages/20260422_segmented_multiple_ofe_wepppyo3_pool/)  
**Summary**: Closed end-to-end with MOFE segmentation production behavior moved to wepppyo3 (`wepp_interchange.segment_single_ofe_slope`), WEPPpy `SlopeFile.segmented_multiple_ofe` hard-switched to Rust path, and legacy Python segmentation retained only behind explicit deprecation (`segmented_multiple_ofe_legacy`). Refactored `WatershedOperationsMixin._build_multiple_ofe` to canonical spawn-first process-pool orchestration with fork retry on `BrokenProcessPool`, bounded sequential fallback, and explicit non-pool failure raising. Validation artifacts captured on `/wc1/runs/po/pointy-toed-fluff`: parity (`3345` files checked, `0` mismatches) and alternating benchmark (old mean `2.148501s`, new mean `0.938375s`, `-56.32%`). Targeted test suites passed (`wepppyo3`: `8 passed`; WEPPpy: `17 passed` via direct local pytest while `wctl` execution was blocked by stopped `weppcloud` compose service). ExecPlan archived under `prompts/completed/` with outcome note.

### Peridot Side-Hillslope Length Capping + Provenance Mode (2026-04-23)
**Status**: ✅ **COMPLETE**  
**Link**: [docs/work-packages/20260422_peridot_side_hillslope_length_capping/](docs/work-packages/20260422_peridot_side_hillslope_length_capping/)  
**Summary**: Closed with side-hillslope length capping delivered in both Peridot abstraction paths (`L_final = min(L_area, L_edge)` for side hillslopes), area-preserving width recomputation, unchanged top/source behavior, and additive hillslope provenance fields (`length_estimate_mode`, `length_area_over_channel`, `length_edge_median`). Peridot tests and schema/manifest checks passed, WEPPpy contract docs were updated, and ExecPlan artifacts were archived under `prompts/completed/`.

### Disturbed MOFE 9002 Soil Support Parity (2026-04-22)
**Status**: ✅ **COMPLETE**  
**Link**: [docs/work-packages/20260421_disturbed_mofe_9002_soils/](docs/work-packages/20260421_disturbed_mofe_9002_soils/)  
**Summary**: Completed end-to-end with an explicit MOFE `sol_ver=9002` contract locked to single-OFE reference semantics for lookup hits and a documented MOFE-specific lookup-miss deviation required by same-version MOFE stack synthesis. Implemented minimal `Disturbed.modify_mofe_soils` update so `9002` lookup misses remain class-aware (`mukey-texid-disturbed_class`) while preserving explicit fallback replacements (`luse`, `stext`, `ksatfac=0.0`, `ksatrec=0.0`). Added MOFE `9002` regression coverage for lookup-hit, lookup-miss, treatment-suffix normalization, class-keying, and area/pct recomputation. Required gates passed: disturbed single+MOFE tests (`17 passed`), lookup contract tests (`30 passed`), soil util tests (`49 passed`). Config-level check against `disturbed9002-10-mofe.cfg` confirmed `disturbed.sol_ver=9002.0` and `wepp.multi_ofe=true` flag presence.

### Geneva Interactive Summary Report (Retroactive) (2026-04-18)
**Status**: ✅ **COMPLETE**  
**Link**: [docs/work-packages/20260418_geneva_interactive_summary_report/](docs/work-packages/20260418_geneva_interactive_summary_report/)  
**Summary**: Recorded retroactive closure for the completed Geneva summary report upgrade. Work shipped interactive `/query/geneva/summary` and `/report/geneva/summary` contracts (filters/options/chart metadata/selected storm/event table), canonical Pure report rendering, marker-to-table linkage, and review-driven hardening (stale-summary suppression, payload sanitization, `no-store` response headers). Follow-on runtime fixes ensured `_base_report.htm` shell dependencies are always provided (`ron`, `current_ron`, `unitizer_nodb`, `precisions`), and regression coverage was updated accordingly.

### Iterative First-Order Link Prune WP-10 WEPPpy E2E Cutover (2026-04-14)
**Status**: ✅ **COMPLETE**  
**Link**: [docs/work-packages/20260414_ifolp_wp10_wepppy_e2e_cutover/](docs/work-packages/20260414_ifolp_wp10_wepppy_e2e_cutover/)  
**Summary**: Closed WP-10 end-to-end with WEPPpy IFOLP cutover behavior: default stream-pruning method is `ifolp`, explicit legacy mode `remove_short_streams` remains selectable, and IFOLP call-site explicitly passes `max_junctions=3`. Completed watershed/rq-engine/UI method plumbing (state defaults, payload validation, schema-default reporting, controller/template propagation), added method-matrix assertions for both pruning paths, and executed required gates: `wctl run-pytest tests/microservices/test_rq_engine_watershed_routes.py` (`36 passed`), `wctl run-pytest tests/rq/test_project_rq_mutation_guards.py` (`11 passed`), `wctl run-pytest tests/topo/test_terrain_processor_wbt_integration.py` (`4 passed`), `wctl run-pytest tests/culverts/test_culvert_batch_rq.py` (`4 passed`), `wctl run-npm lint`, `wctl run-npm test` (`76 suites`, `509 tests`). Review disposition closed with no unresolved high/medium findings; ExecPlan archived under `prompts/completed/`.

### Iterative First-Order Link Prune WP-09 Max Junctions Support (2026-04-14)
**Status**: ✅ **COMPLETE**  
**Link**: [docs/work-packages/20260414_ifolp_wp09_max_junctions_support/](docs/work-packages/20260414_ifolp_wp09_max_junctions_support/)  
**Summary**: Closed WP-09 end-to-end with IFOLP `--max_junctions` support in `weppcloud-wbt` (Rust tool contract + Phase B behavior + parser/phase tests + both Python wrappers), retained omitted-argument baseline behavior, and deterministic explicit `--max_junctions=3` validation. Required gates passed: `cargo check -p whitebox_tools`; `cargo test -p whitebox_tools iterative_first_order_link_prune -- --nocapture` (`77 passed`, `0 failed`); `python -m py_compile whitebox_tools.py WBT/whitebox_tools.py`. Parity/regression artifacts for omitted and `max_junctions=3` modes on run1/run2 matched retained canonical hash `920cc1612bd677a1f8dab935a521f6270e226bf961fd5f72ca770b32cd134c83`, with no-arg artifacts byte-identical to retained baseline canonicals and `max_junctions=3` deterministic across reruns. WEPPpy integration planning now explicitly requires `max_junctions=3`; review disposition closed with no unresolved high/medium findings; ExecPlan archived under `prompts/completed/`.

### Iterative First-Order Link Prune WP-08 WBT Wrapper Exposure + Release Readiness (2026-04-13)
**Status**: ✅ **COMPLETE**  
**Link**: [docs/work-packages/20260413_ifolp_wp08_wrapper_release_readiness/](docs/work-packages/20260413_ifolp_wp08_wrapper_release_readiness/)  
**Summary**: Closed WP-08 with wrapper-surface release readiness and retained-baseline parity stability. Added `iterative_first_order_link_prune` to both Python wrapper surfaces (`whitebox_tools.py`, `WBT/whitebox_tools.py`), validated CLI/wrapper contract checks (`--listtools`, `--toolhelp=IterativeFirstOrderLinkPrune`, missing required args, threshold-pair validation), and passed required gates (`cargo check -p whitebox_tools`, targeted IFOLP tests `51 passed`, `0 failed`, wrapper `py_compile`). Parity spot checks on `/tmp/ifolp_wp05_remediate/run1` and `run2` produced canonical hash `920cc1612bd677a1f8dab935a521f6270e226bf961fd5f72ca770b32cd134c83`, byte-identical to retained `parity-report.final_effective.canonical.json` artifacts. Review disposition closed with no unresolved high/medium findings.

### Iterative First-Order Link Prune WP-07 Optimization Pass (2026-04-13)
**Status**: ✅ **COMPLETE**  
**Link**: [docs/work-packages/20260413_ifolp_wp07_optimization_pass/](docs/work-packages/20260413_ifolp_wp07_optimization_pass/)  
**Summary**: Closed WP-07 with bounded topology optimization and preserved retained behavior. Performance deltas (5 repeats, run1 fixtures): `blackwood_60_5` `0.046s -> 0.042s` (-8.70%), `clueless_aftertaste_anchor_10_100` `0.020s -> 0.020s` (0.00%), `gatecreek_10m_30_2` `0.750s -> 0.706s` (-5.87%). Parity-regression canonical hash remained `920cc1612bd677a1f8dab935a521f6270e226bf961fd5f72ca770b32cd134c83` on run1/run2 and matched retained baseline artifacts. Required gates passed: `cargo check -p whitebox_tools`; targeted IFOLP suite passed (`51 passed`, `0 failed`). Review disposition recorded no unresolved high/medium findings.

### Iterative First-Order Link Prune WP-06 Error Contract + Robustness Hardening (2026-04-13)
**Status**: ✅ **COMPLETE**  
**Link**: [docs/work-packages/20260413_ifolp_wp06_error_contract_robustness_hardening/](docs/work-packages/20260413_ifolp_wp06_error_contract_robustness_hardening/)  
**Summary**: Closed WP-06 with bounded hardening only (no pruning-semantic changes). Added explicit non-finite numeric rejection in parser and threshold-table values, duplicate threshold-code detection, and finite/non-negative boundary guards across Phase A/Phase B/topology inputs. Required gates passed: `cargo check -p whitebox_tools`; `cargo test -p whitebox_tools iterative_first_order_link_prune -- --nocapture` (`50 passed; 0 failed`). Parity-regression reruns on `/tmp/ifolp_wp05_remediate/run1` and `run2` produced stable canonical hash `920cc1612bd677a1f8dab935a521f6270e226bf961fd5f72ca770b32cd134c83` and were byte-identical to retained `parity-report.final_effective.canonical.json` artifacts (no retained-state drift). No unresolved high/medium findings.

### Iterative First-Order Link Prune WP-05 TopAZ Parity Validation (2026-04-14)
**Status**: ✅ **COMPLETE**  
**Link**: [docs/work-packages/20260413_ifolp_wp05_topaz_parity_validation/](docs/work-packages/20260413_ifolp_wp05_topaz_parity_validation/)  
**Summary**: Closed WP-05 with stakeholder-accepted effective parity equivalence. Retained IFOLP state includes H-002 + H-009 + H-010 + H-011; anchor fixture reached exact parity and non-anchor residuals were accepted low-severity after provenance-aligned probe evidence. Current retained artifact canonical hash is `920cc1612bd677a1f8dab935a521f6270e226bf961fd5f72ca770b32cd134c83` (run1/run2 stable; historical governance token `07e351...` retained in older WP-05 records). Final gates passed: `cargo check -p whitebox_tools`; `cargo test -p whitebox_tools iterative_first_order_link_prune -- --nocapture` (`43 passed; 0 failed`). Remaining parity work must treat this retained IFOLP state as the baseline unless a new work package explicitly revises the baseline.

### Iterative First-Order Link Prune WP-04 First-Order-Link Pruning (2026-04-13)
**Status**: ✅ **COMPLETE**  
**Link**: [docs/work-packages/20260413_ifolp_wp04_first_order_link_pruning/](docs/work-packages/20260413_ifolp_wp04_first_order_link_pruning/)  
**Summary**: Completed WP-04 end-to-end in `/workdir/weppcloud-wbt` with Phase B pruning behavior in companion module `iterative_first_order_link_prune_phase_b.rs`. Implemented deterministic receiver-group shortest-link selection with strict epsilon improvement, immediate prune mutation (receiver-preserving normal case + self-receiver terminal special case), stale-candidate skip, degeneration-driven repass cadence with deterministic termination, and single-link parity guard behavior. Tool orchestration now executes Phase A -> Phase B and writes final binary output raster + metadata. Required gates passed: `cargo check -p whitebox_tools`; `cargo test -p whitebox_tools iterative_first_order_link_prune -- --nocapture` (`39 passed; 0 failed`). Review findings were dispositioned with no unresolved high/medium issues; ExecPlan archived under `prompts/completed/`.

### Iterative First-Order Link Prune WP-03 Source-Area Qualification (2026-04-13)
**Status**: ✅ **COMPLETE**  
**Link**: [docs/work-packages/20260413_ifolp_wp03_source_area_qualification/](docs/work-packages/20260413_ifolp_wp03_source_area_qualification/)  
**Summary**: Completed WP-03 end-to-end in `/workdir/weppcloud-wbt` with Phase A source-area qualification behavior in companion module `iterative_first_order_link_prune_phase_a.rs`. Implemented minimum-CSA provisional masking, row-major inline source-walk mutation, receiver transitions (junction collapse and terminal receiver recheck), and stabilization reclassification, then wired Phase A into tool orchestration while keeping the WP-04 Phase B boundary explicit via unsupported placeholder. Required gates passed: `cargo check -p whitebox_tools`; `cargo test -p whitebox_tools iterative_first_order_link_prune -- --nocapture` (`33 passed; 0 failed`). Review findings were dispositioned with no unresolved high/medium issues; ExecPlan archived under `prompts/completed/`.

### Iterative First-Order Link Prune WP-02 Topology Kernel (2026-04-13)
**Status**: ✅ **COMPLETE**  
**Link**: [docs/work-packages/20260412_ifolp_wp02_topology_kernel/](docs/work-packages/20260412_ifolp_wp02_topology_kernel/)  
**Summary**: Completed WP-02 end-to-end in `/workdir/weppcloud-wbt` with deterministic topology-kernel primitives and companion tests. Implemented Whitebox/ESRI pointer decode + neighbor traversal, topology classification + receiver detection, deterministic first-order-link discovery order, and stale-candidate validity checks. Dispositioned review findings (terminal-head half-cell behavior, stream-mask geometry validation for inflow counts, non-negative epsilon clamp + parser rejection of negative epsilon) and expanded synthetic-grid coverage for inflow/state/order/tie/stale behavior. Required gates passed: `cargo check -p whitebox_tools`; `cargo test -p whitebox_tools iterative_first_order_link_prune -- --nocapture` (`28 passed; 0 failed`). WP-02 row in WBT implementation plan marked `done` with review/test fields complete; ExecPlan archived under `prompts/completed/`.

### Iterative First-Order Link Prune WP-01 Tool Scaffolding (2026-04-13)
**Status**: ✅ **COMPLETE**  
**Link**: [docs/work-packages/20260412_ifolp_wp01_tool_scaffolding/](docs/work-packages/20260412_ifolp_wp01_tool_scaffolding/)  
**Summary**: Completed WP-01 tool scaffolding in `/workdir/weppcloud-wbt` with IFOLP command creation, registry wiring (`stream_network_analysis/mod.rs`, `tools/mod.rs`), parser/default/help contract implementation, and targeted parser/registration/placeholder tests (`13 passed`). Parser tests were split into companion module `iterative_first_order_link_prune_parser_tests.rs` to keep tool source maintainable and non-monolithic.

### Iterative First-Order Link Prune WP-00 Parity Harness (2026-04-13)
**Status**: ✅ **COMPLETE**  
**Link**: [docs/work-packages/20260412_ifolp_wp00_parity_harness/](docs/work-packages/20260412_ifolp_wp00_parity_harness/)  
**Summary**: Completed WP-00 end-to-end for IFOLP in `/workdir/weppcloud-wbt`. Delivered checksum-pinned fixture catalog and oracle manifest, parity metric specification, deterministic rerun report, and reusable harness utilities (`ifolp_wp00_prepare_fixtures.py`, `ifolp_wp00_run_topaz_oracle.sh`, `ifolp_wp00_compare_outputs.py`). Required anchor fixture `/wc1/runs/cl/clueless-aftertaste/dem/wbt` was included. WP-00 orchestration row in WBT implementation plan is `done` with review/test/parity gates complete; deterministic canonical hash matched across reruns.

### Upload Boundary Helpers Unification (2026-04-12)
**Status**: ✅ **COMPLETE**  
**Link**: [docs/work-packages/20260412_upload_boundary_helpers_unification/](docs/work-packages/20260412_upload_boundary_helpers_unification/)  
**Summary**: Unified non-ZIP upload boundary logic behind canonical helpers in `wepppy/microservices/upload_boundary.py` and migrated duplicated helper stacks out of `wepppy/microservices/rq_engine/ash_routes.py`, `wepppy/microservices/rq_engine/omni_routes.py`, and `wepppy/weppcloud/routes/nodb_api/roads_bp.py` via `upload_helpers.py` compatibility paths. Preserved per-endpoint caps/allowlists and status semantics (including explicit `413` oversize mapping), added helper and route parity regressions for extension/size behavior, and documented helper ownership in `docs/schemas/upload-endpoint-contract.md`. ZIP canonical controls remained anchored to `wepppy/microservices/shape_converter/archive_validation.py`; culvert semantic validation ownership remained in `wepppy/microservices/culvert_payload_validator.py`. Validation gates passed (`137` targeted tests; full suite `3511 passed`, `36 skipped`) and the dedicated security artifact closed with no unresolved medium/high findings.

### Upload Endpoints Hardening (2026-04-12)
**Status**: ✅ **COMPLETE**  
**Link**: [docs/work-packages/20260411_upload_endpoints_hardening/](docs/work-packages/20260411_upload_endpoints_hardening/)  
**Summary**: Completed scoped non-`shape_converter` upload hardening end-to-end. Culvert ZIP ingestion now reuses validated archive controls from `wepppy/microservices/shape_converter/archive_validation.py` (read-with-limit, safe member validation, controlled extraction), while keeping culvert semantic payload checks in `wepppy/microservices/culvert_payload_validator.py`. Added explicit pre-write size/type enforcement for `upload_huc_fire`, batch-runner geojson+sbs uploads, landuse/treatments user-defined uploads, disturbed SBS uploads, and Roads GeoJSON upload route. Upload-facing error payloads for scoped endpoints no longer leak traceback internals and remain canonical. Regression coverage now includes ZIP abuse fixtures (traversal, encrypted, nested archive, unsupported compression, duplicate paths, quota) and endpoint size/type checks. Validation gates passed (`76` targeted tests; full suite `3502 passed`, `36 skipped`), and the dedicated security review artifact closed with no unresolved medium/high findings.

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
- [docs/work-packages/20260403_roads_map_drilldown/](docs/work-packages/20260403_roads_map_drilldown/) — Complete; ExecPlan archived (implementation completed 2026-04-04, lifecycle verified 2026-04-28)
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
- **Current**: 5 packages
- **Target**: 2-4 packages
- **Status**: above target (additive package load; prioritize closure sequencing)

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
