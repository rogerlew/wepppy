# PROJECT_TRACKER.md
> Kanban board for wepppy work packages and vision items

**Last Updated**: 2025-10-24  
**Active Packages**: 2  
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

**Current WIP**: 2 packages

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

---

## 🚧 In Progress

Currently active work packages. Limit to 2-4 packages to maintain focus.

### NoDb ACID Transaction Update
**Started**: 2025-10-24  
**Status**: Planning Complete - Implementation Ready  
**Size**: Medium (4-6 weeks)  
**Owner**: GitHub Copilot / Codex  
**Link**: [docs/work-packages/20251024_nodb_acid_update/](docs/work-packages/20251024_nodb_acid_update/)  
**Description**: Implement Redis-backed ACID transactions for NoDb controllers with intelligent event-driven cache invalidation.

**Recent Progress**:
- ✅ Work package structure created with detailed planning
- ✅ cache_invalidation_rules.json schema defined
- ✅ 3 implementation prompts created for Codex
- ✅ Architectural decisions finalized (centralized rules, file-based primary)
- ✅ Success criteria and deliverables specified
- ✅ Cache invalidation strategy clarified (cache-only with user overrides)

**Current Work**:
- 🔧 Ready to begin implementation with Redis transaction wrapper

**Next Steps**:
- Implement Redis transaction wrapper in NoDb base class
- Extend RedisPrep with cache invalidation methods
- Update RQ API endpoints for automatic invalidation
- Comprehensive testing and documentation

### Frontend Integration & Smoke Automation
**Started**: 2025-02-24  
**Status**: ~90% complete, smoke automation split to separate package  
**Size**: Medium (3-4 weeks)  
**Owner**: Multiple agents  
**Link**: [docs/work-packages/20251023_frontend_integration/](docs/work-packages/20251023_frontend_integration/)  
**Description**: Complete Pure template migrations, refactor bootstrap initialization, establish repeatable smoke validation flow.

**Recent Progress**:
- ✅ All controllers migrated to Pure templates with StatusStream
- ✅ Bootstrap refactored to use helper-driven initialization
- ✅ Map race condition and preflight script issues resolved
- ✅ URL construction pattern (`url_for_run()`) fixed and documented
- ⏩ Smoke automation moved to separate package

**Current Work**:
- 🔧 Sort out miscellaneous rendering bugs across controllers
- 🔧 Validate reports (WEPP reports, loss summaries, visualizations)

**Next Steps**:
- Complete rendering bug fixes and visual validation
- Polish controller documentation
- Finalize verification checklist
- Close package when all reports validated and rendering stable

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

### StatusStream Telemetry Cleanup
**Completed**: 2025-10-23  
**Duration**: 1 day  
**Link**: [docs/work-packages/20251023_statusstream_cleanup/](docs/work-packages/20251023_statusstream_cleanup/)  
**Description**: Replaced legacy WSClient shim with unified controlBase.attach_status_stream helper.

**Outcome**: Unified telemetry pipeline with no WSClient references; all controllers use StatusStream.

---

### Controller Modernization Documentation Backlog
**Completed**: 2025-02-14  
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
- **Status**: ✅ Within target range

### Throughput
Packages completed per month:
- **October 2025**: 2 packages completed

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
- ✅ Controller Modernization Documentation Backlog (completed 2025-02-14)

### [Month YYYY]
- [Package name] (completed YYYY-MM-DD) - [One line outcome]

---

## 🔧 Tracker Maintenance

**Last reviewed**: 2025-10-24  
**Next review**: 2025-11-24 (monthly)

**Review checklist**:
- [ ] Move stale Done items to History
- [ ] Update WIP count and check against limits
- [ ] Review In Progress packages for stalls (>6 weeks)
- [ ] Verify Backlog priorities still align with current goals
- [ ] Check Vision items for readiness to become packages
- [ ] Update metrics section with recent data
