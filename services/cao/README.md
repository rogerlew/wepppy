# CLI Agent Orchestrator (CAO)

> Lightweight orchestration system for managing multi-agent AI workflows in isolated tmux terminals with intelligent task delegation and hierarchical coordination.

> **See also:** [AGENTS.md](AGENTS.md) for development workflow guidance and [CODEBASE.md](CODEBASE.md) for detailed architecture

---

## Overview

CLI Agent Orchestrator (CAO, pronounced "kay-oh") enables complex problem-solving through hierarchical coordination of specialized AI agents. Each agent operates in an isolated tmux session, maintaining context separation while enabling seamless communication through Model Context Protocol (MCP) servers and a centralized HTTP API.

**Why CAO exists:**
- **Complexity isolation**: Break down large tasks into specialized agent domains without context pollution
- **Parallel execution**: Run independent work streams concurrently while maintaining coordination
- **Scheduled automation**: Execute routine maintenance and monitoring workflows unattended
- **Direct steering**: Interact with worker agents in real-time for course correction and guidance

**Primary users:**
- DevOps teams managing complex infrastructure automation
- Development teams coordinating multi-step code review/generation workflows
- System administrators scheduling routine maintenance tasks
- AI researchers experimenting with multi-agent collaboration patterns

**Key capabilities:**
- Hierarchical supervisor/worker agent patterns
- Three orchestration modes: handoff (synchronous), assign (asynchronous), send_message (communication)
- Cron-based flow scheduling with conditional execution
- Direct tmux session access for monitoring and intervention
- Codex CLI integration for rich local tooling

**Attribution:**
This service is derived from [awslabs/cli-agent-orchestrator](https://github.com/awslabs/cli-agent-orchestrator) under the Apache-2.0 License. The original work has been adapted to integrate with wepppy infrastructure, replacing Amazon Q CLI with Codex CLI as the primary provider. See [LICENSE](LICENSE) for full Apache-2.0 terms and [NOTICE](NOTICE) for attribution details.

---

## Architecture

CAO follows a layered architecture where CLI commands and MCP tools interact with a FastAPI HTTP server that orchestrates tmux sessions through service and client layers:

```
┌─────────────────────────────────────────────────────────────────────┐
│                         Entry Points                                 │
├─────────────────────────┬───────────────────────────────────────────┤
│       CLI Commands      │         MCP Server                        │
│    (cao launch, ...)    │    (handoff, assign, send_message)        │
└──────────────┬──────────┴──────────────┬────────────────────────────┘
               │                         │
               └─────────────┬───────────┘
                             │
                      ┌──────▼──────┐
                      │  FastAPI    │
                      │  HTTP API   │
                      │ (port 9889) │
                      └──────┬──────┘
                             │
                      ┌──────▼──────┐
                      │  Services   │
                      │    Layer    │
                      ├─────────────┤
                      │ • session   │
                      │ • terminal  │
                      │ • inbox     │
                      │ • flow      │
                      └──────┬──────┘
                             │
                ┌────────────┴────────────┐
                │                         │
           ┌────▼────┐               ┌────▼─────┐
           │ Clients │               │Providers │
           ├─────────┤               ├──────────┤
           │ • tmux  │               │ • codex  │
           │ • db    │               └──────────┘
           └────┬────┘                      │
                │                           │
         ┌──────┴──────┐             ┌──────▼──────┐
         │             │             │             │
    ┌────▼────┐  ┌─────▼─────┐ ┌────▼────┐   ┌────▼─────┐
    │  Tmux   │  │  SQLite   │ │ Codex   │   │ Future   │
    │Sessions │  │ Database  │ │   CLI   │   │Providers │
    └─────────┘  └───────────┘ └─────────┘   └──────────┘
```

### Core Components

**Entry Points:**
- `cao` CLI commands (`launch`, `shutdown`, `flow add`, etc.) — User-facing interface
- MCP server tools (`handoff`, `assign`, `send_message`) — Agent-to-agent coordination

**HTTP API Layer (`api/main.py`):**
- FastAPI application on `http://localhost:9889`
- REST endpoints for session/terminal/inbox management
- Lifespan hooks manage background daemons (flow scheduler, inbox watcher)
- Health check at `/health`

**Service Layer:**
- `session_service.py` — List, get, delete tmux sessions
- `terminal_service.py` — Create, control, and query agent terminals
- `inbox_service.py` — Terminal-to-terminal messaging with file-watching for delivery
- `flow_service.py` — Parse, schedule, and execute automated flows

**Client Layer:**
- `tmux.py` — Wrapper around libtmux for session/window/pane operations; sets `CAO_TERMINAL_ID` environment variable
- `database.py` — SQLite persistence for terminals, inbox messages, and flows

**Provider Layer:**
- `base.py` — Abstract interface for CLI tool integration
- `codex.py` — Codex CLI provider with regex-based status detection
- `gemini.py` — Gemini CLI provider with system-prompt injection and status heuristics
- `manager.py` — Maps terminal IDs to provider instances

### Data Storage

All state lives under `~/.wepppy/cao/`:
```
~/.wepppy/cao/
├── db/
│   └── cli-agent-orchestrator.db    # SQLite: terminals, inbox_messages, flows tables
├── logs/
│   ├── terminal/
│   │   └── <terminal-id>.log        # tmux pipe-pane output (watched by inbox service)
│   └── cao.log                      # Application log
└── agent-context/                   # Agent profile working directory
```

Agent profiles are mirrored to `~/.codex/prompts/` so Codex CLI can discover them. When a Gemini
terminal launches, its system prompt is written to `~/.wepppy/cao/agent-context/<terminal-id>/system.md`
and exposed to Gemini CLI via `GEMINI_SYSTEM_MD`.

### Terminal Identity and Status

Each agent terminal receives a unique `CAO_TERMINAL_ID` environment variable at creation. The server tracks terminal status:
- `IDLE` — Ready to receive messages (detected by provider-specific prompt patterns)
- `PROCESSING` — Actively working
- `WAITING_USER_ANSWER` — Blocked on user input (e.g., approval prompts)
- `COMPLETED` — Task finished (handoff mode)
- `ERROR` — Terminal encountered an error

The inbox service watches terminal log files using `watchdog.observers.polling.PollingObserver`. When a terminal transitions to IDLE, pending inbox messages are automatically delivered.

---

## Installation

### Prerequisites

**1. Install tmux (version 3.3 or higher required):**

```bash
bash <(curl -s https://raw.githubusercontent.com/awslabs/cli-agent-orchestrator/refs/heads/main/tmux-install.sh)
```

**2. Install uv:**

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

**3. Install and authenticate Codex CLI:**

```bash
# Install Codex (follow instructions at https://docs.codex.ai/)
# Then authenticate
codex login
```

Verify authentication:
```bash
codex --version
```

### Install CAO

#### Option 1: System-wide Install (Recommended for Production)

From the wepppy repository root:

```bash
# Editable install (for development)
uv pip install -e services/cao

# Verify installation
cao --version
cao-server --help
```

This registers the `cao` and `cao-server` entry points and installs dependencies (FastAPI, libtmux, watchdog, etc.).

#### Option 2: Virtual Environment Install (Recommended for Development)

For isolated development with full control over dependencies:

```bash
# Navigate to CAO directory
cd /workdir/wepppy/services/cao

# Create virtual environment with uv
uv venv .venv

# Activate virtual environment
source .venv/bin/activate

# Install CAO, dependencies, and Rust bindings in one step
bash services/cao/scripts/setup_venv.sh

# Verify installation
cao --version
cao-server --help
```

**What `uv sync` installs:**
- Core dependencies: FastAPI (0.117.1), libtmux (0.46.2), uvicorn (0.37.0)
- MCP integration: fastmcp (2.12.4), mcp (1.15.0)
- Scheduling: APScheduler (3.11.0)
- File watching: watchdog (6.0.0), aiofiles (24.1.0)
- Testing: pytest (8.4.2), pytest-asyncio, pytest-cov, pytest-mock, pytest-xdist
- Code quality: black (25.9.0), isort (6.0.1), mypy (1.18.2)
- CLI framework: cyclopts (3.24.0), rich (14.1.0)
- 93 total packages (see `pyproject.toml` for complete dependency tree)

**What `maturin develop` does:**
- Compiles Rust-based `markdown-extract` Python bindings (`markdown_extract_py`) in release mode
- Installs as editable package in the virtual environment
- Provides `markdown_extract` module for programmatic Markdown manipulation (heading extraction, section editing)
- Used by advanced agent workflows that need to parse/modify documentation files

---

### Single-Worker Requirement

Run the API with a single worker. Multiple workers will duplicate background daemons (flow scheduler) and file watchers (inbox observer), and each process maintains its own in-memory provider registry and tmux state handles. This can cause duplicate flow execution and inconsistent terminal state. The provided systemd unit enforces `--workers 1`.

**Virtual environment benefits:**
- Dependency isolation from system Python
- Reproducible builds via `uv.lock`
- Easy cleanup (`rm -rf .venv`)
- Compatible with IDE tooling (VS Code, PyCharm)

**Deactivating:**
```bash
deactivate
```

---

## Quick Start

### 1. Start the CAO Server

The `cao-server` must be running for all orchestration operations:

```bash
cao-server
```

**What happens:**
- FastAPI application starts on `http://localhost:9889`
- SQLite database initialized at `~/.wepppy/cao/db/cli-agent-orchestrator.db`
- Flow daemon starts checking for scheduled executions every 60 seconds
- Inbox watcher (PollingObserver) starts monitoring `~/.wepppy/cao/logs/terminal/` for IDLE patterns
- Health check available at `http://localhost:9889/health`

Leave this running in a dedicated terminal or tmux session. Logs appear in both stdout and `~/.wepppy/cao/logs/cao.log`.

### 2. Install Agent Profiles

Agent profiles define the system prompt and behavior for specialized agents. CAO includes three built-in profiles:

```bash
# Install supervisor agent (coordinates multi-agent workflows)
cao install code_supervisor

# Install worker agents
cao install developer
cao install reviewer
```

**What `cao install` does:**
1. Copies the agent profile markdown from `services/cao/src/cli_agent_orchestrator/agent_store/` to `~/.wepppy/cao/agent-store/`
2. Mirrors the profile to `~/.codex/prompts/` so Codex CLI can discover it
3. Registers the profile name for use in `cao launch` and flow definitions

**Installing custom agents:**

```bash
# From local file
cao install ./my-custom-agent.md
cao install /absolute/path/to/agent.md

# From URL
cao install https://example.com/agents/custom-agent.md
```

See [docs/agent-profile.md](docs/agent-profile.md) for profile authoring guidance.

### 3. Launch an Agent Session

```bash
# Launch and attach (interactive)
cao launch --agents code_supervisor

# Launch in background (headless)
cao launch --agents developer --headless
```

**What `cao launch` does:**
1. Sends `POST /sessions` to the CAO server with the requested `provider` (default `codex`) and `agent_profile`
2. Server creates a new tmux session (name format: `cao-<random>`)
3. Server creates a terminal within the session and assigns a unique `CAO_TERMINAL_ID`
4. Provider initializes:
   - **Codex:** waits for shell, loads Wojak prompts, runs `codex` for interactive mode
   - **Gemini:** waits for shell, writes `system.md`, exports `GEMINI_SYSTEM_MD`, launches `gemini`
5. Inbox service registers the terminal for message delivery
6. If not headless, attaches your terminal to the tmux session

**Interacting with the agent:**
- Type naturally in the Codex TUI
- Agent has access to MCP tools for orchestration (handoff, assign, send_message)
- Detach with `Ctrl+b, d` (standard tmux detach)

### 4. Working with Tmux Sessions

All agent sessions run in tmux for persistence and isolation:

```bash
# List all sessions
tmux list-sessions

# Attach to a session (if detached)
tmux attach -t cao-<session-id>

# Switch between windows (inside tmux)
Ctrl+b, n          # Next window
Ctrl+b, p          # Previous window
Ctrl+b, w          # List all windows (interactive selector)
Ctrl+b, <number>   # Go to window number (0-9)

# Detach (inside tmux)
Ctrl+b, d

# Kill a session
cao shutdown --session cao-<session-id>

# Kill all CAO sessions
cao shutdown --all
```

**Tip:** Keep `cao-server` in its own tmux session so it persists across terminal disconnects.

---

## Command Reference

### cao-server

Starts the FastAPI HTTP server and background daemons.

```bash
cao-server
```

**Responsibilities:**
- Exposes REST API on `http://localhost:9889` (default, configurable via `SERVER_PORT` in `constants.py`)
- Runs flow daemon (checks for scheduled flows every 60 seconds)
- Runs inbox watcher (monitors terminal logs for IDLE patterns using PollingObserver)
- Manages lifespan events (initialization, cleanup, graceful shutdown)

**Environment variables:**
- None currently required; configuration lives in `src/cli_agent_orchestrator/constants.py`

**Logging:**
- Console output (INFO level by default)
- File output: `~/.wepppy/cao/logs/cao.log`

### cao launch

Creates a new agent session with the specified profile.

```bash
cao launch --agents <profile-name> [--session-name <name>] [--headless] [--provider {codex|gemini}]
```

**Arguments:**
- `--agents` (required): Agent profile name (must be previously installed via `cao install`)
- `--session-name` (optional): Custom tmux session name (default: auto-generated `cao-<uuid>`)
- `--headless` (flag): Launch in background without attaching to tmux session
- `--provider` (optional): Provider to use (default: `codex`; options: `codex`, `gemini`)

**Example:**
```bash
# Interactive session
cao launch --agents code_supervisor

# Gemini CLI session (e.g., for PDF to Markdown workflows)
cao launch --agents developer --provider gemini

# Background session with custom name
cao launch --agents developer --session-name dev-agent-001 --headless
```

**What happens internally:**
1. Validates provider and agent profile
2. Sends `POST http://localhost:9889/sessions?provider=<provider>&agent_profile=<name>[&session_name=<name>]`
3. Server creates tmux session/window, assigns `CAO_TERMINAL_ID`, and initializes the selected CLI provider
4. If not headless, runs `tmux attach-session -t <session-name>`

**Errors:**
- `Failed to connect to cao-server`: Ensure `cao-server` is running
- `Invalid provider`: Provider must be one of `codex`, `gemini`
- `Failed to create session`: Check `~/.wepppy/cao/logs/cao.log` for details

### cao shutdown

Terminates CAO sessions.

```bash
# Shutdown specific session
cao shutdown --session cao-<session-id>

# Shutdown all CAO sessions
cao shutdown --all
```

**What happens:**
1. Sends `DELETE http://localhost:9889/sessions/<session-name>`
2. Server kills the tmux session via `tmux kill-session`
3. Database records for terminals in that session are cleaned up
4. Log files remain for post-mortem analysis

### cao install

Installs an agent profile from built-in store, local file, or URL.

```bash
# Built-in profiles
cao install code_supervisor
cao install developer
cao install reviewer

# Custom profiles
cao install ./my-agent.md
cao install /absolute/path/to/agent.md
cao install https://example.com/agent.md
```

**What happens:**
1. Resolves the source (built-in, file, or URL)
2. Parses the markdown file (validates YAML frontmatter if present)
3. Copies to `~/.wepppy/cao/agent-store/<name>.md`
4. Mirrors to `~/.codex/prompts/<name>.md` for Codex CLI discovery
5. Profile is now usable in `cao launch --agents <name>`

**Profile format:**
```markdown
---
name: my_agent
description: Brief description
---

System prompt content goes here.
This text becomes the agent's instructions.
```

See [docs/agent-profile.md](docs/agent-profile.md) for comprehensive authoring guidelines.

### cao flow add

Registers a scheduled flow for automated execution.

```bash
cao flow add <path-to-flow.md>
```

**Example:**
```bash
cao flow add services/cao/src/cli_agent_orchestrator/flows/doc_janitor.yaml
cao flow add examples/flow/morning-trivia.md
```

**Flow file format (Markdown with YAML frontmatter):**

```yaml
---
name: daily-standup              # Required: unique identifier
schedule: "0 9 * * 1-5"         # Required: cron expression
agent_profile: developer         # Required: installed agent profile name
script: ./health-check.sh       # Optional: conditional execution script
enabled: true                    # Optional: defaults to true
---

Your task instructions go here.
Template variables like [[variable_name]] will be replaced
with output from the script if provided.
```

**What happens:**
1. Parses the flow file and validates required fields (`name`, `schedule`, `agent_profile`)
2. Validates cron expression and calculates next run time
3. Stores flow in database with status `enabled: true` (default)
4. Flow daemon will execute at scheduled times (checks every 60 seconds)

**Errors:**
- `Flow '<name>' already exists`: Use `cao flow remove <name>` first or choose a new name
- `Invalid cron expression`: Fix the `schedule` field (e.g., `"0 9 * * *"` for 9am daily)
- `Missing required field`: Ensure `name`, `schedule`, and `agent_profile` are in frontmatter

### cao flow list

Displays all registered flows with schedule and status.

```bash
cao flow list
```

**Output example:**
```
Name              Schedule       Next Run             Enabled
doc-janitor       0 9 * * *      2025-10-29 09:00:00  True
morning-trivia    30 7 * * *     2025-10-29 07:30:00  True
monitor-service   */5 * * * *    2025-10-28 14:05:00  False
```

### cao flow run

Manually executes a flow (ignores schedule).

```bash
cao flow run <flow-name>
```

**Example:**
```bash
# Test a flow before enabling cron
cao flow run doc-janitor
```

**What happens:**
1. Retrieves flow definition from database
2. If `script` is defined, executes it and checks `{"execute": true/false}` in JSON output
3. If `execute: true` (or no script), creates a new agent session with the flow's agent profile
4. Sends the flow prompt (with template variable substitution) to the agent
5. Updates `last_run` and `next_run` timestamps in database

### cao flow enable/disable

Toggles whether a flow runs on schedule.

```bash
cao flow enable <flow-name>
cao flow disable <flow-name>
```

**Use case:** Temporarily pause a flow without removing it.

### cao flow remove

Deletes a flow from the database.

```bash
cao flow remove <flow-name>
```

**Warning:** This is permanent. Re-add the flow with `cao flow add` if needed.

---

## Orchestration Patterns

CAO supports three patterns for multi-agent coordination, accessible via MCP tools that agents can invoke:

### 1. Handoff (Synchronous Transfer)

**Use when:** You need the result before proceeding (e.g., sequential code review → merge).

**Pattern:**
1. Supervisor agent calls `handoff(agent_profile="reviewer", message="Review PR #123")`
2. CAO creates a new terminal with the `reviewer` profile
3. Supervisor waits until reviewer terminal reaches `COMPLETED` status
4. Reviewer's output is returned to supervisor
5. Reviewer terminal is automatically exited

**Workflow diagram:**

```
┌────────────┐
│ Supervisor │
└─────┬──────┘
      │ handoff(reviewer, "Review PR")
      ├──────────────────────────────►┌──────────┐
      │                                │ Reviewer │
      │                                └────┬─────┘
      │                                     │ (reviews code)
      │                                     │
      │◄────────────────────────────────────┤ COMPLETED
      │ (receives review feedback)          │
      │                                     │ (exits)
      ▼
```

**Example flow:** Generate code → handoff to tester → handoff to reviewer → merge.

### 2. Assign (Asynchronous Spawning)

**Use when:** Tasks can run in parallel or you don't need to wait (e.g., data processing, background monitoring).

**Pattern:**
1. Supervisor calls `assign(agent_profile="analyst", message="Analyze dataset A", callback_message="Report results to supervisor")`
2. CAO creates a new terminal with the `analyst` profile
3. Supervisor receives terminal ID immediately and continues working
4. Analyst works independently in the background
5. When complete, analyst sends results back to supervisor via `send_message`
6. Messages queue in supervisor's inbox until supervisor becomes IDLE

**Workflow diagram:**

```
┌────────────┐
│ Supervisor │
└─────┬──────┘
      │ assign(analyst, "Analyze A")
      ├────────────────────────►┌──────────┐
      │                         │ Analyst  │
      │ assign(analyst, "Analyze B")       └────┬─────┘
      ├────────────────────────►┌──────────┐    │
      │                         │ Analyst  │    │ (parallel work)
      │                         └────┬─────┘    │
      │                              │          │
      │ (continues other work)       │          │
      │                              │          │
      │◄─────send_message────────────┤          │
      │ (queued in inbox)            │          │
      │◄─────send_message────────────┼──────────┤
      │ (queued in inbox)                       │
      ▼ (becomes IDLE, inbox delivers messages) │
```

**Example flow:** Supervisor assigns parallel data analysis to 3 analysts, continues generating report template, combines results when all analysts report back.

See [examples/assign](examples/assign) for a complete working example.

### 3. Send Message (Direct Communication)

**Use when:** You need to communicate with an existing agent (e.g., iterative feedback, swarm coordination).

**Pattern:**
1. Agent A calls `send_message(terminal_id="agent-b-id", message="Update parameter X")`
2. Message is queued in Agent B's inbox
3. Inbox watcher monitors Agent B's log file
4. When Agent B becomes IDLE (detected by provider's idle pattern), message is delivered
5. Agent B processes the message and continues

**Workflow diagram:**

```
┌───────────┐                   ┌───────────┐
│  Agent A  │                   │  Agent B  │
└─────┬─────┘                   └─────┬─────┘
      │                               │ (working, PROCESSING)
      │ send_message(B, "Task update")│
      ├──────────────────────────────►│ (queued in inbox)
      │                               │
      │                               │ (finishes current task)
      │                               │ → IDLE detected
      │                               ├─ Inbox delivers message
      │                               │
      │                               ├─ Processes update
      │◄──────send_message────────────┤
      │ (response queued)             │
      ▼                               ▼
```

**Example flow:** Developer implements feature → sends to reviewer → reviewer requests changes → developer updates → reviewer approves (multi-turn conversation).

### How Orchestration Works Under the Hood

**MCP Tools** are registered in `src/cli_agent_orchestrator/mcp_server/server.py`:
- `handoff` → `POST /sessions/{session}/terminals` + polling for COMPLETED + `GET /terminals/{id}/output`
- `assign` → `POST /sessions/{session}/terminals` + immediate return
- `send_message` → `POST /terminals/{id}/inbox/messages`

**Terminal Status Detection** (`providers/codex.py`):
- Codex provider uses regex patterns on tmux history:
  - `IDLE`: Matches `codex[...] >` or `codex[...] ❯` prompt
  - `WAITING_USER_ANSWER`: Matches "approval required"
  - `ERROR`: Matches "error:" or "failed:"
  - `PROCESSING`: Default state when no other pattern matches

**Inbox Delivery Mechanism** (`services/inbox_service.py`):
- `PollingObserver` watches `~/.wepppy/cao/logs/terminal/` directory
- When a log file changes, `LogFileHandler` reads the tail
- If provider's idle pattern is detected, `check_and_send_pending_messages()` is called
- Codex and Gemini terminals execute queued work via non-interactive CLI invocations (`codex exec …`, `gemini -p … --approval-mode=yolo`)
- All `PENDING` messages for that terminal are sent via `tmux send-keys`
- Message status updated to `DELIVERED` in database

---

## Flows: Scheduled Automation

Flows enable unattended execution of agent tasks on cron schedules with optional conditional logic.

### Flow Anatomy

**Flow file** (`my-flow.md`):

```yaml
---
name: monitor-service
schedule: "*/5 * * * *"          # Every 5 minutes
agent_profile: developer
script: ./health-check.sh        # Optional: conditional execution
enabled: true
---

The service at [[url]] is down (status: [[status_code]]).
Please investigate and triage:
1. Check recent deployments
2. Review error logs
3. Identify root cause
```

**Conditional execution script** (`health-check.sh`):

```bash
#!/bin/bash
set -euo pipefail

URL="https://api.example.com/health"
STATUS=$(curl -s -o /dev/null -w "%{http_code}" "$URL")

if [ "$STATUS" != "200" ]; then
  # Service is down - execute flow
  echo "{\"execute\": true, \"output\": {\"url\": \"$URL\", \"status_code\": \"$STATUS\"}}"
else
  # Service is healthy - skip execution
  echo "{\"execute\": false, \"output\": {}}"
fi
```

**How it works:**
1. Flow daemon runs every 60 seconds (background task in `api/main.py:flow_daemon()`)
2. Queries database for flows where `next_run <= now()` and `enabled = true`
3. For each flow:
   - If `script` defined, execute it and parse JSON output
   - If `{"execute": false}`, skip flow and update `next_run`
   - If `{"execute": true}` or no script, create agent session
   - Render flow prompt template with script output variables (e.g., `[[url]]` → actual URL)
   - Send prompt to agent terminal
   - Update `last_run` and `next_run` in database
4. Agent session persists; use `cao shutdown` to clean up after inspecting results

### Flow Lifecycle

```bash
# Add flow (status: enabled=true by default)
cao flow add monitor-service.md

# List flows (shows schedule and next run time)
cao flow list

# Manually test (ignores schedule)
cao flow run monitor-service

# Disable temporarily
cao flow disable monitor-service

# Re-enable
cao flow enable monitor-service

# Remove permanently
cao flow remove monitor-service
```

### Example 1: Simple Daily Task

**File:** `daily-standup.md`

```yaml
---
name: daily-standup
schedule: "0 9 * * 1-5"  # 9am on weekdays
agent_profile: developer
---

Review yesterday's commits and create a standup summary:
1. What was completed
2. Current blockers
3. Today's priorities
```

**No script:** Executes unconditionally every weekday morning.

### Example 2: Conditional Monitoring

**File:** `disk-space-alert.md`

```yaml
---
name: disk-space-alert
schedule: "0 * * * *"  # Hourly
agent_profile: developer
script: ./check-disk-space.sh
---

Disk usage alert: [[filesystem]] is [[usage]]% full ([[available]] remaining).
Please investigate and free up space.
```

**Script:** `check-disk-space.sh`

```bash
#!/bin/bash
set -euo pipefail

THRESHOLD=80
USAGE=$(df -h / | awk 'NR==2 {print $5}' | sed 's/%//')

if [ "$USAGE" -gt "$THRESHOLD" ]; then
  FILESYSTEM=$(df -h / | awk 'NR==2 {print $1}')
  AVAILABLE=$(df -h / | awk 'NR==2 {print $4}')
  echo "{\"execute\": true, \"output\": {\"filesystem\": \"$FILESYSTEM\", \"usage\": \"$USAGE\", \"available\": \"$AVAILABLE\"}}"
else
  echo "{\"execute\": false, \"output\": {}}"
fi
```

**Behavior:** Only creates agent session when disk usage exceeds 80%.

### Flow Best Practices

1. **Start with manual runs:** Test with `cao flow run <name>` before enabling cron
2. **Use scripts for efficiency:** Avoid spawning agents when conditions aren't met
3. **Clean up sessions:** Flows create persistent tmux sessions; shut them down after inspection
4. **Monitor logs:** Check `~/.wepppy/cao/logs/cao.log` for flow execution history
5. **Keep schedules reasonable:** Avoid sub-minute intervals unless truly necessary

---

## API Reference

The HTTP API powers both CLI commands and MCP tools. Complete documentation available in [docs/api.md](docs/api.md).

**Base URL:** `http://localhost:9889` (configurable via `SERVER_PORT` in `constants.py`)

**Key endpoints:**

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/health` | Health check |
| POST | `/sessions` | Create session with terminal |
| GET | `/sessions` | List all sessions |
| GET | `/sessions/{name}` | Get session details |
| DELETE | `/sessions/{name}` | Kill session |
| POST | `/sessions/{name}/terminals` | Create terminal in existing session |
| GET | `/terminals/{id}` | Get terminal status |
| POST | `/terminals/{id}/input` | Send input to terminal |
| GET | `/terminals/{id}/output` | Get terminal output |
| POST | `/terminals/{id}/exit` | Exit terminal |
| DELETE | `/terminals/{id}` | Delete terminal |
| POST | `/terminals/{id}/inbox/messages` | Send message to terminal |
| GET | `/terminals/{id}/inbox/messages` | List inbox messages |

**Example: Create session via API**

```bash
curl -X POST "http://localhost:9889/sessions?provider=gemini&agent_profile=developer" \
  | jq
```

**Response:**
```json
{
  "terminal_id": "dev-a1b2c3d4",
  "session_name": "cao-e5f6g7h8",
  "window_name": "developer-a1b2",
  "name": "developer-a1b2",
  "provider": "gemini",
  "status": "IDLE",
  "agent_profile": "developer"
}
```

---

## Configuration

Configuration lives in `src/cli_agent_orchestrator/constants.py`:

```python
# Server
SERVER_HOST = "localhost"
SERVER_PORT = 9889
SERVER_VERSION = "1.0.0"

# Paths
CAO_HOME = Path.home() / ".wepppy" / "cao"
AGENT_STORE_DIR = CAO_HOME / "agent-store"
TERMINAL_LOG_DIR = CAO_HOME / "logs" / "terminal"
DATABASE_PATH = CAO_HOME / "db" / "cli-agent-orchestrator.db"

# Providers
PROVIDERS = ["codex", "gemini"]
CODEX_PROMPT_DIR = Path.home() / ".codex" / "prompts"

# Timings
INBOX_POLLING_INTERVAL = 5  # seconds (watchdog poll rate)
FLOW_CHECK_INTERVAL = 60    # seconds (flow daemon)
```

**To customize:**
1. Edit `constants.py` before installation
2. Or set environment variables (if added to code)

---

## Developer Notes

### Adding a New Provider

1. Create `src/cli_agent_orchestrator/providers/my_provider.py` extending `BaseProvider`
2. Implement required methods:
   - `initialize()` — Start the CLI tool and wait for ready state
   - `get_status()` — Detect IDLE/PROCESSING/ERROR/WAITING_USER_ANSWER from output
   - `get_idle_pattern_for_log()` — Return regex pattern for inbox watcher
   - `extract_last_message_from_script()` — Parse final output for handoff return value
   - `exit_cli()` — Return command to exit the tool
3. Register in `constants.py:PROVIDERS`
4. Update `provider_manager.py:create_provider()` to instantiate your provider

### Testing Strategy

Currently no automated test suite. Recommended approach:
- Functional tests using `pytest` + `libtmux` mocks
- Integration tests with real tmux sessions (requires cleanup)
- Provider tests with captured CLI output samples

Create `tests/` directory under `services/cao/` and follow wepppy test conventions (see `tests/AGENTS.md` in repo root).

### Code Organization

- **Entry points** (`cli/`, `mcp_server/`, `api/`) should be thin wrappers calling service layer
- **Services** (`services/`) contain business logic; no direct tmux/database calls
- **Clients** (`clients/`) encapsulate external dependencies (tmux, SQLite)
- **Providers** (`providers/`) implement CLI tool-specific logic; isolate regex patterns

### Known Limitations

1. **Codex-only:** No other AI CLI tools supported yet (future: add Claude CLI, Aider, etc.)
2. **Status detection fragility:** Regex-based provider heuristics may break if Codex changes TUI
3. **No auto-merge for flows:** Scheduled flows create sessions but don't clean up automatically
4. **Single-threaded inbox watcher:** High message volume could cause delivery delays
5. **No authentication:** HTTP API is unauthenticated (assumes localhost-only deployment)

---

## Operational Notes

### Running in Production

**Deployment checklist:**
1. Run `cao-server` as a systemd service (or supervisord)
2. Configure log rotation for `~/.wepppy/cao/logs/`
3. Monitor health endpoint: `curl http://localhost:9889/health`
4. Set up alerts for flow execution failures (check logs)
5. Periodically clean up old tmux sessions: `cao shutdown --all` (use with caution)

**Systemd example:**

```ini
[Unit]
Description=CLI Agent Orchestrator Server
After=network.target

[Service]
Type=simple
User=wepppy
WorkingDirectory=/workdir/wepppy
ExecStart=/home/wepppy/.local/bin/cao-server
Restart=on-failure
RestartSec=10

[Install]
WantedBy=multi-user.target
```

### Monitoring

**Health checks:**
```bash
curl http://localhost:9889/health
# Expected: {"status": "ok", "service": "cli-agent-orchestrator"}
```

**Inspect database:**
```bash
sqlite3 ~/.wepppy/cao/db/cli-agent-orchestrator.db
.tables
SELECT * FROM terminals WHERE status != 'COMPLETED';
SELECT * FROM flows WHERE enabled = 1;
```

**View logs:**
```bash
tail -f ~/.wepppy/cao/logs/cao.log
tail -f ~/.wepppy/cao/logs/terminal/<terminal-id>.log
```

### Troubleshooting

**Problem:** `cao launch` fails with "Failed to connect to cao-server"  
**Solution:** Ensure `cao-server` is running (`ps aux | grep cao-server`)

**Problem:** Flow doesn't execute at scheduled time  
**Solution:** Check `cao flow list` for next run time; verify `enabled: true`; inspect `~/.wepppy/cao/logs/cao.log` for flow daemon errors

**Problem:** Agent terminal stuck in PROCESSING  
**Solution:** Attach to tmux session (`tmux attach -t <session-name>`) and inspect; Codex may be waiting for user approval or encountering an error

**Problem:** Inbox messages not delivered  
**Solution:** Check provider's `get_idle_pattern_for_log()` matches actual prompt; verify terminal log file exists and is being written to

**Problem:** Duplicate flow name error  
**Solution:** Remove existing flow first: `cao flow remove <name>`, then re-add

---

## Further Reading

- [AGENTS.md](AGENTS.md) — Development workflow guidance for maintaining CAO
- [CODEBASE.md](CODEBASE.md) — Detailed architecture and data flow diagrams
- [docs/api.md](docs/api.md) — Complete HTTP API reference
- [docs/agent-profile.md](docs/agent-profile.md) — Agent profile authoring guide
- [docs/doc-janitor-flow.md](docs/doc-janitor-flow.md) — Doc Janitor automation pilot notes
- [examples/](examples/) — Working examples of orchestration patterns

**Wepppy integration:**
- [docs/work-packages/20251102_doc_janitor_flow/](../../docs/work-packages/20251102_doc_janitor_flow/) — Work package tracker for CAO automation pilot

**Upstream project:**
- [awslabs/cli-agent-orchestrator](https://github.com/awslabs/cli-agent-orchestrator) — Original project (Apache-2.0)

---

## License and Attribution

This software is derived from [awslabs/cli-agent-orchestrator](https://github.com/awslabs/cli-agent-orchestrator), licensed under the Apache License 2.0.

**Modifications in this fork:**
- Replaced Amazon Q CLI provider with Codex CLI provider
- Relocated to wepppy service tree (`services/cao/`)
- Updated configuration paths to use `~/.wepppy/cao/` and `~/.codex/prompts/`
- Adapted installation workflow for `uv` package manager
- Integrated with wepppy documentation standards (AGENTS.md, work packages)

**Original Copyright:** Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.

**Derivative Work:** Copyright 2025 University of Idaho. All Rights Reserved.

Licensed under the Apache License, Version 2.0 (the "License"); you may not use this file except in compliance with the License. You may obtain a copy of the License at:

http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the specific language governing permissions and limitations under the License.

See [LICENSE](LICENSE) for full Apache-2.0 license text and [NOTICE](NOTICE) for attribution details.
