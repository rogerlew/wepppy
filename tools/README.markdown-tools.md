# Markdown Extract

[![Crates.io](https://img.shields.io/crates/v/markdown-extract)](https://crates.io/crates/markdown-extract)
[![Docker Pulls](https://img.shields.io/docker/pulls/sean0x42/markdown-extract)](https://hub.docker.com/r/sean0x42/markdown-extract)
[![Build & Test](https://github.com/sean0x42/markdown-extract/actions/workflows/build_and_test.yml/badge.svg)](https://github.com/sean0x42/markdown-extract/actions/workflows/build_and_test.yml)


Extract sections of a markdown file with a regular expression.

---

## ⚠️ For AI Coding Agents

**Both `markdown-extract` and `markdown-edit` are pre-installed on this host at `/usr/local/bin`.**

These tools are designed specifically for AI agent workflows. You can invoke them directly without installation:

- **`markdown-extract`** - Read sections from Markdown files by heading pattern
- **`markdown-edit`** - Modify Markdown files with heading-aware operations (replace, append, insert, delete)

**Key benefits for agents:**
- ✅ Semantic operations on document structure (no brittle line numbers)
- ✅ Safety-first: `--dry-run` for previews, automatic backups, duplicate guards
- ✅ Predictable exit codes for error handling (0-6)
- ✅ Pipeline-friendly (stdin/stdout, handles broken pipes gracefully)
- ✅ Reduces context window usage by extracting only relevant sections

**Quick examples:**
```bash
# Extract a specific section to reduce context
markdown-extract "Installation" README.md

# Preview changes before applying
markdown-edit notes.md append-to "Today" --with-string "- Task completed\\n" --dry-run

# Replace section body while keeping heading
markdown-edit guide.md replace "Setup" --with-string "New content\\n" --keep-heading
```

See full documentation below for complete reference and advanced workflows.

---

## Usage

Given a document called `my-document.md`:

```markdown
# Welcome

This is my amazing markdown document.

## Extract me!

This section should be pulled out.
```

You can extract the second section with the following command:

```console
$ markdown-extract "Extract me!" my-document.md
## Extract me!

This section should be pulled out.
```

Pass `-` as the file argument to read Markdown from standard input:

```console
$ cat my-document.md | markdown-extract "Extract me!" -
```

### Quick Reference

| Flag | Short | Description |
|------|-------|-------------|
| `--all` | `-a` | Extract all matching sections (default: first only) |
| `--case-sensitive` | `-s` | Match pattern exactly (default: case-insensitive) |
| `--no-print-matched-heading` | `-n` | Omit heading line from output (body only) |
| `--help` | `-h` | Show help message |
| `--version` | `-V` | Show version |

**Basic syntax:**
```
markdown-extract [OPTIONS] <PATTERN> <FILE>
```

### Pattern Matching

Patterns are **case-insensitive regex** by default, matched against the heading text (without the `#` markers). Use `--case-sensitive` for exact matches.

```console
# Match any heading containing "install"
$ markdown-extract "install" docs.md

# Exact match with anchors
$ markdown-extract "^Installation$" docs.md

# Multiple possibilities with alternation
$ markdown-extract "Setup|Configuration" docs.md

# Subsections only (three or more #)
$ markdown-extract "^###" docs.md
```

### Extracting Multiple Sections

By default, `markdown-extract` returns only the **first match** and exits. Use `--all` to extract every matching section:

```console
# Get all "Usage" sections across the document
$ markdown-extract "Usage" docs.md --all

# Extract all troubleshooting subsections
$ markdown-extract "^### .* Error" docs.md --all
```

### Output Control

The `--no-print-matched-heading` (or `-n`) flag omits the heading line, returning only the section body:

```console
# Get just the content, no heading
$ markdown-extract "Installation" README.md -n

# Useful for extracting code blocks
$ markdown-extract "Example" docs.md -n | grep -A5 "```bash"
```

### Pipeline-Friendly Behavior

`markdown-extract` handles broken pipes gracefully—if you pipe output to `head`, `less`, or any command that closes early, the CLI exits quietly without error messages.

**Reading from stdin:**
```console
# Process generated content
$ generate-docs | markdown-extract "Installation" -

# Chain with other tools
$ curl https://example.com/docs.md | markdown-extract "API" -

# Filter before extracting
$ cat large-docs.md | grep -v "DRAFT" | markdown-extract "Section" -
```

**Piping output:**
```console
# Preview first 10 lines of a long section
$ markdown-extract "API Reference" docs.md | head -10

# Page through output
$ markdown-extract "Changelog" CHANGELOG.md | less
```

### Common Workflows

**Extract release notes for CI/CD:**
```console
$ markdown-extract "^v1\.2\.0$" CHANGELOG.md > release-notes.txt
```

**Pull API documentation into a script:**
```console
API_DOCS=$(markdown-extract "Authentication" docs/api.md)
echo "$API_DOCS" | process-documentation
```

**Combine with other tools:**
```console
# Count lines in a section
$ markdown-extract "Configuration" README.md | wc -l

# Search within a section
$ markdown-extract "Troubleshooting" docs.md | grep -i "error"

# Extract multiple sections and diff them
$ diff <(markdown-extract "Old API" docs.md) <(markdown-extract "New API" docs.md)
```

**Find all matching headings:**
```console
# See what matches without extracting
$ markdown-extract ".*" docs.md --all | grep "^#"
```

**Process dynamic content:**
```console
# Extract from HTTP response
$ curl -s https://api.example.com/docs | markdown-extract "Endpoints" -

# Extract from command output
$ ./generate-report | markdown-extract "Summary" -

# Chain multiple extractions
$ cat docs.md | markdown-extract "Chapter 1" - | markdown-extract "Summary" -
```

### Section Boundaries

A section includes:
- The matched heading line (unless `-n` is used)
- All content until the next heading of **equal or higher level**
- Subsections are included in their parent section

```markdown
## Parent Section     ← Matched heading
Content here.

### Child Section     ← Included (lower level)
More content.

### Another Child     ← Also included
Final content.

## Next Section        ← Boundary (same level)
Not included.
```

**Examples:**

```console
# Extracts "Parent" + both child sections
$ markdown-extract "Parent Section" doc.md

# Extracts only "Child Section" (no siblings)
$ markdown-extract "Child Section" doc.md
```

### Heading Support

Both **ATX** (`#`) and **Setext** (underline) headings are supported:

```markdown
ATX Heading
===========

Setext level 1 heading

Subheading
----------

Setext level 2 heading

### ATX Level 3

Standard markdown heading
```

**Note:** Headings inside fenced code blocks are ignored:

````markdown
## Real Heading

```markdown
## Not a heading (inside code block)
```
````

### Error Handling & Exit Codes

| Exit Code | Meaning |
|-----------|---------|
| 0 | Success (match found and printed) |
| 1 | No matches found for pattern |
| 2 | File I/O error or invalid UTF-8 |

```console
# Check if a section exists
$ markdown-extract "Deprecated" docs.md > /dev/null 2>&1 && echo "Found"

# Fail CI build if required section is missing
$ markdown-extract "^License$" README.md || exit 1
```

### Limitations

- **UTF-8 only**: Non-UTF-8 files will error
- **Regex size limit**: Patterns over 100 KB are rejected
- **Full document scan**: Large files (>100 MB) may have performance implications

### For AI Agent Workflows

**🤖 Note: These tools are pre-installed at `/usr/local/bin` on this system. You can use them directly in any workflow without installation steps.**

`markdown-extract` excels at keeping agent context windows lean:

**Pre-filter knowledge bases:**
```bash
# Extract only relevant sections for the agent
markdown-extract "API.*Auth" knowledge-base.md > context.txt
```

**Dynamic prompt assembly:**
```python
import subprocess

def get_section(pattern, file):
    result = subprocess.run(
        ["markdown-extract", pattern, file],
        capture_output=True, text=True
    )
    return result.stdout if result.returncode == 0 else None

# Pull targeted instructions
auth_docs = get_section("Authentication", "docs/api.md")
if auth_docs:
    prompt += f"\n\nRelevant documentation:\n{auth_docs}"
```

**Automated context refresh:**
```bash
# Update agent context when docs change (cron/GitHub Actions)
markdown-extract "Quick Start" README.md > agent-context/quickstart.md
markdown-extract "^v.*" CHANGELOG.md --all > agent-context/releases.md
```

**Validation in CI:**
```bash
# Ensure required sections exist before deployment
required_sections=("Installation" "Usage" "License")
for section in "${required_sections[@]}"; do
  markdown-extract "^$section$" README.md > /dev/null || {
    echo "Missing required section: $section"
    exit 1
  }
done
```

## Companion CLI: `markdown-edit`

Need to *change* Markdown after you've found the right section? The repository also ships `markdown-edit`, a heading-aware editor that understands the spans emitted by `markdown-extract`.

Key features:

- Operations scoped to headings: `replace`, `delete`, `append-to`, `prepend-to`, `insert-after`, `insert-before`.
- Payload sources via `--with <path>` (or `-` for stdin) and `--with-string "escaped\ntext"`.
- Safety-first by default: dry-run diffs (`--dry-run`), duplicate guards (`--allow-duplicate` to opt out), atomic writes with optional backups (`--backup` / `--no-backup`).
- Validation aligned with the [markdown-edit specification](./markdown-edit.spec.md): heading-level enforcement, single-section payloads, and friendly exit codes for automation.

Example workflow:

```console
# Preview an append without touching disk
$ markdown-edit README.md append-to "^Changelog$" \
    --with-string "- Documented markdown-edit release\n" \
    --dry-run

# Replace a section body but keep the original heading line
$ markdown-edit docs/guide.md replace "Integration Notes" \
    --with-string "New guidance goes here.\n" \
    --keep-heading
```

Use `--all` (optionally `--max-matches N`) for batched edits, `--quiet` for terse runs, and `--case-sensitive` when the default case-insensitive matching is too broad.

### CLI reference

| Command | Description | Common flags |
|---------|-------------|--------------|
| `markdown-edit <file> replace <pattern>` | Replace an entire section (heading + body) | `--with / --with-string`, `--keep-heading` (or `--body-only`), `--allow-duplicate` |
| `markdown-edit <file> delete <pattern>` | Remove the matching section | `--dry-run`, `--backup/--no-backup`, `--all`, `--max-matches` |
| `markdown-edit <file> append-to <pattern>` | Append payload to the end of the section body | `--with / --with-string`, `--allow-duplicate`, `--dry-run` |
| `markdown-edit <file> prepend-to <pattern>` | Insert payload after the heading, before existing content | Same as append |
| `markdown-edit <file> insert-after <pattern>` | Insert a new section after the matched section | `--with / --with-string`, `--allow-duplicate`, `--dry-run` |
| `markdown-edit <file> insert-before <pattern>` | Insert a new section before the matched section | Same as `insert-after` |

Global knobs: `--all`, `--max-matches N`, `--case-sensitive`, `--quiet`, `--dry-run`, `--backup` / `--no-backup`.

#### Escaped inline payloads

`--with-string` supports a small, predictable escape set for automation. Anything outside this list is rejected with exit code 5.

| Escape | Meaning |
|--------|---------|
| `\\n` | Newline |
| `\\t` | Horizontal tab |
| `\\\\` | Literal backslash |
| `\\"` | Double quote |

Examples:

```console
$ markdown-edit notes.md append-to "^Today$" --with-string "- sync status\\n"
$ markdown-edit notes.md replace "Summary" --with-string "All clear\\n" --keep-heading
```

#### Match limits

`--max-matches` caps how many sections can be touched in a single invocation. Pair it with `--all` when you expect multiple hits but want a hard ceiling.

```console
# Allow up to 3 replacements; fail with exit code 2 if more match
$ markdown-edit docs/*.md replace "^Changelog$" \
    --with updates.md \
    --all \
    --max-matches 3
```

#### Validation failures (examples)

The CLI surfaces actionable messages from the core engine:

- Heading depth mismatch: `insert-before payload heading depth 3 must match target depth 2`
- Duplicate sibling: `heading 'Release Notes' already exists at this level`
- Missing payload heading: `replacement payload must begin with a heading`

#### Performance & safety notes

- Large files: the engine streams once through the document, using byte offsets instead of line numbers (tested >=5 MB). Diff generation is the most expensive step in dry-run mode.
- Backups & atomic writes: every write goes to `file.tmp` and promotes to the original name only after fsync; `--no-backup` skips the `.bak` copy.
- Path hygiene: the CLI operates on user-supplied paths. In CI/CD, prefer repository-relative paths or sandboxed working directories when invoking the tool with untrusted input.

## Installation

> **⚠️ AI Agents:** Skip this section. Both `markdown-extract` and `markdown-edit` are already installed at `/usr/local/bin` on this host. You can use them directly.

### Using Cargo

```console
# Install the extractor from crates.io
$ cargo install markdown-extract-cli

# Build the editor from this workspace
$ cargo install --path crates/markdown-edit-cli
```

Or run the tools in place:

```console
# Extract
$ cargo run -p markdown-extract-cli -- <args>

# Edit
$ cargo run -p markdown-edit-cli -- <args>
```

### Docker

A Docker image is also available, and can be installed with the following
command:

```console
$ docker pull sean0x42/markdown-extract:v2
```

You can then run the container with the following command:

```console
$ docker run -it sean0x42/markdown-extract:v2 --help
```

Note that because markdown-extract accesses the file system, you will need
to mount a volume if you want to access a file on the host. e.g.

``` console
$ docker run -v $PWD:/opt -it sean0x42/markdown-extract:v2 v2.0.0 /opt/CHANGELOG.md
```

If you know a better way of achieving this, please let me know!

## Github Action

This project can be used as a Github action.

Here is a sample workflow usage:

```yaml
- id: extract-changelog
  uses: sean0x42/markdown-extract@v4
  with:
   file: crates/markdown-extract/CHANGELOG.md
   pattern: 'v2.0.0'
- name: Write output to file
  run: |
    printf '${{ steps.extract-changelog.outputs.markdown }}' > CHANGELOG-extracted.txt
- uses: actions/upload-artifact@v3
  with:
   name: changelog
   path: CHANGELOG-extracted.txt
```

For a complete reference view the [action.yml](action.yml).

The action version corresponds to the version of the tool.

## Use Cases

`markdown-extract` shines in several scenarios:

1. **Release automation**: Extract version-specific patch notes from `CHANGELOG.md` for CI/CD pipelines
2. **Documentation generation**: The HashiCorp team uses it to extract API docs and inject them into OpenAPI schemas
3. **AI agent context management**: Pre-filter documentation to keep LLM context windows lean ([see examples above](#for-ai-agent-workflows))
4. **Content validation**: Verify required sections exist in documentation before publishing
5. **Documentation diffing**: Compare sections across versions or files
6. **Selective archiving**: Extract and save specific documentation sections for compliance

## AI Agent Tooling

> **🤖 Both `markdown-extract` and `markdown-edit` are installed at `/usr/local/bin`.** Use them directly in your workflows.
>
> **See detailed examples in the [For AI Agent Workflows](#for-ai-agent-workflows) section above.**

LLM-based agents work best with focused context. These tools help you:

- **Reduce token usage**: Extract only relevant sections instead of sending entire documents
- **Improve accuracy**: Targeted context reduces hallucination and improves response quality  
- **Enable dynamic prompts**: Build context-aware prompts by pulling sections based on user queries
- **Automate freshness**: Schedule extraction jobs to keep agent knowledge bases current

The tool writes clean Markdown to stdout, making it trivial to integrate with any orchestration framework, shell script, or Python automation that can run subprocesses.

**Recommended workflow pattern (extract → modify → edit):**
```bash
# 1. Extract the current section to understand context
current_section=$(markdown-extract "Installation" README.md)

# 2. Generate or modify content based on what you found
# (your logic here)

# 3. Apply the changes with validation
markdown-edit README.md replace "Installation" \
  --with-string "## Installation\n\nNew content here.\n" \
  --dry-run  # Preview first

# 4. If preview looks good, apply without --dry-run
markdown-edit README.md replace "Installation" \
  --with-string "## Installation\n\nNew content here.\n"
```

**Error handling in shell scripts:**
```bash
#!/bin/bash
# Safe section update with validation

if ! markdown-extract "^Configuration$" config.md > /dev/null 2>&1; then
  echo "ERROR: Configuration section not found"
  exit 1
fi

# Preview changes
if ! markdown-edit config.md append-to "Configuration" \
     --with-string "- New option added\n" \
     --dry-run; then
  echo "ERROR: Edit validation failed"
  exit 1
fi

# Apply changes (backup is automatic by default)
markdown-edit config.md append-to "Configuration" \
  --with-string "- New option added\n"
```

**Exit code reference for `markdown-edit`:**

| Exit Code | Meaning | Agent Response |
|-----------|---------|----------------|
| 0 | Success | Proceed with workflow |
| 1 | Section not found | Check pattern, list candidate headings with `markdown-extract ".*" file.md --all \| grep "^#"` |
| 2 | Multiple matches | Use `--all` if intentional, otherwise refine pattern to match single section |
| 3 | Invalid arguments | Fix command syntax or flag usage |
| 4 | I/O failure | Check file permissions and path |
| 5 | Invalid content source | Verify `--with` file exists or `--with-string` escapes are valid (`\n`, `\t`, `\\`, `\"`) |
| 6 | Validation failure | Common causes: payload missing heading for `replace`, heading level mismatch, duplicate sibling heading |

**Real-world integration patterns:**
- GitHub Actions workflows that refresh agent context on doc updates
- Python scripts using `subprocess.run()` to dynamically fetch relevant sections
- Bash orchestration for multi-agent systems with specialized knowledge domains
- CI validation ensuring documentation completeness before agent deployment

