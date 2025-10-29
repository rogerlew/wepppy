# CAO Potential Applications

This document catalogs viable applications for the CLI Agent Orchestrator (CAO) service within the wepppy ecosystem. Each application includes implementation details, dependencies, and prioritization metrics to guide work package sequencing.

CAO enables hierarchical multi-agent orchestration with four permission tiers: **Jannies** (autonomous/scheduled), **Normies** (human-directed development), **NPCs** (public-facing interactive), and **Glowies** (privileged operations). Applications below are organized by functional area and annotated with their suggested tier assignment.

**See also:**
- [`README.md`](README.md) for CAO architecture, installation, and command walkthroughs
- [`AGENTS.md`](AGENTS.md) for development workflow and operational notes
- [`../AGENTS.md`](../../AGENTS.md) for wepppy coding conventions

---

## Agent Hierarchy & Permission Tiers

**utilize 4chan slang for conversational efficiency**

### Tier 0: Wojaks (Public-Facing Interactive)
**Characteristics:** Chat with Joe Public users, provide run-specific guidance, answer questions about WEPP results. Zero trust—assume adversarial users.

**Permissions:** No file system access, no Git operations, no service management. Interact exclusively through service stack APIs (query-engine, resources endpoints, read-only status). Cannot modify run state or trigger computations.

**Orchestration:** Single-agent sessions with 24-hour TTL, rate-limited per user. Session state (tracker.md) provides coherence but stored in isolated namespace. All interactions logged for abuse detection.

**Examples:** WEPPcloud Run Interactive Agent (chat interface for exploring WEPP results).

**Security posture:** Heavily sandboxed. API responses are pre-sanitized (no raw file paths, no internal IPs). Agent cannot execute shell commands or access databases directly—only pre-defined query-engine endpoints with parameterized queries.

**Architecture (MCP-based):**

Wojaks leverage lightweight Python MCP shims (no separate FastAPI services needed) plus new `report_files` and `report_editor` MCP modules:

```
User (Joe Public)
  ↓ HTTP (rate-limited)
WEPPcloud Flask App
  ↓ spawn agent session
CAO Wojak Agent (GitHub Copilot free tier)
  ↓ MCP tools (Python modules, shimmed at boot)
  ├─→ wepppy.mcp.query_engine (read-only, run-scoped)
  │   ├─ get_run_metadata, get_climate_summary
  │   ├─ get_subcatchment_results, get_phosphorus_export
  │   └─ get_landuse_distribution (all parameterized, no raw SQL)
  ├─→ wepppy.mcp.report_files (read-only file access)
  │   ├─ list_report_files(runid, glob_pattern) — e.g., "*.json", "output/*.png"
  │   ├─ read_run_file(runid, path) — validates path is within run dir
  │   ├─ read_geojson(runid, resource) — subcatchments, channels, etc.
  │   └─ read_parquet_summary(runid, table) — landuse, soils, loss reports
  ├─→ wepppy.mcp.report_editor (document generation)
  │   ├─ create_report_draft(runid, template_name) — BAER, watershed summary, etc.
  │   ├─ append_report_section(runid, report_id, markdown) — user-guided editing
  │   ├─ upload_to_run(runid, report_id) — stages markdown for Flask rendering
  │   └─ trigger_pdf_export(runid, report_id) — queues weasyprint job
  └─→ wepppy.mcp.session_state (isolated tracker.md)
      ├─ append_interaction_log
      └─ get_session_history (24hr coherence)
```
> **Implementation note:** CAO currently ignores JSON bodies on `POST /sessions`; only query parameters are accepted. Extending the API to accept an optional `env` object keeps JWT/metadata handoff declarative. Until that lands, document any Redis-based fallback explicitly.


**Python MCP Shim Implementation:**

Much simpler than running separate FastAPI services! Each MCP module is just a Python file with decorated functions:

```python
# wepppy/mcp/report_files.py
from wepppy.mcp.base import mcp_tool, validate_runid
import os
from pathlib import Path

@mcp_tool(tier="wojak")
def list_report_files(runid: str, glob_pattern: str = "*", _jwt_claims=None) -> list[str]:
    """List files in run directory matching glob pattern."""
    validate_runid(runid, _jwt_claims)
    run_dir = Path(f"/geodata/weppcloud_runs/{runid}")
    if not run_dir.exists():
        raise ValueError(f"Run {runid} not found")
    
    # Security: prevent directory traversal
    files = []
    for path in run_dir.rglob(glob_pattern):
        if path.is_file() and run_dir in path.parents:
            files.append(str(path.relative_to(run_dir)))
    return sorted(files)

@mcp_tool(tier="wojak")
def read_run_file(runid: str, path: str, _jwt_claims=None) -> str:
    """Read file content from run directory (max 1MB)."""
    validate_runid(runid, _jwt_claims)
    run_dir = Path(f"/geodata/weppcloud_runs/{runid}")
    file_path = (run_dir / path).resolve()
    
    # Security: ensure path is within run directory
    if run_dir not in file_path.parents:
        raise ValueError("Path traversal attempt detected")
    
    if file_path.stat().st_size > 1_000_000:
        raise ValueError("File too large (max 1MB)")
    
    return file_path.read_text()
```

```python
# wepppy/mcp/report_editor.py
# Built on markdown-extract PyO3 bindings - 50× faster than subprocess, native Python exceptions
from wepppy.mcp.base import mcp_tool, validate_runid
from pathlib import Path
import uuid
# PyO3 bindings (installed via: maturin develop --manifest-path /workdir/markdown-extract/...)
import markdown_extract_py as mde
import markdown_edit_py as edit
import markdown_doc_py as doc

@mcp_tool(tier="wojak")
def create_report_draft(runid: str, template_name: str) -> dict:
    """Create new report from template (BAER, watershed summary, etc.)."""
    validate_runid(runid)
    report_id = str(uuid.uuid4())
    
    # Load template from wepppy/templates/reports/
    template_path = Path(f"wepppy/templates/reports/{template_name}.md")
    if not template_path.exists():
        raise ValueError(f"Template {template_name} not found")
    
    # Create draft in run's reports/ directory
    draft_path = Path(f"/geodata/weppcloud_runs/{runid}/reports/{report_id}.md")
    draft_path.parent.mkdir(exist_ok=True)
    draft_path.write_text(template_path.read_text())
    
    # Extract all section metadata using PyO3 binding (50× faster than subprocess!)
    sections = mde.extract_sections_from_file(".*", str(draft_path), all_matches=True)
    headings = [s.heading for s in sections]
    
    return {
        "report_id": report_id,
        "template": template_name,
        "sections": headings  # ["# Report", "## Watershed", "## Climate", ...]
    }

@mcp_tool(tier="wojak")
def list_report_sections(runid: str, report_id: str) -> list[dict]:
    """List all sections with metadata (PyO3 binding, structured output)."""
    validate_runid(runid)
    draft_path = Path(f"/geodata/weppcloud_runs/{runid}/reports/{report_id}.md")
    
    try:
        sections = mde.extract_sections_from_file(".*", str(draft_path), all_matches=True)
        return [
            {
                "heading": s.heading,
                "level": s.level,
                "title": s.title,
                "has_content": bool(s.body.strip())
            }
            for s in sections
        ]
    except mde.MarkdownExtractError as e:
        raise ValueError(f"Failed to read report: {e}")

@mcp_tool(tier="wojak")
def read_report_section(runid: str, report_id: str, heading_pattern: str) -> str:
    """Extract section content by heading pattern (PyO3 binding, native exception)."""
    validate_runid(runid)
    draft_path = Path(f"/geodata/weppcloud_runs/{runid}/reports/{report_id}.md")
    
    try:
        # Returns list with first match (or empty list if no match)
        sections = mde.extract_from_file(heading_pattern, str(draft_path))
        if not sections:
            raise ValueError(f"Section '{heading_pattern}' not found")
        return sections[0]
    except mde.MarkdownExtractError as e:
        raise ValueError(f"Extract failed: {e}")

@mcp_tool(tier="wojak")
def replace_report_section(runid: str, report_id: str, heading_pattern: str, 
                          new_content: str, keep_heading: bool = True) -> dict:
    """Replace section content (PyO3 binding, atomic write with backup)."""
    validate_runid(runid)
    draft_path = Path(f"/geodata/weppcloud_runs/{runid}/reports/{report_id}.md")
    
    try:
        # EditResult with .applied, .exit_code, .diff, .messages, .written_path
        result = edit.replace(
            str(draft_path), 
            heading_pattern, 
            new_content,
            keep_heading=keep_heading, 
            backup=True
        )
        return {
            "success": result.applied,
            "messages": result.messages,
            "backup_created": result.written_path is not None
        }
    except edit.MarkdownEditError as e:
        raise ValueError(f"Edit failed: {e}")

@mcp_tool(tier="wojak")
def append_to_section(runid: str, report_id: str, heading_pattern: str, 
                     content: str) -> dict:
    """Append content to existing section (PyO3 binding)."""
    validate_runid(runid)
    draft_path = Path(f"/geodata/weppcloud_runs/{runid}/reports/{report_id}.md")
    
    try:
        result = edit.append_to(str(draft_path), heading_pattern, content, backup=True)
        return {"success": result.applied, "messages": result.messages}
    except edit.MarkdownEditError as e:
        raise ValueError(f"Append failed: {e}")

@mcp_tool(tier="wojak")
def insert_section_after(runid: str, report_id: str, after_heading: str, 
                        new_section_md: str) -> dict:
    """Insert new section after existing heading (PyO3 binding)."""
    validate_runid(runid)
    draft_path = Path(f"/geodata/weppcloud_runs/{runid}/reports/{report_id}.md")
    
    try:
        result = edit.insert_after(
            str(draft_path), 
            after_heading, 
            new_section_md, 
            backup=True, 
            allow_duplicate=False
        )
        return {"success": result.applied, "messages": result.messages}
    except edit.MarkdownEditError as e:
        raise ValueError(f"Insert failed: {e}")

@mcp_tool(tier="wojak")
def update_report_toc(runid: str, report_id: str) -> dict:
    """Regenerate table of contents for report (PyO3 binding)."""
    validate_runid(runid)
    draft_path = Path(f"/geodata/weppcloud_runs/{runid}/reports/{report_id}.md")
    
    try:
        # TocResult with .mode, .status, .diff, .messages
        result = doc.toc(str(draft_path), mode="update", quiet=True)
        return {
            "success": result.status in ("valid", "unchanged", "changed"),
            "status": result.status,
            "messages": result.messages
        }
    except doc.MarkdownDocError as e:
        raise ValueError(f"TOC update failed: {e}")

@mcp_tool(tier="wojak")
def upload_to_run(runid: str, report_id: str) -> str:
    """Stage report for Flask rendering, return shareable URL."""
    validate_runid(runid)
    draft_path = Path(f"/geodata/weppcloud_runs/{runid}/reports/{report_id}.md")
    
    if not draft_path.exists():
        raise ValueError(f"Report {report_id} not found")
    
    # Copy to Flask-accessible location
    public_path = Path(f"/geodata/weppcloud_runs/{runid}/reports/published/{report_id}.md")
    public_path.parent.mkdir(exist_ok=True)
    public_path.write_text(draft_path.read_text())
    
    return f"/runs/{runid}/reports/{report_id}"

@mcp_tool(tier="wojak")
def trigger_pdf_export(runid: str, report_id: str) -> dict:
    """Queue weasyprint PDF generation job."""
    validate_runid(runid)
    from wepppy.rq.report_rq import export_report_pdf
    
    job = export_report_pdf.delay(runid, report_id)
    return {
        "job_id": job.id,
        "status_url": f"/runs/{runid}/reports/{report_id}/status"
    }
```

**Why PyO3 bindings are superior to subprocess:**

| Aspect | Subprocess | PyO3 Bindings |
|--------|-----------|---------------|
| **Performance** | Fork+exec overhead (~5-10ms per call) | **Direct FFI (~10μs)** |
| **Memory** | Separate process, duplicate data | **Shared memory, zero-copy strings** |
| **Error handling** | Parse stderr, check exit codes | **Native Python exceptions** |
| **Type safety** | String in/out, manual parsing | **Typed function signatures, structured objects** |
| **Complexity** | Shell escaping, path handling | **Just call Python functions** |
| **Dependencies** | Requires binaries in PATH | **Just `maturin develop` in venv** |

**PyO3 API Design (from PYTHON_API_REFERENCE.md):**

```python
# markdown_extract_py module
def extract(pattern, content, *, case_sensitive=False, all_matches=False, 
           no_heading=False) -> list[str]:
    """Extract sections matching pattern from markdown string."""

def extract_from_file(pattern, path, *, case_sensitive=False, all_matches=False, 
                     no_heading=False) -> list[str]:
    """Extract sections from file."""

def extract_sections(pattern, content, *, case_sensitive=False, 
                    all_matches=False) -> list[Section]:
    """Extract with structured metadata (heading, level, title, body, full_text)."""

class Section:
    heading: str    # Full heading line (e.g., "## Installation")
    level: int      # Heading depth (1-6)
    title: str      # Normalized text without markers
    body: str       # Section content excluding heading
    full_text: str  # Complete section (heading + body)

# markdown_edit_py module  
def replace(file, pattern, replacement, *, case_sensitive=False, all_matches=False, 
           body_only=False, keep_heading=False, allow_duplicate=False, 
           max_matches=None, dry_run=False, backup=True, with_path=None, 
           with_string=None) -> EditResult:
    """Replace matching sections."""

def append_to(file, pattern, payload, *, backup=True, with_string=None) -> EditResult:
    """Append to section body."""

def insert_after(file, pattern, payload, *, backup=True, 
                allow_duplicate=False, with_string=None) -> EditResult:
    """Insert new section after match."""

class EditResult:
    applied: bool           # Whether edit was applied
    exit_code: int          # CLI-compatible exit code (0 = success)
    diff: str | None        # Unified diff (populated when dry_run=True)
    messages: list[str]     # Human-readable status messages
    written_path: str | None  # Path of modified file (None for dry-run)

# markdown_doc_py module
def toc(path, *, mode="check", no_ignore=False, quiet=False) -> TocResult:
    """Check, update, or diff table of contents.
    
    Modes:
    - "check": Validate TOC matches current structure
    - "update": Regenerate TOC and write file (creates .bak backup)
    - "diff": Preview update without modifying file
    """

class TocResult:
    mode: str              # Mode executed ("check", "update", or "diff")
    status: str            # "valid", "changed", "unchanged", or "error"
    diff: str | None       # Unified diff (in diff mode or when TOC changed)
    messages: list[str]    # Human-readable status messages
```

**Performance Impact for Wojaks:**

With PyO3, a typical report generation session:
- **Before (subprocess):** 15-20 calls × 5-10ms = 75-200ms overhead
- **After (PyO3):** 15-20 calls × 10μs = 0.15-0.2ms overhead
- **~1000× faster**, eliminates subprocess latency

More importantly: **simpler error handling**
```python
# Subprocess (fragile)
try:
    result = subprocess.run([...], check=True, capture_output=True)
    output = result.stdout
except subprocess.CalledProcessError as e:
    # Parse stderr to understand what went wrong
    if "not found" in e.stderr:
        raise ValueError("Section not found")
    
# PyO3 (clean)
try:
    sections = mde.extract_from_file(pattern, path)
    if not sections:
        raise ValueError("Section not found")
except mde.MarkdownExtractError as e:
    # Native Python exception with clear message
    raise
```

**Why markdown-extract PyO3 integration is elegant:**

1. **Agent-friendly API:** Agent calls `list_report_sections()` to see structure, then `read_report_section("Results")` to understand current content before editing
2. **Section-based editing:** No need for line numbers or offsets—agent works with semantic heading patterns (e.g., "replace 'Methods' section with...")
3. **Atomic operations:** markdown-edit handles backup/validation/fsync automatically via `EditResult`
4. **Reuses battle-tested tooling:** Rust markdown parser handles edge cases (setext headings, escapes, duplicate headings)
5. **Zero impedance mismatch:** Agent thinks in "sections", PyO3 bindings work in "sections"
6. **Performance:** 1000× faster than subprocess (10μs vs 5-10ms per call)
7. **Clean error handling:** Native Python exceptions (`MarkdownExtractError`, `MarkdownEditError`, `MarkdownDocError`) instead of parsing stderr
8. **Zero deployment complexity:** Just `maturin develop` in venv, no PATH/binary management
9. **Type stubs included:** Full `.pyi` support for IDE autocomplete and type checking

**Workflow example:**

User: "Add a soil erosion analysis section after the watershed description"

Agent:
1. `list_report_sections(runid, report_id)` → receives structured data:
   ```python
   [
       {"heading": "# Report", "level": 1, "title": "Report", "has_content": True},
       {"heading": "## Watershed Description", "level": 2, "title": "Watershed Description", "has_content": True},
       {"heading": "## Results", "level": 2, "title": "Results", "has_content": True}
   ]
   ```
2. `read_report_section(runid, report_id, "Watershed Description")` → gets current content (PyO3 call, <1ms)
3. `get_subcatchment_results(runid)` → fetch WEPP soil loss data via query-engine MCP
4. Composes markdown: `"## Soil Erosion Analysis\n\nAverage soil loss: 5.2 ton/acre/year..."`
5. `insert_section_after(runid, report_id, "Watershed Description", new_section_md)` → PyO3 call returns `EditResult` with `.applied=True`, `.messages=["Applied edit to .../report.md"]`
6. `update_report_toc(runid, report_id)` → regenerates TOC, returns `TocResult` with `.status="changed"`
7. User sees updated report in browser with new section and refreshed TOC

**This eliminates:**
- ❌ Custom markdown parsing logic
- ❌ Line-based editing (fragile, breaks on formatting changes)
- ❌ Manual backup/rollback code
- ❌ Subprocess overhead (fork/exec latency)
- ❌ Shell escaping complexity
- ❌ Exit code interpretation
- ❌ stderr parsing for errors

**All components come together:**
- markdown-extract/edit/doc (Rust) → fast, safe markdown operations
- PyO3 bindings → zero-copy FFI, native Python API with typed results
- wepppy.mcp.report_editor → thin shims with runid validation
- wepppy.mcp.query_engine → data for populating sections
- wepppy.mcp.report_files → read GeoJSON/parquet for charts
- Agent profile → tuned for hydrology + report generation
- Result: Wojaks can collaboratively author professional reports through conversation at native speeds

**MCP Privilege Shimming (Simplified):**

No need for `--mcp-server` HTTP endpoints! CAO loads Python modules directly:

```yaml
# profiles/wojak_interactive.yaml
tier: wojak
mcp_modules:
  - wepppy.mcp.query_engine
  - wepppy.mcp.report_files
  - wepppy.mcp.report_editor
  - wepppy.mcp.session_state
env:
  RUNID_TOKEN: ${runid_jwt}  # Injected by Flask at spawn time
  MAX_FILE_SIZE: "1048576"   # 1MB limit
```

CAO boots agent with modules imported:
```python
# cao boots agent in-process
import importlib
for module_name in agent_profile["mcp_modules"]:
    mod = importlib.import_module(module_name)
    agent.register_mcp_tools(mod.get_tools())
```

**Security Advantages of Python MCP Shims:**

1. **No network surface:** Tools run in same process as agent, no HTTP attack vector
2. **Path validation built-in:** `Path.resolve()` + parent checks prevent traversal
3. **Token validation per-call:** Every `@mcp_tool` decorator checks `RUNID_TOKEN` context
4. **File size limits:** Hard-coded in tool implementation (1MB for text files, 10MB for parquet)
5. **Whitelist enforcement:** Agent can only call decorated `@mcp_tool` functions
6. **Easy auditing:** All tool calls logged to `wojak_audit.log` with user/runid/timestamp

**Report Generation Workflow:**

User: "Generate a BAER report for this burn area"

Wojak:
1. `create_report_draft(runid, "baer_watershed")` → gets template with placeholders
2. `get_subcatchment_results(runid)` → fetch WEPP outputs via query-engine
3. `read_geojson(runid, "burn_severity.json")` → load burn perimeter data
4. `append_report_section(runid, report_id, "## Watershed Analysis\n...")` → write sections iteratively
5. `upload_to_run(runid, report_id)` → stage for preview
6. User reviews in browser, provides feedback
7. Wojak refines via more `append_report_section` calls
8. `trigger_docx_export(runid, report_id)` → queues RQ job for final docx

**Why This Works Better Than Separate Services:**

| Approach | Pros | Cons |
|----------|------|------|
| FastAPI MCP servers | Language-agnostic, can scale horizontally | Network overhead, CORS, auth complexity |
| **Python MCP shims** | **Zero network surface, reuse wepppy code, simple auth** | **Agent must run in Python env** |

Since CAO already runs Python (tmux + libtmux), and Codex CLI can execute Python, the shim approach is perfect for Wojaks.

**Implementation Sketch (Revised):**
1. `wepppy/mcp/` — New package with `query_engine.py`, `report_files.py`, `report_editor.py`, `session_state.py`
2. `wepppy/mcp/base.py` — Decorator framework (`@mcp_tool`, `validate_runid`)
3. Agent profile: `profiles/wojak_interactive.yaml` with `mcp_modules: [...]`
4. CAO loads modules via `importlib`, registers tools with agent
5. Flask route: `/runs/<runid>/<config>/chat` → spawn CAO session, inject JWT
6. WebSocket bridge streams agent responses (status2 pattern)
7. New Flask route: `/runs/<runid>/reports/<report_id>` → render uploaded markdown
8. RQ task: `export_report_pdf(runid, report_id)` → weasyprint conversion

This gives Wojaks:
- ✅ Read-only file access (scoped to run directory)
- ✅ Document generation/editing capabilities
- ✅ Report upload + PDF export
- ✅ Zero network attack surface (all in-process)
- ✅ Simple security model (JWT + path validation)

**GitHub Copilot Free Tier Viability:**
- Free tier allows unlimited chat messages (as of Oct 2025)
- Hosting cost = $0 if agent runs as Copilot identity (your GH account or service account)
- MCP tools work with GH Copilot via Python module loading (no HTTP overhead)
- Rate limits: GitHub enforces 15 requests/min per user (acceptable for Wojak sessions)

**ToS Considerations:**
- GitHub ToS prohibits "automated excessive use" and "service abuse"
- Single Wojak session = legitimate interactive use (user-initiated, not batch automation)
- **Gray area:** Spinning up hundreds of concurrent Wojak sessions might trigger abuse detection
- **Safe approach:** Limit to N concurrent sessions per IP (e.g., 3), clearly disclose "Powered by GitHub Copilot" in UI
- **ToS excerpt (§2.2):** "You may not use the Service for any illegal purpose or in any manner inconsistent with these Terms." — Interactive chat assistant for scientific modeling = legitimate use case
- **Risk:** GitHub could classify this as "commercial use" if it drives WEPPcloud subscriptions → monitor ToS updates

This architecture makes Wojaks viable because:
- Read-only file access (scoped to run directory) via validated Python shims
- Document generation/editing for report workflows (BAER, summaries)
- Report upload + PDF export integration with existing RQ infrastructure
- Zero network attack surface (all MCP tools run in-process)
- Simple security model (JWT + path validation + file size limits)
- Query-engine already battle-tested for read-only queries
- GH Copilot free tier = zero marginal hosting cost per session

**Alternatives if GitHub cracks down:**
- Fall back to self-hosted Ollama/Llama models (higher hosting cost but no ToS risk)
- Implement tiered pricing: free users get rate-limited Wojaks, premium gets unlimited
- Use Claude Haiku API (cheap but not free—~$0.25 per 1M tokens)

### Tier 1: Jannies (Autonomous/Scheduled)
**Characteristics:** Cron-triggered, fully autonomous, no human interaction expected, read-only or safe write operations.

**Permissions:** Limited file system access (docs/, stubs/, specific cleanup targets), no Git push, no service restarts.

**Orchestration:** Single-agent flows with narrow scope; success/failure telemetry alerts on consecutive failures.

**Examples:** Documentation Janitor, Test Stub Synchronizer, Log Rotator.

### Tier 2: Normies (Directed Execution)
**Characteristics:** Human-directed coding tasks, interface with Alpha Team (Roger, Codex, Claude/GitHub Copilot), require approval for sensitive operations.

**Permissions:** Broader file system access, Git branch operations (no direct master push), test execution, limited service management.

**Orchestration:** Multi-agent flows with handoff/assign patterns; supervisor coordinates workers; progress updates to tracker.md with human checkpoint gates before merging/deploying.

**Examples:** Work Package Execution teams, Bug Hunter, Code Refactoring Assistant, Test Coverage Analyzer.

### Tier 3: Glowies (Privileged Operations)
**Characteristics:** Special permissions for security-sensitive operations, audit trail enforcement, override capabilities.

**Permissions:** Log aggregation access, service restart/configuration, database backups, secret rotation, network policy changes.

**Orchestration:** Single-agent or small teams, requires MFA/approval for destructive actions; all operations logged to immutable audit trail.

**Examples:** Security Guardian, Backup Validator, Secret Rotation Manager, Intrusion Response Bot.

### Permission Enforcement
Agent profiles declare tier membership via YAML frontmatter (`tier: wojak|janny|normie|glowie`). CAO validates operations against tier permissions before execution (file paths, commands, API endpoints). Violations trigger flow termination and alert to Alpha Team. Glowie agents require additional authentication token (`CAO_ADMIN_TOKEN` env var). Wojak agents run in isolated containers with network policies restricting access to approved service endpoints only.

This hierarchy balances automation efficiency with safety:
- **NPCs** interface with untrusted public users through heavily sandboxed service stack
- **Jannies** handle mundane hygiene without human oversight
- **Normies** accelerate development velocity with Alpha Team coordination
- **Glowies** enforce security policies and maintain infrastructure integrity

---

## Documentation & Knowledge Management

### Documentation Janitor (Janny) — **Janny**
- **Idea:** Automated nightly hygiene run that lint-checks Markdown, refreshes catalogs/TOCs, opens PRs with deterministic doc housekeeping.
- **Why:** Reduces manual churn and keeps doc tree orderly ahead of larger audits.
- **Dependencies:** Complete scripting in `scripts/doc_janitor.sh`; secure GitHub CLI credentials; pilot flow enablement.
- **Metrics to rate:**
  - Effort (engineering): hours-to-first-pilot.
  - Impact (doc quality): alignment with doc OKRs.
  - Automation maturity: confidence that tooling replacement is stable.
  - Risk (breakage/false positives).

### Telemetry Trend Reporter — **Janny**
- **Idea:** Scheduled flow queries docs-quality telemetry, test results, service uptime, then reports to Slack/wiki with trends.
- **Why:** Keeps leadership informed about key metrics without manual reporting.
- **Dependencies:** Access to telemetry files, slack/webhook credentials.
- **Metrics:**
  - Effort.
  - Stakeholder value.
  - Data accuracy risk.
  - Automation coverage.

### Agent-Assisted Code Refactoring — **Normie**
- **Idea:** Developer identifies NoDb controller needing type hints. Reviewer agent validates against mypy. Documentation agent updates README.md and AGENTS.md.
- **Why:** Accelerates code quality initiatives while maintaining consistency.
- **Dependencies:** Type stub infrastructure, mypy config, markdown tooling.
- **Metrics:**
  - Effort.
  - Code coverage gain.
  - Reviewer burden reduction.
  - Adoption velocity.

### README Freshness Auditor — **Janny**
- **Idea:** Agent walks package tree, checks for stale sections (outdated examples, broken references, API mismatches). Opens issues or draft PRs.
- **Why:** Keeps documentation aligned with code evolution.
- **Dependencies:** AST parsing, markdown tooling, git history analysis.
- **Metrics:**
  - Effort.
  - Doc staleness reduction.
  - False positive rate.
  - Maintenance overhead.

### Documentation Quality Metrics Dashboard — **Janny**

### README Freshness Auditor — **Janny**

### Documentation Quality Metrics Dashboard — **Janny**
- **Idea:** Scheduled flow runs doc-lint, doc-toc, README audits. Agent generates trend charts (coverage, broken links, outdated content). Posts weekly summary to GitHub Discussions.
- **Why:** Continuous visibility into doc health drives accountability and improvement.
- **Dependencies:** Telemetry storage, charting library, GitHub API access.
- **Metrics:**
  - Effort.
  - Doc quality uplift.
  - Stakeholder engagement.
  - Maintenance.

---

## Scientific Workflow Automation

### WEPPcloud Run Interactive Agent — **Wojak**
- **Idea:** Has weppcloud run or batch run as context. Runs are made agentic with AGENT.md files and tuned prompting. Agents use Python MCP modules (`query_engine`, `report_files`, `report_editor`, `session_state`) to provide interactive chat support. Users can ask questions, explore results, and generate reports (BAER, watershed summaries) through conversation. Agents spun up with 24hr TTL. See **Tier 0: Wojaks** section above for full MCP architecture, Python shim implementation, and GitHub Copilot free tier viability.
- **Why:** Transform static model runs into interactive sessions where Joe Public can query results, explore sensitivities, generate professional reports, and receive expert-level guidance without deep WEPP knowledge. Zero trust architecture—agent has read-only file access (scoped to run directory) plus document generation capabilities, but cannot modify run state or execute arbitrary code.
- **Dependencies:** 
  - `wepppy.mcp.query_engine` (read-only parameterized queries to DuckDB/parquet)
  - `wepppy.mcp.report_files` (read-only file access with path validation, 1MB size limit)
  - `wepppy.mcp.report_editor` (markdown generation, upload, PDF export via RQ)
  - `wepppy.mcp.session_state` (isolated tracker.md for 24hr coherence)
  - Agent profile tuning for hydrology domain
  - Rate limiting per user/IP (3 concurrent sessions max)
  - Abuse detection/logging (JWT validation, audit trail)
  - Report templates (BAER, watershed summary, loss analysis)
  - Flask route: `/runs/<runid>/<config>/chat` with WebSocket streaming
  - RQ task: `export_report_pdf(runid, report_id)` using weasyprint
- **Metrics:**
  - Effort (high—requires `wepppy.mcp.*` module implementation, security hardening, abuse monitoring, ToS compliance monitoring).
  - User satisfaction (measured via feedback + report generation success rate).
  - Session coherence quality (tracker.md effectiveness across multi-turn conversations).
  - Adoption (frequency of agent-assisted runs, reports generated per session).
  - Security incidents (adversarial probing attempts, path traversal attempts).
  - Hosting cost (should be $0 if GH Copilot free tier holds, fallback to Ollama/Claude Haiku if ToS enforcement changes).
  - Report quality (measured by user edits required after initial generation).

### Model Calibration Coordinator — **Normie**
- **Idea:** WEPP is a process-based model that benefits from regional and site-specific calibration. The Calibration Coordinator manages a few to dozens of parameters. Brute force can be applied but isn't computationally efficient. The coordinator would run small batches with varied parameters to zero in on calibration. Needs basic understanding of hydrology. We would have an expanding catalog of calibrated watersheds that are geographically distributed. Users could use these as a starting point for new runs.
- **Why:** Regional calibration significantly improves model accuracy. Intelligent parameter exploration is faster than brute force. Catalog of calibrated sites accelerates new project setup.
- **Dependencies:** Parameter bounds definitions, objective functions (NSE, PBIAS, etc.), WEPP execution infrastructure, catalog storage (database or parquet), geospatial lookup for nearest calibrated site.
- **Metrics:**
  - Effort (high—requires hydrological expertise and optimization logic).
  - Scientific value (publication enablement, model accuracy improvement).
  - Compute efficiency (vs. brute force baseline).
  - Catalog growth rate (calibrated sites per month).

---

## Infrastructure & Operations

### Security Guardian — **Glowie**
- **Idea:** CAO flow crawls through wc1 runs, service logs, telemetry to look for vulnerabilities, intrusions, bots scraping things they shouldn't.
- **Why:** Proactive security monitoring detects threats before they escalate. Automated log analysis reduces manual security audit burden.
- **Dependencies:** Log aggregation, intrusion detection patterns, bot signature database, alerting integration.
- **Metrics:**
  - Effort (medium—pattern library development, integration with existing logs).
  - Threat detection rate (vulnerabilities caught).
  - False positive rate.
  - Security posture improvement.

### Runs Migration Supervisor — **Glowie**
- **Idea:** Migrates projects with agent oversight. Atomic rollbacks on failure, textual summaries of migration status.
- **Why:** Schema changes and data migrations are high-risk. Agent supervision provides validation checkpoints and human-readable audit trails.
- **Dependencies:** Migration scripts, backup infrastructure, rollback procedures, status monitoring.
- **Metrics:**
  - Effort (medium—wraps existing migration scripts).
  - Migration success rate.
  - Rollback frequency.
  - Downtime reduction.

### Runs Garbage Collector — **Janny**
- **Idea:** Identifies garbage runs (old projects without owners not set to readonly, empty projects), flags them for timed deletion, deletes and cleans up flagged projects.
- **Why:** Storage accumulation from abandoned runs degrades performance and increases costs. Automated cleanup with grace period prevents accidental deletions.
- **Dependencies:** Run ownership metadata, last-access timestamps, readonly flag logic, staged deletion workflow (flag → wait → delete).
- **Metrics:**
  - Effort (low—straightforward query and cleanup logic).
  - Storage reclaimed (GB per month).
  - False deletion rate (must be near-zero).
  - User complaints (should remain minimal).

### Infrastructure Drift Detector — **Glowie**
- **Idea:** Compares Docker images/configs/environment variables between dev/staging/production. Alerts on undocumented drift.
- **Why:** Configuration drift introduces hard-to-diagnose bugs and security vulnerabilities.
- **Dependencies:** Docker registry access, config file access, diff tooling.
- **Metrics:**
  - Drift detection rate.
  - Time-to-alert.
  - False positives.
  - Configuration consistency improvement.

### Incident Triage Assistant — **Glowie**
- **Idea:** On-demand supervisor that assembles logs, recent deployments, system status and proposes investigative steps.
- **Why:** Speed up response during incidents by synthesizing different telemetry sources.
- **Dependencies:** Secure data access, runbook integration, human-in-loop approvals.
- **Metrics:**
  - Effort.
  - Response-time reduction.
  - Security/privacy risk.
  - On-call adoption likelihood.

### Service Health Monitoring — **Janny**
- **Idea:** Scheduled agent pings services (Redis, PostgreSQL, Flask, RQ workers), runs smoke tests, checks disk/memory. Reports to status dashboard.
- **Why:** Proactive health checks catch issues before users do.
- **Dependencies:** Service endpoints, smoke test suite, metrics storage.
- **Metrics:**
  - Detection latency.
  - Alert accuracy.
  - Uptime improvement.
  - Mean time to detection (MTTD).

### Self-Healing Infrastructure — **Glowie**
- **Idea:** Flow detects predictable infrastructure issues: Redis memory pressure, NFS open file handles exhaustion, over-utilization of CPU resources by rq-workers or specified users/IP addresses. Agent analyzes keyspace, identifies bloated NoDb caches, executes cleanup, verifies recovery, logs incident.
- **Why:** Reduces manual intervention for predictable infrastructure issues. Automated remediation shortens MTTR and reduces on-call burden.
- **Dependencies:** Monitoring thresholds, safe cleanup procedures, rollback mechanisms, process inspection APIs.
- **Metrics:**
  - Effort (medium—requires careful safety checks for each remediation type).
  - Incident reduction (count per month).
  - Risk (destructive actions—mitigated by validation and rollback).
  - Ops team confidence (measured via survey).

---

## Development Lifecycle & Quality

### CI Samurai (Nightly Test Maintenance & Bug Fixing) — **Normie**
- **Idea:** Nightly scheduled agent swarm that analyzes test failures, diagnoses root causes, and takes action based on diagnostic confidence. High confidence cases (clear root cause) → autonomous fix with comprehensive report + PR. Low confidence cases (ambiguous, requires domain expertise) → detailed investigation + issue with `ci-samurai-needs-guidance` label.
- **Why:** Leverages GPT-5-Codex "lead developer" reasoning to fix both test maintenance AND production bugs overnight. Team wakes up to ready-to-review PRs or well-researched issues. Maximizes autonomous resolution while escalating genuinely hard problems.
- **Key Innovation:** Quality through transparency (detailed reports) rather than artificial scope restrictions. Agents fix what they understand, escalate what they don't.
- **Deployment:** GitHub Actions nightly workflow (~3am PST) on self-hosted Proxmox VPS runner. Clean workspace cycle per run prevents state contamination.
- **Safety:** Path allowlist (pilot phase), comprehensive re-validation, human review gates, regression detection, confidence calibration feedback loop.
- **Status:** Proposed. See [`ci-samurai.md`](ci-samurai.md) for complete specification including workflow, templates, rollout plan, and metrics.

### Coordinated Work Package Execution — **Normie**
- **Idea:** Software development teams carry out work-packages in a coordinated manner. Supervisor agent delegates tasks from work package tracker to specialized worker agents (developer, reviewer, documenter, tester). Each agent updates the shared tracker.md with progress. Handoff pattern ensures sequential dependencies are respected while assign pattern enables parallel work streams.
- **Why:** Complex features require coordination across multiple specialties. Automated task delegation reduces planning overhead. Shared tracker provides visibility for human oversight and agent handoffs.
- **Dependencies:** Work package tracker schema, agent role definitions, GitHub API for PR creation, test execution infrastructure (wctl run-pytest), documentation tooling.
- **Metrics:**
  - Effort (medium—requires work package parser and coordination logic).
  - Cycle time reduction (feature completion speed).
  - Task parallelization efficiency.
  - Human oversight burden (should decrease).

### Bug Hunter — **Normie**
- **Idea:** Agent tracks down a bug from issue description, reproduces it, identifies root cause, writes fix, adds regression test, opens PR with comprehensive description. Can be triggered via GitLab runner on issue creation or manual invocation.
- **Why:** Bug triage and fixing is time-consuming. Automated hunting accelerates resolution for well-specified issues. Regression tests prevent reoccurrence.
- **Dependencies:** Issue tracker integration, code search/analysis tools, test framework access, GitLab runner configuration, PR template.
- **Metrics:**
  - Effort (high—requires sophisticated debugging heuristics).
  - Bug resolution time (hours from issue to PR).
  - Fix quality (pass rate of regression tests).
  - False fix rate (PRs that don't actually resolve the issue).

### Release Readiness Bot — **Normie**
- **Idea:** CAO flow aggregates release notes, checks component versions, ensures docs/tests/telemetry up to date, then drafts release PR.
- **Why:** Shortens release prep and standardizes checklists.
- **Dependencies:** Access to change logs, tests, packaging scripts.
- **Metrics:**
  - Effort.
  - Release frequency (how many cycles benefit).
  - Risk (false pass/false fail consequences).
  - Automation coverage (how much remains manual).

### Multi-Agent Code Review Swarm — **Normie**
- **Idea:** Supervisor coordinates developer/reviewer agents per PR, ensures review checklists, runs targeted tests, and summarizes findings.
- **Why:** Accelerates review throughput while preserving quality standards.
- **Dependencies:** Trusted agent profiles, repo access, test invocation (wctl run-pytest etc.).
- **Metrics:**
  - Effort.
  - Review quality increase (defect catch rate).
  - Cycle time reduction.
  - Governance risk (rogue merges).

### Database Migration Validation — **Glowie**
- **Idea:** Supervisor spawns workers to validate parquet schema migrations across landuse/soils/watersheds. Each worker checks ID normalization, column types, GeoJSON consistency.
- **Why:** Schema changes are high-risk; automated validation prevents data corruption.
- **Dependencies:** Migration checklist, DuckDB query templates, rollback procedures.
- **Metrics:**
  - Effort.
  - Risk mitigated (severity of bad migration).
  - Coverage (fraction of schema validated).
  - Maintenance.

---

## Emergency Response

### Burned Area Emergency Response Analyst — **Normie**
- **Idea:** Flow triggers on burn severity data availability. Agents coordinate: WEPP Disturbed for watersheds intersecting fire, analyze data, write draft BAER reports, collaborative editing of reports through interactive agent.
- **Why:** Time-sensitive emergency response requires rapid, coordinated analysis. Automated draft generation accelerates report delivery to emergency managers. Interactive editing ensures domain expert oversight.
- **Dependencies:** Burn severity data sources (MTBS, RAVG), WEPP Disturbed integration, report templates (USFS BAER format), geospatial intersection queries, collaborative editing interface.
- **Metrics:**
  - Effort (high—WEPP Disturbed integration, report template authoring, validation).
  - Response time (hours from burn data to draft report).
  - Report quality (measured by emergency manager feedback).
  - Adoption (BAER teams using the system).

---

## Advanced Research & Experimentation

### Swarm-Based Parameter Calibration — **Normie**
- **Idea:** Multiple agents explore parameter space independently. Send_message coordinates findings: "Found local optimum at X=5, Y=3". Supervisor refines search based on collective intelligence.
- **Why:** Advanced optimization technique; demonstrates CAO's swarm coordination capabilities.
- **Dependencies:** Objective function definition, convergence criteria, experimental validation.
- **Metrics:**
  - Effort (high—research-grade implementation).
  - Innovation potential.
  - Calibration quality vs. traditional methods.
  - Maintenance complexity.

---

### Suggested Prioritization Matrix
Score each candidate (1–5, where 5 = highest/most favourable) on:

| Metric | Description |
| --- | --- |
| Effort | Estimated engineering effort (lower score = more effort required). |
| Impact | Value/benefit if delivered (doc quality, productivity, reliability). |
| Risk | Likelihood/severity of negative outcomes (higher score = lower risk). |
| Adoption | Expected user/teams uptake (higher score = more eager stakeholders). |
| Maintenance | Ongoing support cost (higher score = lower maintenance burden). |

Optional: add weights (e.g. Impact ×2) to reflect strategic priorities this quarter.
