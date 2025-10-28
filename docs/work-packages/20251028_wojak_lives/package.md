# Wojak Lives: Interactive Agent Integration
> Created 2025-10-28 to establish Wojak agent integration with WEPPcloud command bar
> **Status:** Approved — Implementation Ready
> **Owner:** Codex
> **Purpose:** Demonstrates production-ready architecture for secure, run-scoped interactive agent assistance in scientific modeling workflows. Establishes patterns for zero-trust agent integration, non-blocking pub/sub messaging, and JWT-based capability isolation that stakeholders can extend to broader user populations.

## Context

CAO (CLI Agent Orchestrator) provides multi-agent orchestration infrastructure. The Wojak tier represents public-facing interactive agents with zero-trust security posture. This work package establishes the minimal viable path to:

1. Spawn a Wojak agent session for the root WEPPcloud user (Roger)
2. Authenticate via JWT token scoped to user + run context
3. Integrate with command-bar.js for interactive chat interface
4. Provide file access MCP tools (read-only, run-scoped)
5. Provide markdown editing MCP tools (PyO3 bindings)

**Success criteria:** Roger can open command bar, chat with Wojak about a WEPP run, request file contents, and have Wojak edit markdown documents—all within browser UI with zero manual tmux attachment.

## Objectives

### Primary Goals
1. **CAO-WEPPcloud Integration:** Flask route spawns CAO Wojak session, injects JWT, bridges WebSocket for bi-directional communication
2. **JWT Authentication:** Run-scoped token generation/validation in MCP tool decorators
3. **Command Bar Integration:** Extend command-bar.js with agent chat panel, message threading, typing indicators
4. **File MCP Module:** `wepppy.mcp.report_files` with path validation and size limits
5. **Markdown MCP Module:** `wepppy.mcp.report_editor` using PyO3 bindings (markdown_extract_py, markdown_edit_py, markdown_doc_py)

### Secondary Goals (Post-MVP)
- Query-engine MCP integration for WEPP results queries
- Session state persistence (tracker.md) for multi-turn coherence

### Out of Scope
- Autonomous scheduled flows (Janny tier)
- Multi-agent coordination (handoff/assign patterns)
- Report PDF export (requires RQ integration)
- Public deployment (Wojak with untrusted users)
- Rate limiting and abuse detection
- Multi-user rollout
- Rollout beyond dev

## Stakeholders

- **Alpha Team (Roger):** Primary user, integration testing, UX feedback
- **Codex:** Lead Dev, Code review, Work Package Owner post-implementation (depending on scope assessment)
- **Claude/GitHub Copilot:** Planning, Documentation, Secondary Code Reviews

## Success Criteria

### Functional Requirements
- [ ] Flask route `POST /runs/<runid>/<config>/agent/chat` initializes session (non-blocking)
- [ ] Flask route `POST /runs/<runid>/<config>/agent/chat/<session_id>` sends messages to wojak through redis (non-blocking)
- [ ] Flask route `DELETE /runs/<runid>/<config>/agent/chat/<session_id>` terminates session
- [ ] RQ job spawns CAO session with JWT and Redis channels in environment
- [ ] CAO bootstrap script bridges Redis pub/sub ↔ agent stdin/stdout
- [ ] status2 forwards agent responses to browser via existing WebSocket connection
- [ ] Command bar UI displays agent responses with markdown rendering
- [ ] JWT validates user identity and run access scope per MCP tool call
- [ ] `describe_run_contents()` returns metadata summaries (not exhaustive file lists)
- [ ] `read_run_file()` works with path traversal prevention and size limits
- [ ] `list_report_sections()`, `read_report_section()`, `replace_report_section()` work via PyO3 bindings
- [ ] Session cleanup on: user disconnect, JWT expiry, inactivity timeout, CAO failure

### Non-Functional Requirements
- [ ] Agent response latency <2s for simple queries (file reads)
- [ ] PyO3 bindings provide <1ms per markdown operation (vs 5-10ms subprocess baseline)
- [ ] Security: Path validation prevents access outside run directory
- [ ] Security: JWT signature verification fails for tampered tokens
- [ ] UX: Command bar provides clear feedback (typing indicators, error states)

### Quality Gates
- [ ] Manual smoke test: Roger chats with Wojak, reads file, edits `<runid>/AGENTS.md`
- [ ] Security review: JWT implementation follows best practices
- [ ] Code review: Codex or GitHub Copilot validates Flask/JS integration
- [ ] Documentation: README updates for agent chat feature

## Scope & Constraints

### In Scope
- Single-user prototype (root WEPPcloud user only)
- Synchronous request/response chat (no streaming)
- Read-only file access + markdown editing of  `<runid>/AGENTS.md`
- Basic error handling (file not found, JWT validation failure)
- Command bar UI integration (new agent chat panel)

### Out of Scope
- Multi-user JWT management (OAuth, user database)
- Session persistence across page reloads
- Advanced markdown features (TOC generation, batch edits)
- Query-engine integration (WEPP results queries)
- Rate limiting / abuse detection
- Production deployment configuration

### Constraints
- Must use existing CAO infrastructure (`cao-server`, agent profiles)
- Must not modify core CAO orchestration logic
- PyO3 bindings already installed in CAO venv (markdown_extract_py, markdown_edit_py, markdown_doc_py)
- Command bar integration must not break existing keyboard shortcuts or search functionality
- JWT library choice: use Flask-JWT-Extended (already in wepppy dependencies)

## Technical Approach

### Architecture Overview

**Why Redis Pub/Sub instead of direct WebSocket:**
- Flask/gunicorn workers cannot hold persistent WebSocket connections (blocks worker)
- status2 already provides Redis → WebSocket bridging for WEPP progress updates
- Reusing status2 avoids duplicating WebSocket infrastructure
- Redis pub/sub enables async, non-blocking message flow

```
Browser (command-bar.js)
  ↓ [1] POST /agent/chat (initialize session, non-blocking)
  ↓ [2] Subscribe to status2 WebSocket (reuse existing connection)
  ↓ [3] POST /agent/chat/<session_id> (send messages, non-blocking)

Flask Routes (instant return, no worker blocking)
  ↓ [4] Generate JWT token (user + runid scoped)
  ↓ [5] Enqueue RQ job: spawn_wojak_session()
  ↓ [6] Publish user messages to Redis: agent:chat:<runid>:<session_id>

RQ Worker (background job, scales horizontally)
  ↓ [7] Call CAO API to spawn tmux session with JWT in environment
  ↓ [8] Bootstrap script injected into CAO session

CAO Wojak Agent (tmux session with Redis bridge)
  ↓ [9] Subscribe to Redis: agent:chat:<runid>:<session_id> (user messages)
  ↓ [10] Execute MCP tools with JWT validation
  ↓ [11] Publish responses to Redis: agent:response:<runid>:<session_id>
  │
  ├─→ wepppy.mcp.report_files
  │   ├─ describe_run_contents(runid, category=None)  # Metadata summaries
  │   └─ read_run_file(runid, path)                   # Read specific file
  └─→ wepppy.mcp.report_editor
      ├─ list_report_sections(runid, report_id)
      ├─ read_report_section(runid, report_id, pattern)
      └─ replace_report_section(runid, report_id, pattern, content)

status2 (Go service, already running)
  ↓ [12] Subscribe to Redis: agent:response:* pattern
  ↓ [13] Forward to WebSocket clients (by session_id)

Browser receives agent responses via existing status2 connection
```

**Flow explanation:**
1. **[1-3] Browser → Flask:** Non-blocking HTTP requests, no persistent connections
2. **[4-6] Flask → Redis → RQ:** Instant response, work offloaded to background job
3. **[7-8] RQ → CAO:** Spawn agent session with JWT injected into environment
4. **[9-11] CAO ↔ Redis:** Agent subscribes to incoming messages, publishes responses
5. **[12-13] status2 → Browser:** Existing WebSocket infrastructure forwards agent messages

**Key insight:** CAO agent's stdout/stderr is captured and published to Redis (all thinking, tool calls, responses visible to user). This provides full transparency into agent reasoning.

### Session Lifecycle & Cleanup

**Session termination triggers:**
1. **JWT expiration:** 24-hour token expiry (hard cutoff)
2. **User-initiated:** Browser sends DELETE request when closing chat panel
3. **Inactivity timeout:** Redis TTL on last message timestamp (e.g., 30 minutes)
4. **CAO failure:** RQ job failure or tmux session crash (status2 detects disconnect)

**Cleanup sequence:**
```python
# Redis keys with TTL
SET agent:session:<session_id>:last_activity <timestamp> EX 1800  # 30 min TTL
# On cleanup:
- Publish termination message to agent:chat:<runid>:<session_id>
- CAO bootstrap script receives termination, exits gracefully
- status2 notifies browser of session end
- Browser UI displays "Session ended" message
```

### Critical Path Components

#### 1. JWT Token Generation (Flask)
```python
# wepppy/weppcloud/utils/agent_auth.py
from flask_jwt_extended import create_access_token
import datetime

def generate_agent_token(user_id: str, runid: str, config: str) -> str:
    """Generate JWT for agent session scoped to user + run."""
    expires = datetime.timedelta(hours=24)
    token = create_access_token(
        identity=user_id,
        additional_claims={
            "runid": runid,
            "config": config,
            "tier": "wojak"
        },
        expires_delta=expires
    )
    return token
```

#### 2. MCP Tool Decorator (JWT Validation)
```python
# wepppy/mcp/base.py
from flask_jwt_extended import decode_token
from functools import wraps
import os

def mcp_tool(tier: str):
    """Decorator for MCP tools with JWT validation."""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Extract JWT from environment (CAO injects at session spawn)
            token = os.environ.get("AGENT_JWT_TOKEN")
            if not token:
                raise PermissionError("No agent token found")
            
            try:
                claims = decode_token(token)
                if claims.get("tier") != tier:
                    raise PermissionError(f"Tool requires {tier} tier")
                
                # Inject claims into kwargs for runid validation
                kwargs["_jwt_claims"] = claims
                return func(*args, **kwargs)
            except Exception as e:
                raise PermissionError(f"Token validation failed: {e}")
        
        return wrapper
    return decorator

def validate_runid(runid: str, claims: dict):
    """Ensure requested runid matches JWT scope."""
    if claims.get("runid") != runid:
        raise PermissionError(f"Access denied to run {runid}")
```

#### 3. Flask Routes (Non-Blocking)
```python
# wepppy/weppcloud/routes/agent.py
from flask import Blueprint, request, jsonify
from flask_login import login_required, current_user
from wepppy.weppcloud.utils.agent_auth import generate_agent_token
from wepppy.rq.agent_rq import spawn_wojak_session
from redis import Redis
import uuid
import json
import time

agent_bp = Blueprint('agent', __name__)
redis_client = Redis(host='localhost', port=6379, db=2)  # Status DB

@agent_bp.route('/runs/<runid>/<config>/agent/chat', methods=['POST'])
@login_required
def initialize_agent_chat(runid, config):
    """Initialize agent chat session (non-blocking, returns immediately)."""
    
    # Generate unique session ID
    session_id = str(uuid.uuid4())
    
    # Generate JWT scoped to user + run (24-hour expiry)
    token = generate_agent_token(
        user_id=current_user.get_id(),
        runid=runid,
        config=config
    )
    
    # Enqueue RQ job to spawn CAO session (non-blocking)
    # This returns instantly, actual spawning happens in background
    job = spawn_wojak_session.delay(
        runid=runid,
        config=config,
        session_id=session_id,
        jwt_token=token,
        user_id=current_user.get_id()
    )
    
    # Set session activity timestamp (30-minute TTL)
    redis_client.setex(
        f"agent:session:{session_id}:last_activity",
        1800,  # 30 minutes
        int(time.time())
    )
    
    return jsonify({
        "session_id": session_id,
        "job_id": job.id,
        "redis_channel": f"agent:response:{runid}:{session_id}",
        "status": "initializing"
    })

@agent_bp.route('/runs/<runid>/<config>/agent/chat/<session_id>', methods=['POST'])
@login_required
def send_agent_message(runid, config, session_id):
    """Send message to agent via Redis (non-blocking, returns immediately)."""
    
    message = request.json.get('message')
    if not message:
        return jsonify({"error": "No message provided"}), 400
    
    # Publish to Redis channel (CAO agent is subscribed)
    # This returns instantly, agent processes asynchronously
    redis_client.publish(
        f"agent:chat:{runid}:{session_id}",
        json.dumps({
            "type": "user_message",
            "content": message,
            "user_id": current_user.get_id(),
            "timestamp": time.time()
        })
    )
    
    # Update session activity timestamp
    redis_client.setex(
        f"agent:session:{session_id}:last_activity",
        1800,
        int(time.time())
    )
    
    return jsonify({"status": "sent"})

@agent_bp.route('/runs/<runid>/<config>/agent/chat/<session_id>', methods=['DELETE'])
@login_required
def terminate_agent_session(runid, config, session_id):
    """Terminate agent session (user-initiated)."""
    
    # Send termination message to agent
    redis_client.publish(
        f"agent:chat:{runid}:{session_id}",
        json.dumps({
            "type": "terminate",
            "user_id": current_user.get_id(),
            "timestamp": time.time()
        })
    )
    
    # Clean up session metadata
    redis_client.delete(f"agent:session:{session_id}:last_activity")
    
    return jsonify({"status": "terminated"})
```

#### 4. RQ Job (CAO Session Spawner)
```python
# wepppy/rq/agent_rq.py
from rq import job
from redis import Redis
import requests
import json
import time

redis_client = Redis(host='localhost', port=6379, db=2)

@job('default')
def spawn_wojak_session(runid: str, config: str, session_id: str, 
                        jwt_token: str, user_id: str):
    """
    Spawn CAO Wojak session and inject environment variables.
    This runs in RQ worker (background), not blocking Flask.
    """
    
    # Spawn CAO session with JWT and Redis channels in environment
    cao_response = requests.post(
        "http://localhost:9889/sessions",
        params={
            "provider": "codex",
            "agent_profile": "wojak_interactive",
            "session_name": f"wojak-{session_id}"
        },
        json={
            "env": {
                "AGENT_JWT_TOKEN": jwt_token,
                "RUNID": runid,
                "CONFIG": config,
                "SESSION_ID": session_id,
                "REDIS_CHAT_CHANNEL": f"agent:chat:{runid}:{session_id}",
                "REDIS_RESPONSE_CHANNEL": f"agent:response:{runid}:{session_id}"
            }
        }
    )
    
    if cao_response.status_code != 200:
        # Notify user of spawn failure via status2
        redis_client.publish(
            f"agent:response:{runid}:{session_id}",
            json.dumps({
                "type": "error",
                "content": f"Failed to spawn agent session: {cao_response.text}"
            })
        )
        raise Exception("CAO session spawn failed")
    
    # Notify frontend that agent is ready
    redis_client.publish(
        f"agent:response:{runid}:{session_id}",
        json.dumps({
            "type": "system",
            "content": "Agent session initialized. You can start chatting."
        })
    )
    
    return cao_response.json()
```

> **Implementation note:** The current CAO API only reads query parameters. We recommend adding optional JSON support (e.g., `{"env": {...}}`) so JWTs and channel metadata can be handed off explicitly. Until that lands, a temporary workaround (stashing the token in Redis for the bootstrap script) remains possible but carries more moving parts.

#### 5. CAO Bootstrap Script (Redis Bridge)
```python
# services/cao/src/cli_agent_orchestrator/agent_store/wojak_bootstrap.py
"""
Bootstrap script injected into Wojak sessions to handle Redis pub/sub.
This runs in the CAO tmux session, bridging Redis ↔ agent stdin/stdout.

Key responsibilities:
- Subscribe to agent:chat:<runid>:<session_id> for user messages
- Forward user messages to agent stdin (LLM sees them as input)
- Capture agent stdout/stderr and publish to agent:response:<runid>:<session_id>
- Handle termination messages gracefully
"""
import os
import redis
import json
import sys
import select
from threading import Thread
import time

# Redis connection
r = redis.Redis(host='localhost', port=6379, db=2, decode_responses=True)
session_id = os.environ['SESSION_ID']
runid = os.environ['RUNID']
chat_channel = os.environ['REDIS_CHAT_CHANNEL']
response_channel = os.environ['REDIS_RESPONSE_CHANNEL']

def redis_listener():
    """
    Listen for incoming messages from Flask via Redis.
    Forwards user messages to agent stdin.
    """
    pubsub = r.pubsub()
    pubsub.subscribe(chat_channel)
    
    for message in pubsub.listen():
        if message['type'] == 'message':
            try:
                data = json.loads(message['data'])
                
                if data['type'] == 'user_message':
                    # Forward to agent stdin (LLM will see this as user input)
                    print(f"\n[USER]: {data['content']}\n", file=sys.stdout)
                    sys.stdout.flush()
                    
                elif data['type'] == 'terminate':
                    # Graceful shutdown
                    print("\n[SYSTEM]: Session terminated by user.\n", file=sys.stdout)
                    os._exit(0)
                    
            except Exception as e:
                print(f"[ERROR]: Failed to process message: {e}", file=sys.stderr)

def stdout_publisher():
    """
    Capture agent stdout/stderr and publish to Redis.
    This makes all agent thinking/reasoning visible to user.
    """
    while True:
        # Check if there's data available on stdout (non-blocking)
        if select.select([sys.stdin], [], [], 0.1)[0]:
            line = sys.stdin.readline()
            if line:
                # Publish to Redis (status2 will forward to browser)
                r.publish(response_channel, json.dumps({
                    "type": "agent_output",
                    "content": line.strip(),
                    "timestamp": time.time()
                }))

# Start background threads
listener_thread = Thread(target=redis_listener, daemon=True)
listener_thread.start()

publisher_thread = Thread(target=stdout_publisher, daemon=True)
publisher_thread.start()

# Keep process alive
while True:
    time.sleep(1)
    
    # Check session activity TTL (fail-safe)
    last_activity = r.get(f"agent:session:{session_id}:last_activity")
    if not last_activity:
        print("[SYSTEM]: Session expired (inactivity timeout).", file=sys.stderr)
        os._exit(1)
```

#### 6. Command Bar Integration (JavaScript)
```javascript
// wepppy/weppcloud/static-src/command-bar/agent-chat.js

class AgentChat {
    constructor(commandBar) {
        this.commandBar = commandBar;
        this.sessionData = null;
        this.messages = [];
        this.runid = null;
        this.config = null;
    }
    
    async initialize(runid, config) {
        this.runid = runid;
        this.config = config;
        
        // Initialize session (non-blocking, returns immediately)
        const response = await fetch(`/runs/${runid}/${config}/agent/chat`, {
            method: 'POST',
            headers: {'Content-Type': 'application/json'}
        });
        
        if (!response.ok) {
            throw new Error('Failed to initialize agent session');
        }
        
        this.sessionData = await response.json();
        
        // Subscribe to agent responses via existing status2 connection
        // status2 already handles WebSocket → Redis bridging for progress updates
        // We're just reusing that infrastructure for agent messages
        window.StatusStream.subscribe(
            this.sessionData.redis_channel,
            (data) => this.handleAgentMessage(data)
        );
        
        // Show initializing message
        this.messages.push({
            role: 'system',
            content: 'Initializing agent session...',
            timestamp: Date.now()
        });
        this.renderMessages();
    }
    
    async sendMessage(text) {
        if (!this.sessionData) {
            throw new Error('Agent session not initialized');
        }
        
        // Add user message to UI immediately
        this.messages.push({
            role: 'user',
            content: text,
            timestamp: Date.now()
        });
        this.renderMessages();
        this.showTypingIndicator();
        
        // Send message via non-blocking POST (Flask publishes to Redis)
        await fetch(
            `/runs/${this.runid}/${this.config}/agent/chat/${this.sessionData.session_id}`,
            {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({message: text})
            }
        );
    }
    
    handleAgentMessage(data) {
        const msg = JSON.parse(data);
        
        if (msg.type === 'agent_output') {
            // Agent stdout/stderr (thinking, tool calls, responses)
            this.hideTypingIndicator();
            this.messages.push({
                role: 'agent',
                content: msg.content,
                timestamp: msg.timestamp * 1000
            });
            this.renderMessages();
            
        } else if (msg.type === 'system') {
            // System messages (session ready, errors)
            this.messages.push({
                role: 'system',
                content: msg.content,
                timestamp: Date.now()
            });
            this.renderMessages();
            
        } else if (msg.type === 'error') {
            // Error messages
            this.hideTypingIndicator();
            this.messages.push({
                role: 'error',
                content: msg.content,
                timestamp: Date.now()
            });
            this.renderMessages();
        }
    }
    
    renderMessages() {
        const container = this.commandBar.getAgentChatContainer();
        container.innerHTML = this.messages.map(msg => `
            <div class="agent-message agent-message--${msg.role}">
                <div class="agent-message__content">${this.renderMarkdown(msg.content)}</div>
                <div class="agent-message__timestamp">${this.formatTime(msg.timestamp)}</div>
            </div>
        `).join('');
        container.scrollTop = container.scrollHeight;
    }
    
    async cleanup() {
        if (!this.sessionData) return;
        
        // Unsubscribe from status2 channel
        window.StatusStream.unsubscribe(this.sessionData.redis_channel);
        
        // Terminate agent session (sends termination message via Redis)
        await fetch(
            `/runs/${this.runid}/${this.config}/agent/chat/${this.sessionData.session_id}`,
            {method: 'DELETE'}
        );
        
        this.sessionData = null;
        this.messages = [];
    }
}
```

#### 7. status2 Extension (Optional - may already work)
```go
// services/status2/internal/handlers/agent.go
// status2 may already forward agent:response:* patterns via existing pub/sub logic
// If not, add this minimal extension:

func (h *Handler) subscribeAgentChannels(ctx context.Context) {
    // Subscribe to agent response pattern
    pubsub := h.redis.PSubscribe(ctx, "agent:response:*")
    defer pubsub.Close()
    
    for {
        msg, err := pubsub.ReceiveMessage(ctx)
        if err != nil {
            return
        }
        
        // Forward to WebSocket clients (status2 already does this for other channels)
        h.broadcast(msg.Channel, []byte(msg.Payload))
    }
}
```

**Note:** Verify if status2 already forwards arbitrary Redis channels to WebSocket clients. If it does, no code changes needed.

#### 8. MCP Modules (File + Markdown)
```python
# wepppy/mcp/report_files.py
from wepppy.mcp.base import mcp_tool, validate_runid
from pathlib import Path
from typing import Optional

@mcp_tool(tier="wojak")
def describe_run_contents(runid: str, category: Optional[str] = None, _jwt_claims=None) -> dict:
    """
    Describe run contents with metadata summaries instead of exhaustive file lists.
    
    Returns structured metadata about run directories:
    - climate: {hillslope_count, has_monthlies, sample_topaz_ids}
    - wepp: {hillslope_count, channel_count, has_daily_output, sample_files}
    - reports: {count, ids, status}
    - watershed: {delineation_method, subcatchment_count}
    - landuse: {db_name, has_burns, dominant_types}
    - soils: {db_name, dominant_mukeys}
    
    Args:
        runid: Run identifier
        category: Optional filter ("climate", "wepp", "reports", "watershed", "landuse", "soils")
    """
    validate_runid(runid, _jwt_claims)
    
    run_dir = Path(f"/geodata/weppcloud_runs/{runid}")
    if not run_dir.exists():
        raise ValueError(f"Run {runid} not found")
    
    metadata = {}
    
    # Climate metadata
    if not category or category == "climate":
        climate_dir = run_dir / "climate"
        if climate_dir.exists():
            cli_files = list(climate_dir.glob("*.cli"))
            metadata["climate"] = {
                "type": "hillslope_climates",
                "count": len(cli_files),
                "pattern": "<topaz_id>.cli",
                "sample_files": [f.name for f in cli_files[:5]],
                "has_monthlies": (climate_dir / "observed" / "monthly.txt").exists()
            }
    
    # WEPP outputs metadata
    if not category or category == "wepp":
        wepp_dir = run_dir / "wepp" / "output"
        if wepp_dir.exists():
            hill_files = list(wepp_dir.glob("H*.hill.txt"))
            channel_files = list(wepp_dir.glob("C*.channel.txt"))
            metadata["wepp"] = {
                "hillslope_count": len(hill_files),
                "channel_count": len(channel_files),
                "has_daily_output": bool(list(wepp_dir.glob("*.daily.txt"))),
                "sample_files": [f.name for f in (hill_files + channel_files)[:5]]
            }
    
    # Reports metadata
    if not category or category == "reports":
        reports_dir = run_dir / "reports"
        if reports_dir.exists():
            report_files = list(reports_dir.glob("*.md"))
            metadata["reports"] = {
                "count": len(report_files),
                "ids": [f.stem for f in report_files],
                "status": "draft" if report_files else "none"
            }
    
    # Watershed metadata
    if not category or category == "watershed":
        watershed_dir = run_dir / "watershed"
        if watershed_dir.exists():
            metadata["watershed"] = {
                "delineation_method": "peridot" if (watershed_dir / "peridot_slopes.parquet").exists() else "topaz",
                "subcatchment_count": len(list(watershed_dir.glob("subcatchments*.json")))
            }
    
    # Landuse metadata
    if not category or category == "landuse":
        landuse_dir = run_dir / "landuse"
        if landuse_dir.exists():
            metadata["landuse"] = {
                "db_name": "placeholder",  # Would read from NoDb
                "has_burns": (landuse_dir / "fire_date.txt").exists()
            }
    
    # Soils metadata
    if not category or category == "soils":
        soils_dir = run_dir / "soils"
        if soils_dir.exists():
            metadata["soils"] = {
                "db_name": "placeholder",  # Would read from NoDb
            }
    
    return metadata

@mcp_tool(tier="wojak")
def read_run_file(runid: str, path: str, _jwt_claims=None) -> str:
    """Read file content from run directory (max 1MB)."""
    validate_runid(runid, _jwt_claims)
    
    run_dir = Path(f"/geodata/weppcloud_runs/{runid}")
    file_path = (run_dir / path).resolve()
    
    # Security: prevent path traversal
    if run_dir not in file_path.parents:
        raise ValueError("Path traversal attempt detected")
    
    if not file_path.exists():
        raise FileNotFoundError(f"File not found: {path}")
    
    if file_path.stat().st_size > 1_000_000:
        raise ValueError("File too large (max 1MB)")
    
    return file_path.read_text()
```

```python
# wepppy/mcp/report_editor.py
from wepppy.mcp.base import mcp_tool, validate_runid
from pathlib import Path
import markdown_extract_py as mde
import markdown_edit_py as edit

@mcp_tool(tier="wojak")
def list_report_sections(runid: str, report_id: str, _jwt_claims=None) -> list[dict]:
    """List all sections with metadata."""
    validate_runid(runid, _jwt_claims)
    
    draft_path = Path(f"/geodata/weppcloud_runs/{runid}/reports/{report_id}.md")
    if not draft_path.exists():
        raise FileNotFoundError(f"Report {report_id} not found")
    
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
def read_report_section(runid: str, report_id: str, heading_pattern: str, _jwt_claims=None) -> str:
    """Extract section content by heading pattern."""
    validate_runid(runid, _jwt_claims)
    
    draft_path = Path(f"/geodata/weppcloud_runs/{runid}/reports/{report_id}.md")
    
    try:
        sections = mde.extract_from_file(heading_pattern, str(draft_path))
        if not sections:
            raise ValueError(f"Section '{heading_pattern}' not found")
        return sections[0]
    except mde.MarkdownExtractError as e:
        raise ValueError(f"Extract failed: {e}")

@mcp_tool(tier="wojak")
def replace_report_section(runid: str, report_id: str, heading_pattern: str,
                          new_content: str, keep_heading: bool = True, _jwt_claims=None) -> dict:
    """Replace section content with backup."""
    validate_runid(runid, _jwt_claims)
    
    draft_path = Path(f"/geodata/weppcloud_runs/{runid}/reports/{report_id}.md")
    
    try:
        result = edit.replace(
            str(draft_path),
            heading_pattern,
            new_content,
            keep_heading=keep_heading,
            backup=True
        )
        return {
            "success": result.applied,
            "messages": result.messages
        }
    except edit.MarkdownEditError as e:
        raise ValueError(f"Edit failed: {e}")
```

### Integration Checklist

**Backend (Flask + RQ):**
- [ ] Install Flask-JWT-Extended if not already present
- [ ] Create `wepppy/mcp/` package with `__init__.py`, `base.py`, `report_files.py`, `report_editor.py`
- [ ] Create `wepppy/weppcloud/utils/agent_auth.py` for JWT generation
- [ ] Create `wepppy/weppcloud/routes/agent.py` blueprint (3 routes: initialize, send, terminate)
- [ ] Create `wepppy/rq/agent_rq.py` with `spawn_wojak_session` job
- [ ] Register agent blueprint in `wepppy/weppcloud/app.py`

**CAO Integration:**
- [ ] Create `services/cao/src/cli_agent_orchestrator/agent_store/wojak_bootstrap.py` (Redis bridge)
- [ ] Create CAO agent profile: `services/cao/src/cli_agent_orchestrator/agent_store/wojak_interactive.md`
- [ ] Verify CAO session spawn API accepts `env` parameter (should already work)

**status2 Integration:**
- [ ] Verify status2 forwards `agent:response:*` channels to WebSocket clients
- [ ] Add agent channel pattern subscription if not already covered

**Frontend (JavaScript + CSS):**
- [ ] Extend command-bar.js with agent chat UI components
- [ ] Add CSS styles for agent chat panel (message bubbles, typing indicator)
- [ ] Integrate with existing StatusStream for message reception

**Testing:**
- [ ] Manual smoke test with Roger as root user
- [ ] Verify JWT validation rejects tampered tokens
- [ ] Test session cleanup on browser close
- [ ] Test inactivity timeout (30-minute TTL)

## Risks & Mitigations

| Risk | Impact | Likelihood | Mitigation |
|------|--------|------------|------------|
| status2 doesn't forward agent:* channels | High | Low | Verify behavior, add minimal Go code if needed |
| JWT token leakage (browser storage) | High | Low | Token never sent to browser, stays in CAO environment |
| Redis pub/sub message loss | Medium | Low | Redis pub/sub is fire-and-forget; acceptable for chat (user can resend) |
| Path traversal vulnerabilities | High | Low | Comprehensive path validation tests |
| PyO3 bindings not installed in CAO venv | Medium | Low | Verify `maturin develop` ran successfully |
| CAO bootstrap script complexity | Medium | Medium | Start simple (stdin/stdout bridge), iterate |
| Command bar UI breaks existing shortcuts | Medium | Medium | Namespace agent chat keybindings separately |
| Agent response latency >5s | Low | Medium | Set user expectations, show typing indicator |
| Orphaned CAO sessions (cleanup failure) | Low | Medium | Multiple cleanup triggers (JWT, TTL, user, CAO failure) |

## Dependencies

### Infrastructure
- CAO server running on localhost:9889
- Redis running on localhost:6379 (DB 2 for status/pub-sub)
- status2 service running (already exists for WEPP progress updates)
- RQ workers running (already exists for WEPP build jobs)
- PyO3 bindings installed in CAO venv (`markdown_extract_py`, `markdown_edit_py`, `markdown_doc_py`)
- Flask-JWT-Extended library

### Code
- `wepppy.mcp.*` modules (new: base, report_files, report_editor)
- `wepppy.weppcloud.routes.agent` blueprint (new: 3 routes)
- `wepppy.weppcloud.utils.agent_auth` module (new: JWT generation)
- `wepppy.rq.agent_rq` module (new: spawn_wojak_session job)
- `services/cao/.../wojak_bootstrap.py` (new: Redis bridge)
- `services/cao/.../wojak_interactive.md` (new: agent profile)
- Command bar JavaScript refactor (extend existing AgentChat class)
- status2 agent channel subscription (verify/add if needed)

### Testing
- Manual smoke test environment (Roger's dev machine)
- Sample run with markdown reports
- Test files for path traversal validation

## Timeline Estimate

**Effort:** 2-3 days (14-20 hours) for MVP (reduced from 16-24h due to reusing status2/RQ infrastructure)

### Day 1: Backend Foundation (8 hours)
- JWT token generation/validation (1.5h)
- MCP modules with PyO3 bindings (3h)
- Flask routes (3 endpoints) + RQ job (2h)
- CAO bootstrap script (Redis bridge) (1.5h)

### Day 2: Frontend Integration (6 hours)
- Command bar UI components (3h)
- StatusStream integration (reuse existing) (1h)
- CSS styling and polish (1h)
- status2 verification/extension (1h)

### Day 3: Testing & Refinement (8 hours)
- Manual smoke testing (2h)
- Bug fixes and edge cases (4h)
- Security review (JWT, path validation) (2h)

**Codex Review Decision Point:** If backend + frontend integration exceeds 12 hours, pause for Codex review before proceeding to polish phase.

## References

- [CAO README.md](../../services/cao/README.md) — CAO architecture and API reference
- [CAO Potential Applications](../../services/cao/cao-potential-applications.md) — Wojak tier design and MCP architecture
- [PyO3 Bindings API Reference](/workdir/markdown-extract/docs/work-packages/20251028_pyo3_bindings/PYTHON_API_REFERENCE.md) — markdown_extract_py, markdown_edit_py, markdown_doc_py
- [Command Bar Source](../../wepppy/weppcloud/static-src/command-bar/) — Existing command bar implementation
- [Flask-JWT-Extended Docs](https://flask-jwt-extended.readthedocs.io/) — JWT library documentation

## Notes

- **Architecture decision:** Redis pub/sub instead of direct WebSocket to avoid blocking gunicorn workers. Flask routes return instantly, offloading work to RQ jobs and Redis channels.
- **Reusing existing infrastructure:** status2 already provides Redis → WebSocket bridging for WEPP progress updates. We're just adding agent-specific channels to the same pattern.
- **Agent transparency:** CAO agent's stdout/stderr is captured and streamed to browser, so user sees all thinking, tool calls, and responses in real-time (not just final answers).
- **JWT isolation:** Token never sent to browser, stays in CAO session environment. MCP tools validate from `os.environ['AGENT_JWT_TOKEN']`.
- **Session cleanup:** Multiple triggers (JWT expiry, user disconnect, inactivity timeout, CAO failure) ensure no orphaned sessions.
- **File discovery approach:** `describe_run_contents()` returns metadata abstractions rather than exhaustive file lists to handle directories with 40k+ files (climate data, WEPP outputs). Tar archive integration deferred to future work package.
- **Redis as MCP transport:** User → Flask → Redis → CAO effectively makes Redis pub/sub another MCP communication channel (alongside file access and markdown editing).
- Initial prototype focuses on single-user (root) access; multi-user JWT management deferred
- Query-engine MCP integration deferred to post-MVP (requires DuckDB query templates)
- Session persistence across page reloads not required for MVP
- Rate limiting and abuse detection not required for single trusted user

---

**Created:** 2025-10-28  
**Approved:** 2025-10-28  
**Owner:** Codex  
**Status:** Approved — Ready for implementation
