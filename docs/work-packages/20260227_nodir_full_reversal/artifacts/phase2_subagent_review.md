# Phase 2 Subagent Review

## Review Runs

### Run 1: Correctness/Regression Pass (Recovered prior in-thread review evidence)
- Source: recovered active subagent threads from the same parent thread when thread cap blocked new spawns.
- Findings summary:
  - `high`: route-level mutation lock regressions (no-op mutation wrappers), omni lock contention risk, archive root mutation boundary regressions.
  - `medium`: unlocked `upload_dem` mutation path, missing workflow-level guard tests, incomplete export error-contract assertions.
- Representative findings (file/line anchors from reviewer outputs):
  - `wepppy/microservices/rq_engine/upload_climate_routes.py:50,112` (`high`)
  - `wepppy/microservices/rq_engine/landuse_routes.py:52,197` (`high`)
  - `wepppy/nodb/mods/omni/omni_mode_build_services.py:42,53` (`high`)
  - `wepppy/microservices/rq_engine/watershed_routes.py:503,517,587` (`medium`)
  - `tests/rq/test_project_rq_mutation_guards.py:14` (`medium`)

### Run 2: Post-fix static re-review (new agents)
- `reviewer` output (post-fix run):
  - unresolved `medium`: strict NoDir mapping helper typing risk, non-canonical multi-root lock ordering risk.
- `test_guardian` output (post-fix run):
  - unresolved `medium`: missing cross-route strict-typing tests for helper behavior and no direct omni lock-order test.

### Run 3: Final post-fix re-review (after targeted fixes)
- `reviewer` (`agent_id` `019c9da1-85da-75a3-8ce6-40c02898228e`):
  - "Unresolved high/medium correctness findings: 0"
- `test_guardian` (`agent_id` `019c9da1-8608-7b20-a882-2c9c0902c1a9`):
  - "No unresolved high/medium test-adequacy findings remain"

## Final Severity Status

- `high`: 0 unresolved
- `medium`: 0 unresolved
- `low`: residual low-risk notes captured in findings resolution with phase assignment where deferred
