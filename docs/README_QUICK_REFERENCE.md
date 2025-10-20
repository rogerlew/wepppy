# README Documentation Standards - Quick Reference

This quick reference summarizes the README documentation standards for wepppy.

## Files Created

1. **`docs/templates/README_TEMPLATE.md`** — Standard template with 14 sections
2. **`docs/README_AUTHORING_GUIDE.md`** — Comprehensive 13KB authoring guide
3. **`tools/audit_readmes.py`** — Automated quality audit script
4. **`docs/README_AUDIT_REPORT.md`** — Current state analysis
5. **AGENTS.md** — Added "README Documentation Standards" section

## Quick Start

### Creating a New README

```bash
# Copy template to your module
cp docs/templates/README_TEMPLATE.md your/module/README.md

# Edit the file, filling in all sections
# Remove sections that don't apply

# Normalize spelling (preview first!)
diff -u your/module/README.md <(uk2us your/module/README.md)
uk2us -i your/module/README.md
```

### Required Elements

Every README must have:

1. **Header** with module name and one-line description
2. **"See also" link** to relevant AGENTS.md sections
3. **Overview** explaining what, why, and how
4. **At least one code example**
5. **Component/API documentation**

### Auditing README Quality

```bash
# Run audit on all README files
python tools/audit_readmes.py --verbose

# Review the report
cat docs/README_AUDIT_REPORT.md
```

## Template Sections

The template includes these sections (customize as needed):

1. **Header** — Module name, description, AGENTS.md link
2. **Overview** — Purpose and context
3. **Quick Start** — Minimal working example
4. **Components At A Glance** — Table of key classes/functions
5. **Architecture / Design** — Patterns and data flow
6. **Usage / API Reference** — Detailed API documentation
7. **Common Workflows** — Step-by-step guides
8. **File Structure** — Directory tree
9. **Produced Artifacts / Outputs** — Generated files
10. **Testing** — Test commands
11. **Operational Notes** — Performance, gotchas, monitoring
12. **Development Notes** — Extension patterns
13. **Troubleshooting** — Common issues and solutions
14. **References** — Links to related docs
15. **Version History / Changelog** — Major changes

## Scoring System

README files are scored 0-100:

- **Basic (40 pts):** Title (10), Overview (15), Code example (15)
- **Medium (30 pts):** AGENTS.md link (10), API docs (10), Substantial content (10)
- **Nice-to-have (30 pts):** Architecture (10), Testing (10), Troubleshooting (10)

Categories:
- **Excellent** (80-100): Complete and comprehensive
- **Good** (60-79): Well documented with minor gaps
- **Needs Improvement** (40-59): Missing key elements
- **Critical** (0-39): Requires immediate attention

## Current State (2025-10-20)

- **Total files:** 29
- **Excellent:** 2 (7%)
- **Good:** 3 (10%)
- **Needs Improvement:** 6 (21%)
- **Critical:** 18 (62%)

## Priority Actions

### High Priority (Critical - 0-39 points)

Top 5 files needing immediate work:

1. `tests/README.md` (0) — Missing everything
2. `wepppy/all_your_base/README.md` (10) — Missing overview and examples
3. `wepppy/nodb/mods/ash_transport/README.md` (20) — 93 lines but no examples
4. `wepppy/wepp/soils/README.md` (20) — Technical content needs structure
5. `wepppy/microservices/README.md` (20) — Missing overview

### Medium Priority (Needs Improvement - 40-59 points)

Files that would benefit from enhancement:

1. `wctl/README.md` (50) — Add title and AGENTS.md link
2. `wepppy/query_engine/README.md` (50) — Add AGENTS.md link
3. `wepppy/weppcloud/README.md` (45) — Add overview section
4. `wepppy/nodb/mods/omni/README.md` (45) — Add overview
5. `weppcloudR/README.md` (40) — Add AGENTS.md link

## Writing Guidelines

### Style
- Concise and scannable
- Use headings, tables, and lists
- Example-driven (show, don't just tell)
- Technical but accessible
- Link instead of duplicate

### "See Also" Pattern

Always include at the top:

```markdown
> **See also:** [AGENTS.md](../../AGENTS.md) for [Section Name], 
> [Another Section], and [Related Topic] sections.
```

### Code Examples

Include working examples with:
- All necessary imports
- Complete, runnable code
- Expected output or behavior
- Comments explaining key steps

### Integration with AGENTS.md

| README | AGENTS.md |
| --- | --- |
| Module-specific details | Repository-wide patterns |
| API usage examples | Architectural principles |
| File structure | Development workflows |
| Troubleshooting specifics | General best practices |

## Tools and Commands

```bash
# Find all README files
find . -name "README.md" -o -name "readme.md"

# Audit README quality
python tools/audit_readmes.py --output docs/README_AUDIT_REPORT.md

# Normalize spelling (always preview first!)
diff -u path/to/README.md <(uk2us path/to/README.md)
uk2us -i path/to/README.md

# Search for missing sections
grep -L "## Overview" **/README.md
```

## Examples of Well-Documented Modules

Study these as patterns:

- `services/status2/README.md` (80 pts) — Microservice specification
- `services/preflight2/README.md` (80 pts) — Design rationale and architecture
- `docker/README.md` (70 pts) — Operational guide
- `wepppy/nodb/README.md` (60 pts) — Technical reference
- `wepppy/nodb/mods/ash_transport/README.md` — Complete workflow (needs examples to reach higher score)

## Resources

- **Full Guide:** `docs/README_AUTHORING_GUIDE.md`
- **Template:** `docs/templates/README_TEMPLATE.md`
- **Audit Tool:** `tools/audit_readmes.py`
- **Audit Report:** `docs/README_AUDIT_REPORT.md`
- **AGENTS.md:** "README Documentation Standards" section

## When to Update

Update README when you:
- Add/remove public APIs
- Change architecture
- Introduce breaking changes
- Add dependencies
- Discover common issues
- Add significant features

Commit README with code changes to keep documentation in sync.

---

**For complete details, see:** `docs/README_AUTHORING_GUIDE.md`
