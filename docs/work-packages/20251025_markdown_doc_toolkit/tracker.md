# Work Package Tracker: markdown-doc Toolkit

**Status:** Backlog  
**Last Updated:** 2025-10-25 14:30 PST

---

## Task Board

### Backlog

- [ ] **Design & Planning**
  - [ ] Finalize CLI command surface (commands, flags, exit codes)
  - [ ] Design `.markdown-doc.toml` schema
  - [ ] Document link resolution algorithm
  - [ ] Define template validation schema
  - [ ] Write architectural design doc

- [ ] **Phase 1: Foundation**
  - [ ] Set up Rust project structure (Cargo.toml, CI)
  - [ ] Implement configuration parser
  - [ ] Build shared markdown parser wrapper
  - [ ] Implement `catalog` command (basic)
  - [ ] Implement `toc` command (read/write)
  - [ ] Write integration tests for catalog

- [ ] **Phase 2: Quality Gates**
  - [ ] Implement `lint` command skeleton
  - [ ] Add broken-links lint rule
  - [ ] Add heading-hierarchy lint rule
  - [ ] Add required-sections lint rule
  - [ ] Implement `validate` template checking
  - [ ] Add CI integration examples

- [ ] **Phase 3: Refactoring Support**
  - [ ] Design link update engine
  - [ ] Implement `mv` command with dry-run
  - [ ] Implement reference scanning engine
  - [ ] Implement `refs` command
  - [ ] Add atomic operation guarantees
  - [ ] Write comprehensive move tests

- [ ] **Phase 4: Intelligence**
  - [ ] Design search index structure
  - [ ] Implement `search` command
  - [ ] Add index caching
  - [ ] Performance optimization pass
  - [ ] Write user documentation
  - [ ] Create example workflows

### In Progress

*(Nothing yet)*

### Done

*(Nothing yet)*

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

### Context for Next Agent

When resuming this work:
1. Read `package.md` for full scope and objectives
2. Review existing `markdown-extract`/`markdown-edit` source for patterns
3. Check `/workdir/wepppy` for current markdown file count/structure
4. Validate `.markdown-doc.toml` schema against wepppy's needs

### Open Questions

- Should `catalog` include file metadata (size, last modified)?
- Should `lint` support custom rules via plugins?
- Should `mv` handle git mv automatically?
- Should search support regex patterns?

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

## Next Steps

1. **Immediate:** Review with Roger to confirm scope/priorities
2. **Week 1:** Begin architectural design document
3. **Week 1-2:** Implement Phase 1 (foundation + catalog)
4. **Week 2:** Demo `catalog` command for feedback

---

## Related Work Packages

*(None yet - this is the first documentation tooling initiative)*

---

## References

- [markdown-extract source](https://github.com/sean0x42/markdown-extract)
- [markdown-edit spec](../../../tools/README.markdown-tools.md)
- [wepppy doc structure](../../..) - Current documentation layout
- [AGENTS.md](../../../AGENTS.md) - Documentation philosophy
