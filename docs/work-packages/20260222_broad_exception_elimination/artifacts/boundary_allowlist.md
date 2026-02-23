# Boundary Allowlist (Package Snapshot)

Canonical allowlist location:

- `docs/standards/broad-exception-boundary-allowlist.md`

The checker (`tools/check_broad_exceptions.py`) now loads that canonical file by default and suppresses matching `(file, line, handler)` entries in both report and `--enforce-changed` modes.

## Milestone 8 resolution status (2026-02-23)

Deferred swallow-style hotspots called out at Milestone 7 were resolved in Milestone 8:

- `wepppy/weppcloud/routes/user.py`:
  - `_claim_names` no longer uses broad catch; narrowed to `SQLAlchemyError` with explicit warning log.
  - `_build_meta` and `_build_map_meta` keep deliberate per-run boundary catches with explicit logging and route-level regression coverage; these boundaries were promoted to canonical allowlist IDs `BEA-20260223-010` and `BEA-20260223-011`.
- `services/cao/src/cli_agent_orchestrator/services/inbox_service.py`:
  - `_has_idle_pattern` no longer uses broad catch; now uses narrow expected exceptions with explicit logs.
  - provider import detection no longer uses broad catch; now degrades only on import-related failures.

Remaining deferred swallow-style hotspots from this package: `none`.
