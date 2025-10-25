# Work Package: markdown-doc Toolkit

**Status:** Backlog  
**Created:** 2025-10-25  
**Owner:** Roger Lew  
**Lead Agent:** TBD

---

## Overview

Build a comprehensive `markdown-doc` CLI toolkit in Rust that provides project-wide documentation orchestration and intelligence, leveraging the existing `markdown-extract` and `markdown-edit` foundation.

### Problem Statement

WEPPpy has substantial documentation (388+ markdown files) but managing it is becoming a burden:
- No automated link validation (broken internal references go unnoticed)
- No centralized catalog (finding relevant docs requires manual searching)
- No tooling for safe refactoring (moving/renaming docs breaks links)
- No consistency enforcement (templates exist but aren't validated)
- Manual TOC maintenance (error-prone, often out of sync)

### Why Now

- Documentation is critical for AI-native development (agents depend on accurate docs)
- Scale is becoming a problem (388 files and growing)
- Existing Rust tools (`markdown-extract`, `markdown-edit`) provide the foundation
- Project maturity requires better documentation hygiene

---

## Objectives

### Primary Goals

1. **Reduce documentation maintenance burden** by 80% through automation
2. **Prevent documentation drift** with automated validation gates
3. **Enable safe doc refactoring** with automatic link updating
4. **Improve discoverability** through centralized catalog and search

### Success Criteria

- [ ] Broken internal links detected in CI (zero false positives)
- [ ] `DOC_CATALOG.md` auto-generated and always current
- [ ] Files can be moved/renamed without breaking references
- [ ] TOCs auto-update on file changes
- [ ] Template validation enforced for AGENTS.md, README.md, work packages

### Non-Goals (Initial Release)

- External link checking (can add later with caching)
- PDF/HTML export (separate feature)
- Live preview server (separate feature)
- Git integration for metadata (can extract from git separately)

---

## Scope

### In Scope

**Core Commands:**
- `markdown-doc lint` - Validate links, heading hierarchy, required sections
- `markdown-doc catalog` - Generate/update `DOC_CATALOG.md`
- `markdown-doc toc` - Generate/update table of contents
- `markdown-doc refs` - Find references to files/sections
- `markdown-doc search` - Search across all documentation
- `markdown-doc mv` - Move/rename files with automatic link updates
- `markdown-doc validate` - Check against templates

**Infrastructure:**
- `.markdown-doc.toml` configuration file
- Shared parsing library (leverage existing markdown parser)
- Exit codes and error handling conventions
- Agent-friendly output formats

### Out of Scope (Future Phases)

- Phase 2: `watch` mode, `stats`, `meta` commands
- Phase 3: `sync`, `refactor`, `export` commands
- Phase 4: AI context optimization features

---

## Technical Approach

### Key Design Decisions

1. **Leverage existing tools:** `markdown-extract` and `markdown-edit` for low-level ops
2. **Project-aware:** Configuration file defines project boundaries and rules
3. **Exit code conventions:** 0=success, 1=validation failure, 2=not found, 3=bad args, 4=I/O error
4. **Idempotent operations:** Safe to run repeatedly (catalog, toc, validate)
5. **Atomic updates:** Use temp files + rename for safe modifications

### Configuration Example

```toml
[project]
name = "wepppy"
root = "."
exclude = ["_legacy_weppcloud_controls", "_notes", "tmp_*"]

[catalog]
output = "DOC_CATALOG.md"
include_patterns = ["**/*.md"]
exclude_patterns = ["**/node_modules/**", "**/vendor/**"]

[lint]
rules = [
  "broken-links",        # File references must resolve
  "broken-anchors",      # #section anchors must exist in target
  "duplicate-anchors",   # No duplicate heading IDs within file
  "heading-hierarchy",   # No skipped levels (h2→h4)
  "required-sections"    # Schema-based section requirements
]
max_heading_depth = 4

# Schema-based validation (optional, progressive enhancement)
[schemas]

[schemas.default]
# Universal minimum - all markdown files
min_heading_level = 1
max_heading_level = 4
require_top_level_heading = true

[schemas.readme]
# Applied to: **/README.md
# Relaxed - READMEs vary widely by context
required_sections = []  # Start lenient, add patterns as they emerge
allow_empty = false
min_sections = 2  # At least a title + one section

[schemas.agents]
# Applied to: **/AGENTS.md
# Strict - AGENTS.md has defined template
required_sections = [
  "Authorship",
  "Core Directives",
  "Repository Overview"
]
allow_additional = true

[schemas.work_package]
# Applied to: docs/work-packages/**/package.md
# Enforces work package template
required_sections = [
  "Overview",
  "Objectives",
  "Scope",
  "Dependencies",
  "Deliverables"
]
allow_additional = true

[schemas.work_package_tracker]
# Applied to: docs/work-packages/**/tracker.md
required_sections = [
  "Task Board",
  "Decisions Log",
  "Verification Checklist"
]
allow_additional = true
```

### Schema Philosophy

**Start minimal, expand progressively:**

1. **Default schema** - Universal rules that apply everywhere:
   - Must have at least one top-level heading
   - Heading depth ≤ 4 (h1-h4 only, no h5/h6)
   - No empty files

2. **Pattern-based schemas** - Match by file path pattern:
   - `**/AGENTS.md` → agents schema
   - `**/README.md` → readme schema  
   - `docs/work-packages/**/package.md` → work_package schema
   - `docs/work-packages/**/tracker.md` → work_package_tracker schema

3. **Progressive strictness:**
   - READMEs: Lenient (context varies too much)
   - AGENTS.md: Strict (established template)
   - Work packages: Strict (enforces process)

**Why not over-specify initially:**

Analysis of existing files shows:
- **READMEs**: Huge variation (developer notes, architecture overviews, quick starts, API references)
- **AGENTS.md**: Consistent structure across the 5 files (main + submodules)
- **Work packages**: Recently standardized, clear template

**Expansion strategy:**

After MVP, analyze lint failures to identify:
- Common README patterns that could become templates
- Missing sections that indicate incomplete docs
- New document types that need schemas (API specs, dev notes, etc.)

This avoids bikeshedding on schemas before we have lint data.

---

## Feature Details

### 1. `markdown-doc mv` (New Feature)

**Purpose:** Move/rename markdown files while automatically updating all references

**Usage:**
```bash
# Move file
markdown-doc mv docs/old-location.md docs/new-location.md

# Rename file
markdown-doc mv AGENTS.md CONTRIBUTORS.md

# Preview changes without applying
markdown-doc mv source.md dest.md --dry-run
```

**Behavior:**
- Scans all markdown files for references to the source file
- Updates `[text](old-path.md)` → `[text](new-path.md)`
- Updates `[text](old-path.md#section)` → `[text](new-path.md#section)`
- Updates references in catalog files
- Atomic operation (all updates succeed or all fail)
- Backup files created by default (`--no-backup` to disable)

**Exit codes:**
- 0: Success (file moved, all references updated)
- 1: File not found
- 2: Destination exists (unless `--force`)
- 3: Invalid path arguments
- 4: I/O error during move
- 5: Reference update failed (partial state, requires manual fix)

### 2. `markdown-doc catalog` (Core Feature)

**Purpose:** Generate/update centralized documentation catalog with complete table of contents for every file

**Rationale:**

With 388+ markdown files, discovering relevant documentation becomes a major friction point. Developers and agents waste time grepping for keywords or manually browsing directories when they need specific information. The catalog solves this by providing:

1. **Single entry point** - One file to search/browse for all documentation
2. **Complete visibility** - Every heading in every file is indexed
3. **Context at a glance** - TOC structure reveals document organization without opening files
4. **Agent optimization** - AI agents can query the catalog to find relevant sections before fetching full documents

**Integration with `markdown-extract`:**

The catalog becomes a **discovery → extraction workflow**:

```bash
# 1. Find relevant sections in catalog
grep -i "redis" DOC_CATALOG.md
# → Shows AGENTS.md has section "Redis Database Allocation"

# 2. Extract just that section
markdown-extract "Redis Database Allocation" AGENTS.md
# → Returns only the relevant content

# Result: Agents fetch <1% of total docs instead of loading all 388 files
```

This two-step pattern reduces AI context window usage by 10-100x while improving accuracy (agents get exactly the relevant sections, not entire documents with tangential content).

**Human utility:**

- Quick reference: "Which file documents the NoDb pattern?" → Ctrl+F in catalog
- Structure validation: See if sections are organized logically across files
- Onboarding: New contributors scan catalog to understand documentation landscape
- Maintenance: Identify documentation gaps (files with sparse TOCs, missing READMEs)

**Output format (`DOC_CATALOG.md`):**
```markdown
# Documentation Catalog

Last updated: 2025-10-25 14:32:00 PST

## Catalog

- [AGENTS.md](AGENTS.md)
- [readme.md](readme.md)
- [docs/README.md](docs/README.md)
- [docs/god-tier-prompting-strategy.md](docs/god-tier-prompting-strategy.md)
- [wepppy/nodb/README.md](wepppy/nodb/README.md)
... (all 388 files)

---

## AGENTS.md

- [Authorship](#authorship)
- [Core Directives](#core-directives)
- [Repository Overview](#repository-overview)
  - [NoDb Philosophy](#nodb-philosophy)
  - [Redis Database Allocation](#redis-database-allocation)
...

---

## readme.md

- [WEPPpy](#wepppy)
- [Core Architecture](#core-architecture)
...
```

**Usage:**
```bash
# Generate catalog
markdown-doc catalog

# Regenerate from scratch
markdown-doc catalog --regen

# Specify output location
markdown-doc catalog --output DOCS_INDEX.md
```

**Performance requirements:**

- **Concurrent file reading:** Must read and parse files in parallel (not sequentially)
- **Target performance:** Complete catalog generation for 388 files in <5 seconds
- **Scalability:** Gracefully handle 1000+ files without linear slowdown

**Rationale:** Sequential file reading would take 10-30 seconds for 388 files. Concurrent reading achieves <5 seconds, making catalog regeneration fast enough to run on every doc change (watch mode, CI, pre-commit hooks).

### 3. `markdown-doc lint` (Quality Gate)

**Validation rules:**
- **broken-links:** Internal file references resolve
- **broken-anchors:** `#section` anchors exist in target files
- **duplicate-anchors:** No duplicate heading IDs within a file (headings become anchors)
- **heading-hierarchy:** No skipped levels (h1 → h3 invalid)
- **required-sections:** Templates have mandatory sections
- **toc-sync:** TOC markers match actual headings (if present)

**Duplicate anchor detection rationale:**

Markdown renderers generate anchor IDs from headings. Duplicate headings in the same file create ambiguous links:

```markdown
## Configuration
...content...

## Configuration  <!-- ❌ Duplicate anchor #configuration -->
...different content...
```

When you link to `file.md#configuration`, which section do you get? The first? The last? Implementation-dependent.

**How linter handles duplicates:**

```
❌ docs/guide.md:45: Duplicate anchor 'configuration' (also at line 12)
   Suggestion: Rename to "Configuration (Advanced)" or "CLI Configuration"
```

**Common duplicate patterns to catch:**
- Generic headings: "Overview", "Examples", "Notes" appearing multiple times
- Numbered sections: "1. Setup", "1. Usage" (numbers get stripped from anchors)
- Case variations: "API Reference" and "Api reference" both → `#api-reference`

**Output:**
```
❌ docs/guide.md:42: Broken link to 'missing.md'
❌ AGENTS.md:120: Link anchor '#nonexistent' not found in 'readme.md'
❌ tutorial.md:45: Duplicate anchor 'overview' (also at line 8)
⚠️  tutorial.md:15: Heading level skip (h2 → h4)
✅ 385 files validated, 3 errors, 1 warning
```

---

## Deliverables

### Phase 1: Foundation

- [ ] Rust project scaffolding (Cargo.toml, CI setup)
- [ ] Configuration parser (`.markdown-doc.toml`)
- [ ] Shared markdown parsing utilities
- [ ] `catalog` command with concurrent file reading (required)
- [ ] `toc` command (read/write TOC markers)
- [ ] Performance benchmarks (verify <5s for 388 files)

### Phase 2: Quality Gates

- [ ] `lint` command with broken-links rule
- [ ] `lint` broken-anchors rule
- [ ] `lint` duplicate-anchors rule
- [ ] `lint` heading-hierarchy rule
- [ ] `lint` required-sections rule
- [ ] `validate` template checking
- [ ] CI integration docs

### Phase 3: Refactoring Support

- [ ] `mv` command (move/rename with link updates)
- [ ] `refs` command (find references)
- [ ] Link updating engine (core library)
- [ ] Atomic operation guarantees

### Phase 4: Intelligence

- [ ] `search` command (full-text)
- [ ] Index building/caching
- [ ] Performance optimization (>100 files)
- [ ] Documentation and examples

---

## Dependencies

### Technical Dependencies

- Existing `markdown-extract` / `markdown-edit` source code (reference implementation)
- Rust markdown parser (likely `pulldown-cmark`)
- TOML parser (`toml` crate)
- File watching (future: `notify` crate)

### Human Dependencies

- Roger: Architecture decisions, acceptance criteria
- Agent: Implementation, testing, documentation

---

## Risks and Mitigation

| Risk | Impact | Likelihood | Mitigation |
|------|--------|------------|------------|
| Link update introduces bugs | High | Medium | Comprehensive tests, dry-run mode, atomic operations |
| Performance issues on 388+ files | Medium | Low | Concurrent file reading (required), parallel processing, incremental indexing |
| Complex link patterns not handled | Medium | Low | Start with simple patterns, extend iteratively |
| Configuration too complex | Low | Low | Start minimal, add options as needed |

---

## Milestones

- [ ] 1: Demo `catalog` command (verify concurrent reading works, <5s for 388 files)
- [ ] 2: Run `lint` in CI
- [ ] 3: Safe file moves working
- [ ] 4: Full release

---

## References

- [tools/README.markdown-tools.md](../../tools/README.markdown-tools.md) - Existing markdown tools
- [docs/prompt_templates/](../../prompt_templates/) - Template definitions
- [AGENTS.md](../../../AGENTS.md) - Documentation patterns
- [docs/god-tier-prompting-strategy.md](../../god-tier-prompting-strategy.md) - Agent workflows

---

## Notes

- `mv` command is high-value for refactoring workflows
- Agent autonomy: This tool should enable agents to maintain docs
