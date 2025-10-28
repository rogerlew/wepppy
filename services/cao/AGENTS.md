# CAO Service — AGENTS Guide

## Mission
- Maintain and extend the CLI Agent Orchestrator (CAO) that lives under `services/cao`.
- Ensure flows, providers, and automation scripts play nicely with wepppy infrastructure (tmux, Codex CLI, GitHub automation).
- Keep documentation (README, doc-janitor tracker) current when behaviours change.

## Environment
- Python 3.12 (managed via `uv pip install -e services/cao`).
- Codex CLI must be installed and logged-in on the host (`codex --full-auto`, auth lives in `~/.codex/`).
- tmux ≥ 3.3 available on the machine; CAO spawns sessions under `cao-*`.
- SQLite state and agent artefacts live at `~/.wepppy/cao/`.

To import the package directly (outside editable install):
```bash
export PYTHONPATH=/workdir/wepppy/services/cao/src:$PYTHONPATH
python -c "import cli_agent_orchestrator; print(cli_agent_orchestrator.__file__)"
```

## Key Paths
- `services/cao/src/cli_agent_orchestrator/constants.py` – provider/default paths.
- `services/cao/src/cli_agent_orchestrator/providers/codex.py` – Codex provider heuristics.
- `services/cao/src/cli_agent_orchestrator/cli/commands/` – `cao` subcommands.
- `services/cao/src/cli_agent_orchestrator/services/flow_service.py` – flow CRUD/execute.
- `services/cao/src/cli_agent_orchestrator/scripts/` – automation scripts (doc janitor stub).
- `services/cao/docs/doc-janitor-flow.md` + `docs/work-packages/20251102_doc_janitor_flow/` – maintenance pilot notes.

## Workflows
### Install / dev setup
```bash
uv pip install -e services/cao        # brings in FastAPI, libtmux, etc.
cao --help
cao-server                            # start API/mcp server (runs FastAPI + background daemons)
```
> Keep `cao-server` in its own tmux session; logs appear under `~/.wepppy/cao/logs/`.

### Agent provisioning
```bash
cao install code_supervisor           # copies agent markdown + mirrors into ~/.codex/prompts/
cao launch --agents code_supervisor   # new tmux session with Codex CLI
tmux attach -t <session>              # inspect interactive run
```

### Flow management
```bash
cao flow add services/cao/src/cli_agent_orchestrator/flows/doc_janitor.md
cao flow list
cao flow disable doc-janitor          # guardrails on by default
cao flow run doc-janitor              # manual dry-run
```
- Flow files **must** be Markdown with YAML front matter (`name`, `schedule`, `agent_profile`, optional `script`).
- Duplicate `name` entries now raise a friendly error; remove the existing flow via `cao flow remove <name>` first.

### Provider heuristics
- Codex provider assumes the CLI prompt includes the agent system prompt. Update regex patterns in `providers/codex.py` if Codex changes its TUI framing.
- `wait_for_shell` timeout is 10 s; tweak if startup is slower on remote nodes.
- `get_idle_pattern_for_log()` returns a simple substring for inbox watcher; update to reduce false negatives if we observe message drops.

### Doc Janitor pilot
- Script stub (`scripts/doc_janitor.sh`) currently emits TODO steps. Fill in lint/catalog/TOC logic before flipping the flow to `enabled: true`.
- Telemetry should append to `telemetry/docs-quality.jsonl` in the repo when implemented; ensure paths created with `mkdir -p`.

## Quality Gates
- No test suite yet; when adding core logic, prefer functional tests under `services/cao/tests/` (create directory) using pytest + libtmux mocks.
- Run `ruff`/`black`? Not configured; keep code black-compatible and rely on existing repo tooling.
- Keep README, CODEBASE, documentation and this AGENTS file updated when APIs or workflows shift.

## Operational Notes
- `cao-server` binds to `http://localhost:9889`; health endpoint `/health`.
- SQLite DB path: `~/.wepppy/cao/db/cli-agent-orchestrator.db`. Use caution when deleting flows; removing the file wipes all state.
- tmux pipe-pane logs land in `~/.wepppy/cao/logs/terminal/<terminal-id>.log`; inbox watcher looks there for IDLE prompts.
- Codex CLI updates occasionally change colour codes; regression-test provider status detection after upgrading Codex.

## Escalation
- Provider fails to detect prompts -> adjust regex and add logging (`logger.debug`) in `codex.py`.
- Flow execution throws on duplicate names -> use `cao flow remove <name>` then re-add.
- If tmux or Codex not installed, add guard checks in CLI commands before attempting sessions.

Stay aligned with wepppy conventions (uk2us where applicable, documentation-first). When in doubt, coordinate via work-package docs before large automation changes.
