# PROJECT_TRACKER.md
> Kanban board for wepppy work packages and vision items

**Last Updated**: 2025-10-26  
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

**Current WIP**: 3 packages

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

### High-Contrast Dark Mode
**Proposed**: 2025-10-27  
**Size**: Small (5 minutes initial, <1 day validation)  
**Priority**: Medium (user experience win with minimal effort)  
**Description**: Add high-contrast dark mode via CSS media query. Pure grayscale inversion—no color decisions, no theme maintenance burden.

**Scope**:
- Add `@media (prefers-color-scheme: dark)` block to `ui-foundation.css`
- Flip existing color tokens (white→dark gray, black→white)
- Keep accent colors same (green/yellow/red work in both modes)
- One-time smoke test to verify readability
- Zero ongoing maintenance (tokens auto-adapt)

**Strategic Value**: 
- Users get dark mode preference with zero aesthetic bikeshedding
- Developer spends ~5 minutes, never thinks about it again
- Grayscale means no color coordination needed
- Reinforces "zero time on UI aesthetics" philosophy

**Dependencies**: None (current token architecture already supports this)

**Next Steps**: Create work package when developer has 5 minutes; optional contrast ratio validation script for WCAG AA compliance

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

## 🚧 In Progress

Currently active work packages. Limit to 2-4 packages to maintain focus.

**Current WIP Count**: 4 packages

---

### UI Style Guide Refresh
**Started**: 2025-10-27  
**Status**: In Progress - Awaiting Review  
**Size**: Small (1-2 days)  
**Owner**: Claude Sonnet 4.5, GPT-5-Codex (review)  
**Link**: [docs/work-packages/20251027_ui_style_guide_refresh/](docs/work-packages/20251027_ui_style_guide_refresh/)  
**Description**: Merge UI documentation into single agent-training guide with pattern catalog for rapid control construction. Enable <5 minute control creation with zero aesthetic decisions.

**Objective**: Transform UI development from time sink into mechanical pattern-matching workflow.

**Deliverables**:
- ✅ Merged `ui-style-guide.md` (1151 lines)
- ✅ Pattern Catalog (8 copy-paste templates)
- ✅ Quick Reference Tables, Troubleshooting, Testing Checklist
- ✅ "Zero-Aesthetic" design philosophy integration
- ✅ TOC generated via `markdown-doc toc`
- ⏳ GPT-5-Codex review (awaiting feedback)

**Strategic Value**:
- Agents can build UI mechanically: user request → pattern match → template fill → done
- Developer spends zero time on aesthetics, <5 minutes per control
- Patterns enforce consistency automatically (no style drift)
- Foundation for future agent auto-generation system

**Current Status**:
- Pattern catalog complete with 8 patterns (Control Shell, Summary Pane, Advanced Options, Status Panel + WebSocket, Data Table + Pagination, Form with Validation, Status Indicators, Console Layout)
- Composition rules, decision tree, quick reference tables documented
- Review request sent to GPT-5-Codex for technical validation
- Awaiting feedback on pattern accuracy, completeness, composition rules

**Dependencies**: Blocked on GPT-5-Codex review completion

**Next Steps**:
1. Receive Codex review feedback
2. Address technical corrections
3. Add missing patterns if identified
4. Update TOC if structure changes
5. Close package

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

### Frontend Integration & Smoke Automation
**Started**: 2025-02-24  
**Status**: ~85% complete, 7 specific issues identified and documented  
**Size**: Medium (3-4 weeks)  
**Owner**: Multiple agents  
**Link**: [docs/work-packages/20251023_frontend_integration/](docs/work-packages/20251023_frontend_integration/)  
**Description**: Complete Pure template migrations, refactor bootstrap initialization, establish repeatable smoke validation flow.

**Recent Progress**:
- ✅ All controllers migrated to Pure templates with StatusStream
- ✅ Bootstrap refactored to use helper-driven initialization
- ✅ Map race condition and preflight script issues resolved
- ✅ URL construction pattern (`url_for_run()`) fixed and documented
- ✅ **2025-10-27**: Seven outstanding issues analyzed and fully documented with implementation specs

**Current Work** (7 prioritized issues):
1. 🔧 **Legend visual styling**: 2-column layout with color swatches for map legends
2. 🔧 **Report table styling**: Standardize `.wc-table-wrapper` + `.wc-table` classes across all reports
3. 🔧 **Preflight TOC indicators**: Add `data-toc-emoji-value` attributes for completion checkmarks
4. ✅ **Control ordering**: Verify landuse appears before soils (appears correct, needs final validation)
5. 🔧 **Map layer radio enablement**: Wire to `window.lastPreflightChecklist` for dynamic enabling
6. 🔧 **Inline help icons**: Migrate to Pure macro `inline_help` parameter (affects 16+ instances)
7. 🔧 **Controller hint deduplication**: Show job dashboard link in hints, remove from status cards, eliminate message duplication (11 controllers affected)

**Next Steps**:
- Implement hint deduplication (Issue 7) - improves UX across all controllers
- Implement legend styling (Issue 1) - straightforward CSS + markup pattern
- Standardize report tables (Issue 2) - grep survey + template updates
- Restore TOC indicators (Issue 3) - add attributes to runs0_pure.htm
- Wire map layer state (Issue 5) - JS logic in subcatchment_delineation.js
- Enhance Pure macros for inline help (Issue 6) - macro updates + lightweight tooltip handler
- Final visual validation and smoke test integration
- Close package when all 7 issues resolved and rendering stable

---

### Smoke Tests & Profile Harness
**Started**: 2025-02-24  
**Status**: In planning/early implementation  
**Size**: Medium (2-3 weeks)  
**Owner**: Frontend/QA team  
**Link**: [docs/work-packages/20251023_smoke_tests/](docs/work-packages/20251023_smoke_tests/)  
**Description**: Establish Playwright-based smoke harness driven by YAML profiles for quick health snapshots.

**Recent Progress**:
- ✅ Initial quick profile drafted
- ✅ Smoke harness spec documented
- ✅ Test-support blueprint honors SMOKE_RUN_ROOT

**Next Steps**:
- Implement `wctl run-smoke --profile <name>` loader
- Expand Playwright suite to honor profile steps
- Author additional profiles (rattlesnake, blackwood, earth)

---

## ✅ Done

Recently completed work packages. Archive to History section after 30 days.

### NoDb ACID Transaction Update
**Completed**: 2025-10-25  
**Duration**: 1 day (planning only)  
**Status**: ❌ **CANCELLED - Unviable**  
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
- **Status**: ✅ Within target range

### Throughput
Packages completed per month:
- **October 2025**: 3 packages completed/closed (2 completed successfully, 1 cancelled as unviable); 1 package advanced to Phase 3 complete (markdown-doc toolkit)

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

Move packages from "Done" to "History" section (below) after 30 days. This keeps the tracker focused on recent/active work while preserving completion history.

### Questions or Issues

If this tracker format isn't working or you have suggestions:
1. Create a work package for "PROJECT_TRACKER improvements"
2. Document specific pain points and proposed solutions
3. Experiment with changes and gather feedback

---

## 📚 History

### October 2025
- ✅ StatusStream Telemetry Cleanup (completed 2025-10-23)
- ❌ NoDb ACID Transaction Update (cancelled 2025-10-25 - unviable architecture)
- ✅ Controller Modernization Documentation Backlog (completed 2025-02-14)

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
