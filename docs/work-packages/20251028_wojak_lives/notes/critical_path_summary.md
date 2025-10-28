# Critical Path Summary: Wojak Lives

**Date**: 2025-10-28  
**Purpose**: Minimal viable integration for interactive agent chat in WEPPcloud command bar

---

## Executive Summary

**Goal**: Roger (root user) can chat with Wojak agent through command bar, request file contents, and edit markdown reports—all within browser UI with zero manual tmux interaction.

**Estimated Effort**: 16-24 hours (2-3 days)

**Codex Review Gate**: After 12 hours (Phase 1 complete) to validate architecture/security before frontend investment.

---

## Critical Path Components

### Phase 1: Backend Foundation (8 hours)
**Decision Point**: If >12 hours, pause for Codex review

1. **JWT Token Generation** (2h)
   - `wepppy/weppcloud/utils/agent_auth.py`
   - Generate JWT scoped to user + runid + config
   - 24 hour expiry, tier claim for permission enforcement

2. **MCP Base Module** (1.5h)
   - `wepppy/mcp/base.py`
   - `@mcp_tool(tier)` decorator with JWT validation
   - `validate_runid(runid, claims)` helper

3. **File MCP Module** (1.5h)
   - `wepppy/mcp/report_files.py`
   - `list_run_files(runid, glob)` — with path traversal prevention
   - `read_run_file(runid, path)` — 1MB size limit

4. **Markdown MCP Module** (2h)
   - `wepppy/mcp/report_editor.py`
   - Uses PyO3 bindings (markdown_extract_py, markdown_edit_py)
   - `list_report_sections()`, `read_report_section()`, `replace_report_section()`

5. **Flask Agent Route** (1h)
   - `wepppy/weppcloud/routes/agent.py`
   - `POST /runs/<runid>/<config>/agent/chat`
   - Spawns CAO session with JWT in environment

---

### Phase 2: Frontend Integration (8 hours)

1. **Command Bar UI** (4h)
   - `wepppy/weppcloud/static-src/command-bar/agent-chat.js`
   - Agent chat panel with message rendering
   - Typing indicators, error states

2. **WebSocket Client** (3h)
   - Connect to CAO `/terminals/{id}/stream`
   - Bi-directional messaging
   - Connection state management, reconnection

3. **CSS Styling** (1h)
   - Agent chat panel styles
   - Message bubbles, animations
   - Responsive layout

---

### Phase 3: CAO Integration (2 hours)

1. **Agent Profile** (1h)
   - `services/cao/.../agent_store/wojak_interactive.md`
   - System prompt for hydrology + file access
   - MCP modules in frontmatter

2. **CAO Session Spawn** (1h)
   - Verify `POST /sessions` accepts `env` parameter
   - Test JWT passed via `AGENT_JWT_TOKEN` environment variable

---

### Phase 4: Testing & Security (6 hours)

1. **Manual Smoke Testing** (2h)
   - List files, read file, show report sections, replace section
   - Verify JWT validation rejects wrong runid
   - Session cleanup on disconnect

2. **Security Validation** (2h)
   - Path traversal rejection
   - JWT tampering detection
   - File size limit enforcement
   - Runid mismatch rejection

3. **Bug Fixes** (2h)
   - WebSocket disconnect handling
   - Agent timeout handling (>30s)
   - Error message improvements
   - UX polish

---

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────────┐
│ Browser (command-bar.js)                                    │
│  - Agent chat panel UI                                       │
│  - WebSocket client                                          │
└───────────────────────┬─────────────────────────────────────┘
                        │ WebSocket
                        ↓
┌─────────────────────────────────────────────────────────────┐
│ Flask App (weppcloud)                                        │
│  - POST /runs/<runid>/<config>/agent/chat                   │
│  - JWT generation (user + runid + config scope)             │
└───────────────────────┬─────────────────────────────────────┘
                        │ HTTP
                        ↓
┌─────────────────────────────────────────────────────────────┐
│ CAO Server (localhost:9889)                                  │
│  - POST /sessions (spawn with env: AGENT_JWT_TOKEN)          │
│  - WebSocket: /terminals/{id}/stream                         │
└───────────────────────┬─────────────────────────────────────┘
                        │ tmux session spawn
                        ↓
┌─────────────────────────────────────────────────────────────┐
│ Wojak Agent (tmux session)                                   │
│  - Codex CLI with agent profile                              │
│  - MCP modules loaded in-process                             │
└───────────────────────┬─────────────────────────────────────┘
                        │ Python imports
                        ↓
┌─────────────────────────────────────────────────────────────┐
│ MCP Modules (wepppy.mcp.*)                                   │
│  ├─ report_files: list_run_files, read_run_file             │
│  └─ report_editor: list_sections, read_section, replace_*   │
│      (uses PyO3 bindings: markdown_extract_py, edit_py)      │
└─────────────────────────────────────────────────────────────┘
```

---

## Security Model

### JWT Claims
```json
{
  "identity": "roger@uidaho.edu",
  "runid": "abc123",
  "config": "default",
  "tier": "wojak",
  "exp": 1730246400  // 24 hours from issue
}
```

### Permission Enforcement
- Every `@mcp_tool` call validates JWT signature and expiry
- `validate_runid()` ensures requested runid matches token scope
- Path validation prevents traversal outside `/geodata/weppcloud_runs/{runid}/`
- File size limits prevent memory exhaustion (1MB text files)

### Threat Mitigations
| Threat | Mitigation |
|--------|-----------|
| JWT tampering | Signature verification fails |
| JWT replay (different runid) | Runid claim validation rejects |
| Path traversal | `Path.resolve()` + parent checks |
| File size DoS | Hard limit at 1MB per read |
| Token leakage | Stored in memory only, regenerated per session |
| Session hijack | WebSocket tied to browser session, cleanup on disconnect |

---

## Success Criteria

### Functional
- ✅ Roger can spawn agent from command bar
- ✅ Agent can list files in run directory
- ✅ Agent can read file contents (<1MB)
- ✅ Agent can list markdown report sections
- ✅ Agent can replace markdown section with backup
- ✅ JWT validation rejects tampered/mismatched tokens
- ✅ Session terminates when command bar closes

### Performance
- ✅ Agent response latency <2s for file reads
- ✅ PyO3 markdown operations <1ms (vs 5-10ms subprocess)
- ✅ UI responsive, no blocking on agent calls

### Security
- ✅ Path traversal attempts rejected
- ✅ JWT signature verification enforced
- ✅ File size limits enforced
- ✅ Runid scope enforced

---

## Risks & Mitigations

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| CAO WebSocket complexity | Medium | High | Start with polling fallback |
| JWT token leakage | Low | High | Memory-only storage, no localStorage |
| Path traversal vuln | Low | High | Comprehensive validation tests |
| PyO3 bindings missing | Low | Medium | Verify maturin develop ran |
| Command bar UI conflicts | Medium | Medium | Namespace keybindings separately |
| Agent timeout (>30s) | Medium | Low | Set expectations, add timeout UI |

---

## Open Questions

1. **WebSocket vs Polling**: Start with WebSocket or fallback to polling for faster MVP?
   - **Recommendation**: WebSocket first; simpler state management
   
2. **Session Persistence**: Should sessions survive page reloads?
   - **Recommendation**: No for MVP; regenerate on reload
   
3. **Error Handling**: What should UI show for agent errors?
   - **Recommendation**: Error message bubble with retry option
   
4. **Agent Timeout**: How long before declaring agent unresponsive?
   - **Recommendation**: 30s soft timeout (show "still thinking"), 60s hard timeout (offer to restart)

---

## Dependencies Checklist

### Pre-Implementation
- [ ] CAO server running: `curl http://localhost:9889/health`
- [ ] PyO3 bindings installed: `python -c "import markdown_extract_py; print('OK')"`
- [ ] Flask-JWT-Extended available: `python -c "import flask_jwt_extended; print('OK')"`
- [ ] Sample run directory: `/geodata/weppcloud_runs/<test-runid>/`
- [ ] Sample markdown report: `<test-runid>/reports/test.md`

### Post-Implementation
- [ ] All smoke tests pass
- [ ] Security validation tests pass
- [ ] Documentation updated
- [ ] Codex review complete (if triggered)

---

## Next Actions

1. **Verify Dependencies** — Run checklist above, resolve any missing components
2. **Begin Phase 1.1** — Implement JWT generation utility
3. **Track Effort** — Log hours against 12-hour Codex review gate
4. **Update Tracker** — Mark tasks complete as work progresses
5. **Codex Review** — If Phase 1 >12 hours, pause for architecture validation

---

## References

- [package.md](../package.md) — Full work package specification
- [tracker.md](../tracker.md) — Detailed task board with hours tracking
- [CAO README](../../../services/cao/README.md) — CAO architecture
- [PyO3 API Reference](/workdir/markdown-extract/docs/work-packages/20251028_pyo3_bindings/PYTHON_API_REFERENCE.md)
