# Doc Janitor (Janny) Flow (Pilot Notes)

The doc-janitor maintenance flow keeps Markdown hygiene tasks on a schedule using CLI Agent Orchestrator (CAO). This document tracks the pilot configuration created on 2025-11-02.

## Components

- `src/cli_agent_orchestrator/scripts/doc_janitor.sh` — stub script that will eventually run lint/catalog/TOC commands and open maintenance PRs. Currently prints TODO steps for dry-run validation.
- `src/cli_agent_orchestrator/flows/doc_janitor.yaml` — disabled flow definition with a placeholder cron (`0 9 * * *`) and the `code_supervisor` agent profile.
- Work package tracker: `docs/work-packages/20251102_doc_janitor_flow/tracker.md` (in parent repo) captures scope, guardrails, and rollout plan.

## Pilot Checklist

1. **Manual dry run**
   - Start CAO server (`cao-server`) and ensure tmux/gh credentials are loaded.
   - From a supervisor terminal, execute the script:  
     ```bash
     bash src/cli_agent_orchestrator/scripts/doc_janitor.sh
     ```  
     Verify the stub prints the TODO list without modifying the repo.
2. **Wiring test via CAO**
   - Temporarily set `enabled: true` in `flows/doc_janitor.yaml`.
   - Use `cao launch --agents code_supervisor --session-name janitor-test` and call the `doc-janitor` flow once (manual trigger).
   - Confirm the agent runs the script and posts the placeholder output.
   - Revert `enabled` to `false` after the test.
3. **Implement real actions**
   - Flesh out the script with the steps listed in the stub once guardrails are agreed upon.
   - Add diff-size enforcement, branch naming, telemetry append, and PR creation.
4. **Schedule activation**
   - Update the cron expression to the agreed maintenance window.
   - Flip `enabled: true`.
   - Monitor first week of runs; merge PRs manually.

## Operational Notes

- Keep the maintenance branch namespace `automation/doc-janitor/*` for easy filtering.
- If the flow must be paused, disable it in the YAML and remove any queued cron jobs via CAO supervisor terminal.
- Script should exit non-zero on lint failures or guardrail breaches and send status back through MCP so the supervisor can alert maintainers.

