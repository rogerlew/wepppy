# Work Package Tracker: markdown-doc Toolkit

**Status:** Phase 3 Complete — Integration Active  
**Last Updated:** 2025-10-26 19:30 PST

**GitHub Issues:**
- [#417 - RFC Decision Gate](https://github.com/rogerlew/wepppy/issues/417) (Due: Nov 8)
- [#418 - Integration Finalization](https://github.com/rogerlew/wepppy/issues/418) (Due: Nov 8)
- [#419 - Phase 4 Go/No-Go Decision](https://github.com/rogerlew/wepppy/issues/419) (Due: Nov 18)

---

## Task Board

### Backlog

- [ ] **Phase 4: Search & Indexing MVP** — [GitHub Issue #419](https://github.com/rogerlew/wepppy/issues/419) (Blocked - awaiting telemetry data + RFC decisions)
  - [ ] **Pre-M1 Prerequisites** (Due: 2025-11-18)
    - [ ] Collect ≥2 weeks of lint telemetry data (started 2025-10-31)
    - [ ] Resolve RFC open decisions (link-graph caching, CI bench cadence, Phase 4 scope)
    - [ ] Review telemetry to validate Phase 4 justification
  - [ ] **M1 – Index Foundations** (Target: 2025-12-06)
    - [ ] Design search index structure (JSON/SQLite)
    - [ ] Implement tokenizer with Porter stemming
    - [ ] Build basic index builder (full rebuild only)
    - [ ] Implement `markdown-doc search` CLI with TF-IDF ranking
    - [ ] Text/JSON output formats
    - [ ] Initial unit tests
  - [ ] **M2 – Incremental Refresh** (Target: 2025-12-20)
    - [ ] Hash/mtime-based incremental updates
    - [ ] Index stats telemetry integration
    - [ ] `wctl doc-search` wrapper implementation
    - [ ] Performance benchmarks (<5s build, <500ms search)
  - [ ] **M3 – Integration & Docs** (Target: 2026-01-10)
    - [ ] Optional CI index build (behind `DOC_SEARCH_INDEX=1` flag)
    - [ ] Documentation updates (README, tools guide)
    - [ ] Snippet quality validation tests
    - [ ] Resolve open questions (index storage, watch requirements, UI integration, search ignore patterns)

### In Progress

- [ ] **RFC Decision Gate (Due: 2025-11-08)** — [GitHub Issue #417](https://github.com/rogerlew/wepppy/issues/417)
  - [ ] Link graph caching strategy [Due: 2025-11-05]
  - [ ] Phase 4 scope finalization [Due: 2025-11-08]
  - [ ] CI surface area (bench cadence) [Due: 2025-11-03]
  - [ ] Release communications plan [Due: 2025-11-02]
  
- [ ] **Integration Finalization (Nov 2–8)** — [GitHub Issue #418](https://github.com/rogerlew/wepppy/issues/418)
  - [x] ~~Wire Rust checks into docs-quality workflow~~ (Complete: 2025-10-31)
  - [x] ~~Implement telemetry logging~~ (Complete: 2025-10-31)
  - [x] ~~Update `tools/README.markdown-tools.md` with wctl quick start~~ (Complete: 2025-10-26)
  - [ ] Add `.markdown-doc-ignore` guidance to onboarding docs
  - [ ] Draft release notes / announcement for internal channels
  - [ ] Update work package tracker with RFC decisions (this document)

### Done

- [x] **Phase 1: MVP Implementation** (Complete: 2025-10-30)
  - [x] Set up Rust project structure (Cargo.toml, CI)
  - [x] Implement configuration parser with defaults fallback
  - [x] Build shared markdown parser wrapper (pulldown-cmark)
  - [x] Implement `catalog` command with concurrent file reading
    - [x] Selective scanning (--path, --staged flags)
    - [x] Atomic temp-file writes
    - [x] JSON output mode
  - [x] Implement `lint broken-links` command
    - [x] Configurable severity (error/warning/ignore)
    - [x] Ignore lists for known edge cases
    - [x] JSON/SARIF output formats (camelCase compliant)
  - [x] CLI acceptance tests (exit codes, output formats, selective scanning)
  - [x] Performance benchmarks (<5s for 388 files, concurrent safety verified)

- [x] **Phase 2: Quality Gates** (Complete: 2025-10-30)
  - [x] Implement `toc` command (read/write TOC markers)
  - [x] Add additional lint rules:
    - [x] broken-anchors rule
    - [x] duplicate-anchors rule
    - [x] heading-hierarchy rule
    - [x] required-sections rule
  - [x] Implement `validate` command (template compliance)
  - [x] Severity tuning system (per-path exemptions, downgradeable severities)
  - [x] `.markdown-doc-ignore` file support
  - [x] CI integration docs with examples

- [x] **Phase 3: Refactoring Support** (Complete: 2025-10-30)
  - [x] Design link update engine
  - [x] Implement `mv` command with dry-run
  - [x] Implement reference scanning engine
  - [x] Implement `refs` command
  - [x] Add atomic operation guarantees
  - [x] Write comprehensive move tests (including complex fixtures)

- [x] **wepppy Integration** (Complete: 2025-10-31)
  - [x] Implement `wctl doc-*` wrappers (doc-lint, doc-catalog, doc-toc, doc-mv, doc-refs, doc-bench)
  - [x] Wire into docs-quality workflow with SARIF upload
  - [x] Configure Rust checks via `MARKDOWN_DOC_WORKSPACE` secret
  - [x] Add `.markdown-doc-ignore` with `.docker-data/**` exclusion
  - [x] Enable telemetry logging (JSON lines to `telemetry/docs-quality.jsonl`)
  - [x] Document wctl commands in `tools/README.markdown-tools.md`
  - [x] Update wctl README, man page, and AGENTS guide

### Done

- [x] **Design & Planning** (Complete: 2025-10-25)
  - [x] Finalize CLI command surface (commands, flags, exit codes) - See package.md CLI Design section
  - [x] Design `.markdown-doc.toml` schema - See Configuration Example in package.md
  - [x] Document link resolution algorithm - Covered in initial-requirements.md
  - [x] Define template validation schema - Schema Philosophy section complete
  - [x] Clarify MVP scope vs post-MVP phases
  - [x] Define output formats (plain text, JSON, SARIF)
  - [x] Document concurrency model (atomic writes, no global locks)
  - [x] Specify selective scanning modes (--path, --staged)
  - [x] Clarify `lint` vs `validate` relationship
  - [x] Define severity tuning approach (Phase 2)
  - [x] Integrated codex review feedback

---

## Decisions Log

### 2025-10-31: Telemetry Logging Enabled

**Decision:** Implement lightweight telemetry logging in docs-quality workflow  
**Rationale:**
- Phase 4 (search/indexing) requires baseline performance data to justify investment
- Need to measure lint runtime, error counts, and resource usage over time
- Enables data-driven decisions for caching strategies and watch-mode priorities

**Implementation:**
- JSON lines appended to `telemetry/docs-quality.jsonl` on each workflow run
- Format includes: timestamp, commit SHA, lint duration/errors, workflow duration
- Published as `docs-quality-telemetry` artifact for historical analysis
- Minimum 2 weeks of data required before Phase 4 kickoff

**Participants:** Codex, Claude (based on Phase 4 RFC review)

---

### 2025-10-31: SARIF Schema Compliance

**Decision:** Formatter emits camelCase SARIF fields directly  
**Rationale:**
- CodeQL Action v3 requires strict SARIF 2.1.0 compliance
- Manual normalization in workflow was fragile and added complexity
- Native camelCase output (ruleId, physicalLocation, etc.) eliminates transformation step

**Status:** ✅ Resolved - formatter updated, workflow simplified

**Participants:** Codex (based on CodeQL v3 migration requirements)

---

### 2025-10-31: `.docker-data` Permission Strategy

**Decision:** Exclude docker volumes via `.markdown-doc-ignore` instead of permission workarounds  
**Rationale:**
- Docker-managed volumes have restrictive permissions (redis:redis, postgres:postgres)
- Scanning these directories causes permission denied errors in lint/catalog
- Exclusion is cleaner than sudo wrappers or permission loosening
- Aligns with gitignore pattern: build artifacts shouldn't be scanned

**Implementation:**
- Repository ships `.markdown-doc-ignore` with `.docker-data/**`
- Keep `sudo wctl restore-docker-data-permissions` in troubleshooting docs for existing environments
- Future docker volume additions should be added to ignore file

**Status:** ✅ Resolved

**Participants:** Codex, Roger (from RFC adoption discussion)

---### 2025-10-25: Work Package Created

**Decision:** Build `markdown-doc` as standalone Rust CLI  
**Rationale:**
- Leverages existing `markdown-extract`/`markdown-edit` patterns
- Rust provides performance for large doc sets (388+ files)
- Standalone tool = reusable across projects
- Agent-executable by design

**Alternatives considered:**
- Python tool: Rejected (slower, adds dependency)
- Shell scripts: Rejected (complex logic, hard to maintain)
- Extend existing tools: Rejected (different concerns, keep focused)

**Participants:** Roger, Claude

---

### 2025-10-25: `mv` Command Added to Scope

**Decision:** Include `markdown-doc mv` in initial release  
**Rationale:**
- High-value feature for refactoring workflows
- Reduces friction for documentation reorganization
- Prevents broken links when restructuring
- Enables agents to safely move docs

**Implementation notes:**
- Dry-run mode required (preview before apply)
- Atomic operations (all updates succeed or all fail)
- Backup files by default
- Clear exit codes for automation

**Participants:** Roger, Claude

---

### 2025-10-25: Lead Developer Review Integrated

**Decision:** Narrow MVP scope to single vertical slice: `catalog` + `lint broken-links` + config loader  
**Rationale:**
- Original Phase 1 was too broad (multi-quarter roadmap feel)
- Single vertical slice proves end-to-end workflow faster
- Enables early feedback before building additional rules

**Changes made:**
- Moved `toc` command to Phase 2 (not MVP-critical)
- Added selective scanning flags (`--path`, `--staged`) to MVP scope
- Specified output formats (plain text, JSON, SARIF) for agent/human/CI consumers
- Added severity tuning system (ignore lists, downgradeable severities) to Phase 2
- Clarified `validate` vs `lint required-sections` relationship
- Documented concurrency safety (atomic temp-file writes, no global locks)
- Added configuration precedence and fallback behavior
- Deferred `search` command pending acceptance criteria (latency, ranking, snippet quality)
- Updated milestones with concrete acceptance criteria

**Implementation notes:**
- `lint` and `validate` both read `[schemas]` config but serve different purposes
- `lint`: Fast incremental checks (pre-commit suitable)
- `validate`: Deep template conformance (CI gate for critical files)

**Participants:** Roger, Claude (integrating codex feedback)

---

### 2025-10-25: Scope Boundaries Clarified

**Decision:** Move post-MVP commands to "Out of Scope (Future Phases)" section  
**Rationale:**
- `search`, `mv`, `refs`, `toc`, `validate` appeared under "In Scope" but belong to Phase 2-4
- Only `catalog` + `lint broken-links` + config loader constitute MVP/first release
- Clearer separation prevents confusion about first milestone gates

**Changes made:**
- "In Scope" section now lists only MVP components
- "Out of Scope" organized by phase (Phase 2: Quality Gates, Phase 3: Refactoring, Phase 4: Intelligence)
- Success Criteria split into "MVP Exit" vs "Full Toolkit"
- MVP exit criteria now accurately reflect first release scope (no Phase 2/3 features)

**Participants:** Roger (review feedback), Claude

---

## Risks & Issues

### Active Risks

1. **Phase 4 Justification Uncertainty** (Medium)
   - **Risk:** Telemetry may not justify search/indexing investment
   - **Mitigation:** Collect 2+ weeks of baseline data before Phase 4 go/no-go decision; define clear acceptance thresholds
   - **Owner:** Product/Docs leads
   - **Due:** 2025-11-18 (Pre-M1 gate)

2. **RFC Decision Deadlines** (Medium)
   - **Risk:** Open decisions (link-graph caching, CI bench cadence, Phase 4 scope) blocking Phase 4 start
   - **Mitigation:** Scheduled decision reviews with clear owners and due dates (2025-11-02 to 2025-11-08)
   - **Owner:** Platform team, Tooling leads
   - **Status:** In progress

### Resolved Issues

1. **SARIF Upload Failures** (Resolved: 2025-10-31)
   - **Issue:** CodeQL Action v2 deprecated, v3 requires camelCase SARIF fields
   - **Resolution:** Updated formatter to emit native camelCase; workflow simplified
   
2. **Permission Denied on `.docker-data`** (Resolved: 2025-10-31)
   - **Issue:** lint/catalog failing when scanning docker-managed volumes
   - **Resolution:** Added `.markdown-doc-ignore` with `.docker-data/**` exclusion

---

## Verification Checklist

### Phase 1-3 (Complete ✅)

- [x] All commands have `--help` output
- [x] All commands have exit code documentation
- [x] Dry-run mode works for destructive operations (mv)
- [x] Configuration file schema documented
- [x] CI integration implemented (docs-quality workflow)
- [x] README.md includes quickstart
- [x] Performance benchmarked on 388 files (<5s catalog, <5s lint)
- [x] Error messages are actionable
- [x] Agent workflows documented (tools/README.markdown-tools.md)
- [x] Zero panics on invalid input
- [x] Handles missing files gracefully
- [x] UTF-8 validation on all reads
- [x] Atomic file operations (temp + rename)
- [x] Backup files created for destructive ops
- [x] Exit codes consistent across commands (0-4 range)
- [x] Stderr for errors, stdout for data

### Phase 4 Prerequisites (In Progress)

- [x] Telemetry logging implemented (2025-10-31)
- [ ] Telemetry data collection (≥2 weeks required, started 2025-10-31)
- [ ] RFC open decisions resolved (due 2025-11-08)
- [ ] Phase 4 scope finalized with acceptance criteria
- [ ] Release communications drafted

---

## Agent Handoff Notes

### 2025-10-31 — Phase 3 Complete, Integration Active
- Phase 1-3 markdown-doc features shipped from `/workdir/markdown-extract` workspace
- All core commands operational: catalog, lint (with full rule set), toc, validate, mv, refs
- docs-quality workflow fully integrated:
  - Runs `wctl doc-lint` with SARIF/JSON output
  - Executes `cargo fmt/clippy/test` via `MARKDOWN_DOC_WORKSPACE` secret
  - Uploads SARIF to Code Scanning (camelCase compliant)
  - Collects telemetry (JSON lines to `telemetry/docs-quality.jsonl`)
- wctl wrappers complete with comprehensive documentation
- `.markdown-doc-ignore` excludes `.docker-data/**`
- Lint backlog cleared (0 open errors)

### 2025-10-26 — wctl markdown-doc integration handback
- Implemented `wctl doc-*` wrappers via `install.sh` template (doc-lint, doc-catalog, doc-toc, doc-mv, doc-refs, doc-bench) and regenerated `wctl.sh`; added helper functions for binary checks, TOC argument translation, and `/dev/tty` prompts.
- Updated `wctl/README.md` and `wctl/AGENTS.md` with usage guidance, testing expectations, and maintenance notes for the new commands.
- Smoke tests: `wctl doc-lint`, `wctl doc-lint --help`, `wctl doc-catalog --format json --path docs`, `wctl doc-toc README.md`, `wctl doc-refs README.md --path docs`, `wctl doc-bench --path docs --warmup 0 --iterations 1`, plus mocked `doc-mv` flows (`--dry-run-only`, prompt confirm, `--force`) using a temporary PATH shim.
- Known issue resolved: `.markdown-doc-ignore` now excludes `.docker-data/**` so permissions no longer cause failures.

### Context for Next Agent (Phase 4)

**Prerequisites before starting Phase 4:**
1. Wait for ≥2 weeks of telemetry data (started 2025-10-31, ready ~2025-11-18)
2. Resolve RFC open decisions (due 2025-11-08):
   - Link graph caching strategy
   - CI bench cadence (per-PR vs nightly)
   - Phase 4 scope validation (search/watch priorities)
   - Release communications plan
3. Review telemetry data to confirm search investment justification

**When resuming Phase 4 work:**
1. Read Phase 4 RFC (`prompts/rfc_phase4_search_indexing.md`) for complete specification
2. Review Phase 4 scope proposal (`phase4_scope_proposal.md`) for detailed milestones
3. Check telemetry artifact data for baseline lint performance
4. Validate that RFC decisions are resolved
5. Confirm `/workdir/markdown-extract` workspace structure before implementing index builder

**Key Architecture Notes:**
- Search index will live at `.markdown-doc/index.json` (configurable)
- Tokenization: case-insensitive with Porter stemming
- Ranking: TF-IDF with term frequency fallback
- Incremental updates via mtime/hash comparison
- Target: <5s index build, <500ms search (cached index)

### Open Questions

**Phase 4 Related (Answers required by Nov 10-15):**
- Index artifact storage strategy: generated artifacts vs runner cache? [Decision: Nov 10]
- Watch mode requirements capture: implement in Phase 4 or defer to Phase 5? [Decision: Nov 15]
- UI integration: CLI only for MVP or plan portal integration? [Decision: Nov 15]
- Search-specific ignore patterns: rely on `.markdown-doc-ignore` or add search overrides? [Decision: Nov 10]

**RFC Decisions (Due Nov 2-8):**
- Link graph caching + directory move roadmap [Due: Nov 5]
- CI bench cadence (per-PR vs nightly) [Due: Nov 3]
- Release communications channel and audience [Due: Nov 2]
- Phase 4 scope validation (search/watch/stats priorities) [Due: Nov 8]

### Closed Questions

- ~~Should `catalog` include file metadata (size, last modified)?~~ — **Deferred to Phase 2** (not MVP-critical)
- ~~Should `lint` support custom rules via plugins?~~ — **Deferred, start with built-in rules** (extensibility can be added later)
- ~~Should `mv` handle git mv automatically?~~ — **Deferred, manual git integration for now** (avoids git dependency in core tool)
- ~~Should search support regex patterns?~~ — **Answered: Search deferred pending acceptance criteria** (Phase 4 scope)
- ~~How to handle false positives in lint?~~ — **Answered: Severity tuning + ignore lists in Phase 2** (implemented)
- ~~What output formats for CI/agents?~~ — **Answered: JSON and SARIF in MVP** (implemented with camelCase compliance)

### Implementation Notes

- Use `pulldown-cmark` for markdown parsing (proven in existing tools)
- Consider `ignore` crate for .gitignore-aware file walking
- Use `clap` for CLI parsing (consistent with Rust ecosystem)
- Mirror exit code conventions from `markdown-edit`

---

## Communication Log

### 2025-10-31 — Phase 3 Completion & Telemetry Enablement

**Status Update:**
- Phase 1-3 complete and deployed
- Telemetry logging enabled in docs-quality workflow
- SARIF compliance resolved (camelCase native output)
- `.docker-data` permission issue resolved via ignore file

**Next Steps:**
- Collect ≥2 weeks telemetry data (through ~2025-11-18)
- Resolve RFC open decisions (2025-11-02 to 2025-11-08)
- Draft release communications
- Phase 4 go/no-go decision after telemetry review

**Participants:** Codex, Claude

---

### 2025-10-26 — wctl Integration Complete

**Update:**
- All `wctl doc-*` wrappers implemented and documented
- `tools/README.markdown-tools.md` updated with comprehensive quick start
- Smoke tests passing for all commands
- Ready for production use

**Participants:** Codex

---

### 2025-10-25 14:30 PST - Initial Concept

**Roger:**
> "this has substantial documentation and managing documentation is a burden. I'd like to conceptualize documentation tooling to make management easier."

**Features requested:**
- Linting (broken links, project-aware)
- Project-wide catalog with comprehensive TOC
- TOC generation/update
- Reference finding
- Search
- **Move/rename with link updates** (added in discussion)

**Status:** Work package created, Phase 1-3 now complete

---

### 2025-10-25 16:00 PST - Codex Review Integration

**Codex feedback received:**
- MVP scope narrowed to single vertical slice (catalog + lint broken-links + config)
- Added operational details: selective scanning, output formats, CI integration
- Clarified `lint` vs `validate` command relationship
- Documented concurrency safety model (atomic writes, no global locks)
- Specified configuration precedence and fallback behavior
- Deferred `search` command until acceptance criteria defined

**Claude response:**
- Integrated all feedback into package.md
- Added "CLI Design and Integration" section with examples
- Expanded configuration with severity tuning and ignore patterns
- Updated deliverables to reflect MVP focus
- Enhanced milestones with concrete acceptance criteria
- Updated tracker.md with decision log

**Status:** Specification complete, all phases now implemented

---

## Next Steps

### Immediate (Week of 2025-10-28 to 2025-11-08)

1. **RFC Decision Gate** (Due: Nov 2-8)
   - [ ] Finalize link graph caching strategy (Nov 5)
   - [ ] Decide CI bench cadence: per-PR or nightly (Nov 3)
   - [ ] Draft and publish release communications (Nov 2)
   - [ ] Validate Phase 4 scope or defer to Q1 2026 (Nov 8)

2. **Integration Finalization** (Due: Nov 8)
   - [ ] Add `.markdown-doc-ignore` guidance to onboarding documentation
   - [ ] Publish internal release notes announcing new wctl commands
   - [ ] Update work package tracker with RFC decision outcomes
   - [ ] Archive Phase 3 completion artifacts

3. **Telemetry Collection** (Started: Oct 31, Complete: ~Nov 18)
   - [x] Telemetry logging enabled (Oct 31)
   - [ ] Collect ≥2 weeks of baseline data
   - [ ] Review telemetry for Phase 4 justification

### Phase 4 Gate (Week of 2025-11-18)

**Go/No-Go Decision Criteria:**
- [ ] ≥2 weeks of telemetry data collected
- [ ] RFC decisions resolved (link-graph caching, CI cadence, scope)
- [ ] Telemetry review confirms search investment justification
- [ ] Phase 4 open questions resolved (index storage, watch requirements, UI integration, search patterns)

**If Go:**
- Create Phase 4 work package directory structure
- Draft agent prompts for M1-M3 milestones
- Assign agent ownership for index builder, incremental refresh, integration tasks
- Schedule M1 completion target (~Dec 6, 2025)

**If No-Go:**
- Document deferral rationale in tracker
- Schedule Phase 4 revisit for Q1 2026 planning
- Continue monitoring telemetry quarterly

### Long-Term (Q1 2026+)

- Phase 4 implementation (if greenlit): search, indexing, performance optimization
- Phase 5 planning: watch mode, extended statistics, cross-repo federation
- Quarterly telemetry review and tooling refinement

---

## Related Work Packages

*(None yet - this is the first documentation tooling initiative)*

---

## References

- [markdown-extract source](https://github.com/sean0x42/markdown-extract)
- [markdown-edit spec](../../../tools/README.markdown-tools.md)
- [wepppy doc structure](../../..) - Current documentation layout
- [AGENTS.md](../../../AGENTS.md) - Documentation philosophy
