# Initial Requirements - markdown-doc Toolkit

**Date:** 2025-10-25  
**Author:** Roger Lew, Claude Sonnet 4.5

---

## User Story

**As a:** Solo developer maintaining 388+ markdown files across a large codebase  
**I want:** Automated documentation management tooling  
**So that:** I can keep docs accurate and discoverable without manual burden

---

## Core Use Cases

### 1. Daily Development

**Scenario:** Developer modifies code, needs to update related docs

```bash
# Check what would break before moving a file
markdown-doc refs wepppy/nodb/README.md

# Move file and update all references automatically
markdown-doc mv wepppy/nodb/README.md wepppy/nodb/core/README.md

# Validate docs after changes
markdown-doc lint

# Regenerate catalog to reflect new structure
markdown-doc catalog
```

### 2. CI/CD Quality Gates

**Scenario:** Prevent broken docs from merging

```yaml
# .github/workflows/docs.yml
- name: Validate documentation
  run: |
    markdown-doc lint --strict
    markdown-doc validate docs/work-packages/**/*.md
```

**Expected behavior:**
- Exit code 1 if broken links found
- Exit code 1 if required sections missing
- Exit code 0 if all checks pass

### 3. Refactoring Workflows

**Scenario:** Reorganizing documentation structure

```bash
# Preview what would change
markdown-doc mv docs/old-structure/ docs/new-structure/ --dry-run

# Apply changes
markdown-doc mv docs/old-structure/ docs/new-structure/

# Verify no broken links remain
markdown-doc lint
```

### 4. Discovery & Navigation

**Scenario:** Find documentation about specific topic

```bash
# Search all docs
markdown-doc search "NoDb singleton"

# Find what references a specific file
markdown-doc refs AGENTS.md

# Browse catalog
cat DOC_CATALOG.md
```

### 5. Agent Workflows

**Scenario:** AI agent needs to maintain documentation

```bash
# Agent extracts section, modifies it, updates file
markdown-extract "Installation" README.md > section.md
# ... agent modifies section.md ...
markdown-edit README.md replace "Installation" --with section.md

# Agent validates changes
markdown-doc lint README.md
markdown-doc toc README.md --update

# Agent updates catalog
markdown-doc catalog
```

---

## Feature Priorities

### Must Have (MVP)

1. **`catalog`** - Generate `DOC_CATALOG.md` with file list + TOCs
2. **`lint`** - Broken internal link detection
3. **`toc`** - Generate/update table of contents
4. **`mv`** - Move/rename with automatic link updates

**Rationale:** These four commands solve 80% of the pain:
- Catalog improves discoverability
- Lint prevents breakage
- TOC reduces manual maintenance
- Move enables safe refactoring

### Should Have (Phase 2)

5. **`refs`** - Find references to files/sections
6. **`validate`** - Template compliance checking
7. **`search`** - Full-text search across docs

### Nice to Have (Future)

8. **`watch`** - Auto-regenerate on file changes
9. **`stats`** - Documentation health metrics
10. **`sync`** - Cross-reference maintenance

---

## Technical Requirements

### Performance

- Handle 388 files (current wepppy size)
- Gracefully scale to 1000+ files
- `catalog` completes in <5 seconds
- `lint` completes in <10 seconds
- `search` completes in <2 seconds

### Reliability

- Zero false positives for broken link detection
- Atomic operations (all updates succeed or all fail)
- Backup files created for destructive operations
- Idempotent operations (safe to run repeatedly)

### Usability

- Agent-executable (clear exit codes, parseable output)
- Dry-run mode for all destructive operations
- Helpful error messages (actionable, not cryptic)
- Minimal configuration (sensible defaults)

### Integration

- Works with existing `markdown-extract` / `markdown-edit`
- Respects `.gitignore` for file discovery
- CI-friendly (exit codes, JSON output mode)
- No runtime dependencies beyond binary

---

## Configuration Requirements

### `.markdown-doc.toml` Schema

```toml
[project]
name = "wepppy"
root = "."
exclude = ["_notes", "tmp_*", "_legacy_*"]

[catalog]
output = "DOC_CATALOG.md"
include = ["**/*.md"]
exclude = ["**/node_modules/**"]
include_toc = true
include_metadata = false  # future: file size, last modified

[lint]
rules = ["broken-links", "heading-hierarchy", "required-sections"]
max_heading_depth = 4
allow_external = true  # don't check external links (yet)

[toc]
marker_start = "<!-- TOC -->"
marker_end = "<!-- /TOC -->"
max_depth = 3
include_links = true

[templates]
directory = "docs/prompt_templates"
schemas = {
  "AGENTS.md" = ["Authorship", "Core Directives"],
  "README.md" = ["Overview"]
}

[search]
index_path = ".markdown-doc/index"
exclude_code_blocks = true
case_sensitive = false
```

### Override Hierarchy

1. Command-line flags (highest priority)
2. `.markdown-doc.toml` in current directory
3. `.markdown-doc.toml` in git root
4. Built-in defaults (lowest priority)

---

## Link Resolution Algorithm

### Supported Link Formats

```markdown
[text](relative/path.md)              # Relative path
[text](./relative/path.md)            # Explicit relative
[text](../parent/file.md)             # Parent directory
[text](/absolute/from/root.md)        # Absolute from project root
[text](file.md#section)               # With anchor
[text](#section)                      # Same-file anchor
```

### Resolution Rules

1. **Project root:** Git root or directory with `.markdown-doc.toml`
2. **Relative paths:** Relative to current file's directory
3. **Absolute paths:** Relative to project root
4. **Anchor validation:** Parse target file, check heading exists
5. **Case sensitivity:** Follow filesystem (Linux case-sensitive)

### Edge Cases

- `[](empty-link)` → Lint warning
- `[](missing.md)` → Lint error
- `[](file.md#missing-anchor)` → Lint error
- `[](../../../outside-project.md)` → Lint warning (external)
- `[text](http://external.com)` → Skip (external link)

---

## Command-Line Interface Design

### Global Flags

```
--config <path>      Path to .markdown-doc.toml
--quiet              Suppress non-error output
--verbose            Detailed output
--color <auto|always|never>
--help               Show help
--version            Show version
```

### Command Structure

```
markdown-doc <command> [options] [args]

Commands:
  catalog              Generate documentation catalog
  toc                  Generate/update table of contents
  lint                 Validate documentation
  mv                   Move/rename files with link updates
  refs                 Find references to files/sections
  search               Search documentation
  validate             Check against templates
  help                 Show help for commands
```

### Exit Codes

```
0   Success
1   Validation failure (lint errors, required sections missing)
2   Not found (file, section, anchor)
3   Invalid arguments
4   I/O error
5   Partial failure (some operations succeeded, some failed)
```

---

## Integration Points

### With Existing Tools

**markdown-extract:**
- Share markdown parsing logic
- Use same heading detection algorithm
- Consistent ATX/Setext support

**markdown-edit:**
- Share link updating patterns
- Same atomic operation approach
- Consistent backup file strategy

### With wctl

```bash
# Add to wctl utility
wctl doc-lint           → markdown-doc lint
wctl doc-catalog        → markdown-doc catalog
wctl doc-toc <file>     → markdown-doc toc <file> --update
```

### With CI/CD

```bash
# Pre-commit hook
markdown-doc lint || exit 1

# Post-commit hook
markdown-doc catalog --commit

# GitHub Actions
- run: markdown-doc lint --strict --json > report.json
```

---

## Test Scenarios

### Catalog Generation

```bash
# Input: 388 markdown files
# Expected: DOC_CATALOG.md with:
#   - Alphabetically sorted file list
#   - Each file's TOC extracted
#   - Total file count
#   - Last updated timestamp
```

### Link Validation

```bash
# Input: File with [link](missing.md)
# Expected: Exit code 1, error message with file:line

# Input: File with [link](file.md#missing)
# Expected: Exit code 1, error pointing to missing anchor

# Input: All valid links
# Expected: Exit code 0, success summary
```

### File Move

```bash
# Input: mv A.md B.md (5 files reference A.md)
# Expected:
#   - A.md renamed to B.md
#   - All 5 references updated
#   - Backup files created
#   - Exit code 0

# Input: mv A.md B.md --dry-run
# Expected:
#   - No files changed
#   - Preview of changes printed
#   - Exit code 0
```

---

## Open Questions

1. **Catalog format:** Should we use JSON/YAML instead of markdown for machine consumption?
2. **External links:** Should we check them (with caching) or always skip?
3. **Git integration:** Should `mv` automatically run `git mv`?
4. **Performance:** Should we build an index for large repos (>1000 files)?
5. **Custom rules:** Should linting support plugins or just built-in rules?

---

## Success Metrics

### Quantitative

- 50% reduction in time spent maintaining docs
- Zero broken links in production documentation
- <5 minutes to reorganize doc structure (previously hours)
- 100% catalog accuracy (no manual updates needed)

### Qualitative

- Developers confident refactoring docs
- Agents can safely maintain documentation
- New contributors find docs easily via catalog
- CI catches doc issues before merge

---

## Next Steps

1. Review this requirements doc with Roger
2. Create architectural design document
3. Set up Rust project skeleton
4. Implement `catalog` command (simplest, proves infrastructure)
5. Iterate based on feedback
