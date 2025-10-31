# CI Samurai Agent Guide

This document supplements the top-level [AGENTS.md](../../AGENTS.md) with details that apply specifically to the CI Samurai automation stack. All agents (human or AI) working on CI Samurai must read the global guide first, then follow the additional rules below.

## Environment
- Sessions run directly on **`nuc2.local`** inside the production docker-compose stack.
- `/workdir/wepppy` is the live workspace; the CAO server does **not** execute in a throwaway copy.
- Activate the project virtualenv (`source services/cao/.venv/bin/activate`) or call `/workdir/wepppy/services/cao/.venv/bin/python` explicitly.
- Use `wctl` wrappers for all pytest, npm, and docker operations (`wctl run-pytest`, `wctl up`, `wctl run-npm`, etc.). Do **not** call bare `pytest`, `pip install`, or `docker compose` unless you are updating the tooling itself.
- The CAO inbox runs Codex with `--dangerously-bypass-approvals-and-sandbox`; network and filesystem access are unrestricted. Treat the environment as production and avoid destructive actions.

## Workflow Overview
1. Nightly workflow collects triage logs on nuc1 and produces `failures.jsonl`.
2. `run_fixer_loop.py` (on nuc2) optionally runs the infra validator, then spawns a fresh fixer agent per failure via CAO.
3. Each agent must:
   - Read the system prompt and inputs (PRIMARY_TEST, STACK, SNIPPET, etc.).
   - Investigate/fix within allowlisted paths (`tests/**`, `wepppy/**/*.py`), respecting the denylist (`wepppy/nodb/base.py`, `docker/**`, `.github/workflows/**`, `deps/linux/**`).
   - Run the provided `VALIDATION_CMD` (`cd /workdir/wepppy && wctl run-pytest -q <nodeid>`).
   - Open a PR (when tests pass) or issue (when blocked) using `gh`. Include URLs in RESULT_JSON.
   - Emit RESULT_JSON exactly as specified to avoid timeouts.

## Safety Requirements
- No `ssh` back into nuc2—agents are already local. `run_fixer_loop.py` handles remote access when needed.
- Do not uninstall or install global packages. If dependencies are missing, patch the repository or file an issue, but leave the system environment untouched.
- GitHub labels (`ci-samurai`, `infra-check`, confidence tags) must exist; create missing labels via `gh label create` instead of editing repo metadata manually.
- SSH calls initiated by the fixer loop run with host-key checks disabled. Only trusted hosts should be targeted.

## Files & Logging
- `triage.txt`, `failures.jsonl`, and `agent_logs/` live under `/wc1/ci-samurai/logs/<timestamp>/` (nuc1) and the workflow workspace.
- Infra/fixer transcripts are stored in `agent_logs/` for post-run debugging.
- Branches follow `ci/infra/<timestamp>` (infra) and `ci/fix/<date>/<test-slug>` (fixer).

## Troubleshooting
- **No RESULT_JSON**: inspect the session log under `agent_logs/*-noresult.log`.
- **`gh` failure**: ensure network access and labels exist; rerun `gh auth status` inside the CAO environment.
- **Validation fails**: rerun `wctl run-pytest -q <nodeid>` manually to replicate.
- **CAO server down**: restart with `sudo systemctl restart cao-server.service` on nuc2.

## References
- [CI Samurai README](README.md)
- [Top-level AGENTS.md](../../AGENTS.md#ci-samurai-agents)
- [Agent Profiles](../src/cli_agent_orchestrator/agent_store/)
- [run_fixer_loop.py](run_fixer_loop.py)

**Last updated:** $(date +%Y-%m-%d)
