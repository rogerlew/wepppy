# Tracker – StatusStream Telemetry Cleanup

## Summary
Finalized the StatusStream-only pipeline. Notes below capture the key steps and remaining follow-ups (if any).

## Timeline
- **2025-10-23** – Work-package structure proposed and created. Legacy `ws_client.js` removed, docs updated, climate controller/test adjusted, lint/test run.

## Task Board
### Done
- Remove `ws_client.js` and drop from bundle priority list.
- Simplify `control_base.js` surface (remove `manage_ws_client`).
- Update controller stubs/tests (`control_base_stub.js`, climate Jest suite).
- Refresh architecture/docs (AGENTS, README, controllers_js README, prompts).
- Capture work-package README and package documentation.

### Follow-up / Backlog
- Encourage future efforts to start their own work packages.
- Consider migrating older prompt collections into the new structure.

## Decisions
- **2025-10-23** – Adopt `docs/work-packages/YYYYMMDD_slug` convention with `package.md`, `tracker.md`, and `prompts/{active,completed}` directories.
- **2025-10-23** – Archive WSClient prompt under this package rather than keeping it in `docs/prompts/`.

## Risks / Notes
- Watch for stale references to the old prompt path; a pointer stub remains to guide readers.
- If another team depends on the old structure, coordinate future migrations gradually.

## Verification
- `wctl run-npm test -- controllers_js/__tests__/climate.test.js`
- Manual `rg "WSClient"` and `rg "ws_client"` sweeps show only historical notes remain.
