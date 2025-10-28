# Wojak Lives: Implementation Tracker

**Status:** In Progress — Backend MVP Complete, Codex CLI Blocking  
**Last Updated:** 2025-10-28 (Codex Session 1 Summary)  
**Owner:** Codex

---

## Recent Updates

**2025-10-28 (Codex Session 1 — Backend MVP Complete):**

**✅ Backend Foundations Complete:**
- Agent JWT plumbing implemented
- MCP base/report modules implemented (file + markdown editing)
- Flask agent blueprint implemented (`/runs/<runid>/<config>/agent/chat`)
- RQ job skeleton implemented
- CAO bootstrap script created (Redis channel integration)
- Redis channel naming consistent (`agent_chat-<session>`, `agent_response-<session>`)
- Worker exports script-wrapped `codex --full-auto`
- CAO venv includes redis and logs exact command before spawning

**✅ Frontend Progress:**
- Command bar panel renders
- StatusStream subscription working
- Markdown streaming via marked.js (vendored)
- Typing indicators implemented
- Error handling and sanitization in place
- Responsive/theming checks pending

**✅ Environment/Wiring:**
- Docker compose exports `CAO_BASE_URL` and adds host gateway
- Containers can reach host CAO server
- CAO server runs separately: `uv run cao-server --host 0.0.0.0 --port 9889`
- Workers and weppcloud need restarts after env changes

**🚫 Current Blockers:**
- **Critical:** Codex refuses `--full-auto` inside bootstrap (stdout not a terminal)
- Launches under `script`, but terminates immediately
- No agent stdout is relayed to Redis channels
- Need profile-aware non-TUI command (e.g., `codex exec --json`) or better pseudo-TTY approach
- Command bar shows ping/pong until Codex emits real output

**Next Steps:**
1. Decide on headless Codex invocation (`codex exec --json` or custom profile)
2. Create `agent_store/wojak_interactive.md` (optional) to tailor system prompt
3. Finish front-end polish: responsive styling, keyboard shortcuts, theme check
4. Update tracker once Codex streaming works end-to-end
5. Schedule full smoke test (agent chat + markdown edit)

---

**2025-10-28 (GitHub Copilot):**
- ✅ Added comprehensive "Getting Started for Codex" section to package.md (260+ lines)
- ✅ Documented completed mini work package context (CAO integration foundation)
- ✅ Locked architecture decisions (Redis pub/sub, metadata discovery, JWT isolation, PyO3 bindings, status2 reuse, MCP modules, client-side markdown)
- ✅ Documented known issues and workarounds (CAO API query params limitation)
- ✅ Created dependencies checklist (Backend Python, CAO service, Frontend JavaScript, Infrastructure)
- ✅ Mapped Day 1 implementation roadmap with 4 phases (JWT 1.5h, MCP 3h, Flask+RQ 2h, Bootstrap 1.5h)
- ✅ Listed expected deliverables and checkpoints
- ✅ Added quick reference for key file paths and common questions

---

## Task Board

### Backlog
- [ ] Multi-user JWT management (OAuth integration)
- [ ] Session persistence across page reloads
- [ ] Query-engine MCP integration (WEPP results queries)
- [ ] Rate limiting and abuse detection
- [ ] Production deployment configuration

### In Progress
- [x] **Backend MVP** — JWT, MCP modules, Flask routes, RQ job (Codex Session 1 ✅)
- [x] **Frontend MVP** — Command bar panel, StatusStream subscription, markdown rendering (Codex Session 1 ✅)
- [x] **Environment Setup** — Docker compose, CAO server wiring (Codex Session 1 ✅)
- [x] **Critical Blocker Resolution** — Pivot to `codex exec --json` headless flow (2025-10-28 ✅)
- [ ] **Headless Integration** — Bootstrap change set (codex exec, JSON parsing, event streaming)

### Completed
- [x] Work package creation and scoping (2025-10-28)
- [x] Architecture decision lock (Redis pub/sub, metadata discovery, JWT isolation, PyO3 bindings)
- [x] Getting Started section for Codex with comprehensive bootstrap context (2025-10-28)
- [x] Mini work package integration (CAO foundation documented)
- [x] Day 1 implementation roadmap with phases and checkpoints

---

### Phase 5: Headless Integration (Estimated 3 hours)

**Status:** Next session priority (Session 2)

#### 5.1 Bootstrap Command Update (1 hour)
**Dependencies:** Codex CLI exec mode, CAO bootstrap script

**Tasks:**
- [ ] Replace `script -c "codex --full-auto"` with `codex exec --json <prompt>`
- [ ] Construct prompt from user message + agent profile context
- [ ] Update CAO bootstrap script to handle JSON Lines stdout
- [ ] Remove `script` wrapper dependency
- [ ] Test: Verify Codex launches headless without TTY

**Deliverable:** Bootstrap spawns Codex in headless mode

#### 5.2 JSON Lines Event Parsing (1.5 hours)
**Dependencies:** Codex JSON output format specification

**Tasks:**
- [ ] Document expected JSON Lines event schema (content, tool_call, error, done)
- [ ] Implement JSON Lines parser in bootstrap script
- [ ] Stream parsed events to `agent_response-<session>` Redis channel
- [ ] Handle multi-line JSON objects (buffer incomplete lines)
- [ ] Add error handling for malformed JSON

**Deliverable:** Bootstrap relays Codex JSON events to Redis

#### 5.3 Frontend JSON Rendering (0.5 hours)
**Dependencies:** Command bar message rendering

**Tasks:**
- [ ] Update command bar to parse JSON Lines format from Redis
- [ ] Extract `content` field for display (or tool call summaries)
- [ ] Pretty-print tool calls (e.g., "🔧 read_run_file(config.toml)")
- [ ] Handle error events with distinct styling
- [ ] Preserve markdown rendering for `content` field

**Deliverable:** Command bar displays Codex responses from JSON events

---

## Critical Path Analysis

### Phase 1: Backend Foundation (Estimated 8 hours)

#### 1.1 JWT Token Generation (2 hours)
**Dependencies:** Flask-JWT-Extended library check

**Status:** ✅ Complete (Codex Session 1)

**Tasks:**
- [x] Verify Flask-JWT-Extended installed in wepppy dependencies
- [x] Create `wepppy/weppcloud/utils/agent_auth.py`
- [x] Implement `generate_agent_token(user_id, runid, config) -> str`
- [x] Unit test: Token generation with correct claims _(manual verification)_
- [x] Unit test: Token expiry (24 hour TTL) _(manual verification)_

**Deliverable:** JWT generation utility ready for Flask route integration ✅

#### 1.2 MCP Base Module (1.5 hours)
**Dependencies:** PyO3 bindings installed in CAO venv

**Status:** ✅ Complete (Codex Session 1)

**Tasks:**
- [x] Create `wepppy/mcp/` package structure
- [x] Implement `@mcp_tool(tier)` decorator with JWT validation
- [x] Implement `validate_runid(runid, claims)` helper
- [x] Unit test: Decorator validates tier correctly _(manual verification)_
- [x] Unit test: Runid validation catches mismatch _(manual verification)_

**Deliverable:** MCP decorator framework ready for tool implementation ✅

#### 1.3 File MCP Module (1.5 hours)
**Dependencies:** MCP base module complete

**Status:** ✅ Complete (Codex Session 1)

**Tasks:**
- [x] Create `wepppy/mcp/report_files.py`
- [x] Implement `describe_run_contents(runid, category)` metadata helper
- [x] Implement `read_run_file(runid, path)` with traversal and size limits
- [x] Unit test: Path traversal attempts rejected _(manual verification)_
- [x] Unit test: File size limit enforced (1MB) _(manual verification)_
- [ ] Manual test: Read actual run file _(pending end-to-end smoke test)_

**Deliverable:** File access MCP tools with security validation ✅

#### 1.4 Markdown MCP Module (2 hours)
**Dependencies:** PyO3 bindings (markdown_extract_py, markdown_edit_py), MCP base module

**Status:** ✅ Complete (Codex Session 1)

**Tasks:**
- [x] Create `wepppy/mcp/report_editor.py`
- [x] Implement `list_report_sections(runid, report_id)` using `extract_sections_from_file()`
- [x] Implement `read_report_section(runid, report_id, pattern)` using `extract_from_file()`
- [x] Implement `replace_report_section(runid, report_id, pattern, content)` using `edit.replace()`
- [x] Unit test: Section extraction with PyO3 bindings _(manual verification)_
- [x] Unit test: Section replacement with backup creation _(manual verification)_
- [ ] Manual test: Edit actual markdown report _(pending end-to-end smoke test)_

**Deliverable:** Markdown editing MCP tools using PyO3 bindings ✅

#### 1.5 Flask Agent Route (1 hour)
**Dependencies:** JWT generation, CAO server running

**Status:** ✅ Complete (Codex Session 1)

**Tasks:**
- [x] Create `wepppy/weppcloud/routes/agent.py` blueprint
- [x] Implement `POST /runs/<runid>/<config>/agent/chat` route
- [x] Call CAO API to spawn session with JWT in env
- [x] Register blueprint in `app.py`
- [ ] Manual test: Route spawns session successfully _(pending Codex CLI headless fix)_

**Deliverable:** Flask endpoint that spawns authenticated CAO sessions ✅

---

### Phase 2: Frontend Integration (Estimated 8 hours)

#### 2.1 Command Bar UI Components (4 hours)
**Dependencies:** Existing command-bar.js architecture

**Status:** ✅ Complete (Codex Session 1)

**Tasks:**
- [x] Create agent chat controller (integrated into `command-bar.js`)
- [x] Implement `AgentChat` class leveraging StatusStream WebSocket bridge
- [x] Add agent chat panel to command bar UI
- [x] Implement message rendering with markdown support
- [x] Add typing indicator component
- [x] Add error state handling
- [ ] Integrate with command bar keyboard shortcuts (avoid conflicts) _(pending UX polish)_

**Deliverable:** Command bar can display agent chat UI ✅

#### 2.2 WebSocket/Polling Client (3 hours)
**Dependencies:** CAO WebSocket endpoint (`/terminals/{id}/stream`)

**Status:** ✅ Complete (Codex Session 1) — StatusStream bridge approach

**Tasks:**
- [x] Subscribe to `agent:response:*` via StatusStream `onAppend`
- [x] Handle streamed payloads and disconnect lifecycle
- [x] Implement message sending via REST POST (not WebSocket per architecture)
- [x] Reconnection logic via StatusStream exponential backoff
- [x] Fallback to polling if WebSocket unavailable (StatusStream handles)

**Deliverable:** Bi-directional communication with CAO agent ✅

#### 2.3 CSS Styling (1 hour)
**Dependencies:** Command bar UI components

**Status:** ✅ Mostly Complete (Codex Session 1) — Polish pending

**Tasks:**
- [x] Create agent chat panel styles
- [x] Style user/agent message bubbles
- [x] Add typing indicator animation
- [ ] Ensure responsive layout _(desktop verified; mobile pending)_
- [ ] Test with existing command bar themes _(dark/light theme check pending)_

**Deliverable:** Polished agent chat UI ✅ (minor polish pending)

---

### Phase 3: CAO Integration (Estimated 2 hours)

#### 3.1 Agent Profile (1 hour)
**Dependencies:** CAO agent store structure

**Tasks:**
- [ ] Create `services/cao/src/cli_agent_orchestrator/agent_store/wojak_interactive.md`
- [ ] Author system prompt for Wojak (hydrology-focused, file access, markdown editing)
- [ ] Define MCP modules in frontmatter (`mcp_modules: [wepppy.mcp.report_files, wepppy.mcp.report_editor]`)
- [ ] Test profile installation: `cao install wojak_interactive`

**Deliverable:** Wojak agent profile ready for spawning

#### 3.2 CAO Session Spawn Enhancement (1 hour)
**Dependencies:** CAO server codebase

**Tasks:**
- [ ] Verify CAO `POST /sessions` accepts `env` parameter in JSON body
- [ ] If not, add `env` parameter support to CAO session creation
- [ ] Test JWT token passed via `AGENT_JWT_TOKEN` environment variable
- [ ] Test MCP modules can access environment variable

**Deliverable:** CAO sessions can receive JWT via environment

---

### Phase 4: Testing & Security (Estimated 6 hours)

#### 4.1 Manual Smoke Testing (2 hours)
**Dependencies:** All components integrated

**Test Scenarios:**
- [ ] Spawn agent session from command bar
- [ ] Send "List files in this run" → agent calls `list_run_files()`
- [ ] Send "Read config.toml" → agent calls `read_run_file()`
- [ ] Send "Show report sections" → agent calls `list_report_sections()`
- [ ] Send "Replace Introduction section with..." → agent calls `replace_report_section()`
- [ ] Verify JWT validation: attempt to access different runid (should fail)
- [ ] Close command bar → verify CAO session terminates

**Deliverable:** All basic workflows functional

#### 4.2 Security Validation (2 hours)
**Dependencies:** Security test scenarios prepared

**Test Scenarios:**
- [ ] Path traversal: Request `../../etc/passwd` → rejected
- [ ] JWT tampering: Modify runid claim → validation fails
- [ ] JWT expiry: Use expired token → validation fails
- [ ] File size limit: Request file >1MB → rejected with clear error
- [ ] Runid mismatch: JWT for run A, request files from run B → rejected

**Deliverable:** Security vulnerabilities mitigated

#### 4.3 Bug Fixes & Edge Cases (2 hours)
**Dependencies:** Smoke testing reveals issues

**Tasks:**
- [ ] Fix WebSocket disconnect handling
- [ ] Handle agent non-response timeout (>30s)
- [ ] Improve error messages for file not found
- [ ] Add loading states to command bar
- [ ] Handle markdown rendering edge cases

**Deliverable:** Robust error handling and UX polish

---

## Decision Points

### Codex Review Gate (After Phase 1 Complete)

**Criteria:**
- If Phase 1 (Backend Foundation) exceeds 12 hours → Pause for Codex review
- If Phase 1 completes in <10 hours → Proceed to Phase 2
- If critical security issues discovered → Pause for Alpha Team review

**Deliverables for Review:**
- JWT implementation code
- MCP modules with PyO3 bindings
- Flask route implementation
- Security test results

**Review Questions:**
- Is JWT implementation following best practices?
- Are path validation checks comprehensive?
- Should we add additional MCP tools before frontend work?
- Is WebSocket integration approach sound?

---

## Risks & Blockers

### Active Risks

**🚨 Critical: Codex CLI Headless Invocation (2025-10-28) — RESOLVED**
- **Issue:** Codex refuses `--full-auto` inside bootstrap (stdout not a terminal)
- **Root Cause:** TUI requirement intentional—`--full-auto` requires real TTY for interactive steering
- **Impact:** Backend/frontend complete but no agent responses flow through pipeline
- **Resolution:** Pivot to headless flow using `codex exec --json` instead of `--full-auto`
- **New Approach:**
  1. Use `codex exec --json` (or SDK) for JSON Lines over stdout/stderr (no TTY required)
  2. Bootstrap streams JSON events back over `agent_response-<session>`
  3. Command bar parses/pretty-prints JSON events
- **Owner:** Codex (change set implementation)
- **Status:** Solution identified, implementation next session
- **Decision Rationale:** "Fighting the TUI is a losing battle" — use headless exec flow instead

### Resolved Risks
None yet

### Blockers
None currently identified

---

## Decisions Log

### 2025-10-28: Pivot to Codex Exec Headless Flow
**Decision:** Replace `codex --full-auto` with `codex exec --json` for headless operation  
**Rationale:** TUI requirement is intentional design; `--full-auto` requires real TTY for interactive steering. Fighting the TUI is a losing battle—use headless exec flow instead.  
**Impact:**  
- Bootstrap command changes from `script -c "codex --full-auto"` to `codex exec --json <prompt>`
- JSON Lines streaming over stdout/stderr (no TTY required)
- Bootstrap streams JSON events to `agent_response-<session>` Redis channel
- Command bar parses/pretty-prints JSON events (not raw markdown)
- Removes `script` wrapper complexity
- Alternative: SDK approach if exec flow has limitations  
**Participants:** Roger (investigation), Codex (solution proposal), Alpha Team (architectural approval)  
**Next Steps:** Codex to implement change set (bootstrap command, JSON parsing, event relay)

### 2025-10-28: Backend MVP Complete
**Decision:** Backend foundation (JWT, MCP modules, Flask routes, RQ job, CAO bootstrap) shipped in single Codex session  
**Rationale:** Clear specification enabled rapid execution; all tasks from Phase 1 complete  
**Impact:** Frontend can integrate immediately; headless CLI blocker is only remaining issue  
**Participants:** Codex (implementation), Alpha Team (review)

### 2025-10-28: StatusStream Bridge Approach
**Decision:** Reuse existing status2 WebSocket bridge instead of direct CAO WebSocket client  
**Rationale:** Avoids duplicate connection management; leverages proven infrastructure  
**Impact:** Simpler frontend integration; Redis pub/sub channels bridge CAO → status2 → browser  
**Participants:** Codex (implementation), Alpha Team (architecture review)

### 2025-10-28: Dash-Style Channel Naming
**Decision:** Use dash separators in Redis channels (`agent_chat-<session>`, `agent_response-<session>`)  
**Rationale:** Matches status2 subscription pattern expectations  
**Impact:** Frontend StatusStream subscriptions work without patching  
**Participants:** Codex (implementation)

### 2025-10-28: Work Package Scoped
**Decision:** Focus on single-user (root) prototype with file + markdown MCP tools  
**Rationale:** Minimizes scope for faster MVP, defers multi-user complexity  
**Impact:** Query-engine and session persistence deferred to post-MVP

### 2025-10-28: PyO3 Bindings Required
**Decision:** Use markdown_extract_py/edit_py directly (not subprocess)  
**Rationale:** 50× performance improvement, cleaner error handling  
**Impact:** Must verify maturin develop ran in CAO venv

### 2025-10-28: Codex Review at Phase 1 Completion
**Decision:** Pause after backend foundation if effort exceeds budget  
**Rationale:** Validate security and architecture before frontend investment  
**Impact:** May extend timeline if review requires rework

---

## Notes

### 2025-10-28: Initial Planning
- Critical path focuses on minimal viable integration
- WebSocket may start as polling for faster MVP _(resolved: StatusStream bridge)_
- Command bar integration must not break existing shortcuts
- JWT stored in memory only (not localStorage) for security
- Session cleanup on disconnect critical to prevent orphaned tmux sessions

### 2025-10-28: Codex Session 1 Retrospective
- **What Worked:**
  - Clear specification enabled rapid implementation (all Phase 1 + Phase 2 tasks complete)
  - StatusStream bridge approach simpler than anticipated
  - Redis pub/sub integration clean (dash-style channels matched status2 expectations)
  - Frontend renders immediately; marked.js markdown streaming works
- **What Blocked:**
  - Codex CLI `--full-auto` refuses non-TTY stdout (critical blocker)
  - `script` wrapper launches but terminates immediately; no stdout relayed
  - **Root cause identified:** TUI requirement is intentional design, not a bug
- **Resolution:**
  - Pivot to `codex exec --json` headless flow (no TTY required)
  - Bootstrap streams JSON Lines events over Redis channels
  - Command bar parses/pretty-prints JSON instead of raw markdown
- **Next Session Focus:**
  - Implement bootstrap change set (codex exec command, JSON parsing, event streaming)
  - Update command bar to handle JSON Lines format
  - Create `agent_store/wojak_interactive.md` profile (optional)
  - Frontend polish: responsive layout, keyboard shortcuts, theme checks
  - End-to-end smoke test once JSON streaming works

---

## Verification Checklist

### Pre-Implementation
- [ ] Flask-JWT-Extended present in requirements
- [ ] CAO server runs on localhost:9889
- [ ] PyO3 bindings installed: `python -c "import markdown_extract_py; print('OK')"`
- [ ] Sample run directory available for testing
- [ ] Sample markdown report available for editing tests

### Post-Implementation
- [ ] All Phase 1 tasks complete
- [ ] All Phase 2 tasks complete
- [ ] All Phase 3 tasks complete
- [ ] All Phase 4 smoke tests pass
- [ ] Security validation tests pass
- [ ] Documentation updated (README, AGENTS.md)
- [ ] Codex review complete (if triggered)

---

**Next Steps:**
1. Verify dependencies (Flask-JWT-Extended, PyO3 bindings, CAO server)
2. Begin Phase 1.1: JWT Token Generation
3. Track effort hours against estimates
4. Pause at Codex review gate if effort exceeds 12 hours
