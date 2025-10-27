# Work Package Tracker: markdown-doc Toolkit

**Status:** Backlog  
**Last Updated:** 2025-10-25 14:30 PST

---

## Task Board

### Backlog

- [ ] **Phase 1: MVP Implementation**
  - [ ] Set up Rust project structure (Cargo.toml, CI)
  - [ ] Implement configuration parser with defaults fallback
  - [ ] Build shared markdown parser wrapper (pulldown-cmark)
  - [ ] Implement `catalog` command with concurrent file reading
    - [ ] Selective scanning (--path, --staged flags)
    - [ ] Atomic temp-file writes
    - [ ] JSON output mode
  - [ ] Implement `lint broken-links` command
    - [ ] Configurable severity (error/warning/ignore)
    - [ ] Ignore lists for known edge cases
    - [ ] JSON/SARIF output formats
  - [ ] CLI acceptance tests (exit codes, output formats, selective scanning)
  - [ ] Performance benchmarks (<5s for 388 files, concurrent safety)

- [ ] **Phase 2: Quality Gates**
  - [ ] Implement `toc` command (read/write TOC markers)
  - [ ] Add additional lint rules:
    - [ ] broken-anchors rule
    - [ ] duplicate-anchors rule
    - [ ] heading-hierarchy rule
    - [ ] required-sections rule
  - [ ] Implement `validate` command (template compliance)
  - [ ] Severity tuning system (per-path exemptions, downgradeable severities)
  - [ ] `.markdown-doc-ignore` file support
  - [ ] CI integration docs with examples

- [ ] **Phase 3: Refactoring Support**
  - [ ] Design link update engine
  - [ ] Implement `mv` command with dry-run
  - [ ] Implement reference scanning engine
  - [ ] Implement `refs` command
  - [ ] Add atomic operation guarantees
  - [ ] Write comprehensive move tests

- [ ] **Phase 4: Intelligence (Deferred)**
  - [ ] Define acceptance criteria (latency, ranking, snippet quality)
  - [ ] Design search index structure
  - [ ] Implement `search` command
  - [ ] Add index caching
  - [ ] Performance optimization pass
  - [ ] Write user documentation
  - [ ] Create example workflows

### In Progress

- [ ] **CI Integration Sprint (Nov 3)**
  - [x] Wire `cargo fmt --check`, `cargo clippy`, `cargo test --all` into markdown-doc GitHub Actions (conditional step looks for `MARKDOWN_DOC_WORKSPACE` or common install paths; configure runner env to enable enforcement)
  - [x] Add `wctl doc-lint --format sarif` and `wctl doc-bench --path docs --warmup 0 --iterations 1` to PR workflow (`docs-quality.yml`)
  - [x] Publish SARIF results to Code Scanning dashboard with failure gates on errors (Docs Quality workflow uploads); SARIF is normalized to v3 schema post-lint, and lint scope excludes `.docker-data` via explicit path list.
- [ ] **Lint Backlog Triage (Nov 4–7)**
  - [ ] Categorize existing `markdown-doc lint --path docs` findings
  - [ ] Open issues/PBIs for doc fixes vs. intentional ignores
  - [ ] Land initial remediation PR batch (target ≥50% reduction)
- [ ] **Documentation & Comms (Nov 6–8)**
  - [ ] Update `tools/README.markdown-tools.md` with wctl quick start
  - [ ] Add `.markdown-doc-ignore` guidance to onboarding docs
  - [ ] Draft release notes / announcement for internal channels

### Done

- [x] **Design & Planning**
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

### 2025-10-25: Work Package Created

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

*(None identified yet)*

### Resolved Issues

*(None yet)*

---

## Verification Checklist

### Before Release

- [ ] All commands have `--help` output
- [ ] All commands have exit code documentation
- [ ] Dry-run mode works for destructive operations
- [ ] Configuration file schema documented
- [ ] CI integration example provided
- [ ] README.md includes quickstart
- [ ] Performance benchmarked on 388 files
- [ ] Error messages are actionable
- [ ] Agent workflows documented

### Quality Gates

- [ ] Zero panics on invalid input
- [ ] Handles missing files gracefully
- [ ] UTF-8 validation on all reads
- [ ] Atomic file operations (temp + rename)
- [ ] Backup files created for destructive ops
- [ ] Exit codes consistent across commands
- [ ] Stderr for errors, stdout for data

---

## Agent Handoff Notes

### 2025-10-26 — wctl markdown-doc integration handback
- Implemented `wctl doc-*` wrappers via `install.sh` template (doc-lint, doc-catalog, doc-toc, doc-mv, doc-refs, doc-bench) and regenerated `wctl.sh`; added helper functions for binary checks, TOC argument translation, and `/dev/tty` prompts.
- Updated `wctl/README.md`, `wctl/wctl.1`, and `wctl/AGENTS.md` with usage guidance, testing expectations, and maintenance notes for the new commands.
- Smoke tests: `wctl doc-lint`, `wctl doc-lint --help`, `wctl doc-catalog --format json --path docs`, `wctl doc-toc README.md`, `wctl doc-refs README.md --path docs`, `wctl doc-bench --path docs --warmup 0 --iterations 1`, plus mocked `doc-mv` flows (`--dry-run-only`, prompt confirm, `--force`) using a temporary PATH shim.
- Known issue: real `markdown-doc` commands attempt to index `.docker-data/redis`, triggering `Permission denied`; mitigation today is scoping with `--path docs` or using mocks. Follow-up needed to land repo-level `.markdown-doc-ignore` entries or adjust permissions per RFC rollout.
- Update 2025-10-31: Added repo-level `.markdown-doc-ignore` with `.docker-data/**` so markdown-doc skips docker volumes; keep `sudo wctl restore-docker-data-permissions` in onboarding as a troubleshooting step.

### Context for Next Agent

When resuming this work:
1. Read `package.md` for full scope and objectives
2. Review existing `markdown-extract`/`markdown-edit` source for patterns
3. Check `/workdir/wepppy` for current markdown file count/structure
4. Validate `.markdown-doc.toml` schema against wepppy's needs

### Open Questions

- Should `catalog` include file metadata (size, last modified)? — **Deferred to Phase 2**
- Should `lint` support custom rules via plugins? — **Deferred, start with built-in rules**
- Should `mv` handle git mv automatically? — **Deferred, manual git integration for now**
- ~~Should search support regex patterns?~~ — **Answered: Search deferred pending acceptance criteria**
- ~~How to handle false positives in lint?~~ — **Answered: Severity tuning + ignore lists in Phase 2**
- ~~What output formats for CI/agents?~~ — **Answered: JSON and SARIF in MVP**

### Implementation Notes

- Use `pulldown-cmark` for markdown parsing (proven in existing tools)
- Consider `ignore` crate for .gitignore-aware file walking
- Use `clap` for CLI parsing (consistent with Rust ecosystem)
- Mirror exit code conventions from `markdown-edit`

---

## Communication Log

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

**Status:** Work package created, ready for agent pickup

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

**Status:** Specification complete with codex feedback integrated

---

## Next Steps

1. ~~**Immediate:** Review with Roger to confirm scope/priorities~~ — **Done: Codex review integrated**
2. **Week 1:** Begin MVP implementation (catalog + lint broken-links + config loader)
   - Set up Rust project with Cargo.toml
   - Implement config parser with defaults fallback
   - Build catalog command with concurrent file reading
   - Add selective scanning (`--path`, `--staged`) and JSON output
3. **Week 1:** Implement lint broken-links with severity tuning
   - Support ignore patterns from config
   - JSON and SARIF output formats
   - CLI acceptance tests
4. **Week 2:** Performance validation and M1 milestone
   - Benchmark catalog on 388 files (<5s target)
   - Verify concurrent safety (atomic writes)
   - Demo MVP to Roger for feedback

---

## Related Work Packages

*(None yet - this is the first documentation tooling initiative)*

---

## References

- [markdown-extract source](https://github.com/sean0x42/markdown-extract)
- [markdown-edit spec](../../../tools/README.markdown-tools.md)
- [wepppy doc structure](../../..) - Current documentation layout
- [AGENTS.md](../../../AGENTS.md) - Documentation philosophy
