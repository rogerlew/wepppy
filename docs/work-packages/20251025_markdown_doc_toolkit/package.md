# Work Package: markdown-doc Toolkit

**Status:** Phase 3 complete – integration pending  
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

## Status Update (2025-10-30)

- Phase 1 (catalog + lint broken-links) and Phase 2 (quality gates, validate/toc, severity tuning) are complete and shipped in the `/workdir/markdown-extract` workspace.
- Phase 3 refactor tooling (`markdown-doc mv`, `markdown-doc refs`, link graph core) is implemented with comprehensive tests (`cargo test --all`) and documented automation workflows.
- Documentation (README + architecture notes) now covers catalog, lint, validate, toc, mv, refs, JSON outputs, safety guarantees, and agent integration patterns; complex refactor fixtures live under `tests/markdown-doc/refactor/complex/`.
- Outstanding integration work: align markdown-doc CI with `/workdir/wepppy` pipelines (fmt/clippy/test/bench), decide on link-graph caching + directory-move roadmap, apply optional doc refinements (command × exit-code table, README polish), and scope Phase 4 (`search`/`watch`).
- Release-ready binaries installed at `/usr/local/bin`; ready for parent repo adoption pending CI + RFC approval.

---

## Objectives

### Primary Goals

1. **Reduce documentation maintenance burden** by 80% through automation
2. **Prevent documentation drift** with automated validation gates
3. **Enable safe doc refactoring** with automatic link updating
4. **Improve discoverability** through centralized catalog and search

### Success Criteria

**MVP Exit (First Release):**
- [x] `catalog` + `lint broken-links` working end-to-end with selective scanning and JSON output
- [x] Configuration loader with defaults fallback and precedence hierarchy
- [x] Broken internal links detected with configurable severity (zero unintended false positives via ignore lists)
- [x] `DOC_CATALOG.md` auto-generated in <5 seconds for 388 files
- [x] Concurrent safety verified (atomic temp-file writes, no race conditions)
- [x] CLI acceptance tests passing (exit codes, output formats, selective scanning)
- [x] Pre-commit hook and GitHub Actions examples documented

**Full Toolkit (Post-MVP):**
- [x] Files can be moved/renamed without breaking references (`mv` command - Phase 3)
- [x] TOCs auto-update on file changes (`toc` command - Phase 2)
- [x] Template validation enforced for AGENTS.md, README.md, work packages (`validate` command - Phase 2)
- [x] All lint rules operational (broken-anchors, duplicate-anchors, heading-hierarchy, required-sections - Phase 2)
- [x] Severity tuning and per-path exemptions configured (Phase 2)

### Non-Goals (Initial Release)

- External link checking (can add later with caching)
- PDF/HTML export (separate feature)
- Live preview server (separate feature)
- Git integration for metadata (can extract from git separately)

---

## Scope

### In Scope (MVP - First Release)

**Core Commands:**
- `markdown-doc catalog` - Generate/update `DOC_CATALOG.md`
- `markdown-doc lint` - Validate broken links (additional rules in Phase 2)

**Infrastructure:**
- `.markdown-doc.toml` configuration file with defaults fallback
- Shared markdown parsing library (pulldown-cmark wrapper)
- Exit codes and error handling conventions
- Agent-friendly output formats (plain text, JSON, SARIF)
- Selective scanning (`--path`, `--staged` flags)
- Concurrent file reading with atomic writes

### Out of Scope (Post-MVP / Future Phases)

**Phase 2: Quality Gates**
- `lint` additional rules (broken-anchors, duplicate-anchors, heading-hierarchy, required-sections)
- `validate` - Template compliance checking
- `toc` - Generate/update table of contents
- Severity tuning and ignore lists

**Phase 3: Refactoring Support**
- `mv` - Move/rename files with automatic link updates
- `refs` - Find references to files/sections

**Phase 4: Intelligence (Deferred)**
- `search` - Search across all documentation (pending acceptance criteria: latency, ranking, snippet quality)
- `watch` mode - Auto-regenerate on file changes
- `stats` - Documentation health metrics
- `meta` - Cross-reference maintenance
- `sync`, `refactor`, `export` commands
- AI context optimization features

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

# Severity tuning (Phase 2)
[lint.severity]
broken-links = "error"
broken-anchors = "error"
duplicate-anchors = "warning"
heading-hierarchy = "warning"

# Per-path exemptions (Phase 2)
[[lint.ignore]]
path = "_legacy_*/**"
rules = ["broken-links", "heading-hierarchy"]

[[lint.ignore]]
path = "tmp_*/**"
rules = ["*"]  # Ignore all rules

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

### Configuration Precedence

1. **Command-line flags** (highest priority) - e.g., `--config path/to/.markdown-doc.toml`
2. **`.markdown-doc.toml` in current directory** - project-specific overrides
3. **`.markdown-doc.toml` in git root** - repository-wide defaults
4. **Built-in defaults** (lowest priority) - shipped with binary

**Fallback behavior:** If no config file exists, tool operates with sensible defaults (lint all rules as errors, no exclusions, catalog to `DOC_CATALOG.md`). Partial configs merge with defaults (missing sections inherit built-in values, not fail-closed).

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
# Generate catalog (full scan)
markdown-doc catalog

# Selective scanning (faster for incremental updates)
markdown-doc catalog --path docs/
markdown-doc catalog --staged  # Only git staged files

# Regenerate from scratch
markdown-doc catalog --regen

# Specify output location
markdown-doc catalog --output DOCS_INDEX.md

# Machine-readable output for agents
markdown-doc catalog --format json > catalog.json
```

**Output formats:**
- **Plain text** (default): Human-readable markdown with TOCs
- **JSON** (`--format json`): Structured data for agent consumption
  ```json
  {
    "last_updated": "2025-10-25T14:32:00-07:00",
    "file_count": 388,
    "files": [
      {
        "path": "AGENTS.md",
        "headings": [
          {"level": 1, "text": "Authorship", "anchor": "authorship"},
          {"level": 2, "text": "Core Directives", "anchor": "core-directives"}
        ]
      }
    ]
  }
  ```

**Performance requirements:**

- **Concurrent file reading:** Must read and parse files in parallel (not sequentially)
- **Target performance:** Complete catalog generation for 388 files in <5 seconds
- **Scalability:** Gracefully handle 1000+ files without linear slowdown
- **Concurrency safety:** Atomic temp-file writes prevent race conditions when multiple processes run catalog simultaneously (e.g., concurrent CI jobs, agents)
- **No global locks:** Git handles conflict resolution if multiple writers target the same output file

**Rationale:** Sequential file reading would take 10-30 seconds for 388 files. Concurrent reading achieves <5 seconds, making catalog regeneration fast enough to run on every doc change (watch mode, CI, pre-commit hooks). Atomic writes ensure safe concurrent execution without coordination.

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

**CLI flags for selective scanning:**
```bash
# Scan specific directory
markdown-doc lint --path docs/

# Scan only staged files (fast pre-commit check)
markdown-doc lint --staged

# JSON output for CI integration
markdown-doc lint --format json > lint-report.json

# SARIF format for GitHub Code Scanning
markdown-doc lint --format sarif > results.sarif
```

**Structured output example (JSON):**
```json
{
  "summary": {
    "files_scanned": 385,
    "errors": 3,
    "warnings": 1
  },
  "violations": [
    {
      "rule": "broken-links",
      "severity": "error",
      "file": "docs/guide.md",
      "line": 42,
      "message": "Broken link to 'missing.md'"
    }
  ]
}
```

---

## Deliverables

### Phase 1: Foundation (MVP - Single Vertical Slice)

**MVP Scope:** Ship `catalog` + `lint broken-links` + config loader as first working end-to-end workflow

- [x] Rust project scaffolding (Cargo.toml, CI setup)
- [x] Configuration parser (`.markdown-doc.toml`) with defaults fallback
- [x] Shared markdown parsing utilities (pulldown-cmark wrapper)
- [x] `catalog` command with concurrent file reading (required)
  - [x] Selective scanning (--path, --staged flags for partial runs)
  - [x] Atomic temp-file writes (safe for concurrent access)
  - [x] JSON output mode (--format json for agent consumption)
- [x] `lint` command with broken-links rule only (deferred: other rules)
  - [x] Configurable severity (error/warning/ignore per pattern)
  - [x] Ignore lists for known edge cases (e.g., external refs, generated files)
  - [x] JSON/SARIF output for CI integration
- [x] CLI acceptance tests (verify exit codes, output formats, selective scanning)
- [x] Performance benchmarks (verify <5s for 388 files, concurrent safety)

### Phase 2: Quality Gates

- [x] `toc` command (read/write TOC markers) - moved from Phase 1
- [x] `lint` additional rules:
  - [x] broken-anchors rule
  - [x] duplicate-anchors rule
  - [x] heading-hierarchy rule
  - [x] required-sections rule (uses same schema definitions as `validate`)
- [x] `validate` command - template compliance checking
  - [x] Clarify relationship with `lint required-sections`: both read `[schemas]` config
  - [x] Different CLI messaging: `lint` for incremental checks, `validate` for full template conformance
- [x] Severity tuning system:
  - [x] Per-path exemptions (e.g., `_legacy_*` directories)
  - [x] Downgradeable severities (error → warning for specific rules)
  - [x] `.markdown-doc-ignore` file support (like .gitignore)
- [x] CI integration docs with selective scanning examples

### Phase 3: Refactoring Support

- [x] `mv` command (move/rename with link updates)
- [x] `refs` command (find references)
- [x] Link updating engine (core library)
- [x] Atomic operation guarantees

### Phase 4: Intelligence

- [ ] `search` command (full-text) - **Deferred pending acceptance criteria**
  - [ ] Required metrics before implementation:
    - Latency target (e.g., <500ms for 388 files)
    - Ranking algorithm (relevance scoring approach)
    - Snippet extraction quality (context around matches)
  - [ ] Decision: Index building strategy (incremental vs full rebuild)
- [ ] Index building/caching (if search proceeds)
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

- [x] **M1: MVP vertical slice** - `catalog` + `lint broken-links` + config loader working end-to-end
  - Acceptance: CLI can scan 388 files in <5s, output JSON, run selectively with `--path` flag
  - Exit codes correct, error messages actionable
  - Atomic temp-file writes verified (concurrent safety test)
- [ ] **M2: CI integration** - Run `lint` in CI with zero false positives (pending `/workdir/wepppy` pipeline alignment)
  - Acceptance: Pre-commit hook script, GitHub Actions workflow example
  - Ignore lists tuned for wepppy's legacy directories
  - SARIF output working with GitHub Code Scanning
- [x] **M3: Safe file moves** - `mv` command with atomic link updates working
  - Acceptance: Can reorganize docs/ without breaking references
  - Dry-run mode accurate, backups created
- [ ] **M4: Full release** - All Phase 1-3 features complete and adopted in parent repo
  - Acceptance: Documentation complete, wctl integration, agent workflows documented, markdown-doc wired into `/workdir/wepppy` CI

---

## References

- [tools/README.markdown-tools.md](../../tools/README.markdown-tools.md) - Existing markdown tools
- [docs/prompt_templates/](../../prompt_templates/) - Template definitions
- [AGENTS.md](../../../AGENTS.md) - Documentation patterns
- [docs/god-tier-prompting-strategy.md](../../god-tier-prompting-strategy.md) - Agent workflows

---

## CLI Design and Integration

### Selective Scanning Modes

All commands support selective scanning to avoid full repository scans:

```bash
# Scan specific directory
markdown-doc <command> --path docs/work-packages/

# Scan only git staged files (pre-commit workflow)
markdown-doc <command> --staged

# Scan specific files (space-separated)
markdown-doc <command> file1.md file2.md

# Full repository scan (default when no flags provided)
markdown-doc <command>
```

**Use cases:**
- **Pre-commit hooks:** `--staged` for fast incremental checks
- **CI per-PR:** `--path` to scan only changed directories
- **Full validation:** No flags for complete repository audit
- **wctl integration:** `wctl doc-lint --staged` wraps `markdown-doc lint --staged`

### Output Formats

Commands support multiple output formats for different consumers:

| Format | Flag | Consumer | Use Case |
|--------|------|----------|----------|
| Plain text | (default) | Humans | Terminal output, manual review |
| JSON | `--format json` | Agents, scripts | Programmatic parsing, automation |
| SARIF | `--format sarif` | GitHub Code Scanning | Security/quality dashboards |

**Agent workflow example:**
```bash
# Agent checks for broken links before committing doc changes
output=$(markdown-doc lint --staged --format json)
if [ "$(echo $output | jq '.summary.errors')" -gt 0 ]; then
  echo "Documentation validation failed"
  echo $output | jq '.violations'
  exit 1
fi
```

### wctl Integration

Add convenience wrappers to `wctl` for common workflows:

```bash
# Lint documentation
wctl doc-lint              # Full scan
wctl doc-lint --staged     # Pre-commit check
wctl doc-lint --path PATH  # Selective scan

# Regenerate catalog
wctl doc-catalog           # markdown-doc catalog

# Update TOC in specific file
wctl doc-toc FILE          # markdown-doc toc FILE --update

# Move file safely
wctl doc-mv SRC DEST       # markdown-doc mv SRC DEST --dry-run (confirm) → mv
```

### CI Integration Examples

**Pre-commit hook** (`.git/hooks/pre-commit`):
```bash
#!/bin/bash
markdown-doc lint --staged --format json > /tmp/lint-result.json
errors=$(jq '.summary.errors' /tmp/lint-result.json)
if [ "$errors" -gt 0 ]; then
  echo "❌ Documentation validation failed:"
  jq '.violations[] | "\(.file):\(.line): \(.message)"' /tmp/lint-result.json
  exit 1
fi
```

**GitHub Actions workflow** (`.github/workflows/docs-lint.yml`):
```yaml
name: Documentation Quality

on: [pull_request]

jobs:
  lint:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Install markdown-doc
        run: cargo install markdown-doc
      - name: Validate documentation
        run: markdown-doc lint --format sarif > results.sarif
      - name: Upload results
        uses: github/codeql-action/upload-sarif@v3
        with:
          sarif_file: results.sarif
```

### Configuration Relationship: `lint` vs `validate`

Both commands read the same `[schemas]` configuration section but serve different purposes:

**`markdown-doc lint`** - Incremental quality checks
- Runs fast rule-based validations (broken links, heading hierarchy)
- `required-sections` rule uses schema definitions for section checks
- Suitable for pre-commit hooks and rapid feedback
- Focus: Catch common mistakes quickly

**`markdown-doc validate`** - Full template conformance
- Deep structural validation against template schemas
- Checks section order, nesting depth, content patterns
- Slower, more comprehensive analysis
- Focus: Enforce documentation standards for critical files (AGENTS.md, work packages)

**CLI messaging difference:**
```bash
# lint - shows individual rule violations
$ markdown-doc lint AGENTS.md
❌ AGENTS.md:45: Missing required section 'Core Directives'

# validate - shows template conformance status
$ markdown-doc validate AGENTS.md --schema agents
❌ AGENTS.md does not conform to 'agents' schema:
   - Missing required section: 'Core Directives' (expected after 'Authorship')
   - Section order violation: Found 'Repository Overview' before 'Core Directives'
```

---

## Outstanding Work (2025-10-30)

- Align markdown-doc CI with `/workdir/wepppy` automation (fmt, clippy, tests, benchmarks) and expose `wctl` wrappers.
- Decide on link-graph caching and directory-move roadmap before scheduling Phase 4 (`search`, `watch`) work.
- Publish release notes, command × exit-code quick reference, and incremental README polish as features evolve.
- Coordinate adoption timeline with parent repo stakeholders (RFC review, go/no-go, post-integration telemetry plan).
- Distribute `.markdown-doc-ignore` (includes `.docker-data/**`) with rollout notes so catalog/lint skip docker volumes; keep `sudo wctl restore-docker-data-permissions` documented for legacy environments.

### Adoption Plan (Lead Tasks – 2025-11 Sprint)

- **CI Integration (Week of Nov 3):**
  - Extend GitHub Actions / wctl automation to run `cargo fmt --check`, `cargo clippy`, `cargo test --all`, `wctl doc-lint --format sarif`, and `wctl doc-bench --path docs --warmup 0 --iterations 1`.
  - Surface lint JSON/SARIF results in PR checks and add gating thresholds (errors fail, warnings allowed temporarily).
  - ✅ `docs-quality.yml` workflow on self-hosted runner now executes doc-lint/doc-bench (scoped to documentation paths so `.docker-data` stays excluded), normalizes SARIF to CodeQL v3 expectations, and conditionally runs Rust checks when `MARKDOWN_DOC_WORKSPACE` (or known workspace paths) expose a Cargo project; follow-up: set the env var on the runner so fmt/clippy/test always execute.
- **Lint Backlog Triage (Nov 4–7):**
  - Bucket current 36 broken-link errors by category (missing files vs anchor drift) and assign fixes or ignore entries with justification.
  - Track remediation progress in `tracker.md` (mark resolved vs deferred with rationale).
- **Documentation & Comms (Nov 6–8):**
  - Publish quick-start guide in `tools/README.markdown-tools.md` outlining new `wctl doc-*` flows and `.markdown-doc-ignore` usage.
  - Issue release notes / adoption announcement referencing RFC decisions, install steps, and CI expectations.
- **Phase 4 Decision Prep (by Nov 11):**
  - Gather telemetry from lint runs (frequency, runtime, error rate) to inform caching/search scope.
  - Present recommendation on link-graph caching vs. watch mode to stakeholders for Q1 2026 planning.

---

## Notes

- `mv`/`refs` toolchain now ships with complex fixtures validating multi-file refactors.
- Agents can rely on structured JSON/SARIF outputs and `.markdown-doc-ignore` for safe automation.
- **Review integrated:** Lead developer feedback (2025-10-30) has been incorporated throughout the document.
