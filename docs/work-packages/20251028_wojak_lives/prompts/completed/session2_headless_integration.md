# Session 2: Codex Headless Integration Implementation

**Created:** 2025-10-28  
**Owner:** Codex  
**Duration Estimate:** 3 hours  
**Prerequisites:** Session 1 backend/frontend MVP complete

---

## Context

Session 1 delivered complete backend (JWT, MCP modules, Flask routes, RQ job, CAO bootstrap) and frontend MVP (command bar panel, StatusStream subscription, markdown rendering). The critical blocker was resolved: **Codex CLI `--full-auto` requires a TTY by design**. 

**Resolution:** Pivot to `codex exec --json` for headless operation. This session implements the JSON Lines streaming integration.

---

## Architectural Decision: Headless Flow

### What Changed
- **Before:** `script -c "codex --full-auto"` attempted to wrap TUI in pseudo-TTY
- **After:** `codex exec --json <prompt>` outputs JSON Lines over stdout (no TTY required)

### Why It Changed
- TUI requirement is **intentional design** (interactive steering)
- "Fighting the TUI is a losing battle" — use headless exec flow instead
- JSON Lines provides structured output (content, tool_calls, errors, done events)

### Impact
1. Bootstrap command changes from script wrapper to direct exec
2. JSON Lines parsing required (buffer incomplete lines, handle multi-line objects)
3. Frontend parses JSON events instead of raw markdown
4. Cleaner architecture (no script workarounds)

---

## Implementation Tasks

### Phase 5.1: Bootstrap Command Update (1 hour)

**File:** `/workdir/wepppy/services/cao/bootstrap_wojak.py` (or similar)

**Current State (from Session 1):**
```python
# Likely something like:
cmd = ["script", "-c", f"codex --full-auto"]
# ... Redis pub/sub wiring
```

**Required Changes:**
1. **Replace command construction:**
   ```python
   # Build prompt from user message + context
   prompt = f"""You are Wojak, a hydrology assistant for run {runid}.
   User: {user_message}
   
   Available tools: describe_run_contents, read_run_file, list_report_sections, etc.
   """
   
   # Use codex exec --json with wojak_interactive profile
   cmd = [
       "codex", "exec", "--json",
       "--profile", "wojak_interactive",  # or via CAO profile loading
       "--prompt", prompt
   ]
   ```

2. **Remove script wrapper dependency**

3. **Update environment variables:**
   ```python
   env = {
       "AGENT_JWT_TOKEN": jwt_token,
       "RUNID": runid,
       "CONFIG": config,
       # ... existing Redis channel vars
   }
   ```

4. **Test headless launch:**
   - Verify Codex spawns without TTY error
   - Check JSON Lines appear on stdout

**Deliverable:** Bootstrap spawns Codex in headless mode, outputs JSON Lines

---

### Phase 5.2: JSON Lines Event Parsing (1.5 hours)

**File:** Same bootstrap script

**Expected JSON Lines Format (document if unknown):**
```jsonlines
{"type": "content", "text": "Let me check that file for you..."}
{"type": "tool_call", "name": "read_run_file", "args": {"runid": "abc123", "path": "config.toml"}}
{"type": "content", "text": "Here's the configuration:\n\n```toml\n[general]\n..."}
{"type": "done", "success": true}
```

**Required Changes:**

1. **Implement JSON Lines parser:**
   ```python
   import json
   
   buffer = ""
   for line in process.stdout:
       buffer += line
       if line.strip().endswith("}"):  # Complete JSON object
           try:
               event = json.loads(buffer)
               handle_event(event)
               buffer = ""
           except json.JSONDecodeError:
               continue  # Incomplete multi-line JSON
   ```

2. **Event handler:**
   ```python
   def handle_event(event):
       event_type = event.get("type")
       
       if event_type == "content":
           # Stream text content to Redis
           redis_client.publish(
               f"agent_response-{session_id}",
               json.dumps({"type": "content", "text": event["text"]})
           )
       
       elif event_type == "tool_call":
           # Optional: Pretty-print tool calls
           tool_name = event["name"]
           redis_client.publish(
               f"agent_response-{session_id}",
               json.dumps({"type": "tool_call", "name": tool_name})
           )
       
       elif event_type == "error":
           redis_client.publish(
               f"agent_response-{session_id}",
               json.dumps({"type": "error", "message": event["message"]})
           )
       
       elif event_type == "done":
           redis_client.publish(
               f"agent_response-{session_id}",
               json.dumps({"type": "done"})
           )
   ```

3. **Handle malformed JSON:**
   - Log parse errors (don't crash bootstrap)
   - Send error event to frontend

4. **Buffer management:**
   - Handle multi-line JSON objects
   - Clear buffer on successful parse
   - Set max buffer size (10KB) to prevent memory issues

**Deliverable:** Bootstrap relays structured JSON events to Redis channels

---

### Phase 5.3: Frontend JSON Rendering (0.5 hours)

**File:** `/workdir/wepppy/wepppy/weppcloud/controllers_js/command-bar.js` (or agent chat controller)

**Current State (from Session 1):**
Likely assumes raw markdown content from Redis.

**Required Changes:**

1. **Parse JSON events in StatusStream handler:**
   ```javascript
   statusStream.subscribe(`agent_response-${sessionId}`, (data) => {
       try {
           const event = JSON.parse(data);
           handleAgentEvent(event);
       } catch (e) {
           // Fallback: treat as raw text (backward compat)
           appendMessage({ role: 'agent', content: data });
       }
   });
   ```

2. **Event handler:**
   ```javascript
   function handleAgentEvent(event) {
       switch (event.type) {
           case 'content':
               // Append to current message (streaming)
               appendToLastMessage(event.text);
               renderMarkdown();  // marked.js
               break;
           
           case 'tool_call':
               // Pretty-print tool invocation
               appendToolCall(event.name);  // e.g., "🔧 read_run_file(config.toml)"
               break;
           
           case 'error':
               // Distinct error styling
               appendError(event.message);
               break;
           
           case 'done':
               // Hide typing indicator, enable input
               hideTypingIndicator();
               enableInput();
               break;
       }
   }
   ```

3. **Tool call pretty-printing:**
   ```javascript
   function appendToolCall(toolName) {
       const toolElement = document.createElement('div');
       toolElement.className = 'agent-tool-call';
       toolElement.textContent = `🔧 ${toolName}`;
       messagesContainer.appendChild(toolElement);
   }
   ```

4. **CSS for tool calls:**
   ```css
   .agent-tool-call {
       color: var(--vscode-terminal-ansiCyan);
       font-family: var(--vscode-editor-font-family);
       font-size: 0.9em;
       padding: 4px 8px;
       margin: 4px 0;
       background: var(--vscode-editor-background);
       border-left: 3px solid var(--vscode-terminal-ansiCyan);
   }
   ```

**Deliverable:** Command bar displays structured agent responses with tool call visibility

---

## Testing & Validation

### Manual Smoke Test Scenarios

**Test 1: Basic Chat**
1. Open command bar
2. Click "Chat with Wojak" (or similar trigger)
3. Send: "Hello, what files are in this run?"
4. **Expected:** 
   - Typing indicator appears
   - Tool call appears: "🔧 describe_run_contents"
   - Response streams in with markdown formatting
   - Done event hides typing indicator

**Test 2: File Read**
1. Send: "Show me config.toml"
2. **Expected:**
   - Tool call: "🔧 read_run_file"
   - File content appears with syntax highlighting (markdown code fence)

**Test 3: Markdown Edit**
1. Send: "List sections in AGENTS.md"
2. **Expected:**
   - Tool call: "🔧 list_report_sections"
   - Sections listed (Introduction, Methods, etc.)
3. Send: "Replace Introduction with: 'This is a test run.'"
4. **Expected:**
   - Tool call: "🔧 replace_report_section"
   - Confirmation message

**Test 4: Error Handling**
1. Send: "Read ../../etc/passwd"
2. **Expected:**
   - Error event with clear message: "Path validation failed: traversal attempt"
   - Distinct error styling (red border or icon)

**Test 5: JWT Validation**
1. Tamper with JWT in browser dev tools (if accessible)
2. Send any message
3. **Expected:**
   - Error: "JWT validation failed: signature mismatch"

### Security Validation Checklist
- [ ] Path traversal attempts rejected
- [ ] JWT signature validation enforced
- [ ] File size limits respected (1MB)
- [ ] Runid mismatch rejected
- [ ] No access to files outside run directory

---

## Known Issues & Workarounds

### Issue: JSON Lines Schema Unknown
**Impact:** Parser may not match Codex actual output format  
**Workaround:** 
1. Run `codex exec --json --prompt "Hello"` manually to observe format
2. Update parser to match actual schema
3. Document schema in `/workdir/wepppy/services/cao/README.md`

### Issue: Multi-line JSON Objects
**Impact:** Parser may split objects mid-JSON  
**Workaround:**
- Buffer incomplete lines
- Parse on complete `}` boundaries
- Test with multi-paragraph responses

### Issue: Wojak Profile Loading
**Impact:** `codex exec --profile wojak_interactive` may not auto-load  
**Workaround:**
- Verify profile installed: `cao install wojak_interactive`
- Alternative: Pass system prompt inline if profile loading fails
- Check CAO agent_store path: `/workdir/wepppy/services/cao/src/cli_agent_orchestrator/agent_store/wojak_interactive.md`

---

## Files to Modify

### Backend (Python)
1. `/workdir/wepppy/services/cao/bootstrap_wojak.py` (or similar bootstrap script)
   - Update command construction
   - Implement JSON Lines parser
   - Wire event handlers to Redis pub/sub

### Frontend (JavaScript)
2. `/workdir/wepppy/wepppy/weppcloud/controllers_js/command-bar.js`
   - Parse JSON events from StatusStream
   - Render tool calls with pretty-printing
   - Handle error events with distinct styling

### CSS
3. `/workdir/wepppy/wepppy/weppcloud/static/css/command-bar.css` (or similar)
   - Add `.agent-tool-call` styling
   - Add `.agent-error` styling

### Documentation
4. `/workdir/wepppy/docs/work-packages/20251028_wojak_lives/tracker.md`
   - Mark Phase 5 tasks complete
   - Document JSON Lines schema discovered
   - Add retrospective notes

---

## Success Criteria

### Phase 5 Complete When:
- [x] Wojak profile created (`wojak_interactive.md`)
- [ ] Bootstrap launches `codex exec --json` without TTY errors
- [ ] JSON Lines parser handles content, tool_call, error, done events
- [ ] Redis channels receive structured events
- [ ] Frontend displays responses with markdown rendering
- [ ] Tool calls pretty-printed (🔧 icon + function name)
- [ ] Error events styled distinctly
- [ ] All 5 smoke test scenarios pass
- [ ] Security validation checklist complete

---

## Handoff Notes for Codex

### Context You Have
- Session 1 delivered backend + frontend MVP (all Phase 1-4 tasks complete)
- Bootstrap script exists but uses `script -c "codex --full-auto"` (wrong approach)
- Frontend has StatusStream subscription working (Redis → browser pipeline functional)
- MCP modules are implemented and ready (JWT validation, file access, markdown editing)

### What You're Implementing
- Replace script wrapper with `codex exec --json`
- Parse JSON Lines events in bootstrap
- Stream structured events to Redis
- Update frontend to handle JSON format
- Add tool call pretty-printing

### What's Already Done (Don't Redo)
- JWT generation (`wepppy/weppcloud/utils/agent_auth.py`)
- MCP base module (`wepppy/mcp/base.py`)
- File MCP module (`wepppy/mcp/report_files.py`)
- Markdown MCP module (`wepppy/mcp/report_editor.py`)
- Flask agent route (`wepppy/weppcloud/routes/agent.py`)
- Command bar panel UI (HTML/CSS for message bubbles)
- StatusStream subscription (WebSocket bridge)

### Questions to Resolve During Implementation
1. What is the exact JSON Lines schema from `codex exec --json`?
   - Document in code comments
   - Update parser to match
2. How does CAO load the wojak_interactive profile?
   - Via `--profile` flag?
   - Via environment variable?
   - Inline system prompt if needed?
3. Should tool call args be displayed or just function name?
   - Start with function name only
   - Add args as optional enhancement

### Estimated Effort
- **1 hour:** Bootstrap command update + JSON Lines parser
- **1.5 hours:** Event handling + Redis streaming + buffer management
- **0.5 hours:** Frontend JSON parsing + tool call rendering
- **Total:** 3 hours (Phase 5 complete)

### After This Session
- Full end-to-end smoke test (all 5 scenarios)
- Security validation checklist
- Frontend polish (responsive layout, keyboard shortcuts, theme checks)
- Documentation updates (README, tracker retrospective)
- Work package status: **MVP Complete**

---

## Bootstrap Script Template (Starter Code)

```python
#!/usr/bin/env python3
"""
CAO Wojak Bootstrap Script
Spawns Codex in headless mode, bridges Redis pub/sub ↔ JSON Lines events
"""

import os
import sys
import json
import subprocess
import redis
from typing import Optional

def main():
    # Environment from CAO spawn
    jwt_token = os.environ.get("AGENT_JWT_TOKEN")
    runid = os.environ.get("RUNID")
    config = os.environ.get("CONFIG")
    session_id = os.environ.get("SESSION_ID")
    
    # Redis connection
    redis_client = redis.Redis(host="redis", port=6379, db=2, decode_responses=True)
    
    # User message from chat channel
    # TODO: Subscribe to agent_chat-{session_id} for user messages
    
    # Initial prompt construction
    user_message = "Hello, I need help with this WEPP run."  # TODO: Get from Redis
    prompt = f"""You are Wojak, a hydrology assistant for run {runid}.

User: {user_message}

You have access to MCP tools for file reading and markdown editing.
Use describe_run_contents() to discover files, read_run_file() to inspect them.
"""
    
    # Spawn Codex in headless mode
    cmd = [
        "codex", "exec", "--json",
        "--profile", "wojak_interactive",
        "--prompt", prompt
    ]
    
    env = os.environ.copy()
    env["AGENT_JWT_TOKEN"] = jwt_token
    
    process = subprocess.Popen(
        cmd,
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True
    )
    
    # JSON Lines parser
    buffer = ""
    for line in process.stdout:
        buffer += line
        
        # Attempt parse on complete JSON boundary
        if line.strip().endswith("}"):
            try:
                event = json.loads(buffer)
                handle_event(event, redis_client, session_id)
                buffer = ""
            except json.JSONDecodeError:
                continue  # Incomplete multi-line JSON
    
    # Cleanup
    process.wait()
    redis_client.publish(f"agent_response-{session_id}", json.dumps({"type": "done"}))

def handle_event(event: dict, redis_client, session_id: str):
    """Stream JSON event to Redis channel"""
    event_type = event.get("type")
    
    if event_type in ("content", "tool_call", "error", "done"):
        redis_client.publish(
            f"agent_response-{session_id}",
            json.dumps(event)
        )
    else:
        print(f"Unknown event type: {event_type}", file=sys.stderr)

if __name__ == "__main__":
    main()
```

---

**Next Steps:**
1. Review this prompt
2. Implement Phase 5.1 (bootstrap command update)
3. Implement Phase 5.2 (JSON Lines parsing)
4. Implement Phase 5.3 (frontend JSON rendering)
5. Run smoke tests
6. Update tracker with Session 2 retrospective
7. Declare MVP complete if all tests pass

**Estimated completion:** 2025-10-28 (same day if started now)
