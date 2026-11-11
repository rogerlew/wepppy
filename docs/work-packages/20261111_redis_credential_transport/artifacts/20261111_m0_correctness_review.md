# M0 independent correctness review

**Reviewer**: Codex reviewer agent `contract_correctness`
**Date**: 2026-11-11 UTC
**Scope**: proposed transport contract, existing consumers and installed APIs;
no implementation or runtime acceptance approval.
**Reviewed source**: `824c183770ec87fb156e7ad1bbe8f600115ed388` plus the new
`docs/schemas/redis-credential-transport-contract.md` working-tree draft.
**M0 verdict**: PASS for the revised contract only. Initial findings and their
closure are retained below; implementation/runtime acceptance remains pending.

## Findings

1. **High — RQ config is bypassed by existing endpoint environment.** Installed
   RQ 2.12 `rq/cli/helpers.py:393` declares `--url` with `RQ_REDIS_URL` as its
   environment source. `CliConfig.connection` selects this URL before config.
   Changing startup argv to `-c` alone therefore retains legacy URL ingestion by
   RQ and bypasses separate credentials in worker-only deployments. The contract
   must specify how the adapter prevents this branch while preserving endpoint
   precedence and legacy URL input. Require a regression using both environment
   `RQ_REDIS_URL` and config mode.

2. **Medium — RQ config fields cannot preserve the stated interface alone.**
   Installed `get_redis_from_config` accepts host/port/DB/password and selected
   TLS fields, but does not forward username, general socket options or Unix
   socket paths. The contract's `Workers and dashboard` section must choose a
   concrete owned adapter using the existing `--connection-class` hook or a
   launcher that supplies native kwargs. It must preserve supported options and
   fail explicitly for unsupported ones. Adding `REDIS_USERNAME` to a config
   module would silently fail to preserve username.

3. **Medium — streamauth cloning rule changes established timeouts.** The
   contract says streamauth changes only DB and inherits service timeout/retry
   settings. Existing `services/streamauth/auth.go:66` also sets context timeout
   handling, one-second dial/read/write timeouts and `MaxRetries = 0`. Preserve
   these auth-specific settings on an initial clone, then change only DB between
   session DB 11 and revocation DB 0. Do not reinterpret go-redis's zero-retry
   setting during this transport-only migration.

4. **Medium — file terminator is ambiguous in the valid-state contract.**
   `docker/README.md:430` creates the password file with `print`, which adds LF.
   Existing shell command substitution removes trailing LF; native clients trim
   whitespace. The proposed prohibition on surrounding whitespace/CRLF must
   distinguish an allowed file terminator from forbidden password content and
   specify identical normalization before AUTH and server hashing. A raw-file
   prohibition would reject the documented generation workflow.

## Evidence and useful dispositions

- Read installed RQ 2.12 and redis-py 6.2 sources from the local virtualenv;
  no package update or network lookup was needed.
- The sibling dashboard's `rq_dashboard/web.py:79`, `:81` and `:92` already
  forward `RQ_DASHBOARD_REDIS_PASSWORD` separately through `client_options`.
  Its app factory supports `RQ_DASHBOARD_CONFIG`. An owned config adapter may
  therefore avoid editing the sibling, but environment overlay and nonprinting
  credential representation still need direct tests.
- Inventory `wepppy/webservices/rq_dashboard.py` separately from the deployed
  sibling dashboard. Inventory `scripts/deploy-production.sh:1281`, whose
  registration probe uses `from_url` with a separate file-loaded password.
- No confirmed deployed consumer of `redis_async_url` was found in `wepppy`;
  retain and test an explicit async constructor interface without claiming a
  migrated deployed async caller that does not exist.
- Server ACL hashing, protected runtime files, ephemeral CLI environment,
  synthetic canaries and isolated Compose acceptance are suitable design
  directions; operations/security review and real runtime evidence remain
  separate gates.

## Residual acceptance gates

After contract correction, M0 approval permits implementation only. It does not
prove real AUTH, session expiry, correct logical databases, worker registration
or dequeue, process/config nondisclosure, restart/rollback, deployed identity
parity or production readiness. Those remain M1-M4 evidence requirements.

## Re-review and disposition

All four M0 findings are closed in the revised canonical contract:

1. `Workers and dashboard` now requires explicit empty `--url` plus config and
   owned connection-class arguments, while the adapter resolves the original
   endpoint environment. A direct experiment with installed Click confirmed an
   empty explicit URL suppresses `RQ_REDIS_URL` environment lookup. Installed
   RQ's falsey `self.url` then selects config. The end-to-end invocation regression
   remains required because shell argument handling can still lose this value.
2. The same section chooses `wepppy.config.rq_redis.Connection` to construct from
   canonical native kwargs, and keeps credentials out of the imported config
   module. The installed RQ connection-class hook supports this design. Test
   worker-pool child construction, not only the adapter constructor.
3. `Native clients and diagnostics` now explicitly preserves streamauth's own
   context timeout, one-second socket timeouts and `MaxRetries=0`, followed by
   DB 11/0 cloning. This preserves the existing input to go-redis.
4. `Resolution and compatibility` now allows LF file terminators before the
   remaining deployed password bytes are validated and hashed. The documented
   print-based generation workflow is accepted without rotation or rewriting.

The independent correctness gate approves the revised M0 contract for the
standalone pre-implementation checkpoint. Runtime evidence must still establish
safe representations, pool versus client constructor compatibility, URL query
semantics, session overrides, ACL parsing and secret-file failure behavior.

Validation: `wctl doc-lint --path
docs/work-packages/20261111_redis_credential_transport/artifacts/20261111_m0_correctness_review.md`
passed with zero errors/warnings. No broad suite or runtime service mutation was
performed during this review.
