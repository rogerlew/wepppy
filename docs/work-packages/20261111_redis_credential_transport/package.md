# Redis credential transport hardening

**Status**: Open (2026-11-11 UTC); scaffolded, contract checkpoint required

**Timezone**: UTC

## Overview

Remove Redis passwords from connection URLs and process arguments while
preserving the existing mounted-secret lifecycle, Redis topology, logical
databases, default-user authorization and application behavior. Native Python
and Go clients will receive credentials through their existing constructor
fields or providers; CLI-only and Redis-server boundaries will receive
credential-file-aware adapters that do not publish the password in a URL or
argument list.

This package runs before the F5 traceback package so that avoidable
credential-bearing strings no longer enter exception paths. Validation is
intentionally scoped to the changed Redis, session, RQ, status, preflight,
streamauth, Compose and health boundaries. Full pytest and frontend suites are
not acceptance gates for this package.

## Threat Model

- **Assets**: the shared Redis password, sessions, RQ jobs, stream authorization
  state, status/preflight data and Redis availability.
- **Adversaries/failures**: credential disclosure through URLs, argv, error text,
  logs or process inspection; a migration that silently omits AUTH; wrong logical
  database selection; and a startup/health repair that disconnects workers.
- **Trust boundaries**: mounted secret file to Python, Go, shell/CLI and Redis
  server; application process to Redis AUTH; Compose configuration to runtime.
- **Assumption to prove**: the same secret authenticates every intended consumer
  without being materialized in a URL or long-lived command argument.

## Objectives

- Define a canonical Redis endpoint-plus-credential contract that keeps host,
  port, DB and TLS configuration separate from secret values.
- Convert Python sync, async and Flask-session consumers to constructor kwargs or
  credential providers while retaining supported credential-free URL input.
- Convert status2, preflight2 and streamauth to `redis.Options` with separate
  username/password fields.
- Start RQ worker pools through an RQ configuration/connection path that reads
  the mounted secret without a password-bearing `-u` argument.
- Remove the Redis server password from `redis-server --requirepass` argv using a
  protected generated ACL/config input, subject to the contract checkpoint.
- Replace `redis-cli -a` health/operator examples with a reviewed non-URL,
  non-argv credential path.
- Prove all changed boundaries through focused tests and actual scoped Compose
  connections; do not run the full Python or npm suites.

## Scope

### Included

- `wepppy/config/redis_settings.py`, Flask session construction and directly
  affected async consumers.
- `docker/rq-worker-startup.sh` and a minimal owned RQ configuration/launcher
  adapter using RQ's existing config-based connection path.
- status2, preflight2 and shared streamauth Redis configuration and constructors.
- Redis server entrypoint, healthchecks, canary/HPC variants, operator commands
  and rendered Compose assertions that currently expose credentials in URL or
  argv form.
- Backward-compatible parsing of legacy credential-bearing URLs only as an
  explicit transition input: extract once, remove userinfo from retained endpoint
  values, never log it, and give mounted-file credentials precedence.
- Focused Python, Go, shell/Compose, real Redis AUTH, session and RQ worker
  connection validation.

### Explicitly Out of Scope

- Changing the Redis password, secret rotation schedule or current secret-file
  lifecycle.
- Creating new Redis ACL users, command/key restrictions, logical DB mappings,
  Redis topology, persistence policy or TLS policy.
- A secrets manager, dynamic credential provider, new daemon or dependency.
- Traceback/log sanitization, which belongs to the dependent F5 package.
- Full pytest, npm lint or npm tests. The operator explicitly selected scoped
  validation for this package.
- Production deployment. Environment rollout requires separate authorization.

## Complexity Budget

- **Existing mechanisms reused**: `get_secret`, `redis_connection_kwargs`,
  redis-py constructor fields, go-redis `Options`, RQ config-based connections,
  Compose secrets, `wctl`, and the current Redis password/default user.
- **New mechanisms permitted**: one owned RQ config/launcher adapter and one
  protected Redis ACL/config materialization helper; no new dependency.
- **Simplest plausible change tested first**: keep endpoint URLs credential-free
  and pass the current file-loaded password directly to existing client fields.
- **Real acceptance condition**: real clients and RQ workers authenticate to the
  intended DBs while rendered config, argv inspection and logs contain no secret.
- **Evidence required before escalation**: a retained focused failure showing an
  existing client/config interface cannot accept separate credentials.
- **Explicitly prohibited expansion**: new identity service, Redis proxy,
  datastore, network topology, ACL permission redesign or secret rotation system.

## Implementation Fidelity and Evidence

- **Fidelity target**: faithful extraction of current connection behavior.
- **Authoritative source paths**: `wepppy/config/redis_settings.py`,
  `docker/rq-worker-startup.sh`, `docker/redis-entrypoint.sh`, status2/preflight2
  configs and `services/streamauth/auth.go`.
- **Cutover proof required**: every production Compose consumer resolves the
  same endpoint/DB and successfully authenticates using separate credential
  input; no old password URL/argv path remains except tested legacy ingestion.
- **Acceptance evidence type**: direct runtime connection evidence plus focused
  fixtures; no generated scientific output is involved.

## Generated Artifact Validation Gate

- **Applicable**: no. This package changes runtime credential transport and
  generated Compose configuration, not user data/model artifacts.
- **Direct unmocked boundary**: real Redis server AUTH, session set/get, RQ worker
  registration/dequeue smoke, status/preflight/streamauth Redis checks and
  rendered Compose/argv inspection.
- **Actual environment gate**: local canonical Compose is required. Forest or
  production deployment remains separately authorized.
- **Highest completion claim currently supported**: diagnosed/scaffolded.

## Stakeholders

- **Decision owner**: WEPPpy maintainer and Redis/deployment operator.
- **Primary implementers**: configuration, RQ, Go service and Docker maintainers.
- **Reviewers**: independent correctness, QA, security and operations reviewers.
- **Security reviewer**: required and independent of implementation.

## Success Criteria

- [ ] The credential transport contract and consumer inventory are reviewed and
      committed before implementation.
- [ ] Native Python and Go clients retain no password-bearing URL after config
      resolution and authenticate to the correct DB.
- [ ] RQ worker startup/probe/worker-pool registration contains no password in
      URL or argv and preserves queue/worker behavior.
- [ ] Redis server and healthcheck startup contain no raw password in argv,
      rendered Compose or retained logs; any protected ACL/config file has
      least-privilege permissions and cleanup/restart semantics.
- [ ] Legacy credential-bearing URL input is either safely normalized with
      mounted-file precedence or rejected explicitly; it is never re-emitted.
- [ ] Focused Python, Docker, Go, shell and real-Redis integration checks pass.
- [ ] Scoped Compose smoke proves sessions, RQ, status and preflight reach the
      expected logical databases.
- [ ] No full pytest or npm-suite pass is claimed or required.
- [ ] Correctness, QA, security and operations reviews pass.

## Parameterization ADR Gate

- **Parameterization change present**: no.
- **ADR required**: no.
- **Decision provenance captured**: yes, in this package and contract artifact.

## Dependencies

### Prerequisites

- Ratify legacy URL precedence, RQ config adapter and Redis server ACL/config
  materialization before code changes.
- Preserve the F4 stream authorization Redis DB 11/0 behavior.

### Blocks

- [Safe traceback and exceptional-path secret sanitization](../20261111_safe_traceback_sanitization/package.md)
  must not begin implementation until this package's scoped acceptance and
  reviews pass.

## Related Packages

- **Related**: [Status/preflight WebSocket authorization](../20261111_status_preflight_websocket_authorization/package.md).
- **Follow-up**: F5 safe traceback sanitization, linked above.

## Timeline Estimate

- **Expected duration**: 3-6 focused working days.
- **Complexity**: high because Redis is a shared process/container boundary.
- **Risk level**: high availability and secret-handling impact.

## Security Impact and Review Gate

- **Security impact triage**: high.
- **Dedicated security review required**: yes.
- **Triage rationale**: secret transport, Redis AUTH, process arguments and
  worker/session connectivity change across several services.
- **Security review artifact**:
  [artifacts/20261111_security_review.md](artifacts/20261111_security_review.md).
- **QA review artifact**:
  [artifacts/20261111_qa_review.md](artifacts/20261111_qa_review.md).

## Hardening and Observation Model

- **Failure signature**: a Redis password appears in a URL/argv/log, or a valid
  service cannot authenticate/select its established DB after cutover.
- **Health signals**: authenticated PING, session round trip, worker registration
  and queue smoke, service health, correct DB/key isolation and secret scans.
- **Danger signals**: fallback to unauthenticated Redis, password copied into a
  different environment variable, topology/ACL changes, or broad unrelated
  connection refactors.
- **Observation window**: focused local Compose acceptance plus separately
  authorized environment observation before production.
- **Temporary calluses**: legacy URL ingestion only, with explicit warning and a
  tracked retirement decision; never re-emit userinfo.

## Testing Scope Decision

Validation is intentionally scoped. Required commands are refined in the active
ExecPlan, but the gate includes `tests/test_redis_settings.py`, session tests,
RQ worker-startup/Compose contract tests, status2/preflight2/streamauth Go tests,
shell checks and a real canonical Compose Redis/RQ/session/service smoke. Do not
run or claim `wctl run-pytest tests --maxfail=1`, npm lint or full npm tests for
this package.

## References

- `docs/dev-notes/redis_config_refactor.md`
- `docs/dev-notes/redis_dev_notes.md`
- `docker/redis-entrypoint.sh`
- `docker/rq-worker-startup.sh`
- `wepppy/config/redis_settings.py`
- `services/streamauth/auth.go`

## Handoff

Execute this package before F5. Begin with the active ExecPlan, preserve current
secret values/lifecycle and working Redis behavior, and do not broaden into ACL
authorization redesign. No deployment action occurred during scaffolding.
