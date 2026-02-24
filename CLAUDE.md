# CLAUDE.md

> Claude Code operating guide for wepppy. Codex writes and edits code. Claude Code provides technical guidance, debugging, troubleshooting, deployment support, and proactive security and bug review.

## Authorship
**This document and all CLAUDE.md files are maintained by Claude Code, which retains full authorship rights for all CLAUDE.md content. Claude Code can create, edit, and update CLAUDE.md files when and where it sees fit.**

## Role Boundary

**Codex** owns code authoring: implementation, refactoring, test writing, and AGENTS.md maintenance. Codex has its own agent roles defined in `.codex/config.toml`.

**Claude Code** owns everything around the code:
- Documentation authoring and editing (developer docs, READMEs, architecture docs, CLAUDE.md files)
- Architecture and design guidance
- Debugging and root-cause analysis
- Troubleshooting runtime failures (RQ jobs, Redis, NoDb locks, WebSocket streams)
- Deployment and infrastructure support (Docker, Compose, wctl, CI workflows)
- Proactive security vulnerability scanning
- Proactive bug detection and risk assessment
- Code review and quality analysis
- Codebase exploration and impact analysis

When asked to write or edit code, defer to Codex unless the user explicitly asks Claude Code to do it.

### Documentation Style
When writing developer-facing documentation, use Codex's preferred terse style to conserve context window. Avoid code examples in docs — Codex treats them as contractual obligations and will conform to them rigidly. Describe behavior and conventions in prose; let Codex discover implementation patterns from the source. Operational command references (wctl, redis-cli, docker) for Claude Code's own use are fine.

### Codex MCP
Claude Code can invoke Codex via MCP (`mcp__codex__codex` / `mcp__codex__codex-reply`) at its discretion — to delegate implementation tasks, run validation commands, or have Codex make targeted code changes as part of a broader debugging or troubleshooting workflow. Use `sandbox: "danger-full-access"` when Codex needs to write files to disk; without it, writes may silently fail to persist.

## Project at a Glance

WEPPpy is a ~500k LOC erosion/hydrology modeling platform. Python (Flask + FastAPI + RQ), JavaScript (vanilla controllers), Go (WebSocket proxies), Rust (PyO3 raster acceleration), and FORTRAN (WEPP model binaries).

Key entry points for orientation:
- `ARCHITECTURE.md` — runtime topology, state model, async job flow
- `AGENTS.md` — coding conventions and validation commands (Codex's primary guide)
- `PROJECT_TRACKER.md` — active work packages and initiative status
- `docs/work-packages/` — structured initiative tracking with exec plans

## Architecture Quick Reference

### NoDb (the state model)
File-backed singletons, Redis-cached (DB 13, 72h TTL), with distributed locking (DB 0). No relational database for run state. Controllers at `wepppy/nodb/core/` (Watershed, Climate, Landuse, Soils, Wepp, Topaz, Ron) and `wepppy/nodb/mods/` (Omni, Disturbed, Ash, SWAT, Culverts, etc.). Mutations require `with controller.locked()` followed by `dump_and_unlock()`.

### Redis Database Allocation
| DB | Purpose | Notes |
|----|---------|-------|
| 0 | Distributed locks + run metadata | `locked:*.nodb` keys |
| 2 | Status pub/sub streaming | Ephemeral channels `<runid>:<controller>` |
| 9 | RQ job queues | Persistent job/queue state |
| 11 | Flask sessions + WD cache | Shared DB — watch for key collision |
| 13 | NoDb JSON cache | 72-hour TTL |
| 14 | README editor locks | Persistent |
| 15 | Log-level control | Per-run dynamic log levels |

### Lazy Submodule Loading
`wepppy/__init__.py` uses `__getattr__` for lazy imports of: `rq`, `climates`, `mcp`, `nodb`, `profile_recorder`, `locales`, `weppcloud`. Agents hitting `AttributeError` on these names likely have an import ordering issue, not a missing module.

### RQ Job Flow
Route (Flask or rq-engine) → enqueue to Redis DB 9 → `WepppyRqWorker` executes `wepppy/rq/*.py` tasks → tasks acquire NoDb locks, call binaries/services, persist state → publish status to Redis DB 2 → `status2` (Go) fans out via WebSocket → `controllers_js` updates UI.

## Configuration Surface

Full reference: `docs/configuration-reference.md`. When troubleshooting config issues, check these primary sources:

| Source | Path | What it covers |
|--------|------|----------------|
| Redis settings | `wepppy/config/redis_settings.py` | Host, port, password, DB selection, connection pooling |
| Secrets | `wepppy/config/secrets.py` | `*_FILE` env var loading pattern |
| Flask config | `wepppy/weppcloud/configuration.py` | Session, auth, feature flags |
| Docker env | `docker/.env` (gitignored) | UID/GID, passwords, API keys |
| Docker defaults | `docker/defaults.env` | Template with documented defaults |
| Compose topology | `docker/docker-compose.dev.yml` | Service definitions, volumes, networks |
| RQ timeouts | env vars in rq-engine | `RQ_ENGINE_RQ_TIMEOUT` (216000s), `RQ_ENGINE_RUN_SYNC_TIMEOUT` (86400s), `RQ_ENGINE_MIGRATIONS_TIMEOUT` (7200s) |

Secret env vars follow the `*_FILE` pattern (e.g., `REDIS_PASSWORD_FILE=/run/secrets/redis_password`). See `wepppy/config/secrets.py:get_secret()` for the resolution chain.

## Debugging Playbook

### NoDb lock contention
- Check Redis DB 0 for `locked:*.nodb` keys: `redis-cli -n 0 KEYS 'locked:*'`
- Stale locks indicate a worker crashed mid-mutation. TTL is controlled by `WEPPPY_LOCK_TTL_SECONDS`.
- Lock retry pattern is in `wepppy/nodb/README.md` (backoff loop with `NoDbAlreadyLockedError`).

### RQ job failures
- Failed jobs land in `FailedJobRegistry` — no dead-letter queue or automated replay exists.
- Exception logs: `<run_dir>/exceptions.log` (written by `_append_exception_log`, which silently swallows I/O errors).
- Job metadata: `wepppy/rq/job_info.py` or the RQ dashboard (port 9181, basic auth).
- Status stream: Redis DB 2 channels `<runid>:rq`, `<runid>:status`.
- No correlation IDs between rq-engine requests and worker job execution — trace by `runid` + `job_id` across unstructured logs.

### WebSocket / status stream issues
- `status2` (Go service) proxies Redis DB 2 pub/sub to browser WebSocket.
- Check `wctl logs -f status2` for connection errors.
- Browser side: `controlBase.attach_status_stream()` in `controllers_js`.
- Keyspace notifications enabled (`Kh`) but no visible consumer — may be vestigial config.

### Import errors in tests
- Usually caused by incomplete `sys.modules` stubs. See `tests/AGENTS.md` § Module Stub Management.
- Run `wctl check-test-stubs` to validate stub completeness.
- The `_ensure_all_your_base` fixture in `tests/conftest.py` is session-scoped and prevents the most common stub gap.

### Redis connectivity
- All services share a single Redis instance. One container failure cascades.
- Persistence is disabled (`--save ""`, `--appendonly "no"`). Redis restart = total cache/session/in-flight-job loss.
- DB 11 is shared between Flask sessions and WD cache — potential key collision risk.

## Deployment Reference

### Local dev
```
wctl up -d                          # Start Docker Compose dev stack
wctl logs -f weppcloud              # Flask app logs
wctl logs -f rq-worker              # Worker logs
wctl run-pytest tests/<path>        # Run tests inside container
wctl run-npm lint && wctl run-npm test  # Frontend gates
```

### Production
- Compose: `docker/docker-compose.prod.yml` (+ overlays for prod.wepp1, prod.worker)
- Deploy script: `scripts/deploy-production.sh`
- Makefile targets: `make deploy-nuc2`, `make ci-dryrun`
- Images default to `:latest` tags — confirm explicit tags are set before deploying.
- Gunicorn runs as non-root `wepp` user (UID 1000:993).
- Caddy handles TLS termination and reverse proxy.

### CI/CD
- 37 GitHub Actions workflows generated from `scripts/build_forest_workflows.py` specs in `github/forest_workflows/`.
- Hand-editing `.github/workflows/` files will be overwritten on regeneration.
- All CI runs on self-hosted runners (`self-hosted`, `Linux`, `X64`, `homelab`) — no GitHub-hosted fallback.

## Security Review Checklist

When proactively scanning for vulnerabilities, check:

- [ ] **Secrets in code**: grep for hardcoded passwords, API keys, JWT secrets (test files use `pytest-secret-key` / `pytest-jwt-secret` — acceptable for tests only)
- [ ] **CORS configuration**: `CAP_CORS_ORIGIN` defaults to `*` in both dev and prod Compose files
- [ ] **Input validation on upload routes**: no file type validation, no size limits, no sandbox in current upload handlers
- [ ] **Exception handling**: broad exceptions are managed via `docs/standards/broad-exception-boundary-allowlist.md` and enforced by `tools/check_broad_exceptions.py --enforce-changed`. Verify new routes don't introduce unallowlisted broad handlers.
- [ ] **Auth bypass paths**: run-scoped endpoints must call `authorize_run_access(claims, runid)` in rq-engine; verify new routes follow this pattern
- [ ] **Redis ACLs**: single shared password across all services, no per-service ACL
- [ ] **Dependency CVEs**: no `pip-audit` or `safety` in CI; many deps use unpinned (`>=`) versions and git-branch deps without SHA pinning
- [ ] **Docker image tags**: prod Compose defaults to `:latest` — verify pinned tags before deployment

## Document Map

| Document | Audience | Purpose |
|----------|----------|---------|
| `CLAUDE.md` (this file) | Claude Code | Operating guide, debugging, deploy, security |
| `AGENTS.md` | Codex / coding agents | Conventions, validation gates, scope discipline |
| `CONTRIBUTING_AGENTS.md` | All agents | Day-1 contribution workflow |
| `ARCHITECTURE.md` | All contributors | Runtime topology, state contracts |
| `PROJECT_TRACKER.md` | All | Active initiatives kanban |
| `tests/AGENTS.md` | Codex | Test infrastructure, stubs, markers |
| Subsystem `AGENTS.md` files | Codex | Per-module coding playbooks |
| `docs/prompt_templates/` | Codex | Workflow templates for refactors, docs, quality |
