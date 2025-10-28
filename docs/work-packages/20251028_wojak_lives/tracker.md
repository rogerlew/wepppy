# Wojak Lives: Implementation Tracker

**Status:** Critical Path Analysis  
**Last Updated:** 2025-10-28  
**Owner:** Alpha Team (Roger)

---

## Task Board

### Backlog
- [ ] Multi-user JWT management (OAuth integration)
- [ ] Session persistence across page reloads
- [ ] Query-engine MCP integration (WEPP results queries)
- [ ] Rate limiting and abuse detection
- [ ] Production deployment configuration

### In Progress
- [ ] **Critical Path Analysis** — Determine scope and decision point for Codex review

### Completed
- [x] Work package creation and scoping (2025-10-28)

---

## Critical Path Analysis

### Phase 1: Backend Foundation (Estimated 8 hours)

#### 1.1 JWT Token Generation (2 hours)
**Dependencies:** Flask-JWT-Extended library check

**Tasks:**
- [ ] Verify Flask-JWT-Extended installed in wepppy dependencies
- [ ] Create `wepppy/weppcloud/utils/agent_auth.py`
- [ ] Implement `generate_agent_token(user_id, runid, config) -> str`
- [ ] Unit test: Token generation with correct claims
- [ ] Unit test: Token expiry (24 hour TTL)

**Deliverable:** JWT generation utility ready for Flask route integration

#### 1.2 MCP Base Module (1.5 hours)
**Dependencies:** PyO3 bindings installed in CAO venv

**Tasks:**
- [ ] Create `wepppy/mcp/` package structure
- [ ] Implement `@mcp_tool(tier)` decorator with JWT validation
- [ ] Implement `validate_runid(runid, claims)` helper
- [ ] Unit test: Decorator validates tier correctly
- [ ] Unit test: Runid validation catches mismatch

**Deliverable:** MCP decorator framework ready for tool implementation

#### 1.3 File MCP Module (1.5 hours)
**Dependencies:** MCP base module complete

**Tasks:**
- [ ] Create `wepppy/mcp/report_files.py`
- [ ] Implement `list_run_files(runid, glob_pattern)` with path validation
- [ ] Implement `read_run_file(runid, path)` with size limits
- [ ] Unit test: Path traversal attempts rejected
- [ ] Unit test: File size limit enforced (1MB)
- [ ] Manual test: Read actual run file

**Deliverable:** File access MCP tools with security validation

#### 1.4 Markdown MCP Module (2 hours)
**Dependencies:** PyO3 bindings (markdown_extract_py, markdown_edit_py), MCP base module

**Tasks:**
- [ ] Create `wepppy/mcp/report_editor.py`
- [ ] Implement `list_report_sections(runid, report_id)` using `extract_sections_from_file()`
- [ ] Implement `read_report_section(runid, report_id, pattern)` using `extract_from_file()`
- [ ] Implement `replace_report_section(runid, report_id, pattern, content)` using `edit.replace()`
- [ ] Unit test: Section extraction with PyO3 bindings
- [ ] Unit test: Section replacement with backup creation
- [ ] Manual test: Edit actual markdown report

**Deliverable:** Markdown editing MCP tools using PyO3 bindings

#### 1.5 Flask Agent Route (1 hour)
**Dependencies:** JWT generation, CAO server running

**Tasks:**
- [ ] Create `wepppy/weppcloud/routes/agent.py` blueprint
- [ ] Implement `POST /runs/<runid>/<config>/agent/chat` route
- [ ] Call CAO API to spawn session with JWT in env
- [ ] Register blueprint in `app.py`
- [ ] Manual test: Route spawns session successfully

**Deliverable:** Flask endpoint that spawns authenticated CAO sessions

---

### Phase 2: Frontend Integration (Estimated 8 hours)

#### 2.1 Command Bar UI Components (4 hours)
**Dependencies:** Existing command-bar.js architecture

**Tasks:**
- [ ] Create `agent-chat.js` module
- [ ] Implement `AgentChat` class with WebSocket client
- [ ] Add agent chat panel to command bar UI
- [ ] Implement message rendering with markdown support
- [ ] Add typing indicator component
- [ ] Add error state handling
- [ ] Integrate with command bar keyboard shortcuts (avoid conflicts)

**Deliverable:** Command bar can display agent chat UI

#### 2.2 WebSocket/Polling Client (3 hours)
**Dependencies:** CAO WebSocket endpoint (`/terminals/{id}/stream`)

**Tasks:**
- [ ] Implement WebSocket connection to CAO
- [ ] Handle `onmessage`, `onerror`, `onclose` events
- [ ] Implement message sending via WebSocket
- [ ] Add connection state management
- [ ] Add reconnection logic for dropped connections
- [ ] Fallback to polling if WebSocket unavailable (optional)

**Deliverable:** Bi-directional communication with CAO agent

#### 2.3 CSS Styling (1 hour)
**Dependencies:** Command bar UI components

**Tasks:**
- [ ] Create agent chat panel styles
- [ ] Style user/agent message bubbles
- [ ] Add typing indicator animation
- [ ] Ensure responsive layout
- [ ] Test with existing command bar themes

**Deliverable:** Polished agent chat UI

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
None currently identified

### Resolved Risks
None yet

### Blockers
None currently identified

---

## Decisions Log

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
- WebSocket may start as polling for faster MVP
- Command bar integration must not break existing shortcuts
- JWT stored in memory only (not localStorage) for security
- Session cleanup on disconnect critical to prevent orphaned tmux sessions

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
